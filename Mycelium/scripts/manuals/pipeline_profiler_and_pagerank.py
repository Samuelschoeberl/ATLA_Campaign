#!/usr/bin/env python3
"""Timing and weighted PageRank helper for Mycelium pipeline.

Features:
- time_pipeline: run and time key steps (pcs parse, variable update scan, update_char, grow_mushroom)
- build_weighted_graph_from_md: read .md files and produce weighted directed graph
- simple_pagerank: run a basic PageRank using edge weights

Usage: run as script with --time to measure pipeline steps or --graph to build/pagerank
"""
from __future__ import annotations
import time
import json
from pathlib import Path
from typing import Dict, Tuple, List, Any
try:
    from Mycelium.config_common import get_graph_excludes
except Exception:
    def get_graph_excludes(root: Path | str = '.') -> List[str]:
        return ['backups/', 'Mycelium/']
import argparse
import subprocess
import re
import json as _json

ROOT = Path('.').resolve()


def time_command(cmd: List[str]) -> Tuple[float, int, str]:
    start = time.perf_counter()
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        rc = res.returncode
        out = (res.stdout or '') + (res.stderr or '')
    except Exception as e:
        rc = 1
        out = str(e)
    dur = time.perf_counter() - start
    return dur, rc, out


def time_pipeline(pcs_input: str = 'pcs_input.md') -> Dict[str, float]:
    timings: Dict[str, float] = {}

    # 1) parse pcs input via update_variables helper
    cmd = ['python3', 'Mycelium/update_variables_and_rebuild.py', '--pcs-input', pcs_input, '--root', '.', '--dry-run']
    d, rc, out = time_command(cmd)
    timings['parse_and_scan'] = d

    # 2) optionally run update_char (best-effort)
    cmd2 = ['python3', 'Mycelium/update_variables_and_rebuild.py', '--pcs-input', pcs_input, '--root', '.', '--dry-run', '--rebuild']
    d2, rc2, out2 = time_command(cmd2)
    timings['update_char_invoke'] = d2

    # 3) run grow_mushroom to build mushrooms
    cmd3 = ['python3', 'grow_mushroom.py']
    d3, rc3, out3 = time_command(cmd3)
    timings['grow_mushroom'] = d3

    # details kept separate to avoid type issues with timings value type
    details = {'parse_rc': rc, 'update_char_rc': rc2, 'grow_rc': rc3}
    # write verbose outputs for inspection
    (ROOT / 'Mycelium' / 'pipeline_timing.json').write_text(json.dumps({'timings': timings, 'details': details}, indent=2))
    return timings


