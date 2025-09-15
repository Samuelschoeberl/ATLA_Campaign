from pathlib import Path
import os
import fnmatch
import re
from shutil import copy2
from typing import Optional, Sequence, List, Tuple, Dict

DEFAULT_EXCLUDES = {".git", "node_modules", ".obsidian", "__pycache__", "venv", ".venv"}


def load_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors='replace')
    except Exception:
        return None


def unobsidify(text: str) -> str:
    if not text:
        return text
    s = text
    s = re.sub(r'^---\n.*?\n---\n', '', s, flags=re.S)
    s = re.sub(r'%%.*?%%', '', s, flags=re.S)
    s = re.sub(r'!\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', s)
    s = re.sub(r'!\[\[([^\]]+)\]\]', r'\1', s)
    s = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', s)
    s = re.sub(r'\[\[([^\]]+)\]\]', r'\1', s)

    def _collapse_code(m: re.Match) -> str:
        body = m.group(2) or ''
        for ln in body.splitlines():
            ln = ln.strip()
            if ln:
                return f'`{ln}`'
        return '`code`'

    s = re.sub(r'(```|~~~)(.*?)\1', _collapse_code, s, flags=re.S)
    s = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', s)
    s = re.sub(r'(?m)^[ \t]*#{1,6}\s*', '', s)
    s = re.sub(r'[\*_`~]+', '', s)
    s = re.sub(r'\r\n|\r', '\n', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    s = s.strip()
    return s


def gather_file_tree(root: Path, exts=None, excludes=None, include_gitignored: bool = False) -> Tuple[Dict[str,int], Dict[str,str], Dict[str,str]]:
    if exts is None:
        exts = {'.md', '.markdown', '.txt'}
    if excludes is None:
        excludes = DEFAULT_EXCLUDES

    root = Path(root).resolve()
    sizes = {}
    contents = {}
    raw_contents = {}

    gitignore_path = root.joinpath('.gitignore')
    git_patterns = []
    if gitignore_path.exists():
        try:
            raw = gitignore_path.read_text(encoding='utf-8', errors='replace')
            for ln in raw.splitlines():
                ln = ln.strip()
                if not ln or ln.startswith('#'):
                    continue
                git_patterns.append(ln)
        except Exception:
            git_patterns = []

    def matches_gitignore(rel_str: str, parts: List[str]) -> bool:
        for pat in git_patterns:
            p = pat.strip()
            if not p:
                continue
            if p.endswith('/'):
                name = p.rstrip('/')
                if any(part == name for part in parts):
                    return True
                if rel_str.startswith(name + os.sep):
                    return True
            elif '/' in p:
                if fnmatch.fnmatch(rel_str, p):
                    return True
            else:
                if fnmatch.fnmatch(parts[-1], p):
                    return True
        return False

    for p in root.rglob('*'):
        try:
            rel = p.relative_to(root)
            rel_str = str(rel)
            parts = list(rel.parts)
        except Exception:
            rel_str = str(p)
            parts = list(p.parts)

        if any(part in excludes for part in parts):
            continue
        low_parts = [pp.lower() for pp in parts]
        if any('collectionfile' in lp or 'collectionfiles' in lp for lp in low_parts):
            continue
        if any('expandedcollections' in lp or 'simple_expanded_megafile' in lp or 'expanded' == lp for lp in low_parts):
            continue
        if git_patterns and not include_gitignored and matches_gitignore(rel_str, parts):
            continue
        if p.is_file() and (not exts or p.suffix.lower() in exts):
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            rel = p.relative_to(root)
            parts = list(rel.parts)
            file_key = "/".join(parts)
            sizes[file_key] = size or 1
            try:
                if p.suffix.lower() == '.md':
                    txt = p.read_text(encoding='utf-8', errors='replace')
                    contents[file_key] = unobsidify(txt)
                    raw_contents[file_key] = txt
            except Exception:
                pass
            for i in range(1, len(parts)):
                dir_key = "/".join(parts[:i]) + "/"
                sizes[dir_key] = sizes.get(dir_key, 0) + (size or 1)
            sizes['/'] = sizes.get('/', 0) + (size or 1)

    return sizes, contents, raw_contents


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='Gather file tree sizes and contents')
    p.add_argument('root', nargs='?', default='.', help='Root folder to scan')
    args = p.parse_args()
    sizes, contents, raw = gather_file_tree(Path(args.root))
    print(f"Found {len(sizes)} entries; {len(contents)} markdown files with content")
