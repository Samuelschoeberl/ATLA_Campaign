"""Utility to help organize Mycelium content and perform Mycelium-specific maintenance.

Renamed from organize_wfsm.py; adds strain placement, consolidation, and other helpers.
"""
from pathlib import Path
import argparse
import shutil
import re
import json

ROOT = Path('.').resolve()
PKG_DIR = ROOT / 'Mycelium' / 'helpers'
EXCLUDE_DIRS = {"Players Mushroom", "DMs Mushroom", "Mycelium", "archive", ".git"}

CANDIDATE_KEYWORDS = ['util', 'utils', 'helper', 'common', 'lib', 'shared']


def is_small_file(p: Path) -> bool:
    try:
        l = len(p.read_text(encoding='utf-8').splitlines())
        return l < 200
    except Exception:
        return False


def find_imported_elsewhere(p: Path) -> bool:
    name = p.stem
    for q in ROOT.rglob('*.py'):
        if q == p:
            continue
        try:
            txt = q.read_text(encoding='utf-8')
        except Exception:
            continue
        if f"import {name}" in txt or f"from {name} import" in txt or f"{name}." in txt:
            return True
    return False


STRAIN_FILE = ROOT / 'config' / 'Mycelium strain.md'


def load_strain_parents() -> set:
    if not STRAIN_FILE.exists():
        return set()
    try:
        txt = STRAIN_FILE.read_text(encoding='utf-8')
    except Exception:
        return set()
    names = set(m.group(1).strip() for m in re.finditer(r"\[\[([^\]]+)\]\]", txt))
    normalized = set(n.rsplit('.', 1)[0] for n in names if n)
    return normalized


MYCELIUM_CONFIG = ROOT / 'Mycelium' / 'Mycelium.md'


def load_mycelium_mushrooms() -> set:
    """Parse Mycelium/Mycelium.md for mushroom node names like _/Name/."""
    names = set()
    if not MYCELIUM_CONFIG.exists():
        return names
    try:
        txt = MYCELIUM_CONFIG.read_text(encoding='utf-8')
    except Exception:
        return names
    for m in re.finditer(r"_/([^/]+)/", txt):
        names.add(m.group(1))
    return names


def find_linked_elsewhere_md(p: Path, target_name: str) -> bool:
    pattern = f"[[{target_name}]]"
    for q in ROOT.rglob('*.md'):
        if q == p:
            continue
        if 'config' in q.parts:
            continue
        try:
            txt = q.read_text(encoding='utf-8')
        except Exception:
            continue
        if pattern in txt:
            return True
    return False


def find_strain_branch(parent_name: str) -> Path | None:
    for q in ROOT.rglob('*.md'):
        if q.stem != parent_name:
            continue
        try:
            txt = q.read_text(encoding='utf-8')
        except Exception:
            continue
        if '#strainbranch' in txt:
            return q
    return None


def refresh_strain(move: bool = False) -> int:
    parents = load_strain_parents()
    if not parents:
        print(f'No parents found in {STRAIN_FILE} (or file missing).')
        return 0
    print('Strain parents:', ', '.join(sorted(parents)))

    moved = []
    skipped = []

    for p in ROOT.rglob('*.md'):
        if 'config' in p.parts:
            continue
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if p == STRAIN_FILE:
            continue
        try:
            txt = p.read_text(encoding='utf-8')
        except Exception:
            continue
        found_parents = [name for name in parents if f'[[{name}]]' in txt]
        if not found_parents:
            continue
        parent = found_parents[0]
        branch_md = find_strain_branch(parent)
        if not branch_md:
            skipped.append((p, f'no branch for parent {parent}'))
            continue
        dst_folder = branch_md.parent
        if p.parent == dst_folder:
            continue

        score = 0
        if any(k in p.name.lower() for k in CANDIDATE_KEYWORDS):
            score += 2
        if is_small_file(p):
            score += 1
        if found_parents:
            score += 2
        if find_linked_elsewhere_md(p, p.stem):
            score += 2

        if score >= 3:
            dst = dst_folder / p.name
            try:
                src_name = p.parent.name
            except Exception:
                src_name = str(p.parent)
            pretty = f"{src_name} -> [[{p.stem}]] -> {dst_folder.name}"
            print(pretty)
            if move:
                dst_folder.mkdir(parents=True, exist_ok=True)
                shutil.move(str(p), str(dst))
            moved.append((p, dst))
        else:
            skipped.append((p, f'score {score}'))

    print(f'Moved {len(moved)} files, skipped {len(skipped)} files.')
    return 0


