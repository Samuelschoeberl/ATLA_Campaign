# Sync Variables Script Documentation

## Overview

The `sync_variables.py` script provides **bi-directional** synchronization between character sheets and variable files. This ensures that your character sheets and variable files stay in sync automatically.

**Default behavior:** Runs in **watch mode** with bi-directional sync enabled.

## How It Works

The script:
1. Monitors character sheets in `Player Root/PCs/<CharacterName>/<CharacterName> Character Sheet.md`
2. Monitors variable files in `Player Root/variable/PC_variables/<CharacterName>/`
3. Detects changes in **either** location
4. **Sheet → Variable:** When you edit a stat in a character sheet, it updates the corresponding variable file
5. **Variable → Sheet:** When you edit a variable file, it updates the corresponding row in the character sheet
6. Preserves the correct tags for each variable type

## Installation

No installation required! The script is located at:
```
Mycelium/scripts/Python/sync_variables.py
```

## Usage

### Basic Commands

**Watch mode (default - continuously monitor for changes):**
```bash
python3 Mycelium/scripts/Python/sync_variables.py
```

**Run once and exit:**
```bash
python3 Mycelium/scripts/Python/sync_variables.py --once
```

**Sync a specific character (watch mode):**
```bash
python3 Mycelium/scripts/Python/sync_variables.py --character Anju
```

**Sync a specific character (one-time):**
```bash
python3 Mycelium/scripts/Python/sync_variables.py --once --character Anju
```

**Dry run (preview changes without applying them):**
```bash
python3 Mycelium/scripts/Python/sync_variables.py --once --dry-run
```

**Sync only from sheet to variable (one direction):**
```bash
python3 Mycelium/scripts/Python/sync_variables.py --once --direction sheet-to-var
```

**Sync only from variable to sheet (one direction):**
```bash
python3 Mycelium/scripts/Python/sync_variables.py --once --direction var-to-sheet
```

### Shell Wrapper

For convenience, you can also use the shell wrapper:
```bash
# From anywhere in the project
./Mycelium/scripts/shell/sync_vars.sh --watch
```

## Examples

### Example 1: Update Current HP

**Before:**
In `Anju Character Sheet.md`:
```markdown
| current hp | 38 |
```

**Change to:**
```markdown
| current hp | 32 |
```

**Run:**
```bash
python3 Mycelium/scripts/Python/sync_variables.py --once --character Anju
```

**Result:**
The file `Player Root/variable/PC_variables/Anju/Anju_current_hp.md` is updated to:
```markdown
32

#vitality #current_variable #variable_Anju #character_stat_Anju #character_stats_Anju #secondary_stat_Anju
```

### Example 2: Variable → Sheet Sync

**Before:**
Variable file `Anju_max_hp.md` contains:
```markdown
95

#vitality #variable_Anju #character_stat_Anju
```

**Change to:**
```markdown
100

#vitality #variable_Anju #character_stat_Anju
```

**Run:**
```bash
python3 Mycelium/scripts/Python/sync_variables.py --once --character Anju
```

**Result:**
The character sheet is updated:
```markdown
| max hp | 100 |
```

### Example 3: Watch Mode (Default)

Start the script in default watch mode:
```bash
python3 Mycelium/scripts/Python/sync_variables.py --character Anju
```

Now whenever you save changes to **either** `Anju Character Sheet.md` **or** any variable file in `Anju/`, the script will automatically detect and sync the changes bi-directionally.

Press `Ctrl+C` to stop watching.

### Example 4: Dry Run All Characters

Preview what would change across all characters without making any changes:
```bash
python3 Mycelium/scripts/Python/sync_variables.py --once --dry-run
```

Output shows what would be synced:
```
[DRY RUN] Sheet → Variable: Would update Anju_current_hp from 38 to 32
[DRY RUN] Variable → Sheet: Would update Grep max hp row from 85 to 90
...
```

## Command-Line Options

- `--once` : Run once and exit (instead of default watch mode)
- `--dry-run`, `-n` : Show what would be changed without making modifications
- `--character CHARACTER`, `-c` : Only process a specific character (e.g., `--character Anju`)
- `--direction {both,sheet-to-var,var-to-sheet}`, `-d` : Sync direction
  - `both` (default) : Bi-directional sync
  - `sheet-to-var` : Only sync from character sheet to variable files
  - `var-to-sheet` : Only sync from variable files to character sheet

## Supported Variables

The script automatically syncs the following types of variables:

