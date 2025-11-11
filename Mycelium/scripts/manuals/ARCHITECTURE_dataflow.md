# Architecture and Data Flow Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    ATLA Campaign System                          │
└─────────────────────────────────────────────────────────────────┘

                          [Templates]
                              │
                ┌─────────────┼─────────────┐
                │             │             │
         Primary Stats   Secondary Stats  Environmental
         (pc_primary_    (Player Root/    (Player Root/
          stats.md)     variable/secondary_stat/)  variable/environmental/)
                │             │             │
                └─────────────┼─────────────┘
                              │
                              ▼
                   ╔═════════════════════╗
                   ║  recreate_pcs.py    ║
                   ║  (Generate Files)   ║
                   ╚═════════════════════╝
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
        [Variable Files]          [Character Sheets]
    PC_variables/<PC>/         PCs/<PC>/<PC> character
         <PC>_*.md                sheet.md
                │                    │
                │                    │
                └────────┬───────────┘
                         │
                         ▼
              ╔═════════════════════╗
              ║sync_variables.py    ║ ◄── [Watch Loop: 5 sec polling]
              ║(Sync Changes)       ║
              ╚═════════════════════╝
                         │
                ┌────────┴────────┐
                │                 │
                ▼                 ▼
        [Character Sheets]   [Stat Overview]
        (Updated values)     PCs/stat_
                             overview.md
