# Multi-Client Stability Test Suite - Implementation Summary

## Overview

A comprehensive test suite has been created to ensure your TTRPG system can handle up to 10 concurrent clients over local WiFi without crashes, data loss, or synchronization issues.

## What Was Created

### 1. New Test Files

#### `tests/e2e/stability-10-clients.spec.js` (10 tests, ~600 lines)
Core stability testing with 10 simultaneous clients:
- ✓ Simultaneous application loading
- ✓ Initiative Tracker synchronization
- ✓ Simultaneous turn advances
- ✓ Character Sheet HP synchronization
- ✓ Server responsiveness under load
- ✓ Polling behavior with 10 clients
- ✓ Rapid file access
- ✓ Consistency after 50 rapid updates
- ✓ Active session tracking
- ✓ Client disconnect/reconnect handling

#### `tests/e2e/race-conditions.spec.js` (8 tests, ~550 lines)
Edge case testing for concurrent operations:
- ✓ No duplicate characters from simultaneous adds
- ✓ No lost HP updates from concurrent modifications
- ✓ Turn order maintained after simultaneous reordering
- ✓ Concurrent character removal without errors
- ✓ No data corruption during rapid read-write cycles
- ✓ Network interruption recovery
- ✓ Staggered client join consistency
- ✓ File save conflict resolution

### 2. Documentation

#### `tests/STABILITY_TESTING_GUIDE.md`
Comprehensive guide covering:
- Test file descriptions and purposes
- How to run tests
- Synchronization expectations
- Success criteria and failure indicators
- Troubleshooting common issues
- Performance benchmarks
- CI/CD integration examples
- Monitoring in production

#### `tests/QUICK_REFERENCE_STABILITY.md`
Quick reference card with:
- Common commands
- Test script cheat sheet
- Expected results
- Debugging tips
- Performance benchmarks
- Success checklist

### 3. Test Runner

#### `tests/run-stability-tests.sh`
Automated test runner that:
- Checks prerequisites (Python, Node, Playwright)
- Cleans up existing server processes
- Starts backend and frontend servers
- Runs tests with proper configuration
- Generates test reports
- Handles cleanup on exit
- Provides colored output and progress

### 4. Package.json Updates

Added convenient npm scripts:
```json
"test:stability": "Run all stability tests",
"test:stability:headed": "Run with visible browser",
"test:stability:ui": "Interactive UI mode",
"test:10-clients": "Run 10-client tests only",
"test:race": "Run race condition tests only",
"test:sync": "Run all sync tests",
"test:all-multi": "Run all multi-client tests"
```

## Test Coverage

### Components Tested

1. **Initiative Tracker**
   - Turn advancement synchronization
   - Character addition/removal
   - Initiative reordering
   - HP tracking
   - Round counting

2. **Character Sheet**
   - HP value synchronization
   - Stat updates across clients
   - Concurrent edits handling

3. **Server/API**
   - Response times under load
   - Active session tracking
   - File read/write concurrency
   - Error handling

4. **General System**
   - File access patterns
   - Polling behavior
   - Network interruption recovery
   - Client connect/disconnect

### Scenarios Covered

- ✅ 10 clients loading simultaneously
- ✅ 10 clients polling continuously
- ✅ Simultaneous updates from multiple clients
- ✅ Rapid sequential updates (50+ operations)
- ✅ Concurrent reads during writes
- ✅ Network interruptions
- ✅ Client disconnect and reconnect
- ✅ Staggered client connections
- ✅ File save conflicts
- ✅ Race conditions (duplicate data, lost updates)

## How to Use

### Quick Start

```bash
# Navigate to frontend directory
cd Mycelium/scripts/frontend-react

# Run all stability tests
npm run test:stability

# Or use the comprehensive runner
./tests/run-stability-tests.sh
```

### Test Modes

```bash
# Run specific test suites
npm run test:10-clients        # 10-client stability
npm run test:race              # Race conditions
npm run test:sync              # All sync tests

# Run with browser visible (for debugging)
npm run test:stability:headed

# Interactive UI mode
npm run test:stability:ui
```

### View Results

```bash
# HTML report
npm run test:report

# Server activity logs
open http://localhost:9002/api/log_viewer

# Active sessions
curl http://localhost:9002/api/active_sessions
```

## Expected Performance

### Synchronization Times

| Component | Expected | Acceptable | Critical |
|-----------|----------|------------|----------|
| Initiative Tracker | < 2s | < 5s | > 10s |
| Character Sheet | < 5s | < 10s | > 15s |
| Battlemap | < 2s | < 3s | > 5s |

### Server Performance

| Metric | Target | Acceptable | Critical |
|--------|--------|------------|----------|
| Load 10 clients | < 10s | < 30s | > 60s |
| API response | < 1s | < 5s | > 10s |
| Memory usage | < 500MB | < 1GB | > 2GB |

