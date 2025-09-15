"""mycel_brain — prompt construction and clustering helpers.

This module provides:
- find_files_with_tags(root, tags)
- cluster_by_mushroom(files, out_dir)
- assemble_context_snippet(paths)
- generate_prompt(root, out_dir)

It deliberately avoids network calls. If you want to refine prompts with an
LLM, create a local `mycel_llm.py` with `def call_llm(prompt: str) -> str` and
call the CLI with `--call-llm`.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Iterable, List, Dict, Optional


# Fixed folders used for long-term storage inside the Mycelium area.
# Files/topics considered long-term (for example `#data` exports) should be
# persisted under Mycelium/history so they are easy to find and manage.
FIXED_FOLDERS = {
    'history': Path('Mycelium').joinpath('history')
}


def ensure_history_dir() -> Path:
    p = FIXED_FOLDERS['history']
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_datatype_paths(root: Path = Path('.')) -> Dict[str, str]:
    """Parse `Mycelium/history/datatype_paths.md` and return a mapping
    of semantic datatype tags (like 'data:pagerank') to canonical file paths.

    The parser understands simple lines like:
      - #data:pagerank -> `Mycelium/pagerank.json`
    or table rows in `data_referencetable.md`.
    """
    out: Dict[str, str] = {}
    hist = FIXED_FOLDERS['history']
    # consider both the dedicated datatype_paths.md and the (editable) data_referencetable.md
    candidates = [hist.joinpath('datatype_paths.md'), hist.joinpath('data_referencetable.md')]
    for fpath in candidates:
        if not fpath.exists():
            continue
        try:
            text = fpath.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue

        for line in text.splitlines():
            line = line.strip()
            # pattern: - #data:tag -> `path`
            if line.startswith('-') and '->' in line:
                left, right = line.split('->', 1)
                left = left.lstrip('-').strip()
                right = right.strip()
                # If there are backticks somewhere, prefer the first backticked span
                if '`' in right:
                    s = right.find('`')
                    e = right.find('`', s+1)
                    if e > s:
                        right = right[s+1:e].strip()
                else:
                    # strip parenthetical descriptions: take text before any '('
                    if '(' in right:
                        right = right.split('(', 1)[0].strip()
                    # strip trailing punctuation
                    right = right.strip(' `\"\',.)')
                # left may be like '#data:pagerank' or '#data pagerank'
                key = left.lstrip('#').replace(' ', ':')
                out[key] = right
            # table rows: | #data | desc | `path` |
            elif line.startswith('|'):
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) >= 3:
                    tagcell = parts[0]
                    pathcell = parts[-1]
                    path = None
                    # prefer backticked path
                    if '`' in pathcell:
                        start = pathcell.find('`')
                        end = pathcell.find('`', start+1)
                        if end > start:
                            path = pathcell[start+1:end].strip()
                    else:
                        # fallback: take first token that looks like a path (contains '/')
                        toks = pathcell.split()
                        for t in toks:
                            if '/' in t or t.endswith('.json') or t.endswith('.md'):
                                path = t.strip().strip('`.,')
                                break
                    if path:
                        key = tagcell.lstrip('#').replace(' ', ':')
                        out[key] = path
    return out


def get_canonical_path(tag: str, root: Path = Path('.')) -> Optional[Path]:
    """Return a Path for a semantic tag such as 'data:pagerank' if present.

    Falls back to None if not found.
    """
    mapping = load_datatype_paths(root)
    p = mapping.get(tag)
    if not p:
        return None
    return (Path(p) if Path(p).is_absolute() else root.joinpath(p)).resolve()


def get_all_paths(root: Path = Path('.')) -> Dict[str, str]:
    """Return the full mapping of semantic tags -> canonical paths.

    This is a thin wrapper around load_datatype_paths but kept for a cleaner
    public API so other tools can import and call it.
    """
    return load_datatype_paths(root)


def find_files_with_tags(root: Path, tags: Iterable[str]) -> List[Path]:
    tags = set(t.strip('# ').lower() for t in tags)
    out: List[Path] = []
    # If the caller is specifically looking for long-term `#data` files,
    # prefer the `Mycelium/history` fixed folder. Fall back to the vault root
    # if the history folder does not exist yet.
    search_root = root
    if 'data' in tags:
        hist = FIXED_FOLDERS['history']
        if hist.exists():
            search_root = hist
    from Mycelium.fsutil import iter_md_files
    for p in iter_md_files(search_root):
        try:
            text = p.read_text(encoding='utf8', errors='replace')
        except Exception:
            continue
        for t in tags:
            if re.search(rf'(^|\s)#{re.escape(t)}(\s|$|[.,:;])', text, flags=re.I | re.M):
                out.append(p)
                break
    return sorted(set(out))


def find_data_files(root: Path) -> List[Path]:
    return find_files_with_tags(root, ['data'])


def extract_relevant_snippets(path: Path, max_paragraphs: int = 3) -> List[str]:
    text = path.read_text(encoding='utf8', errors='replace')
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    return paragraphs[:max_paragraphs]


def assemble_context_snippet(paths: List[Path], top_k: int = 5) -> str:
    snippets: List[str] = []
    for p in paths[:top_k]:
        snips = extract_relevant_snippets(p, max_paragraphs=2)
        snippets.append(f'File: {p.name}')
        snippets.extend(snips)
        snippets.append('')
    return '\n\n'.join(snippets).strip()


def cluster_by_mushroom(files: List[Path], out_dir: Path) -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = {}
    for p in files:
        # Use the immediate parent folder name as the cluster key (e.g., 'Anju')
        try:
            mush = p.parent.name or 'Unassigned'
        except Exception:
            mush = 'Unassigned'
        mapping.setdefault(mush, []).append(str(p))

    # Cluster outputs are considered long-term artifacts. Persist them under
    # Mycelium/history/clustered so they are kept in the project's fixed
    # history area. If for some reason the history folder cannot be used,
    # fall back to the provided out_dir.
    try:
        clustered_root = ensure_history_dir().joinpath('clustered')
        clustered_root.mkdir(parents=True, exist_ok=True)
    except Exception:
        clustered_root = out_dir.joinpath('clustered')
        clustered_root.mkdir(parents=True, exist_ok=True)
    for mush, paths in mapping.items():
        d = clustered_root.joinpath(mush)
        d.mkdir(parents=True, exist_ok=True)
        for rp in paths:
            safe = re.sub(r'[^0-9A-Za-z_\-\.]+', '_', rp)
            outp = d.joinpath(safe + '.md')
            outp.write_text(f'#cluster {mush}\n\nOriginal: {rp}\n', encoding='utf-8')

    return mapping


def load_pagerank(root: Path) -> Dict[str, float]:
    p = root.joinpath('Mycelium').joinpath('pagerank.json')
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return {}


def generate_prompt(root: Path, out_dir: Path, top_n: int = 20, out_file: Optional[Path] = None, goal: Optional[str] = None) -> Path:
    ranks = load_pagerank(root)
    sorted_nodes = sorted(ranks.items(), key=lambda kv: -kv[1])[:top_n]

    tag_counts: Dict[str, int] = {}
    samples: List[str] = []
    for node, score in sorted_nodes:
        samples.append(f'- {node}: {score:.6f}')
        fpath = Path(node)
        if not fpath.exists():
            alt = root.joinpath(node)
            if alt.exists():
                fpath = alt
        try:
            txt = fpath.read_text(encoding='utf-8', errors='replace')
        except Exception:
            txt = ''
        for m in re.finditer(r"#([A-Za-z0-9_\-]+)", txt):
            tag = m.group(1).lower()
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    top_tags = sorted(tag_counts.items(), key=lambda kv: -kv[1])[:10]

    ts = int(time.time())
    out_dir.mkdir(parents=True, exist_ok=True)
    if out_file is None:
        fname = out_dir.joinpath(f"{ts}_prompt.md")
    else:
        fname = out_file
    lines: List[str] = []
    lines.append('# Mycelium generated prompt')
    lines.append('')
    # explicit LLM-friendly headers expected by other tools/tests
    lines.append('CONTEXT:')
    lines.append('')
    lines.append('Context summary:')
    lines.append('')
    lines.append(f'- total_top_nodes: {len(sorted_nodes)}')
    lines.append('- top_nodes:')
    lines += samples
    lines.append('')
    lines.append('- top_tags:')
    for t, c in top_tags:
        lines.append(f'  - #{t}: {c}')
    lines.append('')
    lines.append('Prompt instructions:')
    lines.append('Use the context above to generate a focused transformation or summary. Prefer concise action items. When suggesting edits or new content, include the target file path in the recommendation.')
    lines.append('')
    # Include an explicit TASK section that captures the requested goal
    lines.append('')
    lines.append('TASK:')
    lines.append('')
    lines.append(goal or 'No explicit goal provided.')
    lines.append('')
    lines.append('Example starter tasks:')
    lines.append('- Suggest 5 short prompts to improve the top 3 nodes.')
    lines.append('- Propose 3 ways to cluster `#data` files for prompt-engineering pipelines.')
    lines.append('')
    fname.write_text('\n'.join(lines), encoding='utf-8')
    return fname


def optimize_with_llm(prompt: str) -> str:
    try:
        import mycel_llm

        if hasattr(mycel_llm, 'call_llm'):
            return mycel_llm.call_llm(prompt)
    except Exception:
        pass
    return prompt


def cli(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog='mycel_brain')
    p.add_argument('--root', type=Path, default=Path('.'), help='vault root')
    p.add_argument('--cluster-data', action='store_true')
    p.add_argument('--generate-prompt', action='store_true')
    p.add_argument('--tags', type=str, default='data', help='comma-separated tags')
    p.add_argument('--goal', type=str, default='Summarize', help='one-line goal')
    p.add_argument('--top-k', type=int, default=8)
    p.add_argument('--out', type=Path, default=Path('Mycelium/brain_outputs'))
    p.add_argument('--call-llm', action='store_true')
    p.add_argument('--show-path', type=str, default=None, help='Show canonical path for a semantic tag (e.g. data:pagerank)')
    args = p.parse_args(argv)

    root = args.root
    out = args.out
    # If user supplied an explicit .md path, treat it as the target file; otherwise treat as directory
    if out.suffix.lower() == '.md':
        out_dir = out.parent if out.parent.exists() else Path('.')
        out_file = out
    else:
        out_dir = out
        out_file = None

    if args.cluster_data:
        tags = [t.strip() for t in args.tags.split(',') if t.strip()]
        files = find_files_with_tags(root, tags)
        mapping = cluster_by_mushroom(files, out)
        print('Clustered files into', len(mapping), 'buckets')

    # show resolved canonical path and exit early
    if args.show_path:
        cp = get_canonical_path(args.show_path, root=root)
        if cp:
            print(cp)
            return 0
        else:
            print('No canonical path found for', args.show_path)
            return 2

    # generate prompt if explicitly requested, or if tags+goal were provided (legacy test usage)
    if args.generate_prompt or (args.tags and args.goal):
        prompt_path = generate_prompt(root, out_dir, top_n=args.top_k, out_file=out_file, goal=args.goal)
        if args.call_llm:
            txt = prompt_path.read_text(encoding='utf-8')
            refined = optimize_with_llm(txt)
            prompt_path.write_text(refined, encoding='utf-8')
            print('Wrote LLM-refined prompt to', prompt_path)
            # Suggest the next manual step to the user and wait for confirmation before exiting.
            try:
                print('\nLLM refinement complete.')
                print('Suggested next step: re-run your ChatGPT coding agent (or chosen assistant) with this prompt file so it can act on the new instructions.')
                print(f'Prompt file: {prompt_path}\n')
                print('When ready to continue, press Enter. To abort, press Ctrl-C.')
                input('Press Enter to continue...')
            except KeyboardInterrupt:
                print('\nAborted by user before continuing.')
                return 0
        else:
            print('Wrote prompt to', prompt_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(cli())
