"""Scan #variable files and display backlinks as an ASCII tree.

This script scans the vault `variable/` folder (discovered from Root.md when
available) and builds backlinks between `#variable` files by parsing `[[...]]`
links inside each file. It prints an ASCII tree showing which files reference
each variable, which helps quickly traverse dependent files to update.

Usage:
  python3 Mycelium/scripts/python/append_backlinks.py [--start NAME] [--max-depth N]

Options:
  --start, -s   Start the tree at a particular variable filename stem (no .md).
  --max-depth   Limit recursion depth (default: 6).
  --write, -w   Optionally append a backlinks section to each variable file (disabled by default).
  --verbose, -v Verbose logging.
"""
from pathlib import Path
import argparse
import importlib.util
import re
import sys


ROOT = Path('.').resolve()


def discover_variable_root() -> Path:
    # Try to reuse existing helper (recreate_pcs) if present
    try:
        helper_path = ROOT.joinpath('Mycelium', 'scripts', 'Python', 'mycelium_grow_mushroom.py')
        if helper_path.exists():
            spec = importlib.util.spec_from_file_location('mycelium_grow_mushroom', str(helper_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                # many scripts here provide find_root_md; reuse logic used elsewhere
                if hasattr(mod, 'find_root_md'):
                    rm = mod.find_root_md()
                    if rm:
                        try:
                            txt = Path(rm).read_text(encoding='utf-8')
                            for ln in txt.splitlines():
                                s = ln.strip()
                                if not s or s.startswith('#'):
                                    continue
                                vault = ROOT.joinpath(s)
                                var_dir = vault.joinpath('variable')
                                if var_dir.exists():
                                    return var_dir
                                # create if missing
                                var_dir.mkdir(parents=True, exist_ok=True)
                                return var_dir
                        except Exception:
                            pass
    except Exception:
        pass
    # fallback
    cand = ROOT.joinpath('Player Root', 'variable')
    cand.mkdir(parents=True, exist_ok=True)
    return cand


def find_variable_files(var_root: Path) -> list[Path]:
    out = []
    for p in var_root.rglob('*.md'):
        try:
            txt = p.read_text(encoding='utf-8')
        except Exception:
            continue
        if '#variable' in txt.lower() or '#variable' in p.name.lower():
            out.append(p)
    return out


def parse_links(text: str) -> list[str]:
    # find [[...]] links
    return [m.strip() for m in re.findall(r"\[\[([^\]]+)\]\]", text)]


def normalize_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\- ]", '', s).strip().lower().replace(' ', '_')


def build_backlinks(files: list[Path], var_root: Path):
    # map stems to paths
    stem_map = {}
    for p in files:
        stem_map[p.stem.lower()] = p
    # graph: node -> set(of files that reference node)
    backlinks = {p: set() for p in files}
    for p in files:
        txt = p.read_text(encoding='utf-8')
        links = parse_links(txt)
        for L in links:
            norm = L.strip()
            # try direct stem match, case-insensitive
            tgt = None
            key = norm.lower()
            if key in stem_map:
                tgt = stem_map[key]
            else:
                # try normalized forms
                n2 = normalize_name(norm)
                for s, path in stem_map.items():
                    if normalize_name(s) == n2:
                        tgt = path
                        break
            if tgt and tgt in backlinks:
                backlinks[tgt].add(p)
    return backlinks


def print_tree(backlinks: dict, start: Path, max_depth: int = 6, seen=None, prefix=''):
    if seen is None:
        seen = set()
    if start in seen or max_depth < 0:
        return
    seen.add(start)
    print(prefix + start.relative_to(ROOT).as_posix())
    children = sorted(backlinks.get(start, []), key=lambda p: p.name.lower())
    for i, c in enumerate(children):
        is_last = (i == len(children) - 1)
        branch = '└── ' if is_last else '├── '
        child_prefix = prefix + ('    ' if is_last else '│   ')
        print(prefix + branch + c.relative_to(ROOT).as_posix())
        # recurse
        print_tree(backlinks, c, max_depth - 1, seen, prefix + ( '    ' if is_last else '│   '))


def main():
    p = argparse.ArgumentParser(description='Generate backlinks ASCII tree for #variable files')
    p.add_argument('--start', '-s', help='Start from this variable stem (no .md)')
    p.add_argument('--max-depth', type=int, default=6, help='Max recursion depth')
    p.add_argument('--write', '-w', action='store_true', help='Append backlinks section to files')
    p.add_argument('--verbose', '-v', action='store_true')
    args = p.parse_args()

    var_root = discover_variable_root()
    files = find_variable_files(var_root)
    if not files:
        print('No #variable files found under', var_root)
        return
    backlinks = build_backlinks(files, var_root)

    # if start given, resolve to path
    if args.start:
        key = args.start.strip().lower()
        candidate = None
        for p in files:
            if p.stem.lower() == key or normalize_name(p.stem) == normalize_name(key):
                candidate = p
                break
        if not candidate:
            print('Start variable not found:', args.start)
            return
        print('Backlink tree for', candidate.relative_to(ROOT))
        print_tree(backlinks, candidate, max_depth=args.max_depth)
    else:
        # print a compact index: nodes with inbound links first
        roots = sorted(files, key=lambda p: p.name.lower())
        for r in roots:
            print_tree(backlinks, r, max_depth=args.max_depth)
            print()

    if args.write:
        # append backlinks section to each file (idempotent)
        for p in files:
            refs = sorted([x.relative_to(ROOT).as_posix() for x in backlinks.get(p, [])])
            if not refs:
                continue
            txt = p.read_text(encoding='utf-8')
            marker = '\n\n<!-- backlinks -->\n'
            if '<!-- backlinks -->' in txt:
                # replace existing section
                head = txt.split('<!-- backlinks -->', 1)[0]
            else:
                head = txt
            tail = '\n\n**Backlinks:**\n'
            for r in refs:
                tail += f'- {r}\n'
            p.write_text(head + marker + tail, encoding='utf-8')
        print('Backlinks appended to files')


if __name__ == '__main__':
    main()
