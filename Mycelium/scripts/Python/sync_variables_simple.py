#!/usr/bin/env python3
"""
Simple bidirectional sync between variable files and character sheets/stat_overview.md

CORE PRINCIPLE: Variable files are the canonical source of truth.
This script compares source files (character sheets, stat_overview.md) with variable files
and only updates variable files when the source is newer.

When environmental variable conflicts are detected, it regenerates all character sheets.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

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
            # Convert safe name back to display name
            name = item.name.replace('_', ' ')
            pc_names.append(name)
    return sorted(pc_names)


def display_name_to_stem(display_name: str) -> str:
    """Convert display name to variable stem."""
    return display_name.lower().replace(' ', '_').replace('-', '_')


def parse_character_sheet(sheet_path: Path) -> Dict[str, Any]:
    """Parse variables from a character sheet markdown file."""
    if not sheet_path.exists():
        return {}
    
    content = sheet_path.read_text(encoding='utf-8')
    variables = {}
    
    # Pattern for markdown tables
    table_pattern = re.compile(
        r'\|([^|]+)\|([^|]+)\|',
        re.MULTILINE
    )
    
    for match in table_pattern.finditer(content):
        left = match.group(1).strip()
        right = match.group(2).strip()
        
        # Skip invalid keys
        if not left:  # Empty
            continue
        if left.startswith('-'):  # Table separator
            continue
        if left.lower() in ['stat', 'ability', 'key', 'name', 'value']:  # Header rows
            continue
        if left.startswith('#'):  # Markdown headers
            continue
        if left.isdigit():  # Just numbers (like "0", "1", "2")
            continue
        if all(c in '-_:| ' for c in left):  # Just punctuation
            continue
        if left.startswith('##'):  # Section headers
            continue
        
        # Skip invalid values
        if not right or all(c in '-_:| ' for c in right):
            continue
        
        # Try to parse the value
        try:
            if right.isdigit() or (right.startswith('-') and right[1:].isdigit()):
                value = int(right)
            elif '.' in right:
                try:
                    value = float(right)
                except ValueError:
                    value = right
            else:
                value = right
            
            var_stem = display_name_to_stem(left)
            
            # Final sanity check on var_stem
            if len(var_stem) < 2:  # Too short
                continue
            if var_stem.isdigit():  # Still just a number
                continue
            
            variables[var_stem] = value
            
        except Exception:
            continue
    
    return variables


def parse_stat_overview(overview_path: Path) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """
    Parse stat_overview.md file.
    Returns: (environmental_vars, pc_vars)
    """
    if not overview_path.exists():
        return {}, {}
    
    content = overview_path.read_text(encoding='utf-8')
    environmental_vars = {}
    pc_vars = {}
    
    # Split into sections
    sections = re.split(r'^##\s+', content, flags=re.MULTILINE)
    
    for section in sections:
        if not section.strip():
            continue
        
        lines = section.split('\n')
        header = lines[0].strip()
        
        if 'global environmental' in header.lower():
            # Parse environmental variables table
            for line in lines[1:]:
                if '|' in line and not line.strip().startswith('|--'):
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 2:
                        key = parts[0]
                        
                        # Skip invalid keys
                        if key.lower() in ['name', 'stat', 'key', 'value', 'tags', 'file']:
                            continue
                        if key.startswith('-') or key.startswith('#'):
                            continue
                        if key.isdigit() or all(c in '-_:| ' for c in key):
                            continue
                        
                        var_stem = display_name_to_stem(key)
                        
                        # Skip if var_stem is too short or invalid
                        if len(var_stem) < 2 or var_stem.isdigit():
                            continue
                        
                        try:
                            value = int(parts[1]) if parts[1].isdigit() else parts[1]
                            environmental_vars[var_stem] = value
                        except Exception:
                            pass
        
        elif header.startswith('Per-PC') or any(pc in header for pc in get_pc_list()):
            # Check for PC name in subsections
            pc_pattern = re.compile(r'^###\s+(.+)$', re.MULTILINE)
            current_pc = None
            
            for line in lines[1:]:
                pc_match = pc_pattern.match(line)
                if pc_match:
                    current_pc = pc_match.group(1).strip()
                    if current_pc not in pc_vars:
                        pc_vars[current_pc] = {}
                elif current_pc and '|' in line and not line.strip().startswith('|--'):
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 2:
                        key = parts[0]
                        
                        # Skip invalid keys
                        if key.lower() in ['stat', 'key', 'name', 'value', 'source file', 'file']:
                            continue
                        if key.startswith('-') or key.startswith('#') or key.startswith('**'):
                            continue
                        if key.isdigit() or all(c in '-_:| ' for c in key):
                            continue
                        
                        var_stem = display_name_to_stem(key)
                        
                        # Skip if var_stem is too short or invalid
                        if len(var_stem) < 2 or var_stem.isdigit():
                            continue
                        
                        try:
                            value = int(parts[1]) if parts[1].isdigit() else parts[1]
                            pc_vars[current_pc][var_stem] = value
                        except Exception:
                            pass
    
    return environmental_vars, pc_vars


def is_environmental_variable(var_stem: str, variable_file_path: Optional[Path] = None) -> bool:
    """
    Check if a variable is environmental by checking if it exists in the environmental directory.
    Environmental variables are shared across all PCs and stored in Player Root/variable/environmental/
    """
    # ONLY check if file exists in environmental directory
    # This is the canonical way to determine if a variable is environmental
    return ENV_VARS_DIR.joinpath(f'{var_stem}.md').exists()


def get_variable_file_path(pc_name: str, var_stem: str, is_environmental: bool) -> Path:
    """Get the path to a variable file."""
    if is_environmental:
        return ENV_VARS_DIR.joinpath(f'{var_stem}.md')
    else:
        safe_name = pc_safe(pc_name)
        return PC_VARS_DIR.joinpath(safe_name, f'{safe_name}_{var_stem}.md')


def get_variable_file_time(var_file: Path) -> float:
    """Get modification time of variable file, or 0 if doesn't exist."""
    return var_file.stat().st_mtime if var_file.exists() else 0


