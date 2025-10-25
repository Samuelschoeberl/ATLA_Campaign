#!/usr/bin/env python3
"""Standalone infer_file_tags.py

This is a small, self-contained CLI that infers candidate tags for markdown
files based on (in order):
  1) folder names above the file
  2) wikilinks inside the file ([[Page Name]])
  3) filename tokens (split on spaces/underscore/hyphen)

The heuristics are intentionally simple and mirror the logic used by the
original `infer_tags_for_file` in `Wiki_File_System_Manager.py`, but this
script avoids importing the larger module so it can be run standalone.

Usage:
  python3 infer_file_tags.py <file-or-dir> [--max-tags N] [--roots ROOT ...]

By default the script prints candidate tags for each file (dry-run).</n+"""
from pathlib import Path
import argparse
import re
from typing import List


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except Exception:
        try:
            return path.read_text(encoding='latin-1')
        except Exception:
            return ''


def infer_tags_for_file(path: Path, roots: List[Path], max_tags: int = 5) -> List[str]:
    text = load_text(path) or ""
    tags = []
    # 1) folder names
    try:
        parent = path.parent
        # collect folder names up to filesystem root
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
    # Normalize and limit
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


def find_candidate_files(root: Path):
    return sorted([p for p in root.rglob('*.md') if p.is_file()])


def main():
    p = argparse.ArgumentParser(description='Infer candidate tags for files using folder names, wikilinks and filename tokens.')
    p.add_argument('paths', nargs='+', help='File(s) or directory(ies) to analyze')
    p.add_argument('--max-tags', type=int, default=5, help='Maximum number of candidate tags to return')
    p.add_argument('--root', action='append', help='Root folder(s) used for inference (defaults to the Mycelium folder)')
    args = p.parse_args()

    THIS_FILE = Path(__file__).resolve()
    DEFAULT_ROOT = THIS_FILE.parents[2]
    roots = [Path(r).resolve() for r in (args.root or [str(DEFAULT_ROOT)])]

    candidate_files = []
    for r in roots:
        candidate_files.extend(find_candidate_files(r))
    candidate_files = sorted(set(candidate_files))

    for pth in args.paths:
        target = Path(pth).resolve()
        targets = []
        if target.is_dir():
            targets = [f for f in target.rglob('*.md') if f.is_file()]
        elif target.is_file():
            targets = [target]
        else:
            print(f"Skipping unknown path: {target}")
            continue

        for t in targets:
            try:
                candidates = infer_tags_for_file(t, roots, max_tags=args.max_tags)
            except Exception as e:
                print(f"Error inferring tags for {t}: {e}")
                continue
            display = ', '.join(candidates) if candidates else '(none)'
            print(f"{t.relative_to(DEFAULT_ROOT)} -> {display}")


if __name__ == '__main__':
    main()
