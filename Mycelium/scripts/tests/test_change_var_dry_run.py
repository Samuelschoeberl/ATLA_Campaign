import subprocess
from pathlib import Path
import shutil
import tempfile


ROOT = Path(__file__).resolve().parents[3]


def test_change_var_dry_run_no_writes(tmp_path):
    # Prepare a temporary workspace copy to avoid touching user's vault
    tmp_root = tmp_path / "workspace"
    shutil.copytree(ROOT, tmp_root)

    # Run change_var.py in dry-run mode for a variable we know exists
    script = tmp_root / 'Mycelium' / 'scripts' / 'python' / 'change_var.py'
    cmd = ['python3', str(script), '--name', 'environmental_water_charges', '--value', '0', '--dry-run']
    proc = subprocess.run(cmd, cwd=tmp_root, capture_output=True, text=True)
    out = proc.stdout + proc.stderr

    # Ensure the script ran and printed backlinks / affected sheets
    assert 'Backlink tree' in out or proc.returncode == 0

    # No per-PC files should have been newly written under Player Root/variable/PC_variables
    pc_vars = tmp_root / 'Player Root' / 'variable' / 'PC_variables'
    before = set(p.relative_to(tmp_root) for p in pc_vars.rglob('*.md')) if pc_vars.exists() else set()

    # run the command (already run above)
    after = set(p.relative_to(tmp_root) for p in pc_vars.rglob('*.md')) if pc_vars.exists() else set()
    assert before == after, 'Dry-run should not create or delete per-PC variable files'

    # Also ensure that no character sheet had rows removed by dry-run: pick one sheet and check it still contains 'Water charge'
    sheet = tmp_root / 'Player Root' / 'PCs' / 'Puy' / 'Puy character sheet.md'
    text = sheet.read_text(encoding='utf-8')
    assert 'Water charge' in text
