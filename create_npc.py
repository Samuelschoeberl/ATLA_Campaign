#!/usr/bin/env python3
"""create_npc.py

Generate a complete NPC Sheet markdown file from minimal inputs
(name, core primary stats, bending levels). Mirrors create_pc.py but
operates on an NPCs folder and uses --npc flags.

Usage:
  python3 create_npc.py --npc "Chief Anu" --str 3 --dex 2 --con 4 --water 2 --earth 1
"""
from __future__ import annotations
import argparse
import subprocess
from pathlib import Path
import sys
import re


TEMPLATE = """## Core Stats

| Stat             | Value | Auto |
| ---------------- | ----- | ---- |
| [[Strength]]     | {STR}     | N    |
| [[Dexterity]]    | {DEX}     | N    |
| [[Constitution]] | {CON}     | N    |
| [[Intelligence]] | {INT}     | N    |
| [[Wisdom]]       | {WIS}     | N    |
| [[Charisma]]     | {CHA}     | N    |

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
    # fallbacks; `update_char.py` should compute the real values if available.
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
    return placeholders


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--npc', required=False, help='NPC name')
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
    p.add_argument('--out-root', default='DMs Part', help='Root folder for NPC files (top-level DMs Part)')
    p.add_argument('--run-update', action='store_true', help='Run update_char.py to compute derived stats if available')
    p.add_argument('--input-file', help='Markdown file containing a table of NPCs to create')
    # Graph generation flags (kept for parity though NPC graphs are optional)
    p.add_argument('--make-graphs', action='store_true', help='Run Wikigraphs.py --pc <name> after creating the NPC sheet')
    p.add_argument('--embed-graphs', action='store_true', help='Pass --embed to Wikigraphs.py when generating graphs (embed plotly JS)')
    p.add_argument('--graphs-verbose', action='store_true', help='Pass --verbose to Wikigraphs.py when generating graphs')
    args = p.parse_args(argv)

    # require either a single name or an input file
    if not args.npc and not args.input_file:
        p.error('either --npc or --input-file is required')

    def create_one(npc_name: str, core_vals: dict, bending_vals: dict, run_update_override: bool | None = None) -> Path:
        placeholders = compute_placeholders(core_vals, bending_vals)
        out_root = Path(args.out_root)
        out_root.mkdir(parents=True, exist_ok=True)
        filename = f"{npc_name} NPC Sheet.md"
        # place NPC sheet directly in the DMs Part top-level folder by default
        fpath = out_root / filename
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
        print(f"Wrote NPC sheet: {fpath}")

        # Add or update npcs_input.md so this NPC is tracked in the master table
        def add_or_update_npcs_input(npc_name: str, core: dict, bending: dict, manual_hp: int, run_update: bool):
            pcs_path = Path(args.out_root) / 'npcs_input.md'
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
                pcs_path.parent.mkdir(parents=True, exist_ok=True)
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
                new_row = format_row_values(npc_name, core, bending, manual_hp, run_update, col_widths)
                pcs_path.write_text(header + '\n' + sep + '\n' + new_row + '\n', encoding='utf-8')
                print(f'Updated npcs_input.md with new NPC: {npc_name} (created new npcs_input.md)')
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
                new_row = format_row_values(npc_name, core, bending, manual_hp, run_update, col_widths)
                lines.extend(['', header, sep, new_row])
                pcs_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                print(f'Appended npcs_input.md with new NPC: {npc_name}')
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
                if parts[0].strip().lower() == npc_name.strip().lower():
                    # replace this line with formatted row
                    lines[i] = format_row_values(npc_name, core, bending, manual_hp, run_update, col_widths)
                    replaced = True
                    break

            if not replaced:
                insert_at = tbl_end + 1
                lines[insert_at:insert_at] = [format_row_values(npc_name, core, bending, manual_hp, run_update, col_widths)]

            pcs_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            print(f'npcs_input.md updated: {"replaced" if replaced else "appended"} {npc_name}')

        # call to add/update npcs_input.md for single creation
        try:
            # determine run_update flag for npcs_input (preserve override if supplied)
            do_update_flag = args.run_update if run_update_override is None else run_update_override
            add_or_update_npcs_input(npc_name, core_vals, bending_vals, manual_total, bool(do_update_flag))
        except Exception as exc:
            print('Failed to update npcs_input.md:', exc)

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
        # Optionally run Wikigraphs to generate per-NPC graphs immediately
        if args.make_graphs:
            graphs_script = Path('Wikigraphs.py')
            if graphs_script.exists():
                cmd = [sys.executable, str(graphs_script), '--pc', npc_name]
                if args.embed_graphs:
                    cmd.append('--embed')
                if args.graphs_verbose:
                    cmd.append('--verbose')
                try:
                    print(f"Running Wikigraphs to generate graphs for NPC: {npc_name}...")
                    try:
                        import Wikigraphs as WG
                        script_dir = Path(__file__).resolve().parent
                        outdir = script_dir.joinpath('graphs')
                        char_sheet = Path('DMs Part') / f"{npc_name} NPC Sheet.md"
                        allowed = None
                        if char_sheet.exists():
                            try:
                                allowed = WG.parse_bending_levels_from_sheet(char_sheet)
                            except Exception:
                                allowed = None
                        WG.make_graphs(Path.cwd(), outdir, allowed_elements_levels=allowed, pc_subtree=Path('DMs Part'), pc_name=npc_name)
                    except Exception:
                        subprocess.run(cmd, check=True)
                    # rename graphs to end with '_npc.html'
                    try:
                        graphs_dir = Path('graphs')
                        sun = graphs_dir / f"{npc_name}_wikigraph_sunburst.html"
                        tre = graphs_dir / f"{npc_name}_wikigraph_treemap.html"
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

    def parse_npcs_from_markdown(path: Path) -> list[dict]:
        """Parse the first markdown table containing a 'Name' column and return
        a list of dicts with normalized keys for each NPC.
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

            pcs.append({'name': name, 'core': core_vals, 'bending': bending_vals, 'run_update': run_update_flag})

        return pcs

    # If an input file provided, create many NPCs
    if args.input_file:
        mdpath = Path(args.input_file)
        if not mdpath.exists():
            print(f"Input file not found: {mdpath}")
            return 1
        parsed = parse_npcs_from_markdown(mdpath)
        if not parsed:
            print('No NPC table found in input file or failed to parse.')
            return 1
        for pc in parsed:
            create_one(pc['name'], pc['core'], pc['bending'], run_update_override=pc.get('run_update'))
        return 0

    # Single NPC (existing behavior)
    core = {
        'STR': args.str,
        'DEX': args.dex,
        'CON': args.con,
        'INT': args.int,
        'WIS': args.wis,
        'CHA': args.cha,
    }
    bending = {'Air': args.air, 'Water': args.water, 'Earth': args.earth, 'Fire': args.fire, 'Spirit': args.spirit}
    # include manual rolled HP into bending dict so compute_placeholders can use it
    bending['Manually_Rolled_Hitpoints'] = args.manual_rolled_hp

    create_one(args.npc, core, bending)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
