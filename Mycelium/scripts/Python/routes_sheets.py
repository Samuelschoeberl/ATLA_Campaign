"""Character-sheet domain routes: update_sheet, customization, stat overview,
environmental variables, ready-state clearing, and the new hot-spot PATCH
endpoint for vitals/ready/conditions backed by the SQLite pc_vitals table.

Split out of the old monolithic frontend_api.py. The old nested-route bug
(`player_root_wikigraphs` defined *inside* `update_sheet()`'s function body,
re-registering a deferred Flask route on every single POST) is fixed here by
simply not re-declaring that redundant route at all — see
`outdated/backend-dead-code-2026-08/README.md`. `/api/wikigraphs` (in
`routes_generation.py`) already covers the same functionality.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

from flask import request, jsonify

import db
import events
import resource_cache
from frontend_api import bp
from sheet_helpers import (
    REPO_ROOT,
    get_player_root_base,
    default_avatar_matrix,
    load_all_customizations,
    load_character_customization,
    save_character_customization,
    _is_valid_hex_color,
    parse_canonical_stats_from_text,
    write_pc_variable_files,
    find_sheet_file,
    parse_vitals_and_conditions,
    apply_vitals_updates_to_text,
    parse_stat_overview_content,
)


def _snapshot_folder(pc_dir: Path):
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


@bp.route("/update_sheet/<pcname>", methods=["POST"])
def update_sheet(pcname):
    """Write a character sheet and optionally propagate derived variables."""
    data = request.get_json() or {}
    content = data.get("content")
    propagate = bool(data.get("propagate", False))

    pc_dir = REPO_ROOT / "Player Root" / "PCs" / pcname
    try:
        pc_dir = pc_dir.resolve()
    except Exception:
        return jsonify(error="Invalid PC path"), 400

    if not pc_dir.exists() or not pc_dir.is_dir():
        return jsonify(error="PC folder not found"), 404

    target = find_sheet_file(pc_dir, pcname)
    if content is None:
        if not target:
            return jsonify(error="No character sheet file found for PC"), 404
        files = _snapshot_folder(pc_dir)
        return jsonify(success=True, files=files)

    if not target:
        return jsonify(error="No character sheet file found for PC"), 404

    try:
        target.write_text(content or "", encoding="utf-8")
        events.publish("file_changed", path=str(target.relative_to(REPO_ROOT).as_posix()), version=resource_cache.compute_version(content or ""))
    except Exception as e:
        return jsonify(error=str(e)), 500

    # Keep the SQLite pc_vitals row in sync with whatever this bulk save
    # just wrote, so a later PATCH /api/sheets/<pc>/fields sees fresh data.
    try:
        parsed = parse_vitals_and_conditions(content or "")
        db.upsert_pc_vitals_from_vault(
            pcname, parsed['current_hp'], parsed['max_hp'], parsed['ready'], parsed['conditions'],
            str(target.relative_to(REPO_ROOT).as_posix()),
        )
    except Exception:
        pass

    try:
        stats = parse_canonical_stats_from_text(content or "")
        if stats:
            ok, err = write_pc_variable_files(pcname, stats)
            write_warning = None if ok else f'writing pc variable files failed: {err}'
        else:
            write_warning = None
    except Exception as e:
        write_warning = f'failed to parse/write pc variables: {e}'

    resource_cache.mark_stat_overview_dirty()

    if propagate:
        try:
            import sys as _sys
            repo_str = str(REPO_ROOT)
            if repo_str not in _sys.path:
                _sys.path.insert(0, repo_str)

            import importlib as _im
            wr = None
            for modname in ("Mycelium.scripts.Python.watch_and_regen", "Mycelium.scripts.python.watch_and_regen"):
                try:
                    wr = _im.import_module(modname)
                    break
                except Exception:
                    wr = None
            if wr is None:
                import importlib.util as _il
                base = Path(__file__).resolve().parent
                alt = base.joinpath('watch_and_regen.py')
                spec = _il.spec_from_file_location('watch_and_regen', str(alt))
                if spec is None or spec.loader is None:
                    raise ImportError('could not load watch_and_regen module')
                wr = _il.module_from_spec(spec)
                spec.loader.exec_module(wr)  # type: ignore
            from types import SimpleNamespace
            a = SimpleNamespace(dry_run=False, create_placeholders=False)
            variable_root = REPO_ROOT.joinpath('Player Root', 'variable')
            env_sub = variable_root.joinpath('environmental')
            vars_root = env_sub if env_sub.exists() and env_sub.is_dir() else variable_root
            pcs_dir = REPO_ROOT.joinpath('Player Root', 'PCs')
            script = REPO_ROOT.joinpath('Mycelium', 'scripts', 'Python', 'recreate_pcs.py')

            try:
                wr.propagate_environmental_from_sheet(target, vars_root, pcs_dir, script, a)
            except Exception as e:
                files = _snapshot_folder(pc_dir)
                relpath = str(target.relative_to(REPO_ROOT).as_posix())
                return jsonify(success=True, path=relpath, files=files, warning=f'propagation failed: {e}')

            ok, err = resource_cache.get_stat_overview_cached(REPO_ROOT)
            files = _snapshot_folder(pc_dir)
            relpath = str(target.relative_to(REPO_ROOT).as_posix())
            if not ok:
                msg = f'propagation succeeded but generate_stat_overview failed: {err}'
                if write_warning:
                    msg += f'; {write_warning}'
                return jsonify(success=True, path=relpath, files=files, warning=msg)
        except Exception as e:
            files = _snapshot_folder(pc_dir)
            relpath = str(target.relative_to(REPO_ROOT).as_posix())
            return jsonify(success=True, path=relpath, files=files, warning=f'propagation unavailable: {e}')

    files = _snapshot_folder(pc_dir)
    relpath = str(target.relative_to(REPO_ROOT).as_posix())
    if write_warning:
        return jsonify(success=True, path=relpath, files=files, warning=write_warning)
    return jsonify(success=True, path=relpath, files=files)


@bp.route('/api/sheets/<pcname>/fields', methods=['PATCH'])
def patch_sheet_fields(pcname):
    """Hot-spot endpoint: update just currentHp/maxHp/ready/conditions.

    This is what actually fixes "two tabs on the same character clobber each
    other" for the fields that matter most during a live session, instead of
    requiring a full-document versioned PUT for every HP tick. Backed by the
    SQLite pc_vitals table for a real transaction instead of a hand-rolled
    file lock; the backing .md sheet is updated immediately afterward
    (write-through) so Obsidian never goes stale.

    Body: { expected_version?: int, fields: { currentHp?, maxHp?, ready?, conditions? } }
    """
    data = request.get_json() or {}
    fields = data.get('fields') or {}
    expected_version = data.get('expected_version')

    allowed = {}
    if 'currentHp' in fields:
        allowed['currentHp'] = fields['currentHp']
    if 'maxHp' in fields:
        allowed['maxHp'] = fields['maxHp']
    if 'ready' in fields:
        allowed['ready'] = bool(fields['ready'])
    if 'conditions' in fields:
        allowed['conditions'] = fields['conditions']
    if not allowed:
        return jsonify(error='No recognized fields provided'), 400

    try:
        new_row = db.update_pc_vitals_fields(pcname, expected_version, allowed)
    except db.VersionConflict as vc:
        return jsonify(error='Version conflict', current=vc.current), 409
    except Exception as e:
        return jsonify(error=str(e)), 500

    # Write-through to the backing .md sheet.
    source_file = new_row.get('sourceFile')
    if not source_file:
        pc_dir = REPO_ROOT / 'Player Root' / 'PCs' / pcname
        sheet = find_sheet_file(pc_dir, pcname) if pc_dir.exists() else None
        source_file = str(sheet.relative_to(REPO_ROOT).as_posix()) if sheet else None

    if source_file:
        sheet_path = REPO_ROOT / source_file
        try:
            current_text, _ = resource_cache.read_with_version(sheet_path)
            if current_text is not None:
                new_text = apply_vitals_updates_to_text(
                    current_text,
                    current_hp=allowed.get('currentHp'),
                    max_hp=allowed.get('maxHp'),
                    ready=allowed.get('ready'),
                    conditions=allowed.get('conditions'),
                )
                if new_text != current_text:
                    resource_cache.write_with_version_check(sheet_path, new_text, expected_version=None, publish_path=source_file)
        except Exception as e:
            # Non-fatal: the DB write (the authoritative part) already succeeded.
            new_row['mirrorWarning'] = str(e)

    if 'currentHp' in allowed or 'maxHp' in allowed:
        resource_cache.mark_stat_overview_dirty()

    return jsonify(success=True, vitals=new_row)


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
                'name': name, 'folderColor': None, 'avatar': default_avatar_matrix(),
                'avatarPng': None, 'updated_at': None
            }
        return jsonify(data)

    body = request.get_json() or {}
    folder_color = body.get('folderColor') or body.get('folder_color')
    avatar = body.get('avatar')
    avatar_png = body.get('avatarPng')

    if folder_color and not _is_valid_hex_color(folder_color):
        return jsonify({'error': 'folderColor must be a hex string like #aabbcc'}), 400

    try:
        payload = save_character_customization(name, folder_color, avatar or default_avatar_matrix(), avatar_png)
        return jsonify({'success': True, 'customization': payload})
    except Exception as e:
        return jsonify({'error': f'Failed to save customization: {e}'}), 500


@bp.route('/api/file-colors', methods=['GET'])
def get_file_colors():
    """Return color mapping for files/folders based on element tags + folder overrides."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from file_colors import compute_file_colors
    except Exception as e:
        return jsonify({'error': f'Failed to import file_colors module: {e}'}), 500

    base = get_player_root_base()
    try:
        colors = compute_file_colors(base, exts=['.md'], excludes=['.git', '__pycache__', 'node_modules'])
        custom_folder_colors = {}
        try:
            customizations = load_all_customizations()
            for cname, cdata in customizations.items():
                col = cdata.get('folderColor')
                if col:
                    colors[f"PCs/{cname}/"] = col
                    custom_folder_colors[cname] = col
        except Exception:
            pass
        return jsonify({'colors': colors, 'custom_folder_colors': custom_folder_colors})
    except Exception as e:
        return jsonify({'error': f'Failed to compute colors: {e}'}), 500


