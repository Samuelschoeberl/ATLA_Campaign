import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';

test('check actual polling interval in browser', async ({ page }) => {
  // Listen to console messages
  const consoleLogs = [];
  page.on('console', msg => {
    consoleLogs.push(msg.text());
    console.log('BROWSER CONSOLE:', msg.text());
  });

  // Navigate to the app
  await page.goto(`${BASE_URL}/?t=${Date.now()}`);
  await page.waitForLoadState('networkidle');
  
  // Wait for file tree and click Initiative Tracker
  await page.waitForSelector('.file-tree', { timeout: 10000 });
  await page.click('.file-tree-item-content:has-text("Initiative Tracker.md")');
  await page.waitForSelector('.initiative-tracker', { timeout: 10000 });
  
  // Wait a bit for the component to mount and log
  await page.waitForTimeout(2000);
  
  // Check console logs
  const pollingLog = consoleLogs.find(log => log.includes('Setting up polling interval'));
  console.log('\n=== POLLING CONFIGURATION ===');
  console.log('Found log:', pollingLog);
  console.log('All logs:', consoleLogs.filter(log => log.includes('InitiativeTracker')));
  
  if (pollingLog) {
    expect(pollingLog).toContain('1000ms');
  } else {
    console.log('WARNING: No polling interval log found!');
    console.log('This means the component might be using OLD cached code');
  }
});
