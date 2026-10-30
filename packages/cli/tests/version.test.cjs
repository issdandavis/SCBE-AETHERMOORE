const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');
const PACKAGE = require('../package.json');

function runCli(args) {
  return spawnSync(process.execPath, [CLI, ...args], {
    encoding: 'utf8',
    env: { ...process.env, NO_COLOR: '1' },
  });
}

test('documented global version aliases print the CLI package version', () => {
  for (const alias of ['--version', '-v']) {
    const result = runCli([alias]);
    assert.equal(result.status, 0, `${alias}: ${result.stderr}`);
    assert.equal(result.stdout.trim(), PACKAGE.version);
    assert.equal(result.stderr, '');
  }
});

test('global version aliases preserve the structured JSON option', () => {
  for (const alias of ['--version', '-v']) {
    const result = runCli([alias, '--json']);
    assert.equal(result.status, 0, `${alias}: ${result.stderr}`);
    const payload = JSON.parse(result.stdout);
    assert.equal(payload.schema_version, 'scbe_aethermoore_cli_version_v1');
    assert.equal(payload.cli_version, PACKAGE.version);
  }
});
