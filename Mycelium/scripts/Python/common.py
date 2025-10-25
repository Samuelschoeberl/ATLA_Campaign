#!/usr/bin/env python3
"""Common utilities for Mycelium scripts (deduplicated helpers).

Import from scripts in this folder via:
  from common import (...)

This module centralizes frequently repeated helpers for:
- repo root detection
- safe numeric parsing and expression evaluation
- markdown variable file read/write
- key normalization and display-name formatting
- table parsing
- variable root discovery and template loading
"""
from __future__ import annotations
from pathlib import Path
import re
import ast
from typing import Any, Dict, List, Optional, Tuple
import importlib.util
import sys

# Single canonical ROOT
# This file is in Mycelium/scripts/Python/, so go up 3 levels to repo root
ROOT = Path(__file__).resolve().parents[3]


# -------- number and expression helpers --------
def to_number(s: Any) -> Any:
    if s is None:
        return 0
    s = str(s).strip()
    if s == '':
        return 0
    s = s.replace(',', ' ')
    try:
        if re.search(r"\d\.\d", s):
            m = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
            if m:
                return float(m.group(0))
            return 0
        m2 = re.search(r"[-+]?[0-9]+", s)
        if m2:
            return int(m2.group(0))
    except Exception:
        pass
    m = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
    if m:
        g = m.group(0)
        return float(g) if '.' in g else int(g)
    return 0


_ALLOWED_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
}
_ALLOWED_UNARY = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}


def safe_eval(expr: str) -> Any:
    """Evaluate a simple arithmetic expression safely (no names/calls)."""
    expr = str(expr).strip()
    if expr == '':
        return 0
    try:
        node = ast.parse(expr, mode='eval')
    except Exception:
        return expr

    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.BinOp):
            op = type(n.op)
            if op not in _ALLOWED_BINOPS:
                raise ValueError('unsupported op')
            return _ALLOWED_BINOPS[op](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.UnaryOp):
            op = type(n.op)
            if op not in _ALLOWED_UNARY:
                raise ValueError('unsupported unary')
            return _ALLOWED_UNARY[op](_eval(n.operand))
        raise ValueError('unsupported expression')

    try:
        return _eval(node)
    except Exception:
        return expr


# -------- markdown utils --------
FENCED_VALUE_PATTERN = re.compile(r"```markdown\n(.*?)\n\n", flags=re.S)


def read_var_value(path: Path) -> str:
    """Return the first value string from a variable markdown file.
    Supports fenced ```markdown blocks or the first non-tag line.
    Returns '' if not found or file missing.
    """
    try:
        txt = path.read_text(encoding='utf-8')
    except Exception:
        return ''
    m = FENCED_VALUE_PATTERN.search(txt)
    if m:
        return m.group(1).strip()
    for ln in txt.splitlines():
        s = ln.strip()
        if not s or s.startswith('#'):
            continue
        return s
    return ''


def write_var_file(path: Path, value: Any, tags: Optional[List[str]] = None) -> None:
    tags = tags or ['#variable']
    tag_line = ' '.join(tags)
    content = f"```markdown\n{value}\n\n{tag_line}\n\n```\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


# -------- name/key helpers --------
def normalize_key(k: str) -> str:
    return k.strip().lower().replace('_', ' ').replace('.', ' ').replace('  ', ' ').strip()


def display_name_for(key: str) -> str:
    mapping = {
        'str': 'Strength', 'dex': 'Dexterity', 'con': 'Constitution',
        'int': 'Intelligence', 'wis': 'Wisdom', 'cha': 'Charisma',
        'hp': 'HP', 'max_hp': 'Max HP',
    }
    kn = key.replace('.', '_').replace(' ', '_').lower()
    if kn in mapping:
        return mapping[kn]
    k = kn.replace('_', ' ').replace('.', ' ')
    words = k.split()
    out = []
    for i, w in enumerate(words):
        if w.lower() in ('hp',):
            out.append(w.upper())
        else:
            out.append(w.capitalize() if i == 0 else w.lower())
    return ' '.join(out)


def name_from_cell(cell: str) -> str:
    m = re.search(r"\[\[([^\]]+)\]\]", cell or '')
    return m.group(1).strip() if m else (cell or '').strip()


def name_from_sheet(path: Path) -> str:
    """Read a character sheet file and return the name (prefer header 'Name:')."""
    try:
        txt = path.read_text(encoding='utf-8')
        for ln in txt.splitlines():
            if ln.strip().lower().startswith('name:'):
                return ln.split(':', 1)[1].strip()
    except Exception:
        pass
    parent = path.parent.name
    if parent:
        return parent
    return path.stem


def pc_safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]", '_', name)


def canonical_variable_key(key: str) -> str:
    """Normalize variable keys so aliases like spaces/dots/underscores match."""
    return re.sub(r'[\s._]+', '_', key.strip().lower())