### Vitals
- `max_hp` → `<Name>_max_hp.md`
- `current hp` → `<Name>_current_hp.md`
- `Initiative` → `<Name>_Initiative.md`
- `Stress Level` → `<Name>_Stress Level.md`
- `Fire Damage Bonus` → `<Name>_Fire Damage Bonus.md`

### Core Stats (Primary Stats)
- `Strength` → `<Name>_Strength.md`
- `Dexterity` → `<Name>_Dexterity.md`
- `Constitution` → `<Name>_Constitution.md`
- `Intelligence` → `<Name>_Intelligence.md`
- `Wisdom` → `<Name>_Wisdom.md`
- `Charisma` → `<Name>_Charisma.md`

### Defensive Stats
- `Evasion` → `<Name>_Evasion.md`
- `Barrier` → `<Name>_Barrier.md`
- `General Armor` → `<Name>_General Armor.md`
- `Physical Armor` → `<Name>_Physical Armor.md`
- `Fire Armor` → `<Name>_Fire Armor.md`
- `Ice Armor` → `<Name>_Ice Armor.md`
- `Spirit Armor` → `<Name>_Spirit Armor.md`

### Bending Slots
- `Waterbending slot` → `<Name>_waterbending slot.md`
- `Earthbending slot` → `<Name>_earthbending slot.md`
- `Firebending slot` → `<Name>_firebending slot.md`
- `Airbending slot` → `<Name>_airbending slot.md`

### Water Charges
- `Environmental water charge` → `<Name>_environmental_water_charge.md`
- `Waterbottle charge` → `<Name>_Waterbottle Charge.md`

## Tags

The script automatically applies the correct tags for each variable type:

- **Primary Stats:** `#variable_{name}`, `#character_stat_{name}`, `#character_stats_{name}`, `#primary_stat_{name}`
- **Secondary Stats:** `#variable_{name}`, `#character_stat_{name}`, `#character_stats_{name}`, `#secondary_stat_{name}`
- **Vitals:** `#vitality`, + secondary stat tags
- **Current Variables:** `#current_variable`, + other relevant tags
- **Defensive:** `#defensive`, + secondary stat tags
- **Element-specific:** `#water`, `#earth`, `#fire`, `#air`, + conditional show tags

## Integration with Other Scripts

The sync script is designed to work alongside other scripts in the Mycelium system:

- **`recreate_pcs.py`**: Generates character sheets from primary stats and templates
- **`update_character_sheets_from_variables.py`**: Updates sheets FROM variables (opposite direction)
- **`change_var.py`**: Programmatically change individual variables

### Workflow Example

1. Manually edit character sheet → Run `sync_variables.py` → Variable files updated
2. Run `recreate_pcs.py` → Character sheets regenerated from variables and formulas
3. Use watch mode during gameplay to keep everything in sync in real-time

## Troubleshooting

### Script doesn't detect changes
- Make sure you've saved the character sheet file
- Check that the table format matches the expected markdown format
- Verify the key names match the supported variables (case-insensitive)

### Wrong tags in variable files
- The script uses predefined tag sets for each variable type
- Check the `VARIABLE_MAPPINGS` list in `sync_variables.py` to see/modify tag assignments

### Watch mode not working
- Ensure you have write permissions to the variable directories
- Check that the character sheet path is correct
- The script checks for file modifications every 1 second

## Command Line Options

```
usage: sync_variables.py [-h] [--watch] [--dry-run] [--character CHARACTER]

Sync character sheet changes to variable files

options:
  -h, --help            show this help message and exit
  --watch, -w           Run in watch mode (continuously monitor for changes)
  --dry-run, -n         Show what would be changed without making modifications
  --character CHARACTER, -c CHARACTER
                        Only process a specific character (e.g., Anju)
```

## Technical Details

### File Format

Variable files use the following format:
```markdown
```markdown
<value>

<tags separated by spaces>

```
```

### Table Parsing

The script looks for markdown tables in the character sheets with this format:
```markdown
| key        | value |
| ---------- | ----: |
| max_hp     |    95 |
| current hp |    38 |
```

Keys are normalized (case-insensitive, spaces/underscores treated the same) for matching.

### Change Detection

In watch mode, the script:
1. Records the last modified timestamp of each character sheet
2. Checks every 1 second for changes
3. When a change is detected, re-parses the sheet and syncs variables
4. Updates the timestamp and continues monitoring

## Future Enhancements

Potential improvements for the script:
- Add support for more variable types as they're added to character sheets
- Implement bi-directional sync (detect variable file changes too)
- Add logging to a file for debugging
- Support for batch operations on multiple characters
- Integration with Git hooks for automatic syncing on commits
