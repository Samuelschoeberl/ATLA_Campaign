Quick usage examples for watch_and_regen.py

This watcher polls `Player Root/PCs` for changes to `* character sheet.md` files and regenerates the affected PC.

Examples:

# Run watcher with 2s interval (dry-run):

python3 Mycelium/scripts/python/watch_and_regen.py --interval 2 --dry-run

# Run watcher and let it call the generator when changes occur:

python3 Mycelium/scripts/python/watch_and_regen.py --interval 1

Options:
--interval N Poll interval in seconds
--pcs-dir PATH Repo-relative PCs root (default: Player Root/PCs)
--script PATH Path to the generator script (default: Mycelium/scripts/python/recreate_pcs.py)
--create-placeholders Forward to generator
--debounce N Minimum seconds between re-runs for the same PC
--dry-run Do not actually run generator; print actions only

Notes:

- The watcher avoids re-triggering on files it just wrote and compares file contents in addition to mtime to reduce noise.
