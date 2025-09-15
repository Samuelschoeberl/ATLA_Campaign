import io
import sys
from pathlib import Path
from argparse import Namespace

import importlib.util
import importlib.machinery


def _load_propagate_function(module_path: Path):
    spec = importlib.util.spec_from_file_location('watch_and_regen', str(module_path))
    mod = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert loader is not None
    loader.exec_module(mod)
    return getattr(mod, 'propagate_environmental_from_sheet')


def test_propagate_env_dry_run_runs_without_error(tmp_path, capsys):
    """Call propagate_environmental_from_sheet in dry-run mode and assert it completes."""
    # create minimal fake structure
    repo_root = tmp_path
    pcs = repo_root / 'Player Root' / 'PCs' / 'Dummy'
    pcs.mkdir(parents=True)
    sheet = pcs / 'Dummy character sheet.md'
    sheet.write_text('| Environmental water charge | 42 |\n')
    vars_root = repo_root / 'Player Root' / 'variable'
    vars_root.mkdir(parents=True)
    # create a template file that has #environmental_variable tag so it is discovered
    env_dir = vars_root / 'environmental'
    env_dir.mkdir(parents=True)
    tpl = env_dir / 'environmental_water_charge.md'
    tpl.write_text('42\n\n#variable #template #environmental_variable #show_if_water_ge_1\n')

    # run the helper in dry-run mode; should not raise
    args = Namespace(dry_run=True, create_placeholders=False)
    module_path = Path.cwd() / 'Mycelium' / 'scripts' / 'python' / 'watch_and_regen.py'
    fn = _load_propagate_function(module_path)
    fn(sheet, vars_root, repo_root / 'Player Root' / 'PCs', Path('Mycelium/scripts/python/recreate_pcs.py'), args)
    # if we reach here without exception the test passes
