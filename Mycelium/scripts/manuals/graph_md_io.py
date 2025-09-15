"""graph_md_io.py
Utility to convert a graph stored as JSON (common d3 format with "nodes" and "links")
into two Markdown table files (`nodes.md`, `edges.md`) and to rebuild the JSON from those
Markdown tables.

This is intentionally dependency-free (standard library only) so it can be used easily
inside the existing Mycelium project.

Usage examples:
    python graph_md_io.py to-md path/to/mygraph.json out_dir
    python graph_md_io.py from-md out_dir/nodes.md out_dir/edges.md out.json

The produced Markdown tables are simple pipe-separated tables with a header row. Any
extra node/link attributes are preserved as additional table columns.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Any, Tuple

# Global verbose flag controlled by CLI
VERBOSE: bool = False


def vprint(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def json_to_tables(graph: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (nodes, edges) where each is a list of dicts.

    Supports common variants:
      - {'nodes': [...], 'links': [...]} (d3-like)
      - {'nodes': [...], 'edges': [...]} or {'nodes': [...], 'links': [...]} 
    """
    nodes = []
    edges = []

    vprint('json_to_tables: graph keys:', list(graph.keys()))
    if 'nodes' in graph:
        if isinstance(graph['nodes'], list):
            nodes = graph['nodes']
            vprint('json_to_tables: detected nodes as list, count=', len(nodes))
        elif isinstance(graph['nodes'], dict):
            # convert mapping id -> path (or value) into list of node dicts
            nodes = []
            for k, v in graph['nodes'].items():
                if isinstance(v, str):
                    nodes.append({'id': k, 'path': v, 'name': k})
                elif isinstance(v, dict):
                    node = dict(v)
                    node.setdefault('id', k)
                    node.setdefault('name', k)
                    nodes.append(node)
                else:
                    nodes.append({'id': k, 'name': k, 'value': v})
            vprint('json_to_tables: converted nodes mapping to list, count=', len(nodes))
    elif isinstance(graph.get('graph'), dict) and isinstance(graph['graph'].get('nodes'), list):
        nodes = graph['graph']['nodes']
    else:
        # try to infer nodes from edges
        nodes = []

    if 'links' in graph and isinstance(graph['links'], list):
        edges = graph['links']
        vprint('json_to_tables: detected links count=', len(edges))
    elif 'edges' in graph and isinstance(graph['edges'], list):
        edges = graph['edges']
        vprint('json_to_tables: detected edges count=', len(edges))
    else:
        # maybe edges stored at top-level
        edges = []

    return nodes, edges


def write_md_table(rows: List[Dict[str, Any]], out_path: str, index_field: str | None = None) -> None:
    """Write a list of dicts to a Markdown table file.

    The columns are the union of keys in all row dicts. Order: index_field first (if given),
    then sorted remaining keys.
    """
    vprint(f'write_md_table: writing {len(rows)} rows to {out_path} (index_field={index_field})')
    if not rows:
        # write an empty table with a single column 'id' to keep format stable
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('| id |\n')
            f.write('| --- |\n')
        return

    # Collect all keys
    keys = set()
    for r in rows:
        keys.update(r.keys())
    keys = list(keys)
    if index_field and index_field in keys:
        keys.remove(index_field)
        keys = [index_field] + sorted(keys)
    else:
        keys = sorted(keys)

    def to_cell(v: Any) -> str:
        if v is None:
            return ''
        if isinstance(v, (dict, list)):
            return json.dumps(v, ensure_ascii=False)
        return str(v)

    with open(out_path, 'w', encoding='utf-8') as f:
        # header
        f.write('| ' + ' | '.join(keys) + ' |\n')
        f.write('| ' + ' | '.join('---' for _ in keys) + ' |\n')
        # rows
        for r in rows:
            f.write('| ' + ' | '.join(to_cell(r.get(k, '')) for k in keys) + ' |\n')


