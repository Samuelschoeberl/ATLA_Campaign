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
        return variants
    # basic variants
    variants.add(s)
    variants.add(s.replace(' ', '_'))
    variants.add(s.lower())
    variants.add(s.upper())
    # remove the word 'bending' when present (e.g. 'Airbending' -> 'Air')
    no_bending = re.sub(r"\bbending\b", '', s, flags=re.IGNORECASE).strip()
    if no_bending and no_bending != s:
        variants.add(no_bending)
        variants.add(no_bending.replace(' ', '_'))
        variants.add(no_bending.lower())
    # common abbreviation expansions
    low = s.lower()
    if 'hitpoint' in low or 'hp' in low:
        variants.add(re.sub(r'hitpoints?', 'HP', s, flags=re.IGNORECASE))
        variants.add(re.sub(r'\bHP\b', 'Hitpoints', s, flags=re.IGNORECASE))
    if 'charge' in low:
        variants.add(s.replace('charges', 'Charges'))
    # handle Level/_Level suffix variants
    if s.endswith(' Level'):
        base = s[:-6].strip()
        variants.add(base)
        variants.add(base.replace(' ', '_'))
    if s.endswith('_Level'):
        base = s[:-6].strip()
        variants.add(base)
        variants.add(base.replace(' ', '_'))
    # also provide swapped variants
    variants.add(s.replace(' Level', '_Level'))
    variants.add(s.replace('_Level', ' Level'))
    return {v for v in variants if v}

def extract_tokens(expr):
    """Extract candidate identifier tokens from a formula expression string."""
    # simple fallback tokenization (words and wiki-links); main matching
    # will be performed by a greedy matcher in main() using known variants.
    tokens = []
    for m in re.findall(r"\[\[([^\]]+)\]\]", expr):
        s = m.strip()
        if s:
            tokens.append(s)
    # also include remaining word tokens
    cleaned = re.sub(r'[\[\]\(\)\{\}\|:,]', ' ', expr)
    cleaned = re.sub(r'[^A-Za-z0-9_ ]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    for w in cleaned.split(' '):
        if w:
            tokens.append(w)
    raw = [t.strip() for t in tokens if t]
    return raw


def extract_tokens_with_known_variants(expr, known_norms):
    """Greedy longest-match extraction using known normalized variants.
    Returns a list of candidate tokens (original substrings).
    """
    # pull out wiki-links first
    candidates = []
    links = re.findall(r"\[\[([^\]]+)\]\]", expr)
    for l in links:
        candidates.append(l.strip())
    # clean punctuation and split into words
    cleaned = re.sub(r'[\[\]\(\)\{\}\|:,]', ' ', expr)
    cleaned = re.sub(r'[^A-Za-z0-9_ ]', ' ', cleaned)
    words = [w for w in re.sub(r'\s+', ' ', cleaned).strip().split(' ') if w]
    i = 0
    n = len(words)
    while i < n:
        matched = False
        # try longest span
        for j in range(n, i, -1):
            span = ' '.join(words[i:j])
            norm = re.sub(r'[_\s]+', ' ', re.sub(r'[\[\]\(\)\{\}\|:,]', ' ', span)).strip().lower()
            # normalize bending removal
            norm = re.sub(r'\bbending\b', '', norm).strip()
            if norm in known_norms:
                candidates.append(span)
                i = j
                matched = True
                break
        if not matched:
            # fallback: take single word
            candidates.append(words[i])
            i += 1
    # dedupe while preserving order
    seen = set()
    out = []
    for t in candidates:
        tt = t.strip()
        if tt and tt not in seen:
            out.append(tt)
            seen.add(tt)
    return out
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

    # prepare mapping of normalized -> original keys for greedy matching
    known_norms = {v for v in defined_variants}
    for key, expr in formulas.items():
        # greedy extraction using known normalized keys reduces fragmentation
        tokens = extract_tokens_with_known_variants(expr, known_norms)
        for t in tokens:
            if t == key:
                continue
            found = False
            for v in normalize_variants(t):
                if v in defined_variants:
                    found = True
                    break
            if not found:
                # ignore pure numeric tokens
                if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", t):
                    continue
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