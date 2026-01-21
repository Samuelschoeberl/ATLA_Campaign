"""Flask blueprint exposing helper endpoints for the React frontend."""
from flask import Blueprint, request, jsonify, send_from_directory, send_file, abort, current_app
from pathlib import Path
import hashlib
import re
import os
import shutil
import sys
import subprocess
import json
from datetime import datetime

from flask import Response, stream_with_context

# Import balance scorer
try:
    from .balance_scorer import get_scorer
    BALANCE_SCORER_AVAILABLE = True
except (ImportError, Exception) as e:
    print(f"Balance scorer not available: {e}")
    BALANCE_SCORER_AVAILABLE = False

# Import simplicity scorer
try:
    from .simplicity_scorer import get_scorer as get_simplicity_scorer
    SIMPLICITY_SCORER_AVAILABLE = True
except (ImportError, Exception) as e:
    print(f"Simplicity scorer not available: {e}")
    SIMPLICITY_SCORER_AVAILABLE = False

# Import full analysis scorer
try:
    from .full_analysis_scorer import get_scorer as get_full_analysis_scorer
    FULL_ANALYSIS_SCORER_AVAILABLE = True
except (ImportError, Exception) as e:
    print(f"Full analysis scorer not available: {e}")
    FULL_ANALYSIS_SCORER_AVAILABLE = False

bp = Blueprint("frontend_api", __name__)

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


# ---- Character customization helpers (folder color + 100×100 avatars) ----
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
    """Create an empty AVATAR_SIZE×AVATAR_SIZE transparent pixel matrix."""
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
    import base64
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
            import io
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
                clean_mode = 'RGBA'
                new_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
                new_img.paste(img, (0, 0), img if img.mode == 'RGBA' else None)
            else:
                # Convert to RGB, no alpha
                clean_mode = 'RGB'
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
                key = name[len(pcname) + 1 : -3]
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
            replaced = False
            for key in variants:
                # table row pattern
                pat_table = re.compile(r'(^\|\s*' + re.escape(key) + r"\s*\|\s*)([^|\n]*)(\|)", re.I | re.M)
                if pat_table.search(text):
                    text = pat_table.sub(lambda m: m.group(1) + ' ' + str(v) + ' ' + m.group(3), text)
                    replaced = True
                    break
                # key: value pattern
                pat_kv = re.compile(r'(^\s*' + re.escape(key) + r"\s*:\s*).*$", re.I | re.M)
                if pat_kv.search(text):
                    text = pat_kv.sub(lambda m: m.group(1) + str(v), text)
                    replaced = True
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

@bp.route("/api/create-md-file", methods=["POST"])
def create_md_file():
    """Create an empty markdown file under the Player Root tree."""
    data = request.get_json() or {}
    folder = (data.get("folderPath") or "").strip()
    filename = (data.get("filename") or "").strip()

    # Basic validation
    if not filename or not filename.lower().endswith(".md"):
        return jsonify(error="Filename must end with .md"), 400
    if "/" in filename or "\\" in filename or ".." in filename:
        return jsonify(error="Invalid filename"), 400

    # Normalize incoming folder path (frontend may send "Player Root/..." prefix)
    if folder.startswith(PLAYER_ROOT_PREFIX):
        rel_folder = folder[len(PLAYER_ROOT_PREFIX) :].lstrip("/")
    else:
        rel_folder = folder.lstrip("/")

    # The frontend exposes content under the repository's "Player Root" top-level
    # directory. Some checkouts place those files at REPO_ROOT itself. Use the
    # helper to determine the correct base path for Player Root content.
    player_base = get_player_root_base()
    if player_base == REPO_ROOT:
        # repository-root layout: if the frontend passed an explicit
        # 'Player Root/...' prefix strip it; otherwise use target_rel as-is
        rel = rel_folder
        if rel.startswith(PLAYER_ROOT_PREFIX):
            rel = rel[len(PLAYER_ROOT_PREFIX) :].lstrip('/')
        target_dir = player_base if not rel else (player_base / rel)
    else:
        # explicit Player Root folder exists
        target_dir = player_base if not rel_folder else (player_base / rel_folder)

    try:
        target_dir = target_dir.resolve()
    except Exception:
        return jsonify(error="Invalid folder path"), 400

    # Ensure target directory is inside the repo
    try:
        repo_resolved = REPO_ROOT.resolve()
        if repo_resolved not in target_dir.parents and target_dir != repo_resolved:
            return jsonify(error="Folder is outside repository"), 400
    except Exception:
        return jsonify(error="Path resolution error"), 400

    if not target_dir.exists() or not target_dir.is_dir():
        return jsonify(error="Folder does not exist"), 400

    full_path = target_dir / filename
    if full_path.exists():
        return jsonify(error="File already exists"), 400

    try:
        # create empty file
        full_path.write_text("", encoding="utf-8")
    except Exception as e:
        return jsonify(error=str(e)), 500

    # Return the created path in the same "Player Root/..." form the frontend uses
    # Compute the path relative to the Player Root directory so we don't
    # accidentally double-prefix 'Player Root/' when returning the API path.
    # Compute a Player-Root-relative path for frontend consumption. Prefer
    # paths relative to the configured player_base; fall back to repo
    # relative paths when necessary.
    try:
        if player_base != REPO_ROOT:
            rel_from_player = full_path.relative_to(player_base).as_posix()
        else:
            # repo-root layout: return repo-relative path but strip any leading
            # 'Player Root/' prefix the client may have sent.
            rel_from_player = full_path.relative_to(REPO_ROOT).as_posix()
            if rel_from_player.startswith(PLAYER_ROOT_PREFIX):
                rel_from_player = rel_from_player[len(PLAYER_ROOT_PREFIX):].lstrip('/')
    except Exception:
        # fallback to repo-relative or raw path
        try:
            rel_from_player = full_path.relative_to(REPO_ROOT).as_posix()
        except Exception:
            rel_from_player = full_path.as_posix()

    return jsonify(success=True, path=f"{PLAYER_ROOT_PREFIX}{rel_from_player}")


@bp.route("/api/find-file/<filename>", methods=["GET"])
def find_file_by_name(filename):
    """Find a file or folder by name in Player Root. Returns the first match.
    Priority: exact filename match (any extension) > .md file > folder
    """
    player_root = get_player_root_base()
    if not player_root.exists():
        return jsonify(error="Player Root not found"), 404
    
    try:
        # First, search for exact filename match (including images, etc.)
        for path in player_root.rglob(filename):
            if path.is_file():
                # Return the relative path from Player Root
                rel_path = path.relative_to(player_root).as_posix()
                return jsonify(path=rel_path, found=True, type='file')
        
        # If filename doesn't have .md extension, try adding it
        if not filename.endswith('.md'):
            search_name = f"{filename}.md"
            for path in player_root.rglob(search_name):
                if path.is_file():
                    # Return the relative path from Player Root
                    rel_path = path.relative_to(player_root).as_posix()
                    return jsonify(path=rel_path, found=True, type='file')
        
        # If no file found, search for a folder with the exact name (without .md)
        folder_name = filename.replace('.md', '') if filename.endswith('.md') else filename
        for path in player_root.rglob(folder_name):
            if path.is_dir():
                # Return the relative path from Player Root
                rel_path = path.relative_to(player_root).as_posix()
                return jsonify(path=rel_path, found=True, type='folder')
        
        # If neither found, return not found
        return jsonify(found=False, message=f"File or folder '{filename}' not found"), 404
    except Exception as e:
        return jsonify(error=str(e)), 500


