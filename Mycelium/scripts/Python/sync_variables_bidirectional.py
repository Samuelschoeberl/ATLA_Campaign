#!/usr/bin/env python3
"""Bidirectional sync between character sheets and variable files.

This script parses variable values from character sheets and writes them back
to the individual variable files, maintaining the same naming logic as recreate_pcs.py.

Environmental variables are special: they are shared across all characters, so if
one character's sheet has a different value, all character sheets must be updated.
"""
from __future__ import annotations
from pathlib import Path
import re
import sys
from typing import Dict, Any, List, Optional, Set, Tuple

# Find repository root
_script_path = Path(__file__).resolve()
ROOT = _script_path
while ROOT.parent != ROOT:
    if (ROOT / '.git').exists():
        break
    ROOT = ROOT.parent
if not (ROOT / '.git').exists():
    ROOT = _script_path.parent.parent.parent

# Standard paths
PLAYER_ROOT = ROOT.joinpath('Player Root')
PC_STATS_TABLE = PLAYER_ROOT.joinpath('pc_primary_stats.md')
PCS_DIR = PLAYER_ROOT.joinpath('PCs')
STAT_OVERVIEW = PCS_DIR.joinpath('stat_overview.md')
VAR_ROOT = PLAYER_ROOT.joinpath('variable')
PC_VARS_DIR = VAR_ROOT.joinpath('PC_variables')
ENV_VARS_DIR = VAR_ROOT.joinpath('environmental')
SECONDARY_TEMPLATES_DIR = VAR_ROOT.joinpath('secondary_stat')


def pc_safe(name: str) -> str:
    """Convert a PC name to a safe filename component."""
    return re.sub(r"[^A-Za-z0-9_\-]", '_', name)


def normalize_name(n: str) -> str:
    """Normalize a variable name to lowercase with underscores."""
    return n.lower().replace('.', '_').replace(' ', '_')


def display_name_to_stem(display: str) -> str:
    """Convert a display name back to a variable stem.
    
    Example: "Environmental water charge" -> "environmental_water_charge"
    """
    # Handle special cases
    mapping = {
        'strength': 'str',
        'dexterity': 'dex',
        'constitution': 'con',
        'intelligence': 'int',
        'wisdom': 'wis',
        'charisma': 'cha',
        'hp': 'hp',
        'max hp': 'max_hp',
    }
    
    normalized = normalize_name(display)
    if normalized in mapping:
        return mapping[normalized]
    
    # Default: just normalize
    return normalized


def to_number(s: Any) -> Any:
    """Convert a string to a number if possible."""
    if s is None:
        return 0
    s = str(s).strip()
    if s == '':
        return 0
    s = s.replace(',', '')
    try:
        if '.' in s:
            return float(s)
        return int(s)
    except Exception:
        m = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
        if m:
            return float(m.group(0)) if '.' in m.group(0) else int(m.group(0))
    return 0


def load_environmental_tags() -> Dict[str, List[str]]:
    """Load tags for all secondary stat templates to identify environmental variables."""
    tag_map: Dict[str, List[str]] = {}
    if not SECONDARY_TEMPLATES_DIR.exists():
        return tag_map
    
    tag_re = re.compile(r"#[-\w]+")
    for p in SECONDARY_TEMPLATES_DIR.glob('*.md'):
        txt = p.read_text(encoding='utf-8')
        # Remove code blocks for tag extraction
        s = re.sub(r'(```|~~~).*?\1', '', txt, flags=re.S)
        tags = tag_re.findall(s)
        tags = [t.lower() for t in tags]
        seen: List[str] = []
        for t in tags:
            if t not in seen:
                seen.append(t)
        tag_map[p.stem.lower()] = seen
    
    # Also check environmental folder
    if ENV_VARS_DIR.exists():
        for p in ENV_VARS_DIR.glob('*.md'):
            txt = p.read_text(encoding='utf-8')
            s = re.sub(r'(```|~~~).*?\1', '', txt, flags=re.S)
            tags = tag_re.findall(s)
            tags = [t.lower() for t in tags]
            seen: List[str] = []
            for t in tags:
                if t not in seen:
                    seen.append(t)
            tag_map[p.stem.lower()] = seen
    
    return tag_map


