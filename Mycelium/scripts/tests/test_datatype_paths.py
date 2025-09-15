import sys
from pathlib import Path
import tempfile
import shutil

import pytest

# Ensure the workspace root is importable so `from Mycelium import mycel_brain` works
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Mycelium import mycel_brain as mb


def test_load_datatype_paths_from_list(tmp_path: Path):
    hist = tmp_path.joinpath('Mycelium').joinpath('history')
    hist.mkdir(parents=True)
    p = hist.joinpath('datatype_paths.md')
    p.write_text("- #data:pagerank -> `Mycelium/pagerank.json`\n- #data:graphs -> `Mycelium/graphs/` (HTML)")

    # patch the FIXED_FOLDERS to point at our tmp history
    mb.FIXED_FOLDERS['history'] = hist
    mapping = mb.load_datatype_paths()
    assert 'data:pagerank' in mapping
    assert mapping['data:pagerank'].endswith('Mycelium/pagerank.json')
    assert 'data:graphs' in mapping
    assert mapping['data:graphs'].endswith('Mycelium/graphs/')


def test_show_path_cli(tmp_path: Path, capsys):
    hist = tmp_path.joinpath('Mycelium').joinpath('history')
    hist.mkdir(parents=True)
    p = hist.joinpath('data_referencetable.md')
    p.write_text("| #data:pagerank | desc | `Mycelium/pagerank.json` |\n")

    mb.FIXED_FOLDERS['history'] = hist
    rc = mb.cli(['--show-path', 'data:pagerank'])
    # cli should print the path and return 0
    assert rc == 0
