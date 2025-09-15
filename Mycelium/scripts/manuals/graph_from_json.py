#!/usr/bin/env python3
"""Create Plotly sunburst and treemap HTML files from a graph JSON produced by the Mycelium manager.

Usage:
    python3 Mycelium/graph_from_json.py <in.json> [--out-dir <dir>]

The JSON should have shape: {"nodes": {id: path, ...}, "edges": [...]}
We treat each node id as a hierarchical path split on '/'. Each node contributes value=1; parents aggregate.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import List

try:
    import plotly.express as px
except Exception:
    print('plotly is required. Install with: pip install plotly', file=sys.stderr)
    raise


def load_graph(path: Path):
    j = json.loads(path.read_text(encoding='utf-8'))
    # Support three input shapes:
    # 1) {"nodes": {id: path, ...}, "edges": [...]}  (existing)
    # 2) {"nodes": [id, id, ...]}                      (nodes as a list)
    # 3) [id, id, ...]                                   (top-level list of paths)
    if isinstance(j, dict):
        nodes = j.get('nodes', {})
        # If nodes is a list, convert to dict for downstream logic (keys are used)
        if isinstance(nodes, list):
            nodes = {str(n): str(n) for n in nodes}
        elif isinstance(nodes, dict):
            # keep as-is
            pass
        else:
            # Fallback: coerce other types into an empty dict
            nodes = {}
        return nodes
    elif isinstance(j, list):
        # Top-level list of path strings -> convert to dict
        return {str(n): str(n) for n in j}
    else:
        # Unknown format
        raise ValueError(f'Unsupported JSON shape in {path}: {type(j)!r}')


def build_rows(nodes: dict) -> List[dict]:
    rows = []
    for nid in nodes:
        # split by / to produce hierarchy; remove empty parts
        parts = [p for p in nid.split('/') if p]
        if not parts:
            parts = [nid]
        row = {f'level_{i}': parts[i] if i < len(parts) else None for i in range(len(parts))}
        # store the parts as a list for later
        row['parts'] = parts
        row['value'] = 1
        rows.append(row)
    return rows


def expand_rows_to_df(rows: List[dict]):
    # Determine max depth
    maxd = max(len(r['parts']) for r in rows) if rows else 0
    data = []
    for r in rows:
        entry = {}
        for i in range(maxd):
            entry[f'level_{i}'] = r['parts'][i] if i < len(r['parts']) else None
        entry['value'] = r['value']
        data.append(entry)
    return data, maxd


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print('Usage: graph_from_json.py <in.json> [--out-dir <dir>]')
        return 2
    inp = Path(argv[0])
    out_dir = Path('Mycelium/graphs')
    if '--out-dir' in argv:
        idx = argv.index('--out-dir')
        out_dir = Path(argv[idx+1])
    out_dir.mkdir(parents=True, exist_ok=True)

    nodes = load_graph(inp)
    rows = build_rows(nodes)
    data, maxd = expand_rows_to_df(rows)

    # Build path columns order
    path_cols = [f'level_{i}' for i in range(maxd)]

    # Create sunburst
    fig_sun = px.sunburst(
        data_frame=data,
        path=path_cols,
        values='value',
        title=inp.stem + ' — Sunburst',
    )
    sun_out = out_dir / (inp.stem + '_sunburst.html')
    fig_sun.write_html(str(sun_out))
    print('Wrote', sun_out)

    # Create treemap
    fig_tree = px.treemap(
        data_frame=data,
        path=path_cols,
        values='value',
        title=inp.stem + ' — Treemap',
    )
    tree_out = out_dir / (inp.stem + '_treemap.html')
    fig_tree.write_html(str(tree_out))
    print('Wrote', tree_out)

    return 0


if __name__ == '__main__':
    try:
        from Mycelium.cli_timer import run_with_timer
    except Exception:
        from cli_timer import run_with_timer
    raise SystemExit(run_with_timer(main))
