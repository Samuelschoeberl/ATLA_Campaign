#!/usr/bin/env python3
"""grow_mushroom.py

Scan the workspace for mushrooms declared in `Mycelium/Mycelium.md` (lines like `_/Name/`).
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
from typing import Dict, List, Set, Tuple, Optional
import re
import json
import sys
import colorsys
import hashlib

try:
    import plotly.graph_objects as go
except Exception:  # pragma: no cover - helpful message if plotly missing
    go = None


ROOT = Path('.').resolve()
MYCELIUM_CONFIG = ROOT / 'Mycelium' / 'Mycelium.md'
OUT_BASE = ROOT / 'Mycelium' / 'Mushrooms'
MD_EXTS = {'.md', '.markdown'}
VERBOSE: bool = False


def vprint(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)


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


def find_root_md() -> Optional[Path]:
    """Return the Path to a Root.md file if present in known locations."""
    # Prefer any Root.md that is outside the Mycelium folder. This ensures the
    # canonical root for growing mushrooms lives at repo-root (or other non-Mycelium
    # locations) rather than inside the working Mycelium vault.
    # quick-check: common internal locations under Mycelium where Root.md may live
    try:
        myc = ROOT.joinpath('Mycelium')
        for sub in ('data/variable', 'data/variables', 'data/variable/Root.md'):
            cand = myc.joinpath(sub).joinpath('Root.md') if not sub.endswith('Root.md') else myc.joinpath(sub)
            try:
                if cand.exists():
                    txt = cand.read_text(encoding='utf-8', errors='ignore')
                    if '#variable' in txt or '#file:Root.md' in txt or '#Mycelium' in txt or '#Root' in txt:
                        import sys as _sys
                        _sys.stderr.write(f"WARNING: Using Root.md inside Mycelium (quick-check): {cand}\n")
                        return cand.resolve()
            except Exception:
                continue
    except Exception:
        pass
    try:
        import subprocess
        candidates = []
        for p in ROOT.rglob('Root.md'):
            try:
                # skip any Root.md that lives under a Mycelium/ path
                if 'Mycelium' in [part for part in p.parts]:
                    continue
                candidates.append(p)
            except Exception:
                continue
        # prefer candidates that git would NOT ignore (use git check-ignore)
        non_ignored = []
        ignored = []
        for p in candidates:
            try:
                res = subprocess.run(['git', 'check-ignore', '--quiet', str(p)], cwd=str(ROOT))
                # returncode == 0 means ignored, non-zero means NOT ignored
                if res.returncode != 0:
                    non_ignored.append(p)
                else:
                    ignored.append(p)
            except Exception:
                # if git isn't available treat this candidate as usable
                non_ignored.append(p)
        if non_ignored:
            return non_ignored[0].resolve()
        if ignored:
            # All candidates are git-ignored: this is a policy violation for Root
            import sys as _sys
            _sys.stderr.write(f"ERROR: Found Root.md files, but they are all ignored by git. Example: {ignored[0]}\n")
            raise RuntimeError(f"All candidate Root.md files are git-ignored; first ignored example: {ignored[0]}")
    except Exception:
        pass
        # fallback: check top-level Root.md specifically
        c = ROOT.joinpath('Root.md')
        try:
            if c.exists():
                return c.resolve()
        except Exception:
            pass

        # final fallback: if no external Root.md exists, allow a Root.md inside
        # the Mycelium folder only if it carries an explicit marker (e.g. '#variable').
        # This supports setups where Root.md is intentionally placed inside the
        # Mycelium manuals but declared as a variable. Emit a warning when used.
        try:
            myc_root = ROOT.joinpath('Mycelium')
            if myc_root.exists():
                # explicit common locations: data/variable or data/variables
                for sub in ('data/variable', 'data/variables'):
                    cand = myc_root.joinpath(sub).joinpath('Root.md')
                    try:
                        if cand.exists():
                            txt = cand.read_text(encoding='utf-8')
                            if '#variable' in txt or '#file:Root.md' in txt or '#Mycelium' in txt or '#Root' in txt:
                                import sys as _sys
                                _sys.stderr.write(f"WARNING: Using Root.md inside Mycelium: {cand} (this file is inside an ignored folder)\n")
                                return cand.resolve()
                    except Exception:
                        pass
                # general fallback: any Root.md under Mycelium that looks like a variable
                for p in myc_root.rglob('Root.md'):
                    try:
                        txt = p.read_text(encoding='utf-8')
                        if '#variable' in txt or '#file:Root.md' in txt or '#Mycelium' in txt or '#Root' in txt:
                            import sys as _sys
                            _sys.stderr.write(f"WARNING: Using Root.md inside Mycelium: {p} (this file is inside an ignored folder)\n")
                            return p.resolve()
                    except Exception:
                        continue
        except Exception:
            pass
    return None


def is_path_git_ignored(p: Path) -> bool:
    """Return True if git would ignore the given path.

    Falls back to False if git is unavailable or an error occurs.
    """
    try:
        import subprocess
        # git check-ignore returns 0 when ignored, 1 when not ignored
        res = subprocess.run(['git', 'check-ignore', '--quiet', str(p)], cwd=str(ROOT))
        return res.returncode == 0
    except Exception:
        return False


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


def write_graphs_for_mushroom(mushroom: str, files: Set[Path], out_dir: Path, depth: int = 1, include_backlinks: bool = False, root_md: Optional[Path] = None) -> Tuple[int, bool]:
    # Prefer canonical long-term graphs folder if available via mycel_brain.get_canonical_path
    try:
        # import on demand to avoid hard dependency cycles
        from Mycelium.mycel_brain import get_canonical_path
        can = get_canonical_path('data:graphs', root=Path('.'))
        if can:
            # create a per-mushroom clusters folder under canonical graphs dir
            out_dir = Path(can).joinpath(f"{mushroom}_clusters")
    except Exception:
        # ignore and use provided out_dir
        pass
    # Decide where to write the persistent subnetwork.json: prefer canonical
    # data:history if available (managed by Mycelium/mycel_brain), otherwise
    # write beside the visual outputs in out_dir.
    try:
        from Mycelium.mycel_brain import get_canonical_path
        hist_can = get_canonical_path('data:history', root=Path('.'))
        if hist_can:
            hist_dir = Path(hist_can).joinpath(f'{mushroom}_clusters')
            hist_dir.mkdir(parents=True, exist_ok=True)
            idx_file = hist_dir.joinpath('subnetwork.json')
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            idx_file = out_dir.joinpath('subnetwork.json')
    except Exception:
        out_dir.mkdir(parents=True, exist_ok=True)
        idx_file = out_dir.joinpath('subnetwork.json')

    idx = [str(p.relative_to(ROOT)) for p in sorted(files)]
    idx_file.write_text(json.dumps(idx, indent=2), encoding='utf-8')
    # Also write a markdown-friendly version so the project's .md parser can
    # consume the same index. We keep the JSON file for helper compatibility
    # but provide `subnetwork.md` with a fenced JSON block.
    try:
        md_idx = out_dir.joinpath('subnetwork.md')
        md_idx.write_text('\n'.join(['```json', json.dumps(idx, indent=2), '```']), encoding='utf-8')
    except Exception:
        pass

    # Always produce HTML visualisations when we write a subnetwork JSON.
    # Use the repo-local `Mycelium/graph_from_json.py` helper if available.
    try:
        import subprocess
        # Prefer a helper in the repo's Mycelium scripts folder, then other sensible locations.
        script_dir = Path(__file__).resolve().parent
        candidates = [
            ROOT.joinpath('Mycelium', 'scripts', 'Python', 'graph_from_json.py'),
            ROOT.joinpath('Mycelium', 'graph_from_json.py'),
            script_dir.joinpath('graph_from_json.py'),
            script_dir.joinpath('Mycelium', 'graph_from_json.py'),
        ]
        gf = None
        for c in candidates:
            if c.exists():
                gf = c
                break
        if gf:
            # call graph_from_json.py <idx_file> --out-dir <out_dir>
            cmd = [sys.executable, str(gf), str(idx_file), '--out-dir', str(out_dir)]
            try:
                subprocess.run(cmd, check=False)
            except Exception:
                # ignore failures here; the JSON is still a useful artifact
                pass
    except Exception:
        # best-effort only; don't prevent the rest of the function
        pass

    if not files:
        # return (file_count, wrote_graphs)
        return 0, False

    # Expand the subnetwork to include files that are cross-referenced by the collected files.
    # This helps the sunburst show the flattened tree of directly referenced nodes.
    def resolve_wikilink_to_path(target: str, base_dir: Path, root: Path) -> Optional[Path]:
        # try local directory first
        cand = base_dir.joinpath(f"{target}.md")
        if cand.exists():
            return cand.resolve()
        # try root-relative
        cand = root.joinpath(f"{target}.md")
        if cand.exists():
            return cand.resolve()
        # fallback: search by stem across the repo (first match)
        try:
            from Mycelium.fsutil import iter_md_files
        except Exception:
            try:
                from scripts.fsutil import iter_md_files
            except Exception:
                def iter_md_files(r: Path):
                    try:
                        for p in r.rglob("*"):
                            try:
                                if p.is_file() and p.suffix.lower() in MD_EXTS:
                                    s = str(p)
                                    if '/.git/' in s or '/backups/' in s or '/graphs/' in s:
                                        continue
                                    yield p.resolve()
                            except Exception:
                                continue
                    except Exception:
                        return
        for p in iter_md_files(root):
            if p.stem == target:
                return p.resolve()
        return None

    def collect_linked_targets(seed_files: Set[Path], root: Path, depth: int = 1) -> Set[Path]:
        all_files = set(seed_files)
        frontier = set(seed_files)
        for _ in range(depth):
            next_frontier: Set[Path] = set()
            for f in frontier:
                try:
                    txt = f.read_text(encoding='utf-8', errors='replace')
                except Exception:
                    continue
                for m in re.finditer(r"\[\[\s*([^\]|]+)(?:\|[^\]]+)?\]\]", txt):
                    target = m.group(1).strip()
                    if not target:
                        continue
                    resolved = resolve_wikilink_to_path(target, f.parent, ROOT)
                    if resolved and resolved not in all_files:
                        all_files.add(resolved)
                        next_frontier.add(resolved)
            frontier = next_frontier
        return all_files

    files = collect_linked_targets(files, ROOT, depth=depth)

    # Ensure we only operate on markdown files for graph generation. This
    # prevents generated artifacts (pdf/html/json) from being pulled into the
    # graph and ensures the visual outputs represent only .md content.
    try:
        files = {p for p in files if p.suffix.lower() in MD_EXTS}
    except Exception:
        files = {p for p in files}

    # Optionally include backlinks: files that refer to any of the current files
    if include_backlinks:
        stems = {p.stem for p in files}
        backlinks: Set[Path] = set()
        try:
            from Mycelium.fsutil import iter_md_files
        except Exception:
            try:
                from scripts.fsutil import iter_md_files
            except Exception:
                def iter_md_files(r: Path):
                    try:
                        for p in r.rglob("*"):
                            try:
                                if p.is_file() and p.suffix.lower() in MD_EXTS:
                                    s = str(p)
                                    if '/.git/' in s or '/backups/' in s or '/graphs/' in s:
                                        continue
                                    yield p.resolve()
                            except Exception:
                                continue
                    except Exception:
                        return
        for p in iter_md_files(ROOT):
            if p in files:
                continue
            try:
                txt = p.read_text(encoding='utf-8', errors='replace')
            except Exception:
                continue
            for m in re.finditer(r"\[\[\s*([^\]|]+)(?:\|[^\]]+)?\]\]", txt):
                target = m.group(1).strip()
                if target in stems:
                    # resolve probable path
                    rp = resolve_wikilink_to_path(target, p.parent, ROOT)
                    if rp:
                        backlinks.add(rp)
                    break
        # merge backlinks into files
        files = files.union(backlinks)

    # Ensure mushrooms include the full original tree for any referenced top-level folders.
    # For example, if any collected file is under 'Mycelium/...', include all markdown files
    # under ROOT/'Mycelium' so the mushroom contains the entire subtree.
    try:
        top_dirs = set()
        for p in list(files):
            try:
                rel = p.relative_to(ROOT)
            except Exception:
                continue
            if rel.parts:
                top_dirs.add(rel.parts[0])
        extra: Set[Path] = set()
        for td in top_dirs:
            td_path = ROOT.joinpath(td)
            # skip top-level dirs that git would ignore (e.g. Mycelium/)
            try:
                if is_path_git_ignored(td_path):
                    vprint(f"Skipping git-ignored top-level dir: {td_path}")
                    continue
            except Exception:
                pass
            if not td_path.exists():
                continue
            # include all files under this top-level subtree except those git-ignored
            for q in td_path.rglob('*'):
                try:
                    # skip git-ignored paths
                    if is_path_git_ignored(q):
                        continue
                    # only include markdown files when expanding top-level
                    # directories into the mushroom; skip binaries/other
                    # generated artifacts so graphs stay focused on .md nodes.
                    if q.is_file() and q.suffix.lower() in MD_EXTS:
                        extra.add(q.resolve())
                except Exception:
                    continue
        if extra:
            files = files.union(extra)
    except Exception:
        # non-fatal; continue with whatever files collected
        pass

    sizes = build_sizes_map(files, ROOT)
    ids, labels, parents, values = build_plotly_lists(sizes, root_label=mushroom)

    # Write an ASCII file-tree for the mushroom into the out_dir for quick review
    try:
        def build_tree(paths: List[str]):
            tree = {}
            for p in sorted(paths):
                # ensure string path
                if isinstance(p, Path):
                    s = str(p)
                else:
                    s = str(p)
                # normalize and split
                parts = s.split('/')
                node = tree
                for i, part in enumerate(parts):
                    if part == '':
                        continue
                    if i == len(parts) - 1:
                        node.setdefault(part, None)
                    else:
                        node = node.setdefault(part, {})
            return tree

        def ascii_from_tree(node, prefix=''):
            lines = []
            items = sorted(node.items(), key=lambda kv: (kv[1] is None, kv[0]))
            for idx, (name, child) in enumerate(items):
                is_last = idx == (len(items) - 1)
                connector = '└─ ' if is_last else '├─ '
                lines.append(prefix + connector + name)
                if child is not None:
                    extension = '   ' if is_last else '│  '
                    lines.extend(ascii_from_tree(child, prefix + extension))
            return lines

        # --- Build inter-file link graph and compute pagerank ---
        def extract_tags(p: Path) -> List[str]:
            try:
                txt = p.read_text(encoding='utf-8', errors='replace')
            except Exception:
                return []
            # prefer explicit 'tags:' YAML-like line
            m = re.search(r'^\s*tags:\s*(.+)$', txt, flags=re.MULTILINE)
            if m:
                vals = m.group(1)
                tags = re.findall(r'#?([A-Za-z0-9_-]+)', vals)
                return [t.lower() for t in tags if t]
            # fallback: collect inline hashtags
            tags = re.findall(r'#([A-Za-z0-9_-]+)', txt)
            return [t.lower() for t in tags]

        # build edges among collected files
        edges: Dict[Path, Set[Path]] = {p: set() for p in files}
        for src in list(files):
            try:
                txt = src.read_text(encoding='utf-8', errors='replace')
            except Exception:
                continue
            for m in re.finditer(r"\[\[\s*([^\]|]+)(?:\|[^\]]+)?\]\]", txt):
                target = m.group(1).strip()
                if not target:
                    continue
                rp = resolve_wikilink_to_path(target, src.parent, ROOT)
                if rp and rp in files:
                    edges[src].add(rp)

        def pagerank(nodes: List[Path], edges_map: Dict[Path, Set[Path]], damping=0.85, iters=50):
            idx = {n: i for i, n in enumerate(nodes)}
            N = len(nodes)
            if N == 0:
                return {}
            M = [[0.0]*N for _ in range(N)]
            for u in nodes:
                us = edges_map.get(u, set())
                if us:
                    w = 1.0 / len(us)
                    for v in us:
                        if v in idx:
                            M[idx[v]][idx[u]] = w
            pr = [1.0 / N] * N
            for _ in range(iters):
                new = [(1.0 - damping) / N] * N
                for i in range(N):
                    s = 0.0
                    for j in range(N):
                        s += M[i][j] * pr[j]
                    new[i] += damping * s
                pr = new
            return {nodes[i]: pr[i] for i in range(N)}

        nodes = list(sorted(files, key=lambda p: str(p)))
        pr_scores = pagerank(nodes, edges)

        # extract primary tag per file
        tag_map: Dict[str, List[Tuple[Path, float]]] = {}
        for p in nodes:
            tags = extract_tags(p)
            primary = tags[0] if tags else 'untagged'
            tag_map.setdefault(primary, []).append((p, pr_scores.get(p, 0.0)))

        # sort groups by pagerank desc
        for k in tag_map:
            tag_map[k].sort(key=lambda kv: -kv[1])

        # write smart_folders metadata and pagerank listing (and attempt to
        # load any pre-existing smart_folders.json for ordering below)
        smart_json: Dict[str, List[str]] = {}
        try:
            sf_dir = out_dir.joinpath('smart_folders')
            sf_dir.mkdir(parents=True, exist_ok=True)
            smart_json = {k: [str(p.relative_to(ROOT)) for p, _ in vals] for k, vals in tag_map.items()}
            # write the computed mapping (this will overwrite only if we
            # generated it in this run). If a user-maintained smart_folders.json
            # already exists we will load it later and prefer its ordering.
            (sf_dir / 'smart_folders.json').write_text(json.dumps(smart_json, indent=2), encoding='utf-8')
            # write markdown counterparts
            try:
                (sf_dir / 'smart_folders.md').write_text('\n'.join(['```json', json.dumps(smart_json, indent=2), '```']), encoding='utf-8')
            except Exception:
                pass
            pagerank_json = {str(p.relative_to(ROOT)): float(pr_scores.get(p, 0.0)) for p in nodes}
            (sf_dir / 'pagerank.json').write_text(json.dumps(pagerank_json, indent=2), encoding='utf-8')
            try:
                (sf_dir / 'pagerank.md').write_text('\n'.join(['```json', json.dumps(pagerank_json, indent=2), '```']), encoding='utf-8')
            except Exception:
                pass
        except Exception:
            pass

        # determine Root.md used and include it in the tree output
        try:
            if root_md:
                try:
                    abs_rm = str(root_md.resolve())
                except Exception:
                    abs_rm = str(root_md)
                rm_line = f'Root.md used: {abs_rm}'
            else:
                rm = find_root_md()
                if rm:
                    try:
                        abs_rm = str(rm.resolve())
                    except Exception:
                        abs_rm = str(rm)
                    rm_line = f'Root.md used: {abs_rm}'
                else:
                    rm_line = 'Root.md used: not found'
        except Exception:
            rm_line = 'Root.md used: unknown (error resolving)'

        # build an annotated ascii listing grouped by tag
        # Prefer ordering from an existing smart_folders.json if present. This
        # allows curated ordering to be reflected in the ASCII tree output.
        ascii_lines = [f'Mushroom: {mushroom}', rm_line, '']
        # attempt to load a user-provided smart_folders.json (prefer existing file)
        try:
            sf_candidate = out_dir.joinpath('smart_folders', 'smart_folders.json')
            if sf_candidate.exists():
                try:
                    loaded_sf = json.loads(sf_candidate.read_text(encoding='utf-8'))
                except Exception:
                    loaded_sf = {}
            else:
                loaded_sf = {}
        except Exception:
            loaded_sf = {}

        for tag in sorted(tag_map.keys()):
            group = tag_map[tag]
            # build a map from path->score for current group
            group_paths = [str(p.relative_to(ROOT)) for p, _ in group]
            group_set = {str(p.relative_to(ROOT)) for p, _ in group}

            ordered: List[Tuple[Path, float]] = []
            # if the loaded smart_folders provides an order for this tag, use it
            if isinstance(loaded_sf, dict) and tag in loaded_sf:
                for rel in loaded_sf.get(tag, []):
                    try:
                        if rel in group_set:
                            # find tuple in group with this relative path
                            for p, sc in group:
                                try:
                                    if str(p.relative_to(ROOT)) == rel:
                                        ordered.append((p, sc))
                                        break
                                except Exception:
                                    continue
                    except Exception:
                        continue
                # append any remaining items that weren't in the smart list
                for p, sc in group:
                    try:
                        rp = str(p.relative_to(ROOT))
                    except Exception:
                        rp = str(p)
                    if rp not in {str(x.relative_to(ROOT)) for x, _ in ordered}:
                        ordered.append((p, sc))
            else:
                # default: use pagerank-sorted order already present
                ordered = group

            ascii_lines.append(f'Tag: {tag} ({len(ordered)} files)')
            for p, score in ordered:
                try:
                    rp = str(p.relative_to(ROOT))
                except Exception:
                    rp = str(p)
                ascii_lines.append(f'  - {rp}  (pagerank={score:.4f})')
            ascii_lines.append('')
        tree_file = out_dir.joinpath('mushroom_tree.md')
        tree_file.write_text('\n'.join(['```', '\n'.join(ascii_lines), '```']), encoding='utf-8')
    except Exception:
        # non-fatal
        pass

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
            # accept #rrggbb or #rrggbbaa (drop alpha if present)
            m = re.match(r'^\s*([^=]+)=\s*(#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?)\s*$', ln)
            if m:
                key = m.group(1).strip()
                val = m.group(2).lower()
                # if 8 hex digits (with alpha), strip the alpha component
                if len(val) == 9:  # '#rrggbbaa'
                    val = val[:7]
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

    # Re-order each parent's children so the "strongest" nodes (those with the
    # most descendant leaf files / most linked files) come first. This makes
    # the graph/tree prefer the shortest path that goes through the most-linked
    # nodes and places strongest nodes nearest the root when visualised.
    # Compute descendant counts for all nodes (populates desc_cache), then
    # sort each child list by descending descendant count, with a stable
    # tiebreaker on the node id.
    for nid in list(parent_children.keys()):
        # ensure computation for each child and the node itself
        for ch in parent_children.get(nid, []):
            try:
                descendant_leaves(ch)
            except Exception:
                # ignore any pathological recursion errors; leave defaults
                desc_cache.setdefault(ch, 1)
    # also ensure root is computed
    try:
        descendant_leaves('/')
    except Exception:
        desc_cache.setdefault('/', 1)

    for pid, children in list(parent_children.items()):
        children.sort(key=lambda c: (-desc_cache.get(c, 0), c))

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

    # Apply directives: prefer exact id match; if not found, match by suffix;
    # if key endswith '/' treat as dir and match any '/<key>' path segment.
    for key, hexcol in mushroom_colours:
        candidates = []
        k = key.strip()
        if k.endswith('/'):
            # match nodes that start with the key OR contain '/<key>' as a path segment
            seg = '/' + k
            for node in ids:
                try:
                    if node.startswith(k) or seg in ('/' + node):
                        candidates.append(node)
                except Exception:
                    continue
        else:
            for node in ids:
                if node == k:
                    candidates = [node]
                    break
            if not candidates:
                for node in ids:
                    if node.endswith('/' + k) or node.endswith(k):
                        candidates.append(node)
        # apply recolor_subtree to best candidates (protect them)
        for c in sorted(candidates, key=lambda s: -len(s)):
            recolor_subtree(c, root_center, 0.35, sat_override=None, val_override=None, level=0, hex_override=hexcol, protect=True)

    # --- Load node-specific colour overrides from node_colours.md (#variable file) ---
    # This file maps node names (or directory-like keys ending with '/') to hex codes.
    # Candidate locations: repository root, Mycelium data/variable, script dir.
    def load_node_colours_from_candidates() -> List[Tuple[str, str]]:
        # First: look for a filepath-variable inside Mycelium/variable which
        # may contain a pointer to the real node_colours.md file. These files
        # are typically marked with '#variable' and '#filepath' and often use
        # a filename like '... .filepath.md'. We'll try to locate and parse
        # any candidate that mentions 'node_colours' and extract the path.
        var_dir = ROOT.joinpath('Mycelium', 'variable')
        try:
            if var_dir.exists():
                for p in sorted(var_dir.iterdir()):
                    try:
                        if not p.is_file():
                            continue
                        txt = p.read_text(encoding='utf-8', errors='ignore')
                        if ('#variable' in txt or '#filepath' in txt) and ('node_colours' in p.name or 'node_colours' in txt):
                            # attempt to extract a path containing 'node_colours.md'
                            m = re.search(r'([\./\w\- _~]+node_colours\.md)', txt)
                            if m:
                                candidate_path = m.group(1).strip()
                                # strip surrounding backticks or quotes
                                candidate_path = candidate_path.strip('`"\'')
                                cp = Path(candidate_path)
                                if not cp.is_absolute():
                                    # resolve relative to repo root and variable dir
                                    cp1 = ROOT.joinpath(candidate_path)
                                    if cp1.exists():
                                        out = load_recolor_md(cp1)
                                        if out:
                                            return out
                                    cp2 = var_dir.joinpath(candidate_path)
                                    if cp2.exists():
                                        out = load_recolor_md(cp2)
                                        if out:
                                            return out
                                else:
                                    if cp.exists():
                                        out = load_recolor_md(cp)
                                        if out:
                                            return out
                    except Exception:
                        continue
        except Exception:
            pass

        # Fallback: check a set of sensible default locations for node_colours.md
        candidates = [
            ROOT.joinpath('Mycelium', 'data', 'variable', 'node_colours.md'),
            ROOT.joinpath('Mycelium', 'data', 'variables', 'node_colours.md'),
            ROOT.joinpath('node_colours.md'),
            Path(__file__).resolve().parent.joinpath('node_colours.md'),
        ]
        out: List[Tuple[str, str]] = []
        for c in candidates:
            try:
                if c.exists():
                    out = load_recolor_md(c)
                    if out:
                        return out
            except Exception:
                continue
        return out

    node_colours = []
    try:
        node_colours = load_node_colours_from_candidates()
    except Exception:
        node_colours = []

    # Apply node colour overrides directly (no protect) so explicit node colours
    # from the variable file take precedence over generated hues.
    for key, hexcol in node_colours:
        candidates = []
        k = key.strip()
        if k.endswith('/'):
            seg = '/' + k
            for node in ids:
                try:
                    if node.startswith(k) or seg in ('/' + node):
                        candidates.append(node)
                except Exception:
                    continue
        else:
            for node in ids:
                if node == k:
                    candidates = [node]
                    break
            if not candidates:
                for node in ids:
                    if node.endswith('/' + k) or node.endswith(k):
                        candidates.append(node)
        for c in sorted(candidates, key=lambda s: -len(s)):
            try:
                if re.match(r'^#[0-9a-fA-F]{6}$', hexcol):
                    colors_by_id[c] = hexcol.lower()
            except Exception:
                colors_by_id.setdefault(c, '#dddddd')

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
    ap.add_argument('--pc', help='Use a PC name: locate the Character Sheet.md and build the subnetwork starting from that file')
    ap.add_argument('--all', action='store_true', help='Process all mushrooms from config (default when no name supplied).')
    ap.add_argument('--outdir', '-o', default=None, help='Base output directory for mushroom folders (default: Mycelium/Mushrooms)')
    ap.add_argument('--depth', type=int, default=1, help='Depth of cross-reference expansion (default: 1)')
    ap.add_argument('--backlinks', action='store_true', help='Include backlinks (files that reference the collected set)')
    ap.add_argument('-v', '--verbose', action='store_true', help='Verbose logging')
    args = ap.parse_args(argv)

    # determine output base
    out_base = Path(args.outdir).resolve() if args.outdir else OUT_BASE

    global VERBOSE
    if args.verbose:
        VERBOSE = True

    pc_mode = False
    if args.pc:
        mushrooms = [args.pc]
        pc_mode = True
    elif args.name:
        mushrooms = [args.name]
    else:
        # prefer explicit Root.md as the default seed
        root_md = find_root_md()
        if root_md:
            try:
                # Use the first non-empty line of Root.md as the canonical mushroom name
                try:
                    txt = root_md.read_text(encoding='utf-8')
                    title = None
                    for ln in txt.splitlines():
                        ln2 = ln.strip()
                        if ln2:
                            title = ln2
                            break
                    if title:
                        mushrooms = [title]
                    else:
                        mushrooms = [root_md.stem]
                except Exception:
                    mushrooms = [root_md.stem]

                # print selected root path when verbose
                try:
                    if VERBOSE:
                        print(f'Using Root.md at: {str(root_md)} (mushroom name: {mushrooms[0]})')
                except Exception:
                    pass
            except Exception:
                mushrooms = parse_mycelium_config(MYCELIUM_CONFIG)
        else:
            mushrooms = parse_mycelium_config(MYCELIUM_CONFIG)

    if not mushrooms:
        # If the config file doesn't exist, try to auto-create a mushroom
        # folder using the repository Root.md (first non-empty line as name).
        # This supports workflows where `Mycelium/Mycelium.md` is missing but
        # a Root.md declares the intended mushroom/folder.
        if not MYCELIUM_CONFIG.exists():
            try:
                rm = find_root_md()
                if rm:
                    try:
                        txt = rm.read_text(encoding='utf-8')
                        title = None
                        for ln in txt.splitlines():
                            ln2 = ln.strip()
                            if ln2:
                                title = ln2
                                break
                        folder_name = title or rm.stem
                    except Exception:
                        folder_name = rm.stem

                    myc_folder = ROOT.joinpath('Mycelium', folder_name)
                    try:
                        myc_folder.mkdir(parents=True, exist_ok=True)
                        # copy Root.md into the new mushroom folder for clarity
                        try:
                            dst = myc_folder.joinpath('Root.md')
                            dst.write_text(rm.read_text(encoding='utf-8'), encoding='utf-8')
                        except Exception:
                            pass
                        vprint(f"Auto-created mushroom folder at: {myc_folder}")
                        mushrooms = [folder_name]
                    except Exception:
                        # fall through to original message if we can't create
                        pass
            except Exception:
                # best-effort only; ignore failures trying to inspect/create
                pass
        if not mushrooms:
            print(f'No mushrooms to process (check {MYCELIUM_CONFIG}).')
            return 0

    # resolve Root.md once here and pass it down to writers so they can
    # unambiguously report which Root.md was used. We do this before
    # the mushrooms loop so we can place outputs relative to the path
    # written inside Root.md (first non-empty line) when available.
    resolved_root_md: Optional[Path] = None
    if not args.name and not args.pc:
        resolved_root_md = find_root_md()

    # concise summary header
    vprint('Processing mushrooms:', ', '.join(mushrooms))
    for m in mushrooms:

        # Use an underscore separator for cluster output directories and
        # place cluster graphs near the Root.md folder when possible.
        # remember the explicit target_path (when Root.md was used) so we
        # can decide whether to exclude the target folder from the scan.
        target_path: Optional[Path] = None
        if args.outdir:
            out_dir = Path(args.outdir).resolve().joinpath(f"{m}_clusters")
        else:
            # If we have a Root.md, place a sibling folder next to the folder
            # that contains Root.md. For example, if Root.md is at
            # Mycelium/data/variable/Root.md, create Mycelium/data/variable_mushroom
            # so it sits next to the 'variable' folder.
            if resolved_root_md:
                try:
                    # Interpret the first non-empty line of Root.md as a repo-relative
                    # path (per your convention). Use that path's parent and create a
                    # sibling folder named '<basename>_mushroom'.
                    try:
                        txt = resolved_root_md.read_text(encoding='utf-8')
                        title = None
                        for ln in txt.splitlines():
                            ln2 = ln.strip()
                            if ln2:
                                title = ln2
                                break
                        target_path_str = title or resolved_root_md.stem
                    except Exception:
                        target_path_str = resolved_root_md.stem

                    target_path = ROOT.joinpath(target_path_str)
                    folder_basename = Path(target_path_str).name
                    # If the path exists and is a directory, write into it directly.
                    if target_path.exists() and target_path.is_dir():
                        out_dir = target_path
                    else:
                        parent_dir = target_path.parent if target_path.parent and str(target_path.parent) != '.' else ROOT
                        out_dir = parent_dir.joinpath(f"{folder_basename}_mushroom")
                except Exception:
                    # fallback to script-local clusters
                    out_dir = Path(__file__).resolve().parent.joinpath(f"{m}_clusters")
            else:
                if str(m).strip().lower() != 'root':
                    out_dir = Path(__file__).resolve().parent.joinpath(f"{m}_clusters")
                else:
                    out_dir = out_base / m
        # Normally we exclude the output folder from the scan to avoid
        # picking up files the script itself writes. However, if the
        # chosen out_dir is the same as the folder that the Root.md
        # points to (i.e. we're writing inside the target folder), we
        # must NOT exclude it — otherwise all tagged files inside the
        # target folder would be skipped (this caused the 0-file result).
        if target_path is not None and out_dir.resolve() == target_path.resolve():
            exclude_dirs = set()
        else:
            exclude_dirs = {out_dir.resolve()}

        # Simplified behaviour: collect all markdown files under the repo
        # (excluding the out_dir) that contain a tag matching the folder name.
        def slugify(name: str) -> str:
            s = name.strip().lower()
            s = re.sub(r'\s+', '_', s)
            s = re.sub(r'[^a-z0-9_-]', '', s)
            return s

        def file_has_tag(p: Path, tags: List[str]) -> bool:
            try:
                txt = p.read_text(encoding='utf-8', errors='replace')
            except Exception:
                return False
            # check YAML-like tags: line starting with 'tags:'
            m = re.search(r'^\s*tags:\s*(.+)$', txt, flags=re.MULTILINE)
            if m:
                vals = m.group(1)
                for t in tags:
                    if re.search(r'\b' + re.escape(t) + r'\b', vals, flags=re.IGNORECASE):
                        return True
            # check inline hashtags
            for t in tags:
                if re.search(r'#' + re.escape(t) + r'\b', txt, flags=re.IGNORECASE):
                    return True
            return False

        raw_tag = m
        slug_tag = slugify(m)
        candidates = {raw_tag, slug_tag}

        matched: List[Path] = []
        try:
            for p in ROOT.rglob('*'):
                try:
                    if not p.is_file():
                        continue
                    if p.suffix.lower() not in MD_EXTS:
                        continue
                    # skip files under the out_dir
                    if any(str(p).startswith(str(ed)) for ed in exclude_dirs):
                        continue
                    if file_has_tag(p, list(candidates)):
                        matched.append(p.resolve())
                except Exception:
                    continue
        except Exception:
            matched = []

        # build an ascii file-tree and write to out_dir/mushroom_tree.md
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            rels = [str(p.relative_to(ROOT)) for p in sorted(matched)]

            def build_tree(paths: List[str]):
                tree = {}
                for s in sorted(paths):
                    parts = s.split('/')
                    node = tree
                    for i, part in enumerate(parts):
                        if part == '':
                            continue
                        if i == len(parts) - 1:
                            node.setdefault(part, None)
                        else:
                            node = node.setdefault(part, {})
                return tree

            def ascii_from_tree(node, prefix=''):
                lines = []
                items = sorted(node.items(), key=lambda kv: (kv[1] is None, kv[0]))
                for idx, (name, child) in enumerate(items):
                    is_last = idx == (len(items) - 1)
                    connector = '└─ ' if is_last else '├─ '
                    lines.append(prefix + connector + name)
                    if child is not None:
                        extension = '   ' if is_last else '│  '
                        lines.extend(ascii_from_tree(child, prefix + extension))
                return lines

            tree = build_tree(rels)
            ascii_lines = [f'Mushroom: {m}', 'Files:']
            ascii_lines.extend(ascii_from_tree(tree, ''))
            tree_file = out_dir.joinpath('mushroom_tree.md')
            tree_file.write_text('\n'.join(['```', '\n'.join(ascii_lines), '```']), encoding='utf-8')
            # Also generate JSON and HTML graphs for the matched files so the
            # visual outputs include the same files listed in the tree. This
            # calls the more featureful writer which will expand cross-links
            # if needed (depth/backlinks) and write Plotly HTML files.
            try:
                files_set = set(matched)
                graph_count, wrote_graphs = write_graphs_for_mushroom(m, files_set, out_dir, depth=args.depth, include_backlinks=args.backlinks, root_md=resolved_root_md)
            except Exception:
                graph_count, wrote_graphs = 0, False
        except Exception:
            pass

        print(f"{m}: {len(matched)} files -> {out_dir.relative_to(ROOT)} (tree)")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
