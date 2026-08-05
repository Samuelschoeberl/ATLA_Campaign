"""Shared path/customization/sheet-parsing helpers used by the route modules.

Extracted from the old monolithic `frontend_api.py` (which used to hold
~40 routes plus all of these helpers in one 3000-line file). Route modules
(`routes_files.py`, `routes_sheets.py`, `routes_generation.py`,
`routes_events.py`) import from here; `frontend_api.py` itself is now just
the Blueprint definition plus the imports that register those routes onto it.
"""
from __future__ import annotations

import base64
import io
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Repo root (same logic as other scripts in this repo)
REPO_ROOT = Path(__file__).resolve().parents[3]
PLAYER_ROOT_PREFIX = "Player Root/"

# Location for generator logs
LOGS_DIR = REPO_ROOT.joinpath('logs')
LOGS_DIR.mkdir(parents=True, exist_ok=True)
WIKIGRAPHS_LOG = LOGS_DIR.joinpath('wikigraphs.log')


def get_player_root_base() -> Path:
    """Return the filesystem path that should be considered the Player Root base.

    Some repositories place player files under a literal top-level folder
    named 'Player Root'. Others have those files at the repository root.
    This helper prefers REPO_ROOT / 'Player Root' when it exists, and
    falls back to REPO_ROOT otherwise so API endpoints work in both layouts.
    """
    cand = REPO_ROOT.joinpath('Player Root')
    try:
        if cand.exists() and cand.is_dir():
            return cand.resolve()
    except Exception:
        pass
    return REPO_ROOT


def is_safe_repo_path(target: Path, repo_root: Path = REPO_ROOT) -> bool:
    """Resolved-path containment check: is target inside repo_root?

    Reused everywhere a route needs to validate a client-supplied path stays
    inside the repository, instead of the naive (and bypassable)
    `str(target).startswith(str(repo_root))` string check.
    """
    try:
        repo_resolved = repo_root.resolve()
        target = target.resolve()
        return repo_resolved in target.parents or target == repo_resolved
    except Exception:
        return False


# ---- Character customization helpers (folder color + 100x100 avatars) ----
AVATAR_SIZE = 100


def _safe_character_slug(name: str) -> str:
    """Normalize a character name into a filesystem-safe slug."""
    slug = re.sub(r'[^A-Za-z0-9_-]+', '_', str(name or 'character')).strip('_')
    return slug or 'character'


def _clamp_byte(val):
    """Clamp arbitrary numeric-ish input to an integer in [0, 255]."""
    try:
        num = float(val)
    except Exception:
        return 0
    if not (num == num and num != float('inf') and num != float('-inf')):
        return 0
    return max(0, min(255, int(round(num))))


def _normalize_pixel(pixel):
    """Return a 4-element RGBA list for varied pixel inputs."""
    if isinstance(pixel, (list, tuple)):
        vals = list(pixel)[:4] + [0, 0, 0, 0]
        return [_clamp_byte(v) for v in vals[:4]]
    if isinstance(pixel, dict):
        return [
            _clamp_byte(pixel.get('r', 0)),
            _clamp_byte(pixel.get('g', 0)),
            _clamp_byte(pixel.get('b', 0)),
            _clamp_byte(pixel.get('a', 0)),
        ]
    return [0, 0, 0, 0]


def default_avatar_matrix():
    """Create an empty AVATAR_SIZE x AVATAR_SIZE transparent pixel matrix."""
    return [
        [[0, 0, 0, 0] for _ in range(AVATAR_SIZE)]
        for _ in range(AVATAR_SIZE)
    ]


def normalize_avatar_matrix(matrix):
    """Ensure the avatar data is a correctly sized RGBA grid."""
    rows = []
    src = matrix if isinstance(matrix, (list, tuple)) else []
    for r in range(AVATAR_SIZE):
        row_src = src[r] if r < len(src) and isinstance(src[r], (list, tuple)) else []
        row = []
        for c in range(AVATAR_SIZE):
            pix = row_src[c] if c < len(row_src) else [0, 0, 0, 0]
            row.append(_normalize_pixel(pix))
        rows.append(row)
    return rows


def _is_valid_hex_color(value: str) -> bool:
    """Return True if the string looks like a #RRGGBB hex color."""
    return bool(re.match(r'^#(?:[0-9a-fA-F]{6})$', str(value or '').strip()))


