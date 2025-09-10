#!/usr/bin/env python3
"""Update the Bending Slots table in a character markdown from the Bending Levels table.

Usage: python3 scripts/update_bending_slots.py "/path/to/Character Sheet.md"

Behavior:
- Parse the '## Bending Levels' table to find elements and their integer levels.
- Compute slots: for level N, produce 1 slot at level N, 2 at N-1, ... until level 1.
- Special rule for Waterbending: multiply the computed slot counts by
    (1 + floor(WaterLevel / 4)). This scales water slots at levels 4,8,12,...
- Replace the existing '## [[Bending Slots]]' table with a generated table that
    only includes elements with at least one slot. If a 'water charges' row exists
    it will be preserved near the top of the table.

This is intentionally small and dependency-free.
"""
import sys
import re
from pathlib import Path

HEADER = "## [[Bending Slots]]"

ELEMENT_DISPLAY = {
    'Waterbending': 'Waterbending',
    'Earthbending': 'Earthbending',
    'Airbending': 'Airbending',
    'Firebending': 'Firebending',
    'Spiritbending': 'Spiritbending',
}

# Mapping from the "Bending Levels" table name to the slot row element name
LEVEL_TO_SLOT_NAME = {
    'Waterbending Level': 'Waterbending Slot',
    'Earthbending Level': 'Earthbending Slot',
    'Airbending Level': 'Airbending Slot',
    'Firebending Level': 'Firebending Slot',
    'Spiritbending Level': 'Spiritbending Slot',
}


def parse_markdown_table(lines, start_index):
    """Parse a markdown table starting at start_index and return (end_index, rows)

    rows is a list of lists (cells stripped). Assumes simple pipe tables.
    """
    rows = []
    i = start_index
    while i < len(lines):
        line = lines[i].strip('\n')
        if not line.startswith('|'):
            break
        # split pipes but ignore leading/trailing pipe
        cols = [c.strip() for c in line.strip().strip('|').split('|')]
        rows.append(cols)
        i += 1
    return i, rows


def find_section(lines, header):
    for idx, line in enumerate(lines):
        if line.strip() == header:
            return idx
    return -1


def compute_slots_for_level(n):
    """Return list of (slot_level, count) for level n, descending slot_level."""
    if n <= 0:
        return []
    out = []
    for k in range(1, n+1):
        slot_level = n + 1 - k
        count = k
        out.append((slot_level, count))
    return out


def compute_spirit_slots_for_level(n):
    """Spiritbending slot progression.

    Based on the provided Spiritbending Slot table, the per-slot counts
    follow the pattern: count(slot_level k) = max(0, n - 2*(k-1)).
    Accessible slot levels are those with a positive count. Return pairs
    in descending slot_level order (so highest slot level first), same
    shape as compute_slots_for_level.
    """
    if n <= 0:
        return []
    pairs = []
    # number of possible slot levels = ceil((n)/2) -> (n+1)//2
    max_level = (n + 1) // 2
    for k in range(max_level, 0, -1):
        count = n - 2 * (k - 1)
        if count > 0:
            pairs.append((k, count))
    return pairs


def element_name_from_level_header(header):
    # try to match e.g. '[[Waterbending Level]]' or 'Waterbending Level'
    h = re.sub(r'\[|\]', '', header).strip()
    return h


def generate_slots_table(slots_map, keep_water_charges=False, existing_water_charges_row=None):
    lines = []
    lines.append('| Element               | Slot level | [[Max Slots]] | current | note | Auto |')
    lines.append('| --------------------- | ---------- | ------------- | ------- | ---- | ---- |')
    if keep_water_charges and existing_water_charges_row:
        lines.append(existing_water_charges_row)
    # slots_map: element -> list of (slot_level, count)
    for element, pairs in slots_map.items():
        # element will be like 'Waterbending Slot' or 'Earthbending Slot'
        for slot_level, count in pairs:
            # Expand into a single row representing that slot-level and max slots = count
            # We'll keep current equal to count for convenience (may be overridden later)
            lines.append(f'| [[{element}]] | {slot_level} | {count} | {count} |      | Y    |')
    return ['' + l for l in lines]


