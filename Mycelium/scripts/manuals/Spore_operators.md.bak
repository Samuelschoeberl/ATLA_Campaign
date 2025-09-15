# Spore operators

This file collects useful terminal commands to quickly "spread spores" across your markdown files by adding tags (`#tag`) and internal links (`[[Link]]`). These operations let your wiki tools and visualisations pick up new relationships so the mushrooms can "grow" and propagate through the graph.

## Why this matters

- Tags (`#spore`, `#mushroom`, etc.) make groupings and search fast.
- Wikilinks (`[[Unique File Name]]`) create explicit graph edges that rigs like `Wikigraphs.py` and other tools use to visualise and propagate content.
- Use unique filenames (kebab-case or PascalCase) so `[[Name]]` resolves unambiguously.

## Safety first (backups & dry run)

Create a quick backup before bulk edits:

```bash
mkdir -p backups
cp -- *.md backups/ 2>/dev/null || cp *.md backups/ 2>/dev/null
```

Dry-run preview (doesn't modify files):

```bash
LINE='[#spore] [[GrowthGuide]]'
shopt -s nullglob
for f in ./*.md; do
  printf 'Would append to %s: %s\n' "$f" "$LINE"
done
shopt -u nullglob
```

## Single-file append (quick)

Append a single line to one file:

```bash
printf '%s\n' 'My custom line with ' >> /path/to/file.md
```

## Non-recursive: append to every `.md` in current folder

Simple, safe variant (handles quotes and special characters):

```bash
LINE='My custom line with '
shopt -s nullglob
for f in ./*.md; do
  printf '%s\n' "$LINE" >> "$f"
done
shopt -u nullglob
```

## Robust: ensure a newline before appending (macOS-compatible)

Some editors leave no trailing newline. This ensures your appended line doesn't merge with the last line:

```bash
LINE='My custom line with '
shopt -s nullglob
for f in ./*.md; do
  if [ -s "$f" ] && [ "$(tail -c1 "$f" | od -An -t uC | tr -d ' ')" != "10" ]; then
    printf '\n' >> "$f"
  fi
  printf '%s\n' "$LINE" >> "$f"
done
shopt -u nullglob
```

## Recursive: include subfolders

Use `find` to walk subfolders and handle filenames safely:

```bash
LINE='My custom line with '
find . -type f -name '*.md' -print0 | while IFS= read -r -d '' f; do
  if [ -s "$f" ] && [ "$(tail -c1 "$f" | od -An -t uC | tr -d ' ')" != "10" ]; then
    printf '\n' >> "$f"
  fi
  printf '%s\n' "$LINE" >> "$f"
done
```

## One-line variant for quick paste

Non-recursive, nullglob, single-line (pasteable):

```bash
shopt -s nullglob; LINE='My custom line with '; for f in ./*.md; do printf '%s\n' "$LINE" >> "$f"; done; shopt -u nullglob
```

## Best practices

- Use a consistent tag namespace (e.g. `#spore`, `#mushroom`, `#propagate`).
- Use unique filenames for wiki linking: `GrowthGuide.md` -> `[[GrowthGuide]]`.
- Prefer `printf` over `echo` for predictable output across shells.
- Run the dry-run first, then backup, then apply.
- Use git to track and revert changes if needed: `git add -A && git commit -m "spore: append tags/links"`.

---

Short contract

- Inputs: directory of `.md` files and a `LINE` string.
- Output: the `LINE` appended to each targeted file (optionally after ensuring a newline).
- Error modes: no `.md` files found (nullglob avoids literal pattern), permission errors, or malformed `LINE` if not quoted.

Edge cases

- Empty files: the LINE will be added as first line.
- Files without trailing newline: handled by robust snippets.
- Filenames with spaces: handled by `find -print0` variant and quoting in loops.

If you'd like, I can:

- Add a short script `spore_append.sh` to `Mycelium/` (executable) so you can run it with one argument.
- Run a dry-run here on a sample folder and show what would be changed.

## Included helper script

I added an executable helper script `Mycelium/spore_append.sh`.

Quick usage example:

```bash
# dry-run, non-recursive
Mycelium/spore_append.sh -l '' -p Mycelium -n

# apply recursively and backup first
Mycelium/spore_append.sh -l '' -p . -R -b
```

The script supports: -l LINE, -p PATH, -R (recursive), -n (dry-run), -b (backup).
