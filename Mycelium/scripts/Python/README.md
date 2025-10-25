````markdown
# Python Scripts Documentation

## sync_variables.py

Detects changes in character sheets and writes them back to their variable files.

### Usage

**One-time sync:**

```bash
# Sync all characters
python3 Mycelium/scripts/Python/sync_variables.py

# Sync a specific character
python3 Mycelium/scripts/Python/sync_variables.py --character Anju

# Dry run (show what would change without making changes)
python3 Mycelium/scripts/Python/sync_variables.py --dry-run
```

**Watch mode (continuously monitor for changes):**

```bash
# Watch all characters
python3 Mycelium/scripts/Python/sync_variables.py --watch

# Watch a specific character
python3 Mycelium/scripts/Python/sync_variables.py --watch --character Anju
```

### Example

When you change a line in a character sheet like:

```markdown
| current hp | 38 |
```

to:

```markdown
| current hp | 32 |
```

The script will automatically update the corresponding variable file (`Anju_current_hp.md`) to:

```markdown
32

#vitality #current_variable #variable_Anju #character_stat_Anju #character_stats_Anju #secondary_stat_Anju
```

### Supported Variables

The script syncs the following types of variables:

- **Vitals:** max_hp, current_hp, Initiative, Stress Level, Fire Damage Bonus
- **Core Stats:** Strength, Dexterity, Constitution, Intelligence, Wisdom, Charisma
- **Defensive:** Evasion, Barrier, General Armor, Physical Armor, Fire Armor, Ice Armor, Spirit Armor
- **Bending Slots:** waterbending slot, earthbending slot, firebending slot, airbending slot
- **Water Charges:** environmental_water_charge, Waterbottle Charge

---

## generate_stat_overview.py

This tiny script scans the repository for player stats and environmental
variable files and writes an aggregated Markdown file at
`Player Root/PCs/stat_overview.md`.

### How to run

Run with the same Python interpreter you use for the frontend server:

```bash
python3 Mycelium/scripts/Python/generate_stat_overview.py
```

### Integration with the frontend API

When the frontend calls the `/update_sheet/<pcname>` endpoint with
`propagate=true`, the server will call the repository's propagation helper
and (on success) attempt to run this generator so `stat_overview.md` stays up
to date. If generation fails, the API will return a warning in its JSON
response.

### Notes

- The generator is intentionally forgiving; it looks for common keys like
  `max_hp`, `current hp`, `evasion`, and `environmental water charge`.
- If you need stricter parsing or additional fields, modify
  `generate_stat_overview.py` accordingly.
````
