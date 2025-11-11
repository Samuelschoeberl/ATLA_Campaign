# Quick Reference Card — sync_variables.py

## Run It

```bash
python3 Mycelium/scripts/Python/sync_variables.py
```

## Stop It

```
Ctrl+C
```

## Options

| Option | Effect | Example |
|--------|--------|---------|
| `--interval N` | Check every N seconds (default 5) | `--interval 10` |
| `--verbose` | Show debug output | `--verbose` |
| `--vault-folder NAME` | Use different vault | `--vault-folder "Dms Root"` |
| `--help` | Show all options | (see below) |

## All Options

```bash
python3 Mycelium/scripts/Python/sync_variables.py --help

usage: sync_variables.py [-h] [--vault-folder VAULT_FOLDER] 
                         [--interval INTERVAL] [--verbose]

Synchronize variable files with character sheets and stat overview

optional arguments:
  -h, --help                show this help message and exit
  --vault-folder VAULT_FOLDER, -V VAULT_FOLDER
                           Vault folder name (default: Player Root)
  --interval INTERVAL, -i INTERVAL
                           Check interval in seconds (default: 5)
  --verbose, -v            Verbose output
```

---

## File Locations

| What | Where |
|------|-------|
| Variable files | `Player Root/variable/PC_variables/<PC>/<PC>_*.md` |
| Character sheets | `Player Root/PCs/<PC>/<PC> character sheet.md` |
| Stat overview | `Player Root/PCs/stat_overview.md` |
| Templates | `Player Root/variable/secondary_stat/*.md` |
| Script | `Mycelium/scripts/Python/sync_variables.py` |
| Docs | `Mycelium/scripts/manuals/` |

---

## Variable File Format

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

#vitality #variable_Anju #character_stat_Anju #secondary_stat_Anju

```
```

---

## What Each Tag Means

| Tag | Means | What It Does |
|-----|-------|-------------|
| `#vitality` | HP/health stat | Included in stat_overview |
| `#defensive` | Armor/defense stat | Included in stat_overview |
| `#environmental_variable` | Global stat | Always written (even if 0) |
| `#variable_Anju` | Belongs to Anju | Identifies PC ownership |
| `#secondary_stat_Anju` | Computed from formula | Tracked for computation |
| `#primary_stat_Anju` | User-entered | Direct from character |

---

## How It Works

```
1. You edit variable file
2. sync_variables detects change (within 5 seconds)
3. Reads new value
4. Updates character sheet
5. Updates stat_overview (if tagged #vitality/#defensive)
6. Reports the sync
7. Back to monitoring
```

---

## Common Commands

```bash
# Start with 5-second check (default)
python3 Mycelium/scripts/Python/sync_variables.py

# See everything that's happening
python3 Mycelium/scripts/Python/sync_variables.py --verbose

# Check every 10 seconds instead
python3 Mycelium/scripts/Python/sync_variables.py --interval 10

# Run in background (continues after you close terminal)
python3 Mycelium/scripts/Python/sync_variables.py &

# Check if script has any syntax errors
python3 -m py_compile Mycelium/scripts/Python/sync_variables.py

# Generate all files from templates (one-time setup)
python3 Mycelium/scripts/Python/recreate_pcs.py

# Generate for specific PC only
python3 Mycelium/scripts/Python/recreate_pcs.py --pc "Anju"
```

---

## Example: Change HP After Damage

### Step 1: Edit Variable File
Open: `Player Root/variable/PC_variables/Anju/Anju_current_hp.md`

Change:
```markdown
```markdown
37    ← Change 38 to 37

#vitality #variable_Anju #character_stat_Anju #character_stats_Anju #secondary_stat_Anju

```
```

Save the file.

### Step 2: Watch sync_variables Detect It
If running with `--verbose`:
```
CHANGE DETECTED: Anju/current_hp: 38 -> 37
✓ Updated character sheet: Anju
✓ Updated stat overview
```

### Step 3: Verify Results

**Character sheet** (`Anju character sheet.md`):
```markdown
| current hp | 37 |  ← Updated!
```

**Stat overview** (`stat_overview.md`):
```markdown
| current_hp | 37 | ... | ← Updated!
```

Done! All three locations in sync with one edit.

---

