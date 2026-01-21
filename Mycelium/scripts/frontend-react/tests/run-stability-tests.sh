#!/bin/bash

# Multi-Client Stability Test Runner
# Handles server startup, test execution, and cleanup for stability testing

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=9002
FRONTEND_PORT=5173
BACKEND_DIR="../Python"
REPO_ROOT="../../.."
VENV_PATH="$REPO_ROOT/.venv"
TEST_TIMEOUT=300  # 5 minutes per test
MAX_CLIENTS=10

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Multi-Client Stability Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    echo -e "${YELLOW}Killing processes on port $port...${NC}"
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
    sleep 1
}

# Function to wait for server
wait_for_server() {
    local url=$1
    local max_wait=$2
    local waited=0
    
    echo -e "${YELLOW}Waiting for server at $url...${NC}"
    
    while [ $waited -lt $max_wait ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Server is ready${NC}"
            return 0
        fi
        sleep 1
        waited=$((waited + 1))
        echo -n "."
    done
    
    echo ""
    echo -e "${RED}✗ Server failed to start within ${max_wait}s${NC}"
    return 1
}

# Function to cleanup
cleanup() {
    echo ""
    echo -e "${YELLOW}Cleaning up...${NC}"
    
    # Kill backend
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    kill_port $BACKEND_PORT
    
    # Kill frontend
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    kill_port $FRONTEND_PORT
    
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Parse arguments
TEST_MODE="all"
HEADED=""
UI_MODE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --stability)
            TEST_MODE="stability"
            shift
            ;;
        --race)
            TEST_MODE="race"
            shift
            ;;
        --sync)
            TEST_MODE="sync"
            shift
            ;;
        --headed)
            HEADED="--headed"
            shift
            ;;
        --ui)
            UI_MODE="--ui"
            shift
            ;;
        --debug)
            HEADED="--debug"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--stability|--race|--sync|--all] [--headed] [--ui] [--debug]"
            exit 1
            ;;
    esac
done

# Step 1: Check prerequisites
echo -e "${BLUE}Step 1: Checking prerequisites...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js found${NC}"

if ! command -v npx &> /dev/null; then
    echo -e "${RED}✗ npx not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ npx found${NC}"

# Check if Playwright is installed
if ! npx playwright --version &> /dev/null; then
    echo -e "${RED}✗ Playwright not found${NC}"
    echo -e "${YELLOW}Installing Playwright...${NC}"
    npm install
    npx playwright install
fi
echo -e "${GREEN}✓ Playwright found${NC}"

echo ""

# Step 2: Clean up any existing servers
echo -e "${BLUE}Step 2: Cleaning up existing servers...${NC}"

if check_port $BACKEND_PORT; then
    kill_port $BACKEND_PORT
fi

if check_port $FRONTEND_PORT; then
    kill_port $FRONTEND_PORT
fi

echo -e "${GREEN}✓ Ports cleaned${NC}"
echo ""

# Step 3: Start backend server
echo -e "${BLUE}Step 3: Starting backend server...${NC}"

cd "$BACKEND_DIR"

# Set environment variables for backend
export NO_RELOAD=1
export FORCE_KILL=1
export HEADLESS=1

# Use virtual environment Python if available
if [ -f "$VENV_PATH/bin/python" ]; then
    PYTHON_CMD="$VENV_PATH/bin/python"
    echo -e "${GREEN}Using virtual environment Python${NC}"
else
    PYTHON_CMD="python3"
fi

# Start backend in background
$PYTHON_CMD run_backend.py > backend.log 2>&1 &
BACKEND_PID=$!

cd - > /dev/null

# Wait for backend to be ready
if ! wait_for_server "http://localhost:$BACKEND_PORT/api/active_sessions" 30; then
    echo -e "${RED}✗ Backend failed to start${NC}"
    echo -e "${YELLOW}Backend log:${NC}"
    tail -n 20 "$BACKEND_DIR/backend.log"
    exit 1