def build_weighted_graph_from_md(root: Path = ROOT, complexity_alpha: float = 0.12, apply_multiplier_to: str = 'incoming', use_extractors: bool = False, proximity_max_dist: int = 3, proximity_decay: float = 0.5) -> Dict[str, Dict[str, float]]:
    """Scan markdown files and build a weighted directed adjacency mapping.

    Weight rules (heuristic):
    - Direct wikilink [[Target]] in file A -> add edge A->Target with base weight 1.0
    - If link appears inside a line containing '#links' tag -> multiply weight by 2.0
    - If multiple occurrences, sum weights
    - If both [[Target]] and plain '[[path|Name]]' variants present, normalize to target basename
    - Short-path boosting: when a file contains both A -> B and A -> C and B links to C, boost A->C by 0.5 (proximity)
    Returns adjacency dict: {source: {target: weight}}
    """
    from Mycelium.fsutil import iter_md_files
    md_files = list(iter_md_files(root))
    adj: Dict[str, Dict[str, float]] = {}
    wikilink_re = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
    tag_links_re = re.compile(r"#links\b", re.IGNORECASE)

    # map file path -> canonical id (relative path)
    def fid(p: Path) -> str:
        try:
            return str(p.resolve().relative_to(root))
        except Exception:
            return str(p.name)

    contents: Dict[str, str] = {}
    # Build file index to resolve wikilinks to exact files (by stem, basename, and relative path parts)
    name_index: Dict[str, List[str]] = {}
    for p in md_files:
        try:
            txt = p.read_text(encoding='utf-8')
        except Exception:
            txt = ''
        contents[fid(p)] = txt
        # index keys: stem, basename (no ext), full relative path, last path component
        key_stem = p.stem
        key_base = p.name
        rel = None
        try:
            rel = str(p.resolve().relative_to(root))
        except Exception:
            rel = p.name
        keys = {key_stem.lower(), key_base.lower(), rel.lower(), rel.split('/')[-1].lower()}
        for k in keys:
            name_index.setdefault(k, []).append(rel)

    # Default excludes driven by config_common
    default_excludes = tuple(get_graph_excludes(root)) + ('Mycelium/graphs', 'Mycelium/*clusters')

    # First pass: collect raw link counts and mark tag usage
    for src, txt in contents.items():
        # skip excluded paths
        if any(src.startswith(x.strip('/')) or ('/' + x.strip('/')) in src for x in default_excludes):
            continue
        adj.setdefault(src, {})
        links = wikilink_re.findall(txt)
        is_tagged = bool(tag_links_re.search(txt))
        for target_raw in links:
            # try to resolve target to an indexed file path
            cand = target_raw.strip()
            # prefer last path component first
            cand_key = cand.split('/')[-1].lower()
            resolved = None
            if cand_key in name_index:
                # if multiple matches prefer exact relative path match, then stem match
                cands = name_index[cand_key]
                if len(cands) == 1:
                    resolved = cands[0]
                else:
                    # prefer exact lower-equal match
                    for cc in cands:
                        if cc.lower() == cand.lower() or cc.lower() == cand_key:
                            resolved = cc
                            break
                    if not resolved:
                        # fallback to shortest path candidate
                        resolved = sorted(cands, key=lambda s: len(s))[0]
            else:
                # try full raw key
                if cand.lower() in name_index:
                    resolved = name_index[cand.lower()][0]

            target = resolved if resolved is not None else cand_key
            if not target:
                continue
            w = 1.0
            if is_tagged:
                w *= 2.0
            adj[src][target] = adj[src].get(target, 0.0) + w

    # If enabled, attempt to apply per-file multipliers extracted by extract_link_multipliers
    if use_extractors:
        try:
            from Mycelium.extract_link_multipliers import compute_link_multipliers  # type: ignore
        except Exception:
            compute_link_multipliers = None
        if compute_link_multipliers is not None:
            # For each source, look for a corresponding multipliers JSON file named <source>.multipliers.json
            for src in list(adj.keys()):
                src_path = Path(root) / src
                mult_path = src_path.with_suffix(src_path.suffix + '.multipliers.json')
                if mult_path.exists():
                    try:
                        data = json.loads(mult_path.read_text(encoding='utf-8'))
                        links = data.get('links', {})
                        for tgt, info in links.items():
                            # map tgt key to candidate resolved name used in adj (use basename fallback)
                            # if exact match exists, apply multiplier; otherwise try basename
                            mult = float(info.get('multiplier', 1.0))
                            if tgt in adj.get(src, {}):
                                adj[src][tgt] = adj[src][tgt] * mult
                            else:
                                # try basename match
                                for k in list(adj.get(src, {}).keys()):
                                    if Path(k).stem.lower() == Path(tgt).stem.lower():
                                        adj[src][k] = adj[src][k] * mult
                    except Exception:
                        pass

    # Replace proximity boost with shortest-path-based distance weighting.
    # Compute unweighted directed adjacency for BFS distance computation.
    unweighted: Dict[str, List[str]] = {s: list(adj.get(s, {}).keys()) for s in adj.keys()}

    # For each source, BFS up to proximity_max_dist and add decayed contributions to reachable nodes
    max_dist = int(proximity_max_dist)
    decay = float(proximity_decay)  # decay per hop (so a node at distance d gets added weight *= decay^(d-1))
    for src in list(adj.keys()):
        # BFS
        from collections import deque
        q = deque()
        seen = {src: 0}
        # initialize with immediate neighbors
        for nb in unweighted.get(src, []):
            q.append((nb, 1))
            seen[nb] = 1
        while q:
            node, dist = q.popleft()
            if dist > max_dist:
                continue
            # add decayed contribution to src->node if node not already directly connected
            if node != src:
                base_contrib = 0.0
                # sum of incoming paths from immediate neighbors at previous level
                # Here we approximate contribution as sum of src->neighbor weights at previous hop
                # For simplicity use avg outgoing weight from predecessor neighbors
                # We'll add a small boost proportional to decay^(dist-1)
                boost = (decay ** (dist - 1)) * 0.2
                adj[src][node] = adj[src].get(node, 0.0) + boost
            # enqueue neighbors
            for nb in unweighted.get(node, []):
                if nb not in seen:
                    seen[nb] = dist + 1
                    q.append((nb, dist + 1))

    # normalize potential self-loops away
    for src in list(adj.keys()):
        if src in adj[src]:
            adj[src].pop(src, None)

    # compute complexity scores for multiplier boost per target
    complexity: Dict[str, float] = {}
    for tgt in {t for out in adj.values() for t in out.keys()}:
        score = 0.0
        # try to locate actual file path under root
        try:
            tgt_path = (root / tgt)
            if tgt_path.exists():
                try:
                    sz = tgt_path.stat().st_size
                except Exception:
                    sz = 0
                score += (sz / 10000.0)  # scale down file size contribution
                # outgoing link count as complexity
                txt = contents.get(tgt, '')
                score += len(wikilink_re.findall(txt))
        except Exception:
            pass
        # if there's a mushroom subnetwork for this target, add its size
        sub_json = None
        try:
            # look for <target>_clusters/subnetwork.json in Mycelium folder
            candidate = Path('Mycelium').joinpath(f"{tgt.split('/')[-1]}_clusters").joinpath('subnetwork.json')
            if candidate.exists():
                try:
                    arr = json.loads(candidate.read_text(encoding='utf-8'))
                    score += len(arr)
                except Exception:
                    pass
        except Exception:
            pass
        complexity[tgt] = score

    # build multiplier map: multiplier = 1 + alpha * log(1+score)
    import math
    multipliers: Dict[str, float] = {}
    for k, s in complexity.items():
        mult = 1.0 + complexity_alpha * math.log1p(s)
        multipliers[k] = mult

    # apply multipliers either to incoming (default) or outgoing edges
    if apply_multiplier_to == 'incoming':
        for src in list(adj.keys()):
            for tgt in list(adj[src].keys()):
                mult = multipliers.get(tgt, 1.0)
                adj[src][tgt] = adj[src][tgt] * mult
    else:
        # outgoing: scale all outgoing edges from node by that node's multiplier
        for src in list(adj.keys()):
            mult = multipliers.get(src, 1.0)
            for tgt in list(adj[src].keys()):
                adj[src][tgt] = adj[src][tgt] * mult

    # persist graph
    (ROOT / 'Mycelium' / 'weighted_graph.json').write_text(json.dumps(adj, indent=2))
    (ROOT / 'Mycelium' / 'weighted_graph_complexity.json').write_text(json.dumps({'complexity': complexity, 'multipliers': multipliers}, indent=2))
    return adj


