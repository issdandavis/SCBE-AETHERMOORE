const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');

function runCli(args, options = {}) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-react-'));
  const env = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
    NO_COLOR: '1',
  };
  return spawnSync(process.execPath, [CLI, ...args], {
    input: options.input || '',
    encoding: 'utf8',
    timeout: options.timeout || 60_000,
    env,
  });
}

test('react help documents audit and compare commands', () => {
  const result = runCli(['react', 'help']);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /scbe react audit/);
  assert.match(result.stdout, /scbe react compare/);
});

test('react audit verifies packets from compound benchmark reports', () => {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-compound-react-'));
  const bench = runCli(['bench', 'compound-decompose', '--out-dir', outDir, '--json'], { timeout: 90_000 });
  assert.equal(bench.status, 0, bench.stderr);

  const reportPath = path.join(outDir, 'latest_report.json');
  const result = runCli(['react', 'audit', '--packet', reportPath, '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_reaction_audit_v1');
  assert.equal(payload.ok, true);
  assert.equal(payload.packet_count, 30);
  assert.ok(payload.packets.every((packet) => packet.hash_ok));
  assert.ok(payload.packets.every((packet) => packet.classification === 'LOSSY_RECOVERABLE'));
});

test('react compare reports shared packet hashes for identical reports', () => {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-compound-compare-'));
  const bench = runCli(['bench', 'compound-decompose', '--out-dir', outDir, '--json'], { timeout: 90_000 });
  assert.equal(bench.status, 0, bench.stderr);

  const reportPath = path.join(outDir, 'latest_report.json');
  const result = runCli(['react', 'compare', '--left', reportPath, '--right', reportPath, '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_reaction_compare_v1');
  assert.equal(payload.left_packet_count, 30);
  assert.equal(payload.right_packet_count, 30);
  assert.equal(payload.classification_changed, false);
  assert.equal(payload.shared_packet_hashes.length, 30);
});
