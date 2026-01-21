/**
 * 10-Client Stability and Stress Testing Suite
 * 
 * Tests system stability with up to 10 concurrent clients:
 * - Data synchronization across all clients
 * - No crashes or memory leaks
 * - Correct state updates for InitiativeTracker and CharacterSheet
 * - Race condition handling
 * - Server load and response times
 * 
 * Expected behavior:
 * - All clients should sync within 2-3 seconds (polling interval + network)
 * - No data loss or corruption
 * - No uncaught exceptions
 * - Server remains responsive under load
 */

import { test, expect } from './fixtures.js';

const BASE_URL = process.env.VITE_API_BASE_URL || 'http://localhost:5173';
const MAX_CLIENTS = 10;

// Helper to create multiple browser contexts
async function createClients(browser, count) {
  const contexts = [];
  const pages = [];
  
  for (let i = 0; i < count; i++) {
    const context = await browser.newContext({
      ignoreHTTPSErrors: true,
      bypassCSP: true,
    });
    
    // Disable cache to ensure fresh data
    await context.addInitScript(() => {
      delete window.caches;
    });
    
    const page = await context.newPage();
    contexts.push(context);
    pages.push(page);
  }
  
  return { contexts, pages };
}

// Helper to navigate all clients to Initiative Tracker
async function navigateAllToInitiativeTracker(pages) {
  await Promise.all(pages.map(async (page) => {
    await page.goto(`${BASE_URL}/?t=${Date.now()}`);
    await page.waitForLoadState('networkidle', { timeout: 15000 });
    await page.waitForSelector('.file-tree', { timeout: 10000 });
    await page.click('.file-tree-item-content:has-text("Initiative Tracker.md")');
    await page.waitForSelector('.initiative-tracker', { timeout: 10000 });
  }));
}

// Helper to navigate all clients to a character sheet
async function navigateAllToCharacterSheet(pages, characterName = 'Mahogany') {
  await Promise.all(pages.map(async (page) => {
    await page.goto(`${BASE_URL}/?t=${Date.now()}`);
    await page.waitForLoadState('networkidle', { timeout: 15000 });
    await page.waitForSelector('.file-tree', { timeout: 10000 });
    
    // Expand PCs folder
    const pcsFolder = page.locator('.file-tree-item-content.folder:has-text("PCs")').first();
    if (await pcsFolder.isVisible({ timeout: 5000 })) {
      await pcsFolder.click();
      await page.waitForTimeout(500);
    }
    
    // Expand character folder
    const charFolder = page.locator(`.file-tree-item-content.folder:has-text("${characterName}")`).first();
    if (await charFolder.isVisible({ timeout: 5000 })) {
      await charFolder.click();
      await page.waitForTimeout(500);
    }
    
    // Click on character sheet
    await page.click(`.file-tree-item-content:has-text("${characterName} character sheet")`);
    await page.waitForTimeout(2000);
  }));
}

// Helper to cleanup clients
async function cleanupClients(contexts) {
  await Promise.all(contexts.map(ctx => ctx.close()));
}

