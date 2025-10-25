#!/bin/bash

# Script to start both backend and React frontend for Mycelium

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Mycelium Backend and Frontend${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

# Start Backend (Flask server)
echo -e "${GREEN}[1/2] Starting Backend (Flask) on port 9002...${NC}"
cd "$REPO_ROOT"
python3 Mycelium/scripts/Python/run_frontend_api.py &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
sleep 2

# Start Frontend (Vite dev server)
echo -e "${GREEN}[2/2] Starting Frontend (React/Vite)...${NC}"
cd "$REPO_ROOT/Mycelium/scripts/frontend-react"
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo -e "${BLUE}Both servers started!${NC}"
echo ""
echo "Backend:  http://localhost:9002  (Flask API)"
echo "Frontend: http://localhost:5173  (React App - check terminal output for actual port)"
echo ""
echo "To stop both servers, press Ctrl+C or run:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Tailing logs... (Ctrl+C to exit)"
wait
