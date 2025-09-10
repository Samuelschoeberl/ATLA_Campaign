#!/usr/bin/env python3
"""
Wikigraphs.py

Scan a workspace (Obsidian vault) and create Plotly Sunburst and Treemap
HTML files that visualize the file/directory structure and file sizes.

Usage:
    python3 Wikigraphs.py --root /path/to/vault --out graphs

Outputs (into out directory):
    - wikigraph_sunburst.html
    - wikigraph_treemap.html

Dependencies: plotly
"""
from __future__ import annotations
import argparse
import os
import plotly
from pathlib import Path
import colorsys
import hashlib
import re
import fnmatch
from typing import Dict, List, Tuple


DEFAULT_EXCLUDES = {".git", "node_modules", ".obsidian", "__pycache__", "venv", ".venv"}
DEFAULT_EXTS = {".md", ".markdown", ".txt"}


def unobsidify(text: str) -> str:
    """Return a plain-text version of an Obsidian markdown string.

    - Replaces wiki-links [[...]] and transclusions ![[...]] with readable text.
    - Removes YAML frontmatter, heading markers, emphasis and code markers.
    - Converts markdown tables into compact text (keeps header + first two rows).
    - Collapses code fences to a short inline representation.
    """
    if not text:
        return text

    s = text
    # remove YAML frontmatter
    s = re.sub(r'^---\n.*?\n---\n', '', s, flags=re.S)
    # remove Obsidian comments %% ... %%
    s = re.sub(r'%%.*?%%', '', s, flags=re.S)

    # replace transclusions and wikilinks: prefer alias when present
    s = re.sub(r'!\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', s)
    s = re.sub(r'!\[\[([^\]]+)\]\]', r'\1', s)
    s = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', s)
    s = re.sub(r'\[\[([^\]]+)\]\]', r'\1', s)

    # collapse code fences (keep first non-empty line)
    def _collapse_code(m: re.Match) -> str:
        body = m.group(2) or ''
        for ln in body.splitlines():
            ln = ln.strip()
            if ln:
                return f'`{ln}`'
        return '`code`'

    s = re.sub(r'(```|~~~)(.*?)\1', _collapse_code, s, flags=re.S)

    # markdown links [text](url) -> text
    s = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', s)
    # remove heading markers and emphasis/code markers
    s = re.sub(r'(?m)^[ \t]*#{1,6}\s*', '', s)
    s = re.sub(r'[\*_`~]+', '', s)

    # convert simple markdown tables into compact text summary
    def _summarize_table(block: str) -> str:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            return ''

        # header is first line, skip separator if present
        header = lines[0]
        if len(lines) > 1 and re.match(r'^\s*\|?\s*[:\-]+', lines[1]):
            data = lines[2:]
        else:
            data = lines[1:]

        def split_row(r: str) -> List[str]:
            # split on pipes, strip leading/trailing empty cells caused by edge pipes
            cells = [c.strip() for c in re.split(r'\s*\|\s*', r.strip().strip('|'))]
            return cells

        hdr_cells = split_row(header)
        # remove any columns named 'Auto' (case-insensitive)
        keep_indices = [i for i, h in enumerate(hdr_cells) if h and h.strip().lower() != 'auto']
        if keep_indices:
            # filter hdr_cells and all shown rows to only kept indices
            hdr_cells = [hdr_cells[i] for i in keep_indices]

            def filter_row_by_indices(row: List[str]) -> List[str]:
                return [row[i] if i < len(row) else '' for i in keep_indices]
        else:
            # nothing to keep? fall back to original header (avoid empty table)
            def filter_row_by_indices(row: List[str]) -> List[str]:
                return row

        # show all data rows for complete table output
        shown = [split_row(r) for r in data]

        # compute column count as max across header and all shown rows
        col_count = max(len(hdr_cells), max((len(r) for r in shown), default=0))

        # normalize row lengths by padding empty cells
        def normalize_row(row: List[str]) -> List[str]:
            if len(row) < col_count:
                return row + [''] * (col_count - len(row))
            return row[:col_count]

        hdr = normalize_row(hdr_cells)
        shown_norm = [normalize_row(filter_row_by_indices(r)) for r in shown]

        # compute max width per column (no huge extra padding; keep compact)
        EXTRA_PAD = 2
        widths = [0] * col_count
        for ci in range(col_count):
            w = len(hdr[ci])
            for r in shown_norm:
                w = max(w, len(r[ci]))
            widths[ci] = w + EXTRA_PAD

        # helpers to build boxed ASCII table using monospace-friendly chars
        def _border_line() -> str:
            parts = []
            for w in widths:
                parts.append('-' * (w + 2))
            return '+' + '+'.join(parts) + '+'

        def format_row_box(row: List[str]) -> str:
            parts = []
            for i, cell in enumerate(row):
                # provide a single space padding on each side
                parts.append(' ' + cell.ljust(widths[i]) + ' ')
            return '|' + '|'.join(parts) + '|'

        out_lines: List[str] = []
        out_lines.append('TABLE:')
        out_lines.append(_border_line())
        out_lines.append(format_row_box(hdr))
        out_lines.append(_border_line())
        for row in shown_norm:
            out_lines.append(format_row_box(row))
        out_lines.append(_border_line())
        return '\n'.join(out_lines)

    # replace contiguous table blocks (lines beginning with |) conservatively
    s = re.sub(r'(?m)(^\s*\|.*(?:\n^\s*\|.*)+)', lambda m: _summarize_table(m.group(0)), s)

    # normalize whitespace
    s = re.sub(r'\r\n|\r', '\n', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    s = s.strip()
    return s


def _html_escape(s: str) -> str:
    # minimal HTML escaping for hover content
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def hsv_to_hex(h: float, s: float, v: float) -> str:
    """Convert HSV (h in [0,1), s,v in [0,1]) to a hex color string like '#rrggbb'."""
    # normalize hue into [0,1)
    hh = h % 1.0
    r, g, b = colorsys.hsv_to_rgb(hh, s, v)
    return '#{0:02x}{1:02x}{2:02x}'.format(int(r * 255), int(g * 255), int(b * 255))


# Hardcoded recolors you want preserved across runs. Each entry is a tuple
# (node_id_or_suffix, hex_color). Node ids are the same ids used by the
# visualization (directories end with '/'); suffix matching is supported.
# Example:
# HARDCODED_RECOLORS = [("Players Part/Rules/Bending Rules/Fire/", "#ff0000")]
HARDCODED_RECOLORS: List[Tuple[str, str]] = []

# Set of node ids that are protected from being overwritten by the normal
# hue-assignment logic. When a recolor is applied with protect=True the
# node and its descendants are added here.
protected_ids: set = set()


def gather_file_tree(root: Path, exts=DEFAULT_EXTS, excludes=DEFAULT_EXCLUDES, include_gitignored: bool = False) -> Tuple[Dict[str, int], Dict[str, str], Dict[str, str]]:
    """Return a mapping of path parts joined by '/' to aggregated size in bytes.

    Keys include directories and files. Directory keys end with '/'.
    """
    root = root.resolve()
    sizes: Dict[str, int] = {}
    # Map from file key (relative path) to sanitized file content (for .md files)
    contents: Dict[str, str] = {}
    # Raw file text (un-sanitized) kept to detect special markers like '![['
    raw_contents: Dict[str, str] = {}

    # Load .gitignore patterns from the vault root (if present) to mirror repo ignores
    gitignore_path = root.joinpath('.gitignore')
    git_patterns: List[str] = []
    if gitignore_path.exists():
        try:
            raw = gitignore_path.read_text(encoding='utf-8', errors='replace')
            for ln in raw.splitlines():
                ln = ln.strip()
                if not ln or ln.startswith('#'):
                    continue
                git_patterns.append(ln)
        except Exception:
            git_patterns = []

    def matches_gitignore(rel_str: str, parts: List[str]) -> bool:
        # Basic support for the simple patterns used in the project's .gitignore
        for pat in git_patterns:
            p = pat.strip()
            if not p:
                continue
            # directory pattern like 'DMs Part/' or 'dir/'
            if p.endswith('/'):
                name = p.rstrip('/')
                # match if any path part equals the directory name or rel path starts with it
                if any(part == name for part in parts):
                    return True
                if rel_str.startswith(name + os.sep):
                    return True
            elif '/' in p:
                # pattern contains a path component; match against the relative path
                if fnmatch.fnmatch(rel_str, p):
                    return True
            else:
                # filename/glob pattern (e.g. *.bak, *.zip, .DS_Store)
                if fnmatch.fnmatch(parts[-1], p):
                    return True
        return False

    for p in root.rglob("*"):
        # Build relative path and parts for matching
        try:
            rel = p.relative_to(root)
            rel_str = str(rel)
            parts = list(rel.parts)
        except Exception:
            rel_str = str(p)
            parts = list(p.parts)

        # Skip excluded directories by simple name matching
        if any(part in excludes for part in parts):
            continue
        # Explicitly ignore common auto-generated collection/expanded files and folders
        low_parts = [p.lower() for p in parts]
        # Skip files or dirs that contain 'collectionfile' (singular) or 'collectionfiles' (plural)
        if any('collectionfile' in lp or 'collectionfiles' in lp for lp in low_parts):
            continue
        # Skip ExpandedCollections and simple/expanded megafiles
        if any('expandedcollections' in lp or 'simple_expanded_megafile' in lp or 'expanded' == lp for lp in low_parts):
            continue
        # Skip files/dirs matched by .gitignore patterns (when present), unless
        # the caller explicitly requested to include gitignored files.
        if git_patterns and not include_gitignored and matches_gitignore(rel_str, parts):
            continue
        if p.is_file() and (not exts or p.suffix.lower() in exts):
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            # relative parts
            rel = p.relative_to(root)
            parts = list(rel.parts)
            # Add file node
            file_key = "/".join(parts)
            sizes[file_key] = size or 1
            # Read markdown content for hover text when available
            try:
                if p.suffix.lower() == '.md':
                    # Read text, sanitize markdown/obsidian syntax, and keep it reasonably sized
                    txt = p.read_text(encoding='utf-8', errors='replace')

                    def sanitize_markdown(s: str) -> str:
                        # Remove YAML frontmatter
                        s = re.sub(r'^---\n.*?\n---\n', '', s, flags=re.S)
                        # Handle Obsidian embeds first: ![[target|display]] -> display, ![[target]] -> target
                        s = re.sub(r'!\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', s)
                        s = re.sub(r'!\[\[([^\]]+)\]\]', r'\1', s)
                        # Obsidian wikilinks with display [[target|display]] -> display
                        s = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', s)
                        # Wikilinks [[target]] -> target
                        s = re.sub(r'\[\[([^\]]+)\]\]', r'\1', s)
                        # Markdown links [text](url) -> text
                        s = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', s)
                        # Remove heading markers at line starts (e.g. #, ##)
                        s = re.sub(r'(?m)^[ \t]*#{1,6}\s*', '', s)
                        # Strip emphasis and code markers *, _, `, ~
                        s = re.sub(r'[\*_`~]+', '', s)
                        # Collapse multiple blank lines
                        s = re.sub(r'\n{3,}', '\n\n', s)
                        # Trim whitespace
                        return s.strip()

                    clean = sanitize_markdown(txt)
                    # Store full sanitized content; trimming will be done at display time
                    contents[file_key] = clean
                    raw_contents[file_key] = txt
            except Exception:
                # ignore read errors
                pass
            # Add directory aggregated sizes
            for i in range(1, len(parts)):
                dir_key = "/".join(parts[:i]) + "/"
                sizes[dir_key] = sizes.get(dir_key, 0) + (size or 1)
            # Also add root directory bucket
            sizes["/"] = sizes.get("/", 0) + (size or 1)

    return sizes, contents, raw_contents


def build_plotly_lists(sizes: Dict[str, int], root_label: str = "root") -> Tuple[List[str], List[str], List[str], List[int]]:
    """Convert sizes mapping into Plotly ids, labels, parents, values lists.

    Returns:
      ids: unique ids for nodes (use canonical keys)
      labels: human-friendly display names
      parents: parent ids (empty string for root)
      values: numeric values
    """
    ids: List[str] = []
    labels: List[str] = []
    parents: List[str] = []
    values: List[int] = []

    # Build a simple parent/child map so we can detect directories that
    # only contain a single child directory (and no direct file children).
    # We'll hide those intermediate directories to make the graph
    # cleaner: attach their descendants to the nearest visible ancestor.
    def parent_of(k: str) -> str:
        if k == "/":
            return ""
        stripped = k.rstrip('/')
        parts = stripped.split('/')
        if len(parts) == 1:
            return "/"
        return "/".join(parts[:-1]) + "/"

    children_map: Dict[str, List[str]] = {}
    for k in sizes.keys():
        if k == "/":
            continue
        p = parent_of(k)
        children_map.setdefault(p, []).append(k)

    # A directory is "visible" when it either:
    # - is root, or
    # - has more than one immediate child, or
    # - has at least one immediate file child (not just a single directory child)
    visible_dirs: set = set()
    for k in sizes.keys():
        if not k.endswith('/'):
            continue
        if k == "/":
            visible_dirs.add(k)
            continue
        childs = children_map.get(k, [])
        if len(childs) > 1:
            visible_dirs.add(k)
            continue
        # if any child is a file, keep this dir visible
        if any(not c.endswith('/') for c in childs):
            visible_dirs.add(k)
            continue

    # Additionally, avoid adding multiple directory nodes that share the
    # exact same basename (label). This removes duplicate folder names from
    # the sunburst: when we've already encountered a directory with the
    # same label, mark later ones as invisible so they're skipped below.
    seen_dir_labels: set = set()
    # iterate in deterministic order (shallow to deep) so the first
    # occurrence is preserved and later ones are removed
    dir_keys = sorted([k for k in sizes.keys() if k.endswith('/')], key=lambda x: (x.count('/'), x))
    for k in dir_keys:
        if k == '/':
            continue
        label = k.rstrip('/').split('/')[-1]
        if label in seen_dir_labels:
            # ensure it's not treated as visible (skip it later)
            if k in visible_dirs:
                visible_dirs.remove(k)
        else:
            seen_dir_labels.add(label)

    # Sort to get deterministic output (shorter keys first)
    items = sorted(sizes.items(), key=lambda kv: (kv[0].count('/'), kv[0]))

    for key, val in items:
        # skip directory nodes that are invisible (they only contain a
        # single directory child and no files) to collapse chains
        if key.endswith('/') and key != '/' and key not in visible_dirs:
            continue

        node_id = key
        # label is basename (for directories show directory name)
        if key == "/":
            label = root_label
            parent = ""
        else:
            # strip trailing slash for name
            stripped = key.rstrip('/')
            parts = stripped.split('/')
            label = parts[-1]
            # compute immediate parent, then climb to the nearest visible ancestor
            p = parent_of(key)
            # climb while p is not root and p is an invisible directory
            while p and p != '/' and p not in visible_dirs:
                p = parent_of(p)
            if p == '/':
                parent = "/"
            elif p == "":
                parent = ""
            else:
                parent = p

        ids.append(node_id)
        labels.append(label)
        parents.append(parent)
        values.append(int(val))

    return ids, labels, parents, values


def make_graphs(root: Path, outdir: Path, exts=DEFAULT_EXTS, excludes=DEFAULT_EXCLUDES, mode: str = 'size', embed_js: bool = False, child_spread: float = 0.35, spread_growth: float = 1.0, recolor_list: List[str] | None = None, allowed_elements_levels: dict | None = None, verbose: bool = False, pc_subtree: Path | None = None, pc_name: str | None = None, include_gitignored: bool = False) -> None:
    # mode: 'size' uses file byte sizes, 'count' counts each file as 1
    sizes, contents, raw_contents = gather_file_tree(root, exts=exts, excludes=excludes, include_gitignored=include_gitignored)

    # If allowed_elements_levels provided, filter the file list to only
    # include files under 'Rules/Bending Rules' that mention an allowed
    # element+level in a wikilink. This is a heuristic: we look for
    # wikilinks like [[Water 3]] or [[Water Level]] or a wikilink that
    # contains the element name and either the numeric level or the word 'level'.
    if allowed_elements_levels:
        allowed_files = set()
        # normalize element names to lowercase for matching
        elem_map = {k.lower(): v for k, v in allowed_elements_levels.items()}

        # If a pc_subtree was provided, avoid matching files that already
        # live inside the PC's previously-created 'Allowed Moves' subtree.
        # This prevents selecting symlinked/copied files under
        # Players Part/PCs/<name>/Allowed Moves/... from earlier runs which
        # would otherwise create nested duplicates.
        pc_allowed_prefix_lower = None
        if pc_subtree is not None:
            try:
                rel_pc = pc_subtree.relative_to(root)
                pc_allowed_prefix_lower = str(rel_pc).replace(os.sep, '/').strip('/').lower() + '/allowed moves/'
            except Exception:
                pc_allowed_prefix_lower = str(pc_subtree).replace(os.sep, '/').strip('/').lower() + '/allowed moves/'

        def file_matches_allowed(file_key: str) -> bool:
            # Skip files that are already inside the PC's Allowed Moves subtree
            # (prevents re-selecting the artifacts we create when mirroring).
            if pc_allowed_prefix_lower and file_key.lower().startswith(pc_allowed_prefix_lower):
                return False
            # Only consider files under Rules/Bending Rules (anywhere in the path)
            if 'rules/bending rules/' not in file_key.lower():
                return False
            txt = raw_contents.get(file_key, contents.get(file_key, ''))
            lower_key = file_key.lower()
            # Extract wikilink inner texts
            inner_links = [m.group(1).lower() for m in re.finditer(r"\[\[([^\]]+)\]\]", (txt or ''))]
            # Also allow matching element keywords anywhere in the file text
            text_lower = (txt or '').lower()

            # Find numeric level mentions in text (e.g. 'level 1' or 'Level 1')
            text_levels = set()
            for m in re.finditer(r'level\s*[:_\- ]*\(?([0-9]+)\)?', text_lower, flags=re.I):
                try:
                    text_levels.add(int(m.group(1)))
                except Exception:
                    continue

            # Find level numbers in the path (folder names like 'level 1')
            path_levels = set()
            for part in lower_key.split('/'):
                m = re.search(r'level\s*[-_ ]*(\d+)', part)
                if m:
                    try:
                        path_levels.add(int(m.group(1)))
                    except Exception:
                        pass

            for elem, lvl in elem_map.items():
                # element keywords: match 'water', 'waterbending' etc.
                elem_kw = elem
                # match by path (file is inside element subtree)
                in_path = elem_kw in lower_key
                # match by wikilink inner texts (preferred)
                in_text_link = any(elem_kw in s for s in inner_links)

                # Include mechanics pages only when the player actually has >0
                # level in the element and the element is referenced via a wikilink.
                if 'mechanic' in lower_key:
                    if in_text_link and lvl > 0:
                        return True

                # If the file lives in a Level N folder under the element, include when N <= allowed level
                if in_path and path_levels:
                    for pl in path_levels:
                        # strictly compare against the allowed level (level 0 allows nothing)
                        allowed_level_for_compare = lvl
                        if pl <= allowed_level_for_compare and pl > 0:
                            return True

                # If the file contains an element wikilink and a Level X mention where X <= allowed level
                if in_text_link and text_levels:
                    for tl in text_levels:
                        allowed_level_for_compare = lvl
                        if tl <= allowed_level_for_compare and tl > 0:
                            return True

                # NOTE: permissive fallbacks that matched plain text mentions (in_text_any)
                # or path-only element presence without level were intentionally removed
                # to require an explicit Level N together with a wikilink or a path-level
                # directory match. This tightens selection so only files that explicitly
                # indicate both element and level will be included.

            return False

        for k in list(sizes.keys()):
            if k.endswith('/'):
                continue
            if file_matches_allowed(k):
                allowed_files.add(k)

        # Rebuild sizes to include only allowed files and their ancestor dirs
        new_sizes: Dict[str, int] = {}
        for fk in allowed_files:
            sz = sizes.get(fk, 1)
            new_sizes[fk] = sz
            parts = fk.split('/')
            for i in range(1, len(parts)):
                dir_key = '/'.join(parts[:i]) + '/'
                new_sizes[dir_key] = new_sizes.get(dir_key, 0) + sz
            new_sizes['/'] = new_sizes.get('/', 0) + sz

        sizes = new_sizes
        # If verbose, print the exact list of selected files for debugging
        if verbose:
            print("Selected files for allowed elements/levels:")
            for p in sorted(allowed_files):
                print(f"  {p}")
        # If a pc_subtree path was provided, mirror the allowed files into
        # a dedicated subtree inside the PC folder so the generated sunburst
        # can be rooted at the character and show only allowed moves.
        if pc_subtree is not None and allowed_files:
            try:
                # Build an in-memory representation of the Allowed Moves subtree
                # without writing any files to disk. For each allowed file we
                # read its size and contents and create keys under
                # 'Rules/Bending Rules/...', so when merged into the PC tree
                # the character node will have a child 'Rules/Bending Rules'.
                sizes_allowed_scan: Dict[str, int] = {}
                contents_allowed: Dict[str, str] = {}
                raw_allowed: Dict[str, str] = {}
                marker = 'rules/bending rules/'
                for fk in sorted(allowed_files):
                    src = root.joinpath(fk)
                    if not src.exists() or not src.is_file():
                        continue
                    try:
                        sz = src.stat().st_size or 1
                    except Exception:
                        sz = 1
                    lower = fk.lower()
                    if marker in lower:
                        pos = lower.find(marker)
                        suffix = fk[pos + len(marker):].lstrip('/')
                        dest_rel = 'Rules/Bending Rules/' + suffix
                    else:
                        # Fallback: place file under Rules/Bending Rules using
                        # its basename so it's visible to the player under the
                        # rules node without reproducing the whole original path.
                        dest_rel = 'Rules/Bending Rules/' + Path(fk).name

                    # Normalize dest_rel to use forward slashes
                    dest_rel = dest_rel.replace(os.sep, '/')

                    # Add file entry
                    sizes_allowed_scan[dest_rel] = sz
                    try:
                        txt = src.read_text(encoding='utf-8', errors='replace')
                    except Exception:
                        txt = ''
                    contents_allowed[dest_rel] = re.sub(r'^---\n.*?\n---\n', '', txt, flags=re.S).strip()
                    raw_allowed[dest_rel] = txt

                    # Ensure directory aggregations exist (Rules/Bending Rules/.../)
                    parts = dest_rel.split('/')
                    for i in range(1, len(parts)):
                        dir_key = '/'.join(parts[:i]) + '/'
                        sizes_allowed_scan[dir_key] = sizes_allowed_scan.get(dir_key, 0) + sz

                # Ensure root bucket for the allowed scan
                sizes_allowed_scan['/'] = sizes_allowed_scan.get('/', sum(v for k, v in sizes_allowed_scan.items() if not k.endswith('/')) or 1)

                # Merge PC and allowed in-memory scans below (no filesystem ops)
                try:
                    # Scan the PC subtree on-disk (character folder) to build its
                    # in-memory index. We will merge the Allowed Moves entries
                    # under this PC root without writing any files.
                    sizes_pc, contents_pc, raw_pc = gather_file_tree(pc_subtree, exts=exts, excludes=excludes)

                    # Remove any previously-created Allowed Moves entries from
                    # the PC scan so we don't keep the 'Allowed Moves/...' keys.
                    sizes_pc_clean: Dict[str, int] = {k: v for k, v in sizes_pc.items() if not k.lower().startswith('allowed moves/')}
                    contents_pc_clean: Dict[str, str] = {k: v for k, v in contents_pc.items() if not k.lower().startswith('allowed moves/')}
                    raw_pc_clean: Dict[str, str] = {k: v for k, v in raw_pc.items() if not k.lower().startswith('allowed moves/')}

                    # Merge sizes: start with cleaned PC sizes and add allowed subtree entries
                    merged_sizes: Dict[str, int] = dict(sizes_pc_clean)
                    for ak, av in sizes_allowed_scan.items():
                        # skip the allowed_scan's own '/' entry
                        if ak == '/':
                            continue
                        merged_sizes[ak] = merged_sizes.get(ak, 0) + av
                    # Recompute root total as sum of file entries (non-directory keys)
                    merged_sizes['/'] = sum(v for k, v in merged_sizes.items() if not k.endswith('/')) or 1

                    # Merge contents and raw_contents; prefer PC content when keys collide
                    merged_contents: Dict[str, str] = dict(contents_pc_clean)
                    for ck, cv in contents_allowed.items():
                        if ck not in merged_contents:
                            merged_contents[ck] = cv
                    merged_raw: Dict[str, str] = dict(raw_pc_clean)
                    for rk, rv in raw_allowed.items():
                        if rk not in merged_raw:
                            merged_raw[rk] = rv

                    sizes, contents, raw_contents = merged_sizes, merged_contents, merged_raw
                except Exception:
                    # if scanning/merging fails, leave sizes as-is
                    pass

            except Exception:
                # non-fatal; don't fail the whole graph build if allowed-scan merge fails
                pass

    # Auto-create simple Expanded megafiles: for any source whose basename starts with 'Expanded',
    # write a file named 'simple_Expanded_Megafile.md' in the same directory containing the
    # sanitized content with embeds inlined (using the sanitized contents index).
    try:
        for file_key, sanitized in list(contents.items()):
            # basename without trailing slash
            base = Path(file_key).name
            if not base.lower().startswith('expanded'):
                continue

            # helper to find sanitized content for a target name
            def find_sanitized_for(target: str) -> str:
                # Try direct matches: exact key
                for k, v in contents.items():
                    if k.lower() == target.lower():
                        return v
                # Try with .md suffix
                if not target.lower().endswith('.md'):
                    for k, v in contents.items():
                        if k.lower().endswith(target.lower() + '.md'):
                            return v
                # Match by filename suffix
                for k, v in contents.items():
                    if k.lower().endswith('/' + target.lower()) or k.lower().endswith(target.lower()):
                        return v
                return ''

            raw = raw_contents.get(file_key, '')

            def embed_repl(m: re.Match) -> str:
                target = m.group(1).strip()
                if '|' in target:
                    target = target.split('|', 1)[0].strip()
                found = find_sanitized_for(target)
                if found:
                    return '\n' + found + '\n'
                return target

            resolved = re.sub(r'!\[\[([^\]]+)\]\]', embed_repl, raw)
            final_text = resolved.strip() or sanitized

            # write into the same directory as the source file
            src_path = root.joinpath(file_key)
            out_dir = src_path.parent if src_path.parent.exists() else root
            out_path = out_dir / 'simple_Expanded_Megafile.md'
            try:
                out_path.write_text(final_text + '\n', encoding='utf-8')
            except Exception:
                # ignore write errors
                pass
    except Exception:
        # non-fatal; continue
        pass
    # Ensure there's at least a root node
    if not sizes:
        sizes = {"/": 1}
    else:
        sizes.setdefault("/", sum(v for k, v in sizes.items() if not k.endswith('/')) or 1)

    # If count mode, convert file entries to 1 and re-aggregate directories
    if mode == 'count':
        new_sizes: Dict[str, int] = {}
        for k, v in sizes.items():
            # files (no trailing slash) => 1
            if k.endswith('/'):
                # keep directories for now
                new_sizes[k] = new_sizes.get(k, 0)
            else:
                new_sizes[k] = 1
                # add counts to parent directories
                parts = k.split('/')
                for i in range(1, len(parts)):
                    dir_key = '/'.join(parts[:i]) + '/'
                    new_sizes[dir_key] = new_sizes.get(dir_key, 0) + 1
                new_sizes['/'] = new_sizes.get('/', 0) + 1
        sizes = new_sizes

    root_label = pc_name if pc_name else root.name
    ids, labels, parents, values = build_plotly_lists(sizes, root_label=root_label)

    # Helper to remove backlink collection blocks from files that declare #collectionfile
    def remove_backlink_collection(s: str) -> str:
        if not s:
            return s
        if '#collectionfile' not in s.lower():
            return s
        # Remove headings that mention 'backlink' and the content under them until next heading
        s = re.sub(r'(?mi)^\s*#{1,6}.*backlink.*\n(?:^(?!\s*#{1,6}).*\n?)*', '', s)
        # Remove plain 'Backlinks' section (no heading) and following list-like lines
        s = re.sub(r'(?mi)^\s*backlinks\s*[:\-]?\s*\n(?:^(?!\s*#{1,6}).*\n?)*', '', s)
        # Remove standalone wikilink list items (common backlink lists)
        s = re.sub(r'(?m)^[ \t]*[-*]\s*\[\[.*?\]\].*\n?', '', s)
        s = re.sub(r'(?m)^[ \t]*\[\[.*?\]\].*\n?', '', s)
        return s.strip()

    # Helper to replace markdown tables with a compact summary representation
    def replace_tables(s: str) -> str:
        if not s:
            return s
        lines = s.splitlines()
        out_lines: List[str] = []
        i = 0
        while i < len(lines):
            ln = lines[i]
            # detect potential table: line contains '|' and next line is a separator like '|---|:---|'
            if '|' in ln and i + 1 < len(lines):
                sep = lines[i + 1]
                if re.match(r'^\s*\|?\s*[:\-]+\s*(\|\s*[:\-]+\s*)*\|?\s*$', sep):
                    # collect data rows after separator
                    header = ln
                    j = i + 2
                    data_rows: List[str] = []
                    while j < len(lines) and '|' in lines[j] and lines[j].strip() != '':
                        data_rows.append(lines[j])
                        j += 1
                    # extract header cells
                    header_cells = [c.strip() for c in re.split(r'\s*\|\s*', header.strip().strip('|')) if c.strip()]
                    # helper to sanitize inline markdown in headers/cells
                    def sanitize_inline(cell: str) -> str:
                        if not cell:
                            return ''
                        # wikilinks [[target|display]] or [[target]] -> display/target
                        cell = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', cell)
                        cell = re.sub(r'\[\[([^\]]+)\]\]', r'\1', cell)
                        # markdown links [text](url) -> text
                        cell = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cell)
                        # remove emphasis and code markers
                        cell = re.sub(r'[\*_`~]+', '', cell)
                        # collapse multiple spaces
                        cell = re.sub(r'\s+', ' ', cell)
                        return cell.strip()

                    if header_cells:
                        # produce a cleaned, full table representation preserving rows
                        clean_header = ' | '.join(sanitize_inline(h) for h in header_cells)
                        out_lines.append(clean_header)
                        # append each data row, cleaned
                        for row in data_rows:
                            row_text = row.strip().strip('|')
                            row_cells = [c.strip() for c in re.split(r'\s*\|\s*', row_text)]
                            clean_row = ' | '.join(sanitize_inline(c) for c in row_cells)
                            out_lines.append(clean_row)
                    else:
                        # no headers found; include raw data rows cleaned
                        for row in data_rows:
                            row_text = row.strip()
                            out_lines.append(sanitize_inline(row_text))
                    i = j
                    continue
            out_lines.append(ln)
            i += 1
        return '\n'.join(out_lines)

    # Build hovertext for each node. For file leaf nodes, prefer markdown content if available.
    hovertexts: List[str] = []
    for node_id in ids:
        if node_id.endswith('/'):
            hovertexts.append('')
        else:
            txt = contents.get(node_id, '')
            if txt:
                # Clean Obsidian-specific syntax for hover text
                cleaned = unobsidify(txt)
                # if multi-line (likely a summarized table), show in monospace <pre>
                if '\n' in cleaned:
                    # preserve multiple spaces using pre so padded columns remain aligned
                    h = '<span style="font-family:monospace;white-space:pre;">' + _html_escape(cleaned).replace('\n', '<br>') + '</span>'
                else:
                    h = _html_escape(cleaned)
                if len(h) > 2000:
                    h = h[:2000] + '...'
                hovertexts.append(h)
            else:
                hovertexts.append('')

    # Create a treemap-specific hovertext that only shows the first couple of rows
    treemap_hovertexts: List[str] = []
    for node_id in ids:
        if node_id.endswith('/'):
            treemap_hovertexts.append('')
            continue
        raw = contents.get(node_id, '')
        if not raw:
            treemap_hovertexts.append('')
            continue
        # Pre-process to remove Obsidian syntax and collapse tables
        pre = unobsidify(raw)
        # take first 2 non-empty lines
        lines = pre.splitlines()
        first_lines: List[str] = []
        for ln in lines:
            t = ln.strip()
            if not t:
                continue
            first_lines.append(t)
            if len(first_lines) >= 2:
                break
        if not first_lines and lines:
            first_lines = [lines[0].strip()]
        # format treemap hover: single-line or short multiline pre
        if len(first_lines) == 1:
            h = _html_escape(first_lines[0])
            if len(lines) > 1:
                h = h + '...'
        else:
            txt_block = '\n'.join(first_lines)
            if len(lines) > len(first_lines):
                txt_block += '\n...'
            h = '<span style="font-family:monospace;white-space:pre;">' + _html_escape(txt_block).replace('\n', '<br>') + '</span>'
        treemap_hovertexts.append(h)

    # Hierarchical gradient: split the hue range for each parent among its
    # immediate children, then recurse so leaves receive colors from their
    # final subrange. Deterministic and stable across runs.
    colors_by_id: Dict[str, str] = {}
    parent_children: Dict[str, List[str]] = {}
    for node_id, parent_id in zip(ids, parents):
        parent_children.setdefault(parent_id, []).append(node_id)

    # Count descendant leaf files for weighting
    desc_cache: Dict[str, int] = {}

    def descendant_leaves(node_id: str) -> int:
        if node_id in desc_cache:
            return desc_cache[node_id]
        children = parent_children.get(node_id, [])
        if not children:
            # leaf (file) counts as 1
            desc_cache[node_id] = 1
            return 1
        total = 0
        for c in children:
            total += descendant_leaves(c)
        # ensure every subtree has at least weight 1
        desc_cache[node_id] = max(1, total)
        return desc_cache[node_id]

    # Deterministic gaussian sampler for child centers. Moved out so it can be
    # reused by recolor_subtree.
    def deterministic_child_center(parent_id: str, child_id: str, idx: int, center: float, spread: float) -> float:
        key = f"{parent_id}||{child_id}||{idx}"
        digest = hashlib.md5(key.encode('utf-8')).hexdigest()
        # use two 8-hex chunks as uint32
        u1 = int(digest[0:8], 16)
        u2 = int(digest[8:16], 16)
        # map to (0,1]
        U1 = (u1 + 1) / (2**32 + 2)
        U2 = (u2 + 1) / (2**32 + 2)
        # Box-Muller -> standard normal
        import math
        z = math.sqrt(-2.0 * math.log(U1)) * math.cos(2.0 * math.pi * U2)
        # sigma chosen so ~99.7% of values fall within +/- spread/2
        sigma = (spread / 6.0) if spread > 0 else 0.0
        raw = center + z * sigma
        # normalize to [0,1)
        def norm(x: float) -> float:
            return x % 1.0
        val = norm(raw)
        # compute signed circular delta from parent center in [-0.5,0.5)
        delta = ((val - center + 0.5) % 1.0) - 0.5
        maxd = spread / 2.0
        if delta > maxd:
            delta = maxd
        if delta < -maxd:
            delta = -maxd
        return norm(center + delta)

    def recolor_subtree(node_id: str, center: float, spread: float, sat_override: float | None = None, val_override: float | None = None, level: int = 0, hex_override: str | None = None, protect: bool = False) -> None:
        """Recursively assign colors to node and its descendants.

        If hex_override is provided and valid it will be used for each node in
        the subtree. If protect is True the node ids will be added to
        `protected_ids` so `assign_hues` will not overwrite them.
        """
        # assign color for this node
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
                            # pastel directories: lower saturation, high value (lighter)
                            sat, val = 0.30, 0.98
                        else:
                            # pastel files: slightly higher saturation than dirs but still muted
                            sat, val = 0.35, 0.98
                colors_by_id[node_id] = hsv_to_hex(hue, sat, val)
            if protect:
                protected_ids.add(node_id)
        except Exception:
            colors_by_id.setdefault(node_id, '#dddddd')

        children = parent_children.get(node_id, [])
        if not children:
            return

        # compute weights proportional to descendant leaf counts
        weights = [max(1, descendant_leaves(c)) for c in children]
        total_weight = sum(weights) or len(children)
        left = (center - spread / 2.0) % 1.0
        acc = 0.0
        for idx, child in enumerate(children):
            w = weights[idx]
            frac = w / total_weight
            child_span = spread * frac
            # compute child center using deterministic gaussian around parent center
            try:
                child_center = deterministic_child_center(node_id, child, idx, center, spread)
            except Exception:
                child_center_rel = acc + child_span / 2.0
                child_center = (left + child_center_rel) % 1.0
            acc += child_span
            # recurse
            next_spread = min(1.0, spread * spread_growth)
            recolor_subtree(child, child_center, next_spread, sat_override=None, val_override=None, level=level + 1, hex_override=hex_override, protect=protect)

    def assign_hues(node_id: str, center: float, spread: float, level: int = 0) -> None:
        children = parent_children.get(node_id, [])
        # Ensure the current node (folder or file) has a color based on the center
        try:
            mid_hue_node = center % 1.0
            # Directories get a slightly lower saturation/value so they're visually
            # distinguishable from file leaves. Files keep the brighter values.
            if node_id.endswith('/'):
                # pastel directories
                sat = 0.30
                val = 0.98
            else:
                # pastel files
                sat = 0.35
                val = 0.98
            # Do not overwrite colors for protected ids
            if node_id not in protected_ids:
                colors_by_id[node_id] = hsv_to_hex(mid_hue_node, sat, val)
        except Exception:
            # fallback color
            colors_by_id.setdefault(node_id, '#dddddd')
    # Use the module-level deterministic_child_center (declared above)

        # Special-case: Avatar Spirit Bridge subtree should be white -> near-white
        # Only apply this when the node represents a directory to avoid matching
        # filenames that contain the phrase.
        if node_id.endswith('/') and 'avatar spirit bridge' in node_id.lower():
            # Recolor the Avatar Spirit Bridge subtree to a white->grey range.
            # Use low saturation and values from ~0.98 (white) down to ~0.82 (grey).
            n = len(children)
            for idx, child in enumerate(children):
                frac = idx / (n - 1) if n > 1 else 0.5
                value = 0.98 - frac * 0.16  # range ~0.98 -> ~0.82
                sat = 0.02
                # Recolor the full subtree under this child with the sat/value overrides
                recolor_subtree(child, center, spread, sat_override=sat, val_override=value, level=level + 1)
            return
        # Special-case: if we're at a 'Bending Rules' folder, give the four
        # primary element folders fixed hue subranges so they map to the
        # requested color palettes. Only apply to directories.
        if node_id.endswith('/') and 'bending rules' in node_id.lower():
            # element -> (start_hue, end_hue)
            element_ranges = {
                # air: light cyan / very light blue
                'air': (0.50, 0.58),
                # water: deeper blue
                'water': (0.66, 0.75),
                # fire: middle of dark to bright red 
                'fire': (0.98, 0.03),
                # earth: dark green (center ~0.30-0.33)
                'earth': (0.25, 0.35),
                # Avatar Spirit Bridge: pale white-grey-ish )
                'Avatar Spirit Bridge': (0.55, 0.62),
            }
            for child in children:
                name = Path(child).name.lower()
                matched = False
                for key, (a, b) in element_ranges.items():
                    if key in name:
                        # handle wrap for fire (a > b)
                        if a <= b:
                            sub_start, sub_end = a, b
                        else:
                            # when range wraps, map it into two parts by shifting
                            # values > a as >a..1 and 0..b; to keep it simple pick midpoint across wrap
                            mid = ((a + (b + 1.0)) / 2.0) % 1.0
                            sub_start = (mid - 0.02) % 1.0
                            sub_end = (mid + 0.02) % 1.0
                        # assign color and recurse
                        mid_hue = ((sub_start + sub_end) / 2.0) % 1.0
                        # compute span, handling wrap-around correctly
                        span = (sub_end - sub_start) % 1.0
                        # avoid zero span
                        if span == 0:
                            span = 0.04
                        # use a pastel variant for element subtrees
                        colors_by_id[child] = hsv_to_hex(mid_hue, 0.35, 0.98)
                        # recolor full subtree under this child using the
                        # mid_hue and span so all descendants get updated.
                        recolor_subtree(child, mid_hue, span)
                        matched = True
                        break
                if not matched:
                    # fallback: neutral light gray range
                    colors_by_id[child] = '#cccccc'
                    recolor_subtree(child, 0.5, 0.5)
            return
        if not children:
            # leaf node: pick center hue
            hue = center % 1.0
            colors_by_id[node_id] = hsv_to_hex(hue, 0.55, 0.95)
            return
        # compute weights proportional to descendant leaf counts
        weights = [max(1, descendant_leaves(c)) for c in children]
        total_weight = sum(weights) or len(children)
        # left edge of the spread (handle wrap by staying in [0,1) arithmetic)
        left = (center - spread / 2.0) % 1.0
        acc = 0.0
        for idx, child in enumerate(children):
            w = weights[idx]
            frac = w / total_weight
            child_span = spread * frac
            # compute child center using deterministic gaussian around parent center
            try:
                child_center = deterministic_child_center(node_id, child, idx, center, spread)
            except Exception:
                # fallback to proportional center
                child_center_rel = acc + child_span / 2.0
                child_center = (left + child_center_rel) % 1.0
            acc += child_span
            # assign mid color for the child
            mid_hue = child_center
            colors_by_id[child] = hsv_to_hex(mid_hue, 0.55, 0.95)
            # next level spread grows/shrinks by spread_growth
            next_spread = min(1.0, spread * spread_growth)
            assign_hues(child, child_center, next_spread, level + 1)

    # Start recursion from root '/'. Use configured child_spread and spread_growth
    # Choose a deterministic root hue based on the vault (root) name so the
    # overall palette isn't always the same light-blue.
    try:
        root_digest = hashlib.md5(str(root.name).encode('utf-8')).hexdigest()
        root_center = int(root_digest[:8], 16) / float(2**32)
    except Exception:
        root_center = 0.5
    assign_hues('/', root_center, child_spread, level=0)

    # Helper: load and save recolor directives to a markdown file inside the
    # vault root. The file is simple: lines matching 'path=#rrggbb' are used.
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

    def write_recolor_md(p: Path, entries: List[Tuple[str, str]]) -> None:
        try:
            lines = ['# Wikigraph recolor settings', '', '<!-- lines of the form: path=#rrggbb -->', '']
            for k, v in entries:
                lines.append(f"{k}={v}")
            p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        except Exception:
            pass

    # Apply any recolor directives passed via CLI --recolor entries. Expected
    # format: 'node_id=#rrggbb' where node_id should match the ids used in the
    # visualization (directories end with '/'). If a node_id matches multiple
    # candidates, the exact match is preferred. Apply recolor_subtree so the
    # override propagates to all descendants.
    # Prefer a recolor file located next to this script so recolors apply
    # even when the script is run from a subdirectory. Fall back to a
    # recolor file in the scanned root. If neither exists use the hardcoded list.
    script_recolor = Path(__file__).resolve().parent.joinpath('color_recolors.md')
    root_recolor = root.joinpath('color_recolors.md')
    if script_recolor.exists():
        recolor_md_path = script_recolor
        file_recolors = load_recolor_md(script_recolor)
    elif root_recolor.exists():
        recolor_md_path = root_recolor
        file_recolors = load_recolor_md(root_recolor)
    else:
        recolor_md_path = script_recolor
        file_recolors = HARDCODED_RECOLORS

    # First apply file-based (protected) recolors. Match and apply to all
    # candidate ids (exact, suffix, etc.) so every folder with that name is
    # recolored, not just the first occurrence.
    for node_part, hex_part in file_recolors:
        if not re.match(r'^#[0-9a-fA-F]{6}$', hex_part):
            continue
        npart = node_part.strip('/').lower()
        targets: List[str] = []
        # exact id match
        if node_part in ids:
            targets.append(node_part)
        # case-insensitive exact matches
        for cand in ids:
            if cand.lower() == node_part.lower() and cand not in targets:
                targets.append(cand)
        # suffix matches (e.g., 'Rules/Bending Rules/Fire/') -> match any path that endswith that
        for cand in ids:
            if cand.strip('/').lower().endswith(npart) and cand not in targets:
                targets.append(cand)
        # substring match when the recolor key starts with an underscore: '_/Bending Rules/' -> match any id containing that substring
        try:
            raw_key = node_part.strip()
            if raw_key.startswith('_'):
                sub = raw_key.lstrip('_').strip('/').lower()
                if sub:
                    for cand in ids:
                        if sub in cand.lower() and cand not in targets:
                            targets.append(cand)
        except Exception:
            pass
        # glob-style matching when '*' present in the recolor key (case-insensitive)
        if '*' in node_part:
            pat = node_part.strip('/').lower()
            for cand in ids:
                try:
                    if fnmatch.fnmatch(cand.strip('/').lower(), pat) and cand not in targets:
                        targets.append(cand)
                except Exception:
                    continue
        # apply to all found targets
        for target in targets:
            recolor_subtree(target, 0.5, 0.5, hex_override=hex_part.lower(), protect=True)

    # Then apply CLI recolors (these are not protected by default).
    # We support a bare --recolor (const='__STORED__') which means "apply
    # stored recolors only"; in that case we do not merge/write the recolor
    # file.
    cli_entries: List[str] = []
    stored_flag = False
    if recolor_list:
        for d in recolor_list:
            if d == '__STORED__':
                stored_flag = True
            elif d:
                cli_entries.append(d)

    # If there are CLI recolor entries, process them and persist the file.
    if cli_entries:
        for directive in cli_entries:
            if '=' not in directive:
                continue
            node_part, hex_part = directive.split('=', 1)
            node_part = node_part.strip()
            hex_part = hex_part.strip()
            if not re.match(r'^#[0-9a-fA-F]{6}$', hex_part):
                # skip invalid hex
                continue
            # find candidate id in ids: exact match preferred, fallback to case-insensitive match
            target = None
            if node_part in ids:
                target = node_part
            else:
                lowered = node_part.lower()
                for cand in ids:
                    if cand.lower() == lowered:
                        target = cand
                        break
            if not target:
                # allow matching by suffix of the node id (case-insensitive)
                npart = node_part.strip('/').lower()
                for cand in ids:
                    if cand.strip('/').lower().endswith(npart):
                        target = cand
                        break
            if not target:
                # allow matching by label (basename) if provided
                for cand in ids:
                    if Path(cand).name.lower() == node_part.lower().strip('/'):
                        target = cand
                        break
            if node_part:
                npart = node_part.strip('/').lower()
                targets: List[str] = []
                # exact id
                if node_part in ids:
                    targets.append(node_part)
                # case-insensitive exact
                lowered = node_part.lower()
                for cand in ids:
                    if cand.lower() == lowered and cand not in targets:
                        targets.append(cand)
                # suffix matches
                for cand in ids:
                    if cand.strip('/').lower().endswith(npart) and cand not in targets:
                        targets.append(cand)
                # basename match fallback
                for cand in ids:
                    if Path(cand).name.lower() == node_part.lower().strip('/') and cand not in targets:
                        targets.append(cand)
                # apply recolor to each target and merge into recolor file once
                if targets:
                    for target in targets:
                        recolor_subtree(target, 0.5, 0.5, hex_override=hex_part.lower(), protect=False)
                    # Merge into file_recolors (overwrite existing entry for same key)
                    k = node_part.strip('/')
                    replaced = False
                    for i, (kk, vv) in enumerate(file_recolors):
                        if kk.strip('/').lower() == k.lower():
                            file_recolors[i] = (node_part, hex_part.lower())
                            replaced = True
                            break
                    if not replaced:
                        file_recolors.append((node_part, hex_part.lower()))
        # After processing CLI recolors, persist updates to the recolor md file
        try:
            write_recolor_md(recolor_md_path, file_recolors)
        except Exception:
            pass
    else:
        # No CLI recolor entries; if user passed bare --recolor (stored_flag)
        # we simply applied file-based recolors above and we do not write the file.
        if stored_flag:
            pass

    # Ensure every id has a color; generate a deterministic fallback for any
    # node that wasn't assigned during the recursive hue allocation. This
    # guarantees the same coloring logic (deterministic, hue-based) applies
    # to all filetypes and to both the sunburst and treemap outputs.
    for n in ids:
        if n not in colors_by_id or colors_by_id.get(n) == '#dddddd':
            # Use md5 of the node id to get a stable pseudo-random hue in [0,1)
            digest = hashlib.md5(n.encode('utf-8')).hexdigest()
            h = int(digest[:8], 16) / float(2**32)
            # fallback pastel color for any unassigned node
            colors_by_id[n] = hsv_to_hex(h % 1.0, 0.35, 0.98)

    # Final ordered colors list aligned with ids
    colors: List[str] = [colors_by_id.get(n, '#dddddd') for n in ids]

    # Prepare short cell text for treemap nodes (sanitized and trimmed)
    cell_texts: List[str] = []
    for node_id in ids:
        txt = ''
        if not node_id.endswith('/'):
            sanitized = contents.get(node_id, '')
            raw = raw_contents.get(node_id, '')
            if sanitized:
                # If the raw file contains embed markers like ![[target]] we should
                # inline the referenced file's full sanitized content in place of the token.
                if raw and '![[' in raw:
                    # helper to find sanitized content for a target name
                    def find_sanitized_for(target: str) -> str:
                        # Try direct matches: exact key
                        for k, v in contents.items():
                            if k.lower() == target.lower():
                                return v
                        # Try with/without .md
                        if not target.lower().endswith('.md'):
                            for k, v in contents.items():
                                if k.lower().endswith(target.lower() + '.md'):
                                    return v
                        # Match by filename suffix
                        for k, v in contents.items():
                            if k.lower().endswith('/' + target.lower()) or k.lower().endswith(target.lower()):
                                return v
                        return ''

                    # replace embeds with the sanitized content of the referenced file
                    def embed_repl(m: re.Match) -> str:
                        target = m.group(1).strip()
                        # strip optional display part if provided (target|display)
                        if '|' in target:
                            target = target.split('|', 1)[0].strip()
                        found = find_sanitized_for(target)
                        if found:
                            return '\n' + found + '\n'
                        # fallback: show the target name
                        return target

                    resolved = re.sub(r'!\[\[([^\]]+)\]\]', embed_repl, raw)
                    # Prefer resolved content if it produced additional material
                    if resolved and resolved != raw:
                        resolved_clean = unobsidify(resolved)
                        if '\n' in resolved_clean:
                            t = '<span style="font-family:monospace;white-space:pre;">' + _html_escape(resolved_clean.strip()).replace('\n', '<br>') + '</span>'
                        else:
                            t = _html_escape(resolved_clean.strip())
                    else:
                        # Fallback to sanitized content for display
                        san_clean = unobsidify(sanitized)
                        if '\n' in san_clean:
                            t = '<span style="font-family:monospace;white-space:pre;">' + _html_escape(san_clean).replace('\n', '<br>') + '</span>'
                        else:
                            t = _html_escape(san_clean).replace('\n', '<br>')
                    txt = t
                else:
                    san_clean = unobsidify(sanitized)
                    # Wrap treemap text in a monospace span and preserve spaces/newlines
                    txt = '<span style="font-family:monospace;white-space:pre;">' + _html_escape(san_clean).replace('\n', '<br>') + '</span>'
        cell_texts.append(txt)

    # Lazy import plotly
    try:
        import plotly.graph_objects as go
    except Exception as e:
        raise RuntimeError("plotly is required; install with: pip install plotly") from e

    outdir.mkdir(parents=True, exist_ok=True)
    # Sanitize the root name for use in filenames (replace unsafe chars with '_')
    try:
        # Preserve spaces and readable characters but remove path separators and nulls.
        raw_name = str(pc_name).strip() if pc_name else str(root.name).strip()
        # Replace path separator characters (shouldn't normally appear in a single name)
        safe_root_name = raw_name.replace(os.sep, '_').replace('\x00', '')
        # Collapse multiple whitespace into a single space
        safe_root_name = re.sub(r'\s+', ' ', safe_root_name)
        if not safe_root_name:
            safe_root_name = 'root'
    except Exception:
        safe_root_name = 'root'

    # Optionally print the filetree used for HTML when verbose is requested.
    if verbose:
        print("\nFiletree used for HTML (id | label | parent | value):")
        for i, node_id in enumerate(ids):
            try:
                lab = labels[i]
                par = parents[i]
                val = values[i]
            except Exception:
                lab = ''
                par = ''
                val = ''
            print(f"  {node_id} | {lab} | parent={par} | value={val}")

    sun = go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        hovertext=hovertexts,
        hovertemplate='%{label}<br>%{hovertext}<extra></extra>',
        marker=dict(colors=colors, line=dict(width=0.5, color='white')),
    )
    fig_sun = go.Figure(sun)
    fig_sun.update_layout(margin=dict(t=10, l=10, r=10, b=10))
    sun_path = outdir / f"{safe_root_name}_wikigraph_sunburst.html"
    fig_sun.write_html(str(sun_path), include_plotlyjs='cdn' if not embed_js else True)

    tre = go.Treemap(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        hovertext=treemap_hovertexts,
        hovertemplate='%{label}<br>%{hovertext}<extra></extra>',
        text=cell_texts,
    texttemplate='%{label}<br>%{text}<extra></extra>',
    textfont=dict(size=12),
        marker=dict(colors=colors, line=dict(width=0.5, color='white')),
    )
    fig_treemap = go.Figure(tre)
    fig_treemap.update_layout(margin=dict(t=10, l=10, r=10, b=10))
    tre_path = outdir / f"{safe_root_name}_wikigraph_treemap.html"
    fig_treemap.write_html(str(tre_path), include_plotlyjs='cdn' if not embed_js else True)

    print(f"Wrote: {sun_path}\nWrote: {tre_path}")

    # Additional charts: top-N files, top-N directories, file-size histogram
    try:
        import plotly.express as px
    except Exception:
        px = None

    # Prepare a simple list of file entries (exclude directories)
    file_items = [(k, v) for k, v in sizes.items() if not k.endswith('/')]

    # Top N files
    def write_top_files(n: int = 20):
        top = sorted(file_items, key=lambda kv: kv[1], reverse=True)[:n]
        if not top:
            return
        names = [k for k, _ in top]
        vals = [v for _, v in top]
        if px:
            fig = px.bar(x=vals, y=names, orientation='h', labels={'x': 'Value', 'y': 'File'}, title=f'Top {n} files by {"size" if mode=="size" else "count"}')
            fig.update_layout(yaxis={'automargin': True}, margin=dict(t=30, l=200))
            out = outdir / f"wikigraph_top_{n}_files.html"
            fig.write_html(str(out), include_plotlyjs='cdn' if not embed_js else True)
        else:
            # If plotly.express is not available, do not produce a fallback text file.
            return

    # Top N directories (directories end with '/')
    def write_top_dirs(n: int = 20):
        dirs = [(k, v) for k, v in sizes.items() if k.endswith('/')]
        top = sorted(dirs, key=lambda kv: kv[1], reverse=True)[:n]
        if not top:
            return
        names = [k for k, _ in top]
        vals = [v for _, v in top]
        if px:
            fig = px.bar(x=vals, y=names, orientation='h', labels={'x': 'Value', 'y': 'Directory'}, title=f'Top {n} directories by {"size" if mode=="size" else "count"}')
            fig.update_layout(yaxis={'automargin': True}, margin=dict(t=30, l=200))
            out = outdir / f"wikigraph_top_{n}_dirs.html"
            fig.write_html(str(out), include_plotlyjs='cdn' if not embed_js else True)
        else:
            # No fallback when plotly.express is missing
            return

    # Histogram of file sizes
    def write_histogram(bins: int = 50):
        vals = [v for k, v in file_items if v > 0]
        if not vals:
            return
        if px:
            import numpy as _np
            # Use log-scale bins for readability when sizes vary widely
            log_vals = _np.log10(_np.array(vals))
            fig = px.histogram(x=log_vals, nbins=bins, labels={'x': 'log10(Value)'}, title='File size distribution (log10 scale)')
            fig.update_layout(margin=dict(t=30, l=10, r=10, b=10))
            out = outdir / "wikigraph_file_size_histogram.html"
            fig.write_html(str(out), include_plotlyjs='cdn' if not embed_js else True)
        else:
            # Skip creating a text histogram if plotly.express isn't available
            return

    # Write additional charts
    #write_top_files(20)
    #write_top_dirs(20)
    #write_histogram(50)