def get_customization_dir() -> Path:
    """Directory that stores per-character customization JSON files."""
    base = get_player_root_base()
    target = base.joinpath('character_customizations')
    target.mkdir(parents=True, exist_ok=True)
    return target


def load_character_customization(name: str):
    """Load a customization record for a specific character name."""
    slug = _safe_character_slug(name)
    path = get_customization_dir().joinpath(f"{slug}.json")
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
        folder_color = raw.get('folderColor') or raw.get('folder_color')
        if folder_color and not _is_valid_hex_color(folder_color):
            folder_color = None
        avatar = normalize_avatar_matrix(raw.get('avatar') or default_avatar_matrix())
        return {
            'name': raw.get('name') or name,
            'folderColor': folder_color,
            'avatar': avatar,
            'avatarPng': raw.get('avatarPng'),  # Include PNG avatar path
            'updated_at': raw.get('updated_at') or datetime.utcnow().isoformat() + 'Z'
        }
    except Exception:
        return None


def load_all_customizations():
    """Load all character customization JSON files into a name->record map."""
    out = {}
    custom_dir = get_customization_dir()
    if not custom_dir.exists():
        return out
    for path in custom_dir.glob('*.json'):
        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        name = raw.get('name') or path.stem
        data = load_character_customization(name)
        if data:
            out[data.get('name') or name] = data
    return out


def save_character_customization(name: str, folder_color, avatar, avatar_png=None):
    """Persist a customization entry and return the normalized payload."""
    slug = _safe_character_slug(name)

    # Save PNG as actual file if provided
    avatar_png_path = None
    if avatar_png:
        try:
            # Extract base64 data from data URL
            if avatar_png.startswith('data:image/png;base64,'):
                base64_data = avatar_png.split(',', 1)[1]
            else:
                base64_data = avatar_png

            # Decode and save to character's folder
            png_data = base64.b64decode(base64_data)

            # Strip color profiles using PIL - aggressive re-encoding
            from PIL import Image
            img = Image.open(io.BytesIO(png_data))

            # Log what we're removing
            if img.info.get('icc_profile'):
                print(f"Stripping ICC profile from {name}")
            if 'sRGB' in img.info:
                print(f"Stripping sRGB chunk from {name}")

            # Create completely clean image
            # Force mode conversion to drop all metadata
            if img.mode == 'RGBA' or 'transparency' in img.info:
                # Keep transparency if present
                new_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
                new_img.paste(img, (0, 0), img if img.mode == 'RGBA' else None)
            else:
                # Convert to RGB, no alpha
                if img.mode != 'RGB':
                    new_img = img.convert('RGB')
                else:
                    new_img = img.copy()
                # Re-paste to clean all metadata
                clean_img = Image.new('RGB', new_img.size)
                clean_img.paste(new_img)
                new_img = clean_img

            # Save with ZERO metadata - this is the key
            output = io.BytesIO()
            new_img.save(output, format='PNG', optimize=False, save_all=False)
            cleaned_png_data = output.getvalue()

            # Find character folder (PCs/CharacterName/)
            player_root = get_player_root_base()
            char_folder = player_root / 'PCs' / name

            # Create folder if it doesn't exist
            char_folder.mkdir(parents=True, exist_ok=True)

            png_file = char_folder / f"{name}_avatar.png"
            png_file.write_bytes(cleaned_png_data)
            # Store relative path
            avatar_png_path = f"PCs/{name}/{name}_avatar.png"
            print(f"Saved avatar PNG (all metadata stripped) to: {png_file}")
        except Exception as e:
            print(f"Error saving PNG file: {e}")
            import traceback
            traceback.print_exc()
            # Continue with data URL if file save fails
            avatar_png_path = avatar_png

    payload = {
        'name': name,
        'folderColor': folder_color if folder_color else None,
        'avatar': normalize_avatar_matrix(avatar),
        'avatarPng': avatar_png_path,  # Store file path instead of data URL
        'updated_at': datetime.utcnow().isoformat() + 'Z'
    }
    target = get_customization_dir().joinpath(f"{slug}.json")
    target.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return payload


