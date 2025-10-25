from flask import Flask, send_from_directory, send_file, request, g
from flask_cors import CORS
from pathlib import Path
from html.parser import HTMLParser
import os
import sys
import re
from urllib.parse import unquote
import fnmatch
import logging
from datetime import datetime
import time

# Fix sys.argv[0] to use absolute path before Flask/werkzeug reloader uses it
# This prevents "can't open file" errors when running from subdirectories
if not os.path.isabs(sys.argv[0]):
    sys.argv[0] = str(Path(__file__).resolve())

# Determine repository root and ensure it's on sys.path so package-style
# imports work regardless of how this script is invoked.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Try to import the blueprint from a few sensible locations so running
# the launcher as a script, module, or from a different cwd still works.
bp = None
try:
    # Prefer package-style import when available
    from Mycelium.scripts.Python.frontend_api import bp as _bp
    bp = _bp
except Exception:
    try:
        # Fallback to same-directory import (when running this file directly)
        from frontend_api import bp as _bp2  # file is in same directory
        bp = _bp2
    except Exception:
        # Final attempt: add the scripts/Python dir to sys.path and import
        scripts_python_dir = Path(__file__).resolve().parent
        if str(scripts_python_dir) not in sys.path:
            sys.path.insert(0, str(scripts_python_dir))
        from frontend_api import bp as _bp3
        bp = _bp3

# create app without default static folder to serve our frontend dir explicitly
app = Flask(__name__, static_folder=None)
CORS(app)  # allow requests from the frontend served from file:// or another host
app.register_blueprint(bp)

# Set up client activity logging
LOG_DIR = REPO_ROOT / 'logs'
LOG_DIR.mkdir(exist_ok=True)
CLIENT_LOG_FILE = LOG_DIR / f'client_activity_{datetime.now().strftime("%Y%m%d")}.log'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(CLIENT_LOG_FILE),
        logging.StreamHandler()  # Also log to console
    ]
)
client_logger = logging.getLogger('client_activity')

# Track active sessions
active_sessions = {}

@app.before_request
def log_request_start():
    """Log the start of each request with client details."""
    g.start_time = time.time()
    
    # Get client info
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Track session (simple IP-based for now)
    if client_ip not in active_sessions:
        active_sessions[client_ip] = {
            'first_seen': datetime.now(),
            'user_agent': user_agent,
            'request_count': 0
        }
    
    active_sessions[client_ip]['request_count'] += 1
    active_sessions[client_ip]['last_seen'] = datetime.now()
    
    client_logger.info(
        f"[{client_ip}] {request.method} {request.path} | "
        f"Session: {active_sessions[client_ip]['request_count']} requests"
    )

@app.after_request
def log_request_end(response):
    """Log the completion of each request."""
    if hasattr(g, 'start_time'):
        duration = (time.time() - g.start_time) * 1000  # Convert to ms
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        client_logger.info(
            f"[{client_ip}] {request.method} {request.path} → "
            f"{response.status_code} | {duration:.2f}ms"
        )
    
    return response

@app.route('/api/active_sessions')
def get_active_sessions():
    """Endpoint to view currently active sessions."""
    sessions_info = []
    for ip, data in active_sessions.items():
        sessions_info.append({
            'ip': ip,
            'first_seen': data['first_seen'].isoformat(),
            'last_seen': data['last_seen'].isoformat(),
            'request_count': data['request_count'],
            'user_agent': data['user_agent']
        })
    return {'sessions': sessions_info, 'total': len(sessions_info)}

@app.route('/api/client_log')
def get_client_log():
    """Endpoint to view the client activity log."""
    lines = request.args.get('lines', 100, type=int)
    
    try:
        if CLIENT_LOG_FILE.exists():
            with open(CLIENT_LOG_FILE, 'r') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                return {
                    'log': ''.join(recent_lines),
                    'total_lines': len(all_lines),
                    'showing_lines': len(recent_lines),
                    'log_file': str(CLIENT_LOG_FILE)
                }
        else:
            return {'log': 'No log file found', 'total_lines': 0}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/log_viewer')
