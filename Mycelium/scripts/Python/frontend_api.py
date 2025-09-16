from flask import Blueprint, request, jsonify, send_from_directory, abort
from pathlib import Path
import hashlib

bp = Blueprint("frontend_api", __name__)

# Repo root (same logic as other scripts in this repo)
REPO_ROOT = Path(__file__).resolve().parents[3]
PLAYER_ROOT_PREFIX = "Player Root/"

@bp.route("/api/create-md-file", methods=["POST"])
def create_md_file():
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
    # directory. Ensure we create files under REPO_ROOT / "Player Root".
    base = REPO_ROOT / "Player Root"
    target_dir = base if not rel_folder else (base / rel_folder)

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
        full_path.write_text("", encoding="utf-8", newline="\n")
    except Exception as e:
        return jsonify(error=str(e)), 500

    # Return the created path in the same "Player Root/..." form the frontend uses
    rel = full_path.relative_to(REPO_ROOT).as_posix()
    return jsonify(success=True, path=f"{PLAYER_ROOT_PREFIX}{rel}")


@bp.route("/player_root", defaults={"subpath": ""})
@bp.route("/player_root/<path:subpath>", methods=["GET", "POST"])
def player_root(subpath):
    # Accept requests for repo root or subpaths. Frontend sends paths without
    # the leading "Player Root/" prefix in most calls; normalize both forms.
    sp = (subpath or "").strip()
    if sp.startswith(PLAYER_ROOT_PREFIX):
        sp = sp[len(PLAYER_ROOT_PREFIX) :].lstrip("/")

    # target base is the Player Root directory inside the repo
    base = REPO_ROOT / "Player Root"
    target = base if not sp else (base / sp)

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
        # For POST, allow creating a new file if parent exists
        if request.method == "POST":
            parent = target.parent
            if not parent.exists() or not parent.is_dir():
                return jsonify(error="Folder does not exist"), 400
            # proceed to create file below
        else:
            return jsonify(error="Not found"), 404

    if request.method == "GET":
        if target.is_dir():
            entries = []
            for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                rel = child.relative_to(REPO_ROOT).as_posix()
                entries.append({
                    "name": child.name,
                    "path": rel,
                    "type": "dir" if child.is_dir() else "file",
                })
            return jsonify(entries=entries)

        # file: return content + hash
        try:
            text = target.read_text(encoding="utf-8")
        except Exception as e:
            return jsonify(error=str(e)), 500
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return jsonify(content=text, hash=h)

    # POST: save/update file content
    if request.method == "POST":
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
            target.write_text(content or "", encoding="utf-8", newline="\n")
        except Exception as e:
            return jsonify(error=str(e)), 500
        h = hashlib.sha256((content or "").encode("utf-8")).hexdigest()
        return jsonify(success=True, hash=h)


@bp.route("/vault/<path:seg>")
def vault(seg):
    # seg may include "Player Root/..."; make it safe relative to REPO_ROOT
    p = Path(seg)
    # normalize and prevent traversal by resolving and ensuring inside repo
    try:
        candidate = (REPO_ROOT / p).resolve()
    except Exception:
        abort(400)
    try:
        repo_resolved = REPO_ROOT.resolve()
        if repo_resolved not in candidate.parents and candidate != repo_resolved:
            abort(403)
    except Exception:
        abort(400)
    # send the file relative to REPO_ROOT
    rel = candidate.relative_to(REPO_ROOT)
    return send_from_directory(str(REPO_ROOT), str(rel))


@bp.route("/update_sheet/<pcname>", methods=["POST"])
def update_sheet(pcname):
    data = request.get_json() or {}
    content = data.get("content")

    # locate the PC directory under Player Root/PCs/<pcname>
    pc_dir = REPO_ROOT / "Player Root" / "PCs" / pcname
    try:
        pc_dir = pc_dir.resolve()
    except Exception:
        return jsonify(error="Invalid PC path"), 400

    if not pc_dir.exists() or not pc_dir.is_dir():
        return jsonify(error="PC folder not found"), 404

    def _find_sheet_file(pc_dir, pcname):
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
        target.write_text(content or "", encoding="utf-8", newline="\n")
    except Exception as e:
        return jsonify(error=str(e)), 500

    # after save, return whole folder snapshot so caller can sync
    files = _snapshot_folder(pc_dir)
    relpath = str(target.relative_to(REPO_ROOT).as_posix())
    return jsonify(success=True, path=relpath, files=files)