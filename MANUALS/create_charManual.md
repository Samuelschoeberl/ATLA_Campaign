# See MANUALS/Usage_Guide.md for a short summary of all manuals

# create_charManual

## Purpose

This short manual explains how to quickly create a Character Sheet using `create_pc.py` and (optionally) generate the corresponding HTML graphs with `Wikigraphs.py` immediately after creation.

## Prerequisites

- `update_char.py` — computes derived stats inside the sheet (recommended).
- `Wikigraphs.py` — creates sunburst/treemap HTML files for the PC (optional).

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

  Quick single-NPC example — create a DM-facing NPC sheet, compute derived stats, and optionally generate embedded graphs:

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

## Create many characters from `pcs_input.md`

If you have multiple rows in the table format in `pcs_input.md`, create them in bulk:

```bash
python3 create_pc.py --input-file pcs_input.md --run-update --make-graphs --embed-graphs
```

## Flags and brief description

- `--name NAME` — required for single-character creation.
- `--input-file PATH` — path to a markdown table describing multiple PCs.
- `--str/--dex/--con/--int/--wis/--cha` — core stats (integers).
- `--air/--water/--earth/--fire/--spirit` — bending levels (integers).
- `--manual-rolled-hp` — summary total for manually rolled HP to insert on the sheet.
- `--out-root` — folder root where `Players Part/PCs/<Name>/` will be created (default: `Players Part/PCs`).
- `--run-update` — run `update_char.py --file <sheet>` after creating the sheet to compute derived stats.
- `--make-graphs` — run `Wikigraphs.py --pc <name>` after creation to generate graphs.
- `--embed-graphs` — pass `--embed` to `Wikigraphs.py` so Plotly JS is embedded into the HTML output.
- `--graphs-verbose` — pass `--verbose` to `Wikigraphs.py` to print selected files during filtering.

## Where outputs land

- Character sheets: `Players Part/PCs/<Name>/<Name> Character Sheet.md`
- Graph HTML: `graphs/<Name>_wikigraph_sunburst.html` and `graphs/<Name>_wikigraph_treemap.html`

## Troubleshooting

- "Could not locate character sheet" when using `update_char.py --name`: use `--pc` or `--file` with the explicit path, or run `create_pc.py`'s output file path directly.
- If `update_char.py` prints warnings about unresolved formulas, check `char_formulas.json` in the repo root — add missing formula keys there if desired.
- If `Wikigraphs.py` fails, run it manually with `--pc <Name>` to see verbose output:

```bash
python3 Wikigraphs.py --pc Anju --verbose --embed
```

- To find character files quickly:

```bash
ls -la "Players Part/PCs/Anju"
find . -type f -iname "*Anju*Character*Sheet*.md" -print
```

## Notes and suggestions

- `--run-update` is optional; `create_pc.py` will still create a usable sheet without it.
- Graph generation is synchronous and will block until `Wikigraphs.py` completes; if you prefer non-blocking generation, consider running `Wikigraphs.py` in the background or via a separate script.
- If you want automated tests for the create+graph flow, I can add a small test harness and a short README explaining CI steps.

If you want any of the following added to this manual, tell me which and I'll update the file:

- A sample `pcs_input.md` table snippet tailored to your vault.
- A troubleshooting section for common Python environment and Plotly errors.
- A short checklist for committing generated files (which files to track vs ignore).

## Full workflows

1. Create a new PC, compute derived stats, and generate graphs (single command):

```bash
python3 create_pc.py --name Anju --str 4 --dex 4 --con 2 --int 3 --wis 3 --cha 2 --water 3 --run-update --make-graphs --embed-graphs
```

2. Bulk create from `pcs_input.md` and generate graphs for all created PCs:

```bash
python3 create_pc.py --input-file pcs_input.md --run-update --make-graphs
```

3. Create a PC but skip immediate graph generation (manual step later):

```bash
python3 create_pc.py --name NewPlayer --run-update
# later
python3 Wikigraphs.py --pc NewPlayer
```
