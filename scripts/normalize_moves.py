#!/usr/bin/env python3
"""Normalize bend move markdown files to the Level 1 move format.

This script:
- walks "Player Root/Rules/Bending Rules"
- processes only files in paths that include "Moves"
- ensures content is wrapped in a ```markdown fence
- ensures the first non-empty line is a header starting with '#', else prepends '#Action'
- normalizes header text (replace spaces with underscores after '#')
- gathers hashtag-style tags found anywhere and ensures they're present at the end as lines

It's conservative: it rewrites only when changes are needed and prints modified file paths.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'Player Root' / 'Rules' / 'Bending Rules'
if not ROOT.exists():
    print(f"ERROR: expected root path {ROOT} to exist", file=sys.stderr)
    sys.exit(1)

md_fns = [p for p in ROOT.rglob('*.md') if 'Moves' in str(p)]

HEADER_RE = re.compile(r'^(#+)\s*(.*)$')
TAG_RE = re.compile(r"#[-\w']+")

modified = []
for p in md_fns:
    s = p.read_text(encoding='utf-8')
    original = s
    # extract inner fenced markdown if present
    inner = s
    m_fence = re.search(r'```\s*markdown\n(.*?)\n```', s, re.S | re.I)
    if m_fence:
        inner = m_fence.group(1)

    lines = inner.splitlines()
    # strip leading/trailing blank lines
    while lines and lines[0].strip() == '':
        lines.pop(0)
    while lines and lines[-1].strip() == '':
        lines.pop()

    # ensure first non-empty line is a header
    if not lines or not lines[0].lstrip().startswith('#'):
        lines.insert(0, '#Action')
        lines.insert(1, '')
    else:
        # normalize header: collapse multiple leading # to single and replace spaces with _ in tag
        header = lines[0].strip()
        m = HEADER_RE.match(header)
        if m:
            hashes, rest = m.groups()
            rest_clean = '_'.join(rest.split())
            lines[0] = f'#' + rest_clean

    content = '\n'.join(lines)

    # collect tags from entire original content
    tags = set(TAG_RE.findall(original))
    # remove tags that are header-like (e.g., #Action, #Bonus_Action, #Level1) keep them too
    # create tags block
    tag_lines = sorted(tags)

    # ensure tags appear at the end as lines (one per line)
    # remove existing trailing tag lines from content
    content_no_trailing_tags = re.sub(r'(\n#[-\w\']+(?:\n#[-\w\']+)*)\s*\Z', '\n', content)
    if tag_lines:
        content_final = content_no_trailing_tags.rstrip() + '\n\n' + '\n'.join(tag_lines) + '\n'
    else:
        content_final = content_no_trailing_tags.rstrip() + '\n'

    # wrap in fenced code block
    new_text = '```markdown\n' + content_final + '```\n'

    if new_text != original:
        p.write_text(new_text, encoding='utf-8')
        modified.append(str(p))

print(f"Processed {len(md_fns)} files under {ROOT}")
if modified:
    print(f"Modified {len(modified)} files:")
    for m in modified:
        print(m)
else:
    print("No files needed modification.")
