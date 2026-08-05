import { test, expect } from './fixtures.js';

/**
 * Test error handling and edge cases
 * Ensures the app handles failures gracefully
 */
test.describe('Error Handling', () => {
  test('handles network failures gracefully', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Simulate network failure by blocking requests
    await page.route('**/api/**', route => route.abort());
    
    // Try to trigger an API call
    await page.reload();
    await page.waitForTimeout(2000);
    
    // App should not crash - just show error state
    const root = await page.locator('#root').isVisible();
    expect(root).toBeTruthy();
  });

  test('handles malformed API responses', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Mock a bad API response
    await page.route('**/api/stat_overview', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ invalid: 'data' })
      });
    });
    
    await page.reload();
    await page.waitForTimeout(2000);
    
    // App should handle invalid data without crashing
    const root = await page.locator('#root').isVisible();
    expect(root).toBeTruthy();
  });

  test('handles 500 server errors gracefully', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Mock a 500 error
    await page.route('**/api/file/**', route => {
      route.fulfill({
        status: 500,
        body: 'Internal Server Error'
      });
    });
    
    // Try to load a file
    await page.goto('/PCs/Mahogany');
    await page.waitForTimeout(2000);
    
    // Should show error but not crash
    const root = await page.locator('#root').isVisible();
    expect(root).toBeTruthy();
  });

  test('handles missing files gracefully', async ({ page, errorTracker }) => {
    // Try to load a file that doesn't exist
    await page.goto('/PCs/NonExistentCharacter');
    await page.waitForTimeout(2000);
    
    // Should show some kind of not found state, but not crash
    const root = await page.locator('#root').isVisible();
    expect(root).toBeTruthy();
  });

  test('handles rapid navigation', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Rapidly navigate between routes
    await page.goto('/PCs');
    await page.goto('/NPCs');
    await page.goto('/Story');
    await page.goto('/PCs/Mahogany');
    await page.goto('/');
    
    await page.waitForTimeout(1000);
    
    // Should handle rapid navigation without errors
    const root = await page.locator('#root').isVisible();
    expect(root).toBeTruthy();
  });

  test('handles page reload during API call', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Start loading a file
    const fileLink = page.locator('text=/\\.md$/').first();
    
    if (await fileLink.isVisible({ timeout: 2000 })) {
      await fileLink.click();
      
      // Immediately reload
      await page.reload();
      await page.waitForTimeout(1000);
      
      // Should recover gracefully
      const root = await page.locator('#root').isVisible();
      expect(root).toBeTruthy();
    }
  });
});
