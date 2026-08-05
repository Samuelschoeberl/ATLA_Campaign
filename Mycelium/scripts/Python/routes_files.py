"""Generic vault file/directory I/O routes: create/read/write/move/search
files and folders under Player Root, plus the RESTful /api/file alias and
/api/list_directory.

Split out of the old monolithic frontend_api.py. Behavior is unchanged from
before except where explicitly called out:
  - PUT/POST to /player_root/<path> now accepts an optional `expected_version`
    in the request body; when present, the write goes through
    resource_cache.write_with_version_check() and returns 409 on a stale
    version instead of silently overwriting. Omitting it preserves the old
    unconditional-overwrite behavior for callers not yet migrated.
  - stat_overview.md's auto-regeneration-on-read now goes through
    resource_cache.get_stat_overview_cached() instead of an unconditional
    subprocess call on every GET.
  - PNG ICC-stripping is now cached (mtime-keyed) via resource_cache instead
    of re-running Pillow on every repeat GET of the same image.
  - /api/list_directory's path-containment check now uses the same
    resolved-path/.parents check as everywhere else, replacing the naive
    (bypassable) str.startswith() string check.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, quote

from flask import request, jsonify, send_from_directory, send_file, abort

import resource_cache
from frontend_api import bp
from sheet_helpers import (
    REPO_ROOT,
    PLAYER_ROOT_PREFIX,
    get_player_root_base,
    is_safe_repo_path,
    parse_canonical_stats_from_text,
    write_pc_variable_files,
    update_character_sheet,
)


@bp.route("/api/create-md-file", methods=["POST"])
def create_md_file():
    """Create an empty markdown file under the Player Root tree."""
    data = request.get_json() or {}
    folder = (data.get("folderPath") or "").strip()
    filename = (data.get("filename") or "").strip()

    if not filename or not filename.lower().endswith(".md"):
        return jsonify(error="Filename must end with .md"), 400
    if "/" in filename or "\\" in filename or ".." in filename:
        return jsonify(error="Invalid filename"), 400

    if folder.startswith(PLAYER_ROOT_PREFIX):
        rel_folder = folder[len(PLAYER_ROOT_PREFIX):].lstrip("/")
    else:
        rel_folder = folder.lstrip("/")

    player_base = get_player_root_base()
    if player_base == REPO_ROOT:
        rel = rel_folder
        if rel.startswith(PLAYER_ROOT_PREFIX):
            rel = rel[len(PLAYER_ROOT_PREFIX):].lstrip('/')
        target_dir = player_base if not rel else (player_base / rel)
    else:
        target_dir = player_base if not rel_folder else (player_base / rel_folder)

    try:
        target_dir = target_dir.resolve()
    except Exception:
        return jsonify(error="Invalid folder path"), 400

    if not is_safe_repo_path(target_dir):
        return jsonify(error="Folder is outside repository"), 400

    if not target_dir.exists() or not target_dir.is_dir():
        return jsonify(error="Folder does not exist"), 400

    full_path = target_dir / filename
    if full_path.exists():
        return jsonify(error="File already exists"), 400

    try:
        full_path.write_text("", encoding="utf-8")
    except Exception as e:
        return jsonify(error=str(e)), 500

    try:
        if player_base != REPO_ROOT:
            rel_from_player = full_path.relative_to(player_base).as_posix()
        else:
            rel_from_player = full_path.relative_to(REPO_ROOT).as_posix()
            if rel_from_player.startswith(PLAYER_ROOT_PREFIX):
                rel_from_player = rel_from_player[len(PLAYER_ROOT_PREFIX):].lstrip('/')
    except Exception:
        try:
            rel_from_player = full_path.relative_to(REPO_ROOT).as_posix()
        except Exception:
            rel_from_player = full_path.as_posix()

    return jsonify(success=True, path=f"{PLAYER_ROOT_PREFIX}{rel_from_player}")


@bp.route("/api/create-folder", methods=["POST"])
def create_folder():
    """Create a new subfolder under the Player Root tree."""
    data = request.get_json() or {}
    folder = (data.get("folderPath") or "").strip()
    foldername = (data.get("foldername") or "").strip()

    if not foldername:
        return jsonify(error="Folder name is required"), 400
    if "/" in foldername or "\\" in foldername or ".." in foldername:
        return jsonify(error="Invalid folder name"), 400

    if folder.startswith(PLAYER_ROOT_PREFIX):
        rel_folder = folder[len(PLAYER_ROOT_PREFIX):].lstrip("/")
    else:
        rel_folder = folder.lstrip("/")

    player_base = get_player_root_base()
    if player_base == REPO_ROOT:
        rel = rel_folder
        if rel.startswith(PLAYER_ROOT_PREFIX):
            rel = rel[len(PLAYER_ROOT_PREFIX):].lstrip('/')
        target_dir = player_base if not rel else (player_base / rel)
    else:
        target_dir = player_base if not rel_folder else (player_base / rel_folder)

    try:
        target_dir = target_dir.resolve()
    except Exception:
        return jsonify(error="Invalid folder path"), 400

    if not is_safe_repo_path(target_dir):
        return jsonify(error="Folder is outside repository"), 400

    if not target_dir.exists() or not target_dir.is_dir():
        return jsonify(error="Parent folder does not exist"), 400

    new_folder_path = target_dir / foldername
    if new_folder_path.exists():
        return jsonify(error="Folder already exists"), 400

    try:
        new_folder_path.mkdir()
    except Exception as e:
        return jsonify(error=str(e)), 500

    return jsonify(success=True, path=f"{PLAYER_ROOT_PREFIX}{rel_folder}/{foldername}".replace("//", "/"))


@bp.route("/api/find-file/<filename>", methods=["GET"])
def find_file_by_name(filename):
    """Find a file or folder by name in Player Root. Returns the first match."""
    player_root = get_player_root_base()
    if not player_root.exists():
        return jsonify(error="Player Root not found"), 404

    try:
        for path in player_root.rglob(filename):
            if path.is_file():
                rel_path = path.relative_to(player_root).as_posix()
                return jsonify(path=rel_path, found=True, type='file')

        if not filename.endswith('.md'):
            search_name = f"{filename}.md"
            for path in player_root.rglob(search_name):
                if path.is_file():
                    rel_path = path.relative_to(player_root).as_posix()
                    return jsonify(path=rel_path, found=True, type='file')

        folder_name = filename.replace('.md', '') if filename.endswith('.md') else filename
        for path in player_root.rglob(folder_name):
            if path.is_dir():
                rel_path = path.relative_to(player_root).as_posix()
                return jsonify(path=rel_path, found=True, type='folder')

        return jsonify(found=False, message=f"File or folder '{filename}' not found"), 404
    except Exception as e:
        return jsonify(error=str(e)), 500


def _serve_png_stripped(target: Path):
    """Serve a PNG with ICC/metadata stripped, using the mtime-keyed cache."""
    cached = resource_cache.get_cached_stripped_png(target)
    if cached is None:
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
            cached = output.getvalue()
            resource_cache.set_cached_stripped_png(target, target.stat().st_mtime, cached)
        except Exception as e:
            print(f"PNG stripping failed, serving raw: {e}")
            return None
    import io
    response = send_file(io.BytesIO(cached), mimetype='image/png', download_name=target.name, conditional=False)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response


@bp.route("/player_root", defaults={"subpath": ""})
@bp.route("/player_root/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"])
def player_root(subpath):
    """Serve, create, or delete files within the Player Root namespace."""
    if request.method == "OPTIONS":
        response = jsonify(success=True)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, HEAD, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    sp = (subpath or "").strip()
    if sp.startswith(PLAYER_ROOT_PREFIX):
        sp = sp[len(PLAYER_ROOT_PREFIX):].lstrip("/")

    player_base = get_player_root_base()
    target = player_base if not sp else (player_base / sp)

    try:
        target = target.resolve()
    except Exception:
        return jsonify(error="Invalid path"), 400

    if not is_safe_repo_path(target):
        return jsonify(error="Path outside repository"), 400

    if not target.exists():
        if request.method in ("POST", "PUT"):
            parent = target.parent
            try:
                if not parent.exists():
                    parent.mkdir(parents=True, exist_ok=True)
                if not parent.is_dir():
                    return jsonify(error="Folder does not exist"), 400
            except Exception:
                return jsonify(error="Could not create parent folder"), 500
        else:
            return jsonify(error="Not found"), 404

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

    if request.method in ("GET", "HEAD"):
        rel_path = target.relative_to(REPO_ROOT).as_posix()
        if rel_path == 'Player Root/PCs/stat_overview.md' or rel_path.endswith('/stat_overview.md'):
            resource_cache.get_stat_overview_cached(REPO_ROOT)

        if target.is_dir():
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

        file_ext = target.suffix.lower()
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'}
        direct_serve_extensions = image_extensions | {'.html', '.htm'}

        if file_ext in direct_serve_extensions:
            if file_ext == '.png' and request.method == 'GET':
                resp = _serve_png_stripped(target)
                if resp is not None:
                    return resp
                # fall through to normal serving on failure

            try:
                mimetype_map = {
                    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
                    '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml',
                    '.bmp': 'image/bmp', '.ico': 'image/x-icon',
                    '.html': 'text/html', '.htm': 'text/html',
                }
                mimetype = mimetype_map.get(file_ext, 'application/octet-stream')
                response = send_file(
                    str(target), mimetype=mimetype, conditional=True,
                    download_name=target.name, max_age=3600
                )
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
                response.headers['Cache-Control'] = 'public, max-age=3600'
                return response
            except Exception as e:
                return jsonify(error=str(e)), 500

        if request.method == "HEAD":
            response = jsonify(success=True)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response

        try:
            text = target.read_text(encoding="utf-8")
        except Exception as e:
            return jsonify(error=str(e)), 500
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return jsonify(content=text, hash=h, version=resource_cache.compute_version(text))

    if request.method in ("POST", "PUT"):
        data = request.get_json() or {}
        content = data.get("content")
        if content is None:
            return jsonify(error="Missing content"), 400
        expected_version = data.get("expected_version")

        if target.exists() and target.is_dir():
            return jsonify(error="Target is a directory"), 400

        try:
            parent = target.parent
            if not parent.exists() or not parent.is_dir():
                return jsonify(error="Folder does not exist"), 400
            rel_for_events = target.relative_to(REPO_ROOT).as_posix()
            if expected_version is not None:
                try:
                    new_version = resource_cache.write_with_version_check(
                        target, content or "", expected_version=expected_version, publish_path=rel_for_events
                    )
                except resource_cache.VersionConflict as vc:
                    return jsonify(
                        error="Version conflict",
                        current_version=vc.current_version,
                        current_content=vc.current_content,
                    ), 409
            else:
                target.write_text(content or "", encoding="utf-8")
                new_version = resource_cache.compute_version(content or "")
                try:
                    import events as _events
                    _events.publish("file_changed", path=rel_for_events, version=new_version)
                except Exception:
                    pass
        except Exception as e:
            return jsonify(error=str(e)), 500

        # If the saved file is the shared stat_overview, parse it and write back per-PC variable files
        try:
            rel = str(target.relative_to(REPO_ROOT).as_posix())
            if rel == 'Player Root/PCs/stat_overview.md':
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
                    if line.strip().startswith("|"):
                        cols = [c.strip() for c in line.split("|") if c.strip()]
                        if len(cols) >= 2:
                            key = cols[0]
                            val = cols[1]
                            key_norm = key.replace(' ', '_')
                            if key_norm in ('max_hp', 'current_hp', 'evasion', 'general_armor'):
                                key_norm2 = 'general armor' if key_norm == 'general_armor' else key_norm
                                pcs[cur][key_norm2] = val
                warnings = []
                for pcname, stats in pcs.items():
                    ok, err = write_pc_variable_files(pcname, stats)
                    if not ok:
                        warnings.append(f'{pcname}: variable write: {err}')
                    try:
                        ok2, err2 = update_character_sheet(pcname, stats)
                        if not ok2:
                            if err2 and 'no changes' not in err2:
                                warnings.append(f'{pcname}: sheet update: {err2}')
                    except Exception as e:
                        warnings.append(f'{pcname}: sheet update exception: {e}')
                data['_stat_overview_parsed'] = pcs
                if warnings:
                    data['_stat_overview_write_warnings'] = warnings
                resource_cache.mark_stat_overview_dirty()
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
                            resource_cache.mark_stat_overview_dirty()
                    except Exception as e:
                        data.setdefault('_pc_write_warnings', []).append(str(e))
        except Exception:
            pass
        h = hashlib.sha256((content or "").encode("utf-8")).hexdigest()
        resp = {"success": True, "hash": h, "version": new_version}
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
    """Serve generated graph files under Mycelium/scripts/manuals via a stable /graphs/ URL."""
    try:
        base_dir = (REPO_ROOT / 'Mycelium' / 'scripts' / 'manuals').resolve()
    except Exception:
        abort(500)
    try:
        candidate = (base_dir / Path(seg)).resolve()
    except Exception:
        abort(404)
    try:
        if not candidate.is_file() or not candidate.exists():
            abort(404)
        if not str(candidate).startswith(str(base_dir)):
            abort(403)
    except Exception:
        abort(404)
    rel = candidate.relative_to(base_dir)
    return send_from_directory(str(base_dir), str(rel))


@bp.route('/<path:seg>')
def serve_generated_wikigraph(seg):
    """Serve generated wikigraph HTML files from the repository root."""
    raw_seg = unquote(seg)

    try:
        allowed_suffixes = ('_wikigraph_sunburst.html', '_wikigraph_treemap.html', '_wikigraph.html')
        if not any(raw_seg.endswith(suf) for suf in allowed_suffixes):
            abort(404)
        candidate = (REPO_ROOT / raw_seg).resolve()
    except Exception:
        abort(404)

    try:
        repo_resolved = REPO_ROOT.resolve()
        if not candidate.exists() or not candidate.is_file():
            found = None
            try:
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
        if not str(candidate).startswith(str(repo_resolved)):
            abort(403)
    except Exception:
        abort(404)

    rel = candidate.relative_to(repo_resolved)
    return send_from_directory(str(repo_resolved), str(rel))


@bp.route('/ws', methods=['GET'])
def ws_probe():
    """Lightweight HTTP probe for WebSocket path (some clients probe /ws)."""
    return ('', 204)


@bp.route("/player_root/move", methods=["POST"])
def player_root_move():
    """Atomically move a file within Player Root."""
    data = request.get_json() or {}
    src = data.get("src")
    dst = data.get("dst")
    if not src or not dst:
        return jsonify(error="Missing src or dst"), 400

    def norm(p):
        s = str(p or "").strip()
        if s.startswith(PLAYER_ROOT_PREFIX):
            s = s[len(PLAYER_ROOT_PREFIX):].lstrip("/")
        return s

    src_rel = norm(src)
    dst_rel = norm(dst)

    base = REPO_ROOT / "Player Root"
    src_path = (base / src_rel).resolve()
    dst_path = (base / dst_rel).resolve()

    def _debug_info():
        try:
            return {'_debug': '1', 'src_resolved': str(src_path), 'dst_resolved': str(dst_path)}
        except Exception:
            return {'_debug': '1'}

    debug_enabled = bool(os.environ.get('FLASK_DEBUG') or os.environ.get('MYCELIUM_DEBUG'))

    if not is_safe_repo_path(src_path) or not is_safe_repo_path(dst_path):
        resp = {'error': 'Path outside repository'}
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

    try:
        dst_parent = dst_path.parent
        if not dst_parent.exists():
            dst_parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        resp = {'error': f"Could not create destination folder: {e}"}
        if debug_enabled:
            resp.update(_debug_info())
        return jsonify(resp), 500

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

    try:
        import events as _events
        _events.publish("file_changed", path=f"{PLAYER_ROOT_PREFIX}{rel}", version=None)
        _events.publish("file_moved", src=src, dst=f"{PLAYER_ROOT_PREFIX}{rel}")
    except Exception:
        pass

    return jsonify(resp)


@bp.route("/player_root/search", methods=["GET"])
def player_root_search():
    """Search markdown files under Player Root for a substring."""
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
    normalized_q = re.sub(r"\s+", " ", q_lower).strip()
    q_tokens = [t.strip() for t in re.split(r"\s+", normalized_q) if t.strip()]

    for p in base.rglob('*.md'):
        try:
            p_res = p.resolve()
        except Exception:
            continue
        if not is_safe_repo_path(p_res):
            continue

        filename = p_res.name or ""
        filename_lower = filename.lower()
        filename_no_ext = filename_lower.rsplit('.', 1)[0]
        score = 0
        filename_phrase_match = False
        filename_token_matches = []
        path_token_matches = []
        filename_match_ratio = 0.0

        if normalized_q and normalized_q in filename_no_ext:
            score += 5000
            filename_phrase_match = True
            if len(filename_no_ext) > 0:
                filename_match_ratio = len(normalized_q) / len(filename_no_ext)
                ratio_bonus = int(filename_match_ratio * 2000)
                score += ratio_bonus

        for tok in q_tokens:
            if tok and tok in filename_no_ext:
                score += 500
                filename_token_matches.append(tok)
            try:
                rel_candidate = p_res.relative_to(REPO_ROOT).as_posix().lower()
            except Exception:
                rel_candidate = filename_lower
            if tok and tok in rel_candidate:
                score += 50
                path_token_matches.append(tok)

        try:
            text = p_res.read_text(encoding='utf-8')
        except Exception:
            continue
        lines = text.splitlines()
        matches = []
        for i, line in enumerate(lines):
            if q_lower in line.lower():
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                context = lines[start:end]
                matches.append({'line_no': i + 1, 'excerpt': line.strip(), 'context': context})

        if matches or score > 0:
            rel = p_res.relative_to(REPO_ROOT).as_posix()
            display_path = rel if rel.startswith(PLAYER_ROOT_PREFIX) else f"{PLAYER_ROOT_PREFIX}{rel}"
            score += 10 * len(matches)
            path_depth = display_path.count('/')
            depth_penalty = path_depth * 100
            score -= depth_penalty

            entry = {'path': display_path, 'match_count': len(matches), 'matches': matches, 'score': score}
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

    out.sort(key=lambda e: (-(e.get('score', 0)), -e['match_count'], e['path']))
    if len(out) > max_files:
        out = out[:max_files]
    return jsonify(results=out)


@bp.route('/api/file/<path:filepath>', methods=['GET'])
def get_file_content(filepath):
    """RESTful alias for /player_root/<path> for cleaner API semantics."""
    player_base = get_player_root_base()
    target = player_base / filepath

    try:
        target = target.resolve()
    except Exception:
        return jsonify({'error': 'Invalid path'}), 400

    if not is_safe_repo_path(target):
        return jsonify({'error': 'Path outside repository'}), 403

    if not target.exists():
        return jsonify({'error': 'File not found'}), 404
    if target.is_dir():
        return jsonify({'error': 'Path is a directory'}), 400

    file_ext = target.suffix.lower()
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'}

    if file_ext in image_extensions:
        mimetype_map = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
            '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml',
            '.bmp': 'image/bmp', '.ico': 'image/x-icon',
        }
        mimetype = mimetype_map.get(file_ext, 'application/octet-stream')

        if file_ext == '.png' and request.method == 'GET':
            resp = _serve_png_stripped(target)
            if resp is not None:
                return resp

        try:
            response = send_file(
                str(target), mimetype=mimetype, conditional=True,
                download_name=target.name, max_age=3600
            )
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Cache-Control'] = 'public, max-age=3600'
            return response
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    try:
        content = target.read_text(encoding='utf-8')
        h = hashlib.sha256(content.encode('utf-8')).hexdigest()
        return jsonify({
            'content': content, 'hash': h, 'version': resource_cache.compute_version(content),
            'path': filepath, 'name': target.name, 'size': len(content)
        })
    except UnicodeDecodeError:
        return jsonify({'error': 'File is not a text file'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/list_directory', methods=['GET'])
def list_directory():
    """List contents of a directory within the campaign workspace."""
    try:
        path_param = request.args.get('path', '')
        target_path = REPO_ROOT / path_param

        try:
            target_path = target_path.resolve()
            if not is_safe_repo_path(target_path):
                return jsonify({'error': 'Access denied: path outside repository'}), 403
        except Exception:
            return jsonify({'error': 'Invalid path'}), 400

        if not target_path.exists():
            return jsonify({'error': f'Path not found: {path_param}'}), 404
        if not target_path.is_dir():
            return jsonify({'error': 'Path is not a directory'}), 400

        items = []
        for item in sorted(target_path.iterdir()):
            if item.name.startswith('.'):
                continue
            items.append({'name': item.name, 'type': 'directory' if item.is_dir() else 'file'})

        return jsonify({'items': items, 'path': path_param})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
