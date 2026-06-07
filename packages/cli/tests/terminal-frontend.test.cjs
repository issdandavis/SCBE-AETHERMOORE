'use strict';

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');
const ESC = '\x1b';

function runCli(args, options = {}) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-terminal-'));
  const env = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
    NO_COLOR: '1',
    ...(options.env || {}),
  };
  const result = spawnSync(process.execPath, [CLI, ...args], {
    input: options.input || '',
    encoding: 'utf8',
    timeout: options.timeout || 20_000,
    env,
  });
  fs.rmSync(home, { recursive: true, force: true });
  return result;
}

test('help documents the terminal frontend and short aliases', () => {
  const result = runCli(['--help']);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /scbe terminal\s+Compact terminal front end/);
  assert.match(result.stdout, /scbe terminal tui/);
  assert.match(result.stdout, /scbe terminal --json/);
  assert.match(result.stdout, /scbe term\s+Short alias for terminal/);
});

test('terminal --json emits parseable frontend state for agents', () => {
  const result = runCli(['terminal', '--json']);

  assert.equal(result.status, 0, result.stderr);
  assert.doesNotMatch(result.stdout, new RegExp(ESC));
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_terminal_frontend_v1');
  assert.equal(payload.title, 'SCBE Terminal Frontend');
  assert.ok(payload.launch.headless.includes('agent-json'));
  assert.ok(payload.quick_commands.some((entry) => entry.command === 'scbe term'));
  assert.equal(payload.natural_language.autocorrect, true);
  assert.equal(typeof payload.natural_language.word_count, 'number');
});

test('terminal alias renders compact human navigation without ANSI under NO_COLOR', () => {
  const result = runCli(['term']);

  assert.equal(result.status, 0, result.stderr);
  assert.doesNotMatch(result.stdout, new RegExp(ESC));
  assert.match(result.stdout, /SCBE Terminal Frontend/);
  assert.match(result.stdout, /QUICK NAV/);
  assert.match(result.stdout, /scbe term tui/);
  assert.match(result.stdout, /NATURAL LANGUAGE/);
  assert.match(result.stdout, /COMMAND GRAMMAR/);
  assert.match(result.stdout, /More detail: scbe terminal --detail/);
});

test('terminal help is short and command-focused', () => {
  const result = runCli(['ui', 'help']);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Usage:/);
  assert.match(result.stdout, /scbe terminal --detail/);
  assert.match(result.stdout, /Aliases:/);
  assert.match(result.stdout, /Shell grammar:/);
});

test('rich shell accepts slash terminal navigation', () => {
  const result = runCli(['shell'], {
    input: '/term\n:exit\n',
    env: { SCBE_MOCK_RESPONSE: 'should-not-call-model' },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /SCBE Terminal Frontend/);
  assert.match(result.stdout, /QUICK NAV/);
  assert.doesNotMatch(result.stdout, /should-not-call-model/);
});

test('rich shell slash run writes a real command receipt path', () => {
  const result = runCli(['shell'], {
    input: '/run echo 2468\n:exit\n',
    env: { SCBE_MOCK_RESPONSE: 'should-not-call-model' },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /2468/);
  assert.doesNotMatch(result.stdout, /should-not-call-model/);
});

test('rich shell bracket command runs obvious command bodies through receipts', () => {
  const result = runCli(['shell'], {
    input: '[verify] echo 1357\n:exit\n',
    env: { SCBE_MOCK_RESPONSE: 'should-not-call-model' },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /\[verify\].*\$ echo 1357/);
  assert.match(result.stdout, /1357/);
  assert.doesNotMatch(result.stdout, /should-not-call-model/);
});
