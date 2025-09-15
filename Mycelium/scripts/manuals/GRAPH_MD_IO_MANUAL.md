tags: #manual

Graph MD IO — Full Manual

Purpose

This manual documents the `graph_md_io.py` utility added to the `Mycelium` folder. The
utility provides:

- JSON -> Markdown table export (`to-md`) producing `nodes.md` + `edges.md`.
- Markdown table -> JSON import (`from-md`) to rebuild the original graph.
- JSON -> flat Markdown export (`to-flat`) producing one `.md` file per node (frontmatter + outgoing edges table).

This is designed for use with Obsidian or any filesystem-based Markdown workflow where you
want to store graph state as human-readable `.md` files and optionally visualize them
(Sankey/treemap) later.

Quick CLI reference

- Export JSON to two Markdown tables:

```bash
python3 Mycelium/graph_md_io.py to-md <graph.json> <out_dir>
```

- Rebuild JSON from two Markdown tables:

```bash
python3 Mycelium/graph_md_io.py from-md <nodes.md> <edges.md> <out.json>
```

- Export JSON into one .md file per node (flat mode):

```bash
python3 Mycelium/graph_md_io.py to-flat <graph.json> <out_dir>
```

These commands are intentionally simple and require only Python 3 in your environment.

Why this design?

- Obsidian users prefer Markdown. Storing graph data in `.md` means you can:
  - View history/diffs in git easily.
  - See node data inline in Obsidian.
  - Use the graph view where node "size" or connectedness is represented (no folders required).
- Markdown tables are easy to parse with small scripts and keep data readable.
- Flat per-node `.md` files allow each node to be treated like an Obsidian note (frontmatter + content).

File formats

1. nodes.md (pipe table)

- Header row: contains column names (keys). Example: `| id | name | path | group |`
- Separator row: `| --- | --- | --- | --- |`
- Each subsequent row: values for each column.
- Complex values (objects/arrays) are stored JSON-encoded inside the cell.
- Numbers are parsed back to int/float where possible.

Example nodes.md fragment

| id  | name        | path                    |
| --- | ----------- | ----------------------- |
| 1   | Root        | /path/to/Root.md        |
| 2   | GrowthGuide | /path/to/GrowthGuide.md |

2. edges.md (pipe table)

- Header includes at least source and target (or other names like src/dst). Example:
  `| src | dst | type | weight |`
- Any attributes on edges (type, weight/value, metadata) are preserved and roundtripped.

Example edges.md fragment

| src                            | dst         | type     | weight |
| ------------------------------ | ----------- | -------- | ------ |
| Mycelium                       | Root        | wikilink | 3      |
| helpers/secondary_stat_formula | unsorted/CL | wikilink |        |

Notes about field names

- The exporter prefers canonical `id`, `source`/`target`, and `value`/`weight` keys but will
  keep whatever keys exist. When reading back, it will normalize `weight` <-> `value` so both names are supported.
- For JSON graphs that have `nodes` as a mapping (id -> path) the tool converts each entry into a node dict
  with `id`, `name`, and `path` keys.

Flat per-node `.md` files (to-flat)

- Each node becomes `out_dir/<sanitized-name>.md`.
- File structure:
  - A simple frontmatter-like block (delimited by `---`) containing `key: value` lines for each node attribute. Complex values are JSON-encoded.
  - Section `## Outgoing edges` with a Markdown table containing the union of all edge attributes for outgoing edges from that node.
