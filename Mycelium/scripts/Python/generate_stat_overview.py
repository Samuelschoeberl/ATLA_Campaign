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
]

ENV_HINT = re.compile(r"environmental[_\.\s]?water[_\.\s]?charge", re.I)


def row_to_kv(line: str):
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


def gather_pc_stats():
    """Gather PC stats from Player Root/variable/PC_variables/<Name>/ directories.
    
    Only includes stats tagged with #vitality or #defensive.
    """
    pcs = {}
    
    if not PC_VARS_DIR.exists():
        return pcs
    
    # Scan each PC's variable directory
    for pc_dir in sorted(PC_VARS_DIR.iterdir()):
        if not pc_dir.is_dir():
            continue
        
        pcname = pc_dir.name
        pcs[pcname] = []
        
        # Scan all variable files for this PC
        for var_file in sorted(pc_dir.glob("*.md")):
            text = read_text(var_file)
            value, tags = extract_first_value_and_tags_from_env(text)
            
            # Only include if tagged with #vitality or #defensive
            has_vitality = any(t.lower() == '#vitality' for t in tags)
            has_defensive = any(t.lower() == '#defensive' for t in tags)
            
            if has_vitality or has_defensive:
                # Extract display name from filename: Anju_max_hp.md -> max_hp
                display_name = var_file.stem.replace(f"{pcname}_", "")
                rel_path = var_file.relative_to(REPO_ROOT).as_posix()
                pcs[pcname].append((display_name, value, rel_path))
    
    return pcs


def also_find_global_files():
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
    lines = []
    # Use the user-specified header/template
    lines.append("# Stat Overview\n")
    lines.append("## Global environmental variables\n")
    lines.append("")
    lines.append("| Name                           | Value | Tags                                                         | File                                                 |")
    lines.append("| ------------------------------ | ----: | ------------------------------------------------------------ | ---------------------------------------------------- |")
    if envs:
        for name, val, tags, p in envs:
            # Name shown as wiki link [[name]] per user's edited format
            link = f"[[{name}]]"
            file_rel = str(p.relative_to(REPO_ROOT).as_posix())
            lines.append(f"| {link} | {val or ''} | {tags or ''} | {file_rel} |")
    else:
        lines.append("| (none) |  |  |  |")

    lines.append("\n\n## Per-PC extracted stats\n")
    lines.append("_(Only shows variables tagged with #vitality or #defensive)_\n")
    
    if pcs:
        for pc, items in pcs.items():
            lines.append(f"\n### {pc}\n")
            
            # Organize stats by tag: vitality first, then defensive
            vitality_stats = []
            defensive_stats = []
            
            for display_name, value, src in items:
                # Read the file again to get its tags for organization
                try:
                    text = read_text(Path(REPO_ROOT) / src)
                    _, tags = extract_first_value_and_tags_from_env(text)
                    has_vitality = any(t.lower() == '#vitality' for t in tags)
                    
                    if has_vitality:
                        vitality_stats.append((display_name, value, src))
                    else:
                        defensive_stats.append((display_name, value, src))
                except Exception:
                    defensive_stats.append((display_name, value, src))
            
            # Display vitality stats if any
            if vitality_stats:
                lines.append("\n**Vitality**\n")
                lines.append("\n| Key           | Value | Source File                            |")
                lines.append("| ------------- | ----- | -------------------------------------- |")
                for name, v, src in vitality_stats:
                    v2 = v if v else ""
                    lines.append(f"| {name} | {v2}    | {src} |")
                lines.append("")
            
            # Display defensive stats if any
            if defensive_stats:
                lines.append("\n**Defensive**\n")
                lines.append("\n| Key           | Value | Source File                            |")
                lines.append("| ------------- | ----- | -------------------------------------- |")
                for name, v, src in defensive_stats:
                    v2 = v if v else ""
                    lines.append(f"| {name} | {v2}    | {src} |")
                lines.append("")
            
    else:
        lines.append("No PCs found under Player Root/variable/PC_variables/\n")

    lines.append("\n_Last generated by Mycelium/scripts/Python/generate_stat_overview.py_\n")
    return "\n".join(lines)


def main():
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
