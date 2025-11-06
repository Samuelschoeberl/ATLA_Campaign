#!/bin/bash

# Game Session Startup Script
# This script starts the backend, frontend, and variable sync for the ATLA Campaign

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base directory
BASE_DIR="/Users/samuelschoberl/projects/ATLA_Campaign"

echo -e "${BLUE}=== Starting ATLA Campaign Game Session ===${NC}\n"

# Step 1: Start Backend Server
echo -e "${GREEN}[1/3] Starting Backend Server...${NC}"
cd "$BASE_DIR"
python3 Mycelium/scripts/Python/run_backend.py &
BACKEND_PID=$!
echo -e "${YELLOW}Backend PID: $BACKEND_PID${NC}"
echo -e "${YELLOW}Backend available at: http://localhost:9002${NC}\n"
sleep 2

# Step 2: Start Frontend
echo -e "${GREEN}[2/3] Starting Frontend...${NC}"
export PATH="/usr/local/bin:$PATH"
cd "$BASE_DIR/Mycelium/scripts/frontend-react"
npm run dev &
FRONTEND_PID=$!
echo -e "${YELLOW}Frontend PID: $FRONTEND_PID${NC}"
echo -e "${YELLOW}Frontend available at: http://localhost:5173${NC}\n"
sleep 2

# Step 3: Start Variable Sync
echo -e "${GREEN}[3/3] Starting Variable Sync...${NC}"
cd "$BASE_DIR/Mycelium/scripts/Python"
python3 sync_variables_direct_edit.py --watch --verbose &
SYNC_PID=$!
echo -e "${YELLOW}Sync PID: $SYNC_PID${NC}\n"

# Save PIDs to a file for easy cleanup
echo "$BACKEND_PID" > "$BASE_DIR/.game_session_pids"
echo "$FRONTEND_PID" >> "$BASE_DIR/.game_session_pids"
echo "$SYNC_PID" >> "$BASE_DIR/.game_session_pids"

echo -e "${BLUE}=== All services started! ===${NC}"
echo -e "${YELLOW}PIDs saved to .game_session_pids${NC}"
echo -e "${YELLOW}To stop all services, run: ./stop_game.sh${NC}\n"

# Wait for all background processes
wait
