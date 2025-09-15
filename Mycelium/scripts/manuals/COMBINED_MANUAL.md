Last updated: 2025-09-11

Update summary: Combined manual assembled from individual MANUALS files on 2025-09-11.

---

# Combined Manual

This file merges the following manuals into a single reference for convenience:

- char_formulas_README.md
- create_charManual.md
- RTFM - Usage_Guide.md
- update_charManual.md
- Wiki_File_System_Manager – MANUAL.md
- Wikigraphs_MANUAL.md

---

## char_formulas_README.md

Character Formulas (README)

## Summary

Formulas used by `update_char.py` live in `char_formulas.json`. The default
formulas provide common derived stats such as Max Hit Points, Evasion and
Armor. The updater will add missing defaults if it detects candidate keys in
the workspace.

If you edit `char_formulas.json`, keep expressions simple and safe. The
updater supports a limited, safe expression evaluator (no arbitrary code
execution).

## Workflows

1. Validate formulas file quickly

```bash
python3 char_formulas_check.py char_formulas.json
```

2. Add a default for a missing key and test on one sheet

```bash
# edit char_formulas.json
python3 update_char.py --file "Players Part/PCs/Anju/Anju Character Sheet.md" --formulas char_formulas.json --extend-formulas
```

3. Run across all PCs as a batch

```bash
python3 update_char.py --sync --input pcs_input.md
```

Note: `update_char.py`, `Wikigraphs.py`, and related orchestration scripts now
prefer the first discovered `PC Character Sheets` folder anywhere under the
repository subtree when locating or creating per-PC Character Sheets. If you
need to target a specific location use `--file <path>` or `--out-root` where
available. Also note that when running orchestration, `--all` will override
`--pc` (i.e. `Wikigraphs.py --all` will run across all PCs even if `--pc` is
provided).

# See MANUALS/Usage_Guide.md for a short summary of all manuals

# char_formulas conventions (short)

This document explains the recommended canonical naming for keys used in `char_formulas.json` and a short summary of how `char_formulas_check.py` matches tokens.

## Canonical key naming (recommendation)

- Use human-friendly Title Case for formula keys that correspond to sheet labels: e.g. `Air Level`, `Manually Rolled HP`, `Waterbending Level`.
- Avoid mixing many variants in the JSON; prefer one canonical key and add a minimal alias only when necessary for backward compatibility.
- Prefer explicit names for single concepts (e.g., `HP_PER_CL` or `Manually Rolled HP`) and map them consistently in `char_formulas.json`.

Examples:

- `Air Level` -> canonical name for a character's air level.
- `Waterbending Level` -> water level (if you prefer `Water Level` use it consistently across sheets and formulas).
- `Manually Rolled HP` -> total manually rolled HP (add an alias like `Manually_Rolled_Hitpoints` only if needed).

## Checker heuristics (how `char_formulas_check.py` works)

- The checker normalizes tokens before matching:
  - Strips common wiki/markdown punctuation (`[[`, `]]`, `(`, `)`, `|`, `:`, `,`, etc.).
  - Collapses underscores and whitespace into canonical spaced/underscore variants.
  - Removes the substring `bending` for matching convenience (so `Airbending`  `Air`).
  - Generates variants: original, spaced, underscored, lowercased, and no-`bending` variants.
- Greedy longest-match extraction: the checker attempts to match longest multi-word spans against known normalized keys to reduce fragmentation (so `Manually Rolled HP` is matched as a single token, not three separate tokens).
- Numeric tokens are ignored in missing-identifier reports.

## How to run

- From the repo root:

```bash
python3 char_formulas_check.py char_formulas.json
```

The script prints any tokens referenced by formulas that are not matched by the defined keys or their normalized variants.

## Tips

- When adding a new sheet label or column in `pcs_input.md`, add the same key (or a minimal alias) to `char_formulas.json` so formulas referencing that label resolve.
- If you choose to rename keys to `snake_case` or another convention, update both `char_formulas.json` and any sheet/template files to match; the checker will still attempt many common variants but consistency reduces surprises.

---

## create_charManual.md

# See MANUALS/Usage_Guide.md for a short summary of all manuals

# create_charManual

## Purpose

This short manual explains how to quickly create a Character Sheet using `create_pc.py` and (optionally) generate the corresponding HTML graphs with `Wikigraphs.py` immediately after creation.

## Prerequisites

- `update_char.py`  computes derived stats inside the sheet (recommended).
- `Wikigraphs.py`  creates sunburst/treemap HTML files for the PC (optional).

Character sheets: `Players Part/PCs/<Name>/<Name> Character Sheet.md`

Note: when present, scripts in this repository now prefer the first discovered
`PC Character Sheets` folder found anywhere under the repository subtree and
will create/read PC folders there instead of the legacy `Players Part/PCs`
path. If you want to force a different location, pass `--out-root` to
`create_pc.py` or use explicit `--file`/`--pc` arguments when running
`update_char.py`/`Wikigraphs.py`.

