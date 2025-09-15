"""graph_to_sankey.py

Generate a Sankey preview HTML from graph JSON or from nodes.md + edges.md.

Usage:
  python3 Mycelium/graph_to_sankey.py from-json <graph.json> <out.html>
  python3 Mycelium/graph_to_sankey.py from-md <nodes.md> <edges.md> <out.html>

Notes:
- The output HTML uses D3 and d3-sankey loaded from CDN. If you want a fully offline
  single-file HTML, tell me and I'll inline the libraries (larger file).

"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

# Verbose flag
VERBOSE: bool = False


def vprint(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)


def load_tables_from_graph_json(path: str):
    vprint('load_tables_from_graph_json: loading', path)
    with open(path, 'r', encoding='utf-8') as f:
        graph = json.load(f)
    # nodes may be list or dict; convert to list of dicts
    nodes = []
    if 'nodes' in graph:
        if isinstance(graph['nodes'], list):
            nodes = graph['nodes']
        elif isinstance(graph['nodes'], dict):
            for k, v in graph['nodes'].items():
                if isinstance(v, str):
                    nodes.append({'id': k, 'name': k, 'path': v})
                elif isinstance(v, dict):
                    node = dict(v)
                    node.setdefault('id', k)
                    node.setdefault('name', k)
                    nodes.append(node)
                else:
                    nodes.append({'id': k, 'name': k, 'value': v})
    # edges: links or edges
    edges = []
    if 'links' in graph and isinstance(graph['links'], list):
        edges = graph['links']
        vprint('load_tables_from_graph_json: links count=', len(edges))
    elif 'edges' in graph and isinstance(graph['edges'], list):
        edges = graph['edges']
        vprint('load_tables_from_graph_json: edges count=', len(edges))
    return nodes, edges


# Try to import the MD table reader from graph_md_io if available; otherwise define a small parser
try:
    import graph_md_io as gmi
    read_md_table = gmi.read_md_table
except Exception:
    def read_md_table(md_path: str) -> List[Dict[str, Any]]:
        # Minimal parser to read pipe tables used in the project.
        with open(md_path, 'r', encoding='utf-8') as f:
            lines = [ln.rstrip('\n') for ln in f if ln.strip()]
        header_idx = None
        for i, ln in enumerate(lines):
            if '|' in ln:
                header_idx = i
                break
        if header_idx is None:
            return []
        header = [c.strip() for c in lines[header_idx].strip('| ').split('|')]
        rows = []
        for ln in lines[header_idx+2:]:
            if '|' not in ln:
                continue
            cells = [c.strip() for c in ln.strip('| ').split('|')]
            if len(cells) < len(header):
                cells += [''] * (len(header) - len(cells))
            row = {}
            for k, v in zip(header, cells):
                if not v:
                    row[k] = ''
                    continue
                v = v.strip()
                if (v.startswith('{') and v.endswith('}')) or (v.startswith('[') and v.endswith(']')):
                    try:
                        row[k] = json.loads(v)
                        continue
                    except Exception:
                        pass
                try:
                    if '.' in v:
                        row[k] = float(v)
                    else:
                        row[k] = int(v)
                    continue
                except Exception:
                    pass
                row[k] = v
            rows.append(row)
        return rows


def build_sankey_data(nodes_table: List[Dict[str, Any]], edges_table: List[Dict[str, Any]]):
    vprint('build_sankey_data: nodes=', len(nodes_table), 'edges=', len(edges_table))
    # Determine node id key
    id_key = None
    if nodes_table:
        sample = nodes_table[0]
        for k in ('id', 'Id', 'ID', 'name'):
            if any(k in n for n in nodes_table):
                id_key = k
                break
    if id_key is None:
        # use index as id
        for i, n in enumerate(nodes_table):
            n.setdefault('id', i)
        id_key = 'id'

    # Map node id to index
    node_ids = [str(n.get(id_key) or n.get('name') or n.get('path') or i) for i, n in enumerate(nodes_table)]
    id_to_index = {nid: i for i, nid in enumerate(node_ids)}

    # If nodes_table lacks explicit names, use name or id for label
    labels = []
    for i, n in enumerate(nodes_table):
        name = n.get('name') or n.get('title') or n.get(id_key) or n.get('path') or node_ids[i]
        labels.append(str(name))

    # Build links with numeric value
    links = []
    for e in edges_table:
        # find source and target keys
        src = e.get('source') or e.get('src') or e.get('src') or e.get('src') or e.get('src')
        if not src:
            src = e.get('src') or e.get('from') or e.get('src') or e.get('src')
        dst = e.get('target') or e.get('dst') or e.get('to') or e.get('dst') or e.get('dst')
        # fallback to common names used in preview
        if not src:
            src = e.get('src') or e.get('src')
        if not dst:
            dst = e.get('dst') or e.get('dst')
        if src is None or dst is None:
            # try the preview naming (src/dst)
            src = e.get('src') or e.get('source') or ''
            dst = e.get('dst') or e.get('target') or ''
        src = str(src)
        dst = str(dst)
        if src not in id_to_index or dst not in id_to_index:
            # try to find by matching name/path fields
            # attempt fuzzy match by node name
            found_src = None
            found_dst = None
            for k, v in id_to_index.items():
                if k == src or k.endswith('/' + src) or k.endswith(src):
                    found_src = v
                if k == dst or k.endswith('/' + dst) or k.endswith(dst):
                    found_dst = v
            if found_src is None or found_dst is None:
                continue
            s_idx = found_src
            t_idx = found_dst
        else:
            s_idx = id_to_index[src]
            t_idx = id_to_index[dst]
        # value
        val = e.get('value') or e.get('weight') or 1
        try:
            val = float(val)
        except Exception:
            val = 1
        links.append({'source': s_idx, 'target': t_idx, 'value': val, 'meta': e})
    vprint('build_sankey_data: built', len(links), 'raw links')

    # aggregate duplicate links between same pair by summing values
    agg = {}
    for l in links:
        key = (l['source'], l['target'])
        agg.setdefault(key, 0)
        agg[key] += l['value']
    final_links = [{'source': k[0], 'target': k[1], 'value': v} for k, v in agg.items()]

    nodes_out = [{'name': labels[i]} for i in range(len(labels))]
    vprint('build_sankey_data: final nodes', len(nodes_out), 'final links', len(final_links))
    return {'nodes': nodes_out, 'links': final_links}


HTML_TEMPLATE = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sankey Preview</title>
<style>
body { font-family: sans-serif; }
#chart { width: 100%; height: 800px; }
.node rect { cursor: move; fill-opacity: .9; shape-rendering: crispEdges; }
.node text { pointer-events: none; text-shadow: 0 1px 0 #fff; font-size: 12px; }
.link { fill: none; stroke: #000; stroke-opacity: .2; }
.link:hover { stroke-opacity: .5; }
</style>
</head>
<body>
<h2>Sankey Preview</h2>
<div id="chart"></div>
<!-- D3 and d3-sankey from CDN -->
<script src="https://unpkg.com/d3@7/dist/d3.min.js"></script>
<script src="https://unpkg.com/d3-sankey@0.12.3/dist/d3-sankey.min.js"></script>
<script>
// data placeholder
const graph = __GRAPH__;

const width = Math.max(960, window.innerWidth - 40);
const height = 800;

const svg = d3.select('#chart').append('svg')
    .attr('width', width)
    .attr('height', height);

const {nodes, links} = graph;

const sankey = d3.sankey()
    .nodeWidth(20)
    .nodePadding(10)
    .extent([[1, 1], [width - 1, height - 6]]);

const {nodes: graphNodes, links: graphLinks} = sankey({nodes: nodes.map(d => Object.assign({}, d)), links: links.map(d => Object.assign({}, d))});

const link = svg.append('g')
  .attr('fill', 'none')
  .attr('stroke-opacity', 0.5)
.selectAll('g')
  .data(graphLinks)
  .join('g')
  .style('mix-blend-mode', 'multiply');

link.append('path')
  .attr('d', d3.sankeyLinkHorizontal())
  .attr('stroke', '#888')
  .attr('stroke-width', d => Math.max(1, d.width))
  .attr('class', 'link')
  .append('title')
  .text(d => `${d.source.name} → ${d.target.name}\n${d.value}`);

const node = svg.append('g')
  .selectAll('g')
  .data(graphNodes)
  .join('g')
  .attr('class', 'node');

node.append('rect')
  .attr('x', d => d.x0)
  .attr('y', d => d.y0)
  .attr('height', d => Math.max(1, d.y1 - d.y0))
  .attr('width', d => Math.max(1, d.x1 - d.x0))
  .attr('fill', '#007acc')
  .append('title')
  .text(d => `${d.name}\n${d.value}`);

node.append('text')
  .attr('x', d => d.x0 - 6)
  .attr('y', d => (d.y1 + d.y0) / 2)
  .attr('dy', '0.35em')
  .attr('text-anchor', 'end')
  .text(d => d.name)
  .filter(d => d.x0 < width / 2)
  .attr('x', d => d.x1 + 6)
  .attr('text-anchor', 'start');

</script>
</body>
</html>
'''


def write_sankey_html(out_path: str, graph_data: Dict[str, Any]):
    vprint('write_sankey_html: writing', out_path)
    s = HTML_TEMPLATE.replace('__GRAPH__', json.dumps(graph_data, ensure_ascii=False))
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(s)


def _cli(argv: List[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    # global flags
    global VERBOSE
    args = list(argv[1:])
    if '--verbose' in args or '--debug' in args:
        VERBOSE = True
        args = [a for a in args if a not in ('--verbose', '--debug')]
    cmd = args[0] if args else ''
    if cmd == 'from-json':
        if len(args) < 3:
            print('usage: from-json <graph.json> <out.html>')
            return 2
        gj = args[1]
        out = args[2]
        nodes, edges = load_tables_from_graph_json(gj)
        data = build_sankey_data(nodes, edges)
        write_sankey_html(out, data)
        print('Wrote', out)
        return 0
    if cmd == 'from-md':
        if len(args) < 4:
            print('usage: from-md <nodes.md> <edges.md> <out.html>')
            return 2
        nm = args[1]
        em = args[2]
        out = args[3]
        vprint('from-md: reading', nm, em)
        nodes = read_md_table(nm)
        edges = read_md_table(em)
        data = build_sankey_data(nodes, edges)
        write_sankey_html(out, data)
        print('Wrote', out)
        return 0
    print('unknown command', cmd)
    return 3


if __name__ == '__main__':
    try:
        from Mycelium.cli_timer import run_with_timer
    except Exception:
        from cli_timer import run_with_timer
    raise SystemExit(run_with_timer(_cli, sys.argv))
