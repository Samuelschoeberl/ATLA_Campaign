# Wiki_File_System_Manager.py Manual

## Overview

`Wiki_File_System_Manager.py` is a powerful bulk find & replace tool designed for markdown files in wiki-style folder hierarchies (such as Obsidian vaults). It recursively processes all markdown files under a specified directory tree, performing text replacements with various options for safety and customization.

## Core Functionality

- **Bulk find & replace** across all markdown files in a directory tree
- **Bracketing mode** to automatically create Obsidian-style wiki-links `[[...]]`
- **Dry-run mode** to preview changes without modifying files
- **Backup support** to preserve original files before changes
- **Smart exclusion** of common directories (`.git`, `node_modules`, etc.)
- **Color-coded output** for easy visualization of changes

## Basic Usage

```bash
python3 Wiki_File_System_Manager.py [paths...] --find TEXT [--replace TEXT | --bracket] [options]
```

### Required Arguments

- `paths` - One or more root directories to scan (defaults to current directory if omitted)
- `--find TEXT` - Text to search for (case-insensitive by default)
- `--replace TEXT` - Replacement text (required unless using `--bracket`)

### Alternative Mode

- `--bracket` or `-b` - Instead of replacing, wrap matches with `[[...]]` to create wiki-links

## Common Usage Examples

### 1. Simple Text Replacement

Replace all instances of "oldname" with "newname":

```bash
python3 Wiki_File_System_Manager.py ../../../Player\ Root/ --find "[[Movement definition]]" --replace "[[Movement]]"
```

### 2. Create Wiki-Links (Bracketing Mode)

Automatically wrap all instances of "Earthbending" with brackets to create `[[Earthbending]]` links:

```bash
python3 Wiki_File_System_Manager.py /path/to/wiki --find Earthbending --bracket
```

This is useful for converting plain text references into Obsidian wiki-links.

### 3. Remove Tags

Remove a hashtag from all files (replace with empty string):

```bash
python3 Wiki_File_System_Manager.py "Dms Root/" --find "#player_root" --replace ""
```

### 4. Dry-Run Preview

Preview changes before applying them:

```bash
python3 Wiki_File_System_Manager.py . --find foo --replace bar --dry-run
```

This shows what would be changed without actually modifying any files.

### 5. Create Backups

Make backups with `.bak` suffix before modifying files:

```bash
python3 Wiki_File_System_Manager.py . --find old --replace new --backup .bak
```

### 6. Case-Sensitive Search

Perform case-sensitive replacement:

```bash
python3 Wiki_File_System_Manager.py . --find TODO --replace DONE --case-sensitive
```

### 7. Multiple Directories

Process multiple directory trees at once:

```bash
python3 Wiki_File_System_Manager.py "Player Root/" "Dms Root/" --find text --replace newtext
```

## Command-Line Options

### Search & Replace Options

| Option | Description |
|--------|-------------|
| `--find TEXT` | Text to search for (required) |
| `--replace TEXT` | Replacement text (required unless using `--bracket`) |
| `-b, --bracket` | Bracketing mode: wrap matches with `[[...]]` |
| `--case-sensitive` | Make search case-sensitive (default is case-insensitive) |

### Directory Control

| Option | Description |
|--------|-------------|
| `--exclude-dir DIR [DIR...]` | Additional directory names to exclude |
| `--no-default-excludes` | Don't exclude default directories |
| `--follow-symlinks` | Follow symbolic links to directories |

**Default excluded directories:**
- `.git`
- `node_modules`
- `.obsidian`
- `__pycache__`
- `venv`
- `.venv`
- `backups`

### Safety & Output Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview changes without writing files |
| `--backup SUFFIX` | Create backup files with specified suffix (e.g., `.bak`) |
| `--compact` | Compact, color-coded output |
| `--no-color` | Disable ANSI colors |

## Output Modes

### Compact Mode (`--compact`)

Shows one line per changed file with color-coding:

```
[DRY] /path/to/file.md (3)
[WRITE] /path/to/other.md (1)
Summary: APPLIED files=52 changed=2 repl=4 backup=.bak
```

- `[DRY]` - Cyan: dry-run mode
- `[WRITE]` - Green: file was modified
- `(N)` - Gray: number of replacements in that file

### Verbose Mode (default)

Shows detailed information:

```
[write] /path/to/file.md -> 3 replacement(s)
[write] /path/to/other.md -> 1 replacement(s)

=== Summary ===
Mode: APPLIED (writes performed)
Files scanned: 52
Files changed: 2
Total replacements: 4
Backup suffix used: .bak

Changed files (up to 10 shown):
  /path/to/file.md (3)
  /path/to/other.md (1)
```

