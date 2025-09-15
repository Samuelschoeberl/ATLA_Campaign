#!/usr/bin/env python3
"""Generate an animated HTML that shows PageRank (or weight) snapshots over time.

Looks for files named like: <timestamp>_<root>.md and extracts a node->weight mapping
from either a JSON code block or the first markdown pipe table in the file.

Outputs a self-contained `mycelium_animation.html` that animates circle sizes over time.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import json
from math import ceil, sqrt
from typing import Dict, List, Tuple


def parse_snapshot_file(path: Path) -> Dict[str, float]:
    txt = path.read_text(encoding='utf-8', errors='replace')
    # 1) look for a fenced ```json block
    m = re.search(r"```json\s*(\{.*?\})\s*```", txt, re.S)
    if m:
        try:
            return {k: float(v) for k, v in json.loads(m.group(1)).items()}
        except Exception:
            pass

    # 2) parse first pipe table (two columns expected: node | weight)
    lines = [ln for ln in txt.splitlines() if ln.strip()]
    start = None
    for i, ln in enumerate(lines):
        if '|' in ln:
            start = i
            break
    if start is not None:
        table_lines = []
        for ln in lines[start:]:
            if '|' not in ln:
                break
            table_lines.append(ln)
        rows = []
        for row in table_lines:
            parts = [p.strip() for p in row.strip().strip('|').split('|')]
            if len(parts) >= 2:
                left, right = parts[0], parts[1]
                # skip separators
                if re.fullmatch(r'-+', left) or re.fullmatch(r'-+', right):
                    continue
                rows.append((left, right))
        out = {}
        for a, b in rows:
            # try numeric parse
            mnum = re.search(r'(-?\d+\.?\d*)', b)
            if mnum:
                try:
                    out[a] = float(mnum.group(1))
                except Exception:
                    out[a] = 0.0
            else:
                # try JSON-like value
                try:
                    out[a] = float(b)
                except Exception:
                    out[a] = 0.0
        if out:
            return out

    # 3) fallback: search for lines like 'Node: <name> = <num>' or '<name> <num>'
    out = {}
    for ln in txt.splitlines():
        m = re.search(r"^\s*([^:\s][^:=]+?)\s*[:=]\s*(-?\d+\.?\d*)\s*$", ln)
        if m:
            try:
                out[m.group(1).strip()] = float(m.group(2))
            except Exception:
                pass
    return out


def collect_snapshots(dirpath: Path) -> List[Tuple[str, Dict[str, float]]]:
    files = []
    for p in sorted(dirpath.iterdir()):
        if p.is_file() and re.match(r"^\d+_.*\.md$", p.name):
            files.append(p)
    snapshots: List[Tuple[str, Dict[str, float]]] = []
    for p in files:
        ts = p.name.split('_', 1)[0]
        data = parse_snapshot_file(p)
        if data:
            snapshots.append((ts, data))
    return snapshots


def build_animation_html(snapshots: List[Tuple[str, Dict[str, float]]], outpath: Path) -> None:
    # gather all node ids
    nodes = []
    node_set = set()
    for _, d in snapshots:
        for k in d.keys():
            if k not in node_set:
                node_set.add(k)
                nodes.append(k)

    # build time series data structure
    times = []
    series = []
    maxw = 0.0
    for ts, d in snapshots:
        times.append(ts)
        row = [d.get(n, 0.0) for n in nodes]
        maxw = max(maxw, max(row) if row else 0.0)
        series.append(row)

    # compute grid layout so positions are deterministic
    n = len(nodes)
    cols = int(ceil(sqrt(max(1, n))))
    spacing = 100
    positions = []
    for i in range(n):
        x = (i % cols) * spacing + 60
        y = (i // cols) * spacing + 60
        positions.append((x, y))

    payload = {
        'nodes': nodes,
        'positions': positions,
        'times': times,
        'series': series,
        'maxw': maxw,
    }

    js_payload = json.dumps(payload)
    tpl = (
        "<!doctype html>\n"
        "<html>\n"
        "<head>\n"
        "  <meta charset=\"utf-8\">\n"
        "  <title>Mycelium PageRank Animation</title>\n"
        "  <script src=\"https://d3js.org/d3.v7.min.js\"></script>\n"
        "  <style>\n"
        "    body { font-family: Arial, sans-serif; }\n"
        "    .node-label { font-size: 10px; text-anchor: middle; pointer-events: none; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <h3>Mycelium PageRank Animation</h3>\n"
        "  <div id=\"timeline\"></div>\n"
        "  <svg id=\"viz\" width=\"1200\" height=\"800\"></svg>\n"
        "  <script>\n"
        "  const data = " + js_payload + ";\n"
        "  const svg = d3.select('#viz');\n"
        "  const nodes = data.nodes.map(function(name,i){ return {name:name, x:data.positions[i][0], y:data.positions[i][1], idx:i}; });\n"
        "  const maxw = data.maxw || 1.0;\n"
        "  const radiusScale = d3.scaleSqrt().domain([0, maxw]).range([2, 48]);\n"
        "\n"
        "  // draw\n"
        "  const g = svg.append('g');\n"
        "  const nodeG = g.selectAll('g.node').data(nodes).enter().append('g').attr('class','node').attr('transform',function(d){return 'translate(' + d.x + ',' + d.y + ')';});\n"
        "  nodeG.append('circle').attr('r',2).attr('fill','#69b3a2').attr('stroke','#222');\n"
        "  nodeG.append('text').attr('class','node-label').attr('y',4).text(function(d){return d.name});\n"
        "\n"
        "  var tix = 0;\n"
        "  function updateFrame(i){\n"
        "    var row = data.series[i];\n"
        "    nodeG.select('circle').transition().duration(800).attr('r',function(d){ return radiusScale(row[d.idx]||0); });\n"
        "    d3.select('#timeline').text('Snapshot ' + (i+1) + '/' + data.times.length + ' — ' + data.times[i]);\n"
        "  }\n"
        "\n"
        "  // autoplay\n"
        "  updateFrame(0);\n"
        "  setInterval(function(){ tix = (tix + 1) % data.times.length; updateFrame(tix); }, 1200);\n"
        "  </script>\n"
        "</body>\n"
        "</html>\n"
    )

    outpath.write_text(tpl, encoding='utf-8')


def main(argv=None):
    p = argparse.ArgumentParser(description='Animate PageRank snapshots into an HTML file')
    p.add_argument('--dir', default='.', help='Directory containing <timestamp>_<root>.md snapshot files')
    p.add_argument('--out', default='Mycelium/mycelium_animation.html', help='Output HTML path')
    args = p.parse_args(argv)

    dirp = Path(args.dir)
    snaps = collect_snapshots(dirp)
    if not snaps:
        print('No snapshots found. Looked for files like <timestamp>_*.md in', dirp)
        return 1
    build_animation_html(snaps, Path(args.out))
    print('Wrote animation to', args.out)
    return 0


if __name__ == '__main__':
    try:
        from Mycelium.cli_timer import run_with_timer
    except Exception:
        from cli_timer import run_with_timer
    raise SystemExit(run_with_timer(main))