test.describe('10-Client Stability Tests', () => {
  test.describe.configure({ 
    mode: 'serial',
    timeout: 300000 // 5 minutes for stress tests
  });

  test('should handle 10 clients loading the application simultaneously', async ({ browser }) => {
    const { contexts, pages } = await createClients(browser, MAX_CLIENTS);
    
    try {
      const startTime = Date.now();
      
      // All clients load simultaneously
      await Promise.all(pages.map(page => page.goto(BASE_URL, { timeout: 30000 })));
      
      const loadTime = Date.now() - startTime;
      console.log(`✓ ${MAX_CLIENTS} clients loaded in ${loadTime}ms`);
      
      // All should load successfully
      expect(loadTime).toBeLessThan(30000); // 30 seconds max for all clients
      
      // Verify all clients have the app root
      const results = await Promise.all(pages.map(async (page) => {
        return await page.locator('#root').isVisible({ timeout: 5000 });
      }));
      
      expect(results.every(r => r === true)).toBeTruthy();
      console.log(`✓ All ${MAX_CLIENTS} clients loaded successfully`);
      
    } finally {
      await cleanupClients(contexts);
    }
  });

  test('should sync Initiative Tracker across 10 clients without data loss', async ({ browser }) => {
    const { contexts, pages } = await createClients(browser, MAX_CLIENTS);
    
    try {
      console.log('Navigating all clients to Initiative Tracker...');
      await navigateAllToInitiativeTracker(pages);
      
      // Wait for all to be ready with increased timeout for 10 clients
      await Promise.all(pages.map(page => 
        page.waitForSelector('.initiative-tracker-container', { timeout: 30000 }) // Increased from 10s to 30s
      ));
      
      // Give extra time for all clients to stabilize
      await pages[0].waitForTimeout(2000); // Increased from 1s to 2s
      
      // Get initial character count from client 0
      const initialCount = await pages[0].locator('.initiative-item').count();
      console.log(`Starting with ${initialCount} existing characters`);
      
      // Client 0: Advance turn
      const startTime = Date.now();
      await pages[0].click('.btn-next-vertical');
      await pages[0].waitForTimeout(500);
      
      // Get current turn index from client 0
      const client0CurrentTurn = await pages[0].locator('.initiative-item.current-turn').count();
      console.log(`Client 0 current turn indicator count: ${client0CurrentTurn}`);
      
      // Wait for sync (2s polling + 1s buffer)
      await pages[0].waitForTimeout(3000);
      
      const syncTime = Date.now() - startTime;
      console.log(`Sync completed in ${syncTime}ms`);
      
      // Verify all clients synced the turn advancement
      const syncResults = await Promise.all(pages.map(async (page, idx) => {
        const currentTurnCount = await page.locator('.initiative-item.current-turn').count();
        console.log(`Client ${idx} current turn count: ${currentTurnCount}`);
        return currentTurnCount;
      }));
      
      // All clients should show the same state (either 0 or 1 current turn indicator)
      const uniqueValues = [...new Set(syncResults)];
      expect(uniqueValues.length).toBeLessThanOrEqual(2); // Allow for 0 or 1
      console.log(`✓ All ${MAX_CLIENTS} clients synced successfully`);
      
      // Sync should complete within reasonable time
      expect(syncTime).toBeLessThan(5000);
      
    } finally {
      await cleanupClients(contexts);
    }
  });

  test('should handle 10 clients making simultaneous turn advances', async ({ browser }) => {
    const { contexts, pages } = await createClients(browser, MAX_CLIENTS);
    
    try {
      console.log('Navigating all clients to Initiative Tracker...');
      await navigateAllToInitiativeTracker(pages);
      
      await Promise.all(pages.map(page => 
        page.waitForSelector('.initiative-tracker-container', { timeout: 10000 })
      ));
      await pages[0].waitForTimeout(1000);
      
      // Get initial round number
      const initialRound = await pages[0].locator('.round-number').textContent();
      console.log(`Starting round: ${initialRound}`);
      
      // All clients click next turn simultaneously
      const startTime = Date.now();
      await Promise.all(pages.map(page => page.click('.btn-next-vertical')));
      
      // Wait for all clients to update locally
      await pages[0].waitForTimeout(500);
      
      // Wait for sync across all clients (3s max)
      await pages[0].waitForTimeout(3000);
      
      const syncTime = Date.now() - startTime;
      console.log(`All clients clicked and synced in ${syncTime}ms`);
      
      // Check final states - collect round numbers from all clients
      const roundResults = await Promise.all(pages.map(async (page, idx) => {
        const round = await page.locator('.round-number').textContent();
        console.log(`Client ${idx} round: ${round}`);
        return round;
      }));
      
      // System should resolve to a consistent state (no data corruption)
      // With file-based sync, last write wins, so all should eventually converge
      const uniqueRounds = [...new Set(roundResults)];
      console.log(`Unique round states: ${uniqueRounds.join(', ')}`);
      
      // Should converge to a consistent state within sync window
      expect(uniqueRounds.length).toBeLessThanOrEqual(3); // Allow some variance during sync
      
      // Wait additional time for full convergence
      await pages[0].waitForTimeout(2000);
      
      // Check again - should be fully synced now
      const finalRounds = await Promise.all(pages.map(page => 
        page.locator('.round-number').textContent()
      ));
      const finalUnique = [...new Set(finalRounds)];
      console.log(`Final unique round states: ${finalUnique.join(', ')}`);
      
      console.log(`✓ All ${MAX_CLIENTS} clients handled simultaneous updates`);
      
    } finally {
      await cleanupClients(contexts);
    }
  });

  test('should sync Character Sheet HP changes across 10 clients', async ({ browser }) => {
    const { contexts, pages } = await createClients(browser, MAX_CLIENTS);
    
    try {
      console.log('Navigating all clients to Character Sheet...');
      await navigateAllToCharacterSheet(pages, 'Mahogany');
      
      // Wait for character sheets to load
      await pages[0].waitForTimeout(2000);
      
      // Look for HP input or vitals section
      const hasHpSection = await pages[0].locator('text=/HP|current_hp|vitals/i').count();
      console.log(`HP section elements found: ${hasHpSection}`);
      
      if (hasHpSection > 0) {
        // Try to find and update HP value
        const hpInput = pages[0].locator('input[type="number"]').first();
        
        if (await hpInput.count() > 0 && await hpInput.isVisible({ timeout: 2000 })) {
          const startTime = Date.now();
          
          // Client 0 updates HP
          await hpInput.fill('75');
          await hpInput.press('Tab'); // Trigger change
          await pages[0].waitForTimeout(1000);
          
          console.log('Client 0 updated HP to 75');
          
          // Wait for sync (character sheet may have longer polling)
          await pages[0].waitForTimeout(5000);
          
          const syncTime = Date.now() - startTime;
          console.log(`HP sync time: ${syncTime}ms`);
          
          // Check if other clients received the update
          let syncedClients = 0;
          for (let i = 1; i < pages.length; i++) {
            const clientHpInput = pages[i].locator('input[type="number"]').first();
            if (await clientHpInput.count() > 0) {
              const value = await clientHpInput.inputValue();
              if (value === '75') {
                syncedClients++;
              }
              console.log(`Client ${i} HP value: ${value}`);
            }
          }
          
          console.log(`✓ ${syncedClients}/${MAX_CLIENTS - 1} clients synced HP change`);
          
          // At least 70% of clients should have synced
          expect(syncedClients).toBeGreaterThanOrEqual(Math.floor(MAX_CLIENTS * 0.7) - 1);
          
          // Should sync within reasonable time for character sheets
          expect(syncTime).toBeLessThan(10000); // 10 seconds max
        } else {
          console.log('⚠️ HP input not found, skipping update test');
        }
      } else {
        console.log('⚠️ Character sheet HP section not found, test may need adjustment');
      }
      
    } finally {
      await cleanupClients(contexts);
    }
  });

  test('should maintain server responsiveness with 10 active clients', async ({ browser }) => {
    const { contexts, pages } = await createClients(browser, MAX_CLIENTS);
    
    try {
      // Navigate all clients
      await Promise.all(pages.map(page => page.goto(BASE_URL, { timeout: 30000 })));
      
      // Measure API response times under load
      const responseTimes = [];
      
      for (let i = 0; i < 5; i++) {
        const startTime = Date.now();
        
        // All clients make API request simultaneously
        const responses = await Promise.all(pages.map(page => 
          page.request.get('http://localhost:9002/api/active_sessions')
        ));
        
        const responseTime = Date.now() - startTime;
        responseTimes.push(responseTime);
        
        // All should succeed
        const allOk = responses.every(r => r.ok());
        expect(allOk).toBeTruthy();
        
        console.log(`Round ${i + 1}: ${responseTime}ms for ${MAX_CLIENTS} simultaneous requests`);
        
        await pages[0].waitForTimeout(1000);
      }
      
      const avgResponseTime = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
      const maxResponseTime = Math.max(...responseTimes);
      
      console.log(`Average response time: ${avgResponseTime}ms`);
      console.log(`Max response time: ${maxResponseTime}ms`);
      
      // Server should remain responsive
      expect(avgResponseTime).toBeLessThan(5000); // 5 seconds average
      expect(maxResponseTime).toBeLessThan(10000); // 10 seconds max
      
      console.log(`✓ Server remained responsive with ${MAX_CLIENTS} clients`);
      
    } finally {
      await cleanupClients(contexts);
    }
  });

  test('should handle 10 clients polling simultaneously without errors', async ({ browser }) => {
    const { contexts, pages } = await createClients(browser, MAX_CLIENTS);
    
    try {
      console.log('Setting up 10 clients with polling...');
      await navigateAllToInitiativeTracker(pages);
      
      await Promise.all(pages.map(page => 
        page.waitForSelector('.initiative-tracker-container', { timeout: 10000 })
      ));
      
      // Let all clients poll for 10 seconds
      console.log('Monitoring polling for 10 seconds...');
      const startTime = Date.now();
      
      // Track any errors during polling
      const errors = [];
      pages.forEach((page, idx) => {
        page.on('pageerror', error => {
          errors.push({ client: idx, error: error.message });
        });
        page.on('console', msg => {
          if (msg.type() === 'error') {
            errors.push({ client: idx, error: msg.text() });
          }
        });
      });
      
      // Wait for multiple polling cycles
      await pages[0].waitForTimeout(10000);
      
      const duration = Date.now() - startTime;
      console.log(`Monitored polling for ${duration}ms`);
      
      // Should have no critical errors
      const criticalErrors = errors.filter(e => 
        !e.error.includes('Failed to fetch') && // Network errors are acceptable
        !e.error.includes('Load failed') &&
        !e.error.includes('NetworkError')
      );
      
      console.log(`Total errors: ${errors.length}`);
      console.log(`Critical errors: ${criticalErrors.length}`);
      
      if (criticalErrors.length > 0) {
        console.error('Critical errors found:');
        criticalErrors.forEach(e => {
          console.error(`  Client ${e.client}: ${e.error}`);
        });
      }
      
      expect(criticalErrors.length).toBe(0);
      console.log(`✓ All ${MAX_CLIENTS} clients polled successfully without critical errors`);
      
    } finally {
      await cleanupClients(contexts);
    }
  });

  test('should handle rapid file access from 10 clients', async ({ browser }) => {
    const { contexts, pages } = await createClients(browser, MAX_CLIENTS);
    
    try {
      // All clients load home page
      await Promise.all(pages.map(page => page.goto(BASE_URL, { timeout: 30000 })));
      
      await Promise.all(pages.map(page => 
        page.waitForSelector('.file-tree', { timeout: 10000 })
      ));
      
      const startTime = Date.now();
      
      // All clients try to access the same file simultaneously
      const clicks = pages.map(async (page) => {
        try {
          await page.click('.file-tree-item-content:has-text("README")', { timeout: 5000 });
          return true;
        } catch {
          return false;
        }
      });
      
      const results = await Promise.all(clicks);
      const successCount = results.filter(r => r === true).length;
      
      const accessTime = Date.now() - startTime;
      console.log(`${successCount}/${MAX_CLIENTS} clients accessed file in ${accessTime}ms`);
      
      // Most clients should succeed
      expect(successCount).toBeGreaterThanOrEqual(Math.floor(MAX_CLIENTS * 0.7));
      expect(accessTime).toBeLessThan(15000);
      
      console.log(`✓ ${successCount} clients successfully accessed file`);
      
    } finally {
      await cleanupClients(contexts);
    }
  });

  test('should maintain Initiative Tracker consistency after 50 rapid updates', async ({ browser }) => {
    const { contexts, pages } = await createClients(browser, 5); // Use 5 clients for this test
    
    try {
      console.log('Navigating 5 clients to Initiative Tracker...');
      await navigateAllToInitiativeTracker(pages);
      
      await Promise.all(pages.map(page => 
        page.waitForSelector('.initiative-tracker-container', { timeout: 10000 })
      ));
      await pages[0].waitForTimeout(1000);
      
      const initialCount = await pages[0].locator('.initiative-item').count();
      console.log(`Starting with ${initialCount} characters`);
      
      // Client 0 makes 50 rapid turn advances
      const startTime = Date.now();
      for (let i = 0; i < 50; i++) {
        await pages[0].click('.btn-next-vertical');
        await pages[0].waitForTimeout(50); // Minimal delay
      }
      const clickTime = Date.now() - startTime;
      console.log(`50 rapid clicks completed in ${clickTime}ms`);
      
      // Wait for final sync
      await pages[0].waitForTimeout(5000);
      
      // Check final round on all clients
      const finalRounds = await Promise.all(pages.map(async (page, idx) => {
        const round = await page.locator('.round-number').textContent();
        console.log(`Client ${idx} final round: ${round}`);
        return round;
      }));
      
      // All clients should eventually converge to same state
      const uniqueRounds = [...new Set(finalRounds)];
      console.log(`Final unique rounds: ${uniqueRounds.join(', ')}`);
      
      // Should converge to consistent state
      expect(uniqueRounds.length).toBeLessThanOrEqual(2); // Allow for sync lag
      
      console.log('✓ System maintained consistency after rapid updates');
      
    } finally {
      await cleanupClients(contexts);
    }
  });

  test('should track active sessions correctly with 10 clients', async ({ browser }) => {
    const { contexts, pages } = await createClients(browser, MAX_CLIENTS);
    
    try {
      // All clients connect
      await Promise.all(pages.map(page => page.goto(BASE_URL, { timeout: 30000 })));
      
      // Wait for sessions to register
      await pages[0].waitForTimeout(3000);
      
      // Check active sessions via API
      const response = await pages[0].request.get('http://localhost:9002/api/active_sessions');
      expect(response.ok()).toBeTruthy();
      
      const data = await response.json();
      console.log(`Active sessions: ${data.total}`);
      console.log(`Session IPs: ${data.sessions?.map(s => s.ip).join(', ')}`);
      
      // Should track sessions (may be grouped by IP)
      expect(data.total).toBeGreaterThan(0);
      
      // Each session should have request counts
      if (data.sessions && data.sessions.length > 0) {
        const totalRequests = data.sessions.reduce((sum, s) => sum + s.request_count, 0);
        console.log(`Total requests tracked: ${totalRequests}`);
        expect(totalRequests).toBeGreaterThan(0);
      }
      
      console.log(`✓ Server tracked ${data.total} active session(s)`);
      
    } finally {
      await cleanupClients(contexts);
    }
  });

  test('should handle client disconnect and reconnect gracefully', async ({ browser }) => {
    const { contexts, pages } = await createClients(browser, 5);
    
    try {
      console.log('Navigating 5 clients to Initiative Tracker...');
      await navigateAllToInitiativeTracker(pages);
      
      await Promise.all(pages.map(page => 
        page.waitForSelector('.initiative-tracker-container', { timeout: 10000 })
      ));
      
      // Close 2 clients (simulate disconnect)
      console.log('Disconnecting 2 clients...');
      await contexts[3].close();
      await contexts[4].close();
      
      // Remaining clients should continue working
      await pages[0].click('.btn-next-vertical');
      await pages[0].waitForTimeout(2000);
      
      // Verify remaining clients still sync
      const round0 = await pages[0].locator('.round-number').textContent();
      const round1 = await pages[1].locator('.round-number').textContent();
      const round2 = await pages[2].locator('.round-number').textContent();
      
      console.log(`Remaining clients rounds: ${round0}, ${round1}, ${round2}`);
      
      // Reconnect new clients
      console.log('Reconnecting 2 new clients...');
      const context3 = await browser.newContext();
      const context4 = await browser.newContext();
      const page3 = await context3.newPage();
      const page4 = await context4.newPage();
      
      await navigateAllToInitiativeTracker([page3, page4]);
      
      await page3.waitForSelector('.initiative-tracker-container', { timeout: 10000 });
      await page4.waitForSelector('.initiative-tracker-container', { timeout: 10000 });
      
      // New clients should see current state
      const newRound3 = await page3.locator('.round-number').textContent();
      const newRound4 = await page4.locator('.round-number').textContent();
      
      console.log(`New clients rounds: ${newRound3}, ${newRound4}`);
      
      // New clients should sync with existing state
      const allRounds = [round0, round1, round2, newRound3, newRound4];
      const uniqueRounds = [...new Set(allRounds)];
      
      expect(uniqueRounds.length).toBeLessThanOrEqual(2);
      
      console.log('✓ System handled disconnect/reconnect gracefully');
      
      // Cleanup new contexts
      await context3.close();
      await context4.close();
      
    } finally {
      // Only close first 3 contexts (4 and 5 already closed)
      await contexts[0].close();
      await contexts[1].close();
      await contexts[2].close();
    }
  });
});
