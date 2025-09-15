import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

from Mycelium.pipeline_profiler_and_pagerank import build_weighted_graph_from_md

import json


def test_build_graph_with_extractors(tmp_path):
    # create a simple md file that links to TargetA
    src = tmp_path / 'Note.md'
    src.write_text('This references [[TargetA]]')
    # create TargetA file so name resolution can find it
    targ = tmp_path / 'TargetA.md'
    targ.write_text('content')

    # create multipliers file for Note.md
    mult = tmp_path / 'Note.md.multipliers.json'
    payload = {'source': str(src), 'tags': [], 'links': {'TargetA': {'occurrences': [0], 'multiplier': 3.0}}, 'complexity': 0.1}
    mult.write_text(json.dumps(payload), encoding='utf-8')

    # run build with and without extractors
    adj_no = build_weighted_graph_from_md(root=tmp_path, use_extractors=False)
    adj_yes = build_weighted_graph_from_md(root=tmp_path, use_extractors=True)
    # find src key in adjacency
    src_key = next(iter(adj_no.keys()))
    # locate target key by stem matching
    def find_weight(adjacency, srck, stem):
        for k, v in adjacency[srck].items():
            if Path(k).stem.lower() == stem.lower() or k.lower() == stem.lower():
                return v
        return None

    w_no = find_weight(adj_no, src_key, 'TargetA')
    w_yes = find_weight(adj_yes, src_key, 'TargetA')
    assert w_no is not None and w_yes is not None
    # multiplier should increase the weight; exact factor varies due to proximity/complexity boosts
    assert w_yes > w_no
    ratio = w_yes / w_no
    # Accept noisy ratio within 50% of requested multiplier (3.0)
    assert abs(ratio - 3.0) / 3.0 < 0.5