fi

echo ""

# Step 4: Start frontend server
echo -e "${BLUE}Step 4: Starting frontend server...${NC}"

npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to be ready
if ! wait_for_server "http://localhost:$FRONTEND_PORT" 30; then
    echo -e "${RED}✗ Frontend failed to start${NC}"
    echo -e "${YELLOW}Frontend log:${NC}"
    tail -n 20 frontend.log
    exit 1
fi

echo ""

# Step 5: Run tests
echo -e "${BLUE}Step 5: Running stability tests...${NC}"
echo -e "${YELLOW}Test mode: $TEST_MODE${NC}"
echo -e "${YELLOW}Max clients: $MAX_CLIENTS${NC}"
echo ""

# Set environment for tests
export VITE_API_BASE_URL="http://localhost:$FRONTEND_PORT"
export CI=0
export REUSE_SERVERS=1  # Tell Playwright to reuse our servers

TEST_COMMAND=""

case $TEST_MODE in
    stability)
        TEST_COMMAND="npx playwright test tests/e2e/stability-10-clients.spec.js tests/e2e/race-conditions.spec.js --workers=1 --config=playwright.config.stability.js $HEADED $UI_MODE"
        ;;
    race)
        TEST_COMMAND="npx playwright test tests/e2e/race-conditions.spec.js --workers=1 --config=playwright.config.stability.js $HEADED $UI_MODE"
        ;;
    sync)
        TEST_COMMAND="npx playwright test tests/e2e/sync-basic.spec.js tests/e2e/scalability-sync.spec.js tests/e2e/speed-multiclient.spec.js --workers=1 --config=playwright.config.stability.js $HEADED $UI_MODE"
        ;;
    all)
        TEST_COMMAND="npx playwright test tests/e2e/stability-10-clients.spec.js tests/e2e/race-conditions.spec.js tests/e2e/sync-basic.spec.js tests/e2e/scalability-sync.spec.js tests/e2e/speed-multiclient.spec.js --workers=1 --config=playwright.config.stability.js $HEADED $UI_MODE"
        ;;
esac

# Run the tests
if eval $TEST_COMMAND; then
    TEST_RESULT=0
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
else
    TEST_RESULT=$?
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ Some tests failed${NC}"
    echo -e "${RED}========================================${NC}"
fi

echo ""

# Step 6: Generate report
echo -e "${BLUE}Step 6: Test results${NC}"
echo ""

# Show summary
if [ -f "test-results/test-results.json" ]; then
    echo -e "${YELLOW}Test Summary:${NC}"
    node -e "
        const fs = require('fs');
        const data = JSON.parse(fs.readFileSync('test-results/test-results.json', 'utf8'));
        const suites = data.suites || [];
        let passed = 0, failed = 0, skipped = 0;
        
        function countTests(suite) {
            if (suite.specs) {
                suite.specs.forEach(spec => {
                    if (spec.ok) passed++;
                    else if (spec.tests && spec.tests[0]?.results[0]?.status === 'skipped') skipped++;
                    else failed++;
                });
            }
            if (suite.suites) {
                suite.suites.forEach(countTests);
            }
        }
        
        suites.forEach(countTests);
        
        console.log('  Passed: ' + passed);
        console.log('  Failed: ' + failed);
        console.log('  Skipped: ' + skipped);
        console.log('  Total: ' + (passed + failed + skipped));
    " 2>/dev/null || echo "  Unable to parse test results"
fi

echo ""
echo -e "${YELLOW}View detailed report:${NC}"
echo -e "  ${BLUE}npx playwright show-report${NC}"
echo ""

echo -e "${YELLOW}Check server logs:${NC}"
echo -e "  Backend:  tail -f $BACKEND_DIR/backend.log"
echo -e "  Frontend: tail -f frontend.log"
echo -e "  Client activity: open http://localhost:$BACKEND_PORT/api/log_viewer"
echo ""

# Exit with test result code
exit $TEST_RESULT
