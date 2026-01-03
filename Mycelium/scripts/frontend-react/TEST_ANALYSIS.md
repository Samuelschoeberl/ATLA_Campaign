# Test Analysis Tools

Automated error analysis and categorization for Playwright E2E tests.

## Quick Start

```bash
# Run tests with automatic analysis (recommended)
npm run test:analyze

# Run with visible browser + analysis
npm run test:analyze:headed

# Interactive UI mode (no analysis needed)
npm run test:ui
```

## Features

### 🔍 Automatic Error Categorization

Errors are automatically categorized into:

- **Frontend Errors** - React, JavaScript, browser exceptions
- **Backend/API Errors** - Server, API endpoints, CORS
- **Test Code Issues** - Selectors, timeouts, assertions  
- **Infrastructure** - Port conflicts, server startup

### 💡 Smart Recommendations

Based on detected error types, you get specific recommendations:

- Port conflicts → Use `FORCE_KILL=1 npm test`
- Backend issues → Check Flask logs and CORS
- Frontend errors → Review console output
- Test issues → Update selectors or timeouts

### 📊 Detailed Reports

- Test summary (passed/failed/skipped)
- Error frequency and examples
- Next debugging steps
- Links to detailed reports

## Tools

### 1. test-with-analysis.sh

Bash wrapper that:
- Sets up correct PATH for Node.js
- Runs tests and captures output
- Analyzes results automatically
- Provides color-coded output

**Usage:**
```bash
./test-with-analysis.sh              # Default analysis
./test-with-analysis.sh --headed     # With visible browser
./test-with-analysis.sh --ui         # Interactive UI
./test-with-analysis.sh --debug      # Debug mode
```

### 2. analyze-test-results.js

Node.js analyzer that:
- Parses Playwright test output
- Categorizes errors by pattern matching
- Generates formatted reports
- Provides actionable recommendations

**Usage:**
```bash
# From pipe
npm test 2>&1 | node analyze-test-results.js

# From file
npm test 2>&1 | tee output.txt
node analyze-test-results.js --file output.txt

# Help
node analyze-test-results.js --help
```

### 3. extract-test-results.js (Legacy)

Original result extractor (still available):
```bash
npm run test:extract              # All results
npm run test:extract:failed       # Failed only
```

## Error Patterns

The analyzer recognizes these patterns:

### Frontend Errors
- `Uncaught.*Error`
- `React.*error`
- `console.error`
- `Cannot read property`
- `undefined is not`
- `TypeError.*component`
- `pageerror`

### Backend/API Errors
- `api/.* failed`
- `fetch.*/api/`
- `500 Internal Server Error`
- `CORS`
- `Failed to fetch`
- `ERR_CONNECTION_REFUSED`

### Test Code Issues
- `locator.*not found`
- `Timeout.*waiting for`
- `selector.*not found`
- `expect.*toBeVisible`
- `waitFor.*timeout`

### Infrastructure Issues
- `EADDRINUSE`
- `port.*already in use`
- `Server.*not ready`
- `Health check.*failed`
- `webServer.*failed`

## Troubleshooting

### PATH Issues

If npm/node are not found:

```bash
# Check current PATH
echo $PATH

# Manually set PATH
export PATH="/usr/local/bin:$PATH"

# Add to ~/.bash_profile or ~/.zshrc
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.bash_profile
```

### Permission Issues

```bash
chmod +x test-with-analysis.sh
```

### Port Conflicts

```bash
# Kill processes on test ports
lsof -ti:9002,5173 | xargs kill -9

# Or use FORCE_KILL
FORCE_KILL=1 npm run test:analyze
```

## Integration with CI/CD

```yaml
# .github/workflows/test.yml
- name: Run E2E tests with analysis
  working-directory: Mycelium/scripts/frontend-react
  run: |
    npm test 2>&1 | tee test-output.txt
    node analyze-test-results.js --file test-output.txt

- name: Upload analysis
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: test-analysis
    path: |
      Mycelium/scripts/frontend-react/test-output.txt
      Mycelium/scripts/frontend-react/test-results/
```

## Customization

### Adding New Error Patterns

Edit `analyze-test-results.js`:

```javascript
const errorPatterns = {
  myCategory: {
    name: 'My Custom Errors',
    color: colors.red,
    patterns: [
      /my-pattern/i,
      /another-pattern/i,
    ],
  },
  // ... existing categories
};
```

### Custom Recommendations

Add to the recommendations section:

```javascript
if (stats.errors.myCategory.length > 0) {
  console.log(`  🔧 Custom category detected. Try:`);
  console.log(`     ${colors.gray}• Your recommendation here${colors.reset}`);
}
```

## Best Practices

1. **Always use analysis mode during development**
   ```bash
   npm run test:analyze
   ```

2. **Use UI mode for debugging specific tests**
   ```bash
   npm run test:ui
   ```

3. **Review categorized errors systematically**
   - Fix infrastructure issues first
   - Then backend problems
   - Then frontend errors
   - Finally test code improvements

4. **Save analysis output for tracking**
   ```bash
   npm run test:analyze 2>&1 | tee "analysis-$(date +%Y%m%d-%H%M%S).txt"
   ```

5. **Check trends over time**
   - Are certain error categories increasing?
   - Are fixes reducing specific error types?
   - Are new tests introducing new error patterns?

## Future Enhancements

Planned features:
- [ ] JSON report parsing
- [ ] Historical error tracking
- [ ] Error frequency graphs
- [ ] Flaky test detection
- [ ] Performance regression alerts
- [ ] AI-powered error suggestions

## Support

For issues or questions:
1. Check the main E2E testing manual
2. Review test output and screenshots
3. Run with `--debug` mode for step-through
4. Check the Playwright documentation

## Files

```
frontend-react/
├── test-with-analysis.sh        # Bash test runner
├── analyze-test-results.js      # Error analyzer
├── extract-test-results.js      # Legacy extractor
├── package.json                 # npm scripts
└── tests/
    ├── e2e/                     # Test suites
    └── E2E_TESTING_GUIDE.md     # Full guide
```
