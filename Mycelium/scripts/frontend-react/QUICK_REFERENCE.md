# E2E Testing - Quick Reference Card

## 🚀 Quick Commands

```bash
# Check if ready to test
npm run check-env

# Run tests with automatic error analysis (recommended)
npm run test:analyze

# Interactive mode (best for development)
npm run test:ui

# Standard tests (no analysis)
npm test
```

## 📊 Understanding Test Output

### Error Categories

| Icon | Category | What It Means | Action |
|------|----------|---------------|--------|
| 🔴 | Frontend Errors | React/JS crashes | Check console.error, component code |
| 🟣 | Backend/API | Server issues | Check Flask logs, CORS, endpoints |
| 🟡 | Test Code | Selectors, timeouts | Update test selectors, add waits |
| 🔵 | Infrastructure | Ports, servers | Kill processes, check ports |

### Example Output

```
Summary:
  Total Tests: 15
  ✓ Passed: 12
  ✗ Failed: 3

Error Breakdown:

▸ Frontend Errors (2):
  • TypeError: Cannot read property 'name' of undefined

▸ Test Code Issues (1):
  • Timeout waiting for selector

Recommendations:
  ⚛️  Frontend errors → Check browser console
  🧪 Test issues → Update selectors or timeouts
```

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `npm not found` | Run: `export PATH="/usr/local/bin:$PATH"` |
| Port in use | Run: `lsof -ti:9002,5173 \| xargs kill -9` |
| Browsers not installed | Run: `npx playwright install` |
| Permission denied | Run: `chmod +x *.sh` |

## 📁 Key Files

```
frontend-react/
├── check-env.sh              - Environment validator
├── test-with-analysis.sh     - Test runner + analyzer
├── analyze-test-results.js   - Error categorizer
├── package.json              - npm commands
└── tests/e2e/*.spec.js       - Test suites
```

## 🎯 Common Workflows

### First Time Setup
```bash
cd Mycelium/scripts/frontend-react
npm run check-env
npm install                    # if needed
npx playwright install         # if needed
```

### Development
```bash
npm run test:ui                # Interactive testing
# Make changes to tests
# Re-run specific tests in UI
```

### Before Commit
```bash
npm run test:analyze           # Check all tests pass
# Fix any failures
# Commit
```

### Debugging Failures
```bash
npm run test:analyze:headed    # See browser
# or
npm run test:debug             # Step through
# or
npm run test:report            # View HTML report
```

## 🔍 Advanced

```bash
# Run specific test file
npx playwright test tests/e2e/routing.spec.js

# Run tests matching pattern
npx playwright test --grep "character"

# Save analysis output
npm run test:analyze 2>&1 | tee test-results-$(date +%Y%m%d).txt

# Kill stuck processes
FORCE_KILL=1 npm run test:analyze
```

## 📖 Documentation

- `TESTING_IMPROVEMENTS.md` - What was improved
- `TEST_ANALYSIS.md` - Analysis tool guide
- `e2e_testing_manual.md` - Complete manual
- `tests/E2E_TESTING_GUIDE.md` - Comprehensive guide

## ⚡ Pro Tips

1. **Always check env first**: `npm run check-env`
2. **Use analysis mode**: Get immediate categorized errors
3. **Interactive for dev**: `npm run test:ui` for rapid iteration
4. **Watch the colors**: Quick visual scan of error types
5. **Read recommendations**: Specific actions for each error type
6. **Check screenshots**: `test-results/` folder after failures

## 🎨 Color Guide

- 🟢 Green `✓` - Passed/Success
- 🔴 Red `✗` - Failed/Error
- 🟡 Yellow `⚠` - Warning/Needs attention
- 🔵 Blue - Info/Headers

---

**Need help?** Run `npm run check-env` to diagnose issues or read the full documentation files.
