# Variable File Writing Mechanism — Deep Dive

## Overview

This document explains how `recreate_pcs.py` writes variable files, particularly focusing on:
1. **Tag transformation** from template sources to generated files
2. **File format** and directory structure
3. **Special handling** for different variable types

---

## Variable File Directory Structure

### Location

```
Player Root/
└── variable/
    ├── secondary_stat/           (← Source templates)
    │   ├── max_hp.md
    │   ├── current_hp.md
    │   └── ...
    └── PC_variables/            (← Generated output)
        ├── Anju/
        │   ├── Anju_max_hp.md
        │   ├── Anju_current_hp.md
        │   └── ...
        ├── Tai/
        │   ├── Tai_max_hp.md
        │   └── ...
        └── ...
```

### Naming Convention

Generated variable files follow the pattern:
```
<PC_Name>_<original_template_stem>.md
```

Examples:
- `Anju_max_hp.md` — from template `max_hp.md`
- `Tai_Fire Attack Roll.md` — from template `Fire Attack Roll.md`
- `Sheph_Waterbending slot.md` — from template `Waterbending slot.md`

---

## File Format

Each generated variable file has this exact structure:

```markdown
```markdown
<VALUE_HERE>

<TAGS_HERE>

```
```

### Components

1. **Fence opening**: Triple backticks with `markdown` info string
2. **Blank line** (line 1)
3. **Value** (line 2) — The computed or primary stat value
4. **Blank line** (line 3)
5. **Tags** (line 4) — Space-separated hashtags
6. **Blank line** (line 5)
7. **Fence closing**: Triple backticks

### Real Example

File: `Anju_max_hp.md`

```markdown
```markdown
38

#vitality #variable_Anju #character_stat_Anju #character_stats_Anju #secondary_stat_Anju

```
```

---

## Tag Transformation Process

### Source: Primary Stats

**Location**: `Player Root/pc_primary_stats.md`

**Example row**:
```markdown
| Anju | Strength | 1 | yes | #primary_stat |
|------|----------|---|-----|---|
```

**Transformation Process** (in `write_character_files()` function):

1. Extract original tags from the `pc_primary_stats.md` row
2. **Filter out**: `#template` tags (if present)
3. **Add character-specific required tags**:
   - `#variable_<PC>` (e.g., `#variable_Anju`)
   - `#character_stat_<PC>` (e.g., `#character_stat_Anju`)
   - `#character_stats_<PC>` (e.g., `#character_stats_Anju`)
   - `#primary_stat_<PC>` (e.g., `#primary_stat_Anju`)

4. **Result**: All tags are suffixed with the character name

**Generated File** (`Anju_Strength.md`):
```markdown
```markdown
1

#variable_Anju #character_stat_Anju #character_stats_Anju #primary_stat_Anju

```
```

---

### Source: Secondary Stats (Templates)

**Location**: `Player Root/variable/secondary_stat/`

**Example template** (`max_hp.md`):
```markdown
`Constitution * 2 + 4`

#secondary_stat #vitality
```

Tags extracted: `#secondary_stat`, `#vitality`

**Transformation Process** (in `write_character_files()` function):

1. Load secondary stat template
2. Extract ALL tags from the template
3. **Preserve custom tags** — Tags like `#vitality`, `#defensive`, `#environmental_variable` are kept
4. **Filter out**: `#template` tags (not copied)
5. **Filter out**: `#secondary_stat` tag (handled separately with suffix)
6. **Add character-specific required tags**:
   - `#variable_<PC>`
   - `#character_stat_<PC>`
   - `#character_stats_<PC>`
   - `#secondary_stat_<PC>`

7. **Combine**: Custom preserved tags + required suffixed tags

**Generated File** (`Anju_max_hp.md`):
```markdown
```markdown
38

#vitality #variable_Anju #character_stat_Anju #character_stats_Anju #secondary_stat_Anju

```
```

Notice:
- `#vitality` is preserved from the template
- All tags get the `_Anju` suffix except the custom ones at the front
- `#secondary_stat` becomes `#secondary_stat_Anju`

---

## Tag Types and Their Meanings

### Required Tags (Always Added)

