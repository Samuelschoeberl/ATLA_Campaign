# Growth Guide

Use tags (`#tag`) and wikilinks (`[[Name]]`) to make files connect in the graph and allow the "mushrooms" to grow and propagate.

Quick goals

- Add a single spore line to many files (append `#spore` or `#variable`).
- Remove accidental spore lines (prune).
- Always dry-run and backup before bulk edits.

Safe examples (run in the target directory)

Append one line to every `.md` (non-recursive):

```bash
shopt -s nullglob
LINE='#spore [[GrowthGuide]]'
for f in ./*.md; do
	printf '%s\n' "$LINE" >> "$f"
done
shopt -u nullglob
```

Append to all `.md` recursively (safe with filenames containing spaces):

```bash
LINE='#spore [[GrowthGuide]]'
find . -type f -name '*.md' -print0 | while IFS= read -r -d '' f; do
	# add newline if file doesn't end with one
	if [ -s "$f" ] && [ "$(tail -c1 "$f" | od -An -t uC | tr -d ' ')" != "10" ]; then
		printf '\n' >> "$f"
	fi
	printf '%s\n' "$LINE" >> "$f"
done
```

Use the provided helper scripts (recommended)

- `Mycelium/spore_append.sh` — append a LINE with options: `-l LINE -p PATH [-R] [-n] [-b]` (recursive/dry-run/backup).
- `Mycelium/spore_prune.sh` — remove a literal LINE with options: `-l LINE -p PATH [-R] [-n] [-b]`.

Example (dry-run then apply):

```bash
# dry-run
Mycelium/spore_append.sh -l '#spore [[GrowthGuide]]' -p 'Mycelium' -n

# apply recursively and backup
Mycelium/spore_append.sh -l '#spore [[GrowthGuide]]' -p . -R -b

# prune accidental insertions (dry-run first)
Mycelium/spore_prune.sh -l '#spore [[GrowthGuide]]' -p . -n
Mycelium/spore_prune.sh -l '#spore [[GrowthGuide]]' -p . -R -b
```

Safety and recovery

- Back up first (scripts support `-b` to copy matched files into `backups/`).
- Use `-n` (dry-run) to preview changes.
- Use git to review and commit changes: `git add -A && git commit -m "chore: apply spore tags"`.
- To revert everything from the backups folder: `cp -a backups/. .`

Notes and best practice

- Use consistent tag namespaces (`#spore`, `#mushroom`, `#propagate`).
- Prefer unique filenames for wikilinks (e.g. `[[GrowthGuide]]`).
- Run changes on a small subset first to confirm behavior.

If you want I can:

- Commit the recent prune to git with a message.
- Show a list of modified files or diffs for review.
