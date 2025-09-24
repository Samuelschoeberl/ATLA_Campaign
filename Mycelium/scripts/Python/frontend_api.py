from flask import Blueprint, request, jsonify, send_from_directory, abort
from pathlib import Path
import hashlib
import re

bp = Blueprint("frontend_api", __name__)

# Repo root (same logic as other scripts in this repo)
REPO_ROOT = Path(__file__).resolve().parents[3]
PLAYER_ROOT_PREFIX = "Player Root/"


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

    # Also write/overwrite a canonical combined file named <pcname>_variables.md
    try:
        pc_dir = REPO_ROOT.joinpath('Player Root', 'PCs', pcname)
        if pc_dir.exists() and pc_dir.is_dir():
            combined = pc_dir.joinpath(f"{pcname}_variables.md")
            lines = []
            lines.append("| Variable                   |        Value |")
            lines.append("| -------------------------- | -----------: |")
            for k, v in stats.items():
                key_variant = k.replace(' ', '_')
                lines.append(f"| {key_variant} | {str(v).rjust(11)} |")
            combined.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    except Exception:
        pass

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
        full_path.write_text("", encoding="utf-8")
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
                target.write_text(content or "", encoding="utf-8")
            except Exception as e:
                return jsonify(error=str(e)), 500

            # If the saved file is the shared stat_overview, parse it and write per-PC variable files
            try:
                rel = str(target.relative_to(REPO_ROOT).as_posix())
                if rel == 'Player Root/PCs/stat_overview.md':
                    # parse the overview and write back per-PC variable files
                    def parse_overview_and_write(text):
                        pcs = {}
                        cur = None
                        for line in text.splitlines():
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
                        # write per-pc files
                        warnings = []
                        for pcname, stats in pcs.items():
                            ok, err = write_pc_variable_files(pcname, stats)
                            if not ok:
                                warnings.append(f'{pcname}: {err}')
                        return warnings

                    warnings = parse_overview_and_write(content)
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
            try:
                from Mycelium.scripts.python import watch_and_regen as wr
            except Exception:
                try:
                    from Mycelium.scripts.Python import watch_and_regen as wr
                except Exception:
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
    return jsonify(success=True, path=relpath, files=files)