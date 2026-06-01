#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const pkgRoot = path.resolve(__dirname, '..');
const { planResearchVaultPacket } = require(path.join(pkgRoot, 'dist', 'index.js'));

function usage() {
  process.stderr.write(
    [
      'Usage:',
      '  node research_vault_plan.cjs --file packet-input.json',
      '  node research_vault_plan.cjs \'{"query":"...","source_cards":[...]}\'',
      '',
    ].join('\n')
  );
}

function readInput(argv) {
  const fileIndex = argv.indexOf('--file');
  if (fileIndex >= 0) {
    const file = argv[fileIndex + 1];
    if (!file) throw new Error('--file requires a path');
    return fs.readFileSync(path.resolve(file), 'utf8');
  }
  const joined = argv
    .filter((arg) => arg !== '--json')
    .join(' ')
    .trim();
  if (!joined) throw new Error('missing Research Vault JSON input');
  return joined;
}

try {
  const raw = readInput(process.argv.slice(2));
  const input = JSON.parse(raw);
  const plan = planResearchVaultPacket(input);
  process.stdout.write(`${JSON.stringify(plan, null, 2)}\n`);
  if (plan.governance.decision === 'DENY') process.exitCode = 3;
} catch (err) {
  process.stderr.write(
    `${JSON.stringify(
      {
        schema_version: 'scbe.agent_bus.research_vault_error.v1',
        error: err instanceof Error ? err.message : String(err),
      },
      null,
      2
    )}\n`
  );
  usage();
  process.exitCode = 1;
}
