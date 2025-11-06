````markdown
# Recreate PCs — CLI Manual

## Summary

This manual documents the command-line interface for the `recreate_pcs.py` generator, which creates PC character sheets and computes secondary stats from templates.

## recreate_pcs.py

### Purpose

- Recompute per-character secondary stats from templates under `Player Root/variable/secondary_stat`
- Generate personalized character sheets with `{{...}}` placeholder substitution
- Write per-character variable files into `Player Root/variable/PC_variables/<PC>/`
- Support both manual runs and automated propagation (used by `watch_and_regen.py`)

### Location

`Mycelium/scripts/Python/recreate_pcs.py`

### Usage

**Run for all PCs with run-update flag set in `Player Root/pc_primary_stats.md`:**

```bash
python3 Mycelium/scripts/Python/recreate_pcs.py
```

**Run for a single character:**

```bash
python3 Mycelium/scripts/Python/recreate_pcs.py --pc "Anju"
```

**Run with verbose output:**

```bash
python3 Mycelium/scripts/Python/recreate_pcs.py --verbose
```

**Regenerate only PCs affected by a specific variable:**

```bash
python3 Mycelium/scripts/Python/recreate_pcs.py --propagate-variable "earthbending_slot"
```

### Options

- `--verbose`, `-v` : Print detailed per-stat evaluation traces and multi-pass resolution logs
- `--pc PC`, `-p` : Limit generation to a single PC name (case-insensitive exact match)
- `--create-placeholders` : Create a minimal `#variable` placeholder file for any referenced variable that doesn't exist yet
- `--vault-folder VAULT_FOLDER`, `-V` : Use the first repository folder matching this name as the vault root (use its `variable/` subfolder). Defaults to "Player Root"
- `--propagate-variable VARIABLE`, `-P` : Only regenerate PCs affected by this variable (stem or filename without .md)

### Behavior Notes

- The script discovers the canonical vault path (defaults to `Player Root`)
- Per-character variable files are written to `<vault>/variable/PC_variables/<Character>/` with filenames prefixed by `<Character>_<originalstem>.md`
- The generator uses a safe AST-based evaluator for formulas. It unescapes markdown-escaped operators and strips a leading `=` from formula lines
- The script will skip copying `#template` tags into generated files but will include `#variable`, `#character_stat`, and `#character_stats` tags
- The character sheet template `Mycelium/data/template/template_Character_Sheet.md` is used if present
- `{{placeholder}}` substitution works for:
  - `{{PC}}` → character name
  - `{{stat_name}}` → computed stat values
  - Stats are inserted into `<!-- STATS_INSERT:type -->` sections:
    - `<!-- STATS_INSERT:core -->` for STR, DEX, CON, INT, WIS, CHA
    - `<!-- STATS_INSERT:vital -->` for HP, Evasion, Armor, etc.
    - `<!-- STATS_INSERT:bending -->` for element levels and slots
    - `<!-- STATS_INSERT:other -->` for other computed stats

### Examples

**Generate all PCs:**
```bash
python3 Mycelium/scripts/Python/recreate_pcs.py
```

**Generate specific PC with verbose output:**
```bash
python3 Mycelium/scripts/Python/recreate_pcs.py --pc "Anju" --verbose
```

**Regenerate only PCs that use a specific variable:**
```bash
python3 Mycelium/scripts/Python/recreate_pcs.py --propagate-variable "max_hp"
```

### Troubleshooting

- If the script doesn't generate any PCs, check that the "Run Update" column in `Player Root/pc_primary_stats.md` is set to "yes"
- If variables are not found, ensure they exist in `Player Root/variable/` or use `--create-placeholders`
- If character sheets have unreplaced `{{placeholders}}`, ensure the variable exists in the PC's computed stats

## Integration with Other Tools

### Used by watch_and_regen.py

The `watch_and_regen.py` script automatically calls `recreate_pcs.py` when it detects changes to character sheets or environmental variables.

### Used by sync_variables.py

When `sync_variables.py` detects variable changes that affect computed stats, it can trigger regeneration through the watcher system.

## Contact

For exact behavior details, inspect `Mycelium/scripts/Python/recreate_pcs.py`.

````
