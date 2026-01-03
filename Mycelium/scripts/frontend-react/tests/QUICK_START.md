# Playwright E2E Testing - Quick Reference

## Install & Setup

```bash
cd Mycelium/scripts/frontend-react
npm install
npx playwright install  # First time only
```

## Run Tests

```bash
npm test              # Run all tests (headless)
npm run test:headed   # Run with browser visible
npm run test:ui       # Interactive UI mode (best for dev)
npm run test:debug    # Step-through debugger
npm run test:report   # View last test report
```

## What Gets Tested

✅ **Backend + Frontend Integration**
- Flask server on port 9002
- Vite dev server on port 5173
- API communication
- CORS configuration
- Asset loading

✅ **Automatic Error Detection**
- Uncaught exceptions → test fails
- console.error() → logged (fails on page errors)
- Network failures → tracked

✅ **User Flows**
- Routing & navigation
- File explorer
- Character sheets
- Dice roller
- GM mode
- Error handling

## Key Files

- `playwright.config.js` - Test configuration
- `tests/e2e/fixtures.js` - Error tracking utilities
- `tests/e2e/*.spec.js` - Test suites
- `tests/E2E_TESTING_GUIDE.md` - Full documentation

## Quick Commands

```bash
# Run specific test file
npx playwright test tests/e2e/server-integration.spec.js

# Run tests matching pattern
npx playwright test --grep "routing"

# Generate new test code
npm run test:codegen

# Update snapshots
npx playwright test --update-snapshots
```

## Debugging Failed Tests

1. Check `test-results/` for screenshots & videos
2. Run `npm run test:headed` to see browser
3. Use `npm run test:debug` for step-through
4. Check traces: `npx playwright show-trace <trace-file>`

## Common Issues

**Port already in use:**
```bash
FORCE_KILL=1 npm test
```

**Tests timeout:**
- Increase timeout in `playwright.config.js`
- Check servers are starting properly
- Verify element selectors are correct

**CI failures:**
```bash
CI=1 npm test  # Use CI mode locally
```

## Writing Tests

```javascript
import { test, expect } from './fixtures.js';

test('my test', async ({ page, errorTracker }) => {
  await page.goto('/');
  await expect(page.locator('#root')).toBeVisible();
  // errorTracker fails test on uncaught exceptions
});
```

## Environment Variables

- `CI=1` - CI mode (more retries, JSON reporter)
- `FORCE_KILL=1` - Auto-kill processes on ports
- `NO_RELOAD=1` - Disable Flask reloader

---

**Full docs:** `tests/E2E_TESTING_GUIDE.md`
