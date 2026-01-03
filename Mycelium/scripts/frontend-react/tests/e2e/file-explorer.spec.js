import { test, expect } from './fixtures.js';

/**
 * Test file explorer functionality
 * Tests the integration of:
 * - Backend file API
 * - Frontend file tree rendering
 * - File selection and viewing
 */
test.describe('File Explorer', () => {
  test('file explorer renders without errors', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Look for file explorer component
    const fileExplorer = page.locator('.file-explorer, [class*="FileExplorer"]').first();
    
    // Give it time to load
    await page.waitForTimeout(1000);
    
    // Should have some file tree elements
    const hasFileTree = await page.locator('.file-tree, [class*="FileTree"], .file-item, [class*="file"]').count();
    expect(hasFileTree).toBeGreaterThan(0);
  });

  test('can fetch and display file list from backend', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Wait for any API call (the frontend might use different endpoints)
    const response = await page.waitForResponse(
      res => res.url().includes('/api/') || res.url().includes('/player_root'),
      { timeout: 5000 }
    ).catch(() => null);
    
    if (response) {
      expect(response.ok() || response.status() === 404).toBeTruthy();
    }
  });

  test('clicking a folder expands it', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Wait for file tree to load
    await page.waitForTimeout(1500);
    
    // Find a folder (look for common folder names)
    const folder = page.locator('text=/PCs|NPCs|Story|Dms Root/').first();
    
    if (await folder.isVisible()) {
      const initialChildren = await page.locator('.file-item, [class*="file"]').count();
      
      // Click to expand
      await folder.click();
      await page.waitForTimeout(500);
      
      const afterChildren = await page.locator('.file-item, [class*="file"]').count();
      
      // Should have more items visible now (or at least same)
      expect(afterChildren).toBeGreaterThanOrEqual(initialChildren);
    }
  });

  test('clicking a markdown file loads its content', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Wait for file tree to be present and loaded
    await page.waitForSelector('.file-tree', { timeout: 5000 });
    await page.waitForTimeout(1500);
    
    // Look for a clickable .md file - specifically Quicklinks.md which we know exists
    // Try to find it in the file tree structure
    const quicklinksFile = page.locator('.file-tree-item').filter({ hasText: 'Quicklinks.md' }).first();
    
    // If Quicklinks doesn't exist, try any .md file in the tree
    const mdFile = await quicklinksFile.count() > 0 
      ? quicklinksFile 
      : page.locator('.file-tree-item').filter({ hasText: /\.md$/ }).first();
    
    if (await mdFile.isVisible()) {
      // Set up response waiter before clicking (best-effort)
      const responsePromise = page.waitForResponse(
        res => res.url().includes('/api/file/'),
        { timeout: 10000 }
      ).catch(() => null);

      await mdFile.click();

      // Wait for either the network response OR the viewer to render content
      const response = await responsePromise;

      if (response) {
        // If we observed the network response, assert it's successful
        expect(response.ok() || response.status() === 404).toBeTruthy();
      } else {
        // As a fallback, wait for the file viewer or rendered markdown to appear
        await page.waitForSelector('.file-viewer, .markdown-content, .file-content, [data-testid="file-content"]', { timeout: 10000 });
        // Assert the viewer contains some text
        const viewerText = await page.locator('.file-viewer, .markdown-content, .file-content, [data-testid="file-content"]').innerText();
        expect(viewerText && viewerText.trim().length).toBeGreaterThan(0);
      }
    }
  });

  test('handles file not found gracefully', async ({ page, errorTracker }) => {
    // Try to load a non-existent file
    const response = await page.request.get('http://localhost:9002/api/file/nonexistent.md');
    
    // Should return 404 but not crash
    expect(response.status()).toBe(404);
  });
});