# Helper: parse canonical stats from free-form markdown content
def parse_canonical_stats_from_text(text: str):
    """Return dict of canonical keys -> string values found in the text.

    Keys: max_hp, current_hp, evasion, general armor
    """
    out = {}
    patterns = [
        (re.compile(r"max[_ ]?hp", re.I), "max_hp"),
        (re.compile(r"current[_ ]?hp|current\s+hp", re.I), "current_hp"),
        (re.compile(r"evasion", re.I), "evasion"),
        (re.compile(r"general\s*armor", re.I), "general armor"),
    ]
    # simple table row or key: value or inline number
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        # try table row style
        if s.startswith("|") and s.count("|") >= 2:
            cols = [c.strip() for c in s.split("|")]
            # skip header/separators
            if len(cols) >= 3 and not cols[1].startswith("---"):
                key = cols[1]
                val = cols[2] if len(cols) > 2 else ""
                for pat, canon in patterns:
                    if pat.search(key) and canon not in out:
                        out[canon] = val
        else:
            # key: value
            m = re.match(r"^\s*([^:]+):\s*(.+)$", s)
            if m:
                key = m.group(1).strip()
                val = m.group(2).strip()
                for pat, canon in patterns:
                    if pat.search(key) and canon not in out:
                        out[canon] = val
            else:
                # inline numeric fallback
                for pat, canon in patterns:
                    if pat.search(s) and canon not in out:
                        m2 = re.search(r"(-?\d+)", s)
                        if m2:
                            out[canon] = m2.group(1)
    return out


def write_pc_variable_files(pcname: str, stats: dict):
    """Write per-PC variable files under Player Root/variable/PC_variables/<pcname>/

    Each file will contain the scalar value on the first line and include a
    small tag line so other tools can recognize it.
    """
    base = REPO_ROOT.joinpath('Player Root', 'variable', 'PC_variables', pcname)
    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception:
        return False, "failed to create pc variable dir"
    for k, v in stats.items():
        # filename like Anju_current_hp.md
        safe_key = k.replace(' ', '_')
        fname = f"{pcname}_{safe_key}.md"
        fpath = base.joinpath(fname)
        # write numeric or raw value
        content = str(v) + "\n\n" + "#variable #environmental_variables #character_stat #character_stats #secondary_stat\n"
        try:
            fpath.write_text(content, encoding='utf-8')
        except Exception as e:
            return False, str(e)
    # Also attempt to update a combined variables file in the PC directory
    try:
        pc_dir = REPO_ROOT.joinpath('Player Root', 'PCs', pcname)
        if pc_dir.exists() and pc_dir.is_dir():
            # prefer a file with 'variables' in the name if present
            candidate = None
            for p in pc_dir.iterdir():
                if not p.is_file():
                    continue
                if 'variables' in p.name.lower() and p.name.lower().endswith('.md'):
                    candidate = p
                    break
            # fallback: <pcname>_variables.md or <pcname>_variables.md (case-insensitive)
            if candidate is None:
                for p in pc_dir.iterdir():
                    if not p.is_file():
                        continue
                    n = p.name.lower()
                    if n.startswith(pcname.lower()) and 'variables' in n and n.endswith('.md'):
                        candidate = p
                        break

            if candidate:
                try:
                    text = candidate.read_text(encoding='utf-8')
                except Exception:
                    text = ''
                lines = text.splitlines()
                out_lines = []
                updated = set()
                for line in lines:
                    if not line.strip().startswith('|'):
                        out_lines.append(line)
                        continue
                    cols = [c.strip() for c in line.split('|') if c.strip()]
                    if not cols:
                        out_lines.append(line)
                        continue
                    key_col = cols[0]
                    key_norm = key_col.replace('.', '_').replace(' ', '_').lower()
                    matched = False
                    for k, v in stats.items():
                        k_variant = k.replace(' ', '_').lower()
                        if k_variant == key_norm:
                            # preserve two-column style if present
                            if len(cols) >= 2:
                                out_lines.append(f"| {k_variant} | {v.rjust(11)} |")
                            else:
                                out_lines.append(f"| {k_variant} | {v} |")
                            updated.add(k_variant)
                            matched = True
                            break
                    if not matched:
                        out_lines.append(line)
                # append missing keys
                for k, v in stats.items():
                    k_variant = k.replace(' ', '_')
                    if k_variant not in updated:
                        out_lines.append(f"| {k_variant} | {str(v).rjust(11)} |")
                try:
                    candidate.write_text('\n'.join(out_lines) + '\n', encoding='utf-8')
                except Exception as e:
                    return False, str(e)
    except Exception:
        # non-fatal: ignore
        pass

    # DISABLED: No longer creating summary *_variables.md files
    # Variables are tracked in Player Root/variable/PC_variables/ only

    return True, None