def main():
    if len(sys.argv) < 2:
        print('Usage: update_bending_slots.py /path/to/Character Sheet.md')
        sys.exit(1)
    p = Path(sys.argv[1])
    if not p.exists():
        print('File not found:', p)
        sys.exit(1)
    text = p.read_text(encoding='utf-8')
    lines = text.splitlines()

    # find Bending Levels section
    bl_idx = find_section(lines, '## Bending Levels')
    if bl_idx == -1:
        print('Could not find "## Bending Levels" section in', p)
        sys.exit(1)
    # parse table immediately after header
    table_start = bl_idx + 1
    # skip possible blank lines
    while table_start < len(lines) and not lines[table_start].strip().startswith('|'):
        table_start += 1
    end_idx, rows = parse_markdown_table(lines, table_start)
    # rows: header, separator, then data rows
    levels = {}
    for r in rows[2:]:
        if len(r) >= 2:
            element_header = r[0]
            level_cell = r[1]
            name = element_name_from_level_header(element_header)
            try:
                lvl = int(level_cell)
            except ValueError:
                # try to parse numbers inside
                m = re.search(r"(\d+)", level_cell)
                lvl = int(m.group(1)) if m else 0
            levels[name] = lvl

    # compute slots map
    slots_map = {}
    # Note: Waterbending does not use per-level slot rows. Instead there is a
    # single 'water charges' row. We therefore skip generating 'Waterbending Slot'
    # entries here and compute a water_charges value separately.
    computed_water_charges = None
    for level_header, slot_name in LEVEL_TO_SLOT_NAME.items():
        if level_header not in levels:
            continue
        n = levels[level_header]
        if 'Waterbending' in level_header:
            # compute a default water charges value if needed. Rule chosen:
            # charges = WaterLevel * (1 + floor(WaterLevel / 4)).
            # If WaterLevel == 0, computed_water_charges remains None.
            if n > 0:
                computed_water_charges = n * (1 + (n // 4))
            continue
        # non-water elements keep the per-level slot rows
        pairs = compute_slots_for_level(n)
        if pairs:
            slots_map[slot_name] = pairs

    # find Bending Slots section to replace the whole section (up to next '---')
    bs_idx = find_section(lines, HEADER)
    header_present = True
    if bs_idx == -1:
        # Header missing: we'll insert the generated table after the Bending Levels table
        # end_idx is the line after the parsed Bending Levels table (defined earlier)
        bs_idx = end_idx
        header_present = False

    # find the marker that ends this section (a line with just '---')
    section_end = None
    for i in range(bs_idx + 1, len(lines)):
        if lines[i].strip() == '---':
            section_end = i
            break
    if section_end is None:
        # fallback: use the end of file
        section_end = len(lines)

    # parse the old table rows between the first '|' after the header and section_end
    tstart = bs_idx + 1
    while tstart < section_end and not lines[tstart].strip().startswith('|'):
        tstart += 1
    tend, old_table_rows = parse_markdown_table(lines, tstart)

    # detect existing water charges row if present, and extract existing 'current' values
    water_row = None
    danger_row = None
    danger_existing = None  # tuple(max, current, slot_level_display)
    existing_current = {}  # key: (element_name, slot_level) -> current int
    for r in old_table_rows:
        if len(r) >= 1 and 'water charges' in r[0].lower():
            # try to parse existing water charges row to preserve values
            # expected form: | [[water charges]] | [[Waterbottle Charges]] | <max> | <current> | ... |
            water_row = r
            continue
        # try to parse regular rows: Element | Slot level | Max | current | ...
        if len(r) >= 4:
            elem_raw = r[0]
            slot_level_raw = r[1]
            current_raw = r[3]
            # normalize element name by stripping [[ ]]
            elem = re.sub(r'\[|\]', '', elem_raw).strip()
            m1 = re.search(r"(\d+)", slot_level_raw)
            slot_level = int(m1.group(1)) if m1 else None
            m2 = re.search(r"(\d+)", current_raw)
            current_val = int(m2.group(1)) if m2 else None
            if slot_level is not None and current_val is not None:
                existing_current[(elem, slot_level)] = current_val
        # detect danger sense reaction row
        if len(r) >= 1 and 'danger' in r[0].lower():
            danger_row = r
            # try to extract numeric fields if present
            try:
                # expected forms: Element | Slot level | Max | current | note
                if len(r) >= 4:
                    slot_level_raw = r[1]
                    max_raw = r[2]
                    cur_raw = r[3]
                    msl = re.search(r"(\d+)", slot_level_raw)
                    mmax = re.search(r"(\d+)", max_raw)
                    mcur = re.search(r"(\d+)", cur_raw)
                    slot_lv = int(msl.group(1)) if msl else None
                    mmaxv = int(mmax.group(1)) if mmax else None
                    mcurv = int(mcur.group(1)) if mcur else None
                    danger_existing = (mmaxv, mcurv, slot_lv)
            except Exception:
                danger_existing = None

    # generate new table lines but preserve current values when available
    new_table_lines = []
    new_table_lines.append('| Element               | Slot level | [[Max Slots]] | current | note | Auto |')
    new_table_lines.append('| --------------------- | ---------- | ------------- | ------- | ---- | ---- |')
    # Build water charges row first: preserve existing if present, otherwise use computed
    if water_row:
        # reconstruct raw row string
        new_table_lines.append('| ' + ' | '.join(water_row) + ' |')
    elif computed_water_charges is not None:
        # create a default water charges row with max=current=computed value
        new_table_lines.append(f'| [[water charges]] | [[Waterbottle Charges]] | {computed_water_charges} | {computed_water_charges} |      | Y    |')
    # Build Danger Sense Reaction row for Airbenders: regenerate numerically when Air level >0
    air_lvl = levels.get('Airbending Level', 0)
    try:
        air_lvl_int = int(air_lvl)
    except Exception:
        air_lvl_int = 0
    if air_lvl_int > 0:
        # compute danger slot count (same mapping as update_char.py)
        if air_lvl_int <= 0:
            danger_count = 0
        else:
            danger_count = min(5, ((max(0, air_lvl_int - 1)) // 4) + 1)
        # slot level display: air level * 2 (keeps consistency with current templates)
        slot_level_display = air_lvl_int * 2
        # preserve existing current/max if available
        if danger_existing and danger_existing[1] is not None:
            cur_val = danger_existing[1]
        else:
            cur_val = danger_count
        if danger_existing and danger_existing[0] is not None:
            max_val = danger_existing[0]
        else:
            max_val = danger_count
        new_table_lines.append(f'| [[Danger Sense Reaction]] | {slot_level_display} | {max_val} | {cur_val} | {slot_level_display} | Y    |')
    else:
        # air level 0: do not include Danger Sense Reaction row (drop existing)
        pass
    for element, pairs in slots_map.items():
        for slot_level, count in pairs:
            elem_key = (element, slot_level)
            # existing_current keys are like ('Earthbending Slot', 1)
            current_val = existing_current.get(elem_key, count)
            new_table_lines.append(f'| [[{element}]] | {slot_level} | {count} | {current_val} |      | Y    |')

    # assemble new document: replace everything between the header and section_end
    # with the regenerated table. If the header was missing, insert the header and
    # a section divider '---'.
    if header_present:
        new_lines = lines[:tstart] + new_table_lines + lines[section_end:]
    else:
        # insert header, table, and section divider at tstart
        new_lines = lines[:tstart] + [HEADER] + new_table_lines + ['---'] + lines[section_end:]
    new_text = '\n'.join(new_lines) + '\n'
    p.write_text(new_text, encoding='utf-8')
    print('Updated bending slots in', p)

if __name__ == '__main__':
    main()
