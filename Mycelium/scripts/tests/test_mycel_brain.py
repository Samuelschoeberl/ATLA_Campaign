import tempfile
from pathlib import Path
import shutil
import os
import sys

# ensure repo root is importable during tests (same pattern used elsewhere in the test suite)
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from Mycelium import mycel_brain


def test_generate_prompt_writes_file(tmp_path):
    root = tmp_path / 'vault'
    root.mkdir()
    # create two tagged files
    (root / 'a.md').write_text('#data\n\nThis is about mushrooms.')
    (root / 'b.md').write_text('Some intro\n\n#data\n\nMore content here.')

    out = tmp_path / 'out.md'
    rc = mycel_brain.cli(['--root', str(root), '--tags', 'data', '--goal', 'Summarize', '--out', str(out)])
    assert rc == 0
    assert out.exists()
    text = out.read_text(encoding='utf8')
    assert 'CONTEXT:' in text
    assert 'TASK:' in text
    assert 'Summarize' in text
import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

from Mycelium import mycel_brain as mb


def test_cluster_and_prompt(tmp_path):
    # create sample data file tagged #data under a mushroom folder
    d = tmp_path / 'Anju'
    d.mkdir()
    f = d.joinpath('sample.md')
    f.write_text('#data\nSample content\n')

    files = [f]
    mapping = mb.cluster_by_mushroom(files, tmp_path / 'out')
    assert 'Anju' in mapping

    # create a fake pagerank.json for prompt generation
    pr = tmp_path.joinpath('Mycelium')
    pr.mkdir()
    pagerank = pr.joinpath('pagerank.json')
    pagerank.write_text('{"Anju/sample.md": 0.5, "Other.md": 0.2}')

    prompt = mb.generate_prompt(tmp_path, tmp_path / 'out', top_n=2)
    assert prompt.exists()
    txt = prompt.read_text(encoding='utf-8')
    assert 'Mycelium generated prompt' in txt
