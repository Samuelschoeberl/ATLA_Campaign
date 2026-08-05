"""Hot-spot PATCH endpoint for battlemap token position/HP/conditions,
backed by the SQLite battlemap_tokens table. Token drags/HP ticks used to
require re-sending the *entire* map JSON (hexGrid + full tokens array +
background + size) on every change with only a client-generated timestamp
for conflict detection (clock-skew hazard) -- see the rework plan's
discovery notes. This endpoint patches one token under a real DB
transaction and mirrors just that token's fields back into the map's JSON
file; grid/background/size edits stay on the existing full-document
versioned PUT (`/player_root/<path>`), since those are rarer, deliberate GM
actions.
"""
from __future__ import annotations

import json

from flask import request, jsonify

import db
import resource_cache
from frontend_api import bp
from sheet_helpers import REPO_ROOT, get_player_root_base


def _resolve_map_path(map_file: str):
    """Map a client-supplied map_file (repo-relative or Player-Root-relative)
    to an absolute Path, matching whichever form rebuild_database.py stored."""
    candidate = REPO_ROOT / map_file
    if candidate.exists():
        return candidate
    candidate2 = get_player_root_base() / map_file
    if candidate2.exists():
        return candidate2
    return candidate


@bp.route('/api/battlemap/<path:map_file>/tokens/<token_id>', methods=['PATCH'])
def patch_battlemap_token(map_file, token_id):
    """Patch one token's position/hp/conditions.

    Body: { expected_version?: int, changes: { position?: {row, col}, hp?, maxHp?, conditions? } }
    """
    data = request.get_json() or {}
    changes = data.get('changes') or {}
    expected_version = data.get('expected_version')
    if not changes:
        return jsonify(error='No changes provided'), 400

    try:
        new_row = db.update_battlemap_token_fields(map_file, token_id, expected_version, changes)
    except db.VersionConflict as vc:
        return jsonify(error='Version conflict', current=vc.current), 409
    except Exception as e:
        return jsonify(error=str(e)), 500

    # Write-through: patch just this token's fields inside the map's JSON file.
    map_path = _resolve_map_path(map_file)
    try:
        if map_path.exists():
            content, _ = resource_cache.read_with_version(map_path)
            map_data = json.loads(content) if content else {}
            tokens = map_data.get('tokens') or []
            for tok in tokens:
                if tok.get('id') == token_id:
                    if new_row.get('row') is not None:
                        tok['row'] = new_row['row']
                    if new_row.get('col') is not None:
                        tok['col'] = new_row['col']
                    if new_row.get('currentHp') is not None:
                        tok['currentHp'] = new_row['currentHp']
                    if new_row.get('maxHp') is not None:
                        tok['maxHp'] = new_row['maxHp']
                    tok['conditions'] = new_row.get('conditions', tok.get('conditions', []))
                    break
            map_data['tokens'] = tokens
            # Preserve the file's existing indent=2 pretty-printing. These
            # files embed a full 100x100 RGBA avatar array per token, so
            # dumping compact/minified here would rewrite the *entire*
            # multi-hundred-thousand-line file as one line on every single
            # token-position/HP patch -- a diff explosion for a one-field
            # change. json.dumps(..., indent=2) doesn't byte-for-byte match
            # JS's JSON.stringify(data, null, 2), but keeps the same
            # structure/line-per-value shape so only genuinely changed
            # tokens produce a meaningfully-sized diff.
            # ensure_ascii=False: without it json.dumps mangles every emoji/
            # unicode character elsewhere in the file (token icons, accented
            # names) into \uXXXX escapes on every single-token patch, even
            # though this write only intended to change one field.
            new_text = json.dumps(map_data, indent=2, ensure_ascii=False)
            try:
                rel_publish = str(map_path.relative_to(REPO_ROOT).as_posix())
            except Exception:
                rel_publish = map_file
            resource_cache.write_with_version_check(map_path, new_text, expected_version=None, publish_path=rel_publish)
    except Exception as e:
        new_row['mirrorWarning'] = str(e)

    return jsonify(success=True, token=new_row)


@bp.route('/api/battlemap/<path:map_file>/tokens', methods=['GET'])
def get_battlemap_tokens(map_file):
    """Return the current DB-backed token list for a map file."""
    tokens = db.get_battlemap_tokens_for_map(map_file)
    return jsonify(tokens=tokens)