@bp.route('/api/stat_overview', methods=['GET'])
def get_stat_overview():
    """Return parsed stat overview data in JSON format (cached/debounced regen)."""
    ok, err = resource_cache.get_stat_overview_cached(REPO_ROOT)
    if not ok:
        return jsonify({'error': 'Failed to generate stat overview', 'stderr': err}), 500

    stat_file = REPO_ROOT / 'Player Root' / 'PCs' / 'stat_overview.md'
    if not stat_file.exists():
        return jsonify({'error': 'Stat overview file not found after generation'}), 404

    content = stat_file.read_text(encoding='utf-8')
    parsed = parse_stat_overview_content(content)
    parsed['last_generated'] = stat_file.stat().st_mtime
    parsed['file_path'] = str(stat_file.relative_to(REPO_ROOT))
    return jsonify(parsed)


@bp.route('/api/stat_overview/regenerate', methods=['POST'])
def regenerate_stat_overview():
    """Explicitly force-regenerate the stat overview file."""
    resource_cache.mark_stat_overview_dirty()
    ok, err = resource_cache.get_stat_overview_cached(REPO_ROOT)
    if not ok:
        return jsonify({'error': 'Failed to regenerate stat overview', 'stderr': err}), 500
    return jsonify({'success': True, 'message': 'Stat overview regenerated successfully'})


