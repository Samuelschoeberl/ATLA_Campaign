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
from typing import Dict, List, Tuple


DEFAULT_EXCLUDES = {".git", "node_modules", ".obsidian", "__pycache__", "venv", ".venv"}
DEFAULT_EXTS = {".md", ".markdown", ".txt"}


def hsv_to_hex(h: float, s: float, v: float) -> str:
    """Convert HSV (h in [0,1), s,v in [0,1]) to a hex color string like '#rrggbb'."""
    # normalize hue into [0,1)
    hh = h % 1.0
    r, g, b = colorsys.hsv_to_rgb(hh, s, v)
    return '#{0:02x}{1:02x}{2:02x}'.format(int(r * 255), int(g * 255), int(b * 255))


def generate_readable_color(h: float, is_directory: bool = False) -> str:
    """Generate readable grayscale/monochrome colors for better readability.
    
    Args:
        h: Hue value (0-1) used to determine brightness level
        is_directory: Whether this is a directory (gets slightly darker shade)
    
    Returns:
        Hex color string optimized for readability
    """
    # Convert hue to a brightness level between light grey and dark grey
    # Use the hue to create variation while keeping colors readable
    brightness_base = 0.3 + (h * 0.5)  # Range from 30% to 80% brightness
    
    if is_directory:
        # Directories get slightly darker shades to distinguish from files
        brightness = max(0.2, brightness_base - 0.1)
    else:
        # Files get lighter shades for better text readability
        brightness = min(0.9, brightness_base + 0.1)
    
    # Create a grayscale color
    gray_value = int(brightness * 255)
    return '#{0:02x}{1:02x}{2:02x}'.format(gray_value, gray_value, gray_value)


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


def gather_file_tree(root: Path, exts=DEFAULT_EXTS, excludes=DEFAULT_EXCLUDES) -> Tuple[Dict[str, int], Dict[str, str], Dict[str, str]]:
    """Return a mapping of path parts joined by '/' to aggregated size in bytes.

    Keys include directories and files. Directory keys end with '/'.
    """
    root = root.resolve()
    sizes: Dict[str, int] = {}
    # Map from file key (relative path) to sanitized file content (for .md files)
    contents: Dict[str, str] = {}
    # Raw file text (un-sanitized) kept to detect special markers like '![['
    raw_contents: Dict[str, str] = {}

    for p in root.rglob("*"):
        # Skip excluded directories
        if any(part in excludes for part in p.parts):
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

    # Sort to get deterministic output (shorter keys first)
    items = sorted(sizes.items(), key=lambda kv: (kv[0].count('/'), kv[0]))

    for key, val in items:
        # id is the canonical key
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
            if len(parts) == 1:
                parent = "/"
            else:
                parent = "/".join(parts[:-1]) + "/"

        ids.append(node_id)
        labels.append(label)
        parents.append(parent)
        values.append(int(val))

    return ids, labels, parents, values


