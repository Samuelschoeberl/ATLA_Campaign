
# This uses absolute Paths so make sure you fix them to where you have the repo cloned

### 1. Start the Backend Server
```bash
cd /Users/samuelschoberl/projects/ATLA_Campaign
python3 Mycelium/scripts/Python/run_backend.py
```
Backend will be available at: `http://localhost:9002`

### 2. Start the Frontend (Development)
```bash
export PATH="/usr/local/bin:$PATH"  # Only needed if brew/npm not in PATH
cd /Users/samuelschoberl/projects/ATLA_Campaign/Mycelium/scripts/frontend-react
npm run dev
```
Frontend will be available at: `http://localhost:5173`

### 3. Start Variable Sync (Optional)
```bash
cd /Users/samuelschoberl/projects/ATLA_Campaign/Mycelium/scripts/Python
python sync_variables.py
```
This runs in watch mode and automatically syncs changes between character sheets and variable files.

**Note:** The script uses absolute paths from the repository root, so it will work correctly regardless of your current directory.

### 4. Generate Initiative Tracker (Combat Only)
```bash
cd /Users/samuelschoberl/projects/ATLA_Campaign/Mycelium/scripts/Python
python generate_initiative.py
```
Creates an initiative tracker for combat. Enter initiative values for each PC and any enemies/NPCs.

**Edit existing tracker:**
```bash
python generate_initiative.py --edit
```

## Cloudflare Tunnel (Optional)

To make the frontend accessible online via a temporary public URL:

```bash
cloudflared tunnel --url http://localhost:5173
```

This creates a secure tunnel to your local frontend. Cloudflare will provide a public URL that you can share with players.

## Complete Game Session Workflow

1. **Start backend** (serves data and APIs)
2. **Start frontend** (player interface)
3. **Start sync script** (keeps character sheets synchronized)
4. **(Optional) Generate initiative tracker** for combat encounters
5. **Play the game!**

## Notes

- The sync script watches for changes in real-time - no need to manually sync
- Sync works in three ways:
  - Character sheets ⟷ Variable files (bidirectional)
  - Environmental variables ⟷ All character sheets (one env var changes all sheets)
  - stat_overview.md → Environmental variables → All sheets
- Backend must be running for frontend to fetch data
- Cloudflare hosting is only for the frontend - backend stays local
- For sync script usage details, see `Mycelium/scripts/manuals/sync_variables_manual.md`
