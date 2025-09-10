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

FORM_RE = re.compile(r'[A-Za-z][A-Za-z0-9_ ]*')

def normalize_variants(name):
    """Return a set of plausible name variants for matching keys."""
    s = name.strip()
    variants = set()
    variants.add(s)
    variants.add(s.replace(' ', '_'))
    variants.add(s.replace('_', ' '))
    # different casing
    variants.add(s.lower())
    variants.add(s.upper())
    # remove 'bending' (Airbending_Level <-> Air Level)
    variants.add(s.replace('bending', '').replace('__','_').strip())
    # add or remove suffix '_Level' / ' Level'
    if 'Level' in s:
        variants.add(s.replace('Level', 'Level').strip())
    if s.endswith('_Level'):
        variants.add(s.replace('_Level', ' Level'))
    if s.endswith(' Level'):
        variants.add(s.replace(' Level', '_Level'))
    return {v for v in variants if v}

def extract_tokens(expr):
    """Extract candidate identifier tokens from a formula expression string."""
    raw = FORM_RE.findall(expr)
    # Filter out purely-numeric and common words
    tokens = []
    for t in raw:
        t = t.strip()
        if not t:
            continue
        if re.fullmatch(r'\d+(\.\d+)?', t):
            continue
        # skip common function/word tokens if any
        if t.lower() in {'and', 'or', 'not'}:
            continue
        tokens.append(t)
    return tokens

def main(path):
    with open(path, 'r', encoding='utf-8') as f:
        formulas = json.load(f)

    defined = set(formulas.keys())
    # also normalize defined variants for lookup
    defined_variants = set()
    for k in defined:
        defined_variants.update(normalize_variants(k))

    missing = defaultdict(set)  # token -> set(of formulas that reference it)

    for key, expr in formulas.items():
        tokens = extract_tokens(expr)
        for t in tokens:
            # skip self references and tokens that are same as the key or literal names like CL that are also keys
            if t == key:
                continue
            # try matching against defined variants
            found = False
            for v in normalize_variants(t):
                if v in defined_variants:
                    found = True
                    break
            if not found:
                missing[t].add(key)

    if not missing:
        print("No missing identifiers found — all tokens referenced in formulas are defined (or matched by heuristic variants).")
        return 0

    print("Missing identifiers referenced by formulas (token -> referenced-from-keys):\n")
    for token, from_keys in sorted(missing.items()):
        print(f"  {token!r} -> referenced in: {', '.join(sorted(from_keys))}")
    print("\nHints:")
    print(" - Tokens like 'Air Level' and 'Airbending_Level' are treated as different; consider adding aliases or normalizing names.")
    print(" - If the missing identifier is a column in `pcs_input.md` (e.g. 'Manually Rolled HP'), consider adding a mapping key or renaming consistently.")
    return 0

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'char_formulas.json'
    sys.exit(main(path))