"""Wrapper exposing build_weighted_graph_from_md from scripts/manuals."""
from importlib import import_module
try:
    mod = import_module('Mycelium.scripts.manuals.pipeline_profiler_and_pagerank')
except Exception:
    from pathlib import Path
    import importlib.util
    alt = Path(__file__).resolve().parent.joinpath('scripts').joinpath('manuals').joinpath('pipeline_profiler_and_pagerank.py')
    if alt.exists():
        spec = importlib.util.spec_from_file_location('Mycelium._manuals_pipeline_profiler_and_pagerank', str(alt))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore
        mod = module
    else:
        raise

build_weighted_graph_from_md = getattr(mod, 'build_weighted_graph_from_md')
simple_pagerank = getattr(mod, 'simple_pagerank', None)
"""Proxy loader for the implementation living under scripts/manuals.pipeline_profiler_and_pagerank"""
import importlib

_mod = importlib.import_module('Mycelium.scripts.manuals.pipeline_profiler_and_pagerank')
for _k, _v in _mod.__dict__.items():
    if not _k.startswith('_'):
        globals()[_k] = _v

