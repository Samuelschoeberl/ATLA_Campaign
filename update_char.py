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


def find_character_file(pc: str | None, npc: str | None, file_arg: str | None) -> Path | None:
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

    # If --npc provided, try common NPC locations under DMs Part/NPCs
    if npc:
        candidates = []
        # DMs Part/NPCs/<NPC>/<NPC> Character Sheet.md
        candidates.append(Path("DMs Part/NPCs") / npc / f"{npc} Character Sheet.md")
        # DMs Part/NPCs/<NPC> Character Sheet.md
        candidates.append(Path("DMs Part/NPCs") / f"{npc} Character Sheet.md")
        # DMs Part/NPCs/<NPC>.md
        candidates.append(Path("DMs Part/NPCs") / f"{npc}.md")
        # Current dir: <npc> Character Sheet.md
        candidates.append(Path(f"{npc} Character Sheet.md"))
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


def replace_secondary_table(lines: list[str], start_idx: int, new_values: Dict[str, int], replacements: list[Dict[str, Any]] | None = None, extra_vars: Dict[str, int] | None = None) -> list[str]:
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
                # Determine whether the corresponding element is present; skip if not
                def _element_level(elem_short: str) -> int:
                    if extra_vars is None:
                        return 0
                    return int(extra_vars.get(f"{elem_short} Level", extra_vars.get(elem_short, 0) or 0))

                # try a few canonical mappings
                if 'water dc' == label:
                    if _element_level('Water') <= 0:
                        i += 1
                        continue
                    new_line = f"{m.group(1)} {new_values.get('waterbending_dc', new_values.get('Waterbending DC', 0))} {m.group(4)}"
                    if new_line != updated[i] and replacements is not None:
                        replacements.append({'index': i, 'old': updated[i], 'new': new_line})
                    updated[i] = new_line
                elif 'earth dc' == label:
                    if _element_level('Earth') <= 0:
                        i += 1
                        continue
                    new_line = f"{m.group(1)} {new_values.get('earthbending_dc', new_values.get('Earthbending DC', 0))} {m.group(4)}"
                    if new_line != updated[i] and replacements is not None:
                        replacements.append({'index': i, 'old': updated[i], 'new': new_line})
                    updated[i] = new_line
                elif 'fire dc' == label:
                    if _element_level('Fire') <= 0:
                        i += 1
                        continue
                    new_line = f"{m.group(1)} {new_values.get('firebending_dc', new_values.get('Firebending DC', 0))} {m.group(4)}"
                    if new_line != updated[i] and replacements is not None:
                        replacements.append({'index': i, 'old': updated[i], 'new': new_line})
                    updated[i] = new_line
                elif 'spirit dc' == label or 'spiritbending dc' == label:
                    if _element_level('Spirit') <= 0:
                        i += 1
                        continue
                    new_line = f"{m.group(1)} {new_values.get('spiritbending_dc', new_values.get('Spiritbending DC', 0))} {m.group(4)}"
                    if new_line != updated[i] and replacements is not None:
                        replacements.append({'index': i, 'old': updated[i], 'new': new_line})
                    updated[i] = new_line
                elif 'air dc' == label or 'airbending dc' == label:
                    if _element_level('Air') <= 0:
                        i += 1
                        continue
                    new_line = f"{m.group(1)} {new_values.get('airbending_dc', new_values.get('Airbending DC', 0))} {m.group(4)}"
                    if new_line != updated[i] and replacements is not None:
                        replacements.append({'index': i, 'old': updated[i], 'new': new_line})
                    updated[i] = new_line
        i += 1
    return updated


