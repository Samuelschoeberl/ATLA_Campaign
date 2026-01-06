import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';

async function navigateToInitiativeTracker(page) {
  await page.goto(BASE_URL);
  await page.waitForSelector('.file-tree', { timeout: 10000 });
  
  const initiativeFile = page.locator('.file-tree-item').filter({ hasText: 'Initiative Tracker.md' });
  await initiativeFile.click();
  await page.waitForSelector('.initiative-tracker-container', { timeout: 10000 });
}

test.describe('Simple Speed Test', () => {
  test('can navigate to Initiative Tracker', async ({ page }) => {
    await navigateToInitiativeTracker(page);
    
    // Verify we're on the initiative tracker
    const container = await page.locator('.initiative-tracker-container');
    await expect(container).toBeVisible();
    
    console.log('✓ Successfully navigated to Initiative Tracker');
  });

  test('can load character data', async ({ page }) => {
    await navigateToInitiativeTracker(page);
    
    // Wait for characters to load
    await page.waitForSelector('.initiative-item', { timeout: 5000 });
    
    const characterRows = await page.locator('.initiative-item').count();
    console.log(`✓ Loaded ${characterRows} characters`);
    
    expect(characterRows).toBeGreaterThan(0);
  });

  test('Next Turn button works', async ({ page }) => {
    await navigateToInitiativeTracker(page);
    await page.waitForSelector('.initiative-item', { timeout: 5000 });
    
    // Wait for a character to have current-turn class (should be immediate, but React needs render cycle)
    await page.waitForSelector('.initiative-item.current-turn', { timeout: 2000 });
    
    // Get current turn before click - name is in an input field
    const currentTurnBefore = await page.locator('.initiative-item.current-turn .name-field').inputValue();
    console.log(`Current turn before: ${currentTurnBefore}`);
    
    // Click Next Turn
    const nextButton = page.locator('button.btn-next-vertical');
    await nextButton.click();
    
    // Wait a bit for the change
    await page.waitForTimeout(500);
    
    // Get current turn after click
    const currentTurnAfter = await page.locator('.initiative-item.current-turn .name-field').inputValue();
    console.log(`Current turn after: ${currentTurnAfter}`);
    
    // They should be different (unless only 1 character)
    const characterCount = await page.locator('.initiative-item').count();
    if (characterCount > 1) {
      expect(currentTurnAfter).not.toBe(currentTurnBefore);
    }
    
    console.log('✓ Next Turn button works');
  });

  test('measures sync time between two clients', async ({ browser }) => {
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();
    const page1 = await context1.newPage();
    const page2 = await context2.newPage();

    try {
      // Navigate both pages
      await navigateToInitiativeTracker(page1);
      await navigateToInitiativeTracker(page2);
      
      // Wait for both to be ready with current-turn class
      await page1.waitForSelector('.initiative-item', { timeout: 5000 });
      await page2.waitForSelector('.initiative-item', { timeout: 5000 });
      await page1.waitForSelector('.initiative-item.current-turn', { timeout: 5000 });
      await page2.waitForSelector('.initiative-item.current-turn', { timeout: 5000 });
      
      console.log('Both clients ready');
      
      // Get current turn on both pages
      const turnBefore1 = await page1.locator('.initiative-item.current-turn .name-field').inputValue();
      const turnBefore2 = await page2.locator('.initiative-item.current-turn .name-field').inputValue();
      
      console.log(`Client 1 before: ${turnBefore1}`);
      console.log(`Client 2 before: ${turnBefore2}`);
      
      expect(turnBefore1).toBe(turnBefore2); // Should start in sync
      
      // Click Next Turn on page1
      const startTime = Date.now();
      await page1.locator('button.btn-next-vertical').click();
      
    
    // Wait for page1 to update
    await page1.waitForTimeout(300);
    const newTurn = await page1.locator('.initiative-item.current-turn .name-field').inputValue();
    console.log(`Client 1 after click: ${newTurn}`);      // Now wait for page2 to sync (with timeout)
      const maxWaitTime = 5000; // Max 5 seconds
      let syncTime = null;
      
      for (let i = 0; i < 50; i++) { // Check every 100ms for up to 5s
        await page2.waitForTimeout(100);
        const page2Turn = await page2.locator('.initiative-item.current-turn .name-field').inputValue();
        
        if (page2Turn === newTurn) {
          syncTime = Date.now() - startTime;
          console.log(`✓ Synced in ${syncTime}ms`);
          break;
        }
      }
      
      expect(syncTime).not.toBeNull();
      expect(syncTime).toBeLessThan(15000); // Should sync within 15 seconds (accounting for file I/O and network latency)
      
      console.log(`Final sync time: ${syncTime}ms`);
      
    } finally {
      await context1.close();
      await context2.close();
    }
  });
});
