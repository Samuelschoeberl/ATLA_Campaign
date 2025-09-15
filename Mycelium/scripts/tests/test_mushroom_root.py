import subprocess
import sys
from pathlib import Path


def test_mushroom_tree_includes_absolute_root(tmp_path):
    repo_root = Path.cwd()
    script = repo_root.joinpath('Mycelium', 'scripts', 'grow_mushroom.py')
    assert script.exists(), f'grow_mushroom.py not found at {script}'

    outdir = tmp_path.joinpath('Root_mushroom_test')
    outdir.mkdir()

    cmd = [sys.executable, str(script), 'Root', '--outdir', str(outdir), '-v']
    # run the script; allow it to succeed or not but produce artifacts
    try:
        res = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired as e:
        # if the script times out, fail the test with diagnostics
        raise AssertionError(f'grow_mushroom.py timed out. stdout:\n{e.stdout}\nstderr:\n{e.stderr}')

    tree_file = outdir.joinpath('Root_clusters', 'mushroom_tree.md')
    assert tree_file.exists(), f'mushroom_tree.md not created; stdout:\n{res.stdout}\nstderr:\n{res.stderr}'

    txt = tree_file.read_text(encoding='utf-8')
    expected = repo_root.joinpath('Mycelium', 'data', 'variable', 'Root.md').resolve()
    assert str(expected) in txt, f'Expected absolute Root.md path {expected} not found in:\n{txt}'
