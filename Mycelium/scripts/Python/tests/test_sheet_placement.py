import tempfile
from pathlib import Path
import shutil

import importlib.util
from pathlib import Path as P

# load recreate_pcs module by file path so tests work from workspace root
ROOT = P('.').resolve()
mod_path = ROOT.joinpath('Mycelium', 'scripts', 'python', 'recreate_pcs.py')
spec = importlib.util.spec_from_file_location('recreate_pcs', str(mod_path))
recreate_pcs = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(recreate_pcs)
write_character_files = recreate_pcs.write_character_files


def test_placement_core_and_vital(tmp_path):
    out_root = tmp_path.joinpath('PCs')
    out_root.mkdir()
    # create a minimal template with markers
    tpl_dir = ROOT.joinpath('Mycelium', 'data', 'template')
    tpl_dir.mkdir(parents=True, exist_ok=True)
    tpl_path = tpl_dir.joinpath('template_Character_Sheet.md')
    tpl_path.write_text('''```markdown
# {{PC}} Character Sheet

## Core Stats

<!-- STATS_INSERT:core -->
| Field | Value |
|---|---:|

## Vital Stats

<!-- STATS_INSERT:vital -->
| Field | Value |
|---|---:|

## Other

<!-- STATS_INSERT:other -->
```
''', encoding='utf-8')

    kv_all = {'str': 4, 'dex': 2, 'max_hp': 20, 'custom.stat': 7}
    write_character_files('TestPC', kv_all, [], {}, out_root)
    sheet = out_root.joinpath('TestPC', 'TestPC character sheet.md')
    assert sheet.exists()
    txt = sheet.read_text(encoding='utf-8')
    assert '| Strength | 4 |' in txt
    assert '| Max Hp | 20 |' in txt or '| Max HP | 20 |' in txt
    assert 'custom.stat' in txt or 'Custom stat' in txt


def teardown_module(module):
    # cleanup the template we wrote
    tpl_dir = ROOT.joinpath('Mycelium', 'data', 'template')
    tpl_path = tpl_dir.joinpath('template_Character_Sheet.md')
    if tpl_path.exists():
        tpl_path.unlink()
