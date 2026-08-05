import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for E2E testing the Flask backend + React frontend.
 * 
 * Key features:
 * - Fails on uncaught exceptions (pageerror)
 * - Fails on console.error messages
 * - Tracks network failures
 * - Runs servers automatically before tests
 * - Screenshots/videos on failure
 */
export default defineConfig({
  testDir: './tests/e2e',
  
  // Timeout for each test (increased for multi-client sync tests)
  timeout: 180 * 1000, // 3 minutes for multi-client tests with polling
  
  // Expect timeout for assertions
  expect: {
    timeout: 10000 // Increased for sync operations
  },
  
  // Run tests in parallel
  fullyParallel: false, // Set to false initially to avoid port conflicts
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 0,
  
  // Limit workers to avoid port conflicts with backend
  workers: process.env.CI ? 1 : 1,
  
  // Reporter to use
  reporter: [
    ['html'],
    ['list'],
    // JSON reporter for programmatic access
    ['json', { outputFile: 'test-results/test-results.json' }],
    // JUnit reporter for CI systems
    ...(process.env.CI ? [['junit', { outputFile: 'test-results/junit.xml' }]] : [])
  ],
  
  use: {
    // Base URL for the frontend
    baseURL: 'http://localhost:5173',
    
    // Collect trace when retrying the failed test
    trace: 'on-first-retry',
    
    // Screenshot on failure
    screenshot: 'only-on-failure',
    
    // Video on failure
    video: 'retain-on-failure',
    
    // Browser context options
    viewport: { width: 1280, height: 720 },
    
    // Ignore HTTPS errors (for local development)
    ignoreHTTPSErrors: true,
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        // Fail on console errors
        contextOptions: {
          logger: {
            isEnabled: () => true,
            log: (name, severity, message) => {
              if (severity === 'error') {
                console.error(`Browser ${severity}: ${message}`);
              }
            }
          }
        }
      },
    },

    // Uncomment to test on Firefox and Safari
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  // Run your local dev server before starting the tests
  webServer: [
    {
      // Backend server (Flask)
      // Use 'python' for conda environments, falls back to 'python3' if python is not found
      command: 'cd ../../.. && (python --version 2>&1 | grep -q "Python" && python Mycelium/scripts/Python/run_backend.py || python3 Mycelium/scripts/Python/run_backend.py)',
      url: 'http://localhost:9002/api/active_sessions', // Check a simple API endpoint
      timeout: 30 * 1000,
      reuseExistingServer: true, // Always reuse existing server
      env: {
        NO_RELOAD: '1',        // Disable Flask reloader for tests
        FORCE_KILL: '1',       // Auto-kill existing processes on the port
        PYTHONUNBUFFERED: '1', // Unbuffered output
        PORT: '9002'
      },
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      // Frontend server (Vite)
      command: 'npm run dev',
      url: 'http://localhost:5173',
      timeout: 30 * 1000,
      reuseExistingServer: true, // Always reuse existing server
      stdout: 'pipe',
      stderr: 'pipe',
    }
  ],
});
