const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const test = require('node:test');

const BIN = path.resolve(__dirname, '..', 'bin', 'scbe.js');

test('demo fallback denies the built-in destructive secret-cleanup command', () => {
  const result = spawnSync(process.execPath, [BIN, 'demo', '--json'], {
    cwd: path.resolve(__dirname, '..'),
    encoding: 'utf8',
    env: { ...process.env, SCBE_FORCE_GATE_FALLBACK: '1' },
  });

  assert.equal(result.status, 0, result.stderr);
  const packet = JSON.parse(result.stdout);
  assert.equal(packet.decision, 'DENY');
  assert.equal(packet.geoseal.allowed, false);
  assert.equal(packet.output, 'Blocked unsafe tool execution request before it reached the shell.');
  assert.match(packet.suggested_correction, /Do not execute/);
  assert(packet.reasons.some((reason) => reason.includes('fallback.secret_path')));
});
