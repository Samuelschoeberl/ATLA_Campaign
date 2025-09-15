"""Helpers to fetch variable files and compute autocomputed variable files.

Provides:
- fetch_variable(identifier, root='.') -> dict

identifier may be a Path to a markdown file or a simple tag like '#Variable'
or a filename stem; the function returns a mapping of keys->int values parsed
from the file. If the file contains formulas or is marked autocomputed (the
presence of a 'Formula' column or the marker '#Autocomputed' in the file),
the loader will evaluate formulas using the project's existing safe-eval
helpers and `char_formulas.json` when available.
"""
from __future__ import annotations

from pathlib import Path
import json
import re
from typing import Dict, Tuple, Optional

# reuse helpers from update_char when possible
try:
    from Mycelium.helpers.update_char import safe_eval_expr, _make_safe_name, parse_table_block
    from Mycelium.helpers.update_char import _strip_wikilink
except Exception:
    # fallback imports for direct script invocation
    try:
        from update_char import safe_eval_expr, _make_safe_name, parse_table_block, _strip_wikilink
    except Exception:
        safe_eval_expr = None
        _make_safe_name = None
        parse_table_block = None
        _strip_wikilink = None


DEFAULT_FORMULAS_PATH = Path('Mycelium') / 'char_formulas.json'


def _find_variable_file(identifier: str, root: Path = Path('.')) -> Optional[Path]:
    # If identifier is a path that exists, return it
    p = Path(identifier)
    if p.exists():
        return p.resolve()
    # try stem match under repo
    from scripts.fsutil import iter_md_files
    for f in iter_md_files(root):
        if f.stem.lower() == identifier.lower():
            return f.resolve()
    # try files that contain '#Variable' tag and where the stem matches
    for f in root.rglob('*.md'):
        try:
            txt = f.read_text(encoding='utf-8')
        except Exception:
            continue
        if '#Variable' in txt and identifier.lower() in f.stem.lower():
            return f.resolve()
    return None


def _load_formulas(path: Path | None = None) -> Dict[str, str]:
    path = Path(path) if path is not None else DEFAULT_FORMULAS_PATH
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return {k: str(v) for k, v in data.items()}
    except Exception:
        return {}


def _parse_two_col_table(path: Path) -> Dict[str, str]:
    txt = path.read_text(encoding='utf-8')
    rows = []
    if parse_table_block:
        try:
            _, table_lines = parse_table_block(txt.splitlines(), 0)
            # table_lines is a list of strings; convert to rows below
            for row in table_lines:
                parts = [p.strip() for p in row.strip().strip('|').split('|')]
                if len(parts) >= 2:
                    left = _strip_wikilink(parts[0]) if _strip_wikilink else parts[0]
                    right = parts[1]
                    rows.append((left, right))
        except Exception:
            rows = []
    # fallback: naive parse of first table
    if not rows:
        lines = txt.splitlines()
        for i, ln in enumerate(lines):
            if '|' in ln:
                # collect contiguous table
                tbl = []
                for j in range(i, len(lines)):
                    if '|' not in lines[j]:
                        break
                    tbl.append(lines[j])
                for r in tbl:
                    parts = [p.strip() for p in r.strip().strip('|').split('|')]
                    if len(parts) >= 2:
                        left = _strip_wikilink(parts[0]) if _strip_wikilink else parts[0]
                        right = parts[1]
                        rows.append((left, right))
                break
    out: Dict[str, str] = {}
    for left, right in rows:
        key = left.strip()
        val = right.strip()
        out[key] = val
    return out


def fetch_variable(identifier: str, root: str | Path = '.') -> Dict[str, int]:
    """Fetch a variable file and return a mapping of label -> int.

    If the file appears autocomputed (contains a 'Formula' column or
    '#Autocomputed'), evaluate formulas using `char_formulas.json` as the
    formula source when needed.
    """
    rootp = Path(root)
    # identifier may be a tag '#Variable' -> return all variable files
    if identifier.strip() == '#Variable' or identifier.strip().lower() == 'variable':
        res: Dict[str, int] = {}
    for f in iter_md_files(rootp):
            try:
                txt = f.read_text(encoding='utf-8')
            except Exception:
                continue
            if '#Variable' in txt:
                    parsed = _parse_two_col_table(f)
                    for k, v in parsed.items():
                        m = re.search(r'(-?\d+)', v)
                        if not m:
                            continue
                        try:
                            res[k] = int(m.group(1))
                        except Exception:
                            continue
        return res

    fpath = _find_variable_file(identifier, rootp)
    if fpath is None:
        raise FileNotFoundError(f'Variable file for "{identifier}" not found')

    parsed = _parse_two_col_table(fpath)
    # detect autocomputed: presence of 'Formula' header or marker
    txt = fpath.read_text(encoding='utf-8')
    autocomputed = False
    if re.search(r'\bFormula\b', txt, flags=re.I) or '#Autocomputed' in txt:
        autocomputed = True

    out: Dict[str, int] = {}
    # simple numeric extraction first
    for k, v in parsed.items():
        m = re.search(r'(-?\d+)', v)
        if m:
            try:
                out[k] = int(m.group(1))
            except Exception:
                out[k] = 0

    if not autocomputed:
        return out

    # Autocomputed: load formulas and evaluate missing keys
    formulas = _load_formulas(DEFAULT_FORMULAS_PATH)
    # Build eval environment from existing out keys
    env = { _make_safe_name(k): v for k, v in out.items() } if _make_safe_name else {k: v for k, v in out.items()}
    # map human labels to formula keys if present
    # Evaluate formulas for keys present in formulas that we don't already have
    for fk, expr in formulas.items():
        # human label variants
        human = fk.replace('_', ' ').title()
        if human in out or fk in out:
            continue
        try:
            if safe_eval_expr:
                val = safe_eval_expr(expr, env)
            else:
                # best-effort: try python eval (restricted)
                val = eval(expr, {'__builtins__': {}}, env)
            out[human] = int(val)
        except Exception:
            # skip unresolved
            continue

    return out
