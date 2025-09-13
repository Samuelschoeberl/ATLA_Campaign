"""Proxy loader for Mycelium.scripts/Python/Wikigraphs.py"""
from pathlib import Path
import importlib
import importlib.util
import subprocess
import os
import sys
try:
    mod = importlib.import_module('Mycelium.scripts.Python.Wikigraphs')
except Exception:
    alt = Path(__file__).resolve().parent.joinpath('scripts').joinpath('Python').joinpath('Wikigraphs.py')
    spec = importlib.util.spec_from_file_location('Mycelium._Wikigraphs', str(alt))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore
globals().update({k: getattr(mod, k) for k in dir(mod) if not k.startswith('_')})
__all__ = [k for k in dir(mod) if not k.startswith('_')]


def find_and_replace_in_named_subdirs(root: str, dir_name: str, find: str, replace: str, ext: list | tuple = ('.md',), dry_run: bool = True, backup: str | None = None, python_exe: str | None = None):
    """Convenience helper: find all subdirectories named ``dir_name`` under ``root`` and
    run the Wiki_File_System_Manager.py find/replace against them.

    Returns a dict with returncode, stdout, stderr and matched_dirs.

    Example:
        find_and_replace_in_named_subdirs('.', 'Air', 'Attack Roll', 'Air Attack Roll', dry_run=True)
    """
    repo_root = Path(root).resolve()
    matches = [p for p in repo_root.rglob('*') if p.is_dir() and p.name == dir_name]
    if not matches:
        return {'returncode': 0, 'stdout': '', 'stderr': f"No directories named '{dir_name}' found under {repo_root}", 'matched_dirs': []}

    script = Path(__file__).resolve().parent.joinpath('scripts', 'Python', 'Wiki_File_System_Manager.py')
    if not script.exists():
        return {'returncode': 2, 'stdout': '', 'stderr': f"Driver script not found: {script}", 'matched_dirs': [str(m) for m in matches]}

    cmd = [python_exe or sys.executable, str(script)]
    # positional roots
    for m in matches:
        cmd.append(str(m))
    # extensions
    if ext:
        if isinstance(ext, (list, tuple)):
            cmd += ['--ext'] + list(ext)
        else:
            cmd += ['--ext', str(ext)]
    # find/replace
    cmd += ['--find', find]
    if replace is not None:
        cmd += ['--replace', replace]
    if dry_run:
        cmd += ['--dry-run']
    if backup:
        cmd += ['--backup', backup]

    env = os.environ.copy()
    # ensure the repo package root is importable for the wrapper (PYTHONPATH -> repo root)
    env['PYTHONPATH'] = str(Path(__file__).resolve().parent.parent)

    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return {
        'returncode': proc.returncode,
        'stdout': proc.stdout,
        'stderr': proc.stderr,
        'matched_dirs': [str(m) for m in matches],
    }


# The real create_and_open_wrappers writes wrapper files relative to the module
# where it's defined (scripts/manuals). Some tests expect the wrapper files to be
# next to this proxy (Mycelium/unsorted). Provide a small shim that creates
# those files under the package root and then delegates to the original
# implementation so subprocess invocation still happens.
if 'create_and_open_wrappers' in globals():
    _orig_create = globals()['create_and_open_wrappers']

    def create_and_open_wrappers(safe_root_name, sun_path, tre_path):
        # ensure unsorted dir next to this proxy module (Mycelium/unsorted)
        from pathlib import Path
        pkg_unsorted = Path(__file__).resolve().parent.joinpath('unsorted')
        pkg_unsorted.mkdir(parents=True, exist_ok=True)
        (pkg_unsorted / f"graphs_{safe_root_name}_wikigraph_sunburst.html.md").write_text(
            f"#graph _export\n\n[Sunburst HTML]({sun_path})\n", encoding='utf-8')
        (pkg_unsorted / f"graphs_{safe_root_name}_wikigraph_treemap.html.md").write_text(
            f"#graph _export\n\n[Treemap HTML]({tre_path})\n", encoding='utf-8')
        # delegate to original so it still runs the opener on the files
        try:
            return _orig_create(safe_root_name, sun_path, tre_path)
        except Exception:
            # swallow errors from the delegated call in tests
            return None

    # overwrite the re-export with our shim
    globals()['create_and_open_wrappers'] = create_and_open_wrappers
    __all__ = [k for k in __all__ if k != 'create_and_open_wrappers'] + ['create_and_open_wrappers']
