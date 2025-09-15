import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

import subprocess
from Mycelium.Wikigraphs import create_and_open_wrappers


def test_create_and_open_wrappers(tmp_path, monkeypatch):
    # prepare fake files
    sun = tmp_path / 'sun.html'
    tre = tmp_path / 'tre.html'
    sun.write_text('<html></html>')
    tre.write_text('<html></html>')

    calls = []

    def fake_run(cmd, check=False):
        calls.append(list(cmd))
        class R:
            returncode = 0
        return R()

    monkeypatch.setattr(subprocess, 'run', fake_run)

    # call helper
    create_and_open_wrappers('Players_Part', sun, tre)

    # assert that subprocess.run was called at least once and wrapper files created
    assert any('sun.html' in c[-1] or 'tre.html' in c[-1] for c in calls)
    # Check wrapper files exist in the Wikigraphs module's unsorted directory
    import Mycelium.Wikigraphs as W
    unsorted = Path(W.__file__).resolve().parent.joinpath('unsorted')
    assert (unsorted / 'graphs_Players_Part_wikigraph_sunburst.html.md').exists()
