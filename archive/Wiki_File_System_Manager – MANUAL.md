"""
Archived manual: Wiki_File_System_Manager – MANUAL.md
"""
try:
from pathlib import Path
src = Path('MANUALS') / 'Wiki_File_System_Manager – MANUAL.md'
if src.exists():
dst = Path(**file**).parent / 'Wiki_File_System_Manager.MANUAL.archived.md'
dst.write_text(src.read_text(encoding='utf-8'), encoding='utf-8')
except Exception:
pass
