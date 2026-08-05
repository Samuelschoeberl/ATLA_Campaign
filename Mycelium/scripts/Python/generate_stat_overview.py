#!/usr/bin/env python3
"""
Generate a stat overview for PCs and environmental variables.

Scans:
- Player Root/variable/environmental/*.md for global environmental variables
- Player Root/PCs/* for per-PC markdown files and extracts common stats like
  max_hp, current hp, evasion, water charge and any lines in tables that
  include those keys.

Writes: Player Root/PCs/stat_overview.md

This is intentionally forgiving: it matches case-insensitively and looks for
simple table rows or key/value lines.
"""
from pathlib import Path
import re
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
PLAYER_ROOT = REPO_ROOT / "Player Root"
ENV_DIR = PLAYER_ROOT / "variable" / "environmental"
PC_DIR = PLAYER_ROOT / "PCs"
PC_VARS_DIR = PLAYER_ROOT / "variable" / "PC_variables"
OUT_FILE = PC_DIR / "stat_overview.md"


def read_text(p: Path):
    """Read text from a path, returning an empty string on failure."""
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def extract_first_value_and_tags_from_env(text: str):
    """Extract the first non-empty value and all tags from a variable file."""
    # Handle markdown code blocks
    in_code_block = False
    value = ""
    tags = []
    
    for line in text.splitlines():
        stripped = line.strip()
        
        # Handle markdown code blocks
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            continue
        
        # Extract value (first non-empty, non-tag line - inside or outside code block)
        if not value and stripped and not stripped.startswith("#"):
            value = stripped
        
        # Extract tags - they may be space-separated on one line
        if stripped.startswith("#"):
            # Split by space to handle multiple tags on one line
            line_tags = [t for t in stripped.split() if t.startswith("#")]
            tags.extend(line_tags)
    
    return value, tags


def extract_first_value_from_env(text: str):
    """Return the first non-tag, non-empty line from an environmental file."""
    # prefer the first non-empty, non-comment line that looks like a value
    # handle both plain text and markdown code blocks
    in_code_block = False
    for line in text.splitlines():
        stripped = line.strip()
        
        # Handle markdown code blocks
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            continue
            
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        # return raw line (e.g. '10' or '32')
        return stripped
    return ""


# Only extract these canonical stats per-PC (user-requested)
CANONICAL_KEYS = [
    (re.compile(r"max[_ ]?hp", re.I), "max_hp"),
    (re.compile(r"current[_ ]?hp|current\s+hp", re.I), "current_hp"),
    (re.compile(r"evasion", re.I), "evasion"),
    (re.compile(r"general\s*armor", re.I), "general armor"),
    (re.compile(r"ready", re.I), "ready"),
]

ENV_HINT = re.compile(r"environmental[_\.\s]?water[_\.\s]?charge", re.I)


def row_to_kv(line: str):
    """Parse a table row or key:value line into a (key, value) pair."""
    # Try to parse a markdown table row like: | key | value |
    parts = [p.strip() for p in line.split("|") if p.strip()]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    # fallback: look for 'key: value'
    m = re.match(r"^\s*([^:]+):\s*(.+)$", line)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None


def normalize_key(line: str):
    """Return (canonical_key, raw_value) or (None, None) if not matched."""
    for pat, canonical in CANONICAL_KEYS:
        if pat.search(line):
            # try to extract a value
            kv = row_to_kv(line)
            if kv:
                return canonical, kv[1]
            # fallback: find first number-like token
            m = re.search(r"(-?\d+\b)", line)
            if m:
                return canonical, m.group(1)
            # no numeric value but key present
            return canonical, ""
    return None, None


def find_matching_lines(text: str):
    """Collect lines that include canonical stat keys or environmental hints."""
    found = []
    for line in text.splitlines():
        # check canonical keys
        for pat, _ in CANONICAL_KEYS:
            if pat.search(line):
                found.append(line.strip())
                break
        else:
            # check environmental hint
            if ENV_HINT.search(line):
                found.append(line.strip())
    return found


def gather_environmentals():
    """Gather environmental variable values and tags for inclusion in the table."""
    out = []
    if not ENV_DIR.exists():
        return out
    seen = set()
    for p in sorted(ENV_DIR.glob("*.md")):
        t = read_text(p)
        # prefer files that match the water charge hint; still include others
        if not ENV_HINT.search(p.name) and not ENV_HINT.search(t):
            # skip unrelated environmental files for clarity
            continue
        val = extract_first_value_from_env(t)
        tags = ", ".join([ln.strip() for ln in t.splitlines() if ln.strip().startswith("#")])
        name = p.stem
        if name in seen:
            continue
        seen.add(name)
        out.append((name, val, tags, p))
    return out


