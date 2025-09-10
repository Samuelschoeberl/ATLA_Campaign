# ATLA_Campaign — Quick Usage Guide

This single-page usage guide summarizes the repository manuals and provides the common commands and workflows you will use every day.

## Contents

- Quick commands
- Typical workflows
- Integration map (which scripts call which)
- Where outputs land
- Quick troubleshooting pointers

## Quick commands

- Create a PC (single):
  ```bash
  python3 create_pc.py --name Anju --str 4 --dex 4 --con 2 --int 3 --wis 3 --cha 2 --water 3 --run-update --make-graphs
  ```
- Update a single sheet (compute derived stats):
  ```bash
  python3 update_char.py --pc Anju
  ```
- Sync all PCs/NPCs from input tables and regenerate graphs:
  ```bash
  python3 update_char.py --sync
  ```
- Regenerate graphs for everything or a specific PC (exact command you requested):

  ````bash
  # ATLA_Campaign — Quick Usage Guide

  This single-page usage guide summarizes the repository manuals and provides the common commands and workflows you will use every day.

  ## Contents

  - Quick commands
  - Typical workflows
  - Integration map (which scripts call which)
  - Where outputs land
  - Quick troubleshooting pointers

  ## Quick commands

  - Create a PC (single):
    ```bash
    python3 create_pc.py --name Anju --str 4 --dex 4 --con 2 --int 3 --wis 3 --cha 2 --water 3 --run-update --make-graphs
  ````

  - Update a single sheet (compute derived stats):
    ```bash
    python3 update_char.py --pc Anju
    ```
  - Sync all PCs/NPCs from input tables and regenerate graphs:
    ```bash
    python3 update_char.py --sync
    ```
  - Regenerate graphs for everything or a specific PC (exact command you requested):
    ```bash
    python3 Wikigraphs.py --root "$(pwd)" --out graphs
    ```
    (or for a single PC with embedded plotly JS):
    ```bash
    python3 Wikigraphs.py --pc Anju --embed --verbose
    ```

  ## Typical workflows

  - New PC: run `create_pc.py` with `--run-update --make-graphs` to create the folder, compute derived stats, and generate graphs.
  - Bulk update: maintain `pcs_input.md` / `npcs_input.md` and run `python3 update_char.py --sync` to push values into sheets, regenerate bending slots, and recreate graphs.
  - Inspect autogen results: after `update_char.py` runs it prints an Autogen Report and writes a `.bak` backup before overwriting.

  ## Integration map

  - `create_pc.py` and `create_npc.py` -> optionally call `update_char.py` -> `update_char.py` calls `scripts/update_bending_slots.py` -> `update_char.py` or `--sync` calls `Wikigraphs.py` to regenerate graphs.

  ## Where outputs land

  - Character sheets: `Players Part/PCs/<Name>/<Name> Character Sheet.md` (NPCs under `DMs Part/NPCs/`)
  - Graphs: `graphs/<Name>_wikigraph_sunburst.html` and `graphs/<Name>_wikigraph_treemap.html`
  - Backups: modified files get `<file>.md.bak` before overwriting

  ## Troubleshooting (quick)

  - "Could not locate character sheet": use `--file <path>` or ensure `--pc <Name>` matches folder name exactly.
  - No graphs shown as "new": the sync script treats overwritten files as existing; use the mtime-reporting option (can be enabled) to list regenerated files.
  - Unresolved formulas: run `python3 char_formulas_check.py char_formulas.json` and add missing keys to `char_formulas.json` or to your sheet/pcs_input.

  ## See also

  Full manuals live in `MANUALS/`:

  - `MANUALS/create_charManual.md` — create_pc/create_npc
  - `MANUALS/update_charManual.md` — update_char usage and internals
  - `MANUALS/Wikigraphs_MANUAL.md` — graph generation and recolors
  - `MANUALS/Wiki_File_System_Manager – MANUAL.md` — bulk wiki maintenance
  - `MANUALS/char_formulas_README.md` — formula naming and checker

  If you want a printable one-page cheat-sheet or embedded examples per script, tell me which form you prefer and I'll add it.
