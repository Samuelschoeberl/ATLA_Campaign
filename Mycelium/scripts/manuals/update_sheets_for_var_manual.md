Quick usage examples for update_sheets_for_var.py

This script recomputes dependent secondary templates and rewrites character sheets for PCs that reference the changed variable.

Examples:

# Update all PCs for environmental_water_charges (dry-run is not implemented; use verbose to inspect)

python3 Mycelium/scripts/python/update_sheets_for_var.py --name environmental_water_charges --verbose

# Limit to a single PC

python3 Mycelium/scripts/python/update_sheets_for_var.py --name Anju_str --pc Anju --verbose

Notes:

- This tool reuses the same formula evaluation as `recreate_pcs.py` and will regenerate a full character sheet using the writer in `recreate_pcs.py`.
- If you keep backups under your repo, regenerated sheets will overwrite them; ensure you have source control before running.
