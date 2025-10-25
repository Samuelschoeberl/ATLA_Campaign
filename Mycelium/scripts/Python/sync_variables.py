#!/usr/bin/env python3
"""Bi-directional sync between character sheets and variable files.

This script detects changes in character sheets (e.g., `Anju Character Sheet.md`)
and writes the updated values back to their corresponding variable files in
`Player Root/variable/PC_variables/<Name>/`, and vice versa.

By default, runs in WATCH MODE with bi-directional sync.

Example (sheet → variable):
  When `| current hp | 38 |` is changed to `| current hp | 32 |` in the sheet,
  it updates `Anju_current_hp.md` to contain `32` with appropriate tags.

Example (variable → sheet):
  When `Anju_current_hp.md` is changed from `38` to `32`,
  it updates the character sheet table to show `| current hp | 32 |`.

Usage:
  python3 sync_variables.py                    # Start watch mode (default)
  python3 sync_variables.py --once             # Run once and exit
  python3 sync_variables.py -c Anju            # Watch only Anju
  python3 sync_variables.py --once -c Anju     # Sync Anju once
  
Options:
  --once         : Run once and exit (instead of default watch mode)
  --dry-run      : Show what would be changed without making modifications
  --character    : Only process a specific character (e.g., --character Anju)
  --direction    : Sync direction: 'both' (default), 'sheet-to-var', 'var-to-sheet'
"""
from __future__ import annotations
from pathlib import Path
import re
import argparse
import time
import sys
from typing import Dict, List, Optional, Set, Tuple

try:
    from .common import read_var_value, write_var_file, to_number, ROOT
except ImportError:
    try:
        from common import read_var_value, write_var_file, to_number, ROOT
    except ImportError:
        # Fallback for standalone execution
        # Get to repo root: this file is in Mycelium/scripts/Python/
        ROOT = Path(__file__).resolve().parents[3]
        
        def read_var_value(path: Path) -> str:
            """Read value from variable file."""
            try:
                txt = path.read_text(encoding='utf-8')
                # Look for content in fenced markdown block
                m = re.search(r"```markdown\n(.*?)\n\n", txt, flags=re.S)
                if m:
                    return m.group(1).strip()
                # Fallback: first non-tag line
                for ln in txt.splitlines():
                    s = ln.strip()
                    if not s or s.startswith('#'):
                        continue
                    return s
            except Exception:
                pass
            return ''
        
        def write_var_file(path: Path, value: str, tags: Optional[List[str]] = None) -> None:
            """Write value to variable file with tags."""
            tags = tags or ['#variable']
            tag_line = ' '.join(tags)
            content = f"```markdown\n{value}\n\n{tag_line}\n\n```\n"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
        
        def to_number(s: str) -> int | float:
            """Convert string to number."""
            if not s:
                return 0
            s = str(s).strip()
            try:
                if '.' in s:
                    return float(s)
                return int(s)
            except ValueError:
                # Extract first number from string
                m = re.search(r'[-+]?\d+\.?\d*', s)
                if m:
                    val = m.group(0)
                    return float(val) if '.' in val else int(val)
                return 0


def regenerate_stat_overview():
    """Regenerate the stat_overview.md file by calling generate_stat_overview.py."""
    try:
        import subprocess
        
        # Regenerate the stat overview
        overview_script = ROOT / 'Mycelium' / 'scripts' / 'Python' / 'generate_stat_overview.py'
        if overview_script.exists():
            subprocess.run([sys.executable, str(overview_script)], 
                          cwd=str(ROOT), 
                          check=False, 
                          capture_output=True,
                          timeout=10)
    except Exception as e:
        # Silently fail - stat overview regeneration is optional
        pass


def get_environmental_variable_path(filename: str) -> Path:
    """Get the path to an environmental variable file."""
    return ENV_VAR_ROOT / filename


def read_environmental_var_value(path: Path) -> str:
    """Read value from an environmental variable file."""
    try:
        txt = path.read_text(encoding='utf-8')
        # Extract first line that's not empty and not a comment/tag
        for line in txt.splitlines():
            s = line.strip()
            if not s or s.startswith('#'):
                continue
            return s
    except Exception:
        pass
    return ''