@bp.route("/player_root", defaults={"subpath": ""})
@bp.route("/player_root/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"])
def player_root(subpath):
    """Serve, create, or delete files within the Player Root namespace."""
    # Handle OPTIONS preflight requests for CORS
    if request.method == "OPTIONS":
        response = jsonify(success=True)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, HEAD, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    # Accept requests for repo root or subpaths. Frontend sends paths without
    # the leading "Player Root/" prefix in most calls; normalize both forms.
    sp = (subpath or "").strip()
    if sp.startswith(PLAYER_ROOT_PREFIX):
        sp = sp[len(PLAYER_ROOT_PREFIX) :].lstrip("/")

    # target base is the Player Root directory inside the repo (or repo root)
    player_base = get_player_root_base()
    target = player_base if not sp else (player_base / sp)

    try:
        target = target.resolve()
    except Exception:
        return jsonify(error="Invalid path"), 400

    # Ensure target is inside repo
    try:
        repo_resolved = REPO_ROOT.resolve()
        if repo_resolved not in target.parents and target != repo_resolved:
            return jsonify(error="Path outside repository"), 400
    except Exception:
        return jsonify(error="Path resolution error"), 400

    if not target.exists():
        # For POST/PUT, allow creating a new file if parent exists
        if request.method in ("POST", "PUT"):
            # allow creating the parent directories if missing so clients
            # can create files in newly created folders such as 'deleted'
            parent = target.parent
            try:
                if not parent.exists():
                    parent.mkdir(parents=True, exist_ok=True)
                if not parent.is_dir():
                    return jsonify(error="Folder does not exist"), 400
            except Exception:
                return jsonify(error="Could not create parent folder"), 500
            # proceed to create file below
        else:
            return jsonify(error="Not found"), 404

    # DELETE: remove a file
    # DELETE: remove a file
    if request.method == "DELETE":
        if not target.exists():
            return jsonify(error="Not found"), 404
        if target.is_dir():
            return jsonify(error="Target is a directory"), 400
        try:
            target.unlink()
            return jsonify(success=True)
        except Exception as e:
            return jsonify(error=str(e)), 500

    # HEAD and GET: retrieve file or directory
    if request.method in ("GET", "HEAD"):
        # Auto-regenerate stat_overview.md before serving it
        rel_path = target.relative_to(REPO_ROOT).as_posix()
        if rel_path == 'Player Root/PCs/stat_overview.md' or rel_path.endswith('/stat_overview.md'):
            try:
                generator_script = REPO_ROOT / 'Mycelium' / 'scripts' / 'Python' / 'generate_stat_overview.py'
                if generator_script.exists():
                    # Run generator silently
                    subprocess.run(
                        [sys.executable, str(generator_script)],
                        cwd=str(REPO_ROOT),
                        capture_output=True,
                        timeout=10
                    )
            except Exception:
                # If generation fails, just serve the existing file
                pass
        
        if target.is_dir():
            # For HEAD requests on directories, just return success
            if request.method == "HEAD":
                response = jsonify(success=True)
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response
            
            entries = []
            for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                rel = child.relative_to(REPO_ROOT).as_posix()
                entries.append({
                    "name": child.name,
                    "path": rel,
                    "type": "dir" if child.is_dir() else "file",
                })
            return jsonify(entries=entries)

        # Check if file is an image, HTML, or binary file
        file_ext = target.suffix.lower()
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'}
        direct_serve_extensions = image_extensions | {'.html', '.htm'}
        
        if file_ext in direct_serve_extensions:
            # For PNG files, strip color profiles on-the-fly before serving
            if file_ext == '.png' and request.method == 'GET':
                try:
                    from PIL import Image
                    import io
                    
                    # Load PNG
                    img = Image.open(str(target))
                    
                    # Strip ALL metadata by re-creating image
                    if img.mode == 'RGBA' or 'transparency' in img.info:
                        clean_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
                        clean_img.paste(img, (0, 0), img if img.mode == 'RGBA' else None)
                    else:
                        clean_img = Image.new('RGB', img.size)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        clean_img.paste(img)
                    
                    # Encode to PNG with NO metadata
                    output = io.BytesIO()
                    clean_img.save(output, format='PNG', optimize=False, save_all=False)
                    output.seek(0)
                    
                    response = send_file(
                        output,
                        mimetype='image/png',
                        download_name=target.name,
                        conditional=False
                    )
                    response.headers['Access-Control-Allow-Origin'] = '*'
                    response.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
                    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
                    return response
                except Exception as e:
                    print(f"PNG stripping failed, serving raw: {e}")
                    # Fall through to normal serving
            
            # Serve image and HTML files directly
            try:
                # Determine mimetype
                mimetype_map = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp',
                    '.svg': 'image/svg+xml',
                    '.bmp': 'image/bmp',
                    '.ico': 'image/x-icon',
                    '.html': 'text/html',
                    '.htm': 'text/html',
                }
                mimetype = mimetype_map.get(file_ext, 'application/octet-stream')
                # Use conditional_get and as_attachment=False for proper streaming
                response = send_file(
                    str(target), 
                    mimetype=mimetype,
                    conditional=True,  # Enable conditional GET (304 responses)
                    download_name=target.name,
                    max_age=3600  # Cache for 1 hour
                )
                # Add CORS headers explicitly
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
                # Add cache control for better performance
                response.headers['Cache-Control'] = 'public, max-age=3600'
                return response
            except Exception as e:
                return jsonify(error=str(e)), 500

        # Text file: return content + hash (or just headers for HEAD)
        if request.method == "HEAD":
            # For HEAD requests on text files, return minimal response with CORS headers
            response = jsonify(success=True)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
            
        try:
            text = target.read_text(encoding="utf-8")
        except Exception as e:
            return jsonify(error=str(e)), 500
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return jsonify(content=text, hash=h)

    # POST/PUT: save/update file content
    if request.method in ("POST", "PUT"):
        data = request.get_json() or {}
        content = data.get("content")
        if content is None:
            return jsonify(error="Missing content"), 400
        force = bool(data.get("force"))

        # If target exists and is a directory, error
        if target.exists() and target.is_dir():
            return jsonify(error="Target is a directory"), 400

        # If file exists and not force, allow overwrite (frontend handles conflicts),
        # but we still write here. Optionally future: check hashes.
        try:
            # ensure parent dir exists
            parent = target.parent
            if not parent.exists() or not parent.is_dir():
                return jsonify(error="Folder does not exist"), 400
            target.write_text(content or "", encoding="utf-8")
        except Exception as e:
            return jsonify(error=str(e)), 500

        # If the saved file is the shared stat_overview, parse it and write per-PC variable files
        try:
            rel = str(target.relative_to(REPO_ROOT).as_posix())
            if rel == 'Player Root/PCs/stat_overview.md':
                # parse the overview and write back per-PC variable files
                pcs = {}
                cur = None
                for line in content.splitlines():
                    m = re.match(r"^###\s+(\S.*)$", line)
                    if m:
                        cur = m.group(1).strip()
                        pcs[cur] = {}
                        continue
                    if cur is None:
                        continue
                    # parse table rows like | key | value | src |
                    if line.strip().startswith("|"):
                        cols = [c.strip() for c in line.split("|") if c.strip()]
                        if len(cols) >= 2:
                            key = cols[0]
                            val = cols[1]
                            # normalize keys to canonical
                            key_norm = key.replace(' ', '_')
                            if key_norm in ('max_hp', 'current_hp', 'evasion', 'general_armor'):
                                # map general_armor back to 'general armor'
                                if key_norm == 'general_armor':
                                    key_norm2 = 'general armor'
                                else:
                                    key_norm2 = key_norm
                                pcs[cur][key_norm2] = val
                # write per-pc files and update character sheets
                warnings = []
                for pcname, stats in pcs.items():
                    ok, err = write_pc_variable_files(pcname, stats)
                    if not ok:
                        warnings.append(f'{pcname}: variable write: {err}')
                    # Attempt to update the character sheet as well
                    try:
                        ok2, err2 = update_character_sheet(pcname, stats)
                        if not ok2:
                            # only record real errors (not 'no changes')
                            if err2 and 'no changes' not in err2:
                                warnings.append(f'{pcname}: sheet update: {err2}')
                    except Exception as e:
                        warnings.append(f'{pcname}: sheet update exception: {e}')
                # include parsed pcs in response so frontend can display what was parsed
                data['_stat_overview_parsed'] = pcs
                if warnings:
                    # include warnings in the response payload later
                    data['_stat_overview_write_warnings'] = warnings
            # Additionally, if any PC sheet file was saved via this generic
            # endpoint (e.g., Player Root/PCs/Anju/Anju Character Sheet.md),
            # extract canonical stats and write per-PC variable files so the
            # combined source files get updated.
            rel = str(target.relative_to(REPO_ROOT).as_posix())
            if rel.startswith('Player Root/PCs/') and rel != 'Player Root/PCs/stat_overview.md':
                parts = rel.split('/')
                if len(parts) >= 3:
                    pcname = parts[2]
                    try:
                        stats = parse_canonical_stats_from_text(content or "")
                        if stats:
                            ok, err = write_pc_variable_files(pcname, stats)
                            if not ok:
                                data.setdefault('_pc_write_warnings', []).append(f'{pcname}: {err}')
                    except Exception as e:
                        data.setdefault('_pc_write_warnings', []).append(str(e))
        except Exception:
            pass
        h = hashlib.sha256((content or "").encode("utf-8")).hexdigest()
        resp = {"success": True, "hash": h}
        # propagate any warnings produced by stat_overview or per-pc writes
        try:
            if isinstance(data, dict):
                if '_stat_overview_write_warnings' in data:
                    resp['stat_overview_warnings'] = data.get('_stat_overview_write_warnings')
                if '_pc_write_warnings' in data:
                    resp['pc_write_warnings'] = data.get('_pc_write_warnings')
        except Exception:
            pass
        return jsonify(resp)



@bp.route('/graphs/<path:seg>')
def graphs_alias(seg):
    """Serve generated graph files under Mycelium/scripts/manuals via a stable /graphs/ URL.

    This creates a safe alias so frontend consumers can link to /graphs/<path>
    instead of relying on /vault/... paths. Only files inside the manuals
    directory are served.
    """
    from pathlib import Path
    try:
        base_dir = (REPO_ROOT / 'Mycelium' / 'scripts' / 'manuals').resolve()
    except Exception:
        abort(500)
    # Candidate file path relative to manuals
    try:
        candidate = (base_dir / Path(seg)).resolve()
    except Exception:
        # treat malformed or unresolvable paths as not-found rather than
        # a bad request; this avoids noisy 400 entries from client probes.
        abort(404)
    # ensure candidate is inside the manuals dir
    try:
        if not candidate.is_file() or not candidate.exists():
            abort(404)
        # Python 3.9+: use is_relative_to for clear intent
        if not str(candidate).startswith(str(base_dir)):
            abort(403)
    except Exception:
        # defensive: treat unexpected failures as not-found to avoid 400 spam
        abort(404)
    rel = candidate.relative_to(base_dir)
    return send_from_directory(str(base_dir), str(rel))


@bp.route('/<path:seg>')
def serve_generated_wikigraph(seg):
    """Serve generated wikigraph HTML files from the repository root.

    This route only serves files whose names match the known wikigraph
    filename patterns to avoid exposing arbitrary repo files via HTTP.
    Example: GET /Player%20Root_wikigraph_sunburst.html
    """
    from urllib.parse import unquote
    # Decode percent-encoded segments (e.g. %20 -> space) so callers can request
    # URLs that include encoded spaces or other safe characters.
    raw_seg = unquote(seg)

    try:
        # Only allow filenames that look like wikigraph outputs
        allowed_suffixes = ('_wikigraph_sunburst.html', '_wikigraph_treemap.html', '_wikigraph.html')
        if not any(raw_seg.endswith(suf) for suf in allowed_suffixes):
            # Not a recognized generated graph file; let other routes handle it
            abort(404)

        candidate = (REPO_ROOT / raw_seg).resolve()
    except Exception:
        # treat resolution/parsing issues as not found rather than bad request
        abort(404)

    try:
        repo_resolved = REPO_ROOT.resolve()
        # If candidate doesn't exist at repo root, attempt to find a file
        # anywhere in the repo with the same basename (e.g., 'Player Root_wikigraph_sunburst.html')
        if not candidate.exists() or not candidate.is_file():
            found = None
            try:
                # match by unquoted basename (raw_seg may contain slashes; we want the filename)
                target_basename = Path(raw_seg).name
                for p in repo_resolved.rglob('*'):
                    try:
                        if p.is_file() and p.name == target_basename and any(p.name.endswith(suf) for suf in allowed_suffixes):
                            found = p
                            break
                    except Exception:
                        continue
            except Exception:
                found = None

            if found is None:
                abort(404)
            candidate = found

        # Ensure the candidate is inside the repository
        if not str(candidate).startswith(str(repo_resolved)):
            abort(403)
    except Exception:
        # defensive: return 404 for unexpected failures when resolving files
        abort(404)

    # Serve the file relative to the repository root
    rel = candidate.relative_to(repo_resolved)
    return send_from_directory(str(repo_resolved), str(rel))


