#!/usr/bin/env python3
from __future__ import annotations
"""Top-level CLI shim for char_formulas_check relocated into the
`WikiFileSystemManager.helpers` package.

This file intentionally contains no implementation. It only delegates to the
packaged helper to avoid duplication and static-import/type errors that
occur when the full implementation exists twice in the repo.
"""
import sys

try:
    from WikiFileSystemManager.helpers.char_formulas_check import main
except Exception as e:
    print('Error: packaged helper WikiFileSystemManager.helpers.char_formulas_check is not importable:', e)
    print('You can run the tool directly with: python -m WikiFileSystemManager.helpers.char_formulas_check')
    raise SystemExit(2)


if __name__ == '__main__':
    # preserve original CLI: optional path argument
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path is None:
        # consult config for default if available
        try:
            from config_loader import get_config
            path = get_config('char_formulas', 'char_formulas.json')
        except Exception:
            path = 'char_formulas.json'
    raise SystemExit(main(path))
#!/usr/bin/env python3
"""
char_formulas_check.py
Find identifiers referenced in char_formulas.json formulas that are not defined as keys.
Usage:
    python3 char_formulas_check.py [path/to/char_formulas.json]
"""

import json
import re
import sys
from collections import defaultdict
try:
    from config_loader import get_config
except Exception:
    def get_config(key, default):
        return default

# Match a word token optionally followed by space-separated word pieces (allows multi-word identifiers like
# 'Manually Rolled HP', but avoids greedy capture across multiple distinct tokens when punctuation/extra spaces present)
FORM_RE = re.compile(r'[A-Za-z][A-Za-z0-9_]*(?:\s+[A-Za-z0-9_]+)*')

def normalize_variants(name):
    """Return a set of plausible name variants for matching keys."""
    # remove common surrounding punctuation and normalize whitespace
    s = re.sub(r'[\[\]\(\)\{\}\|:,]', ' ', name)
    s = s.replace('-', ' ')
    s = re.sub(r'[_\s]+', ' ', s).strip()
    variants = set()
    if not s:
        #!/usr/bin/env python3
        """Compatibility shim for char_formulas_check moved into the WikiFileSystemManager package.

        This shim preserves the original CLI entrypoint `python3 char_formulas_check.py`.
        """
        from __future__ import annotations
        import sys
        try:
            from WikiFileSystemManager.helpers.char_formulas_check import main
        except Exception as e:
            print('Error: packaged helper WikiFileSystemManager.helpers.char_formulas_check is not importable:', e)
            print('Ensure the package is present and try running: python -m WikiFileSystemManager.helpers.char_formulas_check')
            raise SystemExit(2)

        if __name__ == '__main__':
            # preserve original CLI: optional path argument
            path = sys.argv[1] if len(sys.argv) > 1 else None
            if path is None:
                # consult config for default if available
                try:
                    from config_loader import get_config
                    path = get_config('char_formulas', 'char_formulas.json')
                except Exception:
                    path = 'char_formulas.json'
            raise SystemExit(main(path))