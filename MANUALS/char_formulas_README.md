Character Formulas (README)

## Summary

Formulas used by `update_char.py` live in `char_formulas.json`. The default
formulas provide common derived stats such as Max Hit Points, Evasion and
Armor. The updater will add missing defaults if it detects candidate keys in
the workspace.

If you edit `char_formulas.json`, keep expressions simple and safe. The
updater supports a limited, safe expression evaluator (no arbitrary code
execution).

## Workflows

1. Validate formulas file quickly

```bash
python3 char_formulas_check.py char_formulas.json
```

2. Add a default for a missing key and test on one sheet

```bash
# edit char_formulas.json
python3 update_char.py --file "Players Part/PCs/Anju/Anju Character Sheet.md" --formulas char_formulas.json --extend-formulas
```

3. Run across all PCs as a batch

```bash
python3 update_char.py --sync --input pcs_input.md
```

# See MANUALS/Usage_Guide.md for a short summary of all manuals

# char_formulas conventions (short)

This document explains the recommended canonical naming for keys used in `char_formulas.json` and a short summary of how `char_formulas_check.py` matches tokens.

## Canonical key naming (recommendation)

- Use human-friendly Title Case for formula keys that correspond to sheet labels: e.g. `Air Level`, `Manually Rolled HP`, `Waterbending Level`.
- Avoid mixing many variants in the JSON; prefer one canonical key and add a minimal alias only when necessary for backward compatibility.
- Prefer explicit names for single concepts (e.g., `HP_PER_CL` or `Manually Rolled HP`) and map them consistently in `char_formulas.json`.

Examples:

- `Air Level` -> canonical name for a character's air level.
- `Waterbending Level` -> water level (if you prefer `Water Level` use it consistently across sheets and formulas).
- `Manually Rolled HP` -> total manually rolled HP (add an alias like `Manually_Rolled_Hitpoints` only if needed).

## Checker heuristics (how `char_formulas_check.py` works)

- The checker normalizes tokens before matching:
  - Strips common wiki/markdown punctuation (`[[`, `]]`, `(`, `)`, `|`, `:`, `,`, etc.).
  - Collapses underscores and whitespace into canonical spaced/underscore variants.
  - Removes the substring `bending` for matching convenience (so `Airbending` ↔ `Air`).
  - Generates variants: original, spaced, underscored, lowercased, and no-`bending` variants.
- Greedy longest-match extraction: the checker attempts to match longest multi-word spans against known normalized keys to reduce fragmentation (so `Manually Rolled HP` is matched as a single token, not three separate tokens).
- Numeric tokens are ignored in missing-identifier reports.

## How to run

- From the repo root:

```bash
python3 char_formulas_check.py char_formulas.json
```

The script prints any tokens referenced by formulas that are not matched by the defined keys or their normalized variants.

## Tips

- When adding a new sheet label or column in `pcs_input.md`, add the same key (or a minimal alias) to `char_formulas.json` so formulas referencing that label resolve.
- If you choose to rename keys to `snake_case` or another convention, update both `char_formulas.json` and any sheet/template files to match; the checker will still attempt many common variants but consistency reduces surprises.
