#!/bin/bash

# Quick Test - Verify Setup
# This script does a quick sanity check before running full tests

set -e

echo "🔍 Quick Setup Verification"
echo "================================"
echo ""

# Check we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Not in frontend-react directory"
    echo "Please run from: Mycelium/scripts/frontend-react"
    exit 1
fi
echo "✓ In correct directory"

# Check PATH includes /usr/local/bin
if [[ ":$PATH:" != *":/usr/local/bin:"* ]]; then
    echo "⚠️  /usr/local/bin not in PATH, adding it..."
    export PATH=/usr/local/bin:$PATH
fi
echo "✓ PATH configured"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found in PATH"
    exit 1
fi
echo "✓ Node.js found: $(node --version)"

# Check npm
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found"
    exit 1
fi
echo "✓ npm found: $(npm --version)"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi
echo "✓ Python found: $(python3 --version)"

# Check for virtual environment
VENV_PATH="../../../.venv"
if [ -f "$VENV_PATH/bin/python" ]; then
    echo "✓ Virtual environment found"
    PYTHON_CMD="$VENV_PATH/bin/python"
else
    echo "⚠️  No virtual environment found (will use system Python)"
    PYTHON_CMD="python3"
fi

# Check Flask
if ! $PYTHON_CMD -c "import flask" &> /dev/null; then
    echo "❌ Flask not installed"
    echo ""
    echo "   Install with one of these methods:"
    echo "   1. pip3 install --user flask flask-cors"
    echo "   2. brew install python-flask"
    echo ""
    exit 1
fi
echo "✓ Flask installed"

# Check Flask-CORS
if ! $PYTHON_CMD -c "import flask_cors" &> /dev/null; then
    echo "⚠️  Flask-CORS not installed (recommended)"
    echo "   Install with: pip3 install flask-cors"
else
    echo "✓ Flask-CORS installed"
fi

# Check backend exists
if [ ! -f "../Python/run_backend.py" ]; then
    echo "❌ Backend not found at ../Python/run_backend.py"
    exit 1
fi
echo "✓ Backend found"

# Check Playwright
if ! npx playwright --version &> /dev/null; then
    echo "⚠️  Playwright not found, installing..."
    npm install
    npx playwright install
fi
echo "✓ Playwright found: $(npx playwright --version)"

echo ""
echo "================================"
echo "✅ All checks passed!"
echo ""
echo "Ready to run tests. Try:"
echo "  npm run test:stability"
echo "  ./tests/run-stability-tests.sh --stability"
echo ""
