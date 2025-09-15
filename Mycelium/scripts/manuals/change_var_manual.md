Quick usage examples for change_var.py

This helper writes a variable <name>.md under the vault variable folder and triggers the sheet-updater.

Examples (copy-paste):

# Set environmental_water_charges to 5 (dry-run)

python3 Mycelium/scripts/python/change_var.py --name environmental_water_charges --value 5 --dry-run

# Permanently set and trigger updater

python3 Mycelium/scripts/python/change_var.py --name environmental_water_charges --value 5

Notes:

- This script locates your variable folder automatically (uses `Root.md` helper if present, otherwise `Player Root/variable`).
- It writes a fenced markdown value with `#variable` tag so other tools can pick it up.