def _variable_display_score(key: str) -> tuple:
    """Return a tuple that ranks display variants consistently.

    Preference order:
      1. Keys containing underscores (canonical style)
      2. Keys containing spaces
      3. Plain or dotted keys
    Longest key wins within the same bucket, then lexical tiebreaker for stability.
    """
    s = str(key)
    if '_' in s:
        bucket = 2
    elif ' ' in s:
        bucket = 1
    else:
        bucket = 0
    return (bucket, len(s), s.lower())


def dedupe_variable_items(items: Dict[str, Any]) -> List[Tuple[str, Any]]:
    """Return (display_key, value) pairs with aliases collapsed.

    The incoming `items` may contain keys like 'air attack roll', 'air_attack_roll',
    or 'air.attack.roll' that represent the same statistic. This helper keeps only
    the preferred display variant while preserving deterministic ordering.
    """
    dedup: Dict[str, Tuple[str, Any, tuple]] = {}
    for raw_key, raw_val in items.items():
        if raw_key is None:
            continue
        display_key = str(raw_key)
        canon = canonical_variable_key(display_key)
        score = _variable_display_score(display_key)
        existing = dedup.get(canon)
        if existing is None or score > existing[2] or (score == existing[2] and display_key < existing[0]):
            dedup[canon] = (display_key, raw_val, score)
    return [(entry[0], entry[1]) for canon, entry in sorted(dedup.items(), key=lambda kv: kv[0])]


def parse_markdown_table(path: Path) -> Tuple[List[str], List[List[str]]]:
    try:
        txt = path.read_text(encoding='utf-8')
    except Exception:
        return [], []
    lines = [l.rstrip() for l in txt.splitlines()]
    for i in range(len(lines) - 1):
        if '|' in lines[i] and re.search(r"\|\s*-{1,}\s*\|", lines[i + 1]):
            header = [h.strip() for h in lines[i].strip().strip('|').split('|')]
            rows: List[List[str]] = []
            j = i + 2
            while j < len(lines) and '|' in lines[j]:
                row = [c.strip() for c in lines[j].strip().strip('|').split('|')]
                rows.append(row)
                j += 1
            return header, rows
    return [], []


