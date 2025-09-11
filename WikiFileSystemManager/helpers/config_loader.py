from pathlib import Path
from typing import Dict

_CACHE: Dict[str, str] = {}

def _load(path: Path | str = '../system_state.md') -> Dict[str, str]:
    p = Path(path)
    out: Dict[str, str] = {}
    if not p.exists():
        return out
    try:
        txt = p.read_text(encoding='utf-8')
    except Exception:
        return out
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        if '=' not in ln:
            continue
        k, v = ln.split('=', 1)
        key = k.strip()
        val = v.strip()
        if val.lower().startswith('#file:'):
            val = val[len('#file:'):].strip()
        out[key] = val
    return out


def get_config(key: str, default: str) -> str:
    global _CACHE
    if not _CACHE:
        _CACHE = _load()
    return _CACHE.get(key, default)
