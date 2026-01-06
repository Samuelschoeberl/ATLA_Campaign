#!/usr/bin/env python3
"""
Direct bidirectional sync - edits table cells in place, never regenerates files.

CORE PRINCIPLE: Variable files are the canonical source of truth.
When a table cell in a character sheet or stat_overview.md is newer than its
variable file, this script updates the variable file and then directly edits
all other occurrences of that variable in other character sheets and stat_overview.md.

NO REGENERATION - only direct table cell editing.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union

# Setup paths
ROOT = Path(__file__).resolve().parents[3]
PCS_DIR = ROOT.joinpath('Player Root', 'PCs')
PC_VARS_DIR = ROOT.joinpath('Player Root', 'variable', 'PC_variables')
ENV_VARS_DIR = ROOT.joinpath('Player Root', 'variable', 'environmental')
STAT_OVERVIEW = PCS_DIR.joinpath('stat_overview.md')


def pc_safe(name: str) -> str:
    """Convert PC name to safe directory name."""
    return name.replace(' ', '_').replace("'", '')


def get_pc_list() -> List[str]:
    """Get list of all PC names from PCs directory."""
    pc_names = []
    for item in PCS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith('.') and not item.name.startswith('_'):
            name = item.name.replace('_', ' ')
            pc_names.append(name)
    return sorted(pc_names)


def get_character_sheet_path(pc_name: str) -> Optional[Path]:
    """Get the character sheet path, trying multiple naming variants."""
    safe_name = pc_safe(pc_name)
    pc_dir = PCS_DIR.joinpath(safe_name)
    
    if not pc_dir.exists():
        return None
    
    # Try different case variations
    variants = [
        f'{safe_name} character sheet.md',
        f'{safe_name} Character Sheet.md',
        f'{safe_name} Character sheet.md',
        f'{safe_name} character Sheet.md',
    ]
    
    for variant in variants:
        sheet_path = pc_dir.joinpath(variant)
        if sheet_path.exists():
            return sheet_path
    
    return None


def display_name_to_stem(display_name: str) -> str:
    """Convert display name to variable stem."""
    # Remove wikilink brackets
    display_name = re.sub(r'\[\[([^\]]+)\]\]', r'\1', display_name)
    return display_name.lower().replace(' ', '_').replace('-', '_')


def stem_to_display_name(var_stem: str) -> str:
    """Convert variable stem to display name."""
    return var_stem.replace('_', ' ').title()


def is_environmental_variable(var_stem: str) -> bool:
    """Check if a variable is environmental."""
    return ENV_VARS_DIR.joinpath(f'{var_stem}.md').exists()


def get_variable_file_path(pc_name: str, var_stem: str, is_environmental: bool) -> Path:
    """Get the path to a variable file, trying multiple naming variants."""
    if is_environmental:
        # Try multiple variants for environmental variables
        variants = [
            ENV_VARS_DIR.joinpath(f'{var_stem}.md'),
            ENV_VARS_DIR.joinpath(f'{var_stem.replace("_", " ")}.md'),
            ENV_VARS_DIR.joinpath(f'{var_stem.replace("_", " ").title()}.md'),
        ]
        for variant in variants:
            if variant.exists():
                return variant
        return ENV_VARS_DIR.joinpath(f'{var_stem}.md')  # Default
    else:
        # Try multiple variants for PC-specific variables
        safe_name = pc_safe(pc_name)
        pc_var_dir = PC_VARS_DIR.joinpath(safe_name)
        
        # Most common pattern: Puy_Fire Armor.md (Title Case with spaces)
        title_case_with_space = var_stem.replace('_', ' ').title()
        
        # Generate variants with/without trailing 's'
        stems_to_try = [var_stem]
        
        # Try removing trailing 's' (reactions -> reaction)
        if var_stem.endswith('s') and len(var_stem) > 2:
            stems_to_try.append(var_stem[:-1])
        # Try adding trailing 's' (reaction -> reactions)
        else:
            stems_to_try.append(var_stem + 's')
        
        variants = []
        for stem in stems_to_try:
            title_case = stem.replace('_', ' ').title()
            variants.extend([
                pc_var_dir.joinpath(f'{safe_name}_{title_case}.md'),  # Most common!
                pc_var_dir.joinpath(f'{safe_name}_{stem}.md'),
                pc_var_dir.joinpath(f'{safe_name}_{stem.replace("_", " ")}.md'),
                pc_var_dir.joinpath(f'{safe_name} {stem}.md'),
                pc_var_dir.joinpath(f'{safe_name} {stem.replace("_", " ")}.md'),
                pc_var_dir.joinpath(f'{safe_name} {title_case}.md'),
            ])
        
        for variant in variants:
            if variant.exists():
                return variant
        
        return pc_var_dir.joinpath(f'{safe_name}_{var_stem}.md')  # Default


def read_variable_file(var_file: Path) -> Optional[Any]:
    """Read value from a variable file."""
    if not var_file.exists():
        return None
    
    content = var_file.read_text(encoding='utf-8')
    lines = content.strip().split('\n')
    
    if not lines:
        return None
    
    # First non-empty line is the value
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            # Try to parse as number
            try:
                if line.isdigit() or (line.startswith('-') and line[1:].isdigit()):
                    return int(line)
                elif '.' in line:
                    try:
                        return float(line)
                    except ValueError:
                        pass
            except:
                pass
            return line
    
    return None


def write_variable_file(var_file: Path, value: Any, tags: List[str]):
    """Write a variable file."""
    var_file.parent.mkdir(parents=True, exist_ok=True)
    tag_str = ' '.join(tags) if tags else '#variable'
    content = f'{value}\n\n{tag_str}\n'
    var_file.write_text(content, encoding='utf-8')


def find_and_update_table_cell(file_path: Path, var_stem: str, new_value: Any, pc_name: Optional[str] = None, verbose: bool = False) -> bool:
    """
    Find and update a table cell value in a markdown file.
    
    If pc_name is provided and the file is stat_overview.md, will only update
    within that PC's section to avoid cross-contamination.
    
    Returns True if found and updated, False otherwise.
    """
    if not file_path.exists():
        return False
    
    content = file_path.read_text(encoding='utf-8')
    lines = content.splitlines()
    updated = False
    
    # Build search patterns with priority ordering
    # Priority 1: Exact match with underscores (var_stem as-is)
    # Priority 2: Exact match with spaces instead of underscores
    # Priority 3: Title case version
    exact_patterns = [
        var_stem.lower(),                           # exact with underscores: "environmental_water_charge"
        var_stem.replace('_', ' ').lower(),         # exact with spaces: "environmental water charge"
        stem_to_display_name(var_stem).lower()      # title case: "Environmental Water Charge"
    ]
    
    # If this is stat_overview.md and we have a PC name, find the PC's section
    start_line = 0
    end_line = len(lines)
    
    if pc_name and file_path.name == 'stat_overview.md':
        # Find the PC's section by looking for "### PC_Name"
        pc_header = f"### {pc_safe(pc_name)}"
        pc_header_alt = f"### {pc_name}"
        
        for i, line in enumerate(lines):
            if line.strip() == pc_header or line.strip() == pc_header_alt:
                start_line = i
                # Find the end of this PC's section (next ### or end of file)
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith('### '):
                        end_line = j
                        break
                break
        
        if verbose and start_line > 0:
            print(f"    Searching in {pc_name}'s section (lines {start_line}-{end_line})")
    
    # Search within the appropriate range
    for i in range(start_line, end_line):
        line = lines[i]
        
        if '|' not in line:
            continue
        
        parts = line.split('|')
        if len(parts) < 3:
            continue
        
        # Usually: | key | value | or | key | value | other columns |
        key_cell = parts[1].strip() if len(parts) > 1 else ''
        
        # Check for wikilink [[name]]
        wiki_match = re.search(r'\[\[([^\]]+)\]\]', key_cell)
        if wiki_match:
            key_text = wiki_match.group(1).lower()
        else:
            key_text = key_cell.lower()
        
        # Matching strategy with strict priority:
        # 1. EXACT MATCH: key_text exactly equals one of our exact patterns
        # 2. FUZZY MATCH (fallback): only if key is a complete word within pattern
        
        is_match = False
        match_reason = None
        
        # Priority 1: Try exact matches first
        if key_text in exact_patterns:
            is_match = True
            match_reason = "exact"
        
        # Priority 2: Fuzzy matching - only match if key_text is a COMPLETE WORD in the pattern
        # This prevents "water" from matching "environmental_water_charge"
        if not is_match:
            for pattern in exact_patterns:
                # Normalize both to space-separated words for word boundary checking
                pattern_normalized = pattern.replace('_', ' ')
                key_normalized = key_text.replace('_', ' ')
                
                # Split into words and check if key is a complete word in pattern
                pattern_words = pattern_normalized.split()
                key_words = key_normalized.split()
                
                # Only match if ALL key words appear as complete words in pattern
                # AND the key is not trivially short (prevents "a" matching "water")
                if len(key_normalized) > 3 and all(kw in pattern_words for kw in key_words):
                    # Extra check: if pattern has MORE words than key, require key to be meaningful
                    # E.g., "water" shouldn't match "environmental water charge" but
                    # "water charge" could match "environmental water charge"
                    if len(key_words) >= max(1, len(pattern_words) - 1):
                        is_match = True
                        match_reason = "fuzzy"
                        break
        
        if is_match:
            # Found it - update value in column 2 (index 2 in parts)
            if len(parts) > 2:
                old_value = parts[2].strip()
                # Preserve right-alignment for numbers
                if old_value and old_value.lstrip().replace('.', '').replace('-', '').isdigit():
                    # Right-align numbers
                    width = len(old_value)
                    parts[2] = f' {str(new_value):>{width}} '
                else:
                    parts[2] = f' {new_value} '
                
                lines[i] = '|'.join(parts)
                updated = True
                
                if verbose:
                    section_info = f" in {pc_name}'s section" if pc_name else ""
                    print(f"    Updated {file_path.name}{section_info}: {key_cell} = {new_value}")
                break
    
    if updated:
        file_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    
    return updated


def parse_all_table_values(file_path: Path, return_pc_context: bool = False) -> Union[Dict[str, Tuple[Any, int]], Dict[str, Tuple[Any, int, Optional[str]]]]:
    """
    Parse all table values from a file.
    Returns dict of var_stem -> (value, line_number) or (value, line_number, pc_name) if return_pc_context=True
    
    If return_pc_context=True and file is stat_overview.md, includes which PC section the variable belongs to.
    """
    if not file_path.exists():
        return {}
    
    content = file_path.read_text(encoding='utf-8')
    lines = content.splitlines()
    results = {}
    
    # Track current PC section if this is stat_overview.md
    current_pc = None
    is_stat_overview = file_path.name == 'stat_overview.md'
    
    for i, line in enumerate(lines):
        # Check for PC section headers in stat_overview.md
        if is_stat_overview and line.startswith('### '):
            pc_header = line[4:].strip()  # Remove "### "
            # Convert from safe name (X_Testchar) to regular name if needed
            current_pc = pc_header.replace('_', ' ')
            continue
        
        if '|' not in line:
            continue
        
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 3:
            continue
        
        key = parts[1]
        value = parts[2] if len(parts) > 2 else ''
        
        # Skip headers and separators
        if not key or not value:
            continue
        
        # Common table header keywords
        if key.lower() in ['key', 'stat', 'name', 'element', 'slot', 'value', 'amount', 
                           'base', 'level', 'attack roll', 'dc', 'tags', 'file', 'source file']:
            continue
        
        # Skip if value looks like a header
        if value.lower() in ['value', 'amount', 'base', 'level', 'attack roll', 'dc', 
                             'tags', 'file', 'source file']:
            continue
        
        # Skip separator rows
        if re.match(r'^-+$', key) or re.match(r'^-+$', value):
            continue
        
        # Skip markdown formatting
        if key.startswith('#') or key.startswith('**'):
            continue
        
        # Check if next line is a separator (indicates this is a header row)
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            if '|' in next_line and re.search(r'\|-+\|', next_line):
                continue
        
        var_stem = display_name_to_stem(key)
        if len(var_stem) < 2 or var_stem.isdigit():
            continue
        
        # Parse value
        try:
            if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
                parsed_value = int(value)
            elif '.' in value:
                try:
                    parsed_value = float(value)
                except ValueError:
                    parsed_value = value
            else:
                parsed_value = value
            
            if return_pc_context:
                # Make key unique per PC to avoid overwriting: pc_name:var_stem
                if current_pc:
                    unique_key = f"{current_pc}:{var_stem}"
                else:
                    unique_key = var_stem
                results[unique_key] = (parsed_value, i, current_pc)
            else:
                results[var_stem] = (parsed_value, i)
        except:
            continue
    
    return results


def sync_from_variable_files(verbose: bool = False) -> int:
    """
    Sync from variable files to character sheets and stat_overview.
    This is called when variable files are edited directly.
    """
    pc_names = get_pc_list()
    updated_variables = set()
    
    # Check environmental variable files
    if ENV_VARS_DIR.exists():
        for var_file in ENV_VARS_DIR.glob('*.md'):
            var_stem = var_file.stem
            value = read_variable_file(var_file)
            
            if value is None:
                continue
            
            # Check all character sheets to see if they have this variable
            needs_update = False
            for pc_name in pc_names:
                sheet_path = get_character_sheet_path(pc_name)
                if sheet_path:
                    table_values = parse_all_table_values(sheet_path)
                    if var_stem in table_values:
                        sheet_value, _ = table_values[var_stem]
                        if sheet_value != value:
                            needs_update = True
                            break
            
            # Check stat_overview
            if not needs_update and STAT_OVERVIEW.exists():
                table_values = parse_all_table_values(STAT_OVERVIEW)
                if var_stem in table_values:
                    sheet_value, _ = table_values[var_stem]
                    if sheet_value != value:
                        needs_update = True
            
            if needs_update:
                print(f"\n✓ {var_stem} changed in variable file: updating all locations to {value}")
                
                # Update all character sheets that need updating
                for pc in pc_names:
                    sheet = get_character_sheet_path(pc)
                    if sheet:
                        table_values = parse_all_table_values(sheet)
                        if var_stem in table_values:
                            sheet_value, _ = table_values[var_stem]
                            if sheet_value != value:
                                find_and_update_table_cell(sheet, var_stem, value, pc_name=None, verbose=verbose)
                
                # Update stat_overview if needed
                if STAT_OVERVIEW.exists():
                    table_values = parse_all_table_values(STAT_OVERVIEW)
                    if var_stem in table_values:
                        overview_value, _ = table_values[var_stem]
                        if overview_value != value:
                            find_and_update_table_cell(STAT_OVERVIEW, var_stem, value, pc_name=None, verbose=verbose)
                
                updated_variables.add(var_stem)
    
    # Check PC-specific variable files
    if PC_VARS_DIR.exists():
        for pc_dir in PC_VARS_DIR.iterdir():
            if not pc_dir.is_dir():
                continue
            
            pc_safe_name = pc_dir.name
            pc_name = pc_safe_name.replace('_', ' ')
            
            for var_file in pc_dir.glob('*.md'):
                # Extract variable stem from filename like "Puy_Fire Armor.md"
                filename = var_file.stem
                if filename.startswith(pc_safe_name + '_') or filename.startswith(pc_safe_name + ' '):
                    var_name = filename[len(pc_safe_name)+1:]
                    var_stem = display_name_to_stem(var_name)
                else:
                    var_stem = display_name_to_stem(filename)
                
                value = read_variable_file(var_file)
                if value is None:
                    continue
                
                # Check if updates are needed
                sheet_path = get_character_sheet_path(pc_name)
                if not sheet_path:
                    continue
                
                table_values = parse_all_table_values(sheet_path)
                if var_stem not in table_values:
                    continue
                
                sheet_value_tuple = table_values[var_stem]
                sheet_value = sheet_value_tuple[0]  # First element is always the value
                sheet_needs_update = (sheet_value != value)
                
                # Check stat_overview too
                overview_needs_update = False
                if STAT_OVERVIEW.exists():
                    overview_values = parse_all_table_values(STAT_OVERVIEW, return_pc_context=True)
                    overview_key = f"{pc_name}:{var_stem}"
                    if overview_key in overview_values:
                        overview_value_tuple = overview_values[overview_key]
                        overview_value = overview_value_tuple[0]  # First element is always the value
                        overview_needs_update = (overview_value != value)
                
                # Skip if nothing needs updating
                if not sheet_needs_update and not overview_needs_update:
                    continue
                
                # At least one location needs updating
                print(f"\n✓ {var_stem} changed in {pc_name}'s variable file: updating to {value}")
                
                if sheet_needs_update:
                    find_and_update_table_cell(sheet_path, var_stem, value, pc_name=None, verbose=verbose)
                
                if overview_needs_update:
                    find_and_update_table_cell(STAT_OVERVIEW, var_stem, value, pc_name=pc_name, verbose=verbose)
                
                updated_variables.add(var_stem)
    
    return len(updated_variables)


def sync_variables_direct_edit(verbose: bool = False) -> None:
    """
    Sync variables by directly editing table cells - no file regeneration.
    
    Process:
    1. For each variable found in any source file (character sheets, stat_overview.md)
    2. Find the NEWEST occurrence of each variable across all files
    3. Use the newest value as the source of truth
    4. Update variable file if needed, then propagate to all other files
    5. Never regenerate - only edit specific table cells
    """
    print("="*70)
    print("DIRECT SYNC (editing table cells in place)")
    print("="*70)
    
    pc_names = get_pc_list()
    if not pc_names:
        print("No PCs found")
        return
    
    # Collect all source files to scan
    source_files: List[Tuple[Path, str]] = []  # (file_path, pc_name or 'stat_overview')
    
    # Add all character sheets
    for pc_name in pc_names:
        sheet_path = get_character_sheet_path(pc_name)
        if sheet_path:
            source_files.append((sheet_path, pc_name))
    
    # Add stat_overview.md
    if STAT_OVERVIEW.exists():
        source_files.append((STAT_OVERVIEW, 'stat_overview'))
    
    # Track what we've updated and the newest source for each variable
    updated_variables = set()
    # variable_key -> (value, source_time, source_file, source_name, pc_owner)
    newest_values: Dict[str, Tuple[Any, float, Path, str, Optional[str]]] = {}
    
    # PHASE 1: Scan all files to find the newest value for each variable
    for source_file, source_name in source_files:
        if verbose:
            print(f"\nScanning: {source_name}")
        
        source_time = source_file.stat().st_mtime
        
        # For stat_overview, get table values with PC context
        if source_name == 'stat_overview':
            table_values = parse_all_table_values(source_file, return_pc_context=True)
        else:
            table_values = parse_all_table_values(source_file, return_pc_context=False)
        
        for key, value_tuple in table_values.items():
            # Extract var_stem from key (could be "PC:var_stem" or just "var_stem")
            if source_name == 'stat_overview' and ':' in key:
                # PC-specific key format: "PC_Name:var_stem"
                pc_from_key, var_stem = key.split(':', 1)
            else:
                var_stem = key
                pc_from_key = None
            
            # Extract value and optionally PC name
            if source_name == 'stat_overview':
                if len(value_tuple) == 3:
                    value, line_num, pc_owner = value_tuple
                else:
                    value, line_num = value_tuple
                    pc_owner = None
            else:
                if len(value_tuple) == 2:
                    value, line_num = value_tuple
                    pc_owner = None
                else:
                    value, line_num, pc_owner = value_tuple
            
            # Determine if environmental
            is_env = is_environmental_variable(var_stem)
            
            # For PC-specific variables from stat_overview, use the detected PC owner
            if not is_env and source_name == 'stat_overview':
                if pc_owner is None:
                    if verbose:
                        print(f"  - Skipped {var_stem}: found in stat_overview but not in a PC section")
                    continue
                actual_source_name = pc_owner
            else:
                actual_source_name = source_name
            
            # Create unique key for tracking (includes PC name for PC-specific vars)
            if is_env:
                tracking_key = f"env:{var_stem}"
            else:
                tracking_key = f"pc:{actual_source_name}:{var_stem}"
            
            # Check if this is the newest occurrence we've seen
            if tracking_key not in newest_values or source_time > newest_values[tracking_key][1]:
                newest_values[tracking_key] = (value, source_time, source_file, source_name, pc_owner)
                if verbose:
                    print(f"  Found {var_stem} = {value} (mtime: {source_time})")
    
    # PHASE 2: Process each variable using the newest value
    for tracking_key, (value, source_time, source_file, source_name, pc_owner) in newest_values.items():
        # Parse tracking key
        if tracking_key.startswith("env:"):
            is_env = True
            var_stem = tracking_key[4:]  # Remove "env:" prefix
            actual_source_name = None
        else:
            is_env = False
            _, actual_source_name, var_stem = tracking_key.split(":", 2)
        
        # Get variable file
        if is_env:
            var_file = ENV_VARS_DIR.joinpath(f'{var_stem}.md')
        else:
            if not actual_source_name:
                if verbose:
                    print(f"  - Skipped {var_stem}: no PC name for PC-specific variable")
                continue
            var_file = get_variable_file_path(actual_source_name, var_stem, False)
        
        if not var_file.exists():
            if verbose:
                print(f"  - Skipped {var_stem}: no variable file exists")
            continue
        
        # For PC-specific variables, verify the variable file actually belongs to this PC
        if not is_env:
            if not actual_source_name:
                if verbose:
                    print(f"  - Skipped {var_stem}: no PC name for ownership verification")
                continue
            safe_name = pc_safe(actual_source_name)
            expected_pc_dir = PC_VARS_DIR.joinpath(safe_name)
            if not var_file.is_relative_to(expected_pc_dir):
                if verbose:
                    print(f"  - Skipped {var_stem}: variable file doesn't belong to {actual_source_name}")
                continue
        
        # Read current variable value to compare
        current_value = read_variable_file(var_file)
        
        # Check if value actually changed
        if current_value != value:
            # Determine the effective source name for display
            display_source = f"{source_name} ({pc_owner})" if source_name == 'stat_overview' and pc_owner else source_name
            
            if verbose:
                if is_env:
                    print(f"\n✓ {var_stem}: {current_value} → {value} (from {display_source}, newest at {source_time}) [ENVIRONMENTAL]")
                else:
                    print(f"\n✓ {var_stem}: {current_value} → {value} (from {display_source}, newest at {source_time}) [PC-SPECIFIC: {var_file.parent.name}]")
            else:
                print(f"\n✓ {var_stem}: {current_value} → {value} (from {display_source})")
            
            # Always update variable file - we already determined this is the newest value
            if is_env:
                tags = ['#variable', '#secondary_stat', '#template', '#environmental_variables']
            else:
                tag_source = actual_source_name if actual_source_name else source_name
                if tag_source == 'stat_overview':
                    tag_source = pc_owner if pc_owner else 'unknown'
                safe_name = pc_safe(tag_source)
                tags = ['#variable', f'#character_stat_{safe_name}', f'#character_stats_{safe_name}']
            
            write_variable_file(var_file, value, tags)
            
            # Always propagate changes when value differs
            # Now update ALL other files with this variable
            if is_env:
                # Environmental variable - update in ALL character sheets and stat_overview
                print(f"  Propagating to all character sheets and stat_overview...")
                
                # Update stat_overview (skip if it was the source)
                if STAT_OVERVIEW.exists() and source_file != STAT_OVERVIEW:
                    find_and_update_table_cell(STAT_OVERVIEW, var_stem, value, pc_name=None, verbose=verbose)
                
                # Update all character sheets (skip if it was the source)
                for pc in pc_names:
                    sheet = get_character_sheet_path(pc)
                    if sheet and sheet != source_file:
                        find_and_update_table_cell(sheet, var_stem, value, pc_name=None, verbose=verbose)
            else:
                # PC-specific variable - update that PC's sheet and stat_overview
                target_pc = actual_source_name if actual_source_name else source_name
                if target_pc == 'stat_overview':
                    target_pc = pc_owner if pc_owner else source_name
                
                print(f"  Updating {target_pc}'s character sheet and stat_overview...")
                
                # Update this PC's character sheet (skip if it was the source)
                sheet = get_character_sheet_path(target_pc)
                if sheet and sheet != source_file:
                    find_and_update_table_cell(sheet, var_stem, value, pc_name=None, verbose=verbose)
                
                # Update stat_overview (skip if it was the source) - with PC name for section targeting
                if STAT_OVERVIEW.exists() and source_file != STAT_OVERVIEW:
                    find_and_update_table_cell(STAT_OVERVIEW, var_stem, value, pc_name=target_pc, verbose=verbose)
            
            updated_variables.add(var_stem)
    
    if updated_variables:
        print(f"\n{'='*70}")
        print(f"Updated {len(updated_variables)} variables")
        print('='*70)
    else:
        print("\nNo changes needed - all files are in sync")


def watch_mode(interval: int = 10, verbose: bool = False):
    """Run sync in watch mode, checking for changes every N seconds."""
    import time
    import hashlib
    
    def file_hash(path: Path) -> str:
        """Get hash of file contents to detect actual changes."""
        try:
            return hashlib.md5(path.read_bytes()).hexdigest()
        except Exception:
            return ""
    
    print(f"Starting watch mode (checking every {interval} seconds)")
    print("Press Ctrl+C to stop\n")
    
    # Track file content hashes instead of modification times
    tracked_files = {}
    
    # Initialize tracked_files with current state to avoid false detection on startup
    print("Initializing file tracking...")
    if STAT_OVERVIEW.exists():
        tracked_files[STAT_OVERVIEW] = file_hash(STAT_OVERVIEW)
    
    for pc_name in get_pc_list():
        sheet_path = get_character_sheet_path(pc_name)
        if sheet_path:
            tracked_files[sheet_path] = file_hash(sheet_path)
    
    if ENV_VARS_DIR.exists():
        for var_file in ENV_VARS_DIR.glob('*.md'):
            tracked_files[var_file] = file_hash(var_file)
    
    if PC_VARS_DIR.exists():
        for pc_dir in PC_VARS_DIR.iterdir():
            if pc_dir.is_dir():
                for var_file in pc_dir.glob('*.md'):
                    tracked_files[var_file] = file_hash(var_file)
    
    print(f"Tracking {len(tracked_files)} files. Watching for changes...\n")
    
    try:
        while True:
            # Check for file changes
            changed_files = []
            
            # Check stat_overview.md
            if STAT_OVERVIEW.exists():
                current_hash = file_hash(STAT_OVERVIEW)
                if STAT_OVERVIEW not in tracked_files or tracked_files[STAT_OVERVIEW] != current_hash:
                    changed_files.append(str(STAT_OVERVIEW.relative_to(ROOT)))
                    tracked_files[STAT_OVERVIEW] = current_hash
            
            # Check character sheets
            for pc_name in get_pc_list():
                sheet_path = get_character_sheet_path(pc_name)
                if sheet_path:
                    current_hash = file_hash(sheet_path)
                    if sheet_path not in tracked_files or tracked_files[sheet_path] != current_hash:
                        changed_files.append(str(sheet_path.relative_to(ROOT)))
                        tracked_files[sheet_path] = current_hash
            
            # Check environmental variable files
            if ENV_VARS_DIR.exists():
                for var_file in ENV_VARS_DIR.glob('*.md'):
                    current_hash = file_hash(var_file)
                    if var_file not in tracked_files or tracked_files[var_file] != current_hash:
                        changed_files.append(str(var_file.relative_to(ROOT)))
                        tracked_files[var_file] = current_hash
            
            # Check PC-specific variable files
            if PC_VARS_DIR.exists():
                for pc_dir in PC_VARS_DIR.iterdir():
                    if pc_dir.is_dir():
                        for var_file in pc_dir.glob('*.md'):
                            current_hash = file_hash(var_file)
                            if var_file not in tracked_files or tracked_files[var_file] != current_hash:
                                changed_files.append(str(var_file.relative_to(ROOT)))
                                tracked_files[var_file] = current_hash
            
            if changed_files:
                print(f"\n{'='*70}")
                print(f"Changes detected in {len(changed_files)} file(s)")
                for f in changed_files:
                    print(f"  - {f}")
                print('='*70)
                
                # Categorize what changed
                var_files_changed = any('variable/' in f for f in changed_files)
                sheet_files_changed = any(f.endswith('character sheet.md') or f.endswith('stat_overview.md') 
                                         for f in changed_files)
                
                # Determine sync direction:
                # - If BOTH variable AND sheet files changed: script just updated variable from sheet
                #   → Run variable-to-sheet sync to propagate the new value everywhere
                # - If ONLY variable files changed: user edited a variable file directly
                #   → Run variable-to-sheet sync
                # - If ONLY sheet files changed: user edited a sheet
                #   → Run sheet-to-variable sync
                
                if var_files_changed and sheet_files_changed:
                    # Both changed - this means script just updated variable from sheet edit
                    # Now propagate from variable files to ensure all locations sync
                    var_count = sync_from_variable_files(verbose=verbose)
                    if var_count == 0:
                        print("\nNo changes needed - all files are in sync")
                elif var_files_changed:
                    # Only variables changed - user edited variable files directly
                    var_count = sync_from_variable_files(verbose=verbose)
                    if var_count == 0:
                        print("\nNo changes needed - all files are in sync")
                else:
                    # Only sheets changed - user edited character sheets
                    sync_variables_direct_edit(verbose=verbose)
                
                # Update ALL file hashes after sync completes to reflect the new state
                if STAT_OVERVIEW.exists():
                    tracked_files[STAT_OVERVIEW] = file_hash(STAT_OVERVIEW)
                
                for pc_name in get_pc_list():
                    sheet_path = get_character_sheet_path(pc_name)
                    if sheet_path:
                        tracked_files[sheet_path] = file_hash(sheet_path)
                
                if ENV_VARS_DIR.exists():
                    for var_file in ENV_VARS_DIR.glob('*.md'):
                        tracked_files[var_file] = file_hash(var_file)
                
                if PC_VARS_DIR.exists():
                    for pc_dir in PC_VARS_DIR.iterdir():
                        if pc_dir.is_dir():
                            for var_file in pc_dir.glob('*.md'):
                                tracked_files[var_file] = file_hash(var_file)
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\nWatch mode stopped")


def main():
    """Run one-time sync or watch mode based on CLI options."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Direct sync - edit table cells in place')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print detailed information')
    parser.add_argument('--watch', '-w', action='store_true', help='Watch mode: continuously monitor for changes')
    parser.add_argument('--interval', '-i', type=int, default=10, help='Watch mode interval in seconds (default: 10)')
    
    args = parser.parse_args()
    
    if args.watch:
        watch_mode(interval=args.interval, verbose=args.verbose)
    else:
        sync_variables_direct_edit(verbose=args.verbose)


if __name__ == '__main__':
    main()
