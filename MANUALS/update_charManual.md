# See MANUALS/Usage_Guide.md for a short summary of all manuals

# update_charManual

## Purpose

Short manual for `update_char.py`: how to run it, common flags, how formulas work, and how the script integrates with other automation in this repo (character creation and the bending slots updater).

## Quick usage

Update a single character (auto-discover by PC name):

```bash
python3 update_char.py --pc Anju
```

Update a specific Character Sheet file path:

```bash
python3 update_char.py --file "Players Part/PCs/Anju/Anju Character Sheet.md"
```

The script edits the sheet in-place and writes a backup `<file>.bak` before overwriting.

## Flags and behavior

- `--pc <NAME>` — locate `Players Part/PCs/<NAME>/<NAME> Character Sheet.md` and update it.
- `--file <PATH>` — update the specified file.
- `--formulas <PATH>` — load formulas from the given JSON file (defaults to `char_formulas.json`).
- `--extend-formulas` — when provided, missing formula keys are filled from built-in defaults and the combined set is used.
- `--levelup` — (if supported in your version) apply level-up logic before recomputing derived stats.
- `--backup` — create an explicit timestamped backup (the script already writes a `.bak` by default).

## What the script computes

- Reads the `## Core Stats` markdown table to gather STR/DEX/CON/INT/WIS/CHA and other core values.
- Reads `## Bending Levels` to gather element levels.
- Evaluates formulas from `char_formulas.json` (or your provided file) to compute values like Max Hitpoints, Evasion, Armor, and Element DCs.
- Inserts an "Autogen Report" section into the sheet that lists inferred values, applied overrides, and any unresolved formula identifiers.

Formulas are simple expressions that reference other named values (e.g. `10 + CON * 2`). The script uses a restricted safe-eval to avoid executing arbitrary code; only arithmetic and identifiers are allowed.

## Autogen report

After running, the script will insert an autogen report block into the sheet showing:

- Inferred values and where they were used.
- Any unresolved identifiers (tokens referenced by formulas but not defined in the formulas file or sheet).
- A short summary of how many replacements/auto-updates were applied.

You can copy values from this report into the sheet or into `char_formulas.json` to silence warnings in future runs.

## Integration with other tools in this repo

- create_pc.py: when `--run-update` is passed, `create_pc.py` will call `update_char.py` to compute derived stats immediately after creating a new sheet.
- Bending slots updater: after `update_char.py` writes a sheet the repo's `scripts/update_bending_slots.py` is invoked (when present) to regenerate the `## [[Bending Slots]]` section from the `## Bending Levels` table. This keeps slot rows in sync with levels and preserves any user-edited "current" values where possible.

If you rely on custom workflows, be aware these hooks may run automatically; you can always run `update_char.py` directly if you want a single targeted pass.

## Formulas file (`char_formulas.json`)

- Keys are identifiers used when mapping table labels to formula names. Small heuristics are used to match names (e.g. `Air Level` <-> `Airbending_Level`).
- If a formula references an identifier that isn't defined, the autogen report will list it as unresolved.
- Prefer short, stable identifiers (no spaces or use the underscore form) for easier reuse across scripts.

## Troubleshooting

- "Could not resolve formula 'HP_PER_CL'": open `char_formulas.json` and add a suitable key or update your sheet to include the referenced column. Use `char_formulas_check.py` to locate missing identifiers referenced by formulas.
- If `update_char.py` appears to do nothing, confirm it found the expected sheet path; use `--file` with the explicit path to be certain.
- If automatic bending slot changes are not visible, run `python3 scripts/update_bending_slots.py "<sheet path>"` manually to see messages and confirm slot regeneration.

## Examples

Update Anju and view the autogen report in-place:

```bash
python3 update_char.py --pc Anju
```

Use a custom formulas file and extend defaults:

```bash
python3 update_char.py --file "Players Part/PCs/Anju/Anju Character Sheet.md" --formulas my_formulas.json --extend-formulas
```

Run against a single file and then regenerate bending slots explicitly:

```bash
python3 update_char.py --file "Players Part/PCs/Anju/Anju Character Sheet.md"
python3 scripts/update_bending_slots.py "Players Part/PCs/Anju/Anju Character Sheet.md"
```

## Notes and next steps

- If you want a `--dry-run` mode (compute and print replacements without writing), I can add it quickly.
- If you prefer a different behavior for water charges (the separate slot logic used by `update_bending_slots.py`), tell me the formula you want and I will update `scripts/update_bending_slots.py` to match and optionally re-run it across all PC sheets.

## Full workflows

1. Update a single player's sheet and regenerate graphs

```bash
python3 update_char.py --pc Anju
python3 Wikigraphs.py --pc Anju -v
```

2. Batch update all PCs listed in `pcs_input.md` and recreate graphs

```bash
python3 update_char.py --sync --input pcs_input.md
python3 Wikigraphs.py --pc --all -v
```

3. Development loop: tweak formulas and test on one sheet

```bash
# edit char_formulas.json
python3 update_char.py --file "Players Part/PCs/Anju/Anju Character Sheet.md" --formulas char_formulas.json --extend-formulas
# inspect the autogen report inside the sheet
```
