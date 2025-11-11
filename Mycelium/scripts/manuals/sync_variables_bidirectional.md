````markdown
# Sync Variables Bidirectional — CLI Manual

## Summary

This manual documents the command-line interface for `sync_variables_bidirectional.py`, which parses variable values from character sheets and writes them back to individual variable files. This is the reverse operation of `recreate_pcs.py`.

## sync_variables_bidirectional.py

### Purpose

- Parse variable values from character sheets (markdown tables)
- Write parsed values back to individual variable files
- Handle environmental variables (shared across all PCs) specially
- Detect conflicts in environmental variable values across character sheets
- Maintain the same file naming conventions as `recreate_pcs.py`

### Location

`Mycelium/scripts/Python/sync_variables_bidirectional.py`

### Usage

**Sync all PCs:**

```bash
python3 Mycelium/scripts/Python/sync_variables_bidirectional.py
```

**Sync a single PC:**

```bash
python3 Mycelium/scripts/Python/sync_variables_bidirectional.py --pc "Anju"
```

**Sync with verbose output:**

```bash
python3 Mycelium/scripts/Python/sync_variables_bidirectional.py --verbose
```

### Options

- `--pc PC`, `-p` : Sync only this PC name (case-sensitive exact match)
- `--verbose`, `-v` : Print detailed per-variable processing information

### Behavior Notes

#### Variable File Naming

The script follows the same naming conventions as `recreate_pcs.py`:

- **PC-specific variables**: Written to `Player Root/variable/PC_variables/<PC>/<PC>_<variable_stem>.md`
- **Environmental variables**: Written to `Player Root/variable/environmental/<variable_stem>.md`

#### Display Name to Stem Conversion

Character sheets use human-readable display names in tables, but variable files use normalized stems:

- `"Environmental water charge"` → `environmental_water_charge`
- `"Max HP"` → `max_hp`
- `"Strength"` → `str`
- `"Earthbending slot"` → `earthbending_slot`

#### Environmental Variables

Environmental variables are **shared across all characters**. The script:

1. Identifies environmental variables by:
   - Variables with `environmental_` prefix
   - Variables tagged with `#environmental_variable`, `#environmental_variables`, or `#environmental`
   
2. Collects values from all PC character sheets

3. Detects conflicts:
   - If different PCs have different values, issues a warning
   - Shows all conflicting values
   - Uses the first value encountered

4. Writes the final value to the shared environmental variable file

5. Preserves existing tags from template files when updating

#### Tag Preservation

- For environmental variables, existing tags from the template are preserved and merged with standard tags
- For PC variables, standard tags are applied: `#variable`, `#character_stat_<PC>`, `#character_stats_<PC>`

#### Table Parsing

The script extracts variables from markdown tables in character sheets:

```markdown
| key                | value |
| ------------------ | ----: |
| max_hp             |    38 |
| Environmental water charge | 8 |
```

- Skips header rows and separator rows
- Handles dice expressions (e.g., `1d20 + 5`) by keeping them as strings
- Converts numeric values to integers or floats

### Examples

**Sync all character sheets to variable files:**
```bash
python3 Mycelium/scripts/Python/sync_variables_bidirectional.py
```

**Sync only Anju's character sheet:**
```bash
python3 Mycelium/scripts/Python/sync_variables_bidirectional.py --pc "Anju" --verbose
```

**Example output with environmental variable conflict:**
```
Processing Anju...
  Found 20 variables
  Environmental variable: environmental_water_charge = 8

Processing Puy...
  Found 22 variables
  Environmental variable: environmental_water_charge = 10

Processing 1 environmental variables...
WARNING: Environmental variable 'environmental_water_charge' has conflicting values:
  Anju: 8
  Puy: 10
  Using value from first PC: 8
  Wrote environmental variable: environmental_water_charge = 8
  NOTE: Character sheets should be regenerated to sync this value

Sync complete!
```

### Workflow Integration

#### Use Case 1: Manual Updates to Character Sheets

When you manually edit a character sheet to update HP or other stats:

1. Edit the character sheet markdown tables
2. Run `sync_variables_bidirectional.py` to write changes to variable files
3. Optionally run `recreate_pcs.py` to regenerate other affected character sheets

#### Use Case 2: Environmental Variable Updates

When an environmental variable changes (e.g., available water charges):

1. Update the value in **one** character sheet
2. Run `sync_variables_bidirectional.py` to update the environmental variable file
3. Run `recreate_pcs.py` to regenerate **all** character sheets with the new value

#### Bidirectional Sync

- `recreate_pcs.py`: Variables → Character Sheets (forward)
- `sync_variables_bidirectional.py`: Character Sheets → Variables (reverse)

### Troubleshooting

**Problem**: Environmental variable conflicts detected

**Solution**: 
- Decide which value is correct
- Manually edit all conflicting character sheets to use the same value, OR
- Let the script use the first value and run `recreate_pcs.py` to sync all sheets

**Problem**: Variable not being parsed

**Solution**:
- Ensure the variable appears in a markdown table with `| key | value |` format
- Check that the table is not inside a code block
- Verify the display name can be converted to a valid stem

**Problem**: Wrong tags on generated files

**Solution**:
- For environmental variables, check the template file tags in `Player Root/variable/secondary_stat/`
- The script preserves existing template tags

### Limitations

- Only parses markdown tables in character sheets
- Does not parse formulas (only values)
- Assumes character sheets are located at `Player Root/PCs/<PC>/<PC> character sheet.md`
- Does not handle variables outside of tables

## Contact

For exact behavior details, inspect `Mycelium/scripts/Python/sync_variables_bidirectional.py`.

````
