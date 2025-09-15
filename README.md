# Mycelium scripts — quick manual

![alttext](https://github.com/Samuelschoeberl/ATLA_Campaign/blob/main/Mycelium/Mycelium%20Logo.png)
This README explains the `Mycelium/scripts` utilities in this repository, how they interact with the `Player Root` folder, and quick workflows for a DM or a Player.

## What these scripts do

- `Mycelium/scripts/append_backlinks.py` — scans markdown files for `[[wikilink]]` tokens and (dry-run by default) produces a `## Backlinks` section listing incoming links; use `--apply` to write changes.
- `Mycelium/scripts/build_tag_backlinks.py` — scans for hashtag-style tags (e.g. `#NightBloom`) and writes per-tag summary files under an output dir (dry-run by default; `--apply` to write).
- `Mycelium/scripts/animate_pagerank.py` — builds a self-contained HTML animation from timestamped snapshot files named like `<timestamp>_<root>.md` (parses JSON blocks or markdown tables).
- `Mycelium/scripts/grow_mushroom.py` — a proxy that delegates to the Python implementation under `Mycelium/scripts/Python` if present.

## How they relate to `Player Root`

- The scripts scan the repository for `.md` files (including files under `Player Root/PCs`, `Player Root/NPCs`, `Player Root/Rules`, `Player Root/Organisations`, `Player Root/variable`, etc.).
- `append_backlinks.py` will add Obsidian-style links `[[relative/path/to/file]]` into target files so you can see where a PC, NPC or location is referenced.
- `build_tag_backlinks.py` aggregates tag usage into `Tag_Summaries/` (by default), giving a quick index of all files mentioning a tag.
- `animate_pagerank.py` reads snapshot files (eg `20250915_Player Root.md`) and produces an HTML animation useful for visualising changing prominence of PCs/NPCs/locations over time.

## Quick commands (run from repo root)

- Dry-run backlink scan:
  `python3 Mycelium/scripts/append_backlinks.py --root .`
- Apply backlinks (writes files):
  `python3 Mycelium/scripts/append_backlinks.py --root . --apply`
- Build tag summaries (dry-run):
  `python3 Mycelium/scripts/build_tag_backlinks.py --root . --outdir Tag_Summaries`
- Write tag summaries:
  `python3 Mycelium/scripts/build_tag_backlinks.py --root . --outdir Tag_Summaries --apply`
- Create PageRank animation from snapshots in `Player Root`:
  `python3 Mycelium/scripts/animate_pagerank.py --dir "Player Root" --out "Player Root/mycelium_animation.html"` doesn't work yet

## DM recommended workflow

write your Dms notes into a folder that you list in .gitgnore like Dms Root

1. Commit or copy the repo as a backup.
2. Run backlink dry-run and inspect the preview:
   `python3 Mycelium/scripts/append_backlinks.py --root .`
3. If satisfied, apply backlinks:
   `python3 Mycelium/scripts/append_backlinks.py --root . --apply`
4. Build tag summaries for session prep:
   `python3 Mycelium/scripts/build_tag_backlinks.py --root . --apply`
5. If you maintain periodic snapshots, generate an animation and open the HTML to visualise story prominence.

## Player quick usage — where to find everything about your character

Players: most of the information about a character is stored in the PCs folder. Look in `Player Root/PCs/` (player-facing area) depending on your group's workflow. Or edit general information about the world or npc in files on the whole Player Root with your content. Feel free to write create files for bending moves just tag them with #player_created_rule to clarify its not yet been cleared officially yet or it still needs work.

What to look for:

- Character sheet file (usually `<Name> character sheet.md`) — canonical stats
- Session notes and encounters — files whose titles describe an event; these contain context and references to the PC.
- Images and media — look for PNG/JPG files in the same folder (some characters have portraits next to their MD file).
- Backups — files ending in `.bak` are safe copies made previously.

Backlinks and tags (how to find cross-references):

- After the DM runs the repo tools (recommended), each character file will include a `## Backlinks` section listing files that refer to that PC. Open your PC file and scroll to `## Backlinks` to see where you've been mentioned.
- The DM may also generate `Tag_Summaries/` (e.g. `Tag_Summaries/NightBloom/NightBloom.md`) which collects all files using a particular `#tag` (useful for themes, factions, or story hooks).

If you want to preview changes locally (read-only):

```
python3 Mycelium/scripts/append_backlinks.py --root .
python3 Mycelium/scripts/build_tag_backlinks.py --root .
```

These run in dry-run mode by default and will print previews; do not run `--apply` unless you are coordinating with the DM.

## Safety & tips

- Both backlink and tag scripts default to dry-run; always preview before `--apply`.
- Back up or commit before running `--apply`.
- `append_backlinks.py` will include PageRank info if `Mycelium/pagerank.json` exists.
- Snapshot files must match the pattern `^\d+_.*\.md$` for `animate_pagerank.py` to detect them.

## Want automation?

If you want, create a small wrapper script that commits first, runs the scans with `--apply`, and exports the animation—I'll help create it.

---

Generated: concise usage guide for Mycelium scripts and `Player Root` integration.