| Tag | Meaning |
|-----|---------|
| `#variable` | Marks this as a variable file (used by all scripts) |
| `#character_stat` | Marks as a per-character computed stat |
| `#character_stats` | Plural variant, same meaning as above |
| `#primary_stat` | Indicates primary (not derived) stat |
| `#secondary_stat` | Indicates secondary (derived from primary) stat |

**Suffix Rule**: All required tags get the character name appended:
- `#variable_Anju`
- `#character_stat_Anju`
- `#character_stats_Anju`
- `#primary_stat_Anju` or `#secondary_stat_Anju`

### Optional/Custom Tags (Preserved)

These tags come from the template and describe what the variable represents:

| Tag | Meaning | Effect |
|-----|---------|--------|
| `#vitality` | HP-related stat | Always written to variable file, even if value is 0 |
| `#defensive` | Defense/armor stat | Always written to variable file, even if value is 0 |
| `#environmental_variable` | Global environmental stat | Always written to variable file, even if value is 0 |
| `#rollable` | Contains dice notation (not numeric) | Prevents numeric evaluation warnings |
| `#template` | Marks a source template | **NOT COPIED** to generated files |

---

## Special Handling: Zero-Valued Secondaries

### The Zero-Skip Rule

When a secondary stat evaluates to 0, it is **NOT written** to a variable file UNLESS it has one of these tags:
- `#vitality`
- `#defensive`
- `#environmental_variable`

### Rationale

This keeps the variable file system clean by not creating files for:
- Damage bonuses that happen to be 0
- Armor values that are 0
- Status effects that are 0

But ensures essential defensive/vital stats are always present, even when 0.

### Code Location

In `recreate_pcs.py`, function `write_character_files()`:

```python
# If this secondary is numeric zero, skip creating the per-PC file
# unless the template is tagged with #vitality, #defensive or
# #environmental_variable
if is_zero_numeric and ('#vitality' not in tags) and ('#defensive' not in tags):
    # skip writing this secondary variable file
    if verbose:
        print(f"Skipping secondary var file for '{p}' ...")
else:
    fpath.write_text(f'```markdown\n{val}\n\n{" ".join(tags)}\n\n```\n', encoding='utf-8')
```

---

## Tag Suffix Mechanism

### Why Suffixes?

Character-specific tag suffixes allow:
1. **Tracking** which character generated this variable
2. **Quick filtering** (e.g., "all variables for Anju" = tags contain `_Anju`)
3. **Conflict prevention** when syncing multiple campaigns

### Implementation

In `recreate_pcs.py`, function `append_pc_tag_suffix()`:

```python
safe = re.sub(r"[^A-Za-z0-9_\-]", '_', name)
tag_suffix = f"_{safe}"
tag_suffix_lower = tag_suffix.lower()
tag_pattern = re.compile(r'(?<!\w)#([A-Za-z0-9][A-Za-z0-9_\-]*)')

def append_pc_tag_suffix(text: str) -> str:
    def _replace_tag(m):
        tag_body = m.group(1)
        if tag_body.lower().endswith(tag_suffix_lower):
            return f"#{tag_body}"  # already suffixed
        return f"#{tag_body}{tag_suffix}"
    return tag_pattern.sub(_replace_tag, text)
```

### Examples

| Original | PC Name | Result |
|----------|---------|--------|
| `#variable` | Anju | `#variable_Anju` |
| `#secondary_stat` | Tai | `#secondary_stat_Tai` |
| `#vitality` | Sheph | `#vitality` (custom, not suffixed) |
| `#character_stat_Anju` | Anju | `#character_stat_Anju` (already suffixed) |

---

## Writing Process: Step-by-Step

### For Primary Stats

Called once per primary stat in `pc_primary_stats.md`:

```python
for p in primary_names:
    key = p.lower()
    val = kv_all.get(key, 0)
    fname = f"{safe}_{p}.md"  # e.g., "Anju_Strength.md"
    fpath = target_root.joinpath(fname)
    
    # Build tags
    tags: List[str] = []
    if primary_tags and key in primary_tags:
        # Preserve original tags except #template
        base_required = {'#variable', '#character_stat', '#character_stats', '#primary_stat'}
        tags = [t for t in primary_tags[key] if t != '#template' and t not in base_required]
    
    # Add required tags with suffix
    for req in ('#variable_', '#character_stat_', '#character_stats_', '#primary_stat_'):
        tags.append(f'{req}{safe}')
    
    # Write file
    fpath.write_text(f'```markdown\n{val}\n\n{" ".join(tags)}\n\n```\n', encoding='utf-8')
```

