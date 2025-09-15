import tempfile
import os
import json
from pathlib import Path

from Mycelium.Wiki_File_System_Manager import build_graph
from Mycelium.graph_md_io import json_to_flat_md


def run_smoke():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Create Mycelium folder that should be excluded
        (root / 'Mycelium').mkdir()
        (root / 'Mycelium' / 'ignore.md').write_text('#ignore\n')
        # Create two files that link to each other
        a = root / 'A.md'
        b = root / 'B.md'
        a.write_text('[[B]]\n')
        b.write_text('[[A]]\n')

        # Build graph using these candidate files
        candidates = [a, b, root / 'Mycelium' / 'ignore.md']
        g = build_graph([root], candidates)
        # Ensure no node ids for Mycelium file
        assert not any('Mycelium' in v for v in g['nodes'].values())
        # Ensure reciprocal edges exist and bidirectional flag on mirrored edges
        has_pair = False
        for e in g['edges']:
            if e.get('type') == 'wikilink' and any((ee.get('src') == e.get('dst') and ee.get('dst') == e.get('src')) for ee in g['edges']):
                has_pair = True
        assert has_pair

        # Persist graph to a temporary json and convert to flat md
        jp = root / 'g.json'
        jp.write_text(json.dumps(g))
        outdir = root / 'flat'
        outdir.mkdir()
        files = json_to_flat_md(str(jp), str(outdir))
        # Ensure printed files exist
        assert any('A' in p or 'B' in p for p in files)

    print('SMOKE_OK')


if __name__ == '__main__':
    run_smoke()
