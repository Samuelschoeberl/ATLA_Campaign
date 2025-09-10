#!/usr/bin/env python3
"""update_char.py

Ready-to-copy example commands
```bash
# Update Anju by PC folder discovery
python3 update_char.py --pc Anju

# Update a specific Character Sheet file path
python3 update_char.py --file "/path/to/Anju Character Sheet.md"

# Use a custom formulas file and extend it with defaults if needed
python3 update_char.py --pc Anju --formulas my_formulas.json --extend-formulas
```

Read a Character Sheet markdown file, compute derived stats from the Core Stats
table, and update the Vital Stats table in-place.

Usage examples:
    python3 update_char.py --pc Anju
    python3 update_char.py --file "/path/to/Character Sheet.md"

The script looks for a `Character Sheet.md` in a player folder under
`Players Part/PCs/<PC>/Character Sheet.md` or for a file named
"<PC> Character Sheet.md" in the current directory.

Formulas are configurable in `char_formulas.json` (created with defaults).
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import sys
import ast
import subprocess
from datetime import datetime
from typing import Dict, Any


DEFAULT_FORMULAS = {
    "max_hit_points": "10 + CON * 2",
    "evasion": "10 + DEX",
    "armor": "10 + int(CON/2)",
}

# Mapping from common table labels to formula keys
SIMPLE_MAP = {
    'Max Hit Points': 'max_hit_points',
    'Max Hitpoints': 'max_hit_points',
    'Max HP': 'max_hit_points',
    'Evasion': 'evasion',
    'Armor': 'armor',
    'Stress': 'Stress Level',
    'Current Hit Points': 'Current Hit Points',
    'Attack Roll Modifier': 'attack_roll_modifier',
    'Water DC': 'waterbending_dc',
    'Earth DC': 'earthbending_dc',
    'Fire DC': 'firebending_dc',
    'Air DC': 'airbending_dc',
    'Spirit DC': 'spiritbending_dc',
}


def find_character_file(pc: str | None, file_arg: str | None) -> Path | None:
    # If explicit file provided, use that
    if file_arg:
        p = Path(file_arg).expanduser().resolve()
        return p if p.exists() else None

    # If --pc provided, try common locations
    if pc:
        candidates = []
        # Players Part/PCs/<PC>/Character Sheet.md
        candidates.append(Path("Players Part/PCs") / pc / "Character Sheet.md")
        # Players Part/PCs/<PC>/<pc> Character Sheet.md
        candidates.append(Path("Players Part/PCs") / pc / f"{pc} Character Sheet.md")
        # Current dir: <pc> Character Sheet.md
        candidates.append(Path(f"{pc} Character Sheet.md"))
        for c in candidates:
            if c.exists():
                return c.resolve()
    return None


def parse_table_block(lines: list[str], start_idx: int) -> tuple[int, list[str]]:
    """Given lines and index at header line (like '## Core Stats'), return the
    index of the line after the table and the table lines (including header).
    """
    table_lines: list[str] = []
    i = start_idx
    # move forward until we hit a header or blank line after we've seen at least
    # one '|' table row.
    seen_row = False
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('## ') and seen_row:
            break
        if line.strip() == '' and seen_row:
            # blank line after table
            i += 1
            break
        if '|' in line:
            # table row
            table_lines.append(line)
            seen_row = True
        else:
            if seen_row:
                # ended table
                break
            # else skip non-table lines until table begins
        i += 1
    return i, table_lines


def parse_stats_from_core(table_lines: list[str]) -> Dict[str, int]:
    """Parse the Core Stats table and return a mapping of STAT -> int value.

    Accepts stat names like Strength, Dexterity, etc.
    """
    stats: Dict[str, int] = {}
    for row in table_lines:
        # basic row match: | Name | Value |
        m = re.match(r"\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|", row)
        if not m:
            continue
        name = m.group(1).strip()
        val = m.group(2).strip()
        # normalize name
        key = name.lower().strip()
        # map to short codes
        code_map = {
            'strength': 'STR',
            'dexterity': 'DEX',
            'constitution': 'CON',
            'intelligence': 'INT',
            'wisdom': 'WIS',
            'charisma': 'CHA',
        }
        if key in code_map:
            try:
                n = int(val)
            except Exception:
                try:
                    n = int(float(val))
                except Exception:
                    n = 0
            stats[code_map[key]] = n
    # ensure all keys present
    for k in ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']:
        stats.setdefault(k, 0)
    return stats


def parse_bending_levels(lines: list[str], start_idx: int) -> Dict[str, int]:
    """Parse the Bending Levels table under '## Bending Levels' and return mapping like
    {'Air Level': 1, 'Water Level': 2, ...}
    """
    i, table_lines = parse_table_block(lines, start_idx)
    levels: Dict[str, int] = {}
    # Expect header like: | Element | Level | Notes |
    for row in table_lines:
        m = re.match(r"\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|", row)
        if not m:
            continue
        elem = m.group(1).strip()
        val = m.group(2).strip()
        if not elem:
            continue
        # strip Obsidian wikilink markup [[Name]] or [[Page|Label]] -> Label
        if elem.startswith('[[') and elem.endswith(']]'):
            inner = elem[2:-2]
            if '|' in inner:
                elem = inner.split('|', 1)[1].strip()
            else:
                elem = inner.strip()
        # normalize names like 'Airbending' or 'Airbending Level' -> 'Air Level'
        # remove the substring 'bending' and ensure a single 'Level' suffix
        elem = re.sub(r'(?i)bending', '', elem).strip()
        # remove duplicate 'Level' words
        elem = re.sub(r'(?i)\s*level\s*$', '', elem).strip()
        if elem:
            key = f"{elem} Level"
        else:
            continue
        try:
            n = int(val)
        except Exception:
            try:
                n = int(float(val))
            except Exception:
                n = 0
        levels[key] = n
    return levels


def parse_generic_table(table_lines: list[str]) -> Dict[str, int]:
    """Parse a generic two-column markdown table and return mapping of label -> int value."""
    mapping: Dict[str, int] = {}
    for row in table_lines:
        m = re.match(r"\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|", row)
        if not m:
            continue
        label = m.group(1).strip()
        # strip Obsidian wikilink markup [[Name]] or [[Page|Label]] -> Label
        if label.startswith('[[') and label.endswith(']]'):
            inner = label[2:-2]
            if '|' in inner:
                label = inner.split('|', 1)[1].strip()
            else:
                label = inner.strip()
        val = m.group(2).strip()
        try:
            n = int(val)
        except Exception:
            try:
                n = int(float(val))
            except Exception:
                n = 0
        mapping[label] = n
    return mapping


def parse_manually_rolled_hp(lines: list[str], start_idx: int) -> list[tuple[int, str, int]]:
    """Parse the Manually Rolled Hitpoints table and return list of (level, element, rolled)"""
    i, table_lines = parse_table_block(lines, start_idx)
    res: list[tuple[int, str, int]] = []
    for row in table_lines:
        # match | level | element | rolled |
        m = re.match(r"\s*\|\s*(\d+)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|", row)
        if not m:
            continue
        try:
            lvl = int(m.group(1).strip())
        except Exception:
            continue
        elem = m.group(2).strip()
        try:
            rolled = int(m.group(3).strip())
        except Exception:
            rolled = 0
        res.append((lvl, elem, rolled))
    return res


def parse_manual_overrides(lines: list[str]) -> Dict[str, int]:
    """Scan all markdown table rows and return a mapping of label -> value for
    rows where the last meaningful column indicates the value is NOT
    automatically updated (e.g., 'N', 'no').

    The function is tolerant of tables with more than two columns. It strips
    Obsidian wiki links like [[Label|Text]] -> Text when building keys.
    """
    overrides: Dict[str, int] = {}
    for row in lines:
        if '|' not in row:
            continue
        parts = [p.strip() for p in row.split('|')]
        # skip rows that don't have at least a label and a value
        if len(parts) < 3:
            continue
        # parts example: ['', ' Label ', ' Value ', ' note ', ' N ', '']
        # label is parts[1], value is parts[2], possible auto flag is parts[-2]
        label = parts[1]
        val = parts[2]
        # skip separator rows like | --- | --- |
        if re.fullmatch(r"-+", label) or re.fullmatch(r"-+", val):
            continue
        auto_flag = None
        if len(parts) >= 5:
            auto_flag = parts[-2]
        if not auto_flag:
            continue
        if auto_flag.strip().lower() in ('n', 'no', 'false'):
            # try parse numeric value
            try:
                n = int(val)
            except Exception:
                try:
                    n = int(float(val))
                except Exception:
                    # non-numeric manual value -> skip
                    continue
            # strip wiki link markup if present
            kk = label
            if kk.startswith('[[') and kk.endswith(']]'):
                inner = kk[2:-2]
                if '|' in inner:
                    kk = inner.split('|', 1)[1].strip()
                else:
                    kk = inner.strip()
            overrides[kk] = n
            # also include canonical mapping from SIMPLE_MAP if present
            if kk in SIMPLE_MAP:
                overrides[SIMPLE_MAP[kk]] = n
            # and include a safe-name variant
            overrides[_make_safe_name(kk)] = n
    return overrides


def parse_pcs_input_row(pc_name: str, pcs_path: Path = Path('pcs_input.md')) -> Dict[str, int]:
    """Parse `pcs_input.md` and return a mapping of header -> value for the row
    matching pc_name. Numeric cells are converted to int. Returns empty dict if
    file or row not found.
    """
    if not pcs_path.exists():
        return {}
    txt = pcs_path.read_text(encoding='utf-8')
    lines = txt.splitlines()
    header_idx = None
    for i, ln in enumerate(lines):
        if '|' in ln and 'name' in ln.lower():
            header_idx = i
            break
    if header_idx is None:
        return {}
    header_parts = [p.strip() for p in lines[header_idx].split('|')]
    # find separator row
    data_start = header_idx + 1
    if data_start < len(lines) and re.match(r"^\s*\|?\s*-+", lines[data_start]):
        data_start += 1
    for i in range(data_start, len(lines)):
        ln = lines[i]
        if '|' not in ln:
            continue
        parts = [p for p in ln.split('|')]
        # find name column by matching header parts case-insensitively
        name_col = None
        for idx, h in enumerate(header_parts):
            if h and 'name' == h.lower():
                name_col = idx
                break
        if name_col is None:
            # fallback: first non-empty header
            for idx, h in enumerate(header_parts):
                if h.strip():
                    name_col = idx
                    break
        if name_col is None or name_col >= len(parts):
            continue
        cell_name = parts[name_col].strip()
        if cell_name.lower() != pc_name.strip().lower():
            continue
        # found the row; map headers to values
        res: Dict[str, int] = {}
        for idx, h in enumerate(header_parts):
            if not h:
                continue
            label = h
            # strip wikilink markup
            if label.startswith('[[') and label.endswith(']]'):
                inner = label[2:-2]
                if '|' in inner:
                    label = inner.split('|', 1)[1].strip()
                else:
                    label = inner.strip()
            # get corresponding cell if present
            if idx < len(parts):
                val = parts[idx].strip()
            else:
                val = ''
            try:
                n = int(val)
            except Exception:
                try:
                    n = int(float(val))
                except Exception:
                    # non-numeric -> skip or set 0
                    continue
            # add multiple variants to help formula lookup
            res[label] = n
            res[_make_safe_name(label)] = n
            res[label.title()] = n
            res[label.replace(' ', '_')] = n
        return res
    return {}


class SafeEval(ast.NodeVisitor):
    """Very small expression evaluator using AST to avoid eval().

    Supports Names (mapped from provided dict), BinOp, UnaryOp, Call for
    whitelisted functions (int, max, min, math.floor, math.ceil), Num, and
    parentheses.
    """

    ALLOWED_FUNCS = {'int': int, 'max': max, 'min': min, 'abs': abs, 'floor': math.floor, 'ceil': math.ceil}

    def __init__(self, names: Dict[str, Any]):
        self.names = names

    def visit(self, node):
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        elif isinstance(node, ast.BinOp):
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
            raise ValueError(f"Unsupported binary op: {node.op}")
        elif isinstance(node, ast.UnaryOp):
            operand = self.visit(node.operand)
            if isinstance(node.op, ast.USub):
                return -operand
            if isinstance(node.op, ast.UAdd):
                return +operand
            raise ValueError("Unsupported unary op")
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in self.names:
                return self.names[node.id]
            raise ValueError(f"Unknown name: {node.id}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in self.ALLOWED_FUNCS:
                func = self.ALLOWED_FUNCS[node.func.id]
                args = [self.visit(a) for a in node.args]
                return func(*args)
            # allow math.floor / math.ceil as math.floor(x)
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == 'math':
                func_name = node.func.attr
                if func_name in ('floor', 'ceil'):
                    func = getattr(math, func_name)
                    args = [self.visit(a) for a in node.args]
                    return func(*args)
            raise ValueError("Unsupported function call")
        else:
            raise ValueError(f"Unsupported expression node: {node}")


def safe_eval_expr(expr: str, names: Dict[str, Any]) -> Any:
    node = ast.parse(expr, mode='eval')
    return SafeEval(names).visit(node)


def _collect_candidate_formula_keys() -> set:
    """Scan markdown files to collect left-column table labels and quick
    reference placeholders as candidate formula keys.
    """
    keys = set()
    root = Path('.')
    md_files = list(root.rglob('*.md'))
    stopwords = {'note','notes','auto','attribute','value','stat','stats','n','y','current','title','note:'}
    for p in md_files:
        try:
            txt = p.read_text(encoding='utf-8')
        except Exception:
            continue
        # table left-column labels: lines like '| Label |'
        for m in re.finditer(r"\|\s*([^|\n]+?)\s*\|", txt):
            label = m.group(1).strip()
            if not label:
                continue
            # strip wiki link
            label = _strip_wikilink(label)
            # basic sanity filters: must contain letters, not be too short, not be pure numeric/range
            if len(label) < 3:
                continue
            if not re.search(r"[A-Za-z]", label):
                continue
            if re.fullmatch(r"\d+(?:-\d+)?", label):
                continue
            low = label.lower().strip()
            if low in stopwords:
                continue
            if len(low) > 120:
                continue
            # if it's in SIMPLE_MAP, add mapped key
            if label in SIMPLE_MAP:
                keys.add(SIMPLE_MAP[label])
            else:
                safe = _make_safe_name(label)
                if len(safe) > 1 and re.search(r"[A-Za-z]", safe):
                    keys.add(safe)
        # quick reference placeholders like {{airbending_dc}}
        for m in re.finditer(r"\{\{\s*([A-Za-z0-9_ ]+?)\s*\}\}", txt):
            k = m.group(1).strip()
            if not k or len(k) < 3:
                continue
            if not re.search(r"[A-Za-z]", k):
                continue
            lowk = k.lower().strip()
            if lowk in stopwords:
                continue
            if k in SIMPLE_MAP:
                keys.add(SIMPLE_MAP[k])
            else:
                safe = _make_safe_name(k)
                if len(safe) > 1 and re.search(r"[A-Za-z]", safe):
                    keys.add(safe)
    # include SIMPLE_MAP targets explicitly
    for v in SIMPLE_MAP.values():
        keys.add(v)
    return keys


def _default_for_key(key: str) -> str:
    k = key.lower()
    # common heuristics
    if 'hp_per_cl' in k or 'hppercl' in k:
        return '5'
    if k == 'cl' or k.endswith('_cl'):
        return '1'
    if 'max' in k and 'hit' in k:
        return '10 + CON * 2'
    if 'evasion' in k:
        return '10 + DEX'
    if 'armor' in k:
        return '10 + int(CON/2)'
    if k.endswith('_dc') or ' dc' in k or 'bending_dc' in k:
        return '10'
    if 'stress' in k:
        return '0'
    # fallback: 0
    return '0'


def _ensure_formulas_have_defaults(formulas: Dict[str, Any], path: Path) -> Dict[str, Any]:
    """Ensure formulas dict contains sane defaults for candidate keys found
    in the workspace. If we add keys, write back to the JSON file (with a
    .bak backup).
    Returns the possibly-updated formulas dict.
    """
    candidates = _collect_candidate_formula_keys()
    missing = [c for c in sorted(candidates) if c not in formulas]
    if not missing:
        return formulas
    # create backup
    try:
        bak = path.with_suffix(path.suffix + '.bak')
        bak.write_text(path.read_text())
    except Exception:
        pass
    for k in missing:
        formulas[k] = _default_for_key(k)
    try:
        path.write_text(json.dumps(formulas, indent=2) + '\n')
        print(f'Extended formulas file with defaults for: {", ".join(missing)}')
    except Exception as e:
        print('Failed to write formulas file:', e)
    return formulas


def _make_safe_name(name: str) -> str:
    # convert human-friendly names like 'Element Level' -> 'Element_Level'
    return re.sub(r"[^0-9A-Za-z_]+", "_", name).strip('_')


def _strip_wikilink(s: str) -> str:
    """If s is an Obsidian/Markdown wikilink like [[Page|Label]] or [[Label]],
    return the visible label; otherwise return s unchanged.
    """
    if not s:
        return s
    s = s.strip()
    if s.startswith('[[') and s.endswith(']]'):
        inner = s[2:-2]
        if '|' in inner:
            return inner.split('|', 1)[1].strip()
        return inner.strip()
    return s


def compute_derived(stats: Dict[str, int], formulas: Dict[str, str], extra_vars: Dict[str, int] | None = None, cli_overrides: Dict[str, int] | None = None) -> tuple[Dict[str, int], list[str]]:
    """
    Evaluate formulas (which may reference other formula keys or sheet fields).
    Supports multi-word variable names by normalizing them to safe identifiers.

    The evaluation is iterative to resolve dependencies between formulas.
    """
    env: Dict[str, Any] = {k: v for k, v in stats.items()}  # STR, DEX, INT, ...
    extra_vars = extra_vars or {}
    env.update({k: v for k, v in extra_vars.items()})
    cli_overrides = cli_overrides or {}

    # Prepare mapping from human names to safe ids and preprocessed expressions
    name_map: Dict[str, str] = {}
    processed_exprs: Dict[str, str] = {}
    # build a set of candidate variable names: keys from formulas and common sheet fields
    candidate_names = set()
    for k, v in formulas.items():
        # if this formula is a plain numeric string, keep as-is
        candidate_names.add(k)
        if isinstance(v, str):
            # extract potential names from expression
            toks = re.findall(r"[A-Za-z0-9_ ]+", v)
            for t in toks:
                tt = t.strip()
                if tt and not re.fullmatch(r"\d+", tt) and tt.lower() not in ('math','int','max','min','abs','floor','ceil'):
                    candidate_names.add(tt)
    # Add common variants for names so formulas referencing underscores, spaces,
    # 'bending' variants, or titlecased forms will resolve to the same safe id.
    extras = set()
    for name in list(candidate_names):
        extras.add(name.replace('_', ' '))
        extras.add(name.replace(' ', '_'))
        # remove the substring 'bending' and add variants
        if 'bending' in name.lower():
            extras.add(re.sub(r'(?i)bending', '', name).strip())
            extras.add(re.sub(r'(?i)bending', '_', name).strip())
        # titlecase variant
        extras.add(name.title())
    candidate_names.update(extras)

    # create safe name mapping
    for name in sorted(candidate_names, key=lambda s: -len(s)):
        safe = _make_safe_name(name)
        name_map[name] = safe

    # Build processed expressions mapping: replace human names with safe names
    for key, expr in formulas.items():
        if isinstance(expr, (int, float)):
            processed = str(expr)
        else:
            processed = str(expr)
            # replace longer names first to avoid partial replacements
            for human, safe in name_map.items():
                if human == safe:
                    continue
                # use word-boundary-like replace for human names
                pattern = re.compile(rf"\b{re.escape(human)}\b")
                processed = pattern.sub(safe, processed)
        processed_exprs[key] = processed

    # populate env with mapped names from stats and extra_vars
    for human, safe in name_map.items():
        # prefer cli overrides
        if human in cli_overrides:
            env[safe] = cli_overrides[human]
        elif human in extra_vars:
            env[safe] = extra_vars[human]
        else:
            # if stats had a matching short key like 'INT' or 'DEX'
            if human.upper() in stats:
                env[safe] = stats[human.upper()]
            else:
                # if the human name looks like a single short name, try that
                if human.upper() in stats:
                    env[safe] = stats[human.upper()]
                else:
                    # leave undefined for now
                    pass

    env['math'] = math

    results: Dict[str, int] = {}
    unresolved: list[str] = []

    # iterative evaluation to resolve dependencies
    remaining = dict(processed_exprs)
    for iteration in range(10):
        if not remaining:
            break
        progressed = []
        for key, expr in list(remaining.items()):
            # skip if key is overridden by CLI
            if key in cli_overrides:
                try:
                    results[key] = int(cli_overrides[key])
                    env[_make_safe_name(key)] = results[key]
                    progressed.append(key)
                except Exception:
                    progressed.append(key)
                continue
            try:
                # evaluate using safe names in env (names already mapped)
                val = safe_eval_expr(expr, env)
                results[key] = int(val)
                env[_make_safe_name(key)] = int(val)
                progressed.append(key)
            except Exception:
                # can't evaluate yet (missing vars); will retry
                continue
        for k in progressed:
            remaining.pop(k, None)
        if not progressed:
            break

    # Any remaining expressions that couldn't be evaluated become 0
    for k in remaining.keys():
        print(f"Warning: could not resolve formula '{k}' (expr: {formulas.get(k)}) -> defaulting to 0")
        results[k] = 0
        unresolved.append(k)

    # ensure numeric results only
    for k, v in list(results.items()):
        try:
            results[k] = int(v)
        except Exception:
            results[k] = 0

    return results, unresolved


def insert_autogen_report(lines: list[str], inferred: Dict[str, int], overrides: Dict[str, int], unresolved: list[str]) -> list[str]:
    """Insert or replace an '## Autogen Report' section in the document.

    The report contains Inferred values, Overrides (if any), and Unresolved formulas.
    """
    report_lines: list[str] = []
    report_lines.append('## Autogen Report')
    report_lines.append('')
    if inferred:
        report_lines.append('### Inferred values')
        for k, v in inferred.items():
            report_lines.append(f'- {k}: {v}')
        report_lines.append('')
    if overrides:
        report_lines.append('### CLI Overrides')
        for k, v in overrides.items():
            report_lines.append(f'- {k}: {v}')
        report_lines.append('')
    if unresolved:
        report_lines.append('### Unresolved formulas')
        for k in unresolved:
            report_lines.append(f'- {k}')
        report_lines.append('')

    # Find existing Autogen Report header
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if line.strip().lower().startswith('## autogen report'):
            start_idx = i
            break
    if start_idx is not None:
        # find end (next header at same level) or EOF
        for j in range(start_idx + 1, len(lines)):
            if lines[j].strip().startswith('## '):
                end_idx = j
                break
        if end_idx is None:
            end_idx = len(lines)
        new_lines = list(lines[:start_idx]) + report_lines + list(lines[end_idx:])
    else:
        # append at end with a blank line
        new_lines = list(lines)
        if len(new_lines) and new_lines[-1].strip() != '':
            new_lines.append('')
        new_lines.extend(report_lines)
    return new_lines


def parse_autogen_report(lines: list[str]) -> Dict[str, int]:
    """Parse an existing '## Autogen Report' section and return a mapping
    of inferred values (e.g. CL, HP_PER_CL, Element Level, Stress Level).

    The function looks for the '### Inferred values' subsection and parses
    lines like '- CL: 1'. Non-integer values are ignored.
    """
    res: Dict[str, int] = {}
    start_idx = None
    for i, line in enumerate(lines):
        if line.strip().lower().startswith('## autogen report'):
            start_idx = i
            break
    if start_idx is None:
        return res

    # find '### Inferred values' inside the report
    inf_idx = None
    for j in range(start_idx + 1, len(lines)):
        if lines[j].strip().lower().startswith('### inferred values'):
            inf_idx = j
            break
        if lines[j].strip().startswith('## '):
            # no inferred section
            return res
    if inf_idx is None:
        return res

    # collect following list items until next subsection or header
    for k in range(inf_idx + 1, len(lines)):
        ln = lines[k].strip()
        if ln.startswith('### ') or ln.startswith('## '):
            break
        # expect lines like '- CL: 1'
        m = re.match(r"^-\s*([^:]+):\s*(.+)$", ln)
        if not m:
            continue
        key = m.group(1).strip()
        val = m.group(2).strip()
        try:
            num = int(val)
        except Exception:
            try:
                num = int(float(val))
            except Exception:
                continue
        res[key] = num
    return res


def _normalize_words(s: str) -> list[str]:
    words = [w for w in re.split(r'[^0-9A-Za-z]+', s.lower()) if w]
    # rudimentary singularization: strip trailing 's' for simple plurals so
    # 'charge' and 'charges' match the same note stem.
    def singular(w: str) -> str:
        if len(w) > 3 and w.endswith('s'):
            return w[:-1]
        return w
    return [singular(w) for w in words]


def _find_note_for_label(label: str) -> Path | None:
    """Find a markdown file in the workspace whose filename matches the
    significant words from label. Returns the first plausible match or None.
    """
    words = _normalize_words(label)
    if not words:
        return None
    root = Path('.')
    # First pass: prefer files whose stem matches all label words (approx).
    for p in root.rglob('*.md'):
        stem_words = _normalize_words(p.stem)
        if not stem_words:
            continue
        ok = True
        for w in words:
            if not any(w == sw or w in sw or sw in w for sw in stem_words):
                ok = False
                break
        if ok:
            return p
    # Second pass: pick the file with the highest match count (if any)
    best = None
    best_score = 0
    for p in root.rglob('*.md'):
        stem_words = _normalize_words(p.stem)
        if not stem_words:
            continue
        score = 0
        for w in words:
            if any(w == sw or w in sw or sw in w for sw in stem_words):
                score += 1
        if score > best_score:
            best_score = score
            best = p
    if best_score > 0:
        return best
    return None


def _extract_int_from_note(path: Path) -> int | None:
    """Try to extract a sensible integer from the note content.

    Heuristics:
    - look for lines mentioning 'charge'/'charges' with a nearby number
    - otherwise return the first integer found in the file
    """
    try:
        txt = path.read_text(encoding='utf-8')
    except Exception:
        return None
    # Try to parse a two-column markdown table (first matching row with a
    # numeric second column). This works for files like 'Waterbottle Charges.md'.
    for ln in txt.splitlines():
        mrow = re.match(r"\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", ln)
        if mrow:
            left = mrow.group(1).strip()
            right = mrow.group(2).strip()
            try:
                return int(right)
            except Exception:
                # if left contains a range like '1-4' and right is numeric, handled above
                # otherwise continue
                pass
    # look for 'charge' lines like 'charges: 3' or 'Charges 3'
    m = re.search(r'(?i)charges?[^0-9]{0,20}(\d+)', txt)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            pass
    # fallback: first standalone integer
    m2 = re.search(r'\b(\d{1,4})\b', txt)
    if m2:
        try:
            return int(m2.group(1))
        except Exception:
            return None
    return None


# Collector for applied replacements during a run. Each item is a dict with
# keys: file (filled by caller), index, old, new
def _make_replacements_collector() -> list[Dict[str, Any]]:
    return []


def replace_vital_table(lines: list[str], start_idx: int, new_values: Dict[str, int], replacements: list[Dict[str, Any]] | None = None) -> list[str]:
    """Replace entries in the Vital Stats table. Returns updated lines list.
    Looks for rows with 'Max Hit Points', 'Evasion', 'Armor'.
    """
    i = start_idx
    updated = list(lines)
    # detect which column index (if any) contains the auto-flag for this table
    def _detect_auto_col(start: int) -> int | None:
        for j in range(start, len(updated)):
            ln = updated[j]
            if '|' in ln and not re.fullmatch(r"\s*\|\s*-+\s*\|.*", ln):
                # this is likely the header row for the table
                hdr_parts = [p for p in ln.split('|')]
                for idx, cell in enumerate(hdr_parts):
                    if isinstance(cell, str) and re.search(r"auto", cell, flags=re.I):
                        return idx
                return None
        return None

    auto_col_idx = _detect_auto_col(start_idx)

    while i < len(updated):
        line = updated[i]
        if line.strip().startswith('## ') and i != start_idx:
            break
        if '|' in line:
            parts = [p for p in line.split('|')]
            auto_flag = None
            if auto_col_idx is not None and auto_col_idx < len(parts):
                auto_flag = parts[auto_col_idx].strip()
            else:
                # fallback to previous behaviour: second-last cell
                if len(parts) >= 3:
                    auto_flag = parts[-2].strip()
            def _should_update(flag: str | None) -> bool:
                if flag is None or flag == '':
                    return True
                return flag.strip().lower() in ('y', 'yes', 'true')
            if not _should_update(auto_flag):
                i += 1
                continue
            m = re.match(r"(\s*\|\s*([^|]+?)\s*\|\s*)([^|]*?)(\s*\|.*)", line)
            if m:
                raw_label = m.group(2).strip()
                label = _strip_wikilink(raw_label).lower()
                # only overwrite if the existing value cell looks numeric
                cur_val = m.group(3).strip()
                if not re.match(r"^[-+]?\d+(?:\.\d+)?$", cur_val):
                    i += 1
                    continue
                if label in ('max hit points', 'max hit points '):
                    new_line = f"{m.group(1)} {new_values.get('max_hit_points', 0)} {m.group(4)}"
                    if new_line != updated[i] and replacements is not None:
                        replacements.append({'index': i, 'old': updated[i], 'new': new_line})
                    updated[i] = new_line
                elif label == 'evasion':
                    new_line = f"{m.group(1)} {new_values.get('evasion', 0)} {m.group(4)}"
                    if new_line != updated[i] and replacements is not None:
                        replacements.append({'index': i, 'old': updated[i], 'new': new_line})
                    updated[i] = new_line
                elif label == 'armor':
                    new_line = f"{m.group(1)} {new_values.get('armor', 0)} {m.group(4)}"
                    if new_line != updated[i] and replacements is not None:
                        replacements.append({'index': i, 'old': updated[i], 'new': new_line})
                    updated[i] = new_line
                elif label == 'stress':
                    new_line = f"{m.group(1)} {new_values.get('Stress Level', new_values.get('stress', 0))} {m.group(4)}"
                    if new_line != updated[i] and replacements is not None:
                        replacements.append({'index': i, 'old': updated[i], 'new': new_line})
                    updated[i] = new_line
        i += 1
    return updated


def replace_secondary_table(lines: list[str], start_idx: int, new_values: Dict[str, int], replacements: list[Dict[str, Any]] | None = None) -> list[str]:
    """Update Secondary Stats table rows (e.g., Water DC, Earth DC, Fire DC, Spirit DC).
    Matches labels case-insensitively and uses keys from new_values where possible.
    """
    i = start_idx
    updated = list(lines)
    def _detect_auto_col(start: int) -> int | None:
        for j in range(start, len(updated)):
            ln = updated[j]
            if '|' in ln and not re.fullmatch(r"\s*\|\s*-+\s*\|.*", ln):
                hdr_parts = [p for p in ln.split('|')]
                for idx, cell in enumerate(hdr_parts):
                    if isinstance(cell, str) and re.search(r"automatically\s*(updated|generated)|automatically", cell, flags=re.I):
                        return idx
                return None
        return None

    auto_col_idx = _detect_auto_col(start_idx)

    while i < len(updated):
        line = updated[i]
        if line.strip().startswith('## ') and i != start_idx:
            break
        if '|' in line:
            parts = [p for p in line.split('|')]
            auto_flag = None
            if auto_col_idx is not None and auto_col_idx < len(parts):
                auto_flag = parts[auto_col_idx].strip()
            else:
                if len(parts) >= 3:
                    auto_flag = parts[-2].strip()
            def _should_update(flag: str | None) -> bool:
                if flag is None or flag == '':
                    return True
                return flag.strip().lower() in ('y', 'yes', 'true')
            if not _should_update(auto_flag):
                i += 1
                continue
            m = re.match(r"(\s*\|\s*([^|]+?)\s*\|\s*)([^|]*?)(\s*\|.*)", line)
            if m:
                raw_label = m.group(2).strip()
                label = _strip_wikilink(raw_label).lower()
                # only overwrite if the existing value cell looks numeric
                cur_val = m.group(3).strip()
                if not re.match(r"^[-+]?\d+(?:\.\d+)?$", cur_val):
                    i += 1
                    continue
                # try a few canonical mappings
                if 'water dc' == label:
                    new_line = f"{m.group(1)} {new_values.get('waterbending_dc', new_values.get('Waterbending DC', 0))} {m.group(4)}"
                    if new_line != updated[i] and replacements is not None:
                        replacements.append({'index': i, 'old': updated[i], 'new': new_line})
                    updated[i] = new_line
                elif 'earth dc' == label:
                    new_line = f"{m.group(1)} {new_values.get('earthbending_dc', new_values.get('Earthbending DC', 0))} {m.group(4)}"
                    if new_line != updated[i] and replacements is not None:
                        replacements.append({'index': i, 'old': updated[i], 'new': new_line})
                    updated[i] = new_line
                elif 'fire dc' == label:
                    new_line = f"{m.group(1)} {new_values.get('firebending_dc', new_values.get('Firebending DC', 0))} {m.group(4)}"
                    if new_line != updated[i] and replacements is not None:
                        replacements.append({'index': i, 'old': updated[i], 'new': new_line})
                    updated[i] = new_line
                elif 'spirit dc' == label or 'spiritbending dc' == label:
                    new_line = f"{m.group(1)} {new_values.get('spiritbending_dc', new_values.get('Spiritbending DC', 0))} {m.group(4)}"
                    if new_line != updated[i] and replacements is not None:
                        replacements.append({'index': i, 'old': updated[i], 'new': new_line})
                    updated[i] = new_line
                elif 'air dc' == label or 'airbending dc' == label:
                    new_line = f"{m.group(1)} {new_values.get('airbending_dc', new_values.get('Airbending DC', 0))} {m.group(4)}"
                    if new_line != updated[i] and replacements is not None:
                        replacements.append({'index': i, 'old': updated[i], 'new': new_line})
                    updated[i] = new_line
        i += 1
    return updated


def replace_any_table_values(lines: list[str], new_values: Dict[str, int], replacements: list[Dict[str, Any]] | None = None) -> list[str]:
    """Scan the file and update any markdown table row where the left column
    label matches a computed value key. Handles [[Wiki]] labels and common
    variants.
    """
    updated = list(lines)
    # Pre-scan to detect any global auto column index per table header lines
    header_auto_map: dict[int, int | None] = {}
    # key: header line index -> auto column idx (or None)
    for idx, line in enumerate(lines):
        if '|' in line and not re.fullmatch(r"\s*\|\s*-+\s*\|.*", line):
            # potential header
            hdr_parts = [p for p in line.split('|')]
            found = None
            for k, cell in enumerate(hdr_parts):
                if isinstance(cell, str) and re.search(r"automatically\s*(updated|generated)|automatically", cell, flags=re.I):
                    found = k
                    break
            header_auto_map[idx] = found

    for i, line in enumerate(lines):
        if '|' not in line:
            continue
        parts = [p for p in line.split('|')]
        # find nearest header above this row to get its header index
        header_idx = None
        for h in range(i, -1, -1):
            if h in header_auto_map:
                header_idx = h
                break
        auto_flag = None
        if header_idx is not None:
            ai = header_auto_map.get(header_idx)
            if ai is not None and ai < len(parts):
                auto_flag = parts[ai].strip()
        if auto_flag is None:
            # fallback to second-last
            if len(parts) >= 3:
                auto_flag = parts[-2].strip()
        def _should_update(flag: str | None) -> bool:
            if flag is None or flag == '':
                return True
            return flag.strip().lower() in ('y', 'yes', 'true')
        if not _should_update(auto_flag):
            continue
        # Match a table row with at least two columns
        m = re.match(r"(\s*\|\s*([^|]+?)\s*\|\s*)([^|]*?)(\s*\|.*)", line)
        if not m:
            continue
        raw_label = m.group(2).strip()
        # strip wiki links
        label = _strip_wikilink(raw_label)

        # Normal forms to try
        candidates = []
        candidates.append(label)
        candidates.append(label.lower())
        candidates.append(label.title())
        candidates.append(label.replace(' ', ''))
        # common variants
        if label.lower().endswith(' dc'):
            candidates.append(label.lower().replace(' dc','bending_dc'))
        # Map simple known names
        simple_map = {
            'Max Hit Points': 'max_hit_points',
            'Max Hitpoints': 'max_hit_points',
            'Max HP': 'max_hit_points',
            'Evasion': 'evasion',
            'Armor': 'armor',
            'Stress': 'Stress Level',
            'Current Hit Points': 'Current Hit Points',
            'Attack Roll Modifier': 'attack_roll_modifier',
            'Water DC': 'waterbending_dc',
            'Earth DC': 'earthbending_dc',
            'Fire DC': 'firebending_dc',
            'Air DC': 'airbending_dc',
            'Spirit DC': 'spiritbending_dc',
        }

        found_key = None
        # Try simple_map first
        if raw_label in simple_map:
            if simple_map[raw_label] in new_values:
                found_key = simple_map[raw_label]
        # try candidates
        if not found_key:
            for c in candidates:
                # exact match
                if c in new_values:
                    found_key = c
                    break
                # safe-name match
                safe = _make_safe_name(c)
                if safe in new_values:
                    found_key = safe
                    break
                # title/lowercase keys
                if c.title() in new_values:
                    found_key = c.title()
                    break
        if not found_key:
            # try matching case-insensitively among new_values keys
            for k in new_values.keys():
                if k.lower() == label.lower():
                    found_key = k
                    break

        if found_key is not None:
            # only overwrite if existing value cell is numeric
            cur_val = m.group(3).strip()
            if not re.match(r"^[-+]?\d+(?:\.\d+)?$", cur_val):
                continue
            # Replace the value cell with the computed value
            val = new_values.get(found_key, 0)
            new_line = f"{m.group(1)} {val} {m.group(4)}"
            if new_line != updated[i] and replacements is not None:
                replacements.append({'index': i, 'old': updated[i], 'new': new_line})
            updated[i] = new_line

    return updated


def main():
    p = argparse.ArgumentParser(description="Update character sheet derived stats")
    p.add_argument('--pc', help='PC folder/name (e.g. Anju)')
    p.add_argument('--name', help='PC name (used by --levelup)')
    p.add_argument('--levelup', help='Element to level up in pcs_input.md for the named PC (e.g. Fire)')
    p.add_argument('--totalRolledHP', type=int, help='Set Manually Rolled HP value in pcs_input.md when using --levelup')
    p.add_argument('--file', help='Path to Character Sheet.md')
    p.add_argument('--formulas', help='Path to JSON formulas file', default='char_formulas.json')
    p.add_argument('--extend-formulas', action='store_true', help='Allow adding missing default formulas to the formulas file')
    p.add_argument('--all', action='store_true', help='Update all PCs listed in pcs_input.md and generate graphs for each')
    args = p.parse_args()

    # If --levelup provided, update pcs_input.md and then continue to update the sheet
    run_wikigraphs = False
    if getattr(args, 'levelup', None):
        if not getattr(args, 'name', None):
            print('Error: --levelup requires --name <PC name>')
            sys.exit(2)
        def _levelup_pcs_input(element: str, pc_name: str, totalRolledHP: int | None = None, pcs_path: Path = Path('pcs_input.md')) -> int:
            if not pcs_path.exists():
                print(f'pcs_input.md not found at {pcs_path}')
                return 2
            txt = pcs_path.read_text(encoding='utf-8')
            lines = txt.splitlines()
            # Find header line (first line containing 'Name' and pipes)
            header_idx = None
            for i, ln in enumerate(lines):
                if '|' in ln and 'name' in ln.lower():
                    header_idx = i
                    break
            if header_idx is None:
                print('Could not find table header with Name column in pcs_input.md')
                return 2
            header_parts = lines[header_idx].split('|')
            # locate element column index (match by stripped lower equality or contains)
            el = element.strip().lower()
            el_col = None
            # locate manually rolled hp column
            rolled_col = None
            name_col = None
            for idx, part in enumerate(header_parts):
                pstr = part.strip().lower()
                if pstr == 'name' or pstr == 'name':
                    name_col = idx
                if pstr == el or pstr.replace('bending', '').strip() == el:
                    el_col = idx
                # detect Manually Rolled HP header variants
                if pstr in ('manually rolled hp', 'manually_rolled_hp', 'manual', 'manually') or 'manually' in pstr or 'rolled' in pstr:
                    rolled_col = idx
            # fallback: try contains match
            if el_col is None:
                for idx, part in enumerate(header_parts):
                    if el in part.strip().lower():
                        el_col = idx
                        break
            # fallback: try to find rolled column by contains
            if rolled_col is None:
                for idx, part in enumerate(header_parts):
                    if 'manu' in part.lower() or 'roll' in part.lower() or 'manual' in part.lower():
                        rolled_col = idx
                        break
            if name_col is None:
                # default to first non-empty column after possible leading empty
                for idx, part in enumerate(header_parts):
                    if part.strip():
                        name_col = idx
                        break
            if name_col is None:
                print('Could not determine Name column in pcs_input.md')
                return 2
            if el_col is None:
                print(f'Could not find column for element "{element}" in pcs_input.md header')
                return 2

            # Determine data start (skip separator row if present)
            data_start = header_idx + 1
            if data_start < len(lines) and re.match(r"^\s*\|?\s*-+", lines[data_start]):
                data_start += 1

            found = False
            for i in range(data_start, len(lines)):
                ln = lines[i]
                if '|' not in ln:
                    continue
                parts = ln.split('|')
                if name_col >= len(parts):
                    continue
                cell_name = parts[name_col].strip()
                if cell_name.lower() == pc_name.strip().lower():
                    # ensure element column exists
                    while el_col >= len(parts):
                        parts.append(' ')
                    cur = parts[el_col].strip()
                    try:
                        curv = int(cur)
                    except Exception:
                        curv = 0
                    newv = curv + 1
                    parts[el_col] = f' {newv} '
                    # if totalRolledHP provided, set that column as well
                    if totalRolledHP is not None:
                        if rolled_col is None:
                            # try to append at end if no rolled column found
                            parts.append(f' {int(totalRolledHP)} ')
                        else:
                            while rolled_col >= len(parts):
                                parts.append(' ')
                            parts[rolled_col] = f' {int(totalRolledHP)} '
                    lines[i] = '|'.join(parts)
                    found = True
                    break
            if not found:
                print(f'PC name "{pc_name}" not found in pcs_input.md')
                return 2
            # write back
            pcs_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            print(f'Leveled up {element} for {pc_name} -> {newv}')
            return 0

        exit_code = _levelup_pcs_input(args.levelup, args.name, getattr(args, 'totalRolledHP', None))
        # If levelup succeeded, mark to run Wikigraphs after the sheet is updated
        if exit_code == 0:
            run_wikigraphs = True
            print(f"Leveled up {args.levelup} for {args.name} and will regenerate graphs after updating the Character Sheet.")
            # set args.pc so the rest of main will locate and update the sheet
            args.pc = args.name

    # Handle --all: iterate over pcs_input.md rows and run update for each PC,
    # then generate graphs for each PC using Wikigraphs.py
    if getattr(args, 'all', False):
        pcs_path = Path('pcs_input.md')
        if not pcs_path.exists():
            print('pcs_input.md not found; cannot run --all')
            sys.exit(2)
        txt = pcs_path.read_text(encoding='utf-8')
        lines = txt.splitlines()
        header_idx = None
        for i, ln in enumerate(lines):
            if '|' in ln and 'name' in ln.lower():
                header_idx = i
                break
        if header_idx is None:
            print('Could not find table header with Name column in pcs_input.md')
            sys.exit(2)
        header_parts = [p.strip() for p in lines[header_idx].split('|')]
        # find data start
        data_start = header_idx + 1
        if data_start < len(lines) and re.match(r"^\s*\|?\s*-+", lines[data_start]):
            data_start += 1
        names: list[str] = []
        name_col = None
        for idx, h in enumerate(header_parts):
            if h and h.strip().lower() == 'name':
                name_col = idx
                break
        if name_col is None:
            # fallback to first non-empty header
            for idx, h in enumerate(header_parts):
                if h.strip():
                    name_col = idx
                    break
        if name_col is None:
            print('Could not determine Name column in pcs_input.md')
            sys.exit(2)
        for i in range(data_start, len(lines)):
            ln = lines[i]
            if '|' not in ln:
                continue
            parts = [p for p in ln.split('|')]
            if name_col >= len(parts):
                continue
            nm = parts[name_col].strip()
            if not nm:
                continue
            names.append(nm)

        if not names:
            print('No PC names found in pcs_input.md')
            sys.exit(0)

        script_path = Path(__file__).resolve()
        for nm in names:
            print(f"--- Updating PC: {nm}")
            try:
                # invoke this script for the single PC so we reuse all existing logic
                subprocess.run([sys.executable, str(script_path), '--pc', nm], check=True)
            except subprocess.CalledProcessError as e:
                print(f'update_char.py failed for {nm}:', e)
                continue
            # generate graphs for the PC
            try:
                print(f"Generating graphs for {nm}...")
                subprocess.run(['python3', 'Wikigraphs.py', '--pc', nm], check=False)
            except Exception as e:
                print('Failed to run Wikigraphs.py for', nm, ':', e)
        print('Completed --all updates')
        sys.exit(0)

    # Normal single-file or single-pc flow: locate the character sheet file
    fpath = find_character_file(args.pc, args.file)
    if not fpath:
        print('Could not locate character sheet. Provide --file or --pc where file exists.')
        sys.exit(2)

    # Load formulas
    formulas_path = Path(args.formulas)
    if formulas_path.exists():
        try:
            formulas = json.loads(formulas_path.read_text())
        except Exception:
            print('Failed to read formulas file; using defaults')
            formulas = DEFAULT_FORMULAS
    else:
        formulas = DEFAULT_FORMULAS

    # Optionally ensure the formulas file contains defaults for candidate keys.
    # This is disabled by default to avoid mutating a manually-edited
    # `char_formulas.json`. Use --extend-formulas to enable automatic
    # extension behavior.
    if getattr(args, 'extend_formulas', False):
        try:
            formulas = _ensure_formulas_have_defaults(formulas, formulas_path)
        except Exception:
            # non-fatal if extension fails
            pass

    text = fpath.read_text()
    lines = text.splitlines()

    # find Core Stats header
    core_idx = None
    vital_idx = None
    for idx, line in enumerate(lines):
        if line.strip().lower().startswith('## core stats'):
            core_idx = idx
        if line.strip().lower().startswith('## vital stats'):
            vital_idx = idx

    if core_idx is None:
        print('No Core Stats section found in', fpath)
        sys.exit(1)

    _, core_table = parse_table_block(lines, core_idx)
    stats = parse_stats_from_core(core_table)
    # find Bending Levels and Vital/Secondary tables
    bending_idx = None
    secondary_idx = None
    for idx, line in enumerate(lines):
        if line.strip().lower().startswith('## bending levels'):
            bending_idx = idx
        if line.strip().lower().startswith('## secondary stats'):
            secondary_idx = idx

    bending_levels: Dict[str, int] = {}
    if bending_idx is not None:
        bending_levels = parse_bending_levels(lines, bending_idx)

    # parse vital table values to provide variables like 'Stress' if present
    vital_values: Dict[str, int] = {}
    if vital_idx is not None:
        _, vital_table_lines = parse_table_block(lines, vital_idx)
        vital_values = parse_generic_table(vital_table_lines)

    # parse manually rolled hitpoints table if present to infer CL and HP_PER_CL
    rolled_hp = []
    for idx, line in enumerate(lines):
        # heading may be '## Manually Rolled Hitpoints' or '## [[Manually Rolled Hitpoints]]'
        if 'manually rolled hitpoints' in line.lower():
            rolled_hp = parse_manually_rolled_hp(lines, idx)
            break


    # Merge extra vars: bending levels (e.g., 'Air Level'), vital values (e.g., 'Stress')
    extra_vars: Dict[str, int] = {}
    extra_vars.update(bending_levels)
    # If the file already contains an Autogen Report with inferred values,
    # parse and merge them here so they act as inputs to derived formulas.
    parsed_inferred = parse_autogen_report(lines)
    for k, v in parsed_inferred.items():
        # do not overwrite explicit values parsed from tables; they take precedence
        if k not in extra_vars:
            extra_vars[k] = v

    # Try to resolve some unresolved labels by locating a note with a matching
    # name and extracting an integer (e.g., Waterbottle Water Charges -> file
    # 'Waterbottle Water Charges.md' or similar). This helps map in-game items
    # stored elsewhere into numeric inputs for formulas.
    for label in list(formulas.keys()):
        # skip if we already have the value
        if label in extra_vars:
            continue
        # try find a note and extract int
        note = _find_note_for_label(label)
        if note is None:
            continue
        val = _extract_int_from_note(note)
        if val is not None:
            extra_vars[label] = val
    # normalize vital keys like 'Stress' -> 'Stress Level' if appropriate
    for k, v in vital_values.items():
        # strip wikilink if present
        kk = k
        if kk.startswith('[[') and kk.endswith(']]'):
            inner = kk[2:-2]
            if '|' in inner:
                kk = inner.split('|', 1)[1].strip()
            else:
                kk = inner.strip()
        extra_vars[kk] = v

    # Heuristics: create aliases
    # Stress -> Stress Level
    if 'Stress' in extra_vars and 'Stress Level' not in extra_vars:
        extra_vars['Stress Level'] = extra_vars['Stress']
    # Element Level as sum alias if not provided
    if 'Element Level' not in extra_vars:
        total_el = 0
        for el in ('Air Level', 'Water Level', 'Earth Level', 'Fire Level'):
            total_el += int(extra_vars.get(el, 0))
        extra_vars['Element Level'] = total_el
    # Provide short aliases like 'EL' and 'SL'
    if 'Element Level' in extra_vars:
        extra_vars['EL'] = extra_vars['Element Level']
    if 'Stress Level' in extra_vars:
        extra_vars['SL'] = extra_vars['Stress Level']

    # Merge pcs_input.md row for this PC (if available) so formulas can reference
    # columns like 'Manually Rolled HP' directly.
    try:
        pcs_row = parse_pcs_input_row(args.pc)
        # Merge pcs_input values, allowing them to override earlier inferences
        # so manual values in pcs_input.md take precedence.
        for k, v in pcs_row.items():
            extra_vars[k] = v
        # If a Manually Rolled HP value exists under common variants, map it
        # to HP_PER_CL and to Manually_Rolled_Hitpoints so formulas resolve.
        manual_hp_candidates = [
            'Manually Rolled HP', 'Manually_Rolled_HP', 'Manually Rolled Hitpoints',
            'Manually_Rolled_Hitpoints', 'Manually Rolled Hitpoints', 'Manually Rolled HP'
        ]
        manual_val = None
        for c in manual_hp_candidates:
            if c in extra_vars:
                manual_val = int(extra_vars[c])
                break
        # also try safe-name variants
        if manual_val is None:
            for k in list(extra_vars.keys()):
                if _make_safe_name(k).lower().startswith('manually_rolled'):
                    try:
                        manual_val = int(extra_vars[k])
                        break
                    except Exception:
                        continue
        if manual_val is not None:
            extra_vars['HP_PER_CL'] = manual_val
            extra_vars['Manually_Rolled_Hitpoints'] = manual_val
            extra_vars['Manually Rolled Hitpoints'] = manual_val
    except Exception:
        pass

    # Heuristic CL and HP_PER_CL: CL = highest element level if CL not provided
    # If we have rolled HP, prefer that to infer CL and HP_PER_CL
    if rolled_hp:
        # compute CL as max rolled level and HP_PER_CL as avg rolled hp for those levels
        max_lvl = max((r[0] for r in rolled_hp), default=0)
        rolls = [r[2] for r in rolled_hp if r[0] <= max_lvl and r[2] > 0]
        if rolls:
            import math as _math
            avg = _math.ceil(sum(rolls) / len(rolls))
            extra_vars['CL'] = max_lvl
            extra_vars['HP_PER_CL'] = avg
            # Also expose the manually-rolled aggregate under common names so
            # formulas that reference these labels resolve. Some users write
            # formulas like 'HP_PER_CL': 'Manually_Rolled_Hitpoints' or use
            # the spaced variant; provide both.
            extra_vars['Manually_Rolled_Hitpoints'] = avg
            extra_vars['Manually Rolled Hitpoints'] = avg
    if 'CL' not in extra_vars or int(extra_vars.get('CL', 0)) == 0:
        cl_guess = 0
        primary = None
        for el in ('Air Level', 'Water Level', 'Earth Level', 'Fire Level', 'Spirit Level'):
            v = int(extra_vars.get(el, 0))
            if v > cl_guess:
                cl_guess = v
                primary = el
        extra_vars['CL'] = cl_guess

    # HP per CL by primary element
    if 'HP_PER_CL' not in extra_vars or int(extra_vars.get('HP_PER_CL', 0)) == 0:
        primary = None
        maxv = 0
        for el in ('Air Level', 'Water Level', 'Earth Level', 'Fire Level', 'Spirit Level'):
            v = int(extra_vars.get(el, 0))
            if v > maxv:
                maxv = v
                primary = el
        # average dice mapping
        # Air: d6 -> avg 3.5 -> round up 4
        # Water/Fire: d8 -> avg 4.5 -> round up 5
        # Earth: d12 -> avg 6.5 -> round up 7
        # Spirit: d4 -> avg 2.5 -> round up 3
        mapping = {
            'Air Level': 4,
            'Water Level': 5,
            'Fire Level': 5,
            'Earth Level': 7,
            'Spirit Level': 3,
        }
        if primary in mapping:
            extra_vars['HP_PER_CL'] = mapping[primary]
        else:
            extra_vars['HP_PER_CL'] = 5

    # If CL is still zero (template/default), assume starting CL of 1 so
    # derived values like max_hit_points are non-zero in templates.
    # This is a conservative default for empty templates; real characters
    # with explicit CL should override this by setting CL or element levels.
    try:
        if int(extra_vars.get('CL', 0)) == 0:
            extra_vars['CL'] = 1
    except Exception:
        extra_vars['CL'] = 1

    # parse any manual overrides from table rows (rows marked 'N' in the
    # 'Automatically updated' column). These values take precedence as
    # cli_overrides into compute_derived.
    cli_overrides = parse_manual_overrides(lines)

    derived, unresolved = compute_derived(stats, formulas, extra_vars=extra_vars, cli_overrides=cli_overrides)

    if vital_idx is None:
        print('No Vital Stats table found; nothing to update for', fpath)
        sys.exit(0)

    # Prepare a replacements collector to record applied changes
    replacements: list[Dict[str, Any]] = []
    # Replace vital table entries in the original lines
    new_lines = replace_vital_table(lines, vital_idx, derived, replacements=replacements)
    # Replace secondary stats table if present
    if secondary_idx is not None:
        new_lines = replace_secondary_table(new_lines, secondary_idx, derived, replacements=replacements)
    # Replace any other table values that match computed keys
    new_lines = replace_any_table_values(new_lines, derived, replacements=replacements)

    # Build Autogen Report but do not write it into the file; just print it.
    inferred = {}
    for k in ('CL', 'HP_PER_CL', 'Element Level', 'EL', 'Stress Level', 'SL'):
        if k in extra_vars:
            inferred[k] = extra_vars[k]
    overrides = cli_overrides or {}
    report_replacements = []
    for r in replacements:
        report_replacements.append(f"line {r['index']}: {r['old'].strip()} -> {r['new'].strip()}")

    report_lines: list[str] = []
    report_lines.append('## Autogen Report (printed only)')
    report_lines.append('')
    if inferred:
        report_lines.append('### Inferred values')
        for k, v in inferred.items():
            report_lines.append(f'- {k}: {v}')
        report_lines.append('')
    if overrides:
        report_lines.append('### CLI Overrides')
        for k, v in overrides.items():
            report_lines.append(f'- {k}: {v}')
        report_lines.append('')
    if unresolved:
        report_lines.append('### Unresolved formulas')
        for k in unresolved:
            report_lines.append(f'- {k}')
        report_lines.append('')
    # if report_replacements:
    #     report_lines.append('### Applied table replacements')
    #     for s in report_replacements:
    #         report_lines.append(f'- {s}')
    #     report_lines.append('')

    print('\n'.join(report_lines))

    # Apply only the collected replacements (Auto=Y updates) to the original file
    if replacements:
        # make a backup first
        backup = fpath.with_suffix('.md.bak')
        backup.write_text(text)
        # apply replacements to the original lines (indices refer to original)
        for r in replacements:
            idx = r.get('index')
            new = r.get('new')
            if not isinstance(idx, int):
                continue
            if not (0 <= idx < len(lines)):
                continue
            if new is None:
                continue
            # ensure we write a string
            if not isinstance(new, str):
                new = str(new)
            lines[idx] = new
        # write back the minimally-updated file
        fpath.write_text('\n'.join(lines) + '\n')
        print(f'Applied {len(replacements)} Auto-updates to {fpath} (backup at {backup})')
        # regenerate bending slots table if helper script exists
        ub = Path('scripts/update_bending_slots.py')
        if ub.exists():
            try:
                subprocess.run([sys.executable, str(ub), str(fpath)], check=True)
                print('update_bending_slots.py completed; slots updated.')
            except subprocess.CalledProcessError:
                print('update_bending_slots.py failed; slots left as-is.')
    else:
        # nothing to update; leave file unchanged
        print(f'No Auto-updates required for {fpath}')

    # If we were asked to level up earlier and flagged to run Wikigraphs, do it now
    if 'run_wikigraphs' in locals() and run_wikigraphs:
        try:
            print(f"Triggering Wikigraphs for PC '{args.pc}' to refresh graphs...")
            proc = subprocess.run(['python3', 'Wikigraphs.py', '--pc', args.pc], check=False, capture_output=True, text=True)
            if proc.returncode == 0:
                print('Wikigraphs ran successfully')
            else:
                print('Wikigraphs returned non-zero exit code:', proc.returncode)
                if proc.stdout:
                    print('stdout:', proc.stdout)
                if proc.stderr:
                    print('stderr:', proc.stderr)
        except Exception as e:
            print('Failed to run Wikigraphs.py:', e)


if __name__ == '__main__':
    main()
