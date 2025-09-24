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
OUT_FILE = PC_DIR / "stat_overview.md"


def read_text(p: Path):
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def extract_first_value_from_env(text: str):
    # prefer the first non-empty, non-comment line that looks like a value
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        # return raw line (e.g. '10')
        return s
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
    pcs = {}
    if not PC_DIR.exists():
        return pcs
    for pc in sorted(PC_DIR.iterdir()):
        if not pc.is_dir():
            continue
        pcname = pc.name
        pcs[pcname] = []
        # scan all md files under this pc dir
        for md in pc.rglob("*.md"):
            t = read_text(md)
            # find and normalize only the canonical keys
            for line in t.splitlines():
                key, val = normalize_key(line)
                if key:
                    pcs[pcname].append((key, val or "", md.relative_to(REPO_ROOT).as_posix()))
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
    # Only include the canonical keys, in a canonical order
    desired_order = ["max_hp", "current_hp", "evasion", "general armor"]
    if pcs:
        for pc, items in pcs.items():
            lines.append(f"\n### {pc}\n")
            lines.append("\n| Key           | Value | Source File                            |")
            lines.append("| ------------- | ----- | -------------------------------------- |")
            # create a map of key->(value,src) preferring variable files
            # scoring: higher score = more preferred
            def source_score(src_path: str):
                s = src_path.lower()
                score = 0
                # prefer files under Player Root/variable
                if '/player root/variable/' in s:
                    score += 100
                # prefer filenames that include 'variables'
                if 'variables' in s:
                    score += 50
                # prefer files with 'character sheet' or 'character' then smaller bonus
                if 'character sheet' in s or 'character' in s:
                    score += 10
                return score

            seen = {}
            for k, v, src in items:
                existing = seen.get(k)
                if existing is None:
                    seen[k] = (v, src)
                    continue
                # compare scores
                prev_v, prev_src = existing
                prev_score = source_score(prev_src)
                new_score = source_score(src)
                if new_score > prev_score:
                    seen[k] = (v, src)
            for key in desired_order:
                if key in seen:
                    v, src = seen[key]
                    # normalize booleans/None to empty
                    v2 = v if v is not None else ""
                    lines.append(f"| {key} | {v2}    | {src} |")
            lines.append("\n")
    else:
        lines.append("No PCs found under Player Root/PCs/\n")

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
