"""Proxy loader for scripts/Python/grow_utils.py

This module exists so imports like `from Mycelium.scripts.grow_utils import ...`
work during tests by forwarding to the Python implementation under
`Mycelium/scripts/Python/grow_utils.py`.
"""
from pathlib import Path
import importlib.util
alt = Path(__file__).resolve().parent.joinpath('Python').joinpath('grow_utils.py')
import importlib
try:
    mod = importlib.import_module('Mycelium.scripts.Python.grow_utils')
except Exception:
    spec = importlib.util.spec_from_file_location('Mycelium.scripts._grow_utils', str(alt))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore

globals().update({k: getattr(mod, k) for k in dir(mod) if not k.startswith('_')})
__all__ = [k for k in dir(mod) if not k.startswith('_')]
