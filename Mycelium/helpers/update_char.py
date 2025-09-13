from pathlib import Path
import importlib
import importlib.util
try:
    mod = importlib.import_module('Mycelium.scripts.helpers.update_char')
except Exception:
    alt = Path(__file__).resolve().parent.joinpath('..').joinpath('scripts').joinpath('helpers').joinpath('update_char.py').resolve()
    spec = importlib.util.spec_from_file_location('Mycelium.helpers._update_char', str(alt))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore
# Re-export all attributes (including private helpers) so tests can access
# internal functions like _find_note_for_label during unit tests.
globals().update({k: getattr(mod, k) for k in dir(mod)})
__all__ = [k for k in dir(mod)]
