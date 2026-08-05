#!/bin/bash

# Cloudflare Tunnel Startup Script
# This script creates a Cloudflare tunnel to expose the frontend server

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Target URL
TARGET_URL="http://localhost:5173"

echo -e "${BLUE}=== Starting Cloudflare Tunnel ===${NC}\n"

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo -e "${RED}Error: cloudflared is not installed${NC}"
    echo -e "${YELLOW}Install it with: brew install cloudflared${NC}"
    echo -e "${YELLOW}Or visit: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/${NC}"
    exit 1
fi

# Check if target is reachable
echo -e "${GREEN}Checking if target is reachable...${NC}"
if ! curl -s --connect-timeout 5 "$TARGET_URL" > /dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Cannot connect to $TARGET_URL${NC}"
    echo -e "${YELLOW}Make sure the frontend server is running first.${NC}"
    echo -e "${YELLOW}You can start it with: ./start_game.sh or ./start_gm_mode.sh${NC}\n"
fi

# Start the tunnel
echo -e "${GREEN}Starting Cloudflare tunnel to: $TARGET_URL${NC}"
echo -e "${YELLOW}This will generate a public URL with a random subdomain...${NC}\n"

# Run cloudflared tunnel
cloudflared tunnel --url "$TARGET_URL"

# This will keep running until Ctrl+C
echo -e "\n${BLUE}Tunnel stopped.${NC}"
