## Mycelium — File Editor: design, scripts and workflows

This document maps the repository's Python utilities into a small, composable
"file editor" pipeline you can run from the command line to inspect, update and
regenerate character files, tag summaries and graph metadata.

Goals

- Provide a single conceptual flow that ties together the existing scripts.
- Describe safe defaults (dry-run) and how to persist changes (`--apply`).
- Show concrete CLI commands for common editor flows.

Checklist (what a file-editor should do)

- [ ] Discover files that need creation or updates (wikilinks -> unsorted / variable files)
- [ ] Create canonical variable fragments from templates
- [ ] Update primary variables from a centralized `pcs_input.md`
- [ ] Generate secondary stats (derived values)
- [ ] Compute file-network distances and weighted PageRank
- [ ] Append backlinks and per-file metadata into `.md` files
- [ ] Provide safe dry-run and archiving for cleanup operations

Key scripts (role & CLI)

- `scripts/create_unsorted_from_wikilinks.py`

  - Role: discover wiki link targets across a folder and create `Mycelium/unsorted` files.
  - Typical use: `python3 scripts/create_unsorted_from_wikilinks.py "Player Root/PCs" --dry-run`

- `Mycelium/create_from_template.py` (templates under `Mycelium/template`)

  - Role: create files from templates (Primary_variable, Secondary_variable, Character_Sheet, etc.)
  - Typical use: `python3 Mycelium/create_from_template.py --template Primary_variable.md --dest "Players Part/PCs/Anju/Anju Variable.md" --var PC=Anju`

- `Mycelium/mycelium_ttrpg.py`

  - Role: parse files with `#Variable` blocks or `Key: value` rows and emit per-character variable fragment files under `Players Part/PCs/<Name>/<Name>_variables.md`.
  - Typical use: `python3 Mycelium/mycelium_ttrpg.py --input "Mycelium/template" --out-root "Players Part/PCs"`

- `Mycelium/update_variables_and_rebuild.py`

  - Role: pipeline helper that syncs `pcs_input.md` values into variable files, optionally runs character-sheet rebuilds, and initializes templates for missing PCs.
  - Important flags: `--pcs-input <file>`, `--init-templates`, `--create-sheets`, `--apply`.
  - Typical use (dry-run): `python3 Mycelium/update_variables_and_rebuild.py --pcs-input pcs_input.md --root .`

- `generate_secondary_stats.py` and `scripts/ensure_vital_stats.py` / `scripts/update_bending_slots.py`

  - Role: compute derived stats and ensure structural sections exist in Character Sheets (Vital Stats, Bending Slots).
  - Typical use: run after primary variables are updated to sync derived values.

- `Mycelium/compute_shortest_paths.py`

  - Role: build the file network (from wikilinks or JSON) and compute unweighted shortest-path hop distances.
  - Typical use: `python3 Mycelium/compute_shortest_paths.py --root . --apply` (writes `Mycelium/file_network.json` and `Mycelium/distances.json`)

- `Mycelium/pagerank_from_metadata.py`

  - Role: build an adjacency from backlinks metadata or wikilinks and compute PageRank; optionally persist `Mycelium/pagerank.json`.
  - Typical use: `python3 Mycelium/pagerank_from_metadata.py --root . --apply`

- `Mycelium/append_backlinks.py`

  - Role: read PageRank and link data and append/replace `## Backlinks` sections in markdown files (dry-run by default).
  - Typical use: `python3 Mycelium/append_backlinks.py --root . --apply`

- `scripts/cleanup_unused.py`

  - Role: conservative top-level cleanup; already extended with `--aggressive` for a more aggressive candidate scan. Use `--apply` to move candidates to `archive/cleanup/<timestamp>/`.

- `grow_mushroom.py` / `Mycelium/Wikigraphs.py`
  - Role: visual helpers to produce cluster HTML visualizations. Optional part of the pipeline.

How they fit together (recommended pipeline)

1. Discovery: create any missing unsorted placeholders from wikilinks

   - `python3 scripts/create_unsorted_from_wikilinks.py "Player Root" --dry-run`
   - If satisfied: `--dest Mycelium/unsorted --force` to create files.

2. Template initialization / variable fragments

   - Use `Mycelium/create_from_template.py` or `Mycelium/mycelium_ttrpg.py` to emit per-PC variable fragments.
   - Example: `python3 Mycelium/mycelium_ttrpg.py --input "Player Root/PCs" --out-root "Players Part/PCs"`

3. Sync primary variable values from `pcs_input.md`

   - Dry-run: `python3 Mycelium/update_variables_and_rebuild.py --pcs-input pcs_input.md --root .`
   - Persist changes: add `--apply` (recommended to commit a backup before this step).

4. Recompute derived/secondary stats and structural sections

   - `python3 generate_secondary_stats.py` (or run via `update_variables_and_rebuild.py` when `--create-sheets` is used)
   - Then run `scripts/update_bending_slots.py` and `scripts/ensure_vital_stats.py` if you want to ensure bending slots and vital stats tables are present and correct.

5. Compute graph artifacts and PageRank

   - `python3 Mycelium/compute_shortest_paths.py --root . --apply`
   - `python3 Mycelium/pagerank_from_metadata.py --root . --apply`

6. Append backlinks + metadata to files

   - Dry-run: `python3 Mycelium/append_backlinks.py --root .`
   - Persist: `python3 Mycelium/append_backlinks.py --root . --apply`

7. Cleanup and archive stale files
   - Conservative dry-run: `python3 scripts/cleanup_unused.py --root .`
   - Aggressive dry-run: `python3 scripts/cleanup_unused.py --root . --aggressive`
   - Archive selected candidates with `--apply` (the script moves entries into `archive/cleanup/<timestamp>/`)

Operational notes & safety

- Most scripts default to dry-run. Only add `--apply` when you're ready to persist changes.
- Always create a git commit or backup before running `--apply` steps that modify many files.
- The `update_variables_and_rebuild.py` script can initialize templates and create sheets; prefer running it in dry-run first.

Developer-facing contract (small)

- Inputs: `--root` (default `.`) points at the repo/vault; many scripts accept `--root`.
- Outputs: templates, `Mycelium/*.json` artifacts, updated `.md` files under `Players Part/PCs` and the repo root.
- Error modes: missing templates, permission errors, or naming collisions (scripts generally avoid overwriting without `--force`/`--apply`).

Next steps I can take for you

- Add a small top-level `file-editor` CLI wrapper script that runs the above pipeline as stages with `--dry-run`/`--apply` toggles and an orchestration mode.
- Update per-script usage lines in docstrings (I can edit script headers to include the short usage lines if you want them embedded in each file).
- Generate a manifest of all `.py` scripts and their short roles in JSON for easier auditing.

If you'd like I can now either:

- create a `mycelium_file_editor.py` orchestrator that exposes `stage` targets (discover, init, sync, derive, graph, append, cleanup), or
- update docstrings/README entries in-place for each script to make the usage clearer (I recommend adding a single orchestration script first).
