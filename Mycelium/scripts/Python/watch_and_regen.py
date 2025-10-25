#!/usr/bin/env python3
"""Watch character-sheet files and re-run the generator for the changed PC.

This is a light-weight polling watcher (no external deps). It watches for
modification time changes on files named "* character sheet.md" under
`Player Root/PCs/` and, on change, calls the existing
`Mycelium/scripts/python/recreate_pcs.py --pc <Name>` to regenerate that
single PC (so bending rules and variable mirrors are updated).

Usage:
  python3 Mycelium/scripts/python/watch_and_regen.py --interval 2

Options:
  --interval N         Poll interval in seconds (default 2)
  --pcs-dir PATH       Path to PCs root (repo-relative, default: "Player Root/PCs")
  --script PATH        Path to recreate_pcs.py (default: Mycelium/scripts/python/recreate_pcs.py)
  --create-placeholders  Forward this flag to the generator when calling it
  --debounce N         Minimum seconds between regenerations for the same PC (default 1.0)
  --dry-run            Do not call the generator; just print what would be done

This script is intentionally simple and robust: it uses polling + mtime
checks so it works on all platforms without extra packages.
"""
from __future__ import annotations
# reuse shared helpers
from pathlib import Path
import argparse
import time
import sys
from typing import Dict, Optional
import hashlib
import re
import ast
from .common import (
    ROOT,
    _safe_rel,
    scan_sheet_files,
    name_from_cell,
    name_from_sheet,
    run_generator,
    _refresh_last_mtime_for_pc,
    load_environmental_templates,
    _extract_show_if_condition_from_tags,
    _is_in_environmental_folder,
    parse_sheet_for_vars,
    _eval_expr_local,
    _touch_or_update_dependent_files,
    pc_element_level,
    pc_references_env,
)

# keep old name for compatibility
# name_from_sheet is imported from common
# record of files written by this watcher: Path -> timestamp
_recently_written: Dict[Path, float] = {}
# record of last authoritative write time per candidate stem
_last_authoritative: Dict[str, float] = {}


# local aliases to keep older variable names working
# (actual implementations live in common.py)


def _extract_show_if_condition_from_tags(tags: set) -> Optional[tuple]:
    """Parse tags like '#show_if_water_ge_1' and return (element, 'ge', threshold) or None."""
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


def _is_in_environmental_folder(template_path: Path, vars_root: Path) -> bool:
    try:
        rel = template_path.relative_to(vars_root)
        return 'environmental' in [p.lower() for p in rel.parts]
    except Exception:
        return False


def parse_sheet_for_vars(sheet_path: Path) -> Dict[str, str]:
    """Return mapping display_name_lower -> value parsed from small tables in the sheet."""
    res: Dict[str, str] = {}
    try:
        txt = sheet_path.read_text(encoding='utf-8')
    except Exception:
        return res
    # find table rows like: | Environmental water charge | 5 |
    for m in re.finditer(r"^\|\s*([^|]+?)\s*\|\s*([^|\n]+?)\s*\|", txt, flags=re.M):
        key = m.group(1).strip()
        val = m.group(2).strip()
        res[key.lower()] = val
    return res


