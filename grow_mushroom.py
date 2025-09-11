#!/usr/bin/env python3
"""grow_mushroom.py

Scan the workspace for mushrooms declared in `Mycelium/Mycelium_config.md` (lines like `_/Name/`).
For each mushroom:
 - create a folder at `Mycelium/<Name>` (if it doesn't exist)
 - BFS-traverse the workspace (excluding the mushroom's own folder) and collect any .md files
   that contain a wikilink of the form `[[Name]]`.
 - construct a small directory/file size subnetwork for the collected files and write
   two Plotly HTML visualisations: `<Name>_sunburst.html` and `<Name>_treemap.html`.

This is a lightweight, self-contained helper inspired by `Wikigraphs.py` but focussed
on building per-mushroom subnetworks.

Usage:
  python3 grow_mushroom.py

Dependencies: plotly (install with `pip install plotly`)
"""
from __future__ import annotations
from collections import deque
from pathlib import Path
from typing import Dict, List, Set, Tuple
import re
import sys
import json
import colorsys
import hashlib

try:
    import plotly.graph_objects as go
except Exception:  # pragma: no cover - helpful message if plotly missing
    go = None


ROOT = Path('.').resolve()
MYCELIUM_CONFIG = ROOT / 'Mycelium' / 'Mycelium_config.md'
OUT_BASE = ROOT / 'Mycelium' / 'Mushrooms'
MD_EXTS = {'.md', '.markdown'}


def parse_mycelium_config(p: Path) -> List[str]:
    """Return list of mushroom names parsed from lines like '_/Name/'"""
    if not p.exists():
        return []
    txt = p.read_text(encoding='utf-8')
    names = [m.group(1) for m in re.finditer(r"_/([^/]+)/", txt)]
    # unique & preserve order
    seen = set()
    out = []
    for n in names:
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def bfs_collect_linked_files(root: Path, target: str, exclude_dirs: Set[Path]) -> Set[Path]:
    """BFS-traverse `root` and return set of files that contain '[[target]]'.

    exclude_dirs is a set of absolute Path directories to skip entirely.
    We mark visited directories to ensure each directory is processed once.
    """
    found: Set[Path] = set()
    q = deque([root])
    visited_dirs: Set[Path] = set()

    link_pat = re.compile(r"\[\[\s*" + re.escape(target) + r"\s*\]\]")

    while q:
        d = q.popleft()
        try:
            d = d.resolve()
        except Exception:
            continue
        if d in visited_dirs:
            continue
        visited_dirs.add(d)
        # skip excludes
        if any(str(d).startswith(str(ed)) for ed in exclude_dirs):
            continue
        try:
            for child in sorted(d.iterdir()):
                # skip symlinks that might loop
                try:
                    if child.is_dir():
                        q.append(child)
                        continue
                except Exception:
                    continue

                if child.suffix.lower() in MD_EXTS:
                    try:
                        txt = child.read_text(encoding='utf-8')
                    except Exception:
                        continue
                    if link_pat.search(txt):
                        found.add(child.resolve())
        except PermissionError:
            continue
        except FileNotFoundError:
            continue

    return found


def build_sizes_map(files: Set[Path], base: Path) -> Dict[str, int]:
    """Given a set of file Paths, build a mapping of keys -> size bytes.

    Keys are directory-like strings. Files appear as 'a/b/file.md' and
    directories end with '/'. A root key '/' is included.
    """
    sizes: Dict[str, int] = {}
    base = base.resolve()
    def add_file(p: Path):
        rel = p.resolve().relative_to(base)
        parts = rel.parts
        # file key
        file_key = '/'.join(parts)
        try:
            sz = p.stat().st_size
        except Exception:
            sz = 0
        sizes[file_key] = sz
        # add directory aggregates and keys
        for i in range(1, len(parts)):
            dir_key = '/'.join(parts[:i]) + '/'
            sizes.setdefault(dir_key, 0)
            sizes[dir_key] += sz
        # add root
        sizes.setdefault('/', 0)
        sizes['/'] += sz

    for f in sorted(files):
        if base in f.parents or f == base:
            add_file(f)
        else:
            # file outside base; create a synthetic top-level grouping by its first part
            try:
                rel = f.resolve().relative_to(ROOT)
            except Exception:
                rel = f.name
            fake_key = str(rel)
            try:
                sz = f.stat().st_size
            except Exception:
                sz = 0
            sizes[fake_key] = sz
            sizes.setdefault('/', 0)
            sizes['/'] += sz

    return sizes