def read_md_table(md_path: str) -> List[Dict[str, Any]]:
    """Parse a simple Markdown table (pipe separators) into list of dicts.

    - Expects header row then separator row (---). Additional whitespace is trimmed.
    - Cells containing valid JSON (starting with { or [) will be parsed.
    """
    vprint('read_md_table:', md_path)
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = [line.rstrip('\n') for line in f if line.strip()]

    # Find first header line with pipes
    header_idx = None
    for i, line in enumerate(lines):
        if '|' in line:
            header_idx = i
            break
    if header_idx is None:
        return []

    header_line = lines[header_idx]
    # Next line should be separator; we ignore and start at header_idx+2
    header = [c.strip() for c in header_line.strip('| ').split('|')]
    data_lines = []
    for l in lines[header_idx+2:]:
        if '|' not in l:
            continue
        data_lines.append(l)

    rows: List[Dict[str, Any]] = []
    for dl in data_lines:
        cells = [c.strip() for c in dl.strip('| ').split('|')]
        # pad
        if len(cells) < len(header):
            cells += [''] * (len(header) - len(cells))
        row: Dict[str, Any] = {}
        for k, v in zip(header, cells):
            if not v:
                row[k] = ''
                continue
            v = v.strip()
            # Try JSON parse for complex values
            if (v.startswith('{') and v.endswith('}')) or (v.startswith('[') and v.endswith(']')):
                try:
                    row[k] = json.loads(v)
                    continue
                except Exception:
                    pass
            # try number
            try:
                if '.' in v:
                    num = float(v)
                    row[k] = num
                else:
                    num = int(v)
                    row[k] = num
                continue
            except Exception:
                pass
            row[k] = v
        rows.append(row)
    vprint('read_md_table: parsed', len(rows), 'rows from', md_path)
    return rows


def json_to_md_files(json_path: str, out_dir: str) -> Tuple[str, str]:
    """Read a JSON graph and write nodes.md and edges.md to out_dir. Returns paths."""
    vprint('json_to_md_files: loading', json_path)
    with open(json_path, 'r', encoding='utf-8') as f:
        graph = json.load(f)

    nodes, edges = json_to_tables(graph)
    ensure_dir(out_dir)
    vprint('json_to_md_files: writing to', out_dir)
    nodes_path = os.path.join(out_dir, 'nodes.md')
    edges_path = os.path.join(out_dir, 'edges.md')
    # Prefer 'id' as index field for nodes if present; for edges prefer 'source'
    node_index = 'id' if any('id' in n for n in nodes) else None
    write_md_table(nodes, nodes_path, index_field=node_index)

    # For edges, standard keys are source, target, value/weight
    write_md_table(edges, edges_path, index_field='source' if any('source' in e for e in edges) else None)
    return nodes_path, edges_path


