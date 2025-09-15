#tags: #manual
#config

# Centered Mushroom

Root/

# Mushrooms Paths (these are very important folders in the structure that are all tagged with "#Mushroom")

# Per PC Mushrooms

_/Anju/
_/Ash/
_/Puy/
_/Rio/
_/Sora/
_/Tapioca/
\_/PCs/

## Mushroom colours

You can optionally declare per-mushroom colour mappings here. Each mapping is a simple
line of the form:

```
<path>=#rrggbb
```

Notes:

- Use the same path ids that the visualiser uses (directory ids end with '/').
- Example entries:

```
Anju/ = #3ed7e4ff
Ash/  = #1d2088ff
Anju/ = #3e9f51ff   # alternate shorter path form
```

#Mycelium

## Hyperparameters & Presets (machine-readable simple key=value lines)

You can declare automation knobs and tag-presets here. The scripts in `Mycelium/` will look for simple
`key = value` lines (case-insensitive keys) when the `use_config` or equivalent option is enabled.

Format rules (simple and easy to parse):

- Lines of the form `key = value` (no quotes required).
- Comment lines start with `#` and are ignored by parsers.
- Lists are comma-separated values.

Examples and recommended keys:

```
# Hyperparameter presets for the link-multiplier extractor and PageRank pipeline
tag_presets = #Mushroom,#PC,#Ability     # optional list of tags to prioritize
lambda = 0.25                           # decay rate for tag proximity (float)
tag_boost = 0.75                        # boost contributed by explicit tags (float)
alpha_complexity = 0.05                 # multiplier scaling applied from complexity score
multiplier_target = incoming            # 'incoming' or 'outgoing'
use_extractors = false                  # if true, pipeline will load .multipliers.json for files
emit_scores = true                      # write per-node *_scores.md files into Mycelium/unsorted
default_snap_iterations = 10            # number of pagerank iterations for snapshots
```

Notes:

- Parsers should trim whitespace and accept `true|false` (case-insensitive) for booleans.
- `tag_presets` provides a small curated set of tags to bias multiplier extraction or to pre-seed the extractor.

## Execution logs & run datapoints (persisted as Markdown)

When a pipeline run completes (or as configured), the pipeline can emit a compact run log in Markdown
under `Mycelium/logs/` (directory created if missing). Each run log is a single `.md` file named like
`YYYYMMDD_HHMMSS_run.md` and includes the datapoints below so you can inspect runs in Obsidian and
play them back into the network if desired.

The following datapoints are recommended to collect and persist for each run (parser-friendly key:value list):

- timestamp: UTC ISO timestamp of run start
- duration_s: total wall-clock seconds for the run
- total_tags: total number of distinct explicit tags seen across scanned files
- total_files_scanned: number of markdown files scanned
- files_with_multipliers: number of files that had a `.multipliers.json` present or were processed by the extractor
- avg_multiplier: average multiplier applied across all edges (float)
- multiplier_stats: {min, max, median} (JSON object)
- pagerank_iterations: number of iterations used
- top_nodes_emitted: number of top nodes recorded in the run summary
- weighted_graph_path: relative path to the generated `weighted_graph.json`
- pagerank_path: relative path to the emitted `pagerank.json`
- snapshots_dir: relative path to snapshot `.md` files (if any)
- notes: free-form text for operator notes about this run

Example run log file content (machine- and human-readable):

````
# Run log — Mycelium pipeline
timestamp: 2025-09-11T12:34:56Z
duration_s: 12.34
total_tags: 42
total_files_scanned: 128
files_with_multipliers: 7
avg_multiplier: 1.42
multiplier_stats: {"min":1.0, "max":3.5, "median":1.08}
pagerank_iterations: 10
top_nodes_emitted: 20
weighted_graph_path: Mycelium/weighted_graph.json
pagerank_path: Mycelium/pagerank.json
snapshots_dir: Mycelium/snapshots
notes: Monthly run after manual edits to rules

```json
{
	"top_nodes": [ ["Player Root/Rules/Special Attacks.md", 0.0243], ["Root.md", 0.0201] ]
}
````

```

Implementation notes for scripts:
- When the pipeline writes a run log it should ensure `Mycelium/logs` exists and then write the `.md` file.
- Prefer a small, stable key:value format and a trailing fenced JSON block for structured extras like `top_nodes`.
- Scripts can later read these `.md` log files by extracting the key:value lines and parsing the JSON block.

If you want, I can wire the pipeline to write these run logs automatically on each `--graph`/`--pagerank` run; tell me and I'll implement it.
```