def write_variable_file(var_file: Path, value: Any, tags: List[str]):
    """Write a variable file."""
    var_file.parent.mkdir(parents=True, exist_ok=True)
    tag_str = ' '.join(tags) if tags else '#variable'
    content = f'{value}\n\n{tag_str}\n'
    var_file.write_text(content, encoding='utf-8')


def update_table_cell_value(file_path: Path, var_stem: str, new_value: Any, display_name: Optional[str] = None) -> bool:
    """
    Update a specific table cell value in a markdown file.
    Looks for a table row with the variable name and updates its value.
    
    Args:
        file_path: Path to the markdown file
        var_stem: Variable stem to search for (e.g., 'environmental_water_charge', 'max_hp')
        new_value: New value to write
        display_name: Optional display name to match (e.g., 'Environmental water charge')
    
    Returns:
        True if updated, False if not found
    """
    if not file_path.exists():
        return False
    
    content = file_path.read_text(encoding='utf-8')
    lines = content.splitlines()
    updated = False
    
    # Build search patterns
    search_patterns = [var_stem.lower()]
    if display_name:
        search_patterns.append(display_name.lower())
    # Also try with spaces
    search_patterns.append(var_stem.replace('_', ' ').lower())
    
    for i, line in enumerate(lines):
        # Check if this is a table row
        if '|' not in line:
            continue
        
        # Parse table row
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 3:  # Need at least empty|key|value|empty
            continue
        
        # Extract key (usually second column) and value position
        key = parts[1].lower() if len(parts) > 1 else ''
        
        # Check if this row matches our variable
        matches = False
        for pattern in search_patterns:
            if pattern in key or key in pattern:
                matches = True
                break
        
        # Also check for wikilinks [[variable_name]]
        if '[[' in parts[1] and ']]' in parts[1]:
            wiki_content = parts[1][parts[1].find('[[')+2:parts[1].find(']]')].lower()
            if var_stem.lower() in wiki_content or wiki_content in var_stem.lower():
                matches = True
        
        if matches:
            # Found the row - update the value column (usually third column, index 2)
            if len(parts) > 2:
                # Preserve the original spacing and structure
                old_value = parts[2]
                parts[2] = str(new_value).rjust(len(old_value)) if old_value.strip().isdigit() else f' {new_value}'
                
                # Reconstruct the line
                lines[i] = '|' + '|'.join(parts[1:-1]) + '|'
                updated = True
                break
    
    if updated:
        file_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return True
    
    return False


