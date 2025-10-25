# Archived Mycelium Scripts

**Archive Date:** 2025-10-25 16:14:41

## Purpose
These scripts were archived as part of a cleanup effort to remove outdated and unused scripts from the active Mycelium/scripts/Python directory.

## Why These Scripts Were Archived

### Categories of Archived Scripts:

1. **Old/Replaced Functionality** - Minimal stubs and experimental scripts replaced by newer implementations
2. **Deprecated Watch/Sync Scripts** - Old file watchers and sync servers superseded by current system
3. **Old Character Sheet Generators** - Legacy updaters replaced by recreate_pcs.py and recreate_npcs.py
4. **Legacy Graph/Analysis Scripts** - Old graph generators and analysis tools no longer in use
5. **Old Tag/Link Management** - Deprecated tag and link management utilities
6. **Diagnostic/Test Files** - Old test and diagnostic scripts for deprecated systems
7. **Old Variable Management** - Legacy variable creation and management scripts
8. **Old Graph Utilities** - Old graph building utilities replaced by Wikigraphs.py

## Active Scripts (NOT Archived)

The following scripts remain active and in use:
- sync_variables.py (main variable sync system)
- recreate_pcs.py (active PC sheet generator)
- recreate_npcs.py (active NPC sheet generator)
- watch_and_regen.py (file watcher for auto-regeneration)
- run_backend.py (Flask backend server)
- frontend_api.py (main API blueprint)
- common.py (shared utilities)
- generate_initiative.py
- generate_pc_sheets.py
- generate_stat_overview.py
- generate_secondary_stats.py
- Wikigraphs.py (graph visualization)
- And other actively used utilities

## Restoration

If you need to restore any of these scripts:

```bash
# Restore a single file
cp archived_YYYYMMDD_HHMMSS/script_name.py ../Python/

# Restore all files
cp archived_YYYYMMDD_HHMMSS/*.py ../Python/
```

## Safe Deletion

After confirming the system works without these scripts for a sufficient period (e.g., 30-90 days), this archive directory can be safely deleted.