@bp.route('/api/environmental_variable', methods=['POST'])
def update_environmental_variable():
    """Update an environmental variable (like environmental_water_charge)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        name = data.get('name', '')
        current = data.get('current', 0)
        max_value = data.get('max', 0)

        if not name:
            return jsonify({'error': 'Missing "name" field'}), 400

        env_var_path = get_player_root_base() / 'variable' / 'environmental' / f'{name}.md'
        if not env_var_path.exists():
            return jsonify({'error': f'Environmental variable file not found: {env_var_path}'}), 404

        content = env_var_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        new_lines = [f'{current}/{max_value}']

        found_tags = False
        for line in lines:
            stripped = line.strip()
            if not found_tags and not stripped.startswith('#') and stripped:
                continue
            if not stripped or stripped.startswith('#'):
                new_lines.append(line)
                if stripped.startswith('#'):
                    found_tags = True

        new_text = '\n'.join(new_lines)
        resource_cache.write_with_version_check(
            env_var_path, new_text, expected_version=None,
            publish_path=str(env_var_path.relative_to(REPO_ROOT).as_posix()),
        )

        return jsonify({'success': True, 'message': f'Updated {name}', 'value': f'{current}/{max_value}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/environmental_variable/<variable_name>', methods=['GET'])
def get_environmental_variable(variable_name):
    """Get an environmental variable value: { name, current, max }."""
    try:
        env_var_path = get_player_root_base() / 'variable' / 'environmental' / f'{variable_name}.md'
        if not env_var_path.exists():
            return jsonify({'error': f'Environmental variable file not found: {variable_name}'}), 404

        content = env_var_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        value_line = ''
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                value_line = stripped
                break

        current = 0
        max_value = 0
        if value_line:
            slash_match = re.match(r'^(\d+)\s*\/\s*(\d+)$', value_line)
            if slash_match:
                current = int(slash_match.group(1))
                max_value = int(slash_match.group(2))
            else:
                try:
                    num = int(value_line)
                    current = num
                    max_value = num
                except ValueError:
                    pass

        return jsonify({'name': variable_name, 'current': current, 'max': max_value})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/clear_ready/<character_name>', methods=['POST'])
def clear_ready_state(character_name):
    """Clear the ready state for a character by setting it to 'no' in their character sheet."""
    try:
        player_root = get_player_root_base()
        pc_file = player_root / 'PCs' / character_name / f'{character_name} character sheet.md'
        if not pc_file.exists():
            return jsonify({'error': f'Character sheet not found for {character_name}'}), 404

        content = pc_file.read_text(encoding='utf-8')
        lines = content.split('\n')

        in_vitals = False
        ready_found = False
        for i, line in enumerate(lines):
            if '## Vitals' in line:
                in_vitals = True
                continue
            elif line.startswith('## ') and in_vitals:
                break
            if in_vitals and '| ready' in line.lower():
                parts = line.split('|')
                if len(parts) >= 3:
                    parts[2] = '                    no '
                    lines[i] = '|'.join(parts)
                    ready_found = True
                break

        if not ready_found:
            for i, line in enumerate(lines):
                if '## Vitals' in line:
                    in_vitals = True
                    continue
                elif in_vitals and line.startswith('## '):
                    lines.insert(i, '| ready             |                    no |')
                    break

        new_content = '\n'.join(lines)
        resource_cache.write_with_version_check(
            pc_file, new_content, expected_version=None,
            publish_path=str(pc_file.relative_to(REPO_ROOT).as_posix()),
        )
        try:
            db.update_pc_vitals_fields(character_name, None, {'ready': False})
        except Exception:
            pass

        return jsonify({'success': True, 'character': character_name})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
