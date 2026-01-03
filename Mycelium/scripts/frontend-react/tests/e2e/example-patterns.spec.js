import { test, expect } from './fixtures.js';

/**
 * EXAMPLE TEST - Demonstrates key Playwright features
 * 
 * This test shows:
 * 1. How errorTracker automatically catches frontend errors
 * 2. How to test backend/frontend integration
 * 3. How to check for specific error conditions
 * 4. Best practices for E2E testing
 */

test.describe('Example: Key Testing Patterns', () => {
  
  test('Pattern 1: Basic page load with error detection', async ({ page, errorTracker }) => {
    // Navigate to the app
    await page.goto('/');
    
    // Wait for app to render
    await expect(page.locator('#root')).toBeVisible();
    
    // errorTracker automatically fails if there are:
    // - Uncaught exceptions (pageerror events)
    // - console.error() calls
    // No need to manually check!
  });

  test('Pattern 2: Testing API integration', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Wait for any API call to complete
    const response = await page.waitForResponse(
      res => res.url().includes('/api/'),
      { timeout: 5000 }
    ).catch(() => null);
    
    if (response) {
      // Verify response is successful or expected error
      expect(response.status() < 500).toBeTruthy();
    }
  });

  test('Pattern 3: Testing user interactions', async ({ page, errorTracker }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    
    // Find and click a button
    const button = page.getByRole('button', { name: /PCs/i }).first();
    
    if (await button.isVisible()) {
      await button.click();
      
      // Wait for navigation or state change
      await page.waitForTimeout(500);
      
      // Verify the interaction worked
      const hasContent = await page.locator('#root').isVisible();
      expect(hasContent).toBeTruthy();
    }
  });

  test('Pattern 4: Checking for specific errors', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Do something that might cause errors
    await page.reload();
    await page.waitForTimeout(1000);
    
    // Check for CORS errors specifically
    const corsErrors = errorTracker.consoleErrors.filter(err => 
      err.text.toLowerCase().includes('cors')
    );
    
    expect(corsErrors.length).toBe(0);
    
    // Check for failed network requests
    const failedAPICalls = errorTracker.failedRequests.filter(req => 
      req.url.includes('/api/')
    );
    
    expect(failedAPICalls.length).toBe(0);
  });

  test('Pattern 5: Testing error handling', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Mock a network failure for a specific API
    await page.route('**/api/stat_overview', route => route.abort());
    
    // Trigger the API call by reloading
    await page.reload();
    await page.waitForTimeout(2000);
    
    // App should still render (not crash)
    const root = await page.locator('#root').isVisible();
    expect(root).toBeTruthy();
    
    // Note: The app might log console errors for the network failure,
    // but it shouldn't have uncaught exceptions
  });

  test('Pattern 6: Testing navigation flows', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Navigate through the app
    await page.goto('/PCs');
    await page.waitForTimeout(500);
    
    await page.goto('/NPCs');
    await page.waitForTimeout(500);
    
    // Go back
    await page.goBack();
    expect(page.url()).toContain('/PCs');
    
    // Go forward
    await page.goForward();
    expect(page.url()).toContain('/NPCs');
  });

  test('Pattern 7: Waiting for async operations', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Wait for specific element to appear
    await page.waitForSelector('#root', { timeout: 5000 });
    
    // Wait for network idle (all requests complete)
    await page.waitForLoadState('networkidle', { timeout: 10000 });
    
    // Wait for specific condition
    await page.waitForFunction(() => {
      return document.querySelector('#root') !== null;
    });
    
    expect(true).toBeTruthy();
  });

  test('Pattern 8: Testing with different viewports', async ({ page, errorTracker }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    
    // Test mobile UI
    await expect(page.locator('#root')).toBeVisible();
    
    // Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    
    // Test desktop UI
    await expect(page.locator('#root')).toBeVisible();
  });

  test('Pattern 9: Inspecting errorTracker manually', async ({ page, errorTracker }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    
    // After test runs, you can inspect errors manually
    console.log('Console Errors:', errorTracker.consoleErrors);
    console.log('Page Errors:', errorTracker.pageErrors);
    console.log('Failed Requests:', errorTracker.failedRequests);
    
    // The test will automatically fail if pageErrors.length > 0
    // But you can also add custom assertions
    expect(errorTracker.consoleErrors.length).toBeLessThan(5);
  });
});

/**
 * Tips for writing good E2E tests:
 * 
 * 1. Test user flows, not implementation
 *    ✅ "User can create a character"
 *    ❌ "CharacterForm component renders"
 * 
 * 2. Use meaningful selectors
 *    ✅ page.getByRole('button', { name: 'Save' })
 *    ❌ page.locator('.btn-primary-123')
 * 
 * 3. Wait for state, not time
 *    ✅ await page.waitForSelector('#content')
 *    ❌ await page.waitForTimeout(5000)
 * 
 * 4. Test error states
 *    - Network failures
 *    - Invalid data
 *    - Missing resources
 * 
 * 5. Keep tests independent
 *    - Don't rely on test order
 *    - Clean up state if needed
 * 
 * 6. Use errorTracker
 *    - Catches bugs you didn't know existed
 *    - Fails fast on critical errors
 */
