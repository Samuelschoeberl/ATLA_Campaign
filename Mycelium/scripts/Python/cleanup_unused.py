#!/usr/bin/env python3
"""Find top-level files/folders that are not referenced by any .py scripts.

Usage:
  python3 scripts/cleanup_unused.py --root /path/to/repo [--apply] [--archive-dir archive/cleanup] [--preserve NAME]

By default this is a dry-run that prints candidates. Use --apply to move candidates
into the timestamped archive directory under the provided --archive-dir.

The heuristic is conservative: we only consider top-level entries (children of root)
and look for textual mentions of the entry name or relative path inside all .py files.
If zero .py files contain a mention, the entry is considered unused.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List


def gather_py_sources(root: Path) -> List[Path]:
    return [p for p in root.rglob('*.py') if 'archive' not in p.parts and '.git' not in p.parts]


def top_level_entries(root: Path) -> List[Path]:
    return [p for p in sorted(root.iterdir())]


def entry_referenced(entry: Path, py_files: List[Path]) -> bool:
    name = entry.name
    rel = str(entry.relative_to(entry.anchor)) if entry.is_absolute() else str(entry)
    # Candidate tokens to search for
    tokens = {name, rel, rel.replace(' ', ''), rel.replace(' ', '_')}
    # Also search for path fragments (folder/filename)
    if entry.is_dir():
        tokens.add(f"{name}/")
    # read files and search
    for f in py_files:
        try:
            txt = f.read_text(encoding='utf8', errors='ignore')
        except Exception:
            continue
        for t in tokens:
            if t and t in txt:
                return True
    return False


def preview_file(p: Path, n: int = 200) -> str:
    try:
        return p.read_text(encoding='utf8', errors='ignore')[:n]
    except Exception:
        return ''


def main() -> int:
    ap = argparse.ArgumentParser(description='Find and optionally archive top-level entries not referenced by any .py files')
    ap.add_argument('--root', required=False, default='.', help='Repository root')
    ap.add_argument('--apply', action='store_true', help='Move unused entries into archive (instead of dry-run)')
    ap.add_argument('--archive-dir', default='archive/cleanup', help='Base archive directory (inside repo)')
    ap.add_argument('--preserve', action='append', default=[], help='Top-level names to always preserve')
    ap.add_argument('--aggressive', action='store_true', help='Be more aggressive: reduce the built-in preserve defaults')
    args = ap.parse_args()

    root = Path(args.root).expanduser()
    if not root.exists():
        print(f"[error] root not found: {root}")
        return 2

    py_files = gather_py_sources(root)
    print(f"Scanning {len(py_files)} .py files for references...")

    # default conservative preserve set
    preserve_defaults = {'Mycelium', 'Players Part', 'Player Root', 'backups', 'archive', '.git', 'scripts', 'WikiFileSystemManager', 'config'}
    # when aggressive is requested, shrink the defaults to a minimal safe set
    if args.aggressive:
        preserve_defaults = {'Mycelium', 'archive', '.git', 'scripts'}
    preserve = set(preserve_defaults) | set(args.preserve)

    candidates = []
    for ent in top_level_entries(root):
        if ent.name in preserve:
            # skip preserved
            continue
        # skip obvious ephemeral entries
        if ent.name.startswith('.'):
            continue
        # skip if ent is the archive dir
        if str(ent).startswith(args.archive_dir):
            continue
        referenced = entry_referenced(ent, py_files)
        if not referenced:
            candidates.append(ent)

    print(f"Found {len(candidates)} unused top-level entries (dry-run={not args.apply}):")
    for c in candidates:
        if c.is_dir():
            cnt = sum(1 for _ in c.rglob('*'))
            print(f" - DIR: {c} ({cnt} items)")
        else:
            print(f" - FILE: {c} ({c.stat().st_size} bytes)")

    if not candidates:
        print('Nothing to do.')
        return 0

    if not args.apply:
        print('\nRun with --apply to move these entries into the archive directory.')
        return 0

    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    archive_root = root.joinpath(args.archive_dir).joinpath(ts)
    archive_root.mkdir(parents=True, exist_ok=True)

    moved = []
    for c in candidates:
        dest = archive_root.joinpath(c.name)
        try:
            shutil.move(str(c), str(dest))
            moved.append((c, dest))
            print(f"[moved] {c} -> {dest}")
            # preview first 200 chars of text files
            if dest.is_file() and dest.suffix in {'.md', '.txt', '.json', '.py'}:
                print('[preview] ' + preview_file(dest, 200))
        except Exception as e:
            print(f"[error] moving {c}: {e}")

    report = {'timestamp': ts, 'moved': [str(d[1]) for d in moved], 'count': len(moved)}
    report_path = archive_root.joinpath('report.json')
    report_path.write_text(json.dumps(report, indent=2))
    print(f"Archive completed: {archive_root} (moved {len(moved)} items). Report at {report_path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
