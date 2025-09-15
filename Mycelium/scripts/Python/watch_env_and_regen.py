#!/usr/bin/env python3
"""Watch environmental variable files and re-run generator for affected PCs.

Behaviour:
- Polls the repo's variable folders for changes to Markdown files.
- If a changed file contains a tag #environmental_variable or #environmental_variables
  (case-insensitive), the script will infer the element (air/water/earth/fire/spirit)
  from the filename or tags and re-run the generator for all PCs whose element
  level for that element is >= 1.

Usage:
  python3 Mycelium/scripts/python/watch_env_and_regen.py

Options:
  --interval N            Poll interval seconds (default 2)
  --vars-dir PATH         Path to variable root (default 'Player Root/variable')
  --pcs-dir PATH          Path to PCs root (default 'Player Root/PCs')
  --script PATH           Path to recreate_pcs.py (default 'Mycelium/scripts/python/recreate_pcs.py')
  --create-placeholders   Forward --create-placeholders to the generator
  --dry-run               Do not actually run the generator; print actions instead
  --debounce N            Minimum seconds between full-regens for same element (default 1.0)

This is a simple polling watcher so it works without external packages.
"""
from __future__ import annotations
from pathlib import Path
import time
import argparse
import re
import subprocess
import sys
from typing import Dict, Optional
import ast

ROOT = Path('.').resolve()
ELEMENTS = ('air', 'water', 'earth', 'fire', 'spirit')
# remember files we wrote so we can ignore their mtime changes
_recently_written: Dict[Path, float] = {}


def scan_var_files(vars_root: Path) -> Dict[Path, float]:
    out: Dict[Path, float] = {}
    if not vars_root.exists():
        return out
    for p in vars_root.rglob('*.md'):
        try:
            out[p] = p.stat().st_mtime
        except Exception:
            continue
    return out


def file_has_env_tag(path: Path) -> bool:
    try:
        txt = path.read_text(encoding='utf-8')
    except Exception:
        return False
    tags = re.findall(r"#[-\w]+", txt)
    tags = [t.lower() for t in tags]
    return any(t in ('#environmental_variable', '#environmental_variables') for t in tags)


def infer_element_from_filename(path: Path) -> Optional[str]:
    name = path.stem.lower()
    for e in ELEMENTS:
        if e in name:
            return e
    return None


def infer_element_from_tags(path: Path) -> Optional[str]:
    try:
        txt = path.read_text(encoding='utf-8')
    except Exception:
        return None
    tags = re.findall(r"#[-\w]+", txt)
    for t in tags:
        tn = t.lstrip('#').lower()
        if tn in ELEMENTS:
            return tn
    return None


