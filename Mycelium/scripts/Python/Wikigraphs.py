"""Wrapper for scripts/manuals/Wikigraphs.py"""
from importlib import import_module
try:
    mod = import_module('Mycelium.scripts.manuals.Wikigraphs')
except Exception:
    from pathlib import Path
    import importlib.util
    alt = Path(__file__).resolve().parent.joinpath('scripts').joinpath('manuals').joinpath('Wikigraphs.py')
    if alt.exists():
        spec = importlib.util.spec_from_file_location('Mycelium._manuals_Wikigraphs', str(alt))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore
        mod = module
    else:
        raise

Wikigraphs = mod
"""Proxy loader for scripts/manuals/Wikigraphs.py"""
import importlib

_mod = importlib.import_module('Mycelium.scripts.manuals.Wikigraphs')
for _k, _v in _mod.__dict__.items():
	if not _k.startswith('_'):
		globals()[_k] = _v

