#!/usr/bin/env python3
"""Delete (move to deleted folder) all .html files under Player Root.

This script finds all .html files in the Player Root directory and its
subdirectories, then moves them to Player Root/deleted/ maintaining their
relative directory structure.
"""
from pathlib import Path
import shutil
import sys

# Find repository root by looking for .git directory
_script_path = Path(__file__).resolve()
ROOT = _script_path
while ROOT.parent != ROOT:
    if (ROOT / '.git').exists():
        break
    ROOT = ROOT.parent
# If no .git found, fall back to 3 levels up from script (Mycelium/scripts/Python -> repo root)
if not (ROOT / '.git').exists():
    ROOT = _script_path.parent.parent.parent

PLAYER_ROOT = ROOT / 'Player Root'
DELETED_DIR = PLAYER_ROOT / 'deleted'


def main():
    """Move all .html files under Player Root to deleted folder."""
    if not PLAYER_ROOT.exists():
        print(f"ERROR: Player Root directory not found at {PLAYER_ROOT}")
        sys.exit(1)
    
    # Ensure deleted directory exists
    DELETED_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find all .html files under Player Root (excluding deleted folder itself)
    html_files = []
    for html_file in PLAYER_ROOT.rglob('*.html'):
        # Skip files already in deleted folder
        try:
            html_file.relative_to(DELETED_DIR)
            continue
        except ValueError:
            # Not in deleted folder, so include it
            html_files.append(html_file)
    
    if not html_files:
        print("No .html files found to delete.")
        return
    
    print(f"Found {len(html_files)} .html file(s) to move to deleted folder:")
    
    moved_count = 0
    for html_file in html_files:
        try:
            # Get relative path from Player Root
            rel_path = html_file.relative_to(PLAYER_ROOT)
            
            # Construct destination path in deleted folder
            dest_path = DELETED_DIR / rel_path
            
            # Create parent directories if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move the file
            shutil.move(str(html_file), str(dest_path))
            print(f"  Moved: {rel_path}")
            moved_count += 1
            
        except Exception as e:
            print(f"  ERROR moving {html_file}: {e}", file=sys.stderr)
    
    print(f"\nSuccessfully moved {moved_count} file(s) to {DELETED_DIR.relative_to(ROOT)}")


if __name__ == '__main__':
    main()
