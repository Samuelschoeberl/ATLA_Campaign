from pathlib import Path
import re
from typing import Sequence, List, Dict, Tuple, Set
from collections import defaultdict


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return ''


def get_graph_excludes(root: Path) -> List[str]:
    # Best-effort: no external config; exclude Mycelium by default
    return ['Mycelium']


def build_graph(roots: Sequence[Path], candidate_files: Sequence[Path]) -> dict:
    root = Path(roots[0]) if roots else Path('.')
    nodes = {}
    edges: List[dict] = []
    seen_edges: Set[Tuple[str, str, str]] = set()

    def add_edge(src: str, dst: str, typ: str) -> None:
        key = (src, dst, typ)
        if key in seen_edges:
            return
        seen_edges.add(key)
        edges.append({'src': src, 'dst': dst, 'type': typ})

    graph_excludes = [p.rstrip('/') for p in get_graph_excludes(root)]
    for f in candidate_files:
        try:
            rel = f.relative_to(root)
            parts = list(rel.parts)
            if any(p in graph_excludes for p in parts):
                continue
            nid = str(rel.with_suffix('')).replace('\\', '/')
        except Exception:
            if any(p in graph_excludes for p in f.parts):
                continue
            nid = str(f.with_suffix('')).replace('\\', '/')
        nodes[nid] = str(f)

    for nid, fstr in list(nodes.items()):
        f = Path(fstr)
        parent = f.parent
        try:
            parent_rel = parent.relative_to(root)
            parent_id = str(parent_rel).replace('\\', '/')
            if parent_id in nodes:
                add_edge(parent_id, nid, 'parent')
                key = (nid, parent_id, 'child')
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append({'src': nid, 'dst': parent_id, 'type': 'child', 'bidirectional': True})
        except Exception:
            pass

    link_pat = re.compile(r"\[\[\s*([^\]|#]+)")
    name_to_ids = {}
    for nid in nodes:
        name = Path(nodes[nid]).stem
        name_to_ids.setdefault(name.lower(), []).append(nid)
    for nid, fstr in nodes.items():
        txt = load_text(Path(fstr)) or ''
        for m in link_pat.finditer(txt):
            target = m.group(1).strip().lower()
            targets = name_to_ids.get(target, [])
            for t in targets:
                add_edge(nid, t, 'wikilink')
                key = (t, nid, 'wikilink_rev')
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append({'src': t, 'dst': nid, 'type': 'wikilink_rev', 'bidirectional': True})

    return {'nodes': nodes, 'edges': edges}
