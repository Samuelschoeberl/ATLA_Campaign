This is a tiny static Vue 3 frontend to view character sheets served by the env sync server.

# Frontend — Character sheet viewer

Tiny static Vue 3 frontend used to browse and edit character sheets served by the env sync server.

Quick start

1. Start the backend (env sync server). From the repo root:

```bash
# bind to localhost (default)
python3 Mycelium/scripts/python/env_sync_server.py --host 127.0.0.1 --port 9001

# or bind to all interfaces so LAN devices can reach it
python3 Mycelium/scripts/python/env_sync_server.py --bind-all --port 9001
```

2. Serve this frontend folder as static files (quick test):

```bash
cd Mycelium/scripts/frontend
python3 -m http.server 8000
```

3. Open the page in a browser: http://127.0.0.1:8000

Configuring the backend base URL

By default the SPA expects the backend API at http://127.0.0.1:9001. If your backend runs on a different host/port, either:

- Edit `index.html` and change the `BACKEND_BASE` constant at the top, or
- Set `window.MYCELIUM_BACKEND_BASE` before the app loads (for example from the browser console)

Example (serve frontend on the same machine, backend on port 9001):

```bash
# frontend -> http://127.0.0.1:8000
# backend  -> http://127.0.0.1:9001
```

Token / auth

The backend supports an optional shared token. Set the token with the `MYCELIUM_SYNC_TOKEN` environment variable before starting the backend, or pass it to the `manage_env_sync.sh` helper. Browser clients should send this token using one of these headers when doing POSTs:

- `Authorization: Bearer <TOKEN>`
- `X-Auth-Token: <TOKEN>`

CORS

The backend enables simple CORS for browser clients by default and allows the above headers in preflight requests.

Manage script helper

You can start/stop both backend and frontend with the helper script (uses the on-disk `Python` path):

```bash
# from repo root
Mycelium/scripts/Python/manage_env_sync.sh start [LAN_IP] [TOKEN]
Mycelium/scripts/Python/manage_env_sync.sh stop
Mycelium/scripts/Python/manage_env_sync.sh status
```

Notes

- The frontend renders Markdown (GFM tables) using `marked` and sanitizes HTML with `DOMPurify`.
- Saving a sheet via the UI POSTs to the backend and the backend will call the repository's propagation logic so canonical variables and other sheets are updated similarly to the watcher.
- This setup is intentionally minimal and not hardened for public networks. Use a VPN or bind to local interfaces only if you need LAN-only access.

If you want, I can add a one-line systemd/launchd service or improve the UI diffing using jsdiff.