def simple_pagerank(adj: Dict[str, Dict[str, float]], iterations: int = 20, damping: float = 0.85) -> Dict[str, float]:
    nodes = set(adj.keys()) | {t for out in adj.values() for t in out.keys()}
    N = len(nodes)
    ranks = {n: 1.0 / N for n in nodes}

    # precompute out-weight sums
    out_sum = {n: sum(adj.get(n, {}).values()) for n in nodes}

    for _ in range(iterations):
        newr = {n: (1.0 - damping) / N for n in nodes}
        for n in nodes:
            for tgt, w in adj.get(n, {}).items():
                if out_sum.get(n, 0) > 0:
                    newr[tgt] += damping * ranks[n] * (w / out_sum[n])
        ranks = newr

    # write ranks
    (ROOT / 'Mycelium' / 'pagerank.json').write_text(json.dumps(ranks, indent=2))
    return ranks


def write_scores_files(ranks: Dict[str, float], out_dir: Path | str = Path('Mycelium/unsorted')) -> None:
    """Write one markdown file per node containing its pagerank score.

    Filenames use a safe sanitized form of the node id and end with `_scores.md`.
    Each file contains a `#scores` heading and a small fenced JSON block with the node's score.
    """
    try:
        from Mycelium.graph_md_io import _safe_filename
    except Exception:
        def _safe_filename(name: str) -> str:
            bad = '\\/:*?"<>|'
            out = ''.join('_' if c in bad else c for c in name)
            out = out.replace('\n', ' ').strip()
            if not out:
                out = 'node'
            return out

    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)
    for node, score in ranks.items():
        safe = _safe_filename(str(node))
        fname = outp.joinpath(f"{safe}_scores.md")
        payload = {node: float(score)}
        content = '#scores\n\n'
        content += f'**Pagerank**: {float(score):.6f}\n\n'
        content += '```json\n' + _json.dumps(payload, indent=2) + '\n```\n'
        try:
            fname.write_text(content, encoding='utf-8')
        except Exception:
            pass