@bp.route('/ws', methods=['GET'])
def ws_probe():
    """Lightweight HTTP probe for WebSocket path.

    Some frontends attempt a plain GET to /ws to detect a websocket
    endpoint; if no websocket server is attached the Flask stack will
    currently reply with 400 which clutters browser console logs. Return
    a 204 No Content for normal HTTP GET probes so clients see a benign
    response. Real websocket upgrades are handled separately by a proper
    websocket server layer and will not be affected by this handler.
    """
    return ('', 204)


@bp.route("/player_root/move", methods=["POST"])
def player_root_move():
    """Atomically move a file within Player Root.

    Expected JSON body: { "src": "Player Root/PCs/Anju/Anju Inventory.md", "dst": "Player Root/deleted/deleted_Anju Inventory.md" }
    Both paths may be provided with or without the leading "Player Root/" prefix.
    """
    data = request.get_json() or {}
    src = data.get("src")
    dst = data.get("dst")
    if not src or not dst:
        return jsonify(error="Missing src or dst"), 400

    def norm(p):
        """Normalize incoming paths by stripping an optional Player Root prefix."""
        s = str(p or "").strip()
        if s.startswith(PLAYER_ROOT_PREFIX):
            s = s[len(PLAYER_ROOT_PREFIX) :].lstrip("/")
        return s

    src_rel = norm(src)
    dst_rel = norm(dst)

    base = REPO_ROOT / "Player Root"
    src_path = (base / src_rel).resolve()
    dst_path = (base / dst_rel).resolve()

    # Helper to include debug info when enabled
    def _debug_info():
        """Collect resolved paths to aid debugging failed moves."""
        try:
            return {
                '_debug': '1',
                'src_resolved': str(src_path),
                'dst_resolved': str(dst_path),
            }
        except Exception:
            return {'_debug': '1'}

    debug_enabled = bool(os.environ.get('FLASK_DEBUG') or os.environ.get('MYCELIUM_DEBUG'))

    try:
        repo_resolved = REPO_ROOT.resolve()
        # Ensure both are inside the repo
        if (repo_resolved not in src_path.parents and src_path != repo_resolved) or (
            repo_resolved not in dst_path.parents and dst_path != repo_resolved
        ):
            resp = {'error': 'Path outside repository'}
            if debug_enabled:
                resp.update(_debug_info())
            return jsonify(resp), 400
    except Exception:
        resp = {'error': 'Path resolution error'}
        if debug_enabled:
            resp.update(_debug_info())
        return jsonify(resp), 400

    if not src_path.exists():
        resp = {'error': 'Source not found'}
        if debug_enabled:
            resp.update(_debug_info())
        return jsonify(resp), 404
    if src_path.is_dir():
        resp = {'error': 'Source is a directory'}
        if debug_enabled:
            resp.update(_debug_info())
        return jsonify(resp), 400

    # Ensure destination parent exists
    try:
        dst_parent = dst_path.parent
        if not dst_parent.exists():
            dst_parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        resp = {'error': f"Could not create destination folder: {e}"}
        if debug_enabled:
            resp.update(_debug_info())
        return jsonify(resp), 500

    # Attempt an atomic move (os.replace), fallback to shutil.move
    try:
        try:
            os.replace(str(src_path), str(dst_path))
        except Exception:
            shutil.move(str(src_path), str(dst_path))
    except Exception as e:
        resp = {'error': str(e)}
        if debug_enabled:
            resp.update(_debug_info())
        return jsonify(resp), 500

    rel = dst_path.relative_to(REPO_ROOT).as_posix()
    resp = {"success": True, "path": f"{PLAYER_ROOT_PREFIX}{rel}"}
    if debug_enabled:
        resp.update(_debug_info())
    return jsonify(resp)


