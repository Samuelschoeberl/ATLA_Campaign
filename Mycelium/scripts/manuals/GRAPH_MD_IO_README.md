tags: #manual

graph_md_io utility

This utility converts graph JSON (common d3 format with `nodes` and `links`) into two
Markdown tables and can rebuild the JSON from those tables.

Why

- Markdown tables are easy to read and track in Obsidian. They let you commit a snapshot
  of the graph data as `.md` files.
- The tables are simple: `nodes.md` holds node attributes, `edges.md` holds links/weights.

Files created

- nodes.md: pipe table; header contains all node keys encountered (e.g. id, name, group)
- edges.md: pipe table; header contains all edge keys encountered (e.g. source, target, value)

Quick commands

Convert JSON -> MD files

    python Mycelium/graph_md_io.py to-md path/to/graph.json path/to/out_dir

Convert MD files -> JSON

    python Mycelium/graph_md_io.py from-md path/to/out_dir/nodes.md path/to/out_dir/edges.md out.json

Notes

- Complex column values (lists/dicts) are stored as JSON-encoded strings in cells and parsed
  back when reading.
- Numbers are coerced to int/float when possible.

Next steps / ideas

- Add a small preview generator that produces a sankey-like HTML using the edges `value`.
- Add a CLI option to generate an Obsidian-friendly file with frontmatter, or inline the tables
  into an existing note.
