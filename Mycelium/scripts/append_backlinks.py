#!/usr/bin/env python3
"""Compute backlinks from wikilinks and append a '## Backlinks' section to each .md file.

Usage:
  python3 Mycelium/append_backlinks.py --root /path/to/repo [--apply] [--header "## Backlinks"]

Behavior:
 - Scans markdown files under the root (excluding configured excludes if Mycelium.config_common.get_graph_excludes is present).
 - Parses [[wikilink]] tokens and attempts to resolve them to repo .md files via filename/stem or relative paths.
 - For each target file found, replaces any existing header matching the provided header and writes an updated file containing a bullet list of backlinks as Obsidian-style [[path/to/file]] links.
 - Dry-run by default; use --apply to write changes.
"""
from __future__ import annotations

import argparse
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple


LINK_RE = re.compile(r"\[\[([^\]\|\n]+)(?:\|[^\]\n]+)?\]\]")


def get_excludes(root: Path) -> List[str]:
    try:
        from Mycelium import config_common

        return list(config_common.get_graph_excludes(root))
    except Exception:
        return ['backups/', 'Mycelium/']


def find_md_files(root: Path, excludes: List[str]) -> List[Path]:
    files = []
    for p in root.rglob('*.md'):
        rel = p.relative_to(root).as_posix()
        if any(rel.startswith(x.rstrip('/')) for x in excludes):
            continue
        files.append(p)
    return sorted(files)


def parse_links(text: str) -> List[str]:
    return [m.group(1).strip() for m in LINK_RE.finditer(text)]


def resolve_link(link: str, md_files: List[Path], root: Path) -> List[Path]:
    """Try to resolve a link token to one or more markdown files in the repo.
    Heuristics:
      - If link contains a slash, treat as relative path (try with and without .md)
      - Else match by filename stem or name
    """
    candidates: List[Path] = []
    # sanitize link
    link = link.splitlines()[0].strip()
    if not link:
        return []
    if '/' in link:
        p = root.joinpath(link)
        try:
            if p.exists() and p.suffix == '.md':
                candidates.append(p)
        except OSError:
            pass
        pmd = root.joinpath(link + '.md')
        try:
            if pmd.exists():
                candidates.append(pmd)
        except OSError:
            pass

    # match by stem or full name
    for f in md_files:
        if f.stem == link or f.name == link or f.name == f"{link}.md":
            candidates.append(f)

    # dedupe while preserving order
    seen = set()
    out = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def remove_existing_backlinks_section(text: str, header: str) -> str:
    # header e.g. '## Backlinks' -> remove header and following content until next header of same or higher level
    lines = text.splitlines()
    out = []
    i = 0
    n = len(lines)
    header_str = header.strip()
    while i < n:
        if lines[i].strip().startswith(header_str):
            # skip this header line
            i += 1
            # skip until next top-level heading (starts with '#')
            while i < n and not lines[i].lstrip().startswith('#'):
                i += 1
            # continue outer loop without adding skipped content
            continue
        out.append(lines[i])
        i += 1
    return '\n'.join(out).rstrip() + '\n'


def make_obsidian_link(p: Path, root: Path) -> str:
    # Obsidian link: path relative to root without suffix
    try:
        rel = p.relative_to(root)
    except Exception:
        rel = p
    # remove .md suffix
    rel_no_suffix = Path(str(rel)).with_suffix('')
    return f"[[{rel_no_suffix.as_posix()}]]"


