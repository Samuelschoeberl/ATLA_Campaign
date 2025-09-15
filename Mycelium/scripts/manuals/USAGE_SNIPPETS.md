tags: #manual

Ready-to-copy usage snippets (Python)

This file collects ready-to-copy Python snippets that call the top-level methods or CLI entry points discussed across the Mycelium manuals.

1. Call the generator for a single PC (equivalent to `recreate_pcs.py --pc <name>`):

```python
import subprocess
import sys
subprocess.run([sys.executable, 'Mycelium/scripts/python/recreate_pcs.py', '--pc', 'Anju'], check=True)
```

2. Call the watcher helper `propagate_environmental_from_sheet` (dry-run):

```python
from pathlib import Path
from argparse import Namespace
from Mycelium.scripts.python.watch_and_regen import propagate_environmental_from_sheet

propagate_environmental_from_sheet(
    Path('Player Root/PCs/Anju/Anju character sheet.md'),
    Path('Player Root/variable'),
    Path('Player Root/PCs'),
    Path('Mycelium/scripts/python/recreate_pcs.py'),
    Namespace(dry_run=True, create_placeholders=False)
)
```

3. Create a PC via `create_pc.py` and run update:

```python
import subprocess
import sys
subprocess.run([
    sys.executable, 'Mycelium/scripts/manuals/create_pc.py', '--name', 'Anju', '--water', '3', '--run-update'
], check=True)
```

4. Update or create a variable via `change_var.py` (dry-run example):

```python
import subprocess
import sys
subprocess.run([sys.executable, 'Mycelium/scripts/python/change_var.py', '--name', 'environmental_water_charge', '--value', '20', '--dry-run'], check=True)
```

5. Call `update_sheets_for_var.py` to update all dependent sheets for a variable:

```python
import subprocess, sys
subprocess.run([sys.executable, 'Mycelium/scripts/python/update_sheets_for_var.py', '--name', 'environmental_water_charge', '--verbose'], check=True)
```

Notes

- Replace paths with absolute paths or run from the repository root so the relative paths resolve as shown.
- Use `Namespace(dry_run=True, create_placeholders=False)` when calling helper functions directly to preview operations without writes.

#manual
