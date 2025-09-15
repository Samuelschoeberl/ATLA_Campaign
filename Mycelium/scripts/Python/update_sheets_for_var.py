#!/usr/bin/env python3
"""Update character sheets when a single variable changes.

Given a variable stem (no .md), this script:
- finds all secondary templates that reference that variable (directly or transitively),
- for each PC, recomputes secondary stats using the same logic as `recreate_pcs.py`,
- updates any character sheet files under `Player Root/PCs/<PC>/...` where the sheet
  mentions either the changed variable or any dependent stat, replacing the displayed
  value in the markdown table with the newly computed value.

Usage:
  python3 Mycelium/scripts/python/update_sheets_for_var.py -n environmental_water_charges

Options:
  --name / -n : variable stem (required)
  --pc   / -p : optional PC name to limit update
  --verbose / -v : verbose logging
"""
from __future__ import annotations
from pathlib import Path
import argparse
import importlib.util
import re
from .common import (
    ROOT,
    get_variable_root,
    load_secondary_templates,
    load_template_tags,
    parse_markdown_table,
    display_name_for,
    normalize_key,
)



def load_recreate_module() -> object:
    path = ROOT.joinpath('Mycelium', 'scripts', 'python', 'recreate_pcs.py')
    if not path.exists():
        # try capitalized Python folder used elsewhere
        path = ROOT.joinpath('Mycelium', 'scripts', 'Python', 'recreate_pcs.py')
    if not path.exists():
        raise FileNotFoundError(f'recreate_pcs.py not found under expected locations (tried {path})')
    spec = importlib.util.spec_from_file_location('recreate_pcs', str(path))
    if spec is None or spec.loader is None:
        raise ImportError('Could not create module spec for recreate_pcs')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def find_dependent_templates(templates: dict, varname: str) -> set:
    # templates: name -> formula
    name_map = {n.lower(): f for n, f in templates.items()}
    var = varname.lower()
    dep = set()
    # direct dependents: formulas that contain [[var]] or word var
    pattern_bracket = re.compile(r"\[\[\s*([^\]]+)\s*\]\]", flags=re.I)
    word_pat = re.compile(r"\b" + re.escape(var) + r"\b", flags=re.I)
    for n, f in name_map.items():
        if word_pat.search(f):
            dep.add(n)
        else:
            for m in pattern_bracket.findall(f):
                if m.strip().lower().replace('_', ' ').replace('.', ' ') == var.replace('_', ' ').replace('.', ' '):
                    dep.add(n)
    # transitively include templates that reference any found template
    changed = True
    while changed:
        changed = False
        for n, f in name_map.items():
            if n in dep:
                continue
            for token in dep:
                if re.search(r"\b" + re.escape(token) + r"\b", f, flags=re.I) or pattern_bracket.search(f) and token in [t.strip().lower() for t in pattern_bracket.findall(f)]:
                    dep.add(n)
                    changed = True
                    break
    return dep



def build_kv_for_pc(mod, pc_name: str, primary_row: dict, variable_root: Path, primary_names: list) -> dict:
    # start with primary values
    kv = {}
    for k, v in primary_row.items():
        kk = k.strip().lower()
        if kk in ('name', 'run update'):
            continue
        # normalize some keys similar to recreate_pcs
        if 'manually' in kk and 'hp' in kk:
            key_out = 'rolled.hp'
        elif kk == 'riz':
            key_out = 'cha'
        else:
            key_out = kk
        key_out = key_out.replace(' ', '.').replace('/', '.')
        try:
            kv[key_out] = mod.to_number(v)
        except Exception:
            kv[key_out] = 0
    # ensure defaults
    for s in ['str','dex','con','int','wis','cha','water','earth','air','fire','spirit','rolled.hp']:
        kv.setdefault(s, 0)
    # load variable files: prefer per-PC PC_variables/<pc> then global
    pc_safe = re.sub(r"[^A-Za-z0-9_\-]", '_', pc_name)
    per_pc_dir = variable_root.joinpath('PC_variables', pc_safe)
    if per_pc_dir.exists():
        for p in per_pc_dir.glob('*.md'):
            stem = p.stem
            # strip leading '<pc>_' if present
            prefix = pc_safe + '_'
            if stem.lower().startswith(prefix.lower()):
                orig = stem[len(prefix):]
            else:
                orig = stem
            key = normalize_key(orig)
            val_raw = p.read_text(encoding='utf-8')
            # extract first numeric or line from fenced block
            m = re.search(r'```markdown\n(.*?)\n\n', val_raw, flags=re.S)
            if m:
                val = m.group(1).strip()
            else:
                val = val_raw.strip().splitlines()[0].strip() if val_raw.strip() else ''
            kv[key] = mod.to_number(val)
    # global variables
    for p in variable_root.rglob('*.md'):
        # skip those inside PC_variables to avoid overwriting with same-named per-pc
        if 'PC_variables' in p.parts:
            continue
        stem = p.stem
        key = normalize_key(stem)
        val_raw = p.read_text(encoding='utf-8')
        m = re.search(r'```markdown\n(.*?)\n\n', val_raw, flags=re.S)
        if m:
            val = m.group(1).strip()
        else:
            val = val_raw.strip().splitlines()[0].strip() if val_raw.strip() else ''
        kv.setdefault(key, mod.to_number(val))
    return kv


