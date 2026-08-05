# Setup Instructions for Stability Tests

## Prerequisites Installation

Before running the stability tests, you need to install the required dependencies.

### 1. Python Dependencies

The backend requires Flask and Flask-CORS.

**For macOS with Homebrew-managed Python (recommended):**

```bash
# Install with --user flag (safer than --break-system-packages)
pip3 install --user flask flask-cors
```

**Alternative - Using Homebrew directly:**

```bash
brew install python-flask
```

**Alternative - Using a virtual environment:**

```bash
cd /Users/samuelschoberl/projects/ATLA_Campaign
python3 -m venv venv
source venv/bin/activate
pip install flask flask-cors
```

Or if you have a requirements.txt:

```bash
pip3 install --user -r requirements.txt
```

### 2. Node.js Dependencies

The frontend requires Node packages (should already be installed):

```bash
cd Mycelium/scripts/frontend-react
npm install
```

### 3. Playwright Browsers

Install Playwright browser binaries:

```bash
npx playwright install
```

## Verify Setup

Run the verification script:

```bash
cd Mycelium/scripts/frontend-react
./tests/verify-setup.sh
```

## Run Tests

Once dependencies are installed:

```bash
# Make sure /usr/local/bin is in PATH
export PATH=/usr/local/bin:$PATH

# Run stability tests
npm run test:stability

# Or use the automated runner
./tests/run-stability-tests.sh --stability
```

## Troubleshooting

### "No module named 'flask'"

Install Flask (choose one method):

**Option 1: User installation (recommended for Homebrew Python):**
```bash
pip3 install --user flask flask-cors
```

**Option 2: Homebrew:**
```bash
brew install python-flask
```

**Option 3: Virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install flask flask-cors
```

### "npm: command not found"

Add Node to PATH:
```bash
export PATH=/usr/local/bin:$PATH
```

### "Port already in use"

The test runner automatically kills processes on the required ports (9002, 5173). If you see issues, manually kill them:

```bash
lsof -ti:9002 | xargs kill -9
lsof -ti:5173 | xargs kill -9
```

### Backend fails to start

Check the backend log:
```bash
cat Mycelium/scripts/Python/backend.log
```

Common issues:
- Flask not installed
- Port permission issues
- Python version incompatibility (need Python 3.7+)
