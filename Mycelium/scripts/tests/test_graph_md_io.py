import sys
from pathlib import Path
import json

# make repo importable
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

from Mycelium import graph_md_io as g


def test_safe_filename():
    assert g._safe_filename('A/B:C*D?') == 'A_B_C_D_'
    assert g._safe_filename('') == 'node'


def test_write_and_read_md_table(tmp_path):
    rows = [{'id': '1', 'name': 'Root', 'meta': {'x': 1}}, {'id': '2', 'name': 'Child', 'meta': {'x': 2}}]
    p = tmp_path / 'nodes.md'
    g.write_md_table(rows, str(p), index_field='id')
    parsed = g.read_md_table(str(p))
    assert any(r['name'] == 'Root' for r in parsed)
    # meta should be parsed back as dict
    assert isinstance(parsed[0]['meta'], dict)


def test_json_to_flat_md(tmp_path):
    js = {'nodes': [{'id': '1', 'name': 'A'}, {'id': '2', 'name': 'B'}], 'edges': [{'source': '1', 'target': '2', 'weight': 3}]}
    in_file = tmp_path / 'g.json'
    in_file.write_text(json.dumps(js), encoding='utf-8')
    out_dir = tmp_path / 'out'
    written = g.json_to_flat_md(str(in_file), str(out_dir))
    assert len(written) == 2


def test_read_md_table_empty(tmp_path):
    p = tmp_path / 'empty.md'
    p.write_text('')
    parsed = g.read_md_table(str(p))
    assert parsed == []


def test_read_md_table_numeric_coercion(tmp_path):
    txt = '| id | value |\n| --- | --- |\n| a | 123 |\n| b | 4.56 |\n'
    p = tmp_path / 'nums.md'
    p.write_text(txt)
    rows = g.read_md_table(str(p))
    assert isinstance(rows[0]['value'], int) and rows[0]['value'] == 123
    assert isinstance(rows[1]['value'], float) and abs(rows[1]['value'] - 4.56) < 1e-9


def test_safe_filename_collision(tmp_path):
    # two nodes with same display name should create unique filenames
    js = {'nodes': [{'id': '1', 'name': 'Same'}, {'id': '2', 'name': 'Same'}], 'edges': []}
    in_file = tmp_path / 'g2.json'
    in_file.write_text(json.dumps(js), encoding='utf-8')
    out_dir = tmp_path / 'out2'
    written = g.json_to_flat_md(str(in_file), str(out_dir))
    names = [Path(p).name for p in written]
    assert any('Same.md' == n for n in names)
    assert any(n.startswith('Same-') for n in names)


def test_md_files_to_json_edge_shapes(tmp_path):
    # create edges.md with 'value' and 'weight' variants
    nodes = tmp_path / 'nodes.md'
    edges = tmp_path / 'edges.md'
    nodes.write_text('| id | name |\n| --- | --- |\n| 1 | A |\n')
    edges.write_text('| src | dst | value |\n| --- | --- | --- |\n| 1 | 2 | 5 |\n| 1 | 3 | 2.5 |\n')
    gjson = g.md_files_to_json(str(nodes), str(edges))
    assert 'links' in gjson
    assert any(isinstance(e.get('weight'), (int, float)) for e in gjson['links'])