def write_environmental_var_file(path: Path, value: str) -> None:
    """Write value to an environmental variable file, preserving description and tags."""
    try:
        existing_content = path.read_text(encoding='utf-8')
        lines = existing_content.splitlines()
        
        # Preserve everything except the first non-empty, non-tag line (the value)
        new_lines = []
        value_replaced = False
        
        for line in lines:
            s = line.strip()
            if not value_replaced and s and not s.startswith('#'):
                # This is the value line - replace it
                new_lines.append(value)
                value_replaced = True
            else:
                new_lines.append(line)
        
        path.write_text('\n'.join(new_lines), encoding='utf-8')
    except Exception:
        # If file doesn't exist or can't be read, create a simple version
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'{value}\n\n#variable #environmental_variables\n', encoding='utf-8')


def update_all_sheets_with_environmental_var(var_pattern: str, new_value: str, dry_run: bool = False) -> int:
    """Update an environmental variable in ALL character sheets.
    
    Returns the number of sheets updated.
    """
    if not PCS_ROOT.exists():
        return 0
    
    updated_count = 0
    
    for pc_dir in sorted(PCS_ROOT.iterdir()):
        if not pc_dir.is_dir():
            continue
        
        character_name = pc_dir.name
        
        # Skip special directories
        if character_name.startswith('.') or character_name.startswith('X_'):
            continue
        
        sheet_path = pc_dir / f"{character_name} Character Sheet.md"
        if not sheet_path.exists():
            continue
        
        # Check if this sheet has the environmental variable
        sheet_data = parse_character_sheet(sheet_path)
        
        for sheet_key, sheet_value in sheet_data.items():
            if re.match(var_pattern, sheet_key, re.IGNORECASE):
                # Found the environmental variable in this sheet
                if sheet_value != new_value:
                    if not dry_run:
                        if update_sheet_value(sheet_path, var_pattern, new_value, dry_run):
                            print(f"  ✓ Updated {character_name} sheet: {sheet_key} = {new_value}")
                            updated_count += 1
                    else:
                        print(f"  [DRY RUN] Would update {character_name} sheet: {sheet_key} = {new_value}")
                        updated_count += 1
                break
    
    return updated_count


def parse_stat_overview_environmental_vars() -> Dict[str, str]:
    """Parse environmental variables from stat_overview.md.
    
    Returns a dict of {variable_name: value} from the environmental variables table.
    Example: {'environmental_water_charge': '6'}
    """
    stat_overview_path = ROOT / 'Player Root' / 'PCs' / 'stat_overview.md'
    
    if not stat_overview_path.exists():
        return {}
    
    try:
        content = stat_overview_path.read_text(encoding='utf-8')
        lines = content.splitlines()
        
        env_vars = {}
        in_env_section = False
        in_table = False
        
        for i, line in enumerate(lines):
            # Look for the environmental variables section
            if 'Global environmental variables' in line:
                in_env_section = True
                continue
            
            # Stop at the next section (Per-PC stats)
            if in_env_section and '## Per-PC' in line:
                break
            
            # Look for table header with |
            if in_env_section and '|' in line and 'Name' in line and 'Value' in line:
                in_table = True
                # Skip header and separator line
                continue
            
            # Skip the separator line (contains dashes)
            if in_table and '---' in line:
                continue
            
            # Parse table rows
            if in_table and '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3:
                    # parts[0] is empty (before first |)
                    # parts[1] is Name (may contain [[wikilinks]])
                    # parts[2] is Value
                    name = parts[1].strip()
                    value = parts[2].strip()
                    
                    # Extract variable name from [[wikilink]] format
                    match = re.search(r'\[\[(.+?)\]\]', name)
                    if match:
                        var_name = match.group(1).strip()
                        if var_name and value:
                            env_vars[var_name] = value
        
        return env_vars
    except Exception as e:
        print(f"Error parsing stat_overview.md: {e}", file=sys.stderr)
        return {}