def parse_args():
    p = argparse.ArgumentParser(description="Create wikigraph sunburst and treemap HTML files")
    p.add_argument("--root", default='.', help="Path to the vault root")
    p.add_argument("--out", default='graphs', help="Output directory for HTML files")
    p.add_argument("--ext", action='append', help="Extensions to include (e.g. .md). Can be provided multiple times")
    p.add_argument("--exclude", action='append', help="Directory names to exclude (name only). Can be provided multiple times")
    p.add_argument("--embed", action='store_true', help="Embed Plotly JS into the HTML (works offline)")
    p.add_argument("--mode", choices=['size', 'count'], default='size', help="Use file size (bytes) or file count for values")
    p.add_argument("--child-spread", type=float, default=0.35, help="Initial hue spread allocated to root children (0..1)")
    p.add_argument("--spread-growth", type=float, default=1.0, help="Multiplier applied to spread each level (>=0)")
    # --recolor can be provided multiple times. If provided without a value
    # (i.e. `--recolor` alone) it will apply stored recolors from
    # color_recolors.md. If provided with values, each should be
    # path=#rrggbb and will be applied and merged into the recolor file.
    p.add_argument("--recolor", action='append', nargs='?', const='__STORED__', help="Recolor a node subtree with a hex color: 'path=#rrggbb'. Provide no value (just --recolor) to apply stored recolors from color_recolors.md.")
    p.add_argument("--pc", nargs='?', const='__ALL__', help="Generate graphs for a specific PC folder name (Players Part/PCs/<name>), or with no value generate for all names listed in pcs_input.md")
    p.add_argument("--all", action='store_true', help="Generate graphs for every folder under Players Part/PCs")
    p.add_argument("--include-gitignored", action='store_true', help="Include files matched by .gitignore when scanning the vault (by default gitignored files are skipped)")
    p.add_argument("--dms-tree", action='store_true', help="Generate a DMs graph rooted at 'DMs Part', include gitignored files, and name outputs with 'DMs' in the filename")
    p.add_argument("--verbose", "-v", action='store_true', help="Verbose output: print selected files when filtering per-PC")
    return p.parse_args()


