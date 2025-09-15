import re
from pathlib import Path

# Configure PC name and sheet path
pc_name = 'Anju'
vault_root = Path('.').resolve()
pcs_root = vault_root.joinpath('Players Part', 'PCs')
pc_folder = pcs_root.joinpath(pc_name)
char_sheet = pc_folder.joinpath(f"{pc_name} Character Sheet.md")

# Fallback element levels if parsing fails
def parse_bending_levels_from_sheet(path: Path) -> dict:
    try:
        txt = path.read_text(encoding='utf-8')
    except Exception:
        return {}
    lines = txt.splitlines()
    patterns = [
        re.compile(r"\|\s*\[?\[?\s*(Airbending Level|Waterbending Level|Earthbending Level|Firebending Level|Spiritbending Level)\s*\]?\]?\s*\|\s*(\d+)", re.IGNORECASE),
        re.compile(r"(Airbending Level|Waterbending Level|Earthbending Level|Firebending Level|Spiritbending Level)\s*\|\s*(\d+)", re.IGNORECASE),
        re.compile(r"(Air Level|Water Level|Earth Level|Fire Level|Spirit Level)\s*\|\s*(\d+)", re.IGNORECASE),
    ]
    found = {}
    for ln in lines:
        for pat in patterns:
            m = pat.search(ln)
            if m:
                key = m.group(1).strip()
                val = int(m.group(2))
                kln = key.lower()
                if 'air' in kln:
                    found['Air'] = val
                elif 'water' in kln:
                    found['Water'] = val
                elif 'earth' in kln:
                    found['Earth'] = val
                elif 'fire' in kln:
                    found['Fire'] = val
                elif 'spirit' in kln:
                    found['Spirit'] = val
    return found

allowed = parse_bending_levels_from_sheet(char_sheet) if char_sheet.exists() else {}
print(f"Parsed bending levels for {pc_name}: {allowed}")

# Build elem_map lowercase
elem_map = {k.lower(): v for k,v in allowed.items()} if allowed else {}
# If empty, set reasonable defaults (so diagnostic still runs)
if not elem_map:
    elem_map = {'water':3, 'earth':1, 'air':0, 'fire':0, 'spirit':1}

base = vault_root.joinpath('Players Part', 'Rules', 'Bending Rules')
files = sorted([p for p in base.rglob('*') if p.is_file()])

print(f"Found {len(files)} candidate files under {base}\n")

for f in files:
    rel = f.relative_to(vault_root)
    file_key = str(rel).replace('\\', '/')
    lower_key = file_key.lower()
    try:
        txt = f.read_text(encoding='utf-8', errors='replace')
    except Exception:
        txt = ''
    text_lower = txt.lower()
    inner_links = [m.group(1).lower() for m in re.finditer(r"\[\[([^\]]+)\]\]", txt)]
    text_levels = set()
    for m in re.finditer(r'level\s*[:_\- ]*\(?([0-9]+)\)?', text_lower, flags=re.I):
        try:
            text_levels.add(int(m.group(1)))
        except Exception:
            pass
    path_levels = set()
    for part in lower_key.split('/'):
        m = re.search(r'level\s*[-_ ]*(\d+)', part)
        if m:
            try:
                path_levels.add(int(m.group(1)))
            except Exception:
                pass

    reasons = []
    included = False
    for elem, lvl in elem_map.items():
        elem_kw = elem
        in_path = elem_kw in lower_key
        in_text_link = any(elem_kw in s for s in inner_links)
        in_text_any = elem_kw in text_lower
        if 'mechanic' in lower_key:
            if in_path or in_text_link or in_text_any or lvl >= 0:
                reasons.append(f"mechanics-match({elem})")
                included = True
                break
        if in_path and path_levels:
            for pl in path_levels:
                allowed_level_for_compare = lvl if lvl > 0 else 1
                if pl <= allowed_level_for_compare and pl > 0:
                    reasons.append(f"path-level-{pl}<={allowed_level_for_compare}({elem})")
                    included = True
                    break
            if included:
                break
        if (in_text_link or in_text_any or in_path) and text_levels:
            for tl in text_levels:
                allowed_level_for_compare = lvl if lvl > 0 else 1
                if tl <= allowed_level_for_compare and tl > 0:
                    reasons.append(f"text-level-{tl}<={allowed_level_for_compare}({elem})")
                    included = True
                    break
            if included:
                break
        if in_path and lvl <= 0:
            reasons.append(f"in_path_level0({elem})")
            included = True
            break
        if in_text_any and lvl >= 0:
            reasons.append(f"in_text_any({elem})")
            included = True
            break
    # print detailed line
    print(f"{file_key}")
    print(f"  in_path: {any(e in lower_key for e in elem_map.keys())}")
    print(f"  in_text_link: {any(any(e in s for s in inner_links) for e in elem_map.keys())}")
    print(f"  in_text_any: {any(e in text_lower for e in elem_map.keys())}")
    print(f"  path_levels: {sorted(path_levels)}")
    print(f"  text_levels: {sorted(text_levels)}")
    print(f"  reasons: {reasons}")
    print(f"  INCLUDED: {included}\n")