def sync_variables(verbose: bool = False, auto_regenerate: bool = True) -> bool:
    """
    Sync variables from character sheets and stat_overview.md to variable files.
    Only updates variable files when source files are newer.
    
    Returns True if character sheets were regenerated.
    """
    print("="*70)
    print("SYNCING VARIABLES (Variable files are canonical truth)")
    print("="*70)
    
    pc_names = get_pc_list()
    if not pc_names:
        print("No PCs found")
        return False
    
    # Parse stat_overview.md
    stat_overview_time = get_variable_file_time(STAT_OVERVIEW)
    overview_env_vars, overview_pc_vars = parse_stat_overview(STAT_OVERVIEW)
    
    if verbose and STAT_OVERVIEW.exists():
        print(f"\nstat_overview.md modified: {stat_overview_time}")
        print(f"  {len(overview_env_vars)} environmental variables")
        print(f"  {len(overview_pc_vars)} PCs with variables")
    
    # Track environmental variable updates
    env_var_updates = {}  # var_stem -> {source_name: (value, source_time, var_file_time)}
    any_variable_updated = False  # Track if ANY variable file was updated
    
    # Add global environmental variables from stat_overview.md
    for var_stem, value in overview_env_vars.items():
        var_file = ENV_VARS_DIR.joinpath(f'{var_stem}.md')
        
        # ONLY process if the variable file already exists
        if not var_file.exists():
            if verbose:
                print(f"Skipping environmental variable {var_stem}: no variable file exists")
            continue
        
        var_file_time = get_variable_file_time(var_file)
        
        if var_stem not in env_var_updates:
            env_var_updates[var_stem] = {}
        env_var_updates[var_stem]['stat_overview'] = (value, stat_overview_time, var_file_time)
        
        if verbose:
            print(f"Tracking environmental variable from stat_overview: {var_stem} = {value}")
    
    # Process each PC
    for pc_name in pc_names:
        if verbose:
            print(f"\n{'='*50}")
            print(f"Processing: {pc_name}")
            print('='*50)
        
        safe_name = pc_safe(pc_name)
        sheet_path = PCS_DIR.joinpath(safe_name, f'{safe_name} character sheet.md')
        sheet_time = get_variable_file_time(sheet_path)
        
        # Parse character sheet
        sheet_vars = parse_character_sheet(sheet_path) if sheet_path.exists() else {}
        overview_vars = overview_pc_vars.get(pc_name, {})
        
        # Combine variables
        all_vars = {}
        all_vars.update(sheet_vars)
        all_vars.update(overview_vars)
        
        if verbose:
            print(f"Character sheet: {len(sheet_vars)} variables (mtime: {sheet_time})")
            print(f"stat_overview: {len(overview_vars)} variables")
        
        # Process each variable
        for var_stem, value in all_vars.items():
            is_env = is_environmental_variable(var_stem)
            var_file = get_variable_file_path(pc_name, var_stem, is_env)
            
            # ONLY process variables that already have a variable file
            # Never create new variable files - only update existing ones
            if not var_file.exists():
                if verbose:
                    print(f"  - Skipped {var_stem}: no variable file exists (not creating new files)")
                continue
            
            var_file_time = get_variable_file_time(var_file)
            
            # Determine source time (which file this value came from)
            if var_stem in sheet_vars and var_stem in overview_vars:
                # Both have it - use more recent
                source_time = max(sheet_time, stat_overview_time)
                source_name = f'{pc_name}_sheet' if sheet_time > stat_overview_time else 'stat_overview'
            elif var_stem in sheet_vars:
                source_time = sheet_time
                source_name = f'{pc_name}_sheet'
            else:
                source_time = stat_overview_time
                source_name = 'stat_overview'
            
            if is_env:
                # Track environmental variables
                if var_stem not in env_var_updates:
                    env_var_updates[var_stem] = {}
                env_var_updates[var_stem][source_name] = (value, source_time, var_file_time)
            else:
                # Update PC-specific variable if source is newer
                if source_time > var_file_time:
                    tags = ['#variable', f'#character_stat_{safe_name}', f'#character_stats_{safe_name}']
                    write_variable_file(var_file, value, tags)
                    any_variable_updated = True  # Mark that we updated a variable
                    if verbose:
                        print(f"  ✓ Updated {var_stem}: {value} (source newer: {source_time} > {var_file_time})")
                elif verbose:
                    print(f"  - Skipped {var_stem}: variable file is current")
    
    # Process environmental variables
    if env_var_updates:
        print(f"\n{'='*70}")
        print(f"Processing {len(env_var_updates)} environmental variables")
        print('='*70)
        
        needs_regeneration = False
        
        for var_stem, sources in env_var_updates.items():
            # Get the environmental variable file
            var_file = ENV_VARS_DIR.joinpath(f'{var_stem}.md')
            var_file_time = get_variable_file_time(var_file)
            
            # Check for conflicts (different values from different sources)
            unique_values = set(v[0] for v in sources.values())
            
            if len(unique_values) > 1:
                print(f"\n⚠ CONFLICT: {var_stem}")
                for source, (value, source_time, _) in sources.items():
                    print(f"  {source}: {value} (mtime: {source_time})")
                
                # Use value from most recent source
                most_recent_source = max(sources.items(), key=lambda x: x[1][1])
                final_value = most_recent_source[1][0]
                final_time = most_recent_source[1][1]
                
                print(f"  → Using {most_recent_source[0]}: {final_value}")
                
                # Only trigger regeneration if we're actually changing the variable file
                if final_time > var_file_time:
                    needs_regeneration = True
            else:
                # All sources agree
                final_value = next(iter(sources.values()))[0]
                final_time = max(v[1] for v in sources.values())
            
            # Update variable file if any source is newer
            if final_time > var_file_time:
                tags = ['#variable', '#secondary_stat', '#template', '#environmental_variables']
                write_variable_file(var_file, final_value, tags)
                any_variable_updated = True  # Mark that we updated a variable
                print(f"  ✓ Updated {var_stem}: {final_value}")
            elif verbose:
                print(f"  - Skipped {var_stem}: variable file is current")
        
        # Regenerate character sheets if conflicts detected
        if needs_regeneration and auto_regenerate:
            print("\n" + "="*70)
            print("REGENERATING ALL CHARACTER SHEETS")
            print("="*70)
            
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
                else:
                    print("\n✗ Error regenerating character sheets:")
                    print(result.stderr)
            except Exception as e:
                print(f"\n✗ Failed to regenerate: {e}")
    
    # Regenerate stat_overview.md if ANY variable file was updated
    if any_variable_updated:
        print("\n" + "="*70)
        print("REGENERATING stat_overview.md")
        print("="*70)
        
        try:
            import subprocess
            result_overview = subprocess.run(
                [sys.executable, str(ROOT.joinpath('Mycelium', 'scripts', 'Python', 'generate_stat_overview.py'))],
                cwd=str(ROOT),
                capture_output=True,
                text=True
            )
            
            if result_overview.returncode == 0:
                print("✓ stat_overview.md updated successfully!")
            else:
                print("⚠ Warning: Could not update stat_overview.md")
                if verbose:
                    print(result_overview.stderr)
        except Exception as e:
            print(f"⚠ Warning: Failed to regenerate stat_overview.md: {e}")
    
    return needs_regeneration