# -------- vault roots and templates --------
def get_variable_root(foldername: Optional[str] = None) -> Optional[Path]:
    """Best-effort variable folder discovery; mirrors recreate_pcs.get_variable_root."""
    if foldername:
        try:
            fname = foldername.strip()
            for p in ROOT.rglob('*'):
                if p.is_dir() and p.name == fname:
                    var_dir = p.joinpath('variable')
                    var_dir.mkdir(parents=True, exist_ok=True)
                    return var_dir
        except Exception:
            pass
    try:
        helper_path = ROOT.joinpath('Mycelium', 'scripts', 'Python', 'mycelium_grow_mushroom.py')
        if helper_path.exists():
            spec = importlib.util.spec_from_file_location('mycelium_grow_mushroom', str(helper_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
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
                                var_dir.mkdir(parents=True, exist_ok=True)
                                return var_dir
                        except Exception:
                            pass
    except Exception:
        pass
    cand = ROOT.joinpath('Player Root', 'variable')
    if cand.exists():
        return cand
    return None


def load_secondary_templates(dirpath: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not dirpath.exists():
        return out
    for p in sorted(dirpath.glob('*.md')):
        txt = p.read_text(encoding='utf-8')
        stripped = re.sub(r'(```|~~~).*?\1', '', txt, flags=re.S)
        if '#secondary_stat' not in stripped and '#secondary_stat' not in txt:
            continue
        lines = [l for l in stripped.splitlines() if l.strip() and not l.strip().startswith('#')]
        formula = lines[0].strip() if lines else ''
        if not formula:
            m = re.search(r'(```|~~~)(.*?)\1', txt, flags=re.S)
            if m:
                inner = m.group(2)
                inner_lines = [l for l in inner.splitlines() if l.strip() and not l.strip().startswith('#')]
                if inner_lines:
                    formula = inner_lines[0].strip()
        formula = re.sub(r"\\([^\w\s])", r"\1", formula)
        formula = re.sub(r'^\s*=\s*', '', formula)
        out[p.stem] = formula
    return out


def load_template_tags(dirpath: Path) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    if not dirpath.exists():
        return out
    tag_re = re.compile(r"#[-\w]+")
    for p in sorted(dirpath.glob('*.md')):
        txt = p.read_text(encoding='utf-8')
        s = re.sub(r'(```|~~~).*?\1', '', txt, flags=re.S)
        tags = tag_re.findall(s)
        tags = [t.lower() for t in tags]
        seen: List[str] = []
        for t in tags:
            if t not in seen:
                seen.append(t)
        out[p.stem.lower()] = seen
    return out


# -------- sheet update helper --------
def update_sheet_rows(path: Path, updates: Dict[str, Any], verbose: bool = False) -> bool:
    """Update markdown table rows in `path`.
    updates: mapping stat_key -> value. Uses display_name_for(key).
    Returns True if the file changed.
    """
    try:
        txt = path.read_text(encoding='utf-8')
    except Exception:
        return False
    orig = txt
    for key, val in updates.items():
        dname = display_name_for(key)
        pat = re.compile(r"(\|\s*" + re.escape(dname) + r"\s*\|\s*)([^|\n]+)(\|)")
        txt, n = pat.subn(lambda m: m.group(1) + str(val) + ' ' + m.group(3), txt)
        if n == 0:
            # fallback to raw key
            d2 = key.replace('_', ' ').replace('.', ' ')
            pat2 = re.compile(r"(\|\s*" + re.escape(d2) + r"\s*\|\s*)([^|\n]+)(\|)", flags=re.I)
            txt, _ = pat2.subn(lambda m: m.group(1) + str(val) + ' ' + m.group(3), txt)
        if verbose and n:
            print(f'Updated {n} row(s) for {dname} in {path}')
    if txt != orig:
        path.write_text(txt, encoding='utf-8')
        return True
    return False


# -------- environmental / sheet parsing helpers --------
def _safe_rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except Exception:
        return str(p)


# Backwards-compatible aliases for older scripts
def scan_sheet_files(pcs_dir: Path) -> Dict[Path, float]:
    out: Dict[Path, float] = {}
    if not pcs_dir.exists():
        return out
    for p in pcs_dir.rglob('* character sheet.md'):
        try:
            out[p] = p.stat().st_mtime
        except Exception:
            continue
    return out


def _refresh_last_mtime_for_pc(pcs_dir: Path, last_mtimes: Dict[Path, float], pc_name: str) -> None:
    try:
        path = pcs_dir.joinpath(pc_name, f"{pc_name} character sheet.md")
        if path.exists():
            last_mtimes[path] = path.stat().st_mtime
    except Exception:
        pass


def _extract_show_if_condition_from_tags(tags: set) -> Optional[tuple]:
    return extract_show_if_condition_from_tags(tags)


def _is_in_environmental_folder(template_path: Path, vars_root: Path) -> bool:
    return is_in_environmental_folder(template_path, vars_root)


def _eval_expr_local(expr: str) -> Optional[float]:
    try:
        v = safe_eval(expr)
        if isinstance(v, (int, float)):
            return float(v)
        return None
    except Exception:
        return None


def _touch_or_update_dependent_files(changed_path: Path, vars_root: Path) -> None:
    # reuse helper logic from watch scripts: update files that reference changed variable
    try:
        display = changed_path.stem.replace('_', ' ')
        stem = changed_path.stem.lower()
        vars_map: Dict[str, float] = {}
        if vars_root.exists():
            for p in vars_root.rglob('*.md'):
                try:
                    t = p.read_text(encoding='utf-8')
                except Exception:
                    continue
                m = re.search(r'```markdown\n(.*?)\n\n', t, flags=re.S)
                if m:
                    s = m.group(1).strip()
                else:
                    lines = [l.strip() for l in t.splitlines() if l.strip() and not l.strip().startswith('#')]
                    s = lines[0] if lines else ''
                try:
                    mm = re.search(r'[-+]?[0-9]*\.?[0-9]+', s)
                    if mm:
                        vars_map[p.stem.lower()] = float(mm.group(0))
                except Exception:
                    continue
        for p in ROOT.rglob('*.md'):
            try:
                if vars_root in p.parents:
                    continue
            except Exception:
                pass
            try:
                txt = p.read_text(encoding='utf-8')
            except Exception:
                continue
            low = txt.lower()
            if display.lower() in low or stem in low or f'[[{display.lower()}]]' in low:
                lines = txt.splitlines()
                updated = False
                for idx, ln in enumerate(lines):
                    s = ln.strip()
                    if not s:
                        continue
                    if s.startswith('='):
                        expr = s.lstrip('=')
                        def sub_token(m):
                            raw = m.group(1).strip()
                            key = re.sub(r'[^A-Za-z0-9_\-]', '_', raw).lower()
                            v = vars_map.get(key)
                            if v is None:
                                if key.endswith('s') and key[:-1] in vars_map:
                                    v = vars_map.get(key[:-1])
                                elif (key + 's') in vars_map:
                                    v = vars_map.get(key + 's')
                            return str(v if v is not None else 0)
                        new_expr = re.sub(r"\[\[\s*([^\]]+)\s*\]\]", sub_token, expr)
                        val = _eval_expr_local(new_expr)
                        if val is not None:
                            lines[idx] = str(val)
                            updated = True
                        break
                    else:
                        break
                if updated:
                    try:
                        p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                        print('Updated computed file:', p.relative_to(ROOT))
                    except Exception:
                        pass
                else:
                    try:
                        p.write_text(txt, encoding='utf-8')
                        print('Touched dependent file:', p.relative_to(ROOT))
                    except Exception:
                        pass
    except Exception as e:
        print('Failed to update dependent files for', changed_path, e)


def load_environmental_templates(vars_dir: Path) -> Dict[str, Path]:
    """Return mapping normalized stem -> template path for files tagged as environmental variables."""
    out: Dict[str, Path] = {}
    tag_re = re.compile(r"#[-\w]+")
    if not vars_dir.exists():
        return out
    for p in vars_dir.rglob('*.md'):
        try:
            txt = p.read_text(encoding='utf-8')
        except Exception:
            continue
        tags = {t.lower() for t in tag_re.findall(txt)}
        if '#environmental_variable' in tags or '#environmental_variables' in tags:
            stem = p.stem.lower().replace(' ', '_')
            out[stem] = p
            if stem.endswith('s'):
                out[stem[:-1]] = p
            else:
                out[stem + 's'] = p
    return out


def parse_sheet_for_vars(sheet_path: Path) -> Dict[str, str]:
    res: Dict[str, str] = {}
    try:
        txt = sheet_path.read_text(encoding='utf-8')
    except Exception:
        return res
    for m in re.finditer(r"^\|\s*([^|]+?)\s*\|\s*([^|\n]+?)\s*\|", txt, flags=re.M):
        key = m.group(1).strip()
        val = m.group(2).strip()
        res[key.lower()] = val
    return res


def extract_show_if_condition_from_tags(tags: set) -> Optional[tuple]:
    for t in tags:
        if t.startswith('#show_if_'):
            body = t[len('#show_if_'):]
            m = re.match(r"([a-z]+)_ge_([0-9]+)$", body)
            if m:
                elem = m.group(1)
                try:
                    thresh = float(m.group(2))
                except Exception:
                    thresh = 0.0
                return (elem, 'ge', thresh)
    return None


def is_in_environmental_folder(template_path: Path, vars_root: Path) -> bool:
    try:
        rel = template_path.relative_to(vars_root)
        return 'environmental' in [p.lower() for p in rel.parts]
    except Exception:
        return False


def run_generator(script: Path, pc_name: str, create_placeholders: bool, dry_run: bool) -> None:
    import subprocess
    if dry_run:
        print('[DRY] would run generator for', pc_name, 'via', script)
        return
    try:
        print('Running generator for', pc_name)
        subprocess.run([sys.executable, str(script), '--pc', pc_name] + (['--create-placeholders'] if create_placeholders else []), check=False)
    except Exception as e:
        print('Generator call failed for', pc_name, e)


def pc_element_level(pc_dir: Path, element: str) -> float:
    safe = pc_dir.name
    vars_path = pc_dir.joinpath(f"{safe}_variables.md")
    if vars_path.exists():
        try:
            txt = vars_path.read_text(encoding='utf-8')
            for ln in txt.splitlines():
                m = re.match(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", ln)
                if m:
                    key = m.group(1).strip().lower().replace(' ', '_')
                    if key == element or key.endswith('_' + element) or key == element + '_level' or key == element + ' level':
                        try:
                            return float(re.sub(r'[^0-9.+-]', '', m.group(2).strip()) or 0)
                        except Exception:
                            return 0.0
        except Exception:
            pass
    sheet = pc_dir.joinpath(f"{safe} character sheet.md")
    if sheet.exists():
        try:
            txt = sheet.read_text(encoding='utf-8')
            pat = re.compile(r"^\|\s*" + re.escape(element.capitalize()) + r"\s*\|\s*([^|]+)\|", flags=re.M)
            m = pat.search(txt)
            if m:
                s = m.group(1).strip()
                try:
                    return float(re.sub(r'[^0-9.+-]', '', s) or 0)
                except Exception:
                    return 0.0
        except Exception:
            pass
    return 0.0


def pc_references_env(pc_dir: Path, cand: str, display_name: str) -> bool:
    safe = pc_dir.name
    vars_path = pc_dir.joinpath(f"{safe}_variables.md")
    try:
        if vars_path.exists():
            txt = vars_path.read_text(encoding='utf-8').lower()
            if display_name.lower() in txt:
                return True
            if cand.lower() in txt:
                return True
    except Exception:
        pass
    sheet = pc_dir.joinpath(f"{safe} character sheet.md")
    try:
        if sheet.exists():
            s = sheet.read_text(encoding='utf-8').lower()
            if display_name.lower() in s:
                return True
            short = cand.lower()
            if short.startswith('environmental_'):
                short = short[len('environmental_'):]
            if short in s:
                return True
    except Exception:
        pass
    return False