def parse_vitals_from_character_sheet(text: str):
    """Parse vitals from a character sheet markdown Vitals section.
    
    Looks for the "## Vitals" section and extracts key-value pairs from the table.
    Returns list of (key, value) tuples.
    Only extracts fields that match CANONICAL_KEYS patterns.
    """
    vitals = []
    
    # Parse Vitals section
    in_vitals_section = False
    for line in text.splitlines():
        stripped = line.strip()
        
        # Stop parsing if we hit another section
        if stripped.startswith('##'):
            if 'Vitals' in stripped:
                in_vitals_section = True
                continue
            elif in_vitals_section:
                # We've moved past vitals
                break
        
        if in_vitals_section and '|' in line and not line.startswith('|---'):
            parts = [p.strip() for p in line.split('|') if p.strip()]
            
            # Skip header row and rows with only dashes
            if len(parts) >= 2:
                # Skip rows that are clearly headers or separators
                if parts[0].lower() in ['key', 'stat', 'name'] or '---' in parts[0] or parts[0].replace('-', '').strip() == '':
                    continue
                
                key = parts[0]
                value = parts[1] if len(parts) > 1 else ''
                
                # Check if this key matches any CANONICAL_KEYS pattern
                for pat, canonical in CANONICAL_KEYS:
                    if pat.search(key):
                        vitals.append((canonical, value))
                        break
    
    return vitals


def parse_bending_slots_from_character_sheet(text: str):
    """Parse bending slots and water charges from a character sheet markdown.
    
    Looks for the "## Bending Slots" and "## Water charges" sections and extracts values.
    Returns list of (slot_name, value) tuples.
    Excludes environmental water charge (handled as global variable).
    
    This matches the logic in CharacterSheet.jsx's parseCharacterSheet function.
    """
    slots = []
    
    # Parse Bending Slots section
    in_bending_section = False
    for line in text.splitlines():
        stripped = line.strip()
        
        # Stop parsing if we hit the tags line or WARNING section
        if stripped.startswith('#') and not stripped.startswith('##'):
            break
        if 'WARNING' in stripped and stripped.startswith('>'):
            break
        
        if stripped.startswith('## Bending Slots'):
            in_bending_section = True
            continue
        
        if in_bending_section and stripped.startswith('##') and 'Bending Slots' not in stripped:
            in_bending_section = False
        
        if in_bending_section and '|' in line and not line.startswith('|---'):
            parts = [p.strip() for p in line.split('|') if p.strip()]
            
            # Skip header row and rows with only dashes
            if len(parts) >= 2:
                # Skip rows that are clearly headers or separators
                if parts[0].lower() in ['slot', 'slot type', 'bending slot'] or '---' in parts[0] or parts[0].replace('-', '').strip() == '':
                    continue
                
                slot_name = parts[0]
                slot_value = parts[1] if len(parts) > 1 else ''
                
                # Skip environmental water charge (it's a global variable)
                if 'environmental' in slot_name.lower():
                    continue
                
                slots.append((slot_name, slot_value))
    
    # Parse Water charges section
    in_water_section = False
    for line in text.splitlines():
        stripped = line.strip()
        
        # Stop parsing if we hit the tags line or WARNING section
        if stripped.startswith('#') and not stripped.startswith('##'):
            break
        if 'WARNING' in stripped and stripped.startswith('>'):
            break
        
        if stripped.startswith('## Water charges'):
            in_water_section = True
            continue
        
        if in_water_section and stripped.startswith('##') and 'Water charges' not in stripped:
            in_water_section = False
        
        if in_water_section and '|' in line and not line.startswith('|---'):
            parts = [p.strip() for p in line.split('|') if p.strip()]
            
            # Skip header row and rows with only dashes
            if len(parts) >= 2:
                # Skip rows that are clearly headers or separators
                if parts[0].lower() in ['water charge type', 'water charge'] or '---' in parts[0] or parts[0].replace('-', '').strip() == '':
                    continue
                
                charge_name = parts[0]
                charge_value = parts[1] if len(parts) > 1 else ''
                
                # Skip environmental water charge (it's a global variable)
                if 'environmental' in charge_name.lower():
                    continue
                
                slots.append((charge_name, charge_value))
    
    return slots


