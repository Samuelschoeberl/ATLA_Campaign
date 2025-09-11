#!/usr/bin/env python3
"""Add a top-line wikilink [[Name]] to all Character Sheet.md files under the repo.
Backs up original files as <file>.bak before editing.
"""
from pathlib import Path
import re

root = Path('.')
pattern = re.compile(r'^(.*) Character Sheet\.md$')

changed = []
for p in root.rglob('* Character Sheet.md'):
    try:
        text = p.read_text(encoding='utf-8')
    except Exception:
        continue
    lines = text.splitlines()
    if lines and re.match(r'^\s*\[\[.*\]\]\s*$', lines[0]):
        # already has top wikilink
        continue
    # try to infer name from filename or parent folder
    name = None
    m = pattern.match(p.name)
    if m:
        name = m.group(1)
    if not name:
        name = p.parent.name
    wikiline = f'[[{name}]]\n'
    # backup
    bak = p.with_suffix(p.suffix + '.bak')
    try:
        if not bak.exists():
            bak.write_text(text, encoding='utf-8')
        newtext = wikiline + text
        p.write_text(newtext, encoding='utf-8')
        changed.append(str(p))
    except Exception as e:
        print('Failed to update', p, e)

print('Updated files:')
for c in changed:
    print(c)
print(f'Total updated: {len(changed)}')