Create a character named Anju, compute derived stats, and immediately generate embedded graphs:

```bash
python3 create_pc.py --name Anju \
  --str 4 --dex 4 --con 2 --int 3 --wis 3 --cha 2 \
  --water 3 --earth 1 --air 0 --fire 0 --spirit 1 \
  --run-update --make-graphs --embed-graphs --graphs-verbose
```

What this does:

- Writes `Players Part/PCs/Anju/Anju Character Sheet.md`.
- If `--run-update` is given and `update_char.py` exists, it will run it to compute and write derived stats into the sheet.
- If `--make-graphs` is given and `Wikigraphs.py` exists, it will run `Wikigraphs.py --pc Anju` (add `--embed` and `--verbose` depending on flags) and write two files:

  - `graphs/Anju_wikigraph_sunburst.html`
  - `graphs/Anju_wikigraph_treemap.html`

  ## NPCs (DM workflow)

  There is a companion script for NPCs named `create_npc.py` that mirrors `create_pc.py` but targets the DM-facing NPC folder structure.

  Quick single-NPC example  create a DM-facing NPC sheet, compute derived stats, and optionally generate embedded graphs:

  ```bash
  python3 create_npc.py --npc "Lady Kiri" \
    --str 3 --dex 2 --con 3 --int 2 --wis 4 --cha 3 \
    --water 2 --earth 1 --air 0 --fire 0 --spirit 0 \
    --run-update --make-graphs --embed-graphs
  ```

  What this does:

  - Writes `DMs Part/NPCs/Lady Kiri/Lady Kiri NPC Sheet.md`.
  - Adds or updates the DM index at `DMs Part/NPCs/npcs_input.md` (a table similar to `pcs_input.md`) so the NPC can be tracked and recreated in bulk.
  - If `--run-update` is given and `update_char.py` exists, `create_npc.py` will run it with the sheet path to compute derived stats.
  - If `--make-graphs` is given and `Wikigraphs.py` exists, it will run `Wikigraphs.py --pc "Lady Kiri"` (add `--embed` and `--verbose` depending on flags) and write graph files in the repo `graphs/` directory.

  ## Create many NPCs from `npcs_input.md`

  If you maintain a table of NPCs in a markdown file (for example `DMs Part/NPCs/npcs_input.md`), you can create them in bulk:

  ```bash
  python3 create_npc.py --input-file "DMs Part/NPCs/npcs_input.md" --run-update --make-graphs
  ```

  `create_npc.py` accepts the same core flags as `create_pc.py` (`--str/--dex/--con/--int/--wis/--cha`, `--air/--water/--earth/--fire/--spirit`, `--manual-rolled-hp`, `--out-root`, `--run-update`, `--make-graphs`, `--embed-graphs`, `--graphs-verbose`) but defaults are DM-oriented (default `--out-root` is `DMs Part/NPCs`).

  Small notes specific to NPC usage:

  - The default output root for NPCs is `DMs Part/NPCs`; if you prefer a different folder, pass `--out-root`.
  - `npcs_input.md` created by the script lives inside the chosen `--out-root` by default; the script will create parent directories as needed.
  - Bulk parsing is tolerant of wikilinks and common column name variants (same behaviour as `create_pc.py`).

  Troubleshooting (NPC-specific)

  - If `create_npc.py` cannot find the input table you passed to `--input-file`, ensure the path is correct relative to the repository root or pass an absolute path.
  - If `update_char.py` reports "Could not locate character sheet", run it with `--file <path-to-sheet>` rather than `--pc` for DM sheets whose path isn't under `Players Part/PCs`.
  - If graphs are not produced, run `Wikigraphs.py --pc "Lady Kiri" --verbose` manually to inspect filtering and file creation.

---

## RTFM - Usage_Guide.md

One-page cheat sheet linking to the full manuals. Keep this file short 
use the linked manuals for details.

## Key quick commands

- Create a PC and generate graphs:

  ```bash
  python3 create_pc.py --name Bob --run-update --make-graphs
  ```

- Update a single Character Sheet:

  ```bash
  python3 update_char.py --pc Bob
  ```

- Regenerate root + per-PC graphs (union of `pcs_input.md` and existing HTMLs):

  ```bash
  python3 Wikigraphs.py --pc --all -v
  ```

## Where to look

- Graphs: `graphs/<Name>_wikigraph_sunburst.html` and
  `graphs/<Name>_wikigraph_treemap.html`
- Character sheets: `Players Part/PCs/<Name>/<Name> Character Sheet.md` (scripts now prefer a repo-level `PC Character Sheets` folder when present)

## Short workflows (links)