def md_files_to_json(nodes_md: str, edges_md: str) -> Dict[str, Any]:
    vprint('md_files_to_json: reading', nodes_md, edges_md)
    nodes = read_md_table(nodes_md)
    edges = read_md_table(edges_md)

    # Try to coerce edge keys to common names
    def normalize_edge(e: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(e)
        # normalize source-like keys to 'source'
        for s in ('source', 'src', 'from', 'id'):
            if s in out and 'source' not in out:
                out['source'] = out.pop(s)
                break
        # normalize target-like keys to 'target'
        for t in ('target', 'dst', 'to'):
            if t in out and 'target' not in out:
                out['target'] = out.pop(t)
                break
        # normalize weight/value
        if 'value' in out and 'weight' not in out:
            out['weight'] = out['value']
        if 'weight' in out and 'value' not in out:
            out['value'] = out['weight']
        return out

    edges = [normalize_edge(e) for e in edges]
    vprint('md_files_to_json: produced', len(nodes), 'nodes and', len(edges), 'edges')
    return {'nodes': nodes, 'links': edges}


def _safe_filename(name: str) -> str:
    """Return a filesystem-safe filename for the given string."""
    # replace slashes and problematic chars
    bad = '\\/:*?"<>|'
    out = ''.join('_' if c in bad else c for c in name)
    out = out.replace('\n', ' ').strip()
    if not out:
        out = 'node'
    return out


def json_to_flat_md(json_path: str, out_dir: str) -> List[str]:
    """Write one .md file per node into out_dir and return list of paths.

    Each node file contains a small YAML-like frontmatter (plain key: value lines)
    followed by an "Outgoing edges" Markdown table with targets and weights.
    """
    vprint('json_to_flat_md: loading', json_path)
    with open(json_path, 'r', encoding='utf-8') as f:
        graph = json.load(f)

    nodes, edges = json_to_tables(graph)
    ensure_dir(out_dir)
    vprint('json_to_flat_md: writing to', out_dir)

    # Map node ids to node dicts
    id_key = None
    # detect id-like key
    if nodes and isinstance(nodes[0], dict):
        for k in ('id', 'Id', 'ID', 'name'):
            if any(k in n for n in nodes):
                id_key = k
                break
    if id_key is None:
        # fallback: use index as id
        for i, n in enumerate(nodes):
            n.setdefault('id', i)
        id_key = 'id'

    node_map = {str(n.get(id_key)): n for n in nodes}

    # Group edges by source
    outgoing: Dict[str, List[Dict[str, Any]]] = {}
    for e in edges:
        src = str(e.get('source') or e.get('from') or e.get('src') or e.get('id') or '')
        if not src:
            vprint('json_to_flat_md: skipping edge with no source:', e)
            continue
        outgoing.setdefault(src, []).append(e)

    written: List[str] = []
    name_counts: Dict[str, int] = {}
    for nid, node in node_map.items():
        # Choose filename: prefer node name then id
        display = node.get('name') or node.get('title') or nid
        base = _safe_filename(str(display))
        # ensure uniqueness
        count = name_counts.get(base, 0)
        name_counts[base] = count + 1
        if count:
            filename = f"{base}-{count}.md"
        else:
            filename = f"{base}.md"
        path = os.path.join(out_dir, filename)
        vprint('json_to_flat_md: writing node file', path)
        with open(path, 'w', encoding='utf-8') as f:
            # simple frontmatter-ish block (not strict YAML to avoid extra deps)
            f.write('---\n')
            for k, v in sorted(node.items()):
                # write complex values as JSON
                if isinstance(v, (dict, list)):
                    f.write(f"{k}: {json.dumps(v, ensure_ascii=False)}\n")
                else:
                    f.write(f"{k}: {v}\n")
            f.write('---\n\n')

            outs = outgoing.get(nid, [])
            f.write('## Outgoing edges\n\n')
            if not outs:
                f.write('_No outgoing edges._\n')
            else:
                # collect union of keys for edge columns
                keys = set()
                for e in outs:
                    keys.update(e.keys())
                keys = list(keys)
                # prefer source, target, value ordering
                for pref in ('source', 'target', 'value', 'weight'):
                    if pref in keys:
                        keys.remove(pref)
                        keys.insert(0, pref)
                # write header
                f.write('| ' + ' | '.join(keys) + ' |\n')
                f.write('| ' + ' | '.join('---' for _ in keys) + ' |\n')
                for e in outs:
                    def c(v):
                        if v is None:
                            return ''
                        if isinstance(v, (dict, list)):
                            return json.dumps(v, ensure_ascii=False)
                        return str(v)
                    # Ensure bidirectional flag is present in written columns
                    if 'bidirectional' in keys and 'bidirectional' not in e:
                        e = dict(e)
                        e['bidirectional'] = bool(e.get('bidirectional', False))
                    f.write('| ' + ' | '.join(c(e.get(k, '')) for k in keys) + ' |\n')

        written.append(path)
    vprint('json_to_flat_md: wrote', len(written), 'files')

    return written


def _cli(argv: List[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    # Extract global flags
    global VERBOSE
    args = list(argv[1:])
    if '--verbose' in args or '--debug' in args:
        VERBOSE = True
        # remove the flag(s) so subcommands see clean argv positions
        args = [a for a in args if a not in ('--verbose', '--debug')]
    cmd = args[0] if args else ''
    if cmd == 'to-md':
        if len(args) < 3:
            print('usage: to-md <json-in> <out-dir>')
            return 2
        json_in = args[1]
        out_dir = args[2]
        n, e = json_to_md_files(json_in, out_dir)
        print('Wrote', n, e)
        return 0
    if cmd == 'from-md':
        if len(args) < 4:
            print('usage: from-md <nodes.md> <edges.md> <json-out>')
            return 2
        nodes_md = args[1]
        edges_md = args[2]
        out_json = args[3]
        graph = md_files_to_json(nodes_md, edges_md)
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        print('Wrote', out_json)
        return 0
    if cmd == 'to-flat':
        if len(args) < 3:
            print('usage: to-flat <json-in> <out-dir>')
            return 2
        json_in = args[1]
        out_dir = args[2]
        files = json_to_flat_md(json_in, out_dir)
        print('Wrote', len(files), 'files to', out_dir)
        for p in files[:200]:
            print(' -', p)
        return 0
    print('unknown command', cmd)
    return 3


if __name__ == '__main__':
    try:
        from Mycelium.cli_timer import run_with_timer
    except Exception:
        # local import fallback
        from cli_timer import run_with_timer
    raise SystemExit(run_with_timer(_cli, sys.argv))
