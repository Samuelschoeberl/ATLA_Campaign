from flask import Flask, send_from_directory
from flask_cors import CORS
from pathlib import Path
import os
import sys

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

# Ensure the current working directory is the repository root. This makes
# subprocess invocations performed by the API (for example the Wikigraphs
# generator) run with a predictable cwd so output files end up in the
# expected repository-relative locations.
try:
    os.chdir(str(REPO_ROOT))
except Exception:
    # non-fatal; continue without changing cwd
    pass

# create app without default static folder to serve our frontend dir explicitly
app = Flask(__name__, static_folder=None)
CORS(app)  # allow requests from the frontend served from file:// or another host
app.register_blueprint(bp)

# serve the lightweight frontend files from scripts/frontend
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def serve_frontend(path):
    safe_path = Path(path).as_posix()
    # First try to serve from the frontend directory (default UI files).
    try:
        return send_from_directory(str(FRONTEND_DIR), safe_path)
    except Exception:
        # If not found in the frontend directory, fall back to serving from the
        # repository root so assets checked into the repo (like Mycelium Logo.png)
        # are accessible at predictable URLs such as /Mycelium/Mycelium%20Logo.png.
        repo_candidate = REPO_ROOT.joinpath(safe_path)
        if repo_candidate.exists():
            return send_from_directory(str(REPO_ROOT), safe_path)
        # Re-raise the original error to preserve Flask's normal 404 behavior
        raise

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "9002"))

    # Only perform the pre-start port detection in the initial parent process.
    # The Flask/werkzeug reloader spawns a child process (with
    # WERKZEUG_RUN_MAIN='true') which should not repeat the detection logic
    # or prompt the user. Skip the detection there to avoid kill/respawn loops.
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        # we're in the reloader child; skip pre-start checks
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