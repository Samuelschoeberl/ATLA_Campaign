import { test, expect } from './fixtures.js';

/**
 * Test basic app loading
 * Note: This app uses file-tree navigation, not URL-based routing
 */
test.describe('App Loading', () => {
  test('home page loads successfully', async ({ page, errorTracker }) => {
    await page.goto('/');
    await expect(page.locator('#root')).toBeVisible();
  });
});
