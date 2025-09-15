#!/usr/bin/env python3
"""Recreate PCs from Player Root/pc_primary_stats.md.

Reads primary stats, loads secondary templates tagged with #secondary_stat,
recalculates secondaries iteratively, overwrites per-character variable files
under `Player Root/PCs/<Name>/` and writes a `<Name> character sheet.md`.

This script is safe (no network) and uses an AST-based evaluator for formulas.
"""
from __future__ import annotations
from pathlib import Path
import re
import ast
import shutil
from typing import Dict, Any, List, Optional, Tuple
import importlib.util
import sys
import argparse
# reuse common helpers where appropriate (assignments later will prefer common impls)
# Try relative import first (when used as a package). If that fails (script run),
# fall back to absolute package import, then to loading the local `common.py`
# by path. This keeps the script runnable both as a module and as a standalone script.
try:
    from .common import (
        to_number as _to_number,
        safe_eval as _safe_eval,
        parse_markdown_table as _parse_markdown_table,
        name_from_cell as _name_from_cell,
        get_variable_root as _get_variable_root,
        load_secondary_templates as _load_secondary_templates,
        load_template_tags as _load_template_tags,
        display_name_for as _display_name_for,
        pc_safe as _pc_safe,
    )
except Exception:
    try:
        # Try absolute import when running from repo root
        from Mycelium.scripts.Python.common import (
            to_number as _to_number,
            safe_eval as _safe_eval,
            parse_markdown_table as _parse_markdown_table,
            name_from_cell as _name_from_cell,
            get_variable_root as _get_variable_root,
            load_secondary_templates as _load_secondary_templates,
            load_template_tags as _load_template_tags,
            display_name_for as _display_name_for,
            pc_safe as _pc_safe,
        )
    except Exception:
        # Last-resort: import by file path (works even when not a package)
        common_path = Path(__file__).resolve().parent.joinpath('common.py')
        if common_path.exists():
            spec = importlib.util.spec_from_file_location('mycelium_common', str(common_path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[attr-defined]
            _to_number = getattr(mod, 'to_number', None)
            _safe_eval = getattr(mod, 'safe_eval', None)
            _parse_markdown_table = getattr(mod, 'parse_markdown_table', None)
            _name_from_cell = getattr(mod, 'name_from_cell', None)
            _get_variable_root = getattr(mod, 'get_variable_root', None)
            _load_secondary_templates = getattr(mod, 'load_secondary_templates', None)
            _load_template_tags = getattr(mod, 'load_template_tags', None)
            _display_name_for = getattr(mod, 'display_name_for', None)
            _pc_safe = getattr(mod, 'pc_safe', None)
        else:
            _to_number = _safe_eval = _parse_markdown_table = _name_from_cell = _get_variable_root = _load_secondary_templates = _load_template_tags = _display_name_for = _pc_safe = None


def get_variable_root(foldername: Optional[str] = None) -> Optional[Path]:
    """Try to find a Root.md file using the existing mycelium helper.

    If foldername is provided, search the repository for the first
    directory whose name matches `foldername` and return its
    `<that_dir>/variable` path (created if necessary).

    Returns the directory containing the vault's `variable` folder, or
    None if not found.
    """
    # If a folder name was provided, prefer the first matching directory
    # anywhere in the repository and use that as the vault root.
    if foldername:
        try:
            # normalize search name
            fname = foldername.strip()
            for p in ROOT.rglob('*'):
                if p.is_dir() and p.name == fname:
                    try:
                        var_dir = p.joinpath('variable')
                        var_dir.mkdir(parents=True, exist_ok=True)
                        return var_dir
                    except Exception:
                        # if creation fails, continue searching
                        continue
            # also check top-level directory names as a fallback
            for p in ROOT.iterdir():
                if p.is_dir() and p.name == fname:
                    try:
                        var_dir = p.joinpath('variable')
                        var_dir.mkdir(parents=True, exist_ok=True)
                        return var_dir
                    except Exception:
                        break
        except Exception:
            pass
    # Prefer a Root.md that declares the vault root path in its first non-empty
    # non-comment line. If found, use that path's `variable` folder.
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
                        # read Root.md and extract first non-empty, non-# line
                        try:
                            txt = Path(rm).read_text(encoding='utf-8')
                            for ln in txt.splitlines():
                                s = ln.strip()
                                if not s:
                                    continue
                                if s.startswith('#'):
                                    continue
                                # treat this as the repo-relative vault path
                                vault = ROOT.joinpath(s)
                                var_dir = vault.joinpath('variable')
                                var_dir.mkdir(parents=True, exist_ok=True)
                                return var_dir
                        except Exception:
                            # if we can't read or parse Root.md, don't fall back to its parent
                            # (that could be an internal Mycelium folder). Continue to other checks.
                            pass
    except Exception:
        pass
    # fallback: explicitly prefer the repo 'Player Root/variable' if present
    cand = ROOT.joinpath('Player Root', 'variable')
    if cand.exists():
        return cand
    return None


ROOT = Path('.').resolve()
INPUT_TABLE = ROOT.joinpath('Player Root', 'pc_primary_stats.md')
PRIMARY_TEMPLATES_DIR = ROOT.joinpath('Player Root', 'variable', 'primary_stat')
SECONDARY_TEMPLATES_DIR = ROOT.joinpath('Player Root', 'variable', 'secondary_stat')
ENVIRONMENTAL_TEMPLATES_DIR = ROOT.joinpath('Player Root', 'variable', 'environmental')
OUT_ROOT = ROOT.joinpath('Player Root', 'PCs')


def parse_markdown_table(path: Path) -> Tuple[List[str], List[List[str]]]:
    txt = path.read_text(encoding='utf-8')
    lines = [l.rstrip() for l in txt.splitlines()]

    # Find the first markdown table: header row followed by a separator row with dashes
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


def name_from_cell(cell: str) -> str:
    m = re.search(r"\[\[([^\]]+)\]\]", cell)
    if m:
        return m.group(1).strip()
    return cell.strip()


def to_number(s: Any) -> Any:
    if s is None:
        return 0
    s = str(s).strip()
    if s == '':
        return 0
    s = s.replace(',', '')
    try:
        if '.' in s:
            return float(s)
        return int(s)
    except Exception:
        m = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
        if m:
            return float(m.group(0)) if '.' in m.group(0) else int(m.group(0))
    return 0


# safe evaluator
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
        raise ValueError('unsupported expression')

    try:
        return _eval(node)
    except Exception:
        return expr


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
        # unescape markdown-escaped operators (e.g. "\\*" -> "*")
        formula = re.sub(r"\\([^\w\s])", r"\1", formula)
        # allow formulas that start with '=' (common spreadsheet style) by stripping it
        formula = re.sub(r'^\s*=\s*', '', formula)
        out[p.stem] = formula
    return out


def load_environmental_templates(dirpath: Path) -> Dict[str, str]:
    """Load templates from the environmental folder.

    This mirrors load_secondary_templates but looks for the
    #environmental_variable tag (or #environmental_variable in the raw file)
    so environmental variable templates are discovered and returned.
    """
    out: Dict[str, str] = {}
    if not dirpath.exists():
        return out
    for p in sorted(dirpath.glob('*.md')):
        txt = p.read_text(encoding='utf-8')
        stripped = re.sub(r'(```|~~~).*?\1', '', txt, flags=re.S)
        # accept several common tag variants so templates generated elsewhere are discovered
        if ('#environmental_variable' not in stripped and '#environmental_variable' not in txt
            and '#environmental_variables' not in stripped and '#environmental_variables' not in txt
            and '#environmental' not in stripped and '#environmental' not in txt):
            continue
        lines = [l for l in stripped.splitlines() if l.strip() and not l.strip().startswith('#')]
        formula = lines[0].strip() if lines else ''
        if not formula:
            m = re.search(r'(```|~~~)(.*?)\1', txt, flags=re.S)
            if m:
                formula = m.group(2).strip().splitlines()[0] if m.group(2) else ''
        formula = re.sub(r"\\([^\w\s])", r"\1", formula)
        formula = re.sub(r'^\s*=\s*', '', formula)
        out[p.stem] = formula
    return out


def templates_referencing_var(var_stem: str, templates: Dict[str, str]) -> List[str]:
    """Return a list of template stems whose formula references [[var_stem]] or the bare name.

    Matching checks for explicit [[...]] token references and simple substring matches
    (word-boundary) inside the formula to catch variants.
    """
    out: List[str] = []
    if not var_stem:
        return out
    # normalize base and generate likely name variants to match templates
    base = re.sub(r'[^A-Za-z0-9_]', '_', var_stem).lower()
    variants = {base}
    # plural/singular variants
    if base.endswith('s'):
        variants.add(base[:-1])
    else:
        variants.add(base + 's')
    # also accept environmental_ prefix variants: both with and without the prefix
    if base.startswith('environmental_'):
        variants.add(base.replace('environmental_', ''))
    else:
        variants.add('environmental_' + base)

    token_pat = re.compile(r"\[\[\s*([^\]]+)\s*\]\]")

    # build dependency map: for each template, which other templates/variables it references
    deps: Dict[str, List[str]] = {}
    for stem, formula in (templates or {}).items():
        refs: List[str] = []
        if not formula:
            deps[stem] = refs
            continue
        # token references
        for m in token_pat.findall(formula):
            if not m:
                continue
            mnorm = re.sub(r'[^A-Za-z0-9_]', '_', m).lower()
            refs.append(mnorm)
        # bare-word references
        fnorm = re.sub(r'[^A-Za-z0-9_]', '_', formula).lower()
        words = set(re.findall(r"[A-Za-z0-9_]+", fnorm))
        refs.extend(words)
        # normalize and dedupe
        refs_norm = list(dict.fromkeys(refs))
        deps[stem] = refs_norm

    # start with templates that reference any of the initial variants
    initial = set()
    for stem, refs in deps.items():
        for r in refs:
            if r in variants:
                initial.add(stem)
                break

    # BFS/closure: include templates that reference templates in the set
    result: List[str] = []
    queue = list(initial)
    seen_set = set()
    while queue:
        cur = queue.pop(0)
        if cur in seen_set:
            continue
        seen_set.add(cur)
        result.append(cur)
        # find templates that reference `cur`
        for stem, refs in deps.items():
            if stem in seen_set:
                continue
            if cur.lower() in (r.lower() for r in refs):
                queue.append(stem)

    return result


# Prefer shared implementations from common.py when available to reduce duplication.
# These assignments override the local functions above with the shared ones.
try:
    to_number = _to_number
    safe_eval = _safe_eval
    parse_markdown_table = _parse_markdown_table
    name_from_cell = _name_from_cell
    get_variable_root = _get_variable_root
    load_secondary_templates = _load_secondary_templates
    load_template_tags = _load_template_tags
    display_name_for = _display_name_for
    pc_safe = _pc_safe
except Exception:
    # if anything goes wrong, keep local definitions
    pass


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


def load_primary_names(dirpath: Path) -> List[str]:
    if not dirpath.exists():
        return []
    return [p.stem for p in sorted(dirpath.glob('*.md'))]


def compute_secondaries(kv: Dict[str, Any], templates: Dict[str, str], passes: int = 6, verbose: bool = False, known_vars: Optional[set] = None, pc_name: Optional[str] = None, create_placeholders: bool = False, placeholder_dir: Optional[Path] = None, rollable_set: Optional[set] = None, suppress_warnings: Optional[set] = None) -> Dict[str, Any]:
    kv_local: Dict[str, Any] = {}
    for k, v in kv.items():
        lk = k.lower()
        kv_local[lk] = v
        # also allow dotted/underscore variations for template lookups
        kv_local[lk.replace(' ', '.').replace('_', '.')] = v
    # normalize known_vars to dotted-lower form for quick checks
    def _norm_to_dot(s: str) -> str:
        return s.strip().lower().replace('_', ' ').replace('.', ' ').replace('  ', ' ').replace(' ', '.')
    known_dot: set = set()
    if known_vars:
        for k in known_vars:
            known_dot.add(_norm_to_dot(k))
    # track missing variables referenced by templates
    missing_vars: set = set()
    pattern = re.compile(r"\[\[\s*([^\]]+)\s*\]\]")
    for pass_no in range(1, passes + 1):
        changed = False
        if verbose:
            print(f"--- pass {pass_no} ---")
        for name, formula in templates.items():
            key = name.lower()

            def sub(m):
                raw = m.group(1).strip()
                tok = raw.lower()
                tok = tok.replace(' ', '.').replace('_', '.')
                if tok not in kv_local:
                    # if token not known from variable files, warn once
                    if known_dot and tok not in known_dot:
                        if raw not in missing_vars:
                            missing_vars.add(raw)
                            # attempt to create a placeholder file if requested
                            if create_placeholders:
                                # decide where to create: default to secondary templates dir unless placeholder_dir provided
                                target_dir = placeholder_dir or SECONDARY_TEMPLATES_DIR
                                try:
                                    target_dir.mkdir(parents=True, exist_ok=True)
                                    safe_stem = re.sub(r"[^A-Za-z0-9_\- ]", '', raw).strip().replace(' ', '_').lower()
                                    ph_path = target_dir.joinpath(safe_stem + '.md')
                                    if not ph_path.exists():
                                        ph_path.write_text('#variable\n0\n', encoding='utf-8')
                                        print(f"WARNING: missing #variable file for '{raw}' referenced by template '{name}' for PC '{pc_name or 'unknown'}' - created placeholder: {ph_path.relative_to(ROOT)}")
                                    else:
                                        print(f"WARNING: missing #variable file for '{raw}' referenced by template '{name}' for PC '{pc_name or 'unknown'}' (placeholder already exists: {ph_path.relative_to(ROOT)})")
                                except Exception:
                                    print(f"WARNING: missing #variable file for '{raw}' referenced by template '{name}' for PC '{pc_name or 'unknown'}'")
                            else:
                                print(f"WARNING: missing #variable file for '{raw}' referenced by template '{name}' for PC '{pc_name or 'unknown'}'")
                    # fall back to zero
                    return '0'
                return str(kv_local.get(tok, 0))

            expr = pattern.sub(sub, formula)
            # replace bare tokens (like 'earth' or 'max_hp') with known numeric values
            word_pat = re.compile(r"\b([A-Za-z][A-Za-z0-9_ ]*)\b")
            def sub_word(m):
                raw = m.group(1).strip()
                tok = raw.lower().replace(' ', '.').replace('_', '.')
                if tok in kv_local:
                    return str(kv_local.get(tok, 0))
                return m.group(0)

            expr = word_pat.sub(sub_word, expr)
            val = safe_eval(expr)
            if verbose:
                print(f"[{name}] formula: {formula!r} -> expr: {expr!r} => {val!r}")
            # if evaluation returned a non-numeric string, warn once
            if isinstance(val, str) and re.search(r'[A-Za-z]', val):
                if val != formula:
                    # only warn if the formula changed but still contains words
                    # but suppress this warning for templates that are marked
                    # as #rollable (they intentionally contain dice notation).
                    try:
                        is_rollable = False
                        if rollable_set and name.lower() in rollable_set:
                            is_rollable = True
                    except Exception:
                        is_rollable = False
                    if not is_rollable:
                        # allow suppression by normalized template/name
                        try:
                            nname = re.sub(r'[^A-Za-z0-9_]', '_', name).lower()
                        except Exception:
                            nname = name.lower() if isinstance(name, str) else ''
                        if not suppress_warnings or nname not in suppress_warnings:
                            print(f"WARNING: expression for template '{name}' could not be evaluated to a number for PC '{pc_name or 'unknown'}': {expr}")
            def _set_kv(kname: str, value: Any):
                kv_local[kname] = value
                kv_local[kname.replace(' ', '.').replace('_', '.')] = value

            if isinstance(val, (int, float)):
                if kv_local.get(key) != val:
                    _set_kv(key, val)
                    changed = True
                    if verbose:
                        print(f"  -> set {key} = {val}")
            else:
                if kv_local.get(key) != val:
                    _set_kv(key, val)
                    changed = True
                    if verbose:
                        print(f"  -> set {key} = {val}")
        if not changed:
            if verbose:
                print("no changes in this pass, stopping")
            break
    return kv_local


def write_character_files(name: str, kv_all: Dict[str, Any], primary_names: List[str], secondary_templates: Dict[str, str], out_root: Path, var_root: Optional[Path] = None, primary_tags: Optional[Dict[str, List[str]]] = None, secondary_tags: Optional[Dict[str, List[str]]] = None, verbose: bool = False, suppress_warnings: Optional[set] = None) -> None:
    safe = re.sub(r"[^A-Za-z0-9_\-]", '_', name)
    pc_dir = out_root.joinpath(safe)
    pc_dir.mkdir(parents=True, exist_ok=True)
    # variables table
    vars_path = pc_dir.joinpath(f"{safe}_variables.md")
    lines = ['| Variable | Value |', '|---|---:|']
    for k in sorted(kv_all.keys()):
        lines.append(f'| {k} | {kv_all[k]} |')
    vars_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    # write per-stat variable files into the global variable root (if available)
    if var_root is None:
        # fallback to previous behaviour: create mirror folder per-PC
        mirror = pc_dir.joinpath(f"{safe}_variable")
        mirror.mkdir(parents=True, exist_ok=True)
        target_root = mirror
    else:
        # create a per-character subfolder inside a dedicated PC_variables folder
        target_root = var_root.joinpath('PC_variables', safe)
        target_root.mkdir(parents=True, exist_ok=True)
    # Preserve any templates tagged with #current_variable by reading existing
    # character sheet values and injecting them into kv_all so they survive
    # regeneration. secondary_tags keys are template stems (lowercased).
    try:
        cur_keys: List[str] = []
        if secondary_tags:
            for stem, tags in secondary_tags.items():
                if '#current_variable' in (t.lower() for t in tags):
                    cur_keys.append(stem)
        existing_sheet = pc_dir.joinpath(f"{safe} character sheet.md")
        if cur_keys and existing_sheet.exists():
            sheet_txt = existing_sheet.read_text(encoding='utf-8')
            for stem in cur_keys:
                kn = stem.lower()
                # compute display name similar to later rendering rules
                def _display_name(k: str) -> str:
                    mapping = {
                        'str': 'Strength', 'dex': 'Dexterity', 'con': 'Constitution',
                        'int': 'Intelligence', 'wis': 'Wisdom', 'cha': 'Charisma',
                        'hp': 'HP', 'max_hp': 'Max HP',
                    }
                    kk = k.replace('.', '_').replace(' ', '_').lower()
                    if kk in mapping:
                        return mapping[kk]
                    k2 = kk.replace('_', ' ').replace('.', ' ')
                    words = k2.split()
                    out = []
                    for i, w in enumerate(words):
                        if w.lower() in ('hp',):
                            out.append(w.upper())
                        else:
                            out.append(w.capitalize() if i == 0 else w.lower())
                    return ' '.join(out)

                dname = _display_name(kn)
                # look for a table row like: | Display Name | value |
                m = re.search(r"(?im)^\|\s*" + re.escape(dname) + r"\s*\|\s*([^|\n]+)\|", sheet_txt)
                if not m:
                    raw = kn.replace('_', ' ').replace('.', ' ')
                    m = re.search(r"(?im)^\|\s*" + re.escape(raw) + r"\s*\|\s*([^|\n]+)\|", sheet_txt)
                if m:
                    valstr = m.group(1).strip()
                    try:
                        kv_all[kn] = to_number(valstr)
                    except Exception:
                        kv_all[kn] = valstr
                    if verbose:
                        print(f"Preserved current variable '{stem}' for {name}: {kv_all[kn]!r}")
    except Exception:
        # non-fatal preservation failure should not stop generation
        pass
    # primary
    for p in primary_names:
        key = p.lower()
        val = kv_all.get(key, 0)
        # always save files as <character>_<originalfilename>.md inside the per-character folder
        fname = f"{safe}_{p}.md"
        fpath = target_root.joinpath(fname)
        tags: List[str] = []
        if primary_tags and key in primary_tags:
            tags = [t for t in primary_tags[key] if t != '#template']
        for req in ('#variable', '#character_stat', '#character_stats', '#primary_stat'):
            if req not in tags:
                tags.append(req)
        fpath.write_text(f'```markdown\n{val}\n\n{" ".join(tags)}\n\n```\n', encoding='utf-8')
    # secondary
    for p in secondary_templates.keys():
        key = p.lower()
        val = kv_all.get(key, '')
        # follow same naming as primary: <character>_<originalfilename>.md
        fname = f"{safe}_{p}.md"
        fpath = target_root.joinpath(fname)
        tags: List[str] = []
        if secondary_tags and key in secondary_tags:
            tags = [t for t in secondary_tags[key] if t != '#template']
        for req in ('#variable', '#character_stat', '#character_stats', '#secondary_stat'):
            if req not in tags:
                tags.append(req)
        # If this secondary stat evaluates to numeric zero, skip creating the
        # per-PC variable file unless the template is explicitly tagged with
        # #vitality. This keeps zero-valued secondaries out of the variables
        # folder and prevents them from appearing in regenerated character
        # sheets.
        try:
            is_zero_numeric = isinstance(val, (int, float)) and val == 0
        except Exception:
            is_zero_numeric = False
        # If this secondary is numeric zero, skip creating the per-PC file
        # unless the template is tagged with #vitality or #environmental_variable
        # (environmental variables should still be shown even when 0).
        if is_zero_numeric and ('#vitality' not in tags) and ('#environmental_variable' not in tags):
            # skip writing this secondary variable file
            if verbose:
                print(f"Skipping secondary var file for '{p}' for {name} because value is 0 and not #vitality or #environmental_variable")
        else:
            fpath.write_text(f'```markdown\n{val}\n\n{" ".join(tags)}\n\n```\n', encoding='utf-8')

    # write a character sheet using the template if available
    sheet = pc_dir.joinpath(f"{safe} character sheet.md")
    tpl_path = ROOT.joinpath('Mycelium', 'data', 'template', 'template_Character_Sheet.md')
    if tpl_path.exists():
        # prefer using the simple renderer from create_from_template if available
        tpl_raw = tpl_path.read_text(encoding='utf-8')
        tpl_raw_inner = None
        try:
            create_path = ROOT.joinpath('Mycelium', 'scripts', 'manuals', 'create_from_template.py')
            if create_path.exists():
                spec = importlib.util.spec_from_file_location('create_from_template', str(create_path))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                else:
                    mod = None
                # render top-level template replacements (e.g., {{PC}}) if loader provided the function
                if mod is not None and hasattr(mod, 'render_template'):
                    try:
                        rendered = mod.render_template(tpl_path, {'PC': name})
                        # match fenced code blocks and allow an info string after the opening fence
                        m = re.search(r'(?s)(```|~~~)[^\n]*\n(.*?)\n\1', rendered)
                        tpl_raw_inner = m.group(2) if m else rendered
                    except Exception:
                        tpl_raw_inner = None
        except Exception:
            tpl_raw_inner = None
        if tpl_raw_inner is None:
            # allow fences like ```markdown by accepting optional info after the opening fence
            m = re.search(r'(?s)(```|~~~)[^\n]*\n(.*?)\n\1', tpl_raw)
            tpl_raw_inner = m.group(2) if m else tpl_raw

        # helper: normalize keys in kv_all for lookup
        norm_kv = {k.lower().replace('.', '_').replace(' ', '_'): v for k, v in kv_all.items()}

        # Canonical mapping for environmental variables: many templates and
        # placeholders use singular or plural forms (e.g. environmental_water_charge
        # vs environmental_water_charges). For any secondary template tagged with
        # #environmental_variable ensure both singular and plural normalized keys
        # map to the same value in norm_kv so template placeholders resolve.
        if secondary_tags:
            for stem, tags in secondary_tags.items():
                if '#environmental_variable' in tags:
                    # normalized stem (underscores, lowercase)
                    sname = stem.replace('.', '_').replace(' ', '_').lower()
                    # derive singular/plural variants
                    if sname.endswith('s'):
                        singular = sname[:-1]
                        plural = sname
                    else:
                        singular = sname
                        plural = sname + 's'
                    # try to find an existing value for any of the variants
                    found_val = None
                    for cand in (sname, singular, plural, singular.replace('_', '.'), plural.replace('_', '.')):
                        if cand in norm_kv:
                            found_val = norm_kv[cand]
                            break
                        if cand in kv_all:
                            found_val = kv_all[cand]
                            break
                    if found_val is not None:
                        norm_kv[singular] = found_val
                        norm_kv[plural] = found_val

        def normalize_name(n: str) -> str:
            return n.lower().replace('.', '_').replace(' ', '_')

        # Render Bending Rules into a per-PC plaintext/markdown file where
        # occurrences like [[Air]] are replaced with the PC's variable values.
        try:
            rules_root = ROOT.joinpath('Player Root', 'Rules', 'Bending Rules')
            if rules_root.exists():
                token_re = re.compile(r"\[\[\s*([^\]]+)\s*\]\]")
                # ensure old single-file renderer is removed (legacy)
                try:
                    old_r = pc_dir.joinpath('Bending Rules - rendered.md')
                    if old_r.exists():
                        old_r.unlink()
                except Exception:
                    pass
                # create a per-PC Bending Rules folder with suffixed names
                br_root = pc_dir.joinpath(f"Bending Rules - {safe}")
                # remove existing folder to ensure clean regeneration
                try:
                    if br_root.exists():
                        shutil.rmtree(br_root)
                except Exception:
                    pass
                for p in sorted(rules_root.rglob('*.md')):
                    try:
                        rel = p.relative_to(rules_root)
                    except Exception:
                        rel = Path(p.name)
                    txt = p.read_text(encoding='utf-8')
                    # parse tags to decide if this move is learnable by the character
                    tags_in_file = {t.lower() for t in re.findall(r"#[-\w]+", txt)}
                    # Normalize element tags so variants like #spiritbending, #spirit-bending,
                    # or #spirit_bending are recognised as the 'spirit' element (same for others).
                    def _normalize_element_tag(tag: str) -> Optional[str]:
                        # tag is like '#spiritbending' or '#water' (lowercased)
                        if not tag or not tag.startswith('#'):
                            return None
                        core = tag[1:]
                        core = core.replace('-', '').replace('_', '')
                        # strip common suffix 'bending' if present
                        if core.endswith('bending'):
                            core = core[:-7]
                        core = core.strip()
                        if core in ('air', 'water', 'earth', 'fire', 'spirit'):
                            return core
                        return None

                    element_tags = []
                    for t in tags_in_file:
                        et = _normalize_element_tag(t)
                        if et and et not in element_tags:
                            element_tags.append(et)
                    level_re = re.compile(r"#level(\d+)(?:-(\d+))?", flags=re.I)
                    level_matches = level_re.findall(' '.join(tags_in_file))
                    if not element_tags or not level_matches:
                        # skip files that don't declare element and level tags
                        continue

                    satisfied_any = False
                    for elem in element_tags:
                        v = norm_kv.get(normalize_name(elem))
                        try:
                            vnum = float(v) if v is not None else 0.0
                        except Exception:
                            try:
                                vnum = float(to_number(v))
                            except Exception:
                                vnum = 0.0
                        for lm in level_matches:
                            lo = int(lm[0])
                            hi = int(lm[1]) if lm[1] else None
                            if hi is None:
                                if vnum >= lo:
                                    satisfied_any = True
                                    break
                            else:
                                if vnum >= lo and vnum <= hi:
                                    satisfied_any = True
                                    break
                        if satisfied_any:
                            break

                    if not satisfied_any:
                        continue

                    # perform token substitution (same behaviour as before)
                    def sub_token(m):
                        raw = m.group(1).strip()
                        nk = normalize_name(raw)
                        def _tags_for(name_norm: str):
                            if not secondary_tags:
                                return None
                            for stem, tags in secondary_tags.items():
                                try:
                                    if normalize_name(stem) == name_norm or stem == name_norm.replace('_', ' '):
                                        return tags
                                except Exception:
                                    continue
                            return secondary_tags.get(name_norm.replace('_', ' ')) or secondary_tags.get(name_norm)

                        try:
                            tags = _tags_for(nk)
                        except Exception:
                            tags = None
                        is_rollable = False
                        if tags:
                            is_rollable = any('roll' in t.lower() for t in tags)

                        if is_rollable:
                            tmpl = None
                            for k_tmpl in secondary_templates.keys():
                                try:
                                    if normalize_name(k_tmpl) == nk:
                                        tmpl = secondary_templates.get(k_tmpl)
                                        break
                                except Exception:
                                    continue
                            if tmpl is None:
                                tmpl = secondary_templates.get(raw) or secondary_templates.get(raw.title())
                            if tmpl:
                                token_pat = re.compile(r"\[\[\s*([^\]]+)\s*\]\]")
                                def _sub_inner(m2):
                                    raw2 = m2.group(1).strip()
                                    nk2 = normalize_name(raw2)
                                    val2 = norm_kv.get(nk2)
                                    if val2 is None:
                                        val2 = norm_kv.get(nk2.replace('_', '.')) or norm_kv.get(nk2.replace('.', '_'))
                                    if val2 is None:
                                        try:
                                            global_var = var_root.joinpath(re.sub(r"[^A-Za-z0-9_\-]", '_', raw2).lower() + '.md')
                                            if global_var.exists():
                                                m2g = re.search(r'```markdown\n(.*?)\n\n', global_var.read_text(encoding='utf-8'), flags=re.S)
                                                if m2g:
                                                    vv2 = m2g.group(1).strip()
                                                    return str(to_number(vv2))
                                        except Exception:
                                            pass
                                        return '0'
                                    return str(to_number(val2))

                                expr = token_pat.sub(_sub_inner, tmpl)
                                expr = re.sub(r"\s+", ' ', expr).strip()
                                # include the token's display name next to the roll expression
                                return f"{raw} ({expr})"

                        val = norm_kv.get(nk)
                        if val is None:
                            val = norm_kv.get(nk.replace('_', '.')) or norm_kv.get(nk.replace('.', '_'))
                        if val is None:
                            try:
                                global_var = var_root.joinpath(re.sub(r"[^A-Za-z0-9_\-]", '_', raw).lower() + '.md')
                                if global_var.exists():
                                    m2 = re.search(r'```markdown\n(.*?)\n\n', global_var.read_text(encoding='utf-8'), flags=re.S)
                                    if m2:
                                        vv = m2.group(1).strip()
                                        return f"{raw} ({to_number(vv)})"
                            except Exception:
                                pass
                            return f"{raw} (0)"
                        try:
                            vnum = to_number(val)
                        except Exception:
                            vnum = val
                        return f"{raw} ({vnum})"

                    rendered = token_re.sub(sub_token, txt)

                    # build target path inside per-PC bending rules folder
                    # Preserve the original folder structure under the rules root
                    # instead of flattening. Mirror subdirectories and append the
                    # PC-safe suffix to the filename so files remain unique per-PC.
                    if rel.parent and str(rel.parent) != '.':
                        target_dir = br_root.joinpath(rel.parent)
                    else:
                        target_dir = br_root
                    target_dir.mkdir(parents=True, exist_ok=True)
                    # create file name with suffix before extension
                    orig_fname = rel.name
                    stem = Path(orig_fname).stem
                    ext = Path(orig_fname).suffix
                    new_fname = f"{stem} - {safe}{ext}"
                    tgt_file = target_dir.joinpath(new_fname)
                    try:
                        tgt_file.write_text(rendered + '\n', encoding='utf-8')
                    except Exception:
                        # best-effort write; continue on failure
                        pass
        except Exception:
            # non-fatal; don't stop sheet generation if rules rendering fails
            pass

        # force-show rules: parse tags of the form #show_if_<var>_<op>_<n>
        # and evaluate them. We record the conditional in show_if_map and
        # add the stat to `force_show` only when the condition evaluates true.
        force_show: set = set()
        show_if_map: Dict[str, Tuple[str, str, int]] = {}
        show_if_re = re.compile(r'^#show_if_([a-z0-9]+)_(gt|ge|lt|le|eq)_([0-9]+)$')
        if secondary_tags:
            for stem, tags in secondary_tags.items():
                for t in tags:
                    m = show_if_re.match(t)
                    if not m:
                        continue
                    var, op, num = m.group(1), m.group(2), int(m.group(3))
                    norm_stem = normalize_name(stem)
                    show_if_map[norm_stem] = (var, op, num)
                    # lookup value in norm_kv using normalized forms
                    val = norm_kv.get(var) if var in norm_kv else norm_kv.get(var.replace('.', '_')) or norm_kv.get(var.replace('_', '.'))
                    try:
                        vnum = float(val)
                    except Exception:
                        try:
                            vnum = float(to_number(val))
                        except Exception:
                            vnum = 0.0
                    ok = False
                    if op == 'gt':
                        ok = vnum > num
                    elif op == 'ge':
                        ok = vnum >= num
                    elif op == 'lt':
                        ok = vnum < num
                    elif op == 'le':
                        ok = vnum <= num
                    elif op == 'eq':
                        ok = vnum == num
                    if ok:
                        force_show.add(norm_stem)

        suppressed_placeholders: set = set()

        def repl_placeholder(m):
            key = m.group(1).strip()
            nk = normalize_name(key)
            # If this placeholder is controlled by a #show_if and the
            # condition did not evaluate true, mark it suppressed and
            # return an empty string so the row can be removed later.
            try:
                if show_if_map and nk in show_if_map and nk not in force_show:
                    suppressed_placeholders.add(nk)
                    return ''
            except NameError:
                # show_if_map/force_show not defined yet; nothing to suppress
                pass
            val = norm_kv.get(nk)
            if val is None:
                val = norm_kv.get(nk.replace('_', '.'))
            # try common aliases (full names -> short keys)
            if val is None:
                alias_map = {
                    'strength': 'str',
                    'dexterity': 'dex',
                    'constitution': 'con',
                    'intelligence': 'int',
                    'wisdom': 'wis',
                    'charisma': 'cha',
                    'max_hp': 'max_hp',
                }
                if nk in alias_map:
                    val = norm_kv.get(alias_map[nk])
            # if unknown, leave placeholder intact so special tokens like {{PC}} can be replaced later
            return str(val) if val is not None else m.group(0)

        tpl_sub = re.sub(r'{{\s*([^}]+)\s*}}', repl_placeholder, tpl_raw_inner)

        orig_placeholders = set(re.findall(r'{{\s*([^}]+)\s*}}', tpl_raw_inner))
        orig_placeholders = {normalize_name(p) for p in orig_placeholders}

        # detect any placeholders left in the rendered template
        remaining_placeholders = re.findall(r'{{\s*([^}]+)\s*}}', tpl_sub)
        # auto-replace common token {{name}} with the character name
        for ph in list(remaining_placeholders):
            nk = normalize_name(ph)
            if nk == 'name':
                # replace all variants of the placeholder with the actual name
                tpl_sub = re.sub(r'{{\s*' + re.escape(ph) + r'\s*}}', name, tpl_sub)
        # recompute remaining after replacement
        remaining_placeholders = re.findall(r'{{\s*([^}]+)\s*}}', tpl_sub)
        warn_issued: set = set()
        for ph in remaining_placeholders:
            nk = normalize_name(ph)
            # skip placeholders we intentionally replace later (e.g., PC)
            if nk in ('pc',):
                continue
            # if this normalized key isn't present in the character variables, warn
            if nk not in norm_kv and nk not in warn_issued:
                # allow suppression list entries (normalized forms)
                if suppress_warnings and nk in suppress_warnings:
                    warn_issued.add(nk)
                    continue
                warn_issued.add(nk)
                print(f"WARNING: template placeholder '{{{{{ph}}}}}' not found in variables for PC '{name}'")

        def placeholders_in_section(marker: str) -> List[str]:
            parts = tpl_raw_inner.split(marker, 1)
            if len(parts) < 2:
                return []
            tail = parts[1]
            next_mark = '<!-- STATS_INSERT:'
            idx = tail.find(next_mark)
            if idx != -1:
                tail = tail[:idx]
            ph = re.findall(r'{{\s*([^}]+)\s*}}', tail)
            return [normalize_name(p) for p in ph]

        core_keys = placeholders_in_section('<!-- STATS_INSERT:core -->') or ['str', 'dex', 'con', 'int', 'wis', 'cha']
        vital_keys = placeholders_in_section('<!-- STATS_INSERT:vital -->') or ['max_hp', 'evasion', 'rolled_hp', 'rolled.hp']
        bending_keys = placeholders_in_section('<!-- STATS_INSERT:bending -->') or ['air', 'water', 'earth', 'fire', 'spirit']

        extras = {'core': [], 'vital': [], 'bending': [], 'other': []}

        def display_name(k: str) -> str:
            # expand common abbreviations
            mapping = {
                'str': 'Strength',
                'dex': 'Dexterity',
                'con': 'Constitution',
                'int': 'Intelligence',
                'wis': 'Wisdom',
                'cha': 'Charisma',
                'hp': 'HP',
                'max_hp': 'Max HP',
            }
            kn = k.replace('.', '_').replace(' ', '_').lower()
            if kn in mapping:
                return mapping[kn]
            k = k.replace('_', ' ').replace('.', ' ')
            words = k.split()
            out_words: List[str] = []
            for i, p in enumerate(words):
                if p.lower() in ('hp',):
                    out_words.append(p.upper())
                else:
                    if i == 0:
                        out_words.append(p.capitalize())
                    else:
                        out_words.append(p.lower())
            return ' '.join(out_words)

        # build a set of secondary templates that are tagged with #vitality or
        # #environmental_variable so those are still shown even when their
        # numeric value is zero
        vitality_set: set = set()
        if secondary_tags:
            for stem, tags in secondary_tags.items():
                if '#vitality' in tags or '#environmental_variable' in tags:
                    vitality_set.add(normalize_name(stem))

        # force-show rules: parse tags of the form #show_if_<var>_<op>_<n>
        # and add the stat to force_show when the condition evaluates true.
        # force-show rules: parse tags of the form #show_if_<var>_<op>_<n>
        # and evaluate them. We record the conditional in show_if_map and
        # add the stat to `force_show` only when the condition evaluates true.
        force_show: set = set()
        show_if_map: Dict[str, Tuple[str, str, int]] = {}
        show_if_re = re.compile(r'^#show_if_([a-z0-9]+)_(gt|ge|lt|le|eq)_([0-9]+)$')
        if secondary_tags:
            for stem, tags in secondary_tags.items():
                for t in tags:
                    m = show_if_re.match(t)
                    if not m:
                        continue
                    var, op, num = m.group(1), m.group(2), int(m.group(3))
                    norm_stem = normalize_name(stem)
                    show_if_map[norm_stem] = (var, op, num)
                    # lookup value in norm_kv using normalized forms
                    val = norm_kv.get(var) if var in norm_kv else norm_kv.get(var.replace('.', '_')) or norm_kv.get(var.replace('_', '.'))
                    try:
                        vnum = float(val)
                    except Exception:
                        try:
                            vnum = float(to_number(val))
                        except Exception:
                            vnum = 0.0
                    ok = False
                    if op == 'gt':
                        ok = vnum > num
                    elif op == 'ge':
                        ok = vnum >= num
                    elif op == 'lt':
                        ok = vnum < num
                    elif op == 'le':
                        ok = vnum <= num
                    elif op == 'eq':
                        ok = vnum == num
                    if ok:
                        force_show.add(norm_stem)
        if verbose:
            try:
                print(f"DEBUG: show_if_map keys={list(show_if_map.keys())}")
                print(f"DEBUG: force_show={sorted(list(force_show))}")
            except Exception:
                pass

        for nk, v in sorted(norm_kv.items()):
            # omit empty/None values; omit zeros unless the stat is in
            # vitality_set or explicitly force_shown (e.g., stress level when fire>=1)
            if v is None or v == '':
                continue
            # If this stat/template has a #show_if condition and it did not
            # evaluate true, skip showing it entirely (even when non-zero).
            try:
                if 'show_if_map' in locals() and nk in show_if_map and nk not in force_show:
                    # not eligible to be shown for this PC
                    continue
            except Exception:
                pass
            if v == 0 and nk not in vitality_set and nk not in force_show:
                continue
            if nk in orig_placeholders:
                continue
            if nk in core_keys:
                extras['core'].append(f'| {display_name(nk)} | {v} |')
            elif nk in vital_keys or (nk.startswith('max') and 'hp' in nk):
                extras['vital'].append(f'| {display_name(nk)} | {v} |')
            elif nk in bending_keys:
                extras['bending'].append(f'| {display_name(nk)} | {v} |')
            else:
                # skip adding suppressed stats to the 'other' appendix
                try:
                    nk_norm = normalize_name(nk)
                except Exception:
                    nk_norm = nk.lower().replace('.', '_').replace(' ', '_')
                if suppress_warnings and nk_norm in suppress_warnings:
                    # intentionally omit suppressed stat from extras['other']
                    continue
                extras['other'].append(f'| {display_name(nk)} | {v} |')

        lines = tpl_sub.splitlines()

        def insert_rows(marker: str, rows_to_add: List[str]):
            if not rows_to_add:
                return
            for i, line in enumerate(lines):
                if marker in line:
                    for j in range(i + 1, len(lines)):
                        if '---' in lines[j]:
                            insert_at = j + 1
                            for r_idx, r in enumerate(rows_to_add):
                                lines.insert(insert_at + r_idx, r)
                            return
                    for r_idx, r in enumerate(rows_to_add):
                        lines.insert(i + 1 + r_idx, r)
                    return

        insert_rows('<!-- STATS_INSERT:core -->', extras['core'])
        insert_rows('<!-- STATS_INSERT:vital -->', extras['vital'])
        insert_rows('<!-- STATS_INSERT:bending -->', extras['bending'])

        if extras['other']:
            inserted = False
            for i, line in enumerate(lines):
                if '<!-- STATS_INSERT:other -->' in line:
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip() == '':
                            insert_at = j + 1
                            for r_idx, r in enumerate(extras['other']):
                                lines.insert(insert_at + r_idx, r)
                            inserted = True
                            break
                    if not inserted:
                        for r_idx, r in enumerate(extras['other']):
                            lines.insert(i + 1 + r_idx, r)
                        inserted = True
                    break
            if not inserted:
                lines.append('')
                lines.append('> WARNING: The following character stats could not be placed by context and were appended:')
                for r in extras['other']:
                    lines.append(r)

        out_text = '\n'.join(lines) + '\n'
        # Remove any table rows where the value is numeric zero for
        # non-vital secondary stats. This handles placeholders that were
        # directly replaced in the template (e.g. | Foo | 0 |) so those
        # rows don't appear in the final sheet unless the stat is tagged
        # with #vitality.
        try:
            # build vitality set from secondary_tags (normalized names)
            vitality_set: set = set()
            if secondary_tags:
                for stem, tags in secondary_tags.items():
                    if '#vitality' in tags:
                        vitality_set.add(normalize_name(stem))

            for nk, v in sorted(norm_kv.items()):
                if v is None or v == '' or (v == 0 and normalize_name(nk) not in vitality_set and normalize_name(nk) not in force_show):
                    # if numeric zero and not vitality, remove matching table rows
                    try:
                        is_zero = float(v) == 0
                    except Exception:
                        is_zero = str(v).strip() in ('0', '0.0')
                    if is_zero and normalize_name(nk) not in vitality_set and normalize_name(nk) not in force_show:
                        dname = display_name(nk)
                        pat_row = re.compile(r"(?im)^\|\s*" + re.escape(dname) + r"\s*\|[^\n]*\n")
                        out_text, removed = pat_row.subn('', out_text)
                        if removed and verbose:
                            print(f"Removed {removed} table row(s) for zero-valued '{dname}' from sheet for {name}")
                        # fallback raw key and simple plural variants
                        d2 = nk.replace('_', ' ').replace('.', ' ')
                        pat_row2 = re.compile(r"(?im)^\|\s*" + re.escape(d2) + r"\s*\|[^\n]*\n")
                        out_text, removed2 = pat_row2.subn('', out_text)
                        if removed2 and verbose:
                            print(f"Removed {removed2} fallback table row(s) for zero-valued '{d2}' from sheet for {name}")
                        # also remove pluralized/display variants (e.g., 'Danger Sense Reaction' vs 'Danger Sense Reactions')
                        try:
                            d_plural = re.escape(dname) + r"s?"
                            pat_plural = re.compile(r"(?im)^\|\s*(?:" + d_plural + r")\s*\|[^\n]*\n")
                            out_text, remp = pat_plural.subn('', out_text)
                            if remp and verbose:
                                print(f"Removed {remp} pluralized table row(s) for '{dname}' from sheet for {name}")
                        except Exception:
                            pass
            # Also remove rows that still contain unreplaced placeholders like
            # {{Danger Sense Reaction Slot}} when the corresponding variable
            # value is numeric zero and the stat is not #vitality.
            try:
                phs = set(re.findall(r'{{\s*([^}]+)\s*}}', tpl_sub))
                for ph in phs:
                    nk = normalize_name(ph)
                    # try to find value in norm_kv using normalized forms
                    val = None
                    if nk in norm_kv:
                        val = norm_kv.get(nk)
                    else:
                        # try aliases and dotted/underscored variants
                        val = norm_kv.get(nk.replace('_', '.')) or norm_kv.get(nk.replace('.', '_'))
                    try:
                        is_zero = isinstance(val, (int, float)) and val == 0
                    except Exception:
                        try:
                            is_zero = float(val) == 0
                        except Exception:
                            is_zero = str(val).strip() in ('0', '0.0') if val is not None else False
                    if is_zero and nk not in vitality_set:
                        # remove any table row that includes the raw placeholder
                        raw_ph = '{{' + ph + '}}'
                        pat_ph_row = re.compile(r"(?im)^\|[^\n]*" + re.escape(raw_ph) + r"[^\n]*\n")
                        out_text, rem = pat_ph_row.subn('', out_text)
                        if rem and verbose:
                            print(f"Removed {rem} table row(s) containing placeholder '{{{{{ph}}}}}' from sheet for {name}")
                    # Also remove rows for placeholders suppressed by #show_if
                    if nk in suppressed_placeholders:
                        raw_ph = '{{' + ph + '}}'
                        pat_ph_row = re.compile(r"(?im)^\|[^\n]*" + re.escape(raw_ph) + r"[^\n]*\n")
                        out_text, rem2 = pat_ph_row.subn('', out_text)
                        if rem2 and verbose:
                            print(f"Removed {rem2} table row(s) containing suppressed placeholder '{{{{{ph}}}}}' from sheet for {name}")
            except Exception:
                pass
        except Exception:
            pass
        # Also remove any table rows for placeholders that were explicitly
        # suppressed by #show_if (these may have been removed from the
        # template earlier, so they won't appear in the placeholder-based
        # cleanup pass). Ensure rows named by the display name or raw key
        # are removed so suppressed variables don't show even when non-zero.
        try:
            for nk in suppressed_placeholders:
                dname = display_name(nk)
                raw_key = nk.replace('_', ' ').replace('.', ' ')
                # remove rows matching the nicely formatted display name
                pat_row = re.compile(r"(?im)^\|\s*" + re.escape(dname) + r"\s*\|[^\n]*\n")
                out_text, removed = pat_row.subn('', out_text)
                if removed and verbose:
                    print(f"Removed {removed} table row(s) for suppressed '{dname}' from sheet for {name}")
                # fallback: remove rows that use the raw key as the label
                pat_row2 = re.compile(r"(?im)^\|\s*" + re.escape(raw_key) + r"\s*\|[^\n]*\n")
                out_text, removed2 = pat_row2.subn('', out_text)
                if removed2 and verbose:
                    print(f"Removed {removed2} fallback row(s) for suppressed '{raw_key}' from sheet for {name}")
                # also remove any row that contains the raw key text (covers
                # placeholders or other variants that include the key)
                try:
                    pat_contains = re.compile(r"(?im)^\|[^\n]*" + re.escape(raw_key) + r"[^\n]*\n")
                    out_text, rem3 = pat_contains.subn('', out_text)
                    if rem3 and verbose:
                        print(f"Removed {rem3} table row(s) containing suppressed key '{raw_key}' from sheet for {name}")
                except Exception:
                    pass
        except Exception:
            pass
        out_text = out_text.replace('{{PC}}', name)
        # Normalize Vitals header: ensure '## Vitals' with a blank line after it
        try:
            out_text = re.sub(r'(?m)^##\s*Vitals.*$', '## Vitals\n\n', out_text)
        except Exception:
            pass
        sheet.write_text(out_text, encoding='utf-8')
    else:
        out_lines = [f'# {name} — Character Sheet', '']
        out_lines.append('## Stats')
        out_lines.append('')
        out_lines.append('| Stat | Value |')
        out_lines.append('|---|---:|')
        for k in sorted(kv_all.keys()):
            out_lines.append(f'| {k} | {kv_all[k]} |')
        out_text = '\n'.join(out_lines) + '\n'
        sheet.write_text(out_text, encoding='utf-8')

    if verbose:
        try:
            preview_lines = out_text.splitlines()[:10]
            print(f"--- Sheet written: {sheet} ---")
            try:
                mirror_preview = target_root
            except Exception:
                mirror_preview = pc_dir.joinpath(f'{safe}_variable')
            print(f"Variables: {len(kv_all)}  Mirror-dir: {mirror_preview}")
            for L in preview_lines:
                print(L)
            if len(out_text.splitlines()) > len(preview_lines):
                print('... (preview truncated)')
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description='Recreate PCs from primary stats')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print verbose per-stat calculations')
    parser.add_argument('--pc', '-p', help='Only generate for this PC name (case-insensitive)')
    parser.add_argument('--create-placeholders', action='store_true', help='Create minimal #variable placeholder files for missing referenced variables')
    parser.add_argument('--vault-folder', '-V', help='Use the first repository folder matching this name as the vault root (use its `variable/` subfolder)')
    parser.add_argument('--propagate-variable', '-P', help='Only regenerate PCs affected by this variable (stem or filename without .md)')
    args = parser.parse_args()

    header, rows = parse_markdown_table(INPUT_TABLE)
    if not header or not rows:
        print('No table found at', INPUT_TABLE)
        return
    hdr_norm = [h.strip().lower() for h in header]
    primary_names = load_primary_names(PRIMARY_TEMPLATES_DIR)
    secondary_templates = load_secondary_templates(SECONDARY_TEMPLATES_DIR)
    primary_tags = load_template_tags(PRIMARY_TEMPLATES_DIR)
    secondary_tags = load_template_tags(SECONDARY_TEMPLATES_DIR)
    # Also load environmental templates and include them alongside secondary templates
    environmental_templates = load_environmental_templates(ENVIRONMENTAL_TEMPLATES_DIR)
    environmental_tags = load_template_tags(ENVIRONMENTAL_TEMPLATES_DIR)
    # Merge environmental templates into secondary_templates (env should override if duplicate)
    for k, v in environmental_templates.items():
        secondary_templates[k] = v
    # Merge tags: combine tag lists when keys overlap
    for k, tags in (environmental_tags or {}).items():
        if k in secondary_tags and isinstance(secondary_tags[k], list):
            # append any tags not already present
            for t in tags:
                if t not in secondary_tags[k]:
                    secondary_tags[k].append(t)
        else:
            secondary_tags[k] = list(tags)

    # Load optional suppression list at repo root. Each non-empty, non-comment
    # line is normalized and added to the suppress set. This file allows
    # disabling spurious "not found" or "could not be evaluated" warnings
    # for known variable/placeholders used by the character sheet generator.
    suppress_set: set = set()
    sup_path = ROOT.joinpath('supress_warning_character_sheet_generator.md')
    try:
        if sup_path.exists():
            for ln in sup_path.read_text(encoding='utf-8').splitlines():
                s = ln.strip()
                if not s or s.startswith('#'):
                    continue
                # strip common markdown list markers or leading bullets/numbers
                s = re.sub(r'^[\-\*\+\d\.)\s]+', '', s)
                if not s:
                    continue
                # normalize similar to other checks: lowercase, non-alnum -> '_'
                norm = re.sub(r'[^A-Za-z0-9_]', '_', s).lower()
                # canonical underscore form
                suppress_set.add(norm)
                # dot variant (some code uses dots)
                suppress_set.add(norm.replace('_', '.'))
                # space variant (human-friendly)
                suppress_set.add(norm.replace('_', ' '))
                # also add singular/plural variants to cover common mismatches
                try:
                    if norm.endswith('s'):
                        singular = norm[:-1]
                        plural = norm
                    else:
                        singular = norm
                        plural = norm + 's'
                    for v in (singular, plural):
                        suppress_set.add(v)
                        suppress_set.add(v.replace('_', '.'))
                        suppress_set.add(v.replace('_', ' '))
                except Exception:
                    pass
    except Exception:
        # non-fatal: continue without suppressions
        suppress_set = set()

    pcs: List[Tuple[str, Dict[str, Any]]] = []
    propagate_var = args.propagate_variable.strip() if getattr(args, 'propagate_variable', None) else None
    affected_templates: List[str] = []
    if propagate_var:
        # find which templates reference this variable
        affected_templates = templates_referencing_var(propagate_var, secondary_templates)
        if not affected_templates:
            print(f"No templates reference variable '{propagate_var}'. Nothing to do.")
            return
        print(f"Propagating variable '{propagate_var}' -> affected templates: {affected_templates}")
    variable_root = get_variable_root(foldername=args.vault_folder if hasattr(args, 'vault_folder') else None)
    if variable_root is None:
        print("ERROR: Could not determine variable root from a Root.md declaring the vault.\nRefusing to continue to avoid writing into internal Mycelium folders.\nPlease add a Root.md whose first non-comment line is the vault path (for example: 'Player Root') and ensure a 'variable' subfolder exists.")
        sys.exit(1)
    for r in rows:
        if len(r) < len(hdr_norm):
            r += [''] * (len(hdr_norm) - len(r))
        data = dict(zip(hdr_norm, r))
        name = name_from_cell(data.get('name', 'Unknown'))
        if args.pc:
            if name.lower() != args.pc.strip().lower():
                continue
        run = data.get('run update', '').strip().lower()
        if not args.pc and run not in ('yes', 'y', 'true'):
            continue
        kv: Dict[str, Any] = {}
        for k, v in data.items():
            key = k.strip().lower()
            if key == 'name' or key == 'run update':
                continue
            if 'manually' in key and 'hp' in key:
                key_out = 'rolled.hp'
            elif key == 'riz':
                key_out = 'cha'
            else:
                key_out = key
            key_out = key_out.replace(' ', '.').replace('/', '.')
            kv[key_out] = to_number(v)
            if args.verbose:
                print(f"primary: {key_out} = {kv[key_out]!r}")
        for s in ['str','dex','con','int','wis','cha','water','earth','air','fire','spirit','rolled.hp']:
            kv.setdefault(s, 0)
        known = set(primary_names) | set(secondary_templates.keys())
        # determine which secondary templates are marked #rollable so the
        # evaluator can suppress non-numeric-evaluation warnings for them
        rollable_set = set()
        try:
            if secondary_tags:
                for stem, tags in secondary_tags.items():
                    # treat either '#rollable' or shorthand '#roll' (and variants)
                    # as indicators that the template intentionally contains
                    # dice notation and should not emit non-evaluable warnings.
                    tag_lowers = [t.lower() for t in tags]
                    if any('roll' in t for t in tag_lowers):
                        rollable_set.add(stem.lower())
        except Exception:
            rollable_set = set()

        kv_all = compute_secondaries(kv, secondary_templates, verbose=args.verbose, known_vars=known, pc_name=name, create_placeholders=args.create_placeholders, placeholder_dir=variable_root, rollable_set=rollable_set, suppress_warnings=suppress_set)
        for kk, vv in kv.items():
            kv_all.setdefault(kk.lower(), vv)
        if propagate_var:
            # decide if this PC is affected: any affected template stem present in kv_all
            kset = set(kv_all.keys())
            is_affected = False
            for stem in affected_templates:
                cand1 = stem.lower()
                cand2 = stem.lower().replace('_', '.')
                cand3 = stem.lower().replace('.', '_')
                if cand1 in kset or cand2 in kset or cand3 in kset:
                    is_affected = True
                    break
            if is_affected:
                pcs.append((name, kv_all))
        else:
            pcs.append((name, kv_all))

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    for name, kv_all in pcs:
        write_character_files(name, kv_all, primary_names, secondary_templates, OUT_ROOT, var_root=variable_root, primary_tags=primary_tags, secondary_tags=secondary_tags, verbose=args.verbose, suppress_warnings=suppress_set)
        print('Wrote', name)


if __name__ == '__main__':
    main()

