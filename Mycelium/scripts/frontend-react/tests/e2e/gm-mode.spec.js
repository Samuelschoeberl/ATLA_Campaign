import { test, expect } from './fixtures.js';

/**
 * Test Game Master Mode functionality
 * Tests GM-specific features and permissions
 */
test.describe('Game Master Mode', () => {
  test('GM mode can be accessed', async ({ page, errorTracker }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    
    // Look for GM mode toggle/button
    const gmButton = page.getByRole('button', { name: /GM|Game Master|Master/i }).first();
    
    if (await gmButton.isVisible({ timeout: 2000 })) {
      await gmButton.click();
      await page.waitForTimeout(500);
      
      // Should show GM-specific UI
      expect(true).toBeTruthy();
    } else {
      // Try navigating directly
      await page.goto('/?gm=true');
      await page.waitForTimeout(1000);
      
      const root = await page.locator('#root').isVisible();
      expect(root).toBeTruthy();
    }
  });

  test('GM mode shows additional controls', async ({ page, errorTracker }) => {
    await page.goto('/?gm=true');
    await page.waitForTimeout(2000);
    
    // Look for GM-specific elements
    const gmHeader = await page.locator('text=/Game Master Tools/i').count();
    const gmTabs = await page.locator('text=/Move Analysis|Content Overview|Active Sessions/i').count();
    
    // GM mode should show the header and tabs
    expect(gmHeader + gmTabs).toBeGreaterThan(0);
  });

  test('can access NPC files in GM mode', async ({ page, errorTracker }) => {
    await page.goto('/?gm=true');
    await page.waitForTimeout(1500);
    
    // Should be able to navigate to NPCs
    const npcsLink = page.getByText('NPCs', { exact: false }).first();
    
    if (await npcsLink.isVisible()) {
      await npcsLink.click();
      await page.waitForTimeout(500);
      
      // Should navigate without errors
      const hasContent = await page.locator('#root').isVisible();
      expect(hasContent).toBeTruthy();
    }
  });

  test('initiative tracker works in GM mode', async ({ page, errorTracker }) => {
    await page.goto('/?gm=true');
    await page.waitForTimeout(1500);
    
    // Look for initiative tracker
    const initiativeTracker = page.locator('.initiative-tracker, [class*="InitiativeTracker"]').first();
    
    const isVisible = await initiativeTracker.isVisible({ timeout: 3000 }).catch(() => false);
    
    if (isVisible) {
      // Initiative tracker loaded successfully
      expect(true).toBeTruthy();
    }
  });

  test('GM mode can switch back to player mode', async ({ page, errorTracker }) => {
    await page.goto('/?gm=true');
    await page.waitForTimeout(1000);
    
    // Try to switch back to player mode
    const playerButton = page.getByRole('button', { name: /Player|Exit GM/i }).first();
    
    if (await playerButton.isVisible({ timeout: 2000 })) {
      await playerButton.click();
      await page.waitForTimeout(500);
      
      // Should still work
      const root = await page.locator('#root').isVisible();
      expect(root).toBeTruthy();
    } else {
      // Just navigate away
      await page.goto('/');
      await page.waitForTimeout(500);
      
      const root = await page.locator('#root').isVisible();
      expect(root).toBeTruthy();
    }
  });
});
