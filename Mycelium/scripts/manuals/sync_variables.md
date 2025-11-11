# sync_variables.py — Variable Synchronization Manual

## Overview

This manual documents the `sync_variables.py` script, which monitors PC variable files for changes and automatically synchronizes them with:
1. Character sheets (`Player Root/PCs/<PC>/<PC> character sheet.md`)
2. The stat overview (`Player Root/PCs/stat_overview.md`)

## How Variable Files Are Written (from recreate_pcs.py)

### File Structure

Variable files are stored at:
```
Player Root/variable/PC_variables/<PC_Name>/<PC_Name>_<stat_name>.md
```

Each variable file has a consistent format:

```markdown
```markdown
<VALUE>

<TAGS>

```
```

### Tag Transformation

Tags in variable files are transformed from the template sources:

#### Primary Stats (from `Player Root/pc_primary_stats.md`)
- Original template tags: User-defined tags (e.g., `#primary_stat`)
- **Transformation**: Template tags are preserved EXCEPT `#template`, and character-specific tags are appended
- **Result tags**: `#variable_<PC>`, `#character_stat_<PC>`, `#character_stats_<PC>`, `#primary_stat_<PC>`

Example:
```markdown
```markdown
18

#variable_Anju #character_stat_Anju #character_stats_Anju #primary_stat_Anju

```
```

#### Secondary Stats (from templates in `Player Root/variable/secondary_stat/`)
- Original tags: `#secondary_stat` plus any custom tags (e.g., `#vitality`, `#defensive`)
- **Transformation**: Custom tags are preserved, `#template` is excluded, character-specific tags appended
- **Result tags**: `#variable_<PC>`, `#character_stat_<PC>`, `#character_stats_<PC>`, `#secondary_stat_<PC>`, plus original custom tags

