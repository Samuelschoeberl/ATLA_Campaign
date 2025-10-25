#!/usr/bin/env python3
"""
Resiliance.py — lightweight content checker for Character Sheet variable usage.

Usage:
  python3 Resiliance.py --pc

Behavior (assumptions / contract):
- Scans the workspace for markdown files.
- Variable files are markdown files containing the tag "#Variable". Each variable file
  must include a markdown 2-column table (key | value) somewhere; the script parses
  the first table it finds in the file into key/value pairs.
- Character Sheet files are markdown files containing the tag "#Character Sheet".
- Character Sheets reference variables using double-curly tokens like: {{variablename}} or {{variablename.key}}
  (assumed format for this checker).
- When run with --pc, the script restricts Character Sheet checks to files under
  the "Player Root/PCs" directory (if present) and all files that contain the
  "#Character Sheet" tag.

Checks performed:
- All variable files have unique basenames (variablename.md). Duplicate basenames are reported.
- Each variable file contains a parsable 2-column table; otherwise it's reported.
- For each variable token in a Character Sheet, the script verifies there is exactly
  one matching variable file and (if a key is referenced) that the key exists in that variable file.

Exit code: 0 on success (no problems), 2 if problems were found.
"""

import argparse
import pathlib
import re
import sys
from typing import Dict, List, Optional, Tuple

ROOT = pathlib.Path('.').resolve()
# supported variable tags
VAR_TAG = '#Variable'
PRIMARY_TAG = '#Primary_variable'
SECONDARY_TAG = '#Secondary_variable'
CONFIG_TAG = '#config'
CONFIG_VAR_TAG = '#config_variable'
CS_TAG = '#Character Sheet'
TOKEN_RE = re.compile(r"\{\{\s*([A-Za-z0-9_\-]+)(?:\.([A-Za-z0-9_\-]+))?\s*\}\}")


def find_markdown_files(root: pathlib.Path) -> List[pathlib.Path]:
    from scripts.fsutil import iter_md_files
    return list(iter_md_files(root))


def file_contains_tag(path: pathlib.Path, tag: str) -> bool:
    try:
        text = path.read_text(encoding='utf-8')
    except Exception:
        return False
    return tag in text


def parse_first_table(path: pathlib.Path) -> Optional[Dict[str, str]]:
    """Parse the first markdown table with at least two columns into a dict.
    Table rows like: | key | value | ... will be parsed.
    Returns dict or None if no table found.
    """
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines()

    table_block = []
    in_table = False
    for ln in lines:
        if '|' in ln:
            # consider this a table row
            table_block.append(ln)
            in_table = True
        else:
            if in_table:
                break
    if not table_block:
        return None

    # Filter header/separator if present
    rows = []
    for row in table_block:
        # skip separator rows like |---|---|
        if re.match(r'^\s*\|?\s*-{2,}', row):
            continue
        # split by pipes
        parts = [p.strip() for p in row.strip().strip('|').split('|')]
        if len(parts) >= 2:
            rows.append(parts[:2])
    if not rows:
        return None

    # If first row looks like header (contains letters 'key'/'value'), drop it
    if len(rows) > 1:
        hdr = [c.lower() for c in rows[0]]
        if ('key' in hdr[0] or 'name' in hdr[0] or 'variable' in hdr[0]) and ('value' in hdr[1] or 'default' in hdr[1]):
            rows = rows[1:]

    result = {}
    for r in rows:
        k = r[0].strip().strip('`"')
        v = r[1].strip().strip('`"')
        if k:
            result[k] = v
    return result


def collect_variable_files(root: pathlib.Path) -> Tuple[Dict[str, List[pathlib.Path]], Dict[pathlib.Path, Optional[Dict[str, str]]], Dict[pathlib.Path, str]]:
    """Return mapping basename->list(paths), per-path parsed table (or None), and per-path tag."""
    var_files_by_base: Dict[str, List[pathlib.Path]] = {}
    parsed_tables: Dict[pathlib.Path, Optional[Dict[str, str]]] = {}
    var_tag_by_path: Dict[pathlib.Path, str] = {}

    tags = [VAR_TAG, PRIMARY_TAG, SECONDARY_TAG, CONFIG_TAG, CONFIG_VAR_TAG]

    for p in find_markdown_files(root):
        for t in tags:
            if file_contains_tag(p, t):
                base = p.stem
                var_files_by_base.setdefault(base, []).append(p)
                parsed_tables[p] = parse_first_table(p)
                var_tag_by_path[p] = t
                break
    return var_files_by_base, parsed_tables, var_tag_by_path


