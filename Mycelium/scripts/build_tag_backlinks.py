#!/usr/bin/env python3
"""
Build per-tag backlink summary files for a workspace.

Scans all .md files under `root` (default: current directory), extracts hashtag-style
tags (e.g. #Variable, #primary_variable) and writes a folder for each tag under
`outdir` (default: Tag_Summaries) containing a single `<Tag>.md` file listing
backlinks (relative paths) to all files that mention that tag.

Usage:
    python3 Mycelium/build_tag_backlinks.py --root /path/to/repo --outdir MyTagSummaries --apply

The script respects excludes returned by `Mycelium.config_common.get_graph_excludes(root)` if that module exists.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, List, Tuple

TAG_RE = re.compile(r"#([A-Za-z0-9_\-]+)")


def load_excludes(root: Path) -> List[str]:
    """Try to use Mycelium.config_common.get_graph_excludes(root) if available,
    otherwise return a sensible default that excludes the tool's own folder.
    """
    try:
        from Mycelium import config_common

        vals = config_common.get_graph_excludes(root)
        return vals or []
    except Exception:
        # default safe excludes
        return [".git/", "Mycelium/"]


def find_markdown_files(root: Path, excludes: List[str]) -> List[Path]:
    md_files: List[Path] = []
    for p in root.rglob("*.md"):
        # skip files under excluded path fragments
        rel = p.relative_to(root)
        parts = str(rel).split("/")
        if any(excl.rstrip("/") in parts for excl in excludes):
            continue
        md_files.append(p)
    return md_files


def extract_tags_from_text(text: str) -> List[str]:
    return [m.group(1) for m in TAG_RE.finditer(text)]


def first_heading(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("# ")
    return ""


def build_tag_index(root: Path) -> Dict[str, List[Tuple[Path, str]]]:
    excludes = load_excludes(root)
    md_files = find_markdown_files(root, excludes)
    tags: Dict[str, List[Tuple[Path, str]]] = {}
    for p in md_files:
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        found = extract_tags_from_text(text)
        if not found:
            continue
        heading = first_heading(text)
        rel = p.relative_to(root)
        for t in set(found):
            tags.setdefault(t, []).append((rel, heading))
    return tags


def write_tag_summaries(root: Path, outdir: Path, tags: Dict[str, List[Tuple[Path, str]]], apply: bool) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    all_index_lines: List[str] = ["# Tag Backlink Index", ""]
    for tag, entries in sorted(tags.items(), key=lambda kv: kv[0].lower()):
        safe_tag = tag.replace("/", "_")
        tag_dir = outdir / safe_tag
        tag_dir.mkdir(parents=True, exist_ok=True)
        filename = tag_dir / f"{safe_tag}.md"
        lines: List[str] = [f"# {tag}", "", f"Backlinks to files mentioning #{tag}", ""]
        for rel, heading in sorted(entries, key=lambda e: str(e[0])):
            display = str(rel)
            if heading:
                lines.append(f"- [{display}]({display}) \u2014 {heading}")
            else:
                lines.append(f"- [{display}]({display})")

        lines.append("")
        if apply:
            content = "\n".join(lines)
            filename.write_text(content, encoding="utf-8")
            print(f"[wrote] {filename}")
            print("[preview]", content[:200] if content else "(empty)")
        else:
            print(f"[would write] {filename} ({len(entries)} backlinks)")
            print("[preview]", ("\n".join(lines))[:200])

        all_index_lines.append(f"- [{tag}]({safe_tag}/{safe_tag}.md) ({len(entries)})")

    # write master index
    all_index = outdir / "ALL FILES.md"
    all_index_lines.append("")
    if apply:
        content = "\n".join(all_index_lines)
        all_index.write_text(content, encoding="utf-8")
        print(f"[wrote] {all_index}")
        print("[preview]", content[:200])
    else:
        print(f"[would write] {all_index} ({len(tags)} tags)")
        print("[preview]", ("\n".join(all_index_lines))[:200])


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build per-tag backlink summary files")
    ap.add_argument("--root", default=".", help="workspace root to scan")
    ap.add_argument("--outdir", default="Tag_Summaries", help="output directory for tag folders (relative to root)")
    ap.add_argument("--apply", action="store_true", help="actually write files (dry-run by default)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    outdir = root.joinpath(args.outdir)
    tags = build_tag_index(root)
    write_tag_summaries(root, outdir, tags, apply=args.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
