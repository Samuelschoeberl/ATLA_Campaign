#!/usr/bin/env python3
"""generate_secondary_stats.py

Enhanced generator for secondary stats.

Configuration: this script reads default paths from `system_state.md`.
Values that reference files may be written in Obsidian-parsable form as
`#file:<path>`; the loader normalizes these to the underlying path.

- Loads formulas from `char_formulas.json` (falls back to defaults).
- Uses a small AST-based SafeEval for safer expression evaluation.
- Extracts Bending Levels, CL and HP_PER_CL if present in the Character Sheet
    or Autogen Report.
- Can run for a single PC (--pc) or all PCs using the configured `pcs_input`.
"""
from __future__ import annotations
from pathlib import Path
import re
import argparse
import math
import ast
import json
from typing import Dict, Any, List
import os as _os
try:
    from config_loader import get_config
except Exception:
    def get_config(key, default):
        return default

# Debug toggle
PCS_DEBUG = bool(_os.environ.get('PCS_DEBUG'))

DEFAULT_FORMULAS = {
    "Max Hit Points": "10 + CON * 2",
    "Evasion": "10 + DEX",
    "Armor": "10 + int(CON/2)",
}


class SafeEval(ast.NodeVisitor):
    """Minimal AST evaluator allowing arithmetic, names and whitelisted calls."""

    ALLOWED_FUNCS = {'int': int, 'max': max, 'min': min, 'abs': abs, 'floor': math.floor, 'ceil': math.ceil}

    def __init__(self, names: Dict[str, Any]):
        self.names = names

    def visit(self, node):
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        if isinstance(node, ast.BinOp):
            left = self.visit(node.left)
            right = self.visit(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.FloorDiv):
                return left // right
            if isinstance(node.op, ast.Mod):
                return left % right
            if isinstance(node.op, ast.Pow):
                return left ** right
            raise ValueError(f"Unsupported binary op: {type(node.op)}")
        if isinstance(node, ast.UnaryOp):
            val = self.visit(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +val
            if isinstance(node.op, ast.USub):
                return -val
            raise ValueError("Unsupported unary op")
        # numeric / constant literal
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return self.names.get(node.id, 0)
        if isinstance(node, ast.Call):
            # allow simple names or math.floor/ceil
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in self.ALLOWED_FUNCS:
                    func = self.ALLOWED_FUNCS[func_name]
                    args = [self.visit(a) for a in node.args]
                    return func(*args)
            if isinstance(node.func, ast.Attribute):
                # allow math.floor / math.ceil
                val = self.visit(node.func.value)
                if node.func.value and isinstance(node.func.value, ast.Name) and node.func.value.id == 'math':
                    attr = node.func.attr
                    if attr in ('floor', 'ceil'):
                        func = getattr(math, attr)
                        args = [self.visit(a) for a in node.args]
                        return func(*args)
            raise ValueError("Call to disallowed function")
        if isinstance(node, ast.Attribute):
            # allow math.x as a name reference by returning a dummy (handled in Call)
            if isinstance(node.value, ast.Name) and node.value.id == 'math':
                return math
            raise ValueError("Attribute access not allowed")
        if isinstance(node, ast.Tuple):
            return tuple(self.visit(elt) for elt in node.elts)
        raise ValueError(f"Unsupported expression node: {type(node)}")


def safe_eval_expr(expr: str, names: Dict[str, Any]) -> Any:
    try:
        node = ast.parse(expr, mode='eval')
        return SafeEval(names).visit(node)
    except Exception as e:
        raise


def find_character_file(pc: str) -> Path | None:
    # Prefer a 'PC Character Sheets' folder anywhere under the repo if present
    base = Path(__file__).resolve().parent
    try:
        for d in base.rglob('PC Character Sheets'):
            if d.is_dir():
                p1 = d.joinpath('PCs') if (d.joinpath('PCs')).exists() else d
                candidates = [p1 / pc / 'Character Sheet.md', p1 / pc / f"{pc} Character Sheet.md"]
                for p in candidates:
                    if p.exists():
                        return p
    except Exception:
        pass
    # Fallback to legacy locations
    candidates = []
    pcs_root = Path(get_config('pcs_root', 'Players Part/PCs'))
    candidates.append(pcs_root / pc / "Character Sheet.md")
    candidates.append(pcs_root / pc / f"{pc} Character Sheet.md")
    candidates.append(Path(f"{pc} Character Sheet.md"))
    for p in candidates:
        if p.exists():
            return p
    return None


def parse_pcs_input_row(pc_name: str, pcs_path: Path | None = None) -> Dict[str, Any]:
    if pcs_path is None:
        pcs_path = Path(get_config('pcs_input', 'pcs_input.md'))
    if not pcs_path.exists():
        return {}
    txt = pcs_path.read_text(encoding='utf-8')
    lines = [ln for ln in txt.splitlines() if ln.strip()]
    header_idx = None
    for i, ln in enumerate(lines):
        if 'name' in ln.lower() and '|' in ln:
            header_idx = i
            break
    if header_idx is None:
        for i, ln in enumerate(lines):
            if ln.strip().startswith('|'):
                header_idx = i
                break
    if header_idx is None:
        return {}
    header_parts = [p.strip() for p in lines[header_idx].strip().strip('|').split('|')]
    norm_headers = [re.sub(r'[^A-Za-z0-9_]+', ' ', h).strip().lower() for h in header_parts]

    def find_col(*cands):
        for cand in cands:
            cand = cand.lower()
            for idx, h in enumerate(norm_headers):
                if cand in h:
                    return idx
        return None

    idx_name = find_col('name')
    idx_str = find_col('str', 'strength')
    idx_dex = find_col('dex', 'dexterity')
    idx_con = find_col('con', 'constitution')
    idx_int = find_col('int', 'intelligence')
    idx_wis = find_col('wis', 'wisdom')
    idx_cha = find_col('cha', 'charisma')
    idx_water = find_col('water')
    idx_earth = find_col('earth')
    idx_air = find_col('air')
    idx_fire = find_col('fire')
    idx_spirit = find_col('spirit')

    data_start = header_idx + 1
    if data_start < len(lines) and re.match(r"^\s*\|?\s*[-:]+", lines[data_start]):
        data_start += 1

    for ln in lines[data_start:]:
        if not ln.strip().startswith('|'):
            break
        parts = [p.strip() for p in ln.strip().strip('|').split('|')]
        if PCS_DEBUG:
            print(f"[pcs-debug] parse_pcs_input_row parts={parts}")
        if idx_name is None or idx_name >= len(parts):
            continue
        name = parts[idx_name]
        if PCS_DEBUG:
            print(f"[pcs-debug] parse_pcs_input_row name='{name}' (looking for '{pc_name}')")
        if not name:
            continue

        def get_int_at(idx):
            if idx is None or idx >= len(parts):
                return 0
            raw = parts[idx].strip()
            m = re.search(r"(-?\d+)", raw)
            if not m:
                return 0
            try:
                return int(m.group(1))
            except Exception:
                return 0

        if name.lower() != pc_name.lower():
            continue

        return {
            'name': name,
            'STR': get_int_at(idx_str),
            'DEX': get_int_at(idx_dex),
            'CON': get_int_at(idx_con),
            'INT': get_int_at(idx_int),
            'WIS': get_int_at(idx_wis),
            'CHA': get_int_at(idx_cha),
            'Water': get_int_at(idx_water),
            'Earth': get_int_at(idx_earth),
            'Air': get_int_at(idx_air),
            'Fire': get_int_at(idx_fire),
            'Spirit': get_int_at(idx_spirit),
        }
    return {}


def list_all_pcs(pcs_path: Path | None = None) -> List[str]:
    if pcs_path is None:
        pcs_path = Path(get_config('pcs_input', 'pcs_input.md'))
    if not pcs_path.exists():
        return []
    txt = pcs_path.read_text(encoding='utf-8')
    lines = [ln for ln in txt.splitlines() if ln.strip()]
    header_idx = None
    for i, ln in enumerate(lines):
        if 'name' in ln.lower() and '|' in ln:
            header_idx = i
            break
    if header_idx is None:
        for i, ln in enumerate(lines):
            if ln.strip().startswith('|'):
                header_idx = i
                break
    if header_idx is None:
        return []
    header_parts = [p.strip() for p in lines[header_idx].strip().strip('|').split('|')]
    norm_headers = [re.sub(r'[^A-Za-z0-9_]+', ' ', h).strip().lower() for h in header_parts]

    def find_col(*cands):
        for cand in cands:
            cand = cand.lower()
            for idx, h in enumerate(norm_headers):
                if cand in h:
                    return idx
        return None

    idx_name = find_col('name')
    data_start = header_idx + 1
    if data_start < len(lines) and re.match(r"^\s*\|?\s*[-:]+", lines[data_start]):
        data_start += 1
    res: List[str] = []
    for ln in lines[data_start:]:
        if not ln.strip().startswith('|'):
            break
        parts = [p.strip() for p in ln.strip().strip('|').split('|')]
        if PCS_DEBUG:
            print(f"[pcs-debug] list_all_pcs parts={parts}")
        if idx_name is None or idx_name >= len(parts):
            continue
        name = parts[idx_name]
        if not name:
            continue
        # ignore separator rows that are only dashes
        if re.fullmatch(r"-+", name):
            if PCS_DEBUG:
                print(f"[pcs-debug] list_all_pcs skipping dash-only name: '{name}'")
            continue
        res.append(name)
    return res


def extract_current_hitpoints(character_path: Path) -> int | None:
    try:
        txt = character_path.read_text(encoding='utf-8')
    except Exception:
        return None
    for ln in txt.splitlines():
        m = re.match(r"^\s*\|\s*(?:Current Hit Points|Current HP|Current Hitpoints|Current Hit Points)\s*\|\s*([0-9]+)", ln, re.I)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
    m2 = re.search(r'(?i)current[^0-9]{0,10}(\d{1,4})', txt if 'txt' in locals() else '')
    if m2:
        try:
            return int(m2.group(1))
        except Exception:
            return None
    return None


def parse_bending_levels(character_path: Path) -> Dict[str, int]:
    levels: Dict[str, int] = {}
    try:
        txt = character_path.read_text(encoding='utf-8')
    except Exception:
        return levels
    lines = txt.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.strip().lower().startswith('## bending levels'):
            start = i + 1
            break
    if start is None:
        return levels
    # gather table rows
    for i in range(start, len(lines)):
        ln = lines[i].strip()
        if ln == '' or ln.startswith('##'):
            break
        if '|' not in ln:
            continue
        parts = [p.strip() for p in ln.strip().strip('|').split('|')]
        if len(parts) >= 2:
            elem = parts[0]
            val = parts[1]
            # normalize name
            key = re.sub(r'(?i)bending', '', elem).strip()
            key = re.sub(r'(?i)\s*level\s*$', '', key).strip()
            if not key:
                continue
            try:
                n = int(val)
            except Exception:
                n = 0
            levels[f"{key} Level"] = n
    return levels


def parse_autogen_report_inferred(character_path: Path) -> Dict[str, int]:
    res: Dict[str, int] = {}
    try:
        txt = character_path.read_text(encoding='utf-8')
    except Exception:
        return res
    lines = txt.splitlines()
    start_idx = None
    for i, ln in enumerate(lines):
        if ln.strip().lower().startswith('## autogen report'):
            start_idx = i
            break
    if start_idx is None:
        return res
    # find '### Inferred values'
    inf_idx = None
    for j in range(start_idx + 1, len(lines)):
        if lines[j].strip().lower().startswith('### inferred'):
            inf_idx = j
            break
    if inf_idx is None:
        return res
    for k in range(inf_idx + 1, len(lines)):
        ln = lines[k].strip()
        if not ln or ln.startswith('###') or ln.startswith('##'):
            break
        m = re.match(r"[-*]\s*([^:]+):\s*(\d+)", ln)
        if m:
            label = m.group(1).strip()
            val = int(m.group(2))
            res[label] = val
    return res


def load_formulas(path: Path | None = None) -> Dict[str, tuple[str, str]]:
    """Load formulas and return mapping human_label -> (expr, source_key).

    The source_key is the original JSON key (e.g. 'max_hit_points'). The
    human label is used when matching table labels in character sheets.
    """
    formulas: Dict[str, tuple[str, str]] = {}
    # include defaults (use human-label as key, source_key same as label)
    for k, v in DEFAULT_FORMULAS.items():
        formulas[k] = (v, k)
    # Prefer formulas specified in markdown table `secondary_stat_formula.md` if present
    # Resolve formulas path from config if path not provided
    if path is None:
        path = Path(get_config('char_formulas', 'char_formulas.json'))
    mdpath = Path('secondary_stat_formula.md')
    if mdpath.exists():
        try:
            txt = mdpath.read_text(encoding='utf-8')
            # find table header
            lines = txt.splitlines()
            start = None
            for i, ln in enumerate(lines):
                if ln.strip().lower().startswith('## secondary stat formulas'):
                    start = i
                    break
            # fallback: scan whole file for first two-column table
            if start is None:
                start = 0
            # parse table rows after header or from top
            for ln in lines[start:]:
                if '|' not in ln:
                    continue
                parts = [p.strip() for p in ln.strip().strip('|').split('|')]
                if len(parts) < 2:
                    continue
                key = parts[0]
                expr = parts[1]
                if not key or key.lower().startswith('stat') or key.lower().startswith('---'):
                    continue
                # determine source key (use safe underscored lower)
                src = key.replace(' ', '_')
                formulas[key] = (expr, src)
        except Exception:
            pass
    elif path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            for k, v in data.items():
                if not isinstance(k, str):
                    continue
                # determine human label for the key
                if '_' in k:
                    label = k.replace('_', ' ').title()
                else:
                    label = k.title()
                if isinstance(v, str) and v.strip():
                    formulas[label] = (v, k)
        except Exception:
            pass
    return formulas


def compute_secondary(stats: Dict[str, int], formulas: Dict[str, tuple[str, str]], extra_vars: Dict[str, int] | None = None) -> Dict[str, int]:
    env: Dict[str, Any] = {k: v for k, v in stats.items()}
    # allow lowercase and underscore variants
    for k, v in list(stats.items()):
        env[k.lower()] = v
        env[k.upper()] = v
    if extra_vars:
        for k, v in extra_vars.items():
            env[k] = v
            env[k.replace(' ', '_')] = v
            env[k.lower()] = v
    env['math'] = math

    results: Dict[str, int] = {}
    for label, (expr, source_key) in formulas.items():
        try:
            val = safe_eval_expr(expr, env)
            results[label] = int(val)
        except Exception:
            results[label] = 0
    return results


def write_secondary_file(pc: str, dest: Path, derived: Dict[str, int], current_hp: int | None, bending: Dict[str, int], inferred: Dict[str, int], formulas: Dict[str, tuple[str, str]] | None = None, pcs_row: Dict[str, int] | None = None):
    lines: List[str] = []
    lines.append(f"# {pc} — Secondary Stats")
    lines.append("")
    lines.append("| Stat | Value | Formula |")
    lines.append("| --- | ---: | --- |")
    if current_hp is not None:
        formula_expr = ''
        if formulas and 'Current Hit Points' in formulas:
            formula_expr = formulas['Current Hit Points'][0]
        lines.append(f"| Current Hit Points | {current_hp} | {formula_expr} |")
    # include inferred values (CL, HP_PER_CL, Element Level, etc.)
    for k, v in inferred.items():
        formula_expr = ''
        if formulas and k in formulas:
            formula_expr = formulas[k][0]
        lines.append(f"| {k} | {v} | {formula_expr} |")
    # include any numeric fields coming from pcs_input.md that aren't core stats
    if pcs_row:
        # keys to skip: primary stats and element names already represented
        skip_keys = {"STR","DEX","CON","INT","WIS","CHA","Strength","Dexterity","Constitution","Intelligence","Wisdom","Charisma","Water","Earth","Air","Fire","Spirit","name","Name"}
        extras = []
        for k, v in pcs_row.items():
            if not k or k in skip_keys:
                continue
            # only include numeric fields
            try:
                n = int(v)
            except Exception:
                continue
            # avoid duplicates with inferred/bending/derived
            if k in inferred or k in bending or k in derived:
                continue
            extras.append((k, n))
        if extras:
            lines.append('')
            lines.append('## Values from pcs_input.md')
            lines.append('| Field | Value | Formula |')
            lines.append('| --- | ---: | --- |')
            for k, n in extras:
                formula_expr = ''
                if formulas and k in formulas:
                    formula_expr = formulas[k][0]
                lines.append(f"| {k} | {n} | {formula_expr} |")
    # include bending levels
    for k, v in bending.items():
        formula_expr = ''
        if formulas and k in formulas:
            formula_expr = formulas[k][0]
        lines.append(f"| {k} | {v} | {formula_expr} |")
    # include computed derived values and show formula
    for k, v in derived.items():
        formula_expr = ''
        if formulas and k in formulas:
            formula_expr = formulas[k][0]
        lines.append(f"| {k} | {v} | {formula_expr} |")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def process_pc(pc: str, formulas: Dict[str, tuple[str, str]]):
    pcs_row = parse_pcs_input_row(pc)
    if not pcs_row:
        print(f"No row for PC '{pc}' found in pcs_input.md")
    # normalize expected stat keys
    stats: Dict[str, int] = {}
    for name in ('STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA'):
        val = 0
        # direct key
        if name in pcs_row and isinstance(pcs_row[name], int):
            val = pcs_row[name]
        else:
            for k in pcs_row:
                if isinstance(k, str) and k.strip().upper() == name:
                    try:
                        val = int(pcs_row[k])
                    except Exception:
                        val = 0
                    break
        stats[name] = val

    char_path = find_character_file(pc)
    current_hp = None
    bending = {}
    inferred = {}
    if char_path:
        current_hp = extract_current_hitpoints(char_path)
    # Parse bending levels from the sheet, but prefer pcs_input.md when
    # a row exists for this PC. pcs_input.md is authoritative for
    # primary stats and element levels.
    bending = {}
    inferred = {}
    if char_path:
        bending = parse_bending_levels(char_path)
        inferred = parse_autogen_report_inferred(char_path)
    try:
        pcs_row = parse_pcs_input_row(pc)
    except Exception:
        pcs_row = {}
    if pcs_row:
        # Override bending levels from pcs_input.md unconditionally when a
        # pcs_input.md row exists for this PC. Use provided values (including 0).
        try:
            b_override = {}
            for el in ('Water', 'Earth', 'Air', 'Fire', 'Spirit'):
                # accept presence even if zero
                if el in pcs_row:
                    try:
                        b_override[f"{el} Level"] = int(pcs_row.get(el, 0))
                    except Exception:
                        b_override[f"{el} Level"] = 0
            # assign (allow empty dict to leave previous parsing if no keys present)
            if b_override:
                bending = b_override
        except Exception:
            pass
        # Also prefer core stats from pcs_input.md unconditionally when rows exist
        try:
            for k in ('STR','DEX','CON','INT','WIS','CHA'):
                if k in pcs_row:
                    try:
                        stats[k] = int(pcs_row.get(k, stats.get(k,0)))
                    except Exception:
                        stats[k] = int(stats.get(k, 0))
        except Exception:
            pass

    # If CL or HP_PER_CL missing, try to infer from pcs_input 'Manually Rolled HP'
    if 'CL' not in inferred:
        # heuristics: CL is highest bending level
        if bending:
            inferred['CL'] = max(bending.values())
    if 'HP_PER_CL' not in inferred:
        # default HP per CL if not present
        inferred['HP_PER_CL'] = inferred.get('HP_PER_CL', 0)

    derived = compute_secondary(stats, formulas, extra_vars=inferred)

    out_root = Path(get_config('secondary_stats', 'Players Part/PCs'))
    out_candidate = out_root / pc / f"{pc} secondary stats.md"
    if char_path and out_candidate.parent.exists():
        out_path = out_candidate
    else:
        out_path = Path(f"{pc} secondary stats.md")

    write_secondary_file(pc, out_path, derived, current_hp, bending, inferred, formulas=formulas, pcs_row=pcs_row)
    print(f"Wrote secondary stats for {pc} -> {out_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--pc', help='PC name (e.g. Anju)')
    p.add_argument('--all', action='store_true', help='Generate for all PCs in pcs_input.md')
    default_formulas = get_config('char_formulas', 'char_formulas.json')
    p.add_argument('--formulas', default=default_formulas, help='Path to formulas JSON')
    args = p.parse_args()

    formulas = load_formulas(Path(args.formulas))

    if args.all:
        pcs = list_all_pcs()
        for pc in pcs:
            process_pc(pc, formulas)
        return

    if not args.pc:
        print('Please pass --pc NAME or --all')
        return

    process_pc(args.pc, formulas)


if __name__ == '__main__':
    main()
