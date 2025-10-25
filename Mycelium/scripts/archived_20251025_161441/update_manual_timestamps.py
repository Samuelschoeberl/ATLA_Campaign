#!/usr/bin/env python3
"""Update 'Last updated: YYYY-MM-DD' header in MANUALS/*.md for changed files.

Usage:
  - Run manually to stamp all manuals: `python3 scripts/update_manual_timestamps.py --all`
  - Or run from a pre-commit hook to update only staged manuals.

Behavior:
  - If `--all` is passed, update every markdown file in MANUALS.
  - Otherwise, attempt to read `git` staged file list and only update staged manuals.
  - Updates are written in-place.

This script is intentionally small and dependency-free.
"""
from __future__ import annotations
import argparse
import datetime
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
MANUALS_DIR = ROOT / "MANUALS"
TODAY = datetime.date.today().isoformat()


def get_staged_files() -> list[Path]:
    try:
        out = subprocess.check_output(["git", "diff", "--name-only", "--cached"], cwd=ROOT, text=True)
    except Exception:
        return []
    files = [ROOT / p.strip() for p in out.splitlines() if p.strip()]
    return files


def update_file(path: Path) -> bool:
    """Return True if file was modified."""
    if not path.exists() or not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines:
        return False
    # If first non-empty line starts with 'Last updated:' replace it.
    for i, ln in enumerate(lines[:3]):
        if ln.strip():
            idx = i
            break
    else:
        idx = 0
    if lines[idx].startswith("Last updated:"):
        if lines[idx].strip() == f"Last updated: {TODAY}":
            return False
        lines[idx] = f"Last updated: {TODAY}"
    else:
        # insert at top
        lines.insert(0, "")
        lines.insert(0, f"Last updated: {TODAY}")
        lines.insert(0, "")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--all", action="store_true", help="Update all manuals")
    args = p.parse_args()

    if args.all:
        targets = list(MANUALS_DIR.glob("*.md"))
    else:
        staged = get_staged_files()
        targets = [p for p in staged if p.is_file() and p.parent == MANUALS_DIR and p.suffix == ".md"]

    if not targets:
        print("No manual files to update.")
        return 0

    changed = []
    for t in targets:
        try:
            if update_file(t):
                changed.append(t.name)
        except Exception as e:
            print(f"Failed to update {t}: {e}")
    if changed:
        print("Updated:", ", ".join(changed))
    else:
        print("No changes needed.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
