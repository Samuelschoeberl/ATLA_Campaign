CLI manual — Mycelium scripts

Overview

This short manual documents the small set of maintenance CLI scripts in
`Mycelium/scripts/python/` used to compute secondary stats, update character
sheets, and manage per-character variables.

Files covered

- `Mycelium/scripts/python/recreate_pcs.py` — regenerate character sheets and
  per-PC variable mirrors from primary stats and secondary templates.
- `Mycelium/scripts/python/change_var.py` — change or create a single
  variable file by stem (supports a safe `--dry-run`).
- `Mycelium/scripts/python/update_sheets_for_var.py` — find templates that
  depend on a variable and update affected sheets transitively.

Important safety note

These scripts discover the vault root from the repository `Root.md` (the
first non-empty, non-`#` line). They will refuse to write if they cannot
find a declared vault root. This prevents accidental writes to internal
Mycelium folders. The canonical vault variable folder used is:

`<vault>/variable`

Per-character mirror files are written to:

`<vault>/variable/PC_variables/<safe_pc>/`

(recreate code uses `Player Root` when `Root.md` is absent but will prefer
`Root.md` discovery and fail-fast if it's misconfigured).

Quick reference — commands & flags

Recreate (compute secondaries + write sheets):

```bash
python3 Mycelium/scripts/python/recreate_pcs.py [--verbose|-v] [--pc|-p NAME] [--create-placeholders]
```

- `--verbose` / `-v` — print per-pass evaluation traces for debugging.
- `--pc NAME` / `-p NAME` — only operate on a single PC (case-insensitive).
- `--create-placeholders` — auto-create minimal `#variable` placeholder
  files for any missing variable references (created under the vault
  `variable` folder).

Change a single variable (safe dry run + backlinks):

```bash
python3 Mycelium/scripts/python/change_var.py --stem <name> --value <value> [--dry-run] [--verbose]
```

- `--dry-run` prints the backlink tree and does not write files.
- `--verbose` prints extra diagnostic information.

Update sheets for a single variable (transitive):

```bash
python3 Mycelium/scripts/python/update_sheets_for_var.py --name <stem> [--pc <PC>] [--verbose]
```

- Finds all secondary templates that reference `<stem>` (directly or
  transitively). For each affected PC: recompute, write per-PC var file,
  iterate until stable, and regenerate the sheet via
  `recreate_pcs.write_character_files`.

Templates, tags and behavior

- Secondary templates live in `Player Root/variable/secondary_stat/*.md`.
  Templates must include `#secondary_stat` to be considered.
- Tags are scanned using `#[-\w]+` (lowercased internally). Currently used
  tags:
  - `#variable` — file is a variable file (existing convention).
  - `#character_stat` / `#character_stats` — indicates a stat to mirror.
  - `#secondary_stat` — marks a secondary stat template.
  - `#current_variable` — the generator will read the existing sheet to
    preserve these values across rewrites.
  - `#vitality` — forces display of the stat in character sheets even when
    its numeric value is 0.
  - `#show_if_<var>_<op>_<n>` — conditional display tag (new); see below.

Conditional display: `#show_if_*`

Use tags of the form `#show_if_<var>_<op>_<n>` to show a stat only when a
numeric condition on another variable is true. This automates the behavior
we added for `stress level`.

- Example: `#show_if_fire_ge_1` (show when `fire >= 1`).
- Supported ops: `gt` `ge` `lt` `le` `eq` (greater than, greater-or-equal,
  etc.).
- Tags are evaluated at sheet generation time against the normalized
  variable values (numeric coercion via the existing `to_number()` logic).
- If any `#show_if_*` tag on a template evaluates true the stat is
  force-shown even if its numeric value is 0. Multiple `#show_if_*` tags
  combine as OR.

Behavioral notes

- Zero-valued secondaries are omitted from character sheets and per-PC
  variable mirrors by default. Exceptions:

  - Template has `#vitality` (always shown even when 0).
  - Template condition `#show_if_*` evaluates true (force-show).
  - Template explicitly uses `#current_variable` — preserved from existing sheet.

- The sheet writer regenerates the entire sheet from
  `Mycelium/data/template/template_Character_Sheet.md`. This keeps any
  template-driven omission or ordering rules consistent.

Examples

- Regenerate all PCs, create placeholders for missing variables, verbosely:

```bash
python3 Mycelium/scripts/python/recreate_pcs.py --create-placeholders --verbose
```

- Update all sheets affected by a changed variable:

```bash
python3 Mycelium/scripts/python/update_sheets_for_var.py -n environmental_water_charges -v
```

Troubleshooting

- "ERROR: Could not determine variable root" — add or fix `Root.md` so the
  first non-comment/non-empty line names your vault (e.g. `Player Root`).
- If a template references variables that do not exist the generator will
  either warn (and treat missing as 0) or create placeholders when
  `--create-placeholders` is used.

Developer notes

- Main logic lives in `Mycelium/scripts/python/recreate_pcs.py`.
  - `compute_secondaries()` evaluates templates iteratively with a small
    safe AST evaluator.
  - `write_character_files()` renders the sheet and writes per-PC mirrors.
- Updater script (`update_sheets_for_var.py`) imports that module and calls
  `write_character_files()` to ensure consistent rendering rules.

If you want, I can:

- Add a short unit test asserting `#show_if_*` keeps zeros visible when
  conditions hold.
- Run a full repo regeneration now and show a few sheet diffs.

---

Manual created: `Mycelium/scripts/manuals/cli_manual.md`