def log_viewer_page():
    """Simple HTML page to view logs in real-time."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Client Activity Log</title>
        <style>
            body {
                font-family: 'Courier New', monospace;
                background: #1e1e1e;
                color: #d4d4d4;
                padding: 20px;
                margin: 0;
            }
            h1 {
                color: #4ec9b0;
                margin-bottom: 10px;
            }
            .controls {
                margin-bottom: 20px;
                background: #252526;
                padding: 15px;
                border-radius: 5px;
            }
            button {
                background: #0e639c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 3px;
                cursor: pointer;
                margin-right: 10px;
            }
            button:hover {
                background: #1177bb;
            }
            .stats {
                display: inline-block;
                margin-left: 20px;
                color: #858585;
            }
            #log {
                background: #252526;
                padding: 15px;
                border-radius: 5px;
                white-space: pre-wrap;
                word-wrap: break-word;
                max-height: 70vh;
                overflow-y: auto;
                font-size: 12px;
                line-height: 1.5;
            }
            .ip { color: #4ec9b0; }
            .method { color: #569cd6; }
            .path { color: #ce9178; }
            .status-ok { color: #4fc1ff; }
            .status-error { color: #f48771; }
            .time { color: #b5cea8; }
            #sessions {
                margin-top: 20px;
                background: #252526;
                padding: 15px;
                border-radius: 5px;
            }
            .session {
                padding: 10px;
                margin: 5px 0;
                background: #2d2d30;
                border-radius: 3px;
            }
        </style>
    </head>
    <body>
        <h1>🌐 Client Activity Monitor</h1>
        
        <div class="controls">
            <button onclick="fetchLog()">🔄 Refresh Log</button>
            <button onclick="fetchSessions()">👥 Refresh Sessions</button>
            <button onclick="clearLog()">🗑️ Clear Display</button>
            <button onclick="toggleAutoRefresh()">⏯️ <span id="autoRefreshText">Enable</span> Auto-Refresh</button>
            <span class="stats" id="stats">Loading...</span>
        </div>
        
        <h2>Recent Activity</h2>
        <div id="log">Loading log...</div>
        
        <h2>Active Sessions</h2>
        <div id="sessions">Loading sessions...</div>
        
        <script>
            let autoRefreshInterval = null;
            
            function fetchLog() {
                fetch('/api/client_log?lines=200')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('log').textContent = data.log || 'No activity yet';
                        document.getElementById('stats').textContent = 
                            `Showing ${data.showing_lines} of ${data.total_lines} lines`;
                        
                        // Auto-scroll to bottom
                        const logDiv = document.getElementById('log');
                        logDiv.scrollTop = logDiv.scrollHeight;
                    })
                    .catch(err => {
                        document.getElementById('log').textContent = 'Error loading log: ' + err;
                    });
            }
            
            function fetchSessions() {
                fetch('/api/active_sessions')
                    .then(r => r.json())
                    .then(data => {
                        const sessionsDiv = document.getElementById('sessions');
                        if (data.total === 0) {
                            sessionsDiv.innerHTML = '<p>No active sessions</p>';
                        } else {
                            sessionsDiv.innerHTML = data.sessions.map(s => `
                                <div class="session">
                                    <strong>IP:</strong> ${s.ip}<br>
                                    <strong>First seen:</strong> ${new Date(s.first_seen).toLocaleString()}<br>
                                    <strong>Last seen:</strong> ${new Date(s.last_seen).toLocaleString()}<br>
                                    <strong>Requests:</strong> ${s.request_count}<br>
                                    <strong>User Agent:</strong> ${s.user_agent}
                                </div>
                            `).join('');
                        }
                    })
                    .catch(err => {
                        document.getElementById('sessions').innerHTML = 'Error loading sessions: ' + err;
                    });
            }
            
            function clearLog() {
                document.getElementById('log').textContent = '';
            }
            
            function toggleAutoRefresh() {
                const button = document.getElementById('autoRefreshText');
                if (autoRefreshInterval) {
                    clearInterval(autoRefreshInterval);
                    autoRefreshInterval = null;
                    button.textContent = 'Enable';
                } else {
                    autoRefreshInterval = setInterval(() => {
                        fetchLog();
                        fetchSessions();
                    }, 2000);
                    button.textContent = 'Disable';
                }
            }
            
            // Initial load
            fetchLog();
            fetchSessions();
            
            // Refresh every 5 seconds by default
            setInterval(() => {
                fetchLog();
                fetchSessions();
            }, 5000);
        </script>
    </body>
    </html>
    """
    return html

