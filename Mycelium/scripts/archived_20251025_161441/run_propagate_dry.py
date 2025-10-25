# Temporary runner to invoke propagate_environmental_from_sheet in dry-run mode
from pathlib import Path
import sys

# ensure the directory is importable as a package root for relative imports
p = Path(__file__).resolve().parent
sys.path.insert(0, str(p))

import watch_and_regen as wr

class Args:
    dry_run = True
    create_placeholders = False

sheet = Path('Player Root/PCs/Anju/Anju character sheet.md')
vars_root = Path('Player Root/variable')
pcs_dir = Path('Player Root/PCs')
script = Path('Mycelium/scripts/python/recreate_pcs.py')

wr.propagate_environmental_from_sheet(sheet, vars_root, pcs_dir, script, Args())
