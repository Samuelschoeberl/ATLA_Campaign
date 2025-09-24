# generate_stat_overview.py

This tiny script scans the repository for player stats and environmental
variable files and writes an aggregated Markdown file at
`Player Root/PCs/stat_overview.md`.

## How to run

Run with the same Python interpreter you use for the frontend server:

```bash
python3 Mycelium/scripts/Python/generate_stat_overview.py
```

## Integration with the frontend API

When the frontend calls the `/update_sheet/<pcname>` endpoint with
`propagate=true`, the server will call the repository's propagation helper
and (on success) attempt to run this generator so `stat_overview.md` stays up
to date. If generation fails, the API will return a warning in its JSON
response.

## Notes

- The generator is intentionally forgiving; it looks for common keys like
  `max_hp`, `current hp`, `evasion`, and `environmental water charge`.
- If you need stricter parsing or additional fields, modify
  `generate_stat_overview.py` accordingly.