def get_active_pcs():
    """Read pc_primary_stats.md and return set of PC names with 'yes' in Run Update column."""
    active_pcs = set()
    primary_stats_file = PLAYER_ROOT / "pc_primary_stats.md"
    
    if not primary_stats_file.exists():
        # If the file doesn't exist, include all PCs
        return None
    
    try:
        text = read_text(primary_stats_file)
        for line in text.splitlines():
            # Skip header and separator lines
            if not line.strip() or line.startswith('|---') or 'Name' in line and 'STR' in line:
                continue
            
            # Parse table row
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 14:  # Ensure we have enough columns
                    # Extract PC name (remove [[ ]] if present)
                    pc_name = parts[1].replace('[[', '').replace(']]', '').strip()
                    # Check Run Update column (last column)
                    run_update = parts[-2].strip().lower()  # -2 because split creates empty at end
                    
                    if run_update == 'yes':
                        active_pcs.add(pc_name)
    except Exception as e:
        print(f"Warning: Failed to parse pc_primary_stats.md: {e}", file=sys.stderr)
        return None
    
    return active_pcs


def gather_pc_stats():
    """Gather PC stats from Player Root/variable/PC_variables/<Name>/ directories.
    
    Includes stats tagged with #vitality or #defensive, OR stats that match
    vitality/defensive patterns by filename.
    Bending slots are parsed directly from character sheets.
    Only includes PCs with 'yes' in the Run Update column of pc_primary_stats.md.
    """
    pcs = {}
    
    if not PC_VARS_DIR.exists():
        return pcs
    
    # Get list of active PCs (those with "yes" in Run Update)
    active_pcs = get_active_pcs()
    
    # Define vitality and defensive stat patterns
    vitality_patterns = ['hp', 'health']
    defensive_patterns = ['armor', 'barrier', 'evasion', 'defense', 'defence']
    
    # Scan each PC's variable directory
    for pc_dir in sorted(PC_VARS_DIR.iterdir()):
        if not pc_dir.is_dir():
            continue
        
        pcname = pc_dir.name
        
        # Skip PCs that don't have "yes" in Run Update column
        if active_pcs is not None and pcname not in active_pcs:
            continue
        
        pcs[pcname] = {'vitality': [], 'defensive': [], 'bending_slots': []}
        
        # Scan all variable files for this PC for vitality and defensive stats
        for var_file in sorted(pc_dir.glob("*.md")):
            text = read_text(var_file)
            value, tags = extract_first_value_and_tags_from_env(text)
            
            # Check if tagged with #vitality or #defensive
            has_vitality = any(t.lower() == '#vitality' for t in tags)
            has_defensive = any(t.lower() == '#defensive' for t in tags)
            
            # If not tagged, use filename heuristics
            if not has_vitality and not has_defensive:
                filename_lower = var_file.stem.lower()
                
                # Check if filename matches vitality patterns
                for pattern in vitality_patterns:
                    if pattern in filename_lower:
                        has_vitality = True
                        break
                
                # Check if filename matches defensive patterns
                if not has_vitality:
                    for pattern in defensive_patterns:
                        if pattern in filename_lower:
                            has_defensive = True
                            break
            
            # Extract display name from filename: Anju_max_hp.md -> max_hp
            display_name = var_file.stem.replace(f"{pcname}_", "")
            
            # Skip rolled_hp
            if display_name.lower() == 'rolled_hp':
                continue
            
            rel_path = var_file.relative_to(REPO_ROOT).as_posix()
            
            if has_vitality:
                pcs[pcname]['vitality'].append((display_name, value, rel_path))
            elif has_defensive:
                pcs[pcname]['defensive'].append((display_name, value, rel_path))
        
        # Now parse bending slots from the character sheet
        # Look for character sheet file in the PC directory
        char_sheet_path = None
        pc_folder = PC_DIR / pcname
        
        if pc_folder.exists() and pc_folder.is_dir():
            # Look for files containing "character sheet" (case-insensitive)
            for file in pc_folder.glob("*.md"):
                if "character sheet" in file.name.lower():
                    char_sheet_path = file
                    break
        
        # Fallback: look directly in PC_DIR
        if not char_sheet_path:
            for file in PC_DIR.glob("*.md"):
                if pcname.lower() in file.name.lower() and "character sheet" in file.name.lower():
                    char_sheet_path = file
                    break
        
        if char_sheet_path:
            char_sheet_text = read_text(char_sheet_path)
            rel_path = char_sheet_path.relative_to(REPO_ROOT).as_posix()
            
            # Parse vitals from character sheet Vitals section
            char_sheet_vitals = parse_vitals_from_character_sheet(char_sheet_text)
            for vital_name, vital_value in char_sheet_vitals:
                pcs[pcname]['vitality'].append((vital_name, vital_value, rel_path))
            
            # Parse bending slots from character sheet
            bending_slots = parse_bending_slots_from_character_sheet(char_sheet_text)
            for slot_name, slot_value in bending_slots:
                pcs[pcname]['bending_slots'].append((slot_name, slot_value, rel_path))
    
    return pcs


