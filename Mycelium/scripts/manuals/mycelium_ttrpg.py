#!/usr/bin/env python3
"""
mycelium_ttrpg.py

Create per-character variable files from input files that contain '#Variable'
blocks or simple key: value pairs. The generated files are small markdown
fragments (tables) that a templater can include into a character-sheet
template so only relevant sections appear (for example: no Air Levels if the
character has no Air level).

Usage:
  python3 mycelium_ttrpg.py --input path/to/input.md --out-root "Players Part/PCs"

Behavior (conservative defaults):
- If the input file contains a top-level `Name: <value>` or a line like
  `# Name: <value>` that is used as character name. Otherwise the input file
  basename is used.
- The script searches for `#Variable` markers (case-insensitive). If found,
  it parses key:value pairs inside that block. If no explicit `#Variable`
  markers are present the script will fall back to scanning the entire file
  for `Key: value` lines.
- Outputs per-character file: `<out-root>/<Name>/<Name>_variables.md` with a
  `## Character Variables` table of Variable | Value rows. Only variables
  with non-empty values are included. Numeric element levels of zero are
  omitted (so templates can decide not to show Air slots if no `Air` level).

The script is intentionally small and dependency-free.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys
from typing import Dict, List, Tuple, Any, Optional
import ast


def parse_key_values_from_block(lines: List[str]) -> Dict[str, str]:
    """Parse simple key: value pairs from lines. Returns dict of key->value."""
    kv: Dict[str, str] = {}
    table_mode = False
    table_headers: List[str] = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        # detect a simple markdown table header row: | Key | Value |
        if ln.startswith('|') and '|' in ln[1:]:
            parts = [p.strip() for p in ln.strip('|').split('|')]
            # header row -> next row is separator, so skip assignment here
            if not table_mode:
                table_mode = True
                table_headers = parts
                continue
        if table_mode and ln.startswith('|'):
            parts = [p.strip() for p in ln.strip('|').split('|')]
            if len(parts) >= 2:
                key = parts[0]
                val = parts[1]
                kv[key] = val
            continue
        # key: value style
        m = re.match(r'^([^:]+):\s*(.+)$', ln)
        if m:
            key = m.group(1).strip()
            val = m.group(2).strip()
            kv[key] = val
            continue
        # bullet style like - Key: value
        m2 = re.match(r'^[\-\*]\s*([^:]+):\s*(.+)$', ln)
        if m2:
            key = m2.group(1).strip()
            val = m2.group(2).strip()
            kv[key] = val
            continue
    return kv


def extract_variable_blocks(text: str) -> List[Tuple[int, int, List[str]]]:
    """Find blocks starting with a line that contains '#Variable' (case-insensitive)
    and return list of tuples (start_line, end_line, lines).
    If none found returns empty list.
    """
    lines = text.splitlines()
    blocks: List[Tuple[int, int, List[str]]] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if re.search(r'#\s*Variable', ln, re.I):
            # collect until next blank line or next heading starting with '#'
            start = i + 1
            j = start
            collected: List[str] = []
            while j < len(lines):
                lnj = lines[j]
                if lnj.strip().startswith('#') and j > start:
                    break
                collected.append(lnj)
                j += 1
            blocks.append((start, j, collected))
            i = j
        else:
            i += 1
    return blocks


def find_name_in_text(text: str) -> str | None:
    # try Name: value or # Name: value or heading like '# Name'
    m = re.search(r'^[#]*\s*Name:\s*(.+)$', text, re.I | re.M)
    if m:
        return m.group(1).strip()
    # try H1 or H2 first heading
    m2 = re.search(r'^[ \t]*#{1,2}\s*(.+)$', text, re.M)
    if m2:
        return m2.group(1).strip()
    return None


def make_output_text(kv: Dict[str, str]) -> str:
    """Return markdown text for the variables table."""
    lines = []
    lines.append('## Character Variables')
    lines.append('')
    lines.append('| Variable | Value |')
    lines.append('|---|---|')
    for key, val in kv.items():
        if val is None:
            continue
        v = val.strip()
        if not v:
            continue
        # numeric zero check for element levels - skip if zero
        if re.match(r'^\d+$', v) and int(v) == 0:
            continue
        # escape pipe
        v = v.replace('|', '\\|')
        k = key.replace('|', '\\|')
        lines.append(f'| {k} | {v} |')
    lines.append('')
    return '\n'.join(lines)


def write_variables_file(out_root: Path, name: str, text: str) -> Path:
    # create folder out_root / Name
    folder = out_root.joinpath(name)
    folder.mkdir(parents=True, exist_ok=True)
    fname = folder.joinpath(f"{name}_variables.md")
    fname.write_text(text, encoding='utf-8')
    return fname


def process_input_file(path: Path, out_root: Path) -> List[Path]:
    text = path.read_text(encoding='utf-8')
    blocks = extract_variable_blocks(text)
    outputs: List[Path] = []
    if blocks:
        # potentially multiple blocks per file; try to find Name in each block
        for idx, (_s, _e, block_lines) in enumerate(blocks):
            kv = parse_key_values_from_block(block_lines)
            name = kv.get('Name') or kv.get('name') or find_name_in_text('\n'.join(block_lines))
            if not name:
                # fallback to file basename with index
                name = f"{path.stem}" if len(blocks) == 1 else f"{path.stem}_{idx+1}"
            out_text = make_output_text(kv)
            outp = write_variables_file(out_root, sanitize_name(name), out_text)
            outputs.append(outp)
    else:
        # fallback: parse entire file for key:value
        kv = parse_key_values_from_block(text.splitlines())
        if not kv:
            # nothing to do
            return []
    name = kv.get('Name') or kv.get('name') or find_name_in_text(text) or path.stem
    out_text = make_output_text(kv)
    outp = write_variables_file(out_root, sanitize_name(name), out_text)
    outputs.append(outp)
    return outputs


def sanitize_name(name: str) -> str:
    # basic sanitize: remove filesystem-unfriendly chars, trim
    n = name.strip()
    n = re.sub(r'[\\/:\?\*\"<>\|]+', '', n)
    n = n.replace('\n', ' ').strip()
    return n


def _to_number(val: str) -> Optional[float]:
    """Try to convert a string to int or float. Returns None on failure."""
    if val is None:
        return None
    v = str(val).strip()
    if not v:
        return None
    # remove commas
    v = v.replace(',', '')
    try:
        if re.match(r'^-?\d+$', v):
            return int(v)
        return float(v)
    except Exception:
        return None


def _safe_eval_expr(expr: str) -> float:
    """Safely evaluate a numeric expression containing only literals and + - * / and parentheses.

    Raises ValueError for disallowed nodes.
    """
    node = ast.parse(expr, mode='eval')

    def _eval(n: ast.AST) -> float:
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant):
            if isinstance(n.value, (int, float)):
                return n.value
            raise ValueError('Invalid constant')
        if isinstance(n, ast.Num):
            return n.n  # type: ignore[attr-defined]
        if isinstance(n, ast.BinOp):
            left = _eval(n.left)
            right = _eval(n.right)
            if isinstance(n.op, ast.Add):
                return left + right
            if isinstance(n.op, ast.Sub):
                return left - right
            if isinstance(n.op, ast.Mult):
                return left * right
            if isinstance(n.op, ast.Div):
                return left / right
            if isinstance(n.op, ast.FloorDiv):
                return left // right
            if isinstance(n.op, ast.Mod):
                return left % right
            if isinstance(n.op, ast.Pow):
                return left ** right
            raise ValueError('Unsupported binary operator')
        if isinstance(n, ast.UnaryOp):
            val = _eval(n.operand)
            if isinstance(n.op, ast.UAdd):
                return +val
            if isinstance(n.op, ast.USub):
                return -val
            raise ValueError('Unsupported unary operator')
        if isinstance(n, ast.Call):
            raise ValueError('Function calls not allowed')
        raise ValueError(f'Unsupported expression: {type(n).__name__}')

    return float(_eval(node))


def load_secondary_templates(dirpath: Path) -> Dict[str, str]:
    """Load all .md files from a directory and return mapping stem -> content (stripped).

    The content is treated as a single-line formula, for example: [[air]] + [[water]]
    """
    tpl: Dict[str, str] = {}
    if not dirpath.exists() or not dirpath.is_dir():
        return tpl
    for p in sorted(dirpath.glob('*.md')):
        try:
            txt = p.read_text(encoding='utf-8').strip()
        except Exception:
            txt = ''
        if not txt:
            continue
        # strip surrounding code fences if present
        content = txt
        if content.startswith('```'):
            content = '\n'.join([ln for ln in content.splitlines() if not ln.strip().startswith('```')])
        content = content.strip()
        # only include files that explicitly declare themselves as secondary templates
        if re.search(r"#\s*secondary_stat\b", content, re.I):
            # remove comment/tag lines (starting with #) and keep the formula lines
            formula_lines = [ln for ln in content.splitlines() if not ln.strip().startswith('#')]
            formula = '\n'.join(formula_lines).strip()
            if formula:
                tpl[p.stem] = formula
    return tpl


def compute_secondary_stats(kv: Dict[str, str], templates: Dict[str, str]) -> Dict[str, str]:
    """Compute secondary stats from templates and return dict of new key->value strings.

    Templates may contain placeholders like [[air]] which will be replaced by the
    corresponding numeric value from kv (case-insensitive). Missing values default to 0.
    """
    out: Dict[str, str] = {}
    if not templates:
        return out
    # prepare case-insensitive lookup for initial kv
    base_kv: Dict[str, str] = {k.lower(): v for k, v in kv.items()}
    placeholder_re = re.compile(r"\[\[\s*([^\]]+?)\s*\]\]")

    # iterative evaluation: allow secondary templates to reference each other.
    # Repeat until stable or max iterations reached.
    max_iter = max(3, len(templates) * 2)
    for _ in range(max_iter):
        changed = False
        for name, formula in templates.items():
            lname = name.lower()
            # replace placeholders with numeric literals, prefer already computed values
            def _repl(m: re.Match) -> str:
                var = m.group(1).strip()
                lv = var.lower()
                # check computed secondary first
                if lv in out:
                    return out[lv]
                # then check base kv
                if lv in base_kv:
                    num = _to_number(base_kv[lv])
                    return str(num) if num is not None else '0'
                # allow dots in names like rolled.hp
                if lv in base_kv:
                    num = _to_number(base_kv[lv])
                    return str(num) if num is not None else '0'
                # missing -> 0
                return '0'

            expr_filled = placeholder_re.sub(_repl, formula).strip()
            try:
                res = _safe_eval_expr(expr_filled)
            except Exception:
                continue
            sval = str(int(res)) if abs(res - int(res)) < 1e-9 else str(res)
            # store under lowercase key to enable lookup
            if out.get(lname) != sval:
                out[lname] = sval
                changed = True
        if not changed:
            break
    # return with original case where possible (use templates keys)
    final: Dict[str, str] = {}
    for k in templates.keys():
        v = out.get(k.lower())
        if v is not None:
            final[k] = v
    return final


def _lookup_value_for_key(kv_all: Dict[str, str], key: str) -> Optional[str]:
    """Try multiple variations of key to find a value in kv_all (case-insensitive)."""
    if not kv_all:
        return None
    k = key.lower()
    kv_lc = {kk.lower(): vv for kk, vv in kv_all.items()}
    # direct
    if k in kv_lc:
        return kv_lc[k]
    # underscore / dot / dash variants
    for alt in (k.replace('.', '_'), k.replace('-', '_'), k.replace('_', '.'), k.replace('_', '-')):
        if alt in kv_lc:
            return kv_lc[alt]
    return None


def write_character_stat_files(out_root: Path, name: str, variable_root: Path, kv_all: Dict[str, str]) -> None:
    """Create a mirror of `variable_root` under out_root/<name>/<name>_variable and
    write a file for every stat. Filenames are prefixed with character name.
    """
    if not variable_root.exists():
        return
    base_folder = out_root.joinpath(sanitize_name(name))
    dest_base = base_folder.joinpath(f"{sanitize_name(name)}_variable")
    for src in sorted(variable_root.rglob('*.md')):
        rel = src.relative_to(variable_root)
        target_dir = dest_base.joinpath(rel.parent)
        target_dir.mkdir(parents=True, exist_ok=True)
        # prefix filename
        target_name = f"{sanitize_name(name)}_{src.name}"
        target_path = target_dir.joinpath(target_name)
        # try to determine value for this stat from kv_all
        stem = src.stem
        val = _lookup_value_for_key(kv_all, stem)
        if val is not None:
            # write simple markdown with value
            content = val
            # if original file was a code-fenced template, keep it simple
            target_path.write_text(content, encoding='utf-8')
            continue
        # otherwise, try to read template and substitute placeholders
        try:
            tpl = src.read_text(encoding='utf-8')
        except Exception:
            tpl = ''
        # strip fences
        if tpl.startswith('```'):
            tpl = '\n'.join([ln for ln in tpl.splitlines() if not ln.strip().startswith('```')])
        # substitute placeholders like [[x]] using kv_all
        def _repl(m: re.Match) -> str:
            key = m.group(1).strip()
            v = _lookup_value_for_key(kv_all, key)
            return v if v is not None else '0'

        tpl_filled = re.sub(r"\[\[\s*([^\]]+?)\s*\]\]", _repl, tpl)
        # write the filled template (or empty string)
        target_path.write_text(tpl_filled.strip(), encoding='utf-8')


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='Create per-character variable files from input markdowns')
    p.add_argument('--input', '-i', required=True, help='Input file or directory containing input files')
    p.add_argument('--out-root', '-o', default=None, help='Output root for character folders (if omitted read from Mycelium config)')
    p.add_argument('--secondary-dir', '-s', default=None, help='Directory containing secondary stat templates (md files)')
    p.add_argument('--ext', default='.md', help='Input file extension to scan when input is a directory')
    args = p.parse_args(argv)

    input_path = Path(args.input)
    # prefer explicit CLI out-root; otherwise try to read from Mycelium config markdown
    if args.out_root:
        out_root = Path(args.out_root)
    else:
        try:
            from Mycelium.helpers.path_vars import find_path_var
            guessed = find_path_var(Path('.'))
        except Exception:
            guessed = None
        out_root = Path(guessed) if guessed else Path('Players Part/PCs')
    created: List[Path] = []
    # load secondary templates from default location or provided dir
    secondary_templates: Dict[str, str] = {}
    sd = Path(args.secondary_dir) if args.secondary_dir else Path('Player Root/variable/secondary_stat')
    # if the path doesn't exist relative to cwd, try searching upward from this script's parent
    if not sd.exists():
        script_parent = Path(__file__).resolve().parent
        # look up to 5 levels for the expected folder
        found = None
        for up in range(5):
            candidate = script_parent.joinpath(*(['..'] * up)).resolve().joinpath('Player Root/variable/secondary_stat')
            if candidate.exists():
                found = candidate
                break
        if found:
            sd = found
    secondary_templates = load_secondary_templates(sd)
    if input_path.is_dir():
        for pth in sorted(input_path.glob(f'*{args.ext}')):
            # when computing secondary stats we need to parse the file first and then
            # inject computed values before writing the variables file. We'll reuse
            # the existing process_input_file but if secondary templates are present
            # compute them and append to the generated file after creation.
            created += process_input_file(pth, out_root)
            txt = pth.read_text(encoding='utf-8')
            if secondary_templates and re.search(r"#\s*secondary_stat\b", txt, re.I):
                # read back the generated variables file to get kv, compute secondaries and
                # rewrite variables file including computed secondaries.
                # Find created file(s) for this character folder
                name_guess = None
                # try to find Name in original file
                txt = pth.read_text(encoding='utf-8')
                name_guess = find_name_in_text(txt) or pth.stem
                folder = out_root.joinpath(sanitize_name(name_guess))
                varfile = folder.joinpath(f"{sanitize_name(name_guess)}_variables.md")
                if varfile.exists():
                    # parse existing table into kv
                    vtxt = varfile.read_text(encoding='utf-8')
                    # simple parse: look for | Variable | Value | rows
                    kv = {}
                    for ln in vtxt.splitlines():
                        m = re.match(r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', ln)
                        if m:
                            k = m.group(1).strip()
                            v = m.group(2).strip()
                            kv[k] = v
                    computed = compute_secondary_stats(kv, secondary_templates)
                    if computed:
                        # merge and rewrite
                        kv.update(computed)
                        out_text = make_output_text(kv)
                        varfile.write_text(out_text, encoding='utf-8')
                        # also write per-stat files mirroring variable folder
                        write_character_stat_files(out_root, name_guess, sd.parent, kv)
    elif input_path.is_file():
        created += process_input_file(input_path, out_root)
    txt = input_path.read_text(encoding='utf-8')
    if secondary_templates and re.search(r"#\s*secondary_stat\b", txt, re.I):
            # same post-process for single file
            pth = input_path
            name_guess = find_name_in_text(pth.read_text(encoding='utf-8')) or pth.stem
            folder = out_root.joinpath(sanitize_name(name_guess))
            varfile = folder.joinpath(f"{sanitize_name(name_guess)}_variables.md")
            if varfile.exists():
                vtxt = varfile.read_text(encoding='utf-8')
                kv = {}
                for ln in vtxt.splitlines():
                    m = re.match(r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', ln)
                    if m:
                        k = m.group(1).strip()
                        v = m.group(2).strip()
                        kv[k] = v
                computed = compute_secondary_stats(kv, secondary_templates)
                if computed:
                    kv.update(computed)
                    out_text = make_output_text(kv)
                    varfile.write_text(out_text, encoding='utf-8')
                    write_character_stat_files(out_root, name_guess, sd.parent, kv)
    else:
        print(f"Input path not found: {input_path}")
        return 2

    if created:
        for c in created:
            print(f"Wrote: {c}")
    else:
        print("No variable files created.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
