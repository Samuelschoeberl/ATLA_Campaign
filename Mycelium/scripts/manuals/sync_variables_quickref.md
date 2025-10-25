# sync_variables.py - Quick Reference

## Quick Start
```bash
# Start bi-directional watch mode (DEFAULT - just run it!)
python3 Mycelium/scripts/Python/sync_variables.py

# Watch only one character (bi-directional)
python3 Mycelium/scripts/Python/sync_variables.py -c Anju

# One-time sync (run once and exit)
python3 Mycelium/scripts/Python/sync_variables.py --once

# One-time sync for one character
python3 Mycelium/scripts/Python/sync_variables.py --once -c Anju
```

## Direction Control
```bash
# Default: watch mode with both directions
python3 Mycelium/scripts/Python/sync_variables.py

# One-time: Sheet → Variables only
python3 Mycelium/scripts/Python/sync_variables.py --once -d sheet-to-var

# One-time: Variables → Sheet only
python3 Mycelium/scripts/Python/sync_variables.py --once -d var-to-sheet
```

## Common Use Cases

### During Gameplay (Most Common!)
```bash
# Just run it - starts watching everything!
python3 Mycelium/scripts/Python/sync_variables.py

# Or watch just one character
python3 Mycelium/scripts/Python/sync_variables.py -c Anju
```
Now edit either character sheets OR variable files and save - changes sync automatically in both directions!

### After Manual Edits (One-Time Sync)
```bash
# Preview changes first
python3 Mycelium/scripts/Python/sync_variables.py --once -n

# Apply changes once
python3 Mycelium/scripts/Python/sync_variables.py --once
```

### Troubleshooting
```bash
# Check what would change for one character (dry-run)
python3 Mycelium/scripts/Python/sync_variables.py --once -n -c Anju
```

## Example Changes

**Edit variable file (Anju_current_hp.md):**
```markdown
28
```

**Auto-syncs to character sheet:** `| current hp | 28 |`

---

**OR edit character sheet:**
```markdown
| current hp | 32 |
```

**Auto-syncs to variable file:** `Anju_current_hp.md` contains `32`

## Options
- `-c, --character NAME` - Process only this character
- `--once` - Run once and exit (instead of default watch mode)
- `-n, --dry-run` - Preview without making changes
- `-d, --direction DIR` - Sync direction: `both` (default), `sheet-to-var`, or `var-to-sheet`
- `-h, --help` - Show full help

## Tips
- **NEW:** Just run the script with no args - it starts watching automatically!
- Use `--once` when you want a one-time sync instead of continuous watching
- Use `-c Anju` to watch or sync just one character
- Use dry-run (`-n`) to preview changes before applying
- Use `--once -d var-to-sheet` if you only want to update sheets from variables once
- Press `Ctrl+C` to stop watch mode
