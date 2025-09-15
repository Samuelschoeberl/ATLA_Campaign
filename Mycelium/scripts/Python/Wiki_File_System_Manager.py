"""Wrapper for scripts/manuals/Wiki_File_System_Manager.py"""
from importlib import import_module
try:
    mod = import_module('Mycelium.scripts.manuals.Wiki_File_System_Manager')
except Exception:
    from pathlib import Path
    import importlib.util
    alt = Path(__file__).resolve().parent.joinpath('scripts').joinpath('manuals').joinpath('Wiki_File_System_Manager.py')
    if alt.exists():
        spec = importlib.util.spec_from_file_location('Mycelium._manuals_Wiki_File_System_Manager', str(alt))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore
        mod = module
    else:
        raise

build_graph = getattr(mod, 'build_graph')
"""Proxy loader for scripts/manuals/Wiki_File_System_Manager.py"""
import importlib

_mod = importlib.import_module('Mycelium.scripts.manuals.Wiki_File_System_Manager')
for _k, _v in _mod.__dict__.items():
    if not _k.startswith('_'):
        globals()[_k] = _v

# --- Bulk Find & Replace Script ---
# This script provides advanced bulk find & replace, backlink collection, and file manipulation utilities for Markdown and text files.
# It is designed for use in Obsidian vaults, code repositories, and similar folder structures.
#
# Features:
#   - Recursive find & replace with optional bracketing (Obsidian-style links)
#   - Backlink collection and auto-updating of collection files
#   - Appending strings to files
#   - Color-coded and compact output modes
#   - Dry-run and backup support
#   - Exclusion of common folders (e.g., .git, node_modules)
#
# Author: Samuelschoeberl (2025)
#
from pathlib import Path
import argparse
import os
import re
import sys
from shutil import copy2
import subprocess
# -------- Color helpers --------
def Sync():
    # NOTE: remove_auto_collection_block was previously nested/duplicated here.
    # The function is intentionally omitted to avoid accidental self-mutation
    # of this module. Collectionfile recreation routines should avoid
    # modifying this file; any automated removal of blocks should be
    # performed on target files only.
    """
    Syncs the local repository with the remote 'main' branch.
    Pulls all changes from 'origin/main' into the current branch.
    """
    try:
        # Stage all changes
        subprocess.run(["git", "add", "-A"], check=True)
        # Commit with automated message (ignore if nothing to commit)
        commit_proc = subprocess.run(["git", "commit", "-m", "Automated sync commit"], capture_output=True, text=True)
        # Git may report 'nothing to commit' on stdout or stderr depending on version/localization.
        out = (commit_proc.stdout or "") + (commit_proc.stderr or "")
        if commit_proc.returncode != 0:
            if 'nothing to commit' in out.lower() or 'no changes added to commit' in out.lower():
                print("Nothing to commit, working tree clean.")
                # Nothing to do; continue to fetch/merge in case remote has updates
            else:
                print(f"Git commit failed: {out.strip()}")
                # Continue but avoid pushing an undefined state
        else:
            # commit succeeded; push the new commit
            subprocess.run(["git", "push", "origin", "HEAD"], check=True)
        # Push local commits to remote
        # Fetch latest from origin and merge origin/main into current branch
        subprocess.run(["git", "fetch", "origin"], check=True)
        subprocess.run(["git", "merge", "origin/main"], check=True)
        print("Sync complete.")
        main(["--recreate-collectionfiles"])
        # Stage, commit, and push any changes from collectionfile recreation
        subprocess.run(["git", "add", "-A"], check=True)
        # Try to commit collectionfile updates; ignore failure if nothing changed
        coll_commit = subprocess.run(["git", "commit", "-m", "Automated collectionfile update"], capture_output=True, text=True)
        coll_out = (coll_commit.stdout or "") + (coll_commit.stderr or "")
        if coll_commit.returncode == 0:
            subprocess.run(["git", "push", "origin", "HEAD"], check=True)
        else:
            if 'nothing to commit' in coll_out.lower() or 'no changes added to commit' in coll_out.lower():
                print("No collectionfile changes to commit.")
            else:
                print(f"Collectionfile commit failed: {coll_out.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"Error during sync: {e}")
        return 1
    return 0
from typing import Iterator, List, Optional, Sequence, Tuple, Union, Callable, Set
try:
    from Mycelium.config_common import get_graph_excludes
except Exception:
    def get_graph_excludes(root='.'):
        return ['backups/', 'Mycelium/']
import fnmatch
import json
try:
    from config_loader import get_config
except Exception:
    def get_config(key, default):
        return default


# Default directories to exclude from scanning
_dms_root = get_config('dms_root', 'DMs Part')
DEFAULT_EXCLUDES = {".git", "node_modules", ".obsidian", "__pycache__", "venv", ".venv"}
if _dms_root:
    DEFAULT_EXCLUDES.add(_dms_root)


# -------- Color helpers --------
class Colors:
    """ANSI color codes for terminal output formatting."""
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"



def colorize(enabled: bool, text: str, *effects: str) -> str:
    """Wrap text in ANSI color codes if enabled."""
    if not enabled or not effects:
        return text
    return "".join(effects) + text + Colors.RESET



def iter_files(
    roots: Sequence[Path],
    include_globs: Sequence[str],
    exclude_dirs: Sequence[str],
    use_default_excludes: bool,
    follow_symlinks: bool,
) -> Iterator[Path]:
    """
    Recursively yield files under the given root directories, honoring include glob patterns and directory excludes.
    - roots: List of root directories or files to scan.
    - include_globs: Glob patterns to include (e.g., ['**/*.md']).
    - exclude_dirs: Directory names to exclude.
    - use_default_excludes: Whether to use built-in excludes.
    - follow_symlinks: Whether to follow symlinks.
    """
    excludes = set(exclude_dirs)
    if use_default_excludes:
        excludes |= DEFAULT_EXCLUDES

    for root in roots:
        if root.is_file():
            # For single files, still apply include_globs if provided
            rel = root.name
            if include_globs:
                if not any(fnmatch.fnmatch(rel, patt) or fnmatch.fnmatch(str(root), patt) for patt in include_globs):
                    continue
            yield root
            continue

        for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
            # Prune excluded directories
            pruned = []
            for d in list(dirnames):
                if d in excludes:
                    pruned.append(d)
            for d in pruned:
                dirnames.remove(d)

            for fname in filenames:
                fpath = Path(dirpath) / fname
                if include_globs:
                    # Test both path relative to root and absolute string
                    try:
                        rel = str(fpath.relative_to(root))
                    except Exception:
                        rel = str(fpath)
                    if not any(fnmatch.fnmatch(rel, patt) or fnmatch.fnmatch(str(fpath), patt) for patt in include_globs):
                        continue
                yield fpath



def should_process_file(path: Path, exts: Sequence[str]) -> bool:
    """Return True if the file should be processed based on extension filter."""
    if not exts:
        return True
    if not path.is_file():
        return False
    return path.suffix.lower() in {e.lower() for e in exts}



def load_text(path: Path) -> Optional[str]:
    """Read a UTF-8 text file, returning None if not decodable."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Not a UTF-8 text file
        return None
    except Exception:
        return None


def unobsidify(text: str) -> str:
    """Return a plain-text version of an Obsidian markdown string.

    - Replaces wiki-links [[...]] and transclusions ![[...]] with readable text.
    - Removes YAML frontmatter, heading markers, emphasis and code markers.
    - Converts markdown tables into compact text (keeps header + first two rows).
    - Collapses code fences to a short inline representation.
    """
    if not text:
        return text

    s = text
    # remove YAML frontmatter
    s = re.sub(r'^---\n.*?\n---\n', '', s, flags=re.S)
    # remove Obsidian comments %% ... %%
    s = re.sub(r'%%.*?%%', '', s, flags=re.S)

    # replace transclusions and wikilinks: prefer alias when present
    s = re.sub(r'!\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', s)
    s = re.sub(r'!\[\[([^\]]+)\]\]', r'\1', s)
    s = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', s)
    s = re.sub(r'\[\[([^\]]+)\]\]', r'\1', s)

    # collapse code fences (keep first non-empty line)
    def _collapse_code(m: re.Match) -> str:
        body = m.group(2) or ''
        for ln in body.splitlines():
            ln = ln.strip()
            if ln:
                return f'`{ln}`'
        return '`code`'

    s = re.sub(r'(```|~~~)(.*?)\1', _collapse_code, s, flags=re.S)

    # markdown links [text](url) -> text
    s = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', s)
    # remove heading markers and emphasis/code markers
    s = re.sub(r'(?m)^[ \t]*#{1,6}\s*', '', s)
    s = re.sub(r'[\*_`~]+', '', s)

    # convert simple markdown tables into compact text summary
    def _summarize_table(block: str) -> str:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            return ''

        # header is first line, skip separator if present
        header = lines[0]
        if len(lines) > 1 and re.match(r'^\s*\|?\s*[:\-]+', lines[1]):
            data = lines[2:]
        else:
            data = lines[1:]

        def split_row(r: str) -> List[str]:
            # split on pipes, strip leading/trailing empty cells caused by edge pipes
            cells = [c.strip() for c in re.split(r'\s*\|\s*', r.strip().strip('|'))]
            return cells

        hdr_cells = split_row(header)
        # remove any columns named 'Auto' (case-insensitive)
        keep_indices = [i for i, h in enumerate(hdr_cells) if h and h.strip().lower() != 'auto']
        if keep_indices:
            # filter hdr_cells and all shown rows to only kept indices
            hdr_cells = [hdr_cells[i] for i in keep_indices]

            def filter_row_by_indices(row: List[str]) -> List[str]:
                return [row[i] if i < len(row) else '' for i in keep_indices]
        else:
            # nothing to keep? fall back to original header (avoid empty table)
            def filter_row_by_indices(row: List[str]) -> List[str]:
                return row

        # show all data rows for complete table output
        shown = [split_row(r) for r in data]

        # compute column count as max across header and all shown rows
        col_count = max(len(hdr_cells), max((len(r) for r in shown), default=0))

        # normalize row lengths by padding empty cells
        def normalize_row(row: List[str]) -> List[str]:
            if len(row) < col_count:
                return row + [''] * (col_count - len(row))
            return row[:col_count]

        hdr = normalize_row(hdr_cells)
        shown_norm = [normalize_row(filter_row_by_indices(r)) for r in shown]

        # compute max width per column (no huge extra padding; keep compact)
        EXTRA_PAD = 2
        widths = [0] * col_count
        for ci in range(col_count):
            w = len(hdr[ci])
            for r in shown_norm:
                w = max(w, len(r[ci]))
            widths[ci] = w + EXTRA_PAD

        # helpers to build boxed ASCII table using monospace-friendly chars
        def _border_line() -> str:
            parts = []
            for w in widths:
                parts.append('-' * (w + 2))
            return '+' + '+'.join(parts) + '+'

        def format_row_box(row: List[str]) -> str:
            parts = []
            for i, cell in enumerate(row):
                # provide a single space padding on each side
                parts.append(' ' + cell.ljust(widths[i]) + ' ')
            return '|' + '|'.join(parts) + '|'

        out_lines: List[str] = []
        out_lines.append('TABLE:')
        out_lines.append(_border_line())
        out_lines.append(format_row_box(hdr))
        out_lines.append(_border_line())
        for row in shown_norm:
            out_lines.append(format_row_box(row))
        out_lines.append(_border_line())
        return '\n'.join(out_lines)

    # replace contiguous table blocks (lines beginning with |) conservatively
    s = re.sub(r'(?m)(^\s*\|.*(?:\n^\s*\|.*)+)', lambda m: _summarize_table(m.group(0)), s)

    # normalize whitespace
    s = re.sub(r'\r\n|\r', '\n', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    s = s.strip()
    return s


def gather_file_tree(root: Path, exts=None, excludes=None, include_gitignored: bool = False):
    """Return sizes, contents, raw_contents for files under root.

    This is a lightweight variant of the function used in Wikigraphs; it
    mirrors behavior used by the graph builder and visualization tools.
    """
    if exts is None:
        exts = {'.md', '.markdown', '.txt'}
    if excludes is None:
        excludes = DEFAULT_EXCLUDES

    root = Path(root).resolve()
    sizes = {}
    contents = {}
    raw_contents = {}

    gitignore_path = root.joinpath('.gitignore')
    git_patterns = []
    if gitignore_path.exists():
        try:
            raw = gitignore_path.read_text(encoding='utf-8', errors='replace')
            for ln in raw.splitlines():
                ln = ln.strip()
                if not ln or ln.startswith('#'):
                    continue
                git_patterns.append(ln)
        except Exception:
            git_patterns = []

    def matches_gitignore(rel_str: str, parts: List[str]) -> bool:
        for pat in git_patterns:
            p = pat.strip()
            if not p:
                continue
            if p.endswith('/'):
                name = p.rstrip('/')
                if any(part == name for part in parts):
                    return True
                if rel_str.startswith(name + os.sep):
                    return True
            elif '/' in p:
                if fnmatch.fnmatch(rel_str, p):
                    return True
            else:
                if fnmatch.fnmatch(parts[-1], p):
                    return True
        return False

    for p in root.rglob('*'):
        try:
            rel = p.relative_to(root)
            rel_str = str(rel)
            parts = list(rel.parts)
        except Exception:
            rel_str = str(p)
            parts = list(p.parts)

        if any(part in excludes for part in parts):
            continue
        low_parts = [pp.lower() for pp in parts]
        if any('collectionfile' in lp or 'collectionfiles' in lp for lp in low_parts):
            continue
        if any('expandedcollections' in lp or 'simple_expanded_megafile' in lp or 'expanded' == lp for lp in low_parts):
            continue
        if git_patterns and not include_gitignored and matches_gitignore(rel_str, parts):
            continue
        if p.is_file() and (not exts or p.suffix.lower() in exts):
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            rel = p.relative_to(root)
            parts = list(rel.parts)
            file_key = "/".join(parts)
            sizes[file_key] = size or 1
            try:
                if p.suffix.lower() == '.md':
                    txt = p.read_text(encoding='utf-8', errors='replace')
                    contents[file_key] = unobsidify(txt)
                    raw_contents[file_key] = txt
            except Exception:
                pass
            for i in range(1, len(parts)):
                dir_key = "/".join(parts[:i]) + "/"
                sizes[dir_key] = sizes.get(dir_key, 0) + (size or 1)
            sizes['/'] = sizes.get('/', 0) + (size or 1)

    return sizes, contents, raw_contents



def write_text_with_backup(path: Path, content: str, backup_suffix: Optional[str], color: bool) -> None:
    """Write content to file, making a backup if requested."""
    # Never mutate this script
    if os.path.abspath(str(path)) == os.path.abspath(__file__):
        if color:
            print(f"{Colors.DIM}[skip]{Colors.RESET} {path} (self-mutation prevented)")
        return

    # Create a single backup if requested
    if backup_suffix:
        try:
            backup_path = path.with_suffix(path.suffix + backup_suffix)
            copy2(path, backup_path)
            if color:
                print(f"{Colors.DIM}[backup]{Colors.RESET} {backup_path}")
        except Exception as e:
            print(colorize(color, f"[warn] Failed to create backup for {path}: {e}", Colors.YELLOW), file=sys.stderr)

    try:
        # Always overwrite the file, even if content is unchanged
        path.write_text(content, encoding="utf-8")
        if color:
            print(f"{Colors.GREEN}[CONFIRM]{Colors.RESET} Overwrote {path}")
        if getattr(sys, '_wfsm_debug', False):
            print(f"[DEBUG] New content preview: {content[:100]!r}")
    except Exception as e:
        print(f"[ERROR] Failed to write to {path}: {e}", file=sys.stderr)



# -------- Collectionfile Cleanup and Recreation --------
def recreate_collectionfiles(roots: Sequence[Path], candidate_files: Sequence[Path], dry_run: bool, backup_suffix: Optional[str], color: bool, compact: bool):

    collectionfiles = []
    for f in candidate_files:
        # Ignore any file that is a backup (case-insensitive)
        if f.suffix.lower() == ".bak":
            continue
        # Only process .md files
        if f.suffix.lower() != ".md":
            continue
        text = load_text(f)
        if text is not None and "#Collectionfile" in text:
            collectionfiles.append(f)

    # Find all expected collectionfile paths (by label) that are missing and create them
    # For robustness, scan all candidate_files for #Collectionfile, and if a file is missing, create it
    # (This is a fallback for when a file is deleted or missing)
    for f in candidate_files:
        if f.suffix.lower() == ".bak":
            continue
        if f.suffix.lower() != ".md":
            continue
        if not f.exists():
            # Create a new file with #Collectionfile
            if not dry_run:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text("#Collectionfile\n", encoding="utf-8")
            # Always append to collectionfiles so update_collection_block runs for new files
            collectionfiles.append(f)
    updated = 0
    skipped = 0
    for target in collectionfiles:
        label = target.stem
        backlinks = gather_backlinks(label, candidate_files, exclude_path=target)
        changed, count = update_collection_block(
            target, roots, backlinks, label, dry_run, backup_suffix, color, compact
        )
        if changed:
            updated += 1
        else:
            skipped += 1

        # --- Also recreate Expanded<CollectionName>.md with ![[...]] embeds in a subfolder ---
        expanded_subfolder = target.parent / "ExpandedCollections"
        expanded_subfolder.mkdir(parents=True, exist_ok=True)
        expandedfile = expanded_subfolder / f"Expanded{label}.md"
        embed_lines = [f"![[{p.name}]]" for p in backlinks if p.suffix != ".bak"]
        if embed_lines:
            embed_content = "\n\n---\n---\n---\n\n".join(embed_lines) + "\n\n---\n---\n---\n\n"
        else:
            embed_content = "<!-- No backlinks found -->\n"
        if not dry_run:
            write_text_with_backup(expandedfile, embed_content, backup_suffix, color)

    print(f"Collectionfiles: {updated} updated, {skipped} skipped.")


# -------- Append String to Files --------

def append_string_to_files(
    files: Sequence[Path],
    append_str: str,
    dry_run: bool,
    backup_suffix: Optional[str],
    color: bool,
    compact: bool,
) -> int:
    """
    Append a string to the end of each file, unless already present.
    Returns the number of files changed.
    """
    changed_files = 0
    for f in files:
        text = load_text(f)
        if text is None:
            continue
        # Only append if not already present at the end
        if text.rstrip().endswith(append_str):
            if compact:
                print(f"{colorize(color, '[SKIP]', Colors.GRAY)} {colorize(color, str(f), Colors.DIM)} (already present)")
            else:
                print(f"[skip] {f} (already present)")
            continue
        new_text = text
        if not text.endswith("\n"):
            new_text += "\n"
        new_text += append_str + "\n"
        changed_files += 1
        if compact:
            tag = "DRY" if dry_run else "WRITE"
            tag_color = Colors.CYAN if dry_run else Colors.GREEN
            print(f"{colorize(color, '[' + tag + ']', tag_color)} {colorize(color, str(f), Colors.BOLD)} (appended)")
        else:
            if dry_run:
                print(f"[dry-run] {f} -> appended string")
            else:
                print(f"[write] {f} -> appended string")
        if not dry_run:
            write_text_with_backup(f, new_text, backup_suffix, color)
    return changed_files


# -------- Tag helpers and graph export --------
ROOT_MUSH_BEGIN = "<!-- BEGIN-ROOT-MUSHROOMS -->"
ROOT_MUSH_END = "<!-- END-ROOT-MUSHROOMS -->"


def extract_hashtags(text: str) -> List[str]:
    """Return a list of hashtag strings (without leading #) found in text."""
    if not text:
        return []
    # Match #tag, allowing slashes and dashes and apostrophes in tags
    tags = re.findall(r"(?<!\w)#([A-Za-z0-9_\-/']+)", text)
    # Normalize: lowercase
    return [t.strip() for t in tags if t.strip()]


try:
    # prefer local standalone helper to keep this module small
    from Mycelium.scripts.Python.ensure_tags_on_file import ensure_tags_on_file  # type: ignore
except Exception:
    # fallback to relative import if package context differs
    from .ensure_tags_on_file import ensure_tags_on_file  # type: ignore


def remove_tags_from_file(path: Path, tags: Sequence[str], dry_run: bool, backup_suffix: Optional[str], color: bool) -> bool:
    """Remove hashtag occurrences from a file. tags are without leading '#'. Return True if changed."""
    text = load_text(path)
    if text is None:
        return False
    changed = False
    new_text = text
    for t in tags:
        pattern = re.compile(r"(?<!\w)#" + re.escape(t) + r"\b", re.IGNORECASE)
        new_text, n = pattern.subn('', new_text)
        if n > 0:
            changed = True
    # Cleanup: collapse multiple spaces and blank lines produced
    new_text = re.sub(r"[ \t]+\n", "\n", new_text)
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    if changed and not dry_run:
        write_text_with_backup(path, new_text, backup_suffix, color)
    return changed


def infer_tags_for_file(path: Path, roots: Sequence[Path], candidate_files: Sequence[Path], max_tags: int = 5) -> List[str]:
    """Infer candidate tags for a file using folder names, wikilinks and filename tokens."""
    text = load_text(path) or ""
    tags = []
    # 1) folder names
    try:
        parent = path.parent
        while parent and parent != parent.parent:
            name = parent.name.strip()
            if name and name not in tags:
                tags.append(name)
            parent = parent.parent
    except Exception:
        pass
    # 2) wikilinks
    link_pattern = re.compile(r"\[\[\s*([^\]|#]+)")
    for m in link_pattern.finditer(text):
        t = m.group(1).strip()
        if t and t not in tags:
            tags.append(t)
    # 3) filename tokens
    stem = path.stem
    for tok in re.split(r"[\s_\-]+", stem):
        tok = tok.strip()
        if tok and tok not in tags:
            tags.append(tok)
    # Lowercase and limit
    normalized = []
    for t in tags:
        t2 = re.sub(r"[^A-Za-z0-9_\-/']+", '', t)
        if not t2:
            continue
        t2 = t2.replace(' ', '_')
        if t2.lower() not in [x.lower() for x in normalized]:
            normalized.append(t2)
        if len(normalized) >= max_tags:
            break
    return normalized


def write_root_mushroom_list(path: Path, mushrooms: Sequence[str], dry_run: bool, backup_suffix: Optional[str], color: bool) -> bool:
    """Write a small block listing root_mushroomlist_settings inside a file. Returns True if changed."""
    text = load_text(path) or ""
    block = [ROOT_MUSH_BEGIN]
    block.append(json.dumps(list(mushrooms)))
    block.append(ROOT_MUSH_END)
    block_text = "\n".join(block) + "\n"
    pattern = re.compile(re.escape(ROOT_MUSH_BEGIN) + r".*?" + re.escape(ROOT_MUSH_END), re.DOTALL)
    if pattern.search(text):
        new_text = pattern.sub(block_text, text, count=1)
    else:
        new_text = text.rstrip('\n') + "\n\n" + block_text
    if new_text != text:
        if not dry_run:
            write_text_with_backup(path, new_text, backup_suffix, color)
        return True
    return False


try:
    from Mycelium.scripts.Python.graph_builder import build_graph  # type: ignore
except Exception:
    from .graph_builder import build_graph  # type: ignore



def make_replacer(
    needle: str,
    replacement: Optional[str],
    case_sensitive: bool,
    bracket_mode: bool,
) -> Tuple[re.Pattern, Union[str, Callable[[re.Match], str]]]:
    """
    Build a regex pattern and replacement for find/replace.
    If bracket_mode is enabled, wrap matches with [[...]] unless already inside a link.
    Returns (pattern, replacement or function).
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    escaped = re.escape(needle)

    if bracket_mode:
        # Match the needle anywhere, but only wrap if neighbors are not letters
        pattern = re.compile(escaped, flags)

        def repl_func(match):
            s = match.string
            start, end = match.start(), match.end()
            # Check left neighbor
            if start > 0 and s[start-1].isalpha():
                return match.group(0)
            # Check right neighbor
            if end < len(s) and s[end].isalpha():
                return match.group(0)
            # Scan left for [[ and right for ]]
            left = s.rfind('[[', 0, start)
            right = s.find(']]', end)
            # If there is a [[ before and a ]] after, and no ]] between [[ and match, and no [[ between match and ]], it's inside a wiki-link
            if left != -1 and right != -1:
                # Ensure there is no ]] between [[ and match
                if s.find(']]', left, start) == -1 and s.find('[[', end, right) == -1:
                    return match.group(0)  # Already inside a link
            return f"[[{match.group(0)}]]"

        return pattern, repl_func

    # Normal replacement mode
    pattern = re.compile(escaped, flags)
    if replacement is None:
        # Should never happen if args are validated, but guard anyway.
        replacement = ""
    return pattern, replacement



def process_file(
    path: Path,
    pattern: re.Pattern,
    repl: Union[str, Callable[[re.Match], str]],
) -> Tuple[int, Optional[str]]:
    """
    Apply the regex pattern and replacement to the file's content.
    Returns (number of replacements, new content or None if unchanged).
    """
    text = load_text(path)
    if text is None:
        return 0, None
    # If repl is a function, use it; else, use as string
    if callable(repl):
        new_text, n = pattern.subn(repl, text)
    else:
        new_text, n = pattern.subn(repl, text)
    if n == 0:
        return 0, None
    return n, new_text



# ---------- Backlink Collection Utilities ----------

# Markers for auto-generated backlink blocks
COLL_BEGIN_TMPL = "<!-- BEGIN-AUTO-COLLECTION:{label} -->"
COLL_END = "<!-- END-AUTO-COLLECTION -->"


def best_relative_without_suffix(path: Path, roots: Sequence[Path]) -> str:
    """
    Return the shortest relative path (POSIX style, no file suffix) from any root.
    Used for pretty backlink display.
    """
    candidates: List[str] = []
    for r in roots:
        try:
            rel = path.relative_to(r)
            candidates.append(str(rel))
        except Exception:
            pass
    if not candidates:
        candidates.append(str(path))
    # Pick the shortest string representation
    chosen = min(candidates, key=len)
    # Drop suffix and normalize separators
    return str(Path(chosen).with_suffix("")).replace("\\", "/")



def gather_backlinks(
    label: str,
    candidate_files: Sequence[Path],
    exclude_path: Path,
) -> List[Path]:
    """
    Return files that contain a wiki-link to the label (case-insensitive).
    Used for backlink collection.
    """
    link_pattern = re.compile(r"\[\[\s*([^\]|#]+)", re.IGNORECASE)
    results: List[Path] = []
    for f in candidate_files:
        if f == exclude_path or f.suffix == ".bak":
            continue
        text = load_text(f)
        if text is None:
            continue
        # Find all wiki-links in the file
        found = False
        for m in link_pattern.finditer(text):
            link_target = m.group(1).strip()
            # Compare as whole word (case-insensitive)
            if link_target.lower() == label.lower():
                found = True
                break
        if found:
            results.append(f)
    # Sort by filename (case-insensitive), stable
    results.sort(key=lambda p: str(p).lower())
    return results


try:
    from Mycelium.scripts.Python.update_collection_block import update_collection_block  # type: ignore
except Exception:
    from .update_collection_block import update_collection_block  # type: ignore


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Recursively bulk find & replace text in files (safe for Obsidian vaults and repos)."
    )
    
    parser.add_argument(
        "--recreate-collectionfiles",
        action="store_true",
        help="Delete and recreate all files containing <#>Collectionfile (run independently).",
    )
    
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Root paths to scan. Defaults to current directory.",
    )
    parser.add_argument(
        "--find",
        help="Text to search for. Case-insensitive by default (use --case-sensitive to toggle).",
    )
    parser.add_argument(
        "--replace",
        help="Replacement text. Ignored if bracketing mode (-b) is enabled.",
    )
    parser.add_argument(
        "--ext",
        nargs="*",
        default=[],
        help="File extensions to include (e.g., --ext .md .txt). If omitted, all files are considered.",
    )
    parser.add_argument(
        "--include",
        nargs="*",
        default=[],
        help='Glob patterns to include (e.g., --include \"**/*.md\" \"**/*.txt\").',
    )
    parser.add_argument(
        "--exclude-dir",
        nargs="*",
        default=[],
        help="Directory names to exclude (in addition to defaults).",
    )
    parser.add_argument(
        "--no-default-excludes",
        action="store_true",
        help=f"Do not exclude default directories: {', '.join(sorted(DEFAULT_EXCLUDES))}.",
    )
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Make search case-sensitive (default is case-insensitive).",
    )
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Descend into symlinked directories.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files.",
    )
    parser.add_argument(
        "--backup",
        default=None,
        help="Backup suffix to use when writing changes (e.g., .bak). Backup created only if a file is modified.",
    )
    parser.add_argument(
        "-b",
        "--bracket",
        action="store_true",
        help="Bracketing mode: wrap matches with [[...]] if not already bracketed. Ignores --replace.",
    )
    # NEW: compact/color flags
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Short, color-coded output (does not change functionality).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors even if the terminal supports them.",
    )
    # NEW: collection files
    parser.add_argument(
        "--collectionfile",
        action="append",
        default=[],
        help=(
            "Path to a target note to maintain a backlinks list inside. "
            "Label inferred from file name (stem); e.g., Action.md collects files containing [[Action]]. "
            "Use multiple times for multiple targets."
        ),
    )

    # NEW: debug flag
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output.",
    )

    # Tagging and graph features
    parser.add_argument(
        "--add-tags",
        nargs="*",
        default=None,
        help="Tags to add to every processed file (space-separated, no leading #).",
    )
    parser.add_argument(
        "--remove-tags",
        nargs="*",
        default=None,
        help="Tags to remove from every processed file (no leading #).",
    )
    parser.add_argument(
        "--infer-tags",
        action="store_true",
        help="Infer and print candidate tags for each file (does not write unless used with --add-tags).",
    )
    parser.add_argument(
        "--export-graph",
        help="Path to write JSON graph of nodes/edges for candidate files.",
    )
    parser.add_argument(
        "--write-root-mushrooms",
        nargs="*",
        default=None,
        help="For each processed file, write a root_mushroomlist_settings block listing provided mushroom ids (as strings).",
    )

    # NEW: append string to end of files
    parser.add_argument(
        "--append",
        help="String to append to the end of each file (e.g., --append '[[Earthbending]]').",
    )

    args = parser.parse_args(argv)

    # Validation: allow either find/replace/bracket OR collection mode (or both),
    # but allow --recreate-collectionfiles to run standalone
    if not args.recreate_collectionfiles:
        if not args.collectionfile and not args.append:
            if not args.find:
                parser.error("--find is required unless --collectionfile or --append is used.")
            if not args.bracket and args.replace is None:
                parser.error("--replace is required unless bracketing mode (-b/--bracket) is used.")
        else:
            if args.find and (not args.bracket) and (args.replace is None):
                parser.error("--replace is required when using --find (unless -b/--bracket).")

    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    # Enable debug prints globally if --debug is set
    if getattr(args, 'debug', False):
        # Use the top-level sys module (imported at module scope).
        # _wfsm_debug is a dynamic attribute used for debugging; set it safely.
        try:
            sys._wfsm_debug = True  # type: ignore[attr-defined]
        except Exception:
            setattr(sys, '_wfsm_debug', True)

    def debug_print(msg):
        if getattr(args, 'debug', False):
            print(msg)

    debug_print("[debug] bulk_find_replace.py main() started")
    debug_print(f"[debug] Parsed args: {args}")

    # Decide on color usage
    color_enabled = sys.stdout.isatty() and (os.environ.get("NO_COLOR") is None) and (not args.no_color)
    debug_print(f"[debug] color_enabled: {color_enabled}")

    roots = [Path(p).resolve() for p in args.paths]
    debug_print(f"[debug] roots: {roots}")

    # Candidate files to scan
    files_iter = iter_files(
        roots=roots,
        include_globs=args.include,
        exclude_dirs=args.exclude_dir,
        use_default_excludes=not args.no_default_excludes,
        follow_symlinks=args.follow_symlinks,
    )

    candidate_files = [f for f in files_iter if should_process_file(f, args.ext)]

    if args.recreate_collectionfiles:
        debug_print("[debug] Entering recreate_collectionfiles block")
        recreate_collectionfiles(roots, candidate_files, args.dry_run, args.backup, color_enabled, args.compact)
        debug_print("[debug] Finished recreate_collectionfiles block")
        return 0
    total_changes = 0
    changed_files: List[Tuple[Path, int]] = []

    # ---------- Append String Pipeline ----------
    if args.append:
        appended = append_string_to_files(
            candidate_files,
            args.append,
            args.dry_run,
            args.backup,
            color_enabled,
            args.compact,
        )
        if args.compact:
            print(f"{colorize(color_enabled, 'Summary:', Colors.BOLD)} {colorize(color_enabled, 'APPEND', Colors.BLUE if args.dry_run else Colors.GREEN)} files={len(candidate_files)} appended={appended}")
        else:
            print(f"\n=== Summary (Append) ===")
            print(f"Files scanned: {len(candidate_files)}")
            print(f"Files appended: {appended}")
        # If only append was requested, skip the rest
        if not (args.find or args.collectionfile):
            return 0

    # ---------- Find/Replace pipeline ----------
    if args.find:
        pattern, repl = make_replacer(
            needle=args.find,
            replacement=args.replace,
            case_sensitive=args.case_sensitive,
            bracket_mode=args.bracket,
        )

        for f in candidate_files:
            n, new_text = process_file(f, pattern, repl)
            if n > 0 and new_text is not None:
                changed_files.append((f, n))
                total_changes += n
                if args.compact:
                    tag = "DRY" if args.dry_run else "WRITE"
                    tag_color = Colors.CYAN if args.dry_run else Colors.GREEN
                    print(
                        f"{colorize(color_enabled, '[' + tag + ']', tag_color)} "
                        f"{colorize(color_enabled, str(f), Colors.BOLD)} "
                        f"{colorize(color_enabled, '(' + str(n) + ')', Colors.GRAY)}"
                    )
                else:
                    if args.dry_run:
                        print(f"[dry-run] {f} -> {n} replacement(s)")
                    else:
                        print(f"[write] {f} -> {n} replacement(s)")
                if not args.dry_run:
                    write_text_with_backup(f, new_text, args.backup, color_enabled)

    # ---------- Tagging / Inference / Root-mushroom pipeline ----------
    tag_changes = 0
    infer_results = {}
    if args.infer_tags or args.add_tags or args.remove_tags or args.write_root_mushrooms or args.export_graph:
        # Build graph info once for inference/export
        graph = build_graph(roots, candidate_files)

    if args.infer_tags:
        for f in candidate_files:
            candidates = infer_tags_for_file(f, roots, candidate_files)
            infer_results[str(f)] = candidates
            print(f"Inferred for {f}: {candidates}")

    if args.add_tags:
        for f in candidate_files:
            changed = ensure_tags_on_file(f, args.add_tags, args.dry_run, args.backup, color_enabled)
            if changed:
                tag_changes += 1

    if args.remove_tags:
        for f in candidate_files:
            changed = remove_tags_from_file(f, args.remove_tags, args.dry_run, args.backup, color_enabled)
            if changed:
                tag_changes += 1

    if args.write_root_mushrooms:
        for f in candidate_files:
            changed = write_root_mushroom_list(Path(f), args.write_root_mushrooms, args.dry_run, args.backup, color_enabled)
            if changed:
                tag_changes += 1

    if args.export_graph:
        try:
            out = args.export_graph
            payload = graph
            # ensure parent exists
            outpath = Path(out)
            outpath.parent.mkdir(parents=True, exist_ok=True)
            if not args.dry_run:
                outpath.write_text(json.dumps(payload, indent=2), encoding='utf-8')
            print(f"Graph exported to {out} (nodes={len(payload.get('nodes',{}))}, edges={len(payload.get('edges',[]))})")
        except Exception as e:
            print(f"Failed to write graph: {e}", file=sys.stderr)

    # ---------- Collection pipeline ----------
    collections_updated = 0
    collections_items = 0
    backlink_graph = []  # For ASCII graph output
    if args.collectionfile:
        for t in args.collectionfile:
            target = Path(t).resolve()
            label = target.stem
            backlinks = gather_backlinks(label, candidate_files, exclude_path=target)
            changed, count = update_collection_block(
                target, roots, backlinks, label, args.dry_run, args.backup, color_enabled, args.compact
            )
            if changed:
                collections_updated += 1
            collections_items += count
            # Collect for ASCII graph
            backlink_graph.append((label, [best_relative_without_suffix(p, roots) for p in backlinks]))

            # --- Create All<CollectionName>.md with embedded links ---
            allfile = target.parent / f"All{label}.md"
            if backlinks:
                embed_lines = [f"![[{p.name}]]" for p in backlinks]
                embed_content = "\n\n\n---\n\n\n".join(embed_lines) + "\n\n\n---\n\n\n"
            else:
                embed_content = "<!-- No backlinks found -->\n"
            if not args.dry_run:
                write_text_with_backup(allfile, embed_content, args.backup, color_enabled)
            # --- Also create/update ExpandedCollections/Expanded{label}.md ---
            expanded_subfolder = target.parent / "ExpandedCollections"
            expanded_subfolder.mkdir(parents=True, exist_ok=True)
            expandedfile = expanded_subfolder / f"Expanded{label}.md"
            if backlinks:
                expanded_embed_lines = [f"![[{p.name}]]" for p in backlinks if p.suffix != ".bak"]
                expanded_content = "\n\n---\n---\n---\n\n".join(expanded_embed_lines) + "\n\n---\n---\n---\n\n"
            else:
                expanded_content = "<!-- No backlinks found -->\n"
            if not args.dry_run:
                write_text_with_backup(expandedfile, expanded_content, args.backup, color_enabled)

    # ---------- Summary ----------
    if args.compact:
        parts = [
            colorize(color_enabled, "Summary:", Colors.BOLD),
        ]
        if args.find:
            mode = "DRY" if args.dry_run else "APPLIED"
            parts.append(colorize(color_enabled, mode, Colors.BLUE if args.dry_run else Colors.GREEN))
            parts += [
                f"files={len(candidate_files)}",
                f"changed={len(changed_files)}",
                f"repl={total_changes}",
            ]
            if not args.dry_run and args.backup:
                parts.append(f"backup={args.backup}")
        if args.collectionfile:
            parts += [
                f"collections={collections_updated}/{len(args.collectionfile)}",
                f"items={collections_items}",
            ]
        print(" ".join(parts))
    else:
        if args.find:
            mode = "DRY-RUN (no writes)" if args.dry_run else "APPLIED (writes performed)"
            print("\n=== Summary (Find/Replace) ===")
            print(f"Mode: {mode}")
            print(f"Files scanned: {len(candidate_files)}")
            print(f"Files changed: {len(changed_files)}")
            print(f"Total replacements: {total_changes}")
            if not args.dry_run and args.backup:
                print(f"Backup suffix used: {args.backup}")
            if not changed_files:
                print("No changes made.")
            else:
                # Show a short top-10 preview of changed files
                print("\nChanged files (up to 10 shown):")
                for f, n in changed_files[:10]:
                    print(f"  {f} ({n})")
                if len(changed_files) > 10:
                    print(f"  ... and {len(changed_files) - 10} more")
        if args.collectionfile:
            print("\n=== Summary (Collections) ===")
            print(f"Targets updated: {collections_updated}/{len(args.collectionfile)}")
            print(f"Total backlinks enumerated: {collections_items}")
            if not args.find:
                # If only collections were requested, still show scanned file count
                print(f"Files scanned: {len(candidate_files)}")


    # ---------- ASCII Graph Output for Collections ----------
    if args.collectionfile and backlink_graph:
        from collections import defaultdict
        print("\n=== Backlink Graph (ASCII) ===")
        cwd = os.path.relpath(os.getcwd(), str(roots[0]) if roots else os.getcwd())
        for label, links in backlink_graph:
            # Build tree for this label
            tree = defaultdict(dict)
            for link in links:
                rel = os.path.relpath(str(link), str(roots[0]) if roots else os.getcwd())
                parts = rel.split(os.sep)
                d = tree
                for part in parts:
                    if part not in d:
                        d[part] = {}
                    d = d[part]
            # Only bracket files ([[...]] ) for files that are inside the specified root folder.
            root_base = Path(roots[0]).resolve() if roots else None

            def print_tree(d, prefix="", path_parts: Optional[List[str]] = None):
                if path_parts is None:
                    path_parts = []
                items = list(d.items())
                for idx, (name, subtree) in enumerate(items):
                    connector = "└── " if idx == len(items)-1 else "├── "
                    if subtree:
                        print(f"{prefix}{connector}{name}")
                        extension = "    "  # Always use spaces, no vertical lines
                        print_tree(subtree, prefix + extension, path_parts + [name])
                    else:
                        try:
                            rel_path = os.path.join(*([p for p in path_parts] + [name]))
                        except Exception:
                            rel_path = name
                        bracket = True
                        if root_base is None:
                            bracket = False
                        else:
                            try:
                                full_path = (root_base / rel_path).resolve()
                                bracket = os.path.commonpath([str(full_path), str(root_base)]) == str(root_base)
                            except Exception:
                                bracket = False
                        if bracket:
                            print(f"{prefix}{connector}[[{name}]]")
                        else:
                            print(f"{prefix}{connector}{name}")

            print_tree(tree, prefix="  ")
        print()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
