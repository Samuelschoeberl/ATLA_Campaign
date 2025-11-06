#!/bin/bash

# Game Session Shutdown Script
# This script stops all running game session services

# Colors for output
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base directory
BASE_DIR="/Users/samuelschoberl/projects/ATLA_Campaign"
PID_FILE="$BASE_DIR/.game_session_pids"

echo -e "${BLUE}=== Stopping ATLA Campaign Game Session ===${NC}\n"

if [ ! -f "$PID_FILE" ]; then
    echo -e "${RED}No PID file found. Services may not be running.${NC}"
    exit 1
fi

# Read PIDs and kill processes
while IFS= read -r pid; do
    if ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${YELLOW}Stopping process $pid...${NC}"
        kill "$pid"
    else
        echo -e "${YELLOW}Process $pid not running${NC}"
    fi
done < "$PID_FILE"

# Clean up PID file
rm "$PID_FILE"

echo -e "\n${BLUE}=== All services stopped! ===${NC}"
