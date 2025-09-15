tags: #manual

Environmental variable propagation (sheet-authoritative)

This small document describes the sheet-authoritative propagation method used by
`Mycelium/scripts/python/watch_and_regen.py`.

Summary

- When a character sheet contains a table row labeled like `Environmental water charge`, the
  watcher compares that numeric value to the repository canonical variable files under
  `Player Root/variable/<stem>.md` and `Player Root/variable/secondary_stat/<stem>.md`.
- If the sheet value differs, the watcher treats the sheet as authoritative: it writes the
  canonical file(s) and propagates the new numeric value into other character sheets.
- The watcher avoids immediate flip-flops by tracking recent authoritative writes and
  skipping overwrites when the canonical file was updated more recently than the sheet.

Exposed function

The watcher exposes a top-level helper function you can call from other scripts or tests:

- `propagate_environmental_from_sheet(sheet_path, vars_root, pcs_dir, script, args)`

Parameters

- `sheet_path` (Path): path to the changed character sheet
- `vars_root` (Path): path to `Player Root/variable`
- `pcs_dir` (Path): path to `Player Root/PCs`
- `script` (Path): path to `recreate_pcs.py` (used by the watcher to schedule regenerations)
- `args`: argparse Namespace (only `--dry-run` and `--create-placeholders` are consulted)

Usage example (Python):

```python
from pathlib import Path
from Mycelium.scripts.python.watch_and_regen import propagate_environmental_from_sheet
from argparse import Namespace

sheet = Path('Player Root/PCs/Anju/Anju character sheet.md')
vars_root = Path('Player Root/variable')
pcs_dir = Path('Player Root/PCs')
script = Path('Mycelium/scripts/python/recreate_pcs.py')
args = Namespace(dry_run=True, create_placeholders=False)

propagate_environmental_from_sheet(sheet, vars_root, pcs_dir, script, args)
```

Notes

- This function follows the same semantics as the running watcher and respects the
  `--dry-run` flag (it will print what it would do).
- Manual editing of the canonical files will still be detected by the variable watcher
  and can trigger regenerations if PCs reference the variable.

#environmental_variable #manual
