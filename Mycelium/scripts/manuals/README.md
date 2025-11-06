# Mycelium Scripts — Documentation Index

**Last Updated:** October 25, 2025

This folder contains documentation for the Mycelium tooling scripts used in the ATLA Campaign project.

## Core Documentation

### Character Management

- **[sync_variables_manual.md](sync_variables_manual.md)** — Bi-directional sync between character sheets and variable files (default: watch mode)
- **[sync_variables_quickref.md](sync_variables_quickref.md)** — Quick reference for sync_variables.py commands
- **[recreate_pcs.md](recreate_pcs.md)** — PC character sheet generation and secondary stat computation
- **[recreate_npcs.md](recreate_npcs.md)** — NPC character sheet generation with element-filtered bending rules
- **[watch_and_regen_manual.md](watch_and_regen_manual.md)** — Automatic regeneration watcher with environmental variable propagation

### Variables and Stats

- **[environmental_variables.md](environmental_variables.md)** — Environmental variables system guide
- **[environmental_propagation.md](environmental_propagation.md)** — How environmental variables propagate across character sheets
- **[char_formulas_README.md](char_formulas_README.md)** — Formula system for computed stats
- **[character_sheets_manual.md](character_sheets_manual.md)** — Character sheet structure and placeholder system

### Frontend and Visualization

- **[Frontend Manual.md](Frontend Manual.md)** — Frontend behavior, UI flows, and server APIs
- **[Wikigraphs_MANUAL.md](Wikigraphs_MANUAL.md)** — Graph visualization generation (sunburst/treemap)

### File System Management

- **[Wiki_File_System_Manager_manual.md](Wiki_File_System_Manager_manual.md)** — Bulk find & replace for markdown files across directory trees

## Quick Start Guide

### 1. Sync Character Variables

**Default (watch mode, bi-directional):**
```bash
python3 Mycelium/scripts/Python/sync_variables.py
```

**One-time sync:**
```bash
python3 Mycelium/scripts/Python/sync_variables.py --once
```

### 2. Regenerate Character Sheets

**All PCs:**
```bash
python3 Mycelium/scripts/Python/recreate_pcs.py
```

**Single PC:**
```bash
python3 Mycelium/scripts/Python/recreate_pcs.py --pc Anju
```

**All NPCs:**
```bash
python3 Mycelium/scripts/Python/recreate_npcs.py
```

### 3. Auto-Watch for Changes

```bash
python3 Mycelium/scripts/Python/watch_and_regen.py
```

### 4. Generate Wikigraphs

```bash
python3 Mycelium/scripts/Python/Wikigraphs.py --root "Player Root"
```

### 5. Bulk Find & Replace

**Simple replacement:**
```bash
python3 Mycelium/scripts/Python/Wiki_File_System_Manager.py . --find oldtext --replace newtext
```

**Create wiki-links:**
```bash
python3 Mycelium/scripts/Python/Wiki_File_System_Manager.py . --find Earthbending --bracket
```

## Script Locations

All scripts are located in `Mycelium/scripts/Python/`:
- `sync_variables.py` — Bi-directional variable sync
- `recreate_pcs.py` — PC generation
- `recreate_npcs.py` — NPC generation  
- `watch_and_regen.py` — Auto-regeneration watcher
- `Wikigraphs.py` — Graph visualization
- `common.py` — Shared utilities
- `frontend_api.py` — API blueprint
- `run_backend.py` — Flask server
- `Wiki_File_System_Manager.py` — Bulk find & replace for markdown files

## Workflow Recommendations

### Development Workflow
1. Start `sync_variables.py` in watch mode (default behavior)
2. Start `watch_and_regen.py` in another terminal
3. Edit character sheets or variable files — changes sync automatically
4. When formulas need recalculation, regeneration happens automatically

### Manual Workflow
1. Edit character sheets or variables
2. Run `sync_variables.py --once` to sync changes
3. Run `recreate_pcs.py` to regenerate sheets if needed
4. Run `Wikigraphs.py` to update visualizations

## Key Concepts

### Bi-Directional Sync
The sync system works in both directions:
- **Sheet → Variable:** Edit a stat in the character sheet → variable file updates
- **Variable → Sheet:** Edit a variable file → character sheet updates

### Environmental Variables
Special variables that propagate across all character sheets:
- Stored in `Player Root/variable/`
- Automatically distributed to all PCs that meet requirements
- Element-aware (e.g., only shown to PCs with water ≥ 1)

### Auto-Regeneration
The watch system detects changes and triggers regeneration:
- Monitors character sheets for changes
- Propagates environmental variables
- Regenerates only affected characters
- Handles debouncing to avoid duplicate runs

## File Structure

```
Player Root/
├── PCs/
│   ├── Anju/
│   │   ├── Anju character sheet.md
│   │   └── Anju_variables.md
│   └── Grep/
│       └── Grep character sheet.md
└── variable/
    ├── PC_variables/
    │   ├── Anju/
    │   │   ├── Anju_max_hp.md
    │   │   ├── Anju_current_hp.md
    │   │   └── ...
    │   └── Grep/
    │       └── ...
    ├── secondary_stat/
    │   ├── max_hp.md (template)
    │   ├── evasion.md (template)
    │   └── ...
    └── environmental_water_charge.md

Dms Root/
├── NPCs/
│   └── low_earth/
│       ├── low_earth character sheet.md
│       └── Bending Rules - low_earth/
└── variable/
    └── NPC_variables/
        └── low_earth/
            └── ...
```

## Getting Help

- Check the specific manual for each tool
- Run any script with `--help` to see command-line options
- Use `--dry-run` to preview what would happen
- Use `--verbose` for detailed output

## Recent Changes (2025-10-25)

- **NEW:** Added `Wiki_File_System_Manager.py` - Streamlined bulk find & replace tool
- Cleaned up outdated scripts and manuals
- Updated all documentation to match current script behavior
- Clarified that `sync_variables.py` runs in **watch mode by default**
- Added `--once` flag documentation for one-time runs
- Documented bi-directional sync capabilities
- Updated all command examples with correct paths

## Contact

For exact behavior details, inspect the Python scripts in `Mycelium/scripts/Python/`.

#manual #documentation #mycelium