def is_environmental_variable(var_stem: str, tag_map: Dict[str, List[str]]) -> bool:
    """Check if a variable is an environmental variable (shared across all PCs)."""
    norm_stem = normalize_name(var_stem)
    
    # Check if it starts with 'environmental_'
    if norm_stem.startswith('environmental_'):
        return True
    
    # Check tags for #environmental_variable or #environmental_variables
    if norm_stem in tag_map:
        tags = tag_map[norm_stem]
        return any(t in ('#environmental_variable', '#environmental_variables', '#environmental') 
                   for t in tags)
    
    # Check with 'environmental_' prefix
    env_stem = f'environmental_{norm_stem}'
    if env_stem in tag_map:
        tags = tag_map[env_stem]
        return any(t in ('#environmental_variable', '#environmental_variables', '#environmental') 
                   for t in tags)
    
    return False


def parse_character_sheet(sheet_path: Path) -> Dict[str, Any]:
    """Parse a character sheet and extract variable values from tables.
    
    Returns a dict mapping normalized variable names to their values.
    """
    if not sheet_path.exists():
        return {}
    
    txt = sheet_path.read_text(encoding='utf-8')
    variables: Dict[str, Any] = {}
    
    # Parse markdown tables: | key | value |
    table_row_pattern = re.compile(r'^\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|', re.MULTILINE)
    
    for match in table_row_pattern.finditer(txt):
        key_raw = match.group(1).strip()
        value_raw = match.group(2).strip()
        
        # Skip header rows and separator rows
        if key_raw.lower() in ('key', 'stat', 'variable', 'name', 'element', 'slot', 
                                'water charge type', 'initiative', 'movement'):
            continue
        if re.match(r'^-+$', key_raw) or re.match(r'^-+$', value_raw):
            continue
        if value_raw.lower() in ('value', 'amount', 'base', 'level', 'attack roll', 'dc'):
            continue
        
        # Convert display name to stem
        var_stem = display_name_to_stem(key_raw)
        
        # Parse the value
        # Check if it looks like a dice expression (keep as string)
        if re.search(r'\d+d\d+', value_raw, re.IGNORECASE):
            variables[var_stem] = value_raw
        else:
            # Try to convert to number
            variables[var_stem] = to_number(value_raw)
    
    return variables