def update_sheet_file(path: Path, updates: dict, verbose: bool = False) -> bool:
    """updates: mapping display_name -> new_value (stringable). Returns True if changed."""
    txt = path.read_text(encoding='utf-8')
    orig = txt
    for key, val in updates.items():
        dname = display_name_for(key)
        # If the new value is numerically zero, remove any table rows for this stat
        is_zero = False
        try:
            is_zero = float(val) == 0
        except Exception:
            # non-numeric string; treat literal '0' as zero
            try:
                is_zero = str(val).strip() in ('0', '0.0')
            except Exception:
                is_zero = False

        if is_zero:
            # remove exact display name rows
            pat_row = re.compile(r"(?im)^\|\s*" + re.escape(dname) + r"\s*\|[^\n]*\n")
            txt, removed = pat_row.subn('', txt)
            if removed and verbose:
                print(f'Removed {removed} occurrence(s) of "{dname}" from {path}')
            # also try raw key fallback
            d2 = key.replace('_', ' ').replace('.', ' ')
            pat_row2 = re.compile(r"(?im)^\|\s*" + re.escape(d2) + r"\s*\|[^\n]*\n")
            txt, removed2 = pat_row2.subn('', txt)
            if removed2 and verbose:
                print(f'Removed {removed2} fallback occurrence(s) of "{d2}" from {path}')
            # continue to next update
            continue

        # match markdown table rows with the stat name in first column
        # pattern: | <name> | <value> |
        pat = re.compile(r"(\|\s*" + re.escape(dname) + r"\s*\|\s*)([^|\n]+)(\|)")
        txt, n = pat.subn(lambda m: m.group(1) + str(val) + ' ' + m.group(3), txt)
        if n > 0 and verbose:
            print(f'Updated {n} occurrence(s) of "{dname}" in {path}')
        # also try the raw key name as a fallback (normalized)
        if n == 0:
            d2 = key.replace('_', ' ').replace('.', ' ')
            pat2 = re.compile(r"(\|\s*" + re.escape(d2) + r"\s*\|\s*)([^|\n]+)(\|)", flags=re.I)
            txt, n2 = pat2.subn(lambda m: m.group(1) + str(val) + ' ' + m.group(3), txt)
            if n2 > 0 and verbose:
                print(f'Updated {n2} fallback occurrence(s) of "{d2}" in {path}')
    if txt != orig:
        path.write_text(txt, encoding='utf-8')
        return True
    return False


