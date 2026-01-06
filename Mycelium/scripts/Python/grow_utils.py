"""Helpers for git-aware file operations during Mycelium growth scripts."""
from pathlib import Path
from typing import Optional
import subprocess


def read_root_title(root_md: Path) -> Optional[str]:
    """Return the first non-empty line of a Root.md file as the title.

    Returns None if the file doesn't exist or is empty.
    """
    try:
        txt = root_md.read_text(encoding='utf-8')
    except Exception:
        return None
    for ln in txt.splitlines():
        s = ln.strip()
        if s:
            return s
    return None


def is_path_git_ignored(p: Path) -> bool:
    """Return True if git would ignore the given path.

    Falls back to False if git is unavailable or an error occurs.
    """
    try:
        res = subprocess.run(['git', 'check-ignore', '--quiet', str(p)], cwd=str(Path.cwd()))
        return res.returncode == 0
    except Exception:
        return False
