#!/usr/bin/env python3
"""Compatibility wrapper for Wikigraphs.

This thin wrapper imports and re-exports the canonical implementation
from `Mycelium.scripts.Python.Wikigraphs`. It intentionally contains no
other logic to avoid duplication and to keep the migration safe.
"""
from importlib import import_module
import sys
from pathlib import Path

# Ensure repo root is on sys.path so the package import works when invoked
REPO_ROOT = Path(__file__).resolve().parents[3]
repo_str = str(REPO_ROOT)
if repo_str not in sys.path:
    sys.path.insert(0, repo_str)

_canonical = import_module('Mycelium.scripts.Python.Wikigraphs')

# Re-export public symbols from canonical module
if hasattr(_canonical, '__all__'):
    for _n in getattr(_canonical, '__all__'):
        globals()[_n] = getattr(_canonical, _n)
else:
    for _n in dir(_canonical):
        if not _n.startswith('_'):
            globals()[_n] = getattr(_canonical, _n)

__all__ = [n for n in globals() if not n.startswith('_')]
#!/usr/bin/env python3
"""Compatibility wrapper for Wikigraphs.

Thin wrapper that imports and re-exports the canonical implementation
from Mycelium.scripts.Python.Wikigraphs. Keep this file minimal so older
import paths continue to work during the migration.
"""
from importlib import import_module
import sys
from pathlib import Path

# Ensure repo root is on sys.path so the package import works when invoked
REPO_ROOT = Path(__file__).resolve().parents[3]
repo_str = str(REPO_ROOT)
if repo_str not in sys.path:
    sys.path.insert(0, repo_str)

_canonical = import_module('Mycelium.scripts.Python.Wikigraphs')

# Re-export public symbols from canonical module
if hasattr(_canonical, '__all__'):
    for _n in getattr(_canonical, '__all__'):
        globals()[_n] = getattr(_canonical, _n)
else:
    for _n in dir(_canonical):
        if not _n.startswith('_'):
            globals()[_n] = getattr(_canonical, _n)

