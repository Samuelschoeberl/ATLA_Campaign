#!/usr/bin/env python3
"""pulse.py

Stage all changes, commit with a message, and push the current branch.

Usage:
  pulse.py -m "message"        # commit and push
  pulse.py --dry-run -m "msg"  # print actions but don't run
  pulse.py --no-push -m "msg"  # stage+commit only

This script is intentionally small and conservative:
- exits if not in a git repository
- does nothing if there are no changes after staging
- attempts `git push --set-upstream origin <branch>` if no upstream exists
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd, capture=False, check=True):
    if capture:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if check and res.returncode != 0:
            raise subprocess.CalledProcessError(res.returncode, cmd, output=res.stdout, stderr=res.stderr)
        return res
    else:
        return subprocess.run(cmd, check=check)


def git_root():
    try:
        res = run(["git", "rev-parse", "--show-toplevel"], capture=True)
        out = res.stdout
        if isinstance(out, bytes):
            out = out.decode()
        return Path(out.strip())
    except Exception:
        return None


def current_branch():
    res = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True)
    out = res.stdout
    if isinstance(out, bytes):
        out = out.decode()
    return out.strip()


def has_index_changes():
    # list staged files
    res = run(["git", "diff", "--cached", "--name-only"], capture=True)
    return bool(res.stdout.strip())


def main():
    p = argparse.ArgumentParser(description="Stage all changes, commit, and push the current branch")
    p.add_argument("-m", "--message", required=True, help="Commit message")
    p.add_argument("--dry-run", action="store_true", help="Show actions but don't execute")
    p.add_argument("--no-push", action="store_true", help="Do not push after commit")
    args = p.parse_args()

    root = git_root()
    if root is None:
        print("Not inside a git repository. Aborting.")
        sys.exit(2)

    print(f"Repository root: {root}")
    if args.dry_run:
        print("DRY RUN: the following commands would run:")
        print("  git add -A")
        print(f"  git commit -m '{args.message}' (if there are staged changes)")
        if not args.no_push:
            print("  git push origin <branch> (or --set-upstream if needed)")
        sys.exit(0)

    # Find unstaged modified files and untracked (non-ignored) files
    # modified but unstaged
    res_mod = run(["git", "diff", "--name-only"], capture=True)
    out_mod = res_mod.stdout
    if isinstance(out_mod, bytes):
        out_mod = out_mod.decode()
    if not isinstance(out_mod, str):
        out_mod = str(out_mod)
    modified_files = [l for l in out_mod.splitlines() if l]

    # untracked, excluding ignored
    res_untracked = run(["git", "ls-files", "--others", "--exclude-standard"], capture=True)
    out_untracked = res_untracked.stdout
    if isinstance(out_untracked, bytes):
        out_untracked = out_untracked.decode()
    if not isinstance(out_untracked, str):
        out_untracked = str(out_untracked)
    untracked_files = [l for l in out_untracked.splitlines() if l]

    to_add = modified_files + untracked_files
    if to_add:
        print(f"Staging {len(to_add)} files (not adding ignored files):")
        for p in to_add:
            print("  ", p)
        if args.dry_run:
            print("DRY RUN: would run: git add -- <files>")
        else:
            # sanitize and add files individually to avoid pathspec/quoting issues
            def sanitize_path(x: str) -> str:
                # remove surrounding double quotes if present
                if len(x) >= 2 and ((x[0] == '"' and x[-1] == '"') or (x[0] == "'" and x[-1] == "'")):
                    x = x[1:-1]
                # decode common backslash-escaped byte sequences like \342\200\223 -> actual UTF-8 bytes
                try:
                    decoded = bytes(x, 'utf-8').decode('unicode_escape')
                    # if unicode_escape produced bytes interpreted as latin-1, keep decoded as-is
                    x = decoded
                except Exception:
                    pass
                return x

            for p in to_add:
                sp = sanitize_path(p)
                try:
                    run(["git", "add", "--", sp])
                except subprocess.CalledProcessError:
                    # if single add fails, show which file and continue
                    print(f"Warning: git add failed for: {sp}", file=sys.stderr)

    # If there are no staged changes, exit cleanly
    if not has_index_changes():
        print("No changes to commit after staging. Nothing to do.")
        sys.exit(0)

    # Commit
    print(f"Committing with message: {args.message!r}")
    try:
        run(["git", "commit", "-m", args.message])
    except subprocess.CalledProcessError as e:
        print("git commit failed:", e, file=sys.stderr)
        sys.exit(e.returncode)

    if args.no_push:
        print("Skipping push (by --no-push).")
        sys.exit(0)

    # Determine branch and push
    branch = current_branch()
    print(f"Pushing branch: {branch}")

    # Try simple push; if it fails because upstream is not set, try set-upstream
    try:
        run(["git", "push", "origin", branch])
        print("Push succeeded.")
    except subprocess.CalledProcessError:
        print("Initial push failed; attempting to set upstream and push.")
        try:
            run(["git", "push", "--set-upstream", "origin", branch])
            print("Push with upstream set succeeded.")
        except subprocess.CalledProcessError as e:
            print("Push failed:", e, file=sys.stderr)
            sys.exit(e.returncode)


if __name__ == "__main__":
    main()