def build_plotly_lists(sizes: Dict[str, int], root_label: str = 'root') -> Tuple[List[str], List[str], List[str], List[int]]:
    """Convert sizes mapping to Plotly ids, labels, parents, values.
    Simple approach: use keys as ids; parent is the immediate directory containing the item.
    """
    ids: List[str] = []
    labels: List[str] = []
    parents: List[str] = []
    values: List[int] = []

    # ensure deterministic order
    items = sorted(sizes.items(), key=lambda kv: (kv[0].count('/'), kv[0]))

    for key, val in items:
        ids.append(key)
        if key == '/':
            labels.append(root_label)
            parents.append("")
            values.append(val)
            continue
        if key.endswith('/'):
            lab = key.rstrip('/').split('/')[-1] or key
            labels.append(lab)
            parent = '/'.join(key.rstrip('/').split('/')[:-1])
            if parent:
                parent = parent + '/'
            else:
                parent = '/'
            parents.append(parent)
            values.append(val)
        else:
            lab = key.split('/')[-1]
            labels.append(lab)
            parent = '/'.join(key.split('/')[:-1])
            if parent:
                parent = parent + '/'
            else:
                parent = '/'
            parents.append(parent)
            values.append(val)

    return ids, labels, parents, values


def write_graphs_for_mushroom(mushroom: str, files: Set[Path], out_dir: Path) -> Tuple[int, bool]:
    out_dir.mkdir(parents=True, exist_ok=True)
    idx_file = out_dir / 'subnetwork.json'
    idx = [str(p.relative_to(ROOT)) for p in sorted(files)]
    idx_file.write_text(json.dumps(idx, indent=2), encoding='utf-8')

    if not files:
        # return (file_count, wrote_graphs)
        return 0, False

    sizes = build_sizes_map(files, ROOT)
    ids, labels, parents, values = build_plotly_lists(sizes, root_label=mushroom)

    if go is None:
        # cannot write graphs
        return len(files), False

    # Hierarchical hue assignment with recolor recursion (adapted from Wikigraphs.py)
    def hsv_to_hex(h: float, s: float, v: float) -> str:
        hh = h % 1.0
        r, g, b = colorsys.hsv_to_rgb(hh, s, v)
        return '#{0:02x}{1:02x}{2:02x}'.format(int(r * 255), int(g * 255), int(b * 255))

    def load_recolor_md(p: Path) -> List[Tuple[str, str]]:
        if not p.exists():
            return []
        out: List[Tuple[str, str]] = []
        try:
            txt = p.read_text(encoding='utf-8', errors='replace')
        except Exception:
            return []
        for ln in txt.splitlines():
            m = re.match(r'^\s*([^=]+)=\s*(#[0-9a-fA-F]{6})\s*$', ln)
            if m:
                key = m.group(1).strip()
                val = m.group(2).lower()
                out.append((key, val))
        return out

    # Build parent -> children map
    parent_children: Dict[str, List[str]] = {}
    for node_id, parent_id in zip(ids, parents):
        parent_children.setdefault(parent_id if parent_id is not None else '', []).append(node_id)

    desc_cache: Dict[str, int] = {}
    def descendant_leaves(node_id: str) -> int:
        if node_id in desc_cache:
            return desc_cache[node_id]
        children = parent_children.get(node_id, [])
        if not children:
            desc_cache[node_id] = 1
            return 1
        total = 0
        for c in children:
            total += descendant_leaves(c)
        desc_cache[node_id] = max(1, total)
        return desc_cache[node_id]

    def deterministic_child_center(parent_id: str, child_id: str, idx: int, center: float, spread: float) -> float:
        key = f"{parent_id}||{child_id}||{idx}"
        digest = hashlib.md5(key.encode('utf-8')).hexdigest()
        u1 = int(digest[0:8], 16)
        u2 = int(digest[8:16], 16)
        U1 = (u1 + 1) / (2**32 + 2)
        U2 = (u2 + 1) / (2**32 + 2)
        import math
        z = math.sqrt(-2.0 * math.log(U1)) * math.cos(2.0 * math.pi * U2)
        sigma = (spread / 6.0) if spread > 0 else 0.0
        raw = center + z * sigma
        def norm(x: float) -> float:
            return x % 1.0
        val = norm(raw)
        delta = ((val - center + 0.5) % 1.0) - 0.5
        maxd = spread / 2.0
        if delta > maxd:
            delta = maxd
        if delta < -maxd:
            delta = -maxd
        return norm(center + delta)

    colors_by_id: Dict[str, str] = {}
    protected_ids: set = set()

    def recolor_subtree(node_id: str, center: float, spread: float, sat_override: float | None = None, val_override: float | None = None, level: int = 0, hex_override: str | None = None, protect: bool = False) -> None:
        try:
            if hex_override and re.match(r'^#[0-9a-fA-F]{6}$', hex_override):
                colors_by_id[node_id] = hex_override.lower()
            else:
                hue = center % 1.0
                if sat_override is not None and val_override is not None:
                    sat = sat_override
                    val = val_override
                else:
                    if node_id.endswith('/'):
                        sat, val = 0.30, 0.98
                    else:
                        sat, val = 0.35, 0.98
                    colors_by_id[node_id] = hsv_to_hex(hue, sat, val)
            if protect:
                protected_ids.add(node_id)
        except Exception:
            colors_by_id.setdefault(node_id, '#dddddd')

        children = parent_children.get(node_id, [])
        if not children:
            return

        weights = [max(1, descendant_leaves(c)) for c in children]
        total_weight = sum(weights) or len(children)
        left = (center - spread / 2.0) % 1.0
        acc = 0.0
        for idx, child in enumerate(children):
            w = weights[idx]
            frac = w / total_weight
            child_span = spread * frac
            try:
                child_center = deterministic_child_center(node_id, child, idx, center, spread)
            except Exception:
                child_center_rel = acc + child_span / 2.0
                child_center = (left + child_center_rel) % 1.0
            acc += child_span
            next_spread = min(1.0, spread * 1.0)
            recolor_subtree(child, child_center, next_spread, sat_override=None, val_override=None, level=level + 1, hex_override=hex_override, protect=protect)

    def assign_hues(node_id: str, center: float, spread: float, level: int = 0) -> None:
        children = parent_children.get(node_id, [])
        try:
            mid_hue_node = center % 1.0
            if node_id.endswith('/'):
                sat = 0.30
                val = 0.98
            else:
                sat = 0.35
                val = 0.98
            if node_id not in protected_ids:
                colors_by_id[node_id] = hsv_to_hex(mid_hue_node, sat, val)
        except Exception:
            colors_by_id.setdefault(node_id, '#dddddd')
        if not children:
            hue = center % 1.0
            colors_by_id[node_id] = hsv_to_hex(hue, 0.55, 0.95)
            return
        weights = [max(1, descendant_leaves(c)) for c in children]
        total_weight = sum(weights) or len(children)
        left = (center - spread / 2.0) % 1.0
        acc = 0.0
        for idx, child in enumerate(children):
            w = weights[idx]
            frac = w / total_weight
            child_span = spread * frac
            try:
                child_center = deterministic_child_center(node_id, child, idx, center, spread)
            except Exception:
                child_center_rel = acc + child_span / 2.0
                child_center = (left + child_center_rel) % 1.0
            acc += child_span
            mid_hue = child_center
            colors_by_id[child] = hsv_to_hex(mid_hue, 0.55, 0.95)
            next_spread = min(1.0, spread * 1.0)
            assign_hues(child, child_center, next_spread, level + 1)

    # Start hue assignment from '/' root using mushroom name for deterministic seed
    try:
        root_digest = hashlib.md5(str(mushroom).encode('utf-8')).hexdigest()
        root_center = int(root_digest[:8], 16) / float(2**32)
    except Exception:
        root_center = 0.5
    assign_hues('/', root_center, 0.35, level=0)

    # Load mushroom colour directives and apply recolor_subtree (protect overrides)
    recolor_name = 'mushroom_colours.md'
    fallback_recolor = 'color_recolors.md'
    script_recolor = Path(__file__).resolve().parent.joinpath(recolor_name)
    root_recolor = ROOT.joinpath(recolor_name)
    script_fallback = Path(__file__).resolve().parent.joinpath(fallback_recolor)
    root_fallback = ROOT.joinpath(fallback_recolor)
    if script_recolor.exists():
        mushroom_colours = load_recolor_md(script_recolor)
    elif root_recolor.exists():
        mushroom_colours = load_recolor_md(root_recolor)
    elif script_fallback.exists():
        mushroom_colours = load_recolor_md(script_fallback)
    elif root_fallback.exists():
        mushroom_colours = load_recolor_md(root_fallback)
    else:
        mushroom_colours = []

    # Apply directives: prefer exact id match; if not found, match by suffix; if key endswith '/' treat as dir
    for key, hexcol in mushroom_colours:
        candidates = []
        if key.endswith('/'):
            for node in ids:
                if node.startswith(key):
                    candidates.append(node)
        else:
            for node in ids:
                if node == key:
                    candidates = [node]
                    break
            if not candidates:
                for node in ids:
                    if node.endswith('/' + key) or node.endswith(key):
                        candidates.append(node)
        # apply recolor_subtree to best candidates (protect them)
        for c in sorted(candidates, key=lambda s: -len(s)):
            recolor_subtree(c, root_center, 0.35, sat_override=None, val_override=None, level=0, hex_override=hexcol, protect=True)

    colors_list = [colors_by_id.get(n, '#dddddd') for n in ids]

    fig_sun = go.Figure(go.Sunburst(ids=ids, labels=labels, parents=parents, values=values, marker=dict(colors=colors_list), maxdepth=-1))
    fig_treemap = go.Figure(go.Treemap(ids=ids, labels=labels, parents=parents, values=values, marker=dict(colors=colors_list)))

    sun_path = out_dir / f"{mushroom}_sunburst.html"
    tree_path = out_dir / f"{mushroom}_treemap.html"
    fig_sun.update_layout(margin=dict(t=30, l=10, r=10, b=10))
    fig_treemap.update_layout(margin=dict(t=30, l=10, r=10, b=10))
    fig_sun.write_html(str(sun_path), include_plotlyjs='cdn')
    fig_treemap.write_html(str(tree_path), include_plotlyjs='cdn')
    return len(files), True


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description='Grow mushrooms: collect files linking to a mushroom and generate graphs.')
    ap.add_argument('name', nargs='?', help='Optional mushroom name to grow (e.g. Anju). If omitted, all mushrooms from config are processed.')
    ap.add_argument('--all', action='store_true', help='Process all mushrooms from config (default when no name supplied).')
    ap.add_argument('--outdir', '-o', default=None, help='Base output directory for mushroom folders (default: Mycelium/Mushrooms)')
    args = ap.parse_args(argv)

    # determine output base
    out_base = Path(args.outdir).resolve() if args.outdir else OUT_BASE

    if args.name:
        mushrooms = [args.name]
    else:
        # default to processing all mushrooms from config
        mushrooms = parse_mycelium_config(MYCELIUM_CONFIG)

    if not mushrooms:
        print(f'No mushrooms to process (check {MYCELIUM_CONFIG}).')
        return 0

    # concise summary header
    print('Processing mushrooms:', ', '.join(mushrooms))
    for m in mushrooms:
        out_dir = out_base / m
        exclude_dirs = {out_dir.resolve()}
        linked = bfs_collect_linked_files(ROOT, m, exclude_dirs)
        linked = {p for p in linked if not any(str(p).startswith(str(ed)) for ed in exclude_dirs)}
        count, wrote = write_graphs_for_mushroom(m, linked, out_dir)
        status = 'graphs' if wrote else 'index'
        print(f'{m}: {count} files -> {out_dir.relative_to(ROOT)} ({status})')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