## Troubleshooting

### Changes not syncing?

```bash
# 1. Is the script running?
ps aux | grep sync_variables

# 2. Are variable files there?
ls Player Root/variable/PC_variables/Anju/

# 3. Is the file format correct?
cat Player Root/variable/PC_variables/Anju/Anju_current_hp.md
# Should see: ```markdown, value, tags, ```

# 4. Run verbose to see what's happening
python3 Mycelium/scripts/Python/sync_variables.py --verbose
```

### Character sheet not updating?

```bash
# Check sheet exists
ls Player Root/PCs/Anju/"Anju character sheet.md"

# Check it has the right table format
grep "current hp" Player Root/PCs/Anju/"Anju character sheet.md"

# Should output something like: | current hp | 38 |
```

### Stat overview not updating?

```bash
# Check the variable has #vitality tag
grep "#vitality" Player Root/variable/PC_variables/Anju/Anju_current_hp.md

# If empty: stat won't sync to overview (by design)
# Only #vitality and #defensive stats go to stat_overview
```

---

## Documentation

| Document | Read Time | Purpose |
|----------|-----------|---------|
| QUICKSTART | 5 min | Get started immediately |
| COMPLETE_GUIDE | 15 min | Understand how it works |
| ARCHITECTURE | 20 min | See system design |
| variable_file_writing | 30 min | Learn tag transformation |
| sync_variables | Reference | All features and options |
| INDEX | Reference | Find what you need |

**Start with**: `QUICKSTART_sync_variables.md`

---

## System Overview

```
Templates (recreate_pcs.py)
        ↓
Variable Files (PC_variables/)
        ↓
sync_variables.py (detects changes every 5 sec)
        ↓
    ├─ Character Sheets (always updated)
    └─ Stat Overview (if #vitality/#defensive tags)
```

---

## Key Points

- ✓ Variable files are the source of truth
- ✓ Edit one place, everything else updates
- ✓ 5-second polling means near-instant sync
- ✓ Tags control where values go
- ✓ Format must be exactly right for parsing
- ✓ One-way sync: variable files → sheets → overview
- ✓ Always include #vitality/#defensive tags for overview sync

---

## File Format Must Be Exact

✓ Correct:
```markdown
```markdown
38

#vitality #variable_Anju #character_stat_Anju #secondary_stat_Anju

```
```

✗ Wrong (missing fenced block):
```markdown
38
#vitality
```

✗ Wrong (no blank lines):
```markdown
```markdown
38
#vitality
```
```

✗ Wrong (no opening fence info):
```markdown
```
38

#vitality
```
```

---

## Emergency Commands

```bash
# Stop everything
killall python3

# Regenerate all files from scratch
python3 Mycelium/scripts/Python/recreate_pcs.py

# Check syntax
python3 -m py_compile Mycelium/scripts/Python/sync_variables.py

# Test variable file reading
python3 -c "import re; txt = open('Player Root/variable/PC_variables/Anju/Anju_current_hp.md').read(); m = re.search(r'```markdown\n(.*?)\n\n', txt, flags=re.S); print(m.group(1) if m else 'NOT FOUND')"
```

---

## One Page Workflow

```
DAY 1: Setup
└─ python3 Mycelium/scripts/Python/recreate_pcs.py

DAY 2+: Run & Use
├─ python3 Mycelium/scripts/Python/sync_variables.py
├─ Edit variable files as needed
└─ Watch everything sync automatically

Check status:
└─ ps aux | grep sync_variables
```

---

## Stats That Should Update

### Always Updated
- ✓ Character sheet tables

### If Tagged #vitality
- ✓ Stat overview → Vitality section
- ✓ Example: current_hp, max_hp

### If Tagged #defensive
- ✓ Stat overview → Defensive section
- ✓ Example: Evasion, Armor values

### If Tagged #environmental_variable
- ✓ Written to variable files even when 0
- ✓ Not typically in stat_overview

---

## Integration

Works with:
- ✓ recreate_pcs.py (generates initial files)
- ✓ Character sheet markdown files
- ✓ Stat overview markdown file
- ✓ Any markdown table format

---

Print this card or bookmark the manuals for quick reference!

For full documentation: `Mycelium/scripts/manuals/INDEX_documentation.md`
