One-page cheat sheet linking to the full manuals. Keep this file short —
use the linked manuals for details.

## Key quick commands

- Create a PC and generate graphs:

  ```bash
  python3 create_pc.py --name Anju --run-update --make-graphs
  ```

- Update a single Character Sheet:

  ```bash
  python3 update_char.py --pc Anju
  ```

- Regenerate root + per-PC graphs (union of `pcs_input.md` and existing HTMLs):

  ```bash
  python3 Wikigraphs.py --pc --all -v
  ```

## Where to look

- Graphs: `graphs/<Name>_wikigraph_sunburst.html` and
  `graphs/<Name>_wikigraph_treemap.html`
- Character sheets: `Players Part/PCs/<Name>/<Name> Character Sheet.md`

## Short workflows (links)

- Manual refresh colors + graphs: [[MANUALS/update_recolouring.py|update_recolouring]] + [[MANUALS/Wikigraphs_MANUAL.md]]
- Create + initialize PC: [[MANUALS/create_charManual.md]]
- Update sheets and autogen report: [[MANUALS/update_charManual.md]]
- Vault sync & collectionfiles: [[MANUALS/Wiki_File_System_Manager – MANUAL.md]]
- Formula guidance: [[MANUALS/char_formulas_README.md]]

## Troubleshooting pointer

- If scripts fail, run them with `-v` to see verbose diagnostics and check `graphs/` for outputs.

If you want this as a printable one-page PDF or a single combined manual, I can generate it.
