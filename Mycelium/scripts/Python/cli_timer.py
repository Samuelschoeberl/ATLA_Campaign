"""Migrated cli_timer from manuals."""
import time

class Timer:
    def __init__(self):
        self.start = time.time()
    def elapsed(self):
        return time.time() - self.start

def main():
    t = Timer()
    print('cli_timer placeholder, elapsed', t.elapsed())

if __name__ == '__main__':
    main()
"""Top-level wrapper for scripts/manuals/cli_timer.py"""
from importlib import import_module
try:
    mod = import_module('Mycelium.scripts.manuals.cli_timer')
except Exception:
    # fallback: import by path
    from pathlib import Path
    import importlib.util
    alt = Path(__file__).resolve().parent.joinpath('scripts').joinpath('manuals').joinpath('cli_timer.py')
    if alt.exists():
        spec = importlib.util.spec_from_file_location('Mycelium._manuals_cli_timer', str(alt))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore
        mod = module
    else:
        raise

run_with_timer = getattr(mod, 'run_with_timer')
"""Proxy loader for scripts/manuals/cli_timer.py"""
import importlib

_mod = importlib.import_module('Mycelium.scripts.manuals.cli_timer')
for _k, _v in _mod.__dict__.items():
	if not _k.startswith('_'):
		globals()[_k] = _v

