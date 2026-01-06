#!/usr/bin/env python3
"""
Generate per-PC folders and variable files from the spreadsheet at
`Player Root/pc_primary_stats.md` and the templates in
`Player Root/variable/primary_stat` and `Player Root/variable/secondary_stat`.

Writes into `Player Root/PCs/<Name>/`:
 - `<Name>_variables.md` (table Variable | Value)
 - `<Name>_variable/` with per-template files named `<Name>_<template>.md`

This is intentionally small and self-contained so it can be rerun easily.
"""
from __future__ import annotations
from pathlib import Path
import re
import ast
from typing import Dict, List, Tuple, Any

try:
    from common import dedupe_variable_items
except Exception:
    # fallback when run as module
    from Mycelium.scripts.Python.common import dedupe_variable_items  # type: ignore

ROOT = Path('.').resolve()
INPUT_TABLE = ROOT.joinpath('Player Root', 'pc_primary_stats.md')
PRIMARY_TEMPLATES = ROOT.joinpath('Player Root', 'variable', 'primary_stat')
SECONDARY_TEMPLATES = ROOT.joinpath('Player Root', 'variable', 'secondary_stat')
OUT_ROOT = ROOT.joinpath('Player Root', 'PCs')


def parse_markdown_table(path: Path) -> Tuple[List[str], List[List[str]]]:
    """Parse a markdown table and return header + row data."""
    txt = path.read_text(encoding='utf-8')
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    if not lines:
        return [], []
    # find header line starting with | and separator line
    header_idx = None
    sep_idx = None
    for i, l in enumerate(lines):
        if l.startswith('|') and '|' in l:
            header_idx = i
            if i+1 < len(lines) and re.match(r'^\|?\s*:-+', lines[i+1]):
                sep_idx = i+1
            else:
                # look for typical separator with dashes
                for j in range(i+1, min(i+4, len(lines))):
                    if re.match(r'^\|?\s*-', lines[j]):
                        sep_idx = j
                        break
            break
    if header_idx is None:
        return [], []
    header = [h.strip() for h in lines[header_idx].strip('|').split('|')]
    data = []
    for l in lines[sep_idx+1:]:
        if not l.startswith('|'):
            continue
        row = [c.strip() for c in l.strip('|').split('|')]
        if len(row) < 2:
            continue
        data.append(row)
    return header, data


def name_from_cell(cell: str) -> str:
    """Extract a PC name from a wikilink cell or plain string."""
    # cell like [[Anju]] or Anju
    m = re.search(r"\[\[([^\]]+)\]\]", cell)
    if m:
        return m.group(1).strip()
    return cell.strip()


def to_number(s: str) -> Any:
    """Convert a string to int/float when possible, otherwise return 0."""
    if s is None:
        return 0
    s = str(s).strip()
    if s == '':
        return 0
    # remove commas
    s = s.replace(',', '')
    try:
        if '.' in s:
            return float(s)
        return int(s)
    except Exception:
        # try to extract leading number
        m = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
        if m:
            return float(m.group(0)) if '.' in m.group(0) else int(m.group(0))
    return 0


# safe evaluator using ast
_allowed_binops = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
}
_allowed_unary = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}


def safe_eval(expr: str) -> Any:
    """Evaluate simple numeric expressions safely."""
    expr = expr.strip()
    if expr == '':
        return 0
    try:
        node = ast.parse(expr, mode='eval')
    except Exception:
        return expr

    def _eval(n):
        """Evaluate a limited AST node to avoid arbitrary code execution."""
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Num):
            return n.n
        if isinstance(n, ast.BinOp):
            op = type(n.op)
            if op not in _allowed_binops:
                raise ValueError('unsupported op')
            left = _eval(n.left)
            right = _eval(n.right)
            return _allowed_binops[op](left, right)
        if isinstance(n, ast.UnaryOp):
            op = type(n.op)
            if op not in _allowed_unary:
                raise ValueError('unsupported unary')
            return _allowed_unary[op](_eval(n.operand))
        if isinstance(n, ast.Call):
            raise ValueError('calls not allowed')
        # names not allowed
        raise ValueError('unsupported expression')

    try:
        return _eval(node)
    except Exception:
        return expr


def load_secondary_templates(dirpath: Path) -> Dict[str, str]:
    """Load secondary stat formulas from markdown templates."""
    templates = {}
    if not dirpath.exists():
        return templates
    for p in dirpath.glob('*.md'):
        txt = p.read_text(encoding='utf-8')
        s = re.sub(r'(```|~~~).*?\1', '', txt, flags=re.S)
        if '#secondary_stat' not in s:
            continue
        # take first non-empty non-tag line as formula block, otherwise whole file
        lines = [l for l in s.splitlines() if l.strip() and not l.strip().startswith('#')]
        formula = lines[0].strip() if lines else ''
        templates[p.stem] = formula
    return templates


