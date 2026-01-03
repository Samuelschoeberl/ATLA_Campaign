#!/usr/bin/env node
/**
 * Test Results Analyzer
 * 
 * Analyzes Playwright test output from terminal and categorizes errors:
 * - Frontend errors (React, JavaScript)
 * - Backend errors (API, server)
 * - Test errors (selectors, timeouts)
 * - Infrastructure errors (ports, servers not starting)
 * 
 * Usage:
 *   npm test 2>&1 | node analyze-test-results.js
 *   node analyze-test-results.js < test-output.txt
 *   node analyze-test-results.js --file test-output.txt
 *   node analyze-test-results.js --json-report playwright-report/results.json
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');

// ANSI color codes
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  white: '\x1b[37m',
  gray: '\x1b[90m',
  bold: '\x1b[1m',
};

// Error categorization patterns
const errorPatterns = {
  frontend: {
    name: 'Frontend Errors',
    color: colors.red,
    patterns: [
      /Uncaught.*Error/i,
      /React.*error/i,
      /console\.error/i,
      /Cannot read propert/i,
      /undefined is not/i,
      /null is not an object/i,
      /TypeError.*component/i,
      /<anonymous>:\d+:\d+/,
      /at Object\.<anonymous>/,
      /pageerror/i,
    ],
  },
  backend: {
    name: 'Backend/API Errors',
    color: colors.magenta,
    patterns: [
      /api\/.* failed/i,
      /fetch.*\/api\//i,
      /500 Internal Server Error/i,
      /404.*api/i,
      /CORS/i,
      /Failed to fetch/i,
      /Network request failed/i,
      /ERR_CONNECTION_REFUSED/i,
      /Flask/i,
    ],
  },
  test: {
    name: 'Test Code Issues',
    color: colors.yellow,
    patterns: [
      /locator.*not found/i,
      /Timeout.*waiting for/i,
      /selector.*not found/i,
      /expect.*toBeVisible/i,
      /expect.*toBe/i,
      /waitFor.*timeout/i,
      /Element is not visible/i,
      /No element found/i,
    ],
  },
  infrastructure: {
    name: 'Infrastructure Issues',
    color: colors.cyan,
    patterns: [
      /EADDRINUSE/i,
      /port.*already in use/i,
      /Server.*not ready/i,
      /Health check.*failed/i,
      /webServer.*failed/i,
      /Could not start.*server/i,
      /Connection refused/i,
      /localhost:\d+.*refused/i,
      /ModuleNotFoundError/i,
      /ImportError/i,
      /No module named/i,
      /Process from config\.webServer/i,
      /Exit code:/i,
    ],
  },
};

// Statistics
const stats = {
  total: 0,
  passed: 0,
  failed: 0,
  skipped: 0,
  errors: {
    frontend: [],
    backend: [],
    test: [],
    infrastructure: [],
    uncategorized: [],
  },
  tests: [],
};

function categorizeError(errorText) {
  for (const [category, config] of Object.entries(errorPatterns)) {
    for (const pattern of config.patterns) {
      if (pattern.test(errorText)) {
        return category;
      }
    }
  }
  return 'uncategorized';
}

function parseTestLine(line) {
  // Match test result lines
  const testMatch = line.match(/([✓✗×]) (.+?) \((\d+(?:ms|s))\)/);
  if (testMatch) {
    const [, status, name, duration] = testMatch;
    stats.total++;
    if (status === '✓') {
      stats.passed++;
    } else {
      stats.failed++;
    }
    stats.tests.push({ name, status, duration });
    return true;
  }
  
  // Match error lines
  const errorMatch = line.match(/Error:|Failed:|TypeError:|ReferenceError:|at /);
  if (errorMatch) {
    const category = categorizeError(line);
    stats.errors[category].push(line.trim());
    return true;
  }
  
  return false;
}

function processStream(stream) {
  return new Promise((resolve) => {
    const rl = readline.createInterface({
      input: stream,
      crlfDelay: Infinity,
    });

    rl.on('line', (line) => {
      parseTestLine(line);
    });

    rl.on('close', () => {
      resolve();
    });
  });
}

function printReport() {
  console.log(`\n${colors.bold}${colors.blue}═══════════════════════════════════════════════════════════════${colors.reset}`);
  console.log(`${colors.bold}${colors.blue}   TEST RESULTS ANALYSIS${colors.reset}`);
  console.log(`${colors.bold}${colors.blue}═══════════════════════════════════════════════════════════════${colors.reset}\n`);

  // Summary
  console.log(`${colors.bold}Summary:${colors.reset}`);
  console.log(`  Total Tests: ${stats.total}`);
  console.log(`  ${colors.green}✓ Passed: ${stats.passed}${colors.reset}`);
  console.log(`  ${colors.red}✗ Failed: ${stats.failed}${colors.reset}`);
  console.log(`  ${colors.gray}⊘ Skipped: ${stats.skipped}${colors.reset}\n`);

  // Error breakdown
  const hasErrors = Object.values(stats.errors).some(arr => arr.length > 0);
  
  if (hasErrors) {
    console.log(`${colors.bold}Error Breakdown:${colors.reset}\n`);
    
    for (const [category, config] of Object.entries(errorPatterns)) {
      const errors = stats.errors[category];
      if (errors.length > 0) {
        console.log(`${config.color}${colors.bold}▸ ${config.name} (${errors.length}):${colors.reset}`);
        const uniqueErrors = [...new Set(errors)].slice(0, 5);
        uniqueErrors.forEach(err => {
          console.log(`  ${colors.gray}•${colors.reset} ${err.substring(0, 100)}...`);
        });
        if (errors.length > 5) {
          console.log(`  ${colors.gray}... and ${errors.length - 5} more${colors.reset}`);
        }
        console.log('');
      }
    }
    
    // Uncategorized errors
    if (stats.errors.uncategorized.length > 0) {
      console.log(`${colors.yellow}${colors.bold}▸ Uncategorized Errors (${stats.errors.uncategorized.length}):${colors.reset}`);
      const uniqueErrors = [...new Set(stats.errors.uncategorized)].slice(0, 3);
      uniqueErrors.forEach(err => {
        console.log(`  ${colors.gray}•${colors.reset} ${err.substring(0, 100)}...`);
      });
      if (stats.errors.uncategorized.length > 3) {
        console.log(`  ${colors.gray}... and ${stats.errors.uncategorized.length - 3} more${colors.reset}`);
      }
      console.log('');
    }
  }

  // Recommendations
  console.log(`${colors.bold}${colors.cyan}Recommendations:${colors.reset}\n`);
  
  if (stats.errors.infrastructure.length > 0) {
    console.log(`  ${colors.cyan}⚡${colors.reset} Infrastructure issues detected. Try:`);
    
    // Check for Python module errors
    const hasPythonModuleError = stats.errors.infrastructure.some(err => 
      err.includes('ModuleNotFoundError') || err.includes('No module named')
    );
    
    if (hasPythonModuleError) {
      console.log(`     ${colors.gray}• Install Python dependencies:${colors.reset}`);
      console.log(`     ${colors.gray}  pip install flask flask-cors${colors.reset}`);
      console.log(`     ${colors.gray}• Or activate your Python virtual environment${colors.reset}`);
    } else {
      console.log(`     ${colors.gray}FORCE_KILL=1 npm test${colors.reset}`);
      console.log(`     ${colors.gray}lsof -ti:9002,5173 | xargs kill -9${colors.reset}`);
    }
    console.log('');
  }
  
  if (stats.errors.backend.length > 0) {
    console.log(`  ${colors.magenta}🔌${colors.reset} Backend issues detected. Check:`);
    console.log(`     ${colors.gray}• Flask server logs${colors.reset}`);
    console.log(`     ${colors.gray}• API endpoint availability${colors.reset}`);
    console.log(`     ${colors.gray}• CORS configuration${colors.reset}\n`);
  }
  
  if (stats.errors.frontend.length > 0) {
    console.log(`  ${colors.red}⚛️${colors.reset}  Frontend errors detected. Review:`);
    console.log(`     ${colors.gray}• Browser console output${colors.reset}`);
    console.log(`     ${colors.gray}• Component error boundaries${colors.reset}`);
    console.log(`     ${colors.gray}• Uncaught exceptions in code${colors.reset}\n`);
  }
  
  if (stats.errors.test.length > 0) {
    console.log(`  ${colors.yellow}🧪${colors.reset} Test code issues. Consider:`);
    console.log(`     ${colors.gray}• Updating selectors${colors.reset}`);
    console.log(`     ${colors.gray}• Increasing timeouts${colors.reset}`);
    console.log(`     ${colors.gray}• Adding better wait conditions${colors.reset}\n`);
  }

  // Next steps
  if (stats.failed > 0) {
    console.log(`${colors.bold}Next Steps:${colors.reset}`);
    console.log(`  1. View detailed report: ${colors.cyan}npm run test:report${colors.reset}`);
    console.log(`  2. Run tests with UI: ${colors.cyan}npm run test:ui${colors.reset}`);
    console.log(`  3. Debug specific test: ${colors.cyan}npm run test:debug${colors.reset}`);
    console.log(`  4. Check screenshots: ${colors.gray}test-results/${colors.reset}\n`);
  }

  console.log(`${colors.bold}${colors.blue}═══════════════════════════════════════════════════════════════${colors.reset}\n`);
}

async function main() {
  const args = process.argv.slice(2);
  
  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
${colors.bold}Test Results Analyzer${colors.reset}

Analyzes Playwright test output and categorizes errors.

${colors.bold}Usage:${colors.reset}
  npm test 2>&1 | node analyze-test-results.js
  node analyze-test-results.js --file test-output.txt
  node analyze-test-results.js --json-report playwright-report/results.json

${colors.bold}Options:${colors.reset}
  --file <path>         Read test output from file
  --json-report <path>  Analyze JSON report from Playwright
  --help, -h            Show this help message

${colors.bold}Categories:${colors.reset}
  • Frontend Errors      - React, JavaScript, browser errors
  • Backend/API Errors   - Server, API, CORS issues
  • Test Code Issues     - Selectors, timeouts, assertions
  • Infrastructure       - Ports, server startup problems
`);
    return;
  }

  const fileIndex = args.indexOf('--file');
  const jsonIndex = args.indexOf('--json-report');

  if (fileIndex !== -1 && args[fileIndex + 1]) {
    const filePath = args[fileIndex + 1];
    const stream = fs.createReadStream(filePath);
    await processStream(stream);
  } else if (jsonIndex !== -1 && args[jsonIndex + 1]) {
    // TODO: Implement JSON report parsing
    console.error('JSON report parsing not yet implemented');
    process.exit(1);
  } else if (!process.stdin.isTTY) {
    // Read from stdin
    await processStream(process.stdin);
  } else {
    console.error('Error: No input provided. Use --file or pipe test output.');
    console.error('Run with --help for usage information.');
    process.exit(1);
  }

  printReport();
  
  // Exit with appropriate code
  process.exit(stats.failed > 0 ? 1 : 0);
}

if (require.main === module) {
  main().catch(err => {
    console.error('Error:', err);
    process.exit(1);
  });
}

module.exports = { categorizeError, parseTestLine, stats };
