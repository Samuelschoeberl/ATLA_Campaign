import subprocess
import sys
from pathlib import Path


def write_file(p: Path, content: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')


def test_change_var_triggers_update_and_per_pc_files(tmp_path):
    """Integration-style test: run change_var to change environmental_water_charges and
    ensure the exact file in Player Root/variable/secondary_stat is updated, then the
    stub updater is invoked which updates Water_charge.md and writes per-PC files.
    """
    root = tmp_path
    # create minimal Player Root structure
    var_sec = root / 'Player Root' / 'variable' / 'secondary_stat'
    write_file(var_sec / 'water_charge.md', '```markdown\n0\n\n#variable\n\n```\n')

    # create one PC so stub will create per-pc files
    pc_dir = root / 'Player Root' / 'PCs' / 'Anju'
    write_file(pc_dir / 'Anju character sheet.md', '| Name | Value |\n|---|---|\n| Water Charge | 0 |')

    # copy change_var.py from repo into tmp project
    repo_change = Path(__file__).resolve().parents[1] / 'Mycelium' / 'scripts' / 'python' / 'change_var.py'
    target_change = root / 'Mycelium' / 'scripts' / 'python' / 'change_var.py'
    write_file(target_change, repo_change.read_text(encoding='utf-8'))

    # write a stub update_sheets_for_var that simulates updating dependent templates and per-pc files
    stub_updater = root / 'Mycelium' / 'scripts' / 'python' / 'update_sheets_for_var.py'
    stub_code = '''#!/usr/bin/env python3
import argparse
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--name', '-n', required=True)
    args = p.parse_args()
    ROOT = Path('.').resolve()
    # update Water_charge.md to indicate it was changed
    wc = ROOT.joinpath('Player Root','variable','secondary_stat','Water_charge.md')
    wc.parent.mkdir(parents=True, exist_ok=True)
    wc.write_text("""```markdown
17

#variable

```
""", encoding='utf-8')
    # create per-pc file for any PC found
    pcs_root = ROOT.joinpath('Player Root','PCs')
    for pc in pcs_root.iterdir():
        if pc.is_dir():
            perpc = ROOT.joinpath('Player Root','variable','PC_variables', pc.name)
            perpc.mkdir(parents=True, exist_ok=True)
            f = perpc.joinpath(f"{pc.name}_Water_charge.md")
            f.write_text("""```markdown
17

#variable #character_stat

```
""", encoding='utf-8')

if __name__ == '__main__':
    main()
'''
    write_file(stub_updater, stub_code)

    # run change_var in the tmp project
    cmd = [sys.executable, 'Mycelium/scripts/python/change_var.py', '-n', 'environmental_water_charges', '-v', '7']
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    print(proc.stdout)
    print(proc.stderr, file=sys.stderr)
    assert proc.returncode == 0

    # check the exact variable file was created/updated
    env_file = root / 'Player Root' / 'variable' / 'environmental_water_charges.md'
    assert env_file.exists()
    txt = env_file.read_text(encoding='utf-8')
    assert '7' in txt

    # stub updater should have written Water_charge.md
    wc = root / 'Player Root' / 'variable' / 'secondary_stat' / 'Water_charge.md'
    assert wc.exists()
    assert '17' in wc.read_text(encoding='utf-8')

    # per-pc file should exist
    perpc = root / 'Player Root' / 'variable' / 'PC_variables' / 'Anju' / 'Anju_Water_charge.md'
    assert perpc.exists()
    assert '17' in perpc.read_text(encoding='utf-8')
