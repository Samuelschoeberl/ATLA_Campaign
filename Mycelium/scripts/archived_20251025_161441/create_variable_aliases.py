#!/usr/bin/env python3
"""Create alias files for #variable files.

This script scans Player Root/variable/** for Markdown files and, for
known short-name stems (for example `str`), creates a human-friendly
alias file (for example `Strength.md`) next to the original. The
alias file contains the same content but ensures a `#alias` tag is
present on the first tag line (or inserted at the top if no tag line
exists).

Idempotent: it will not overwrite existing alias files.
"""
from pathlib import Path
import re
import sys


VARIABLE_ROOT = Path(__file__).resolve().parents[3] / 'Player Root' / 'variable'


def normalize(name: str) -> str:
    return re.sub(r'[^a-z0-9]', '', name.lower())


ALIAS_MAP = {
    'str': 'strength',
    'dex': 'dexterity',
    'con': 'constitution',
    'int': 'intelligence',
    'wis': 'wisdom',
    'cha': 'charisma',
    'hp': 'hp',
}


def add_alias_tag_to_content(content: str) -> str:
    # Find first non-empty line
    lines = content.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == '':
            continue
        # If it's a tag line (starts with #), append #alias if missing
        if ln.lstrip().startswith('#'):
            if '#alias' in ln:
                return content
            lines[i] = ln.rstrip() + ' #alias'
            return '\n'.join(lines) + ('\n' if content.endswith('\n') else '')
        else:
            # Insert a new tag line at the top
            return '#alias\n' + content
    # Empty file
    return '#alias\n'


def main():
    root = VARIABLE_ROOT
    if not root.exists():
        print(f"Variable root not found: {root}")
        sys.exit(1)

    created = 0
    skipped = 0
    for p in root.rglob('*.md'):
        stem = p.stem
        key = normalize(stem)
        if key not in ALIAS_MAP:
            continue
        alias_name = ALIAS_MAP[key]
        # create lowercase alias filenames to avoid relying on capitalisation
        alias_path = p.with_name(alias_name.lower() + p.suffix)
        if alias_path.exists():
            skipped += 1
            continue
        content = p.read_text(encoding='utf-8')
        new_content = add_alias_tag_to_content(content)
        alias_path.write_text(new_content, encoding='utf-8')
        print(f"Created alias: {alias_path.relative_to(root.parent)} -> from {p.relative_to(root.parent)}")
        created += 1

    print(f"Done. Created: {created}, Skipped (already existed): {skipped}")


if __name__ == '__main__':
    main()
