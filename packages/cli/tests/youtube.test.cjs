const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');

function runCli(args) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-youtube-home-'));
  return spawnSync(process.execPath, [CLI, ...args], {
    encoding: 'utf8',
    timeout: 30_000,
    env: {
      ...process.env,
      HOME: home,
      USERPROFILE: home,
      NO_COLOR: '1',
    },
  });
}

function writePackage(data) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-youtube-package-'));
  const file = path.join(dir, 'package.json');
  fs.writeFileSync(file, JSON.stringify(data, null, 2));
  return file;
}

test('youtube review passes a complete package', () => {
  const file = writePackage({
    title: 'How I Automate My YouTube Workflow Without Losing Control',
    description: 'A practical walkthrough of a local-first workflow for creators with review gates and manual approval.',
    tags: ['youtube automation', 'creator tools', 'workflow'],
    script: Array.from({ length: 50 }, () => 'safe automation').join(' '),
    privacy: 'unlisted',
  });

  const result = runCli(['youtube', 'review', file, '--json']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_youtube_package_review_v1');
  assert.equal(payload.decision, 'PASS');
  assert.ok(payload.score >= 90);
});

test('youtube review fails invalid privacy and empty description', () => {
  const file = writePackage({
    title: 'Tiny',
    description: '',
    tags: [],
    privacy: 'auto-public-now',
  });

  const result = runCli(['youtube', 'review', file, '--json']);

  assert.equal(result.status, 1, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.decision, 'FAIL');
  assert.ok(payload.findings.some((finding) => finding.field === 'privacy' && finding.severity === 'fail'));
  assert.ok(payload.findings.some((finding) => finding.field === 'description' && finding.severity === 'fail'));
});

test('help documents youtube package review', () => {
  const result = runCli(['--help']);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /youtube review <file>/);
});
