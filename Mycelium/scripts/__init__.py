"""Mycelium scripts package.

This file intentionally left minimal to allow imports like
`import Mycelium.scripts.python.watch_and_regen`.
"""

# Keep this package minimal; alias the existing 'Python' subpackage as 'python'
# so imports using either case work on different environments.
try:
	from . import Python as python  # type: ignore
except Exception:
	# best-effort only
	python = None  # type: ignore
import sys
# Create a sys.modules alias so `import Mycelium.scripts.python` works even if
# the folder on disk is named 'Python' (common on macOS case-insensitive filesystems).
if python is not None:
	sys.modules.setdefault('Mycelium.scripts.python', python)

__all__ = []