def main() -> None:
    p = argparse.ArgumentParser(description='Update character sheets affected by a changed variable')
    p.add_argument('--name', '-n', required=True, help='Variable filename stem (no .md)')
    p.add_argument('--pc', '-p', help='Optional PC to limit updates')
    p.add_argument('--verbose', '-v', action='store_true')
    args = p.parse_args()

    mod = load_recreate_module()
    # prefer shared discovery
    var_root = get_variable_root()
    if var_root is None:
        # fallback to recreate_pcs helper if available
        var_root = getattr(mod, 'get_variable_root', lambda: None)()
    if var_root is None:
        print('ERROR: could not determine variable root; abort')
        return
    # extract constants and functions from recreate_pcs module with sensible fallbacks
    SECONDARY_TEMPLATES_DIR = getattr(mod, 'SECONDARY_TEMPLATES_DIR', ROOT.joinpath('Player Root', 'variable', 'secondary_stat'))
    PRIMARY_TEMPLATES_DIR = getattr(mod, 'PRIMARY_TEMPLATES_DIR', ROOT.joinpath('Player Root', 'variable', 'primary_stat'))
    INPUT_TABLE = getattr(mod, 'INPUT_TABLE', ROOT.joinpath('Player Root', 'pc_primary_stats.md'))
    OUT_ROOT = getattr(mod, 'OUT_ROOT', ROOT.joinpath('Player Root', 'PCs'))
    to_number = getattr(mod, 'to_number', None)
    compute_secondaries = getattr(mod, 'compute_secondaries', None)
    write_character_files = getattr(mod, 'write_character_files', None)
    name_from_cell = getattr(mod, 'name_from_cell', None)

    secondary_templates = load_secondary_templates(SECONDARY_TEMPLATES_DIR)
    primary_names = getattr(mod, 'load_primary_names', lambda d: [])(PRIMARY_TEMPLATES_DIR)
    primary_tags = load_template_tags(PRIMARY_TEMPLATES_DIR)
    secondary_tags = load_template_tags(SECONDARY_TEMPLATES_DIR)
    dependent = find_dependent_templates(secondary_templates, args.name)
    if args.verbose:
        print('Dependent templates:', dependent)
    # also include the changed variable itself as a "stat" to update
    affected = set([normalize_key(args.name)]) | set(dependent)

    # parse primary table to get PC rows
    header, rows = parse_markdown_table(INPUT_TABLE)
    hdr_norm = [h.strip().lower() for h in header]
    pcs = []
    for r in rows:
        if len(r) < len(hdr_norm):
            r += [''] * (len(hdr_norm) - len(r))
        data = dict(zip(hdr_norm, r))
        if name_from_cell:
            name = name_from_cell(data.get('name', 'Unknown'))
        else:
            from common import name_from_cell as _nfc
            name = _nfc(data.get('name', 'Unknown'))
        if args.pc and name.lower() != args.pc.strip().lower():
            continue
        pcs.append((name, data))

    updated_any = False
    for name, data in pcs:
        if args.verbose:
            print('Processing PC', name)
        kv = build_kv_for_pc(mod, name, data, var_root, primary_names)
        # recompute secondaries
        if compute_secondaries is None:
            raise RuntimeError('recreate_pcs.compute_secondaries is required')
        kv_all = compute_secondaries(kv, secondary_templates, verbose=args.verbose, known_vars=set(primary_names) | set(secondary_templates.keys()), pc_name=name)
        # ensure per-character variable file for the changed variable is written and iterate until stable
        changed_key_norm = normalize_key(args.name)
        # attempt iterative stabilization: write per-pc var file and recompute until value stabilizes
        per_pc_dir = var_root.joinpath('PC_variables', re.sub(r"[^A-Za-z0-9_\-]", '_', name))
        per_pc_dir.mkdir(parents=True, exist_ok=True)
        target_var_path = per_pc_dir.joinpath(f"{re.sub(r"[^A-Za-z0-9_\-]", '_', name)}_{args.name}.md")
        stable = False
        last_val = None
        for iter_no in range(6):
            # pick value from kv_all (try dotted and spaced variants)
            kdot = changed_key_norm.replace(' ', '.')
            val = kv_all.get(kdot)
            if val is None:
                val = kv_all.get(changed_key_norm)
            if val is None:
                # nothing to write
                break
            # write per-pc variable file
            try:
                content = f"```markdown\n{val}\n\n#variable #character_stat\n\n```\n"
                target_var_path.write_text(content, encoding='utf-8')
                if args.verbose:
                    print(f'Wrote per-PC variable: {target_var_path.relative_to(ROOT)}')
            except Exception:
                print(f'Could not write per-PC variable: {target_var_path}')
            # rebuild kv including the newly written per-pc file, then recompute
            kv = build_kv_for_pc(mod, name, data, var_root, primary_names)
            new_kv_all = compute_secondaries(kv, secondary_templates, verbose=args.verbose, known_vars=set(primary_names) | set(secondary_templates.keys()), pc_name=name)
            new_val = new_kv_all.get(kdot) or new_kv_all.get(changed_key_norm)
            if args.verbose:
                print(f'Iter {iter_no+1}: var {args.name} old={val!r} new={new_val!r}')
            if new_val == last_val:
                stable = True
                kv_all = new_kv_all
                break
            last_val = new_val
            kv_all = new_kv_all
        if not stable and args.verbose:
            print(f'Variable {args.name} did not fully stabilize after iterations for PC {name}')
        # Instead of editing sheet rows in-place, regenerate the full character sheet
        # from the template using recreate_pcs.write_character_files. This will
        # overwrite the existing sheet and omit any zero-valued rows per the
        # template rendering logic in recreate_pcs.py.
        try:
            # call the writer from the recreate module
            if write_character_files is None:
                raise RuntimeError('recreate_pcs.write_character_files is required')
            write_character_files(name, kv_all, primary_names, secondary_templates, OUT_ROOT, var_root=var_root, primary_tags=primary_tags, secondary_tags=secondary_tags, verbose=args.verbose)
            updated_any = True
            safe = re.sub(r"[^A-Za-z0-9_\-]", '_', name)
            sheet = ROOT.joinpath('Player Root', 'PCs', safe, f"{safe} character sheet.md")
            print('Rewrote sheet for', name, '->', sheet.relative_to(ROOT))
        except Exception as e:
            if args.verbose:
                print('Failed to rewrite sheet for', name, e)
    if not updated_any:
        print('No sheets were updated')


if __name__ == '__main__':
    main()
