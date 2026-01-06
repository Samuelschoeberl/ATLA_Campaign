#!/usr/bin/env python3
"""Extract per-target link multipliers from a single Markdown file.

Usage:
  python3 extract_link_multipliers.py <file.md> --out out.json [--lambda 0.25 --tag-boost 0.75 --alpha-complexity 0.05 --agg-mode sum]

Produces JSON: {
  "source": "path/to/file.md",
  "tags": [...],
  "links": { "Target Name": {"occurrences": [line_indices], "multiplier": 1.23 } },
  "complexity": 1.23
}
"""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import re
import math
from typing import Dict, List


def parse_file_lines(p: Path) -> List[str]:
    """Load a file into a list of lines, tolerating encoding issues."""
    try:
        txt = p.read_text(encoding='utf-8', errors='replace')
    except Exception:
        txt = ''
    return txt.splitlines()


def extract_explicit_tags(lines: List[str]) -> List[str]:
    """Collect hashtag-style tags near the top of the document."""
    tags = set()
    for ln in lines[:30]:
        for m in re.finditer(r"#([A-Za-z0-9_\-]+)", ln):
            tags.add(m.group(1).lower())
    return sorted(tags)


def find_wikilinks(lines: List[str]) -> Dict[str, List[int]]:
    """Return mapping of wikilink targets to the line numbers where they appear."""
    wik = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
    out: Dict[str, List[int]] = {}
    for i, ln in enumerate(lines):
        for m in wik.finditer(ln):
            target = m.group(1).strip()
            out.setdefault(target, []).append(i)
    return out


def find_keyword_occurrences(lines: List[str], keywords: List[str]) -> Dict[str, List[int]]:
    """Find approximate keyword hits by substring matching against each line."""
    out: Dict[str, List[int]] = {}
    low = [k.lower() for k in keywords]
    for i, ln in enumerate(lines):
        l = ln.lower()
        for k in low:
            if k and k in l:
                out.setdefault(k, []).append(i)
    return out


def decay_multiplier(d: int, lam: float, tag_boost: float, explicit: bool) -> float:
    """Compute the weight contribution for a tag hit at distance `d`."""
    # base multiplier contribution from a tag occurrence at distance d lines
    base = 1.0
    boost = tag_boost if explicit else (tag_boost / 2.0)
    return base + boost * math.exp(-lam * d)


def compute_link_multipliers(file_path: Path, lam: float = 0.25, tag_boost: float = 0.75, alpha: float = 0.05, agg_mode: str = 'sum') -> Dict:
    """Aggregate wikilinks, tags, and keyword hints into per-target multipliers."""
    lines = parse_file_lines(file_path)
    tags = extract_explicit_tags(lines)
    wikilinks = find_wikilinks(lines)

    # also treat explicit tags as keyword occurrences at their lines
    tag_line_index: Dict[str, List[int]] = {}
    for i, ln in enumerate(lines):
        for t in tags:
            if ('#' + t) in ln.lower():
                tag_line_index.setdefault(t, []).append(i)

    results: Dict = {
        'source': str(file_path),
        'tags': tags,
        'links': {},
    }

    # fallback keyword matching: use link target names as keywords to search if needed
    link_keywords = [k for k in wikilinks.keys()]
    keyword_occ = find_keyword_occurrences(lines, link_keywords)

    for target, occ_lines in wikilinks.items():
        # compute per-tag contributions
        contributions: List[float] = []
        for t in tags:
            t_lines = tag_line_index.get(t, [])
            for tl in t_lines:
                # use nearest occurrence between target occurrences and tag occurrences
                mind = min(abs(tl - ol) for ol in occ_lines) if occ_lines else abs(tl)
                contributions.append(decay_multiplier(mind, lam, tag_boost, True))
        # also use keyword occurrences (non-explicit tags)
        for k, klines in keyword_occ.items():
            if k.lower() == target.lower():
                for kl in klines:
                    mind = min(abs(kl - ol) for ol in occ_lines) if occ_lines else abs(kl)
                    contributions.append(decay_multiplier(mind, lam, tag_boost, False))

        if not contributions:
            link_mult = 1.0
        else:
            if agg_mode == 'max':
                link_mult = max(contributions)
            else:
                link_mult = min(4.0, 1.0 + sum((c - 1.0) for c in contributions))

        results['links'][target] = {
            'occurrences': occ_lines,
            'multiplier': round(link_mult, 4),
        }

    # complexity score
    word_count = sum(len(ln.split()) for ln in lines)
    outgoing_links = len(wikilinks)
    complexity = math.log1p(word_count) * math.sqrt(1 + outgoing_links)
    results['complexity'] = round(complexity, 4)
    if alpha and results['links']:
        for t, v in results['links'].items():
            v['multiplier'] = round(min(4.0, v['multiplier'] * (1.0 + alpha * complexity)), 4)

    return results


def _cli(argv=None):
    """Command-line entry point for quick analysis."""
    p = argparse.ArgumentParser()
    p.add_argument('file', help='Markdown file to analyze')
    p.add_argument('--out', default=None, help='JSON output file (defaults to <file>.multipliers.json)')
    p.add_argument('--lambda', dest='lam', type=float, default=0.25)
    p.add_argument('--tag-boost', type=float, default=0.75)
    p.add_argument('--alpha-complexity', type=float, default=0.05)
    p.add_argument('--agg-mode', choices=['sum', 'max'], default='sum')
    args = p.parse_args(argv)
    pth = Path(args.file)
    out = compute_link_multipliers(pth, lam=args.lam, tag_boost=args.tag_boost, alpha=args.alpha_complexity, agg_mode=args.agg_mode)
    out_path = Path(args.out) if args.out else pth.with_suffix(pth.suffix + '.multipliers.json')
    out_path.write_text(json.dumps(out, indent=2), encoding='utf-8')
    print('Wrote', out_path)


if __name__ == '__main__':
    raise SystemExit(_cli())
"""Wrapper exposing compute_link_multipliers from scripts/manuals."""
from importlib import import_module
try:
    mod = import_module('Mycelium.scripts.manuals.extract_link_multipliers')
except Exception:
    from pathlib import Path
    import importlib.util
    alt = Path(__file__).resolve().parent.joinpath('scripts').joinpath('manuals').joinpath('extract_link_multipliers.py')
    if alt.exists():
        spec = importlib.util.spec_from_file_location('Mycelium._manuals_extract_link_multipliers', str(alt))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore
        mod = module
    else:
        raise

compute_link_multipliers = getattr(mod, 'compute_link_multipliers')
"""Proxy loader for scripts/manuals/extract_link_multipliers.py"""
import importlib

_mod = importlib.import_module('Mycelium.scripts.manuals.extract_link_multipliers')
for _k, _v in _mod.__dict__.items():
	if not _k.startswith('_'):
		globals()[_k] = _v
