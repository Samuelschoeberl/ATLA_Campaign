"""Wrapper for scripts/manuals/Wikigraphs.py"""
from importlib import import_module
import sys
from pathlib import Path
# Ensure repository root is on sys.path so 'Mycelium' package imports work
REPO_ROOT = Path(__file__).resolve().parents[3]
repo_str = str(REPO_ROOT)
if repo_str not in sys.path:
    sys.path.insert(0, repo_str)

try:
    mod = import_module('Mycelium.scripts.manuals.Wikigraphs')
except Exception:
    from pathlib import Path
    import importlib.util
    alt = Path(__file__).resolve().parent.joinpath('scripts').joinpath('manuals').joinpath('Wikigraphs.py')
    if alt.exists():
        spec = importlib.util.spec_from_file_location('Mycelium._manuals_Wikigraphs', str(alt))
        if spec is None or spec.loader is None:
            raise ImportError('could not load Wikigraphs module from file')
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

if __name__ == '__main__':
    # When executed directly, try to call the wrapped module's main() so
    # CLI arguments like --all/--verbose are handled by the underlying script.
    import sys
    target = None
    # prefer the module object 'mod' created earlier
    if 'mod' in globals():
        target = globals().get('mod')
    elif '_mod' in globals():
        target = globals().get('_mod')
    # If the module exposes a main() function, call it (it can read sys.argv).
    if target and hasattr(target, 'main') and callable(getattr(target, 'main')):
        try:
            target.main()
        except TypeError:
            # some mains accept argv; try passing args
            try:
                target.main(sys.argv[1:])
            except Exception as e:
                print('Wikigraphs main() raised:', e)
    elif 'main' in globals() and callable(globals()['main']):
        try:
            globals()['main']()
        except TypeError:
            try:
                globals()['main'](sys.argv[1:])
            except Exception as e:
                print('Wikigraphs main() raised:', e)
    else:
        print('No main() function found in Wikigraphs module; nothing to run.')

