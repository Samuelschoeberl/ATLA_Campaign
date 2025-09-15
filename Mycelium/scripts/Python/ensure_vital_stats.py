#!/usr/bin/env python3
"""Ensure Vital Stats table exists in Players Part/PCs/*/Character Sheet.md

Idempotent: if the sheet already contains a '## Vital Stats' header, it's left
unchanged. Otherwise a standard Vital Stats table is inserted after the
Bending Slots section (or near the end of the file).
"""
from pathlib import Path
import re
import sys


VITAL_BLOCK = [
    '## Vital Stats',
    '',
    '| Attribute | Value | Note | Auto |',
    '| --- | ---: | --- | ---- |',
    '| Max Hit Points | 0 |  | Y |',
    '| Evasion | 0 |  | Y |',
    '| Armor | 0 |  | Y |',
    '| Stress | 0 |  | Y |',
    '',
]


def ensure_vital(path: Path) -> bool:
    try:
        txt = path.read_text(encoding='utf-8')
    except Exception:
        return False
    lines = txt.splitlines()
    for ln in lines:
        if ln.strip().lower().startswith('## vital stats'):
            return False

    # find insertion point: after a '## Bending Slots' section if present,
    # otherwise after the last top-level header, otherwise at EOF.
    insert_at = len(lines)
    for i, ln in enumerate(lines):
        if ln.strip().lower().startswith('## bending slots'):
            # find end of that block (next '## ' header or blank line after table)
            j = i + 1
            seen_table = False
            while j < len(lines):
                l2 = lines[j]
                if '|' in l2:
                    seen_table = True
                if l2.strip().startswith('## ') and seen_table:
                    insert_at = j
                    break
                j += 1
            if insert_at == len(lines):
                insert_at = j
            break

    new_lines = lines[:insert_at] + VITAL_BLOCK + lines[insert_at:]
    try:
        path.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
        return True
    except Exception:
        return False


def main():
    pcs_root = Path('Players Part/PCs')
    if not pcs_root.exists():
        print('Players Part/PCs not found; nothing to do')
        return 2
    changed = []
    for folder in pcs_root.iterdir():
        if not folder.is_dir():
            continue
        cs = folder / 'Character Sheet.md'
        if cs.exists():
            if ensure_vital(cs):
                changed.append(str(cs))
    if changed:
        print('Inserted Vital Stats into:')
        for p in changed:
            print(' -', p)
    else:
        print('No changes (all sheets already had Vital Stats)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
