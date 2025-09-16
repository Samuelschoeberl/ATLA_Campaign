"""Proxy script that delegates to Mycelium/scripts/Python/mycelium_grow_mushroom.py
so tests that expect `Mycelium/scripts/grow_mushroom.py` to exist can run it.
"""
from pathlib import Path
import runpy
import sys

alt = Path(__file__).resolve().parent.joinpath('Python').joinpath('mycelium_grow_mushroom.py')
if alt.exists():
    runpy.run_path(str(alt), run_name='__main__')
else:
    print('grow_mushroom.py not found', file=sys.stderr)
    raise SystemExit(2)