def sync_stat_overview_to_env_vars(dry_run: bool = False) -> Dict[str, Tuple[str, str]]:
    """Sync environmental variables from stat_overview.md to env var files and all sheets.
    
    Returns a dict of {var_name: (old_value, new_value)} for changed variables.
    """
    stat_overview_env_vars = parse_stat_overview_environmental_vars()
    
    if not stat_overview_env_vars:
        return {}
    
    changes = {}
    
    for var_name, stat_value in stat_overview_env_vars.items():
        # Get the environmental variable file path
        env_file_path = get_environmental_variable_path(f"{var_name}.md")
        
        # Read current value from env file
        current_value = read_environmental_var_value(env_file_path) if env_file_path.exists() else ''
        
        # Check if value differs
        if current_value != stat_value:
            changes[var_name] = (current_value, stat_value)
            
            if not dry_run:
                # Update the environmental variable file
                write_environmental_var_file(env_file_path, stat_value)
                print(f"✓ Updated environmental variable {var_name}.md from stat_overview: {current_value!r} → {stat_value!r}")
                
                # Find the pattern for this variable and propagate to all sheets
                for pattern, var_suffix in ENVIRONMENTAL_MAPPINGS:
                    if var_suffix == f"{var_name}.md":
                        updated = update_all_sheets_with_environmental_var(pattern, stat_value, dry_run)
                        if updated > 0:
                            print(f"  ✓ Propagated to {updated} character sheet(s)")
                        break
            else:
                print(f"[DRY RUN] Would update environmental variable {var_name}.md from stat_overview: {current_value!r} → {stat_value!r}")
    
    return changes


# Paths
PCS_ROOT = ROOT / 'Player Root' / 'PCs'
VAR_ROOT = ROOT / 'Player Root' / 'variable' / 'PC_variables'
ENV_VAR_ROOT = ROOT / 'Player Root' / 'variable' / 'environmental'
STAT_OVERVIEW_PATH = ROOT / 'Player Root' / 'PCs' / 'stat_overview.md'