def parse_bending_levels_from_sheet(path: Path) -> dict:
    """Parse a character sheet markdown file and return a dict of element->level.

    Looks for the '## Bending Levels' table and extracts the Level column.
    Returns keys like 'Air', 'Water', 'Earth', 'Fire', 'Spirit' with integer levels.
    """
    txt = path.read_text(encoding='utf-8')
    lines = txt.splitlines()
    # Patterns to match lines like:
    # | [[Waterbending Level]] | 3 | ...
    # or
    # | Waterbending Level | 3 |
    # or free text: Waterbending Level | 3
    patterns = [
        re.compile(r"\|\s*\[?\[?\s*(Airbending Level|Waterbending Level|Earthbending Level|Firebending Level|Spiritbending Level)\s*\]?\]?\s*\|\s*(\d+)", re.IGNORECASE),
        re.compile(r"(Airbending Level|Waterbending Level|Earthbending Level|Firebending Level|Spiritbending Level)\s*\|\s*(\d+)", re.IGNORECASE),
        # also match simpler labels like 'Air Level | 1' or 'Water Level | 3'
        re.compile(r"(Air Level|Water Level|Earth Level|Fire Level|Spirit Level)\s*\|\s*(\d+)", re.IGNORECASE),
    ]

    found: dict = {}
    for ln in lines:
        for pat in patterns:
            m = pat.search(ln)
            if m:
                key = m.group(1).strip()
                val = int(m.group(2))
                kln = key.lower()
                if 'air' in kln:
                    found['Air'] = val
                elif 'water' in kln:
                    found['Water'] = val
                elif 'earth' in kln:
                    found['Earth'] = val
                elif 'fire' in kln:
                    found['Fire'] = val
                elif 'spirit' in kln:
                    found['Spirit'] = val
    return found


