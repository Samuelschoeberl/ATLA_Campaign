#!/usr/bin/env python3
"""Create an aggregated folder named <original>_mushroom/ at the repo root
by copying a source directory while skipping files matched by the repo
`.gitignore` (so the resulting folder is safe to add to git).

Usage examples:
        python3 scripts/aggregate_mycelium.py Mycelium/variable/Root.md
  python3 scripts/aggregate_mycelium.py Mycelium/ --force --git-add

The script will create a directory named <basename>_mushroom at the git
repository root (determined with `git rev-parse --show-toplevel`). Files
that are ignored by git (per `git check-ignore`) are skipped. Use
`--dry-run` to preview actions.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path | None:
    try:
        p = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                           cwd=str(start),
                           stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL,
                           check=True,
                           text=True)
        return Path(p.stdout.strip())
    except subprocess.CalledProcessError:
        return None


def is_ignored_by_git(path: Path, repo_root: Path) -> bool:
    """Return True if git would ignore the given path (relative to repo_root).

    Falls back to False (not ignored) if git is unavailable or the check
    can't be performed.
    """
    try:
        rel = os.path.relpath(str(path), str(repo_root))
        # git check-ignore returns 0 if ignored, 1 if not ignored, 128 on error
        r = subprocess.run(["git", "check-ignore", "--quiet", rel],
                           cwd=str(repo_root))
        return r.returncode == 0
    except Exception:
        # If anything goes wrong, be conservative and treat file as not ignored
        return False


def copy_tree_filtered(src: Path, dest: Path, repo_root: Path, dry_run: bool):
    copied = 0
    skipped = 0
    for root, dirs, files in os.walk(src):
        root_path = Path(root)
        rel_dir = root_path.relative_to(src)
        target_dir = dest.joinpath(rel_dir)
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        for f in files:
            src_file = root_path / f
            # Determine whether git ignores this path
            try:
                ignored = is_ignored_by_git(src_file, repo_root)
            except Exception:
                ignored = False

            if ignored:
                skipped += 1
                print(f"SKIP (ignored): {src_file}")
                continue

            dest_file = target_dir / f
            if dry_run:
                print(f"DRY  copy: {src_file} -> {dest_file}")
            else:
                shutil.copy2(src_file, dest_file)
                print(f"COPY: {src_file} -> {dest_file}")
            copied += 1

    return copied, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate a folder into a repository-root '<name>_mushroom' while skipping git-ignored files.")
    parser.add_argument("source", help="Source file or directory to aggregate")
    parser.add_argument("--dest", help="Optional destination directory name (basename). If omitted, uses <source_basename>_mushroom")
    parser.add_argument("--force", action="store_true", help="Remove existing destination before creating")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without copying")
    parser.add_argument("--git-add", action="store_true", help="Run `git add` on the created folder (optional)")
    args = parser.parse_args(argv)

    src = Path(args.source).expanduser().resolve()
    if not src.exists():
        print(f"Source not found: {src}")
        return 2

    # Determine repo root
    repo_root = find_repo_root(src.parent) or find_repo_root(Path.cwd())
    if repo_root is None:
        print("Warning: not inside a git repository. .gitignore checks will be skipped.")
        repo_root = Path.cwd()

    if args.dest:
        dest_name = args.dest
    else:
        base = src.name
    dest_name = f"{base}_mushroom"

    dest = (repo_root / dest_name).resolve()

    if dest.exists():
        if args.force:
            if args.dry_run:
                print(f"DRY remove existing: {dest}")
            else:
                print(f"Removing existing destination: {dest}")
                shutil.rmtree(dest)
        else:
            print(f"Destination already exists: {dest}. Use --force to replace.")
            return 3

    # Create dest dir
    if not args.dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    # If source is a file, copy single file into dest root
    if src.is_file():
        # copy the single file as dest/<filename>
        dest_file = dest / src.name
        if args.dry_run:
            print(f"DRY copy: {src} -> {dest_file}")
        else:
            shutil.copy2(src, dest_file)
            print(f"COPY: {src} -> {dest_file}")
        copied, skipped = (1, 0) if not args.dry_run else (0, 0)
    else:
        copied, skipped = copy_tree_filtered(src, dest, repo_root, args.dry_run)

    print(f"Done. Copied: {copied}, Skipped (ignored): {skipped}")

    if args.git_add and not args.dry_run:
        try:
            subprocess.run(["git", "add", str(dest)], cwd=str(repo_root), check=True)
            print(f"git add {dest} -> OK")
        except subprocess.CalledProcessError:
            print("git add failed (is this a git repo?)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
