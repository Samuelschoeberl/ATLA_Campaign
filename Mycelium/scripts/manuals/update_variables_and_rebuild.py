#!/usr/bin/env python3
"""update_variables_and_rebuild.py

Pipeline helper:
- Read primary values from `pcs_input.md` for PCs.
- Scan the repo for variable files tagged as primary (#Primary_variable)
  and for variable files that *lack* the secondary tag (#Secondary_variable).
- For matching variable files, update the first 2-column markdown table's
  numeric values from the pcs_input row when a table key matches a pcs column.
- Optionally run the existing character-sheet pipeline (`update_char.py`) to
  recompute derived/secondary stats and rewrite Character Sheets.

Design notes / contract (inputs/outputs):
- Input: pcs_input.md (path configurable), repository markdown files.
- Output: variable files updated in-place (backed up with suffix), and
  optionally `update_char.py --sync` executed to regenerate sheets.

This script is intentionally verbose with debug comments so it's easy to
follow what it will change during a dry-run.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
import re
import shutil
from typing import Dict, List, Tuple, Optional

# Some constants matching the project's conventions (Resiliance.py)
PRIMARY_TAG = '#Primary_variable'
SECONDARY_TAG = '#Secondary_variable'
VAR_TAG = '#Variable'


def parse_pcs_input(pcs_path: Path) -> Tuple[List[str], Dict[str, Dict[str, int]]]:
    """Parse pcs_input.md and return (pc_names, per-pc dict of values).

    Returns:
      - list of PC names (in original case)
      - mapping pc_name_lower -> dict of column -> int

    Heuristics are permissive: header row is detected by a line containing
    'name' and '|' (markdown table), numeric cells parsed as ints.
    """
    if not pcs_path.exists():
        print(f"[warn] pcs_input not found at: {pcs_path}")
        return [], {}
    txt = pcs_path.read_text(encoding='utf-8')
    lines = [ln for ln in txt.splitlines()]
    header_idx = None
    for i, ln in enumerate(lines):
        if '|' in ln and 'name' in ln.lower():
            header_idx = i
            break
    if header_idx is None:
        # fallback: first table-like line
        for i, ln in enumerate(lines):
            if ln.strip().startswith('|'):
                header_idx = i
                break
    if header_idx is None:
        print('[warn] could not find header row in pcs_input.md')
        return [], {}

    header_parts = [p.strip() for p in lines[header_idx].strip().strip('|').split('|')]
    # determine data start (skip separator row)
    data_start = header_idx + 1
    if data_start < len(lines) and re.match(r"^\s*\|?\s*-+", lines[data_start]):
        data_start += 1

    pc_names: List[str] = []
    mapping: Dict[str, Dict[str, int]] = {}
    # normalize header labels to keys we can match against variable files
    norm_headers = [re.sub(r'[^A-Za-z0-9_]+', ' ', h).strip() for h in header_parts]

    for ln in lines[data_start:]:
        if '|' not in ln:
            continue
        parts = [p.strip() for p in ln.strip().strip('|').split('|')]
        if not parts:
            continue
        # try to find name column (first header that contains 'name')
        name_col = None
        for idx, h in enumerate(header_parts):
            if h and 'name' == h.strip().lower():
                name_col = idx
                break
        if name_col is None:
            name_col = 0
        if name_col >= len(parts):
            continue
        name = parts[name_col]
        if not name:
            continue
        pc_names.append(name)
        rowmap: Dict[str, int] = {}
        for idx, h in enumerate(header_parts):
            if not h:
                continue
            if idx >= len(parts):
                continue
            cell = parts[idx]
            # try integer parse
            m = re.search(r"(-?\d+)", cell)
            if not m:
                continue
            try:
                val = int(m.group(1))
            except Exception:
                continue
            hdr = h.strip()
            # common short names mapping
            if hdr.lower() in ('str','strength'):
                rowmap['STR'] = val
            elif hdr.lower() in ('dex','dexterity'):
                rowmap['DEX'] = val
            elif hdr.lower() in ('con','constitution'):
                rowmap['CON'] = val
            elif hdr.lower() in ('int','intelligence'):
                rowmap['INT'] = val
            elif hdr.lower() in ('wis','wisdom'):
                rowmap['WIS'] = val
            elif hdr.lower() in ('cha','charisma'):
                rowmap['CHA'] = val
            else:
                # keep header as-is and also a safe-name variant
                rowmap[hdr] = val
                safe = re.sub(r"[^0-9A-Za-z_]+", "_", hdr).strip('_')
                rowmap[safe] = val
        mapping[name.lower()] = rowmap

    return pc_names, mapping


def parse_first_table(text: str) -> Tuple[Optional[int], Optional[int], List[Tuple[str, str]]]:
    """Find the first contiguous markdown table in text and return
    (start_line_idx, end_line_idx, rows).

    rows is a list of (left, right) strings for each two-column row.
    Returns (None, None, []) when no table found.
    """
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if '|' in ln:
            start = i
            break
    if start is None:
        return None, None, []
    # gather until a blank line or a non-table line after table started
    table_lines = []
    for j in range(start, len(lines)):
        ln = lines[j]
        if '|' not in ln:
            if table_lines:
                break
            else:
                # skip leading non-table lines (shouldn't happen)
                continue
        table_lines.append(ln)

    rows: List[Tuple[str, str]] = []
    for row in table_lines:
        # naive two-column parse: take first two pipe-separated cells
        parts = [p.strip() for p in row.strip().strip('|').split('|')]
        if len(parts) < 2:
            continue
        left = parts[0]
        right = parts[1]
        # skip separator rows like ---
        if re.fullmatch(r"-+", left) or re.fullmatch(r"-+", right):
            continue
        rows.append((left, right))

    end = start + len(table_lines) if table_lines else start
    return start, end, rows


def replace_first_table(text: str, rows_new: List[Tuple[str, str]], start: int, end: int) -> str:
    """Replace the lines from start..end with a regenerated table from rows_new."""
    out_lines = text.splitlines()
    table_lines = []
    table_lines.append('| ' + ' | '.join(['Field', 'Value']) + ' |')
    table_lines.append('| --- | ---: |')
    for left, right in rows_new:
        table_lines.append(f'| {left} | {right} |')
    new = out_lines[:start] + table_lines + out_lines[end:]
    return '\n'.join(new) + '\n'


def update_variable_file(path: Path, pcs_map: Dict[str, Dict[str, int]], pcs_names: List[str], dry_run: bool = True, backup_suffix: str | None = '.bak', debug: bool = False) -> bool:
    """Update a single variable file using pcs_map when possible.

    Returns True if file would be (or was) modified.
    """
    if debug:
        print(f"[debug] Inspecting variable file: {path}")
    try:
        txt = path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"[error] failed to read {path}: {e}")
        return False

    start, end, rows = parse_first_table(txt)
    if start is None:
        if debug:
            print(f"[debug] No table found in {path}; skipping.")
        return False

    # Determine candidate PC name to use: try filename stem and parent folder
    stem = path.stem
    parent = path.parent.name
    candidates = [stem, parent]
    matched_pc = None
    for c in candidates:
        if not c:
            continue
        for nm in pcs_names:
            if c.strip().lower() == nm.strip().lower():
                matched_pc = nm
                break
        if matched_pc:
            break

    if not matched_pc:
        if debug:
            print(f"[debug] Could not match file {path} to any PC name; available pcs: {pcs_names[:6]}...")
        # If no PC match, still attempt to update rows by matching header keys to any pcs column
        perpc = None
    else:
        perpc = pcs_map.get(matched_pc.lower(), None)
        if debug:
            print(f"[debug] Matched {path} -> PC '{matched_pc}' with data keys: {list(perpc.keys()) if perpc else 'NONE'}")

    changed = False
    new_rows: List[Tuple[str, str]] = []
    for left, right in rows:
        key = left.strip()
        # normalize key variants to try matching
        key_variants = [key, key.title(), key.upper(), re.sub(r"[^0-9A-Za-z_]+", "_", key).strip('_')]
        updated_value = None
        if perpc:
            for kv in key_variants:
                if kv in perpc:
                    updated_value = str(perpc[kv])
                    break
            # also try short-code names for core stats (Strength -> STR)
            short_map = {'Strength': 'STR', 'Dexterity': 'DEX', 'Constitution': 'CON', 'Intelligence': 'INT', 'Wisdom': 'WIS', 'Charisma': 'CHA'}
            if updated_value is None and key in short_map and short_map[key] in perpc:
                updated_value = str(perpc[short_map[key]])

        # If no per-PC mapping available, try to pull a value from any PC's first row if the header matches
        if updated_value is None:
            # scan pcs_map for any column match and take the first non-zero value found
            for pc, pm in pcs_map.items():
                for kv in key_variants:
                    if kv in pm:
                        updated_value = str(pm[kv])
                        break
                if updated_value is not None:
                    break

        # If we found an updated value and it differs from the file, update
        cur_val = right.strip()
        if updated_value is not None:
            # compare numeric substrings to avoid changing comments
            cur_num = re.search(r"(-?\d+)", cur_val)
            new_num = re.search(r"(-?\d+)", updated_value)
            cur_str = cur_num.group(1) if cur_num else cur_val
            new_str = new_num.group(1) if new_num else updated_value
            if str(cur_str) != str(new_str):
                if debug:
                    print(f"[debug] Will update '{key}' in {path}: {cur_val} -> {new_str}")
                new_rows.append((left, new_str))
                changed = True
                continue
        # otherwise keep original
        new_rows.append((left, right))

    if not changed:
        if debug:
            print(f"[debug] No changes for {path}")
        return False

    # assemble new text and write (or dry-run)
    # static type-safety: ensure `end` is not None (parse_first_table returns
    # Optional[int], and some type-checkers won't infer that `end` is valid
    # just because `start` was checked above). If `end` is unexpectedly
    # None, skip this file to avoid corrupting it.
    if end is None:
        if debug:
            print(f"[debug] Unexpected missing table end index for {path}; skipping write")
        return False
    new_text = replace_first_table(txt, new_rows, start, end)
    if dry_run:
        print(f"[dry-run] would update: {path}")
        # preview the new text (first 200 chars)
        try:
            print('[preview]', new_text[:200] if new_text else '(empty)')
        except Exception:
            pass
        return True

    # write backup then write file
    if backup_suffix:
        bak = path.with_name(path.name + (backup_suffix or '.bak'))
        try:
            shutil.copy2(path, bak)
            if debug:
                print(f"[debug] Wrote backup: {bak}")
        except Exception as e:
            print(f"[warn] failed to write backup for {path}: {e}")
    try:
        path.write_text(new_text, encoding='utf-8')
        print(f"[wrote] {path}")
        try:
            print('[preview]', new_text[:200] if new_text else '(empty)')
        except Exception:
            pass
    except Exception as e:
        print(f"[error] failed to write {path}: {e}")
        return False

    return True


def scan_and_update(root: Path, pcs_input: Path, dry_run: bool = True, backup_suffix: str | None = '.bak', debug: bool = False) -> Tuple[int, int]:
    """Scan repository for variable files and update them.

    Returns (count_files_scanned, count_files_modified_or_would_modify)
    """
    pcs_names, pcs_map = parse_pcs_input(pcs_input)
    if debug:
        print(f"[debug] Parsed PCs: {pcs_names}")

    from Mycelium.fsutil import iter_md_files
    files = list(iter_md_files(root))
    scanned = 0
    modified = 0
    for p in files:
        scanned += 1
        try:
            txt = p.read_text(encoding='utf-8')
        except Exception:
            continue
        # skip files in backups/ or graphs/ to avoid noise
        if str(p).startswith('backups') or '/backups/' in str(p) or '/graphs/' in str(p):
            continue
        # select variable files we want to update:
        has_primary = PRIMARY_TAG in txt
        has_secondary = SECONDARY_TAG in txt
        has_var = VAR_TAG in txt
        # condition: either explicitly primary-tagged OR variable file without secondary tag
        if has_primary or (has_var and not has_secondary):
            if debug:
                print(f"[debug] Candidate variable file: {p} (primary={has_primary}, secondary={has_secondary})")
            ok = update_variable_file(p, pcs_map, pcs_names, dry_run=dry_run, backup_suffix=backup_suffix, debug=debug)
            if ok:
                modified += 1

    return scanned, modified


def run_update_char(sync_input: Path, debug: bool = False) -> int:
    """Invoke update_char.py --sync --input <sync_input> to regenerate sheets.

    Returns subprocess exit code.
    """
    script = Path('Mycelium') / 'helpers' / 'update_char.py'
    # fallback to repository root script if not found
    if not script.exists():
        script = Path('update_char.py')
    if not script.exists():
        print(f"[error] update_char.py not found at expected locations: Mycelium/helpers/update_char.py or update_char.py")
        return 2
    cmd = [sys.executable, str(script), '--sync', '--input', str(sync_input)]
    if debug:
        print(f"[debug] Running: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, check=False)
        return res.returncode
    except Exception as e:
        print(f"[error] failed to run update_char.py: {e}")
        return 3


def main(argv=None):
    p = argparse.ArgumentParser(description='Update primary variable files from pcs_input.md and optionally rebuild character sheets')
    p.add_argument('--pcs-input', default='pcs_input.md', help='Path to pcs_input.md')
    p.add_argument('--root', default='.', help='Repository root to scan')
    p.add_argument('--dry-run', action='store_true', default=True, help='Do not write files; just show planned changes (default ON)')
    p.add_argument('--apply', action='store_true', help='Actually write changes (overrides --dry-run)')
    p.add_argument('--init-templates', action='store_true', help='Create missing primary variable files from templates (dry-run by default)')
    p.add_argument('--create-sheets', action='store_true', help='Create default Character Sheet files for PCs when missing (uses templates; dry-run by default)')
    p.add_argument('--backup', default='.bak', help='Backup suffix to write before changing files (set to empty to disable)')
    p.add_argument('--rebuild', action='store_true', help='After updating variables, run update_char.py --sync to regenerate sheets')
    p.add_argument('--build-tag-summaries', action='store_true', help='Build per-tag backlink summaries (dry-run by default)')
    p.add_argument('--build-tag-outdir', default='Tag_Summaries', help='Output directory for tag summaries (relative to --root)')
    p.add_argument('--debug', action='store_true', help='Verbose debug prints and in-file comments')
    args = p.parse_args(argv)

    dry_run = not args.apply
    backup_suffix = args.backup if args.backup else None
    root = Path(args.root)
    pcs_input = Path(args.pcs_input)

    if args.debug:
        print(f"[debug] Starting scan root={root}, pcs_input={pcs_input}, dry_run={dry_run}, backup={backup_suffix}")

    # Optionally initialize template-based primary variable files for PCs
    if args.init_templates:
        try:
            from Mycelium.create_from_template import create_from_template
        except Exception:
            create_from_template = None
        pcs_names, _ = parse_pcs_input(pcs_input)
        created = 0
        for nm in pcs_names:
            # derive a typical destination path under the provided root
            dest = Path(root).joinpath('Players Part/PCs') / nm / f"{nm} Variable.md"
            if dest.exists():
                continue
            if create_from_template is None:
                print('[warn] create_from_template helper not available; cannot init templates')
                break
            try:
                if dry_run:
                    print(f"[dry-run] would create template for {nm} -> {dest}")
                    # show rendered preview
                    try:
                        from Mycelium.create_from_template import render_template, list_templates
                        templates = list_templates()
                        if 'Primary_variable.md' in templates:
                            txt = render_template(templates['Primary_variable.md'], {'PC': nm})
                            print('[preview]', txt[:200])
                    except Exception:
                        pass
                else:
                    create_from_template('Primary_variable.md', dest, {'PC': nm}, overwrite=False)
                    print(f"[wrote] {dest}")
                    created += 1
            except Exception as e:
                print(f"[error] failed to create template for {nm}: {e}")
        if dry_run:
            print('[init-templates] dry-run mode: no files were written')
        else:
            print(f'[init-templates] created {created} files')

    # Optionally create Character Sheet files for PCs
    if args.create_sheets:
        try:
            from Mycelium.create_from_template import create_from_template
        except Exception:
            create_from_template = None
        pcs_names, _ = parse_pcs_input(pcs_input)
        created_sheets = 0
        for nm in pcs_names:
            dest = Path(root).joinpath('Players Part/PCs') / nm / 'Character Sheet.md'
            # fallback local filename under root
            local_dest = Path(root).joinpath(f"{nm} Character Sheet.md")
            if dest.exists() or local_dest.exists():
                continue
            if create_from_template is None:
                print('[warn] create_from_template helper not available; cannot create character sheets')
                break
            try:
                if dry_run:
                    print(f"[dry-run] would create Character Sheet for {nm} -> {dest}")
                    try:
                        from Mycelium.create_from_template import render_template, list_templates
                        templates = list_templates()
                        if 'Character_Sheet.md' in templates:
                            txt = render_template(templates['Character_Sheet.md'], {'PC': nm})
                            print('[preview]', txt[:200])
                    except Exception:
                        pass
                else:
                    create_from_template('Character_Sheet.md', dest, {'PC': nm}, overwrite=False)
                    print(f"[wrote] {dest}")
                    created_sheets += 1
            except Exception as e:
                print(f"[error] failed to create Character Sheet for {nm}: {e}")
        if dry_run:
            print('[create-sheets] dry-run mode: no files were written')
        else:
            print(f'[create-sheets] created {created_sheets} character sheets')

    # Optionally build per-tag backlink summary files
    if args.build_tag_summaries:
        try:
            from Mycelium.scripts.manuals import build_tag_backlinks
        except Exception:
            build_tag_backlinks = None
        if build_tag_backlinks is None:
            print('[warn] build_tag_backlinks not available; cannot build tag summaries')
        else:
            outdir = args.build_tag_outdir
            # call high level functions directly to control apply flag and root
            tags = build_tag_backlinks.build_tag_index(root)
            apply_flag = not dry_run
            build_tag_backlinks.write_tag_summaries(root, root.joinpath(outdir), tags, apply=apply_flag)

    scanned, modified = scan_and_update(root, pcs_input, dry_run=dry_run, backup_suffix=backup_suffix, debug=args.debug)
    print(f"Scanned {scanned} files; candidate variable files changed (or would change): {modified}")

    if args.rebuild:
        if dry_run:
            print('[dry-run] rebuild requested; would run update_char.py --sync --input', pcs_input)
        else:
            code = run_update_char(pcs_input, debug=args.debug)
            if code == 0:
                print('Rebuild (update_char.py --sync) completed successfully.')
            else:
                print('Rebuild returned non-zero exit code:', code)


if __name__ == '__main__':
    try:
        from Mycelium.cli_timer import run_with_timer
    except Exception:
        from cli_timer import run_with_timer
    run_with_timer(main)
