# Multi-Client Stability Test Suite

## Overview

This test suite ensures the TTRPG system can handle up to 10 concurrent clients over local WiFi without crashes, data loss, or synchronization issues.

## Test Files

### 1. `stability-10-clients.spec.js`
**Purpose**: Core stability testing with 10 simultaneous clients

**Tests**:
- ✓ Simultaneous application loading (10 clients)
- ✓ Initiative Tracker synchronization across 10 clients
- ✓ Simultaneous turn advances from multiple clients
- ✓ Character Sheet HP synchronization across 10 clients
- ✓ Server responsiveness under load
- ✓ Polling behavior with 10 active clients
- ✓ Rapid file access from multiple clients
- ✓ Consistency after 50 rapid updates
- ✓ Active session tracking
- ✓ Graceful client disconnect/reconnect

**Expected Results**:
- All clients should sync within 2-5 seconds (depending on polling interval)
- No data loss or corruption
- Server remains responsive (< 5s avg response time)
- No critical errors or crashes

### 2. `race-conditions.spec.js`
**Purpose**: Edge case testing for concurrent operations

**Tests**:
- ✓ No duplicate characters from simultaneous adds
- ✓ HP updates don't get lost with concurrent modifications
- ✓ Turn order maintained after simultaneous reordering
- ✓ Concurrent character removal without errors
- ✓ No data corruption during rapid read-write cycles
- ✓ Network interruption recovery
- ✓ Staggered client join consistency
- ✓ File save conflict resolution

**Expected Results**:
- Last-write-wins conflict resolution
- No data corruption or invalid states
- All clients converge to consistent state
- System handles edge cases gracefully

### 3. Existing Test Files

#### `speed-multiclient.spec.js`
- Multi-client sync speed benchmarks
- Initiative Tracker 2-3 client tests
- Battlemap Viewer sync tests
- Performance measurements

#### `scalability-sync.spec.js`
- Real-time battlemap updates
- Near real-time initiative sync
- Delayed character sheet sync

#### `sync-basic.spec.js`
- Basic 2-client synchronization
- File access without conflicts

## Running the Tests

### Quick Start

```bash
# Run all stability tests
npm run test:stability

# Run specific test file
npx playwright test tests/e2e/stability-10-clients.spec.js

# Run with UI mode for debugging
npx playwright test --ui tests/e2e/stability-10-clients.spec.js

# Run race condition tests only
npx playwright test tests/e2e/race-conditions.spec.js
```

### Full Test Suite

```bash
# Run all E2E tests
npm test

# Run with specific number of workers (reduce for less powerful machines)
npx playwright test --workers=1

# Generate HTML report
npx playwright show-report
```

### Debugging Failed Tests

```bash
# Run in debug mode with headed browser
npx playwright test --debug tests/e2e/stability-10-clients.spec.js

# Run specific test by name
npx playwright test -g "should handle 10 clients loading"

# Show trace for failed test
npx playwright show-trace test-results/.../trace.zip
```

## Test Configuration

### `playwright.config.js` Settings

```javascript
{
  timeout: 180000,        // 3 minutes per test
  expect: { timeout: 10000 },  // 10s for assertions
  workers: 1,             // Serial execution to avoid port conflicts
  retries: 0,             // No retries (for stability testing)
}
```

### Environment Variables

```bash
# Set base URL
export VITE_API_BASE_URL=http://localhost:5173

# Enable CI mode
export CI=1

# Disable cache
export NO_CACHE=1
```

## Synchronization Expectations

### Initiative Tracker
- **Polling Interval**: 1 second
- **Save Guard**: 500ms debounce
- **Expected Sync Time**: 1-2 seconds
- **Max Acceptable Latency**: 5 seconds

### Character Sheet
- **Polling Interval**: 2-5 seconds (configurable)
- **Save Debounce**: 1 second
- **Expected Sync Time**: 3-6 seconds
- **Max Acceptable Latency**: 10 seconds

### Battlemap Viewer
- **Polling Interval**: 1 second
- **Real-time Updates**: WebSocket (if enabled)
- **Expected Sync Time**: 1-2 seconds
- **Max Acceptable Latency**: 3 seconds

