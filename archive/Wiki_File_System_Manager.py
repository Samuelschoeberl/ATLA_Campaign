"""Archived original Wiki_File_System_Manager.py preserved for history."""
from pathlib import Path
orig = Path('Wiki_File_System_Manager.py')
if orig.exists():
    try:
        text = orig.read_text(encoding='utf-8')
        (Path(__file__).parent / 'Wiki_File_System_Manager.original.py').write_text(text, encoding='utf-8')
    except Exception:
        pass
