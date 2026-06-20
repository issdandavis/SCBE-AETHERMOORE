'use strict';

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const router = require('../lib/utterance-router.js');
const log = require('../lib/utterance-log.js');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');

function tmpLog() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-utt-router-'));
  return path.join(dir, 'utterance-log.jsonl');
}

function runCli(args, options = {}) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-utt-router-'));
  const env = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
    NO_COLOR: '1',
    ...(options.env || {}),
  };
  return spawnSync(process.execPath, [CLI, ...args], {
    encoding: 'utf8',
    timeout: options.timeout || 15_000,
    env,
  });
}

test('utterance router chooses the closest learned command from corpus', () => {
  const corpus = {
    version: ['show local package manifest'],
    status: ['show current system state'],
  };

  const result = router.resolve('show local package manifest', corpus, {
    validCommands: ['version', 'status'],
  });

  assert.equal(result.resolved_command, 'version');
  assert.equal(result.source, 'utterance_corpus');
  assert.ok(result.confidence >= 0.99);
});

test('utterance router ignores labels that are not executable commands', () => {
  const corpus = {
    'not-a-command': ['show local package manifest'],
  };

  const result = router.resolve('show local package manifest', corpus, {
    validCommands: ['version'],
  });

  assert.equal(result.resolved_command, null);
  assert.equal(result.confidence, 0);
});

test('natural-language CLI can use learned corpus before static fallback', () => {
  const logPath = tmpLog();
  log.logUtterance(
    {
      utterance: 'show local package manifest',
      tool: 'version',
      score: 0.91,
      decision: 'ALLOW',
      confirmed: true,
    },
    { logPath, enabled: true }
  );

  const result = runCli(['show', 'local', 'package', 'manifest', '--json'], {
    env: { SCBE_UTTERANCE_LOG: logPath },
  });

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.resolved_command, 'version');
  assert.equal(payload.source, 'utterance_corpus');
  assert.equal(payload.executed, false);
});
