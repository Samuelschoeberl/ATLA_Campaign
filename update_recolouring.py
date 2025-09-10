#!/usr/bin/env python3
"""
update_recolouring.py

Read a color_recolors markdown file and sort contiguous mapping blocks so
that parent paths appear before their children (tree order). Non-mapping
lines (comments, blank lines) are preserved in place.

Usage:
  python update_recolouring.py [--file PATH] [--dry-run]

Creates a backup file when writing changes: <file>.bak
"""
from __future__ import annotations

import argparse
import shutil
import re
from pathlib import Path
from typing import List, Tuple


MAPPING_RE = re.compile(r"^\s*(?P<path>.+?)=#(?P<hex>[0-9A-Fa-f]{6})\s*$")


def sort_key_for_path(path: str) -> Tuple:
    # Unescape a leading backslash used for escaping some special paths
    p = path.lstrip()
    if p.startswith('\\'):
        p = p[1:]

    # Normalize and split into meaningful segments (ignore empty segments)
    segments = [seg.casefold() for seg in p.split('/') if seg != '']

    # Return a tuple of segments which sorts lexicographically; shorter tuples
    # (parents) will compare before deeper children when they share a prefix.
    return tuple(segments)


def process_lines(lines: List[str]) -> List[str]:
    out: List[str] = []
    i = 0
    n = len(lines)
    while i < n:
        # If current line starts a mapping, collect the contiguous mapping block
        m = MAPPING_RE.match(lines[i])
        if m:
            start = i
            block: List[Tuple[str, str, str]] = []  # (orig_line, path, hex)
            while i < n:
                mm = MAPPING_RE.match(lines[i])
                if not mm:
                    break
                path = mm.group('path')
                hexcode = mm.group('hex')
                block.append((lines[i], path, hexcode))
                i += 1

            # Sort the block so parents come before children and lexicographic within same level
            block_sorted = sorted(block, key=lambda t: sort_key_for_path(t[1]))

            # Append sorted original lines
            out.extend([item[0] for item in block_sorted])
            continue

        # Non-mapping line: copy as-is
        out.append(lines[i])
        i += 1

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Sort color_recolors mapping blocks into tree order")
    ap.add_argument('--file', '-f', default='color_recolors.md', help='Path to color_recolors.md')
    ap.add_argument('--dry-run', action='store_true', help='Print result to stdout instead of writing')
    ap.add_argument('--sort', action='store_true', help='Apply sorting and write the file (creates a .bak backup)')
    ap.add_argument('--blend-characters', action='store_true', help='Generate per-character colour mappings from element levels in npc_input.md')
    ap.add_argument('--prefix', default='NPCs/', help='Path prefix to use for generated character mappings (default: "NPCs/")')
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}")
        return 2

    text = path.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)

    # If requested, generate blended colours for characters and inject into the
    # Per-NPC generated block (or append one).
    if args.blend_characters:
        # Read base colours from the existing file mappings (Air/Water/Fire/Earth/Spirit)
        base_cols = {}
        for ln in lines:
            mm = MAPPING_RE.match(ln)
            if not mm:
                continue
            p = mm.group('path').strip()
            h = mm.group('hex')
            # Keys in file are like _/Air/ or _/Water/
            if p.endswith('/'):  # folder style
                key = p
            else:
                key = p
            base_cols[key] = h

        # helper to lookup element base colour by element name
        def element_hex(name: str) -> str | None:
            # try few likely forms
            candidates = [f'_/%s/' % name, f'_{name}/', f'/{name}/', name]
            name_l = name
            for c in candidates:
                if c in base_cols:
                    return base_cols[c]
            # fallback: try case-insensitive match ending with name
            for k, v in base_cols.items():
                if k.lower().endswith(name_l.lower() + '/') or k.lower().endswith('/' + name_l.lower() + '/'):
                    return v
            return None

        # Parse npc_input.md to extract names and element levels
        npc_path = Path('npc_input.md')
        char_rows = []  # list of (name, {element: value})
        if npc_path.exists():
            table_lines = npc_path.read_text(encoding='utf-8').splitlines()
            # find header line (starts with | and contains Name)
            header_idx = None
            for idx, tln in enumerate(table_lines):
                if tln.strip().startswith('|') and 'Name' in tln:
                    header_idx = idx
                    break
            if header_idx is not None:
                headers = [h.strip() for h in table_lines[header_idx].split('|')]
                # map header name to index
                header_map = {h: i for i, h in enumerate(headers)}
                # element names to look up
                elems = ['Water', 'Earth', 'Air', 'Fire', 'Spirit']
                # process subsequent rows until a non-table line
                for row in table_lines[header_idx+2:]:
                    if not row.strip().startswith('|'):
                        break
                    cols = [c.strip() for c in row.split('|')]
                    if len(cols) <= 1:
                        continue
                    name = cols[1]
                    data = {}
                    for e in elems:
                        try:
                            idx = headers.index(e)
                            val = cols[idx] if idx < len(cols) else ''
                            data[e] = int(val) if val.isdigit() else 0
                        except ValueError:
                            data[e] = 0
                    char_rows.append((name, data))

        else:
            print('Warning: npc_input.md not found; no character colours will be generated')

        # Also read PCs from pcs_input.md and include them
        pcs_path = Path('pcs_input.md')
        if pcs_path.exists():
            table_lines = pcs_path.read_text(encoding='utf-8').splitlines()
            header_idx = None
            for idx, tln in enumerate(table_lines):
                if tln.strip().startswith('|') and 'Name' in tln:
                    header_idx = idx
                    break
            if header_idx is not None:
                headers = [h.strip() for h in table_lines[header_idx].split('|')]
                elems = ['Water', 'Earth', 'Air', 'Fire', 'Spirit']
                for row in table_lines[header_idx+2:]:
                    if not row.strip().startswith('|'):
                        break
                    cols = [c.strip() for c in row.split('|')]
                    if len(cols) <= 1:
                        continue
                    name = cols[1]
                    data = {}
                    for e in elems:
                        try:
                            idx = headers.index(e)
                            val = cols[idx] if idx < len(cols) else ''
                            data[e] = int(val) if val.isdigit() else 0
                        except ValueError:
                            data[e] = 0
                    char_rows.append((name, data))

        # convert hex to rgb and back
        def hex_to_rgb(h: str):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        def rgb_to_hex(rgb):
            return ''.join(f'{int(max(0,min(255,v))):02x}' for v in rgb)

        # helper: find best matching markdown file for a character name in workspace
        import string

        def normalize(s: str) -> str:
            s = s.lower()
            # remove punctuation
            s = ''.join(ch for ch in s if ch.isalnum() or ch.isspace())
            s = ' '.join(s.split())
            return s

        def find_file_for_name(name: str):
            norm_name = normalize(name)
            name_tokens = norm_name.split()
            best = None
            best_score = 0
            for candidate in Path('.').rglob('*.md'):
                # skip the color_recolors file itself
                if candidate.name == Path(args.file).name:
                    continue
                cand_name = normalize(candidate.stem)
                score = 0
                # exact match
                if cand_name == norm_name:
                    return candidate
                # token matches
                for t in name_tokens:
                    if t and t in cand_name:
                        score += 1
                # prefer files under DMs Part/NPCs or NPCs or PCs if present
                path_str = str(candidate)
                if 'dmspart' in path_str.lower() or '/npcs/' in path_str.lower():
                    score += 1
                if score > best_score:
                    best_score = score
                    best = candidate
            return best

        # build generated folder-level mapping lines (underscore-prefixed folders)
        folder_map: dict[str, str] = {}
        for name, data in char_rows:
            # compute weighted mix
            weights = sum(data.values())
            if weights == 0:
                colour = 'f3efe1'
            else:
                acc = [0.0, 0.0, 0.0]
                for elem, val in data.items():
                    hexcol = element_hex(elem)
                    if not hexcol:
                        continue
                    r, g, b = hex_to_rgb(hexcol)
                    w = val / weights
                    acc[0] += r * w
                    acc[1] += g * w
                    acc[2] += b * w
                colour = rgb_to_hex(acc)

            candidate = find_file_for_name(name)
            if candidate:
                folder_name = candidate.parent.name
            else:
                # fallback: sanitized folder name from character name
                safe = name.replace(',', '').strip()
                folder_name = ' '.join(safe.split())

            # produce underscore-prefixed folder key
            key = f'_/{folder_name}/'
            # keep the first computed colour for a folder
            if key not in folder_map:
                folder_map[key] = colour

        # create sorted gen_lines from folder_map
        gen_lines = [f"{k}=#{v}\n" for k, v in sorted(folder_map.items(), key=lambda kv: sort_key_for_path(kv[0]))]

        # Insert or replace the generated block under the Per-NPC header
        header_key = None
        for idx, ln in enumerate(lines):
            if ln.strip().lower().startswith('# per-npc pastel overrides'):
                header_key = idx
                break

        if header_key is None:
            # append header and block
            lines.append('\n')
            lines.append('# Per-NPC pastel overrides (generated)\n')
            lines.append('\n')
            lines.extend(gen_lines)
        else:
            # find start of mappings after header
            j = header_key + 1
            # skip blank lines
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            # from j, find end of contiguous mapping block
            k = j
            while k < len(lines) and MAPPING_RE.match(lines[k]):
                k += 1
            # replace [j:k] with gen_lines
            new_block = ['\n'] + ['# Per-NPC pastel overrides (generated)\n', '\n'] + gen_lines
            # splice
            lines = lines[:header_key] + new_block + lines[k:]

    new_lines = process_lines(lines)

    # If user asked for a dry-run, print the resulting sorted output.
    if args.dry_run:
        print(''.join(new_lines), end='')

    # If user asked to apply sorting, write backup and file.
    if args.sort:
        bak = path.with_suffix(path.suffix + '.bak')
        try:
            shutil.copy2(path, bak)
            print(f'Backup written to: {bak}')
        except Exception as e:
            print(f'Warning: could not write backup: {e}')

        path.write_text(''.join(new_lines), encoding='utf-8')
        print(f'Wrote sorted mappings to: {path}')
        return 0

    # If neither dry-run nor sort was requested, inform the user and exit.
    print('No action requested. Use --dry-run to preview changes or --sort to apply them.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
