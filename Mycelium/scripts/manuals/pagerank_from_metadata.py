#!/usr/bin/env python3
"""Compute PageRank from per-file metadata (Backlinks) or fallback to wikilinks.

Reads all `.md` files under `--root` (skipping configured excludes). For each file it
prefers explicit `## Backlinks` -> `### Outgoing links` lists. If only `Incoming links`
are present the script inverts them. If no backlinks metadata exists it falls back to
scanning the file for `[[wikilink]]` occurrences.

Outputs a weighted directed adjacency and uses the existing `simple_pagerank` from the
pipeline helper to compute and (optionally) persist `Mycelium/pagerank.json`.

Usage:
  python3 Mycelium/pagerank_from_metadata.py --root . [--apply] [--iterations N] [--damping D]

"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

try:
    from scripts.pipeline_profiler_and_pagerank import simple_pagerank
    from Mycelium.config_common import get_graph_excludes
    from Mycelium.helpers.path_vars import find_path_var
except Exception:
    # fallback if modules not importable (keeps script runnable in isolation)
    try:
        from pipeline_profiler_and_pagerank import simple_pagerank  # type: ignore
    except Exception:
        simple_pagerank = None  # type: ignore
    def get_graph_excludes(root='.'):
        return ['backups/', 'Mycelium/']
    def find_path_var(root):
        return None


WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def build_name_index(root: Path) -> Dict[str, List[str]]:
    """Return a mapping of lowercase keys -> list of relative paths.

    Keys include stem, basename, full relative path and last path component.
    """
    from Mycelium.fsutil import iter_md_files
    md_files = list(iter_md_files(root))
    idx: Dict[str, List[str]] = {}
    for p in md_files:
        try:
            rel = str(p.resolve().relative_to(root))
        except Exception:
            rel = p.name
        key_stem = p.stem.lower()
        key_base = p.name.lower()
        key_rel = rel.lower()
        key_last = rel.split('/')[-1].lower()
        for k in {key_stem, key_base, key_rel, key_last}:
            idx.setdefault(k, []).append(rel)
    return idx


def parse_backlinks_section(txt: str) -> Tuple[List[str], List[str]]:
    """Return (incoming, outgoing) lists parsed from a `## Backlinks` section.

    The function looks for '### Incoming links' and '### Outgoing links' headings and
    collects the following bullet lines until the next heading. Bullet lines like
    '- [[path]]' or '- path' are supported.
    """
    incoming: List[str] = []
    outgoing: List[str] = []
    lower = txt
    m = re.search(r"^##\s+Backlinks\b", txt, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return incoming, outgoing

    start = m.start()
    sec = txt[start:]

    # find incoming block
    inc_m = re.search(r"###\s+Incoming links\b(.*?)(?:###|$)", sec, flags=re.IGNORECASE | re.DOTALL)
    if inc_m:
        block = inc_m.group(1)
        for line in block.splitlines():
            line = line.strip()
            if line.startswith('-'):
                cand = line.lstrip('-').strip()
                # unwrap [[...]] if present
                w = WIKILINK_RE.findall(cand)
                if w:
                    incoming.extend([x.strip() for x in w if x.strip()])
                else:
                    if cand:
                        incoming.append(cand)

    out_m = re.search(r"###\s+Outgoing links\b(.*?)(?:###|$)", sec, flags=re.IGNORECASE | re.DOTALL)
    if out_m:
        block = out_m.group(1)
        for line in block.splitlines():
            line = line.strip()
            if line.startswith('-'):
                cand = line.lstrip('-').strip()
                w = WIKILINK_RE.findall(cand)
                if w:
                    outgoing.extend([x.strip() for x in w if x.strip()])
                else:
                    if cand:
                        outgoing.append(cand)

    return incoming, outgoing


def resolve_candidate(cand: str, name_index: Dict[str, List[str]], root: Path) -> str:
    """Resolve a candidate target string to a relative path in the vault.

    Heuristics: prefer exact relative match, then basename/stem matches, else return
    the candidate's last path component as fallback.
    """
    if not cand:
        return ''
    cand = cand.strip()
    # try to treat cand as a relative path first
    try_paths = [cand, cand + '.md']
    for p in try_paths:
        tryp = root.joinpath(p)
        if tryp.exists():
            try:
                return str(tryp.resolve().relative_to(root))
            except Exception:
                return p

    key = cand.split('/')[-1].lower()
    # candidate with wikilink pipe 'path|Name' should already be stripped by caller
    if key in name_index:
        cands = name_index[key]
        if len(cands) == 1:
            return cands[0]
        # prefer exact match
        for cc in cands:
            if cc.lower() == cand.lower() or cc.lower().endswith('/' + key):
                return cc
        return sorted(cands, key=lambda s: len(s))[0]

    # fallback to the key itself
    return key


def build_adj_from_metadata(root: Path) -> Dict[str, Dict[str, float]]:
    root = root.resolve()
    excludes = tuple(get_graph_excludes(root))
    from Mycelium.fsutil import iter_md_files
    md_files = [p for p in iter_md_files(root)]
    name_index = build_name_index(root)
    adj: Dict[str, Dict[str, float]] = {}

    for p in md_files:
        rel = None
        try:
            rel = str(p.resolve().relative_to(root))
        except Exception:
            rel = p.name
        if any(rel.startswith(x.strip('/')) or ('/' + x.strip('/')) in rel for x in excludes):
            continue
        txt = ''
        try:
            txt = p.read_text(encoding='utf-8', errors='replace')
        except Exception:
            txt = ''

        incoming, outgoing = parse_backlinks_section(txt)
        resolved_out: List[str] = []
        if outgoing:
            for c in outgoing:
                tgt = resolve_candidate(c, name_index, root)
                if tgt:
                    resolved_out.append(tgt)
        elif incoming:
            # invert incoming -> outgoing for this node
            for c in incoming:
                tgt = resolve_candidate(c, name_index, root)
                if tgt:
                    # incoming from `tgt` means edge tgt -> rel, so record that later
                    # we'll store edges as rel -> [] but note inversion by marking a special token
                    resolved_out.append(('__INVERT__', tgt))
        else:
            # fallback to wikilinks found anywhere in the file
            found = WIKILINK_RE.findall(txt)
            for c in found:
                tgt = resolve_candidate(c, name_index, root)
                if tgt:
                    resolved_out.append(tgt)

        # add node and its outgoing edges (some entries could be inversion tuples)
        adj.setdefault(rel, {})
        for item in resolved_out:
            if isinstance(item, tuple) and item[0] == '__INVERT__':
                # record inverted edge from item[1] -> rel by ensuring source node exists
                src = item[1]
                adj.setdefault(src, {})
                adj[src][rel] = adj[src].get(rel, 0.0) + 1.0
            else:
                tgt = item
                adj[rel][tgt] = adj[rel].get(tgt, 0.0) + 1.0

    # ensure all nodes appear even if isolated
    for k in list(name_index.values()):
        for v in k:
            adj.setdefault(v, {})

    return adj


def cli(argv=None):
    p = argparse.ArgumentParser(description='Compute PageRank from file metadata/backlinks or wikilinks')
    p.add_argument('--root', default=None, help='Vault root (if not provided will try Mycelium config)')
    p.add_argument('--apply', action='store_true', help='Write Mycelium/pagerank.json (default: dry-run)')
    p.add_argument('--iterations', type=int, default=20)
    p.add_argument('--damping', type=float, default=0.85)
    p.add_argument('--top', type=int, default=20, help='Show top-N nodes in dry-run output')
    args = p.parse_args(argv)

    # prefer explicit CLI root; otherwise try reading path variables from Mycelium config
    if args.root:
        root = Path(args.root)
    else:
        guessed = find_path_var(Path('.'))
        root = Path(guessed) if guessed else Path('.')
    print(f"Scanning markdown under {root} (excludes={get_graph_excludes(root)}) to build adjacency using metadata/wikilinks...")
    adj = build_adj_from_metadata(root)
    total_nodes = len(adj)
    total_edges = sum(len(v) for v in adj.values())
    print(f"Built adjacency: {total_nodes} nodes, {total_edges} edges")

    if simple_pagerank is None:
        print('simple_pagerank not available (could not import). Aborting.')
        return

    ranks = simple_pagerank(adj, iterations=args.iterations, damping=args.damping)

    # report
    ordered = sorted(ranks.items(), key=lambda kv: kv[1], reverse=True)
    print('\nTop pagerank nodes:')
    for node, score in ordered[: args.top]:
        print(f"{node}: {score:.6f}")

    if args.apply:
        # simple_pagerank already writes Mycelium/pagerank.json; but ensure it's in correct path
        outp = Path(args.root).resolve() / 'Mycelium' / 'pagerank.json'
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(ranks, indent=2), encoding='utf-8')
        print(f"Wrote {outp}")
    else:
        print('\nDry-run: PageRank computed but not persisted. Run with --apply to write Mycelium/pagerank.json')


if __name__ == '__main__':
    cli()
