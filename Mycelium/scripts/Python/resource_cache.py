"""Versioned in-process cache + per-path locking for vault files.

Sits next to `common.py`. Three things live here that used to be scattered
(or entirely missing) across `frontend_api.py`:

1. A per-path `threading.RLock` so concurrent writes to the same file (from
   Flask request threads, the folded-in variable-sync background thread, and
   `watch_and_regen.propagate_environmental_from_sheet`) can't interleave.
2. A server-authoritative content-hash "version" for optimistic-concurrency
   writes: callers read a version, and a write must supply the version it was
   based on or get rejected with a `VersionConflict` (-> HTTP 409) instead of
   silently clobbering someone else's concurrent edit.
3. Small caches for expensive, frequently-repeated derived work that used to
   run on every request with no memoization: the stat-overview subprocess
   regeneration (previously triggered from three separate call sites), the
   move-analysis scorer results, and PNG ICC-profile stripping.

Scale note: this is a LAN app for a handful of concurrent players, not a
web-scale service — plain dicts + locks are the right level of engineering
here, not a distributed cache.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import events

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------

def compute_version(content) -> str:
    """Return a short, stable content-hash version identifier."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content or b"").hexdigest()[:16]


class VersionConflict(Exception):
    """Raised by write_with_version_check() when expected_version is stale."""

    def __init__(self, current_content: str, current_version: str):
        super().__init__("version conflict")
        self.current_content = current_content
        self.current_version = current_version


_path_locks: Dict[str, threading.RLock] = {}
_path_locks_meta_lock = threading.Lock()


def get_lock(path: Path) -> threading.RLock:
    """Return (creating if necessary) the RLock guarding a given file path."""
    key = str(Path(path).resolve()) if Path(path).exists() else str(path)
    with _path_locks_meta_lock:
        lock = _path_locks.get(key)
        if lock is None:
            lock = threading.RLock()
            _path_locks[key] = lock
        return lock


def read_with_version(path: Path) -> Tuple[Optional[str], Optional[str]]:
    """Read a file's current content + version. Returns (None, None) if missing."""
    path = Path(path)
    lock = get_lock(path)
    with lock:
        if not path.exists():
            return None, None
        content = path.read_text(encoding="utf-8")
        return content, compute_version(content)


def write_with_version_check(
    path: Path,
    new_content: str,
    expected_version: Optional[str] = None,
    publish_path: Optional[str] = None,
) -> str:
    """Write new_content to path, guarded by that path's lock.

    If expected_version is provided, it must match the current on-disk
    version or a VersionConflict is raised (caller turns this into an HTTP
    409 with the conflict's current_content/current_version). Pass
    expected_version=None to force-write unconditionally (used by call sites
    not yet migrated to version-checked saves).

    On success, publishes a "file_changed" event (path defaults to the
    repo-relative-ish string passed as publish_path, falling back to str(path))
    so SSE-subscribed clients know to refetch.
    """
    path = Path(path)
    lock = get_lock(path)
    with lock:
        current_content = path.read_text(encoding="utf-8") if path.exists() else None
        current_version = compute_version(current_content) if current_content is not None else None
        if expected_version is not None and current_version != expected_version:
            raise VersionConflict(current_content or "", current_version or "")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_content, encoding="utf-8")
        new_version = compute_version(new_content)
        try:
            events.publish("file_changed", path=publish_path or str(path), version=new_version)
        except Exception:
            # Never let a pub/sub hiccup break the actual write.
            pass
        return new_version


# ---------------------------------------------------------------------------
# Stat overview: collapse 3 independent subprocess-per-request call sites
# into one cached/debounced path.
# ---------------------------------------------------------------------------

_stat_overview_dirty = True
_stat_overview_lock = threading.Lock()
_stat_overview_last_regen: float = 0.0
_STAT_OVERVIEW_MIN_INTERVAL = 1.0  # seconds; coalesce rapid-fire dirty marks


