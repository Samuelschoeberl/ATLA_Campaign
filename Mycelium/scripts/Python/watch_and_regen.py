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
import threading
import time
from typing import Dict, Optional
import hashlib
import re
import ast

try:
    import resource_cache as _resource_cache
except Exception:
    _resource_cache = None

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
# Guards both dicts above -- propagate_environmental_from_sheet() can now be
# called concurrently from Flask request threads (routes_sheets.update_sheet)
# and, previously, from this module's own standalone watch loop (removed --
# see outdated/backend-dead-code-2026-08/README.md). Two concurrent sheet
# saves touching these dicts with no lock was a real race under Flask's
# threaded=True.
_state_lock = threading.Lock()


def _write_locked(path: Path, content: str) -> None:
    """Write a file under its resource_cache per-path lock, if available,
    so this can't interleave with a direct Flask-thread write or the
    folded-in variable-sync background thread touching the same file."""
    if _resource_cache is not None:
        with _resource_cache.get_lock(path):
            path.write_text(content, encoding='utf-8')
    else:
        path.write_text(content, encoding='utf-8')


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
    """Check whether a template resides under an environmental folder."""
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
                """Read the canonical value from a variable file."""
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
                """Normalize a numeric-ish string to a float."""
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
                    _write_locked(global_var, new_content)
                    with _state_lock:
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
                            _write_locked(b, txt)
                            _write_locked(sheet, new_txt)
                            with _state_lock:
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
                                _write_locked(b, txt)
                                _write_locked(sheet, new_txt)
                                with _state_lock:
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
    """Evaluate a tiny arithmetic expression used in markdown computed files."""
    try:
        node = ast.parse(expr, mode='eval')
    except Exception:
        return None
    def _eval(n):
        """Recursively evaluate AST nodes in a safe subset."""
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
    """Touch files that reference a variable or recompute simple expressions."""
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
                            """Swap in numeric values for [[var]] tokens before eval."""
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
    """Return a PC's element level by reading variables or sheet tables."""
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
    """Deprecated: the standalone polling watch loop that used to live here
    has been removed as part of the backend sync rework (see
    outdated/backend-dead-code-2026-08/README.md). It was never actually
    launched by start_game.sh or run_backend.py -- only this module's
    `propagate_environmental_from_sheet()` function was ever live, called
    synchronously from the Flask request thread in routes_sheets.update_sheet()
    with proper per-path locking (see _write_locked/_state_lock above).

    Kept as a stub (rather than deleted) so `python3 watch_and_regen.py` still
    exits cleanly instead of erroring, in case anything still invokes it
    directly out of habit.
    """
    print(
        "watch_and_regen.py's standalone watch loop has been removed -- it was "
        "dead code (never launched in production). Its only live function, "
        "propagate_environmental_from_sheet(), is still called directly from "
        "the Flask backend on every character-sheet save. See "
        "outdated/backend-dead-code-2026-08/README.md for details."
    )


if __name__ == '__main__':
    main()
