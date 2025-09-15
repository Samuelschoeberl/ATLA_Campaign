"""Minimal, TTRPG-focused subset of Mycelium functionality.

This module is intended to be small and self-contained so it can be used when
the full Mycelium package is excluded (for example, via a `--light` flag).
It intentionally avoids optional heavy dependencies.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List


def read_note_summary(path: Path, max_chars: int = 400) -> str:
    try:
        text = path.read_text(encoding='utf8', errors='replace')
    except Exception:
        return ''
    # simple heuristic: first two paragraphs
    paras = [p.strip() for p in text.split('\n\n') if p.strip()]
    summary = ' '.join(paras[:2])
    return summary[:max_chars]


def top_k_by_pagerank(rank_map: Dict[str, float], k: int = 10) -> List[str]:
    return [n for n, _ in sorted(rank_map.items(), key=lambda kv: -kv[1])[:k]]


def minimal_cli_help() -> str:
    return 'Mycelium_light: read_note_summary(path) and top_k_by_pagerank(rank_map, k)'


if __name__ == '__main__':
    print(minimal_cli_help())