def consolidate_mycelium(apply_changes: bool = False) -> int:
    base = ROOT / 'Mycelium'
    if not base.exists():
        print('Mycelium folder not found; nothing to consolidate.')
        return 0

    # load pagerank snapshot if available to pick the highest-ranked file as target
    def _load_pagerank() -> dict:
        # Pagerank snapshot is written to Mycelium/pagerank.json by the pipeline
        pr_path = ROOT / 'Mycelium' / 'pagerank.json'
        try:
            if pr_path.exists():
                return json.loads(pr_path.read_text(encoding='utf-8'))
        except Exception:
            pass
        return {}

    pagerank = _load_pagerank()

    stems: dict[str, list[Path]] = {}
    for p in base.rglob('*.md'):
        stems.setdefault(p.stem, []).append(p)

    planned: list[tuple[Path, list[Path], dict[Path, float]]] = []
    for stem, paths in stems.items():
        if len(paths) <= 1:
            continue
        # compute scores (relative path from repo root -> pagerank keys)
        scores: dict[Path, float] = {}
        for p in paths:
            try:
                key = str(p.relative_to(ROOT))
            except Exception:
                key = str(p)
            scores[p] = float(pagerank.get(key, 0.0))

        max_score = max(scores.values())
        # choose highest-ranked; if tie, fall back to alphabetical (deterministic)
        candidates_best = [p for p, s in scores.items() if s == max_score]
        if len(candidates_best) > 1:
            target = min(sorted(candidates_best))
        else:
            target = candidates_best[0]

        sources = [p for p in sorted(paths) if p != target]
        planned.append((target, sources, scores))

    if not planned:
        print('No duplicates found under Mycelium.')
        return 0

    # load known mushroom nodes
    mushrooms = load_mycelium_mushrooms()
    for target, sources, scores in planned:
        src_folders = [s.parent.name for s in [target] + sources]
        # unique, preserve order
        seen = set()
        src_unique = [x for x in src_folders if not (x in seen or seen.add(x))]
        src_part = ' -- '.join(src_unique)
        # pick mushroom for target folder if it matches any defined mushrooms
        target_mush = next((p for p in (target.parent.name, target.parent.parent.name if target.parent.parent else None) if p in mushrooms), 'Unknown')
        print(f'{src_part} -- [{target.stem}] -> {target_mush}')
    dead_dir = base / 'Dead Cells'
    if apply_changes:
        for target, sources, scores in planned:
            try:
                tgt_txt = target.read_text(encoding='utf-8')
            except Exception:
                tgt_txt = ''
            for s in sources:
                try:
                    src_txt = s.read_text(encoding='utf-8')
                except Exception:
                    src_txt = ''
                sep = '\n\n---\n\n'
                if not tgt_txt.endswith(sep):
                    tgt_txt = tgt_txt.rstrip() + sep
                tgt_txt += src_txt
            target.write_text(tgt_txt, encoding='utf-8')
            for s in sources:
                try:
                    s.unlink()
                except Exception:
                    print(f'Warning: failed to delete {s}')
        print('Consolidation applied.')
    else:
        dead_dir.mkdir(parents=True, exist_ok=True)
        for target, sources, scores in planned:
            # show pagerank scores for target and sources when doing a dry-run
            try:
                tgt_key = str(target.relative_to(ROOT))
            except Exception:
                tgt_key = str(target)
            tgt_score = scores.get(target, 0.0) if isinstance(scores, dict) else 0.0
            print(f'[dry-run] Will keep: {target.relative_to(ROOT)} (pagerank={tgt_score})')
            for s in sources:
                try:
                    dest = dead_dir / s.name
                    if dest.exists():
                        i = 1
                        while True:
                            candidate = dead_dir / f"{s.stem}_{i}{s.suffix}"
                            if not candidate.exists():
                                dest = candidate
                                break
                            i += 1
                    shutil.copy2(str(s), str(dest))
                    try:
                        src_key = str(s.relative_to(ROOT))
                    except Exception:
                        src_key = str(s)
                    src_score = scores.get(s, 0.0) if isinstance(scores, dict) else 0.0
                    print(f'Copied {s.relative_to(ROOT)} -> {dest.relative_to(ROOT)} (pagerank={src_score})')
                except Exception:
                    print(f'Warning: failed to copy {s} to Dead Cells')
        print('Duplicates copied to Mycelium/Dead Cells. Run again with --sort to merge and remove originals.')

    return 0


def candidates():
    for p in ROOT.glob('*.py'):
        if p.name == 'organize_wfsm.py' or p.name.startswith('WikiFileSystemManager'):
            continue
        if p.parent.name in EXCLUDE_DIRS:
            continue
        if p.name in ('config_loader.py', 'create_pc.py', 'create_npc.py', 'Wikigraphs.py'):
            continue
        score = 0
        if any(k in p.name.lower() for k in CANDIDATE_KEYWORDS):
            score += 2
        if is_small_file(p):
            score += 1
        if find_imported_elsewhere(p):
            score += 2
        if score >= 3:
            yield p


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--move', action='store_true', help='(deprecated) explicitly perform moves; kept for compatibility')
    ap.add_argument('--dry-run', action='store_true', help='Do not perform moves; show what would happen (default: perform moves)')
    ap.add_argument('--refresh-strain', action='store_true', help='Run automated strain-based placement from config/Mycelium strain.md')
    ap.add_argument('--consolidate-mycelium', action='store_true', help='Find duplicate .md names under Mycelium and propose concatenation')
    ap.add_argument('--sort', action='store_true', help='When set with --consolidate-mycelium, actually perform the concatenation and remove duplicates')
    args = ap.parse_args(argv)
    PKG_DIR.mkdir(parents=True, exist_ok=True)
    move = args.move or (not args.dry_run)

    if args.refresh_strain:
        return refresh_strain(move=move)
    if args.consolidate_mycelium:
        return consolidate_mycelium(apply_changes=args.sort)

    found = list(candidates())
    if not found:
        print('No helper candidates found.')
        return 0
    print('Candidates to move:')
    for p in found:
        print(' -', p)
    if move:
        for p in found:
            dst = PKG_DIR / p.name
            print(f'Moving {p} -> {dst}')
            shutil.move(str(p), str(dst))
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
