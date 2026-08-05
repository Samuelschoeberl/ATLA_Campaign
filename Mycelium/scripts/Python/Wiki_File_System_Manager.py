#!/usr/bin/env python3
"""
Wiki_File_System_Manager.py - Bulk Find & Replace for Markdown Files

This script provides bulk find & replace operations across markdown files
in a directory tree structure. Designed for Obsidian vaults and wiki-style
folder hierarchies.

Features:
  - Recursive find & replace in markdown files
  - Optional bracketing mode for Obsidian wiki-links [[...]]
  - Dry-run and backup support
  - Case-sensitive/insensitive search
  - Directory exclusion patterns
  - Color-coded output

Author: Samuel Schoberl (2025)
"""

import argparse
import os
import re
import sys
from pathlib import Path
from shutil import copy2
from typing import Iterator, List, Optional, Sequence, Tuple

# Default directories to exclude from scanning
DEFAULT_EXCLUDES = {".git", "node_modules", ".obsidian", "__pycache__", "venv", ".venv", "backups"}

# ANSI color codes for terminal output
class Colors:
    """ANSI escape sequences grouped for readability when printing."""
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"


def colorize(enabled: bool, text: str, *effects: str) -> str:
    """Wrap text in ANSI color codes if enabled."""
    if not enabled or not effects:
        return text
    return "".join(effects) + text + Colors.RESET


def iter_markdown_files(
    roots: Sequence[Path],
    exclude_dirs: Sequence[str],
    use_default_excludes: bool,
    follow_symlinks: bool,
) -> Iterator[Path]:
    """
    Recursively yield markdown files under the given root directories.
    
    Args:
        roots: List of root directories to scan
        exclude_dirs: Directory names to exclude
        use_default_excludes: Whether to use built-in excludes
        follow_symlinks: Whether to follow symlinks
        
    Yields:
        Path objects for each .md file found
    """
    excludes = set(exclude_dirs)
    if use_default_excludes:
        excludes |= DEFAULT_EXCLUDES

    for root in roots:
        if root.is_file():
            # Single file specified
            if root.suffix.lower() == '.md':
                yield root
            continue

        for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
            # Prune excluded directories
            dirnames[:] = [d for d in dirnames if d not in excludes]
            
            # Yield markdown files
            for filename in filenames:
                if filename.lower().endswith('.md'):
                    yield Path(dirpath) / filename


def load_text(path: Path) -> Optional[str]:
    """Load text from file, returning None on failure."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[warn] Failed to read {path}: {e}", file=sys.stderr)
        return None


def write_text_with_backup(
    path: Path,
    content: str,
    backup_suffix: Optional[str],
    color: bool
) -> None:
    """Write content to file, optionally creating a backup first."""
    if backup_suffix:
        try:
            backup_path = path.with_suffix(path.suffix + backup_suffix)
            copy2(path, backup_path)
            if color:
                print(f"{colorize(color, '[backup]', Colors.DIM)} {backup_path}")
        except Exception as e:
            print(f"[warn] Failed to create backup for {path}: {e}", file=sys.stderr)

    try:
        path.write_text(content, encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] Failed to write to {path}: {e}", file=sys.stderr)


def make_replacer(
    needle: str,
    replacement: Optional[str],
    case_sensitive: bool,
    bracket_mode: bool,
) -> Tuple[re.Pattern, str]:
    """
    Build a regex pattern and replacement for find/replace.
    
    Args:
        needle: Text to search for
        replacement: Text to replace with (ignored if bracket_mode=True)
        case_sensitive: Whether search is case-sensitive
        bracket_mode: If True, wrap matches with [[...]] instead of replacing
        
    Returns:
        Tuple of (compiled regex pattern, replacement string or function)
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    escaped = re.escape(needle)

    if bracket_mode:
        # Match the needle, but only wrap if not already inside brackets
        # and neighbors are not alphanumeric
        pattern = re.compile(escaped, flags)
        
        def repl_func(match):
            """Wrap the matched text in [[...]] unless it is already linked."""
            s = match.string
            start, end = match.start(), match.end()
            
            # Check left neighbor
            if start > 0 and s[start-1].isalpha():
                return match.group(0)
            
            # Check right neighbor
            if end < len(s) and s[end].isalpha():
                return match.group(0)
            
            # Check if already inside wiki-link brackets [[...]]
            left = s.rfind('[[', 0, start)
            right = s.find(']]', end)
            
            if left != -1 and right != -1:
                # Ensure no ]] between [[ and match, and no [[ between match and ]]
                if s.find(']]', left, start) == -1 and s.find('[[', end, right) == -1:
                    return match.group(0)  # Already inside a link
            
            return f"[[{match.group(0)}]]"
        
        return pattern, repl_func

    # Normal replacement mode
    pattern = re.compile(escaped, flags)
    return pattern, replacement or ""