# Mapping of sheet table keys to variable file suffixes and their tags
# Format: (sheet_key_pattern, variable_suffix, tags)
VARIABLE_MAPPINGS = [
    # Vitals
    (r'max[_ ]?hp', 'max_hp', ['#vitality', '#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    (r'current[_ ]?hp', 'current_hp', ['#vitality', '#current_variable', '#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    (r'initiative', 'Initiative', ['#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    (r'stress[_ ]?level', 'Stress Level', ['#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    (r'fire[_ ]?damage[_ ]?bonus', 'Fire Damage Bonus', ['#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    
    # Core Stats
    (r'strength', 'Strength', ['#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#primary_stat_{name}']),
    (r'dexterity', 'Dexterity', ['#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#primary_stat_{name}']),
    (r'constitution', 'Constitution', ['#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#primary_stat_{name}']),
    (r'intelligence', 'Intelligence', ['#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#primary_stat_{name}']),
    (r'wisdom', 'Wisdom', ['#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#primary_stat_{name}']),
    (r'charisma', 'Charisma', ['#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#primary_stat_{name}']),
    
    # Defensive
    (r'evasion', 'Evasion', ['#defensive', '#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    (r'barrier', 'Barrier', ['#defensive', '#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    (r'general[_ ]?armor', 'General Armor', ['#defensive', '#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    (r'physical[_ ]?armor', 'Physical Armor', ['#defensive', '#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    (r'fire[_ ]?armor', 'Fire Armor', ['#defensive', '#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    (r'ice[_ ]?armor', 'Ice Armor', ['#defensive', '#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    (r'spirit[_ ]?armor', 'Spirit Armor', ['#defensive', '#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    
    # Bending Slots
    (r'waterbending[_ ]?slot', 'waterbending slot', ['#water', '#show_if_water_ge_1', '#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    (r'earthbending[_ ]?slot', 'earthbending slot', ['#earth', '#show_if_earth_ge_1', '#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    (r'firebending[_ ]?slot', 'firebending slot', ['#fire', '#show_if_fire_ge_1', '#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    (r'airbending[_ ]?slot', 'airbending slot', ['#air', '#show_if_air_ge_1', '#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
    
    # Water charges (per-character)
    (r'waterbottle[_ ]?charge', 'Waterbottle Charge', ['#environmental_variables', '#variable_{name}', '#character_stat_{name}', '#character_stats_{name}', '#secondary_stat_{name}']),
]

# Environmental variables that are shared across ALL characters
# Format: (sheet_key_pattern, filename_in_environmental_folder)
ENVIRONMENTAL_MAPPINGS = [
    (r'environmental[_ ]?water[_ ]?charge', 'environmental_water_charge.md'),
]


def normalize_key(key: str) -> str:
    """Normalize a key for comparison."""
    return key.strip().lower().replace('_', ' ').replace('.', ' ')


def parse_character_sheet(sheet_path: Path) -> Dict[str, str]:
    """Parse a character sheet and extract key-value pairs from tables.
    
    Returns a dict with normalized keys and their values.
    """
    try:
        content = sheet_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading {sheet_path}: {e}", file=sys.stderr)
        return {}
    
    data = {}
    lines = content.splitlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Detect markdown table (look for separator line with dashes)
        if '|' in line and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if re.search(r'\|[\s\-:]+\|', next_line):
                # Found a table header
                headers = [h.strip() for h in line.strip('|').split('|')]
                
                # Skip separator line
                i += 2
                
                # Read table rows
                while i < len(lines) and '|' in lines[i]:
                    row = [c.strip() for c in lines[i].strip('|').split('|')]
                    if len(row) >= 2:
                        # Assuming first column is key, second is value
                        key = normalize_key(row[0])
                        value = row[1].strip()
                        if key and value:
                            data[key] = value
                    i += 1
                continue
        
        i += 1
    
    return data


def get_variable_file_path(character_name: str, var_suffix: str) -> Path:
    """Get the path to a variable file."""
    filename = f"{character_name}_{var_suffix}.md"
    return VAR_ROOT / character_name / filename


def extract_value(value_str: str) -> str:
    """Extract the numeric or string value from a sheet cell.
    
    Handles cases like:
    - "38" -> "38"
    - "1d20 + 1" -> "1d20 + 1" (keep formula)
    - "0" -> "0"
    """
    return value_str.strip()


def format_tags(tags: List[str], character_name: str) -> List[str]:
    """Format tags by replacing {name} placeholder with character name."""
    return [tag.replace('{name}', character_name) for tag in tags]


def sync_character_sheet(character_name: str, dry_run: bool = False) -> Dict[str, Tuple[str, str]]:
    """Sync a character sheet to variable files.
    
    Returns a dict of {variable_name: (old_value, new_value)} for changed variables.
    """
    sheet_path = PCS_ROOT / character_name / f"{character_name} Character Sheet.md"
    
    if not sheet_path.exists():
        print(f"Character sheet not found: {sheet_path}", file=sys.stderr)
        return {}
    
    # Parse the character sheet
    sheet_data = parse_character_sheet(sheet_path)
    
    if not sheet_data:
        return {}
    
    changes = {}
    
    # First, check for environmental variables (shared across all characters)
    for pattern, env_filename in ENVIRONMENTAL_MAPPINGS:
        # Find matching key in sheet data
        for sheet_key, sheet_value in sheet_data.items():
            if re.match(pattern, sheet_key, re.IGNORECASE):
                env_path = get_environmental_variable_path(env_filename)
                
                # Read current value from environmental variable file
                current_value = read_environmental_var_value(env_path) if env_path.exists() else ''
                
                # Extract new value
                new_value = extract_value(sheet_value)
                
                # Check if value changed
                if current_value != new_value:
                    changes[f"ENV:{env_filename}"] = (current_value, new_value)
                    
                    if not dry_run:
                        # Write the new value to environmental file
                        write_environmental_var_file(env_path, new_value)
                        print(f"✓ Updated environmental variable {env_filename}: {current_value!r} → {new_value!r}")
                        
                        # Propagate to all character sheets
                        updated_count = update_all_sheets_with_environmental_var(pattern, new_value, dry_run=False)
                        print(f"  ↳ Propagated to {updated_count} character sheet(s)")
                    else:
                        print(f"[DRY RUN] Would update environmental {env_filename}: {current_value!r} → {new_value!r}")
                        update_all_sheets_with_environmental_var(pattern, new_value, dry_run=True)
                
                break  # Found a match, move to next environmental mapping
    
    # Then, process per-character variables
    for pattern, var_suffix, tags in VARIABLE_MAPPINGS:
        # Find matching key in sheet data
        for sheet_key, sheet_value in sheet_data.items():
            if re.match(pattern, sheet_key, re.IGNORECASE):
                var_path = get_variable_file_path(character_name, var_suffix)
                
                # Read current value from variable file
                current_value = read_var_value(var_path) if var_path.exists() else ''
                
                # Extract new value
                new_value = extract_value(sheet_value)
                
                # Check if value changed
                if current_value != new_value:
                    changes[var_suffix] = (current_value, new_value)
                    
                    if not dry_run:
                        # Write the new value
                        formatted_tags = format_tags(tags, character_name)
                        write_var_file(var_path, new_value, formatted_tags)
                        print(f"✓ Updated {character_name}_{var_suffix}: {current_value!r} → {new_value!r}")
                    else:
                        print(f"[DRY RUN] Would update {character_name}_{var_suffix}: {current_value!r} → {new_value!r}")
                
                break  # Found a match, move to next mapping
    
    # Regenerate stat overview if changes were made
    if changes and not dry_run:
        regenerate_stat_overview()
    
    return changes


def sync_all_characters(dry_run: bool = False) -> Dict[str, Dict[str, Tuple[str, str]]]:
    """Sync all character sheets to variable files.
    
    Returns a dict of {character_name: {variable: (old, new)}} for all changes.
    """
    if not PCS_ROOT.exists():
        print(f"PCs root not found: {PCS_ROOT}", file=sys.stderr)
        return {}
    
    all_changes = {}
    
    for pc_dir in sorted(PCS_ROOT.iterdir()):
        if not pc_dir.is_dir():
            continue
        
        character_name = pc_dir.name
        
        # Skip special directories
        if character_name.startswith('.') or character_name.startswith('X_'):
            continue
        
        changes = sync_character_sheet(character_name, dry_run)
        if changes:
            all_changes[character_name] = changes
    
    # Note: sync_character_sheet already calls regenerate_stat_overview for each character
    # We don't need to call it again here to avoid redundant regenerations
    
    return all_changes


def update_sheet_value(sheet_path: Path, key_pattern: str, new_value: str, dry_run: bool = False) -> bool:
    """Update a value in a character sheet table.
    
    Returns True if the value was updated, False otherwise.
    """
    try:
        content = sheet_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading {sheet_path}: {e}", file=sys.stderr)
        return False
    
    lines = content.splitlines()
    updated = False
    
    # Find and update the value in the table
    for i, line in enumerate(lines):
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 3:
                # parts[0] is before first |, parts[1] is key, parts[2] is value
                key = parts[1].strip()
                if re.match(key_pattern, normalize_key(key), re.IGNORECASE):
                    # Found the row, update the value
                    old_value = parts[2].strip()
                    if old_value != new_value:
                        # Preserve the formatting - keep the same spacing pattern
                        # Replace just the value part, keeping surrounding whitespace structure
                        old_value_index = parts[2].find(old_value)
                        if old_value_index >= 0:
                            # Keep leading spaces, replace value, keep trailing spaces
                            leading = parts[2][:old_value_index]
                            trailing = parts[2][old_value_index + len(old_value):]
                            parts[2] = leading + new_value + trailing
                        else:
                            # Fallback: just use padded value
                            parts[2] = ' ' + new_value.rjust(len(old_value)) + ' '
                        
                        new_line = '|'.join(parts)
                        
                        if not dry_run:
                            lines[i] = new_line
                            updated = True
                        else:
                            updated = True
                        break
    
    if updated and not dry_run:
        sheet_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    
    return updated


def sync_variables_to_sheet(character_name: str, dry_run: bool = False) -> Dict[str, Tuple[str, str]]:
    """Sync variable files to character sheet (reverse direction).
    
    Returns a dict of {variable_name: (old_value, new_value)} for changed variables.
    """
    sheet_path = PCS_ROOT / character_name / f"{character_name} Character Sheet.md"
    var_dir = VAR_ROOT / character_name
    
    if not sheet_path.exists():
        print(f"Character sheet not found: {sheet_path}", file=sys.stderr)
        return {}
    
    if not var_dir.exists():
        return {}
    
    # Parse current sheet data
    sheet_data = parse_character_sheet(sheet_path)
    
    changes = {}
    
    # Check each variable file
    for pattern, var_suffix, tags in VARIABLE_MAPPINGS:
        var_path = get_variable_file_path(character_name, var_suffix)
        
        if not var_path.exists():
            continue
        
        # Read value from variable file
        var_value = read_var_value(var_path)
        
        # Find corresponding key in sheet
        sheet_key = None
        for sk in sheet_data.keys():
            if re.match(pattern, sk, re.IGNORECASE):
                sheet_key = sk
                break
        
        if sheet_key:
            sheet_value = sheet_data[sheet_key]
            
            # Check if values differ
            if sheet_value != var_value:
                changes[var_suffix] = (sheet_value, var_value)
                
                if not dry_run:
                    # Update the sheet
                    if update_sheet_value(sheet_path, pattern, var_value, dry_run):
                        print(f"✓ Updated {character_name} sheet {sheet_key}: {sheet_value!r} → {var_value!r}")
                else:
                    print(f"[DRY RUN] Would update {character_name} sheet {sheet_key}: {sheet_value!r} → {var_value!r}")
    
    # Check environmental variables
    for pattern, var_suffix in ENVIRONMENTAL_MAPPINGS:
        env_var_path = get_environmental_variable_path(var_suffix)
        
        if not env_var_path.exists():
            continue
        
        # Read value from environmental variable file
        env_value = read_environmental_var_value(env_var_path)
        
        # Find corresponding key in sheet
        sheet_key = None
        for sk in sheet_data.keys():
            if re.match(pattern, sk, re.IGNORECASE):
                sheet_key = sk
                break
        
        if sheet_key:
            sheet_value = sheet_data[sheet_key]
            
            # Check if values differ
            if sheet_value != env_value:
                changes[var_suffix] = (sheet_value, env_value)
                
                if not dry_run:
                    # Update the sheet
                    if update_sheet_value(sheet_path, pattern, env_value, dry_run):
                        print(f"✓ Updated {character_name} sheet {sheet_key} from environmental: {sheet_value!r} → {env_value!r}")
                else:
                    print(f"[DRY RUN] Would update {character_name} sheet {sheet_key} from environmental: {sheet_value!r} → {env_value!r}")
    
    # Regenerate stat overview if changes were made
    if changes and not dry_run:
        regenerate_stat_overview()
    
    return changes


def sync_all_variables_to_sheets(dry_run: bool = False) -> Dict[str, Dict[str, Tuple[str, str]]]:
    """Sync all variable files to their character sheets.
    
    Returns a dict of {character_name: {variable: (old, new)}} for all changes.
    """
    if not PCS_ROOT.exists():
        print(f"PCs root not found: {PCS_ROOT}", file=sys.stderr)
        return {}
    
    all_changes = {}
    
    for pc_dir in sorted(PCS_ROOT.iterdir()):
        if not pc_dir.is_dir():
            continue
        
        character_name = pc_dir.name
        
        # Skip special directories
        if character_name.startswith('.') or character_name.startswith('X_'):
            continue
        
        changes = sync_variables_to_sheet(character_name, dry_run)
        if changes:
            all_changes[character_name] = changes
    
    return all_changes


def sync_environmental_variables_to_sheets(dry_run: bool = False) -> Dict[str, Tuple[str, str]]:
    """Sync all environmental variable files to all character sheets.
    
    Returns a dict of {env_var_name: (old_value, new_value)} for changed variables.
    """
    if not ENV_VAR_ROOT.exists():
        return {}
    
    changes = {}
    
    # Check each environmental variable
    for pattern, env_filename in ENVIRONMENTAL_MAPPINGS:
        env_path = get_environmental_variable_path(env_filename)
        
        if not env_path.exists():
            continue
        
        # Read value from environmental file
        env_value = read_environmental_var_value(env_path)
        
        # Update all character sheets with this value
        # (The function returns the count, but we need to check if any were different)
        # For now, just propagate the value to all sheets
        if not dry_run:
            updated_count = update_all_sheets_with_environmental_var(pattern, env_value, dry_run=False)
            if updated_count > 0:
                changes[env_filename] = ('unknown', env_value)  # We don't track old values here
                print(f"✓ Synced environmental variable {env_filename} to {updated_count} sheet(s)")
        else:
            updated_count = update_all_sheets_with_environmental_var(pattern, env_value, dry_run=True)
            if updated_count > 0:
                changes[env_filename] = ('unknown', env_value)
    
    # Regenerate stat overview if changes were made
    if changes and not dry_run:
        regenerate_stat_overview()
    
    return changes


def watch_mode(character: Optional[str] = None, dry_run: bool = False, direction: str = 'both'):
    """Watch for changes and sync continuously in both directions."""
    sync_sheet_to_var = direction in ('both', 'sheet-to-var')
    sync_var_to_sheet = direction in ('both', 'var-to-sheet')
    
    print("Starting bi-directional watch mode... Press Ctrl+C to stop")
    print(f"Watching: {PCS_ROOT}")
    if sync_sheet_to_var and sync_var_to_sheet:
        print("Direction: Both (sheets ⟷ variables)")
    elif sync_sheet_to_var:
        print("Direction: Sheet → Variables only")
    else:
        print("Direction: Variables → Sheet only")
    
    # Track last modified times for sheets and variable files
    last_modified_sheets: Dict[Path, float] = {}
    last_modified_vars: Dict[Path, float] = {}
    last_modified_env: Dict[Path, float] = {}  # Track environmental variables
    
    # Initialize with current state - sheets
    if character:
        sheet_path = PCS_ROOT / character / f"{character} Character Sheet.md"
        if sheet_path.exists():
            last_modified_sheets[sheet_path] = sheet_path.stat().st_mtime
        
        # Initialize variable files for this character
        var_dir = VAR_ROOT / character
        if var_dir.exists():
            for var_file in var_dir.glob('*.md'):
                last_modified_vars[var_file] = var_file.stat().st_mtime
    else:
        # Initialize all character sheets
        for pc_dir in PCS_ROOT.iterdir():
            if pc_dir.is_dir() and not pc_dir.name.startswith('.') and not pc_dir.name.startswith('X_'):
                sheet_path = pc_dir / f"{pc_dir.name} Character Sheet.md"
                if sheet_path.exists():
                    last_modified_sheets[sheet_path] = sheet_path.stat().st_mtime
                
                # Initialize variable files
                var_dir = VAR_ROOT / pc_dir.name
                if var_dir.exists():
                    for var_file in var_dir.glob('*.md'):
                        last_modified_vars[var_file] = var_file.stat().st_mtime
    
    # Initialize environmental variable files
    if ENV_VAR_ROOT.exists():
        for env_file in ENV_VAR_ROOT.glob('*.md'):
            last_modified_env[env_file] = env_file.stat().st_mtime
    
    # Initialize stat_overview.md monitoring
    last_modified_stat_overview = STAT_OVERVIEW_PATH.stat().st_mtime if STAT_OVERVIEW_PATH.exists() else 0
    
    try:
        while True:
            time.sleep(0.5)  # Check twice per second for faster response
            
            # Check stat_overview.md for environmental variable changes
            if sync_sheet_to_var and STAT_OVERVIEW_PATH.exists():
                current_mtime = STAT_OVERVIEW_PATH.stat().st_mtime
                if current_mtime > last_modified_stat_overview:
                    print(f"\n📊 Detected change in stat_overview.md")
                    changes = sync_stat_overview_to_env_vars(dry_run)
                    if changes:
                        print(f"  ✓ Synced {len(changes)} environmental variable(s) from stat_overview")
                    last_modified_stat_overview = current_mtime
                    
                    # Update all environmental file mtimes to avoid triggering env→sheet sync
                    for env_path in last_modified_env.keys():
                        if env_path.exists():
                            last_modified_env[env_path] = env_path.stat().st_mtime
                    
                    # Update all sheet mtimes to avoid triggering sheet→var sync
                    for sheet_path in last_modified_sheets.keys():
                        if sheet_path.exists():
                            last_modified_sheets[sheet_path] = sheet_path.stat().st_mtime
            
            # Check environmental variable files for modifications (env → all sheets)
            if sync_var_to_sheet:
                for env_path in list(last_modified_env.keys()):
                    if not env_path.exists():
                        del last_modified_env[env_path]
                        continue
                    
                    current_mtime = env_path.stat().st_mtime
                    
                    if current_mtime > last_modified_env[env_path]:
                        env_name = env_path.stem
                        print(f"\n🌍 Detected change in environmental variable {env_name}.md")
                        sync_environmental_variables_to_sheets(dry_run)
                        last_modified_env[env_path] = current_mtime
                        
                        # Update all sheet mtimes to avoid triggering sheet→var sync
                        for sheet_path in last_modified_sheets.keys():
                            if sheet_path.exists():
                                last_modified_sheets[sheet_path] = sheet_path.stat().st_mtime
            
            # Check sheets for modifications (sheet → var)
            if sync_sheet_to_var:
                for sheet_path in list(last_modified_sheets.keys()):
                    if not sheet_path.exists():
                        del last_modified_sheets[sheet_path]
                        continue
                    
                    current_mtime = sheet_path.stat().st_mtime
                    
                    if current_mtime > last_modified_sheets[sheet_path]:
                        print(f"\n🔄 Detected change in {sheet_path.name} (sheet → variables)")
                        character_name = sheet_path.parent.name
                        sync_character_sheet(character_name, dry_run)
                        last_modified_sheets[sheet_path] = current_mtime
            
            # Check variable files for modifications (var → sheet)
            if sync_var_to_sheet:
                for var_path in list(last_modified_vars.keys()):
                    if not var_path.exists():
                        del last_modified_vars[var_path]
                        continue
                    
                    current_mtime = var_path.stat().st_mtime
                    
                    if current_mtime > last_modified_vars[var_path]:
                        character_name = var_path.parent.name
                        var_name = var_path.stem
                        print(f"\n🔄 Detected change in {var_name}.md (variable → sheet)")
                        sync_variables_to_sheet(character_name, dry_run)
                        last_modified_vars[var_path] = current_mtime
                        
                        # Also update the sheet's mtime to avoid triggering sheet→var sync
                        sheet_path = PCS_ROOT / character_name / f"{character_name} Character Sheet.md"
                        if sheet_path.exists():
                            last_modified_sheets[sheet_path] = sheet_path.stat().st_mtime
            
            # Check for new files if watching all characters
            if not character:
                for pc_dir in PCS_ROOT.iterdir():
                    if pc_dir.is_dir() and not pc_dir.name.startswith('.') and not pc_dir.name.startswith('X_'):
                        # Check for new sheets
                        sheet_path = pc_dir / f"{pc_dir.name} Character Sheet.md"
                        if sheet_path.exists() and sheet_path not in last_modified_sheets:
                            last_modified_sheets[sheet_path] = sheet_path.stat().st_mtime
                        
                        # Check for new variable files
                        var_dir = VAR_ROOT / pc_dir.name
                        if var_dir.exists():
                            for var_file in var_dir.glob('*.md'):
                                if var_file not in last_modified_vars:
                                    last_modified_vars[var_file] = var_file.stat().st_mtime
                
                # Check for new environmental variable files
                if ENV_VAR_ROOT.exists():
                    for env_file in ENV_VAR_ROOT.glob('*.md'):
                        if env_file not in last_modified_env:
                            last_modified_env[env_file] = env_file.stat().st_mtime
                            
    except KeyboardInterrupt:
        print("\n\nStopped watching")


def main():
    parser = argparse.ArgumentParser(
        description='Bi-directional sync between character sheets and variable files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--once', action='store_true',
                        help='Run once and exit (instead of default watch mode)')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Show what would be changed without making modifications')
    parser.add_argument('--character', '-c', type=str,
                        help='Only process a specific character (e.g., Anju)')
    parser.add_argument('--direction', '-d', type=str, 
                        choices=['both', 'sheet-to-var', 'var-to-sheet'],
                        default='both',
                        help='Sync direction: both (default), sheet-to-var, or var-to-sheet')
    
    args = parser.parse_args()
    
    # Default behavior: watch mode with bi-directional sync
    if not args.once:
        watch_mode(args.character, args.dry_run, args.direction)
    elif args.character:
        # One-time sync for specific character
        if args.direction in ('both', 'sheet-to-var'):
            print(f"Syncing character sheet → variables: {args.character}")
            changes = sync_character_sheet(args.character, args.dry_run)
            if not changes:
                print(f"No changes detected (sheet → variables) for {args.character}")
        
        if args.direction in ('both', 'var-to-sheet'):
            print(f"Syncing variables → character sheet: {args.character}")
            changes = sync_variables_to_sheet(args.character, args.dry_run)
            if not changes:
                print(f"No changes detected (variables → sheet) for {args.character}")
    else:
        # One-time sync for all characters
        if args.direction in ('both', 'sheet-to-var'):
            print("Syncing all character sheets → variables...")
            all_changes = sync_all_characters(args.dry_run)
            
            if not all_changes:
                print("No changes detected (sheet → variables)")
            else:
                print(f"\nTotal characters updated (sheet → variables): {len(all_changes)}")
                for char, changes in all_changes.items():
                    print(f"  {char}: {len(changes)} variable(s)")
        
        if args.direction in ('both', 'var-to-sheet'):
            print("\nSyncing all variables → character sheets...")
            all_changes = sync_all_variables_to_sheets(args.dry_run)
            
            if not all_changes:
                print("No changes detected (variables → sheet)")
            else:
                print(f"\nTotal characters updated (variables → sheet): {len(all_changes)}")
                for char, changes in all_changes.items():
                    print(f"  {char}: {len(changes)} variable(s)")


if __name__ == '__main__':
    main()
