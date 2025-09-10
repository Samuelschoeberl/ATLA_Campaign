<!-- See MANUALS/Usage_Guide.md for a short summary of all manuals -->

## 🔄 How to Sync Your Vault (Git + Collectionfiles)

To sync your local vault with the remote repository **and** automatically update all collectionfiles (backlink blocks):

```bash
python -c "from Wiki_File_System_Manager import Sync; Sync()"
```

To manually recreate all collectionfiles (backlink blocks) without syncing:

```bash
python Wiki_File_System_Manager.py --ext .md --recreate-collectionfiles
```

This will:

- Stage, commit, and push all local changes
- Pull and merge the latest from `origin/main`
- Recreate all collectionfiles (backlink blocks)
- Commit and push any new collectionfile changes

---

## 🚀 Quickstart

Copy-paste friendly commands. See also: [[Wiki_File_System_Manager (Manual)]], [[Wiki_File_System_Manager (FAQ)]]

> **Tips:** Start with `--dry-run`, scope with `--ext .md`, keep backups with `--backup .bak`.

---

### Safe wiki-link bracketing

Bracket plain mentions, skipping already-linked:

```bash
python Wiki_File_System_Manager.py --ext .md --find "[[[[Bumi]]]]" --bracket --dry-run
```

```
python Wiki_File_System_Manager.py --ext .md --find "[[[[Bumi]]]]" --bracket --backup .bak
```

### Literal find/replace

```bash
python Wiki_File_System_Manager.py --ext .md --find "Omashu" --replace "City of Omashu" --backup .bak
```

Case-sensitive:

```bash
python Wiki_File_System_Manager.py --ext .md --case-sensitive --find "Spirit" --replace "spirit" --backup .bak
```

With punctuation/special chars (still literal):

```bash
python Wiki_File_System_Manager.py --ext .md --find "old" --replace "new" --backup .bak
```

---

### Scope control

Only session logs:

```bash
python Wiki_File_System_Manager.py Sessions --ext .md --include "**/Session*.md" --find "Appa" --replace "Appa the Sky Bison"
```

Exclude extra dirs:

```bash
python Wiki_File_System_Manager.py --ext .md --exclude-dir "Archive" "Exports" --find "Sokka" --replace "Sokka (Water Tribe)"
```

Single file:

```bash
python Wiki_File_System_Manager.py Notes/NPCs/Katara.md --find "Waterbending" --replace "Waterbending (Healing)"
```

Follow symlinks (rare):

```bash
python Wiki_File_System_Manager.py --follow-symlinks --ext .md --find "Ba Sing Se" --replace "Ba Sing Se (Lower Ring)"
```

Multiple roots:

```bash
python Wiki_File_System_Manager.py Notes Lore --ext .md --find "Pai Sho" --replace "Pai Sho (White Lotus)"
```

---

### Collections (backlinks)

Create/update `Action.md` backlinks block + `AllAction.md` embeds:

```bash
python Wiki_File_System_Manager.py --ext .md --collectionfile "Indexes/Action.md" --compact
```

---

### Append lines

Append a footer if missing:

```bash
python Wiki_File_System_Manager.py --ext .md --append "[[Index:NPCs]]" --backup .bak
```

Combine append + replace in one pass:

```bash
python Wiki_File_System_Manager.py --ext .md \
	--append "[[Index:Sessions]]" \
	--find "Zuko" --replace "Zuko (Crowned Prince)" \
	--backup .bak --compact
```

---

That’s it. Keep `--dry-run` until output looks right; then drop it and keep `--backup .bak` for safety.
