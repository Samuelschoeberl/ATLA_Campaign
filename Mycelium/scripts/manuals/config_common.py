from __future__ import annotations

from pathlib import Path
from typing import List
try:
    from config_loader import get_config
except Exception:
    def get_config(key, default=None):
        return default


def _parse_simple_cfg(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    try:
        for ln in path.read_text(encoding='utf-8', errors='replace').splitlines():
            ln = ln.strip()
            if not ln or ln.startswith('#'):
                continue
            if '=' not in ln:
                continue
            k, v = [p.strip() for p in ln.split('=', 1)]
            out[k.lower()] = v
    except Exception:
        pass
    return out


def get_graph_excludes(root: Path | str = '.') -> List[str]:
    """Return a list of directory/file exclude patterns used by graph builders.

    Priority:
      1. config_loader.get_config('graph_excludes') if available (should be list or comma-separated string)
      2. Parse `Mycelium/Mycelium_config.md` for a key `graph_excludes = a,b,c`
      3. Fallback to ['backups/', 'Mycelium/']
    """
    rootp = Path(root)
    # 1) try config_loader
    cfg = get_config('graph_excludes', None)
    if cfg:
        if isinstance(cfg, (list, tuple)):
            return [str(x).rstrip('/') + '/' if not str(x).endswith('/') else str(x) for x in cfg]
        if isinstance(cfg, str):
            return [s.strip().rstrip('/') + '/' for s in cfg.split(',') if s.strip()]

    # 2) try Mycelium/Mycelium_config.md file
    try:
        cfg_path = rootp.joinpath('Mycelium').joinpath('Mycelium_config.md')
        parsed = _parse_simple_cfg(cfg_path)
        if 'graph_excludes' in parsed:
            val = parsed['graph_excludes']
            return [s.strip().rstrip('/') + '/' for s in val.split(',') if s.strip()]
    except Exception:
        pass

    # 3) fallback defaults
    return ['backups/', 'Mycelium/']


def node_id_from_path(p: Path | str, root: Path | str = '.') -> str:
    """Normalize a filesystem path into a canonical node id string.

    Rules:
      - If p is a Path, make it relative to root when possible.
      - Remove file suffix (.md) and normalize separators to '/'.
      - Do not start with a leading './' or '/'.
    """
    rp = Path(root)
    pp = Path(p)
    try:
        rel = pp.resolve().relative_to(rp.resolve())
    except Exception:
        # fallback to path name
        rel = pp
    # remove suffix
    if rel.suffix:
        rel = rel.with_suffix('')
    s = str(rel).replace('\\', '/')
    # strip leading ./ or /
    s = s.lstrip('./')
    s = s.lstrip('/')
    return s
