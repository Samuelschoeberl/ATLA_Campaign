#!/usr/bin/env python3
"""Append a tag to all markdown files under a folder.

This is a safe helper that adds a single tag (e.g. `#fire`) to every
markdown file under a folder (recursively by default). It supports a
`--dry-run` mode that shows what would change without writing files.

Usage:
  python3 Mycelium/scripts/python/tag_folder.py --folder "Player Root/Rules/Bending Rules" --tag fire --dry-run

The `--tag` value may be provided without the leading '#'.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import sys

ROOT = Path('.').resolve()


def main() -> None:
    p = argparse.ArgumentParser(description='Append a tag to all files under a folder')
    p.add_argument('--folder', '-f', required=True, help='Folder containing files (repo-relative or absolute)')
    p.add_argument('--tag', '-t', required=True, help='Tag to append (with or without leading #)')
    p.add_argument('--pattern', help='Glob pattern to match files (default **/*.md)', default='**/*.md')
    p.add_argument('--recursive', action='store_true', default=True, help='Search recursively (default: true)')
    p.add_argument('--no-recursive', dest='recursive', action='store_false', help='Do not search recursively')
    p.add_argument('--dry-run', action='store_true', help='Show changes without writing')
    args = p.parse_args()

    folder = Path(args.folder)
    if not folder.is_absolute():
        folder = ROOT.joinpath(folder)
    if not folder.exists():
        # If the provided path doesn't exist, treat the argument as a
        # folder name and search the repository for the first directory
        # whose name matches (case-insensitive). This allows passing a
        # simple folder name like "Level1" instead of the full path.
        target_name = Path(args.folder).name
        found = None
        try:
            for p in ROOT.rglob('*'):
                if p.is_dir() and p.name.lower() == target_name.lower():
                    found = p
                    break
        except Exception:
            found = None
        if found:
            folder = found
            print(f'Using first matching folder in repo: {folder.relative_to(ROOT)}')
        else:
            print('ERROR: folder not found:', folder)
            sys.exit(1)

    tag = args.tag.strip()
    if not tag.startswith('#'):
        tag = '#' + tag

    glob_pat = args.pattern if args.recursive else args.pattern.split('/')[-1]
    files = sorted(folder.glob(glob_pat))
    if not files:
        print('No files matched under', folder)
        return

    added = 0
    skipped = 0
    for f in files:
        if not f.is_file():
            continue
        try:
            txt = f.read_text(encoding='utf-8')
        except Exception:
            print('Could not read', f)
            continue
        # skip if tag already present anywhere
        if tag.lower() in txt.lower():
            skipped += 1
            continue
        if args.dry_run:
            print('[DRY] would add', tag, 'to', f.relative_to(ROOT))
            added += 1
            continue
        # append tag as a newline at the end
        if not txt.endswith('\n'):
            txt += '\n'
        txt += tag + '\n'
        try:
            f.write_text(txt, encoding='utf-8')
            print('Added', tag, 'to', f.relative_to(ROOT))
            added += 1
        except Exception as e:
            print('Failed writing', f, e)
    print(f'Done. added={added} skipped={skipped}')


if __name__ == '__main__':
    main()