def propagate_environmental_from_sheet(sheet_path: Path, vars_root: Path, pcs_dir: Path, script: Path, args) -> None:
    """Exposeable helper: read a single character sheet, compare environmental rows to canonical
    variable files, and if the sheet is authoritative, write canonical files and propagate into other
    character sheets. This is the same logic used by the watcher but made callable for tests/manuals.

    Parameters:
    - sheet_path: Path to the changed character sheet
    - vars_root: Path to Player Root/variable
    - pcs_dir: Path to Player Root/PCs
    - script: Path to recreate_pcs.py (used for regen calls)
    - args: parsed argparse Namespace (used for --dry-run and create_placeholders)
    """
    # reuse code from the watcher loop: detect env templates, parse rows, write canonical and propagate
    env_templates = load_environmental_templates(vars_root)
    vars_found = parse_sheet_for_vars(sheet_path)
    for display, val in vars_found.items():
        stem = display.lower().replace(' ', '_')
        candidates = [stem, stem.rstrip('s'), stem + 's']
        for cand in candidates:
            if cand not in env_templates:
                continue
            # Prefer the actual template's canonical stem when writing files
            tpl = env_templates.get(cand)
            canonical_stem = tpl.stem if (tpl is not None) else cand
            global_var = vars_root.joinpath(canonical_stem + '.md')
            # Environmental variables go directly in environmental/, not in secondary_stat/
            new_content = f"{val}\n\n#variable #secondary_stat #template #environmental_variables\n"
            # read canonical existing numeric value
            def _read_canonical(p: Path) -> Optional[str]:
                try:
                    if p.exists():
                        txt = p.read_text(encoding='utf-8')
                        m = re.search(r'```markdown\n(.*?)\n\n', txt, flags=re.S)
                        if m:
                            return m.group(1).strip()
                        lines = [l.strip() for l in txt.splitlines() if l.strip() and not l.strip().startswith('#')]
                        return lines[0] if lines else ''
                except Exception:
                    return None
                return None

            def _norm_num(s: Optional[str]) -> Optional[float]:
                if s is None:
                    return None
                try:
                    return float(re.sub(r'[^0-9.+-]', '', str(s)) or 0)
                except Exception:
                    try:
                        m = re.search(r'[-+]?[0-9]*\.?[0-9]+', str(s))
                        if m:
                            return float(m.group(0))
                    except Exception:
                        return None
                return None

            # Only check the global environmental variable file
            canon_val = _read_canonical(global_var)
            try:
                sheet_num = _norm_num(val)
            except Exception:
                sheet_num = None
            canon_num = _norm_num(canon_val)

            if canon_num is not None and sheet_num is not None and canon_num == sheet_num:
                if args.dry_run:
                    print('[DRY] canonical matches sheet for', cand)
                continue

            # treat sheet as authoritative
            if args.dry_run:
                print('[DRY] would set canonical', _safe_rel(global_var), 'to', val)
            else:
                try:
                    global_var.write_text(new_content, encoding='utf-8')
                    _recently_written[global_var] = time.time()
                    _last_authoritative[cand] = time.time()
                    print('Updated environmental variable file:', _safe_rel(global_var))
                except Exception as e:
                    print('Failed to write canonical var', global_var, e)

            # propagate value into other sheets
            for other_pc in pcs_dir.iterdir():
                if not other_pc.is_dir():
                    continue
                if other_pc.name == sheet_path.parent.name:
                    continue
                sheet = other_pc.joinpath(f"{other_pc.name} character sheet.md")
                if not sheet.exists():
                    continue
                try:
                    txt = sheet.read_text(encoding='utf-8')
                except Exception:
                    continue
                # check show_if tags on the canonical template (if any)
                show_if = None
                try:
                    tpl = env_templates.get(cand)
                    if tpl and tpl.exists():
                        ttxt = tpl.read_text(encoding='utf-8')
                        tagset = {t.lower() for t in re.findall(r"#[-\w]+", ttxt)}
                        show_if = _extract_show_if_condition_from_tags(tagset)
                except Exception:
                    show_if = None

                pat = re.compile(r"(?im)^(\|\s*" + re.escape(display) + r"\s*\|)\s*([^|]+)\|", flags=re.M)
                m = pat.search(txt)
                if m:
                    # if a show_if condition is present, ensure this PC meets it
                    if show_if is not None:
                        elem, op, thresh = show_if
                        if pc_element_level(other_pc, elem) < thresh:
                            # skip propagation for this PC
                            continue
                    new_row = f"| {display} | {val} |"
                    new_txt = pat.sub(new_row, txt, count=1)
                    if new_txt != txt:
                        try:
                            b = sheet.with_suffix('.md.bak')
                            b.write_text(txt, encoding='utf-8')
                            sheet.write_text(new_txt, encoding='utf-8')
                            _recently_written[sheet] = time.time()
                            print('Propagated', display, '->', _safe_rel(sheet))
                        except Exception:
                            pass
                else:
                    short = stem
                    pat2 = re.compile(r"(?im)^\|\s*([^|]*" + re.escape(short) + r"[^|]*)\|\s*([^|]+)\|", flags=re.M)
                    m2 = pat2.search(txt)
                    if m2:
                        # respect show_if for stem-based matches too
                        if show_if is not None:
                            elem, op, thresh = show_if
                            if pc_element_level(other_pc, elem) < thresh:
                                continue
                        new_row = f"| {m2.group(1).strip()} | {val} |"
                        new_txt = pat2.sub(new_row, txt, count=1)
                        if new_txt != txt:
                            try:
                                b = sheet.with_suffix('.md.bak')
                                b.write_text(txt, encoding='utf-8')
                                sheet.write_text(new_txt, encoding='utf-8')
                                _recently_written[sheet] = time.time()
                                print('Propagated (stem) ', display, '->', _safe_rel(sheet))
                            except Exception:
                                pass

            # print canonical file after propagation
            try:
                if global_var.exists():
                    try:
                        txt = global_var.read_text(encoding='utf-8')
                    except Exception:
                        txt = '<failed to read>'
                    print('Canonical file', _safe_rel(global_var), 'now contains:')
                    print(txt)
                else:
                    if args.dry_run:
                        print('[DRY] Canonical file (would be)', global_var.relative_to(ROOT), 'with content:')
                        print(new_content)
            except Exception as e:
                print('Failed to print canonical files after propagation:', e)



