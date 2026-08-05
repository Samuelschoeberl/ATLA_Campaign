#!/bin/bash

# Game Master Mode Quick Start
# This script starts both the backend and frontend for GM Mode

cd "$(dirname "$0")"

echo "🎲 Starting Game Master Mode..."
echo ""

# Check if backend is already running
if lsof -Pi :9002 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "✓ Backend already running on port 9002"
else
    echo "🚀 Starting backend server..."
    # Start backend in background
    python3 Mycelium/scripts/Python/run_backend.py &
    BACKEND_PID=$!
    echo "   Backend PID: $BACKEND_PID"
    sleep 2
fi

# Check if frontend is already running
if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "✓ Frontend already running on port 5173"
else
    echo "🚀 Starting frontend server..."
    cd Mycelium/scripts/frontend-react
    npm run dev &
    FRONTEND_PID=$!
    echo "   Frontend PID: $FRONTEND_PID"
    cd ../../..
    sleep 3
fi

echo ""
echo "✨ Game Master Mode is ready!"
echo ""
echo "📍 Access points:"
echo "   Player Mode:  http://localhost:5173"
echo "   GM Mode:      http://localhost:5173?gm=true"
echo "   Log Viewer:   http://localhost:9002/api/log_viewer"
echo ""
echo "💡 Toggle between modes using the button in the top-right corner"
echo ""
echo "Press Ctrl+C to stop servers"

# Wait for user interrupt
trap "echo ''; echo '🛑 Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# Keep script running
wait
