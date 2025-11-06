#!/usr/bin/env python3
"""Recreate NPCs from Dms Root/Npc_primary_stats.md.

Reads primary stats, loads secondary templates tagged with #secondary_stat,
recalculates secondaries iteratively, overwrites per-character variable files
under `Dms Root/NPCs/<Name>/` and writes a `<Name> character sheet.md`.

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
        dedupe_variable_items as _dedupe_variable_items,
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
            dedupe_variable_items as _dedupe_variable_items,
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
            _dedupe_variable_items = getattr(mod, 'dedupe_variable_items', None)
        else:
            _to_number = _safe_eval = _parse_markdown_table = _name_from_cell = _get_variable_root = _load_secondary_templates = _load_template_tags = _display_name_for = _pc_safe = _dedupe_variable_items = None

if _dedupe_variable_items is None:
    def _dedupe_variable_items(items: Dict[str, Any]):
        return sorted(items.items())


# Find repository root by looking for .git directory
_script_path = Path(__file__).resolve()
ROOT = _script_path
while ROOT.parent != ROOT:
    if (ROOT / '.git').exists():
        break
    ROOT = ROOT.parent
# If no .git found, fall back to 3 levels up from script (Mycelium/scripts/Python -> repo root)
if not (ROOT / '.git').exists():
    ROOT = _script_path.parent.parent.parent


def get_variable_root(foldername: Optional[str] = None) -> Optional[Path]:
    """Get the Dms Root variable folder for NPCs.
    
    This function is specifically for NPC generation and always uses Dms Root,
    ignoring Root.md to keep PC and NPC generation completely separate.

    Returns the directory containing the Dms Root's `variable` folder.
    """
    # Always use Dms Root for NPCs - do not use Root.md or Player Root
    dms_var = ROOT.joinpath('Dms Root', 'variable')
    dms_var.mkdir(parents=True, exist_ok=True)
    return dms_var


INPUT_TABLE = ROOT.joinpath('Dms Root', 'Npc_primary_stats.md')
# Read templates from Player Root but write NPC files to Dms Root
PLAYER_VAR_ROOT = ROOT.joinpath('Player Root', 'variable')
PRIMARY_TEMPLATES_DIR = PLAYER_VAR_ROOT.joinpath('primary_stat')
SECONDARY_TEMPLATES_DIR = PLAYER_VAR_ROOT.joinpath('secondary_stat')
ENVIRONMENTAL_TEMPLATES_DIR = PLAYER_VAR_ROOT.joinpath('environmental')
# Write location for NPC variables stays in Dms Root
DMS_VAR_ROOT = ROOT.joinpath('Dms Root', 'variable')
DMS_VAR_ROOT.mkdir(parents=True, exist_ok=True)
OUT_ROOT = ROOT.joinpath('Dms Root', 'NPCs')


def parse_markdown_table(path: Path) -> Tuple[List[str], List[List[str]]]:
    txt = path.read_text(encoding='utf-8')
    lines = [l.rstrip() for l in txt.splitlines()]

    # Find the first markdown table: header row followed by a separator row with dashes
    for i in range(len(lines) - 1):
        if '|' in lines[i] and re.search(r"\|\s*-{1,}\s*\|", lines[i + 1]):
            header = [c.strip() for c in lines[i].split('|') if c.strip()]
            rows = []
            for j in range(i + 2, len(lines)):
                if '|' not in lines[j]:
                    break
                row = [c.strip() for c in lines[j].split('|') if c.strip() or lines[j].startswith('|')]
                if row:
                    rows.append(row)
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
            return to_number(m.group())
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
            left = _eval(n.left)
            right = _eval(n.right)
            op = _allowed_binops.get(type(n.op))
            if op:
                return op(left, right)
            raise ValueError('unsupported binop')
        if isinstance(n, ast.UnaryOp):
            operand = _eval(n.operand)
            op = _allowed_unary.get(type(n.op))
            if op:
                return op(operand)
            raise ValueError('unsupported unaryop')
        if isinstance(n, ast.Call):
            raise ValueError('function calls not allowed')
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
            # If first line is empty, try to find formula in code blocks
            code_blocks = re.findall(r'(?:```|~~~)(.*?)(?:```|~~~)', txt, flags=re.S)
            for block in code_blocks:
                block_lines = [l.strip() for l in block.splitlines() if l.strip() and not l.strip().startswith('#')]
                if block_lines:
                    formula = block_lines[0]
                    break
        if not formula:
            continue
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
            # try code blocks
            code_blocks = re.findall(r'(?:```|~~~)(.*?)(?:```|~~~)', txt, flags=re.S)
            for block in code_blocks:
                block_lines = [l.strip() for l in block.splitlines() if l.strip() and not l.strip().startswith('#')]
                if block_lines:
                    formula = block_lines[0]
                    break
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
            ref = m.strip().lower()
            ref = re.sub(r'[^A-Za-z0-9_]', '_', ref)
            refs.append(ref)
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
            if stem not in seen_set and cur in refs:
                queue.append(stem)

    return result


# Prefer shared implementations from common.py when available to reduce duplication.
# These assignments override the local functions above with the shared ones.
# NOTE: Do NOT override get_variable_root since it relies on our local ROOT variable
try:
    to_number = _to_number
    safe_eval = _safe_eval
    parse_markdown_table = _parse_markdown_table
    name_from_cell = _name_from_cell
    # get_variable_root = _get_variable_root  # Keep local version that uses correct ROOT
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


def compute_secondaries(kv: Dict[str, Any], templates: Dict[str, str], passes: int = 6, verbose: bool = False, known_vars: Optional[set] = None, npc_name: Optional[str] = None, create_placeholders: bool = False, placeholder_dir: Optional[Path] = None, rollable_set: Optional[set] = None, suppress_warnings: Optional[set] = None) -> Dict[str, Any]:
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
            print(f"Pass {pass_no}")
        for name, formula in templates.items():
            name_lower = name.lower()
            # Don't skip already-computed values - they may need recomputation if their dependencies changed
            # Replace [[Variable]] tokens with their values
            def repl(m):
                var = m.group(1).strip()
                var_lower = var.lower().replace(' ', '.').replace('_', '.')
                if var_lower in kv_local:
                    val = kv_local[var_lower]
                    return str(val)
                var_norm = _norm_to_dot(var)
                if var_norm not in known_dot and var_norm not in missing_vars:
                    missing_vars.add(var_norm)
                return m.group(0)
            expanded = pattern.sub(repl, formula)
            
            # replace bare tokens (like 'earth' or 'max_hp') with known numeric values
            word_pat = re.compile(r"\b([A-Za-z][A-Za-z0-9_ ]*)\b")
            def sub_word(m):
                raw = m.group(1).strip()
                tok = raw.lower().replace(' ', '.').replace('_', '.')
                if tok in kv_local:
                    return str(kv_local.get(tok, 0))
                return m.group(0)

            expanded = word_pat.sub(sub_word, expanded)
            
            try:
                result = safe_eval(expanded)
                # Check if rollable (contains dice notation like 1d6, 2d8, etc.)
                is_rollable = bool(re.search(r'\d+d\d+', expanded.lower()))
                if is_rollable or (rollable_set and name_lower in rollable_set):
                    # For rollable stats, store the formula as-is if it couldn't be evaluated to a number
                    if not isinstance(result, (int, float)):
                        result = expanded
                if isinstance(result, (int, float)) or isinstance(result, str):
                    kv_local[name_lower] = result
                    changed = True
                    if verbose:
                        print(f"  {name} = {result}")
            except Exception as e:
                if verbose:
                    print(f"  {name} could not be evaluated: {e}")
        if not changed:
            break
    return kv_local


def write_character_files(name: str, kv_all: Dict[str, Any], primary_names: List[str], secondary_templates: Dict[str, str], out_root: Path, var_root: Optional[Path] = None, primary_tags: Optional[Dict[str, List[str]]] = None, secondary_tags: Optional[Dict[str, List[str]]] = None, verbose: bool = False, suppress_warnings: Optional[set] = None, subfolder: Optional[str] = None) -> None:
    safe = re.sub(r"[^A-Za-z0-9_\-]", '_', name)
    tag_suffix = f"_{safe}"
    tag_suffix_lower = tag_suffix.lower()
    tag_pattern = re.compile(r'(?<!\w)#([A-Za-z0-9][A-Za-z0-9_\-]*)')

    def append_npc_tag_suffix(text: str) -> str:
        def _replace_tag(m):
            tag_name = m.group(1).lower()
            if tag_name.endswith(tag_suffix_lower):
                return m.group(0)
            return f'#{m.group(1)}{tag_suffix}'

        return tag_pattern.sub(_replace_tag, text)

    # If subfolder is specified, create the NPC folder inside that subfolder
    if subfolder and subfolder.strip():
        npc_dir = out_root.joinpath(subfolder.strip(), safe)
    else:
        npc_dir = out_root.joinpath(safe)
    npc_dir.mkdir(parents=True, exist_ok=True)

    # write per-stat variable files into the global variable root (if available)
    if var_root is None:
        # fallback to previous behaviour: create mirror folder per-NPC
        mirror = npc_dir.joinpath(f"{safe}_variable")
        mirror.mkdir(parents=True, exist_ok=True)
        target_root = mirror
    else:
        # create a per-character subfolder inside a dedicated NPC_variables folder
        target_root = var_root.joinpath('NPC_variables', safe)
        # delete existing folder to ensure clean regeneration
        try:
            if target_root.exists():
                shutil.rmtree(target_root)
        except Exception:
            pass
        target_root.mkdir(parents=True, exist_ok=True)
    
    # Preserve any templates tagged with #current_variable (or #current_variable_<charactername>) 
    # by reading existing character sheet values and injecting them into kv_all so they survive
    # regeneration. secondary_tags keys are template stems (lowercased).
    try:
        cur_keys: List[str] = []
        if secondary_tags:
            for stem, tags in secondary_tags.items():
                for t in tags:
                    if t.startswith('#current_variable'):
                        cur_keys.append(stem)
                        break
        existing_sheet = npc_dir.joinpath(f"{safe} character sheet.md")
        if cur_keys and existing_sheet.exists():
            sheet_txt = existing_sheet.read_text(encoding='utf-8')
            for ck in cur_keys:
                # Try to extract the value from the existing sheet
                # Look for patterns like "**stat_name**: value"
                pattern = re.compile(rf'\*\*{re.escape(ck)}\*\*:\s*([^\n]+)', re.IGNORECASE)
                m = pattern.search(sheet_txt)
                if m:
                    preserved_val = m.group(1).strip()
                    kv_all[ck.lower()] = preserved_val
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
            tags = list(primary_tags[key])
            tags = [append_npc_tag_suffix(t) for t in tags]
        # add required tags with character name suffix (always, to track which character generated this)
        for req in ('#variable_', '#character_stat_', '#character_stats_', '#primary_stat_', '#npc_stat_'):
            tags.append(req + safe)
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
            tags = list(secondary_tags[key])
            tags = [append_npc_tag_suffix(t) for t in tags]
        # add required tags with character name suffix (always, to track which character generated this)
        for req in ('#variable_', '#character_stat_', '#character_stats_', '#secondary_stat_', '#npc_stat_'):
            tags.append(req + safe)
        # If this secondary stat evaluates to numeric zero, skip creating the
        # per-NPC variable file unless the template is explicitly tagged with
        # #vitality or #defensive. This keeps most zero-valued secondaries out
        # of the variables folder while ensuring key defensive/vital stats stay
        # present even when their value is currently 0.
        try:
            num_val = to_number(val)
        except Exception:
            num_val = None
        # If this secondary is numeric zero, skip creating the per-NPC file
        # unless the template is tagged with #vitality, #defensive or
        # #environmental_variable (environmental variables should still be
        # shown even when 0).
        if num_val == 0 and isinstance(val, (int, float)):
            tag_strs = [t.lower() for t in tags]
            if not any(t in tag_strs for t in ['#vitality', '#defensive', '#environmental_variable', '#environmental_variables', '#environmental']):
                continue

        fpath.write_text(f'```markdown\n{val}\n\n{" ".join(tags)}\n\n```\n', encoding='utf-8')

    # Render Bending Rules into a per-NPC plaintext/markdown file where
    # occurrences like [[Air]] are replaced with the NPC's variable values.
    try:
        # Check both Player Root and Dms Root for bending rules
        rules_root_player = ROOT.joinpath('Player Root', 'Rules', 'Bending Rules')
        rules_root_dms = ROOT.joinpath('Dms Root', 'Rules', 'Bending Rules')
        rules_root = rules_root_dms if rules_root_dms.exists() else rules_root_player
        
        if rules_root.exists():
            # normalize known vars for lookups
            norm_kv = {k.lower().replace('.', '_').replace(' ', '_'): v for k, v in kv_all.items()}
            
            # Canonical mapping for environmental variables
            if secondary_tags:
                for stem, tags in secondary_tags.items():
                    if '#environmental_variable' in tags:
                        sname = stem.replace('.', '_').replace(' ', '_').lower()
                        if sname.endswith('s'):
                            singular = sname[:-1]
                            plural = sname
                        else:
                            singular = sname
                            plural = sname + 's'
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
            
            token_re = re.compile(r"\[\[\s*([^\]]+)\s*\]\]")
            
            def render_rule_content(source_text: str) -> str:
                """Replace tokens like [[Stat]] with rendered values for this NPC."""
                
                def sub_token(m):
                    raw = m.group(1).strip()
                    nk = normalize_name(raw)
                    
                    def _tags_for(name_norm: str):
                        if secondary_tags:
                            for stem, tags in secondary_tags.items():
                                if normalize_name(stem) == name_norm:
                                    return tags
                        return []
                    
                    try:
                        tags = _tags_for(nk)
                    except Exception:
                        tags = []
                    is_rollable = False
                    if tags:
                        is_rollable = any('roll' in t.lower() for t in tags)
                    
                    if is_rollable:
                        # For rollable stats, preserve the formula/dice notation with value
                        val = norm_kv.get(nk)
                        if val is None:
                            val = norm_kv.get(nk.replace('_', '.'))
                        if val is None:
                            for k, v in norm_kv.items():
                                if normalize_name(k) == nk:
                                    val = v
                                    break
                        if val is not None and isinstance(val, str) and re.search(r'\d+d\d+', val.lower()):
                            # preserve wikilink format with dice expression
                            return f"[[{raw}]] ({val})"
                    
                    val = norm_kv.get(nk)
                    if val is None:
                        val = norm_kv.get(nk.replace('_', '.')) or norm_kv.get(nk.replace('.', '_'))
                    if val is None:
                        try:
                            # try to find in global variable files
                            global_var = var_root.joinpath(re.sub(r"[^A-Za-z0-9_\-]", '_', raw).lower() + '.md') if var_root else None
                            if global_var and global_var.exists():
                                m2 = re.search(r'```markdown\n(.*?)\n\n', global_var.read_text(encoding='utf-8'), flags=re.S)
                                if m2:
                                    vv = m2.group(1).strip()
                                    # preserve wikilink format
                                    return f"[[{raw}]] ({to_number(vv)})"
                        except Exception:
                            pass
                        # preserve wikilink format
                        return f"[[{raw}]] (0)"
                    try:
                        vnum = to_number(val)
                    except Exception:
                        vnum = val
                    # preserve wikilink format
                    return f"[[{raw}]] ({vnum})"
                
                return append_npc_tag_suffix(token_re.sub(sub_token, source_text))
            
            # ensure old single-file renderer is removed (legacy)
            try:
                old_r = npc_dir.joinpath('Bending Rules - rendered.md')
                if old_r.exists():
                    old_r.unlink()
            except Exception:
                pass
            
            # create a per-NPC Bending Rules folder with suffixed names
            br_root = npc_dir.joinpath(f"Bending Rules - {safe}")
            # remove existing folder to ensure clean regeneration
            try:
                if br_root.exists():
                    shutil.rmtree(br_root)
            except Exception:
                pass
            
            category_tags = {
                '#action': 'Action',
                '#bonus_action': 'Bonus Action',
                '#reaction': 'Reaction',
                '#danger_sense_reaction': 'Danger Sense Reaction',
            }
            action_type_root = None
            
            for p in sorted(rules_root.rglob('*.md')):
                try:
                    rel = p.relative_to(rules_root)
                except Exception:
                    continue
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
                
                if '#signature_move' in tags_in_file:
                    npc_tag = f"#{normalize_name(name)}"
                    if npc_tag not in tags_in_file:
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
                
                rendered = render_rule_content(txt)
                matched_categories = [category_tags[t] for t in category_tags.keys() if t in tags_in_file]
                
                # build target path inside per-NPC bending rules folder
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
                    tgt_file.write_text(rendered, encoding='utf-8')
                except Exception:
                    pass
                
                # Additionally copy move into action-based folders when tagged
                if matched_categories:
                    if action_type_root is None:
                        action_type_root = npc_dir.joinpath(f"Bending Moves by Action Type - {safe}")
                        action_type_root.mkdir(parents=True, exist_ok=True)
                    for cat in matched_categories:
                        cat_dir = action_type_root.joinpath(cat)
                        cat_dir.mkdir(parents=True, exist_ok=True)
                        cat_file = cat_dir.joinpath(new_fname)
                        try:
                            cat_file.write_text(rendered, encoding='utf-8')
                        except Exception:
                            pass
    except Exception:
        # non-fatal; don't stop sheet generation if rules rendering fails
        pass
    
    # write a character sheet using the template if available
    sheet = npc_dir.joinpath(f"{safe} character sheet.md")
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

        # Canonical mapping for environmental variables
        if secondary_tags:
            for stem, tags in secondary_tags.items():
                if '#environmental_variable' in tags:
                    sname = stem.replace('.', '_').replace(' ', '_').lower()
                    if sname.endswith('s'):
                        singular = sname[:-1]
                        plural = sname
                    else:
                        singular = sname
                        plural = sname + 's'
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

        # build vitality/defensive set for later use
        vitality_set: set = set()
        if secondary_tags:
            for stem, tags in secondary_tags.items():
                if '#vitality' in tags or '#defensive' in tags or '#environmental_variable' in tags:
                    vitality_set.add(normalize_name(stem))

        # force-show rules: parse tags of the form #show_if_<var>_<op>_<n>
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
                    val = norm_kv.get(var) if var in norm_kv else norm_kv.get(var.replace('.', '_')) or norm_kv.get(var.replace('_', '.'))
                    try:
                        vnum = float(val) if val is not None else 0.0
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
            # If this placeholder is controlled by a #show_if and condition not met, suppress it
            try:
                if show_if_map and nk in show_if_map and nk not in force_show:
                    suppressed_placeholders.add(nk)
                    return ''
            except NameError:
                pass
            val = norm_kv.get(nk)
            if val is None:
                val = norm_kv.get(nk.replace('_', '.'))
            # try common aliases
            if val is None:
                alias_map = {
                    'strength': 'str', 'dexterity': 'dex', 'constitution': 'con',
                    'intelligence': 'int', 'wisdom': 'wis', 'charisma': 'cha',
                    'max_hp': 'max_hp',
                }
                if nk in alias_map:
                    val = norm_kv.get(alias_map[nk])
            return str(val) if val is not None else m.group(0)

        tpl_sub = re.sub(r'{{\s*([^}]+)\s*}}', repl_placeholder, tpl_raw_inner)

        orig_placeholders = set(re.findall(r'{{\s*([^}]+)\s*}}', tpl_raw_inner))
        orig_placeholders = {normalize_name(p) for p in orig_placeholders}

        # detect remaining placeholders and warn if needed
        remaining_placeholders = re.findall(r'{{\s*([^}]+)\s*}}', tpl_sub)
        for ph in list(remaining_placeholders):
            nk = normalize_name(ph)
            if nk == 'name':
                tpl_sub = re.sub(r'{{\s*' + re.escape(ph) + r'\s*}}', name, tpl_sub)
        remaining_placeholders = re.findall(r'{{\s*([^}]+)\s*}}', tpl_sub)
        warn_issued: set = set()
        for ph in remaining_placeholders:
            nk = normalize_name(ph)
            if nk in ('pc',):
                continue
            if nk not in norm_kv and nk not in warn_issued:
                if suppress_warnings and nk in suppress_warnings:
                    warn_issued.add(nk)
                    continue
                warn_issued.add(nk)
                print(f"WARNING: template placeholder '{{{{{ph}}}}}' not found in variables for NPC '{name}'")

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
            mapping = {
                'str': 'Strength', 'dex': 'Dexterity', 'con': 'Constitution',
                'int': 'Intelligence', 'wis': 'Wisdom', 'cha': 'Charisma',
                'hp': 'HP', 'max_hp': 'Max HP',
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

        for nk, v in sorted(norm_kv.items()):
            if v is None or v == '':
                continue
            try:
                if 'show_if_map' in locals() and nk in show_if_map and nk not in force_show:
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
                try:
                    nk_norm = normalize_name(nk)
                except Exception:
                    nk_norm = nk.lower().replace('.', '_').replace(' ', '_')
                if suppress_warnings and nk_norm in suppress_warnings:
                    continue
                extras['other'].append(f'| {display_name(nk)} | {v} |')

        lines = tpl_sub.splitlines()

        def insert_rows(marker: str, rows_to_add: List[str]):
            if not rows_to_add:
                return
            for i, line in enumerate(lines):
                if marker in line:
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip() and not lines[j].strip().startswith('|'):
                            break
                    for r_idx, r in enumerate(rows_to_add):
                        lines.insert(j + r_idx, r)
                    return

        insert_rows('<!-- STATS_INSERT:core -->', extras['core'])
        insert_rows('<!-- STATS_INSERT:vital -->', extras['vital'])
        insert_rows('<!-- STATS_INSERT:bending -->', extras['bending'])

        if extras['other']:
            inserted = False
            for i, line in enumerate(lines):
                if '<!-- STATS_INSERT:other -->' in line:
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip() and not lines[j].strip().startswith('|'):
                            break
                    if not inserted:
                        for r in extras['other']:
                            lines.insert(j, r)
                        inserted = True
                    break
            if not inserted:
                lines.append('')
                lines.append('> WARNING: The following character stats could not be placed by context and were appended:')
                for r in extras['other']:
                    lines.append(r)

        out_text = '\n'.join(lines) + '\n'
        
        # Remove rows for suppressed placeholders
        try:
            for nk in suppressed_placeholders:
                dname = display_name(nk)
                raw_key = nk.replace('_', ' ').replace('.', ' ')
                pat_row = re.compile(r"(?im)^\|\s*" + re.escape(dname) + r"\s*\|[^\n]*\n")
                out_text, removed = pat_row.subn('', out_text)
                if removed and verbose:
                    print(f"Removed {removed} table row(s) for suppressed '{dname}' from sheet for {name}")
                pat_row2 = re.compile(r"(?im)^\|\s*" + re.escape(raw_key) + r"\s*\|[^\n]*\n")
                out_text, removed2 = pat_row2.subn('', out_text)
                if removed2 and verbose:
                    print(f"Removed {removed2} fallback row(s) for suppressed '{raw_key}' from sheet for {name}")
        except Exception:
            pass
        
        # Replace [[...]] wikilink-style references with their actual values
        # This handles cases where {{current_hp}} resolves to [[max_hp]] and we need to show the value
        def replace_wikilink(m):
            var = m.group(1).strip()
            var_lower = var.lower().replace(' ', '_').replace('.', '_')
            val = norm_kv.get(var_lower)
            if val is None:
                val = norm_kv.get(var_lower.replace('_', '.'))
            if val is None:
                # try common aliases
                alias_map = {
                    'strength': 'str', 'dexterity': 'dex', 'constitution': 'con',
                    'intelligence': 'int', 'wisdom': 'wis', 'charisma': 'cha',
                    'max_hp': 'max_hp', 'maxhp': 'max_hp',
                }
                if var_lower in alias_map:
                    val = norm_kv.get(alias_map[var_lower])
            # If we have a value, return it; otherwise keep the wikilink for player reference
            return str(val) if val is not None else m.group(0)
        
        wikilink_pattern = re.compile(r'\[\[([^\]]+)\]\]')
        out_text = wikilink_pattern.sub(replace_wikilink, out_text)
        
        out_text = out_text.replace('{{PC}}', name)
        out_text = out_text.replace('{{NPC}}', name)
        
        # Normalize Vitals header
        try:
            out_text = re.sub(r'(?m)^##\s*Vitals.*$', '## Vitals\n\n', out_text)
        except Exception:
            pass
        
        sheet.write_text(out_text, encoding='utf-8')
    else:
        # Create a simple character sheet with all stats
        lines = [f"# {name} Character Sheet\n"]
        lines.append("\n## Primary Stats\n")
        for p in primary_names:
            key = p.lower()
            val = kv_all.get(key, 0)
            lines.append(f"**{p}**: {val}\n")
        lines.append("\n## Secondary Stats\n")
        for p in sorted(secondary_templates.keys()):
            key = p.lower()
            if key in kv_all:
                val = kv_all[key]
                lines.append(f"**{p}**: {val}\n")
        out_text = '\n'.join(lines)
        sheet.write_text(out_text, encoding='utf-8')

    if verbose:
        print(f"Wrote character sheet to: {sheet}")
        print(f"Variable files written to: {target_root}")


def main() -> None:
    parser = argparse.ArgumentParser(description='Recreate NPCs from primary stats')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print verbose per-stat calculations')
    parser.add_argument('--npc', '-n', help='Only generate for this NPC name (case-insensitive)')
    parser.add_argument('--create-placeholders', action='store_true', help='Create minimal #variable placeholder files for missing referenced variables')
    parser.add_argument('--propagate-variable', '-P', help='Only regenerate NPCs affected by this variable (stem or filename without .md)')
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
            secondary_tags[k] = tags

    # Load optional suppression list at repo root. Each non-empty, non-comment
    # line is normalized and added to the suppress set. This file allows
    # disabling spurious "not found" or "could not be evaluated" warnings
    # for known variable/placeholders used by the character sheet generator.
    suppress_set: set = set()
    sup_path = ROOT.joinpath('supress_warning_character_sheet_generator.md')
    try:
        if sup_path.exists():
            sup_text = sup_path.read_text(encoding='utf-8')
            for line in sup_text.splitlines():
                s = line.strip()
                if not s or s.startswith('#'):
                    continue
                # normalize the suppression key to match how warnings are generated
                norm = s.lower().replace('_', '.').replace(' ', '.')
                suppress_set.add(norm)
    except Exception:
        pass

    npcs: List[Tuple[str, Dict[str, Any], str]] = []
    propagate_var = args.propagate_variable.strip() if getattr(args, 'propagate_variable', None) else None
    affected_templates: List[str] = []
    if propagate_var:
        # find all templates that reference this variable (directly or transitively)
        affected_templates = templates_referencing_var(propagate_var, secondary_templates)
        if args.verbose:
            print(f"Variable '{propagate_var}' affects templates: {affected_templates}")
    
    # Always use Dms Root for NPC generation - this is created at module load time
    variable_root = get_variable_root()
    
    for r in rows:
        if len(r) < len(hdr_norm):
            r += [''] * (len(hdr_norm) - len(r))
        data = dict(zip(hdr_norm, r))
        name = name_from_cell(data.get('name', 'Unknown'))
        if args.npc:
            if name.lower() != args.npc.strip().lower():
                continue
        run = data.get('run update', '').strip().lower()
        if not args.npc and run not in ('yes', 'y', 'true'):
            continue
        
        # Extract subfolder if present
        subfolder = data.get('subfolder', '').strip()
        
        kv: Dict[str, Any] = {}
        for k, v in data.items():
            key = k.strip().lower()
            if key == 'name' or key == 'run update' or key == 'subfolder':
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
        known = set(primary_names) | set(secondary_templates.keys()) | set(['str','dex','con','int','wis','cha','water','earth','air','fire','spirit','rolled.hp'])
        
        # Also add variable file stems from the global variable directory
        if variable_root and variable_root.exists():
            for var_dir in variable_root.glob('*/'):  # subdirectories like primary_stat, secondary_stat, etc.
                for var_file in var_dir.glob('*.md'):
                    known.add(var_file.stem)
        
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

        kv_all = compute_secondaries(kv, secondary_templates, verbose=args.verbose, known_vars=known, npc_name=name, create_placeholders=args.create_placeholders, placeholder_dir=variable_root, rollable_set=rollable_set, suppress_warnings=suppress_set)
        for kk, vv in kv.items():
            kv_all.setdefault(kk.lower(), vv)
        if propagate_var:
            # decide if this NPC is affected: any affected template stem present in kv_all
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
                npcs.append((name, kv_all, subfolder))
        else:
            npcs.append((name, kv_all, subfolder))

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    for name, kv_all, subfolder in npcs:
        write_character_files(name, kv_all, primary_names, secondary_templates, OUT_ROOT, var_root=variable_root, primary_tags=primary_tags, secondary_tags=secondary_tags, verbose=args.verbose, suppress_warnings=suppress_set, subfolder=subfolder)
        print('Wrote', name)


if __name__ == '__main__':
    main()
