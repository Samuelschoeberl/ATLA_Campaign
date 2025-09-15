#!/usr/bin/env python3
"""Sort files in Mycelium/unsorted into mushroom folders.

Behavior:
- Parses Mycelium/Mycelium.md for the [[Mushrooms]] value (comma-separated list).
- For each file in Mycelium/unsorted, finds the first mushroom whose name appears in the filename
  (case-insensitive, alphanumeric match) and moves the file into Mycelium/<Mushroom>/.
- Creates mushroom folders if they don't exist.
"""
from pathlib import Path
import re
import sys

ROOT = Path('.').resolve()
UNSORTED = ROOT / 'Mycelium' / 'unsorted'
MYCELIUM_MD = ROOT / 'Mycelium' / 'Mycelium.md'


def parse_mushrooms() -> list[str]:
    if not MYCELIUM_MD.exists():
        return []
    txt = MYCELIUM_MD.read_text(encoding='utf-8')
    # find line with [[Mushrooms]] in table
    for ln in txt.splitlines():
        if '[[Mushrooms]]' in ln:
            # attempt to parse pipe-separated row
            parts = [p.strip() for p in ln.split('|') if p.strip()]
            if len(parts) >= 2:
                val = parts[1]
                # split by commas
                items = [i.strip().strip('/') for i in val.split(',') if i.strip()]
                return items
    return []


def normalize(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '', s.lower())


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Sort files in Mycelium/unsorted into mushroom folders')
    ap.add_argument('--backup', action='store_true', help='Place moved files under backups/ instead of Mycelium/<Mushroom>/')
    args = ap.parse_args()

    mush = parse_mushrooms()
    if not mush:
        print('No mushrooms found in Mycelium.md; nothing to do.')
        return 1
    norms = [(m, normalize(m)) for m in mush]
    print('Mushrooms:', mush)

    if not UNSORTED.exists():
        print('No unsorted folder found; nothing to do.')
        return 0

    moved = 0
    for p in sorted(UNSORTED.iterdir()):
        if not p.is_file():
            continue
        name = p.name
        nname = normalize(name)
        target_dir = None
        for m, nm in norms:
            if nm and nm in nname:
                target_dir = ROOT / 'Mycelium' / m
                break
        if target_dir:
            # when backup requested, place the moved file under backups/<Mycelium>/<Mushroom>/
            if args.backup:
                backup_dir = ROOT / 'backups' / 'Mycelium' / target_dir.name
                target_dir = backup_dir
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / p.name
            i = 1
            while target.exists():
                target = target_dir / f"{p.stem}_{i}{p.suffix}"
                i += 1
            p.rename(target)
            print(f"moved: {p} -> {target}")
            moved += 1
    print(f"Done. moved={moved}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
