tags: #manual

## How to test the Mycelium scripts and pipeline

This short guide shows the recommended commands for running the project's automated tests
and doing safe dry-run exercises of core scripts (pagerank, consolidation, variable updates).

1. Run unit tests (pytest)

```bash
python3 -m pytest -vv -r a
```

This runs the full test suite with very-verbose output and prints a compact pass/fail summary.

2. Dry-run the Mycelium consolidation (safe preview)

```bash
python3 mycelium_caretaker.py --consolidate-mycelium --dry-run
```

This copies duplicates into `Mycelium/Dead Cells` and prints which file would be kept (PageRank-aware).

3. Run the pagerank pipeline (dry-run then persist)

Dry-run / preview:

```bash
python3 Mycelium/scripts/manuals/pipeline_profiler_and_pagerank.py --root .
```

Persist (writes `Mycelium/pagerank.json`):

```bash
python3 Mycelium/scripts/manuals/pipeline_profiler_and_pagerank.py --root . --apply
```

4. Test `fix-variable` CLI in dry-run + auto-pick mode

```bash
python3 mycelium_ctl.py fix-variable "Name" --dry-run --auto-pick
```

5. Safety notes

- Prefer `--dry-run` for unfamiliar steps. When using `--apply` or `--sort`, commit or backup first.

If you want, I can also add a small test that asserts the caretaker `--dry-run` output contains expected pagerank messages.