def main() -> int:
    ap = argparse.ArgumentParser(description='Append backlinks to .md files')
    ap.add_argument('--root', default=None, help='Repository root (if omitted, will try Mycelium config)')
    ap.add_argument('--apply', action='store_true', help='Write changes (default: dry-run)')
    ap.add_argument('--header', default='## Backlinks', help='Header to insert/replace')
    ap.add_argument('--min-links', type=int, default=1, help='Only write section if at least this many backlinks')
    args = ap.parse_args()
    # prefer explicit CLI root; otherwise try to read from config markdown
    if args.root:
        root = Path(args.root)
    else:
        try:
            from Mycelium.helpers.path_vars import find_path_var
            guessed = find_path_var(Path('.'))
        except Exception:
            guessed = None
        root = Path(guessed) if guessed else Path('.')
    excludes = get_excludes(root)
    md_files = find_md_files(root, excludes)
    print(f"Scanning {len(md_files)} markdown files (excludes={excludes})...")

    # map target -> set of sources (incoming) and source -> set of targets (outgoing)
    backlinks: Dict[Path, Set[Path]] = {p: set() for p in md_files}
    out_links: Dict[Path, Set[Path]] = {p: set() for p in md_files}

    for src in md_files:
        try:
            txt = src.read_text(encoding='utf8', errors='ignore')
        except Exception:
            continue
        links = parse_links(txt)
        resolved_targets: Set[Path] = set()
        for link in links:
            targets = resolve_link(link, md_files, root)
            for t in targets:
                backlinks.setdefault(t, set()).add(src)
                resolved_targets.add(t)
        out_links[src] = resolved_targets

    # load pagerank scores if available
    pagerank_scores: Dict[str, float] = {}
    pr_path = Path('Mycelium/pagerank.json')
    if pr_path.exists():
        try:
            pr = json.loads(pr_path.read_text(encoding='utf8'))
            # ensure float values
            pagerank_scores = {k: float(v) for k, v in pr.items()}
        except Exception:
            pagerank_scores = {}

    to_update: List[Tuple[Path, str]] = []
    for target, sources in backlinks.items():
        if not sources or len(sources) < args.min_links:
            continue
        # load target text
        try:
            ttxt = target.read_text(encoding='utf8', errors='ignore')
        except Exception:
            continue
        base = remove_existing_backlinks_section(ttxt, args.header)
        links_lines = [f"- {make_obsidian_link(s, root)}" for s in sorted(sources)]
        # Build metadata: incoming/outgoing lists and pagerank
        incoming_section = '\n'.join(links_lines)
        outgoing_lines = [f"- {make_obsidian_link(s, root)}" for s in sorted(out_links.get(target, []))]
        pagerank_key = None
        try:
            pagerank_key = str(target.relative_to(Path(args.root) if hasattr(args, 'root') else root).as_posix())
        except Exception:
            try:
                pagerank_key = str(target.relative_to(root).as_posix())
            except Exception:
                pagerank_key = target.as_posix()

        pr_score = pagerank_scores.get(pagerank_key, None)

        # build the combined section: Backlinks header + incoming list, then metadata
        section_lines = [f"\n{args.header}\n"]
        section_lines.append('')
        section_lines.extend(links_lines)
        section_lines.append('')
        # metadata block: tags line
        section_lines.append('#variable #links')
        section_lines.append('')
        section_lines.append('### Incoming links')
        if incoming_section:
            section_lines.append('')
            section_lines.extend(links_lines)
        else:
            section_lines.append('\n- (none)')
        section_lines.append('')
        section_lines.append('### Outgoing links')
        if outgoing_lines:
            section_lines.append('')
            section_lines.extend(outgoing_lines)
        else:
            section_lines.append('\n- (none)')
        section_lines.append('')
        section_lines.append('### PageRank')
        if pr_score is not None:
            section_lines.append('')
            section_lines.append(f'- {pr_score:.8f}')
        else:
            section_lines.append('\n- N/A')

        section = '\n'.join(section_lines) + '\n'
        new_text = base + section
        if new_text != ttxt:
            to_update.append((target, new_text))

    print(f"Found {len(to_update)} files that would be updated (dry-run={not args.apply})")
    for p, new in to_update[:50]:
        print(f" - {p} -> backlinks: {new.count('\n' + args.header + '\n')} sections")
        # print small preview
        preview = '\n'.join(new.splitlines()[-10:])
        print('---preview---')
        print(preview[:400])
        print('---')

    if not args.apply:
        print('\nRun with --apply to write these changes.')
        return 0

    # apply writes
    for p, new in to_update:
        p.write_text(new, encoding='utf8')
        print(f"[wrote] {p}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