```

---

## Data Flow: Complete Cycle

### Phase 1: Generation (One-time or periodic)

```
┌──────────────────────────────────────────────────────────────┐
│  recreate_pcs.py runs                                        │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
      ┌───────────────────────────────────────┐
      │ Load primary stats from                │
      │ Player Root/pc_primary_stats.md        │
      │                                        │
      │ Read: Strength=1, Dexterity=2, etc.   │
      └───────────────────────────────────────┘
                              │
                              ▼
      ┌───────────────────────────────────────┐
      │ Load secondary stat templates from    │
      │ Player Root/variable/secondary_stat/  │
      │                                        │
      │ Read: max_hp formula, Evasion, etc.   │
      │ Extract tags: #vitality, #defensive   │
      └───────────────────────────────────────┘
                              │
                              ▼
      ┌───────────────────────────────────────┐
      │ Compute secondary stats by:           │
      │ 1. Substitute primary values          │
      │ 2. Evaluate formulas                  │
      │ 3. Iterative passes until stable      │
      │                                        │
      │ Example: max_hp = CON*2+4 = 2*2+4=8  │
      └───────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
    Write Primary      Write Secondary       Write Character
    Variables          Variables            Sheets
        │                   │                    │
        ▼                   ▼                    ▼
  Anju_Strength.md   Anju_max_hp.md         Anju character
     (value: 1)        (value: 8)           sheet.md
  [tags: #primary_]  [tags: #vitality,
                      #secondary_]
```

### Phase 2: Synchronization (Continuous monitoring)

```
┌────────────────────────────────────────────────────────────────┐
│  sync_variables.py WATCH LOOP (every 5 seconds)               │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
      ┌───────────────────────────────────────┐
      │ Scan variable file directory:          │
      │ PC_variables/<PC>/*.md                 │
      │                                        │
      │ Check modification times               │
      └───────────────────────────────────────┘
                              │
                              ▼
      ┌───────────────────────────────────────┐
      │ For each file that changed:           │
      │ 1. Compare mtime with cached          │
      │ 2. If different, file was modified    │
      │ 3. Read new value from fenced block   │
      │                                        │
      │ Example: Anju_current_hp.md mtime     │
      │ changed, value changed to 37          │
      └───────────────────────────────────────┘
                              │
                              ▼
      ┌───────────────────────────────────────┐
      │ Report changes:                        │
      │ CHANGE DETECTED: Anju/current_hp      │
      │ 38 -> 37                              │
      └───────────────────────────────────────┘
                              │
        ┌─────────────────────┴──────────────────┐
        │                                        │
        ▼                                        ▼
    Update Character Sheet             Update Stat Overview
        │                                        │
        ▼                                        ▼
    Find table row:                    Check tags:
    | current hp | 38 |               Is #vitality
        │                              or #defensive?
        │                                  │
        ▼                                  ▼
    Replace value:                    If YES:
    | current hp | 37 |               Find row in overview
        │                              Replace value
        ▼                                  │
    Write file                            ▼
    (Anju character                    Write file
     sheet.md)                         (stat_overview.md)
        │                                  │
        └──────────────┬───────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Report completion:           │
        │ ✓ Updated character sheet    │
        │ ✓ Updated stat overview      │
        └──────────────────────────────┘
```

---

## File Transformation Chain

```
┌─────────────────────────────────────────────────────────────┐
│ TEMPLATE                                                    │
│ Player Root/variable/secondary_stat/max_hp.md             │
│                                                             │
│ Content:                                                    │
│ `CON * 2 + 4`                                             │
│                                                             │
│ Tags: #secondary_stat #vitality                           │
└─────────────────────────────────────────────────────────────┘
                              │
                    ╔═════════╨═════════╗
                    │ recreate_pcs.py   │
                    │ transforms:       │
                    │ 1. Compute value  │
                    │ 2. Add tags       │
                    ║ 3. Create file    │
                    ╚═════════╤═════════╝
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ VARIABLE FILE                                               │
│ Player Root/variable/PC_variables/Anju/Anju_max_hp.md    │
│                                                             │
│ Content:                                                    │
│ ```markdown                                                 │
│ 38                                                          │
│                                                             │
│ #vitality #variable_Anju #character_stat_Anju ...        │
│ ```                                                         │
│                                                             │
│ Tags analyzed by sync_variables:                           │
│ - #vitality ─────────────────────────────┐                │
│ - #variable_Anju (track for Anju)        │                │
│ - #character_stat_Anju (per-char stat)   │                │
│ - #secondary_stat_Anju (computed stat)   │                │
└─────────────────────────────────────────────────────────────┘
                              │
                    ╔═════════╨═════════╗
                    │ sync_variables.py │
                    │ reads value:      │
                    │ 38                │
                    │                   │
                    │ checks tags:      │
                    │ "has #vitality"   │
                    ║ ─> include in    │
                    │    stat_overview  │
                    ╚═════════╤═════════╝
                              │
                ┌─────────────┴──────────────┐
                │                           │
                ▼                           ▼
┌─────────────────────────┐    ┌───────────────────────────┐
│ CHARACTER SHEET         │    │ STAT OVERVIEW             │
│ Anju character sheet.md │    │ PCs/stat_overview.md      │
│                         │    │                           │
│ | max_hp | 38 |        │    │ ### Anju                  │
│ | current_hp | 38 |    │    │ **Vitality**              │
│ | Evasion | 11 |       │    │ | max_hp | 38 | File ... │
│ ...                     │    │ | current_hp | 38 | ...  │
│                         │    │ ...                       │
└─────────────────────────┘    └───────────────────────────┘
```

---

## Tag Flow Through System

```
TEMPLATE (source)
│
├─ Has: #secondary_stat #vitality
│
▼
recreate_pcs.py processing
│
├─ Preserves: #vitality
├─ Removes: #template (if present)
├─ Adds required suffixed: #variable_<PC>, #secondary_stat_<PC>, etc.
│
▼
VARIABLE FILE (generated)
│
├─ Tags: #vitality #variable_Anju #character_stat_Anju #secondary_stat_Anju
│
▼
sync_variables.py reading
│
├─ Extracts: #vitality, #variable_Anju, #secondary_stat_Anju, etc.
├─ Decision: "Has #vitality" → include in stat_overview
│
▼
SYNC TARGETS (updated)
│
├─ Character Sheet: Always updated
├─ Stat Overview: Updated if #vitality or #defensive present
```

---

## Directory Structure at Sync Time

```
Player Root/
│
├── PCs/
│   ├── Anju/
│   │   └── Anju character sheet.md
│   │       ├─ | Strength | 1 |
│   │       ├─ | max_hp | 38 |
│   │       ├─ | current_hp | 38 |
│   │       ├─ | Evasion | 11 |
│   │       └─ ... (other stats in tables)
│   │
│   ├── Tai/
│   │   └── Tai character sheet.md
│   │
│   └── stat_overview.md
│       ├─ ### Anju
│       │  **Vitality**
│       │  | current_hp | 38 | Player Root/variable/PC_variables/Anju/Anju_current_hp.md |
│       │  | max_hp | 38 | Player Root/variable/PC_variables/Anju/Anju_max_hp.md |
│       │
│       │  **Defensive**
│       │  | Evasion | 11 | Player Root/variable/PC_variables/Anju/Anju_Evasion.md |
│       │
│       └─ (repeated for all PCs)
│
└── variable/
    ├── secondary_stat/
    │   ├── max_hp.md (template: CON*2+4, tags: #secondary_stat #vitality)
    │   ├── current_hp.md
    │   ├── Evasion.md
    │   └── ...
    │
    └── PC_variables/
        ├── Anju/
        │   ├── Anju_Strength.md
        │   │   ```markdown
        │   │   1
        │   │   #variable_Anju #primary_stat_Anju ...
        │   │   ```
        │   │
        │   ├── Anju_max_hp.md
        │   │   ```markdown
        │   │   38
        │   │   #vitality #variable_Anju #secondary_stat_Anju ...
        │   │   ```
        │   │
        │   └── ... (all other stats)
        │
        └── Tai/
            ├── Tai_Strength.md
            └── ... (all other stats)
```

---

## Script Interaction Map

```
┌─────────────────────────────────────────────────────┐
│                  recreate_pcs.py                    │
│  ┌────────────────────────────────────────────────┐ │
│  │ Generate initial files on demand               │ │
│  │ - Character sheets                              │ │
│  │ - Variable files (with computed values)         │ │
│  │ - Tags transformation                           │ │
│  └────────────────────────────────────────────────┘ │
│          └─────────────┬──────────┐                 │
│                        │          │                 │
│                        ▼          ▼                 │
│                   Character   Variable              │
│                   Sheets      Files                 │
└─────────────────────────────────────────────────────┘
         │
         │ (Whenever values need to be recomputed)
         │
┌─────────────────────────────────────────────────────┐
│               sync_variables.py                     │
│  ┌────────────────────────────────────────────────┐ │
│  │ Continuous synchronization                     │ │
│  │ - Monitor variable files for changes           │ │
│  │ - Sync to character sheets                     │ │
│  │ - Sync to stat_overview                        │ │
│  │ - Apply tag-based filtering                    │ │
│  └────────────────────────────────────────────────┘ │
│     ▲              │              │                 │
│     │              ▼              ▼                 │
│     │          Updated        Updated               │
│     │          Sheets          Stats                │
│     │                                               │
│     └──────── [Detects changes]                    │
│              Every 5 seconds                        │
└─────────────────────────────────────────────────────┘
```

---

## Update Propagation Example

### Scenario: Player takes damage (current_hp reduced from 38 to 37)

```
TIME 0:00 — User edits variable file
─────────────────────────────────────
Anju_current_hp.md: 38 → 37
(File mtime changes)

TIME 0:05 — sync_variables.py detects change
────────────────────────────────────────────
┌─ Scans variable files
├─ Sees: Anju_current_hp.md mtime changed
├─ Reads: New value = 37
├─ Compares: Cache had 38, now 37 → Different!
└─ Reports: CHANGE DETECTED: Anju/current_hp: 38 -> 37

TIME 0:06 — Updates character sheet
──────────────────────────────────
Anju character sheet.md:
  Before: | current hp | 38 |
  After:  | current hp | 37 |

Checks tags: #vitality found
→ This stat should be in stat_overview

TIME 0:07 — Updates stat_overview
──────────────────────────────────
PCs/stat_overview.md → Anju → Vitality section:
  Before: | current_hp | 38 | ...
  After:  | current_hp | 37 | ...

TIME 0:08 — Reports completion
───────────────────────────────
✓ Updated character sheet: Anju
✓ Updated stat overview

FINAL STATE
───────────
Variable file:   Anju_current_hp = 37
Character sheet: Anju current_hp = 37
Stat overview:   Anju current_hp = 37
(All in sync)
```

---

## Key Design Principles

| Principle | Implementation |
|-----------|-----------------|
| **Variable files are source of truth** | sync_variables reads from these files first |
| **Tag-based routing** | `#vitality`/`#defensive` tags determine sync targets |
| **One-way sync** | Variable files → Sheets → Overview (not bidirectional) |
| **Polling instead of file watches** | More portable, simpler, less resource-intensive |
| **Character-specific tags** | `_<PC>` suffixes track ownership |
| **Non-destructive updates** | Regex replacements preserve file structure |
| **Graceful degradation** | Missing files/fields don't crash the watcher |

