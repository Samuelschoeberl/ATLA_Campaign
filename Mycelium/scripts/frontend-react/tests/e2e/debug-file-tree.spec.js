import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';

test.describe('Debug File Tree', () => {
  test('check what files are visible', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForTimeout(3000); // Give it time to load
    
    // Log all file items with WRONG selector
    const fileItems = await page.locator('.file-item').all();
    console.log(`Found ${fileItems.length} file items with .file-item`);
    
    // Log all file items with CORRECT selector
    const fileTreeItems = await page.locator('.file-tree-item').all();
    console.log(`Found ${fileTreeItems.length} file items with .file-tree-item`);
    
    for (let i = 0; i < fileTreeItems.length && i < 20; i++) {
      const text = await fileTreeItems[i].textContent();
      console.log(`File ${i}: "${text}"`);
    }
    
    // Check if Initiative Tracker specifically exists
    const initiativeFile = page.locator('.file-tree-item').filter({ hasText: 'Initiative Tracker' });
    const count = await initiativeFile.count();
    console.log(`\nInitiative Tracker matches: ${count}`);
    
    if (count > 0) {
      const text = await initiativeFile.first().textContent();
      console.log(`Initiative Tracker text: "${text}"`);
    }
    
    // Try different selectors
    const anyInitiative = await page.locator('text=/Initiative/i').all();
    console.log(`\nAny text containing "Initiative": ${anyInitiative.length}`);
    for (let i = 0; i < anyInitiative.length && i < 5; i++) {
      const text = await anyInitiative[i].textContent();
      console.log(`  - "${text}"`);
    }
    
    // Take a screenshot
    await page.screenshot({ path: 'test-results/debug-file-tree.png', fullPage: true });
  });
  
  test('check if Initiative Tracker loads', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForTimeout(2000);
    
    // Click on Initiative Tracker
    const initiativeTracker = page.locator('.file-tree-item').filter({ hasText: 'Initiative Tracker.md' });
    console.log('Looking for Initiative Tracker...');
    const isVisible = await initiativeTracker.isVisible({ timeout: 3000 });
    console.log(`Initiative Tracker visible: ${isVisible}`);
    
    if (isVisible) {
      await initiativeTracker.click();
      console.log('Clicked Initiative Tracker');
      await page.waitForTimeout(2000); // Wait for content to load
      
      // Check for initiative tracker container
      const tracker = page.locator('.initiative-tracker-container');
      const trackerVisible = await tracker.isVisible({ timeout: 3000 }).catch(() => false);
      console.log(`Initiative tracker container visible: ${trackerVisible}`);
      
      if (trackerVisible) {
        console.log('✓ Initiative Tracker loaded successfully!');
      } else {
        // Check what's actually in file-explorer-content
        const content = page.locator('.file-explorer-content').first();
        const text = await content.textContent();
        console.log(`File explorer content: ${text?.substring(0, 200)}`);
      }
      
      // Take a screenshot
      await page.screenshot({ path: 'test-results/debug-initiative-tracker.png', fullPage: true });
    }
  });
});