def main():
    args = parse_args()
    # Always use the directory the script is run from as the repository/vault root.
    # This makes the file-tree generation independent of a --root argument.
    root = Path.cwd().resolve()
    # ALWAYS write outputs into the 'graphs' folder located next to this script.
    # This overrides any --out passed on the CLI to ensure results are colocated
    # with the script itself.
    try:
        script_dir = Path(__file__).resolve().parent
        outdir = script_dir.joinpath('graphs')
    except Exception:
        outdir = Path(args.out).expanduser().resolve()
    exts = DEFAULT_EXTS if not args.ext else {e if e.startswith('.') else '.' + e for e in args.ext}
    excludes = DEFAULT_EXCLUDES.union(set(args.exclude or []))
    print(f"Scanning: {root}\nExtensions: {sorted(exts)}\nExcludes: {sorted(excludes)}\nMode: {args.mode}\nEmbed JS: {args.embed}\nWriting to: {outdir}")

    # If --pc provided, generate per-PC graphs.
    if args.pc is not None:
        pc_arg = args.pc
        # Resolve Players Part/PCs relative to script directory first, then cwd
        script_dir = Path(__file__).resolve().parent
        pcs_root = script_dir.joinpath('Players Part', 'PCs')
        if not pcs_root.exists():
            pcs_root = Path('Players Part') / 'PCs'

        # Helper to read pcs_input.md and return a mapping of name -> element levels
        def read_pcs_input(path: Path) -> dict:
            try:
                txt = path.read_text(encoding='utf-8')
            except Exception:
                return {}
            out: dict = {}
            lines = [ln for ln in txt.splitlines() if ln.strip()]
            if not lines:
                return out
            # find first table header line
            header_idx = None
            for i, ln in enumerate(lines):
                if ln.strip().startswith('|') and 'name' in ln.lower():
                    header_idx = i
                    break
            if header_idx is None:
                # fallback: try first line that starts with '|' as header
                for i, ln in enumerate(lines):
                    if ln.strip().startswith('|'):
                        header_idx = i
                        break
            if header_idx is None:
                return out
            header = [c.strip() for c in lines[header_idx].split('|')]
            # build column name -> index
            col_index = {h.lower(): idx for idx, h in enumerate(header) if h}
            # element column names we care about
            elements = ['water', 'earth', 'air', 'fire', 'spirit']
            # parse subsequent table rows until a non-table line encountered
            for ln in lines[header_idx+1:]:
                if not ln.strip().startswith('|'):
                    break
                parts = [c.strip() for c in ln.split('|')]
                if len(parts) < 2:
                    continue
                name = parts[1]
                if not name:
                    continue
                levels: dict = {}
                for el in elements:
                    val = 0
                    # try to find header that matches element exactly or like 'water'
                    for key, idx in col_index.items():
                        if el in key:
                            try:
                                raw = parts[idx] if idx < len(parts) else ''
                                raw = raw.strip()
                                if raw == '':
                                    val = 0
                                else:
                                    # try parse int, strip non-digits
                                    m = re.search(r"(\d+)", raw)
                                    if m:
                                        val = int(m.group(1))
                            except Exception:
                                val = 0
                            break
                    levels[el.capitalize()] = val
                out[name] = levels
            return out

        target_names: list[str] = []
        pcs_levels = {}
        if pc_arg == '__ALL__':
            pcs_file = Path('pcs_input.md')
            pcs_levels = read_pcs_input(pcs_file)
            target_names = list(pcs_levels.keys())
        else:
            # still try to read pcs_input for a potential levels row for this PC
            pcs_file = Path('pcs_input.md')
            pcs_levels = read_pcs_input(pcs_file)
            target_names = [pc_arg]

        for name in target_names:
            pc_folder = pcs_root / name
            if not pc_folder.exists():
                print(f"PC folder not found: {pc_folder}")
                continue
            # Use PC folder as root and write outputs into script-local graphs
            print(f"Generating graphs for PC: {name} -> root {pc_folder}")
            # Attempt to read the character sheet to extract allowed bending levels
            char_sheet = pc_folder / f"{name} Character Sheet.md"
            allowed = None
            if char_sheet.exists():
                try:
                    allowed = parse_bending_levels_from_sheet(char_sheet)
                    print(f"  Parsed bending levels: {allowed}")
                except Exception as e:
                    print(f"  Could not parse character sheet {char_sheet}: {e}")
            else:
                # If there is no character sheet, attempt to use pcs_input.md levels
                if pcs_levels and name in pcs_levels:
                    allowed = pcs_levels.get(name)
                    if allowed:
                        print(f"  Using levels from pcs_input.md: {allowed}")

            # Pass the overall vault root so Rules/Bending Rules are scanned, but
            # provide the pc_folder as pc_subtree so the allowed subtree can be
            # created under the character folder.
            make_graphs(root, outdir, exts=exts, excludes=excludes, mode=args.mode, embed_js=args.embed, child_spread=args.child_spread, spread_growth=args.spread_growth, recolor_list=args.recolor, allowed_elements_levels=allowed, verbose=args.verbose, pc_subtree=pc_folder, pc_name=name, include_gitignored=args.include_gitignored)
        return

    # If --dms-tree provided, produce a DMs-rooted graph that includes files
    # matched by .gitignore and write outputs named with 'DMs'. This is a
    # convenience wrapper that roots the visualization at the DMs Part folder.
    if args.dms_tree:
        script_dir = Path(__file__).resolve().parent
        dms_folder = script_dir.joinpath('DMs Part')
        if not dms_folder.exists():
            dms_folder = Path('DMs Part')
        if not dms_folder.exists():
            print(f"DMs Part folder not found: {dms_folder}")
        else:
            print(f"Generating DMs graph rooted at: {dms_folder} (including .gitignore entries)")
            # Use the overall repo root for scanning so Rules/ and other
            # top-level folders remain discoverable, but set pc_subtree so
            # outputs are named 'DMs' and the allowed-merge behavior (if any)
            # will place mirrored nodes under the DMs subtree.
            make_graphs(root, outdir, exts=exts, excludes=excludes, mode=args.mode, embed_js=args.embed, child_spread=args.child_spread, spread_growth=args.spread_growth, recolor_list=args.recolor, verbose=args.verbose, pc_subtree=dms_folder, pc_name='DMs', include_gitignored=True)
        return

    # If --all provided, iterate every folder under Players Part/PCs and generate graphs
    if args.all:
        script_dir = Path(__file__).resolve().parent
        pcs_root = script_dir.joinpath('Players Part', 'PCs')
        if not pcs_root.exists():
            pcs_root = Path('Players Part') / 'PCs'

        if not pcs_root.exists():
            print(f"PCs root not found: {pcs_root}")
        else:
            for child in sorted(pcs_root.iterdir()):
                if not child.is_dir():
                    continue
                name = child.name
                pc_folder = child
                print(f"Generating graphs for PC: {name} -> root {pc_folder}")
                char_sheet = pc_folder / f"{name} Character Sheet.md"
                allowed = None
                if char_sheet.exists():
                    try:
                        allowed = parse_bending_levels_from_sheet(char_sheet)
                        print(f"  Parsed bending levels: {allowed}")
                    except Exception as e:
                        print(f"  Could not parse character sheet {char_sheet}: {e}")

                make_graphs(root, outdir, exts=exts, excludes=excludes, mode=args.mode, embed_js=args.embed, child_spread=args.child_spread, spread_growth=args.spread_growth, recolor_list=args.recolor, allowed_elements_levels=allowed, verbose=args.verbose, pc_subtree=pc_folder, pc_name=name, include_gitignored=args.include_gitignored)
        return

    # Default: generate graphs for the cwd root
    make_graphs(root, outdir, exts=exts, excludes=excludes, mode=args.mode, embed_js=args.embed, child_spread=args.child_spread, spread_growth=args.spread_growth, recolor_list=args.recolor, include_gitignored=args.include_gitignored)


if __name__ == '__main__':
    main()