## Success Criteria

### ✅ System is Stable When:
1. All 10 clients can load simultaneously (< 30s)
2. Data syncs across all clients within acceptable latency
3. No uncaught exceptions or page errors
4. Server remains responsive under load (< 5s avg response)
5. No data corruption or lost updates
6. Graceful handling of client disconnect/reconnect
7. Consistent state across all clients after sync window

### ❌ System Needs Attention If:
1. Sync times exceed 10 seconds regularly
2. Data loss or corruption occurs
3. Clients see inconsistent states after sync
4. Server becomes unresponsive
5. Memory leaks or resource exhaustion
6. Frequent uncaught exceptions
7. Race conditions cause duplicate/invalid data

## Common Issues and Solutions

### Issue: Tests Timeout
**Cause**: Server not running or slow to start
**Solution**: 
```bash
# Ensure backend is running
cd Mycelium/scripts/Python
python run_backend.py

# Check server is accessible
curl http://localhost:9002/api/active_sessions
```

### Issue: "Element not found" errors
**Cause**: UI not fully loaded or cached state
**Solution**:
- Increase timeout values in test
- Add `waitForLoadState('networkidle')`
- Clear browser cache between runs

### Issue: Sync tests fail intermittently
**Cause**: Timing sensitivity or file system latency
**Solution**:
- Increase sync wait times
- Check file system performance
- Run tests serially with `workers: 1`

### Issue: Port already in use
**Cause**: Previous test run didn't cleanup
**Solution**:
```bash
# Kill processes on ports
lsof -ti:9002 | xargs kill -9
lsof -ti:5173 | xargs kill -9

# Or use environment variable
FORCE_KILL=1 python run_backend.py
```

## Performance Benchmarks

Based on test runs with 10 clients:

| Metric | Target | Acceptable | Critical |
|--------|--------|------------|----------|
| Initial Load | < 10s | < 30s | > 60s |
| Initiative Sync | < 2s | < 5s | > 10s |
| Character HP Sync | < 5s | < 10s | > 15s |
| Server Response | < 1s | < 5s | > 10s |
| Memory Usage | < 500MB | < 1GB | > 2GB |

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Multi-Client Stability Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - uses: actions/setup-node@v2
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          npm ci
      
      - name: Run stability tests
        run: |
          npm run test:stability
        env:
          CI: true
          HEADLESS: true
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: test-results/
```

## Monitoring in Production

### Client Activity Logs

View real-time client activity:
```bash
# Web interface
open http://localhost:9002/api/log_viewer

# API endpoint
curl http://localhost:9002/api/active_sessions
```

### Active Session Tracking

The backend tracks:
- Client IP addresses
- Request counts per session
- First/last seen timestamps
- User agent information

Access via: `http://localhost:9002/api/active_sessions`

## Next Steps

### Recommended Improvements
1. **Add WebSocket support** for real-time updates (reduce latency)
2. **Implement optimistic UI updates** (better perceived performance)
3. **Add conflict resolution UI** (show when data conflicts occur)
4. **Database backend** (replace file-based storage for better concurrency)
5. **Session management** (track user identity, not just IP)
6. **Load balancing** (for > 10 clients)
7. **Rate limiting** (prevent abuse)

### Performance Optimizations
1. Implement differential sync (only send changes)
2. Add connection pooling
3. Enable HTTP/2 or HTTP/3
4. Use Redis for session state
5. Implement caching layers
6. Add request batching

## Troubleshooting

### Debug Mode

Run tests with extensive logging:
```bash
DEBUG=pw:api npx playwright test tests/e2e/stability-10-clients.spec.js
```

### Visual Testing

Run with browser UI visible:
```bash
npx playwright test --headed --workers=1 tests/e2e/stability-10-clients.spec.js
```

### Trace Viewer

Capture and view execution traces:
```bash
# Run with trace
npx playwright test --trace on

# View trace
npx playwright show-trace test-results/.../trace.zip
```

## Contact

For issues or questions about the test suite:
- Check test output logs in `test-results/`
- Review Playwright HTML report: `npx playwright show-report`
- Check server logs in `logs/client_activity_*.log`