### Test Execution Time

- **10-client tests**: ~15 minutes
- **Race condition tests**: ~10 minutes
- **Full multi-client suite**: ~40 minutes

## Known Limitations

### File-Based Sync
- Uses file system for state persistence
- Last-write-wins conflict resolution
- 1-2 second polling intervals
- Eventual consistency model

### Recommended for Production
1. Consider WebSocket implementation for real-time updates
2. Use database backend for better concurrency
3. Implement optimistic UI updates
4. Add conflict resolution UI
5. Consider Redis for session state

## Integration with Existing Tests

The new tests complement existing test files:

- `sync-basic.spec.js` - Basic 2-client sync (existing)
- `scalability-sync.spec.js` - 3-client sync validation (existing)
- `speed-multiclient.spec.js` - 2-5 client performance (existing)
- **`stability-10-clients.spec.js`** - 10-client stability (NEW)
- **`race-conditions.spec.js`** - Edge cases (NEW)

All tests use the same fixtures and configuration, ensuring consistency.

## Monitoring in Production

### Server Activity Logging

The backend (`run_backend.py`) already includes:
- Client activity tracking
- Request counting per session
- IP-based session identification
- Timestamped logs

Access via:
```bash
# Web interface
open http://localhost:9002/api/log_viewer

# API endpoint
curl http://localhost:9002/api/active_sessions

# Log files
tail -f logs/client_activity_*.log
```

## Next Steps

### Immediate Actions
1. Run the test suite: `npm run test:stability`
2. Review the HTML report: `npm run test:report`
3. Check for any failures and debug
4. Verify sync times meet expectations

### Before Production
1. Run full test suite multiple times
2. Test on actual WiFi network (not localhost)
3. Monitor resource usage during tests
4. Verify with actual game session (manual testing)
5. Set up continuous monitoring

### Future Enhancements
1. Add WebSocket support for real-time updates
2. Implement database backend for better concurrency
3. Add load testing (> 10 clients)
4. Implement automatic reconnection on network loss
5. Add conflict resolution UI
6. Set up automated CI/CD testing

## Troubleshooting

### Common Issues

**Tests fail with timeout:**
```bash
# Ensure servers are running
curl http://localhost:9002/api/active_sessions
curl http://localhost:5173

# Increase timeouts in playwright.config.js
```

**Port conflicts:**
```bash
# Kill existing processes
lsof -ti:9002 | xargs kill -9
lsof -ti:5173 | xargs kill -9

# Or use the test runner which handles this
./tests/run-stability-tests.sh
```

**Sync tests intermittently fail:**
- File system latency may vary
- Increase wait times in tests
- Run with `--workers=1` (serial execution)
- Check disk performance

### Debug Mode

```bash
# Run single test in debug mode
npx playwright test --debug -g "should handle 10 clients loading"

# Show browser UI
npm run test:stability:headed

# View execution trace
npx playwright show-trace test-results/.../trace.zip
```

## Files Modified/Created

```
Mycelium/scripts/frontend-react/
├── tests/
│   ├── e2e/
│   │   ├── stability-10-clients.spec.js    (NEW - 10 client tests)
│   │   ├── race-conditions.spec.js         (NEW - race condition tests)
│   │   ├── sync-basic.spec.js              (existing)
│   │   ├── scalability-sync.spec.js        (existing)
│   │   └── speed-multiclient.spec.js       (existing)
│   ├── run-stability-tests.sh              (NEW - test runner)
│   ├── STABILITY_TESTING_GUIDE.md          (NEW - full guide)
│   └── QUICK_REFERENCE_STABILITY.md        (NEW - quick ref)
└── package.json                             (UPDATED - new scripts)
```

## Success Metrics

The system is considered stable when:
- ✅ All 10 clients load within 30 seconds
- ✅ Data syncs across all clients within 5 seconds
- ✅ No uncaught exceptions or crashes
- ✅ Server remains responsive (< 5s avg)
- ✅ No data corruption or lost updates
- ✅ Graceful handling of disconnects
- ✅ Consistent state across all clients

## Conclusion

You now have a comprehensive test suite that validates your TTRPG system can handle 10 concurrent clients reliably. The tests cover:

- ✅ Core functionality (Initiative Tracker, Character Sheets)
- ✅ Synchronization and data consistency
- ✅ Race conditions and edge cases
- ✅ Server performance and responsiveness
- ✅ Error handling and recovery

Run `npm run test:stability` to validate your system is ready for multi-player use over local WiFi!

---

**Documentation**: See `tests/STABILITY_TESTING_GUIDE.md` for comprehensive details.  
**Quick Reference**: See `tests/QUICK_REFERENCE_STABILITY.md` for common commands.  
**Test Runner**: Use `./tests/run-stability-tests.sh` for automated execution.
