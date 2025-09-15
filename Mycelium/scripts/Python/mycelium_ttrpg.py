#!/usr/bin/env python3
"""
mycelium_ttrpg.py

Create per-PC folders and a DMs folder by copying markdown files relevant
to each PC (files tagged with #<PCname> or tagged #PC) and copy every
markdown into the DMs folder. Then call the project's Wikigraphs.py to
generate sunburst and treemap HTML files into the repository `graphs/`
folder.

Assumptions (reasonable defaults):
- Tags are simple single-token hashtags like `#Anju` or `#PC` (no spaces).
- PC folders will be created under `Players Part/PCs/<Name>`.
- DMs folder will be created as `DMs Part/`.
- Files are copied preserving their relative path under each target
  character root.

Usage:
  python3 mycelium_ttrpg.py
  python3 mycelium_ttrpg.py --roots . --run-graphs

This script prints every file it creates (copied target paths).
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set


DEFAULT_EXCLUDES = {'.git', 'node_modules', '.obsidian', '__pycache__', 'venv', '.venv'}
MD_EXTS = {'.md', '.markdown', '.txt'}


def find_md_files(root: Path, excludes: Set[str] = DEFAULT_EXCLUDES) -> List[Path]:
    out: List[Path] = []
    from scripts.fsutil import iter_md_files
    for p in iter_md_files(root):
        parts = set(p.parts)
        if parts & excludes:
            continue
        out.append(p)
    for p in root.rglob('*.markdown'):
        parts = set(p.parts)
        if parts & excludes:
            continue
        out.append(p)
    for p in root.rglob('*.txt'):
        parts = set(p.parts)
        if parts & excludes:
            continue
        out.append(p)
    # dedupe
    uniq = sorted(dict.fromkeys(out), key=lambda x: str(x))
    return uniq


def extract_tags_from_text(text: str) -> Set[str]:
    # Match simple hashtags like #Anju, #PC, #Some_Name.
    # Return normalized lower-case tag tokens for case-insensitive handling.
    return set(m.group(1).lower() for m in re.finditer(r"#([A-Za-z0-9_-]+)\b", text))


def copy_preserve_rel(root: Path, src: Path, dest_root: Path) -> Path:
    rel = src.relative_to(root)
    dest = dest_root.joinpath(rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Export per-PC and DMs folders and make graphs')
    parser.add_argument('--root', '-r', default='.', help='Vault root (default: current dir)')
    parser.add_argument('--out-graphs', default='graphs', help='Graphs output folder (passed to Wikigraphs.py)')
    parser.add_argument('--run-graphs', action='store_true', help='Run Wikigraphs.py after export')
    parser.add_argument('--dry-run', action='store_true', help="Don't copy files, only show what would happen")
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args(argv)

    repo_root = Path(args.root).resolve()
    print(f"Using root: {repo_root}")

    md_files = find_md_files(repo_root)
    print(f"Found {len(md_files)} markdown/text files (scanning for tags)")

    # Map normalized tag -> list of source files
    tag_map: Dict[str, List[Path]] = {}
    # Preserve first-seen original tag case for nicer folder names
    orig_tag_case: Dict[str, str] = {}
    files_with_no_tags: List[Path] = []

    for p in md_files:
        try:
            txt = p.read_text(encoding='utf-8', errors='replace')
        except Exception:
            txt = ''
        tags = extract_tags_from_text(txt)
        if not tags:
            files_with_no_tags.append(p)
        for t in tags:
            # remember the original-case token if present in the text
            # find exact token to preserve case (first occurrence)
            m = re.search(rf"#({re.escape(t)})\b", txt, flags=re.IGNORECASE)
            disp = m.group(1) if m else t
            tag_map.setdefault(t, []).append(p)
            orig_tag_case.setdefault(t, disp)

    # Try to read a canonical list of PCs from config/pcs_input.md and
    # use that as a whitelist so we don't treat arbitrary tag-like tokens
    # (stat labels, hex colors, etc.) as PC names.
    def read_pcs_input(root: Path) -> Set[str]:
        p = root.joinpath('config', 'pcs_input.md')
        if not p.exists():
            return set()
        try:
            txt = p.read_text(encoding='utf-8', errors='replace')
        except Exception:
            return set()
        # extract names from links like [[Anju]] in the table
        found = set(m.group(1).strip().lower() for m in re.finditer(r"\[\[([^\]]+)\]\]", txt))
        return found

    pcs_whitelist = read_pcs_input(repo_root)
    if pcs_whitelist:
        # Only treat tags that appear in the pcs_input.md listing as PCs
        pc_names = sorted([t for t in tag_map.keys() if t not in ('pc', 'dm') and t in pcs_whitelist])
        print(f"Using pcs_input.md whitelist: {len(pcs_whitelist)} names; will export for {len(pc_names)} matching tagged PCs")
    else:
        # Fall back to previous permissive behavior
        pc_names = sorted([t for t in tag_map.keys() if t not in ('pc', 'dm')])
        if not pc_names:
            print('No PC tags found. Files tagged #PC (if any) will be copied into the aggregate PCs folder.')

    players_root = repo_root.joinpath('Players Part', 'PCs')
    dms_root = repo_root.joinpath('DMs Part')

    created_files: List[Path] = []

    # Create per-PC folders and copy files
    per_pc_created: Dict[str, List[Path]] = {}

    for pc in pc_names:
        display_name = orig_tag_case.get(pc, pc)
        pc_folder = players_root.joinpath(display_name)
        if args.verbose:
            print(f"Preparing PC folder: {pc_folder}")
        if not args.dry_run:
            pc_folder.mkdir(parents=True, exist_ok=True)
        # Files explicitly tagged with the PC or with #PC should be copied into this PC
        files_for_pc: Set[Path] = set(tag_map.get(pc, []))
        files_pc_tag = set(tag_map.get('pc', []))
        files_for_pc.update(files_pc_tag)
        if not files_for_pc:
            if args.verbose:
                print(f"  No files matched for PC '{display_name}'")
            continue
        per_pc_created[display_name] = []
        for src in sorted(files_for_pc):
            dest = players_root.joinpath(display_name)
            if args.dry_run:
                print(f"Would copy {src} -> {dest / src.relative_to(repo_root)}")
            else:
                outp = copy_preserve_rel(repo_root, src, dest)
                created_files.append(outp)
                per_pc_created[display_name].append(outp)
                print(f"Copied {src} -> {outp}")

    # Copy files with #PC tag into all PCs if no explicit PCs found
    if not pc_names and 'pc' in tag_map:
        # create a 'PCs' aggregate folder under Players Part/PCs/PCs
        default_pc = players_root.joinpath('PCs')
        if not args.dry_run:
            default_pc.mkdir(parents=True, exist_ok=True)
        for src in sorted(tag_map.get('pc', [])):
            if args.dry_run:
                print(f"Would copy {src} -> {default_pc / src.relative_to(repo_root)}")
            else:
                outp = copy_preserve_rel(repo_root, src, default_pc)
                created_files.append(outp)
                print(f"Copied {src} -> {outp}")

    # Create DMs folder and copy every markdown file into it (preserving path)
    if args.verbose:
        print(f"Preparing DMs folder: {dms_root}")
    if not args.dry_run:
        dms_root.mkdir(parents=True, exist_ok=True)
    for src in sorted(md_files):
        if args.dry_run:
            print(f"Would copy {src} -> {dms_root / src.relative_to(repo_root)}")
        else:
            outp = copy_preserve_rel(repo_root, src, dms_root)
            created_files.append(outp)
            # Only print a small sample to avoid flooding
            if args.verbose:
                print(f"Copied {src} -> {outp}")

    print(f"Finished exporting. {len(created_files)} files created/copied.")

    # Rich terminal summary
    print('\nExport summary:')
    print(f'- Total source markdown files scanned: {len(md_files)}')
    print(f'- Total files written/copied: {len(created_files)}')
    # per-PC breakdown
    if per_pc_created:
        print('- Per-PC created files:')
        for pc_name, files in sorted(per_pc_created.items()):
            print(f'  - {pc_name}: {len(files)} file(s)')
            if args.verbose and files:
                for f in files[:10]:
                    print(f'      - {f}')
                if len(files) > 10:
                    print(f'      ... and {len(files)-10} more')
    else:
        print('- No per-PC files were created by this run.')
    # DMs count (approx: all md files)
    print(f'- DMs folder contains (copied) {len(md_files)} source files.')

    # Try to include FILE_TRACKER summary if available
    try:
        from Mycelium.helpers.update_char import FILE_TRACKER
        lines = FILE_TRACKER.summary_lines()
        if lines:
            print('\nFile activity (from FILE_TRACKER):')
            for ln in lines:
                print(ln)
    except Exception:
        # not available or no activity
        pass

    # Optionally run Wikigraphs.py to make graphs
    if args.run_graphs:
        wikigraphs = Path('Mycelium/scripts/manuals/Wikigraphs.py')
        if not wikigraphs.exists():
            print(f"Wikigraphs script not found at {wikigraphs}; cannot run graphs.")
            return 1

        # Generate per-PC graphs by invoking Wikigraphs.py --pc <Name>
        if pc_names:
            for norm_name in pc_names:
                display_name = orig_tag_case.get(norm_name, norm_name)
                print(f"Generating graphs for PC: {display_name}")
                cmd = [sys.executable, str(wikigraphs), '--pc', display_name, '--out', args.out_graphs]
                try:
                    subprocess.run(cmd, check=False)
                except Exception as e:
                    print(f"Failed to run Wikigraphs for PC {display_name}: {e}")

        # Generate DMs graphs using --dms-tree
        print("Generating DMs graph (rooted at DMs Part)")
        cmd = [sys.executable, str(wikigraphs), '--dms-tree', '--out', args.out_graphs]
        try:
            subprocess.run(cmd, check=False)
        except Exception as e:
            print(f"Failed to run Wikigraphs for DMs: {e}")

    print('Done')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
