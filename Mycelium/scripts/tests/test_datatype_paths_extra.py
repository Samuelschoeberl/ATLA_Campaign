import sys
from pathlib import Path

import pytest

# Ensure workspace root is importable
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Mycelium import mycel_brain as mb


def test_missing_tag_returns_nonzero(tmp_path: Path):
    hist = tmp_path.joinpath('Mycelium').joinpath('history')
    hist.mkdir(parents=True)
    # create a mapping for a different tag
    p = hist.joinpath('datatype_paths.md')
    p.write_text("- #data:pagerank -> `Mycelium/pagerank.json`\n")

    mb.FIXED_FOLDERS['history'] = hist
    rc = mb.cli(['--show-path', 'data:missing'])
    # should return non-zero when no canonical path exists
    assert rc == 2


def test_parse_parenthetical_and_table(tmp_path: Path):
    hist = tmp_path.joinpath('Mycelium').joinpath('history')
    hist.mkdir(parents=True)
    p1 = hist.joinpath('datatype_paths.md')
    p1.write_text("- #data:graphs -> `Mycelium/graphs/` (HTML preview)\n")

    p2 = hist.joinpath('data_referencetable.md')
    # table with backticked path in last column
    p2.write_text("| #data:complex | some desc | `Mycelium/complex/path.json` |\n")

    mb.FIXED_FOLDERS['history'] = hist
    mapping = mb.load_datatype_paths()
    assert 'data:graphs' in mapping
    assert mapping['data:graphs'].endswith('Mycelium/graphs/')
    assert 'data:complex' in mapping
    assert mapping['data:complex'].endswith('Mycelium/complex/path.json')


def test_get_canonical_path_absolute_and_relative(tmp_path: Path):
    hist = tmp_path.joinpath('Mycelium').joinpath('history')
    hist.mkdir(parents=True)

    # absolute path entry
    abs_dir = tmp_path.joinpath('absgraphs')
    abs_dir.mkdir()
    p_abs = hist.joinpath('data_referencetable.md')
    p_abs.write_text(f"| #data:absgraphs | desc | `{abs_dir}` |\n")

    # relative path entry
    rel_md = hist.joinpath('datatype_paths.md')
    rel_md.write_text("- #data:relgraphs -> `Mycelium/graphs/`\n")

    # create the relative target so resolution is clearer
    (tmp_path.joinpath('Mycelium').joinpath('graphs')).mkdir(parents=True)

    mb.FIXED_FOLDERS['history'] = hist

    p1 = mb.get_canonical_path('data:absgraphs', root=tmp_path)
    assert p1 is not None
    assert p1.resolve() == abs_dir.resolve()

    p2 = mb.get_canonical_path('data:relgraphs', root=tmp_path)
    assert p2 is not None
    # should resolve under the provided root
    assert str(tmp_path.joinpath('Mycelium').joinpath('graphs')) in str(p2)