def watch_mode(interval: int = 10, verbose: bool = False):
    """Run sync in watch mode, checking for changes every N seconds."""
    import time
    
    print(f"Starting watch mode (checking every {interval} seconds)")
    print("Press Ctrl+C to stop\n")
    
    # Track file modification times
    tracked_files = {}
    
    try:
        while True:
            # Check for file changes
            changed_files = []
            
            # Check stat_overview.md
            if STAT_OVERVIEW.exists():
                current_time = STAT_OVERVIEW.stat().st_mtime
                if STAT_OVERVIEW not in tracked_files or tracked_files[STAT_OVERVIEW] != current_time:
                    changed_files.append(str(STAT_OVERVIEW.relative_to(ROOT)))
                    tracked_files[STAT_OVERVIEW] = current_time
            
            # Check character sheets
            for pc_name in get_pc_list():
                safe_name = pc_safe(pc_name)
                sheet_path = PCS_DIR.joinpath(safe_name, f'{safe_name} character sheet.md')
                if sheet_path.exists():
                    current_time = sheet_path.stat().st_mtime
                    if sheet_path not in tracked_files or tracked_files[sheet_path] != current_time:
                        changed_files.append(str(sheet_path.relative_to(ROOT)))
                        tracked_files[sheet_path] = current_time
            
            if changed_files:
                print(f"\n{'='*70}")
                print(f"Changes detected in {len(changed_files)} file(s)")
                for f in changed_files:
                    print(f"  - {f}")
                print('='*70)
                
                # Run sync
                regenerated = sync_variables(verbose=verbose)
                
                if regenerated:
                    print("\nCharacter sheets were regenerated - updating tracked times...")
                    # Re-track all character sheets since they were just regenerated
                    for pc_name in get_pc_list():
                        safe_name = pc_safe(pc_name)
                        sheet_path = PCS_DIR.joinpath(safe_name, f'{safe_name} character sheet.md')
                        if sheet_path.exists():
                            tracked_files[sheet_path] = sheet_path.stat().st_mtime
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\nWatch mode stopped")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Sync variables between character sheets and variable files')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print detailed information')
    parser.add_argument('--no-regenerate', action='store_true', help='Do not auto-regenerate character sheets')
    parser.add_argument('--watch', '-w', action='store_true', help='Watch mode: continuously monitor for changes')
    parser.add_argument('--interval', '-i', type=int, default=10, help='Watch mode interval in seconds (default: 10)')
    
    args = parser.parse_args()
    
    if args.watch:
        watch_mode(interval=args.interval, verbose=args.verbose)
    else:
        sync_variables(verbose=args.verbose, auto_regenerate=not args.no_regenerate)


if __name__ == '__main__':
    main()