### For Secondary Stats

Called once per secondary template:

```python
for p in secondary_templates.keys():
    key = p.lower()
    val = kv_all.get(key, '')
    fname = f"{safe}_{p}.md"  # e.g., "Anju_max_hp.md"
    fpath = target_root.joinpath(fname)
    
    # Build tags
    tags: List[str] = []
    if secondary_tags and key in secondary_tags:
        # Preserve original tags except #template and required
        base_required = {'#variable', '#character_stat', '#character_stats', '#secondary_stat'}
        tags = [t for t in secondary_tags[key] if t != '#template' and t not in base_required]
    
    # Add required tags with suffix
    for req in ('#variable_', '#character_stat_', '#character_stats_', '#secondary_stat_'):
        tags.append(f'{req}{safe}')
    
    # Zero-skip check
    if is_zero_numeric and ('#vitality' not in tags) and ('#defensive' not in tags):
        continue  # don't write
    
    # Write file
    fpath.write_text(f'```markdown\n{val}\n\n{" ".join(tags)}\n\n```\n', encoding='utf-8')
```

---

## File Example: Complete Walkthrough

### Scenario

PC: **Anju**
Template: `Fire Armor` (secondary stat, tagged `#secondary_stat #defensive`)

### Step 1: Load Template

File: `Player Root/variable/secondary_stat/Fire Armor.md`

```markdown
`fire_armor_base + fire_armor_bonus`

#secondary_stat #defensive
```

### Step 2: Compute Value

Using Anju's stats:
- `fire_armor_base` = 2
- `fire_armor_bonus` = 0
- Result: `2 + 0 = 2`

### Step 3: Extract Tags

From template: `#secondary_stat`, `#defensive`

### Step 4: Transform Tags

1. Start with: `[#secondary_stat, #defensive]`
2. Remove `#template`: (none present)
3. Remove required tags: (none present)
4. Preserved tags: `[#defensive]`
5. Add required suffixed: `[#variable_Anju, #character_stat_Anju, #character_stats_Anju, #secondary_stat_Anju]`
6. Final: `#defensive #variable_Anju #character_stat_Anju #character_stats_Anju #secondary_stat_Anju`

### Step 5: Write File

Path: `Player Root/variable/PC_variables/Anju/Anju_Fire Armor.md`

```markdown
```markdown
2

#defensive #variable_Anju #character_stat_Anju #character_stats_Anju #secondary_stat_Anju

```
```

---

## Integration Points

### With sync_variables.py

The sync script reads these variable files:

1. **Reads value**:
   ```python
   m = re.search(r'```markdown\n(.*?)\n\n', txt, flags=re.S)
   value = m.group(1).strip()  # Extracts "2"
   ```

2. **Reads tags**:
   ```python
   m = re.search(r'```markdown\n.*?\n\n(.*?)\n\n```', txt, flags=re.S)
   tags = re.findall(r'#([A-Za-z0-9_\-]+)', m.group(1))
   # ['defensive', 'variable_Anju', 'character_stat_Anju', ...]
   ```

3. **Uses tags to decide sync behavior**:
   - If `#vitality` or `#defensive`: Update stat_overview.md
   - Otherwise: Only update character sheet

### With generate_stat_overview.py

The stat overview generator:

1. Scans all variable files
2. Filters for those tagged with `#vitality` or `#defensive`
3. Creates tables organized by stat type

---

## Key Takeaways

| Aspect | Rule |
|--------|------|
| **File location** | `PC_variables/<PC>/<PC>_<stat>.md` |
| **Value format** | Inside fenced ```markdown block |
| **Tag preservation** | Custom tags kept, `#template` removed |
| **Tag suffixing** | All required tags get `_<PC>` suffix |
| **Zero handling** | Skip secondary zeros unless `#vitality/#defensive` |
| **Purpose** | Source of truth for all computed stats |

---

## Contact

For exact code details:
- `recreate_pcs.py`: Functions `write_character_files()` and `append_pc_tag_suffix()`
- `common.py`: Helper functions for tag extraction and variable I/O
- `sync_variables.py`: Reading and using these tags for synchronization
