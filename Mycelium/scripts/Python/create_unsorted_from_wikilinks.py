#!/usr/bin/env python3
"""Create markdown files in Mycelium/unsorted for every wikilink found.

Usage:
    python3 scripts/create_unsorted_from_wikilinks.py <folder> [--dest DEST] [--dry-run] [--force] [--backup] [--tag-from-source]

Behavior / contract:
- Scans all .md files under the given folder (recursively) for [[Link]] tokens.
- For each unique link text found, creates a file named <link>.md under the destination
  directory (default: Mycelium/unsorted). Slashes in link names are replaced with '_'.
- Does not overwrite existing files unless --force is provided. Use --dry-run to preview.

Examples:
  python3 scripts/create_unsorted_from_wikilinks.py "Player Root/PCs" --dry-run
  python3 scripts/create_unsorted_from_wikilinks.py . --dest Mycelium/unsorted --force
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys
import hashlib
import os

ROOT = Path('.').resolve()
DEFAULT_DEST = ROOT / 'Mycelium' / 'unsorted'

WIKILINK_RE = re.compile(r"\[\[\s*([^\]|]+?)(?:\|[^\]]*)?\s*\]\]")


def safe_filename_from_link(name: str) -> str:
    # preserve readable text but avoid directory separators
    s = name.strip()
    s = s.replace('/', '_')
    s = s.replace('\\', '_')
    # collapse whitespace
    s = '_'.join(s.split())
    if not s:
        s = 'untitled'
    return f"{s}.md"


def read_repo_root_name() -> str | None:
    """Read config/varaibles/Root.md first line as repository root name (if present)."""
    cfg = ROOT / 'config' / 'varaibles' / 'Root.md'
    try:
        txt = cfg.read_text(encoding='utf-8')
    except Exception:
        return None
    for ln in txt.splitlines():
        line = ln.strip()
        if line and not line.startswith('#'):
            return line
    return None


def unique_filename_across_repo(candidate: str, content: str) -> str:
    """Return a filename guaranteed unique across repo. If collisions exist with different content, append short hash."""
    # if candidate exists anywhere and content differs, add hash
    paths = list(ROOT.rglob(candidate))
    if not paths:
        return candidate
    # compute content hash
    h = hashlib.sha1(content.encode('utf-8')).hexdigest()[:8]
    for p in paths:
        try:
            existing = p.read_text(encoding='utf-8')
        except Exception:
            continue
        if existing == content:
            # identical content; reuse the candidate name
            return candidate
    # collision with different content -> append hash
    stem = Path(candidate).stem
    suffix = Path(candidate).suffix
    return f"{stem}_{h}{suffix}"


def collect_wikilinks(folder: Path) -> dict[str, set[Path]]:
    """Return mapping of link text -> set of source file Paths where it was found."""
    out: dict[str, set[Path]] = {}
    for p in folder.rglob('*.md'):
        try:
            txt = p.read_text(encoding='utf-8')
        except Exception:
            continue
        for m in WIKILINK_RE.findall(txt):
            name = m.split('#', 1)[0].strip()  # drop anchor part if any
            if not name:
                continue
            out.setdefault(name, set()).add(p)
    return out


def create_files_for_links(links: dict[str, set[Path]], dest: Path, dry_run: bool = False, force: bool = False, tag: str | None = None, ensure_unique: bool = True, tag_from_source: bool = False) -> tuple[list[Path], int]:
    """Create files for links. Returns (created_paths_list, skipped_count).

    links: mapping of link text -> set of source files where the link was found.
    If tag_from_source is True, one `#<foldername>` tag is added per unique parent folder of source files.
    """
    dest.mkdir(parents=True, exist_ok=True)
    created_paths: list[Path] = []
    skipped = 0
    for name in sorted(links.keys()):
        sources = links.get(name, set())
        fname = safe_filename_from_link(name)
        fpath = dest / fname
        if fpath.exists() and not force:
            skipped += 1
            print(f"skip (exists): {fpath}")
            continue
        content_lines = []
        # optional top tag line from constant tag
        if tag:
            content_lines.append(tag)
        # optional tags derived from source folder names
        if tag_from_source and sources:
            # compute unique parent folder names (immediate parent directory of source file)
            parent_names = sorted({s.parent.name for s in sources if s.parent.name})
            for pn in parent_names:
                content_lines.append(f"#{pn}")
        # top wikilink for easier linking
        content_lines.append(f"[[{name}]]")
        content = "\n\n".join(content_lines) + "\n"
        # ensure filename uniqueness across repo if requested
        if ensure_unique:
            fname = unique_filename_across_repo(fname, content)
            fpath = dest / fname
        if dry_run:
            print(f"[dry-run] would create: {fpath}")
        else:
            fpath.write_text(content, encoding='utf-8')
            print(f"created: {fpath}")
        created_paths.append(fpath)
    return created_paths, skipped


def main(argv=None):
    ap = argparse.ArgumentParser(description='Create files in Mycelium/unsorted from wikilinks')
    ap.add_argument('folder', help='Folder to scan for .md files (recursive)')
    ap.add_argument('--dest', default=str(DEFAULT_DEST), help='Destination directory (default: Mycelium/unsorted)')
    ap.add_argument('--dry-run', action='store_true', help='Show what would be created')
    ap.add_argument('--force', action='store_true', help='Overwrite existing files')
    ap.add_argument('--tag', default='#unsorted', help='Optional tag line to add at file top (default: #unsorted)')
    ap.add_argument('--tag-from-source', action='store_true', help='Add a tag of the form #<foldername> derived from each source file parent folder where the link was found')
    ap.add_argument('--assign-tags', help='Comma-separated tags to add to each created file (e.g. "Anju,Ash")')
    ap.add_argument('--sort', action='store_true', help='After creating files, move each file into first Mycelium folder matching one of its tags')
    ap.add_argument('--graph-root', default=str(ROOT / 'Mycelium'), help='Root path to traverse when sorting (default: Mycelium)')
    ap.add_argument('--canonical', action='store_true', help='When sorting into mushroom folders, create a canonical copy in repo root and symlink into folders instead of moving')
    ap.add_argument('--mushroom', help='Optional mushroom folder name to create a duplicate structure in (use with --canonical)')
    ap.add_argument('--backup', action='store_true', help='Write created files under backups/ (keeps created files in backups/<dest>)')
    args = ap.parse_args(argv)

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        print(f"Folder not found: {folder}")
        return 2

    links = collect_wikilinks(folder)
    if not links:
        print('No wikilinks found.')
        return 0

    dest = Path(args.dest)
    # If requested, place the created files under the repository backups/ tree
    if args.backup:
        backup_root = ROOT / 'backups'
        try:
            rel = dest.relative_to(ROOT)
        except Exception:
            rel = Path(dest)
        dest = backup_root / rel
        print(f"Using backups destination: {dest}")
    # read repository root canonical name (informational)
    repo_root_name = read_repo_root_name()
    if repo_root_name:
        print(f"Repository root name from config: {repo_root_name}")

    created_paths, skipped = create_files_for_links(links, dest, dry_run=args.dry_run, force=args.force, tag=args.tag, ensure_unique=True, tag_from_source=args.tag_from_source)

    # If assign-tags provided, append those tag lines to the created files (if not dry-run)
    if args.assign_tags and not args.dry_run:
        assign = [t.strip() for t in args.assign_tags.split(',') if t.strip()]
        for p in created_paths:
            try:
                txt = p.read_text(encoding='utf-8')
            except Exception:
                continue
            lines = txt.splitlines()
            # insert all assign-tags as separate lines at top before wikilink
            new_top = '\n'.join(assign) + '\n' + '\n'.join(lines)
            p.write_text(new_top, encoding='utf-8')
            print(f"tagged: {p} -> {assign}")

    # Sorting: move created files into first matching folder under graph-root that matches any tag
    moved = 0
    if args.sort and not args.dry_run:
        graph_root = Path(args.graph_root)
        if not graph_root.exists() or not graph_root.is_dir():
            print(f"graph-root not found: {graph_root}; skipping sort")
        else:
            # prepare a map of directory names to first matching dir path (preserve discovery order)
            dir_map: dict[str, Path] = {}
            for d in graph_root.rglob('*'):
                if d.is_dir():
                    name = d.name
                    key = name.lower()
                    if key not in dir_map:
                        dir_map[key] = d

            for p in created_paths:
                try:
                    txt = p.read_text(encoding='utf-8')
                except Exception:
                    continue
                # collect tags from file: lines starting with '#'
                file_tags = [ln.lstrip('#').strip() for ln in txt.splitlines() if ln.strip().startswith('#')]
                # include assign-tags as well
                if args.assign_tags:
                    file_tags = list(dict.fromkeys([*file_tags, *[t.strip() for t in args.assign_tags.split(',') if t.strip()]]))
                dest_dir: Path | None = None
                for t in file_tags:
                    key = t.lower()
                    if key in dir_map:
                        dest_dir = dir_map[key]
                        break
                if dest_dir:
                    # when canonical requested, create a symlink inside dest_dir pointing to canonical file
                    if args.canonical:
                        # canonical file is p (already created in dest), create link in dest_dir
                        canon = p
                        link_target = dest_dir / p.name
                        # ensure unique link name
                        i = 1
                        while link_target.exists():
                            link_target = dest_dir / f"{p.stem}_{i}{p.suffix}"
                            i += 1
                        os.symlink(os.path.relpath(canon, start=dest_dir), link_target)
                        moved += 1
                        print(f"symlinked: {link_target} -> {canon}")
                    else:
                        # move file into folder (ensure unique filename)
                        target = dest_dir / p.name
                        i = 1
                        while target.exists():
                            target = dest_dir / f"{p.stem}_{i}{p.suffix}"
                            i += 1
                        p.rename(target)
                        moved += 1
                        print(f"moved: {p} -> {target}")

    print(f"Done. created={len(created_paths)} skipped={skipped} moved={moved}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
