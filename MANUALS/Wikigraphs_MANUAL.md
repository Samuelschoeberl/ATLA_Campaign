## Wikigraphs — Manual

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

````markdown
## Wikigraphs — Manual

## Purpose

`Wikigraphs.py` scans an Obsidian-style vault (or any folder of markdown/text
files) and produces interactive Plotly Sunburst and Treemap HTML visualizations
of the directory/file hierarchy and file sizes (or file counts). Primary HTML
outputs are `<root>_wikigraph_sunburst.html` and
`<root>_wikigraph_treemap.html`, written into the `--out` directory.

## Prerequisites

- Python 3.8+
- plotly (install with `pip install plotly`)

Optional (used for histogram chart): numpy

- `pip install numpy`

## Quick usage

Generate graphs for the current workspace root (default is the current
working directory):

```bash
python3 Wikigraphs.py
```

Generate graphs for a specific PC folder (Players Part/PCs/<name> or the repository's first "PC Character Sheets" folder):

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

## Notes on `--pc` and `--all`

-- `--pc NAME` generates per-PC graphs for the named PC. The script prefers
the repository's first `PC Character Sheets` folder when present; otherwise
it falls back to `Players Part/PCs/NAME`. If multiple folders share the
same basename the first match found is used.

- When generating per-PC graphs the script will try to parse the character
  sheet (`<NAME> Character Sheet.md`) to derive allowed bending levels and
  may mirror matching Rules pages under the character node so the graph
  reflects only relevant Rules/moves.
- `--pc` without a value combined with `--all` (union-mode) gathers names from
  `pcs_input.md` and also infers roots from existing `*_wikigraph_*.html`
  filenames; use this to regenerate the union of known graphs plus canonical
  PCs.
  -- `--all` (alone) iterates every discovered PC folder (preferring a
  `PC Character Sheets` folder if found) and can be used to bulk-generate graphs.

## Deletion safety

- Deletions (when cleaning stale graphs) are limited to files matching
  `*_wikigraph_*.html` within known graphs folders and the script directory.
  Repository-root graph filenames are protected by default. Run with `-v` to
  preview which graphs will be produced and which stale files will be removed.

If you want a preview-only deletion mode I can add a `--dry-delete` or
`--confirm-deletes` flag to list candidates and require confirmation.

## Flags and options

- `--root PATH` : Path to vault root (default: current working dir)
- `--out DIR` : Output directory for HTML files (default: `graphs` next to
  the script)
- `--ext .md` : Add file extensions to include (can be repeated)
- `--exclude NAME` : Exclude directories by name (can be repeated)
- `--embed` : Embed Plotly JS into output HTML (offline usage)
- `--mode` : `size` (default) or `count` — use file sizes (bytes) or file
  counts for node values
- `--recolor path=#rrggbb` : Recolor a node subtree; provide multiple times
  to apply multiple recolors. Provide `--recolor` without a value to apply
  stored recolors from `color_recolors.md` only.
- `--pc [NAME]` : See notes above. Use no value + `--all` to infer names.
- `--all` : Generate graphs for every folder under `Players Part/PCs` or used
  in union mode with `--pc`.
- `--include-gitignored` : Include files matched by `.gitignore` when
  scanning (disabled by default)
- `--dms-tree` : Convenience: generate a graph rooted at `DMs Part/`, include
  gitignored files, and name outputs with `DMs` in the filename.
- `--materialize-unresolved` : When building per-PC graphs, write unresolved
  `[[links]]` as placeholder files under the PC folder `Unresolved Links/` so
  per-PC graphs include visible placeholders for missing targets.
- `--child-spread` (float, default `0.35`) : Initial hue spread allocated to
  root children (0..1).
- `--spread-growth` (float, default `1.0`) : Multiplier applied to hue spread
  at each level (>=0).
- `-v` / `--verbose` : Verbose output and diagnostic prints

## Examples and workflows

- Rebuild everything (root + every PC):
  `python3 Wikigraphs.py --all`
- Rebuild root + any PC-graphs inferred from existing HTMLs and
  `pcs_input.md`:
  `python3 Wikigraphs.py --pc --all -v`

## Troubleshooting

- If `plotly` is missing: `pip install plotly`.
- If the histogram page fails, install `numpy` (optional): `pip install numpy`.
- If output HTML files don't appear where expected, check the printed
  "Writing to" folder at script start; the script prefers the `graphs`
  folder next to the script.
- If recolors don't appear as expected, run `python3 Wikigraphs.py --recolor`
  (no value) to force stored recolors from `color_recolors.md` and inspect
  the printed recolor applications.
- Default excludes: `.git`, `node_modules`, `.obsidian`, `__pycache__`,
  `venv`, `.venv`. Use `--exclude` to add more.
- Default included extensions: `.md`, `.markdown`, `.txt`. Use `--ext` to add
  others.

## Full workflow examples

1. Daily root + per-PC refresh (recommended)

Purpose: keep top-level graphs and each player's sunburst up-to-date.

Steps:

- From the repo root, update recolors if needed (optional):

  ```bash
  python3 update_recolouring.py --file color_recolors.md --sort
  ```

- Regenerate root + all PC graphs (safe default):

  ```bash
  python3 Wikigraphs.py --all -v
  ```

What this does:

- Writes `ATLA_Campaign_wikigraph_sunburst.html` and
  `ATLA_Campaign_wikigraph_treemap.html` into `graphs/`.
- Reads `pcs_input.md` and any existing files like `Anju_wikigraph_sunburst.html`
  to build a union of per-PC roots to (re)generate.
- Deletes stale `*_wikigraph_*.html` files not present in the regenerated set
  (limited to known graphs folders).

2. Rebuild a single PC's graphs after changing a Character Sheet

Purpose: when a single player's allowed moves or sheet changes.

```bash
python3 Wikigraphs.py --pc Anju -v
```

Notes: the script will try to locate `Players Part/PCs/Anju` and parse
`Anju Character Sheet.md` to determine allowed bending levels and mirror
selected Rules files under the PC subtree so the sunburst is rooted at the
character and shows only allowed moves.

3. Generate offline/self-contained HTML (embed plotly.js)

```bash
python3 Wikigraphs.py --embed --pc --all
```

4. Quick development loop (adjust recolors)

```bash
# preview recolors without writing
python3 Wikigraphs.py --pc --all -v

# make targeted recolor changes and persist them
python3 Wikigraphs.py --recolor 'Players Part/Rules/Bending Rules/Fire/=#ff6666'
```

## Recoloring (manual overrides and persistence)

The script supports recoloring subtrees and persisting recolors to
`color_recolors.md` in the vault root (or next to the script). Format:

```
path=#rrggbb
```

Examples:

```
/=#ffb3b3
Players Part/Rules/Bending Rules/Fire/=#ffb3b3
```

Rules for matching recolor directives

- Matching is forgiving and applied to all matching node ids (not just the
  first): exact id match (directories end with `/`), case-insensitive exact
  matches, suffix matches (path endswith), and basename fallback (final
  path component).

Behavior / implementation notes

- The script looks for `color_recolors.md` next to the script and in the
  scanned `--root`. If neither exists it will fall back to any
  `HARDCODED_RECOLORS` present in the source.
- File-based recolors are applied first and treated as protected: the
  hue-assignment algorithm will not overwrite protected node ids and the
  recolor is propagated to descendants (protect=True).
- CLI recolors provided with `--recolor 'path=#rrggbb'` are applied after
  file-based recolors and (unless run with the no-write stored-only flag)
  are merged into the recolor file.
- Provide `--recolor` with no value to mean "apply stored recolors only"
  (do not modify the recolor file).

## Deterministic hierarchical colors

- Colors are assigned deterministically from the vault name and tree
  structure so repeated runs produce stable palettes.
- The algorithm splits a hue range among immediate children weighted by
  descendant leaf counts and uses a deterministic gaussian-like sampler for
  child centers to avoid rigidly evenly-spaced palettes while remaining
  deterministic.

## Contract (inputs / outputs / success criteria)

- Inputs: filesystem root (`--root`) containing markdown/text files and an
  optional `pcs_input.md` listing PCs.
- Outputs: one or more HTML files in `--out` (sunburst + treemap, optionally
  top-N lists and a histogram).
- Error modes: missing `plotly` (import error), malformed CLI recolor
  entries, or missing PC folders when `--pc NAME` is requested.
- Success: HTML files are written and the script exits with code 0. With
  `--verbose` the script prints diagnostic information about matched files
  and recolor applications.

## Quick checklist before running

- Ensure `plotly` is installed: `pip install plotly`
- Install `numpy` if you want the histogram: `pip install numpy`
- Run with `-v` first for an inspection run (prints matched recolors and
  candidate roots) before committing recolor file changes or deletions.

## Development notes

- The treemap shows the full sanitized `.md` file text inside cells (no
  truncation). Hovertext for sunburst and treemap is limited to ~1000 chars.
- Embedded files `![[...]]` are inlined heuristically by filename/suffix
  lookup in the sanitized content index. This does not resolve ambiguous
  aliases or complex frontmatter aliasing.

## Contact / Next changes

If you'd like any of these additions I can implement them:

- `--dump-colors`: print node -> hex mappings at runtime
- Persist resolved node ids instead of shorthand keys in `color_recolors.md`
- `--recolor-remove path`: CLI removal helper for persisted recolors

---

Manual created for `Wikigraphs.py` — keep this file in the repo root next to the script for quick reference.
````

- `--root` (default `.`) — vault root path to scan
