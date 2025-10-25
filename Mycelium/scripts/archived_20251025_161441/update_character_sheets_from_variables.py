#!/usr/bin/env python3
"""Update character sheets so they include all #character_stat variables found in each PC's variable folder.

For each folder `Player Root/PCs/<Name>/<Name>_variable/` this script will:
 - scan all `*.md` files and select those containing `#character_stat` (case-insensitive)
 - extract the first non-tag line from the fenced block as the value
 - detect if the file contains `#primary_stat` or `#secondary_stat` and mark origin
 - rewrite `<Name> character sheet.md` to include a Stats table with Variable | Value | Origin

This is safe and idempotent.
"""
from __future__ import annotations
from pathlib import Path
import re
from typing import List, Tuple

ROOT = Path('.').resolve()
PCS_ROOT = ROOT.joinpath('Player Root', 'PCs')


def extract_value_and_origin(text: str) -> Tuple[str, str]:
    low = text.lower()
    origin = ''
    if '#primary_stat' in low:
        origin = 'primary'
    if '#secondary_stat' in low:
        # secondary takes precedence if present
        origin = 'secondary'

    # try to extract content from first fenced code block
    m = re.search(r'```(?:[^\n]*)\n(.*?)\n```', text, flags=re.S)
    content = m.group(1) if m else text
    # split into lines and pick first non-empty non-tag line
    for ln in content.splitlines():
        ln2 = ln.strip()
        if not ln2:
            continue
        if ln2.startswith('#'):
            continue
        return ln2, origin
    # fallback: return empty string or a reasonable default
    return '', origin


def normalize_varname(filename: str, prefix: str) -> str:
    name = Path(filename).stem
    # remove prefix if present (case-insensitive)
    if name.lower().startswith(prefix.lower() + '_'):
        return name[len(prefix) + 1:]
    return name


def process_pc(pc_dir: Path) -> None:
    name = pc_dir.name
    mirror = pc_dir.joinpath(f"{name}_variable")
    if not mirror.exists() or not mirror.is_dir():
        return
    rows: List[Tuple[str, str, str]] = []  # var, value, origin
    for p in sorted(mirror.glob('*.md')):
        try:
            txt = p.read_text(encoding='utf-8')
        except Exception:
            continue
        if '#character_stat' not in txt.lower():
            continue
        val, origin = extract_value_and_origin(txt)
        var = normalize_varname(p.name, name)
        rows.append((var, val, origin))

    # write sheet
    sheet = pc_dir.joinpath(f"{name} character sheet.md")
    lines: List[str] = []
    lines.append(f'# {name} — Character Sheet')
    lines.append('')
    lines.append('## Stats')
    lines.append('')
    lines.append('| Variable | Value | Origin |')
    lines.append('|---|---:|:---:|')
    for var, val, origin in sorted(rows):
        lines.append(f'| {var} | {val} | {origin} |')
    lines.append('')
    sheet.write_text('\n'.join(lines), encoding='utf-8')


def main():
    if not PCS_ROOT.exists():
        print('PCs folder not found at', PCS_ROOT)
        return
    for child in sorted(PCS_ROOT.iterdir()):
        if not child.is_dir():
            continue
        process_pc(child)
        print('Updated sheet for', child.name)


if __name__ == '__main__':
    main()
