# Starting Mycelium Backend & React Frontend

## Quick Start (Automated)

Run the start script from the repository root:

```bash
./Mycelium/scripts/shell/start_servers.sh
```

This will start both servers automatically.

---

## Manual Start (Step by Step)

### 1. Start the Backend (Flask API)

Open a terminal and run:

```bash
cd /Users/samuelschoberl/projects/ATLA_Campaign
python3 Mycelium/scripts/Python/run_frontend_api.py
```

The backend will start on **http://localhost:9002**

**Environment variables you can use:**

- `PORT=8080` - Change the port (default: 9002)
- `FORCE_KILL=1` - Auto-kill any process on that port
- `NO_RELOAD=1` - Disable Flask auto-reload

Example with custom port:

```bash
PORT=8080 python3 Mycelium/scripts/Python/run_frontend_api.py
```

---

### 2. Start the Frontend (React/Vite)

Open a **second terminal** and run:

```bash
cd /Users/samuelschoberl/projects/ATLA_Campaign/Mycelium/scripts/frontend-react
npm run dev
```

The frontend will start on **http://localhost:5173** (Vite's default port)

---

## Accessing the Application

Once both servers are running:

1. **Open your browser** to: http://localhost:5173
2. The React frontend will automatically proxy API calls to the backend on port 9002

---

## Stopping the Servers

Press `Ctrl+C` in each terminal window to stop the respective server.

---

## Troubleshooting

### Backend won't start - Port already in use

If you see an error about port 9002 being in use:

```bash
FORCE_KILL=1 python3 Mycelium/scripts/Python/run_frontend_api.py
```

Or manually kill the process:

```bash
lsof -ti:9002 | xargs kill -9
```

### Frontend won't start - npm not found

Make sure Node.js is installed:

```bash
brew install node
```

Then install dependencies:

```bash
cd Mycelium/scripts/frontend-react
npm install
```

### Backend API errors (500, 404)

Make sure you're in the repository root when starting the backend:

```bash
cd /Users/samuelschoberl/projects/ATLA_Campaign
python3 Mycelium/scripts/Python/run_frontend_api.py
```

### Wrong port configuration

The Vite config (in `frontend-react/vite.config.js`) proxies API calls to `localhost:8000`. If your backend runs on a different port, update the proxy configuration or set the backend base URL in the browser console:

```javascript
window.MYCELIUM_BACKEND_BASE = "http://localhost:9002";
```

---

## What Each Server Does

**Backend (Flask - Port 9002)**

- Serves the API endpoints (`/player_root`, `/api/*`)
- Handles file operations (read, write, move, delete)
- Generates wikigraphs
- Manages character sheets

**Frontend (React/Vite - Port 5173)**

- Serves the React application
- Provides the user interface
- Makes API calls to the backend
- Hot-reloads on code changes during development