def collect_character_sheets(root: pathlib.Path, pc_only: bool) -> List[pathlib.Path]:
    out = []
    for p in find_markdown_files(root):
        if file_contains_tag(p, CS_TAG):
            if pc_only:
                # require 'Player Root/PCs' in path parts, but be permissive
                parts = str(p).split('/')
                if 'Player Root' in parts and 'PCs' in parts:
                    out.append(p)
            else:
                out.append(p)
    return out


def extract_tokens_from_sheet(path: pathlib.Path) -> List[Tuple[str, Optional[str]]]:
    text = path.read_text(encoding='utf-8')
    return TOKEN_RE.findall(text)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Resiliance — check Character Sheet variable usage')
    ap.add_argument('--pc', action='store_true', help='Only check Player PC Character Sheets (under Player Root/PCs)')
    args = ap.parse_args(argv)

    pc_only = args.pc

    print(f"Scanning repository at: {ROOT}")
    var_map, parsed_tables, var_tag_by_path = collect_variable_files(ROOT)

    problems = 0

    # Report duplicates
    dupes = {k: v for k, v in var_map.items() if len(v) > 1}
    if dupes:
        print('\nDuplicate variable filenames detected (same basename, multiple files):')
        for base, paths in dupes.items():
            print(f"  {base}.md:")
            for p in paths:
                print(f"    - {p}")
        problems += len(dupes)
    else:
        print('\nNo duplicate variable filenames found.')

    # Report variable files missing/invalid table
    bad_tables = [p for p, tbl in parsed_tables.items() if tbl is None]
    if bad_tables:
        print('\nVariable files missing a 2-column markdown table or unparsable:')
        for p in bad_tables:
            tag = var_tag_by_path.get(p, '(unknown)')
            print(f"  - {p} (tag: {tag})")
        problems += len(bad_tables)
    else:
        print('\nAll variable files contain a parsable table.')

    # Character sheets
    sheets = collect_character_sheets(ROOT, pc_only=pc_only)
    print(f"\nFound {len(sheets)} Character Sheet file(s) to check (pc_only={pc_only}).")

    for s in sheets:
        tokens = extract_tokens_from_sheet(s)
        if not tokens:
            print(f"\n[s] {s}: No variable tokens found (OK or maybe intentional).")
            continue
        print(f"\nChecking {s} -> tokens found: {len(tokens)}")
        for tok in tokens:
            varname, key = tok
            # locate variable file
            paths = var_map.get(varname, [])
            if not paths:
                print(f"  - Missing variable file for token {{ {{ {varname}{'.'+key if key else ''} }} }} in {s}")
                problems += 1
                continue
            if len(paths) > 1:
                print(f"  - Ambiguous variable reference '{varname}' in {s}: multiple files match: {paths}")
                problems += 1
                continue
            # single path
            vf = paths[0]
            tbl = parsed_tables.get(vf)
            if tbl is None:
                print(f"  - Variable file {vf} has no parsable table (referenced by {s})")
                problems += 1
                continue
            if key:
                if key not in tbl:
                    print(f"  - Missing key '{key}' in variable file {vf} (referenced by {s})")
                    problems += 1
                else:
                    # OK - show resolved example mapping
                    print(f"  - OK: {varname}.{key} -> {tbl[key]}")
            else:
                print(f"  - OK: variable file exists for '{varname}' ({vf}), keys: {', '.join(tbl.keys())}")

    print('\nSummary:')
    if problems == 0:
        print('  No problems found.')
    else:
        print(f'  Problems found: {problems} (see output above).')

    sys.exit(0 if problems == 0 else 2)


if __name__ == '__main__':
    main()
