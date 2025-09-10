#!/usr/bin/env python3
"""create_wiki_todos.py

Scan a workspace for Obsidian-style wiki links [[Page]] and create missing
target .md files with a small template.

Behavior / heuristics:
- Finds links of the form [[target]] or [[target|alias]] or [[target#heading]]
- Skips links that look like URLs (contains '://') or point to non-md assets
- If the link contains a slash (e.g. Folder/Page) it is treated as a path from
  the workspace root. If it contains no slash, the new file is created next to
  the source file that referenced it.

Usage:
  python create_wiki_todos.py [--root PATH] [--dry-run] [--yes]

Defaults to running in the current working directory and will create files
unless --dry-run is provided.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import List, Set, Tuple

WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
SKIP_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf', '.mp3', '.mp4'}


def find_markdown_files(root: Path) -> List[Path]:
    md_files = []
    for p in root.rglob('*.md'):
        md_files.append(p)
    return md_files


def extract_targets(text: str) -> List[str]:
    """Return plausible link targets found in text.

    Skip matches that contain newlines, control chars, very long content or
    look like markdown blocks (which often indicate a broken match).
    """
    results: List[str] = []
    for m in WIKI_LINK_RE.finditer(text):
        raw = m.group(1)
        # skip multiline or control chars
        if any(c in raw for c in ('\n', '\r', '\t')):
            continue
        raw = raw.strip()
        # skip absurdly long matches
        if len(raw) > 200:
            continue
        # skip obvious markdown fragments that matched accidentally
        if '---' in raw or '***' in raw or raw.startswith('- ') or raw.startswith('* '):
            continue
        if not raw:
            continue
        results.append(raw)
    return results


def normalize_target(raw: str) -> str:
    """From the inner link text, strip alias/anchor and return target path-like string.

    Also sanitize common problematic characters.
    """
    # remove alias after |
    if '|' in raw:
        raw = raw.split('|', 1)[0]
    # remove anchor after #
    if '#' in raw:
        raw = raw.split('#', 1)[0]
    raw = raw.strip()

    # sanitize: remove leftover brackets or control chars
    raw = raw.strip('[]\n\r\t')
    # collapse repeated dots
    raw = re.sub(r'\.{2,}', '.', raw)
    # remove trailing/leading punctuation that would make bad filenames
    raw = re.sub(r'^[\s\-\_\[\]:]+|[\s\-\_\[\]:]+$', '', raw)
    # remove characters illegal on macOS paths like ':' (keep unicode letters)
    raw = raw.replace(':', ' -')
    # final safe fallback
    return raw.strip()


def is_external(raw: str) -> bool:
    return '://' in raw


def has_skip_ext(raw: str) -> bool:
    lower = raw.lower()
    for ext in SKIP_EXTS:
        if lower.endswith(ext):
            return True
    return False


def is_valid_filename_component(s: str) -> bool:
    # very small heuristic: avoid names that still contain brackets or start with '[' or are just punctuation
    if not s:
        return False
    if s.startswith('[') or s.endswith(']'):
        return False
    # avoid single-character weird names or names that are just punctuation
    if all(ch in '._-' for ch in s):
        return False
    if len(s) > 240:
        return False
    return True


def resolve_target_path(raw: str, src_file: Path, root: Path) -> Path:
    """Resolve where to create the file on disk.

    Rules:
    - If raw contains a slash, treat it as a path relative to root.
    - Otherwise, treat it as the same-folder filename next to src_file.
    - If no extension provided, append .md
    """
    raw = raw.strip()
    if not raw:
        raise ValueError('empty target')

    # If the raw already ends with .md, keep it. Otherwise append .md
    target_rel = raw if raw.lower().endswith('.md') else f"{raw}.md"

    # If there's a slash, treat as root-relative path (Obsidian style)
    if '/' in raw:
        return (root / target_rel).resolve()

    # else create next to source file
    return (src_file.parent / target_rel).resolve()


def create_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    title = path.stem.replace('_', ' ')
    content = f"# {title}\n\nTODO: Create content for {path.name}\n\n*(Automatically created by create_wiki_todos.py)*\n"
    path.write_text(content, encoding='utf-8')


def map_target_to_outdir(target_path: Path, raw: str, src_file: Path, root: Path, out_dir: Path, basename_counts: dict) -> Path:
    """Map every target to a single file under out_dir using only the basename.

    If multiple targets share the same basename, append a numeric suffix to
    avoid collisions: "Name.md", "Name (1).md", "Name (2).md".
    """
    filename = target_path.name
    # normalize filename whitespace
    filename = filename.strip()
    if not filename:
        raise ValueError('empty filename')

    count = basename_counts.get(filename, 0)
    if count == 0:
        mapped = out_dir / filename
    else:
        stem = Path(filename).stem
        suffix = Path(filename).suffix or '.md'
        mapped = out_dir / f"{stem} ({count}){suffix}"

    basename_counts[filename] = count + 1
    return mapped.resolve()


def scan_and_create(root: Path, dry_run: bool = False, max_create: int | None = None, out_dir: Path | None = None) -> Tuple[Set[Path], Set[Path]]:
    md_files = find_markdown_files(root)
    to_create: Set[Path] = set()
    seen: Set[Path] = set()

    basename_counts: dict = {}
    for md in md_files:
        try:
            text = md.read_text(encoding='utf-8')
        except Exception:
            # skip files we can't read
            continue

        for raw in extract_targets(text):
            nr = normalize_target(raw)
            if not nr:
                continue
            if is_external(nr):
                continue
            if has_skip_ext(nr):
                continue

            # validate filename component(s)
            comps = [c for c in nr.split('/') if c]
            if not comps:
                continue
            if not all(is_valid_filename_component(c) for c in comps):
                continue

            try:
                target_path = resolve_target_path(nr, md, root)
            except ValueError:
                continue

            # keep track of the original intended path
            seen.add(target_path)

            # If a file with that path exists in the repo, skip autogeneration
            if target_path in seen:
                continue    

            # If the original file already exists in the repo, skip autogeneration
            try:
                orig_exists = target_path.exists()
            except OSError:
                orig_exists = False

            if orig_exists:
                continue

            # map to out_dir (one file per unique basename)
            if out_dir is None:
                out_dir = root / 'autogenerated_wiki'
            try:
                mapped = map_target_to_outdir(target_path, nr, md, root, out_dir, basename_counts)
            except ValueError:
                continue
            to_create.add(mapped)

    created: Set[Path] = set()
    if dry_run or not to_create:
        return to_create, created

    # ensure out_dir exists when actually creating
    if out_dir is None:
        out_dir = root / 'autogenerated_wiki'
    out_dir.mkdir(parents=True, exist_ok=True)

    # enforce max_create if provided
    to_act = sorted(to_create)
    if max_create is not None:
        to_act = to_act[:max_create]

    for p in to_act:
        try:
            create_file(p)
            created.add(p)
        except OSError:
            # skip files we can't write
            continue

    return to_create, created


def main():
    ap = argparse.ArgumentParser(description='Create missing wiki-linked .md files')
    ap.add_argument('--root', '-r', default='.', help='workspace root to scan (default .)')
    ap.add_argument('--dry-run', '-n', action='store_true', help="show what would be created")
    ap.add_argument('--yes', '-y', action='store_true', help='actually create missing files')
    ap.add_argument('--max', '-m', type=int, default=None, help='maximum files to create in one run')
    ap.add_argument('--out-dir', default='autogenerated_wiki', help='where to place autogenerated files (relative to root)')

    args = ap.parse_args()
    root = Path(args.root).resolve()
    if not root.exists():
        print(f'Root {root} does not exist')
        raise SystemExit(2)

    should_dry = args.dry_run or not args.yes

    out_dir = (root / args.out_dir).resolve()
    to_create, created = scan_and_create(root, dry_run=should_dry, max_create=args.max, out_dir=out_dir)

    if should_dry:
        if to_create:
            print(f'Would create {len(to_create)} files under {out_dir.relative_to(root)}:')
            for p in sorted(to_create):
                try:
                    print(f'  {p.relative_to(root)}')
                except Exception:
                    print(f'  {p}')
        else:
            print('No missing wiki targets found.')
        return

    if created:
        print(f'Created {len(created)} files:')
        for p in sorted(created):
            print(f'  {p.relative_to(root)}')
    else:
        print('No files were created.')


if __name__ == '__main__':
    main()