def read_pc_variable_files(pcname: str):
    """Read per-PC variable files under Player Root/variable/PC_variables/<pcname>/

    Return a dict of canonical keys -> values (strings). If no files exist,
    try to read a combined file in the PC dir (e.g., Anju_variables.md).
    """
    out = {}
    base = REPO_ROOT.joinpath('Player Root', 'variable', 'PC_variables', pcname)
    if base.exists() and base.is_dir():
        for p in sorted(base.iterdir()):
            if not p.is_file() or not p.name.lower().endswith('.md'):
                continue
            name = p.name
            # expected pattern: <pcname>_<key>.md
            if name.lower().startswith(pcname.lower() + '_'):
                key = name[len(pcname) + 1: -3]
                try:
                    txt = p.read_text(encoding='utf-8')
                except Exception:
                    continue
                # take first non-empty non-comment line
                for line in txt.splitlines():
                    s = line.strip()
                    if not s or s.startswith('#'):
                        continue
                    out[key.replace('.', '_')] = s
                    break
    # fallback: combined file in PC dir
    if not out:
        pc_dir = REPO_ROOT.joinpath('Player Root', 'PCs', pcname)
        if pc_dir.exists() and pc_dir.is_dir():
            combined = None
            for p in pc_dir.iterdir():
                if p.is_file() and p.name.lower().endswith('.md') and 'variables' in p.name.lower():
                    combined = p
                    break
            if combined:
                try:
                    text = combined.read_text(encoding='utf-8')
                except Exception:
                    text = ''
                for line in text.splitlines():
                    if not line.strip().startswith('|'):
                        continue
                    cols = [c.strip() for c in line.split('|') if c.strip()]
                    if len(cols) >= 2:
                        key = cols[0].replace('.', '_')
                        val = cols[1]
                        out[key] = val
    return out


