# Multi-Client Stability Testing - Quick Reference

## 🚀 Quick Start

```bash
# Run all stability tests (recommended first run)
npm run test:stability

# Run with visual browser (for debugging)
npm run test:stability:headed

# Run with Playwright UI (interactive)
npm run test:stability:ui
```

## 📋 Test Scripts

### Stability Tests
```bash
npm run test:stability          # Run 10-client + race condition tests
npm run test:10-clients          # Only 10-client stability tests
npm run test:race                # Only race condition tests
```

### Sync Tests
```bash
npm run test:sync                # All synchronization tests
npm run test:all-multi           # All multi-client tests (comprehensive)
```

### Utility Commands
```bash
npm run test:report              # View HTML test report
npm run test:ui                  # Interactive test mode
npm run test:debug               # Debug specific test
```

## 🎯 What Each Test File Does

| File | Purpose | Clients | Time |
|------|---------|---------|------|
| `stability-10-clients.spec.js` | Core stability with 10 clients | 10 | ~15 min |
| `race-conditions.spec.js` | Edge cases & conflicts | 2-5 | ~10 min |
| `sync-basic.spec.js` | Basic 2-client sync | 2 | ~2 min |
| `scalability-sync.spec.js` | Real-time sync validation | 3 | ~3 min |
| `speed-multiclient.spec.js` | Performance benchmarks | 2-5 | ~8 min |

## 🔍 What Gets Tested

### ✅ Stability Tests
- [x] 10 clients loading simultaneously
- [x] Initiative Tracker sync across all clients
- [x] Simultaneous turn advances
- [x] Character HP synchronization
- [x] Server responsiveness under load
- [x] Polling behavior with multiple clients
- [x] Rapid file access
- [x] 50+ rapid updates consistency
- [x] Active session tracking
- [x] Client disconnect/reconnect

### ✅ Race Condition Tests
- [x] No duplicate characters (simultaneous adds)
- [x] No lost HP updates (concurrent edits)
- [x] Turn order consistency (simultaneous reorders)
- [x] Concurrent character removal
- [x] No data corruption (rapid read-write)
- [x] Network interruption recovery
- [x] Staggered client joins
- [x] File save conflict resolution

## 🎨 Running Specific Tests

```bash
# Run one test by name
npx playwright test -g "should handle 10 clients loading"

# Run one test file
npx playwright test tests/e2e/stability-10-clients.spec.js

# Run with specific browser
npx playwright test --project=chromium

# Run in debug mode
npx playwright test --debug tests/e2e/stability-10-clients.spec.js
```

## 📊 Expected Results

### ✅ Pass Criteria
- All clients sync within **2-5 seconds**
- No data loss or corruption
- Server response time < **5 seconds** average
- No uncaught exceptions
- Graceful handling of disconnects

### ❌ Failure Indicators
- Sync times > 10 seconds
- Data inconsistency across clients
- Server unresponsive (> 10s)
- Page crashes or errors
- Lost updates or duplicates

## 🐛 Debugging Failed Tests

### View Test Report
```bash
npm run test:report
```

### Run in Headed Mode
```bash
npm run test:stability:headed
```

### Check Logs
```bash
# Server activity log
open http://localhost:9002/api/log_viewer

# Active sessions
curl http://localhost:9002/api/active_sessions

# Test results
cat test-results/test-results.json
```

### Common Issues

**Tests timeout:**
```bash
# Check servers are running
curl http://localhost:9002/api/active_sessions
curl http://localhost:5173
```

**Port conflicts:**
```bash
# Kill processes on ports
lsof -ti:9002 | xargs kill -9
lsof -ti:5173 | xargs kill -9
```

**Cache issues:**
```bash
# Clear browser cache and restart tests
rm -rf test-results/
npm run test:stability
```

## 📈 Performance Benchmarks

| Operation | Expected | Acceptable | Critical |
|-----------|----------|------------|----------|
| Load 10 clients | < 10s | < 30s | > 60s |
| Initiative sync | < 2s | < 5s | > 10s |
| HP update sync | < 5s | < 10s | > 15s |
| Server response | < 1s | < 5s | > 10s |

## 🛠️ Advanced Usage

### Custom Test Runner
```bash
# Use the comprehensive test runner
./tests/run-stability-tests.sh --stability --headed

# Options:
#   --stability  Run stability tests only
#   --race       Run race condition tests only
#   --sync       Run sync tests only
#   --headed     Show browser UI
#   --ui         Interactive UI mode
#   --debug      Debug mode
```

### Environment Variables
```bash
# Set custom base URL
export VITE_API_BASE_URL=http://192.168.1.100:5173
npm run test:stability

# Enable CI mode (headless)
export CI=1
npm test

# Force kill existing servers
export FORCE_KILL=1
```

### Parallel vs Serial Execution
```bash
# Serial (safer, recommended for stability tests)
npx playwright test --workers=1

# Parallel (faster, but may have port conflicts)
npx playwright test --workers=4
```

## 📚 Documentation

- **Full Guide**: `tests/STABILITY_TESTING_GUIDE.md`
- **Playwright Docs**: https://playwright.dev
- **Test Fixtures**: `tests/e2e/fixtures.js`
- **Config**: `playwright.config.js`

## 🔧 Maintenance

### Update Tests
```bash
# Add new test
vim tests/e2e/stability-10-clients.spec.js

# Run to verify
npm run test:10-clients
```

### Update Snapshots
```bash
npx playwright test --update-snapshots
```

### Clean Test Results
```bash
rm -rf test-results/ playwright-report/
```

## ⚡ Pro Tips

1. **Run serially first**: Use `--workers=1` to avoid interference
2. **Check logs**: Use `/api/log_viewer` to see real-time activity
3. **Start small**: Test with 2-3 clients before 10
4. **Monitor resources**: Watch CPU/memory during tests
5. **Use UI mode**: `--ui` flag for interactive debugging
6. **Check traces**: Playwright captures full execution traces
7. **Increase timeouts**: Adjust `timeout` in config for slow machines

## 🎯 Success Checklist

Before production deployment:

- [ ] All 10-client tests pass
- [ ] All race condition tests pass
- [ ] Average sync time < 3 seconds
- [ ] Server remains responsive under load
- [ ] No memory leaks after extended use
- [ ] Graceful client disconnect handling
- [ ] Consistent state across all clients
- [ ] No data corruption or loss

## 📞 Getting Help

1. Check `STABILITY_TESTING_GUIDE.md` for detailed info
2. View test report: `npm run test:report`
3. Check server logs: `http://localhost:9002/api/log_viewer`
4. Review test output in `test-results/`
5. Run with `--debug` flag for step-by-step execution

---

**Last Updated**: January 2026  
**Tested with**: 10 concurrent clients, ~40 min full suite
