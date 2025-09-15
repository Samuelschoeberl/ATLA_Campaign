Recreate PCs — CLI manual

Summary

This manual documents the command-line interface for the `recreate_pcs.py` generator and the `change_var.py` helper.

recreate_pcs.py

Purpose

- Recompute per-character secondary stats from templates under `Player Root/variable/secondary_stat` and write per-character outputs.

Location

- `Mycelium/scripts/python/recreate_pcs.py`

Usage

- Run for all PCs with run-update flag set in `Player Root/pc_primary_stats.md`:

  python3 Mycelium/scripts/python/recreate_pcs.py [--create-placeholders] [--verbose]

- Run for a single character:

  python3 Mycelium/scripts/python/recreate_pcs.py --pc "Anju"

Options

- --verbose, -v: print detailed per-stat evaluation traces and multi-pass resolution logs.
- --pc, -p: limit generation to a single PC name (case-insensitive exact match).
- --create-placeholders: create a minimal `#variable` placeholder file for any referenced variable that doesn't exist yet.

Behavior notes

- The script discovers the canonical vault path from a `Root.md` file (it uses the first non-empty, non-`#` line as the vault path). The script will refuse to continue if it can't determine a vault `variable` folder, to avoid writing into internal Mycelium folders.
- When a canonical variable root is found, the script writes per-character variable files into `<vault>/variable/PC_variables/<Character>/` with filenames prefixed by `<Character>_<originalstem>.md`.
- The generator uses a safe AST-based evaluator for formulas. It unescapes markdown-escaped operators and strips a leading `=` from formula lines.
- The script will skip copying `#template` tags into generated files but will include `#variable`, `#character_stat`, and `#character_stats` tags.
- The character sheet template `Mycelium/data/template/template_Character_Sheet.md` is used if present; `{{PC}}` and other placeholders are replaced when possible and stats are inserted into STATS_INSERT sections.

Troubleshooting

- If the script exits early with an error about the variable root, add or fix a `Root.md` file whose first non-comment line is the vault folder name (for example: `Player Root`) and ensure that folder contains a `variable/` subfolder (or allow the script to create it).

change_var.py

Purpose

- Modify or create a single `#variable` file by specifying its filename stem (filenames must be unique across the vault `variable` folder).

Location

- `Mycelium/scripts/python/change_var.py`

Usage

- Update an existing variable or create it if missing:

  python3 Mycelium/scripts/python/change_var.py --name "environmental_water_charges" --value 7 --tags "#variable #custom"

Options

- --name, -n: required — the variable filename stem (unique across the vault). Do not include `.md`.
- --value, -v: required — the numeric or string value to write into the variable file.
- --tags, -t: optional — a space-separated string of tags to include (default: `#variable`).
- --raw: optional — write the value verbatim (no fenced markdown block). If omitted, the script writes a fenced markdown block like:

  ```markdown
  <value>

  <tags>
  ```

Behavior notes

- The script locates the canonical vault from `Root.md` (same as `recreate_pcs.py`) and searches recursively under `<vault>/variable/` for a file whose stem matches `--name` (case-insensitive). If found, it's updated. If not found, a new file is created under `<vault>/variable/` named `<name>.md`.
- The script prints the path that was updated or created.

Examples

- Update an existing variable:

  python3 Mycelium/scripts/python/change_var.py -n Environmental_Water_Charges -v 5

- Create a new variable with custom tags and a string value:

  python3 Mycelium/scripts/python/change_var.py -n my_custom_flag -v "on" -t "#variable #flagged"

Contact

- This manual is generated automatically. If behavior differs from what's documented, inspect `Mycelium/scripts/python/recreate_pcs.py` and `Mycelium/scripts/python/change_var.py` for exact behavior.