Example (for a #vitality-tagged stat):
```markdown
```markdown
38

#vitality #variable_Anju #character_stat_Anju #character_stats_Anju #secondary_stat_Anju

```
```

### Key Tag Rules

1. **#template tags are excluded** — The source templates are not copied to generated variable files
2. **#variable tag is always added** with character suffix
3. **Custom tags are preserved** — Tags like `#vitality`, `#defensive`, `#environmental_variable` are retained
4. **Character-specific suffixes** — All tags get the character name appended (e.g., `#variable_Anju`)

### Special Variables

**Zero-valued secondaries**: Secondary stats that evaluate to 0 are NOT written to variable files UNLESS they are tagged with:
- `#vitality`
- `#defensive`
- `#environmental_variable`

This keeps non-essential zero-valued stats out of the variable file system while ensuring important defensive/vital stats are always present.

---

## How sync_variables.py Works

### 1. Initialization

The script discovers the variable file structure:
```
Player Root/
  variable/
    PC_variables/
      Anju/
        Anju_max_hp.md
        Anju_current_hp.md
        Anju_Evasion.md
        ...
      Tai/
        Tai_max_hp.md
        ...
```

### 2. File Monitoring (5-second polling)

The watcher maintains:
- **file_mtimes**: Tracks last modification time of each variable file
- **current_values**: In-memory cache of all known values

Every 5 seconds, it:
1. Scans the `PC_variables/` directory
2. Checks modification times of all `.md` files
3. For any modified file:
   - Reads the new value from the fenced block
   - Compares with the cached value
   - Reports the change if different

### 3. Synchronization Flow

When a change is detected:

```
Variable file changed
         ↓
Read new value from ```markdown fence
         ↓
Match PC name and stat name
         ↓
Update character sheet table
  ├→ Find table row by display name
  ├→ Replace value in that row
  └→ Write updated sheet
         ↓
Update stat overview (if tagged #vitality/#defensive)
  ├→ Find stat row by display name
  ├→ Replace value in that row
  └→ Write updated overview
         ↓
Report sync complete
```

### 4. Character Sheet Updates

The script finds and updates values in table rows:

**Pattern matched:**
```markdown
| Display Name | old_value |
```

**Example:**
```markdown
| max_hp | 38 |
| current hp | 38 |
| Evasion | 11 |
```

The script uses regex to find these patterns (case-insensitive) and replaces the value.

### 5. Stat Overview Updates

Only updates stats tagged with `#vitality` or `#defensive`.

The stat overview file (`stat_overview.md`) contains tables like:

```markdown
### Anju

**Vitality**

| Key | Value | Source File |
| --- | --- | --- |
| current_hp | 38 | Player Root/variable/PC_variables/Anju/Anju_current_hp.md |
| max_hp | 38 | Player Root/variable/PC_variables/Anju/Anju_max_hp.md |

**Defensive**

| Key | Value | Source File |
| --- | --- | --- |
| Evasion | 11 | Player Root/variable/PC_variables/Anju/Anju_Evasion.md |
```

The script updates the Value column for these entries when their source variable files change.

---

## Usage

### Basic Usage (5-second polling)

```bash
python3 Mycelium/scripts/Python/sync_variables.py
```

### Custom Check Interval

```bash
python3 Mycelium/scripts/Python/sync_variables.py --interval 10
```

Checks every 10 seconds instead of 5.

### Verbose Mode

```bash
python3 Mycelium/scripts/Python/sync_variables.py --verbose
```

Prints detailed information about:
- File scans
- Detected changes
- Table updates
- Tag inspection

### Specific Vault Folder

```bash
python3 Mycelium/scripts/Python/sync_variables.py --vault-folder "Dms Root"
```

Targets a different vault (default: "Player Root").

### All Options

```bash
python3 Mycelium/scripts/Python/sync_variables.py --help
```

---

## Architecture

### Key Classes and Methods

#### `VariableFileWatcher`
Main class managing the synchronization loop.

**Methods:**

- `__init__(vault_root, verbose)` — Initialize with vault discovery
- `scan_variable_files()` — Find all PC variable files
- `read_variable_file(path)` — Extract value from fenced block
- `detect_changes()` — Identify modified files
- `update_character_sheet(pc_name, changes)` — Sync to character sheet
- `update_stat_overview(changes)` — Sync to stat overview
- `_update_table_value(content, key, value)` — Regex-based table updater
- `_read_variable_tags(path)` — Extract tags from variable file
- `initial_load()` — Load all known values on startup
- `run_watch_loop(check_interval)` — Main polling loop

### File Reading Format

**Variable files** use this regex to extract values:
```regex
```markdown\n(.*?)\n\n
```

This matches the fenced block and captures the value between the opening fence and blank line.

### Tag Detection

Tags are extracted using:
```regex
```markdown\n.*?\n\n(.*?)\n\n```
```

Then individual tags are found with:
```regex
#([A-Za-z0-9_\-]+)
```

---

## Integration with Other Scripts

### With recreate_pcs.py

`recreate_pcs.py` writes the initial variable files when:
- `--pc "PC_Name"` generates for a specific PC
- Run without args generates for all PCs with `Run Update: yes` in `pc_primary_stats.md`

**Workflow:**
1. Run `recreate_pcs.py` to generate initial character sheets and variable files
2. Start `sync_variables.py` in a separate terminal
3. Modify character sheets or variable files → sync_variables picks up changes

### With watch_and_regen.py

If `watch_and_regen.py` is running, it may also trigger `recreate_pcs.py` regeneration. The two scripts:
- **recreate_pcs.py**: Generates files from templates
- **sync_variables.py**: Keeps them in sync when manual edits occur

---

## Data Flow Example

### Scenario: User edits max_hp in character sheet

1. **User action**: Edits `Anju character sheet.md`, changes `max_hp` from 38 to 40
2. **Current state**: 
   - Variable file still has 38
   - Character sheet now has 40
   - *(sync_variables currently doesn't sync sheet → variable, only variable → sheet)*

### Scenario: User edits variable file

1. **User action**: Edits `Anju_max_hp.md`, changes value from 38 to 40
2. **sync_variables detection** (next 5-second check):
   - Sees mtime changed on `Anju_max_hp.md`
   - Reads new value: 40
   - Compares with cached 38 → different
   - Reports change
3. **Synchronization**:
   - Updates `Anju character sheet.md`: `| max_hp | 40 |`
   - If tagged `#vitality`: Updates `stat_overview.md` entry
4. **Result**:
   - Variable file: 40
   - Character sheet: 40
   - Stat overview: 40

---

## Limitations and Future Enhancements

### Current Behavior

- **One-way sync**: Variable files → Character sheets → Stat overview
- **No rollback**: If a variable file is deleted, the old value is forgotten
- **Manual sheet edits not synced back**: Changes in character sheets don't propagate to variable files
- **No conflict resolution**: If multiple changes happen simultaneously, only the latest is used

### Possible Enhancements

1. **Two-way sync**: Detect character sheet edits and update variable files
2. **History tracking**: Keep change logs of value transitions
3. **Validation**: Check formulas and constraints when updating
4. **Bulk operations**: Handle multiple variable changes atomically
5. **Watchers integration**: Trigger `recreate_pcs.py` when templates change
6. **Conflict resolution**: Handle simultaneous edits more gracefully

---

## Troubleshooting

### Script doesn't detect changes

**Check:**
- Variable files exist at `Player Root/variable/PC_variables/<PC>/`
- Files have correct format with fenced blocks
- Modification time is actually changing (check with `ls -la`)
- Check interval isn't too short (minimum 1 second)

### Character sheet not updating

**Check:**
- Character sheet exists at `Player Root/PCs/<PC>/<PC> character sheet.md`
- Table format is correct: `| Key | Value |`
- Key name matches (case-insensitive matching is used, but exact format helps)
- Use `--verbose` to see attempted matches

### Stat overview not updating

**Check:**
- `stat_overview.md` exists at `Player Root/PCs/stat_overview.md`
- Variable is tagged with `#vitality` or `#defensive`
- Table format is correct
- Use `--verbose` to see tag detection

### Performance Issues

**Solutions:**
- Increase `--interval` to reduce polling frequency
- Disable `--verbose` to reduce console output
- Consider running in background: `nohup python3 ... &`

---

## Contact

For exact implementation details, see `Mycelium/scripts/Python/sync_variables.py`.

For variable file writing details, see `Mycelium/scripts/Python/recreate_pcs.py`.
