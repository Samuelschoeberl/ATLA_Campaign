run_frontend_api.py — Manual

## Purpose

`run_frontend_api.py` is a small launcher script that creates and runs a Flask application which exposes the project's frontend files (from `Mycelium/scripts/frontend`) and registers a blueprint `bp` from `frontend_api.py` that implements the API used by the frontend. It intentionally avoids Flask's default static folder and instead serves frontend assets from the repository's `scripts/frontend` directory so the static UI can be opened and developed without packaging.

## Where it lives

File path:

`Mycelium/scripts/Python/run_frontend_api.py`

## Prerequisites

- Python 3.8+ (or whatever your project's standard Python version is).
- `Flask` and `flask-cors` installed in the active environment (project virtualenv recommended).
- The `frontend_api.py` blueprint must be present in the same directory (it is imported as `from frontend_api import bp`).

## Recommended setup

1. Create and activate a virtual environment in the project root (if you don't have one):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # if you have one, otherwise at least install Flask
pip install flask flask-cors
```

2. Run the server (default port 9002):

```bash
PORT=9002 python3 Mycelium/scripts/Python/run_frontend_api.py
```

## Key behaviors and features

- The script constructs a Flask app with `static_folder=None` and registers the `frontend_api` blueprint (which exposes endpoints under `/player_root` and other routes used by the frontend).

- It serves the static frontend directory `Mycelium/scripts/frontend` explicitly using `send_from_directory` in the `serve_frontend` route. This makes the UI accessible at `http://localhost:9002/`.

- Before starting, the script tries to detect any processes listening on the configured port (default 9002) using `lsof` on macOS (falls back gracefully if `lsof` fails). If listeners are found it will either prompt you (interactive shells) to kill them or abort. Use environment variable `FORCE_KILL=1` to automatically kill detected listeners.

- The script supports a `NO_RELOAD` environment variable to start Flask without the werkzeug reloader. When `NO_RELOAD=1` the script runs in single-process mode and will not spawn a reloader child process.

- When the werkzeug reloader is used, the script detects the reloader child process (by checking `WERKZEUG_RUN_MAIN`) and skips the pre-start port detection logic there to avoid double prompting or accidental recursion.

## Environment variables

- `PORT` — network port to listen on. Defaults to `9002`.
- `FORCE_KILL` — if set to `1`, automatically attempt to kill processes listening on `PORT` before starting.
- `NO_RELOAD` — if set to `1`, start Flask without the werkzeug reloader (single-process). This is useful for debugging or when run from tooling that cannot handle reloader behavior.

## Usage examples

Start normally on the default port:

```bash
python3 Mycelium/scripts/Python/run_frontend_api.py
```

Start on a custom port:

```bash
PORT=8080 python3 Mycelium/scripts/Python/run_frontend_api.py
```

Auto-kill any process listening on the port (non-interactive):

```bash
FORCE_KILL=1 PORT=9002 python3 Mycelium/scripts/Python/run_frontend_api.py
```

Start without the werkzeug reloader (single-process):

```bash
NO_RELOAD=1 python3 Mycelium/scripts/Python/run_frontend_api.py
```

## Troubleshooting

- "Port already in use" message or prompt: the script lists processes it found listening on the port and will ask whether to kill them. If running in CI or a non-interactive shell, set `FORCE_KILL=1` to auto-kill.

- Permission errors when using `lsof`: ensure `lsof` is available and the user has permission to inspect process information. On macOS `lsof` is standard; on some systems you may need to install it.

- Import errors for `frontend_api`: ensure `frontend_api.py` exists in `Mycelium/scripts/Python` and that its dependencies are installed.

- If you see unexpected reloader behavior (server restarting twice), try `NO_RELOAD=1` to disable the reloader.

## Security notes

- This server is intended for local development only. It disables Flask's static folder and explicitly serves files from the repo for convenience. Do not expose this server to untrusted networks. It runs with `debug=True` by default when the reloader is enabled — which should never be used in production.

- The script will SIGTERM/SIGKILL other processes when `FORCE_KILL=1` is set. Use with care to avoid terminating unrelated services.

## Further improvements (suggested)

- Add a command-line flag parser (argparse or click) to make behavior explicit and documented in `--help` instead of relying solely on environment variables.
- Add an option to serve over HTTPS for local testing of secure contexts.
- Provide a small health-check endpoint (e.g. `/health`) and a JSON status response for CI checks.

## Notes for maintainers

- The blueprint `bp` is imported from `frontend_api.py`. That file contains the application logic for the `/player_root` API and file-write handlers used by the frontend.
- The frontend files are served from `Mycelium/scripts/frontend`. If you move the UI files, update the `FRONTEND_DIR` in this script accordingly.

### Delete behavior from the frontend UI

- The web UI (served from `Mycelium/scripts/frontend/index.html`) now exposes a Delete button in the markdown editor. When a user deletes a file the client first prompts for confirmation. If confirmed, the client creates a copy of the file under `Player Root/deleted/deleted_<originalfilename>` (preserving the file contents) and then requests deletion of the original file. This is a conservative _move-to-deleted_ approach to avoid immediate destructive deletion.
- The server endpoints used are the existing `/player_root/<folder>/<name>` POST endpoint to create the deleted copy and the `/player_root/<folder>/<name>` DELETE endpoint to remove the original. Ensure those endpoints are available in `frontend_api.py`.
- Note: This behavior is implemented client-side; the server does not currently provide a dedicated 'move' endpoint. If desired, an atomic server-side move endpoint could be added to avoid race conditions between create/delete operations.
- The server now exposes a dedicated atomic server-side move endpoint at `/player_root/move` which accepts a JSON body `{ "src": "<path>", "dst": "<path>" }`. The frontend uses this endpoint to atomically move files into `Player Root/deleted` when deleting from the UI to avoid the create-then-delete race.

---

Generated on 2025-09-24