def replace_any_table_values(lines: list[str], new_values: Dict[str, int], replacements: list[Dict[str, Any]] | None = None, extra_vars: Dict[str, int] | None = None) -> list[str]:
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
        # If this row looks like an element-specific 'charges' row (e.g. water charges)
        # and that element is absent (level <= 0), remove the row entirely.
        label_l = label.lower()
        def _elem_lvl(short: str) -> int:
            if extra_vars is None:
                return 0
            try:
                return int(extra_vars.get(f"{short} Level", extra_vars.get(short, 0) or 0))
            except Exception:
                return 0
        # common pattern: contains element name and 'charge' or 'waterbottle'
        for short in ('water','air','earth','fire','spirit'):
            if short in label_l and ('charge' in label_l or 'waterbottle' in label_l):
                if _elem_lvl(short.title()) <= 0:
                    # remove this row
                    if replacements is not None:
                        replacements.append({'index': i, 'old': updated[i], 'new': ''})
                    updated[i] = ''
                    continue
        # Danger Sense Reaction is Air-specific: if Air level is zero, remove the row
        if 'danger sense' in label_l or 'danger sense reaction' in label_l:
            if _elem_lvl('Air') <= 0:
                if replacements is not None:
                    replacements.append({'index': i, 'old': updated[i], 'new': ''})
                updated[i] = ''
                continue
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
        # Map of derived keys that are element-specific -> element short name
        element_map_keys = {
            'waterbending_dc': 'Water', 'waterbending dc': 'Water', 'water dc': 'Water', 'water': 'Water',
            'airbending_dc': 'Air', 'airbending dc': 'Air', 'air dc': 'Air', 'air': 'Air',
            'earthbending_dc': 'Earth', 'earthbending dc': 'Earth', 'earth dc': 'Earth', 'earth': 'Earth',
            'firebending_dc': 'Fire', 'firebending dc': 'Fire', 'fire dc': 'Fire', 'fire': 'Fire',
            'spiritbending_dc': 'Spirit', 'spiritbending dc': 'Spirit', 'spirit dc': 'Spirit', 'spirit': 'Spirit',
            'danger sense reaction': 'Air'
        }

        def _is_element_allowed_for_key(kname: str) -> bool:
            if extra_vars is None:
                return True
            kn = kname.lower()
            for kk, short in element_map_keys.items():
                if kk == kn or kk in kn or kn in kk:
                    lvl = int(extra_vars.get(f"{short} Level", extra_vars.get(short, 0) or 0))
                    return lvl > 0
            return True

        if found_key is not None:
            # only overwrite if existing value cell is numeric
            cur_val = m.group(3).strip()
            if not re.match(r"^[-+]?\d+(?:\.\d+)?$", cur_val):
                continue
            # skip element-specific keys when that element is not present
            if not _is_element_allowed_for_key(found_key):
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
    p.add_argument('--npc', help='NPC name (searches under "DMs Part/NPCs")')
    p.add_argument('--name', help='PC name (used by --levelup)')
    p.add_argument('--levelup', help='Element to level up in pcs_input.md for the named PC (e.g. Fire)')
    p.add_argument('--totalRolledHP', type=int, help='Set Manually Rolled HP value in pcs_input.md when using --levelup')
    p.add_argument('--file', help='Path to Character Sheet.md')
    p.add_argument('--formulas', help='Path to JSON formulas file', default='char_formulas.json')
    p.add_argument('--extend-formulas', action='store_true', help='Allow adding missing default formulas to the formulas file')
    p.add_argument('--all', action='store_true', help='Update all PCs listed in pcs_input.md and generate graphs for each')
    p.add_argument('--sync', action='store_true', help='Sync all PCs and NPCs: update sheets for every entry in pcs_input.md and npcs_input.md and generate graphs for each')
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

    # Handle --sync: update all PCs and NPCs and generate graphs for each
    if getattr(args, 'sync', False):
        # Prepare graphs directory snapshot so we can report newly created files
        graphs_dir = Path('graphs')
        existing_graphs = set()
        try:
            if graphs_dir.exists():
                for p in graphs_dir.iterdir():
                    if p.is_file() and p.suffix == '.html':
                        existing_graphs.add(p.resolve())
        except Exception:
            existing_graphs = set()
        def names_from_input(path: Path) -> list[str]:
            if not path.exists():
                return []
            txt = path.read_text(encoding='utf-8')
            lines = txt.splitlines()
            header_idx = None
            for i, ln in enumerate(lines):
                if '|' in ln and 'name' in ln.lower():
                    header_idx = i
                    break
            if header_idx is None:
                return []
            header_parts = [p.strip() for p in lines[header_idx].split('|')]
            data_start = header_idx + 1
            if data_start < len(lines) and re.match(r"^\s*\|?\s*-+", lines[data_start]):
                data_start += 1
            # find name column
            name_col = None
            for idx, h in enumerate(header_parts):
                if h and h.strip().lower() == 'name':
                    name_col = idx
                    break
            if name_col is None:
                for idx, h in enumerate(header_parts):
                    if h.strip():
                        name_col = idx
                        break
            if name_col is None:
                return []
            res: list[str] = []
            for i in range(data_start, len(lines)):
                ln = lines[i]
                if '|' not in ln:
                    continue
                parts = [p for p in ln.split('|')]
                if name_col >= len(parts):
                    continue
                nm = parts[name_col].strip()
                if nm:
                    res.append(nm)
            return res

        # collect PC names
        pc_names = names_from_input(Path('pcs_input.md'))
        # collect NPC names from DMs Part/npcs_input.md or npcs_input.md
        npc_input_candidates = [Path('DMs Part') / 'npcs_input.md', Path('npcs_input.md'), Path('DMs Part/npcs_input.md')]
        npc_names = []
        for p in npc_input_candidates:
            if p.exists():
                npc_names = names_from_input(p)
                if npc_names:
                    break

        # Ensure Character Sheet files exist for all PCs and NPCs before processing.
        def ensure_pc_sheet(name: str):
            # Preferred path: Players Part/PCs/<Name>/Character Sheet.md
            folder = Path('Players Part') / 'PCs' / name
            folder.mkdir(parents=True, exist_ok=True)
            candidate = folder / 'Character Sheet.md'
            if not candidate.exists():
                lines = []
                lines.append(f"**Name:** {name}")
                lines.append("")
                lines.append('## Core Stats')
                lines.append('| Stat | Value |')
                lines.append('| ---- | ----: |')
                for s in ('Strength','Dexterity','Constitution','Intelligence','Wisdom','Charisma'):
                    lines.append(f'| {s} | 0 |')
                lines.append('')
                lines.append('## Bending Levels')
                lines.append('| Element                 | Level | Notes                  | Auto |')
                lines.append('| ----------------------- | ----- | ---------------------- | ---- |')
                lines.append('| [[Airbending Level]]    | 0     |                        | Y    |')
                lines.append('| [[Waterbending Level]]  | 0     |                        | Y    |')
                lines.append('| [[Earthbending Level]]  | 0     |                        | Y    |')
                lines.append('| [[Firebending Level]]   | 0     |                        | Y    |')
                lines.append('| [[Spiritbending Level]] | 0     |                        | Y    |')
                try:
                    candidate.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                    print(f'  Created PC folder and character sheet: {candidate}')
                except Exception as e:
                    print(f'  Failed to create PC sheet for {name}:', e)

        def ensure_npc_sheet(name: str):
            # Create under DMs Part/NPCs/<name>/<name> Character Sheet.md
            folder = Path('DMs Part') / 'NPCs' / name
            folder.mkdir(parents=True, exist_ok=True)
            candidate = folder / f"{name} Character Sheet.md"
            # Also create DMs Part/<name> NPC Sheet.md for compatibility with graphing
            alt = Path('DMs Part') / f"{name} NPC Sheet.md"
            if not candidate.exists() and not alt.exists():
                lines = []
                lines.append(f"**Name:** {name}")
                lines.append("")
                lines.append('## Core Stats')
                lines.append('| Stat | Value |')
                lines.append('| ---- | ----: |')
                for s in ('Strength','Dexterity','Constitution','Intelligence','Wisdom','Charisma'):
                    lines.append(f'| {s} | 0 |')
                lines.append('')
                lines.append('## Bending Levels')
                lines.append('| Element                 | Level | Notes                  | Auto |')
                lines.append('| ----------------------- | ----- | ---------------------- | ---- |')
                lines.append('| [[Airbending Level]]    | 0     |                        | Y    |')
                lines.append('| [[Waterbending Level]]  | 0     |                        | Y    |')
                lines.append('| [[Earthbending Level]]  | 0     |                        | Y    |')
                lines.append('| [[Firebending Level]]   | 0     |                        | Y    |')
                lines.append('| [[Spiritbending Level]] | 0     |                        | Y    |')
                try:
                    candidate.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                    # also write alt for compatibility
                    if not alt.exists():
                        try:
                            alt.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                        except Exception:
                            pass
                    print(f'  Created NPC folder and character sheet: {candidate}')
                except Exception as e:
                    print(f'  Failed to create NPC sheet for {name}:', e)

        for nm in pc_names:
            ensure_pc_sheet(nm)
        for nm in npc_names:
            ensure_npc_sheet(nm)

        script_path = Path(__file__).resolve()
        # Update PCs
        for nm in pc_names:
            print(f"--- Sync updating PC: {nm}")
            try:
                # Before invoking update for this PC, ensure the Character Sheet's
                # '## Bending Levels' table matches pcs_input.md (so level-up
                # changes are reflected in-sheet). This keeps modular parts in sync.
                try:
                    pcs_row = parse_pcs_input_row(nm, Path('pcs_input.md'))
                except Exception:
                    pcs_row = {}
                # locate the character file
                char_file = find_character_file(pc=nm, npc=None, file_arg=None)
                if char_file and pcs_row:
                    try:
                        txt = char_file.read_text(encoding='utf-8')
                        lns = txt.splitlines()
                        # find bending levels header
                        bl_idx = None
                        for i, ln in enumerate(lns):
                            if ln.strip().lower().startswith('## bending levels'):
                                bl_idx = i
                                break
                        # Build desired table lines
                        desired = []
                        desired.append('| Element                 | Level | Notes                  | Auto |')
                        desired.append('| ----------------------- | ----- | ---------------------- | ---- |')
                        elems = [('Airbending Level','Air'), ('Waterbending Level','Water'), ('Earthbending Level','Earth'), ('Firebending Level','Fire'), ('Spiritbending Level','Spirit')]
                        for label, key in elems:
                            # pcs_row keys typically 'Air', 'Water', etc.
                            val = pcs_row.get(key, pcs_row.get(key.title(), 0))
                            try:
                                val = int(val)
                            except Exception:
                                val = 0
                            desired.append(f'| [[{label}]]    | {val}     |                        | Y    |')
                        if bl_idx is not None:
                            # find first table line after header
                            start = bl_idx + 1
                            while start < len(lns) and not lns[start].strip().startswith('|'):
                                start += 1
                            # find end using parse_table_block
                            end_idx, _ = parse_table_block(lns, bl_idx)
                            # replace
                            new_lines = lns[:start] + desired + lns[end_idx:]
                        else:
                            # append at end if no bending levels header exists
                            if lns and lns[-1].strip() != '':
                                lns.append('')
                            lns.append('## Bending Levels')
                            lns.extend(desired)
                            new_lines = lns
                        # write back if changed
                        new_text = '\n'.join(new_lines) + '\n'
                        if new_text != txt:
                            backup = char_file.with_suffix('.md.bak')
                            backup.write_text(txt)
                            char_file.write_text(new_text)
                            print(f'  Updated Bending Levels in {char_file} from pcs_input.md')
                            # Also sync Manually Rolled Hitpoints from pcs_input.md if present
                            try:
                                # try common column keys in pcs_row
                                manu_keys = ['Manually Rolled HP', 'Manually_Rolled_HP', 'Manually Rolled Hitpoints', 'Manually_Rolled_Hitpoints']
                                manu_val = None
                                for k in manu_keys:
                                    if k in pcs_row:
                                        try:
                                            manu_val = int(pcs_row[k])
                                            break
                                        except Exception:
                                            continue
                                # also try simple 'Manually Rolled HP' in safe variants
                                if manu_val is None:
                                    for k, v in pcs_row.items():
                                        if _make_safe_name(k).lower().startswith('manually_rolled'):
                                            try:
                                                manu_val = int(v)
                                                break
                                            except Exception:
                                                continue
                                if manu_val is not None:
                                    try:
                                        cur_txt = char_file.read_text(encoding='utf-8')
                                        cur_lines = cur_txt.splitlines()
                                        # locate Manually Rolled Hitpoints header
                                        mh_idx = None
                                        for ii, ln in enumerate(cur_lines):
                                            if ln.strip().lower().startswith('##') and 'manually rolled hitpoints' in ln.lower():
                                                mh_idx = ii
                                                break
                                        desired_mh = []
                                        desired_mh.append('## [[Manually Rolled Hitpoints]]')
                                        desired_mh.append('| Rolled Hp | Total |')
                                        desired_mh.append('| --------- | ----: |')
                                        desired_mh.append(f'| Manually Rolled Hitpoints | {int(manu_val)} |')
                                        if mh_idx is not None:
                                            # find table start
                                            tstart = mh_idx + 1
                                            while tstart < len(cur_lines) and not cur_lines[tstart].strip().startswith('|'):
                                                tstart += 1
                                            tend, _ = parse_table_block(cur_lines, mh_idx)
                                            new_lines2 = cur_lines[:tstart] + desired_mh + cur_lines[tend:]
                                        else:
                                            if cur_lines and cur_lines[-1].strip() != '':
                                                cur_lines.append('')
                                            cur_lines.append('## [[Manually Rolled Hitpoints]]')
                                            cur_lines.extend(desired_mh[1:])
                                            new_lines2 = cur_lines
                                        new_text2 = '\n'.join(new_lines2) + '\n'
                                        if new_text2 != cur_txt:
                                            b2 = char_file.with_suffix('.md.bak')
                                            b2.write_text(cur_txt)
                                            char_file.write_text(new_text2)
                                            print(f'  Synced Manually Rolled Hitpoints ({manu_val}) into {char_file}')
                                    except Exception as ee:
                                        print('  Failed to sync manually rolled HP for', nm, ':', ee)
                            except Exception:
                                pass
                            # Run update_bending_slots.py to regenerate the Bending Slots section
                            try:
                                ub = Path('scripts/update_bending_slots.py')
                                if ub.exists():
                                    subprocess.run([sys.executable, str(ub), str(char_file)], check=True)
                                    print('  update_bending_slots.py completed; slots updated.')
                                    # Force water charges row to computed value from pcs_row if present
                                    try:
                                        # compute water charges from Water level
                                        wv = pcs_row.get('Water', pcs_row.get('water', pcs_row.get('Waterbending', 0)))
                                        try:
                                            wv = int(wv)
                                        except Exception:
                                            wv = 0
                                        if wv > 0:
                                            computed_water = wv * (1 + (wv // 4))
                                            cur_txt2 = char_file.read_text(encoding='utf-8')
                                            clines = cur_txt2.splitlines()
                                            # find Bending Slots section
                                            bs_idx2 = None
                                            for ii, ln in enumerate(clines):
                                                if ln.strip().startswith('## [[Bending Slots]]'):
                                                    bs_idx2 = ii
                                                    break
                                            if bs_idx2 is not None:
                                                # find table start
                                                tstart = bs_idx2 + 1
                                                while tstart < len(clines) and not clines[tstart].strip().startswith('|'):
                                                    tstart += 1
                                                tend = tstart
                                                # find end of table
                                                while tend < len(clines) and clines[tend].strip().startswith('|'):
                                                    tend += 1
                                                changed = False
                                                for ri in range(tstart, tend):
                                                    row = clines[ri]
                                                    if '|' in row:
                                                        cols = [c.strip() for c in row.strip().strip('|').split('|')]
                                                        if cols and 'water charges' in cols[0].lower():
                                                            # Rebuild the row to use computed value
                                                            newrow = f'| [[water charges]] | [[Waterbottle Charges]] | {computed_water} | {computed_water} |      | Y    |'
                                                            if newrow != row:
                                                                clines[ri] = newrow
                                                                changed = True
                                                if changed:
                                                    b3 = char_file.with_suffix('.md.bak')
                                                    b3.write_text(cur_txt2)
                                                    char_file.write_text('\n'.join(clines) + '\n')
                                                    print(f'  Forced water charges -> {computed_water} in {char_file}')
                                    except Exception:
                                        pass
                            except subprocess.CalledProcessError:
                                print('  update_bending_slots.py failed; slots left as-is.')
                    except Exception as e:
                        print('  Failed to sync bending levels for', nm, ':', e)

                subprocess.run([sys.executable, str(script_path), '--pc', nm], check=True)
            except subprocess.CalledProcessError as e:
                print(f'update_char.py failed for {nm}:', e)
                continue
            # per-PC graph generation skipped here; graphs will be generated
            # once after all PCs/NPCs have been fully updated so they reflect
            # the latest computed stats.

        # Update NPCs
        for nm in npc_names:
            print(f"--- Sync updating NPC: {nm}")
            try:
                # Ensure NPC bending levels are synced from npc_input.md before update
                try:
                    # parse npc row
                    npc_row = parse_pcs_input_row(nm, Path('npc_input.md'))
                except Exception:
                    npc_row = {}
                # locate NPC character file
                char_file = find_character_file(pc=None, npc=nm, file_arg=None)
                # If no character sheet exists, create a folder named after the NPC
                # under 'DMs Part/NPCs' and create a minimal Character Sheet.md there.
                if char_file is None:
                    try:
                        folder = Path('DMs Part') / 'NPCs' / nm
                        folder.mkdir(parents=True, exist_ok=True)
                        candidate = folder / f"{nm} Character Sheet.md"
                        if not candidate.exists():
                            tpl_lines = []
                            tpl_lines.append(f"**Name:** {nm}")
                            tpl_lines.append("")
                            tpl_lines.append("## Bending Levels")
                            tpl_lines.append("| Element                 | Level | Notes                  | Auto |")
                            tpl_lines.append("| ----------------------- | ----- | ---------------------- | ---- |")
                            tpl_lines.append("| [[Airbending Level]]    | 0     |                        | Y    |")
                            tpl_lines.append("| [[Waterbending Level]]  | 0     |                        | Y    |")
                            tpl_lines.append("| [[Earthbending Level]]  | 0     |                        | Y    |")
                            tpl_lines.append("| [[Firebending Level]]   | 0     |                        | Y    |")
                            tpl_lines.append("| [[Spiritbending Level]] | 0     |                        | Y    |")
                            candidate.write_text('\n'.join(tpl_lines) + '\n', encoding='utf-8')
                            print(f'  Created NPC folder and character sheet: {candidate}')
                        char_file = candidate.resolve()
                    except Exception as e:
                        print(f'  Failed to create NPC folder/sheet for {nm}:', e)
                if char_file and npc_row:
                    try:
                        txt = char_file.read_text(encoding='utf-8')
                        lns = txt.splitlines()
                        bl_idx = None
                        for i, ln in enumerate(lns):
                            if ln.strip().lower().startswith('## bending levels'):
                                bl_idx = i
                                break
                        desired = []
                        desired.append('| Element                 | Level | Notes                  | Auto |')
                        desired.append('| ----------------------- | ----- | ---------------------- | ---- |')
                        elems = [('Airbending Level','Air'), ('Waterbending Level','Water'), ('Earthbending Level','Earth'), ('Firebending Level','Fire'), ('Spiritbending Level','Spirit')]
                        for label, key in elems:
                            val = npc_row.get(key, npc_row.get(key.title(), 0))
                            try:
                                val = int(val)
                            except Exception:
                                val = 0
                            desired.append(f'| [[{label}]]    | {val}     |                        | Y    |')
                        if bl_idx is not None:
                            start = bl_idx + 1
                            while start < len(lns) and not lns[start].strip().startswith('|'):
                                start += 1
                            end_idx, _ = parse_table_block(lns, bl_idx)
                            new_lines = lns[:start] + desired + lns[end_idx:]
                        else:
                            if lns and lns[-1].strip() != '':
                                lns.append('')
                            lns.append('## Bending Levels')
                            lns.extend(desired)
                            new_lines = lns
                        new_text = '\n'.join(new_lines) + '\n'
                        if new_text != txt:
                            backup = char_file.with_suffix('.md.bak')
                            backup.write_text(txt)
                            char_file.write_text(new_text)
                            print(f'  Updated Bending Levels in NPC sheet {char_file} from npc_input.md')
                            # Sync Manually Rolled Hitpoints for NPCs if present in npc_row
                            try:
                                manu_val = None
                                for k in ('Manually Rolled HP', 'Manually_Rolled_HP', 'Manually Rolled Hitpoints'):
                                    if k in npc_row:
                                        try:
                                            manu_val = int(npc_row[k])
                                            break
                                        except Exception:
                                            continue
                                if manu_val is None:
                                    for k, v in npc_row.items():
                                        if _make_safe_name(k).lower().startswith('manually_rolled'):
                                            try:
                                                manu_val = int(v)
                                                break
                                            except Exception:
                                                continue
                                if manu_val is not None:
                                    try:
                                        cur_txt = char_file.read_text(encoding='utf-8')
                                        cur_lines = cur_txt.splitlines()
                                        mh_idx = None
                                        for ii, ln in enumerate(cur_lines):
                                            if ln.strip().lower().startswith('##') and 'manually rolled hitpoints' in ln.lower():
                                                mh_idx = ii
                                                break
                                        desired_mh = []
                                        desired_mh.append('## [[Manually Rolled Hitpoints]]')
                                        desired_mh.append('| Rolled Hp | Total |')
                                        desired_mh.append('| --------- | ----: |')
                                        desired_mh.append(f'| Manually Rolled Hitpoints | {int(manu_val)} |')
                                        if mh_idx is not None:
                                            tstart = mh_idx + 1
                                            while tstart < len(cur_lines) and not cur_lines[tstart].strip().startswith('|'):
                                                tstart += 1
                                            tend, _ = parse_table_block(cur_lines, mh_idx)
                                            new_lines2 = cur_lines[:tstart] + desired_mh + cur_lines[tend:]
                                        else:
                                            if cur_lines and cur_lines[-1].strip() != '':
                                                cur_lines.append('')
                                            cur_lines.append('## [[Manually Rolled Hitpoints]]')
                                            cur_lines.extend(desired_mh[1:])
                                            new_lines2 = cur_lines
                                        new_text2 = '\n'.join(new_lines2) + '\n'
                                        if new_text2 != cur_txt:
                                            b2 = char_file.with_suffix('.md.bak')
                                            b2.write_text(cur_txt)
                                            char_file.write_text(new_text2)
                                            print(f'  Synced Manually Rolled Hitpoints ({manu_val}) into NPC sheet {char_file}')
                                    except Exception as ee:
                                        print('  Failed to sync manually rolled HP for NPC', nm, ':', ee)
                            except Exception:
                                pass
                            # regenerate bending slots for NPCs
                            try:
                                ub = Path('scripts/update_bending_slots.py')
                                if ub.exists():
                                    subprocess.run([sys.executable, str(ub), str(char_file)], check=True)
                                    print('  update_bending_slots.py completed for NPC; slots updated.')
                                    # Force water charges using npc_row if present
                                    try:
                                        wv = npc_row.get('Water', npc_row.get('water', 0))
                                        try:
                                            wv = int(wv)
                                        except Exception:
                                            wv = 0
                                        if wv > 0:
                                            computed_water = wv * (1 + (wv // 4))
                                            cur_txt2 = char_file.read_text(encoding='utf-8')
                                            clines = cur_txt2.splitlines()
                                            bs_idx2 = None
                                            for ii, ln in enumerate(clines):
                                                if ln.strip().startswith('## [[Bending Slots]]'):
                                                    bs_idx2 = ii
                                                    break
                                            if bs_idx2 is not None:
                                                tstart = bs_idx2 + 1
                                                while tstart < len(clines) and not clines[tstart].strip().startswith('|'):
                                                    tstart += 1
                                                tend = tstart
                                                while tend < len(clines) and clines[tend].strip().startswith('|'):
                                                    tend += 1
                                                changed = False
                                                for ri in range(tstart, tend):
                                                    row = clines[ri]
                                                    if '|' in row:
                                                        cols = [c.strip() for c in row.strip().strip('|').split('|')]
                                                        if cols and 'water charges' in cols[0].lower():
                                                            newrow = f'| [[water charges]] | [[Waterbottle Charges]] | {computed_water} | {computed_water} |      | Y    |'
                                                            if newrow != row:
                                                                clines[ri] = newrow
                                                                changed = True
                                                if changed:
                                                    b3 = char_file.with_suffix('.md.bak')
                                                    b3.write_text(cur_txt2)
                                                    char_file.write_text('\n'.join(clines) + '\n')
                                                    print(f'  Forced water charges -> {computed_water} in NPC sheet {char_file}')
                                    except Exception:
                                        pass
                            except subprocess.CalledProcessError:
                                print('  update_bending_slots.py failed for NPC; slots left as-is.')
                    except Exception as e:
                        print('  Failed to sync NPC bending levels for', nm, ':', e)

                subprocess.run([sys.executable, str(script_path), '--npc', nm], check=True)
            except subprocess.CalledProcessError as e:
                print(f'update_char.py failed for NPC {nm}:', e)
                continue
            # per-NPC graph generation skipped here; global graph run after sync
            # will produce graphs for all updated sheets. We'll rename NPC graphs
            # after the global run to ensure they include the '_npc' suffix.

        # After syncing all PC/NPC sheets, also regenerate graphs for the workspace
        try:
            print('Generating graphs for synced PCs/NPCs...')
            # Prefer invoking Wikigraphs.py for the whole workspace so graphs for all
            # updated sheets are created. Use --root cwd and output to 'graphs'.
            proc = subprocess.run(['python3', 'Wikigraphs.py', '--root', str(Path.cwd()), '--out', 'graphs'], check=False, capture_output=True, text=True)
            if proc.returncode == 0:
                print('Wikigraphs completed successfully')
            else:
                print('Wikigraphs returned non-zero exit code:', proc.returncode)
                if proc.stdout:
                    print('stdout:', proc.stdout)
                if proc.stderr:
                    print('stderr:', proc.stderr)
            # After global run, ensure NPC graph filenames end with '_npc.html'
            try:
                graphs_dir = Path('graphs')
                if graphs_dir.exists():
                    for nm in npc_names:
                        sun = graphs_dir / f"{nm}_wikigraph_sunburst.html"
                        tre = graphs_dir / f"{nm}_wikigraph_treemap.html"
                        for pth in (sun, tre):
                            if pth.exists():
                                new = pth.with_name(pth.stem + '_npc.html')
                                try:
                                    pth.replace(new)
                                    print(f'Renamed {pth} -> {new}')
                                except Exception:
                                    pass
            except Exception:
                pass
        except Exception as e:
            print('Failed to run Wikigraphs.py after --sync:', e)

        # Summarize newly created graph HTML files in the graphs directory
        try:
            new_graphs = []
            if graphs_dir.exists():
                for p in sorted(graphs_dir.iterdir()):
                    if p.is_file() and p.suffix == '.html' and p.resolve() not in existing_graphs:
                        new_graphs.append(p)
            if new_graphs:
                print('\nNewly created graph files:')
                for p in new_graphs:
                    print(f'- {p}')
            else:
                print('\nNo new graph files detected in', graphs_dir)
        except Exception:
            print('Could not summarize graph files (error listing graphs directory)')

        print('Sync complete')
        sys.exit(0)

    # Normal single-file or single-pc flow: locate the character sheet file
    fpath = find_character_file(getattr(args, 'pc', None), getattr(args, 'npc', None), args.file)
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

    # Compute Danger Sense Reaction (slot) from Air Level and include in derived
    try:
        air_level = int(extra_vars.get('Air Level', extra_vars.get('Air', 0) or 0))
    except Exception:
        try:
            air_level = int(extra_vars.get('Air', 0))
        except Exception:
            air_level = 0
    # Mapping: 1-4 -> 1, 5-8 -> 2, 9-12 -> 3, 13-16 -> 4, 17-20 -> 5
    if air_level <= 0:
        danger_slot = 0
    else:
        danger_slot = min(5, ((max(0, air_level - 1)) // 4) + 1)
    # Only include this purely-secondary stat if the character actually has Air levels
    # (prevents showing 'Danger Sense Reaction' for non-airbenders)
    if air_level > 0:
        # Use human-friendly label matching the sheet: 'Danger Sense Reaction'
        derived['Danger Sense Reaction'] = int(danger_slot)

    if vital_idx is None:
        print('No Vital Stats table found; nothing to update for', fpath)
        sys.exit(0)

    # Prepare a replacements collector to record applied changes
    replacements: list[Dict[str, Any]] = []
    # Replace vital table entries in the original lines
    new_lines = replace_vital_table(lines, vital_idx, derived, replacements=replacements)
    # Replace secondary stats table if present (pass extra_vars to allow gating)
    if secondary_idx is not None:
        new_lines = replace_secondary_table(new_lines, secondary_idx, derived, replacements=replacements, extra_vars=extra_vars)
    # Replace any other table values that match computed keys (pass extra_vars)
    new_lines = replace_any_table_values(new_lines, derived, replacements=replacements, extra_vars=extra_vars)

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
        # Ensure per-element sections exist or are removed based on Bending Levels
        # New behavior: introduce a distinct 'Primary Stats' section (sourced from pcs_input.md)
        # and only keep/insert per-element modular sections for elements that are either
        # present (level > 0) or mentioned in the PC folder name (e.g., 'Waterbender').
        try:
            # Read updated text and lines
            cur_txt = fpath.read_text(encoding='utf-8')
            cur_lines = cur_txt.splitlines()

            # Build a small primary-stats block from pcs_input.md (if available)
            try:
                pcs_row_local = parse_pcs_input_row(args.pc)
            except Exception:
                pcs_row_local = {}

            # Insert or replace a `## Primary Stats (from pcs_input.md)` section
            def _build_primary_stats_block(pcs_row: Dict[str, int]) -> list[str]:
                """Build the Primary Stats block using the exact style from the
                Characters Sheet Template (`Players Part/PCs/Character Sheet Template.md`).
                """
                out: list[str] = []
                out.append('## Primary Stats (optional / autogenerated)')
                out.append('')
                out.append('| Stat | Value |')
                out.append('| ---- | ----: |')
                # core stats first (keep empty cells when no value available so
                # the block matches the template spacing)
                for core in ('STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA'):
                    val = pcs_row.get(core, pcs_row.get(core.title(), ''))
                    if val is None:
                        val = ''
                    out.append(f'| {core} | {val} |')
                out.append('')
                # element levels as a separate simple two-column table (template style)
                for el in ('Air', 'Water', 'Earth', 'Fire', 'Spirit'):
                    v = pcs_row.get(el, pcs_row.get(el.title(), extra_vars.get(f"{el} Level", 0)))
                    try:
                        v = int(v)
                    except Exception:
                        v = 0
                    out.append(f'| {el} Level | {v} |')
                out.append('')
                return out

            # find existing Primary Stats header if any
            ps_header_idx = None
            for i, ln in enumerate(cur_lines):
                if ln.strip().lower().startswith('## primary stats'):
                    ps_header_idx = i
                    break
            primary_block = _build_primary_stats_block(pcs_row_local)
            if ps_header_idx is not None:
                # replace existing block until next '## ' or EOF
                j = ps_header_idx + 1
                while j < len(cur_lines) and not cur_lines[j].strip().startswith('## '):
                    j += 1
                cur_lines = cur_lines[:ps_header_idx] + primary_block + cur_lines[j:]
            else:
                # insert before Bending Levels if present, else before Autogen Report, else at end
                insert_idx = len(cur_lines)
                for i, ln in enumerate(cur_lines):
                    if ln.strip().lower().startswith('## bending levels'):
                        insert_idx = i
                        break
                if insert_idx == len(cur_lines):
                    for i, ln in enumerate(cur_lines):
                        if ln.strip().lower().startswith('## autogen report'):
                            insert_idx = i
                            break
                cur_lines = cur_lines[:insert_idx] + primary_block + cur_lines[insert_idx:]

            # Determine allowed elements: those with level>0 OR mentioned in the PC folder name
            element_map = {
                'Air Level': '## Airbending',
                'Water Level': '## Waterbending',
                'Earth Level': '## Earthbending',
                'Fire Level': '## Firebending',
                'Spirit Level': '## Spiritbending',
            }

            folder_name = ''
            try:
                # look for a descriptive folder name (Players Part/PCs/<PC>)
                parent = fpath.parent
                # prefer immediate parent folder name
                folder_name = parent.name.lower() if parent.name else ''
                # also check grandparent in case sheet is directly in Players Part/PCs
                gp = parent.parent
                if gp and gp.name:
                    # include grandparent too for matching compound names
                    folder_name = (folder_name + ' ' + gp.name.lower()).strip()
            except Exception:
                folder_name = ''

            def _section_index(lines, header):
                for i, ln in enumerate(lines):
                    if ln.strip().startswith(header):
                        return i
                return -1

            def _remove_section(lines, start_idx):
                i = start_idx + 1
                while i < len(lines):
                    if lines[i].strip().startswith('## '):
                        break
                    i += 1
                return lines[:start_idx] + lines[i:]

            def _insert_default_section(lines, header):
                insert_idx = len(lines)
                for i, ln in enumerate(lines):
                    if ln.strip().lower().startswith('## autogen report'):
                        insert_idx = i
                        break
                section = [header, '', f'- Placeholder for {header[3:]} content', '']
                return lines[:insert_idx] + section + lines[insert_idx:]

            changed = False
            for lvl_key, header in element_map.items():
                lvl = int(extra_vars.get(lvl_key, 0)) if extra_vars.get(lvl_key, None) is not None else 0
                # also check pcs_input row for element shorthand like 'Water'
                short_name = lvl_key.split()[0]
                pcs_val = pcs_row_local.get(short_name, pcs_row_local.get(short_name.title(), 0))
                try:
                    pcs_val = int(pcs_val)
                except Exception:
                    pcs_val = 0
                # allowed if level>0 (sheet-derived) or pcs_input says >0, or folder name mentions the element
                allowed = (lvl > 0) or (pcs_val > 0) or (short_name.lower() in folder_name)
                idx = _section_index(cur_lines, header)
                if not allowed:
                    # remove section if present
                    if idx != -1:
                        cur_lines = _remove_section(cur_lines, idx)
                        changed = True
                else:
                    # ensure section exists
                    if idx == -1:
                        cur_lines = _insert_default_section(cur_lines, header)
                        changed = True

            if changed:
                b4 = fpath.with_suffix('.md.bak')
                b4.write_text(cur_txt)
                fpath.write_text('\n'.join(cur_lines) + '\n')
                print('Synchronized per-element modular sections based on Bending Levels and folder for', fpath)
        except Exception:
            pass
    else:
        # nothing to update; still regenerate bending slots to ensure slot rows
        # (water charges, Danger Sense Reaction, etc.) are kept in sync with
        # current Bending Levels. This makes the script idempotent for slots.
        print(f'No Auto-updates required for {fpath}')
        ub = Path('scripts/update_bending_slots.py')
        if ub.exists():
            try:
                subprocess.run([sys.executable, str(ub), str(fpath)], check=True)
                print('update_bending_slots.py completed; slots updated.')
            except subprocess.CalledProcessError:
                print('update_bending_slots.py failed; slots left as-is.')

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
        # If this run was for an NPC, rename generated HTML to end with '_npc.html'
        if getattr(args, 'npc', None):
            try:
                graphs_dir = Path('graphs')
                nm = args.npc
                sun = graphs_dir / f"{nm}_wikigraph_sunburst.html"
                tre = graphs_dir / f"{nm}_wikigraph_treemap.html"
                for pth in (sun, tre):
                    if pth.exists():
                        new = pth.with_name(pth.stem + '_npc.html')
                        try:
                            pth.replace(new)
                            print(f'Renamed {pth} -> {new}')
                        except Exception:
                            pass
            except Exception:
                pass


if __name__ == '__main__':
    main()
