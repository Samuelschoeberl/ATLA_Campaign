import json
import sys
from pathlib import Path

# make the repo root importable so tests can import Mycelium as a package
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

from Mycelium.extract_link_multipliers import compute_link_multipliers


def test_simple_file(tmp_path):
    p = tmp_path / 'sample.md'
    p.write_text('#idea #robotics\nThis is a test file referencing [[TargetA]] and [[TargetB]].\n#robotics here.\n')
    out = compute_link_multipliers(p)
    assert 'TargetA' in out['links']
    assert 'TargetB' in out['links']
    assert out['complexity'] >= 0
