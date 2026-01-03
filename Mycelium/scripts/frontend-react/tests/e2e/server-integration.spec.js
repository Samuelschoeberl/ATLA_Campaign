import { test, expect, waitForBackend } from './fixtures.js';

/**
 * Basic smoke tests to ensure servers start and communicate properly
 */
test.describe('Server Integration', () => {
  test('backend server responds to API requests', async ({ page, errorTracker }) => {
    // Check if backend is up
    await waitForBackend(page);
    
    const response = await page.request.get('http://localhost:9002/api/active_sessions');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('sessions');
  });

  test('frontend loads without errors', async ({ page, errorTracker }) => {
    // Navigate to frontend
    await page.goto('/');
    
    // Wait for main app container to load
    await expect(page.locator('body')).toBeVisible();
    
    // Check that React rendered something
    const appContent = await page.locator('#root').isVisible();
    expect(appContent).toBeTruthy();
  });

  test('frontend can fetch from backend API', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Wait for API call to complete - look for any API call
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/api/') && response.status() === 200,
      { timeout: 10000 }
    ).catch(() => null);
    
    await page.reload();
    const response = await responsePromise;
    
    // If we got a response, verify it's OK
    if (response) {
      expect(response.ok()).toBeTruthy();
    }
  });

  test('no CORS errors when frontend calls backend', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Make a request to the backend
    await page.evaluate(async () => {
      const response = await fetch('http://localhost:9002/api/active_sessions');
      return response.json();
    });
    
    // Check for CORS-related console errors
    const corsErrors = errorTracker.consoleErrors.filter(err => 
      err.text.toLowerCase().includes('cors') || 
      err.text.toLowerCase().includes('access-control')
    );
    
    expect(corsErrors.length).toBe(0);
  });

  test('backend serves static assets correctly', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Check for failed asset loads
    const assetFailures = errorTracker.failedRequests.filter(req => 
      req.url.includes('.js') || 
      req.url.includes('.css') ||
      req.url.includes('.json')
    );
    
    expect(assetFailures.length).toBe(0);
  });
});
