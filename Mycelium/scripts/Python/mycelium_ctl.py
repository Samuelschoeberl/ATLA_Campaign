#!/usr/bin/env python3
"""Lightweight top-level control CLI for Mycelium tasks.

Subcommands implemented:
- pagerank: build graph and compute pagerank (wraps pipeline helper)
- update-variables: run variable scan/update (wraps update_variables_and_rebuild)
- fix-variable: ensure only one canonical variable .md for a given name (interactive)

This script uses existing pipeline helpers where possible and performs safe
in-place edits when adjusting variable file tags. It is intentionally small and
conservative.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import sys
import re


ROOT = Path('.').resolve()


def pagerank_command(args: argparse.Namespace) -> int:
    try:
        from Mycelium.scripts.manuals.pipeline_profiler_and_pagerank import build_weighted_graph_from_md, simple_pagerank, emit_pagerank_snapshots, write_scores_files
    except Exception as e:
        print(f"[error] could not import pagerank helpers: {e}")
        return 2
    print('[info] Building weighted graph...')
    g = build_weighted_graph_from_md(root=ROOT, complexity_alpha=args.complexity_alpha, apply_multiplier_to=args.multiplier_target, use_extractors=getattr(args, 'use_extractors', False), proximity_max_dist=args.proximity_max_distance, proximity_decay=args.proximity_decay)
    print(f"[info] Graph built with {len(g)} source nodes")
    print('[info] Computing PageRank...')
    ranks = simple_pagerank(g, iterations=args.iterations, damping=args.damping)
    if args.emit_snapshots:
        emit_pagerank_snapshots(g, Path(args.snapshots_dir), prefix='pagerank', iterations=args.snap_iterations)
    if args.scores:
        write_scores_files(ranks, out_dir=Path('Mycelium/unsorted'))
    top = sorted(ranks.items(), key=lambda kv: -kv[1])[:20]
    print('Top pagerank nodes:')
    for k, v in top:
        print(f'  {k}: {v:.6f}')
    # persist pagerank.json already performed by simple_pagerank helper
    return 0


def update_variables_command(args: argparse.Namespace) -> int:
    try:
        from Mycelium.scripts.manuals.update_variables_and_rebuild import scan_and_update
    except Exception as e:
        print(f"[error] could not import update_variables helper: {e}")
        return 2
    pcs_input = Path(args.pcs_input) if args.pcs_input else Path('pcs_input.md')
    print(f"[info] Scanning for variable files and updating from {pcs_input} (dry_run={args.dry_run})")
    try:
        n_updated, n_checked = scan_and_update(ROOT, pcs_input, dry_run=args.dry_run, backup_suffix=(None if args.no_backup else '.bak'), debug=args.debug)
        print(f"[info] Completed: {n_updated} files updated (checked {n_checked})")
        return 0
    except Exception as e:
        print(f"[error] update failed: {e}")
        return 3


def find_variable_candidates(varname: str) -> list[Path]:
    var_lower = varname.lower()
    candidates: list[Path] = []
    from scripts.fsutil import iter_md_files
    for p in iter_md_files(ROOT):
        try:
            stem = p.stem.lower()
            # match exact stem, or variants like 'name (alt)' or 'name - alt'
            if not (stem == var_lower or stem.startswith(var_lower + ' ') or var_lower in stem):
                continue
            txt = p.read_text(encoding='utf-8', errors='ignore')
            if re.search(r"#variable\b", txt, re.IGNORECASE):
                candidates.append(p)
        except Exception:
            continue
    return sorted(candidates)


def ensure_tags_line(txt: str) -> str:
    # Ensure there's a 'tags:' line near the top; if not, insert after first line
    lines = txt.splitlines()
    for i, L in enumerate(lines[:8]):
        if L.strip().lower().startswith('tags:'):
            return txt
    # insert tags: #Variable at second line
    if len(lines) >= 1:
        lines.insert(1, 'tags: #Variable')
    else:
        lines = ['tags: #Variable']
    return '\n'.join(lines) + '\n'


def fix_variable_command(args: argparse.Namespace) -> int:
    if not args.name:
        print('[error] fix-variable requires a variable name')
        return 2
    candidates = find_variable_candidates(args.name)
    if not candidates:
        print(f"[info] No variable files found for '{args.name}'")
        return 0
    if len(candidates) == 1 and not args.force:
        print(f"[info] Single variable file found: {candidates[0]}")
        return 0
    print(f"[warn] Multiple variable files found for '{args.name}':")
    for i, p in enumerate(candidates):
        txt = p.read_text(encoding='utf-8', errors='ignore')
        primary = bool(re.search(r"#primary_variable\b", txt, re.IGNORECASE))
        sec = bool(re.search(r"#secondary_variable\b", txt, re.IGNORECASE))
        print(f"  [{i}] {p}  (primary={primary} secondary={sec})")
    if args.prefer is not None:
        choice = args.prefer
    else:
        # if auto_pick requested, select highest pagerank candidate non-interactively
        if getattr(args, 'auto_pick', False):
            try:
                from Mycelium.scripts.manuals.mycel_brain import load_pagerank
                pr = load_pagerank(ROOT)
            except Exception:
                pr = {}
            best_score = None
            best_idx = 0
            for i, p in enumerate(candidates):
                # try repo-relative posix key first, fallback to filename
                try:
                    rel = str(p.relative_to(ROOT).as_posix())
                except Exception:
                    rel = p.name
                score = float(pr.get(rel, pr.get(p.name, 0.0) or 0.0))
                if best_score is None or score > best_score:
                    best_score = score
                    best_idx = i
            choice = best_idx
        else:
            # prompt
            try:
                resp = input(f"Choose index to prefer as PRIMARY (0..{len(candidates)-1}), or 'a' to abort: ")
            except Exception:
                print('[error] no input available; aborting')
                return 3
            if resp.strip().lower() in ('a', 'q', 'none'):
                print('Aborted by user.')
                return 1
            try:
                choice = int(resp.strip())
            except Exception:
                print('[error] invalid choice')
                return 4
    if choice < 0 or choice >= len(candidates):
        print('[error] choice out of range')
        return 4
    chosen = candidates[choice]
    # Before making changes, ensure chosen file looks like a character primary variable
    try:
        chosen_txt = chosen.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        chosen_txt = ''
    required_tags = ['#character_stat', '#primary_stat', '#variable']
    missing = [t for t in required_tags if not re.search(re.escape(t) + r"\b", chosen_txt, re.IGNORECASE)]
    if missing and not args.force:
        print(f"[warn] Chosen file {chosen} is missing expected tags: {', '.join(missing)}")
    # If --force-any-variable or --auto-pick provided, skip the interactive tag-check regardless of missing tags
    if missing and not (args.force or getattr(args, 'force_any_variable', False) or getattr(args, 'auto_pick', False)):
         try:
             resp = input('Proceed anyway and mark as PRIMARY? [y/N]: ')
         except Exception:
             print('[error] no input available; aborting')
             return 3
         if resp.strip().lower() not in ('y', 'yes'):
             print('Aborted by user.')
             return 1
    print(f'[info] Marking {chosen} as PRIMARY; others will be marked SECONDARY')
    for p in candidates:
        try:
            txt = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            print(f'[warn] could not read {p}; skipping')
            continue
        # ensure tags line exists
        txt = ensure_tags_line(txt)
        # normalize tags line
        lines = txt.splitlines()
        for i, L in enumerate(lines[:8]):
            if L.strip().lower().startswith('tags:'):
                tags = L[len('tags:'):].strip()
                tags_set = {t.strip() for t in re.split(r'[ ,]+', tags) if t.strip()}
                # ensure #Variable present
                tags_set.add('#Variable')
                if p == chosen:
                    tags_set.discard('#Secondary_variable')
                    tags_set.add('#Primary_variable')
                else:
                    tags_set.discard('#Primary_variable')
                    tags_set.add('#Secondary_variable')
                lines[i] = 'tags: ' + ' '.join(sorted(tags_set))
                break
        newtxt = '\n'.join(lines) + ('\n' if not txt.endswith('\n') else '')
        try:
            if args.dry_run:
                print(f"[dry-run] would write tags for {p}: {lines[1] if len(lines)>1 else '<no tags line>'}")
            else:
                # backup
                if args.backup:
                    bak = p.with_suffix(p.suffix + '.bak')
                    try:
                        p.rename(bak)
                        bak.write_text(txt, encoding='utf-8')
                        # restore original name
                        bak.rename(p)
                    except Exception:
                        # fall back to writing a .bak copy
                        try:
                            p.with_suffix(p.suffix + '.bak').write_text(txt, encoding='utf-8')
                        except Exception:
                            pass
                p.write_text(newtxt, encoding='utf-8')
                print(f'[info] Updated tags for {p}')
        except Exception as e:
            print(f'[error] failed to update {p}: {e}')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog='mycelium_ctl')
    sub = p.add_subparsers(dest='cmd')

    pa = sub.add_parser('pagerank', help='Build graph and compute pagerank')
    pa.add_argument('--iterations', type=int, default=20)
    pa.add_argument('--damping', type=float, default=0.85)
    pa.add_argument('--complexity-alpha', type=float, default=0.12)
    pa.add_argument('--multiplier-target', choices=['incoming', 'outgoing'], default='incoming')
    pa.add_argument('--use-extractors', action='store_true')
    pa.add_argument('--proximity-max-distance', type=int, default=3)
    pa.add_argument('--proximity-decay', type=float, default=0.5)
    pa.add_argument('--emit-snapshots', action='store_true')
    pa.add_argument('--snapshots-dir', default='Mycelium/snapshots')
    pa.add_argument('--snap-iterations', type=int, default=10)
    pa.add_argument('--scores', action='store_true')

    pu = sub.add_parser('update-variables', help='Scan and update variable files from pcs_input.md')
    pu.add_argument('--pcs-input', default='pcs_input.md')
    pu.add_argument('--dry-run', action='store_true')
    pu.add_argument('--no-backup', dest='no_backup', action='store_true')
    pu.add_argument('--debug', action='store_true')

    pf = sub.add_parser('fix-variable', help='Ensure single canonical variable .md for a given name')
    pf.add_argument('name', type=str, help='Variable basename (without .md)')
    pf.add_argument('--prefer', type=int, default=None, help='Index to prefer (non-interactive)')
    pf.add_argument('--dry-run', action='store_true')
    pf.add_argument('--backup/--no-backup', dest='backup', default=True)
    pf.add_argument('--force', action='store_true', help='Skip prompt when single candidate')
    pf.add_argument('--proximity-decay', action='store_true', help=argparse.SUPPRESS)
    # Allow force-marking any file as PRIMARY even if it lacks expected stat tags
    pf.add_argument('--force-any-variable', action='store_true', dest='force_any_variable', help='Mark file as PRIMARY even if it lacks expected tags')
    pf.add_argument('--auto-pick', action='store_true', dest='auto_pick', help='Non-interactive: pick candidate with highest PageRank')

    args = p.parse_args(argv)
    if args.cmd == 'pagerank':
        return pagerank_command(args)
    if args.cmd == 'update-variables':
        return update_variables_command(args)
    if args.cmd == 'fix-variable':
        return fix_variable_command(args)
    p.print_help()
    return 0


if __name__ == '__main__':
    rc = main()
    raise SystemExit(rc)