def load_primary_template_names(dirpath: Path) -> List[str]:
    """List the stem names for all primary stat templates."""
    if not dirpath.exists():
        return []
    return [p.stem for p in dirpath.glob('*.md')]


def compute_secondaries(kv: Dict[str, Any], templates: Dict[str, str]) -> Dict[str, Any]:
    """Iteratively compute secondary stats using template formulas."""
    kv_local = {k.lower(): v for k, v in kv.items()}
    # iterative passes
    for _ in range(6):
        changed = False
        for name, formula in templates.items():
            key = name.lower()
            # substitute placeholders [[x]] case-insensitively
            def sub(m):
                """Replace placeholders with the current numeric value."""
                token = m.group(1).strip().lower()
                # map spaces/dots/underscores
                token_key = token
                return str(kv_local.get(token_key, 0))
            expr = re.sub(r"\[\[\s*([^\]]+)\s*\]\]", sub, formula)
            val = safe_eval(expr)
            if isinstance(val, (int, float)):
                if kv_local.get(key) != val:
                    kv_local[key] = val
                    changed = True
            else:
                # non-numeric: store raw string
                if kv_local.get(key) != val:
                    kv_local[key] = val
                    changed = True
        if not changed:
            break
    return kv_local


def write_character_files(name: str, kv_all: Dict[str, Any], primary_names: List[str], secondary_templates: Dict[str, str], out_root: Path) -> None:
    """Write variable markdown files for a single PC."""
    safe_name = re.sub(r"[^A-Za-z0-9_\-]", '_', name)
    pc_dir = out_root.joinpath(safe_name)
    pc_dir.mkdir(parents=True, exist_ok=True)
    # variables file
    vars_path = pc_dir.joinpath(f"{safe_name}_variables.md")
    lines = ["| Variable | Value |", "|---|---:|"]
    for display_key, value in dedupe_variable_items(kv_all):
        lines.append(f"| {display_key} | {value} |")
    vars_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    # per-stat mirrored folder
    mirror = pc_dir.joinpath(f"{safe_name}_variable")
    mirror.mkdir(parents=True, exist_ok=True)
    # primary templates -> write numeric or 0
    for p in primary_names:
        val = kv_all.get(p.lower(), 0)
        path = mirror.joinpath(f"{safe_name}_{p}.md")
        path.write_text(str(val) + '\n', encoding='utf-8')
    # secondary templates
    for p, formula in secondary_templates.items():
        val = kv_all.get(p.lower(), '')
        path = mirror.joinpath(f"{safe_name}_{p}.md")
        path.write_text(str(val) + '\n', encoding='utf-8')


def main():
    """Generate per-PC variables and mirrored files from pc_primary_stats.md."""
    header, rows = parse_markdown_table(INPUT_TABLE)
    if not header or not rows:
        print('No table found at', INPUT_TABLE)
        return
    # normalize header names
    hdr_norm = [h.lower().strip() for h in header]
    # mapping header titles to keys we want
    # look for 'manually rolled hp' -> rolled.hp
    primary_names = load_primary_template_names(PRIMARY_TEMPLATES)
    secondary_templates = load_secondary_templates(SECONDARY_TEMPLATES)

    pcs = []
    for r in rows:
        # pad row
        if len(r) < len(hdr_norm):
            r += [''] * (len(hdr_norm) - len(r))
        data = dict(zip(hdr_norm, r))
        name = name_from_cell(data.get('name', 'Unknown'))
        run_update = data.get('run update', '').lower()
        if run_update and run_update not in ('yes', 'y', 'true'):
            continue
        kv = {}
        # map common headers
        for k, v in data.items():
            key = k.replace(' ', '.').replace('/', '.').lower()
            if key == 'name' or key == 'run.update':
                continue
            if 'manually' in key and 'hp' in key:
                key = 'rolled.hp'
            # simplify Water/Earth/Air etc to lowercase keys
            key = key.replace('\u00A0', ' ')
            kv[key] = to_number(v)
        # also flatten common primary stat names to simple keys
        # ensure common keys exist (con, str, dex, int, wis, cha)
        for s in ['str','dex','con','int','wis','cha','water','earth','air','fire','spirit','rolled.hp']:
            kv.setdefault(s, 0)
        # compute secondaries
        kv_all = compute_secondaries(kv, secondary_templates)
        # merge numeric originals (lowercased)
        for kk, vv in kv.items():
            kv_all.setdefault(kk.lower(), vv)
        pcs.append((name, kv_all))

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    for name, kv_all in pcs:
        write_character_files(name, kv_all, primary_names, secondary_templates, OUT_ROOT)
        print('Wrote', name)


if __name__ == '__main__':
    main()