- Manual refresh colors + graphs: [[MANUALS/update_recolouring.py|update_recolouring]] + [[MANUALS/Wikigraphs_MANUAL.md]]
- Create + initialize PC: [[MANUALS/create_charManual.md]]
- Update sheets and autogen report: [[MANUALS/update_charManual.md]]
- Vault sync & collectionfiles: [[MANUALS/Wiki_File_System_Manager  MANUAL.md]]
- Formula guidance: [[MANUALS/char_formulas_README.md]]

## Troubleshooting pointer

- If scripts fail, run them with `-v` to see verbose diagnostics and check `graphs/` for outputs.

If you want this as a printable one-page PDF or a single combined manual, I can generate it.

---

## update_charManual.md

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

-- `--pc <NAME>`  locate a character sheet for `<NAME>` and update it. The script will prefer a repository-level `PC Character Sheets` folder when present; otherwise it falls back to `Players Part/PCs/<NAME>/<NAME> Character Sheet.md`.

- `--file <PATH>`  update the specified file.
- `--formulas <PATH>`  load formulas from the given JSON file (defaults to `char_formulas.json`).
- `--extend-formulas`  when provided, missing formula keys are filled from built-in defaults and the combined set is used.
- `--levelup`  (if supported in your version) apply level-up logic before recomputing derived stats.
- `--backup`  create an explicit timestamped backup (the script already writes a `.bak` by default).

## What the script computes

- Reads the `## Core Stats` markdown table to gather STR/DEX/CON/INT/WIS/CHA and other core values.
- Reads `## Bending Levels` to gather element levels.
- Evaluates formulas from `char_formulas.json` (or your provided file) to compute values like Max Hitpoints, Evasion, Armor, and Element DCs.
- Inserts an "Autogen Report" section into the sheet that lists inferred values, applied overrides, and any unresolved formula identifiers.

Template integration note:

- The character-sheet templater (`create_pc.py`) now loads `char_formulas.json` and attempts to compute secondary stats at sheet creation time so the newly-created Character Sheet contains accurate derived values from the start. The templater still writes conservative fallbacks if formulas are missing or evaluation fails.
- `update_char.py` continues to be the canonical updater for in-place edits; its evaluation order and autogen report are unchanged, but both tools use `char_formulas.json` as the base lookup sheet when computing secondary stats.

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

If you rely on custom workflows, be aware these hooks may run automatically; you can always run `update_char.py` directly with `--file` if you want a single targeted pass. Note that `--all` (when present) will override `--pc` in orchestration scripts like `Wikigraphs.py`.

---

## Wiki_File_System_Manager  MANUAL.md

<!-- See MANUALS/Usage_Guide.md for a short summary of all manuals -->

## 

d04 How to Sync Your Vault (Git + Collectionfiles)

To sync your local vault with the remote repository **and** automatically update all collectionfiles (backlink blocks):

```bash
python -c "from Wiki_File_System_Manager import Sync; Sync()"
```

To manually recreate all collectionfiles (backlink blocks) without syncing:

```bash
python Wiki_File_System_Manager.py --ext .md --recreate-collectionfiles
```

This will:

- Stage, commit, and push all local changes
- Pull and merge the latest from `origin/main`
- Recreate all collectionfiles (backlink blocks)
- Commit and push any new collectionfile changes

---

## Wikigraphs_MANUAL.md

## Wikigraphs  Manual

## Purpose

Wikigraphs.py scans an Obsidian-style vault and produces interactive Plotly
Sunburst and Treemap HTML visualizations of the file/directory structure.
It produces two main HTML outputs per root: `<root>_wikigraph_sunburst.html`
and `<root>_wikigraph_treemap.html`.

## Prerequisites

- Python 3.8+
- plotly (install with `pip install plotly`)

## Quick usage

Generate graphs for the current workspace root:

```bash
python3 Wikigraphs.py
```

Generate graphs for a specific PC folder (Players Part/PCs/<name> or the project's first "PC Character Sheets" folder):

```bash
python3 Wikigraphs.py --pc Anju
```

Generate per-PC graphs for all PCs collected from `pcs_input.md` or inferred
from existing graph HTML filenames:

```bash
python3 Wikigraphs.py --pc __ALL__
```

Note: when run with `--all` the script will attempt a small orchestration
pipeline before generating graphs (best-effort; failures do not abort the
run): `generate_secondary_stats.py --all`, `update_recolouring.py` (if
present), and `update_char.py --all`. The `--all` flag now always overrides
`--pc` and will iterate every discovered PC folder (preferring the first
`PC Character Sheets` folder found in the repository tree when present).

Recreate graphs for every PC and any existing graph roots inferred from
already-present HTML files, and remove stale HTMLs:

```bash
python3 Wikigraphs.py --pc --all -v
```

... End of combined manual ...
