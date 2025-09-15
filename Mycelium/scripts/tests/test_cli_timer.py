import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

from Mycelium.cli_timer import run_with_timer


def test_run_with_timer_output(capsys):
    def quick(x):
        return x * 2
    res = run_with_timer(quick, 3)
    captured = capsys.readouterr()
    assert res == 6
    assert '[Time] Total elapsed:' in captured.out
