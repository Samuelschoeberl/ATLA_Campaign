"""Helpers to read small markdown files that declare variables like '#path' or '#variable'.

Contract:
- A markdown file containing a line like 'path: Players Part/PCs' or a top-level tag '#path'
  will be parsed to supply default values for scripts. The helper exposes `find_path_var`
  which searches common config files and returns a repo-relative path if found.
"""
from pathlib import Path
import re
from typing import Optional


def parse_key_values_from_md(text: str) -> dict:
    out = {}
    # simple key: value pairs
    for line in text.splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            k = k.strip().lower()
            v = v.strip()
            if k:
                out[k] = v
    return out


def find_path_var(repo_root: Path, candidates=None) -> Optional[str]:
    """Search for a path variable in common markdown files under repo_root.

    Returns a string path (repo-relative) or None.
    """
    if candidates is None:
        # updated to new repository layout where variable files live under
        # Mycelium/variable/ and templates under Mycelium/template/
        candidates = [
            repo_root / 'Mycelium' / 'Mycelium_config.md',
            repo_root / 'Mycelium' / 'variable' / 'Root.md',
            repo_root / 'Mycelium' / 'Mycelium.md',
            repo_root / 'Mycelium' / 'Mycelium_config.md.bak',
            repo_root / 'Mycelium' / 'Mycelium_config.md'
        ]

    tag_re = re.compile(r"#\s*path\b", flags=re.IGNORECASE)
    key_re = re.compile(r"^path\s*:\s*(.+)$", flags=re.IGNORECASE)

    for p in candidates:
        try:
            txt = p.read_text(encoding='utf-8')
        except Exception:
            continue
        # first, look for explicit key: value
        for ln in txt.splitlines():
            m = key_re.match(ln.strip())
            if m:
                val = m.group(1).strip()
                if val:
                    return val
        # next, look for a '#path' tag followed by a path in the next non-empty line
        if tag_re.search(txt):
            for i, ln in enumerate(txt.splitlines()):
                if tag_re.search(ln):
                    # look ahead
                    for ln2 in txt.splitlines()[i+1:i+6]:
                        if ln2.strip():
                            # take the line as path
                            return ln2.strip()
    return None
