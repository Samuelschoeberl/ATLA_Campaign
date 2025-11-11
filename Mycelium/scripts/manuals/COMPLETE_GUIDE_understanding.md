# Understanding Variable Synchronization: Complete Guide

## What Was Created

You now have a complete variable synchronization system consisting of:

1. **sync_variables.py** — The main script that monitors and syncs changes
2. **Detailed documentation** — Understanding how the system works
3. **Quick start guides** — For immediate usage

---

## The Problem This Solves

In your ATLA campaign system, you have:
- **Variable files** (one per stat per character)
- **Character sheets** (with multiple tables)
- **Stat overview** (summary table)

Before sync_variables.py:
- **Manual work** — Any change to a variable file had to be manually copied to sheets and overview
- **Inconsistency** — Easy to forget to update one location, leaving data out of sync
- **Error-prone** — Manual copying leads to typos and mistakes

After sync_variables.py:
- **Automatic sync** — Changes propagate in seconds
- **Consistent** — Single source of truth (variable files)
- **Hands-free** — Just edit the variable file, everything else updates

---

## How It All Fits Together

### The Variable File System

```
Each stat is stored as a separate file:
├── Anju_max_hp.md (38)
├── Anju_current_hp.md (38)
├── Anju_Evasion.md (11)
├── Tai_max_hp.md (50)
└── ... (hundreds of files)

Each file has format:
├── Value in fenced markdown block
├── Tags that describe what this stat is
└── Character-specific tags for tracking
```

### The Tag System

Tags are labels that tell sync_variables what to do:

```
#vitality       ─→ "This stat goes in Vitality section of stat_overview"
#defensive      ─→ "This stat goes in Defensive section of stat_overview"
#variable_Anju  ─→ "This variable belongs to Anju"
#secondary_stat ─→ "This stat is computed from primary stats"
```

### The Sync Engine

```
5-second polling loop:
1. Check which variable files have been modified
2. Read the new values
3. Update character sheets with new values
4. Update stat_overview for #vitality/#defensive stats
5. Report what changed
6. Wait 5 seconds, repeat
```

---

## Tag Transformation: The Complete Story

### Where Tags Come From

**Primary stats**: User-entered in `Player Root/pc_primary_stats.md`
```markdown
| Anju | Strength | 1 | yes |
```
Gets tags: `#variable_Anju #character_stat_Anju #primary_stat_Anju`

**Secondary stats**: Templates in `Player Root/variable/secondary_stat/`
```markdown
`CON * 2 + 4`
#secondary_stat #vitality
```
Gets tags: `#vitality #variable_Anju #character_stat_Anju #secondary_stat_Anju`

### How Tags Are Transformed

**Rule 1: Preserve custom tags**
- `#vitality` stays as `#vitality` (not suffixed)
- `#defensive` stays as `#defensive`
- These describe what the stat represents

**Rule 2: Remove template markers**
- `#template` tags are NOT copied to variable files
- We keep the computed value, not the formula

**Rule 3: Add character-specific required tags**
- Every stat gets `#variable_<PC>` to track it belongs to this PC
- Every stat gets `#character_stat_<PC>` and `#secondary_stat_<PC>` or `#primary_stat_<PC>`

**Result**: Each variable file has all needed info to be processed correctly

### Why This Matters

When sync_variables.py reads a file, it:
1. **Sees `#vitality`** → Decides "include this in stat_overview"
2. **Sees `#variable_Anju`** → Knows "this belongs to Anju"
3. **Sees `#secondary_stat_Anju`** → Knows "this is a computed stat"

These tags control what happens to the value.

---

## The Complete Workflow

### Step 1: Initialize (One time)
```bash
python3 Mycelium/scripts/Python/recreate_pcs.py
```
- Reads primary stats from pc_primary_stats.md
- Reads templates from secondary_stat/
- Computes all values
- Creates variable files with proper tags
- Creates character sheets
- Creates stat_overview.md

### Step 2: Monitor (Continuous)
```bash
python3 Mycelium/scripts/Python/sync_variables.py &
```
- Runs in background
- Watches for changes every 5 seconds
- When a variable file changes:
  - Updates character sheet
  - Updates stat_overview (if tagged appropriately)
  - Reports the change

### Step 3: Use (Normal workflow)
```
When you want to make a change:
1. Edit the variable file (or character sheet)
2. sync_variables detects it (within 5 seconds)
3. Everything gets updated automatically
4. Done!
```

