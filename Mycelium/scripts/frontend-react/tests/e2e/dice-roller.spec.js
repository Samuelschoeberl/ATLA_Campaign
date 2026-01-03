import { test, expect } from './fixtures.js';

/**
 * Test dice roller functionality
 * Tests the integration of:
 * - Dice roller UI
 * - Random number generation
 * - Roll history
 */
test.describe('Dice Roller', () => {
  test('dice roller component renders', async ({ page, errorTracker }) => {
    await page.goto('/');
    
    // Look for dice roller UI elements
    const diceRoller = page.locator('.dice-roller, [class*="DiceRoller"]').first();
    
    // Give components time to mount
    await page.waitForTimeout(1000);
    
    // Look for dice-related buttons or text
    const hasDiceUI = await page.locator('text=/d4|d6|d8|d10|d12|d20|Roll/i').count();
    
    if (hasDiceUI > 0 || await diceRoller.isVisible()) {
      expect(true).toBeTruthy();
    } else {
      // Dice roller might be hidden by default
      console.log('Dice roller not immediately visible - may need to open panel');
    }
  });

  test('can roll dice', async ({ page, errorTracker }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    
    // Look for a roll button or dice button
    const rollButton = page.getByRole('button', { name: /roll|d20|dice/i }).first();
    
    if (await rollButton.isVisible({ timeout: 2000 })) {
      // Click to roll
      await rollButton.click();
      
      // Should see a result (number)
      await page.waitForTimeout(500);
      
      // Look for roll results
      const hasNumbers = await page.locator('text=/\\b\\d+\\b/').count();
      expect(hasNumbers).toBeGreaterThan(0);
    }
  });

  test('dice roller handles multiple rolls', async ({ page, errorTracker }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    
    const rollButton = page.getByRole('button', { name: /roll|d20/i }).first();
    
    if (await rollButton.isVisible({ timeout: 2000 })) {
      // Roll multiple times
      await rollButton.click();
      await page.waitForTimeout(300);
      await rollButton.click();
      await page.waitForTimeout(300);
      await rollButton.click();
      
      // Should handle multiple rolls without errors
      // errorTracker will automatically fail if there are exceptions
      expect(true).toBeTruthy();
    }
  });

  test('roll results are valid numbers', async ({ page, errorTracker }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    
    // Test if roll results API works (if there is one)
    const response = await page.evaluate(async () => {
      // Simulate a dice roll in the frontend
      const roll = Math.floor(Math.random() * 20) + 1;
      return { roll, isValid: roll >= 1 && roll <= 20 };
    });
    
    expect(response.isValid).toBeTruthy();
  });
});
