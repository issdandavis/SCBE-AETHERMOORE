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
  assert.match(result.stdout, /scbe react code/);
  assert.match(result.stdout, /scbe react balance/);
  assert.match(result.stdout, /scbe react geometry/);
  assert.match(result.stdout, /scbe react audio/);
});

test('react balance emits an exactly balanced, audit-verifiable receipt', () => {
  const result = runCli(['react', 'balance', '--reactants', 'C3H8,O2', '--products', 'CO2,H2O', '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_react_balance_v1');
  assert.equal(payload.ok, true);
  assert.equal(payload.equation, 'C3H8 + 5 O2 -> 3 CO2 + 4 H2O');
  assert.deepEqual(payload.coefficients, [1, 5, 3, 4]);
  const packet = payload.reaction_state_packet;
  assert.equal(packet.classification, 'BIJECTIVE');

  // The receipt must survive the audit lane: the hash always verifies; when a
  // signer backend exists the signature must verify too (never report false).
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-balance-receipt-'));
  const packetPath = path.join(dir, 'packet.json');
  fs.writeFileSync(packetPath, JSON.stringify(packet));
  const audit = runCli(['react', 'audit', '--packet', packetPath, '--json']);
  assert.equal(audit.status, 0, audit.stderr);
  const auditPayload = JSON.parse(audit.stdout);
  assert.equal(auditPayload.ok, true);
  const row = auditPayload.packets[0];
  assert.equal(row.hash_ok, true);
  assert.notEqual(row.signature_verified, false, 'signed receipt failed signature verification');
  if (packet.signature_alg) {
    assert.equal(row.signature_verified, true);
  }
});

test('react geometry classifies CO2 as a linear rotor', (t) => {
  const result = runCli(['react', 'geometry', '--smiles', 'O=C=O', '--json']);
  const payload = JSON.parse(result.stdout);
  if (!payload.ok && /RDKit is required/i.test(payload.error || '')) {
    t.skip('RDKit not installed in this environment');
    return;
  }
  assert.equal(result.status, 0, result.stderr);
  assert.equal(payload.schema_version, 'scbe_react_geometry_v1');
  assert.equal(payload.ok, true);
  assert.equal(payload.rotor_type, 'linear');
  assert.equal(payload.reaction_state_packet.classification, 'LOSSY_RECOVERABLE');
});

test('react audit verifies packets from compound benchmark reports', () => {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-compound-react-'));
  const bench = runCli(['bench', 'compound-decompose', '--out-dir', outDir, '--json'], {
    timeout: 90_000,
  });
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
  const bench = runCli(['bench', 'compound-decompose', '--out-dir', outDir, '--json'], {
    timeout: 90_000,
  });
  assert.equal(bench.status, 0, bench.stderr);

  const reportPath = path.join(outDir, 'latest_report.json');
  const result = runCli([
    'react',
    'compare',
    '--left',
    reportPath,
    '--right',
    reportPath,
    '--json',
  ]);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_reaction_compare_v1');
  assert.equal(payload.left_packet_count, 30);
  assert.equal(payload.right_packet_count, 30);
  assert.equal(payload.classification_changed, false);
  assert.equal(payload.shared_packet_hashes.length, 30);
});

test('react code emits a bijective packet for identical files', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-react-code-'));
  const source = path.join(dir, 'source.py');
  const target = path.join(dir, 'target.py');
  fs.writeFileSync(source, 'print("same")\n');
  fs.writeFileSync(target, 'print("same")\n');

  const result = runCli(['react', 'code', '--source', source, '--target', target, '--json']);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_react_code_v1');
  assert.equal(payload.ok, true);
  assert.equal(payload.reaction_state_packet.domain, 'code');
  assert.equal(payload.reaction_state_packet.classification, 'BIJECTIVE');
});

test('react audio emits an observable packet with declared magnetoelastic model', () => {
  const result = runCli([
    'react',
    'audio',
    '--frequency',
    '440',
    '--model',
    'magnetoelastic',
    '--json',
  ]);
  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_react_audio_v1');
  assert.equal(payload.ok, true);
  assert.equal(payload.reaction_state_packet.domain, 'audio');
  assert.equal(payload.observables.field_relationship, 'strain-magnetization coupling proxy');
  assert.equal(typeof payload.observables.stability, 'number');
});
