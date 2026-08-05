#!/usr/bin/env node

/**
 * Extract test results with screenshots and video paths
 * Usage: node extract-test-results.js [--failed-only]
 */

const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const failedOnly = args.includes('--failed-only');

const resultsPath = path.join(__dirname, 'test-results', 'test-results.json');
const reportDir = path.join(__dirname, 'playwright-report');

if (!fs.existsSync(resultsPath)) {
  console.error('❌ No test results found. Run "npm test" first.');
  process.exit(1);
}

const results = JSON.parse(fs.readFileSync(resultsPath, 'utf-8'));

console.log('# Playwright Test Results\n');
console.log(`**Date:** ${new Date().toISOString()}\n`);
console.log(`**Total:** ${results.suites.reduce((sum, s) => sum + s.specs.length, 0)} tests`);
console.log(`**Duration:** ${(results.stats.duration / 1000).toFixed(2)}s\n`);

// Extract all test specs
const allTests = [];
results.suites.forEach(suite => {
  suite.specs.forEach(spec => {
    spec.tests.forEach(test => {
      test.results.forEach(result => {
        allTests.push({
          suite: suite.title,
          file: suite.file,
          title: spec.title,
          status: result.status,
          duration: result.duration,
          error: result.error,
          attachments: result.attachments || []
        });
      });
    });
  });
});

// Filter if needed
const testsToShow = failedOnly 
  ? allTests.filter(t => t.status !== 'passed' && t.status !== 'skipped')
  : allTests;

if (testsToShow.length === 0) {
  console.log('✅ All tests passed! No failures to report.\n');
  process.exit(0);
}

// Group by status
const grouped = {
  failed: testsToShow.filter(t => t.status === 'failed'),
  passed: testsToShow.filter(t => t.status === 'passed'),
  flaky: testsToShow.filter(t => t.status === 'flaky'),
  skipped: testsToShow.filter(t => t.status === 'skipped')
};

// Output results
Object.entries(grouped).forEach(([status, tests]) => {
  if (tests.length === 0) return;
  
  console.log(`\n## ${status.toUpperCase()} (${tests.length})\n`);
  
  tests.forEach((test, idx) => {
    console.log(`### ${idx + 1}. ${test.title}`);
    console.log(`- **File:** \`${test.file}\``);
    console.log(`- **Suite:** ${test.suite}`);
    console.log(`- **Duration:** ${test.duration}ms`);
    console.log(`- **Status:** ${test.status}`);
    
    if (test.error) {
      console.log(`- **Error:**`);
      console.log('```');
      console.log(test.error.message || test.error);
      console.log('```');
    }
    
    if (test.attachments.length > 0) {
      console.log(`- **Attachments:**`);
      test.attachments.forEach(att => {
        const relativePath = path.relative(process.cwd(), att.path || '');
        console.log(`  - ${att.name}: \`${relativePath}\``);
        
        // For screenshots and videos, also output absolute path
        if (att.contentType && (att.contentType.includes('image') || att.contentType.includes('video'))) {
          console.log(`    - Absolute: \`${att.path}\``);
        }
      });
    }
    
    console.log('');
  });
});

// Summary
console.log('\n## Summary\n');
console.log('| Status | Count |');
console.log('|--------|-------|');
Object.entries(grouped).forEach(([status, tests]) => {
  if (tests.length > 0) {
    const emoji = status === 'passed' ? '✅' : status === 'failed' ? '❌' : '⚠️';
    console.log(`| ${emoji} ${status} | ${tests.length} |`);
  }
});

// Output paths summary
console.log('\n## Artifact Locations\n');
console.log(`- **JSON Report:** \`${resultsPath}\``);
console.log(`- **HTML Report:** \`${reportDir}/index.html\``);
console.log(`- **Test Results:** \`test-results/\``);
console.log(`- **Screenshots:** \`test-results/*/test-failed-*.png\``);
console.log(`- **Videos:** \`test-results/*/video.webm\``);
console.log(`- **Traces:** \`test-results/*/trace.zip\``);

console.log('\n---');
console.log('💡 **Tip:** Open HTML report with `npm run test:report`');
console.log('💡 **Tip:** View trace files with `npx playwright show-trace <trace-file>`\n');