def process_file(
    path: Path,
    pattern: re.Pattern,
    repl,
) -> Tuple[int, Optional[str]]:
    """
    Apply the regex pattern and replacement to the file's content.
    
    Args:
        path: File to process
        pattern: Compiled regex pattern
        repl: Replacement string or function
        
    Returns:
        Tuple of (number of replacements, new content or None if unchanged)
    """
    text = load_text(path)
    if text is None:
        return 0, None
    
    # Apply substitution
    if callable(repl):
        new_text, n = pattern.subn(repl, text)
    else:
        new_text, n = pattern.subn(repl, text)
    
    if n == 0:
        return 0, None
    
    return n, new_text


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Bulk find & replace in markdown files across a directory tree.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Replace 'oldname' with 'newname' in all markdown files
  %(prog)s /path/to/wiki --find oldname --replace newname
  
  # Bracket all instances of 'Earthbending' (create wiki-links)
  %(prog)s /path/to/wiki --find Earthbending --bracket
  
  # Dry-run with backup suffix
  %(prog)s . --find foo --replace bar --dry-run --backup .bak
  
  # Case-sensitive search excluding specific directories
  %(prog)s . --find TODO --replace DONE --case-sensitive --exclude-dir archive old
        """
    )
    
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Root paths to scan (defaults to current directory)",
    )
    
    parser.add_argument(
        "--find",
        required=True,
        help="Text to search for (case-insensitive by default)",
    )
    
    parser.add_argument(
        "--replace",
        help="Replacement text (required unless --bracket is used)",
    )
    
    parser.add_argument(
        "-b", "--bracket",
        action="store_true",
        help="Bracketing mode: wrap matches with [[...]] instead of replacing",
    )
    
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Make search case-sensitive (default is case-insensitive)",
    )
    
    parser.add_argument(
        "--exclude-dir",
        nargs="*",
        default=[],
        help="Directory names to exclude (in addition to defaults)",
    )
    
    parser.add_argument(
        "--no-default-excludes",
        action="store_true",
        help=f"Do not exclude default directories: {', '.join(sorted(DEFAULT_EXCLUDES))}",
    )
    
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Follow symbolic links to directories",
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files",
    )
    
    parser.add_argument(
        "--backup",
        default=None,
        metavar="SUFFIX",
        help="Backup suffix (e.g., .bak) - backup created only if file is modified",
    )
    
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Compact, color-coded output",
    )
    
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors",
    )

    args = parser.parse_args(argv)

    # Validation
    if not args.bracket and args.replace is None:
        parser.error("--replace is required unless --bracket is used")

    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main entry point for the script."""
    args = parse_args(argv)
    
    # Determine color usage
    color_enabled = (
        sys.stdout.isatty() 
        and os.environ.get("NO_COLOR") is None 
        and not args.no_color
    )
    
    # Resolve root paths
    roots = [Path(p).resolve() for p in args.paths]
    
    # Build pattern and replacement
    pattern, repl = make_replacer(
        needle=args.find,
        replacement=args.replace,
        case_sensitive=args.case_sensitive,
        bracket_mode=args.bracket,
    )
    
    # Collect markdown files
    markdown_files = list(iter_markdown_files(
        roots=roots,
        exclude_dirs=args.exclude_dir,
        use_default_excludes=not args.no_default_excludes,
        follow_symlinks=args.follow_symlinks,
    ))
    
    if not markdown_files:
        print("No markdown files found.")
        return 0
    
    # Process files
    total_changes = 0
    changed_files: List[Tuple[Path, int]] = []
    
    for f in markdown_files:
        n, new_text = process_file(f, pattern, repl)
        
        if n > 0 and new_text is not None:
            changed_files.append((f, n))
            total_changes += n
            
            if args.compact:
                tag = "DRY" if args.dry_run else "WRITE"
                tag_color = Colors.CYAN if args.dry_run else Colors.GREEN
                print(
                    f"{colorize(color_enabled, '[' + tag + ']', tag_color)} "
                    f"{colorize(color_enabled, str(f), Colors.BOLD)} "
                    f"{colorize(color_enabled, '(' + str(n) + ')', Colors.GRAY)}"
                )
            else:
                mode = "dry-run" if args.dry_run else "write"
                print(f"[{mode}] {f} -> {n} replacement(s)")
            
            # Write changes
            if not args.dry_run:
                write_text_with_backup(f, new_text, args.backup, color_enabled)
    
    # Print summary
    if args.compact:
        mode = "DRY" if args.dry_run else "APPLIED"
        mode_color = Colors.BLUE if args.dry_run else Colors.GREEN
        parts = [
            colorize(color_enabled, "Summary:", Colors.BOLD),
            colorize(color_enabled, mode, mode_color),
            f"files={len(markdown_files)}",
            f"changed={len(changed_files)}",
            f"repl={total_changes}",
        ]
        if not args.dry_run and args.backup:
            parts.append(f"backup={args.backup}")
        print(" ".join(parts))
    else:
        mode = "DRY-RUN (no writes)" if args.dry_run else "APPLIED (writes performed)"
        print(f"\n=== Summary ===")
        print(f"Mode: {mode}")
        print(f"Files scanned: {len(markdown_files)}")
        print(f"Files changed: {len(changed_files)}")
        print(f"Total replacements: {total_changes}")
        
        if not args.dry_run and args.backup:
            print(f"Backup suffix used: {args.backup}")
        
        if changed_files:
            print("\nChanged files (up to 10 shown):")
            for f, n in changed_files[:10]:
                print(f"  {f} ({n})")
            if len(changed_files) > 10:
                print(f"  ... and {len(changed_files) - 10} more")
        else:
            print("No changes made.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