- Filenames are sanitized: characters not safe for filenames (/ \ : \* ? " < > |) are replaced with `_` and collisions get numeric suffixes.

Example single node file (Mycelium.md)

---

id: Mycelium
name: Mycelium
path: /.../Mycelium.md

---

## Outgoing edges

| src      | dst       | type     |
| -------- | --------- | -------- |
| Mycelium | Root      | wikilink |
| Mycelium | Anju/Anju | wikilink |

Roundtrip guarantees and limitations

- Roundtrip (JSON -> MD -> JSON) preserves string keys and JSON-serializable values; complex nested objects are stored as JSON strings in table cells and parsed back.
- Numeric values are coerced to numbers when reading (`int` if no decimal point, otherwise `float`).
- Empty cells become empty strings.
- The order of columns in tables is not guaranteed on output (the code orders keys deterministically where possible), but all keys are preserved.

Edge cases handled

- `nodes` as list of dicts (standard d3): supported.
- `nodes` as dict mapping (your mygraph_preview.json): converted to node dicts with `id` and `path`.
- `edges` named `links` or `edges`: both recognized.
- Complex values in cells are JSON-encoded and parsed back.
- When node ids are missing, indices are used as fallback ids.

Troubleshooting

- If `to-flat` writes 0 files, inspect the JSON topology. Typical causes:
  - `nodes` missing entirely or empty in the JSON.
  - Edge keys are present but source keys are empty or non-matching with node ids.
- If cells contain commas, pipes, or newlines they will be JSON-encoded (and appear as JSON text in the cell). This is expected.

Integrating with Obsidian

- Drop the `flat_preview` folder into your vault. Each node file is a note you can open.
- Because filenames are flat (no folders), the Obsidian graph view will show nodes as files where their size/importance is determined by outgoing/incoming edges in your visualization tool.
- Consider adding backlinks or frontmatter fields you prefer (the frontmatter block in each file is simple key:value lines; you may convert to YAML if you prefer strict YAML frontmatter).

Extending for Sankey/Graph previews

- The `nodes.md` + `edges.md` output is ready to feed into a small D3 or plotly script to create Sankey diagrams. The important field is the edge weight (commonly `value` or `weight`). If absent, you can compute weights by counting duplicate edges or adding a `weight` column manually.
- Idea for a follow-up script: `graph_to_sankey_html.py` which reads `nodes.md` and `edges.md` and emits a single `preview_sankey.html` that is self-contained (D3 + inline data).

Developer notes / internals

- Files in `Mycelium/graph_md_io.py` to inspect:
  - `json_to_tables` — converts input graph into (nodes, edges). Handles `nodes` as list or dict.
  - `write_md_table` / `read_md_table` — table writer/parser. Minimal, dependency-free.
  - `json_to_md_files` / `md_files_to_json` — high-level roundtrip helpers.
  - `json_to_flat_md` — produces per-node `.md` files.
  - `_safe_filename` — sanitizes names for filesystem.

Examples and recipes

1. Save a snapshot before editing programmatically

```bash
python3 Mycelium/graph_md_io.py to-md Mycelium/graphs/mygraph_preview.json Mycelium/snapshots/snapshot-2025-09-11
```

This produces `nodes.md` and `edges.md` which you can commit to git as a readable snapshot.

2. Edit edges.md manually (e.g., change weights) and rebuild JSON for visualization

```bash
# edit Mycelium/snapshots/snapshot-2025-09-11/edges.md in Obsidian
python3 Mycelium/graph_md_io.py from-md Mycelium/snapshots/snapshot-2025-09-11/nodes.md Mycelium/snapshots/snapshot-2025-09-11/edges.md Mycelium/snapshots/snapshot-2025-09-11/graph.json
```

3. Generate flat notes for Obsidian and inspect graph view

```bash
python3 Mycelium/graph_md_io.py to-flat Mycelium/graphs/mygraph_preview.json Mycelium/flat_preview
# Open Mycelium/flat_preview in your Obsidian vault (or copy files there)
```

Next steps and optional features you may want

- A small HTML Sankey generator (D3) that consumes the Markdown tables and writes a self-contained HTML preview.
- Optionally use strict YAML frontmatter instead of simple frontmatter-like lines for compatibility with Obsidian plugins that read YAML.
- Option to write outgoing + incoming tables inside the same per-node file, or add backlink generation.
- Add tests that roundtrip multiple sample graphs and validate fields are preserved.

Contact / support

If you want me to add the Sankey preview generator, strict YAML frontmatter, or inline updates to your existing notes, tell me which next step you prefer and I will implement it and test on your sample graph.