def make_graphs(root: Path, outdir: Path, exts=DEFAULT_EXTS, excludes=DEFAULT_EXCLUDES, mode: str = 'size', embed_js: bool = False, child_spread: float = 0.35, spread_growth: float = 1.0, recolor_list: List[str] | None = None) -> None:
    # mode: 'size' uses file byte sizes, 'count' counts each file as 1
    sizes, contents, raw_contents = gather_file_tree(root, exts=exts, excludes=excludes)

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

    ids, labels, parents, values = build_plotly_lists(sizes, root_label=root.name)

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
                # Remove backlink collections and collapse tables first, then convert newlines
                cleaned = replace_tables(remove_backlink_collection(txt))
                h = cleaned.replace('\n', '<br>')
                if len(h) > 1000:
                    h = h[:1000] + '...'
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
        # Pre-process to remove backlink collections and collapse tables
        pre = replace_tables(remove_backlink_collection(raw))
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
        h = '<br>'.join(first_lines)
        if len(lines) > len(first_lines):
            h = h + '...'
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
                # Always use readable color generation for consistent black-on-white theme
                is_directory = node_id.endswith('/')
                colors_by_id[node_id] = generate_readable_color(hue, is_directory)
            if protect:
                protected_ids.add(node_id)
        except Exception:
            colors_by_id.setdefault(node_id, '#cccccc')

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
            # Do not overwrite colors for protected ids
            if node_id not in protected_ids:
                is_directory = node_id.endswith('/')
                colors_by_id[node_id] = generate_readable_color(mid_hue_node, is_directory)
        except Exception:
            # fallback color
            colors_by_id.setdefault(node_id, '#cccccc')
    # Use the module-level deterministic_child_center (declared above)

        # Avatar Spirit Bridge uses the same grayscale approach as other sections
        # for consistent readability
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
                        # Use readable colors for Bending Rules elements
                        is_directory = child.endswith('/')
                        colors_by_id[child] = generate_readable_color(mid_hue, is_directory)
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
            is_directory = node_id.endswith('/')
            colors_by_id[node_id] = generate_readable_color(hue, is_directory)
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
            is_directory = child.endswith('/')
            colors_by_id[child] = generate_readable_color(mid_hue, is_directory)
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
    # Load persisted recolors from `color_recolors.md` in the vault root.
    recolor_md_path = root.joinpath('color_recolors.md')
    file_recolors = load_recolor_md(recolor_md_path) if recolor_md_path.exists() else HARDCODED_RECOLORS

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
            is_directory = n.endswith('/')
            colors_by_id[n] = generate_readable_color(h % 1.0, is_directory)

    # Final ordered colors list aligned with ids
    colors: List[str] = [colors_by_id.get(n, '#cccccc') for n in ids]

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
                        resolved_clean = replace_tables(remove_backlink_collection(resolved))
                        t = re.sub(r'\n+', '<br>', resolved_clean.strip())
                    else:
                        # Fallback to sanitized content for display
                        san_clean = replace_tables(remove_backlink_collection(sanitized))
                        t = san_clean.replace('\n', '<br>')
                    txt = t
                else:
                    san_clean = replace_tables(remove_backlink_collection(sanitized))
                    t = san_clean.replace('\n', '<br>')
                    # Do not truncate treemap cell text — show full sanitized content
                    txt = t
        cell_texts.append(txt)

    # Lazy import plotly
    try:
        import plotly.graph_objects as go
    except Exception as e:
        raise RuntimeError("plotly is required; install with: pip install plotly") from e

    outdir.mkdir(parents=True, exist_ok=True)

    sun = go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        hovertext=hovertexts,
        hovertemplate='%{label}<br>%{hovertext}<extra></extra>',
        marker=dict(colors=colors, line=dict(width=1, color='black')),
        textfont=dict(size=14, color='black', family='Arial'),
    )
    fig_sun = go.Figure(sun)
    fig_sun.update_layout(
        margin=dict(t=10, l=10, r=10, b=10),
        paper_bgcolor='#2a2a2a',  # Dark grey background
        plot_bgcolor='white',     # White plot area
        font=dict(color='black', family='Arial', size=12)
    )
    sun_path = outdir / "wikigraph_sunburst.html"
    fig_sun.write_html(str(sun_path), include_plotlyjs='cdn' if not embed_js else True,
                       config={'displayModeBar': False},
                       div_id="my-div",
                       include_mathjax=False,
                       post_script="""
                       <style>
                           body { background-color: #2a2a2a !important; margin: 0; padding: 20px; }
                       </style>
                       """)

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
        textfont=dict(size=12, color='black', family='Arial'),
        marker=dict(colors=colors, line=dict(width=1, color='black')),
    )
    fig_treemap = go.Figure(tre)
    fig_treemap.update_layout(
        margin=dict(t=10, l=10, r=10, b=10),
        paper_bgcolor='#2a2a2a',  # Dark grey background
        plot_bgcolor='white',     # White plot area  
        font=dict(color='black', family='Arial', size=12)
    )
    tre_path = outdir / "wikigraph_treemap.html"
    fig_treemap.write_html(str(tre_path), include_plotlyjs='cdn' if not embed_js else True,
                           config={'displayModeBar': False},
                           div_id="my-div",
                           include_mathjax=False,
                           post_script="""
                           <style>
                               body { background-color: #2a2a2a !important; margin: 0; padding: 20px; }
                           </style>
                           """)

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
            fig = px.bar(x=vals, y=names, orientation='h', 
                        labels={'x': 'Value', 'y': 'File'}, 
                        title=f'Top {n} files by {"size" if mode=="size" else "count"}',
                        color_discrete_sequence=['#666666'])  # Single grey color for all bars
            fig.update_layout(
                yaxis={'automargin': True}, 
                margin=dict(t=30, l=200),
                paper_bgcolor='#2a2a2a',  # Dark grey background
                plot_bgcolor='white',     # White plot area
                font=dict(color='black', family='Arial', size=12),
                title=dict(font=dict(color='white'))  # White title text on dark background
            )
            fig.update_traces(marker_line_color='black', marker_line_width=1)
            out = outdir / f"wikigraph_top_{n}_files.html"
            fig.write_html(str(out), include_plotlyjs='cdn' if not embed_js else True,
                           config={'displayModeBar': False},
                           div_id="my-div",
                           include_mathjax=False,
                           post_script="""
                           <style>
                               body { background-color: #2a2a2a !important; margin: 0; padding: 20px; }
                           </style>
                           """)
        else:
            # Fallback: basic text file
            out = outdir / f"wikigraph_top_{n}_files.txt"
            out.write_text('\n'.join(f"{v}\t{k}" for k, v in top))

    # Top N directories (directories end with '/')
    def write_top_dirs(n: int = 20):
        dirs = [(k, v) for k, v in sizes.items() if k.endswith('/')]
        top = sorted(dirs, key=lambda kv: kv[1], reverse=True)[:n]
        if not top:
            return
        names = [k for k, _ in top]
        vals = [v for _, v in top]
        if px:
            fig = px.bar(x=vals, y=names, orientation='h', 
                        labels={'x': 'Value', 'y': 'Directory'}, 
                        title=f'Top {n} directories by {"size" if mode=="size" else "count"}',
                        color_discrete_sequence=['#666666'])  # Single grey color for all bars
            fig.update_layout(
                yaxis={'automargin': True}, 
                margin=dict(t=30, l=200),
                paper_bgcolor='#2a2a2a',  # Dark grey background
                plot_bgcolor='white',     # White plot area
                font=dict(color='black', family='Arial', size=12),
                title=dict(font=dict(color='white'))  # White title text on dark background
            )
            fig.update_traces(marker_line_color='black', marker_line_width=1)
            out = outdir / f"wikigraph_top_{n}_dirs.html"
            fig.write_html(str(out), include_plotlyjs='cdn' if not embed_js else True,
                           config={'displayModeBar': False},
                           div_id="my-div",
                           include_mathjax=False,
                           post_script="""
                           <style>
                               body { background-color: #2a2a2a !important; margin: 0; padding: 20px; }
                           </style>
                           """)
        else:
            out = outdir / f"wikigraph_top_{n}_dirs.txt"
            out.write_text('\n'.join(f"{v}\t{k}" for k, v in top))

    # Histogram of file sizes
    def write_histogram(bins: int = 50):
        vals = [v for k, v in file_items if v > 0]
        if not vals:
            return
        if px:
            import numpy as _np
            # Use log-scale bins for readability when sizes vary widely
            log_vals = _np.log10(_np.array(vals))
            fig = px.histogram(x=log_vals, nbins=bins, 
                             labels={'x': 'log10(Value)'}, 
                             title='File size distribution (log10 scale)',
                             color_discrete_sequence=['#666666'])  # Single grey color
            fig.update_layout(
                margin=dict(t=30, l=10, r=10, b=10),
                paper_bgcolor='#2a2a2a',  # Dark grey background
                plot_bgcolor='white',     # White plot area
                font=dict(color='black', family='Arial', size=12),
                title=dict(font=dict(color='white'))  # White title text on dark background
            )
            fig.update_traces(marker_line_color='black', marker_line_width=1)
            out = outdir / "wikigraph_file_size_histogram.html"
            fig.write_html(str(out), include_plotlyjs='cdn' if not embed_js else True,
                           config={'displayModeBar': False},
                           div_id="my-div",
                           include_mathjax=False,
                           post_script="""
                           <style>
                               body { background-color: #2a2a2a !important; margin: 0; padding: 20px; }
                           </style>
                           """)
        else:
            out = outdir / "wikigraph_file_size_histogram.txt"
            out.write_text('\n'.join(str(v) for v in vals))

    # Write additional charts
    write_top_files(20)
    write_top_dirs(20)
    write_histogram(50)


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
    return p.parse_args()


def main():
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    outdir = Path(args.out).expanduser().resolve()
    exts = DEFAULT_EXTS if not args.ext else {e if e.startswith('.') else '.' + e for e in args.ext}
    excludes = DEFAULT_EXCLUDES.union(set(args.exclude or []))
    print(f"Scanning: {root}\nExtensions: {sorted(exts)}\nExcludes: {sorted(excludes)}\nMode: {args.mode}\nEmbed JS: {args.embed}\nWriting to: {outdir}")
    make_graphs(root, outdir, exts=exts, excludes=excludes, mode=args.mode, embed_js=args.embed, child_spread=args.child_spread, spread_growth=args.spread_growth, recolor_list=args.recolor)


if __name__ == '__main__':
    main()
