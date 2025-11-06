```markdown
# Watch and Regen — CLI Manual

## Summary

The `watch_and_regen.py` script polls `Player Root/PCs` for changes to character sheet files and automatically regenerates the affected PC using `recreate_pcs.py`. It also handles environmental variable propagation across character sheets.

## Purpose

- Monitor character sheet files for changes
- Automatically trigger PC regeneration when changes are detected
- Propagate environmental variables across all character sheets
- Handle show_if conditions for element-specific environmental variables
- Avoid duplicate regenerations through debouncing and content comparison

## Location

`Mycelium/scripts/Python/watch_and_regen.py`

## Usage

**Start watcher with default 2-second interval:**

```bash
python3 Mycelium/scripts/Python/watch_and_regen.py
```

**Run watcher with custom interval (1 second):**

```bash
python3 Mycelium/scripts/Python/watch_and_regen.py --interval 1
```

**Dry-run mode (show what would happen without actually doing it):**

```bash
python3 Mycelium/scripts/Python/watch_and_regen.py --dry-run
```

**Monitor with verbose logging:**

```bash
python3 Mycelium/scripts/Python/watch_and_regen.py --interval 2 --create-placeholders
```

## Options

- `--interval N` : Poll interval in seconds (default: 2.0)
- `--pcs-dir PATH` : Repo-relative PCs folder (default: `Player Root/PCs`)
- `--script PATH` : Path to the generator script (default: `Mycelium/scripts/Python/recreate_pcs.py`)
- `--create-placeholders` : Forward `--create-placeholders` flag to the generator
- `--debounce N` : Minimum seconds between re-runs for the same PC (default: 1.0)
- `--dry-run` : Do not actually run generator; print actions only

## How It Works

1. **Monitors character sheets**: Scans `Player Root/PCs/*/` for `* character sheet.md` files
2. **Content comparison**: Compares both mtime AND content to avoid false positives
3. **Self-write detection**: Ignores files that were just written by the generator itself
4. **Environmental variable detection**: Parses changed sheets for environmental variable rows
5. **Propagation**: When an environmental variable changes:
   - Updates the canonical variable file in `Player Root/variable/`
   - Propagates the new value to all other character sheets
   - Respects `show_if` conditions (e.g., only shows to PCs with water ≥ 1)
6. **Smart regeneration**: Only regenerates PCs that are affected by the variable change
7. **Debouncing**: Prevents rapid re-triggers for the same PC

## Environmental Variable Propagation

The watcher handles environmental variables specially:

- Detects changes to variables like "environmental water charge", "environmental fire damage", etc.
- Treats the changed sheet as authoritative
- Updates the canonical variable file in `Player Root/variable/`
- Propagates to all other character sheets that should have the variable
- Respects element-level requirements (e.g., `#show_if:water>=1`)
- Regenerates only affected PCs (those with the required element level)

## Examples

### Example 1: Basic Monitoring

```bash
python3 Mycelium/scripts/Python/watch_and_regen.py
```

Output:
```
Watching Player Root/PCs every 2.0 s; generator: Mycelium/scripts/Python/recreate_pcs.py
Change detected for PC Anju
Updated environmental variable file: Player Root/variable/environmental_water_charge.md
Propagated environmental water charge -> Player Root/PCs/Grep/Grep character sheet.md
Running generator for Anju...
Running generator for Grep...
```

### Example 2: Dry-Run Mode

```bash
python3 Mycelium/scripts/Python/watch_and_regen.py --interval 1 --dry-run
```

Output:
```
Watching Player Root/PCs every 1.0 s; generator: Mycelium/scripts/Python/recreate_pcs.py
Change detected for PC Anju
[DRY] would set canonical Player Root/variable/environmental_water_charge.md to 5
[DRY] Would run: recreate_pcs.py --pc Anju
```

### Example 3: Custom Configuration

```bash
python3 Mycelium/scripts/Python/watch_and_regen.py \
  --interval 3 \
  --debounce 2 \
  --create-placeholders
```

## Notes

- The watcher avoids re-triggering on files it just wrote by tracking recent write timestamps
- It compares file contents in addition to mtime to reduce noise from editor touches
- Debouncing prevents rapid repeated regenerations when multiple changes occur quickly
- Environmental variable propagation is element-aware and respects show_if conditions

## Troubleshooting

- If changes aren't detected, check file naming: files must be named `<PCName> character sheet.md`
- If propagation doesn't work, verify the environmental variable template exists and has proper tags
- If regeneration is too frequent, increase `--debounce` value
- Use `--dry-run` to debug what the watcher would do without actually running the generator

## Integration

This script is designed to run alongside `sync_variables.py`:
- `sync_variables.py` handles sheet ↔ variable file sync
- `watch_and_regen.py` handles regeneration when formulas need recalculation
- Together they provide a complete auto-update workflow

## Contact

For exact behavior details, inspect `Mycelium/scripts/Python/watch_and_regen.py`.

```
