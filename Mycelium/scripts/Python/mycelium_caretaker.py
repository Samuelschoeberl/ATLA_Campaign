#!/usr/bin/env python3
"""Root-level wrapper for Mycelium Caretaker consolidation functions.

This mirrors the in-repo script at Mycelium/scripts/manuals/Mycelium Caretaker.py
but provides a convenient top-level CLI like other `mycelium_*.py` files.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = Path(__file__).resolve().parent / 'Mycelium' / 'scripts' / 'manuals' / 'Mycelium Caretaker.py'


def _load_caretaker_module(path: Path):
    spec = importlib.util.spec_from_file_location('mycelium_caretaker_module', str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog='mycelium_caretaker')
    ap.add_argument('--consolidate-mycelium', action='store_true', help='Find duplicate .md names under Mycelium and propose/perform consolidation')
    ap.add_argument('--sort', action='store_true', help='When set with --consolidate-mycelium, actually perform the concatenation and remove duplicates')
    ap.add_argument('--dry-run', action='store_true', help='Alias for not applying changes (default behaviour when --sort is not present)')
    args = ap.parse_args(argv)

    if not SCRIPT_PATH.exists():
        print(f'Error: caretaker script not found at {SCRIPT_PATH}', file=sys.stderr)
        return 2

    if args.consolidate_mycelium:
        mod = _load_caretaker_module(SCRIPT_PATH)
        # call the function directly; matches original signature: (apply_changes: bool = False)
        apply_changes = bool(args.sort)
        return mod.consolidate_mycelium(apply_changes=apply_changes)

    ap.print_help()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
