'use strict';

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');

function seedLog() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-utt-cli-'));
  const logPath = path.join(dir, 'u.jsonl');
  const rows = [
    {
      utterance: 'scan my repo',
      tool: 'scbe-antivirus',
      score: 0.9,
      decision: 'ALLOW',
      confirmed: true,
    },
    {
      utterance: 'find federal grants',
      tool: 'research-sam-gov',
      score: 0.8,
      decision: 'ALLOW',
      confirmed: false,
    },
    {
      utterance: 'blocked attempt',
      tool: 'geoseal-seal',
      score: 0.7,
      decision: 'BLOCKED',
      confirmed: false,
    },
  ];
  const body = rows
    .map((r) => JSON.stringify({ v: 1, ts: '2026-06-06T12:00:00.000Z', ...r }))
    .join('\n');
  fs.writeFileSync(logPath, `${body}\n`);
  return logPath;
}

function run(args, logPath) {
  return spawnSync(process.execPath, [CLI, ...args], {
    encoding: 'utf8',
    timeout: 15_000,
    env: { ...process.env, SCBE_UTTERANCE_LOG: logPath, NO_COLOR: '1' },
  });
}

test('utterances export emits per-tool corpus and excludes BLOCKED routes', () => {
  const logPath = seedLog();
  const r = run(['utterances', 'export'], logPath);
  assert.equal(r.status, 0, r.stderr);
  const corpus = JSON.parse(r.stdout);
  assert.deepEqual(corpus['scbe-antivirus'], ['scan my repo']);
  assert.deepEqual(corpus['research-sam-gov'], ['find federal grants']);
  assert.equal(Object.prototype.hasOwnProperty.call(corpus, 'geoseal-seal'), false);
});

test('utterances export --confirmed keeps only approved routes', () => {
  const logPath = seedLog();
  const r = run(['utterances', 'export', '--confirmed'], logPath);
  assert.equal(r.status, 0, r.stderr);
  const corpus = JSON.parse(r.stdout);
  assert.deepEqual(corpus['scbe-antivirus'], ['scan my repo']);
  assert.equal(Object.prototype.hasOwnProperty.call(corpus, 'research-sam-gov'), false);
});

test('utterances export --min filters by confidence', () => {
  const logPath = seedLog();
  const r = run(['utterances', 'export', '--min', '0.85'], logPath);
  assert.equal(r.status, 0, r.stderr);
  const corpus = JSON.parse(r.stdout);
  assert.deepEqual(corpus['scbe-antivirus'], ['scan my repo']); // 0.9 kept
  assert.equal(Object.prototype.hasOwnProperty.call(corpus, 'research-sam-gov'), false); // 0.8 dropped
});

test('utterances export --out writes corpus to a file', () => {
  const logPath = seedLog();
  const outPath = `${logPath}.corpus.json`;
  const r = run(['utterances', 'export', '--out', outPath], logPath);
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /wrote \d+ tool\(s\) ->/);
  const corpus = JSON.parse(fs.readFileSync(outPath, 'utf8'));
  assert.ok(corpus['scbe-antivirus']);
});

test('utterances stats reports totals as JSON', () => {
  const logPath = seedLog();
  const r = run(['utterances', 'stats'], logPath);
  assert.equal(r.status, 0, r.stderr);
  const s = JSON.parse(r.stdout);
  assert.equal(s.total, 3);
  assert.equal(s.tools, 3);
});

test('utterances path prints the configured log path', () => {
  const logPath = seedLog();
  const r = run(['utterances', 'path'], logPath);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.stdout.trim(), logPath);
});

test('utterances help exits 0 and documents export', () => {
  const logPath = seedLog();
  const r = run(['utterances', 'help'], logPath);
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /export/);
  assert.match(r.stdout, /SCBE_NO_UTTERANCE_LOG/);
});