__all__ = [n for n in globals() if not n.startswith('_')]
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

    # Decide effective output directory.
    # Historically, when invoked as a CLI the script placed cluster graphs
    # under Mycelium/<safe_root_name>clusters for easier discovery. Preserve
    # that behavior when running as the standalone script (when ARGS global
    # is present). However, when called programmatically via import and the
    # caller provided an explicit `outdir`, prefer that outdir so callers
    # (like reboot_env_sync.sh) can control where HTML files are written.
    if safe_root_name.lower() != 'root' and globals().get('ARGS'):
        # When invoked from the CLI, default behavior historically placed
        # cluster graphs under Mycelium/<safe_root_name>clusters so the
        # outputs are easy to find next to the script. However, if the CLI
        # explicitly provided a non-default --root path (for example
        # `--root "Player Root/"`) the user likely expects the outputs to
        # be written alongside that scanned root. Respect that intent by
        # writing into the scanned `root` when ARGS.root is set to something
        # other than the default '.'. Otherwise preserve the historical
        # Mycelium clusters location for convenience.
        args_obj = globals().get('ARGS')
        root_arg = None
        try:
            root_arg = getattr(args_obj, 'root', None)
        except Exception:
            root_arg = None

        if root_arg and str(root_arg).strip() not in ('.', ''):
            # Write outputs into the scanned root folder so they appear next to
            # the user's vault structure (e.g. `Player Root/Player Root_wikigraph_*.html`).
            effective_outdir = root
        else:
            # place cluster graphs under Mycelium/<name>clusters when called from CLI
            effective_outdir = Path(__file__).resolve().parent.joinpath(f"{safe_root_name}clusters")
    else:
        # prefer the explicit outdir provided by the caller
        effective_outdir = outdir
    effective_outdir.mkdir(parents=True, exist_ok=True)

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
    # Use a light grey background for the plot and page
    fig_sun.update_layout(margin=dict(t=10, l=10, r=10, b=10), paper_bgcolor='#f0f0f0', plot_bgcolor='#f0f0f0')
    sun_path = effective_outdir / f"{safe_root_name}_wikigraph_sunburst.html"
    # Remove any existing variants of this graph to avoid editors or sync
    # tools creating numbered copies (e.g. '... 2.html'). This ensures the
    # newly generated graph overwrites previous outputs instead of leaving
    # multiple versions behind.
    try:
        for p in effective_outdir.glob(f"{safe_root_name}_wikigraph_sunburst*.html"):
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                # non-fatal: continue cleaning other matches
                continue
    except Exception:
        pass
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
    # Use a light grey background for the plot and page
    fig_treemap.update_layout(margin=dict(t=10, l=10, r=10, b=10), paper_bgcolor='#f0f0f0', plot_bgcolor='#f0f0f0')
    tre_path = effective_outdir / f"{safe_root_name}_wikigraph_treemap.html"
    # Clean up existing treemap HTML variants so the new file replaces any
    # previous copies and avoids versioned filenames introduced by external
    # tools or editors.
    try:
        for p in effective_outdir.glob(f"{safe_root_name}_wikigraph_treemap*.html"):
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                continue
    except Exception:
        pass
    fig_treemap.write_html(str(tre_path), include_plotlyjs='cdn' if not embed_js else True)

    print(f"Wrote: {sun_path}\nWrote: {tre_path}")
    # Quick debug: print absolute paths for generated files and the
    # intended copy destinations so callers (or server logs) can verify
    # where files were written and where they will be copied.
    try:
        try:
            sun_abs = Path(sun_path).resolve()
        except Exception:
            sun_abs = Path(sun_path)
        try:
            tre_abs = Path(tre_path).resolve()
        except Exception:
            tre_abs = Path(tre_path)
        try:
            estimated_dest_dir = root if root and root.exists() else effective_outdir
        except Exception:
            estimated_dest_dir = effective_outdir
        try:
            dest_sun_est = Path(estimated_dest_dir).joinpath(sun_path.name).resolve()
        except Exception:
            dest_sun_est = Path(estimated_dest_dir).joinpath(sun_path.name)
        try:
            dest_tre_est = Path(estimated_dest_dir).joinpath(tre_path.name).resolve()
        except Exception:
            dest_tre_est = Path(estimated_dest_dir).joinpath(tre_path.name)
        print(f"DEBUG_PATHS: generated sun -> {sun_abs}")
        print(f"DEBUG_PATHS: generated tre -> {tre_abs}")
        print(f"DEBUG_PATHS: intended dest dir -> {Path(estimated_dest_dir).resolve() if Path(estimated_dest_dir).exists() else estimated_dest_dir}")
        print(f"DEBUG_PATHS: dest sun -> {dest_sun_est}")
        print(f"DEBUG_PATHS: dest tre -> {dest_tre_est}")
    except Exception:
        # Non-fatal debug step; don't interfere with normal operation
        pass
    # By user request: ensure generated graphs are placed in the scanned root
    # directory so that the sunburst/treemap for a scanned folder appear next
    # to that folder (e.g. Player Root/Player Root_wikigraph_*.html or
    # Rules/Bending Rules/Bending Rules_wikigraph_*.html).
    try:
        debug = False
        try:
            args_obj = globals().get('ARGS')
            if args_obj and getattr(args_obj, 'debug', False):
                debug = True
        except Exception:
            debug = False

        try:
            from shutil import copy2
            # destination is the scanned root directory
            dest_dir = root if root and root.exists() else effective_outdir
            dest_sun = Path(dest_dir).joinpath(sun_path.name)
            dest_tre = Path(dest_dir).joinpath(tre_path.name)
            # Skip copying if source and destination are the same resolved path
            try:
                src_sun_res = Path(sun_path).resolve()
                dst_sun_res = Path(dest_sun).resolve()
            except Exception:
                src_sun_res = Path(sun_path)
                dst_sun_res = Path(dest_sun)

            try:
                src_tre_res = Path(tre_path).resolve()
                dst_tre_res = Path(dest_tre).resolve()
            except Exception:
                src_tre_res = Path(tre_path)
                dst_tre_res = Path(dest_tre)

            copied = []
            if src_sun_res != dst_sun_res:
                copy2(str(sun_path), str(dest_sun))
                copied.append((sun_path, dest_sun))
            else:
                if debug:
                    print(f"Debug: skipping copy of sunburst (source == dest): {src_sun_res}")

            if src_tre_res != dst_tre_res:
                copy2(str(tre_path), str(dest_tre))
                copied.append((tre_path, dest_tre))
            else:
                if debug:
                    print(f"Debug: skipping copy of treemap (source == dest): {src_tre_res}")

            if debug:
                for s, d in copied:
                    print(f"Debug: copied {s} -> {d}")
            else:
                if copied:
                    pairs = ' and '.join(str(d) for _, d in copied)
                    print(f"Also copied graphs to scanned root: {pairs}")
        except Exception as e:
            print(f"Warning: failed to copy generated graphs into scanned root: {e}")
    except Exception:
        # Non-fatal; don't break generation
        pass
    # If requested, create wrapper files and attempt to open them
    try:
        if globals().get('ARGS') and getattr(ARGS, 'print_out', False):
            create_and_open_wrappers(safe_root_name, sun_path, tre_path)
    except Exception:
        pass

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
            out = effective_outdir / f"wikigraph_top_{n}_files.html"
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
            out = effective_outdir / f"wikigraph_top_{n}_dirs.html"
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
            out = effective_outdir / "wikigraph_file_size_histogram.html"
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
    p.add_argument("--pc", nargs='?', const='__ALL__', help="Generate graphs for a specific PC folder name (under the configured pcs_root), or with no value generate for all names listed in the configured pcs_input (see system_state.md)")
    p.add_argument("--all", action='store_true', help="Generate graphs for every folder under Player Root/PCs/ (overrides --pc)")
    p.add_argument("--include-gitignored", action='store_true', help="Include files matched by .gitignore when scanning the vault (by default gitignored files are skipped)")
    p.add_argument("--dms-tree", action='store_true', help="Generate a DMs graph rooted at 'DMs Part', include gitignored files, and name outputs with 'DMs' in the filename")
    p.add_argument("--materialize-unresolved", action='store_true', help="When building per-PC graphs, write unresolved [[links]] as placeholder files under the PC folder 'Unresolved Links/'")
    p.add_argument("--verbose", "-v", action='store_true', help="Verbose output: print selected files when filtering per-PC")
    p.add_argument("--debug", action='store_true', help="Debug mode: print extra diagnostics and traces")
    p.add_argument("--print_out", action='store_true', help="When graphs are written, open resulting .md wrapper in Obsidian and .html in browser")
    p.add_argument("--opener", default=None, help="Command to open files (e.g. 'obsidian'). If not provided, uses platform default (open/xdg-open)")
    return p.parse_args()