def also_find_global_files():
    """Search the repo for ad-hoc files that match canonical stat names."""
    # catch loose files like Rules/Evasion.md or Player Root/variable/current_hp.md
    extras = []
    # look for filenames that match key hints anywhere in the repo
    hints = ["evasion", "current_hp", "current hp", "environmental_water_charge"]
    for p in REPO_ROOT.rglob("*.md"):
        name = p.name.lower()
        for h in hints:
            if h in name:
                t = read_text(p)
                matches = find_matching_lines(t)
                extras.append((p.relative_to(REPO_ROOT).as_posix(), matches, p))
                break
    return extras


def render_markdown(envs, pcs, extras):
    """Render the overview markdown content for globals, PCs, and extra files."""
    lines = []
    # Use the user-specified header/template
    lines.append("# Stat Overview\n")
    lines.append("## Global environmental variables\n")
    lines.append("")
    lines.append("| Name                           | Value | Tags                                                         | File                                                 |")
    if envs:
        for name, val, tags, p in envs:
            # Name shown as wiki link [[name]] per user's edited format
            link = f"[[{name}]]"
            file_rel = str(p.relative_to(REPO_ROOT).as_posix())
            lines.append(f"| {link} | {val or ''} | {tags or ''} | {file_rel} |")
    else:
        lines.append("| (none) |  |  |  |")

    lines.append("\n\n## Per-PC extracted stats\n")
    lines.append("_(Only shows variables tagged with #vitality, #defensive, or #bending_slot, or matching patterns)_\n")
    
    if pcs:
        for pc, data in pcs.items():
            lines.append(f"\n### {pc}\n")
            
            vitality_stats = data.get('vitality', [])
            defensive_stats = data.get('defensive', [])
            bending_slots = data.get('bending_slots', [])
            
            # Display vitality stats if any
            if vitality_stats:
                lines.append("\n**Vitality**\n")
                lines.append("\n| Key           | Value | Source File                            |")
                for name, v, src in vitality_stats:
                    v2 = v if v else ""
                    lines.append(f"| {name} | {v2}    | {src} |")
                lines.append("")
            
            # Display defensive stats if any
            if defensive_stats:
                lines.append("\n**Defensive**\n")
                lines.append("\n| Key           | Value | Source File                            |")
                for name, v, src in defensive_stats:
                    v2 = v if v else ""
                    lines.append(f"| {name} | {v2}    | {src} |")
                lines.append("")
            
            # Display bending slots if any
            if bending_slots:
                lines.append("\n**Consumable Resources**\n")
                lines.append("")
                lines.append("| Resource Name            | Current/Max | Source File                                       |")
                lines.append("| ------------------------ | ----------- | ------------------------------------------------- |")
                for name, v, src in bending_slots:
                    v2 = v if v else ""
                    # Pad columns for proper alignment
                    name_padded = name[:24].ljust(24)
                    value_padded = v2[:11].ljust(11)
                    src_padded = src[:49].ljust(49)
                    lines.append(f"| {name_padded} | {value_padded} | {src_padded} |")
                lines.append("")
            
    else:
        lines.append("No PCs found under Player Root/variable/PC_variables/\n")

    lines.append("\n_Last generated by Mycelium/scripts/Python/generate_stat_overview.py_\n")
    return "\n".join(lines)


def main():
    """Generate stat_overview.md by aggregating PC sheets and environmental vars."""
    envs = gather_environmentals()
    pcs = gather_pc_stats()
    extras = also_find_global_files()
    md = render_markdown(envs, pcs, extras)
    try:
        OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUT_FILE.write_text(md, encoding="utf-8")
        print(f"Wrote {OUT_FILE}")
    except Exception as e:
        print("Failed to write output:", e, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
