# Quick Start: Variable Synchronization

## What You Need to Know

### 1. Variable Files Exist Here
```
Player Root/variable/PC_variables/<PC>/<PC>_<stat>.md
```

### 2. Variable File Format
```markdown
```markdown
<VALUE>

<TAGS>

```
```

Example:
```markdown
```markdown
38

#vitality #variable_Anju #character_stat_Anju #character_stats_Anju #secondary_stat_Anju

```
```

### 3. Tags Explained

**Required Tags** (always suffixed with character name):
- `#variable_<PC>` — "This is a variable file"
- `#character_stat_<PC>` — "This is a per-character stat"
- `#secondary_stat_<PC>` or `#primary_stat_<PC>` — Indicates origin
- `#character_stats_<PC>` — Plural variant

**Custom Tags** (from templates):
- `#vitality` — HP/health related
- `#defensive` — Armor/defense related
- `#environmental_variable` — Global environmental stat
- `#rollable` — Contains dice notation

---

## Using sync_variables.py

### Start Watching
```bash
cd /Users/samuelschoberl/projects/ATLA_Campaign
python3 Mycelium/scripts/Python/sync_variables.py
```

Output:
```
Starting variable file watcher (checking every 5s)...
Press Ctrl+C to stop

============================================================
Changes detected at 2025-11-01 14:32:15
============================================================
CHANGE DETECTED: Anju/current_hp: 38 -> 37
✓ Updated character sheet: Anju
✓ Updated stat overview
```

### Options

**Different check interval** (every 10 seconds):
```bash
python3 Mycelium/scripts/Python/sync_variables.py --interval 10
```

**Verbose mode** (see all debug info):
```bash
python3 Mycelium/scripts/Python/sync_variables.py --verbose
```

**Different vault**:
```bash
python3 Mycelium/scripts/Python/sync_variables.py --vault-folder "Dms Root"
```

---

## Workflow: How It All Works Together

### Step 1: Generate Initial Files
```bash
python3 Mycelium/scripts/Python/recreate_pcs.py
```

This creates:
- Character sheets in `Player Root/PCs/<PC>/<PC> character sheet.md`
- Variable files in `Player Root/variable/PC_variables/<PC>/<PC>_*.md`
- Updates `Player Root/PCs/stat_overview.md`

### Step 2: Start the Watcher
```bash
python3 Mycelium/scripts/Python/sync_variables.py &
```

Now any changes to variable files are automatically synced to:
- Character sheets
- Stat overview

### Step 3: Make Changes

Edit a variable file or character sheet, and sync_variables automatically:
1. Detects the change (every 5 seconds)
2. Updates the character sheet
3. Updates the stat overview
4. Reports what changed

---

## Example: Change a Character's HP

### Scenario
You want to reduce Anju's current HP from 38 to 37 (taking damage).

### Option A: Edit the Variable File
1. Open `Player Root/variable/PC_variables/Anju/Anju_current_hp.md`
2. Change the value:
   ```markdown
   ```markdown
   37  # ← Changed from 38
   
   #vitality #variable_Anju #character_stat_Anju #character_stats_Anju #secondary_stat_Anju
   
   ```
   ```
3. Save the file
4. **Automatic**: sync_variables detects this and updates:
   - `Anju character sheet.md` → `| current hp | 37 |`
   - `stat_overview.md` → Anju Vitality row → `37`

### Option B: Edit Character Sheet Directly
1. Open `Player Root/PCs/Anju/Anju character sheet.md`
2. Find the Vitals section and change `current hp` value
3. **Note**: Currently sync_variables only goes one direction (variable file → sheet)
   - To make the variable file update, you'd also need to edit the variable file OR regenerate with recreate_pcs

---

## Tag Guide: What Each Tag Means

| Tag | Means | Effect |
|-----|-------|--------|
| `#variable_Anju` | "This is a variable file for Anju" | Used to identify and filter variables |
| `#vitality` | "This is a vitality stat" | Always synced to stat_overview |
| `#defensive` | "This is a defensive stat" | Always synced to stat_overview |
| `#environmental_variable` | "Global environmental stat" | Written even when value = 0 |
| `#secondary_stat_Anju` | "Derived from primary stats" | Computed from formula |
| `#primary_stat_Anju` | "Direct from character sheet" | User-entered or rarely updated |
| `#rollable` | "Contains dice notation" | Not evaluated as math expression |

---

## File Structure at a Glance

```
Player Root/
├── PCs/
│   ├── Anju/
│   │   └── Anju character sheet.md        ← Tables to update
│   ├── Tai/
│   │   └── Tai character sheet.md
│   └── stat_overview.md                   ← Summary of all vitality/defensive
│
└── variable/
    ├── secondary_stat/
    │   ├── max_hp.md                      ← Templates
    │   ├── current_hp.md
    │   └── Evasion.md
    └── PC_variables/
        ├── Anju/
        │   ├── Anju_max_hp.md             ← Generated, synced
        │   ├── Anju_current_hp.md
        │   └── Anju_Evasion.md
        └── Tai/
            ├── Tai_max_hp.md
            └── ...
```

---

## Troubleshooting

### Changes not appearing?

1. **Check variable file exists**:
   ```bash
   ls Player Root/variable/PC_variables/Anju/
   ```

2. **Check character sheet exists**:
   ```bash
   ls Player Root/PCs/Anju/
   ```

3. **Run with verbose**:
   ```bash
   python3 Mycelium/scripts/Python/sync_variables.py --verbose
   ```

4. **Check table format**:
   - Variable files: Should have `| key | value |` format
   - Character sheets: Should have markdown tables

### Variable file format wrong?

Template:
```markdown
```markdown
<VALUE>

<TAGS>

```
```

Check:
- Opening fence: `\`\`\`markdown` (with markdown info string)
- Exactly one blank line after value
- Tags on one line, space-separated
- Exactly one blank line after tags
- Closing fence: `\`\`\`` (3 backticks)

---

## Common Commands

```bash
# Start watching (default 5 second interval)
python3 Mycelium/scripts/Python/sync_variables.py

# Watch with 10 second interval
python3 Mycelium/scripts/Python/sync_variables.py --interval 10

# Watch with detailed output
python3 Mycelium/scripts/Python/sync_variables.py --verbose

# Stop watching
Ctrl+C

# Check if script has syntax errors
python3 -m py_compile Mycelium/scripts/Python/sync_variables.py

# Run only for specific PC
python3 Mycelium/scripts/Python/recreate_pcs.py --pc "Anju"
```

---

## Key Points to Remember

1. **Variable files are the source of truth** — Update these and everything else follows
2. **5-second polling** — Changes appear within 5 seconds of file modification
3. **One-way sync** — Variable files → Character sheets → Stat overview
4. **Tags control behavior** — `#vitality` and `#defensive` stats go to stat overview
5. **Format matters** — Fenced blocks must be exactly right for reading/writing to work

---

## Where to Find More Info

- **Variable file format details**: `Mycelium/scripts/manuals/variable_file_writing.md`
- **Complete sync_variables documentation**: `Mycelium/scripts/manuals/sync_variables.md`
- **recreate_pcs manual**: `Mycelium/scripts/manuals/recreate_pcs.md`
- **Script source**: `Mycelium/scripts/Python/sync_variables.py`