---

## Real Example: Anju Takes Damage

### Initial State
```
Variable file:   Anju_current_hp.md contains 38
Character sheet: | current hp | 38 |
Stat overview:   | current_hp | 38 | Anju | Vitality
```

### User Action
Edit `Anju_current_hp.md`:
```markdown
```markdown
37    ← Changed from 38

#vitality #variable_Anju #character_stat_Anju #character_stats_Anju #secondary_stat_Anju

```
```

### What sync_variables Does

**Detect** (at 5-second mark):
```
Scanning... found Anju_current_hp.md modified
Reading value... 37 (was 38)
Change detected: Anju/current_hp 38 → 37
```

**Sync to character sheet**:
```markdown
Before: | current hp | 38 |
After:  | current hp | 37 |
```

**Sync to stat overview** (because it has #vitality tag):
```markdown
Before: | current_hp | 38 | Anju | Vitality
After:  | current_hp | 37 | Anju | Vitality
```

**Report**:
```
CHANGE DETECTED: Anju/current_hp: 38 -> 37
✓ Updated character sheet: Anju
✓ Updated stat overview
```

### Final State
```
Variable file:   Anju_current_hp.md contains 37 ✓
Character sheet: | current hp | 37 | ✓
Stat overview:   | current_hp | 37 | Anju | Vitality ✓
```

All three sources are now in sync, with just one manual edit!

---

## Key Concepts

### Variable Files Are Central
```
Variable files = Source of truth
Character sheet = Mirror/display
Stat overview = Summary view

All flow from variable files
```

### Tags Control Behavior
```
#vitality         → Include in stat_overview under Vitality
#defensive        → Include in stat_overview under Defensive
#environmental    → Always write file, even if value is 0
#variable_Anju    → Belongs to Anju
#primary_stat     → User-entered value
#secondary_stat   → Computed from formula
```

### One-Way Synchronization
```
Variable files → Character sheets → Stat overview

Currently, changes flow in one direction.
The watcher doesn't yet sync character sheet edits back to variable files.
(This could be added as a future enhancement)
```

### 5-Second Polling
```
Check → Detect → Sync → Report → Wait 5 sec → Check
```

Very reliable, easy to monitor, low resource usage.

---

## File Organization

### Variable Root
```
Player Root/
└── variable/
    ├── secondary_stat/                    (Templates)
    │   ├── max_hp.md
    │   ├── current_hp.md
    │   └── ...
    └── PC_variables/                      (Generated)
        ├── Anju/
        │   ├── Anju_max_hp.md
        │   ├── Anju_current_hp.md
        │   └── ...
        ├── Tai/
        ├── Rio/
        └── ...
```

### PC Sheets
```
Player Root/
└── PCs/
    ├── Anju/
    │   └── Anju character sheet.md
    ├── Tai/
    │   └── Tai character sheet.md
    └── stat_overview.md
```

---

## Using sync_variables.py

### Start It
```bash
python3 Mycelium/scripts/Python/sync_variables.py
```

### Options
```bash
# Check every 10 seconds instead of 5
--interval 10

# See detailed debug info
--verbose

# Use a different vault
--vault-folder "Dms Root"
```

### Stop It
```bash
Ctrl+C
```

### Monitor It
```bash
# In another terminal, watch the output
tail -f log_file.txt  (if redirected)

# Or just watch the terminal where it's running
```

---

## How To: Common Tasks

### Task: Update a PC's HP after damage
1. Open `Player Root/variable/PC_variables/<PC>/<PC>_current_hp.md`
2. Change the value
3. Save
4. Within 5 seconds: Character sheet and stat_overview update automatically

### Task: Change an armor value
1. Open the corresponding armor variable file
2. Change the value
3. Save
4. Within 5 seconds: Synced everywhere

### Task: Force a full regeneration
1. Run: `python3 Mycelium/scripts/Python/recreate_pcs.py`
2. This recomputes everything from templates
3. Variable files are recreated
4. Sheets are regenerated

### Task: Monitor changes in real-time
1. Start sync_variables: `python3 Mycelium/scripts/Python/sync_variables.py --verbose`
2. Edit variable files in another terminal
3. Watch the watcher detect and sync changes

---

## Understanding the Tag System in Depth

### Why Multiple Tags?

```
#variable_Anju
├─ Part 1: "variable" says "I'm a variable file"
└─ Part 2: "_Anju" says "I belong to Anju"

This allows:
- Finding all variables: grep for "#variable"
- Finding all Anju variables: grep for "#variable_Anju"
- Filter by character: grep for "_Anju"
```

### The Suffix Pattern

```
#variable      → #variable_Anju
#secondary_stat → #secondary_stat_Anju
#character_stat → #character_stat_Anju

But NOT:
#vitality → #vitality (not suffixed!)
#defensive → #defensive (not suffixed!)

Why? Because custom tags are meaningful across characters.
Required tags track ownership with suffixes.
```

### Reading Tags

sync_variables.py extracts tags using regex:
```python
# Find this pattern in the file
```markdown
<value>

<tags>

```

# Extract tags
tags = re.findall(r'#([A-Za-z0-9_\-]+)', tag_line)
# Result: ['vitality', 'variable_Anju', 'secondary_stat_Anju', ...]
```

---

## Troubleshooting

### Changes not syncing?

**Check 1**: Is sync_variables running?
```bash
ps aux | grep sync_variables
```

**Check 2**: Do the variable files exist?
```bash
ls Player Root/variable/PC_variables/
```

**Check 3**: Are they in the right format?
```bash
cat Player Root/variable/PC_variables/Anju/Anju_current_hp.md
# Should see: ```markdown, value, tags, ```
```

**Check 4**: Run with verbose to see what's happening
```bash
python3 Mycelium/scripts/Python/sync_variables.py --verbose
```

### Tags not being used correctly?

**Check tags in the file**:
```bash
grep "#vitality" Player Root/variable/PC_variables/Anju/Anju_current_hp.md
# If empty, the stat won't appear in stat_overview
```

**Regenerate variable files**:
```bash
python3 Mycelium/scripts/Python/recreate_pcs.py
```

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────┐
│  Templates                                          │
│  (secondary_stat/, pc_primary_stats.md)            │
└────────────┬────────────────────────────────────────┘
             │
             │ recreate_pcs.py
             │ (generates + tags)
             ▼
┌─────────────────────────────────────────────────────┐
│  Variable Files                                     │
│  (PC_variables/PC/PC_*.md)                          │
│  ├─ Value                                           │
│  └─ Tags for routing                                │
└────────┬───────────────────────────────┬────────────┘
         │                               │
         │ sync_variables.py             │
         │ (detects changes)             │
         ▼                               ▼
    Character Sheets               Stat Overview
    (display tables)               (summary tables)
```

---

## What Makes This System Work

1. **Clear data structure** — Variable files have consistent format
2. **Unique tags** — Tags describe what each stat is
3. **Character suffixes** — Track ownership and enable filtering
4. **Polling mechanism** — Reliable, simple detection
5. **Regex-based updates** — Preserve file structure while changing values
6. **Source of truth** — Variable files are the single source

---

## Next Steps

1. **Try it**: `python3 Mycelium/scripts/Python/sync_variables.py --verbose`
2. **Edit a variable file**: Change a value in `PC_variables/`
3. **Watch it sync**: See the change propagate
4. **Explore**: Read the detailed manuals for deeper understanding
5. **Optimize**: Adjust interval if needed, add more features

---

## Documentation Files

| File | Purpose |
|------|---------|
| `sync_variables.md` | Complete manual with all options |
| `variable_file_writing.md` | Deep dive into tag transformation |
| `QUICKSTART_sync_variables.md` | Fast reference guide |
| `ARCHITECTURE_dataflow.md` | System diagrams and flows |
| `sync_variables.py` | The actual script |

Read them in this order:
1. Start with QUICKSTART
2. Explore ARCHITECTURE for data flow
3. Read sync_variables.md for complete details
4. Dive into variable_file_writing.md for the technical details

---

## Summary

You now have a complete system that:
- ✓ Stores stats in individual variable files
- ✓ Tracks stat ownership with character-specific tags
- ✓ Routes stats to appropriate display locations based on tags
- ✓ Automatically synchronizes changes across sheets and overview
- ✓ Polls every 5 seconds for maximum reliability
- ✓ Handles missing files gracefully
- ✓ Provides detailed logging and debugging

This enables a workflow where you:
1. Edit a single variable file
2. Everything else updates automatically
3. Never manually sync stats again
4. Have a single source of truth

Enjoy your synchronized campaign system!
