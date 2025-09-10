## Purpose

`Wikigraphs.py` scans an Obsidian-style vault (or any folder of markdown/text files) and writes Plotly Sunburst and Treemap HTML visualizations that show the directory/file hierarchy, sizes (or counts), and sanitized Markdown content inside nodes.

This manual explains usage, CLI options, recolor persistence, and a few implementation notes so you can tune and extend behavior.

## Example workflows

- updates All PC graphs:

```bash
python3 update_char.py --all
```

- Regenerate graphs:

```bash
python3 Wikigraphs.py --root "$(pwd)" --out graphs
```

```bash
python3 Wikigraphs.py --root "$(pwd)" --out graphs --child-spread 0.7
```

Quick copy-paste commands

```bash
# Generate graphs for the current vault and write into ./graphs (default)
python3 Wikigraphs.py --root "$(pwd)" --out graphs

# Generate graphs for a single PC folder (e.g. Players Part/PCs/Anju)
python3 Wikigraphs.py --pc Anju --verbose --embed

# Generate graphs for every PC folder under Players Part/PCs
python3 Wikigraphs.py --all --verbose --embed

# Apply a one-shot recolor directive and persist it to color_recolors.md
python3 Wikigraphs.py --recolor "Rules/Bending Rules/Fire/=#ff0000"

# Apply stored recolors only (do not modify color_recolors.md)
python3 Wikigraphs.py --recolor
```

- Recolor every matching `Bending Rules/Fire` subtree to red and persist:

```bash
python3 Wikigraphs.py --root "$(pwd)" --out graphs --recolor "Rules/Bending Rules/Fire/=#ffb3b3"
```

- Apply stored recolors only without changing the recolor file:

```bash
python3 Wikigraphs.py --root "$(pwd)" --out graphs --recolor
```

## Requirements

- Python 3.8+
- plotly (required to produce the HTML visualizations)
- numpy (optional, used for the file-size histogram)

Install the main dependency:

```bash
pip install plotly
# optional: pip install numpy
```

## Quick start

Run the script from the vault root (writes files into `graphs/` by default):

```bash
python3 Wikigraphs.py --root "$(pwd)" --out graphs
```

Files written (into the output folder):

- `wikigraph_sunburst.html` — Plotly Sunburst
- `wikigraph_treemap.html` — Plotly Treemap
- `wikigraph_top_20_files.html` (or `.txt` fallback)
- `wikigraph_top_20_dirs.html` (or `.txt` fallback)
- `wikigraph_file_size_histogram.html` (or `.txt` fallback)

Open the HTML files in your browser.

## Main behaviors and special handling

- Markdown (`.md`) files: the script reads the raw file text, sanitizes it (removes YAML frontmatter, Obsidian/Markdown wikilink syntax, headings, emphasis and code markers) and stores the sanitized text for use in hover text and treemap cell text.
- Embeds: `![[target]]` embeds are handled early and the script will try to inline the referenced file's sanitized content when building the treemap cell text and when creating simple `Expanded` megafiles.
- Tables: basic Markdown tables are converted to a compact plaintext representation preserving header and rows.
- Backlink collections: files containing `#collectionfile` will have backlink/Backlinks sections removed so those backlink lists don't pollute the cell text.
- Treemap cell text: the treemap displays the full sanitized file content for each `.md` file (the script intentionally does not truncate treemap text). Hovertext is limited to ~1000 characters.
- `Expanded` megafiles: any source file with a basename starting with `Expanded` will cause the script to create a `simple_Expanded_Megafile.md` in the same directory with embeds inlined (sanitized content).

## CLI options

Run `python3 Wikigraphs.py --help` to see the same list; here are the important ones:

- `--root` (default `.`) — vault root path to scan
- `--out` (default `graphs`) — output directory
- `--ext` (repeatable) — include file extensions (e.g. `--ext .md`) (defaults to `.md`, `.markdown`, `.txt`)
- `--exclude` (repeatable) — directory names to ignore (`.git`, `.obsidian`, etc. are excluded by default)
- `--embed` — embed Plotly JS into the HTML so files are fully offline-capable
- `--mode` `size|count` — use file bytes (size) or counts for values
- `--child-spread` (float, 0..1, default `0.35`) — initial hue spread allocated among root children; larger values make sibling hues farther apart
- `--spread-growth` (float, default `1.0`) — multiplier applied to spread each level
- `--recolor` (repeatable, optional-argument) — recolor a subtree; usage explained below