# serve the lightweight frontend files from scripts/frontend
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

# ---- Targeted static asset helpers and routes (favicon/logo fallbacks) ----
def _safe_send_path(candidate_path: Path):
    """Return a response for candidate_path if it exists and is a file, else None."""
    try:
        if candidate_path.exists() and candidate_path.is_file():
            return send_file(str(candidate_path))
    except Exception:
        pass
    return None

@app.route('/favicon.ico')
def serve_favicon():
    # Try a few common locations; fall back to the repository logo
    candidates = [
        FRONTEND_DIR / 'favicon.ico',
        REPO_ROOT / 'favicon.ico',
        REPO_ROOT / 'Mycelium' / 'favicon.ico',
        REPO_ROOT / 'Mycelium' / 'Mycelium Logo.png',
        REPO_ROOT / 'Mycelium' / 'Logo.png',
    ]
    for c in candidates:
        resp = _safe_send_path(c)
        if resp:
            return resp
    from werkzeug.exceptions import NotFound
    raise NotFound()

@app.route('/Logo.png')
@app.route('/Mycelium/Logo.png')
def serve_logo_png():
    # Map generic Logo.png requests to the canonical repo logo file when present
    candidates = [
        REPO_ROOT / 'Mycelium' / 'Mycelium Logo.png',
        REPO_ROOT / 'Mycelium' / 'Logo.png',
        FRONTEND_DIR / 'Logo.png',
        REPO_ROOT / 'Logo.png',
    ]
    for c in candidates:
        resp = _safe_send_path(c)
        if resp:
            return resp
    from werkzeug.exceptions import NotFound
    raise NotFound()

@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def serve_frontend(path):
    # Build a prioritized list of candidate paths to try for this request.
    # Start by URL-decoding and normalizing the incoming path, then include
    # variants (original, double-decoded, %20->space, basename fallbacks).
    decoded = unquote(path or "")
    decoded = decoded.lstrip('/')
    original = (path or "").lstrip('/')
    candidates = []
    def add_once(p):
        if not p:
            return
        pp = Path(p).as_posix()
        if pp not in candidates:
            candidates.append(pp)

    add_once(decoded)
    add_once(original)
    try:
        double_decoded = unquote(decoded)
        add_once(double_decoded)
    except Exception:
        double_decoded = None
    if "%20" in (path or ""):
        add_once(original.replace('%20', ' '))
    # basename fallbacks (try under Mycelium/ and at repo root)
    bn = Path(decoded).name
    if bn:
        add_once(Path('Mycelium', bn).as_posix())
        add_once(bn)

    # Debug: print attempts
    try:
        my_dir = REPO_ROOT.joinpath('Mycelium')
        my_listing = []
        if my_dir.exists() and my_dir.is_dir():
            my_listing = [p.name for p in sorted(my_dir.iterdir())]
        print(f"serve_frontend: REPO_ROOT='{REPO_ROOT}' candidates={candidates} Mycelium_listing={my_listing}", flush=True)
    except Exception:
        print(f"serve_frontend: REPO_ROOT='{REPO_ROOT}' candidates={candidates}", flush=True)

    # Try each candidate: prefer FRONTEND_DIR, then REPO_ROOT. Use send_file for
    # absolute filesystem paths when possible to avoid send_from_directory quirks.
    for cand in candidates:
        # check frontend dir
        fe_path = FRONTEND_DIR.joinpath(cand)
        if fe_path.exists():
            try:
                # If candidate contains directory parts, serve from that folder
                parts = Path(cand).parts
                if len(parts) > 1:
                    folder = FRONTEND_DIR.joinpath(*parts[:-1])
                    return send_from_directory(str(folder), parts[-1])
                return send_from_directory(str(FRONTEND_DIR), cand)
            except Exception:
                try:
                    return send_file(str(fe_path))
                except Exception:
                    pass

        # check repo root
        repo_path = REPO_ROOT.joinpath(cand)
        if repo_path.exists():
            try:
                return send_file(str(repo_path))
            except Exception:
                try:
                    # fallback: serve using send_from_directory with folder/filename split
                    parts = Path(cand).parts
                    if len(parts) > 1:
                        folder = REPO_ROOT.joinpath(*parts[:-1])
                        return send_from_directory(str(folder), parts[-1])
                    return send_from_directory(str(REPO_ROOT), cand)
                except Exception:
                    pass

    # No candidate matched; raise a NotFound (will become 404)
    from werkzeug.exceptions import NotFound
    raise NotFound()


