import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for stability tests run by run-stability-tests.sh
 * This config does NOT start webServers since the test runner handles that.
 */
export default defineConfig({
  testDir: './tests/e2e',
  
  timeout: 180 * 1000, // 3 minutes for multi-client tests
  
  expect: {
    timeout: 10000
  },
  
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Serial execution for stability tests
  
  reporter: [
    ['html'],
    ['list'],
    ['json', { outputFile: 'test-results/test-results.json' }],
  ],
  
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // NO webServer configuration - servers are started by run-stability-tests.sh
});