## Recoloring (manual overrides and persistence)

The script supports recoloring subtrees and persisting those recolors to `color_recolors.md` in the vault root.

Format of the recolor file (`color_recolors.md`): lines of the form:

```
path=#rrggbb
```

Examples:

```
/=#ffb3b3
Players Part/Rules/Bending Rules/Fire/=#ffb3b3
```

Rules for matching recolor directives

- The matching is forgiving and applies to **all** matching node ids (not just the first):
  - Exact id match (the id used inside the visualization; directories end with `/`).
  - Case-insensitive exact matches.
  - Suffix matches: if you provide `Rules/Bending Rules/Fire/` it will match any node id whose path ends with that suffix (useful if you have multiple top-level folders named similarly).
  - Basename fallback (match by the final path component) is also attempted.

Behavior

- File-based recolors (those in `color_recolors.md`) are applied first and marked as protected: the main hue-assignment algorithm will not overwrite protected node ids (and the recolor will be recursively applied to their descendants).
- CLI recolors (provided with `--recolor 'path=#rrggbb'`) are applied and merged into the recolor file after successful processing.
- Provide `--recolor` with no value (just the flag) to mean "apply stored recolors only"; in that case the script will apply the recolors from `color_recolors.md` but will not rewrite the file.

Examples

- Apply one-shot recolor and persist it:

```bash
python3 Wikigraphs.py --root "$(pwd)" --out graphs --recolor "Rules/Bending Rules/Fire/=#ff0000"
```

- Apply stored recolors only (don't change `color_recolors.md`):

```bash
python3 Wikigraphs.py --root "$(pwd)" --out graphs --recolor
```

Notes about persisted keys

- The script merges CLI-provided keys into the recolor file using the user-provided key string (not the fully-resolved node id). If you prefer to store fully-resolved ids (one entry per resolved target) tell the maintainer and the script can be adjusted to persist resolved entries instead.
- To remove or edit recolors you can directly edit `color_recolors.md`; a small CLI removal helper is not currently implemented.

## Deterministic hierarchical colors

- Colors are assigned deterministically from the vault name and the tree structure so repeated runs produce stable palettes.
- The algorithm splits a hue spread among immediate children weighted by descendant leaf counts and uses a deterministic Gaussian-based sampler for child centers to avoid rigid evenly-spaced palettes while remaining deterministic.
- A fallback deterministic color is generated for any node that wasn't explicitly assigned.

If you want coarser or wider palettes, increase `--child-spread` (closer to 1.0 spreads children across more of the hue circle).

## Troubleshooting

- If you see an import error about `plotly` when running the script, install it with `pip install plotly`.
- If the histogram page fails, install `numpy` (optional) with `pip install numpy`.
- If recolors don't appear as expected, run the script with `--recolor` alone to force stored recolors to be applied and check `color_recolors.md` keys for the correct path/suffix. You can also invoke CLI recolors with the full node id if you need an exact match.

## Development notes

- The treemap intentionally shows the full sanitized `.md` file text inside cells (no truncation). Hovertext for sunburst and treemap is limited to ~1000 chars to keep the hover concise.
- Embedded files `![[...]]` are inlined heuristically by filename/suffix lookup in the sanitized content index. If you need more robust embed resolution (frontmatter aliases, explicit path handling) the embed resolution helper can be extended.

## Contact / Next changes

If you want any of the following, I can add them:

- `--dump-colors` flag to print node → hex mappings at runtime (useful to verify which nodes were matched by recolor directives)
- Persist resolved node ids instead of shorthand keys in `color_recolors.md`
- CLI remove (`--recolor-remove path`) to delete persisted recolors

---

Manual created for `Wikigraphs.py` — keep this file in the repo root next to the script for quick reference.