@bp.route('/api/generate-graphs', methods=['POST'])
def generate_graphs():
    """Generate sunburst and treemap HTML files using Wikigraphs.py.

    Expected JSON body: { "folder": "Player Root/PCs/Anju" }

    Behavior/Assumptions:
      - The generated HTML files will be written into the folder specified by
        the `folder` parameter (must be a path inside the repository).
      - The generator will scan the configured Player Root (vault) for data.
        This keeps behaviour consistent with other repository tools.
    """
    data = request.get_json() or {}
    folder = (data.get('folder') or data.get('folderPath') or '').strip()

    # normalize incoming folder path
    # Treat an exact 'Player Root' (with or without trailing slash) as the repo root
    if folder.rstrip('/') == PLAYER_ROOT_PREFIX.rstrip('/'):
        rel_folder = ''
    elif folder.startswith(PLAYER_ROOT_PREFIX):
        rel_folder = folder[len(PLAYER_ROOT_PREFIX) :].lstrip('/')
    else:
        rel_folder = folder.lstrip('/')

    player_base = get_player_root_base()
    # compute target dir where HTML files will be written
    if player_base == REPO_ROOT:
        # repo-root layout: treat rel_folder as repo-relative
        target_dir = REPO_ROOT if not rel_folder else (REPO_ROOT / rel_folder)
    else:
        target_dir = player_base if not rel_folder else (player_base / rel_folder)

    try:
        target_dir = target_dir.resolve()
    except Exception:
        return jsonify(error='Invalid folder path'), 400

    # target_path is the folder the generator should scan; use the resolved target_dir
    target_path = target_dir

    # ensure inside repo
    try:
        repo_resolved = REPO_ROOT.resolve()
        if repo_resolved not in target_dir.parents and target_dir != repo_resolved:
            return jsonify(error='Folder is outside repository'), 400
    except Exception:
        return jsonify(error='Path resolution error'), 400

    if not target_dir.exists() or not target_dir.is_dir():
        return jsonify(error='Folder does not exist'), 400

    # Try to import Wikigraphs.make_graphs and call it directly for best UX.
    script_module = None
    tried_import = []
    make_graphs_func = None
    try:
        import importlib
        # try package-style import first
        tried_import.append('Mycelium.scripts.Python.Wikigraphs')
        script_module = importlib.import_module('Mycelium.scripts.Python.Wikigraphs')
    except Exception:
        script_module = None
    if script_module is None:
        try:
            tried_import.append('scripts.Python.Wikigraphs')
            script_module = importlib.import_module('scripts.Python.Wikigraphs')
        except Exception:
            script_module = None

    if script_module is not None:
        make_graphs_func = getattr(script_module, 'make_graphs', None)

    generated = []
    errors = []
    captured_stdout = ''
    captured_stderr = ''

    # Call make_graphs directly when available. Use target_path as the scan root
    # so the generator focuses on the requested folder, and use target_dir as
    # the output directory so files are written into the requested folder.
    if callable(make_graphs_func):
        try:
            # capture any prints the imported function may produce
            import io
            old_out, old_err = sys.stdout, sys.stderr
            buf_out, buf_err = io.StringIO(), io.StringIO()
            sys.stdout, sys.stderr = buf_out, buf_err
            try:
                make_graphs_func(root=target_path, outdir=target_dir)
            finally:
                sys.stdout, sys.stderr = old_out, old_err
            captured_stdout = buf_out.getvalue() or ''
            captured_stderr = buf_err.getvalue() or ''
            if captured_stdout:
                current_app.logger.info('[wikigraphs stdout]\n' + captured_stdout)
            if captured_stderr:
                current_app.logger.warning('[wikigraphs stderr]\n' + captured_stderr)
            # persist to log file
            try:
                import json
                with open(str(WIKIGRAPHS_LOG), 'a', encoding='utf-8') as lf:
                    # write stdout lines as structured JSON events
                    if captured_stdout:
                        for ln in captured_stdout.splitlines():
                            if ln.strip() == '':
                                continue
                            lf.write(json.dumps({'severity': 'info', 'text': ln}) + '\n')
                    if captured_stderr:
                        for ln in captured_stderr.splitlines():
                            if ln.strip() == '':
                                continue
                            lf.write(json.dumps({'severity': 'error', 'text': ln}) + '\n')
            except Exception:
                pass
        except Exception as e:
            errors.append(str(e))
    else:
        # Fallback: subprocess invocation of the script file
        try:
            script_path = REPO_ROOT.joinpath('Mycelium', 'scripts', 'Python', 'Wikigraphs.py')
            if not script_path.exists():
                script_path = REPO_ROOT.joinpath('Mycelium', 'scripts', 'manuals', 'Wikigraphs.py')
            if not script_path.exists():
                return jsonify(error='Wikigraphs.py not found to run'), 500
            # Use relative root arg like the existing /api/wikigraphs endpoint
            arg_root = str(rel_folder) if rel_folder else '.'
            cmd = [sys.executable, str(script_path), '--root', arg_root, '--out', str(target_dir)]
            proc = subprocess.run(cmd, cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            captured_stdout = proc.stdout or ''
            captured_stderr = proc.stderr or ''
            if captured_stdout:
                current_app.logger.info('[wikigraphs stdout]\n' + captured_stdout)
            if captured_stderr:
                current_app.logger.warning('[wikigraphs stderr]\n' + captured_stderr)
            # persist to log file
            try:
                import json
                with open(str(WIKIGRAPHS_LOG), 'a', encoding='utf-8') as lf:
                    if captured_stdout:
                        for ln in captured_stdout.splitlines():
                            if ln.strip() == '':
                                continue
                            lf.write(json.dumps({'severity': 'info', 'text': ln}) + '\n')
                    if captured_stderr:
                        for ln in captured_stderr.splitlines():
                            if ln.strip() == '':
                                continue
                            lf.write(json.dumps({'severity': 'error', 'text': ln}) + '\n')
            except Exception:
                pass
            if proc.returncode != 0:
                errors.append(proc.stderr or proc.stdout or f'Exit {proc.returncode}')
        except Exception as e:
            errors.append(str(e))

    # Collect generated files in the target directory matching wikigraph patterns
    try:
        from urllib.parse import quote
        for p in target_dir.iterdir():
            if not p.is_file():
                continue
            if p.name.endswith('_wikigraph_sunburst.html') or p.name.endswith('_wikigraph_treemap.html') or p.name.endswith('_wikigraph.html'):
                try:
                    # Prefer repo-relative path
                    rel = p.relative_to(REPO_ROOT).as_posix()
                except Exception:
                    # If that fails, try to express path relative to the player_base
                    try:
                        rel = (player_base.relative_to(REPO_ROOT).as_posix().rstrip('/') + '/' + p.relative_to(player_base).as_posix()).lstrip('/')
                    except Exception:
                        rel = p.as_posix()
                # URL-encode each path segment so the returned path can be requested
                parts = rel.split('/')
                quoted = '/'.join(quote(seg) for seg in parts if seg != '')
                generated.append('/' + quoted)
    except Exception:
        pass

    if errors and not generated:
        return jsonify(success=False, errors=errors, tried_import=tried_import, stdout=captured_stdout, stderr=captured_stderr), 500

    return jsonify(success=True, files=generated, errors=errors, tried_import=tried_import, stdout=captured_stdout, stderr=captured_stderr)


@bp.route("/player_root/search", methods=["GET"])
def player_root_search():
    """Search markdown files under Player Root for a substring.

    Query params:
      q - search query (required)
      max_files - optional, max number of files to return (default 200)

    Response: { results: [ { path: 'Player Root/PCs/Anju/Anju.md', matches: [ {line_no: N, context: ['prev','match','next'], excerpt: 'matched line snippet'} ], match_count: M } ] }
    """
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify(error='Missing query param q'), 400
    try:
        max_files = int(request.args.get('max_files', 200))
    except Exception:
        max_files = 200

    base = REPO_ROOT.joinpath('Player Root')
    try:
        base = base.resolve()
    except Exception:
        return jsonify(error='Repository path error'), 500

    out = []
    q_lower = q.lower()
    debug_enabled = bool(os.environ.get('FLASK_DEBUG') or os.environ.get('MYCELIUM_DEBUG'))
    # prepare filename tokenization for better ranking
    normalized_q = re.sub(r"\s+", " ", q_lower).strip()
    q_tokens = [t.strip() for t in re.split(r"\s+", normalized_q) if t.strip()]

    # Walk Player Root for .md files
    for p in base.rglob('*.md'):
        try:
            p_res = p.resolve()
        except Exception:
            continue
        # ensure inside repo
        try:
            repo_res = REPO_ROOT.resolve()
            if repo_res not in p_res.parents and p_res != repo_res:
                continue
        except Exception:
            continue

        # compute filename-based score boost
        filename = p_res.name or ""
        filename_lower = filename.lower()
        # strip extension for filename phrase matching (prefer 'Anju Character Sheet' over '.md')
        filename_no_ext = filename_lower.rsplit('.', 1)[0]
        score = 0
        filename_phrase_match = False
        filename_token_matches = []
        path_token_matches = []
        filename_match_ratio = 0.0
        
        # exact phrase in filename (no extension) -> very large boost
        if normalized_q and normalized_q in filename_no_ext:
            score += 5000
            filename_phrase_match = True
            
            # Add bonus based on how much of the filename the query represents
            # This favors shorter filenames that are closer matches
            # e.g., "Airdash" matching "Airdash.md" (100% match) vs "Airdash - Mahogany.md" (50% match)
            if len(filename_no_ext) > 0:
                filename_match_ratio = len(normalized_q) / len(filename_no_ext)
                # Scale the ratio bonus: up to 2000 points for a perfect match
                ratio_bonus = int(filename_match_ratio * 2000)
                score += ratio_bonus
        
        # token matches in filename -> medium boost
        for tok in q_tokens:
            if tok and tok in filename_no_ext:
                score += 500
                filename_token_matches.append(tok)
            # also boost if token appears anywhere in the file's repo-relative path
            try:
                rel_candidate = p_res.relative_to(REPO_ROOT).as_posix().lower()
            except Exception:
                rel_candidate = filename_lower
            if tok and tok in rel_candidate:
                score += 50
                path_token_matches.append(tok)

        # read lines
        try:
            text = p_res.read_text(encoding='utf-8')
        except Exception:
            continue
        lines = text.splitlines()
        matches = []
        for i, line in enumerate(lines):
            if q_lower in line.lower():
                # gather context: two lines before and after where available
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                context = lines[start:end]
                matches.append({
                    'line_no': i + 1,
                    'excerpt': line.strip(),
                    'context': context,
                })
        # include files that either have content matches, or have a filename/path match score
        if matches or score > 0:
            rel = p_res.relative_to(REPO_ROOT).as_posix()
            # Avoid double-prefixing 'Player Root/' if the relative path already includes it
            display_path = rel if rel.startswith(PLAYER_ROOT_PREFIX) else f"{PLAYER_ROOT_PREFIX}{rel}"
            # add content-based score (each match contributes)
            score += 10 * len(matches)
            
            # Apply path length penalty - prefer shorter paths
            # Count directory depth (number of slashes in path)
            path_depth = display_path.count('/')
            # Subtract points based on depth (each level costs 100 points)
            # This ensures shorter paths rank higher when scores are otherwise equal
            depth_penalty = path_depth * 100
            score -= depth_penalty
            
            entry = {
                'path': display_path,
                'match_count': len(matches),
                'matches': matches,
                'score': score,
            }
            if debug_enabled:
                entry['_debug_score'] = {
                    'filename_phrase': filename_phrase_match,
                    'filename_tokens': filename_token_matches,
                    'path_tokens': path_token_matches,
                    'content_matches': [m['line_no'] for m in matches],
                    'path_depth': path_depth,
                    'filename_match_ratio': filename_match_ratio,
                    'score_breakdown': {
                        'filename_phrase': 5000 if filename_phrase_match else 0,
                        'filename_match_ratio': int(filename_match_ratio * 2000) if filename_phrase_match else 0,
                        'filename_tokens': 500 * len(filename_token_matches),
                        'path_tokens': 50 * len(path_token_matches),
                        'content_matches': 10 * len(matches),
                        'depth_penalty': -depth_penalty,
                    },
                }
            out.append(entry)

    # sort primarily by score (desc), then match_count, then path
    out.sort(key=lambda e: (-(e.get('score', 0)), -e['match_count'], e['path']))
    if len(out) > max_files:
        out = out[:max_files]
    return jsonify(results=out)


@bp.route('/api/wikigraphs', methods=['POST'])
def api_wikigraphs():
    """Run the repository's Wikigraphs script for a given folder under Player Root.

    Expected JSON body: { "root": "Player Root/PCs/Anju" } or { "root": "PCs/Anju" }
    """
    data = request.get_json() or {}
    root = data.get('root') or ''
    s = str(root or '').strip()
    # Accept either 'Player Root' or 'Player Root/...' forms from the client.
    prefix_no_slash = PLAYER_ROOT_PREFIX.rstrip('/')
    if s == prefix_no_slash:
        s = ''
    elif s.startswith(prefix_no_slash + '/'):
        s = s[len(prefix_no_slash) + 1 :].lstrip('/')
    target_rel = s or ''

    # resolve target folder using the configured player base
    try:
        player_base = get_player_root_base()
        if target_rel:
            target_path = (player_base / target_rel).resolve()
        else:
            target_path = player_base.resolve()
    except Exception as e:
        return jsonify({'error': f'Path resolution error: {e}'}), 400

    try:
        repo_res = REPO_ROOT.resolve()
        if repo_res not in target_path.parents and target_path != repo_res:
            return jsonify({'error': 'Target outside repository'}), 400
    except Exception:
        return jsonify({'error': 'Repository resolution error'}), 500

    if not target_path.exists() or not target_path.is_dir():
        return jsonify({'error': 'Target folder not found'}), 404

    # Try known script locations
    script_path = REPO_ROOT.joinpath('Mycelium', 'scripts', 'Python', 'Wikigraphs.py')
    if not script_path.exists():
        script_path = REPO_ROOT.joinpath('Mycelium', 'scripts', 'manuals', 'Wikigraphs.py')
        if not script_path.exists():
            return jsonify({'error': 'Wikigraphs script not found on server'}), 500

    # When no specific target was requested, pass '.' so the script's
    # argument parser receives a sensible default rather than an empty string.
    arg_root = str(target_rel) if target_rel else '.'
    cmd = [sys.executable, str(script_path), '--root', arg_root]
    try:
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300)
        out = proc.stdout or ''
        err = proc.stderr or ''
        status = proc.returncode
        if status != 0:
            return jsonify({'success': False, 'code': status, 'stdout': out, 'stderr': err}), 500

        # Attempt to discover the generated graph HTML files and return
        # URL-encoded paths so the frontend can probe them directly. This
        # helps when filenames contain spaces which become percent-encoded
        # in HTTP requests.
        written = []
        try:
            from urllib.parse import quote

            # Collect candidate files across the repository that look like
            # output of the generator.
            candidates = list(repo_res.rglob('*_wikigraph_*.html'))
            for p in candidates:
                try:
                    rel = p.relative_to(repo_res).as_posix()
                except Exception:
                    # skip paths that cannot be relativized
                    continue

                # Decide whether this file is relevant to the requested target
                rel_norm = rel
                # If a specific target was requested, require target_rel to
                # appear in the relative path.
                if target_rel:
                    if target_rel.replace('\\', '/') not in rel_norm:
                        continue
                else:
                    # root requested: behavior depends on whether the repo
                    # uses an explicit 'Player Root' folder or places player
                    # content at the repository root. When a literal Player
                    # Root folder exists, prefer files under it; otherwise
                    # accept repo-root candidates.
                    player_base = get_player_root_base()
                    if player_base != REPO_ROOT:
                        if not (rel_norm.startswith('Player Root/') or 'Player Root' in rel_norm):
                            continue

                # URL-encode each path segment to produce a safe HTTP path
                parts = rel.split('/')
                quoted = '/'.join(quote(p) for p in parts)
                written.append('/' + quoted)
        except Exception:
            written = []

        return jsonify({'success': True, 'code': status, 'stdout': out, 'stderr': err, 'written': written})
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Wikigraphs run timed out'}), 504
    except Exception as e:
        return jsonify({'error': f'Failed to run Wikigraphs: {e}'}), 500


