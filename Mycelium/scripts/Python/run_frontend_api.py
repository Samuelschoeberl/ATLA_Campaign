from flask import Flask, send_from_directory
from flask_cors import CORS
from pathlib import Path
import os

# import the blueprint
from frontend_api import bp  # file is in same directory

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
    return send_from_directory(str(FRONTEND_DIR), safe_path)

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
    force_kill = os.environ.get("FORCE_KILL", "0") == "1"

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
    app.run(host="0.0.0.0", port=port, debug=debug_mode, use_reloader=debug_mode)