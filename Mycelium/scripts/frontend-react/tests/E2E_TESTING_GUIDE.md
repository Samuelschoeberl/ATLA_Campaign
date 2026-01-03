# Playwright E2E Testing Guide

## Overview

This project uses [Playwright](https://playwright.dev/) for end-to-end testing of the Flask backend (`run_backend.py`) and React frontend integration. The tests catch real-world issues that unit tests miss:

- ✅ **Routing issues** - Deep linking, client-side routing, 404 handling
- ✅ **Runtime errors** - Uncaught exceptions, console.error messages
- ✅ **Integration problems** - CORS issues, API failures, network errors
- ✅ **Bundling issues** - Missing assets, import errors
- ✅ **Auth flows** - Session handling, permissions
- ✅ **"Works locally" issues** - Environment-specific bugs

## What Makes These Tests Special

### Automatic Error Detection

The tests **automatically fail** if:

1. **Uncaught exceptions occur** (`pageerror` event)
2. **Console.error is called** (frontend errors)
3. **Network requests fail unexpectedly** (optional, per test)

This is configured in `tests/e2e/fixtures.js` with the `errorTracker` fixture.

### Real Server Integration

- **Flask backend** starts automatically on port 9002
- **Vite dev server** starts automatically on port 5173
- Tests run against real servers, not mocks
- Catches CORS, routing, and bundling issues

## Installation

Playwright is already installed as a dev dependency:

```bash
npm install
```

To install browser binaries (first time only):

```bash
npx playwright install
```

## Running Tests

### Quick Start

```bash
# Run all tests (headless)
npm test

# Run with browser visible (headed mode)
npm run test:headed

# Run with Playwright UI (best for development)
npm run test:ui

# Debug a specific test
npm run test:debug

# View last test report
npm run test:report
```

### Advanced Commands

```bash
# Run a specific test file
npx playwright test tests/e2e/server-integration.spec.js

# Run tests matching a pattern
npx playwright test --grep "routing"

# Run in specific browser
npx playwright test --project=chromium

# Update snapshots (if you add visual tests)
npx playwright test --update-snapshots

# Generate test code interactively
npm run test:codegen
```

## Test Structure

```
tests/
└── e2e/
    ├── fixtures.js                    # Error tracking, utilities
    ├── server-integration.spec.js     # Backend/frontend communication
    ├── routing.spec.js                # Client-side routing, deep linking
    ├── file-explorer.spec.js          # File tree, file loading
    ├── character-sheet.spec.js        # Character data, stats
    ├── dice-roller.spec.js            # Dice rolling functionality
    ├── gm-mode.spec.js                # GM-specific features
    └── error-handling.spec.js         # Edge cases, failures
```

## Test Categories

### 🌐 Server Integration Tests
- Backend API responds correctly
- Frontend can fetch from backend
- No CORS errors
- Static assets load properly

### 🔀 Routing Tests
- Home page loads
- Navigation between sections (PCs, NPCs, Story)
- Deep linking works (e.g., `/PCs/Mahogany`)
- Browser back/forward buttons work
- 404 routes still serve the SPA

### 📁 File Explorer Tests
- File tree renders
- Folders expand/collapse
- Clicking files loads content
- Handles missing files gracefully

### 🎭 Character Sheet Tests
- Character data loads
- Stats display correctly
- Can switch between characters
- JSON data is accessible

### 🎲 Dice Roller Tests
- Dice roller UI renders
- Can roll dice
- Handles multiple rolls
- Results are valid

### 👑 GM Mode Tests
- GM mode can be accessed
- Shows additional controls
- Initiative tracker works
- Can access NPC files
- Can switch back to player mode

### ❌ Error Handling Tests
- Network failures don't crash the app
- Malformed API responses handled
- 500 errors shown gracefully
- Missing files handled
- Rapid navigation works
- Page reload during API call

## Configuration

### `playwright.config.js`

Key settings:

```javascript
{
  baseURL: 'http://localhost:5173',
  timeout: 30000,  // 30 seconds per test
  retries: 2,      // Retry failed tests (CI only)
  workers: 1,      // Run tests serially (avoid port conflicts)
  
  webServer: [
    // Flask backend
    {
      command: 'python3 run_backend.py',
      url: 'http://localhost:9002',
      env: { NO_RELOAD: '1', FORCE_KILL: '1' }
    },
    // Vite frontend
    {
      command: 'npm run dev',
      url: 'http://localhost:5173'
    }
  ]
}
```

### Environment Variables

Control test behavior:

```bash
# Run in CI mode (more retries, JSON output)
CI=1 npm test

# Keep existing servers running (don't start new ones)
npm test  # reuseExistingServer=true by default

# Force kill existing processes on ports
FORCE_KILL=1 npm test
```

## Writing New Tests

### Basic Test Template

```javascript
import { test, expect } from './fixtures.js';

test.describe('My Feature', () => {
  test('should do something', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Your test code here
    await expect(page.locator('#root')).toBeVisible();
    
    // errorTracker automatically fails on:
    // - Uncaught exceptions
    // - console.error messages
  });
});
```

### Error Tracker Usage

The `errorTracker` fixture automatically tracks:

```javascript
test('example', async ({ page, errorTracker }) => {
  await page.goto('/');
  
  // After test, these are automatically checked:
  // errorTracker.consoleErrors - All console.error() calls
  // errorTracker.pageErrors - All uncaught exceptions
  // errorTracker.failedRequests - HTTP 4xx/5xx responses
  
  // Test fails if pageErrors.length > 0
});
```

### Testing Expected Errors

If you expect errors (e.g., testing error handling):

```javascript
test('handles errors gracefully', async ({ page, errorTracker }) => {
  await page.route('**/api/**', route => route.abort());
  
  await page.goto('/');
  
  // App should still render even with API failures
  await expect(page.locator('#root')).toBeVisible();
  
  // Note: This test will pass even if there are console errors,
  // as long as there are no uncaught exceptions
});
```

## Best Practices

### ✅ Do

- **Use error tracker** - It catches bugs automatically
- **Test real user flows** - Navigation, form submission, etc.
- **Test error states** - Network failures, 404s, etc.
- **Use page.waitForTimeout() sparingly** - Prefer waitForSelector()
- **Run tests before pushing** - Catch integration issues early

### ❌ Don't

- **Mock everything** - These are E2E tests, use real servers
- **Test implementation details** - Test user-visible behavior
- **Make tests dependent on each other** - Each test should be isolated
- **Hardcode data** - Use the actual data from your backend
- **Ignore flaky tests** - Fix them or remove them

## Debugging

### Test Fails - What to Check

1. **Check the error message** - Playwright gives detailed errors
2. **Look at screenshots** - `test-results/` folder has screenshots
3. **Watch the video** - Videos saved on failure
4. **Check traces** - Open with `npx playwright show-trace`
5. **Run in headed mode** - `npm run test:headed`
6. **Run in debug mode** - `npm run test:debug`

### Common Issues

**"Timeout waiting for..."**
- Server didn't start in time
- Element selector is wrong
- Page is still loading

**"Page crashed"**
- Frontend has a critical error
- Check browser console in headed mode

**"net::ERR_CONNECTION_REFUSED"**
- Backend not running
- Wrong port number
- Firewall blocking connection

**"CORS error"**
- Backend CORS not configured
- Frontend using wrong API URL

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: 18
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          cd Mycelium/scripts/frontend-react
          npm ci
          npx playwright install --with-deps
          pip install flask flask-cors
      
      - name: Run tests
        run: |
          cd Mycelium/scripts/frontend-react
          CI=1 npm test
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: Mycelium/scripts/frontend-react/playwright-report/
```

## Test Coverage

Current test coverage:

- ✅ Server startup and communication
- ✅ Frontend loading and rendering
- ✅ CORS configuration
- ✅ Static asset serving
- ✅ Client-side routing
- ✅ Deep linking
- ✅ File explorer functionality
- ✅ Character sheet loading
- ✅ Dice roller
- ✅ GM mode features
- ✅ Error handling
- ⚠️ Battlemap (pending three.js setup)
- ⚠️ Initiative tracker (pending)
- ⚠️ Bending moves (pending)

## Resources

- [Playwright Documentation](https://playwright.dev/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Debugging Tests](https://playwright.dev/docs/debug)
- [CI/CD Setup](https://playwright.dev/docs/ci)

## Troubleshooting

### Tests hang or timeout

1. Check if ports 9002 and 5173 are available
2. Kill existing processes: `lsof -ti:9002 | xargs kill -9`
3. Run with `FORCE_KILL=1 npm test`

### Browser won't install

```bash
# Manual installation
npx playwright install chromium
npx playwright install-deps
```

### Tests pass locally but fail in CI

1. Check environment variables
2. Verify Python/Node versions match
3. Check for hardcoded paths
4. Enable `CI=1` for CI-specific behavior

## Support

For issues or questions:
1. Check test output and screenshots in `test-results/`
2. Run with `--debug` flag for step-by-step execution
3. Check browser console in headed mode
4. Review trace files with `npx playwright show-trace`

---

**Happy Testing! 🎭**