def parse_bending_levels_from_sheet(path: Path) -> dict:
    """Parse a character sheet markdown file and return a dict of element->level.

    Looks for the '## Bending Levels' table and extracts the Level column.
    Returns keys like 'Air', 'Water', 'Earth', 'Fire', 'Spirit' with integer levels.
    """
    txt = path.read_text(encoding='utf-8')
    lines = txt.splitlines()

    def _assign(found: dict, name: str, val: int) -> None:
        kln = name.lower()
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

    found: dict = {}

    # 1) Try to find an explicit '## Bending Levels' section and parse the markdown table
    start_idx = None
    for i, ln in enumerate(lines):
        if re.match(r'^\s*##\s*Bending Levels', ln, re.IGNORECASE):
            start_idx = i
            break

    if start_idx is not None:
        # find header row (the first line after the heading that looks like a pipe table header)
        header_idx = None
        for j in range(start_idx + 1, min(len(lines), start_idx + 30)):
            if '|' in lines[j] and re.search(r'level', lines[j], re.IGNORECASE):
                header_idx = j
                break

        if header_idx is not None:
            header_line = lines[header_idx]
            # identify column index for 'Level'
            hdr_cells = [c.strip().lower() for c in header_line.strip().strip('|').split('|')]
            level_col = None
            for idx, h in enumerate(hdr_cells):
                if 'level' == h or 'level' in h:
                    # prefer a plain 'level' header, otherwise accept any containing 'level'
                    level_col = idx
                    break

            # if we didn't detect a 'Level' header, fallback to second column
            if level_col is None:
                if len(hdr_cells) >= 2:
                    level_col = 1
                else:
                    level_col = 0

            # parse subsequent rows until a blank or non-table line
            row_idx = header_idx + 1
            # skip separator row if present (---)
            if row_idx < len(lines) and re.match(r'^\s*\|?\s*[:\-\s\|]+$', lines[row_idx]):
                row_idx += 1

            while row_idx < len(lines):
                row = lines[row_idx].strip()
                if not row or not ('|' in row):
                    break
                cells = [c.strip() for c in row.strip().strip('|').split('|')]
                # element cell is likely first non-empty cell
                elem_cell = cells[0] if cells else ''
                # level cell may be at level_col (guard length)
                level_cell = ''
                if level_col is not None and level_col < len(cells):
                    level_cell = cells[level_col]
                # extract numeric from level_cell
                m = re.search(r'(\d+)', level_cell)
                val = int(m.group(1)) if m else 0
                # normalize element name (strip wikilink [[...]] if present)
                elem = re.sub(r'\[\[|\]\]', '', elem_cell)
                elem = re.sub(r'\[|\]', '', elem)
                elem = elem.strip()
                if elem:
                    _assign(found, elem, val)
                else:
                    # try to infer element from full row text
                    _assign(found, row, val)

                row_idx += 1

            if PCS_DEBUG:
                print(f"[pcs-debug] parse_bending_levels_from_sheet found (table): {found}")
            return found

    # 2) Fallback: scan whole file for loose 'Air Level | 3' or '[[Airbending Level]] | 3' patterns
    fallback_patterns = [
        re.compile(r"\b(airbending level|waterbending level|earthbending level|firebending level|spiritbending level)\b[^\d]*(\d+)", re.IGNORECASE),
        re.compile(r"\b(air level|water level|earth level|fire level|spirit level)\b[^\d]*(\d+)", re.IGNORECASE),
        re.compile(r"\[\[([^\]]+?)\]\][^\d]*(\d+)", re.IGNORECASE),
    ]
    for ln in lines:
        for pat in fallback_patterns:
            m = pat.search(ln)
            if m:
                key = m.group(1).strip()
                val = int(m.group(2))
                _assign(found, key, val)

    if PCS_DEBUG:
        print(f"[pcs-debug] parse_bending_levels_from_sheet fallback found: {found}")
    return found


def read_pcs_input(path: Path) -> Tuple[dict, dict]:
    """Top-level helper: Read `pcs_input.md` and return (elements_map, stats_map).

    elements_map: name -> {Water,Earth,Air,Fire,Spirit}
    stats_map: name -> {Strength,Dexterity,Constitution,Intelligence,Wisdom,Charisma}
    """
    try:
        txt = path.read_text(encoding='utf-8')
    except Exception:
        return {}, {}

    elements_out: dict = {}
    stats_out: dict = {}
    lines = [ln for ln in txt.splitlines() if ln.strip()]
    if not lines:
        return elements_out, stats_out

    # Find header: prefer a line with 'name' and pipe separators
    header_idx = None
    for i, ln in enumerate(lines):
        if 'name' in ln.lower() and '|' in ln:
            header_idx = i
            break
    if header_idx is None:
        # fallback: first pipe-starting line
        for i, ln in enumerate(lines):
            if ln.strip().startswith('|'):
                header_idx = i
                break
    if header_idx is None:
        return elements_out, stats_out

    # normalize header parts
    header_parts = [p.strip() for p in lines[header_idx].strip().strip('|').split('|')]
    norm_headers = [re.sub(r'[^A-Za-z0-9_]+', ' ', h).strip().lower() for h in header_parts]

    if PCS_DEBUG:
        print(f"[pcs-debug] header_parts={header_parts}")
        print(f"[pcs-debug] norm_headers={norm_headers}")

    def find_col(*candidates):
        for cand in candidates:
            cand = cand.lower()
            for idx, h in enumerate(norm_headers):
                if cand in h:
                    return idx
        return None

    idx_name = find_col('name')
    idx_str = find_col('str', 'strength')
    idx_dex = find_col('dex', 'dexterity')
    idx_con = find_col('con', 'constitution')
    idx_int = find_col('int', 'intelligence')
    idx_wis = find_col('wis', 'wisdom')
    idx_cha = find_col('cha', 'charisma')

    idx_water = find_col('water')
    idx_earth = find_col('earth')
    idx_air = find_col('air')
    idx_fire = find_col('fire')
    idx_spirit = find_col('spirit')

    # data rows start after header and optional separator
    data_start = header_idx + 1
    if data_start < len(lines) and re.match(r"^\s*\|?\s*[-:]+", lines[data_start]):
        data_start += 1

    for ln in lines[data_start:]:
        if not ln.strip().startswith('|'):
            # stop at first non-table row
            break
        parts = [p.strip() for p in ln.strip().strip('|').split('|')]
        if PCS_DEBUG:
            print(f"[pcs-debug] row parts={parts}")
        if idx_name is None or idx_name >= len(parts):
            continue
        name = parts[idx_name]
        # normalize and filter out separator rows that are only dashes like '------'
        if isinstance(name, str):
            name = name.strip()
        if not name:
            continue
        if re.fullmatch(r"-+", name):
            # skip table separator-like rows
            if PCS_DEBUG:
                print(f"[pcs-debug] skipping dash-only pcs_input row: '{name}'")
            continue
        if PCS_DEBUG:
            print(f"[pcs-debug] extracted name='{name}' (compare lower to keys)")

        def get_int_at(idx):
            if idx is None or idx >= len(parts):
                return 0
            raw = parts[idx]
            raw = raw.strip()
            if raw == '':
                return 0
            m = re.search(r"(-?\d+)", raw)
            if not m:
                return 0
            try:
                return int(m.group(1))
            except Exception:
                return 0

        core = {
            'Strength': get_int_at(idx_str),
            'Dexterity': get_int_at(idx_dex),
            'Constitution': get_int_at(idx_con),
            'Intelligence': get_int_at(idx_int),
            'Wisdom': get_int_at(idx_wis),
            'Charisma': get_int_at(idx_cha),
        }
        elems = {
            'Water': get_int_at(idx_water),
            'Earth': get_int_at(idx_earth),
            'Air': get_int_at(idx_air),
            'Fire': get_int_at(idx_fire),
            'Spirit': get_int_at(idx_spirit),
        }

        stats_out[name] = core
        elements_out[name] = elems

    return elements_out, stats_out