@bp.route('/api/tail-wikigraphs')
def tail_wikigraphs():
    """Stream the latest Wikigraphs log as Server-Sent Events (SSE).

    Clients can open an EventSource to this endpoint to receive new log
    lines as they are appended. This is a simple implementation which polls
    the log file for new content.
    """
    def event_stream():
        """Yield log lines as SSE data events while the connection remains open."""
        import time
        # Keep polling: if the log file doesn't exist yet, wait silently until it does.
        while True:
            try:
                # Open file and seek to the end
                with open(str(WIKIGRAPHS_LOG), 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(0, os.SEEK_END)
                    while True:
                        line = f.readline()
                        if line:
                            # SSE data: each event is a data: line
                            yield f'data: {line.rstrip()}\n\n'
                        else:
                            # sleep briefly before retrying
                            time.sleep(0.2)
            except FileNotFoundError:
                # Do not send a placeholder message; wait for the log file to appear.
                time.sleep(0.5)
                continue
            except GeneratorExit:
                return
            except Exception as e:
                # Send an explicit error event (useful for debugging), then continue polling.
                yield f'data: (tail error: {e})\n\n'
                time.sleep(0.5)
                continue

    return Response(stream_with_context(event_stream()), mimetype='text/event-stream')


@bp.route("/update_sheet/<pcname>", methods=["POST"])
def update_sheet(pcname):
    """Write a character sheet and optionally propagate derived variables."""
    data = request.get_json() or {}
    content = data.get("content")
    propagate = bool(data.get("propagate", False))

    # locate the PC directory under Player Root/PCs/<pcname>
    pc_dir = REPO_ROOT / "Player Root" / "PCs" / pcname
    try:
        pc_dir = pc_dir.resolve()
    except Exception:
        return jsonify(error="Invalid PC path"), 400

    if not pc_dir.exists() or not pc_dir.is_dir():
        return jsonify(error="PC folder not found"), 404

    def _find_sheet_file(pc_dir, pcname):
        """Pick the best-matching markdown sheet for the given PC."""
        candidates = []
        for p in pc_dir.iterdir():
            if not p.is_file():
                continue
            name = p.name.lower()
            if not name.endswith(".md"):
                continue
            if pcname.lower() in name and ("character" in name or "sheet" in name):
                candidates.append(p)
        if not candidates:
            for p in pc_dir.iterdir():
                if p.is_file() and p.name.lower().endswith(".md") and p.name.lower().startswith(pcname.lower()):
                    candidates.append(p)
        return candidates[0] if candidates else None

    def _snapshot_folder(pc_dir):
        """Return name/path/content/hash for markdown files in the PC folder."""
        files = []
        for p in sorted(pc_dir.iterdir(), key=lambda x: x.name.lower()):
            if not p.is_file() or not p.name.lower().endswith('.md'):
                continue
            try:
                text = p.read_text(encoding='utf-8')
            except Exception:
                text = ''
            h = hashlib.sha256((text or '').encode('utf-8')).hexdigest()
            files.append({
                'name': p.name,
                'path': str(p.relative_to(REPO_ROOT).as_posix()),
                'content': text,
                'hash': h,
            })
        return files

    target = _find_sheet_file(pc_dir, pcname)
    if content is None:
        # No content provided: just return a snapshot of the folder
        if not target:
            return jsonify(error="No character sheet file found for PC"), 404
        files = _snapshot_folder(pc_dir)
        return jsonify(success=True, files=files)

    # content provided: write sheet and return folder snapshot
    if not target:
        return jsonify(error="No character sheet file found for PC"), 404

    try:
        target.write_text(content or "", encoding="utf-8")
    except Exception as e:
        return jsonify(error=str(e)), 500

    # After saving the sheet, attempt to extract canonical stats and write per-PC variable files
    try:
        stats = parse_canonical_stats_from_text(content or "")
        if stats:
            ok, err = write_pc_variable_files(pcname, stats)
            if not ok:
                # include a warning but continue to propagation
                write_warning = f'writing pc variable files failed: {err}'
            else:
                write_warning = None
        else:
            write_warning = None
    except Exception as e:
        write_warning = f'failed to parse/write pc variables: {e}'

    # after save, return whole folder snapshot so caller can sync
    # If client requested propagation/regeneration, call the repository's
    # propagation helper (watch_and_regen.propagate_environmental_from_sheet)
    if propagate:
        try:
            # Ensure repository root is on sys.path so package imports succeed when
            # this module is executed directly (no parent package context).
            import sys as _sys
            repo_str = str(REPO_ROOT)
            if repo_str not in _sys.path:
                _sys.path.insert(0, repo_str)

            # Try normal package import first, then fall back to file-based import.
            # Try package imports using importlib to avoid static import errors
            import importlib as _im
            wr = None
            for modname in ("Mycelium.scripts.Python.watch_and_regen", "Mycelium.scripts.python.watch_and_regen"):
                try:
                    wr = _im.import_module(modname)
                    break
                except Exception:
                    wr = None
            if wr is None:
                # Fall back to file-based import from the same directory as this module
                import importlib.util as _il
                base = Path(__file__).resolve().parent
                alt = base.joinpath('watch_and_regen.py')
                spec = _il.spec_from_file_location('watch_and_regen', str(alt))
                if spec is None or spec.loader is None:
                    raise ImportError('could not load watch_and_regen module')
                wr = _il.module_from_spec(spec)
                spec.loader.exec_module(wr)  # type: ignore
            # prepare args expected by the propagate helper
            from types import SimpleNamespace
            a = SimpleNamespace(dry_run=False, create_placeholders=False)
            # Use the server's REPO_ROOT so propagation operates on the same repository
            # paths the frontend expects. Prefer the 'environmental' subfolder if it
            # exists (many templates live under Player Root/variable/environmental),
            # so the propagation helper will write canonical files where templates live.
            variable_root = REPO_ROOT.joinpath('Player Root', 'variable')
            env_sub = variable_root.joinpath('environmental')
            vars_root = env_sub if env_sub.exists() and env_sub.is_dir() else variable_root
            pcs_dir = REPO_ROOT.joinpath('Player Root', 'PCs')
            # recreate_pcs script path (best-effort)
            script = REPO_ROOT.joinpath('Mycelium', 'scripts', 'Python', 'recreate_pcs.py')

            # call the propagation function; it will update canonical variable files
            # and record written files in wr._recently_written
            try:
                wr.propagate_environmental_from_sheet(target, vars_root, pcs_dir, script, a)
            except Exception as e:
                # non-fatal: include warning in the response so clients can surface it
                files = _snapshot_folder(pc_dir)
                relpath = str(target.relative_to(REPO_ROOT).as_posix())
                return jsonify(success=True, path=relpath, files=files, warning=f'propagation failed: {e}')
            # After propagation succeeds, attempt to regenerate the aggregated
            # stat overview so the frontend can display up-to-date derived stats.
            try:
                import subprocess as _sub
                # prefer the same interpreter running this server
                gen = REPO_ROOT.joinpath('Mycelium', 'scripts', 'Python', 'generate_stat_overview.py')
                if gen.exists():
                    _sub.run([_sys.executable, str(gen)], check=True, cwd=str(REPO_ROOT))
            except Exception as ge:
                files = _snapshot_folder(pc_dir)
                relpath = str(target.relative_to(REPO_ROOT).as_posix())
                # include write_warning in response if present
                if write_warning:
                    return jsonify(success=True, path=relpath, files=files, warning=f'propagation succeeded but generate_stat_overview failed: {ge}; {write_warning}')
                return jsonify(success=True, path=relpath, files=files, warning=f'propagation succeeded but generate_stat_overview failed: {ge}')
        except Exception as e:
            # could not import or invoke propagation; return success but include warning
            files = _snapshot_folder(pc_dir)
            relpath = str(target.relative_to(REPO_ROOT).as_posix())
            return jsonify(success=True, path=relpath, files=files, warning=f'propagation unavailable: {e}')

    files = _snapshot_folder(pc_dir)
    relpath = str(target.relative_to(REPO_ROOT).as_posix())
    if write_warning:
        return jsonify(success=True, path=relpath, files=files, warning=write_warning)
    resp = jsonify(success=True, path=relpath, files=files)
    # return the normal response
    # NOTE: subsequent routes appended below
    
    # --- Additional endpoint: run Wikigraphs for a folder under Player Root ---
    @bp.route('/player_root/wikigraphs', methods=['POST'])
    def player_root_wikigraphs():
        """Run the repository's Wikigraphs script for a given folder under Player Root.

        Expected JSON body: { "root": "Player Root/PCs/Anju" } or { "root": "PCs/Anju" }
        """
        data = request.get_json() or {}
        root = data.get('root') or ''
        s = str(root or '').strip()
        if s.startswith(PLAYER_ROOT_PREFIX):
            s = s[len(PLAYER_ROOT_PREFIX):].lstrip('/')
        target_rel = s or ''

        # resolve target folder
        try:
            base = (REPO_ROOT / 'Player Root').resolve()
            target_path = (base / target_rel).resolve()
        except Exception as e:
            return jsonify({'error': f'Path resolution error: {e}'}), 400

        try:
            repo_res = REPO_ROOT.resolve()
            if repo_res not in target_path.parents and target_path != repo_res:
                return jsonify({'error': 'Target outside repository'}), 400
        except Exception:
            return jsonify({'error': 'Repository resolution error'}), 500

        if not target_path.exists() or not target_path.is_dir():
            return jsonify({'error': 'Target folder not found'}), 404

        # Try known script locations
        script_path = REPO_ROOT.joinpath('Mycelium', 'scripts', 'Python', 'Wikigraphs.py')
        if not script_path.exists():
            script_path = REPO_ROOT.joinpath('Mycelium', 'scripts', 'manuals', 'Wikigraphs.py')
            if not script_path.exists():
                return jsonify({'error': 'Wikigraphs script not found on server'}), 500

        cmd = [sys.executable, str(script_path), '--root', str(target_rel)]
        try:
            proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300)
            out = proc.stdout or ''
            err = proc.stderr or ''
            status = proc.returncode
            if status != 0:
                return jsonify({'success': False, 'code': status, 'stdout': out, 'stderr': err}), 500
            return jsonify({'success': True, 'code': status, 'stdout': out, 'stderr': err})
        except subprocess.TimeoutExpired:
            return jsonify({'error': 'Wikigraphs run timed out'}), 504
        except Exception as e:
            return jsonify({'error': f'Failed to run Wikigraphs: {e}'}), 500

    return resp


