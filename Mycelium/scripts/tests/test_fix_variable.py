import json
from pathlib import Path
import subprocess


def test_fix_variable_auto_pick(tmp_path, capsys):
    # Create a small repo structure
    repo = tmp_path
    (repo / 'Mycelium').mkdir()
    # three candidate variable files
    a = repo / 'Danger Sense Reaction.md'
    b = repo / 'Danger Sense Reaction (alt).md'
    c = repo / 'Danger Sense Reaction (old).md'
    # mark them as variables
    a.write_text('#variable\n#character_stat\n', encoding='utf-8')
    b.write_text('#variable\n', encoding='utf-8')
    c.write_text('#variable\n', encoding='utf-8')
    # pagerank.json prefers the second file (b)
    pr = {
        str(b.name): 0.9,
        str(a.name): 0.1,
        str(c.name): 0.05
    }
    (repo / 'Mycelium' / 'pagerank.json').write_text(json.dumps(pr), encoding='utf-8')

    # run mycelium_ctl fix-variable in dry-run auto-pick mode
    cmd = ['python3', str(Path.cwd() / 'mycelium_ctl.py'), 'fix-variable', 'Danger Sense Reaction', '--dry-run', '--auto-pick']
    # run in tmp repo as CWD
    res = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True)
    out = res.stdout + res.stderr
    assert 'Marking' in out and 'PRIMARY' in out or 'would write tags' in out
