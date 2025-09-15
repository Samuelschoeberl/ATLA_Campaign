import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

from Mycelium.pipeline_profiler_and_pagerank import write_scores_files


def test_write_scores_files(tmp_path):
    ranks = {'Note.md': 0.123456, 'Other.md': 0.5}
    out = tmp_path / 'unsorted'
    write_scores_files(ranks, out_dir=out)
    # check one file exists
    f = out.joinpath('Note.md_scores.md')
    assert f.exists()
    txt = f.read_text(encoding='utf-8')
    assert '#scores' in txt
    assert 'Pagerank' in txt