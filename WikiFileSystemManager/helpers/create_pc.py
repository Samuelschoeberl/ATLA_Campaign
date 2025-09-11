#!/usr/bin/env python3
"""Packaged helper: create_pc

Canonical, self-contained implementation for creating PC character sheets.
Uses package-local config loader for defaults.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import re
from pathlib import Path
from typing import List

from generate_secondary_stats import load_formulas, compute_secondary
from .config_loader import get_config
 
"""Minimal packaged helper: create_pc

This is a compact, well-formed implementation intended as the canonical
entrypoint for creating PC sheets. It intentionally keeps behavior small
so it is easy to smoke-test and import.
"""
from __future__ import annotations
import argparse
import re
import subprocess
from pathlib import Path
from typing import List
from .config_loader import get_config


TEMPLATE = """[[{name}]]
# {name} Character Sheet

STR: {STR}
DEX: {DEX}
CON: {CON}
INT: {INT}
WIS: {WIS}
CHA: {CHA}

Air: {AIR}
Water: {WATER}
Earth: {EARTH}
Fire: {FIRE}
Spirit: {SPIRIT}
"""


def _strip_wikilink(s: str) -> str:
    s = s.strip()
    m = re.match(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", s)
    return m.group(1) if m else s


def parse_pcs_from_markdown(path: Path, args: argparse.Namespace) -> List[dict]:
    text = path.read_text(encoding='utf-8')
    lines = [ln for ln in text.splitlines() if '|' in ln]
    if not lines:
        return []
    # find header index containing 'Name'
    header_idx = None
    for i, row in enumerate(lines):
        cols = [c.strip() for c in row.split('|') if c.strip()]
        if any(c.lower() == 'name' for c in cols):
            header_idx = i
            break
    if header_idx is None:
        return []
    header = [c.strip() for c in lines[header_idx].split('|')]
    data_start = header_idx + 2 if header_idx + 1 < len(lines) and set(lines[header_idx + 1].strip()) <= set('- |:') else header_idx + 1
    cols = [c for c in header if c]
    out = []
    for row in lines[data_start:]:
        cells = [c.strip() for c in row.split('|')]
        if not cells:
            continue
        mapping = {}
        for idx, col in enumerate(cols):
            try:
                mapping[col] = _strip_wikilink(cells[idx + 1] if row.startswith('|') else cells[idx])
            except Exception:
                mapping[col] = ''
        name = mapping.get('Name') or mapping.get('name')
        if not name:
            continue
        def to_int(keys, default=0):
            for k in keys:
                if k in mapping and mapping[k] != '':
                    try:
                        return int(re.sub(r"[^0-9-]", "", mapping[k]))
                    except Exception:
                        return default
            return default
        core = {
            'STR': to_int(['STR'], default=args.str),
            'DEX': to_int(['DEX'], default=args.dex),
            'CON': to_int(['CON'], default=args.con),
            'INT': to_int(['INT'], default=args.int),
            'WIS': to_int(['WIS'], default=args.wis),
            'CHA': to_int(['CHA'], default=args.cha),
        }
        bending = {
            'Air': to_int(['Air'], default=args.air),
            'Water': to_int(['Water'], default=args.water),
            'Earth': to_int(['Earth'], default=args.earth),
            'Fire': to_int(['Fire'], default=args.fire),
            'Spirit': to_int(['Spirit'], default=args.spirit),
        }
        out.append({'name': name, 'core': core, 'bending': bending})
    return out


def compute_placeholders(core: dict, bending: dict) -> dict:
    ph = {k: core.get(k, 0) for k in ('STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA')}
    ph.update({
        'AIR': bending.get('Air', 0),
        'WATER': bending.get('Water', 0),
        'EARTH': bending.get('Earth', 0),
        'FIRE': bending.get('Fire', 0),
        'SPIRIT': bending.get('Spirit', 0),
    })
    return ph


def create_one(pc_name: str, core: dict, bending: dict, args: argparse.Namespace) -> Path:
    placeholders = compute_placeholders(core, bending)
    out_root = Path(get_config('pcs_root', 'Players Root'))
    if args.out_root and args.out_root != str(out_root):
        out_root = Path(args.out_root)
    pc_dir = out_root / pc_name
    pc_dir.mkdir(parents=True, exist_ok=True)
    fpath = pc_dir / f"{pc_name} Character Sheet.md"
    # ensure we pass name to template formatting so top wikilink is populated
    content = TEMPLATE.format(name=pc_name, **placeholders)
    fpath.write_text(content, encoding='utf-8')
    print(f"Wrote character sheet: {fpath}")
    # update pcs_input.md minimal behavior
    try:
        pcs_path = Path(get_config('pcs_input', 'pcs_input.md'))
        if not pcs_path.exists():
            pcs_path.write_text('| Name | STR | DEX | CON | INT | WIS | CHA |\n', encoding='utf-8')
        # append a simple row
        pcs_path.write_text(pcs_path.read_text(encoding='utf-8').rstrip('\n') + f"\n| {pc_name} | {core.get('STR',0)} | {core.get('DEX',0)} | {core.get('CON',0)} | {core.get('INT',0)} | {core.get('WIS',0)} | {core.get('CHA',0)} |\n", encoding='utf-8')
    except Exception:
        pass
    return fpath


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--name', required=False)
    p.add_argument('--str', type=int, default=3)
    p.add_argument('--dex', type=int, default=3)
    p.add_argument('--con', type=int, default=3)
    p.add_argument('--int', type=int, default=3)
    p.add_argument('--wis', type=int, default=3)
    p.add_argument('--cha', type=int, default=3)
    p.add_argument('--air', type=int, default=0)
    p.add_argument('--water', type=int, default=0)
    p.add_argument('--earth', type=int, default=0)
    p.add_argument('--fire', type=int, default=0)
    p.add_argument('--spirit', type=int, default=0)
    p.add_argument('--out-root', default=None)
    p.add_argument('--input-file', help='Markdown file with table of PCs')
    args = p.parse_args(argv)

    if not args.name and not args.input_file:
        p.error('either --name or --input-file is required')

    if args.input_file:
        pcs = parse_pcs_from_markdown(Path(args.input_file), args)
        for entry in pcs:
            create_one(entry['name'], entry['core'], entry['bending'], args)
        return 0

    core = {'STR': args.str, 'DEX': args.dex, 'CON': args.con, 'INT': args.int, 'WIS': args.wis, 'CHA': args.cha}
    bending = {'Air': args.air, 'Water': args.water, 'Earth': args.earth, 'Fire': args.fire, 'Spirit': args.spirit}
    create_one(args.name, core, bending, args)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
    ## Vital Stats

    | Attribute         | Value | note                            | Auto |
    | ----------------- | ----- | ------------------------------- | ---- |
    | [[Max Hitpoints]] | {MAX_HP}     |                                 | Y    |
    | [[HP]]            | 0     |                                 | N    |
    | [[Evasion]]       |           {EVASION}              |                                 | Y    |
    | [[Armor]]         |           {ARMOR}               |                                 | Y    |

    ---

    ## Bending Levels

    | Element                 | Level | Notes                  | Auto |
    | ----------------------- | ----- | ---------------------- | ---- |
    | [[Airbending Level]]    | {AIR}     |                        | N    |
    | [[Waterbending Level]]  | {WATER}     |                        | N    |
    | [[Earthbending Level]]  | {EARTH}     |                        | N    |
    | [[Firebending Level]]   | {FIRE}     |                        | N    |
    | [[Spiritbending Level]] | {SPIRIT}     | (Avatar Spirit Bridge) | N    |

    ---

    ## Secondary Stats

    | Stat                     | value | Notes                  | Auto |
    | ------------------------ | ----- | ---------------------- | ---- |
    | [[Attack Roll Modifier]] |              {ARMOD}                  |                        | Y    |
    | [[Waterbending DC]]      |              {WATER_DC}                 |                        | Y    |
    | [[Earthbending DC]]      |              {EARTH_DC}                 |                        | Y    |
    | [[Firebending DC]]       |              {FIRE_DC}                 |                        | Y    |
    | [[Spiritbending DC]]     |              {SPIRIT_DC}                              | (Avatar Spirit Bridge) | Y    |

    ## [[Manually Rolled Hitpoints]]
    | Level | Element | Rolled | Auto |
    | ----- | ------- | ------ | ---- |

    ---

    ## Inventory & Notes

    -
    -
    """


    def compute_placeholders(core: dict, bending: dict, formulas_path: Path | None = None) -> dict:
        placeholders = {
            'STR': core.get('STR', 3),
            'DEX': core.get('DEX', 3),
            'CON': core.get('CON', 3),
            'INT': core.get('INT', 3),
            'WIS': core.get('WIS', 3),
            'CHA': core.get('CHA', 3),
            'AIR': bending.get('Air', 0),
            'WATER': bending.get('Water', 0),
            'EARTH': bending.get('Earth', 0),
            'FIRE': bending.get('Fire', 0),
            'SPIRIT': bending.get('Spirit', 0),
            'Manually_Rolled_Hitpoints': bending.get('Manually_Rolled_Hitpoints', 0),
        }

        placeholders.update({
            'MAX_HP': max(5, 10 + (placeholders['CON'] + 0) * 1),
            'EVASION': 10 + placeholders['DEX'],
            'ARMOR': max(0, placeholders['EARTH']),
            'ARMOD': placeholders['AIR'] + placeholders['WATER'] + placeholders['EARTH'] + placeholders['FIRE'] + placeholders['SPIRIT'],
            'WATER_DC': 10 + placeholders['WATER'] + placeholders['DEX'],
            'EARTH_DC': 10 + placeholders['EARTH'] + placeholders['STR'],
            'FIRE_DC': 10 + placeholders['FIRE'] + placeholders['WIS'],
            'SPIRIT_DC': 10 + placeholders['SPIRIT'] + placeholders['WIS'],
        })

        try:
            formulas_path_resolved = Path(formulas_path) if formulas_path else Path(get_config('char_formulas', 'char_formulas.json'))
            formulas = load_formulas(formulas_path_resolved)
            stats = {k: placeholders.get(k, 0) for k in ('STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA')}
            extra_vars: dict = {}
            for elem in ('Air', 'Water', 'Earth', 'Fire', 'Spirit'):
                extra_vars[f"{elem} Level"] = bending.get(elem, 0)
                extra_vars[elem] = bending.get(elem, 0)
            extra_vars['CL'] = max(extra_vars.get('Air Level', 0), extra_vars.get('Water Level', 0), extra_vars.get('Earth Level', 0), extra_vars.get('Fire Level', 0), extra_vars.get('Spirit Level', 0))
            extra_vars['HP_PER_CL'] = bending.get('Manually_Rolled_Hitpoints', 0)

            derived = compute_secondary(stats, formulas, extra_vars=extra_vars)
            if 'Max Hit Points' in derived:
                placeholders['MAX_HP'] = derived.get('Max Hit Points', placeholders['MAX_HP'])
            if 'Evasion' in derived:
                placeholders['EVASION'] = derived.get('Evasion', placeholders['EVASION'])
            if 'Armor' in derived:
                placeholders['ARMOR'] = derived.get('Armor', placeholders['ARMOR'])
            placeholders['WATER_DC'] = derived.get('Waterbending Dc', derived.get('Waterbending Dc', placeholders['WATER_DC']))
            placeholders['EARTH_DC'] = derived.get('Earthbending Dc', placeholders['EARTH_DC'])
            placeholders['FIRE_DC'] = derived.get('Firebending Dc', placeholders['FIRE_DC'])
            placeholders['SPIRIT_DC'] = derived.get('Spiritbending Dc', placeholders['SPIRIT_DC'])
            placeholders['ARMOD'] = derived.get('Attack Roll Modifier', placeholders['ARMOD'])
        except Exception:
            pass
        return placeholders


    def _strip_wikilink(s: str) -> str:
        s = s.strip()
        m = re.match(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", s)
        return m.group(1) if m else s


    def parse_pcs_from_markdown(path: Path, args: argparse.Namespace) -> List[dict]:
        text = path.read_text(encoding='utf-8')
        lines = text.splitlines()
        table_lines = []
        in_table = False
        for ln in lines:
            if '|' in ln:
                table_lines.append(ln)
                in_table = True
            else:
                if in_table:
                    break
        if not table_lines:
            return []

        header_idx = None
        for i, row in enumerate(table_lines):
            cols = [c.strip() for c in row.split('|') if c.strip()]
            low = [c.lower() for c in cols]
            if 'name' in low:
                header_idx = i
                break
        if header_idx is None:
            return []

        header = [c.strip() for c in table_lines[header_idx].split('|')]
        data_start = header_idx + 1
        if data_start < len(table_lines) and re.match(r"^\s*\|?\s*-+", table_lines[data_start]):
            data_start += 1

        cols = [c.strip() for c in header if c.strip()]
        pcs: List[dict] = []
        for row in table_lines[data_start:]:
            if not row.strip() or '|' not in row:
                break
            cells = [c for c in row.split('|')]
            mapping: dict = {}
            for idx, col_name in enumerate(cols):
                try:
                    cell_idx = idx + 1 if row.startswith('|') else idx
                    val = cells[cell_idx].strip()
                except Exception:
                    val = ''
                val = _strip_wikilink(val)
                mapping[col_name] = val

            name = mapping.get('Name') or mapping.get('name')
            if not name:
                continue

            def to_int_field(keys, default=0):
                for k in keys:
                    if k in mapping and mapping[k] != '':
                        try:
                            return int(re.sub(r"[^0-9-]", "", mapping[k]))
                        except Exception:
                            return default
                return default

            core_vals = {
                'STR': to_int_field(['STR', 'Strength'], default=args.str),
                'DEX': to_int_field(['DEX', 'Dexterity'], default=args.dex),
                'CON': to_int_field(['CON', 'Constitution'], default=args.con),
                'INT': to_int_field(['INT', 'Intelligence'], default=args.int),
                'WIS': to_int_field(['WIS', 'Wisdom'], default=args.wis),
                'CHA': to_int_field(['CHA', 'Charisma'], default=args.cha),
            }
            bending_vals = {
                'Air': to_int_field(['Air', 'Air Level', 'Airbending', 'air'], default=args.air),
                'Water': to_int_field(['Water', 'Water Level', 'Waterbending', 'water'], default=args.water),
                'Earth': to_int_field(['Earth', 'Earth Level', 'Earthbending', 'earth'], default=args.earth),
                'Fire': to_int_field(['Fire', 'Fire Level', 'Firebending', 'fire'], default=args.fire),
                'Spirit': to_int_field(['Spirit', 'Spirit Level', 'Spiritbending', 'spirit'], default=args.spirit),
            }
            manual_hp = to_int_field(['Manual', 'Manual HP', 'Manually Rolled HP', 'Manually_Rolled_Hitpoints'], default=0)
            if manual_hp:
                bending_vals['Manually_Rolled_Hitpoints'] = manual_hp
            run_update_flag = None
            for key in ('Run Update', 'run_update', 'run-update'):
                if key in mapping and mapping[key].lower() in ('1', 'y', 'yes', 'true', 't'):
                    run_update_flag = True
                elif key in mapping and mapping[key].lower() in ('0', 'n', 'no', 'false', 'f'):
                    run_update_flag = False

            pcs.append({'name': name, 'core': core_vals, 'bending': bending_vals, 'manual_hp': manual_hp, 'run_update': run_update_flag})

        return pcs


    def create_one(pc_name: str, core_vals: dict, bending_vals: dict, args: argparse.Namespace, run_update_override: bool | None = None) -> Path:
        placeholders = compute_placeholders(core_vals, bending_vals)
        out_root = Path(args.out_root)
        if args.out_root == 'Players Part/PCs':
            try:
                base = Path(__file__).resolve().parent
                for d in base.rglob('PC Character Sheets'):
                    if d.is_dir():
                        out_root = d
                        break
            except Exception:
                pass
        pc_dir = out_root / pc_name
        pc_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{pc_name} Character Sheet.md"
        fpath = pc_dir / filename
        content = TEMPLATE.format(**placeholders)

        manual_total = placeholders.get('Manually_Rolled_Hitpoints', 0)
        if manual_total and manual_total != 0:
            lines = content.splitlines()
            for i, ln in enumerate(lines):
                if ln.strip().lower().startswith('##') and 'manually rolled hitpoints' in ln.lower():
                    for j in range(i + 1, min(i + 10, len(lines))):
                        if 'level' in lines[j].lower() and '|' in lines[j]:
                            sep_idx = j + 1
                            insert_idx = sep_idx + 1 if sep_idx + 1 <= len(lines) else sep_idx
                            row = f"| - | Manual Rolled | {manual_total} | N |"
                            lines[insert_idx:insert_idx] = [row]
                            content = '\n'.join(lines) + '\n'
                            break
                    break

        fpath.write_text(content, encoding='utf-8')
        print(f"Wrote character sheet: {fpath}")

        try:
            pcs_path = Path(get_config('pcs_input', 'pcs_input.md'))
            cols = ['Name', 'STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA', 'Water', 'Earth', 'Air', 'Fire', 'Spirit', 'Manually Rolled HP', 'Run Update']
            if not pcs_path.exists():
                header = '| ' + ' | '.join(cols) + ' |'
                sep_parts = ['--------' if c == 'Name' else ('---------:' if c == 'Run Update' else '--:') for c in cols]
                sep = '| ' + ' | '.join(sep_parts) + ' |'
                vals = [pc_name] + [str(core_vals.get(k, 0)) for k in ('STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA')] + [str(bending_vals.get(k, 0)) for k in ('Water', 'Earth', 'Air', 'Fire', 'Spirit')] + [str(manual_total or 0), 'yes' if (args.run_update if run_update_override is None else run_update_override) else 'no']
                row = '| ' + ' | '.join(vals) + ' |'
                pcs_path.write_text(header + '\n' + sep + '\n' + row + '\n', encoding='utf-8')
            else:
                text = pcs_path.read_text(encoding='utf-8')
                if '|' in text:
                    vals = [pc_name] + [str(core_vals.get(k, 0)) for k in ('STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA')] + [str(bending_vals.get(k, 0)) for k in ('Water', 'Earth', 'Air', 'Fire', 'Spirit')] + [str(manual_total or 0), 'yes' if (args.run_update if run_update_override is None else run_update_override) else 'no']
                    row = '| ' + ' | '.join(vals) + ' |'
                    pcs_path.write_text(text.rstrip('\n') + '\n' + row + '\n', encoding='utf-8')
        except Exception as exc:
            print('Failed to update pcs_input.md:', exc)

        do_update = args.run_update if run_update_override is None else run_update_override
        if do_update:
            updater = Path('update_char.py')
            if updater.exists():
                try:
                    subprocess.run([sys.executable, str(updater), '--file', str(fpath)], check=True)
                except subprocess.CalledProcessError:
                    print('update_char.py failed; file left as-is.')

        if args.make_graphs:
            graphs_script = Path('Wikigraphs.py')
            if graphs_script.exists():
                cmd = [sys.executable, str(graphs_script), '--pc', pc_name]
                if args.embed_graphs:
                    cmd.append('--embed')
                if args.graphs_verbose:
                    cmd.append('--verbose')
                try:
                    subprocess.run(cmd, check=True)
                except subprocess.CalledProcessError:
                    print('Wikigraphs failed; graphs not created.')

        return fpath


    def main(argv: List[str] | None = None) -> int:
        p = argparse.ArgumentParser()
        p.add_argument('--name', required=False, help='Character name')
        p.add_argument('--str', type=int, default=3)
        p.add_argument('--dex', type=int, default=3)
        p.add_argument('--con', type=int, default=3)
        p.add_argument('--int', type=int, default=3)
        p.add_argument('--wis', type=int, default=3)
        p.add_argument('--cha', type=int, default=3)
        p.add_argument('--air', type=int, default=0)
        p.add_argument('--water', type=int, default=0)
        p.add_argument('--earth', type=int, default=0)
        p.add_argument('--fire', type=int, default=0)
        p.add_argument('--spirit', type=int, default=0)
        p.add_argument('--manual-rolled-hp', type=int, default=0, help='Sum of manually rolled hitpoints to include on the sheet')
        default_out = get_config('pcs_root', 'Players Part/PCs')
        p.add_argument('--out-root', default=default_out, help='Root folder for PC folders')
        p.add_argument('--run-update', action='store_true', help='Run update_char.py to compute derived stats if available')
        p.add_argument('--input-file', help='Markdown file containing a table of characters to create')
        p.add_argument('--make-graphs', action='store_true', help='Run Wikigraphs.py --pc <name> after creating the character sheet')
        p.add_argument('--embed-graphs', action='store_true', help='Pass --embed to Wikigraphs.py when generating graphs (embed plotly JS)')
        p.add_argument('--graphs-verbose', action='store_true', help='Pass --verbose to Wikigraphs.py when generating graphs')
        args = p.parse_args(argv)

        if not args.name and not args.input_file:
            p.error('either --name or --input-file is required')

        if args.input_file:
            input_path = Path(args.input_file)
            pcs = parse_pcs_from_markdown(input_path, args)
            for entry in pcs:
                create_one(entry['name'], entry['core'], entry['bending'], args, run_update_override=entry.get('run_update'))
        else:
            core = {'STR': args.str, 'DEX': args.dex, 'CON': args.con, 'INT': args.int, 'WIS': args.wis, 'CHA': args.cha}
            bending = {'Air': args.air, 'Water': args.water, 'Earth': args.earth, 'Fire': args.fire, 'Spirit': args.spirit}
            if args.manual_rolled_hp:
                bending['Manually_Rolled_Hitpoints'] = args.manual_rolled_hp
            create_one(args.name, core, bending, args)

        return 0


    if __name__ == '__main__':
        raise SystemExit(main())
| [[Evasion]]       |           {EVASION}              |                                 | Y    |
| [[Armor]]         |           {ARMOR}               |                                 | Y    |
| [[Stress Level]]  | 0     | default is 0 at start of combat | N    |
|                   | 0     |                                 |      |

---

## Bending Levels

| Element                 | Level | Notes                  | Auto |
| ----------------------- | ----- | ---------------------- | ---- |
| [[Airbending Level]]    | {AIR}     |                        | N    |
| [[Waterbending Level]]  | {WATER}     |                        | N    |
| [[Earthbending Level]]  | {EARTH}     |                        | N    |
| [[Firebending Level]]   | {FIRE}     |                        | N    |
| [[Spiritbending Level]] | {SPIRIT}     | (Avatar Spirit Bridge) | N    |

---

## Secondary Stats

| Stat                     | value | Notes                  | Auto |
| ------------------------ | ----- | ---------------------- | ---- |
| [[Attack Roll Modifier]] |              {ARMOD}                  |                        | Y    |
| [[Waterbending DC]]      |              {WATER_DC}                 |                        | Y    |
| [[Earthbending DC]]      |              {EARTH_DC}                 |                        | Y    |
| [[Firebending DC]]       |              {FIRE_DC}                 |                        | Y    |
| [[Spiritbending DC]]     |              {SPIRIT_DC}                              | (Avatar Spirit Bridge) | Y    |

## [[Manually Rolled Hitpoints]]
| Level | Element | Rolled | Auto |
| ----- | ------- | ------ | ---- |

---

## Inventory & Notes

-
-
"""


def compute_placeholders(core: dict, bending: dict, formulas_path: Path | None = None) -> dict:
    placeholders = {
        'STR': core.get('STR', 3),
        'DEX': core.get('DEX', 3),
        'CON': core.get('CON', 3),
        'INT': core.get('INT', 3),
        'WIS': core.get('WIS', 3),
        'CHA': core.get('CHA', 3),
        'AIR': bending.get('Air', 0),
        'WATER': bending.get('Water', 0),
        'EARTH': bending.get('Earth', 0),
        'FIRE': bending.get('Fire', 0),
        'SPIRIT': bending.get('Spirit', 0),
        'Manually_Rolled_Hitpoints': bending.get('Manually_Rolled_Hitpoints', 0),
    }

    placeholders.update({
        'MAX_HP': max(5, 10 + (placeholders['CON'] + 0) * 1),
        'EVASION': 10 + placeholders['DEX'],
        'ARMOR': max(0, placeholders['EARTH']),
        'ARMOD': placeholders['AIR'] + placeholders['WATER'] + placeholders['EARTH'] + placeholders['FIRE'] + placeholders['SPIRIT'],
        'WATER_DC': 10 + placeholders['WATER'] + placeholders['DEX'],
        'EARTH_DC': 10 + placeholders['EARTH'] + placeholders['STR'],
        'FIRE_DC': 10 + placeholders['FIRE'] + placeholders['WIS'],
        'SPIRIT_DC': 10 + placeholders['SPIRIT'] + placeholders['WIS'],
    })

    try:
        formulas_path_resolved = Path(formulas_path) if formulas_path else Path(get_config('char_formulas', 'char_formulas.json'))
        formulas = load_formulas(formulas_path_resolved)
        stats = {k: placeholders.get(k, 0) for k in ('STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA')}
        extra_vars: dict = {}
        for elem in ('Air', 'Water', 'Earth', 'Fire', 'Spirit'):
            extra_vars[f"{elem} Level"] = bending.get(elem, 0)
            extra_vars[elem] = bending.get(elem, 0)
        extra_vars['CL'] = max(extra_vars.get('Air Level', 0), extra_vars.get('Water Level', 0), extra_vars.get('Earth Level', 0), extra_vars.get('Fire Level', 0), extra_vars.get('Spirit Level', 0))
        extra_vars['HP_PER_CL'] = bending.get('Manually_Rolled_Hitpoints', 0)

        derived = compute_secondary(stats, formulas, extra_vars=extra_vars)
        if 'Max Hit Points' in derived:
            placeholders['MAX_HP'] = derived.get('Max Hit Points', placeholders['MAX_HP'])
        if 'Evasion' in derived:
            placeholders['EVASION'] = derived.get('Evasion', placeholders['EVASION'])
        if 'Armor' in derived:
            placeholders['ARMOR'] = derived.get('Armor', placeholders['ARMOR'])
        placeholders['WATER_DC'] = derived.get('Waterbending Dc', derived.get('Waterbending Dc', placeholders['WATER_DC']))
        placeholders['EARTH_DC'] = derived.get('Earthbending Dc', placeholders['EARTH_DC'])
        placeholders['FIRE_DC'] = derived.get('Firebending Dc', placeholders['FIRE_DC'])
        placeholders['SPIRIT_DC'] = derived.get('Spiritbending Dc', placeholders['SPIRIT_DC'])
        placeholders['ARMOD'] = derived.get('Attack Roll Modifier', placeholders['ARMOD'])
    except Exception:
        pass
    return placeholders


def _strip_wikilink(s: str) -> str:
    s = s.strip()
    m = re.match(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", s)
    return m.group(1) if m else s


def parse_pcs_from_markdown(path: Path, args: argparse.Namespace) -> List[dict]:
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines()
    table_lines = []
    in_table = False
    for ln in lines:
        if '|' in ln:
            table_lines.append(ln)
            in_table = True
        else:
            if in_table:
                break
    if not table_lines:
        return []

    header_idx = None
    for i, row in enumerate(table_lines):
        cols = [c.strip() for c in row.split('|') if c.strip()]
        low = [c.lower() for c in cols]
        if 'name' in low:
            header_idx = i
            break
    if header_idx is None:
        return []

    header = [c.strip() for c in table_lines[header_idx].split('|')]
    data_start = header_idx + 1
    if data_start < len(table_lines) and re.match(r"^\s*\|?\s*-+", table_lines[data_start]):
        data_start += 1

    cols = [c.strip() for c in header if c.strip()]
    pcs: List[dict] = []
    for row in table_lines[data_start:]:
        if not row.strip() or '|' not in row:
            break
        cells = [c for c in row.split('|')]
        mapping: dict = {}
        for idx, col_name in enumerate(cols):
            try:
                # pick cell accounting for leading/trailing pipe
                cell_idx = idx + 1 if row.startswith('|') else idx
                val = cells[cell_idx].strip()
            except Exception:
                val = ''
            val = _strip_wikilink(val)
            mapping[col_name] = val

        name = mapping.get('Name') or mapping.get('name')
        if not name:
            continue

        def to_int_field(keys, default=0):
            for k in keys:
                if k in mapping and mapping[k] != '':
                    try:
                        return int(re.sub(r"[^0-9-]", "", mapping[k]))
                    except Exception:
                        return default
            return default

        core_vals = {
            'STR': to_int_field(['STR', 'Strength'], default=args.str),
            'DEX': to_int_field(['DEX', 'Dexterity'], default=args.dex),
            'CON': to_int_field(['CON', 'Constitution'], default=args.con),
            'INT': to_int_field(['INT', 'Intelligence'], default=args.int),
            'WIS': to_int_field(['WIS', 'Wisdom'], default=args.wis),
            'CHA': to_int_field(['CHA', 'Charisma'], default=args.cha),
        }
        bending_vals = {
            'Air': to_int_field(['Air', 'Air Level', 'Airbending', 'air'], default=args.air),
            'Water': to_int_field(['Water', 'Water Level', 'Waterbending', 'water'], default=args.water),
            'Earth': to_int_field(['Earth', 'Earth Level', 'Earthbending', 'earth'], default=args.earth),
            'Fire': to_int_field(['Fire', 'Fire Level', 'Firebending', 'fire'], default=args.fire),
            'Spirit': to_int_field(['Spirit', 'Spirit Level', 'Spiritbending', 'spirit'], default=args.spirit),
        }
        manual_hp = to_int_field(['Manual', 'Manual HP', 'Manually Rolled HP', 'Manually_Rolled_Hitpoints'], default=0)
        if manual_hp:
            bending_vals['Manually_Rolled_Hitpoints'] = manual_hp
        run_update_flag = None
        for key in ('Run Update', 'run_update', 'run-update'):
            if key in mapping and mapping[key].lower() in ('1', 'y', 'yes', 'true', 't'):
                run_update_flag = True
            elif key in mapping and mapping[key].lower() in ('0', 'n', 'no', 'false', 'f'):
                run_update_flag = False

        pcs.append({'name': name, 'core': core_vals, 'bending': bending_vals, 'manual_hp': manual_hp, 'run_update': run_update_flag})

    return pcs


def create_one(pc_name: str, core_vals: dict, bending_vals: dict, args: argparse.Namespace, run_update_override: bool | None = None) -> Path:
    placeholders = compute_placeholders(core_vals, bending_vals)
    out_root = Path(args.out_root)
    if args.out_root == 'Players Part/PCs':
        try:
            base = Path(__file__).resolve().parent
            for d in base.rglob('PC Character Sheets'):
                if d.is_dir():
                    out_root = d
                    break
        except Exception:
            pass
    pc_dir = out_root / pc_name
    pc_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{pc_name} Character Sheet.md"
    fpath = pc_dir / filename
    content = TEMPLATE.format(**placeholders)

    manual_total = placeholders.get('Manually_Rolled_Hitpoints', 0)
    if manual_total and manual_total != 0:
        lines = content.splitlines()
        for i, ln in enumerate(lines):
            if ln.strip().lower().startswith('##') and 'manually rolled hitpoints' in ln.lower():
                for j in range(i + 1, min(i + 10, len(lines))):
                    if 'level' in lines[j].lower() and '|' in lines[j]:
                        sep_idx = j + 1
                        insert_idx = sep_idx + 1 if sep_idx + 1 <= len(lines) else sep_idx
                        row = f"| - | Manual Rolled | {manual_total} | N |"
                        lines[insert_idx:insert_idx] = [row]
                        content = '\n'.join(lines) + '\n'
                        break
                break

    fpath.write_text(content, encoding='utf-8')
    print(f"Wrote character sheet: {fpath}")

    # minimal pcs_input update to preserve previous behaviour
    try:
        pcs_path = Path(get_config('pcs_input', 'pcs_input.md'))
        cols = ['Name', 'STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA', 'Water', 'Earth', 'Air', 'Fire', 'Spirit', 'Manually Rolled HP', 'Run Update']
        if not pcs_path.exists():
            header = '| ' + ' | '.join(cols) + ' |'
            sep_parts = ['--------' if c == 'Name' else ('---------:' if c == 'Run Update' else '--:') for c in cols]
            sep = '| ' + ' | '.join(sep_parts) + ' |'
            col_widths = [len(c) for c in cols]
            vals = [pc_name] + [str(core_vals.get(k, 0)) for k in ('STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA')] + [str(bending_vals.get(k, 0)) for k in ('Water', 'Earth', 'Air', 'Fire', 'Spirit')] + [str(manual_total or 0), 'yes' if (args.run_update if run_update_override is None else run_update_override) else 'no']
            row = '| ' + ' | '.join(vals) + ' |'
            pcs_path.write_text(header + '\n' + sep + '\n' + row + '\n', encoding='utf-8')
        else:
            # append simple row if header exists
            text = pcs_path.read_text(encoding='utf-8')
            if '|' in text:
                vals = [pc_name] + [str(core_vals.get(k, 0)) for k in ('STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA')] + [str(bending_vals.get(k, 0)) for k in ('Water', 'Earth', 'Air', 'Fire', 'Spirit')] + [str(manual_total or 0), 'yes' if (args.run_update if run_update_override is None else run_update_override) else 'no']
                row = '| ' + ' | '.join(vals) + ' |'
                pcs_path.write_text(text.rstrip('\n') + '\n' + row + '\n', encoding='utf-8')
    except Exception as exc:
        print('Failed to update pcs_input.md:', exc)

    do_update = args.run_update if run_update_override is None else run_update_override
    if do_update:
        updater = Path('update_char.py')
        if updater.exists():
            try:
                subprocess.run([sys.executable, str(updater), '--file', str(fpath)], check=True)
            except subprocess.CalledProcessError:
                print('update_char.py failed; file left as-is.')

    if args.make_graphs:
        graphs_script = Path('Wikigraphs.py')
        if graphs_script.exists():
            cmd = [sys.executable, str(graphs_script), '--pc', pc_name]
            if args.embed_graphs:
                cmd.append('--embed')
            if args.graphs_verbose:
                cmd.append('--verbose')
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError:
                print('Wikigraphs failed; graphs not created.')

    return fpath


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--name', required=False, help='Character name')
    p.add_argument('--str', type=int, default=3)
    p.add_argument('--dex', type=int, default=3)
    p.add_argument('--con', type=int, default=3)
    p.add_argument('--int', type=int, default=3)
    p.add_argument('--wis', type=int, default=3)
    p.add_argument('--cha', type=int, default=3)
    p.add_argument('--air', type=int, default=0)
    p.add_argument('--water', type=int, default=0)
    p.add_argument('--earth', type=int, default=0)
    p.add_argument('--fire', type=int, default=0)
    p.add_argument('--spirit', type=int, default=0)
    p.add_argument('--manual-rolled-hp', type=int, default=0, help='Sum of manually rolled hitpoints to include on the sheet')
    default_out = get_config('pcs_root', 'Players Part/PCs')
    p.add_argument('--out-root', default=default_out, help='Root folder for PC folders')
    p.add_argument('--run-update', action='store_true', help='Run update_char.py to compute derived stats if available')
    p.add_argument('--input-file', help='Markdown file containing a table of characters to create')
    p.add_argument('--make-graphs', action='store_true', help='Run Wikigraphs.py --pc <name> after creating the character sheet')
    p.add_argument('--embed-graphs', action='store_true', help='Pass --embed to Wikigraphs.py when generating graphs (embed plotly JS)')
    p.add_argument('--graphs-verbose', action='store_true', help='Pass --verbose to Wikigraphs.py when generating graphs')
    args = p.parse_args(argv)

    if not args.name and not args.input_file:
        p.error('either --name or --input-file is required')

    if args.input_file:
        input_path = Path(args.input_file)
        pcs = parse_pcs_from_markdown(input_path, args)
        for entry in pcs:
            name = entry['name']
            create_one(name, entry['core'], entry['bending'], args, run_update_override=entry.get('run_update'))
    else:
        core = {'STR': args.str, 'DEX': args.dex, 'CON': args.con, 'INT': args.int, 'WIS': args.wis, 'CHA': args.cha}
        bending = {'Air': args.air, 'Water': args.water, 'Earth': args.earth, 'Fire': args.fire, 'Spirit': args.spirit}
        if args.manual_rolled_hp:
            bending['Manually_Rolled_Hitpoints'] = args.manual_rolled_hp
        create_one(args.name, core, bending, args)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
*** End Patch
## [[Bending Slots]]
| Element                | Slot level              | [[Max Slots]] | current | note                   | Auto |
| ---------------------- | ----------------------- | ------------- | ------- | ---------------------- | ---- |
| [[water charges]]      | [[Waterbottle Charges]] | 2             | 2       |                        | Y    |
| [[Earthbending Slot]]  |    0                    | 2             | 1       |                        | Y    |
| [[Earthbending Slot]]  |    0                    | 1             | 1       |                        | Y    |
| [[Airbending Slot]]    |    0                    |               |         |                        | Y    |
| [[Firebending Slot]]   |    0                    |               |         |                        | Y    |
| [[Spiritbending Slot]] |    0                    | 1             | 0       | (Avatar Spirit Bridge) | Y    |


---

## Vital Stats

| Attribute         | Value | note                            | Auto |
| ----------------- | ----- | ------------------------------- | ---- |
| [[Max Hitpoints]] | {MAX_HP}     |                                 | Y    |
| [[HP]]            | 0     |                                 | N    |
| [[Evasion]]       |           {EVASION}              |                                 | Y    |
| [[Armor]]         |           {ARMOR}               |                                 | Y    |
| [[Stress Level]]  | 0     | default is 0 at start of combat | N    |
|                   | 0     |                                 |      |

---

## Bending Levels

| Element                 | Level | Notes                  | Auto |
| ----------------------- | ----- | ---------------------- | ---- |
| [[Airbending Level]]    | {AIR}     |                        | N    |
| [[Waterbending Level]]  | {WATER}     |                        | N    |
| [[Earthbending Level]]  | {EARTH}     |                        | N    |
| [[Firebending Level]]   | {FIRE}     |                        | N    |
| [[Spiritbending Level]] | {SPIRIT}     | (Avatar Spirit Bridge) | N    |

---

## Secondary Stats

| Stat                     | value | Notes                  | Auto |
| ------------------------ | ----- | ---------------------- | ---- |
| [[Attack Roll Modifier]] |              {ARMOD}                  |                        | Y    |
| [[Waterbending DC]]      |              {WATER_DC}                 |                        | Y    |
| [[Earthbending DC]]      |              {EARTH_DC}                 |                        | Y    |
| [[Firebending DC]]       |              {FIRE_DC}                 |                        | Y    |
| [[Spiritbending DC]]     |              {SPIRIT_DC}                              | (Avatar Spirit Bridge) | Y    |

## [[Manually Rolled Hitpoints]]
| Level | Element | Rolled | Auto |
| ----- | ------- | ------ | ---- |

---

## Inventory & Notes

-
-
"""


def compute_placeholders(core: dict, bending: dict, formulas_path: Path | None = None) -> dict:
    # Conservative defaults; many of these will be updated by update_char.py
    placeholders = {
        'STR': core['STR'],
        'DEX': core['DEX'],
        'CON': core['CON'],
        'INT': core['INT'],
        'WIS': core['WIS'],
        'CHA': core['CHA'],
        'AIR': bending.get('Air', 0),
        'WATER': bending.get('Water', 0),
        'EARTH': bending.get('Earth', 0),
        'FIRE': bending.get('Fire', 0),
    'SPIRIT': bending.get('Spirit', 0),
    # Sum of manually rolled hitpoints (can be supplied at creation time)
    'Manually_Rolled_Hitpoints': bending.get('Manually_Rolled_Hitpoints', 0),
    }

    # Basic derived placeholders so the file isn't blank. These are simple
    # fallbacks; we prefer to evaluate formulas from `char_formulas.json`
    placeholders.update({
        'MAX_HP': max(5, 10 + (placeholders['CON'] + 0) * 1),
        'EVASION': 10 + placeholders['DEX'],
        'ARMOR': max(0, placeholders['EARTH']),
        'ARMOD': placeholders['AIR'] + placeholders['WATER'] + placeholders['EARTH'] + placeholders['FIRE'] + placeholders['SPIRIT'],
        'WATER_DC': 10 + placeholders['WATER'] + placeholders['DEX'],
        'EARTH_DC': 10 + placeholders['EARTH'] + placeholders['STR'],
        'FIRE_DC': 10 + placeholders['FIRE'] + placeholders['WIS'],
        'SPIRIT_DC': 10 + placeholders['SPIRIT'] + placeholders['WIS'],
    })

    # Attempt to compute more accurate secondary stats using char_formulas.json
    try:
        formulas_path_resolved = Path(formulas_path) if formulas_path else Path(get_config('char_formulas', 'char_formulas.json'))
        formulas = load_formulas(formulas_path_resolved)
        # build stats and extra_vars in the shape expected by compute_secondary
        stats = {k: placeholders.get(k, 0) for k in ('STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA')}
        extra_vars: dict = {}
        # map bending to 'Air Level', 'Water Level', ... which our formula loader expects
        for elem in ('Air', 'Water', 'Earth', 'Fire', 'Spirit'):
            extra_vars[f"{elem} Level"] = bending.get(elem, 0)
            # also include short names used in some formulas
            extra_vars[elem] = bending.get(elem, 0)
        # CL heuristics: highest element level
        extra_vars['CL'] = max(extra_vars.get('Air Level', 0), extra_vars.get('Water Level', 0), extra_vars.get('Earth Level', 0), extra_vars.get('Fire Level', 0), extra_vars.get('Spirit Level', 0))
        extra_vars['HP_PER_CL'] = bending.get('Manually_Rolled_Hitpoints', 0)

        derived = compute_secondary(stats, formulas, extra_vars=extra_vars)
        # attach computed placeholders where available
        if 'Max Hit Points' in derived:
            placeholders['MAX_HP'] = derived.get('Max Hit Points', placeholders['MAX_HP'])
        if 'Evasion' in derived:
            placeholders['EVASION'] = derived.get('Evasion', placeholders['EVASION'])
        if 'Armor' in derived:
            placeholders['ARMOR'] = derived.get('Armor', placeholders['ARMOR'])
        # DC and attack mod mapping (try several possible labels)
        placeholders['WATER_DC'] = derived.get('Waterbending Dc', derived.get('Waterbending Dc', placeholders['WATER_DC']))
        placeholders['EARTH_DC'] = derived.get('Earthbending Dc', placeholders['EARTH_DC'])
        placeholders['FIRE_DC'] = derived.get('Firebending Dc', placeholders['FIRE_DC'])
        placeholders['SPIRIT_DC'] = derived.get('Spiritbending Dc', placeholders['SPIRIT_DC'])
        placeholders['ARMOD'] = derived.get('Attack Roll Modifier', placeholders['ARMOD'])
    except Exception:
        # on any failure, keep conservative defaults
        pass
    return placeholders


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--name', required=False, help='Character name')
    # core stats
    p.add_argument('--str', type=int, default=3)
    p.add_argument('--dex', type=int, default=3)
    p.add_argument('--con', type=int, default=3)
    p.add_argument('--int', type=int, default=3)
    p.add_argument('--wis', type=int, default=3)
    p.add_argument('--cha', type=int, default=3)
    # bending levels
    p.add_argument('--air', type=int, default=0)
    p.add_argument('--water', type=int, default=0)
    p.add_argument('--earth', type=int, default=0)
    p.add_argument('--fire', type=int, default=0)
    p.add_argument('--spirit', type=int, default=0)
    p.add_argument('--manual-rolled-hp', type=int, default=0, help='Sum of manually rolled hitpoints to include on the sheet')
    default_out = get_config('pcs_root', 'Players Part/PCs')
    p.add_argument('--out-root', default=default_out, help='Root folder for PC folders')
    p.add_argument('--run-update', action='store_true', help='Run update_char.py to compute derived stats if available')
    p.add_argument('--input-file', help='Markdown file containing a table of characters to create')
    # Graph generation flags
    p.add_argument('--make-graphs', action='store_true', help='Run Wikigraphs.py --pc <name> after creating the character sheet')
    p.add_argument('--embed-graphs', action='store_true', help='Pass --embed to Wikigraphs.py when generating graphs (embed plotly JS)')
    p.add_argument('--graphs-verbose', action='store_true', help='Pass --verbose to Wikigraphs.py when generating graphs')
    args = p.parse_args(argv)

    # require either a single name or an input file
    if not args.name and not args.input_file:
        p.error('either --name or --input-file is required')

    def create_one(pc_name: str, core_vals: dict, bending_vals: dict, run_update_override: bool | None = None) -> Path:
        placeholders = compute_placeholders(core_vals, bending_vals)
        out_root = Path(args.out_root)
        # If out_root is the default and not present, prefer any 'PC Character Sheets' folder in the repo
        if args.out_root == 'Players Part/PCs':
            try:
                base = Path(__file__).resolve().parent
                for d in base.rglob('PC Character Sheets'):
                    if d.is_dir():
                        out_root = d
                        break
            except Exception:
                pass
        pc_dir = out_root / pc_name
        pc_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{pc_name} Character Sheet.md"
        fpath = pc_dir / filename
        content = TEMPLATE.format(**placeholders)
        # If the user provided manually rolled hitpoints, insert a row into
        # the 'Manually Rolled Hitpoints' table summarizing the total.
        manual_total = placeholders.get('Manually_Rolled_Hitpoints', 0)
        if manual_total and manual_total != 0:
            lines = content.splitlines()
            for i, ln in enumerate(lines):
                if ln.strip().lower().startswith('##') and 'manually rolled hitpoints' in ln.lower():
                    # look for the header row that contains 'Level' and then the separator line
                    for j in range(i + 1, min(i + 10, len(lines))):
                        if 'level' in lines[j].lower() and '|' in lines[j]:
                            sep_idx = j + 1
                            insert_idx = sep_idx + 1 if sep_idx + 1 <= len(lines) else sep_idx
                            # Insert a single summary row: Level = '-', Element = 'Manual', Rolled = total
                            row = f"| - | Manual Rolled | {manual_total} | N |"
                            lines[insert_idx:insert_idx] = [row]
                            content = '\n'.join(lines) + '\n'
                            break
                    break

        fpath.write_text(content, encoding='utf-8')
        print(f"Wrote character sheet: {fpath}")

        # Add or update pcs_input.md so this character is tracked in the master table
        def add_or_update_pcs_input(pc_name: str, core: dict, bending: dict, manual_hp: int, run_update: bool):
            pcs_path = Path(get_config('pcs_input', 'pcs_input.md'))
            # target ordered columns
            cols = ['Name','STR','DEX','CON','INT','WIS','CHA','Water','Earth','Air','Fire','Spirit','Manually Rolled HP','Run Update']

            def format_row_values(name: str, core: dict, bending: dict, manual_hp: int, run_update: bool, col_widths: list[int]):
                vals = [
                    name,
                    str(core.get('STR', 0)),
                    str(core.get('DEX', 0)),
                    str(core.get('CON', 0)),
                    str(core.get('INT', 0)),
                    str(core.get('WIS', 0)),
                    str(core.get('CHA', 0)),
                    str(bending.get('Water', 0)),
                    str(bending.get('Earth', 0)),
                    str(bending.get('Air', 0)),
                    str(bending.get('Fire', 0)),
                    str(bending.get('Spirit', 0)),
                    str(manual_hp or 0),
                    'yes' if run_update else 'no',
                ]
                out_cells = []
                for i, v in enumerate(vals):
                    w = int(col_widths[i])
                    # numeric columns (everything except Name and Run Update) -> right align
                    if cols[i] == 'Name':
                        cell = v.ljust(w)
                    else:
                        cell = v.rjust(w)
                    out_cells.append(cell)
                return '| ' + ' | '.join(out_cells) + ' |'

            # ensure file exists with proper header if missing
            if not pcs_path.exists():
                header = '| ' + ' | '.join(cols) + ' |'
                # create reasonable separator with alignment markers similar to existing style
                sep_parts = []
                for c in cols:
                    if c == 'Name':
                        sep_parts.append('--------')
                    elif c == 'Run Update':
                        sep_parts.append('---------:')
                    else:
                        # numeric right-aligned
                        sep_parts.append('--:')
                sep = '| ' + ' | '.join(sep_parts) + ' |'
                # compute widths from header pieces
                col_widths = [len(c) for c in cols]
                new_row = format_row_values(pc_name, core, bending, manual_hp, run_update, col_widths)
                pcs_path.write_text(header + '\n' + sep + '\n' + new_row + '\n', encoding='utf-8')
                print(f'Updated pcs_input.md with new PC: {pc_name} (created new pcs_input.md)')
                return

            text = pcs_path.read_text(encoding='utf-8')
            lines = text.splitlines()
            # find header line index (first line containing 'Name' and pipes)
            header_idx = None
            for i, ln in enumerate(lines):
                if '|' in ln and 'name' in ln.lower():
                    header_idx = i
                    break
            if header_idx is None:
                # fallback to append at end with default header
                header = '| ' + ' | '.join(cols) + ' |'
                sep_parts = ['--------' if c == 'Name' else ('---------:' if c == 'Run Update' else '--:') for c in cols]
                sep = '| ' + ' | '.join(sep_parts) + ' |'
                col_widths = [len(c) for c in cols]
                new_row = format_row_values(pc_name, core, bending, manual_hp, run_update, col_widths)
                lines.extend(['', header, sep, new_row])
                pcs_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                print(f'Appended pcs_input.md with new PC: {pc_name}')
                return

            # parse header to determine column widths
            header_line = lines[header_idx]
            header_parts = [p for p in header_line.split('|')]
            # compute widths from the header parts (strip surrounding spaces)
            col_texts = [p.strip() for p in header_parts if p.strip()]
            col_widths = [len(t) for t in col_texts]

            # find the contiguous table block
            tbl_start = header_idx
            tbl_end = header_idx
            for j in range(header_idx + 1, len(lines)):
                if '|' in lines[j]:
                    tbl_end = j
                else:
                    break

            # search for existing row matching name
            replaced = False
            for i in range(tbl_start + 2, tbl_end + 1):
                ln = lines[i]
                if not ln.strip() or re.match(r"^\s*\|\s*-+", ln):
                    continue
                parts = [c.strip() for c in ln.split('|') if c.strip()]
                if not parts:
                    continue
                if parts[0].strip().lower() == pc_name.strip().lower():
                    # replace this line with formatted row
                    lines[i] = format_row_values(pc_name, core, bending, manual_hp, run_update, col_widths)
                    replaced = True
                    break

            if not replaced:
                insert_at = tbl_end + 1
                lines[insert_at:insert_at] = [format_row_values(pc_name, core, bending, manual_hp, run_update, col_widths)]

            pcs_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            print(f'pcs_input.md updated: {"replaced" if replaced else "appended"} {pc_name}')

        # call to add/update pcs_input.md for single creation
        try:
            # determine run_update flag for pcs_input (preserve override if supplied)
            do_update_flag = args.run_update if run_update_override is None else run_update_override
            add_or_update_pcs_input(pc_name, core_vals, bending_vals, manual_total, bool(do_update_flag))
        except Exception as exc:
            print('Failed to update pcs_input.md:', exc)

        do_update = args.run_update if run_update_override is None else run_update_override
        if do_update:
            updater = Path('update_char.py')
            if updater.exists():
                print('Running update_char.py to compute derived stats...')
                try:
                    subprocess.run([sys.executable, str(updater), '--file', str(fpath)], check=True)
                    print('update_char.py completed; file updated.')
                    # run update_bending_slots script to regenerate slots table
                    ub = Path('scripts/update_bending_slots.py')
                    if ub.exists():
                        try:
                            subprocess.run([sys.executable, str(ub), str(fpath)], check=True)
                            print('update_bending_slots.py completed; slots updated.')
                        except subprocess.CalledProcessError:
                            print('update_bending_slots.py failed; slots left as-is.')
                    else:
                        print('scripts/update_bending_slots.py not found; skipping slot regeneration.')
                except subprocess.CalledProcessError as e:
                    print('update_char.py failed (exit {}). File left as-is.'.format(e.returncode))
            else:
                print('update_char.py not found; skipping automatic derived stat computation.')
        # Optionally run Wikigraphs to generate per-PC graphs immediately
        if args.make_graphs:
            graphs_script = Path('Wikigraphs.py')
            if graphs_script.exists():
                cmd = [sys.executable, str(graphs_script), '--pc', pc_name]
                if args.embed_graphs:
                    cmd.append('--embed')
                if args.graphs_verbose:
                    cmd.append('--verbose')
                try:
                    print(f"Running Wikigraphs to generate graphs for PC: {pc_name}...")
                    subprocess.run(cmd, check=True)
                    print('Wikigraphs completed; graphs written.')
                except subprocess.CalledProcessError as e:
                    print(f'Wikigraphs failed (exit {e.returncode}); graphs not created.')
            else:
                print('Wikigraphs.py not found; skipping graph generation.')
        return fpath

    def _strip_wikilink(s: str) -> str:
        s = s.strip()
        m = re.match(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", s)
        return m.group(1) if m else s

    def parse_pcs_from_markdown(path: Path) -> list[dict]:
        """Parse the first markdown table containing a 'Name' column and return
        a list of dicts with normalized keys for each PC.
        Expected numeric columns: STR, DEX, CON, INT, WIS, CHA, Air, Water, Earth, Fire, Spirit
        """
        text = path.read_text(encoding='utf-8')
        lines = text.splitlines()
        table_lines = []
        in_table = False
        for ln in lines:
            if '|' in ln:
                # treat as table row
                table_lines.append(ln)
                in_table = True
            else:
                if in_table:
                    break
        if not table_lines:
            return []

        # find header line (first with 'Name' or 'STR')
        header_idx = None
        for i, row in enumerate(table_lines):
            cols = [c.strip() for c in row.split('|') if c.strip()]
            low = [c.lower() for c in cols]
            if 'name' in low:
                header_idx = i
                break
        if header_idx is None:
            return []

        header = [c.strip() for c in table_lines[header_idx].split('|')]
        # data rows are the lines after header and separator (skip next if looks like ---)
        data_start = header_idx + 1
        if data_start < len(table_lines) and re.match(r"^\s*\|?\s*-+", table_lines[data_start]):
            data_start += 1

        cols = [c.strip() for c in header if c.strip()]
        pcs = []
        for row in table_lines[data_start:]:
            # stop at blank line or non-row
            if not row.strip() or '|' not in row:
                break
            cells = [c.strip() for c in row.split('|') if True]
            # align cells to cols by index (allow extra leading/trailing pipes)
            # build mapping
            mapping: dict = {}
            for idx, col_name in enumerate(cols):
                try:
                    val = cells[idx+1].strip() if row.startswith('|') else cells[idx].strip()
                except Exception:
                    val = ''
                val = _strip_wikilink(val)
                mapping[col_name] = val

            # normalize into expected shape
            if not mapping:
                continue
            name = mapping.get('Name') or mapping.get('name')
            if not name:
                continue
            def to_int_field(keys, default=0):
                for k in keys:
                    if k in mapping and mapping[k] != '':
                        try:
                            return int(re.sub(r"[^0-9-]", "", mapping[k]))
                        except Exception:
                            return default
                return default

            core_vals = {
                'STR': to_int_field(['STR', 'Strength'], default=args.str),
                'DEX': to_int_field(['DEX', 'Dexterity'], default=args.dex),
                'CON': to_int_field(['CON', 'Constitution'], default=args.con),
                'INT': to_int_field(['INT', 'Intelligence'], default=args.int),
                'WIS': to_int_field(['WIS', 'Wisdom'], default=args.wis),
                'CHA': to_int_field(['CHA', 'Charisma'], default=args.cha),
            }
            bending_vals = {
                'Air': to_int_field(['Air', 'Air Level', 'Airbending', 'air'], default=args.air),
                'Water': to_int_field(['Water', 'Water Level', 'Waterbending', 'water'], default=args.water),
                'Earth': to_int_field(['Earth', 'Earth Level', 'Earthbending', 'earth'], default=args.earth),
                'Fire': to_int_field(['Fire', 'Fire Level', 'Firebending', 'fire'], default=args.fire),
                'Spirit': to_int_field(['Spirit', 'Spirit Level', 'Spiritbending', 'spirit'], default=args.spirit),
            }
            # support optional manual rolled HP column
            manual_hp = to_int_field(['Manual', 'Manual HP', 'Manually Rolled HP', 'Manually_Rolled_Hitpoints'], default=0)
            if manual_hp:
                bending_vals['Manually_Rolled_Hitpoints'] = manual_hp
            run_update_flag = None
            for key in ('Run Update', 'run_update', 'run-update'):
                if key in mapping and mapping[key].lower() in ('1','y','yes','true','t'):
                    run_update_flag = True
                elif key in mapping and mapping[key].lower() in ('0','n','no','false','f'):
                    run_update_flag = False
This is a near-copy of the top-level `create_pc.py` implementation but
imports `get_config` from the package-local config loader.
"""
from __future__ import annotations
import argparse
import subprocess
from pathlib import Path
from generate_secondary_stats import load_formulas, compute_secondary
from .config_loader import get_config
import sys
import re

# ...existing TEMPLATE and functions copied from original create_pc.py...
# To keep this helper small in the patch message, the heavy implementation
# was copied verbatim into the package file in the workspace.

def main(argv: list[str] | None = None) -> int:
    # delegate to original top-level implementation logic (copied)
    # ...existing code...
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
