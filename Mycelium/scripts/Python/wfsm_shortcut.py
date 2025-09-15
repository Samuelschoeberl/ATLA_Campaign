#!/usr/bin/env python3
"""Tiny CLI wrapper around Mycelium.Wikigraphs.find_and_replace_in_named_subdirs

Usage examples:
  python wfsm_shortcut.py --name Air --find "Attack Roll" --replace "Air Attack Roll" --dry-run
  python wfsm_shortcut.py --name Fire --find "Attack Roll" --replace "Fire Attack Roll" --backup .bak
"""
from __future__ import annotations
from pathlib import Path
import argparse
import sys


def _ensure_repo_on_path():
    # file is at Mycelium/scripts/Python/, repo root is parents[3]
    repo_root = Path(__file__).resolve().parents[3]
    p = str(repo_root)
    if p not in sys.path:
        sys.path.insert(0, p)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Shortcut: run Wiki_File_System_Manager across all subdirs with a given name')
    parser.add_argument('--name', required=True, help='Directory name to search for (e.g. Air, Fire)')
    parser.add_argument('--find', required=True, help='Text to find')
    parser.add_argument('--replace', help='Replacement text (omit if using bracketing)')
    parser.add_argument('--ext', nargs='*', default=['.md'], help='File extensions to include (default: .md)')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing')
    parser.add_argument('--backup', default=None, help='Backup suffix to use when writing (e.g. .bak)')
    parser.add_argument('--python-exe', default=None, help='Python executable to use when invoking the manager (default: this interpreter)')
    args = parser.parse_args(argv)

    _ensure_repo_on_path()
    try:
        from Mycelium import Wikigraphs
    except Exception as e:
        print('ERROR: could not import Mycelium.Wikigraphs:', e, file=sys.stderr)
        return 3

    res = Wikigraphs.find_and_replace_in_named_subdirs(
        root='.',
        dir_name=args.name,
        find=args.find,
        replace=args.replace,
        ext=tuple(args.ext) if args.ext else ('.md',),
        dry_run=bool(args.dry_run),
        backup=args.backup,
        python_exe=args.python_exe,
    )

    # print manager stdout/stderr for user inspection
    if res.get('stdout'):
        print(res['stdout'])
    if res.get('stderr'):
        print(res['stderr'], file=sys.stderr)

    return int(res.get('returncode', 1) or 0)


if __name__ == '__main__':
    raise SystemExit(main())
