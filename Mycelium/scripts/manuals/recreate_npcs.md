Recreate NPCs — CLI manual

Summary

This manual documents the command-line interface for the `recreate_npcs.py` generator, which creates NPC character sheets and personalized bending rules from the NPC primary stats table.

recreate_npcs.py

Purpose

- Recompute per-NPC secondary stats from templates under `Dms Root/variable/secondary_stat` (or falls back to `Player Root/variable/secondary_stat` if not present)
- Generate personalized character sheets with `{{...}}` placeholder substitution
- Create per-NPC bending rules folders filtered by element proficiency levels
- Write per-NPC variable files into `Dms Root/variable/NPC_variables/<NPC>/`

Location

- `Mycelium/scripts/Python/recreate_npcs.py`

Usage

- Run for all NPCs with run-update flag set in `Dms Root/Npc_primary_stats.md`:

  python3 Mycelium/scripts/Python/recreate_npcs.py [--create-placeholders] [--verbose]

- Run for a single NPC:

  python3 Mycelium/scripts/Python/recreate_npcs.py --npc "low_earth"

Options

- --verbose, -v: print detailed per-stat evaluation traces and multi-pass resolution logs
- --npc, -n: limit generation to a single NPC name (case-insensitive exact match)
- --create-placeholders: create a minimal `#variable` placeholder file for any referenced variable that doesn't exist yet
- --propagate-variable, -P: only regenerate NPCs affected by this variable (stem or filename without .md)

Behavior notes

- The script always uses `Dms Root/variable/` for NPC generation, completely independent from Player Root
- Variable templates are loaded from `Dms Root/variable/` folders, with fallback to `Player Root/variable/` if templates don't exist in Dms Root
- Per-NPC variable files are written to `Dms Root/variable/NPC_variables/<NPC>/` with filenames prefixed by `<NPC>_<originalstem>.md`
- All tags in generated files are suffixed with the NPC name (e.g., `#earthbending_low_earth`) to distinguish from PC tags
- The generator uses a safe AST-based evaluator for formulas, matching the PC script behavior
- Character sheets use the template at `Mycelium/data/template/template_Character_Sheet.md` if present
- `{{placeholder}}` substitution works identically to the PC script:
  - Core stats (STR, DEX, etc.) are inserted into `<!-- STATS_INSERT:core -->` sections
  - Vital stats (HP, Evasion, etc.) go into `<!-- STATS_INSERT:vital -->` sections
  - Bending levels go into `<!-- STATS_INSERT:bending -->` sections
  - Other computed stats go into `<!-- STATS_INSERT:other -->` sections

Bending Rules Generation

- Creates `<NPC_folder>/Bending Rules - <NPC>/` with personalized moves
- Only includes moves matching the NPC's element proficiency levels:
  - Level requirements use `>=` logic (e.g., earth=2 gets both Level 1 and Level 2 moves)
  - Level ranges like `#level2-4` are properly handled
- Excludes signature moves unless tagged with the specific NPC name
- Variable substitution in moves shows both the variable name and value: `[[earthbending slot]] (3)`
- Creates action-type organization in `Bending Moves by Action Type - <NPC>/`:
  - Action
  - Bonus Action
  - Reaction
  - Danger Sense Reaction
- Always includes shared core rules folder
- Checks both `Dms Root/Rules/Bending Rules` and `Player Root/Rules/Bending Rules`

Output Structure

For each NPC, the script creates:

```
Dms Root/NPCs/<NPC>/
├── <NPC> character sheet.md
├── Bending Rules - <NPC>/
│   ├── core rules/ (copied from shared rules)
│   ├── <Element>/
│   │   └── <Element>bending Moves/
│   │       ├── Level 1/
│   │       └── Level 2/
└── Bending Moves by Action Type - <NPC>/
    ├── Action/
    ├── Bonus Action/
    └── Reaction/
```

Variable files:
```
Dms Root/variable/NPC_variables/<NPC>/
├── <NPC>_str.md
├── <NPC>_dex.md
├── <NPC>_max_hp.md
├── <NPC>_earthbending_slot.md
└── ... (all computed stats)
```

Differences from PC Script

- **No Root.md dependency**: Always uses Dms Root, never reads Root.md
- **NPC-specific tags**: All tags suffixed with NPC name (e.g., `#npc_stat_low_earth`)
- **Separate variable storage**: NPCs stored in `NPC_variables/` subfolder
- **Dual source checking**: Can use templates from either Dms Root or Player Root
- **Signature moves**: Excluded unless explicitly tagged with the NPC's name

Examples

- Generate all NPCs:
  ```bash
  python3 Mycelium/scripts/Python/recreate_npcs.py
  ```

- Generate specific NPC with verbose output:
  ```bash
  python3 Mycelium/scripts/Python/recreate_npcs.py --npc "low_earth" --verbose
  ```

- Regenerate only NPCs affected by a variable change:
  ```bash
  python3 Mycelium/scripts/Python/recreate_npcs.py --propagate-variable "earthbending_slot"
  ```

Troubleshooting

- If no NPCs are generated, check that the "Run Update" column in `Dms Root/Npc_primary_stats.md` is set to "yes"
- If character sheets have unreplaced `{{placeholders}}`, ensure the variable exists in the NPC's computed stats
- If bending moves are missing, verify:
  - The NPC has the required element level (e.g., earth >= 1 for Level 1 moves)
  - The move files have proper `#level` and element tags
  - Move files exist in either `Dms Root/Rules/Bending Rules` or `Player Root/Rules/Bending Rules`

Contact

- This manual is generated automatically. For exact behavior, inspect `Mycelium/scripts/Python/recreate_npcs.py`.