def parse_simple_config(cfg_path: Path) -> Dict[str, Any]:
    """Parse simple key=value lines from Mycelium_config.md.

    Accepts booleans true/false, numbers, and comma-separated lists.
    Returns a dict of lowercased keys to python values.
    """
    out: Dict[str, Any] = {}
    if not cfg_path.exists():
        return out
    try:
        txt = cfg_path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return out
    for raw in txt.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            continue
        k, v = [p.strip() for p in line.split('=', 1)]
        kl = k.lower()
        vl = v.strip()
        # booleans
        if vl.lower() in ('true', 'false'):
            out[kl] = (vl.lower() == 'true')
            continue
        # numbers
        try:
            if '.' in vl:
                out[kl] = float(vl)
            else:
                out[kl] = int(vl)
            continue
        except Exception:
            pass
        # list (comma separated)
        if ',' in vl:
            out[kl] = [x.strip() for x in vl.split(',') if x.strip()]
        else:
            out[kl] = vl
    return out


def scan_vault_stats(root: Path) -> Dict[str, Any]:
    """Compute run datapoints such as total_tags, total_files_scanned, files_with_multipliers."""
    from Mycelium.fsutil import iter_md_files
    md_files = [p for p in iter_md_files(root) if 'backups' not in str(p) and '/graphs' not in str(p).replace('\\', '/')]
    total_files_scanned = len(md_files)
    tags = set()
    files_with_multipliers = 0
    import re as _re
    tag_re = _re.compile(r"#([A-Za-z0-9_\-]+)")
    for p in md_files:
        try:
            txt = p.read_text(encoding='utf-8', errors='replace')
        except Exception:
            txt = ''
        for m in tag_re.finditer(txt):
            tags.add(m.group(1).lower())
        mp = p.with_suffix(p.suffix + '.multipliers.json')
        if mp.exists():
            files_with_multipliers += 1
    return {
        'total_tags': len(tags),
        'total_files_scanned': total_files_scanned,
        'files_with_multipliers': files_with_multipliers,
    }


def write_run_log(data: Dict[str, Any], out_dir: Path | str = Path('Mycelium/logs')) -> Path:
    """Write a run log markdown file based on provided data and return its path."""
    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)
    ts = data.get('timestamp', '')
    fname = (ts.replace(':', '').replace('-', '').replace('T', '_').split('.')[0] or 'run') + '_run.md'
    path = outp.joinpath(fname)
    # stable key:value listing and optional JSON block for top_nodes
    lines = ['# Run log — Mycelium pipeline']
    for k in (
        'timestamp','duration_s','total_tags','total_files_scanned','files_with_multipliers',
        'pagerank_iterations','top_nodes_emitted','weighted_graph_path','pagerank_path','snapshots_dir','notes'
    ):
        if k in data and data[k] is not None:
            lines.append(f"{k}: {data[k]}")
    top_nodes = data.get('top_nodes')
    if top_nodes:
        lines.append('')
        lines.append('```json')
        lines.append(_json.dumps({'top_nodes': top_nodes}, indent=2))
        lines.append('```')
    txt = '\n'.join(lines) + '\n'
    try:
        path.write_text(txt, encoding='utf-8')
    except Exception:
        pass
    return path


