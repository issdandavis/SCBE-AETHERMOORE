#!/usr/bin/env node
/* Run one TypeScript debug scenario from JSON and print one JSON receipt. */

const fs = require('node:fs');

require('ts-node/register/transpile-only');

const { runTypeScriptDebugScenario } = require('../src/game/typescriptDebugHarness.ts');

function readInput() {
  const fileIndex = process.argv.indexOf('--file');
  if (fileIndex >= 0) {
    const filePath = process.argv[fileIndex + 1];
    if (!filePath) {
      throw new Error('--file requires a path');
    }
    return fs.readFileSync(filePath, 'utf8');
  }

  const inlineIndex = process.argv.indexOf('--json');
  if (inlineIndex >= 0) {
    const value = process.argv[inlineIndex + 1];
    if (!value) {
      throw new Error('--json requires a JSON string');
    }
    return value;
  }

  if (!process.stdin.isTTY) {
    return fs.readFileSync(0, 'utf8');
  }

  throw new Error('Provide --file, --json, or stdin JSON');
}

function main() {
  const raw = readInput();
  const scenario = JSON.parse(raw);
  const receipt = runTypeScriptDebugScenario(scenario);
  process.stdout.write(`${JSON.stringify(receipt, null, 2)}\n`);
}

try {
  main();
} catch (error) {
  const message = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
  process.stderr.write(`${message}\n`);
  process.exit(1);
}
