import importlib.util
from pathlib import Path


def load_watcher():
    root = Path('.').resolve()
    mod_path = root.joinpath('Mycelium', 'scripts', 'python', 'watch_env_and_regen.py')
    spec = importlib.util.spec_from_file_location('watch_env_and_regen', str(mod_path))
    if spec is None or spec.loader is None:
        raise RuntimeError('Could not load watcher module')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_schedules_for_water_charge():
    root = Path('.')
    changed = root.joinpath('Player Root', 'variable', 'secondary_stat', 'environmental_water_charge.md')
    watcher = load_watcher()
    scheduled = watcher.scheduled_pcs_for_env(changed, vars_root=root.joinpath('Player Root', 'variable'), pcs_root=root.joinpath('Player Root', 'PCs'))
    # Anju's sheet contains 'Environmental water charge' and has Water level 2, so expect Anju
    assert 'Anju' in scheduled
    # scheduled list should only include PCs that actually reference the variable
    for pc in scheduled:
        assert (root.joinpath('Player Root', 'PCs', pc)).exists()
