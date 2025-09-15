"""Small helper to wrap CLI entrypoints and print total elapsed time.

Usage: import run_with_timer and call with your main/cli function.
"""
from __future__ import annotations
import time
from typing import Callable, Any


def run_with_timer(func: Callable[..., Any], *args, **kwargs) -> Any:
    """Call func(*args, **kwargs) and print elapsed wall time when done.

    The wrapped function may return a value (e.g., an exit code) which
    will be returned unchanged. Any exception raised will propagate after
    the elapsed time is printed.
    """
    start = time.perf_counter()
    try:
        return func(*args, **kwargs)
    finally:
        elapsed = time.perf_counter() - start
        try:
            print(f"[Time] Total elapsed: {elapsed:.3f}s")
        except Exception:
            # best effort only
            pass
