import pytest
from pathlib import Path
import importlib.util

# import the common module by path to ensure tests run independent of package layout
p = Path(__file__).resolve().parents[1].joinpath('common.py')
spec = importlib.util.spec_from_file_location('common', str(p))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)  # type: ignore[attr-defined]

common = mod


def test_to_number():
    assert common.to_number('42') == 42
    assert common.to_number(' 3.14 ') == pytest.approx(3.14)
    assert common.to_number('') == 0
    assert common.to_number(None) == 0
    assert common.to_number('abc 7 def') == 7


def test_safe_eval():
    assert common.safe_eval('1+2*3') == 7
    assert common.safe_eval('  ') == 0
    # unsupported or complex expression returns the original string or raises; ensure numeric case
    assert common.safe_eval('4/2') == 2


def test_read_var_value(tmp_path):
    f = tmp_path.joinpath('v.md')
    f.write_text('```markdown\n123\n\n#variable\n\n```\n')
    assert common.read_var_value(f) == '123'
    f2 = tmp_path.joinpath('v2.md')
    f2.write_text('#variable\n456\n')
    assert common.read_var_value(f2) == '456'


def test_parse_markdown_table(tmp_path):
    t = tmp_path.joinpath('tab.md')
    t.write_text('\n| Name | STR | CON |\n|---|---:|---:|\n| Anju | 12 | 14 |\n')
    hdr, rows = common.parse_markdown_table(t)
    assert 'Name' in hdr
    assert rows[0][0] == 'Anju'
