# Environmental Variables - Complete Implementation Guide

## Overview
Environmental variables are **shared variables** that propagate to ALL character sheets automatically. When any character sheet or the environmental variable file itself changes, the sync script ensures all sheets stay synchronized.

## How It Works

### 1. Variable Storage
- **Location**: `Player Root/variable/environmental/`
- **Example**: `environmental_water_charge.md`
- **Format**: Same as regular variables (fenced code block with value and tags)

### 2. Bidirectional Sync

#### Sheet → Environmental File → All Other Sheets
When you change `environmental_water_charge` in **any** character sheet:
1. Script detects the change in that sheet
2. Updates `Player Root/variable/environmental/environmental_water_charge.md`
3. Propagates the new value to **all other character sheets**
4. Regenerates `stat_overview.md`

#### Environmental File → All Sheets
When you change `environmental_water_charge.md` directly:
1. Script detects the change in the environmental file
2. Updates **all character sheets** with the new value
3. Regenerates `stat_overview.md`

#### stat_overview.md → Environmental File → All Sheets
When you change the value in the environmental variables table in `stat_overview.md`:
1. Script detects the change in stat_overview
2. Updates the environmental variable file
3. Propagates the new value to **all character sheets**

**Example:** Changing the value column for `[[environmental_water_charge]]` from `6` to `8` in stat_overview.md will update the environmental file and all character sheets.

### 3. Implementation Details

#### In sync_character_sheet() (Sheet → Var direction):
- **Line ~260**: Checks environmental variables FIRST before regular variables
- If environmental variable changed in sheet:
  - Updates environmental file
  - Calls `update_all_sheets_with_environmental_var()` to propagate
  - Skips creating a per-character variable file for this variable

#### In sync_variables_to_sheet() (Var → Sheet direction):
- **Line ~538**: After checking regular variables, checks environmental variables
- Reads from `Player Root/variable/environmental/*.md`
- Updates the current character's sheet if value differs

#### In watch_mode():
- **Line ~800**: Monitors stat_overview.md for environmental variable changes
- **Line ~820**: Monitors environmental variable files for changes
- **Line ~880**: Detects new environmental variable files
- When stat_overview changes, syncs env vars to files and all sheets
- When environmental file changes, syncs to all sheets

### 4. Configuration

Environmental variables are defined in `ENVIRONMENTAL_MAPPINGS`:
```python
ENVIRONMENTAL_MAPPINGS = [
    (r'environmental[_ ]?water[_ ]?charge', 'environmental_water_charge.md'),
    # Add more environmental variables here
]
```

Each entry has:
1. **Regex pattern** to match the key in character sheets
2. **Filename** in the environmental folder

## Adding New Environmental Variables

To add a new environmental variable:

1. Add to `ENVIRONMENTAL_MAPPINGS`:
   ```python
   (r'environmental[_ ]?spirit[_ ]?energy', 'environmental_spirit_energy.md'),
   ```

2. Add the variable to character sheet tables:
   ```markdown
   | Environmental Spirit Energy | 100 |
   ```

3. The sync script will automatically:
   - Create the environmental file on first change
   - Keep all sheets synchronized
   - Monitor for changes in watch mode

## Usage Examples

### Example 1: Update in Character Sheet
```bash
# 1. Edit Anju's character sheet
# Change "Environmental Water Charge" from 50 to 75

# 2. Sync script (in watch mode) detects change
✓ Updated environmental variable environmental_water_charge.md: '50' → '75'
✓ Propagating environmental_water_charge to all sheets
✓ Updated Ash sheet environmental_water_charge: '50' → '75'
✓ Updated Grep sheet environmental_water_charge: '50' → '75'
... (all other sheets)
✓ Regenerated stat_overview.md
```

### Example 2: Update in Environmental File
```bash
# 1. Edit Player Root/variable/environmental/environmental_water_charge.md
# Change value from 75 to 100

# 2. Sync script detects change
✓ Environmental file changed: environmental_water_charge.md
✓ Updated Anju sheet environmental_water_charge from environmental: '75' → '100'
✓ Updated Ash sheet environmental_water_charge from environmental: '75' → '100'
... (all other sheets)
✓ Regenerated stat_overview.md
```

### Example 3: Update in stat_overview.md
```bash
# 1. Edit Player Root/PCs/stat_overview.md
# In the "Global environmental variables" table, change:
# | [[environmental_water_charge]] | 6 | ... |
# to:
# | [[environmental_water_charge]] | 10 | ... |

# 2. Sync script detects change
📊 Detected change in stat_overview.md
✓ Updated environmental variable environmental_water_charge.md from stat_overview: '6' → '10'
  ✓ Propagated to 11 character sheet(s)
  ✓ Synced 1 environmental variable(s) from stat_overview
```

## Key Functions

- `get_environmental_variable_path(filename)` - Get path to environmental variable file
- `read_environmental_var_value(path)` - Read value from environmental file
- `write_environmental_var_file(path, value)` - Write to environmental file
- `update_all_sheets_with_environmental_var(var_suffix, new_value, pattern)` - Propagate to all sheets
- `sync_environmental_variables_to_sheets()` - Sync all environmental vars to all sheets
- `parse_stat_overview_environmental_vars()` - Parse environmental variables from stat_overview.md
- `sync_stat_overview_to_env_vars()` - Sync environmental variables from stat_overview to files and sheets

## Testing

To test the complete implementation:

1. **Test Sheet → Environmental → Sheets**:
   ```bash
   # Change environmental_water_charge in Anju's sheet
   # Verify environmental_water_charge.md updated
   # Verify all other character sheets updated
   ```

2. **Test Environmental → Sheets**:
   ```bash
   # Change environmental_water_charge.md directly
   # Verify all character sheets updated
   ```

3. **Test stat_overview → Environmental → Sheets**:
   ```bash
   # Change environmental_water_charge value in stat_overview.md table
   # Verify environmental_water_charge.md updated
   # Verify all character sheets updated
   ```

2. **Test Environmental → Sheets**:
   ```bash
   # Change environmental_water_charge.md directly
   # Verify all character sheets updated
   ```

3. **Test Watch Mode**:
   ```bash
   cd /path/to/Mycelium/scripts/Python
   python sync_variables.py
   # Make changes while script is running
   ```

4. **Test New Environmental File**:
   ```bash
   # Create new environmental_spirit_energy.md
   # Verify watch mode detects it
   ```

## Architecture Notes

- Environmental variables are checked **first** in sync_character_sheet() to ensure priority
- No per-character variable files are created for environmental variables
- All sheets get updated simultaneously when environmental variable changes
- stat_overview.md regeneration happens after all sheets are updated
- Watch mode monitors environmental folder separately from per-character variables