def main():
    global ARGS
    args = parse_args()
    ARGS = args
    # enable PCS debug via --verbose as convenient shorthand
    global PCS_DEBUG
    PCS_DEBUG = PCS_DEBUG or bool(args.verbose)
    # debug mode enables more detailed diagnostic printing
    global DEBUG
    DEBUG = bool(getattr(args, 'debug', False))
    if DEBUG:
        # debug implies verbose for additional prints used by PCS_DEBUG spots
        PCS_DEBUG = True
    # Determine the repository/vault root. Default is cwd but allow --root to
    # explicitly override the scanned root (supports relative and absolute paths).
    # This makes it possible to run e.g. `--root "Player Root/"` to scan only
    # that subtree and produce graphs rooted at that folder.
    try:
        root_arg = Path(args.root or '.')
    except Exception:
        root_arg = Path('.')
    if not root_arg.is_absolute():
        root = Path.cwd().joinpath(root_arg).resolve()
    else:
        root = root_arg.resolve()
    # Determine output dir from system_state.md (editable) or fall back to CLI
    try:
        script_dir = Path(__file__).resolve().parent
    except Exception:
        script_dir = Path('.').resolve()
    cfg_out = get_config('graphs', args.out)
    # Prefer a graphs folder next to the script when the config value is the default
    if cfg_out == args.out:
        outdir = script_dir.joinpath(cfg_out)
    else:
        outdir = Path(cfg_out).expanduser().resolve()
    exts = DEFAULT_EXTS if not args.ext else {e if e.startswith('.') else '.' + e for e in args.ext}
    excludes = DEFAULT_EXCLUDES.union(set(args.exclude or []))
    print(f"Scanning: {root}\nExtensions: {sorted(exts)}\nExcludes: {sorted(excludes)}\nMode: {args.mode}\nEmbed JS: {args.embed}\nWriting to: {outdir}")
    if DEBUG:
        try:
            pfile = Path(__file__).resolve()
            print(f"[debug] script file: {pfile}")
            parents = [str(p) for p in pfile.parents]
            print(f"[debug] script parents (top-first): {parents}")
            print(f"[debug] cwd: {Path.cwd()}")
            print(f"[debug] repo root candidate (script.parents[3] if present): {parents[3] if len(parents)>3 else '(not present)'}")
        except Exception as _e:
            print(f"[debug] failed to print startup diagnostics: {_e}")

    # If --pc provided, generate per-PC graphs. If --all is set, it overrides --pc.
    # Determine pc_arg from --pc. If --all is set it overrides --pc.
    pc_arg = args.pc if args.pc is not None else None
    if args.all:
        pc_arg = '__ALL__'
    # Resolve PCs root. Prefer an explicit 'PC Character Sheets' folder if present
    # somewhere in the repository subtree; otherwise fall back to the canonical
    # 'Players Part/PCs' location next to the script or in the cwd.
    script_dir = Path(__file__).resolve().parent
    pcs_root = find_first_pc_character_sheets(script_dir)
    if pcs_root is None:
        # Respect configured pcs_root if present, otherwise default legacy path
        cfg_pcs = get_config('pcs_root', 'Players Part/PCs')
        try:
            pcs_root = script_dir.joinpath(*(cfg_pcs.split('/')))
        except Exception:
            pcs_root = script_dir.joinpath('Players Part', 'PCs')
        if not pcs_root.exists():
            pcs_root = Path(cfg_pcs)

    # Use the top-level read_pcs_input helper (returns elements_map, stats_map)

    target_names: list[str] = []
    pcs_levels = {}
    pcs_stats = {}
    # Names of graphs we generate during this run (used to prune stale HTMLs)
    generated_names: list[str] = []

    # Helper: collect HTML-inferred root names from existing *_wikigraph_*.html files
    def infer_names_from_existing_htmls(base: Path) -> set:
        out_set = set()
        try:
            for p in base.rglob('*_wikigraph_*.html'):
                nm = p.name
                if '_wikigraph_' in nm:
                    root_part = nm.split('_wikigraph_', 1)[0].strip()
                    if root_part:
                        out_set.add(root_part)
        except Exception:
            pass
        return out_set

        if pc_arg == '__ALL__' and args.all:
            # When both --pc (no value) and --all are provided we build the
            # union of names from pcs_input.md and any existing wikigraph HTMLs
            # found in the repository. This ensures we recreate every per-PC
            # graph that exists or that is declared in pcs_input.md, and then
            # allows us to remove stale HTML files.
            pcs_file = Path(get_config('pcs_input', 'pcs_input.md'))
            pcs_levels, pcs_stats = read_pcs_input(pcs_file)
            names_from_pcs = set(pcs_levels.keys())
            # infer from script-local graphs directory and also the repo tree
            script_dir = Path(__file__).resolve().parent
            names_from_html = infer_names_from_existing_htmls(script_dir)
            # Also check top-level 'graphs' and 'Players Part/graphs' folders if present
            names_from_html.update(infer_names_from_existing_htmls(script_dir.joinpath('graphs')) if script_dir.joinpath('graphs').exists() else set())
            names_from_html.update(infer_names_from_existing_htmls(script_dir.joinpath('Players Part').joinpath('graphs')) if script_dir.joinpath('Players Part').joinpath('graphs').exists() else set())
            # Filter out any names that contain no alphanumeric characters
            # (these are likely artifacts like '-------' produced from table
            # separators or stale files). Keep names that have at least one
            # ASCII letter or digit.
            combined_raw = names_from_pcs.union(names_from_html)
            combined = sorted([n for n in combined_raw if isinstance(n, str) and re.search(r'[A-Za-z0-9]', n)])
            target_names = list(combined)
        else:
            # existing behavior: either specific PC provided or --pc without --all
            pcs_file = Path(get_config('pcs_input', 'pcs_input.md'))
            pcs_levels, pcs_stats = read_pcs_input(pcs_file)
            if pc_arg == '__ALL__':
                target_names = list(pcs_levels.keys())
            else:
                target_names = [pc_arg]

        # Generate graphs for each target name. Attempt to locate the PC folder
        # under Players Part/PCs; if not found try a broader search. If no
        # folder exists we still generate an HTML named after the PC (pc_name)
        # so files inferred from existing HTMLs are recreated.
        generated_names = []
        for name in target_names:
            pc_folder = pcs_root / name
            if not pc_folder.exists():
                # If the PC is defined in pcs_input.md, create its folder under
                # the Players Part/PCs root so we can create a Character Sheet.
                created_folder = False
                if name in pcs_levels:
                    try:
                        pc_folder = pcs_root / name
                        pc_folder.mkdir(parents=True, exist_ok=True)
                        created_folder = True
                        print(f"Created PC folder: {pc_folder}")
                    except Exception as e:
                        print(f"Failed to create PC folder {pcs_root / name}: {e}")

                if not created_folder:
                    # try to find a directory anywhere under the script dir with this basename
                    found = None
                    try:
                        for d in Path(__file__).resolve().parent.rglob('*'):
                            if d.is_dir() and d.name == name:
                                found = d
                                break
                    except Exception:
                        found = None
                    if found:
                        pc_folder = found
                    else:
                        # not found; warn but continue to generate a named graph without pc_subtree
                        print(f"PC folder not found (will still generate named graph): {pcs_root / name}")

            print(f"Generating graphs for PC: {name} -> root {pc_folder if pc_folder.exists() else '(no folder)'}")
            char_sheet = None
            allowed = None
            if pc_folder.exists():
                char_sheet = pc_folder / f"{name} Character Sheet.md"
                # If the character sheet is missing (or present but appears
                # to be a minimal stub), create/overwrite it with the full
                # template used by update_char.ensure_pc_sheet when verbose is set.
                # Always create or re-create the full character sheet template
                # when the PC folder exists and the sheet is missing or appears
                # incomplete. Previously this only ran on --verbose; make it
                # unconditional for per-PC generation.
                should_create = False
                if not char_sheet.exists():
                    should_create = True
                else:
                    try:
                        txt = char_sheet.read_text(encoding='utf-8', errors='replace')
                        # consider it incomplete if it lacks a Core Stats header
                        # or the expected bending-level wikilinks
                        # If the file contains our AUTOGEN_MARKER we treat it as
                        # autogenerated and allow overwriting so pcs_input.md edits
                        # propagate into regenerated sheets.
                        if AUTOGEN_MARKER in txt or '## Core Stats' not in txt or '[[Airbending Level]]' not in txt:
                            should_create = True
                    except Exception:
                        should_create = True

                # Primary stat defaults: prefer values from pcs_input.md, fallback to zeros
                primary_stats = {'Strength':0,'Dexterity':0,'Constitution':0,'Intelligence':0,'Wisdom':0,'Charisma':0}
                if pcs_stats and name in pcs_stats:
                    primary_stats.update(pcs_stats.get(name, {}))

                if should_create:
                    try:
                        print(f"  Character sheet missing or incomplete; creating: {char_sheet}")
                        folder = pc_folder
                        folder.mkdir(parents=True, exist_ok=True)
                        lines = []
                        # mark autogenerated files so later runs can detect them
                        lines.append(AUTOGEN_MARKER)
                        lines.append(f"**Name:** {name}")
                        lines.append("")
                        lines.append('## Core Stats')
                        lines.append('| Stat | Value |')
                        lines.append('| ---- | ----: |')
                        for s in ('Strength','Dexterity','Constitution','Intelligence','Wisdom','Charisma'):
                            val = primary_stats.get(s, 0)
                            lines.append(f'| {s} | {val} |')
                        lines.append('')
                        lines.append('## Bending Levels')
                        lines.append('| Element                 | Level | Notes                  | Auto |')
                        lines.append('| ----------------------- | ----- | ---------------------- | ---- |')
                        lines.append('| [[Airbending Level]]    | 0     |                        | Y    |')
                        lines.append('| [[Waterbending Level]]  | 0     |                        | Y    |')
                        lines.append('| [[Earthbending Level]]  | 0     |                        | Y    |')
                        lines.append('| [[Firebending Level]]   | 0     |                        | Y    |')
                        lines.append('| [[Spiritbending Level]] | 0     |                        | Y    |')
                        # Add Vital Stats and Secondary Stats placeholders so update_char.py can populate them
                        lines.append('')
                        lines.append('## Vital Stats')
                        lines.append('| Label | Value | Auto |')
                        lines.append('| ----- | ----: | ---- |')
                        lines.append('| Max Hit Points | 0 | Y |')
                        lines.append('| Current Hit Points | 0 | Y |')
                        lines.append('| Evasion | 0 | Y |')
                        lines.append('| Armor | 0 | Y |')
                        lines.append('')
                        lines.append('## Secondary Stats')
                        lines.append('| Label | Value | Auto |')
                        lines.append('| ----- | ----: | ---- |')
                        lines.append('| Example Secondary | 0 | Y |')
                        try:
                            char_sheet.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                            print(f'  Created PC folder and character sheet: {char_sheet}')
                        except Exception as e:
                            print(f'  Could not create character sheet {char_sheet}: {e}')
                    except Exception as e:
                        print(f"  Could not create character sheet {char_sheet}: {e}")
                if char_sheet.exists():
                    try:
                        allowed = parse_bending_levels_from_sheet(char_sheet)
                        print(f"  Parsed bending levels: {allowed}")
                        # Prefer pcs_input.md values when a row exists for this PC.
                        # If pcs_input.md declares any non-zero element level for the
                        # PC we'll use those values as authoritative.
                        try:
                            # If a pcs_input.md row exists for this PC, treat it as
                            # authoritative for bending levels (unconditional override).
                            if pcs_levels and name in pcs_levels:
                                pcs_allowed = pcs_levels.get(name)
                                if pcs_allowed is not None:
                                    allowed = pcs_allowed
                                    print(f"  Overriding with pcs_input.md levels (authoritative): {allowed}")
                        except Exception:
                            pass
                    except Exception as e:
                        print(f"  Could not parse character sheet {char_sheet}: {e}")
                else:
                    # Prefer primary stats and bending levels from pcs_input.md
                    if pcs_levels and name in pcs_levels:
                        allowed = pcs_levels.get(name)
                        if allowed:
                            print(f"  Using levels from pcs_input.md: {allowed}")
                    # Also prepare to use primary stats from pcs_input.md when creating sheets
                # Primary stat defaults: prefer values from pcs_input.md, fallback to zeros
                primary_stats = {'Strength':0,'Dexterity':0,'Constitution':0,'Intelligence':0,'Wisdom':0,'Charisma':0}
                if pcs_stats and name in pcs_stats:
                    primary_stats.update(pcs_stats.get(name, {}))

            # If pc_folder exists pass it as pc_subtree so mirroring works;
            # otherwise call make_graphs with pc_name only to recreate the HTML files.
            if pc_folder.exists():
                make_graphs(root, outdir, exts=exts, excludes=excludes, mode=args.mode, embed_js=args.embed, child_spread=args.child_spread, spread_growth=args.spread_growth, recolor_list=args.recolor, allowed_elements_levels=allowed, verbose=args.verbose, pc_subtree=pc_folder, pc_name=name, include_gitignored=args.include_gitignored, materialize_unresolved=args.materialize_unresolved)
            else:
                make_graphs(root, outdir, exts=exts, excludes=excludes, mode=args.mode, embed_js=args.embed, child_spread=args.child_spread, spread_growth=args.spread_growth, recolor_list=args.recolor, allowed_elements_levels=allowed, verbose=args.verbose, pc_subtree=None, pc_name=name, include_gitignored=args.include_gitignored, materialize_unresolved=args.materialize_unresolved)
            generated_names.append(name)

        # Always generate the root graphs as well so the top-level sunburst/treemap
        # exists alongside per-PC outputs.
        try:
            print("Generating root graphs for workspace")
            make_graphs(root, outdir, exts=exts, excludes=excludes, mode=args.mode, embed_js=args.embed, child_spread=args.child_spread, spread_growth=args.spread_growth, recolor_list=args.recolor, verbose=args.verbose, include_gitignored=args.include_gitignored, materialize_unresolved=args.materialize_unresolved)
        except Exception as e:
            print(f"Could not generate root graphs: {e}")

        # If we built the combined list (pc + html inferred), remove stale HTML files
        # that no longer correspond to any name in generated_names. We look for
        # files matching '*_wikigraph_*.html' under the script dir and its graphs
        # subfolders.
        if args.pc == '__ALL__' and args.all:
            to_check_dirs = [Path(__file__).resolve().parent]
            gdir = Path(__file__).resolve().parent.joinpath('graphs')
            if gdir.exists():
                to_check_dirs.append(gdir)
            pp_gdir = Path(__file__).resolve().parent.joinpath('Players Part').joinpath('graphs')
            if pp_gdir.exists():
                to_check_dirs.append(pp_gdir)

            existing_htmls = []
            for base in to_check_dirs:
                try:
                    for p in base.rglob('*_wikigraph_*.html'):
                        existing_htmls.append(p)
                except Exception:
                    continue

            # Determine roots that are considered current (exact match).
            # Also protect the repository root's safe name so we don't delete
            # the top-level graphs we just wrote.
            current_roots = set(generated_names)
            try:
                raw_name = str(root.name).strip()
                safe_root_name = raw_name.replace(os.sep, '_').replace('\x00', '')
                safe_root_name = re.sub(r'\s+', ' ', safe_root_name)
                current_roots.add(safe_root_name)
                current_roots.add(raw_name)
            except Exception:
                pass
            for p in existing_htmls:
                nm = p.name
                if '_wikigraph_' in nm:
                    root_part = nm.split('_wikigraph_', 1)[0].strip()
                    if root_part not in current_roots:
                        try:
                            p.unlink()
                            print(f"Deleted stale graph: {p}")
                        except Exception:
                            print(f"Could not delete stale graph: {p}")
        return

    # If --dms-tree provided, produce a DMs-rooted graph that includes files
    # matched by .gitignore and write outputs named with 'DMs'. This is a
    # convenience wrapper that roots the visualization at the DMs Part folder.
    if args.dms_tree:
        script_dir = Path(__file__).resolve().parent
        # Respect configured DMs root
        cfg_dms = get_config('dms_root', 'DMs Part')
        try:
            dms_folder = script_dir.joinpath(*(cfg_dms.split('/')))
        except Exception:
            dms_folder = script_dir.joinpath('DMs Part')
        if not dms_folder.exists():
            dms_folder = Path(cfg_dms)
        if not dms_folder.exists():
            print(f"DMs Part folder not found: {dms_folder}")
        else:
            print(f"Generating DMs graph rooted at: {dms_folder} (including .gitignore entries)")
            # Use the overall repo root for scanning so Rules/ and other
            # top-level folders remain discoverable, but set pc_subtree so
            # outputs are named 'DMs' and the allowed-merge behavior (if any)
            # will place mirrored nodes under the DMs subtree.
            make_graphs(root, outdir, exts=exts, excludes=excludes, mode=args.mode, embed_js=args.embed, child_spread=args.child_spread, spread_growth=args.spread_growth, recolor_list=args.recolor, verbose=args.verbose, pc_subtree=dms_folder, pc_name='DMs', include_gitignored=True, materialize_unresolved=args.materialize_unresolved)
        return

    # If --all provided, iterate every folder under Players Part/PCs and generate graphs
    if args.all:
        script_dir = Path(__file__).resolve().parent
        pcs_root = find_first_pc_character_sheets(script_dir)
        if pcs_root is None:
            # common vault layouts: 'Players Part/PCs' or 'Player Root/PCs'
            candidates = [
                script_dir.joinpath('Players Part', 'PCs'),
                script_dir.joinpath('Player Root', 'PCs'),
                Path('Players Part') / 'PCs',
                Path('Player Root') / 'PCs',
                # also try a case-insensitive scan under script_dir
            ]
            found = None
            for c in candidates:
                if c.exists():
                    found = c
                    break
            if not found:
                # try a case-insensitive search for a folder named 'players part' or 'player root'
                for child in script_dir.iterdir():
                    if not child.is_dir():
                        continue
                    low = child.name.lower()
                    if low in ('players part', 'player root'):
                        pcdir = child.joinpath('PCs')
                        if pcdir.exists():
                            found = pcdir
                            break
            pcs_root = found or script_dir.joinpath('Players Part', 'PCs')

        if not pcs_root.exists():
            print(f"PCs root not found: {pcs_root} (tried Players Part/PCs and Player Root/PCs)")
        else:
            # Remove stale punctuation-only graph HTMLs that can be inferred as PCs
            try:
                graph_dir = outdir
                if not graph_dir.exists():
                    graph_dir = Path('graphs')
                if graph_dir.exists():
                    for f in graph_dir.glob('*_wikigraph_*.html'):
                        stem = f.name.split('_wikigraph_')[0]
                        # if the stem contains no alphanumeric characters it's likely stale
                        if re.fullmatch(r'[^A-Za-z0-9]+', stem):
                            try:
                                f.unlink()
                                if PCS_DEBUG:
                                    print(f"[pcs-debug] removed stale graph file: {f}")
                            except Exception:
                                pass
            except Exception:
                pass
            # Orchestration pre-steps: regenerate secondary stats, update recolors,
            # and update character sheets before generating graphs for every PC.
            # Run external scripts from the repository root using the same
            # Python interpreter. Failures are non-fatal but printed.
            try:
                print("Orchestration: regenerating secondary stats for all PCs...")
                subprocess.run([sys.executable, str(script_dir.joinpath('generate_secondary_stats.py')), '--all'], check=False)
            except Exception as e:
                print(f"Warning: failed to run generate_secondary_stats.py --all: {e}")
            try:
                    print("Orchestration: updating recolors (update_recolouring.py)...")
                    # update_recolouring.py was moved into the package helpers; run via -m
                    subprocess.run([sys.executable, '-m', 'WikiFileSystemManager.helpers.update_recolouring'], check=False)
            except Exception as e:
                print(f"Warning: failed to run update_recolouring.py: {e}")
            # Load pcs_input.md so we can prefer primary stats and element levels
            pcs_file = Path(get_config('pcs_input', 'pcs_input.md'))
            pcs_levels, pcs_stats = read_pcs_input(pcs_file)

            # Pre-create AUTOGEN character sheets for every PC declared in pcs_input.md
            # so that update_char.py --all can find and update them. Skip names that
            # are empty or look like table separators (dash-only).
            try:
                created_any = False
                for pc_name in list(pcs_stats.keys()):
                    if not isinstance(pc_name, str):
                        continue
                    nm = pc_name.strip()
                    if not nm:
                        continue
                    # skip names that are only dashes or punctuation
                    if re.fullmatch(r"[-\W]+", nm):
                        if PCS_DEBUG:
                            print(f"[pcs-debug] skipping autogen for invalid pc name: '{nm}'")
                        continue
                    pc_folder = pcs_root / nm
                    try:
                        pc_folder.mkdir(parents=True, exist_ok=True)
                    except Exception:
                        continue
                    char_sheet = pc_folder / f"{nm} Character Sheet.md"
                    if char_sheet.exists():
                        # preserve existing sheets
                        continue
                    # primary stats defaults from pcs_input.md
                    primary_stats = {'Strength':0,'Dexterity':0,'Constitution':0,'Intelligence':0,'Wisdom':0,'Charisma':0}
                    if pcs_stats and nm in pcs_stats:
                        primary_stats.update(pcs_stats.get(nm, {}))
                    try:
                        lines = []
                        lines.append(AUTOGEN_MARKER)
                        lines.append(f"**Name:** {nm}")
                        lines.append("")
                        lines.append('## Core Stats')
                        lines.append('| Stat | Value |')
                        lines.append('| ---- | ----: |')
                        for s in ('Strength','Dexterity','Constitution','Intelligence','Wisdom','Charisma'):
                            val = primary_stats.get(s, 0)
                            lines.append(f'| {s} | {val} |')
                        lines.append('')
                        lines.append('## Bending Levels')
                        lines.append('| Element                 | Level | Notes                  | Auto |')
                        lines.append('| ----------------------- | ----- | ---------------------- | ---- |')
                        lines.append('| [[Airbending Level]]    | 0     |                        | Y    |')
                        lines.append('| [[Waterbending Level]]  | 0     |                        | Y    |')
                        lines.append('| [[Earthbending Level]]  | 0     |                        | Y    |')
                        lines.append('| [[Firebending Level]]   | 0     |                        | Y    |')
                        lines.append('| [[Spiritbending Level]] | 0     |                        | Y    |')
                        # Add Vital and Secondary placeholders for bulk-created sheets
                        lines.append('')
                        lines.append('## Vital Stats')
                        lines.append('| Label | Value | Auto |')
                        lines.append('| ----- | ----: | ---- |')
                        lines.append('| Max Hit Points | 0 | Y |')
                        lines.append('| Current Hit Points | 0 | Y |')
                        lines.append('| Evasion | 0 | Y |')
                        lines.append('| Armor | 0 | Y |')
                        lines.append('')
                        lines.append('## Secondary Stats')
                        lines.append('| Label | Value | Auto |')
                        lines.append('| ----- | ----: | ---- |')
                        lines.append('| Example Secondary | 0 | Y |')

                        try:
                            char_sheet.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                            created_any = True
                            if PCS_DEBUG:
                                print(f"[pcs-debug] created AUTOGEN sheet: {char_sheet}")
                            # Print the created character sheet and its secondary stats file
                            try:
                                txt = char_sheet.read_text(encoding='utf-8', errors='replace')
                                print('\n--- FILE: ' + str(char_sheet) + ' ---')
                                print('```')
                                print(txt.rstrip())
                                print('```')
                            except Exception:
                                pass
                            # attempt to print secondary stats file if present
                            try:
                                sec = pc_folder / f"{nm} secondary stats.md"
                                if sec.exists():
                                    stxt = sec.read_text(encoding='utf-8', errors='replace')
                                    print('\n--- FILE: ' + str(sec) + ' ---')
                                    print('```')
                                    print(stxt.rstrip())
                                    print('```')
                            except Exception:
                                pass
                        except Exception:
                            pass
                    except Exception:
                        pass
                if created_any and PCS_DEBUG:
                    print("[pcs-debug] AUTOGEN sheets created for pcs_input.md entries")
            except Exception:
                pass

            # Now update character sheets (some may have just been created)
            try:
                print("Orchestration: updating character sheets (update_char.py --all)...")
                subprocess.run([sys.executable, str(script_dir.joinpath('update_char.py')), '--all'], check=False)
            except Exception as e:
                print(f"Warning: failed to run update_char.py --all: {e}")

            # Also generate graphs for the top-level Player Root folder (if present)
            try:
                player_root_dir = script_dir.joinpath('Player Root')
                if player_root_dir.exists() and player_root_dir.is_dir():
                    print(f"Generating graphs for Player Root -> root {player_root_dir}")
                    try:
                        make_graphs(root, outdir, exts=exts, excludes=excludes, mode=args.mode, embed_js=args.embed, child_spread=args.child_spread, spread_growth=args.spread_growth, recolor_list=args.recolor, verbose=args.verbose, pc_subtree=player_root_dir, pc_name='Player Root', include_gitignored=args.include_gitignored, materialize_unresolved=args.materialize_unresolved)
                        try:
                            generated_names.append('Player Root')
                        except Exception:
                            pass
                    except Exception as e:
                        print(f"Could not generate Player Root graphs: {e}")
            except Exception:
                pass

            for child in sorted(pcs_root.iterdir()):
                if not child.is_dir():
                    continue
                name = child.name
                # Skip folders whose names are punctuation-only (e.g. '-------')
                if re.fullmatch(r'[^A-Za-z0-9]+', name):
                    if PCS_DEBUG:
                        print(f"[pcs-debug] skipping punctuation-only pc folder during iteration: '{name}'")
                    continue
                pc_folder = child
                print(f"Generating graphs for PC: {name} -> root {pc_folder}")
                char_sheet = pc_folder / f"{name} Character Sheet.md"
                allowed = None
                # If the character sheet is missing or incomplete, create the
                # full template (when verbose). If present and complete, parse it.
                should_create2 = False
                if not char_sheet.exists() and args.verbose:
                    should_create2 = True
                elif char_sheet.exists() and args.verbose:
                    try:
                        txt = char_sheet.read_text(encoding='utf-8', errors='replace')
                        if '## Core Stats' not in txt or '[[Airbending Level]]' not in txt:
                            should_create2 = True
                    except Exception:
                        should_create2 = True

                # Primary stat defaults: prefer values from pcs_input.md, fallback to zeros
                primary_stats = {'Strength':0,'Dexterity':0,'Constitution':0,'Intelligence':0,'Wisdom':0,'Charisma':0}
                if pcs_stats and name in pcs_stats:
                    primary_stats.update(pcs_stats.get(name, {}))

                if should_create2:
                    try:
                        print(f"  Character sheet missing or incomplete; creating: {char_sheet}")
                        folder = pc_folder
                        folder.mkdir(parents=True, exist_ok=True)
                        lines = []
                        # mark autogenerated files so later runs can detect them
                        lines.append(AUTOGEN_MARKER)
                        lines.append(f"**Name:** {name}")
                        lines.append("")
                        lines.append('## Core Stats')
                        lines.append('| Stat | Value |')
                        lines.append('| ---- | ----: |')
                        for s in ('Strength','Dexterity','Constitution','Intelligence','Wisdom','Charisma'):
                            val = primary_stats.get(s, 0)
                            lines.append(f'| {s} | {val} |')
                        lines.append('')
                        lines.append('## Bending Levels')
                        lines.append('| Element                 | Level | Notes                  | Auto |')
                        lines.append('| ----------------------- | ----- | ---------------------- | ---- |')
                        lines.append('| [[Airbending Level]]    | 0     |                        | Y    |')
                        lines.append('| [[Waterbending Level]]  | 0     |                        | Y    |')
                        lines.append('| [[Earthbending Level]]  | 0     |                        | Y    |')
                        lines.append('| [[Firebending Level]]   | 0     |                        | Y    |')
                        lines.append('| [[Spiritbending Level]] | 0     |                        | Y    |')
                        try:
                            char_sheet.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                            print(f'  Created PC folder and character sheet: {char_sheet}')
                            # print created sheet + secondary stats in monospace
                            try:
                                txt = char_sheet.read_text(encoding='utf-8', errors='replace')
                                print('\n--- FILE: ' + str(char_sheet) + ' ---')
                                print('```')
                                print(txt.rstrip())
                                print('```')
                            except Exception:
                                pass
                            try:
                                sec = pc_folder / f"{name} secondary stats.md"
                                if sec.exists():
                                    stxt = sec.read_text(encoding='utf-8', errors='replace')
                                    print('\n--- FILE: ' + str(sec) + ' ---')
                                    print('```')
                                    print(stxt.rstrip())
                                    print('```')
                            except Exception:
                                pass
                        except Exception as e:
                            print(f'  Could not create character sheet {char_sheet}: {e}')
                    except Exception as e:
                        print(f"  Could not create character sheet {char_sheet}: {e}")

                if char_sheet.exists():
                    try:
                        allowed = parse_bending_levels_from_sheet(char_sheet)
                        print(f"  Parsed bending levels: {allowed}")
                        # Prefer pcs_input.md values when present for this PC.
                        try:
                            # Unconditionally prefer pcs_input.md when a row exists
                            # for this PC. Use whatever values are present (including 0).
                            if pcs_levels and name in pcs_levels:
                                pcs_allowed = pcs_levels.get(name)
                                if pcs_allowed is not None:
                                    allowed = pcs_allowed
                                    print(f"  Overriding with pcs_input.md levels (authoritative): {allowed}")
                        except Exception:
                            pass
                    except Exception as e:
                        print(f"  Could not parse character sheet {char_sheet}: {e}")

                make_graphs(root, outdir, exts=exts, excludes=excludes, mode=args.mode, embed_js=args.embed, child_spread=args.child_spread, spread_growth=args.spread_growth, recolor_list=args.recolor, allowed_elements_levels=allowed, verbose=args.verbose, pc_subtree=pc_folder, pc_name=name, include_gitignored=args.include_gitignored, materialize_unresolved=args.materialize_unresolved)
        return

    # Default: generate graphs for the cwd root
    make_graphs(root, outdir, exts=exts, excludes=excludes, mode=args.mode, embed_js=args.embed, child_spread=args.child_spread, spread_growth=args.spread_growth, recolor_list=args.recolor, include_gitignored=args.include_gitignored, materialize_unresolved=args.materialize_unresolved)


if __name__ == '__main__':
    main()