## How Bracketing Mode Works

The `--bracket` mode intelligently wraps text with `[[...]]` for Obsidian wiki-links:

### When it brackets:
- Text is NOT already inside `[[...]]`
- Text is NOT adjacent to letters (word boundaries respected)

### When it skips:
- Already inside wiki-link brackets: `[[Earthbending]]`
- Adjacent to letters: `Earthbending123` or `myEarthbending`

### Example:

Input:
```
Earthbending is cool. [[Earthbending]] already linked.
The Earthbending123 exception.
```

Command:
```bash
python3 Wiki_File_System_Manager.py . --find Earthbending --bracket
```

Output:
```
[[Earthbending]] is cool. [[Earthbending]] already linked.
The Earthbending123 exception.
```

## Workflow Examples

### Scenario 1: Renaming a Character Across All Notes

You need to rename "Zuko" to "Prince Zuko" in all markdown files:

```bash
# 1. Preview the changes first
python3 Wiki_File_System_Manager.py . --find "Zuko" --replace "Prince Zuko" --dry-run

# 2. Apply with backups for safety
python3 Wiki_File_System_Manager.py . --find "Zuko" --replace "Prince Zuko" --backup .bak
```

### Scenario 2: Converting Plain References to Wiki-Links

You want to convert all mentions of "Firebending" into wiki-links:

```bash
# Create [[Firebending]] links everywhere
python3 Wiki_File_System_Manager.py "Dms Root/" "Player Root/" --find Firebending --bracket
```

### Scenario 3: Cleaning Up Tags

Remove obsolete tags from your vault:

```bash
# Remove #deprecated tag
python3 Wiki_File_System_Manager.py . --find "#deprecated" --replace "" --compact
```

### Scenario 4: Updating File References

Update file references after reorganization:

```bash
# Update old path references
python3 Wiki_File_System_Manager.py . \
  --find "old_folder/document.md" \
  --replace "new_folder/document.md" \
  --dry-run
```

## Safety Best Practices

1. **Always dry-run first** - Use `--dry-run` to preview changes
2. **Use backups for important changes** - Add `--backup .bak` for safety
3. **Start with small scope** - Test on a single directory before running on entire vault
4. **Check case sensitivity** - Default is case-insensitive; use `--case-sensitive` if needed
5. **Exclude sensitive directories** - Use `--exclude-dir` for areas you don't want to modify

## Common Patterns

### Replace with Empty String (Deletion)
```bash
# Remove text completely
python3 Wiki_File_System_Manager.py . --find "delete this" --replace ""
```

### Case-Insensitive Tag Removal
```bash
# Remove tags regardless of case
python3 Wiki_File_System_Manager.py . --find "#oldtag" --replace "" --compact
```

### Specific Directory Processing
```bash
# Only process NPCs folder
python3 Wiki_File_System_Manager.py "Dms Root/NPCs/" --find old --replace new
```

### Exclude Specific Folders
```bash
# Process but skip archive and backup folders
python3 Wiki_File_System_Manager.py . --find text --replace newtext \
  --exclude-dir archive backup old_files
```

## Troubleshooting

### No files found
- Check that you're in the correct directory
- Verify the path argument points to a directory with `.md` files
- Check if directories are being excluded (use `--no-default-excludes` to test)

### No matches found
- Verify the search text is correct
- Check if you need `--case-sensitive`
- Try a dry-run with a known string to test the search

### Unexpected replacements
- Use `--dry-run` first to preview
- Check word boundaries (bracketing mode respects them automatically)
- Consider `--case-sensitive` if needed

### Files not being modified
- Ensure you're not using `--dry-run`
- Check file permissions
- Verify files aren't marked as read-only

## Technical Notes

- **Encoding**: All files are read/written as UTF-8
- **Line endings**: Preserved as-is from original files
- **Regex**: Uses Python's `re` module with proper escaping
- **Recursion**: Uses `os.walk()` for efficient directory traversal
- **Backup timing**: Backups created only when file is actually modified

## Integration with Other Scripts

This script is part of the Mycelium toolkit and works well with:

- `sync_variables.py` - Use Wiki_File_System_Manager to update variable references
- `recreate_pcs.py` - Use after bulk renaming to regenerate character sheets
- `watch_and_regen.py` - Watches for changes made by Wiki_File_System_Manager

## Version History

- **2025-10-25**: Rewritten as focused bulk find & replace tool
  - Streamlined to core functionality
  - Improved bracketing logic
  - Added compact output mode
  - Enhanced color-coded display

## See Also

- `sync_variables_manual.md` - Variable synchronization
- `recreate_pcs_manual.md` - Character sheet generation
- `README.md` - Overview of all Mycelium scripts