def pc_element_level(pc_dir: Path, element: str) -> float:
    # try reading <PC>_variables.md first (table produced by generator)
    safe = pc_dir.name
    vars_path = pc_dir.joinpath(f"{safe}_variables.md")
    if vars_path.exists():
        try:
            txt = vars_path.read_text(encoding='utf-8')
            for ln in txt.splitlines():
                m = re.match(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", ln)
                if m:
                    key = m.group(1).strip().lower()
                    val = m.group(2).strip()
                    # Only accept explicit element keys or common level suffixes.
                    # Avoid matching keys that merely contain the element (e.g. 'waterbottle')
                    if key.replace(' ', '_') == element or key == element or key == element + '_level' or key == element + ' level':
                        try:
                            return float(re.sub(r'[^0-9.+-]', '', val) or 0)
                        except Exception:
                            try:
                                return float(re.sub(r'[^0-9.+-]', '', val.split()[0]))
                            except Exception:
                                return 0.0
        except Exception:
            pass
    # fallback: parse character sheet table
    sheet = pc_dir.joinpath(f"{safe} character sheet.md")
    if sheet.exists():
        try:
            txt = sheet.read_text(encoding='utf-8')
            # look for a row in Bending Levels table like: | Water | 2 |
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
    sheet = pc_dir.joinpath(f"{safe} character sheet.md")
    try:
        if sheet.exists():
            s = sheet.read_text(encoding='utf-8').lower()
            if display_name.lower() in s:
                return True
            short = cand.lower()
            if short.startswith('environmental_'):
                short = short[len('environmental_'):]
            if short in s:
                return True
    except Exception:
        pass
    return False


from typing import Optional


def scheduled_pcs_for_env(changed_path: Path, vars_root: Optional[Path] = None, pcs_root: Optional[Path] = None) -> list:
    """Return list of PC names that would be scheduled for regen when changed_path is modified.

    This mirrors the decision logic used by the CLI watcher and is intended
    for testing / dry-run introspection.
    """
    if vars_root is None:
        vars_root = ROOT.joinpath('Player Root', 'variable')
    if pcs_root is None:
        pcs_root = ROOT.joinpath('Player Root', 'PCs')
    out: list = []
    if not file_has_env_tag(changed_path):
        return out
    elem = infer_element_from_filename(changed_path) or infer_element_from_tags(changed_path)
    if not elem:
        return out
    if not pcs_root.exists():
        return out
    for pc_dir in pcs_root.iterdir():
        if not pc_dir.is_dir():
            continue
        lvl = pc_element_level(pc_dir, elem)
        if lvl < 1:
            continue
        if not pc_references_env(pc_dir, changed_path.stem.lower(), changed_path.stem.replace('_', ' ')):
            continue
        out.append(pc_dir.name)
    return out


def run_generator_for_pc(script: Path, pc_name: str, create_placeholders: bool, dry_run: bool) -> None:
    cmd = [sys.executable, str(script), '--pc', pc_name]
    if create_placeholders:
        cmd.append('--create-placeholders')
    if dry_run:
        print('[DRY] would run:', ' '.join(cmd))
        return
    try:
        subprocess.run(cmd, check=False)
    except Exception as e:
        print('Generator failed for', pc_name, e)


def _load_vars_map(vars_root: Path) -> Dict[str, float]:
    """Load simple numeric values from variable files under vars_root and secondary_stat.

    Returns mapping of normalized stem -> numeric value (or 0 if unparsable).
    """
    out: Dict[str, float] = {}
    def read_value(p: Path) -> Optional[float]:
        try:
            t = p.read_text(encoding='utf-8')
        except Exception:
            return None
        # try fenced markdown pattern produced by generator
        m = re.search(r'```markdown\n(.*?)\n\n', t, flags=re.S)
        if m:
            s = m.group(1).strip()
        else:
            # fallback: first line that isn't a tag/comment
            lines = [l.strip() for l in t.splitlines() if l.strip() and not l.strip().startswith('#')]
            s = lines[0] if lines else ''
        try:
            return float(re.sub(r'[^0-9.+-]', '', s) or 0)
        except Exception:
            try:
                m = re.search(r'[-+]?[0-9]*\.?[0-9]+', s)
                if m:
                    return float(m.group(0))
                return None
            except Exception:
                return None

    # global vars
    if vars_root.exists():
        for p in vars_root.rglob('*.md'):
            stem = p.stem.lower()
            val = read_value(p)
            if val is None:
                continue
            out[stem] = val
    # secondary_stat mirrors
    sec = vars_root.joinpath('secondary_stat')
    if sec.exists():
        for p in sec.rglob('*.md'):
            stem = p.stem.lower()
            val = read_value(p)
            if val is None:
                continue
            out[stem] = val
    return out


def _eval_expr(expr: str) -> Optional[float]:
    """Very small safe evaluator for arithmetic expressions using ast."""
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


def _update_dependent_files(changed_path: Path, vars_root: Path) -> None:
    """Find markdown files that reference the changed variable and touch or evaluate them.

    If a file contains a leading '=' formula line, attempt to substitute [[Token]] with
    values from variable files and evaluate the expression, replacing the '=' line with
    the computed numeric result. Otherwise rewrite the file to refresh its mtime.
    """
    try:
        display = changed_path.stem.replace('_', ' ')
        stem = changed_path.stem.lower()
        # build vars map
        vars_map = _load_vars_map(vars_root)
        # search repo for .md files that reference either display or stem or [[display]]
        for p in ROOT.rglob('*.md'):
            # skip variable files themselves
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
                # candidate
                changed = False
                lines = txt.splitlines()
                # find first non-empty, non-comment line
                for idx, ln in enumerate(lines):
                    s = ln.strip()
                    if not s:
                        continue
                    if s.startswith('<!--') or s.startswith('#'):
                        # still treat '#' as content sometimes; only skip pure tags
                        pass
                    # if line starts with '=', evaluate
                    if s.startswith('='):
                        expr = s.lstrip('=')
                        # substitute [[Token]] occurrences
                        def sub_token(m):
                            raw = m.group(1).strip()
                            key = re.sub(r'[^A-Za-z0-9_\-]', '_', raw).lower()
                            # try vars_map
                            v = vars_map.get(key)
                            if v is None:
                                # try with/without s plural
                                if key.endswith('s') and key[:-1] in vars_map:
                                    v = vars_map.get(key[:-1])
                                elif (key + 's') in vars_map:
                                    v = vars_map.get(key + 's')
                            return str(v if v is not None else 0)

                        new_expr = re.sub(r"\[\[\s*([^\]]+)\s*\]\]", sub_token, expr)
                        # also replace plain variable stems if present
                        for k, v in vars_map.items():
                            new_expr = re.sub(r"\b" + re.escape(k) + r"\b", str(v), new_expr, flags=re.I)
                        val = _eval_expr(new_expr)
                        if val is not None:
                            # replace the line with the computed numeric result
                            lines[idx] = str(val)
                            changed = True
                        break
                    else:
                        break
                if changed:
                    try:
                        p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                        print('Updated computed file:', p.relative_to(ROOT))
                    except Exception:
                        pass
                else:
                    # touch file by rewriting same content to update mtime
                    try:
                        p.write_text(txt, encoding='utf-8')
                        print('Touched dependent file:', p.relative_to(ROOT))
                    except Exception:
                        pass
    except Exception as e:
        print('Failed to update dependent files for', changed_path, e)


def main() -> None:
    p = argparse.ArgumentParser(description='Watch environmental variable files and regenerate affected PCs')
    p.add_argument('--interval', type=float, default=2.0)
    p.add_argument('--vars-dir', default='Player Root/variable')
    p.add_argument('--pcs-dir', default='Player Root/PCs')
    p.add_argument('--script', default='Mycelium/scripts/python/recreate_pcs.py')
    p.add_argument('--create-placeholders', action='store_true')
    p.add_argument('--debounce', type=float, default=1.0)
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    vars_root = ROOT.joinpath(args.vars_dir)
    pcs_root = ROOT.joinpath(args.pcs_dir)
    script = ROOT.joinpath(args.script)
    if not script.exists():
        print('ERROR: generator script not found:', script)
        sys.exit(1)

    last = scan_var_files(vars_root)
    # keep last text to detect content changes (not only mtime)
    last_texts: Dict[Path, str] = {}
    for p in list(last.keys()):
        try:
            last_texts[p] = p.read_text(encoding='utf-8')
        except Exception:
            last_texts[p] = ''
    last_run_for_element: Dict[str, float] = {}
    print('Watching', vars_root, 'every', args.interval, 's; generator:', script)
    try:
        while True:
            time.sleep(args.interval)
            cur = scan_var_files(vars_root)
            for path, mtime in cur.items():
                # if we recently wrote this file, ignore the following mtime change
                recent = _recently_written.get(path)
                if recent is not None and mtime <= recent + 1.5:
                    last[path] = mtime
                    continue
                prev = last.get(path)
                if prev is None or mtime > prev + 1e-6:
                    # changed file
                    if not file_has_env_tag(path):
                        # not an environmental variable; ignore
                        continue
                    # read content and compare with last_texts to avoid reacting to identical rewrites
                    try:
                        cur_txt = path.read_text(encoding='utf-8')
                    except Exception:
                        cur_txt = ''
                    prev_txt = last_texts.get(path)
                    if prev_txt is not None and cur_txt == prev_txt:
                        # no content change, skip
                        last[path] = mtime
                        continue
                    last_texts[path] = cur_txt
                    # infer element
                    elem = infer_element_from_filename(path) or infer_element_from_tags(path)
                    if not elem:
                        print('Changed environmental file but element not inferred, skipping:', path.relative_to(ROOT))
                        continue
                    now = time.time()
                    lr = last_run_for_element.get(elem, 0)
                    if now - lr < args.debounce:
                        print('Debounced element regen for', elem)
                        continue
                    print('Environmental variable changed for element', elem, 'file:', path.relative_to(ROOT))
                    # also update dependent files (rules/collection) that reference this env var
                    try:
                        _update_dependent_files(path, vars_root)
                    except Exception:
                        pass
                    # find PCs with element level >= 1
                    if not pcs_root.exists():
                        print('PCs folder not found:', pcs_root)
                        continue
                    for pc_dir in pcs_root.iterdir():
                        if not pc_dir.is_dir():
                            continue
                        lvl = pc_element_level(pc_dir, elem)
                        if lvl < 1:
                            continue
                        # only schedule regen if the PC references this env var
                        if not pc_references_env(pc_dir, path.stem.lower(), path.stem.replace('_', ' ')):
                            continue
                        pc_name = pc_dir.name
                        print(' -> scheduling regen for', pc_name, '(level', lvl, ')')
                        run_generator_for_pc(script, pc_name, args.create_placeholders, args.dry_run)
                    last_run_for_element[elem] = time.time()
                    # after we possibly ran generator(s), mark that we touched dependent files
                    try:
                        _recently_written[path] = time.time()
                    except Exception:
                        pass
            last = cur
    except KeyboardInterrupt:
        print('\nStopped')


if __name__ == '__main__':
    main()
