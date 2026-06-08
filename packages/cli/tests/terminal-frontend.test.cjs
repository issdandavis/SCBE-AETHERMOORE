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
  assert.match(result.stdout, /scbe terminal bench/);
  assert.match(result.stdout, /scbe term\s+Short alias for terminal/);
  assert.match(result.stdout, /scbe exec npm test/);
  assert.match(result.stdout, /scbe x git status --short/);
});

test('bare scbe opens the compact terminal panel instead of the long manual', () => {
  const result = runCli([]);

  assert.equal(result.status, 0, result.stderr);
  assert.doesNotMatch(result.stdout, new RegExp(ESC));
  assert.match(result.stdout, /SCBE TERMINAL/);
  assert.match(result.stdout, /Quick nav/);
  assert.doesNotMatch(result.stdout, /scbe-aethermoore-cli/);
});

test('terminal --json emits parseable frontend state for agents', () => {
  const result = runCli(['terminal', '--json']);

  assert.equal(result.status, 0, result.stderr);
  assert.doesNotMatch(result.stdout, new RegExp(ESC));
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_terminal_frontend_v1');
  assert.equal(payload.title, 'SCBE Terminal Frontend');
  assert.ok(payload.launch.headless.includes('agent-json'));
  assert.equal(payload.launch.token_exec, 'scbe x <program> [args...]');
  assert.ok(payload.quick_commands.some((entry) => entry.command === 'scbe term'));
  assert.ok(payload.quick_commands.some((entry) => entry.command === 'scbe x <cmd>'));
  assert.ok(payload.modes.some((entry) => entry.id === 'token_exec'));
  assert.equal(payload.natural_language.autocorrect, true);
  assert.equal(typeof payload.natural_language.word_count, 'number');
});

test('exec runs command tokens through the governed receipt path', () => {
  const result = runCli(['exec', '--json', 'node', '--version']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_terminal_run_v1');
  assert.equal(payload.command, 'node --version');
  assert.equal(payload.success, true);
  assert.match(payload.stdout_preview, /^v\d+\./);
  assert.equal(payload.compass.lane, 'node');
});

test('x is a short alias for exec', () => {
  const result = runCli(['x', '--json', 'node', '--version']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_terminal_run_v1');
  assert.equal(payload.command, 'node --version');
  assert.equal(payload.success, true);
});

test('terminal alias renders compact human navigation without ANSI under NO_COLOR', () => {
  const result = runCli(['term']);

  assert.equal(result.status, 0, result.stderr);
  assert.doesNotMatch(result.stdout, new RegExp(ESC));
  assert.match(result.stdout, /SCBE TERMINAL/);
  assert.match(result.stdout, /Quick nav/);
  assert.match(result.stdout, /scbe term tui/);
  assert.match(result.stdout, /Last receipt/);
  assert.match(result.stdout, /Inputs/);
  assert.match(result.stdout, /More: scbe term --detail/);
});

test('terminal help is short and command-focused', () => {
  const result = runCli(['ui', 'help']);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Usage:/);
  assert.match(result.stdout, /scbe terminal --detail/);
  assert.match(result.stdout, /scbe terminal bench/);
  assert.match(result.stdout, /Aliases:/);
  assert.match(result.stdout, /Shell grammar:/);
});

test('terminal bench emits measured JSON scenarios', () => {
  const result = runCli(['term', 'bench', '--runs', '1', '--json'], { timeout: 30_000 });

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_terminal_frontend_benchmark_v1');
  assert.equal(payload.runs, 1);
  assert.ok(payload.scenarios.length >= 3);
  assert.ok(payload.scenarios.every((scenario) => scenario.ok));
  assert.ok(payload.scenarios.every((scenario) => scenario.median_ms > 0));
});

test('rich shell accepts slash terminal navigation', () => {
  const result = runCli(['shell'], {
    input: '/term\n:exit\n',
    env: { SCBE_MOCK_RESPONSE: 'should-not-call-model' },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /SCBE TERMINAL/);
  assert.match(result.stdout, /Quick nav/);
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