# Dedicated, robust handler for files under /Mycelium/
@app.route('/Mycelium/<path:subpath>')
def serve_mycelium(subpath):
    # subpath may be percent-encoded; decode and try to serve the file from
    # the repository's Mycelium directory.
    try:
        decoded = unquote(subpath or '')
        decoded = decoded.lstrip('/')
        # candidate under REPO_ROOT/Mycelium/<decoded>
        cand = REPO_ROOT.joinpath('Mycelium', decoded)
        if cand.exists() and cand.is_file():
            return send_file(str(cand))
        # fallback: try using the raw subpath directly
        cand2 = REPO_ROOT.joinpath('Mycelium', subpath)
        if cand2.exists() and cand2.is_file():
            return send_file(str(cand2))
        # fallback: try basename lookup in Mycelium/
        bn = Path(decoded).name
        if bn:
            cand3 = REPO_ROOT.joinpath('Mycelium', bn)
            if cand3.exists() and cand3.is_file():
                return send_file(str(cand3))
    except Exception:
        pass
    from werkzeug.exceptions import NotFound
    raise NotFound()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "9002"))

    # Only perform the pre-start port detection in the initial parent process.
    # The Flask/werkzeug reloader spawns a child process (with
    # WERKZEUG_RUN_MAIN='true') which should not repeat the detection logic
    # or prompt the user. Skip the detection there to avoid kill/respawn loops.
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        # we're in the reloader child; skip pre-start checks
        # Ensure cwd is repo root for subprocess calls
        try:
            os.chdir(str(REPO_ROOT))
        except Exception:
            pass
        # respect NO_RELOAD flag (child shouldn't run when NO_RELOAD set)
        no_reload = os.environ.get('NO_RELOAD', '0') == '1'
        if no_reload:
            # Parent intended no-reload; child should not proceed
            raise SystemExit(0)
        app.run(host="0.0.0.0", port=port, debug=True)
        raise SystemExit(0)

    # Before starting, detect any processes listening on this port and offer to kill them.
    # On macOS, `lsof -i :<port> -sTCP:LISTEN` works well; fall back to netstat if needed.
    # Respect explicit FORCE_KILL, but also auto-enable in CI/non-interactive runs
    env_force_kill = os.environ.get("FORCE_KILL", "0") == "1"
    # Auto-enable force_kill when running in CI or headless/non-interactive shells.
    auto_enable = os.environ.get("HEADLESS", "0") == "1" or os.environ.get("CI", "0") == "1" or os.environ.get("NO_PROMPT", "0") == "1"
    force_kill = env_force_kill or auto_enable or (not __import__('sys').stdin.isatty())

    def find_listeners(p: int):
        import subprocess
        try:
            out = subprocess.check_output(["lsof", "-i", f":{p}", "-sTCP:LISTEN"], stderr=subprocess.DEVNULL, text=True)
            lines = [l for l in out.splitlines() if l.strip()]
            # first line is header; parse subsequent lines to extract PID and COMMAND
            listeners = []
            for ln in lines[1:]:
                parts = ln.split()
                if len(parts) >= 2:
                    cmd = parts[0]
                    pid = parts[1]
                    listeners.append((cmd, int(pid), ln))
            return listeners
        except Exception:
            return []

    listeners = find_listeners(port)
    if listeners:
        print(f"Detected {len(listeners)} process(es) listening on port {port}:")
        for cmd, pid, raw in listeners:
            print(f"  PID={pid} CMD={cmd}  -> {raw}")

        should_kill = False
        if force_kill:
            should_kill = True
        else:
            try:
                # only prompt if running in interactive terminal
                import sys
                if sys.stdin.isatty():
                    ans = input("Kill these processes and continue? [y/N]: ")
                    should_kill = ans.strip().lower() in ("y", "yes")
                else:
                    print("Non-interactive shell; set FORCE_KILL=1 to auto-kill.")
            except Exception:
                pass

        if should_kill:
            import os as _os, signal, time as _time
            # First attempt graceful termination
            for _cmd, _pid, _ in listeners:
                try:
                    print(f"Sending SIGTERM to PID {_pid}...")
                    _os.kill(_pid, signal.SIGTERM)
                except Exception as e:
                    print(f"Failed to SIGTERM PID {_pid}: {e}")

            # wait for the port to free up, with retries
            def still_listening():
                return bool(find_listeners(port))

            wait_seconds = 5
            interval = 0.25
            waited = 0.0
            while waited < wait_seconds and still_listening():
                _time.sleep(interval)
                waited += interval

            # escalate to SIGKILL if something still listens
            if still_listening():
                print("Some processes are still listening after SIGTERM; escalating to SIGKILL")
                for _cmd, _pid, _ in find_listeners(port):
                    try:
                        print(f"Sending SIGKILL to PID {_pid}...")
                        _os.kill(_pid, signal.SIGKILL)
                    except Exception as e:
                        print(f"Failed to SIGKILL PID {_pid}: {e}")

                # final short wait
                _time.sleep(0.5)

            if still_listening():
                print("Port still in use after attempted kills; aborting server start.")
                raise SystemExit(1)
        else:
            print("Not killing existing listeners; aborting server start.")
            raise SystemExit(1)
        
        
    # Allow starting without the werkzeug reloader for stable single-process runs
    no_reload = os.environ.get('NO_RELOAD', '0') == '1'
    debug_mode = not no_reload
    
    # Ensure cwd is repo root for subprocess calls
    try:
        os.chdir(str(REPO_ROOT))
    except Exception:
        pass
    
    # Optionally run the Wikigraphs generator in the background on startup.
    # Controlled by RUN_WIKIGRAPHS_ON_STARTUP=1 environment variable to avoid
    # surprising behavior in test or CI runs.
    try:
        run_wikigraphs = os.environ.get('RUN_WIKIGRAPHS_ON_STARTUP', '0') == '1'
        if run_wikigraphs:
            import subprocess, time
            script = Path(__file__).resolve().parents[1].joinpath('Python', 'Wikigraphs.py')
            if script.exists():
                cmd = [sys.executable, str(script), '--root', '.']
                # spawn as background process (detached)
                proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                pid_file = REPO_ROOT.joinpath('server_pid.txt')
                try:
                    pid_file.write_text(str(proc.pid) + '\n', encoding='utf-8')
                except Exception:
                    pass
                print(f"Spawned Wikigraphs background process, PID={proc.pid}")
                # small delay to allow process to start
                time.sleep(0.1)
    except Exception as e:
        print(f"Failed to spawn Wikigraphs on startup: {e}")

    app.run(host="0.0.0.0", port=port, debug=debug_mode, use_reloader=debug_mode)