@bp.route('/api/characters/customizations', methods=['GET'])
def get_character_customizations():
    """Return all stored character customization files (folder color + avatar matrices)."""
    try:
        customizations = load_all_customizations()
        return jsonify({'customizations': customizations})
    except Exception as e:
        return jsonify({'error': f'Failed to read customizations: {e}'}), 500


@bp.route('/api/characters/<name>/customization', methods=['GET', 'POST'])
def character_customization(name):
    """Read or persist customization for a specific character."""
    if request.method == 'GET':
        data = load_character_customization(name)
        if not data:
            data = {
                'name': name,
                'folderColor': None,
                'avatar': default_avatar_matrix(),
                'avatarPng': None,
                'updated_at': None
            }
        return jsonify(data)

    body = request.get_json() or {}
    folder_color = body.get('folderColor') or body.get('folder_color')
    avatar = body.get('avatar')
    avatar_png = body.get('avatarPng')

    if folder_color and not _is_valid_hex_color(folder_color):
        return jsonify({'error': 'folderColor must be a hex string like #aabbcc'}), 400

    try:
        payload = save_character_customization(
            name, 
            folder_color, 
            avatar or default_avatar_matrix(),
            avatar_png
        )
        return jsonify({'success': True, 'customization': payload})
    except Exception as e:
        return jsonify({'error': f'Failed to save customization: {e}'}), 500


@bp.route('/api/file-colors', methods=['GET'])
def get_file_colors():
    """
    Return color mapping for files and folders in the current directory tree.
    Colors are computed based on element tags and hierarchical blending.
    """
    try:
        # Import the color computation module
        sys.path.insert(0, str(Path(__file__).parent))
        from file_colors import compute_file_colors
    except Exception as e:
        return jsonify({'error': f'Failed to import file_colors module: {e}'}), 500
    
    # Get the player root base
    base = get_player_root_base()
    
    # Compute colors for all files/folders
    try:
        colors = compute_file_colors(base, exts=['.md'], excludes=['.git', '__pycache__', 'node_modules'])
        custom_folder_colors = {}
        try:
            customizations = load_all_customizations()
            for cname, cdata in customizations.items():
                col = cdata.get('folderColor')
                if col:
                    # Player Root relative paths use PCs/<Name>/
                    colors[f"PCs/{cname}/"] = col
                    custom_folder_colors[cname] = col
        except Exception:
            pass
        return jsonify({'colors': colors, 'custom_folder_colors': custom_folder_colors})
    except Exception as e:
        return jsonify({'error': f'Failed to compute colors: {e}'}), 500


@bp.route('/api/file/<path:filepath>', methods=['GET'])
def get_file_content(filepath):
    """
    RESTful endpoint to get file content.
    This is an alias for /player_root/<path> for cleaner API semantics.
    """
    # Get the player root base
    player_base = get_player_root_base()
    
    # Resolve the file path
    target = player_base / filepath
    
    try:
        target = target.resolve()
    except Exception:
        return jsonify({'error': 'Invalid path'}), 400
    
    # Security check: ensure target is inside repo
    try:
        repo_resolved = REPO_ROOT.resolve()
        if repo_resolved not in target.parents and target != repo_resolved:
            return jsonify({'error': 'Path outside repository'}), 403
    except Exception:
        return jsonify({'error': 'Path resolution error'}), 400
    
    # Check if file exists
    if not target.exists():
        return jsonify({'error': 'File not found'}), 404
    
    # Must be a file, not a directory
    if target.is_dir():
        return jsonify({'error': 'Path is a directory'}), 400
    
    # Check if it's an image or binary file
    file_ext = target.suffix.lower()
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'}
    
    if file_ext in image_extensions:
        # Serve image files directly, stripping PNG profiles on-the-fly
        mimetype_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.bmp': 'image/bmp',
            '.ico': 'image/x-icon',
        }
        mimetype = mimetype_map.get(file_ext, 'application/octet-stream')

        # For PNGs, strip metadata/ICC profiles to avoid color shifts (same as player_root handler)
        if file_ext == '.png' and request.method == 'GET':
            try:
                from PIL import Image
                import io

                img = Image.open(str(target))
                if img.mode == 'RGBA' or 'transparency' in img.info:
                    clean_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    clean_img.paste(img, (0, 0), img if img.mode == 'RGBA' else None)
                else:
                    clean_img = Image.new('RGB', img.size)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    clean_img.paste(img)

                output = io.BytesIO()
                clean_img.save(output, format='PNG', optimize=False, save_all=False)
                output.seek(0)

                response = send_file(
                    output,
                    mimetype='image/png',
                    download_name=target.name,
                    conditional=False
                )
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Cache-Control'] = 'public, max-age=3600'
                return response
            except Exception as e:
                print(f"PNG stripping failed for /file: {e}")
                # Fall through to normal serving
        
        try:
            response = send_file(
                str(target),
                mimetype=mimetype,
                conditional=True,
                download_name=target.name,
                max_age=3600
            )
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Cache-Control'] = 'public, max-age=3600'
            return response
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # Text file: return content as JSON
    try:
        content = target.read_text(encoding='utf-8')
        h = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        return jsonify({
            'content': content,
            'hash': h,
            'path': filepath,
            'name': target.name,
            'size': len(content)
        })
    except UnicodeDecodeError:
        return jsonify({'error': 'File is not a text file'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/stat_overview', methods=['GET'])
def get_stat_overview():
    """
    Return parsed stat overview data in JSON format.
    Automatically regenerates the stat overview file before reading.
    """
    try:
        # Run the stat overview generator
        generator_script = REPO_ROOT / 'Mycelium' / 'scripts' / 'Python' / 'generate_stat_overview.py'
        if not generator_script.exists():
            return jsonify({'error': 'Stat overview generator script not found'}), 404
        
        # Execute the generator
        result = subprocess.run(
            [sys.executable, str(generator_script)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Failed to generate stat overview',
                'stderr': result.stderr
            }), 500
        
        # Read the generated file
        stat_file = REPO_ROOT / 'Player Root' / 'PCs' / 'stat_overview.md'
        if not stat_file.exists():
            return jsonify({'error': 'Stat overview file not found after generation'}), 404
        
        content = stat_file.read_text(encoding='utf-8')
        
        # Parse the markdown content into structured JSON
        parsed = parse_stat_overview_content(content)
        
        # Add metadata
        parsed['last_generated'] = stat_file.stat().st_mtime
        parsed['file_path'] = str(stat_file.relative_to(REPO_ROOT))
        
        return jsonify(parsed)
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Stat overview generation timed out'}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to get stat overview: {str(e)}'}), 500


@bp.route('/api/stat_overview/regenerate', methods=['POST'])
def regenerate_stat_overview():
    """
    Explicitly regenerate the stat overview file.
    """
    try:
        generator_script = REPO_ROOT / 'Mycelium' / 'scripts' / 'Python' / 'generate_stat_overview.py'
        if not generator_script.exists():
            return jsonify({'error': 'Stat overview generator script not found'}), 404
        
        result = subprocess.run(
            [sys.executable, str(generator_script)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Failed to regenerate stat overview',
                'stderr': result.stderr
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Stat overview regenerated successfully',
            'stdout': result.stdout
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Stat overview generation timed out'}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to regenerate stat overview: {str(e)}'}), 500


