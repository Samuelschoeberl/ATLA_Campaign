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
        title=inp.stem + '  Sunburst',
    )
    sun_out = out_dir / (inp.stem + '_sunburst.html')
    fig_sun.write_html(str(sun_out))
    print('Wrote', sun_out)

    # Create treemap
    fig_tree = px.treemap(
        data_frame=data,
        path=path_cols,
        values='value',
        title=inp.stem + '  Treemap',
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
#!/usr/bin/env python3
"""Minimal graph_from_json shim.
This writes a tiny HTML stub listing the number of files in the provided index.
Used only so `grow_mushroom.py` can call a helper script without failing if the
real graph generator is absent.

Usage: python3 graph_from_json.py <index.json> --out-dir <outdir>
"""
from pathlib import Path
import argparse
import json
import sys
import html as html_mod

def main(argv=None):
    ap = argparse.ArgumentParser(description='Stub graph_from_json')
    ap.add_argument('index_file')
    ap.add_argument('--out-dir', '-o', default='.', help='Output directory')
    args = ap.parse_args(argv)
    idx = Path(args.index_file)
    out = Path(args.out_dir)
    try:
        files = json.loads(idx.read_text(encoding='utf-8'))
    except Exception:
        files = []
    out.mkdir(parents=True, exist_ok=True)
    html_parts = []
    html_parts.append('<!doctype html>')
    html_parts.append('<html><head><meta charset="utf-8"><title>Graph stub</title>')
    html_parts.append('<style>body{font-family:system-ui,Helvetica,Arial,sans-serif;padding:18px}pre{background:#f8f8f8;border:1px solid #eee;padding:12px;overflow:auto;max-height:420px}details{margin-bottom:12px}summary{font-weight:600;cursor:pointer}</style>')
    html_parts.append('</head><body>')
    html_parts.append(f'<h1>Graph stub for {html_mod.escape(idx.name)}</h1>')
    html_parts.append(f'<p>Found {len(files)} files in index.</p>')

    # For each referenced file, attempt to read and embed its contents.
    if not files:
        html_parts.append('<p><em>No files listed in index.</em></p>')
    else:
        for f in files:
            try:
                p = Path(f)
                # if path is relative, resolve against repository root (cwd)
                if not p.is_absolute():
                    p = Path.cwd().joinpath(p)
                display_path = str(p)
                if p.exists() and p.is_file():
                    try:
                        txt = p.read_text(encoding='utf-8', errors='replace')
                        esc = html_mod.escape(txt)
                        html_parts.append(f'<details><summary>{html_mod.escape(display_path)}</summary><pre>{esc}</pre></details>')
                    except Exception as e:
                        html_parts.append(f'<details><summary>{html_mod.escape(display_path)}</summary><pre>Could not read file: {html_mod.escape(str(e))}</pre></details>')
                else:
                    html_parts.append(f'<details><summary>{html_mod.escape(display_path)}</summary><pre>File not found</pre></details>')
            except Exception as e:
                html_parts.append(f'<details><summary>{html_mod.escape(str(f))}</summary><pre>Error: {html_mod.escape(str(e))}</pre></details>')

    html_parts.append('</body></html>')
    html = '\n'.join(html_parts)
    try:
        out.joinpath('graph_stub.html').write_text(html, encoding='utf-8')
    except Exception as e:
        print('Could not write stub:', e, file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
