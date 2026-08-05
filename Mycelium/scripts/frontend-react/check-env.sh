#!/bin/bash
# Environment Check for Playwright Tests
# Verifies all dependencies and configuration

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Playwright Test Environment Check${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"

ERRORS=0

# Fix PATH
export PATH="/usr/local/bin:$PATH"

# Check Node.js
echo -n "Checking Node.js... "
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓${NC} Found: $NODE_VERSION"
else
    echo -e "${RED}✗ Not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check npm
echo -n "Checking npm... "
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo -e "${GREEN}✓${NC} Found: v$NPM_VERSION"
else
    echo -e "${RED}✗ Not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check if we're in the right directory
echo -n "Checking directory... "
if [ -f "package.json" ] && grep -q "playwright" package.json; then
    echo -e "${GREEN}✓${NC} Correct directory"
else
    echo -e "${RED}✗ Wrong directory or missing package.json${NC}"
    echo -e "  ${YELLOW}Run from: Mycelium/scripts/frontend-react/${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check node_modules
echo -n "Checking dependencies... "
if [ -d "node_modules" ] && [ -d "node_modules/@playwright" ]; then
    echo -e "${GREEN}✓${NC} Installed"
else
    echo -e "${YELLOW}⚠${NC} Missing or incomplete"
    echo -e "  ${YELLOW}Run: npm install${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check Playwright browsers
echo -n "Checking Playwright browsers... "
if [ -d "$HOME/.cache/ms-playwright" ] || [ -d "$HOME/Library/Caches/ms-playwright" ]; then
    echo -e "${GREEN}✓${NC} Installed"
else
    echo -e "${YELLOW}⚠${NC} Not installed"
    echo -e "  ${YELLOW}Run: npx playwright install${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check test files
echo -n "Checking test files... "
if [ -d "tests/e2e" ] && [ -f "tests/e2e/fixtures.js" ]; then
    TEST_COUNT=$(find tests/e2e -name "*.spec.js" | wc -l | tr -d ' ')
    echo -e "${GREEN}✓${NC} Found $TEST_COUNT test files"
else
    echo -e "${RED}✗ Test files missing${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check analysis tools
echo -n "Checking analysis tools... "
if [ -f "analyze-test-results.js" ] && [ -x "test-with-analysis.sh" ]; then
    echo -e "${GREEN}✓${NC} Available"
else
    echo -e "${YELLOW}⚠${NC} Some tools missing"
    if [ ! -x "test-with-analysis.sh" ]; then
        echo -e "  ${YELLOW}Run: chmod +x test-with-analysis.sh${NC}"
    fi
fi

# Check for port conflicts
echo -n "Checking ports 9002, 5173... "
PORT_9002=$(lsof -ti:9002 2>/dev/null | wc -l | tr -d ' ')
PORT_5173=$(lsof -ti:5173 2>/dev/null | wc -l | tr -d ' ')

if [ "$PORT_9002" = "0" ] && [ "$PORT_5173" = "0" ]; then
    echo -e "${GREEN}✓${NC} Available"
else
    echo -e "${YELLOW}⚠${NC} Some ports in use"
    if [ "$PORT_9002" != "0" ]; then
        echo -e "  ${YELLOW}Port 9002: Process running (PID: $(lsof -ti:9002))${NC}"
    fi
    if [ "$PORT_5173" != "0" ]; then
        echo -e "  ${YELLOW}Port 5173: Process running (PID: $(lsof -ti:5173))${NC}"
    fi
    echo -e "  ${YELLOW}Use: FORCE_KILL=1 npm test${NC}"
fi

# Check Python and Flask (required for backend)
echo -n "Checking Python & Flask... "

# Try python (conda), then python3, then python2
PYTHON_CMD=""
for cmd in python python3 python2; do
    if command -v $cmd &> /dev/null; then
        PYTHON_CMD=$cmd
        break
    fi
done

if [ -n "$PYTHON_CMD" ]; then
    if $PYTHON_CMD -c "import flask" 2>/dev/null; then
        FLASK_VERSION=$($PYTHON_CMD -c "import flask; print(flask.__version__)" 2>/dev/null)
        PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
        echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION + Flask $FLASK_VERSION"
    else
        echo -e "${YELLOW}⚠${NC} Flask not installed"
        echo -e "  ${YELLOW}Tests need Flask backend. Install:${NC}"
        if [[ "$CONDA_DEFAULT_ENV" != "" ]]; then
            echo -e "  ${YELLOW}conda install flask flask-cors${NC}"
            echo -e "  ${YELLOW}# or: pip install flask flask-cors${NC}"
        else
            echo -e "  ${YELLOW}pip install flask flask-cors${NC}"
        fi
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${RED}✗ Python not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ Environment ready!${NC}"
    echo ""
    echo "Quick start:"
    echo -e "  ${BLUE}npm run test:analyze${NC}     - Run tests with analysis"
    echo -e "  ${BLUE}npm run test:ui${NC}          - Interactive UI mode"
    echo -e "  ${BLUE}npm test${NC}                 - Standard headless tests"
else
    echo -e "${RED}✗ Found $ERRORS issue(s)${NC}"
    echo ""
    echo "Fix the issues above and run this script again."
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

exit $ERRORS
