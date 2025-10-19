"""Lightweight fallback config loader for CI/tests.

Provides get_config(key, default=None) which looks up environment variables
and returns default when unset. This file exists to satisfy static analyzers
and provide a minimal runtime environment when the project's full
configuration system isn't available.
"""
import os
from typing import Any

def get_config(key: str, default: Any = None) -> Any:
    """Return configuration value for key from environment, else default."""
    return os.environ.get(key, default)
