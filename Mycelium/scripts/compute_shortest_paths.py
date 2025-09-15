#!/usr/bin/env python3
"""Build a file network from wikilinks (or consume an existing graph JSON) and compute
shortest-path hop distances between files. Output is suitable for use by pagerank
weighting or further graph analytics.

Usage:
  python3 Mycelium/compute_shortest_paths.py --root /path/to/repo [--from-json Mycelium/weighted_graph.json] [--apply] [--max-depth N]

Outputs (when --apply):
  - Mycelium/file_network.json  : { nodes: [...], adjacency: { node: [neigh,...] } }
  - Mycelium/distances.json     : { source: { target: distance (int hops) } }

Behavior:
 - If --from-json provided, tries to extract nodes/edges from that JSON (expects edges with 'source' and 'dest' or similar keys).
 - Otherwise scans .md files under the repo root, uses [[link]] tokens and simple heuristics to resolve targets.
 - Computes unweighted shortest path hop-distances (BFS). Use --max-depth to limit search depth.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import deque
from pathlib import Path
from typing import Dict, List, Set


LINK_RE = re.compile(r"\[\[([^\]\|\n]+)(?:\|[^\]\n]+)?\]\]")


def get_excludes(root: Path):
    try:
        from Mycelium import config_common

        return list(config_common.get_graph_excludes(root))
    except Exception:
        return ['backups/', 'Mycelium/']


def find_md_files(root: Path, excludes: List[str]) -> List[Path]:
    files = []
    from Mycelium.fsutil import iter_md_files
    for p in iter_md_files(root):
        rel = p.relative_to(root).as_posix()
        if any(rel.startswith(x.rstrip('/')) for x in excludes):
            continue
        files.append(p)
    return sorted(files)


def parse_links(text: str) -> List[str]:
    return [m.group(1).strip() for m in LINK_RE.finditer(text)]


def resolve_link(link: str, md_files: List[Path], root: Path) -> List[Path]:
    candidates: List[Path] = []
    # sanitize link: remove newlines and trim
    link = link.splitlines()[0].strip()
    if not link:
        return []
    if '/' in link:
        p = root.joinpath(link)
        try:
            if p.exists() and p.suffix == '.md':
                candidates.append(p)
        except OSError:
            # skip pathological path
            pass
        pmd = root.joinpath(link + '.md')
        try:
            if pmd.exists():
                candidates.append(pmd)
        except OSError:
            pass

    for f in md_files:
        if f.stem == link or f.name == link or f.name == f"{link}.md":
            candidates.append(f)

    seen = set()
    out = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def build_network_from_md(root: Path, excludes: List[str]):
    md_files = find_md_files(root, excludes)
    md_index = {p: idx for idx, p in enumerate(md_files)}
    adjacency: Dict[str, List[str]] = {p.as_posix(): [] for p in md_files}

    for src in md_files:
        try:
            txt = src.read_text(encoding='utf8', errors='ignore')
        except Exception:
            continue
        links = parse_links(txt)
        for link in links:
            targets = resolve_link(link, md_files, root)
            for t in targets:
                adjacency[src.as_posix()].append(t.as_posix())

    nodes = [p.as_posix() for p in md_files]
    return nodes, adjacency


def build_network_from_json(path: Path):
    raw = json.loads(path.read_text(encoding='utf8'))
    nodes = []
    adjacency: Dict[str, List[str]] = {}
    # heuristics: raw may contain 'nodes' and 'edges'
    if isinstance(raw, dict) and 'nodes' in raw and 'edges' in raw:
        for n in raw['nodes']:
            if isinstance(n, dict):
                nid = n.get('id') or n.get('name') or n.get('label')
            else:
                nid = n
            if nid is None:
                continue
            nodes.append(str(nid))
            adjacency[str(nid)] = []
        for e in raw['edges']:
            src = e.get('source') or e.get('src') or e.get('from')
            dst = e.get('dest') or e.get('target') or e.get('to')
            if src is None or dst is None:
                continue
            adjacency.setdefault(str(src), []).append(str(dst))
    else:
        raise RuntimeError('Unsupported JSON graph format')

    return nodes, adjacency


def bfs_shortest_paths(nodes: List[str], adjacency: Dict[str, List[str]], max_depth: int | None = None):
    distances: Dict[str, Dict[str, int]] = {}
    for src in nodes:
        dist: Dict[str, int] = {src: 0}
        q = deque([src])
        while q:
            cur = q.popleft()
            dcur = dist[cur]
            if max_depth is not None and dcur >= max_depth:
                continue
            for nb in adjacency.get(cur, []):
                if nb not in dist:
                    dist[nb] = dcur + 1
                    q.append(nb)
        distances[src] = dist
    return distances


def main() -> int:
    ap = argparse.ArgumentParser(description='Build file network and compute shortest path hop distances')
    ap.add_argument('--root', default=None, help='Repository root (if omitted, will try Mycelium config)')
    ap.add_argument('--from-json', help='Path to JSON graph to consume instead of scanning .md files')
    ap.add_argument('--apply', action='store_true', help='Write outputs into Mycelium/')
    ap.add_argument('--max-depth', type=int, default=None, help='Limit BFS to this hop depth (limits computation)')
    ap.add_argument('--max-distance', type=int, default=None, help='When writing distances.json, only retain target distances <= this threshold (saves space)')
    args = ap.parse_args()

    # prefer explicit CLI root; otherwise attempt to read from Mycelium config markdowns
    if args.root:
        root = Path(args.root)
    else:
        try:
            from Mycelium.helpers.path_vars import find_path_var
            guessed = find_path_var(Path('.'))
        except Exception:
            guessed = None
        root = Path(guessed) if guessed else Path('.')
    excludes = get_excludes(root)

    if args.from_json:
        graph_path = Path(args.from_json)
        print(f"Loading graph from JSON: {graph_path}")
        nodes, adjacency = build_network_from_json(graph_path)
    else:
        print(f"Scanning markdown under {root} (excludes={excludes}) to build network...")
        nodes, adjacency = build_network_from_md(root, excludes)

    print(f"Built network: {len(nodes)} nodes, adjacency entries: {len(adjacency)}")

    distances = bfs_shortest_paths(nodes, adjacency, max_depth=args.max_depth)
    # stats
    total_pairs = sum(len(d) for d in distances.values())
    print(f"Computed shortest-path distances: total reachable pairs={total_pairs}")

    if not args.apply:
        print('Dry-run: no files written. Use --apply to write Mycelium/file_network.json and Mycelium/distances.json')
        return 0

    outdir = root.joinpath('Mycelium')
    outdir.mkdir(parents=True, exist_ok=True)
    fn = outdir.joinpath('file_network.json')
    dn = outdir.joinpath('distances.json')
    fn.write_text(json.dumps({'nodes': nodes, 'adjacency': adjacency}, indent=2), encoding='utf8')
    # Optionally prune distances to only keep targets within max_distance
    if args.max_distance is not None:
        pruned = {}
        for src, distmap in distances.items():
            small = {t: d for t, d in distmap.items() if d <= args.max_distance}
            pruned[src] = small
        dn.write_text(json.dumps(pruned, indent=2), encoding='utf8')
        print(f"Wrote pruned distances (max_distance={args.max_distance}) to {dn}")
    else:
        dn.write_text(json.dumps(distances, indent=2), encoding='utf8')
        print(f"Wrote {fn} and {dn}")
    print(f"Wrote {fn} and {dn}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
