#!/bin/bash
# Test runner with automatic error analysis
#
# Usage:
#   ./test-with-analysis.sh              # Run all tests with analysis
#   ./test-with-analysis.sh --headed     # Run with visible browser
#   ./test-with-analysis.sh --ui         # Run with Playwright UI
#   ./test-with-analysis.sh --debug      # Run in debug mode

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure we're in the correct directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Playwright Test Suite with Analysis${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"

# Fix PATH to include Node.js
export PATH="/usr/local/bin:$PATH"

# Verify npm is available
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm not found in PATH${NC}"
    echo "PATH=$PATH"
    echo ""
    echo "Please ensure Node.js is installed and in your PATH"
    exit 1
fi

echo -e "${GREEN}✓${NC} npm found: $(which npm)"
echo -e "${GREEN}✓${NC} npm version: $(npm --version)"
echo -e "${GREEN}✓${NC} node version: $(node --version)"
echo ""

# Check if we should run with analysis
MODE="${1:---analyze}"

case "$MODE" in
    --ui)
        echo -e "${BLUE}▸${NC} Running tests in UI mode..."
        npm run test:ui
        ;;
    --debug)
        echo -e "${BLUE}▸${NC} Running tests in debug mode..."
        npm run test:debug
        ;;
    --headed)
        echo -e "${BLUE}▸${NC} Running tests with visible browser..."
        npm run test:headed 2>&1 | tee test-output.log
        echo ""
        echo -e "${BLUE}▸${NC} Analyzing results..."
        node analyze-test-results.js --file test-output.log
        rm test-output.log
        ;;
    --analyze|*)
        echo -e "${BLUE}▸${NC} Running tests with automatic analysis..."
        echo ""
        
        # Run tests and capture output
        if npm test 2>&1 | tee test-output.log; then
            echo ""
            echo -e "${GREEN}✓ All tests passed!${NC}"
            rm test-output.log
        else
            echo ""
            echo -e "${YELLOW}⚠ Tests failed or couldn't start. Analyzing...${NC}"
            echo ""
            
            # Check for common issues
            if grep -q "ModuleNotFoundError.*flask" test-output.log; then
                echo -e "${RED}✗ Flask not installed!${NC}"
                echo ""
                echo -e "${YELLOW}The backend server requires Flask. Install it with:${NC}"
                echo -e "  ${BLUE}pip install flask flask-cors${NC}"
                echo -e "  ${GRAY}# or if using a virtual environment:${NC}"
                echo -e "  ${BLUE}source venv/bin/activate && pip install flask flask-cors${NC}"
                echo ""
            fi
            
            node analyze-test-results.js --file test-output.log
            EXIT_CODE=$?
            rm test-output.log
            exit $EXIT_CODE
        fi
        ;;
esac

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Done!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
