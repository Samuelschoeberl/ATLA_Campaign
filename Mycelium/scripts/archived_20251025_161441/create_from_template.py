#!/usr/bin/env python3
"""Create files from templates in Mycelium/template.

Usage examples:
  python3 create_from_template.py --list
  python3 create_from_template.py --template Primary_variable.md --dest "Players Part/PCs/Anju/Anju Variable.md" --var PC=Anju

This tool is intentionally small and dependency-free. It supports simple
placeholder replacement using {{KEY}} tokens.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict
import shutil

TEMPLATE_DIR = Path(__file__).resolve().parent.joinpath('template')


def list_templates() -> Dict[str, Path]:
    out = {}
    if not TEMPLATE_DIR.exists():
        return out
    for p in TEMPLATE_DIR.iterdir():
        if p.is_file() and p.suffix.lower() == '.md':
            out[p.name] = p
    return out


def render_template(path: Path, vars: Dict[str, str]) -> str:
    txt = path.read_text(encoding='utf-8')
    for k, v in vars.items():
        txt = txt.replace('{{' + k + '}}', v)
    return txt


def create_from_template(template_name: str, dest: Path, vars: Dict[str, str], overwrite: bool = False) -> Path:
    templates = list_templates()
    if template_name not in templates:
        raise FileNotFoundError(f'Template not found: {template_name}')
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not overwrite:
        raise FileExistsError(f'Destination exists: {dest}')
    txt = render_template(templates[template_name], vars)
    dest.write_text(txt, encoding='utf-8')
    # print first 200 characters preview for visibility
    preview = txt[:200]
    print(f"[wrote] {dest}")
    print("[preview]", preview if preview else "(empty)")
    return dest


def cli(argv=None) -> int:
    p = argparse.ArgumentParser(prog='create_from_template')
    p.add_argument('--list', action='store_true')
    p.add_argument('--template', help='Template filename inside Mycelium/template')
    p.add_argument('--dest', help='Destination path to write the rendered template')
    p.add_argument('--var', action='append', default=[], help='Key=Value placeholder substitution; may be repeated')
    p.add_argument('--overwrite', action='store_true')
    args = p.parse_args(argv)

    if args.list:
        for name in sorted(list_templates()):
            print(name)
        return 0

    if not args.template or not args.dest:
        print('usage: --template NAME --dest PATH [--var KEY=VAL]')
        return 2

    vars: Dict[str, str] = {}
    for v in args.var:
        if '=' in v:
            k, val = v.split('=', 1)
            vars[k] = val
    try:
        p = create_from_template(args.template, Path(args.dest), vars, overwrite=args.overwrite)
        print('Wrote', p)
        return 0
    except Exception as e:
        print('Error:', e)
        return 3


if __name__ == '__main__':
    raise SystemExit(cli())