def _eval_expr_local(expr: str) -> Optional[float]:
    try:
        node = ast.parse(expr, mode='eval')
    except Exception:
        return None
    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant):
            return n.value
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
            raise ValueError('unsupported op')
        if isinstance(n, ast.UnaryOp):
            if isinstance(n.op, ast.UAdd):
                return +_eval(n.operand)
            if isinstance(n.op, ast.USub):
                return -_eval(n.operand)
            raise ValueError('unsupported unary')
        raise ValueError('unsupported')
    try:
        return float(_eval(node))
    except Exception:
        return None


def _touch_or_update_dependent_files(changed_path: Path, vars_root: Path) -> None:
    # reuse a lightweight approach similar to watch_env_and_regen
    try:
        display = changed_path.stem.replace('_', ' ')
        stem = changed_path.stem.lower()
        # build vars map
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
                        # replace [[Token]] with numeric values
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


def pc_element_level(pc_dir: Path, element: str) -> float:
    # try to read the per-PC variables file first
    safe = pc_dir.name
    vars_path = pc_dir.joinpath(f"{safe}_variables.md")
    if vars_path.exists():
        try:
            txt = vars_path.read_text(encoding='utf-8')
            for ln in txt.splitlines():
                m = re.match(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", ln)
                if m:
                    key = m.group(1).strip().lower().replace(' ', '_')
                    # Only accept explicit element keys or common level suffixes.
                    # Avoid matching keys that merely contain the element (e.g. 'waterbottle')
                    if key == element or key.endswith('_' + element) or key == element + '_level' or key == element + ' level':
                        try:
                            return float(re.sub(r'[^0-9.+-]', '', m.group(2).strip()) or 0)
                        except Exception:
                            return 0.0
        except Exception:
            pass
    # fallback to reading character sheet
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
    """Return True if the PC's variables or sheet appear to reference the environmental variable.

    cand is a normalized stem like 'environmental_water_charge' or 'environmental_water_charges'.
    display_name is the human table label parsed from the sheet (e.g. 'Environmental water charge').
    """
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
    # fallback to scanning the character sheet
    sheet = pc_dir.joinpath(f"{safe} character sheet.md")
    try:
        if sheet.exists():
            s = sheet.read_text(encoding='utf-8').lower()
            if display_name.lower() in s:
                return True
            # also look for the non-prefixed stem, e.g., 'water_charge' or 'water_charges'
            short = cand.lower()
            if short.startswith('environmental_'):
                short = short[len('environmental_'):]
            if short in s:
                return True
    except Exception:
        pass
    return False


def main() -> None:
    p = argparse.ArgumentParser(description='Watch PC sheets and re-run generator for changed PC')
    p.add_argument('--interval', type=float, default=2.0, help='Poll interval seconds')
    p.add_argument('--pcs-dir', default='Player Root/PCs', help='Repo-relative PCs folder')
    p.add_argument('--script', default='Mycelium/scripts/python/recreate_pcs.py', help='Path to recreate_pcs.py')
    p.add_argument('--create-placeholders', action='store_true', help='Forward --create-placeholders to generator')
    p.add_argument('--debounce', type=float, default=1.0, help='Seconds minimum between re-runs for the same PC')
    p.add_argument('--dry-run', action='store_true', help='Do not actually run generator')
    args = p.parse_args()

    pcs_dir = ROOT.joinpath(args.pcs_dir)
    script = ROOT.joinpath(args.script)
    if not script.exists():
        print('ERROR: generator script not found:', script)
        sys.exit(1)

    last_mtimes = scan_sheet_files(pcs_dir)
    # keep last file contents to avoid retriggering when mtimes change but
    # content is identical (editors that touch mtimes or generators that
    # rewrite files without content change can cause duplicates)
    last_contents: Dict[Path, str] = {}
    for p in list(last_mtimes.keys()):
        try:
            last_contents[p] = p.read_text(encoding='utf-8')
        except Exception:
            last_contents[p] = ''
    last_run: Dict[str, float] = {}
    print('Watching', pcs_dir, 'every', args.interval, 's; generator:', script)
    try:
        while True:
            time.sleep(args.interval)
            current = scan_sheet_files(pcs_dir)
            # detect added/changed files and group by PC so we only run once per PC per scan
            changed_by_pc: Dict[str, list] = {}
            for path, mtime in current.items():
                prev = last_mtimes.get(path)
                # ignore changes we just wrote ourselves within a short grace
                recent = _recently_written.get(path)
                if recent is not None and mtime <= recent + 1.5:
                    # consider this a self-write; update bookkeeping and skip
                    last_mtimes[path] = mtime
                    continue
                if prev is None or mtime > prev + 1e-6:
                    # check content change to avoid duplicate triggers when mtime
                    # changed but content stayed the same
                    try:
                        cur_txt = path.read_text(encoding='utf-8')
                    except Exception:
                        cur_txt = ''
                    old_txt = last_contents.get(path)
                    if old_txt is not None and cur_txt == old_txt:
                        # update mtime bookkeeping but skip as content didn't change
                        last_mtimes[path] = mtime
                        continue
                    # record new content
                    last_contents[path] = cur_txt
                    pc_name = name_from_sheet(path)
                    changed_by_pc.setdefault(pc_name, []).append(path)

            if changed_by_pc:
                # load environmental templates map once
                vars_root = ROOT.joinpath('Player Root', 'variable')
                env_templates = load_environmental_templates(vars_root)
            # prevent handling the same environmental candidate multiple times in one scan
            processed_candidates = set()
            for pc_name, paths in changed_by_pc.items():
                now = time.time()
                lr = last_run.get(pc_name, 0)
                if now - lr < args.debounce:
                    if args.dry_run:
                        print('Debounced regen for', pc_name)
                    continue
                print('Change detected for PC', pc_name)
                # For each changed sheet path for this PC, parse possible environmental variable rows
                for p in paths:
                    # parse sheet table rows
                    vars_found = parse_sheet_for_vars(p)
                    for display, val in vars_found.items():
                        # normalize display to candidate stems
                        stem = display.lower().replace(' ', '_')
                        candidates = [stem, stem.rstrip('s'), stem + 's']
                        for cand in candidates:
                            # skip if we've already handled this candidate in this scan
                            if cand in processed_candidates:
                                continue
                            if cand not in env_templates:
                                continue
                            # canonical path
                            tpl = env_templates.get(cand)
                            canonical_stem = tpl.stem if (tpl is not None) else cand
                            global_var = vars_root.joinpath(canonical_stem + '.md')
                            # build canonical content we would write
                            new_content = f"{val}\n\n#variable #secondary_stat #template #environmental_variables\n"
                            # read canonical existing numeric value (if any)
                            def _read_canonical(p: Path) -> Optional[str]:
                                try:
                                    if p.exists():
                                        txt = p.read_text(encoding='utf-8')
                                        # try fenced block first
                                        m = re.search(r'```markdown\n(.*?)\n\n', txt, flags=re.S)
                                        if m:
                                            return m.group(1).strip()
                                        # fallback: first non-tag line
                                        lines = [l.strip() for l in txt.splitlines() if l.strip() and not l.strip().startswith('#')]
                                        return lines[0] if lines else ''
                                except Exception:
                                    return None
                                return None

                            # Only check the global environmental variable file
                            canon_val = _read_canonical(global_var)
                            # normalize numeric strings for compare
                            def _norm_num(s: Optional[str]) -> Optional[float]:
                                if s is None:
                                    return None
                                try:
                                    return float(re.sub(r'[^0-9.+-]', '', str(s)) or 0)
                                except Exception:
                                    try:
                                        m = re.search(r'[-+]?[0-9]*\.?[0-9]+', str(s))
                                        if m:
                                            return float(m.group(0))
                                    except Exception:
                                        return None
                                return None

                            try:
                                sheet_num = _norm_num(val)
                            except Exception:
                                sheet_num = None
                            canon_num = _norm_num(canon_val)

                            # If canonical exists and equals sheet value, nothing to do
                            if canon_num is not None and sheet_num is not None and canon_num == sheet_num:
                                # nothing changed
                                if args.dry_run:
                                    print('[DRY] canonical matches sheet for', cand)
                                continue

                            # If canonical file was updated more recently than this sheet, skip overwrite.
                            try:
                                sheet_mtime = p.stat().st_mtime
                            except Exception:
                                sheet_mtime = time.time()
                            canon_mtime = None
                            try:
                                if global_var.exists():
                                    canon_mtime = global_var.stat().st_mtime
                            except Exception:
                                canon_mtime = None
                            last_auth = _last_authoritative.get(cand)
                            # If canonical has a newer authoritative timestamp, don't let this sheet overwrite it
                            if last_auth is not None and sheet_mtime <= last_auth + 0.01:
                                if args.dry_run:
                                    print('[DRY] skipping overwrite for', cand, 'because canonical was updated more recently')
                                continue

                            # At this point: sheet value differs from canonical (or no canonical present)
                            # Treat the sheet value as authoritative: write canonical files and propagate
                            if args.dry_run:
                                print('[DRY] would set canonical', global_var.relative_to(ROOT), 'to', val)
                            else:
                                try:
                                    global_var.write_text(new_content, encoding='utf-8')
                                    _recently_written[global_var] = time.time()
                                    # mark last authoritative update for this candidate
                                    _last_authoritative[cand] = time.time()
                                    print('Updated environmental variable file:', global_var.relative_to(ROOT))
                                except Exception as e:
                                    print('Failed to write canonical var', global_var, e)
                            # propagate this value into other character sheets: replace matching table rows
                            for other_pc in pcs_dir.iterdir():
                                if not other_pc.is_dir():
                                    continue
                                if other_pc.name == pc_name:
                                    continue
                                sheet_path = other_pc.joinpath(f"{other_pc.name} character sheet.md")
                                if not sheet_path.exists():
                                    continue
                                try:
                                    txt = sheet_path.read_text(encoding='utf-8')
                                except Exception:
                                    continue
                                # replace a table row that begins with the display name
                                pat = re.compile(r"(?im)^(\|\s*" + re.escape(display) + r"\s*\|)\s*([^|]+)\|", flags=re.M)
                                m = pat.search(txt)
                                # check show_if tags on the canonical template (if any)
                                show_if = None
                                try:
                                    tpl = env_templates.get(cand)
                                    if tpl and tpl.exists():
                                        ttxt = tpl.read_text(encoding='utf-8')
                                        tagset = {t.lower() for t in re.findall(r"#[-\w]+", ttxt)}
                                        show_if = _extract_show_if_condition_from_tags(tagset)
                                except Exception:
                                    show_if = None

                                if m:
                                    # construct replacement row preserving spacing style
                                    # if a show_if condition is present, ensure this PC meets it
                                    if show_if is not None:
                                        elem, op, thresh = show_if
                                        if pc_element_level(other_pc, elem) < thresh:
                                            # skip propagation for this PC
                                            continue
                                    new_row = f"| {display} | {val} |"
                                    new_txt = pat.sub(new_row, txt, count=1)
                                    if new_txt != txt:
                                        try:
                                            # backup and write
                                            b = sheet_path.with_suffix('.md.bak')
                                            b.write_text(txt, encoding='utf-8')
                                            sheet_path.write_text(new_txt, encoding='utf-8')
                                            _recently_written[sheet_path] = time.time()
                                            print('Propagated', display, '->', _safe_rel(sheet_path))
                                        except Exception:
                                            pass
                                else:
                                    # also attempt to find stem-like rows (water_charge etc.)
                                    short = stem
                                    pat2 = re.compile(r"(?im)^\|\s*([^|]*" + re.escape(short) + r"[^|]*)\|\s*([^|]+)\|", flags=re.M)
                                    m2 = pat2.search(txt)
                                    if m2:
                                        new_row = f"| {m2.group(1).strip()} | {val} |"
                                        new_txt = pat2.sub(new_row, txt, count=1)
                                        if new_txt != txt:
                                            try:
                                                # respect show_if for stem-based matches too
                                                if show_if is not None:
                                                    elem, op, thresh = show_if
                                                    if pc_element_level(other_pc, elem) < thresh:
                                                        continue
                                                b = sheet_path.with_suffix('.md.bak')
                                                b.write_text(txt, encoding='utf-8')
                                                sheet_path.write_text(new_txt, encoding='utf-8')
                                                _recently_written[sheet_path] = time.time()
                                                print('Propagated (stem) ', display, '->', _safe_rel(sheet_path))
                                            except Exception:
                                                pass
                            # After propagating into other sheets, print the canonical file
                            try:
                                if global_var.exists():
                                    try:
                                        txt = global_var.read_text(encoding='utf-8')
                                    except Exception:
                                        txt = '<failed to read>'
                                    print('Canonical file', _safe_rel(global_var), 'now contains:')
                                    print(txt)
                                else:
                                    if args.dry_run:
                                        print('[DRY] Canonical file (would be)', _safe_rel(global_var), 'with content:')
                                        print(new_content)
                            except Exception as e:
                                print('Failed to print canonical file after propagation:', e)
                            # mark this candidate as handled for this scan
                            processed_candidates.add(cand)
                            # trigger regenerations for all PCs with this element >= 1
                            # infer element from stem (e.g., environmental_water_charge -> water)
                            elem = None
                            for e in ('air', 'water', 'earth', 'fire', 'spirit'):
                                if e in cand:
                                    elem = e
                                    break
                            if elem:
                                # regenerate only PCs that both have elem level >=1
                                # and appear to reference this environmental variable
                                for pc_dir in pcs_dir.iterdir():
                                    if not pc_dir.is_dir():
                                        continue
                                    target_pc = pc_dir.name
                                    # avoid regenerating the same PC twice here
                                    if target_pc == pc_name:
                                        continue
                                    lvl = pc_element_level(pc_dir, elem)
                                    if lvl < 1:
                                        continue
                                    # only regenerate if the PC references this env var
                                    if not pc_references_env(pc_dir, cand, display):
                                        continue
                                    run_generator(script, target_pc, args.create_placeholders, args.dry_run)
                                    # refresh mtime so generator-written sheet doesn't immediately re-trigger
                                    _refresh_last_mtime_for_pc(pcs_dir, last_mtimes, target_pc)
                # now run generator for the PC that changed
                run_generator(script, pc_name, args.create_placeholders, args.dry_run)
                _refresh_last_mtime_for_pc(pcs_dir, last_mtimes, pc_name)
                last_run[pc_name] = time.time()
            # detect removed files (so they don't trigger later)
            last_mtimes = current
    except KeyboardInterrupt:
        print('\nStopped watching')


if __name__ == '__main__':
    main()