def mark_stat_overview_dirty() -> None:
    """Flag that stat_overview.md should be regenerated before it's next read."""
    global _stat_overview_dirty
    with _stat_overview_lock:
        _stat_overview_dirty = True


def get_stat_overview_cached(repo_root: Path, timeout: int = 30) -> Tuple[bool, Optional[str]]:
    """Ensure stat_overview.md is up to date, regenerating at most once per
    _STAT_OVERVIEW_MIN_INTERVAL even under repeated dirty-marks/requests.

    Returns (ok, error_message).
    """
    global _stat_overview_dirty, _stat_overview_last_regen
    with _stat_overview_lock:
        now = time.time()
        stale_by_time = (now - _stat_overview_last_regen) >= _STAT_OVERVIEW_MIN_INTERVAL
        if not _stat_overview_dirty and _stat_overview_last_regen > 0:
            return True, None
        if not stale_by_time and _stat_overview_last_regen > 0:
            # Someone else regenerated very recently; treat as fresh enough.
            return True, None

        generator_script = repo_root / "Mycelium" / "scripts" / "Python" / "generate_stat_overview.py"
        if not generator_script.exists():
            return False, "Stat overview generator script not found"
        try:
            result = subprocess.run(
                [sys.executable, str(generator_script)],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False, "Stat overview generation timed out"
        except Exception as e:
            return False, str(e)
        if result.returncode != 0:
            return False, result.stderr or "generator failed"
        _stat_overview_dirty = False
        _stat_overview_last_regen = time.time()
        try:
            events.publish("file_changed", path="Player Root/PCs/stat_overview.md", version=None)
        except Exception:
            pass
        return True, None


# ---------------------------------------------------------------------------
# Move-analysis scoring cache: keyed on a hash of the scanned move files'
# combined mtime/size so /api/analyze-moves doesn't re-parse+re-score the
# whole tree on every call.
# ---------------------------------------------------------------------------

_analysis_cache: Dict[str, dict] = {}
_analysis_cache_lock = threading.Lock()


def analysis_cache_key(move_files) -> str:
    """Build a cache key from a list of Path objects based on mtime+size."""
    parts = []
    for p in sorted(move_files, key=lambda x: str(x)):
        try:
            st = p.stat()
            parts.append(f"{p}:{st.st_mtime_ns}:{st.st_size}")
        except Exception:
            parts.append(f"{p}:missing")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def analysis_cache_get(key: str):
    with _analysis_cache_lock:
        return _analysis_cache.get(key)


def analysis_cache_set(key: str, value) -> None:
    with _analysis_cache_lock:
        # Keep this small; there's only ever a handful of distinct
        # element/level/mode combinations in practice.
        if len(_analysis_cache) > 100:
            _analysis_cache.clear()
        _analysis_cache[key] = value


# ---------------------------------------------------------------------------
# PNG ICC-stripping cache: avoid re-running Pillow re-encode on every repeat
# GET of the same image.
# ---------------------------------------------------------------------------

_png_cache: Dict[str, Tuple[float, bytes]] = {}
_png_cache_lock = threading.Lock()
_PNG_CACHE_MAX_ENTRIES = 50


def get_cached_stripped_png(path: Path) -> Optional[bytes]:
    """Return previously-stripped PNG bytes for path if the mtime still matches."""
    path = Path(path)
    try:
        mtime = path.stat().st_mtime
    except Exception:
        return None
    key = str(path)
    with _png_cache_lock:
        entry = _png_cache.get(key)
        if entry and entry[0] == mtime:
            return entry[1]
    return None


def set_cached_stripped_png(path: Path, mtime: float, data: bytes) -> None:
    path = Path(path)
    key = str(path)
    with _png_cache_lock:
        if len(_png_cache) >= _PNG_CACHE_MAX_ENTRIES and key not in _png_cache:
            # Evict an arbitrary (oldest-inserted-ish) entry; dict preserves
            # insertion order in Python 3.7+, so pop the first key.
            try:
                _png_cache.pop(next(iter(_png_cache)))
            except StopIteration:
                pass
        _png_cache[key] = (mtime, data)