def emit_pagerank_snapshots(adj: Dict[str, Dict[str, float]], out_dir: Path, prefix: str = 'Mycelium', iterations: int = 20, damping: float = 0.85) -> None:
    """Run PageRank iteratively and emit a timestamped .md snapshot file per iteration.

    Each snapshot file is named: <tsms>_iter<NN>_<prefix>.md and contains a fenced JSON block
    with the mapping node->rank for that iteration. The animator reads those files.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    nodes = sorted(set(adj.keys()) | {t for out in adj.values() for t in out.keys()})
    N = len(nodes)
    ranks = {n: 1.0 / N for n in nodes}
    out_sum = {n: sum(adj.get(n, {}).values()) for n in nodes}
    base_ts = int(time.time() * 1000)
    for it in range(1, iterations + 1):
        newr = {n: (1.0 - damping) / N for n in nodes}
        for n in nodes:
            for tgt, w in adj.get(n, {}).items():
                if out_sum.get(n, 0) > 0:
                    newr[tgt] += damping * ranks[n] * (w / out_sum[n])
        ranks = newr
        # write snapshot
        safe_prefix = re.sub(r'[^0-9A-Za-z_\-]+', '_', prefix)
        fname = f"{base_ts}_{it:03d}_{safe_prefix}.md"
        p = out_dir.joinpath(fname)
        payload = {k: float(v) for k, v in ranks.items()}
        md = '```json\n' + json.dumps(payload, indent=2) + '\n```\n'
        p.write_text(md, encoding='utf-8')



def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--time', action='store_true', help='Run and time pipeline steps')
    p.add_argument('--graph', action='store_true', help='Build weighted graph from markdown files')
    p.add_argument('--pagerank', action='store_true', help='Compute pagerank on built graph')
    p.add_argument('--decay-weighted', action='store_true', help='Build a decay-weighted adjacency from distances.json and use it for pagerank')
    p.add_argument('--distances-path', default='Mycelium/distances.json', help='Path to distances.json produced by compute_shortest_paths')
    p.add_argument('--decay-fn', choices=['inv', 'exp'], default='inv', help='Decay function: inv => 1/(1+param*d), exp => exp(-param*d)')
    p.add_argument('--decay-param', type=float, default=1.0, help='Parameter for decay function (multiplier on distance)')
    p.add_argument('--decay-max-distance', type=int, default=None, help='Only include distances <= this when building decay-weighted graph')
    p.add_argument('--proximity-max-distance', type=int, default=3, help='Max hop distance used for proximity boosts when building weighted graph (default: 3)')
    p.add_argument('--proximity-decay', type=float, default=0.5, help='Decay per hop for proximity boost (default: 0.5)')
    p.add_argument('--mix-direct', action='store_true', help='When building decay-weighted graph, mix in direct adjacency from built graph')
    p.add_argument('--mix-mult', type=float, default=1.0, help='Multiplier applied to decay-weight contribution when mixing with direct weights')
    p.add_argument('--exclude', action='append', help='Paths to exclude from indexing (can be provided multiple times)')
    p.add_argument('--complexity-alpha', type=float, default=0.12, help='Alpha multiplier for complexity-based boost')
    p.add_argument('--multiplier-target', choices=['incoming', 'outgoing'], default='incoming', help='Apply complexity multipliers to incoming or outgoing edges')
    p.add_argument('--emit-snapshots', action='store_true', help='Emit timestamped PageRank snapshot .md files for each iteration')
    p.add_argument('--snapshots-dir', default='Mycelium/snapshots', help='Output directory for snapshot .md files')
    p.add_argument('--snap-iterations', type=int, default=10, help='Number of PageRank iterations to emit snapshots for')
    p.add_argument('--scores', action='store_true', help='Write per-node pagerank score files into Mycelium/unsorted (files named [[Filename_scores]].md)')
    args = p.parse_args(argv)

    # Load config and override defaults where CLI kept defaults
    cfg = parse_simple_config(Path('Mycelium/Mycelium_config.md'))
    # helpers to detect whether a flag kept default
    def maybe_override(current, default, key, cast=None):
        if key not in cfg:
            return current
        if current == default:
            v = cfg[key]
            if cast:
                try:
                    return cast(v)
                except Exception:
                    return current
            return v
        return current

    args.complexity_alpha = maybe_override(args.complexity_alpha, 0.12, 'alpha_complexity', float)
    args.multiplier_target = maybe_override(args.multiplier_target, 'incoming', 'multiplier_target', str)
    # booleans default false -> allow config true to turn on
    if cfg.get('use_extractors', None) is True:
        setattr(args, 'use_extractors', True)
    else:
        setattr(args, 'use_extractors', False)
    if cfg.get('emit_scores', None) is True and args.scores is False:
        args.scores = True
    args.snap_iterations = maybe_override(args.snap_iterations, 10, 'default_snap_iterations', int)
    # proximity options may be driven by config
    args.proximity_max_distance = maybe_override(args.proximity_max_distance, 3, 'proximity_max_distance', int)
    args.proximity_decay = maybe_override(args.proximity_decay, 0.5, 'proximity_decay', float)

    if args.time:
        t = time_pipeline()
        print('Timings:', json.dumps(t, indent=2))
    # Collect run log datapoints when graph or pagerank requested
    import datetime as _dt
    run_started = _dt.datetime.utcnow()
    start_ts = time.perf_counter()
    run_data: Dict[str, Any] = {
        'timestamp': run_started.replace(microsecond=0).isoformat() + 'Z',
        'pagerank_iterations': None,
        'weighted_graph_path': 'Mycelium/weighted_graph.json',
        'pagerank_path': 'Mycelium/pagerank.json',
        'snapshots_dir': args.snapshots_dir if args.emit_snapshots else None,
        'notes': '',
    }
    if args.graph:
        g = build_weighted_graph_from_md(complexity_alpha=args.complexity_alpha, apply_multiplier_to=args.multiplier_target, use_extractors=getattr(args, 'use_extractors', False), proximity_max_dist=args.proximity_max_distance, proximity_decay=args.proximity_decay)
        print('Built graph with', len(g), 'sources')
    # Option: build decay-weighted adjacency based on distances.json
    def build_decay_weighted_graph(distances_path: str, max_dist_prune: int | None, decay_fn: str, decay_param: float) -> Dict[str, Dict[str, float]]:
        import math
        dp = Path(distances_path)
        if not dp.exists():
            raise FileNotFoundError(f"Distances file not found: {dp}")
        raw = json.loads(dp.read_text(encoding='utf-8'))
        out: Dict[str, Dict[str, float]] = {}
        for src, distmap in raw.items():
            out.setdefault(src, {})
            for tgt, d in distmap.items():
                try:
                    dval = int(d)
                except Exception:
                    try:
                        dval = int(float(d))
                    except Exception:
                        continue
                if src == tgt:
                    continue
                if max_dist_prune is not None and dval > max_dist_prune:
                    continue
                if decay_fn == 'inv':
                    w = 1.0 / (1.0 + decay_param * float(dval))
                else:
                    # exponential decay
                    w = math.exp(-decay_param * float(dval))
                out[src][tgt] = float(w)
        # persist
        try:
            (ROOT / 'Mycelium' / 'decay_weighted_graph.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
        except Exception:
            pass
        return out
    if args.pagerank:
        # by default build the standard weighted graph
        g = build_weighted_graph_from_md(complexity_alpha=args.complexity_alpha, apply_multiplier_to=args.multiplier_target, use_extractors=getattr(args, 'use_extractors', False), proximity_max_dist=args.proximity_max_distance, proximity_decay=args.proximity_decay)
        # if decay-weighted requested, override or mix
        if getattr(args, 'decay_weighted', False):
            try:
                # build_decay_weighted_graph(distances_path, max_dist_prune, decay_fn, decay_param)
                decay_adj = build_decay_weighted_graph(args.distances_path, args.decay_max_distance, args.decay_fn, args.decay_param)
            except Exception as e:
                print(f"[error] could not build decay-weighted graph: {e}")
                decay_adj = {}
            if getattr(args, 'mix_direct', False):
                # merge: direct weights kept, add decay weights multiplied by mix_mult
                merged: Dict[str, Dict[str, float]] = {}
                keys = set(list(g.keys()) + list(decay_adj.keys()))
                for src in keys:
                    merged.setdefault(src, {})
                    # direct weights
                    for tgt, w in g.get(src, {}).items():
                        merged[src][tgt] = merged[src].get(tgt, 0.0) + float(w)
                    # decay weights
                    for tgt, w in decay_adj.get(src, {}).items():
                        merged[src][tgt] = merged[src].get(tgt, 0.0) + float(w) * float(args.mix_mult)
                g = merged
            else:
                # use decay-only adjacency
                g = decay_adj
        r = simple_pagerank(g)
        if args.emit_snapshots:
            emit_pagerank_snapshots(g, Path(args.snapshots_dir), prefix='pagerank', iterations=args.snap_iterations)
        if args.scores:
            write_scores_files(r, out_dir=Path('Mycelium/unsorted'))
        top = sorted(r.items(), key=lambda kv: -kv[1])[:20]
        print('Top ranks:')
        for k, v in top:
            print(f'  {k}: {v:.6f}')
        run_data['pagerank_iterations'] = args.snap_iterations
        run_data['top_nodes_emitted'] = len(top)
        run_data['top_nodes'] = [(k, float(v)) for k, v in top]
    # Emit run log if either graph/pagerank ran
    if args.graph or args.pagerank:
        run_data.update(scan_vault_stats(ROOT))
        run_data['duration_s'] = round(time.perf_counter() - start_ts, 3)
        write_run_log(run_data)


if __name__ == '__main__':
    try:
        from Mycelium.cli_timer import run_with_timer
    except Exception:
        from cli_timer import run_with_timer
    raise SystemExit(run_with_timer(main))
