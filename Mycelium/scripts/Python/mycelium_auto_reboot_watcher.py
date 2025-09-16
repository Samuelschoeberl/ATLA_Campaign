#!/usr/bin/env python3
"""
File watcher for Mycelium repo: automatically runs reboot_env_sync.sh when any .md file containing 'character sheet' in its filename changes.

- Checks every 60 seconds for changes
- Only triggers on .md files with 'character sheet' in the filename
"""
import os
import sys
import subprocess
from pathlib import Path
import time
import fnmatch

REPO_ROOT = Path(__file__).resolve().parents[3]
REBOOT_SCRIPT = REPO_ROOT / "Mycelium/scripts/Python/reboot_env_sync.sh"
GITIGNORE = REPO_ROOT / ".gitignore"
CHECK_INTERVAL = 60  # seconds

def get_gitignore_patterns():
    patterns = []
    if GITIGNORE.exists():
        with open(GITIGNORE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                patterns.append(line)
    return patterns

def is_ignored(path, patterns):
    rel_path = os.path.relpath(path, REPO_ROOT)
    for pat in patterns:
        if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(os.path.basename(rel_path), pat):
            return True
    return False

def find_character_sheet_md_files(patterns):
    files = []
    for p in REPO_ROOT.rglob("*.md"):
        if "character sheet" in p.name.lower() and not is_ignored(str(p), patterns):
            files.append(p)
    return files

def get_mtime_map(files):
    return {str(f): f.stat().st_mtime for f in files}

if __name__ == "__main__":
    patterns = get_gitignore_patterns()
    print(f"Monitoring .md files with 'character sheet' in filename under {REPO_ROOT} (excluding .gitignored files)...")
    last_mtimes = get_mtime_map(find_character_sheet_md_files(patterns))
    while True:
        time.sleep(CHECK_INTERVAL)
        files = find_character_sheet_md_files(patterns)
        current_mtimes = get_mtime_map(files)
        changed = False
        for f, mtime in current_mtimes.items():
            if f not in last_mtimes or last_mtimes[f] != mtime:
                print(f"Detected change in: {f}")
                changed = True
        if changed:
            print("Rebooting server due to character sheet change...")
            subprocess.Popen(["bash", str(REBOOT_SCRIPT)])
        last_mtimes = current_mtimes
