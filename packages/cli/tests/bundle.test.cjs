const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');

function runCli(args, options = {}) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-bundle-home-'));
  const env = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
    NO_COLOR: '1',
  };
  return spawnSync(process.execPath, [CLI, ...args], {
    cwd: options.cwd || process.cwd(),
    input: options.input || '',
    encoding: 'utf8',
    timeout: options.timeout || 30_000,
    env,
  });
}

test('bundle help documents automatic file or text input', () => {
  const result = runCli(['bundle', 'help']);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /scbe bundle <file\|text>/);
  assert.match(result.stdout, /bundle verify/);
  assert.match(result.stdout, /binary-hex/);
});

test('bundle auto-creates from a source file and verifies current bytes', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-bundle-'));
  const source = path.join(dir, 'tool.py');
  const bundle = path.join(dir, 'bundle.json');
  fs.writeFileSync(source, 'def add(a, b):\n    return a + b\n', 'utf8');

  const created = runCli(['bundle', source, '--out', bundle, '--json']);
  assert.equal(created.status, 0, created.stderr);
  const payload = JSON.parse(created.stdout);
  assert.equal(payload.bundle.schema_version, 'scbe_polyglot_reaction_bundle_v1');
  assert.equal(payload.bundle.entries[0].kind, 'code');
  assert.equal(payload.bundle.entries[0].role, 'RU');
  assert.equal(payload.bundle.entries[0].language, 'python');
  assert.ok(fs.existsSync(bundle));

  const verified = runCli(['bundle', 'verify', '--bundle', bundle, '--json']);
  assert.equal(verified.status, 0, verified.stderr);
  const report = JSON.parse(verified.stdout);
  assert.equal(report.ok, true);
  assert.equal(report.bundle_hash_ok, true);
  assert.equal(report.entry_checks[0].ok, true);
});

test('bundle auto-creates from plain intent text when no file exists', () => {
  const result = runCli(['bundle', 'route chemistry code and binary together', '--json']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.bundle.entries[0].kind, 'text');
  assert.equal(payload.bundle.entries[0].role, 'KO');
  assert.match(payload.bundle.intent, /route chemistry code/);
  assert.equal(payload.bundle.classification, 'BIJECTIVE');
});

test('bundle add appends a chemistry tube and projection exposes binary hex route', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-bundle-add-'));
  const notes = path.join(dir, 'notes.txt');
  const smiles = path.join(dir, 'ethanol.smi');
  const bundle = path.join(dir, 'bundle.json');
  fs.writeFileSync(notes, 'main intent identity anchor\n', 'utf8');
  fs.writeFileSync(smiles, 'CCO\n', 'utf8');

  const created = runCli(['bundle', 'create', '--input', notes, '--out', bundle, '--json']);
  assert.equal(created.status, 0, created.stderr);

  const added = runCli(['bundle', 'add', '--bundle', bundle, '--file', smiles, '--json']);
  assert.equal(added.status, 0, added.stderr);
  const addPayload = JSON.parse(added.stdout);
  assert.equal(addPayload.bundle.entries.length, 2);
  assert.equal(addPayload.bundle.entries[1].kind, 'chem');
  assert.equal(addPayload.bundle.entries[1].language, 'smiles');

  const projection = runCli(['bundle', 'translate', '--bundle', bundle, '--to', 'binary-hex', '--json']);
  assert.equal(projection.status, 0, projection.stderr);
  const projected = JSON.parse(projection.stdout);
  assert.equal(projected.schema_version, 'scbe_polyglot_bundle_projection_v1');
  assert.equal(projected.entries.length, 2);
  assert.ok(projected.entries.every((entry) => entry.hex_preview));
});

test('bundle verify fails when source bytes drift after sealing', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-bundle-drift-'));
  const source = path.join(dir, 'tool.js');
  const bundle = path.join(dir, 'bundle.json');
  fs.writeFileSync(source, 'export const x = 1;\n', 'utf8');

  const created = runCli(['bundle', source, '--out', bundle, '--json']);
  assert.equal(created.status, 0, created.stderr);
  fs.writeFileSync(source, 'export const x = 2;\n', 'utf8');

  const verified = runCli(['bundle', 'verify', '--bundle', bundle, '--json']);
  assert.equal(verified.status, 1);
  const report = JSON.parse(verified.stdout);
  assert.equal(report.ok, false);
  assert.equal(report.bundle_hash_ok, true);
  assert.equal(report.entry_checks[0].ok, false);
});