@bp.route('/api/environmental_variable', methods=['POST'])
def update_environmental_variable():
    """
    Update an environmental variable (like environmental_water_charge).
    Expects JSON: { "name": "environmental_water_charge", "current": 5, "max": 10 }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        name = data.get('name', '')
        current = data.get('current', 0)
        max_value = data.get('max', 0)
        
        if not name:
            return jsonify({'error': 'Missing "name" field'}), 400
        
        # Construct the file path - assumes environmental variables are in Player Root/variable/environmental/
        env_var_path = get_player_root_base() / 'variable' / 'environmental' / f'{name}.md'
        
        if not env_var_path.exists():
            return jsonify({'error': f'Environmental variable file not found: {env_var_path}'}), 404
        
        # Read the existing file to preserve tags and structure
        content = env_var_path.read_text(encoding='utf-8')
        
        # Parse content - typically: value on first line, then blank, then tags
        lines = content.split('\n')
        new_lines = []
        
        # Add the new value as the first line
        new_lines.append(f'{current}/{max_value}')
        
        # Preserve blank lines and tags
        found_tags = False
        for line in lines:
            stripped = line.strip()
            # Skip the old value line (first non-tag, non-empty line)
            if not found_tags and not stripped.startswith('#') and stripped:
                continue
            # Keep blank lines and tag lines
            if not stripped or stripped.startswith('#'):
                new_lines.append(line)
                if stripped.startswith('#'):
                    found_tags = True
        
        # Write back to file
        env_var_path.write_text('\n'.join(new_lines), encoding='utf-8')
        
        return jsonify({
            'success': True,
            'message': f'Updated {name}',
            'value': f'{current}/{max_value}'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/environmental_variable/<variable_name>', methods=['GET'])
def get_environmental_variable(variable_name):
    """
    Get an environmental variable value.
    Returns JSON: { "name": "environmental_water_charge", "current": 5, "max": 10 }
    """
    try:
        # Construct the file path
        env_var_path = get_player_root_base() / 'variable' / 'environmental' / f'{variable_name}.md'
        
        if not env_var_path.exists():
            return jsonify({'error': f'Environmental variable file not found: {variable_name}'}), 404
        
        # Read the file content
        content = env_var_path.read_text(encoding='utf-8')
        
        # Parse content - typically: value on first line, then blank, then tags
        lines = content.split('\n')
        value_line = ''
        
        for line in lines:
            stripped = line.strip()
            # Find the first non-tag, non-empty line
            if stripped and not stripped.startswith('#'):
                value_line = stripped
                break
        
        # Parse current/max format
        current = 0
        max_value = 0
        
        if value_line:
            slashMatch = re.match(r'^(\d+)\s*\/\s*(\d+)$', value_line)
            if slashMatch:
                current = int(slashMatch.group(1))
                max_value = int(slashMatch.group(2))
            else:
                # Single number format
                try:
                    num = int(value_line)
                    current = num
                    max_value = num
                except ValueError:
                    pass
        
        return jsonify({
            'name': variable_name,
            'current': current,
            'max': max_value
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
    in_table = False
    
    for i, line in enumerate(lines):
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

@bp.route('/api/clear_ready/<character_name>', methods=['POST'])
def clear_ready_state(character_name):
    """
    Clear the ready state for a character by setting it to 'no' in their character sheet.
    """
    try:
        # Find the character sheet file
        player_root = get_player_root_base()
        pc_file = player_root / 'PCs' / character_name / f'{character_name} character sheet.md'
        
        if not pc_file.exists():
            return jsonify({'error': f'Character sheet not found for {character_name}'}), 404
        
        # Read the file
        content = pc_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # Find and update the ready line in the vitals section
        in_vitals = False
        ready_found = False
        
        for i, line in enumerate(lines):
            if '## Vitals' in line:
                in_vitals = True
                continue
            elif line.startswith('## ') and in_vitals:
                # We've moved past vitals without finding ready
                break
            
            if in_vitals and '| ready' in line.lower():
                # Update the ready line
                parts = line.split('|')
                if len(parts) >= 3:
                    parts[2] = '                    no '
                    lines[i] = '|'.join(parts)
                    ready_found = True
                break
        
        if not ready_found:
            # If ready wasn't found, we need to add it
            # Find the end of the vitals table
            for i, line in enumerate(lines):
                if '## Vitals' in line:
                    in_vitals = True
                    continue
                elif in_vitals and line.startswith('## '):
                    # Insert before this line
                    lines.insert(i, '| ready             |                    no |')
                    break
        
        # Write the file back
        new_content = '\n'.join(lines)
        pc_file.write_text(new_content, encoding='utf-8')
        
        return jsonify({'success': True, 'character': character_name})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/analyze-moves', methods=['POST'])
def analyze_moves():
    """Analyze bending moves for specific elements and levels.
    
    Expected JSON body:
    {
        "elements": ["air", "water"],
        "levels": [1, 2],
        "mode": "balance" | "uniqueness" | "simplicity" | "full"
    }
    
    Returns:
    {
        "moves": [
            {
                "name": "Air Blade",
                "level": 1,
                "element": "air",
                "actionType": "Action",
                "range": "...",
                "damage": "...",
                "effects": "...",
                "description": "...",
                "filePath": "...",
                "mlBalanceScore": ...,
                "mlSimplicityScore": ...,
                "mlFullScore": ...
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()
        elements = data.get('elements', ['air'])
        if isinstance(elements, str):
            elements = [elements]
        levels = data.get('levels', [1, 2])
        mode = data.get('mode', 'balance')  # balance, uniqueness, simplicity, full
        
        # Build paths to bending moves
        player_root = get_player_root_base()
        
        moves = []
        
        for element in elements:
            element_lower = element.lower()
            element_path = player_root / 'Rules' / 'Bending Rules' / element_lower.capitalize() / f'{element_lower.capitalize()}bending Moves'
            
            if not element_path.exists():
                print(f'Warning: Element path not found: {element_path}')
                continue
            
            for level in levels:
                level_path = element_path / f'Level {level}'
                if not level_path.exists():
                    continue
                
                # Find all .md files in this level
                for move_file in level_path.glob('*.md'):
                    try:
                        content = move_file.read_text(encoding='utf-8')
                        move_info = parse_move_content(content, move_file.stem, level, element_lower)
                        move_info['filePath'] = str(move_file.relative_to(REPO_ROOT))
                        
                        # Add scoring based on mode
                        if mode in ['balance', 'full'] and BALANCE_SCORER_AVAILABLE:
                            try:
                                balance_scorer = get_scorer()
                                balance_result = balance_scorer.score_move(move_info)
                                balance_feedback = balance_scorer.generate_feedback(move_info, balance_result)
                                
                                move_info['mlBalanceScore'] = balance_result['score']
                                move_info['mlBalanceScoringMethod'] = balance_result['method']
                                move_info['mlBalanceFeedback'] = balance_feedback
                            except Exception as e:
                                print(f"Balance scoring error for {move_info['name']}: {e}")
                        
                        if mode in ['simplicity', 'full'] and SIMPLICITY_SCORER_AVAILABLE:
                            try:
                                simplicity_scorer = get_simplicity_scorer()
                                simplicity_score = simplicity_scorer.calculate_score(move_info)
                                simplicity_feedback = simplicity_scorer.generate_feedback(move_info)
                                
                                move_info['mlSimplicityScore'] = simplicity_score
                                move_info['mlSimplicityFeedback'] = simplicity_feedback
                            except Exception as e:
                                print(f"Simplicity scoring error for {move_info['name']}: {e}")
                        
                        # Calculate uniqueness score (for uniqueness or full mode)
                        if mode in ['uniqueness', 'full']:
                            try:
                                uniqueness_score = calculate_uniqueness_score(move_info)
                                move_info['uniquenessScore'] = uniqueness_score
                            except Exception as e:
                                print(f"Uniqueness scoring error for {move_info['name']}: {e}")
                                move_info['uniquenessScore'] = 5.0
                        
                        # Full analysis mode combines all three
                        if mode == 'full' and FULL_ANALYSIS_SCORER_AVAILABLE:
                            try:
                                # Need all three scores
                                balance_score = move_info.get('mlBalanceScore', 5.0)
                                simplicity_score = move_info.get('mlSimplicityScore', 5.0)
                                uniqueness_score = move_info.get('uniquenessScore', 5.0)
                                
                                full_scorer = get_full_analysis_scorer()
                                full_result = full_scorer.calculate_score(
                                    uniqueness_score,
                                    balance_score,
                                    simplicity_score,
                                    uniqueness_data=move_info.get('uniquenessData'),
                                    balance_data=move_info.get('mlBalanceFeedback'),
                                    simplicity_data=move_info.get('mlSimplicityFeedback')
                                )
                                full_feedback = full_scorer.generate_feedback(
                                    uniqueness_score,
                                    balance_score,
                                    simplicity_score,
                                    uniqueness_data=move_info.get('uniquenessData'),
                                    balance_data=move_info.get('mlBalanceFeedback'),
                                    simplicity_data=move_info.get('mlSimplicityFeedback')
                                )
                                
                                move_info['mlFullScore'] = full_result['score']
                                move_info['mlFullMethod'] = full_result['method']
                                move_info['mlFullBreakdown'] = full_result['breakdown']
                                move_info['mlFullFeedback'] = full_feedback
                            except Exception as e:
                                print(f"Full analysis error for {move_info['name']}: {e}")
                        
                        moves.append(move_info)
                    except Exception as e:
                        print(f"Error parsing {move_file}: {e}")
                        continue
        
        return jsonify({'moves': moves, 'elements': elements, 'levels': levels, 'mode': mode})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/balance-visualization', methods=['POST'])
def balance_visualization():
    """Generate visualization data for balance score distributions.
    
    Expected JSON body:
    {
        "moves": [array of move objects with mlBalanceScore]
    }
    
    Returns:
    {
        "histogram": {...},
        "boxplot": {...},
        "scatterplot": {...},
        "statistics": {...}
    }
    """
    try:
        data = request.get_json()
        moves = data.get('moves', [])
        
        if not moves:
            return jsonify({'error': 'No moves provided'}), 400
        
        # Extract scores
        scores = []
        move_names = []
        elements = []
        levels = []
        action_types = []
        
        for move in moves:
            score = move.get('mlBalanceScore') or move.get('balanceScore')
            if score is not None:
                scores.append(float(score))
                move_names.append(move.get('name', 'Unknown'))
                elements.append(move.get('element', 'unknown'))
                levels.append(move.get('level', 1))
                action_types.append(move.get('actionType', 'Action'))
        
        if not scores:
            return jsonify({'error': 'No balance scores found in moves'}), 400
        
        import numpy as np
        scores_array = np.array(scores)
        
        # Calculate statistics
        statistics = {
            'mean': float(np.mean(scores_array)),
            'median': float(np.median(scores_array)),
            'std': float(np.std(scores_array)),
            'min': float(np.min(scores_array)),
            'max': float(np.max(scores_array)),
            'q25': float(np.percentile(scores_array, 25)),
            'q75': float(np.percentile(scores_array, 75)),
            'total': len(scores),
            'severely_underpowered': int(np.sum(scores_array <= 3.5)),
            'underpowered': int(np.sum((scores_array > 3.5) & (scores_array <= 4.5))),
            'slightly_below': int(np.sum((scores_array > 4.5) & (scores_array <= 5.5))),
            'balanced': int(np.sum((scores_array > 5.5) & (scores_array <= 7.0))),
            'slightly_above': int(np.sum((scores_array > 7.0) & (scores_array <= 8.0))),
            'overpowered': int(np.sum((scores_array > 8.0) & (scores_array <= 9.0))),
            'severely_overpowered': int(np.sum(scores_array > 9.0))
        }
        
        # Histogram data
        hist_counts, hist_edges = np.histogram(scores_array, bins=20, range=(0, 10))
        histogram = {
            'counts': hist_counts.tolist(),
            'edges': hist_edges.tolist(),
            'bin_centers': [(hist_edges[i] + hist_edges[i+1]) / 2 for i in range(len(hist_edges)-1)]
        }
        
        # Box plot data by element
        boxplot_by_element = {}
        for element in set(elements):
            element_scores = [scores[i] for i in range(len(scores)) if elements[i] == element]
            if element_scores:
                boxplot_by_element[element] = {
                    'scores': element_scores,
                    'min': float(np.min(element_scores)),
                    'q25': float(np.percentile(element_scores, 25)),
                    'median': float(np.median(element_scores)),
                    'q75': float(np.percentile(element_scores, 75)),
                    'max': float(np.max(element_scores)),
                    'mean': float(np.mean(element_scores))
                }
        
        # Box plot data by level
        boxplot_by_level = {}
        for level in set(levels):
            level_scores = [scores[i] for i in range(len(scores)) if levels[i] == level]
            if level_scores:
                boxplot_by_level[str(level)] = {
                    'scores': level_scores,
                    'min': float(np.min(level_scores)),
                    'q25': float(np.percentile(level_scores, 25)),
                    'median': float(np.median(level_scores)),
                    'q75': float(np.percentile(level_scores, 75)),
                    'max': float(np.max(level_scores)),
                    'mean': float(np.mean(level_scores))
                }
        
        # Scatter plot data
        scatterplot = {
            'scores': scores,
            'names': move_names,
            'elements': elements,
            'levels': levels,
            'action_types': action_types
        }
        
        # Category distribution for pie chart
        categories = {
            'Severely Underpowered': statistics['severely_underpowered'],
            'Underpowered': statistics['underpowered'],
            'Slightly Below Avg': statistics['slightly_below'],
            'Well Balanced': statistics['balanced'],
            'Slightly Above Avg': statistics['slightly_above'],
            'Overpowered': statistics['overpowered'],
            'Severely Overpowered': statistics['severely_overpowered']
        }
        
        return jsonify({
            'histogram': histogram,
            'boxplot_by_element': boxplot_by_element,
            'boxplot_by_level': boxplot_by_level,
            'scatterplot': scatterplot,
            'statistics': statistics,
            'categories': categories
        })
    
    except Exception as e:
        import traceback
        print(f"Visualization error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def calculate_uniqueness_score(move_info):
    """Calculate a uniqueness score for a move based on its properties.
    
    Score ranges from 0-10, with higher scores indicating more unique/creative moves.
    Uses finer granularity (0.1 increments) for more varied scores.
    """
    score = 5.0  # Base score
    
    effects = (move_info.get('effects') or '') + ' ' + (move_info.get('description') or '')
    effects_lower = effects.lower()
    action_type = move_info.get('actionType', 'Action')
    range_text = (move_info.get('range') or '').lower()
    
    # Action type variety (+0 to +1.2)
    if 'danger sense' in action_type.lower():
        score += 1.2  # Very rare action type
    elif 'reaction' in action_type.lower():
        score += 0.9  # Reactions are more unique
    elif 'bonus action' in action_type.lower():
        score += 0.4
    
    # Range creativity (+0 to +1.8)
    if 'cone' in range_text:
        score += 1.7
    elif 'line' in range_text:
        score += 1.5
    elif 'radius' in range_text or 'aoe' in range_text or 'area' in range_text:
        score += 1.2
    elif 'self' in range_text and 'radius' not in range_text:
        score += 0.6
    elif any(num in range_text for num in ['5', '10', '15', '25']):
        score += 0.3  # Non-standard range numbers
    
    # Effect complexity and variety (+0 to +4.5)
    complexity_score = 0
    
    # Special mechanics
    if 'concentration' in effects_lower:
        complexity_score += 1.8
    if 'lingering' in effects_lower or 'persistent' in effects_lower or 'ongoing' in effects_lower:
        complexity_score += 2.2
    if 'charge' in effects_lower or 'stack' in effects_lower:
        complexity_score += 1.5
    
    # Status effects (more varied scoring)
    status_effects = {
        'stunned': 1.5, 'paralyzed': 1.5, 'petrified': 1.8,
        'prone': 0.8, 'dazed': 1.0, 'blinded': 1.2,
        'disadvantage': 0.7, 'advantage': 0.6, 'restrained': 1.1
    }
    for status, value in status_effects.items():
        if status in effects_lower:
            complexity_score += value
            break  # Only count one status effect
    
    # Movement effects
    movement_effects = {
        'pull': 0.7, 'push': 0.6, 'knock': 0.8, 'shove': 0.6,
        'teleport': 1.8, 'swap': 1.6, 'slide': 0.9
    }
    for movement, value in movement_effects.items():
        if movement in effects_lower:
            complexity_score += value
            break
    
    score += min(4.5, complexity_score)
    
    # Utility features (+0 to +2.8)
    utility_score = 0
    
    if any(word in effects_lower for word in ['dash', 'disengage', 'dodge']):
        utility_score += 0.7
    if any(word in effects_lower for word in ['move', 'movement', 'speed']):
        utility_score += 0.4
    if any(word in effects_lower for word in ['wall', 'barrier', 'shield', 'dome']):
        utility_score += 1.7
    if any(word in effects_lower for word in ['terrain', 'environment', 'create', 'shape']):
        utility_score += 1.3
    if any(word in effects_lower for word in ['ally', 'willing', 'friendly']):
        utility_score += 0.8
    if any(word in effects_lower for word in ['support', 'buff', 'enhance']):
        utility_score += 0.9
    if any(word in effects_lower for word in ['heal', 'restore', 'recover']):
        utility_score += 1.1
    
    score += min(2.8, utility_score)
    
    # Damage variety (+0 to +1.5)
    damage_variety = 0
    if 'slashing' in effects_lower:
        damage_variety += 0.6
    if 'piercing' in effects_lower:
        damage_variety += 0.6
    if any(word in effects_lower for word in ['multi', 'multiple', 'several']):
        damage_variety += 0.5
    if any(word in effects_lower for word in ['projectile', 'volley', 'barrage']):
        damage_variety += 0.7
    
    score += min(1.5, damage_variety)
    
    # Resource generation (+0 to +2.0)
    if any(word in effects_lower for word in ['temporary slot', 'bonus slot', 'gain slot']):
        score += 2.0
    elif 'generate' in effects_lower or 'create slot' in effects_lower:
        score += 1.6
    
    # Interaction with other moves (+0 to +1.0)
    if 'combo' in effects_lower or 'synerg' in effects_lower:
        score += 1.0
    elif 'combine' in effects_lower or 'enhance another' in effects_lower:
        score += 0.8
    
    # Cap at 10 and round to 1 decimal place
    score = min(10.0, score)
    
    return round(score, 1)


def parse_move_content(content: str, name: str, level: int, element: str):
    """Parse a move markdown file and extract key information."""
    move_info = {
        'name': name,
        'level': level,
        'element': element,
        'actionType': 'Unknown',
        'range': None,
        'damage': None,
        'effects': None,
        'description': None,
        'duration': None,
        'cost': None
    }
    
    # Extract action type from hashtags
    action_tags = ['#Action', '#Bonus_Action', '#Bonus_action', '#Reaction', '#Danger_Sense_Reaction']
    for tag in action_tags:
        if tag in content:
            if 'Danger_Sense' in tag:
                move_info['actionType'] = 'Danger Sense Reaction'
            elif 'Bonus' in tag:
                move_info['actionType'] = 'Bonus Action'
            elif 'Reaction' in tag:
                move_info['actionType'] = 'Reaction'
            elif 'Action' in tag:
                move_info['actionType'] = 'Action'
            break
    
    # Extract range
    range_match = re.search(r'\*\*Range:?\*\*\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
    if range_match:
        move_info['range'] = range_match.group(1).strip()
    else:
        # Try alternative formats
        range_match = re.search(r'-\s*Range:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if range_match:
            move_info['range'] = range_match.group(1).strip()
        # Check for radius
        radius_match = re.search(r'Radius:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if radius_match:
            move_info['range'] = f"Radius: {radius_match.group(1).strip()}"
    
    # Extract damage
    damage_match = re.search(r'\*\*Damage:?\*\*\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
    if damage_match:
        move_info['damage'] = damage_match.group(1).strip()
    else:
        damage_match = re.search(r'-\s*Damage:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if damage_match:
            move_info['damage'] = damage_match.group(1).strip()
    
    # Extract duration
    duration_match = re.search(r'\*\*Duration:?\*\*\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
    if duration_match:
        move_info['duration'] = duration_match.group(1).strip()
    
    # Extract cost
    cost_match = re.search(r'Cost:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
    if cost_match:
        move_info['cost'] = cost_match.group(1).strip()
    
    # Extract effects section
    effects_match = re.search(r'\*\*Effect[s]?:?\*\*\s*(.+?)(?:\n\n|$)', content, re.IGNORECASE | re.DOTALL)
    if effects_match:
        move_info['effects'] = effects_match.group(1).strip()
    else:
        # Try to get bullet points as effects
        effect_lines = []
        for line in content.split('\n'):
            if line.strip().startswith('-') and not any(x in line for x in ['Range:', 'Damage:', 'Duration:', 'Cost:']):
                effect_lines.append(line.strip().lstrip('- ').strip())
        if effect_lines:
            move_info['effects'] = ' '.join(effect_lines)
    
    # If no effects found, use entire content as description
    if not move_info['effects']:
        # Remove hashtags and extract text
        clean_content = re.sub(r'#\w+', '', content)
        clean_content = re.sub(r'\*\*[^*]+\*\*:?', '', clean_content)
        clean_content = ' '.join([line.strip() for line in clean_content.split('\n') if line.strip() and not line.strip().startswith('-')])
        move_info['description'] = clean_content.strip()[:200]  # Limit to 200 chars
    
    return move_info


@bp.route('/api/list_directory', methods=['GET'])
def list_directory():
    """
    List contents of a directory within the campaign workspace.
    
    Query params:
      path (str): Relative path from REPO_ROOT (e.g., "Dms Root/NPCs")
    
    Returns:
      {
        "items": [
          {"name": "...", "type": "file|directory"},
          ...
        ]
      }
    """
    try:
        path_param = request.args.get('path', '')
        
        # Resolve the path
        target_path = REPO_ROOT / path_param
        
        # Security check: ensure the resolved path is within REPO_ROOT
        try:
            target_path = target_path.resolve()
            if not str(target_path).startswith(str(REPO_ROOT)):
                return jsonify({'error': 'Access denied: path outside repository'}), 403
        except Exception:
            return jsonify({'error': 'Invalid path'}), 400
        
        if not target_path.exists():
            return jsonify({'error': f'Path not found: {path_param}'}), 404
        
        if not target_path.is_dir():
            return jsonify({'error': 'Path is not a directory'}), 400
        
        items = []
        for item in sorted(target_path.iterdir()):
            # Skip hidden files and system files
            if item.name.startswith('.'):
                continue
            
            items.append({
                'name': item.name,
                'type': 'directory' if item.is_dir() else 'file'
            })
        
        return jsonify({'items': items, 'path': path_param})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
