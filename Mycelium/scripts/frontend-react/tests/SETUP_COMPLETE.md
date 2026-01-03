# Playwright E2E Testing Setup - Complete ✅

## What Was Built

A comprehensive end-to-end testing suite using Playwright that tests the integration between:
- **Flask Backend** (`run_backend.py` on port 9002)
- **React Frontend** (Vite dev server on port 5173)

## Key Features

### 🎯 Automatic Error Detection

The tests automatically **fail** if:
1. **Uncaught exceptions** occur in the browser (`pageerror`)
2. **Console.error()** is called (frontend errors)
3. **Page errors** happen during navigation

This is the killer feature that catches "works locally" issues.

### 🚀 Real Server Integration

- Both servers start automatically before tests run
- Tests run against real APIs, not mocks
- Catches CORS, routing, bundling, and config issues
- Realistic environment = fewer surprises in production

### 📊 Comprehensive Test Coverage

**Test Suites Created:**

1. **server-integration.spec.js** - Backend/frontend communication
   - Backend API responds
   - Frontend loads without errors
   - No CORS issues
   - Static assets load correctly

2. **routing.spec.js** - Navigation and deep linking
   - Client-side routing works
   - Deep links work (e.g., `/PCs/Mahogany`)
   - Browser back/forward buttons
   - 404 handling

3. **file-explorer.spec.js** - File system integration
   - File tree renders
   - Folders expand/collapse
   - Files load content from backend
   - Error handling for missing files

4. **character-sheet.spec.js** - Character data
   - Character sheets load
   - Stats display correctly
   - Switching between characters
   - JSON data loading

5. **dice-roller.spec.js** - Game mechanics
   - Dice roller UI renders
   - Can roll dice
   - Multiple rolls work
   - Results are valid

6. **gm-mode.spec.js** - GM features
   - GM mode can be accessed
   - Shows additional controls
   - Initiative tracker
   - NPC file access

7. **error-handling.spec.js** - Edge cases
   - Network failures handled gracefully
   - Malformed API responses
   - 500 errors don't crash app
   - Rapid navigation works
   - Page reload during API calls

8. **example-patterns.spec.js** - Documentation/examples
   - Shows all testing patterns
   - Best practices
   - How to use fixtures

## Files Created

```
Mycelium/scripts/frontend-react/
├── playwright.config.js           # Main configuration
├── package.json                   # Updated with test scripts
├── .gitignore                     # Ignore test results
└── tests/
    ├── E2E_TESTING_GUIDE.md      # Comprehensive documentation
    ├── QUICK_START.md            # Quick reference
    └── e2e/
        ├── fixtures.js           # Error tracking utilities
        ├── server-integration.spec.js
        ├── routing.spec.js
        ├── file-explorer.spec.js
        ├── character-sheet.spec.js
        ├── dice-roller.spec.js
        ├── gm-mode.spec.js
        ├── error-handling.spec.js
        └── example-patterns.spec.js
```

## How to Use

### First Time Setup

```bash
cd Mycelium/scripts/frontend-react
npm install
npx playwright install
```

### Running Tests

```bash
# Run all tests (headless)
npm test

# Run with browser visible (best for debugging)
npm run test:headed

# Interactive UI mode (best for development)
npm run test:ui

# Debug mode (step through tests)
npm run test:debug

# View test report
npm run test:report
```

### Development Workflow

1. **Write code** in your feature
2. **Run tests**: `npm run test:ui` (interactive mode)
3. **Fix any failures** - tests will tell you exactly what broke
4. **Commit** - tests are your safety net

### What Gets Tested

Every test automatically checks:
- ✅ No uncaught JavaScript exceptions
- ✅ No console.error() calls (that indicate bugs)
- ✅ API calls succeed (or fail gracefully)
- ✅ UI renders correctly
- ✅ Navigation works
- ✅ Error states are handled

## Configuration Highlights

### playwright.config.js

- **Servers start automatically** - No manual setup needed
- **Error tracking enabled** - Fails on uncaught exceptions
- **Screenshots on failure** - Saved to `test-results/`
- **Videos on failure** - See what went wrong
- **Traces on retry** - Detailed debugging info
- **CI-friendly** - Retries, JSON output, headless mode

