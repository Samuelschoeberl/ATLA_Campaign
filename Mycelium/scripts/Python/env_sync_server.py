#!/usr/bin/env python3
"""Simple HTTP server to share environmental variables and character sheets.

This server exposes a tiny JSON API (no auth) used for simple client sync:

- GET /env_vars             -> JSON mapping stem -> {"value": str, "path": relpath}
- GET /sheet/<pc>          -> raw text content of the PC's character sheet
- POST /update_sheet/<pc>  -> JSON {"content": "...", "propagate": true}

When a sheet is updated via POST the server will write the sheet file (with a
backup) and call the existing propagate logic from `watch_and_regen.py` so
canonical variable files and other character sheets are updated in the same
way the watcher does.

This implementation intentionally uses only the Python standard library so it
has no extra runtime deps and can be run alongside the existing tooling.
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import unquote
import os
import base64
import hashlib
import subprocess

# reuse existing watcher logic
import importlib.util
import sys
import re

# Ensure the repository root is on sys.path so `import Mycelium...` works when
# this file is executed as a script.
try:
    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
except Exception:
    pass


# load watch_and_regen from the package if possible; try both casings
try:
    from Mycelium.scripts.python import watch_and_regen as wr
except Exception:
    try:
        from Mycelium.scripts.Python import watch_and_regen as wr
    except Exception:
        # final fallback: load by file path
        import importlib.util, sys
        base = Path(__file__).resolve().parent
        alt = base.joinpath('watch_and_regen.py')
        spec = importlib.util.spec_from_file_location('watch_and_regen', str(alt))
        if spec is None or spec.loader is None:
            raise ImportError('could not load watch_and_regen module')
        wr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(wr)  # type: ignore
LOCK = threading.Lock()
# Simple SSE broadcaster: background thread writes messages to connected clients
_sse_clients = set()
_sse_lock = threading.Lock()

# Simple WebSocket broadcaster (minimal RFC6455 support)
_ws_clients = set()
_ws_lock = threading.Lock()
WS_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


def _ws_frame(text: str) -> bytes:
    # encode a single unmasked text frame from server to client
    payload = text.encode('utf-8')
    plen = len(payload)
    header = bytearray()
    header.append(0x81)  # FIN + text
    if plen <= 125:
        header.append(plen)
    elif plen <= 65535:
        header.append(126)
        header.extend(plen.to_bytes(2, 'big'))
    else:
        header.append(127)
        header.extend(plen.to_bytes(8, 'big'))
    return bytes(header) + payload


def _ws_broadcast_text(msg: str) -> None:
    with _ws_lock:
        dead = []
        for sock in list(_ws_clients):
            try:
                sock.sendall(_ws_frame(msg))
            except Exception:
                dead.append(sock)
        for d in dead:
            _ws_clients.discard(d)


def _ws_broadcast_json(obj) -> None:
    try:
        _ws_broadcast_text(json.dumps(obj))
    except Exception:
        pass


def _ws_send_to(sock, obj) -> None:
    try:
        sock.sendall(_ws_frame(json.dumps(obj)))
    except Exception:
        with _ws_lock:
            _ws_clients.discard(sock)


def _ws_ping_broadcaster(interval: float = 15.0):
    def run():
        while True:
            try:
                with _ws_lock:
                    clients = list(_ws_clients)
                payload = json.dumps({'cmd': 'server_ping', 'ts': time.time()})
                for s in clients:
                    try:
                        s.sendall(_ws_frame(payload))
                    except Exception:
                        with _ws_lock:
                            _ws_clients.discard(s)
            except Exception:
                pass
            time.sleep(interval)
    t = threading.Thread(target=run, daemon=True)
    t.start()


def _sse_broadcast(event: str, data: str) -> None:
    payload = f"event: {event}\n"
    # data may be multi-line; SSE requires each line to start with 'data:'
    for ln in data.splitlines():
        payload += f"data: {ln}\n"
    payload += "\n"
    with _sse_lock:
        dead = []
        for w in list(_sse_clients):
            try:
                w.write(payload.encode('utf-8'))
                w.flush()
            except Exception:
                dead.append(w)
        for d in dead:
            _sse_clients.discard(d)


def _start_recent_writes_broadcaster(interval: float = 1.0):
    """Background thread: poll wr._recently_written for new writes and broadcast events."""
    def run():
        seen = set()
        while True:
            try:
                cur = set(getattr(wr, '_recently_written', {}).keys())
                new = [p for p in cur if p not in seen]
                if new:
                    files_map = {}
                    for p in new:
                        try:
                            rel = str(p.relative_to(wr.ROOT)) if p.is_absolute() else str(p)
                        except Exception:
                            rel = str(p)
                        try:
                            files_map[rel] = p.read_text(encoding='utf-8')
                        except Exception:
                            files_map[rel] = ''
                    try:
                        # debug log
                        try:
                            print(f"[recent_writes] broadcasting propagated for: {list(files_map.keys())}", flush=True)
                        except Exception:
                            pass
                        # convert updated list to last path-segment names and dedupe
                        last_names = []
                        for p in files_map.keys():
                            try:
                                last = str(Path(p).parts[-1])
                            except Exception:
                                last = str(p)
                            last_names.append(last)
                        seen_l = set(); updated_names = []
                        for n in last_names:
                            if n not in seen_l:
                                seen_l.add(n); updated_names.append(n)
                        _sse_broadcast('propagated', json.dumps({'updated': updated_names, 'files': files_map}))
                        try:
                            _ws_broadcast_json({'event': 'propagated', 'updated': updated_names, 'files': files_map})
                        except Exception:
                            pass
                    except Exception:
                        pass
                    seen.update(new)
                # prune seen set to avoid unbounded growth: keep intersection with cur
                seen = set(x for x in seen if x in cur)
            except Exception:
                pass
            time.sleep(interval)
    t = threading.Thread(target=run, daemon=True)
    t.start()


def _start_variable_folder_watcher(interval: float = 1.0):
    """Background thread: poll the Player Root/variable folder for changes and broadcast updates.

    This ensures clients are notified when variable files are edited outside the normal watcher flow.
    """
    def run():
        last_mtimes = {}
        root = None
        while True:
            try:
                try:
                    root = wr.ROOT.joinpath('Player Root', 'variable')
                except Exception:
                    root = None
                if root and root.exists():
                    cur = {}
                    for p in root.rglob('*.md'):
                        try:
                            stat = p.stat()
                            cur[str(p)] = stat.st_mtime
                        except Exception:
                            continue
                    # detect changed or new files
                    changed = [Path(p) for p, m in cur.items() if p not in last_mtimes or last_mtimes[p] != m]
                    # detect deleted files (treat as change)
                    deleted = [Path(p) for p in last_mtimes.keys() if p not in cur]
                    if changed or deleted:
                        files_map = {}
                        updated = []
                        for p in changed:
                            try:
                                rel = str(p.relative_to(wr.ROOT)) if p.is_absolute() else str(p)
                                files_map[rel] = p.read_text(encoding='utf-8')
                                updated.append(rel)
                            except Exception:
                                continue
                        for p in deleted:
                            try:
                                rel = str(Path(p).relative_to(wr.ROOT))
                                updated.append(rel)
                                files_map[rel] = ''
                            except Exception:
                                continue
                        if updated:
                            payload = {'pc': None, 'updated': updated, 'files': files_map}
                            # debug logs to aid verification
                            try:
                                print(f"[variable_watcher] detected changes: {updated}", flush=True)
                            except Exception:
                                pass
                            try:
                                print(f"[variable_watcher] broadcasting payload with keys: {list(files_map.keys())}", flush=True)
                            except Exception:
                                pass
                            try:
                                _sse_broadcast('propagated', json.dumps(payload))
                            except Exception:
                                pass
                            try:
                                _ws_broadcast_json({'event': 'propagated', **payload})
                            except Exception:
                                pass
                            # no automatic regeneration here; external tooling should invoke recreate_pcs when appropriate
                    last_mtimes = cur
                # else: nothing to do
            except Exception:
                pass
            time.sleep(interval)
    t = threading.Thread(target=run, daemon=True)
    t.start()


def _read_canonical(p: Path) -> Optional[str]:
    try:
        if p.exists():
            txt = p.read_text(encoding='utf-8')
            import re
            m = re.search(r'```markdown\n(.*?)\n\n', txt, flags=re.S)
            if m:
                return m.group(1).strip()
            lines = [l.strip() for l in txt.splitlines() if l.strip() and not l.strip().startswith('#')]
            return lines[0] if lines else ''
    except Exception:
        return None
    return None


class EnvSyncHandler(BaseHTTPRequestHandler):
    server_version = 'EnvSync/0.1'

    def _load_gitignore(self, base: Path):
        """Load simple .gitignore-style patterns from the repo root and base directory.

        This is intentionally lightweight: supports literal filenames and simple
        directory ignores (trailing slash), ignores blank lines and comments.
        """
        patterns = set()
        candidates = [wr.ROOT.joinpath('.gitignore'), base.joinpath('.gitignore')]
        for p in candidates:
            try:
                if p.exists():
                    for ln in p.read_text(encoding='utf-8').splitlines():
                        ln = ln.strip()
                        if not ln or ln.startswith('#'):
                            continue
                        patterns.add(ln)
            except Exception:
                continue
        return patterns

    def _build_tree(self, base: Path):
        """Return a JSON-serializable listing for directory `base`.

        Each directory entry is a dict: {name, path, type: 'file'|'dir'}
        The `path` is relative to wr.ROOT and is safe to use with /Player_Root/<path>.
        """
        # report paths relative to the Player Root so clients can navigate using
        # simple paths like "PCs/..." instead of including the top-level folder.
        player_root = wr.ROOT.joinpath('Player Root').resolve()
        try:
            rel_base = os.path.relpath(str(base.resolve()), str(player_root))
        except Exception:
            # if relpath fails, fall back to repo-relative path
            try:
                rel_base = str(base.relative_to(wr.ROOT))
            except Exception:
                rel_base = str(base)
        out = {'path': rel_base if rel_base not in ('.', './') else '', 'name': base.name, 'type': 'dir', 'entries': []}
        ignore = self._load_gitignore(base)
        try:
            for it in sorted([p for p in base.iterdir()], key=lambda x: x.name.lower()):
                name = it.name
                # skip by gitignore simple patterns
                skip = False
                for pat in ignore:
                    if pat.endswith('/') and it.is_dir() and name == pat[:-1]:
                        skip = True
                        break
                    if pat == name:
                        skip = True
                        break
                if skip:
                    continue
                try:
                    rel = os.path.relpath(str(it.resolve()), str(player_root))
                except Exception:
                    try:
                        rel = str(it.relative_to(wr.ROOT))
                    except Exception:
                        rel = str(it)
                if it.is_dir():
                    out['entries'].append({'name': name, 'path': rel, 'type': 'dir'})
                else:
                    out['entries'].append({'name': name, 'path': rel, 'type': 'file'})
        except Exception:
            pass
        return out

    # token/auth removed: server allows unauthenticated modifications by design

    def _send_json(self, obj, status=200):
        # backward-compatible: allow caller to pass precomputed ETag/header by
        # attaching a special _headers key to the obj (not sent to client) or
        # passing an attribute on the handler in future.
        extra_headers = None
        if isinstance(obj, dict) and '_headers' in obj:
            extra_headers = obj.pop('_headers')
        data = json.dumps(obj, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        # simple CORS for browser clients
        self.send_header('Access-Control-Allow-Origin', '*')
        if extra_headers:
            try:
                for k, v in extra_headers.items():
                    self.send_header(k, v)
            except Exception:
                pass
        self.end_headers()
        self.wfile.write(data)

    def _send_text(self, txt: str, status=200):
        data = txt.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/markdown; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        # allow caller to attach an ETag header by setting self._extra_text_header
        try:
            extra = getattr(self, '_extra_text_header', None)
            if extra and isinstance(extra, dict):
                for k, v in extra.items():
                    self.send_header(k, v)
        except Exception:
            pass
        # clear any one-off header after use
        try:
            if hasattr(self, '_extra_text_header'):
                delattr(self, '_extra_text_header')
        except Exception:
            pass
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = unquote(self.path)
        # allow case-insensitive access to Player_Root (accept /player_root too)
        pl = path.lower()
        # Serve a browsable view of the on-disk "Player Root" directory at /Player_Root
        if pl == '/player_root' or pl == '/player_root/':
            try:
                base = wr.ROOT.joinpath('Player Root')
                tree = self._build_tree(base)
                self._send_json(tree)
            except Exception as e:
                self._send_json({'error': 'failed to list Player Root', 'detail': str(e)}, status=500)
            return

        if pl.startswith('/player_root/'):
            # strip the prefix and any leading slash
            rel = path[len('/player_root/'):].lstrip('/')
            rel = unquote(rel)
            try:
                base = wr.ROOT.joinpath('Player Root')
                target = (base.joinpath(rel)).resolve()
                # ensure target is inside base
                try:
                    if not target.is_relative_to(base.resolve()):
                        raise Exception('path outside player root')
                except AttributeError:
                    # Python <3.9 fallback
                    if str(base.resolve()) not in str(target):
                        raise Exception('path outside player root')

                if target.is_dir():
                    tree = self._build_tree(target)
                    # add URL to each entry for easy navigation
                    for e in tree.get('entries', []):
                        e['url'] = f"/player_root/{e['path']}"
                    self._send_json(tree)
                    return

                if target.is_file():
                    try:
                        txt = target.read_text(encoding='utf-8')
                        # report file path relative to Player Root when possible
                        player_root = wr.ROOT.joinpath('Player Root').resolve()
                        try:
                            file_rel = str(target.relative_to(player_root))
                        except Exception:
                            file_rel = str(target.relative_to(wr.ROOT))
                        # compute sha256 for ETag/hash and include as header + field
                        try:
                            h = hashlib.sha256(txt.encode('utf-8')).hexdigest()
                        except Exception:
                            h = None
                        headers = {}
                        if h:
                            headers['ETag'] = h
                        # include hash in body for clients that prefer JSON field
                        body = {'type': 'file', 'name': target.name, 'path': file_rel, 'content': txt}
                        if h:
                            body['hash'] = h
                        # use special _headers key to pass through _send_json
                        if headers:
                            body['_headers'] = headers
                        self._send_json(body)
                        return
                    except Exception as e:
                        self._send_json({'error': 'failed to read file', 'detail': str(e)}, status=500)
                        return
            except Exception as e:
                self._send_json({'error': 'invalid path', 'detail': str(e)}, status=400)
            return
        # Root landing page: show links and a simple sheet lookup form
        if path == '/' or path == '/index.html':
            # generate a simple list of PCs (link to their sheet) so LAN clients can browse
            pcs_dir = wr.ROOT.joinpath('Player Root', 'PCs')
            entries = []
            try:
                if pcs_dir.exists():
                    for p in sorted([d for d in pcs_dir.iterdir() if d.is_dir()], key=lambda x: x.name.lower()):
                        name = p.name
                        # check if a sheet file exists; only include PCs that have a sheet
                        candidates = [f"{name} character sheet.md", f"{name} Character Sheet.md"]
                        for c in candidates:
                            if p.joinpath(c).exists():
                                entries.append(name)
                                break
            except Exception:
                entries = []

            links_html = ''
            if entries:
                links_html += '<h2>Character sheets</h2><ul>'
                for name in entries:
                    safe = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    links_html += f'<li><a href="/sheet/{safe}">{safe}</a></li>'
                links_html += '</ul>'

            html = (
                '<!doctype html><html><head><meta charset="utf-8"><title>Mycelium Env Sync</title>'
                '<meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="font-family:system-ui,Arial;max-width:900px;margin:24px">'
                '<h1>Mycelium Env Sync</h1>'
                '<p>This server exposes environmental variables and character sheets.</p>'
                '<ul>'
                '<li><a href="/env_vars">/env_vars</a> — JSON list of environment variables</li>'
                '<li>/sheet/&lt;PC&gt; — raw character sheet markdown for PC folder (example: <a href="/sheet/Anju">/sheet/Anju</a>)</li>'
                '</ul>'
                + links_html +
                '<form onsubmit="event.preventDefault(); location.href=\'/sheet/\'+encodeURIComponent(document.getElementById(\'pc\').value);">'
                '<label>PC folder name: <input id="pc" /></label> <button type="submit">Open sheet</button>'
                '</form>'
                '<p><small>Frontend UI: <a href="/">(use the static frontend on port 8000)</a></small></p>'
                '</body></html>'
            )
            data = html.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        # GET /env_vars
        if path == '/env_vars' or path == '/env_vars/':
            vars_root = wr.ROOT.joinpath('Player Root', 'variable')
            out = {}
            for p in vars_root.rglob('*.md') if vars_root.exists() else []:
                try:
                    val = _read_canonical(p) or ''
                except Exception:
                    val = ''
                out[p.stem] = {'value': val, 'path': str(p.relative_to(wr.ROOT))}
            self._send_json(out)
            return

        # GET /pcs -> JSON list of PC folder names that have sheets
        if path == '/pcs' or path == '/pcs/':
            pcs_dir = wr.ROOT.joinpath('Player Root', 'PCs')
            out = []
            try:
                if pcs_dir.exists():
                    for p in sorted([d for d in pcs_dir.iterdir() if d.is_dir()], key=lambda x: x.name.lower()):
                        name = p.name
                        candidates = [f"{name} character sheet.md", f"{name} Character Sheet.md"]
                        for c in candidates:
                            if p.joinpath(c).exists():
                                out.append(name)
                                break
            except Exception:
                out = []
            self._send_json(out)
            return

        # SSE endpoint for client updates
        if path == '/events':
            # establish SSE stream
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            # register the client wfile for broadcasting
            with _sse_lock:
                _sse_clients.add(self.wfile)
            # write an initial comment line to force some data to the client
            try:
                self.wfile.write(b": connected\n\n")
                self.wfile.flush()
            except Exception:
                pass
            # keep the connection open until client disconnects
            try:
                while True:
                    time.sleep(1)
            except Exception:
                with _sse_lock:
                    _sse_clients.discard(self.wfile)
            return

        # WebSocket endpoint (minimal) at /ws
        if path == '/ws':
            # Check upgrade headers
            if self.headers.get('Upgrade', '').lower() != 'websocket':
                self._send_json({'error': 'must upgrade to websocket'}, status=400)
                return
            key = self.headers.get('Sec-WebSocket-Key')
            if not key:
                self._send_json({'error': 'missing Sec-WebSocket-Key'}, status=400)
                return
            accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode('utf-8')).digest()).decode('ascii')
            self.send_response(101)
            self.send_header('Upgrade', 'websocket')
            self.send_header('Connection', 'Upgrade')
            self.send_header('Sec-WebSocket-Accept', accept)
            self.end_headers()
            # register socket
            sock = self.request
            with _ws_lock:
                _ws_clients.add(sock)

            def ws_reader(s, addr):
                try:
                    while True:
                        hdr = s.recv(2)
                        if not hdr or len(hdr) < 2:
                            break
                        b1, b2 = hdr[0], hdr[1]
                        opcode = b1 & 0x0f
                        masked = b2 & 0x80
                        plen = b2 & 0x7f
                        if plen == 126:
                            ext = s.recv(2)
                            plen = int.from_bytes(ext, 'big')
                        elif plen == 127:
                            ext = s.recv(8)
                            plen = int.from_bytes(ext, 'big')
                        mask = b''
                        if masked:
                            mask = s.recv(4)
                        data = b''
                        while len(data) < plen:
                            chunk = s.recv(plen - len(data))
                            if not chunk:
                                break
                            data += chunk
                        if masked and mask:
                            data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
                        if opcode == 0x8:
                            # close frame
                            break
                        if opcode == 0x1:
                            # text frame
                            try:
                                txt = data.decode('utf-8')
                                # expect JSON commands: { cmd: 'echo'|'list_pcs'|'reload'|'ping', ... }
                                try:
                                    obj = json.loads(txt)
                                except Exception:
                                    obj = None
                                if obj and isinstance(obj, dict):
                                    cmd = obj.get('cmd')
                                    if cmd == 'echo':
                                        _ws_send_to(s, {'cmd': 'echo', 'msg': obj.get('msg')})
                                    elif cmd == 'list_pcs':
                                        pcs_dir = wr.ROOT.joinpath('Player Root', 'PCs')
                                        names = []
                                        try:
                                            if pcs_dir.exists():
                                                for d in pcs_dir.iterdir():
                                                    if d.is_dir():
                                                        names.append(d.name)
                                        except Exception:
                                            pass
                                        _ws_send_to(s, {'cmd': 'list_pcs', 'pcs': names})
                                    elif cmd == 'reload' and obj.get('pc'):
                                        # send an artificial propagated event for pc reload
                                        pcname = obj.get('pc')
                                        _ws_send_to(s, {'cmd': 'reloaded', 'pc': pcname})
                                    elif cmd == 'ping':
                                        _ws_send_to(s, {'cmd': 'pong', 'ts': time.time()})
                            except Exception:
                                pass
                except Exception:
                    pass
                finally:
                    with _ws_lock:
                        _ws_clients.discard(s)

            t = threading.Thread(target=ws_reader, args=(sock, self.client_address), daemon=True)
            t.start()
            return

        # GET /sheet/<pc>
        if path.startswith('/sheet/'):
            pc = path[len('/sheet/'):].strip('/')
            pc = unquote(pc)
            pcs_dir = wr.ROOT.joinpath('Player Root', 'PCs')
            pc_dir = pcs_dir.joinpath(pc)
            candidates = [f"{pc} character sheet.md", f"{pc} Character Sheet.md"]
            sheet_path = None
            for c in candidates:
                p = pc_dir.joinpath(c)
                if p.exists():
                    sheet_path = p
                    break
            if sheet_path is None:
                self._send_json({'error': 'sheet not found'}, status=404)
                return
            try:
                txt = sheet_path.read_text(encoding='utf-8')
            except Exception:
                self._send_json({'error': 'failed to read sheet'}, status=500)
                return
            self._send_text(txt)
            return

        self._send_json({'error': 'unknown endpoint'}, status=404)

    def do_POST(self):
        path = unquote(self.path)
    # unauthenticated: all clients allowed to modify server files
        length = int(self.headers.get('content-length', 0))
        body = self.rfile.read(length).decode('utf-8') if length else ''
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {}

        # POST /apply_table_edit -> {pc: <pcName>, tableIndex: int, row: int, col: int, value: str}
        if path == '/apply_table_edit':
            pc = payload.get('pc')
            tableIndex = int(payload.get('tableIndex', 0))
            row = int(payload.get('row', 0))
            col = int(payload.get('col', 0))
            value = payload.get('value')
            if not pc or value is None:
                self._send_json({'error': 'missing parameters'}, status=400)
                return

            # locate sheet path (reuse same candidate logic as update)
            pcs_dir = wr.ROOT.joinpath('Player Root', 'PCs')
            pc_dir = pcs_dir.joinpath(pc)
            candidates = [f"{pc} character sheet.md", f"{pc} Character Sheet.md"]
            sheet_path = None
            for c in candidates:
                p = pc_dir.joinpath(c)
                if p.exists():
                    sheet_path = p
                    break
            if sheet_path is None:
                self._send_json({'error': 'sheet not found'}, status=404)
                return

            with LOCK:
                try:
                    text = sheet_path.read_text(encoding='utf-8')
                except Exception as e:
                    self._send_json({'error': 'failed to read sheet', 'detail': str(e)}, status=500)
                    return

                # find pipe-style table blocks that contain a separator line
                lines = text.split('\n')
                blocks = []  # list of (start,end) line indices inclusive
                i = 0
                while i < len(lines):
                    if '|' in lines[i]:
                        j = i
                        while j < len(lines) and ('|' in lines[j] or lines[j].strip() == ''):
                            j += 1
                        block_lines = lines[i:j]
                        # check if block contains a separator line like | --- | --- |
                        sep_found = False
                        for bl in block_lines:
                            if re.search(r"^\s*\|?\s*:-{1,}|-{3,}\s*\|", bl) or re.search(r"^\s*\|?\s*-{3,}\s*\|", bl):
                                sep_found = True
                                break
                            # alternative: line with '-' and '|' in it
                            if '|' in bl and re.search(r"[-]{3,}", bl):
                                sep_found = True
                                break
                        if sep_found:
                            blocks.append((i, j - 1))
                        i = j
                    else:
                        i += 1

                if tableIndex >= len(blocks):
                    self._send_json({'error': 'table not found', 'tables': len(blocks)}, status=400)
                    return

                s, e = blocks[tableIndex]
                table_lines = lines[s:e+1]
                # parse table into rows of cells
                parsed = []
                for tl in table_lines:
                    # remove leading/trailing | but keep empty cells
                    rowparts = [p.rstrip() for p in re.split(r"\|", tl)[1:-1]] if '|' in tl else []
                    # fallback: split preserving empties
                    if not rowparts and '|' in tl:
                        rowparts = [p.rstrip() for p in tl.strip().strip('|').split('|')]
                    parsed.append([p.strip() for p in rowparts])

                if row >= len(parsed) or col >= len(parsed[row]):
                    self._send_json({'error': 'cell out of range', 'rows': len(parsed), 'cols': [len(r) for r in parsed]}, status=400)
                    return

                parsed[row][col] = str(value)

                # compute column widths
                colWidths = []
                for r in parsed:
                    for ci, cval in enumerate(r):
                        if len(colWidths) <= ci:
                            colWidths.append(0)
                        colWidths[ci] = max(colWidths[ci], len(cval))

                new_table_lines = []
                for r in parsed:
                    new_table_lines.append('| ' + ' | '.join((c + ' ' * (colWidths[i] - len(c))) for i, c in enumerate(r)) + ' |')

                # backup and write
                try:
                    bak = sheet_path.with_suffix('.md.bak')
                    bak.write_text(text, encoding='utf-8')
                    out = lines[:s] + new_table_lines + lines[e+1:]
                    new_text = '\n'.join(out)
                    sheet_path.write_text(new_text, encoding='utf-8')
                    wr._recently_written[sheet_path] = time.time()
                except Exception as e:
                    self._send_json({'error': 'failed to write sheet', 'detail': str(e)}, status=500)
                    return

            self._send_json({'status': 'ok', 'content': new_text})
            return

        # POST /player_root/<path> -> save file edits. Payload: { content: str }
        if path.startswith('/player_root/'):
            rel = path[len('/player_root/'):].lstrip('/')
            rel = unquote(rel)
            base = wr.ROOT.joinpath('Player Root')
            target = (base.joinpath(rel)).resolve()
            try:
                # ensure target is inside base
                try:
                    if not target.is_relative_to(base.resolve()):
                        raise Exception('path outside player root')
                except AttributeError:
                    if str(base.resolve()) not in str(target):
                        raise Exception('path outside player root')
                # only allow writing to existing files (don't create arbitrary new files)
                if not target.exists() or not target.is_file():
                    self._send_json({'error': 'target not found or not a file'}, status=404)
                    return
                content = payload.get('content')
                if content is None:
                    self._send_json({'error': 'missing content'}, status=400)
                    return
                with LOCK:
                    try:
                        bak = target.with_suffix(target.suffix + '.bak')
                        bak.write_text(target.read_text(encoding='utf-8'), encoding='utf-8')
                        target.write_text(content, encoding='utf-8')
                    except Exception as e:
                        self._send_json({'error': 'failed to write file', 'detail': str(e)}, status=500)
                        return
                self._send_json({'status': 'ok'})
                return
            except Exception as e:
                self._send_json({'error': 'invalid path', 'detail': str(e)}, status=400)
                return

        # POST /update_sheet/<pc>
        if path.startswith('/update_sheet/'):
            pc = path[len('/update_sheet/'):].strip('/')
            pc = unquote(pc)
            content = payload.get('content')
            propagate = bool(payload.get('propagate', True))
            if content is None:
                self._send_json({'error': 'missing content'}, status=400)
                return

            pcs_dir = wr.ROOT.joinpath('Player Root', 'PCs')
            pc_dir = pcs_dir.joinpath(pc)
            candidates = [f"{pc} character sheet.md", f"{pc} Character Sheet.md"]
            sheet_path = None
            for c in candidates:
                p = pc_dir.joinpath(c)
                if p.exists() or p.parent.exists():
                    sheet_path = p
                    break

            if sheet_path is None:
                self._send_json({'error': 'pc folder not found'}, status=404)
                return

            # write with a backup while holding a lock to avoid races
            with LOCK:
                try:
                    if sheet_path.exists():
                        bak = sheet_path.with_suffix('.md.bak')
                        bak.write_text(sheet_path.read_text(encoding='utf-8'), encoding='utf-8')
                    sheet_path.parent.mkdir(parents=True, exist_ok=True)
                    sheet_path.write_text(content, encoding='utf-8')
                    # record recent write so watcher won't immediately re-handle
                    wr._recently_written[sheet_path] = time.time()
                except Exception as e:
                    self._send_json({'error': 'failed to write sheet', 'detail': str(e)}, status=500)
                    return

            # reuse propagation logic from watcher to update canonical files and other sheets
            if propagate:
                try:
                    # build minimal args namespace expected by propagate function
                    from types import SimpleNamespace
                    a = SimpleNamespace(dry_run=False, create_placeholders=False)
                    vars_root = wr.ROOT.joinpath('Player Root', 'variable')
                    script = wr.ROOT.joinpath('Mycelium', 'scripts', 'python', 'recreate_pcs.py')
                    # call the helper that handles a single sheet
                    # capture pre-existing recently written snapshot
                    pre = {p: t for p, t in getattr(wr, '_recently_written', {}).items()}
                    wr.propagate_environmental_from_sheet(sheet_path, vars_root, pcs_dir, script, a)
                    # determine newly written paths since pre snapshot
                    post = {p: t for p, t in getattr(wr, '_recently_written', {}).items()}
                    new_paths = [p for p in post.keys() if p not in pre]
                    files_map = {}
                    for p in new_paths:
                        try:
                            rel = str(p.relative_to(wr.ROOT)) if p.is_absolute() else str(p)
                        except Exception:
                            rel = str(p)
                        try:
                            files_map[rel] = p.read_text(encoding='utf-8')
                        except Exception:
                            files_map[rel] = ''
                    if files_map:
                        try:
                            # for readability on clients, reduce 'updated' entries to
                            # the last path segment (folder or filename) and dedupe
                            last_names = []
                            for p in files_map.keys():
                                try:
                                    last = str(Path(p).parts[-1])
                                except Exception:
                                    last = p
                                last_names.append(last)
                            # dedupe while preserving order
                            seen_l = set()
                            updated_names = []
                            for n in last_names:
                                if n not in seen_l:
                                    seen_l.add(n)
                                    updated_names.append(n)
                            payload = {'pc': pc, 'updated': updated_names, 'files': files_map}
                            _sse_broadcast('propagated', json.dumps(payload))
                            try:
                                _ws_broadcast_json({'event': 'propagated', **payload})
                            except Exception:
                                pass
                        except Exception:
                            pass
                except Exception as e:
                    # non-fatal, return success but include warning
                    self._send_json({'status': 'ok', 'warning': f'propagation failed: {e}'})
                    return

            self._send_json({'status': 'ok'})
            return

        self._send_json({'error': 'unknown endpoint'}, status=404)


def main():
    p = argparse.ArgumentParser(description='Run simple env sync HTTP server')
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8000)
    p.add_argument('--bind-all', action='store_true', help='bind to 0.0.0.0')
    args = p.parse_args()
    host = '0.0.0.0' if args.bind_all else args.host
    addr = (host, args.port)
    srv = ThreadingHTTPServer(addr, EnvSyncHandler)
    # start background broadcaster that notifies SSE clients about recent writes
    try:
        _start_recent_writes_broadcaster()
    except Exception:
        pass
    try:
        _ws_ping_broadcaster()
    except Exception:
        pass
    try:
        _start_variable_folder_watcher()
    except Exception:
        pass
    print(f'Env sync server listening on http://{host}:{args.port}')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nshutting down')
        srv.shutdown()


if __name__ == '__main__':
    main()