def parse_stat_overview(overview_path: Path) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Parse the stat_overview.md file to extract environmental and PC-specific variables.
    
    Returns:
        (environmental_vars, pc_vars)
        - environmental_vars: Dict mapping var_stem to value
        - pc_vars: Dict mapping PC name to dict of {var_stem: value}
    """
    if not overview_path.exists():
        return {}, {}
    
    txt = overview_path.read_text(encoding='utf-8')
    environmental_vars: Dict[str, Any] = {}
    pc_vars: Dict[str, Dict[str, Any]] = {}
    
    # Parse markdown tables: | Key | Value | ... |
    lines = txt.splitlines()
    current_section = None
    current_pc = None
    
    for i, line in enumerate(lines):
        # Track sections
        if line.startswith('## Global environmental variables'):
            current_section = 'environmental'
            current_pc = None
        elif line.startswith('## Per-PC extracted stats'):
            current_section = 'per-pc'
            current_pc = None
        elif line.startswith('### ') and current_section == 'per-pc':
            # Extract PC name
            current_pc = line[4:].strip()
            if current_pc not in pc_vars:
                pc_vars[current_pc] = {}
        
        # Parse table rows
        if '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 3:
                continue
            
            # Skip header and separator rows
            if parts[1].lower() in ('name', 'key', 'stat', 'variable') or re.match(r'^-+$', parts[1]):
                continue
            
            key_raw = parts[1]
            value_raw = parts[2] if len(parts) > 2 else ''
            
            if not key_raw or not value_raw:
                continue
            
            # Process based on section
            if current_section == 'environmental':
                # Extract variable name from wikilink if present
                match = re.search(r'\[\[([^\]]+)\]\]', key_raw)
                if match:
                    var_stem = normalize_name(match.group(1))
                else:
                    var_stem = normalize_name(key_raw)
                
                # Parse value
                if re.search(r'\d+d\d+', value_raw, re.IGNORECASE):
                    environmental_vars[var_stem] = value_raw
                else:
                    environmental_vars[var_stem] = to_number(value_raw)
                    
            elif current_section == 'per-pc' and current_pc:
                # PC-specific variable
                var_stem = display_name_to_stem(key_raw)
                
                # Parse value
                if re.search(r'\d+d\d+', value_raw, re.IGNORECASE):
                    pc_vars[current_pc][var_stem] = value_raw
                else:
                    pc_vars[current_pc][var_stem] = to_number(value_raw)
    
    return environmental_vars, pc_vars


def get_pc_list() -> List[str]:
    """Get list of PC names from the primary stats table."""
    if not PC_STATS_TABLE.exists():
        return []
    
    txt = PC_STATS_TABLE.read_text(encoding='utf-8')
    lines = [l.rstrip() for l in txt.splitlines()]
    
    # Find the table
    for i in range(len(lines) - 1):
        if '|' in lines[i] and re.search(r"\|\s*-{1,}\s*\|", lines[i + 1]):
            # Found header and separator
            names = []
            j = i + 2
            while j < len(lines) and '|' in lines[j]:
                row = [c.strip() for c in lines[j].strip().strip('|').split('|')]
                if row:
                    # Extract name from first column (may be a wikilink)
                    name_cell = row[0]
                    m = re.search(r"\[\[([^\]]+)\]\]", name_cell)
                    if m:
                        names.append(m.group(1).strip())
                    elif name_cell.strip():
                        names.append(name_cell.strip())
                j += 1
            return names
    
    return []


def write_variable_file(pc_name: str, var_stem: str, value: Any, 
                         tags: List[str], is_environmental: bool = False) -> None:
    """Write a variable value to its file.
    
    Preserves existing tags from template files when updating environmental variables.
    
    Args:
        pc_name: Name of the PC (empty string for environmental variables)
        var_stem: Variable stem name (e.g., 'environmental_water_charge')
        value: Value to write
        tags: List of tags to include (will be merged with existing tags for env vars)
        is_environmental: If True, write to environmental folder instead
    """
    safe_name = pc_safe(pc_name)
    
    if is_environmental:
        # Environmental variables go in the environmental folder
        var_file = ENV_VARS_DIR.joinpath(f'{var_stem}.md')
        var_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Try to preserve existing tags from the template
        if var_file.exists():
            try:
                existing_content = var_file.read_text(encoding='utf-8')
                # Extract existing tags
                tag_pattern = re.compile(r'#[-\w]+')
                existing_tags = tag_pattern.findall(existing_content)
                # Merge with new tags, preserving order and removing duplicates
                all_tags = []
                seen = set()
                for t in existing_tags + tags:
                    t_lower = t.lower()
                    if t_lower not in seen:
                        all_tags.append(t)
                        seen.add(t_lower)
                tags = all_tags
            except Exception:
                # If we can't read existing file, just use provided tags
                pass
    else:
        # PC-specific variables go in PC_variables/<PC>/<PC>_<var>.md
        pc_var_dir = PC_VARS_DIR.joinpath(safe_name)
        pc_var_dir.mkdir(parents=True, exist_ok=True)
        var_file = pc_var_dir.joinpath(f'{safe_name}_{var_stem}.md')
    
    # Format tags
    tag_str = ' '.join(tags) if tags else '#variable'
    
    # Write the file without code fences (matching recreate_pcs.py format)
    content = f'{value}\n\n{tag_str}\n'
    var_file.write_text(content, encoding='utf-8')


def parse_variable_from_character_sheets(pc_names: Optional[List[str]] = None, 
                                          verbose: bool = False,
                                          auto_regenerate: bool = True) -> bool:
    """Parse variables from character sheets and write them to variable files.
    
    This is the reverse operation of recreate_pcs.py: it reads character sheets
    and updates the source variable files.
    
    IMPORTANT: Environmental variables are shared across all PCs. When this script
    detects different values for an environmental variable across character sheets,
    it will:
    1. Issue a warning showing all conflicting values
    2. Use the first value encountered
    3. Write that value to the environmental variable file
    4. Automatically regenerate ALL character sheets to sync the value (if auto_regenerate=True)
    
    Variable file naming follows recreate_pcs.py conventions:
    - PC variables: Player Root/variable/PC_variables/<PC>/<PC>_<variable_stem>.md
    - Environmental variables: Player Root/variable/environmental/<variable_stem>.md
    
    Args:
        pc_names: Optional list of PC names to process. If None, process all PCs.
        verbose: If True, print detailed information.
        auto_regenerate: If True (default), automatically regenerate all character sheets
                        when environmental variable conflicts are detected.
    
    Returns:
        True if character sheets were regenerated, False otherwise.
    """
    # Get list of all PCs if not specified
    if pc_names is None:
        pc_names = get_pc_list()
    
    if not pc_names:
        print("No PCs found to process")
        return False
    
    # Load environmental variable tags
    tag_map = load_environmental_tags()
    
    # Track environmental variables and their values across PCs
    env_vars: Dict[str, Dict[str, Any]] = {}  # var_stem -> {pc_name: value}
    
    # First, parse stat_overview.md if it exists
    stat_overview_time = 0
    if STAT_OVERVIEW.exists():
        stat_overview_time = STAT_OVERVIEW.stat().st_mtime
        if verbose:
            print(f"\nParsing stat_overview.md...")
        
        overview_env_vars, overview_pc_vars = parse_stat_overview(STAT_OVERVIEW)
        
        # Add environmental variables from overview
        for var_stem, value in overview_env_vars.items():
            if var_stem not in env_vars:
                env_vars[var_stem] = {}
            env_vars[var_stem]['stat_overview'] = value
            if verbose:
                print(f"  Found environmental variable in overview: {var_stem} = {value}")
        
        # Add PC variables from overview
        for pc_name, variables in overview_pc_vars.items():
            if verbose:
                print(f"  Found {len(variables)} variables for {pc_name} in overview")
            # These will be written as PC-specific variables later
    
    # Track which sources were used for environmental variables
    env_var_sources: Dict[str, Dict[str, float]] = {}  # var_stem -> {source: mtime}
    
    # Process each PC
    for pc_name in pc_names:
        safe_name = pc_safe(pc_name)
        sheet_path = PCS_DIR.joinpath(safe_name, f'{safe_name} character sheet.md')
        
        # Collect variables from stat_overview if available
        overview_vars = {}
        if STAT_OVERVIEW.exists() and pc_name in overview_pc_vars:
            overview_vars = overview_pc_vars[pc_name].copy()
        
        # Parse character sheet if it exists
        sheet_vars = {}
        sheet_time = 0
        if sheet_path.exists():
            sheet_time = sheet_path.stat().st_mtime
            sheet_vars = parse_character_sheet(sheet_path)
        
        if not sheet_path.exists() and not overview_vars:
            if verbose:
                print(f"No data found for {pc_name}")
            continue
        
        # Determine which source is more recent and merge variables
        variables = {}
        if sheet_time > stat_overview_time:
            # Character sheet is newer, prefer its values
            variables = sheet_vars.copy()
            # Add any variables from overview that aren't in sheet
            for k, v in overview_vars.items():
                if k not in variables:
                    variables[k] = v
            if verbose and sheet_path.exists():
                print(f"\nProcessing {pc_name} (character sheet more recent)...")
        else:
            # stat_overview is newer or equal, prefer its values
            variables = overview_vars.copy()
            # Add any variables from sheet that aren't in overview
            for k, v in sheet_vars.items():
                if k not in variables:
                    variables[k] = v
            if verbose and overview_vars:
                print(f"\nProcessing {pc_name} (stat_overview more recent)...")
        
        if verbose:
            print(f"  Found {len(variables)} variables")
        
        # Write variables to files
        for var_stem, value in variables.items():
            # Determine if this is an environmental variable
            is_env = is_environmental_variable(var_stem, tag_map)
            
            if is_env:
                # Track environmental variables for conflict detection
                # Do NOT write them to PC-specific folders
                if var_stem not in env_vars:
                    env_vars[var_stem] = {}
                env_vars[var_stem][pc_name] = value
                
                # Track the source and modification time
                if var_stem not in env_var_sources:
                    env_var_sources[var_stem] = {}
                
                # Determine which source this value came from
                if sheet_time > stat_overview_time and sheet_path.exists():
                    # Character sheet is the source
                    env_var_sources[var_stem][pc_name] = sheet_time
                else:
                    # stat_overview is the source - only record it once
                    if 'stat_overview' not in env_var_sources[var_stem]:
                        env_var_sources[var_stem]['stat_overview'] = stat_overview_time
                    # Also add this PC using stat_overview value
                    if pc_name not in env_vars[var_stem]:
                        env_vars[var_stem][pc_name] = value
                
                if verbose:
                    print(f"  Environmental variable (tracked): {var_stem} = {value}")
            else:
                # Write PC-specific variable immediately
                # Determine appropriate tags
                tags = ['#variable', f'#character_stat_{safe_name}', 
                        f'#character_stats_{safe_name}']
                
                write_variable_file(pc_name, var_stem, value, tags, is_environmental=False)
                
                if verbose:
                    print(f"  PC variable: {var_stem} = {value}")
    
    # Handle environmental variables
    needs_regeneration = False
    if env_vars:
        print(f"\nProcessing {len(env_vars)} environmental variables...")
        
        for var_stem, pc_values in env_vars.items():
            # Check if all PCs have the same value
            unique_values = set(pc_values.values())
            
            if len(unique_values) > 1:
                print(f"WARNING: Environmental variable '{var_stem}' has conflicting values:")
                for pc, val in pc_values.items():
                    print(f"  {pc}: {val}")
                
                # Determine which source was modified most recently
                most_recent_source = None
                most_recent_time = 0
                
                if var_stem in env_var_sources:
                    for source, mtime in env_var_sources[var_stem].items():
                        if mtime > most_recent_time:
                            most_recent_time = mtime
                            most_recent_source = source
                
                # Get the value from the most recent source
                if most_recent_source == 'stat_overview':
                    # Get the stat_overview value directly from env_vars
                    final_value = env_vars[var_stem]['stat_overview']
                    print(f"  Using value from most recently modified source (stat_overview.md): {final_value}")
                elif most_recent_source and most_recent_source in pc_values:
                    final_value = pc_values[most_recent_source]
                    print(f"  Using value from most recently modified source ({most_recent_source}): {final_value}")
                else:
                    # Fallback to first value if we can't determine modification times
                    final_value = list(pc_values.values())[0]
                    print(f"  Using value from first source: {final_value}")
                
                needs_regeneration = True
            else:
                # All values are the same, use any of them
                final_value = list(pc_values.values())[0]
            
            # Write to environmental folder
            tags = ['#variable', '#secondary_stat', '#template', '#environmental_variables']
            write_variable_file('', var_stem, final_value, tags, is_environmental=True)
            
            if verbose:
                print(f"  Wrote environmental variable: {var_stem} = {final_value}")
    
    # Automatically regenerate all character sheets if environmental variables changed
    if needs_regeneration and auto_regenerate:
        print("\n" + "="*70)
        print("Environmental variable conflicts detected!")
        print("Automatically regenerating ALL character sheets to sync values...")
        print("="*70 + "\n")
        
        # Clean up: Delete all PC-specific environmental variable files before regenerating
        # These files will be recreated by recreate_pcs.py with the correct values
        print("Cleaning up PC-specific environmental variable files...")
        try:
            for pc_dir in PC_VARS_DIR.iterdir():
                if pc_dir.is_dir():
                    for var_file in pc_dir.glob('*environmental*.md'):
                        try:
                            var_file.unlink()
                            if verbose:
                                print(f"  Deleted: {var_file.relative_to(ROOT)}")
                        except Exception:
                            pass
        except Exception as e:
            if verbose:
                print(f"Note: Could not clean up all environmental files: {e}")
        
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, str(ROOT.joinpath('Mycelium', 'scripts', 'Python', 'recreate_pcs.py'))],
                cwd=str(ROOT),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("\n✓ Character sheets regenerated successfully!")
                if verbose:
                    print(result.stdout)
            else:
                print("\n✗ Error regenerating character sheets:")
                print(result.stderr)
                return False
        except Exception as e:
            print(f"\n✗ Failed to regenerate character sheets: {e}")
            print("Please run manually: python3 Mycelium/scripts/Python/recreate_pcs.py")
            return False
    elif needs_regeneration and not auto_regenerate:
        print("\n" + "="*70)
        print("Environmental variable conflicts detected!")
        print("Auto-regeneration disabled. Please run manually:")
        print("  python3 Mycelium/scripts/Python/recreate_pcs.py")
        print("="*70 + "\n")
    
    return needs_regeneration


def watch_mode(interval: int = 10, verbose: bool = False, auto_regenerate: bool = True) -> None:
    """Continuously monitor character sheets and stat_overview.md for changes.
    
    Args:
        interval: Number of seconds between checks
        verbose: If True, print detailed information
        auto_regenerate: If True, automatically regenerate sheets on conflicts
    """
    print("="*70)
    print("WATCH MODE: Monitoring character sheets and stat_overview.md for changes...")
    print(f"Checking every {interval} seconds. Press Ctrl+C to stop.")
    print("="*70)
    print()
    
    # Track modification times for all monitored files
    last_mtimes: Dict[str, float] = {}
    
    def get_current_mtimes() -> Dict[str, float]:
        """Get modification times for all monitored files."""
        mtimes = {}
        
        # Monitor stat_overview.md
        if STAT_OVERVIEW.exists():
            mtimes[str(STAT_OVERVIEW)] = STAT_OVERVIEW.stat().st_mtime
        
        # Monitor all character sheets
        pc_names = get_pc_list()
        for pc_name in pc_names:
            safe_name = pc_safe(pc_name)
            sheet_path = PCS_DIR.joinpath(safe_name, f'{safe_name} character sheet.md')
            if sheet_path.exists():
                mtimes[str(sheet_path)] = sheet_path.stat().st_mtime
        
        return mtimes
    
    # Initialize with current modification times
    last_mtimes = get_current_mtimes()
    
    try:
        while True:
            import time
            time.sleep(interval)
            
            # Check for changes
            current_mtimes = get_current_mtimes()
            changed_files = []
            
            for filepath, mtime in current_mtimes.items():
                if filepath not in last_mtimes or last_mtimes[filepath] < mtime:
                    changed_files.append(filepath)
            
            # Check for new files
            for filepath in current_mtimes:
                if filepath not in last_mtimes:
                    changed_files.append(filepath)
            
            if changed_files:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{timestamp}] Changes detected!")
                
                # Show which files changed
                for filepath in changed_files:
                    path = Path(filepath)
                    if path.name == 'stat_overview.md':
                        print(f"  Modified: stat_overview.md")
                    else:
                        # Extract PC name from path
                        pc_name = path.parent.name
                        print(f"  Modified: {pc_name}")
                
                print("\nSyncing variables...")
                regenerated = parse_variable_from_character_sheets(
                    pc_names=None,
                    verbose=verbose,
                    auto_regenerate=auto_regenerate
                )
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{timestamp}] Sync complete!")
                if regenerated:
                    print("All character sheets have been updated with synchronized environmental variables.")
                print()
                
                # Update last known modification times
                last_mtimes = get_current_mtimes()
            
    except KeyboardInterrupt:
        print("\n\nWatch mode stopped by user.")
        print("Exiting...")
        return


def main():
    """Main entry point for the script."""
    import argparse
    import time
    from datetime import datetime
    
    parser = argparse.ArgumentParser(
        description='Parse variables from character sheets and update variable files'
    )
    parser.add_argument('--pc', '-p', type=str, 
                        help='Process only this PC (by name)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print detailed processing information')
    parser.add_argument('--no-auto-regenerate', action='store_true',
                        help='Disable automatic regeneration of character sheets when '
                             'environmental variable conflicts are detected')
    parser.add_argument('--watch', '-w', action='store_true',
                        help='Watch for changes and sync automatically every 10 seconds')
    parser.add_argument('--interval', '-i', type=int, default=10,
                        help='Watch interval in seconds (default: 10)')
    
    args = parser.parse_args()
    
    pc_names = None
    if args.pc:
        pc_names = [args.pc]
    
    if args.watch:
        # Run in watch mode
        watch_mode(
            interval=args.interval,
            verbose=args.verbose,
            auto_regenerate=not args.no_auto_regenerate
        )
    else:
        # Single run mode
        regenerated = parse_variable_from_character_sheets(
            pc_names=pc_names, 
            verbose=args.verbose,
            auto_regenerate=not args.no_auto_regenerate
        )
        
        print("\nSync complete!")
        if regenerated:
            print("All character sheets have been updated with synchronized environmental variables.")


if __name__ == '__main__':
    main()