### fixtures.js

Custom Playwright fixtures:
- **errorTracker** - Monitors console errors, page errors, failed requests
- **Helper functions** - Wait for backend, wait for frontend
- **Automatic assertions** - Fails test if uncaught exceptions occur

## Why This Matters

### Before Playwright E2E:
❌ CORS issues discovered in production  
❌ Routes work locally but break in build  
❌ Frontend crashes not caught by unit tests  
❌ "It works on my machine" syndrome  
❌ Integration bugs slip through  

### After Playwright E2E:
✅ Integration issues caught immediately  
✅ Real user flows tested end-to-end  
✅ Frontend errors fail tests automatically  
✅ CORS, routing, bundling tested  
✅ Confidence in deployments  

## Testing Philosophy

These are **integration tests**, not unit tests:
- Test **user flows**, not implementation
- Test **real servers**, not mocks
- Test **error states**, not just happy paths
- **Fail fast** on uncaught errors
- **Provide context** with screenshots and traces

## Examples

### Test that catches uncaught exceptions:

```javascript
test('loads without errors', async ({ page, errorTracker }) => {
  await page.goto('/');
  // If there's ANY uncaught exception, test fails automatically
  await expect(page.locator('#root')).toBeVisible();
});
```

### Test that checks API integration:

```javascript
test('backend responds', async ({ page, errorTracker }) => {
  const response = await page.request.get('http://localhost:9002/api/files');
  expect(response.ok()).toBeTruthy();
});
```

### Test that verifies no CORS issues:

```javascript
test('no CORS errors', async ({ page, errorTracker }) => {
  await page.goto('/');
  
  const corsErrors = errorTracker.consoleErrors.filter(err => 
    err.text.toLowerCase().includes('cors')
  );
  
  expect(corsErrors.length).toBe(0);
});
```

## Next Steps

### Recommended:

1. **Install browsers**: `npx playwright install`
2. **Run tests**: `npm run test:ui` (interactive mode is great!)
3. **Fix any failures** - They'll tell you what's broken
4. **Add tests for new features** - Use `example-patterns.spec.js` as template
5. **Run before commits** - Catch issues early

### Optional Enhancements:

- Add visual regression testing (screenshots)
- Add performance testing (lighthouse)
- Add accessibility testing (axe)
- Add API contract testing
- Set up CI/CD integration (GitHub Actions)

## Resources

- **Quick Start**: `tests/QUICK_START.md`
- **Full Guide**: `tests/E2E_TESTING_GUIDE.md`
- **Examples**: `tests/e2e/example-patterns.spec.js`
- **Playwright Docs**: https://playwright.dev/

## Success Metrics

After running the tests, you'll know:
- ✅ Backend starts successfully
- ✅ Frontend starts successfully
- ✅ They can communicate (no CORS issues)
- ✅ Routes work (including deep links)
- ✅ File explorer works
- ✅ Character sheets load
- ✅ Dice roller works
- ✅ GM mode works
- ✅ Error handling works
- ✅ No uncaught exceptions
- ✅ No console errors (or they're expected)

## Troubleshooting

**Tests won't run?**
```bash
npx playwright install  # Install browsers
```

**Port already in use?**
```bash
FORCE_KILL=1 npm test  # Auto-kill existing processes
```

**Tests failing?**
```bash
npm run test:headed  # See what's happening
npm run test:debug   # Step through tests
```

**Need help?**
- Check `test-results/` for screenshots
- Check `playwright-report/` for HTML report
- Read `tests/E2E_TESTING_GUIDE.md`

---

## Summary

You now have a **professional-grade E2E testing setup** that:

1. **Catches bugs automatically** - Uncaught exceptions fail tests
2. **Tests real integration** - Backend + Frontend working together
3. **Tests user flows** - Navigation, file loading, character sheets, etc.
4. **Provides debugging tools** - Screenshots, videos, traces
5. **Documents itself** - Clear test names and comprehensive guides
6. **CI-ready** - Can run in GitHub Actions or any CI system

**Run your first test:**
```bash
cd Mycelium/scripts/frontend-react
npm run test:ui
```

**Happy Testing! 🎭**
