from pathlib import Path
from Mycelium.scripts.grow_utils import read_root_title


def test_read_root_title(tmp_path):
    p = tmp_path.joinpath('Root.md')
    p.write_text('\nPlayer Root\n')
    title = read_root_title(p)
    assert title == 'Player Root'
