import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';

// This spec used to assert on a specific hardcoded "Setting up polling
// interval"/"1000ms" console.log line from InitiativeTracker.jsx. That log
// line never actually existed in the current component (per the rework
// discovery notes -- it was already stale/leftover from an older version),
// and the premise itself is gone now regardless: InitiativeTracker's
// tracker-file sync and turn/round advance are driven by the shared SSE
// stream (`/api/events`) plus a DB-backed PATCH endpoint
// (`/api/initiative/turn`) instead of blind polling. See
// src/data/vaultResource.js and routes_initiative.py.

test('initiative tracker opens the shared SSE stream instead of polling', async ({ page }) => {
  const requests = [];
  page.on('request', (req) => requests.push(req.url()));

  await page.goto(`${BASE_URL}/?t=${Date.now()}`);
  await page.waitForLoadState('networkidle');

  await page.waitForSelector('.file-tree', { timeout: 10000 });
  await page.click('.file-tree-item-content:has-text("Initiative Tracker.md")');
  await page.waitForSelector('.initiative-tracker', { timeout: 10000 });

  // Give the shared EventSource a moment to connect.
  await page.waitForTimeout(1000);

  const sseRequest = requests.find((u) => u.includes('/api/events'));
  expect(sseRequest, 'expected the shared SSE stream (/api/events) to be opened').toBeTruthy();
});

test('advancing the turn PATCHes /api/initiative/turn instead of only overwriting the whole file', async ({ page }) => {
  const patchRequests = [];
  page.on('request', (req) => {
    if (req.method() === 'PATCH' && req.url().includes('/api/initiative/turn')) {
      patchRequests.push(req.url());
    }
  });

  await page.goto(`${BASE_URL}/?t=${Date.now()}`);
  await page.waitForLoadState('networkidle');

  await page.waitForSelector('.file-tree', { timeout: 10000 });
  await page.click('.file-tree-item-content:has-text("Initiative Tracker.md")');
  await page.waitForSelector('.initiative-tracker', { timeout: 10000 });

  const nextTurnButton = page.locator('.btn-next-vertical');
  if ((await nextTurnButton.count()) === 0 || (await nextTurnButton.isDisabled())) {
    test.skip(true, 'No combatants in the tracker to advance a turn for');
    return;
  }

  await nextTurnButton.click();
  await page.waitForTimeout(500);

  expect(patchRequests.length, 'expected a PATCH /api/initiative/turn request after advancing the turn').toBeGreaterThan(0);
});