def update_character_sheet(pcname: str, stats: dict):
    """Try to find the character sheet file for pcname and update canonical stats.

    Returns (True, None) on success (file modified), or (False, reason) on no-op/error.
    """
    try:
        pc_dir = REPO_ROOT.joinpath('Player Root', 'PCs', pcname)
        if not pc_dir.exists() or not pc_dir.is_dir():
            return False, 'pc folder not found'

        # find candidate sheet file (similar heuristics to update_sheet endpoint)
        candidate = None
        for p in pc_dir.iterdir():
            if not p.is_file() or not p.name.lower().endswith('.md'):
                continue
            name = p.name.lower()
            if pcname.lower() in name and ('character' in name or 'sheet' in name):
                candidate = p
                break
        if candidate is None:
            for p in pc_dir.iterdir():
                if p.is_file() and p.name.lower().endswith('.md') and p.name.lower().startswith(pcname.lower()):
                    candidate = p
                    break

        if candidate is None:
            return False, 'no character sheet file found'

        try:
            text = candidate.read_text(encoding='utf-8')
        except Exception as e:
            return False, f'read error: {e}'

        orig = text
        # For each canonical stat, try to replace table rows like '| key | value |' or 'key: value'
        for k, v in stats.items():
            # consider variants: underscore and space
            variants = [k, k.replace('_', ' ')]
            for key in variants:
                # table row pattern
                pat_table = re.compile(r'(^\|\s*' + re.escape(key) + r"\s*\|\s*)([^|\n]*)(\|)", re.I | re.M)
                if pat_table.search(text):
                    text = pat_table.sub(lambda m: m.group(1) + ' ' + str(v) + ' ' + m.group(3), text)
                    break
                # key: value pattern
                pat_kv = re.compile(r'(^\s*' + re.escape(key) + r"\s*:\s*).*$", re.I | re.M)
                if pat_kv.search(text):
                    text = pat_kv.sub(lambda m: m.group(1) + str(v), text)
                    break
            # continue to next stat

        if text != orig:
            try:
                candidate.write_text(text, encoding='utf-8')
                return True, None
            except Exception as e:
                return False, f'write error: {e}'
        return False, 'no changes'
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Vitals/conditions text transforms, shared between rebuild_database.py (vault
# -> DB) and the PATCH /api/sheets/<pc>/fields write-through (DB -> vault).
# Mirrors the parsing convention already used client-side in
# characterSheetParser.js's parseSheetVitalsAndConditions, so a sheet edited
# by hand in Obsidian and one produced by this write-through round-trip
# identically.
# ---------------------------------------------------------------------------

_CONDITION_ACTIVE_VALUES = {'yes', 'true', '1', 'active', 'x', 'y'}


def find_sheet_file(pc_dir: Path, pcname: str) -> Optional[Path]:
    """Pick the best-matching markdown character sheet file for a PC folder."""
    candidates = []
    for p in pc_dir.iterdir():
        if not p.is_file() or not p.name.lower().endswith('.md'):
            continue
        name = p.name.lower()
        if pcname.lower() in name and ('character' in name or 'sheet' in name):
            candidates.append(p)
    if not candidates:
        for p in pc_dir.iterdir():
            if p.is_file() and p.name.lower().endswith('.md') and p.name.lower().startswith(pcname.lower()):
                candidates.append(p)
    return candidates[0] if candidates else None


def parse_vitals_and_conditions(text: str) -> dict:
    """Return {current_hp, max_hp, ready, conditions} parsed from sheet text."""
    out = {'current_hp': None, 'max_hp': None, 'ready': False, 'conditions': []}

    def _row_value(key: str) -> Optional[str]:
        pat = re.compile(r"\|\s*" + re.escape(key) + r"\s*\|\s*([^|\n]+?)\s*\|", re.I)
        m = pat.search(text)
        return m.group(1).strip() if m else None

    cur = _row_value('current_hp')
    if cur is not None:
        try:
            out['current_hp'] = int(float(re.sub(r'[^0-9.+-]', '', cur) or 0))
        except Exception:
            pass
    mx = _row_value('max_hp')
    if mx is not None:
        try:
            out['max_hp'] = int(float(re.sub(r'[^0-9.+-]', '', mx) or 0))
        except Exception:
            pass
    ready_val = _row_value('ready')
    if ready_val is not None:
        out['ready'] = ready_val.strip().lower() in _CONDITION_ACTIVE_VALUES

    conditions: List[str] = []
    cond_match = re.search(r"## Conditions\s*\n\n(.*?)(?:\n\n##|\n#|$)", text, re.S)
    if cond_match:
        for row in cond_match.group(1).splitlines():
            if not row.strip() or '---' in row:
                continue
            cells = [c.strip() for c in row.split('|') if c.strip()]
            if len(cells) >= 2 and cells[0].lower() != 'condition':
                if cells[1].strip().lower() in _CONDITION_ACTIVE_VALUES:
                    if cells[0] not in conditions:
                        conditions.append(cells[0])
    for m in re.finditer(r"#condition[_\s-](\w+)", text, re.I):
        name = m.group(1).replace('_', ' ')
        if name not in conditions:
            conditions.append(name)
    out['conditions'] = conditions
    return out


def apply_vitals_updates_to_text(text: str, current_hp=None, max_hp=None, ready=None, conditions=None) -> str:
    """Return sheet text with the given vitals fields updated in place.

    Numeric/ready fields are updated via their existing `| key | value |` row
    (inserted at the end of the Vitals section if the row doesn't exist yet).
    The `## Conditions` table, if `conditions` is not None, is fully replaced
    with a table listing just the given active conditions (rows for
    conditions not listed are implicitly inactive, matching the frontend
    parser's convention).
    """
    def _set_row(txt: str, key: str, value) -> str:
        pat = re.compile(r"(\|\s*" + re.escape(key) + r"\s*\|\s*)([^|\n]+)(\|)", re.I)
        new_txt, n = pat.subn(lambda m: m.group(1) + f' {value} ' + m.group(3), txt)
        if n:
            return new_txt
        # Row doesn't exist yet: append it at the end of the Vitals table.
        vitals_match = re.search(r"(## Vitals\s*\n\n(?:.*\n)*?)(\n##|\n?$)", txt)
        if vitals_match:
            insert_at = vitals_match.end(1)
            row = f"| {key.ljust(18)} | {value} |\n"
            return txt[:insert_at] + row + txt[insert_at:]
        return txt

    if current_hp is not None:
        text = _set_row(text, 'current_hp', current_hp)
    if max_hp is not None:
        text = _set_row(text, 'max_hp', max_hp)
    if ready is not None:
        text = _set_row(text, 'ready', 'yes' if ready else 'no')

    if conditions is not None:
        table = "## Conditions\n\n| Condition        | Active |\n| ---------------- | :----: |\n"
        for cond in conditions:
            table += f"| {cond.ljust(16)} | yes |\n"
        if re.search(r"## Conditions\s*\n\n(.*?)(?:\n\n##|\n#|$)", text, re.S):
            text = re.sub(
                r"## Conditions\s*\n\n(.*?)(?:\n\n##|\n#|$)",
                lambda m: table + ("\n\n##" if m.group(0).endswith("\n\n##") else ""),
                text, count=1, flags=re.S,
            )
        else:
            text = text.rstrip('\n') + '\n\n' + table
    return text


def parse_stat_overview_content(content: str):
    """
    Parse the markdown stat overview content into structured JSON.

    Returns:
        {
            'environmental': [{'name': str, 'value': str, 'tags': str, 'file': str}, ...],
            'pcs': {
                'PCName': {
                    'vitality': [{'key': str, 'value': str, 'source': str}, ...],
                    'defensive': [{'key': str, 'value': str, 'source': str}, ...]
                },
                ...
            }
        }
    """
    result = {
        'environmental': [],
        'pcs': {}
    }

    lines = content.splitlines()
    current_section = None
    current_pc = None
    current_category = None

    for line in lines:
        stripped = line.strip()

        # Detect sections
        if stripped == '## Global environmental variables' or stripped == '## Global Environmental Variables':
            current_section = 'environmental'
            current_pc = None
            current_category = None
            continue
        elif stripped == '## Per-PC extracted stats' or stripped == '## Per-PC Extracted Stats':
            current_section = 'pcs'
            current_pc = None
            current_category = None
            continue

        # Detect PC names (### heading)
        if stripped.startswith('### '):
            current_pc = stripped[4:].strip()
            if current_pc not in result['pcs']:
                result['pcs'][current_pc] = {
                    'vitality': [],
                    'defensive': [],
                    'bending_slots': []
                }
            current_category = None
            continue

        # Detect category (#### or **category**)
        if stripped.startswith('#### '):
            category = stripped[5:].strip().lower()
            if category == 'vitality':
                current_category = 'vitality'
            elif category == 'defensive':
                current_category = 'defensive'
            elif category in ['bending slots', 'consumable resources']:
                current_category = 'bending_slots'
            continue

        if stripped.startswith('**') and stripped.endswith('**'):
            category = stripped.strip('*').strip().lower()
            if category == 'vitality':
                current_category = 'vitality'
            elif category == 'defensive':
                current_category = 'defensive'
            elif category in ['bending slots', 'consumable resources']:
                current_category = 'bending_slots'
            continue

        # Parse table rows
        if '|' in stripped and not stripped.startswith('|--'):
            parts = [p.strip() for p in stripped.split('|') if p.strip()]

            # Skip header rows and separator rows (rows with only dashes)
            if parts:
                first_col = parts[0]
                # Skip if header row
                if first_col.lower() in ['name', 'key', 'resource name', 'slot type']:
                    continue
                # Skip if separator row (contains only dashes and spaces)
                if all(c in '- ' for c in first_col) and '-' in first_col:
                    continue

            # Environmental table row
            if current_section == 'environmental' and not current_pc and len(parts) >= 4:
                name = parts[0].replace('[[', '').replace(']]', '')
                result['environmental'].append({
                    'name': name,
                    'value': parts[1],
                    'tags': parts[2],
                    'file': parts[3]
                })

            # PC stats table row
            elif current_pc and current_category and len(parts) >= 3:
                result['pcs'][current_pc][current_category].append({
                    'key': parts[0],
                    'value': parts[1],
                    'source': parts[2]
                })

    return result
