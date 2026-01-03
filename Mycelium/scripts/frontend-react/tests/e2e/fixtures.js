import { test as base, expect } from '@playwright/test';

/**
 * Extended test fixture with error tracking and common utilities.
 * 
 * This automatically:
 * - Captures console.error messages
 * - Captures uncaught exceptions (pageerror)
 * - Tracks failed network requests
 * - Provides common helper methods
 */
export const test = base.extend({
  // Track errors that occur during the test
  errorTracker: async ({ page }, use) => {
    const errors = {
      consoleErrors: [],
      pageErrors: [],
      failedRequests: [],
    };

    // Listen for console.error
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.consoleErrors.push({
          text: msg.text(),
          location: msg.location(),
        });
      }
    });

    // Listen for uncaught exceptions
    page.on('pageerror', (error) => {
      errors.pageErrors.push({
        message: error.message,
        stack: error.stack,
      });
    });

    // Listen for failed requests
    page.on('response', (response) => {
      if (response.status() >= 400) {
        errors.failedRequests.push({
          url: response.url(),
          status: response.status(),
          statusText: response.statusText(),
        });
      }
    });

    // Provide the error tracker to the test
    await use(errors);

    // After the test, assert no critical errors occurred
    // (unless the test explicitly expects them)
    if (errors.pageErrors.length > 0) {
      console.error('❌ Uncaught exceptions detected:');
      errors.pageErrors.forEach((err, i) => {
        console.error(`  ${i + 1}. ${err.message}`);
        if (err.stack) console.error(`     ${err.stack}`);
      });
    }

    if (errors.consoleErrors.length > 0) {
      console.warn('⚠️  Console errors detected:');
      errors.consoleErrors.forEach((err, i) => {
        console.warn(`  ${i + 1}. ${err.text}`);
      });
    }

    // Fail the test if there were page errors (uncaught exceptions)
    expect(errors.pageErrors, 'Should not have uncaught exceptions').toHaveLength(0);
  },

  // Helper to wait for backend API to be ready
  backendReady: async ({ page }, use) => {
    const checkBackend = async () => {
      try {
        const response = await page.request.get('http://localhost:9002/api/active_sessions');
        return response.ok();
      } catch {
        return false;
      }
    };

    await use(checkBackend);
  },

  // Helper to wait for frontend to be ready
  frontendReady: async ({ page }, use) => {
    const checkFrontend = async () => {
      try {
        await page.goto('/', { waitUntil: 'networkidle', timeout: 5000 });
        return true;
      } catch {
        return false;
      }
    };

    await use(checkFrontend);
  },
});

/**
 * Helper function to wait for a condition with timeout
 */
export async function waitForCondition(conditionFn, timeoutMs = 10000, intervalMs = 100) {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeoutMs) {
    if (await conditionFn()) {
      return true;
    }
    await new Promise(resolve => setTimeout(resolve, intervalMs));
  }
  
  throw new Error(`Condition not met within ${timeoutMs}ms`);
}

/**
 * Helper to check if backend API is responding
 */
export async function waitForBackend(page, timeoutMs = 10000) {
  return waitForCondition(async () => {
    try {
      const response = await page.request.get('http://localhost:9002/api/active_sessions');
      return response.ok();
    } catch {
      return false;
    }
  }, timeoutMs);
}

/**
 * Helper to check if frontend is loaded
 */
export async function waitForFrontend(page, timeoutMs = 10000) {
  return waitForCondition(async () => {
    try {
      await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 2000 });
      return await page.locator('body').isVisible();
    } catch {
      return false;
    }
  }, timeoutMs);
}

export { expect };
