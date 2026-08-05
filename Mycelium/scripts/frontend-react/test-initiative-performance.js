const fetch = require('node-fetch');

const API_BASE_URL = 'http://localhost:3001';
const filePath = 'Player Root/Initiative Tracker.md';

async function testReadPerformance() {
  console.log('\n=== Testing Initiative Tracker Read Performance ===\n');
  
  const times = [];
  for (let i = 0; i < 10; i++) {
    const start = Date.now();
    const response = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`);
    await response.json();
    const duration = Date.now() - start;
    times.push(duration);
    console.log(`Read ${i + 1}: ${duration}ms`);
  }
  
  const avg = times.reduce((a, b) => a + b, 0) / times.length;
  const max = Math.max(...times);
  const min = Math.min(...times);
  
  console.log(`\nRead Performance:`);
  console.log(`  Average: ${avg.toFixed(0)}ms`);
  console.log(`  Min: ${min}ms`);
  console.log(`  Max: ${max}ms`);
  
  return { avg, max, min };
}

async function testWritePerformance() {
  console.log('\n=== Testing Initiative Tracker Write Performance ===\n');
  
  // Get current content first
  const readResponse = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`);
  const data = await readResponse.json();
  const originalContent = data.content;
  
  const times = [];
  for (let i = 0; i < 10; i++) {
    const start = Date.now();
    await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: originalContent }),
    });
    const duration = Date.now() - start;
    times.push(duration);
    console.log(`Write ${i + 1}: ${duration}ms`);
    
    // Small delay to avoid overwhelming the server
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  const avg = times.reduce((a, b) => a + b, 0) / times.length;
  const max = Math.max(...times);
  const min = Math.min(...times);
  
  console.log(`\nWrite Performance:`);
  console.log(`  Average: ${avg.toFixed(0)}ms`);
  console.log(`  Min: ${min}ms`);
  console.log(`  Max: ${max}ms`);
  
  return { avg, max, min };
}

async function testRoundTripLatency() {
  console.log('\n=== Testing Round-Trip Sync Latency ===\n');
  
  // Write then immediately read
  const times = [];
  for (let i = 0; i < 5; i++) {
    const readResponse = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`);
    const data = await readResponse.json();
    const content = data.content;
    
    // Modify content slightly
    const modifiedContent = content.replace(/Round:\*\* (\d+)/, (match, num) => `Round:** ${parseInt(num) + 1}`);
    
    const start = Date.now();
    
    // Write
    await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: modifiedContent }),
    });
    
    // Immediately read back
    const verifyResponse = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`);
    await verifyResponse.json();
    
    const duration = Date.now() - start;
    times.push(duration);
    console.log(`Round-trip ${i + 1}: ${duration}ms`);
    
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  
  const avg = times.reduce((a, b) => a + b, 0) / times.length;
  const max = Math.max(...times);
  const min = Math.min(...times);
  
  console.log(`\nRound-Trip Latency:`);
  console.log(`  Average: ${avg.toFixed(0)}ms`);
  console.log(`  Min: ${min}ms`);
  console.log(`  Max: ${max}ms`);
  
  return { avg, max, min };
}

async function main() {
  try {
    const readStats = await testReadPerformance();
    const writeStats = await testWritePerformance();
    const roundTripStats = await testRoundTripLatency();
    
    console.log('\n\n=== SUMMARY ===\n');
    console.log(`Read:       ${readStats.avg.toFixed(0)}ms avg (${readStats.min}-${readStats.max}ms)`);
    console.log(`Write:      ${writeStats.avg.toFixed(0)}ms avg (${writeStats.min}-${writeStats.max}ms)`);
    console.log(`Round-Trip: ${roundTripStats.avg.toFixed(0)}ms avg (${roundTripStats.min}-${roundTripStats.max}ms)`);
    
    console.log('\n=== ANALYSIS ===\n');
    if (readStats.avg > 100) {
      console.log('⚠️  Read performance is SLOW (>100ms average)');
    } else {
      console.log('✅ Read performance is acceptable');
    }
    
    if (writeStats.avg > 200) {
      console.log('⚠️  Write performance is SLOW (>200ms average)');
    } else {
      console.log('✅ Write performance is acceptable');
    }
    
    if (roundTripStats.avg > 500) {
      console.log('⚠️  Round-trip sync is VERY SLOW (>500ms average)');
      console.log('   This explains why tests are timing out.');
    } else if (roundTripStats.avg > 300) {
      console.log('⚠️  Round-trip sync is SLOW (>300ms average)');
    } else {
      console.log('✅ Round-trip sync is acceptable');
    }
    
    console.log('\nExpected sync time for 1-second polling:');
    console.log(`  Best case: ${roundTripStats.min}ms (write + next poll)`);
    console.log(`  Average:   ${Math.round(roundTripStats.avg + 500)}ms (write + half poll interval)`);
    console.log(`  Worst case: ${roundTripStats.max + 1000}ms (write + full poll interval)`);
    
  } catch (error) {
    console.error('Error running tests:', error);
  }
}

main();
