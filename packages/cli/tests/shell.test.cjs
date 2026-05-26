const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');

function runCli(args, options = {}) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-shell-'));
  const env = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
    NO_COLOR: '1',
  };
  return spawnSync(process.execPath, [CLI, ...args], {
    input: options.input || '',
    encoding: 'utf8',
    timeout: options.timeout || 15_000,
    env,
  });
}

test('help documents governed shell modes', () => {
  const result = runCli(['--help']);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /scbe shell\s+Governed AI shell/);
  assert.match(result.stdout, /scbe shell --ai/);
  assert.match(result.stdout, /scbe shell --tui/);
  assert.match(result.stdout, /scbe shell --minimal/);
});

test('minimal shell preserves scriptable exit behavior', () => {
  const result = runCli(['shell', '--minimal'], { input: ':exit\n' });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /SCBE Terminal/);
  assert.doesNotMatch(result.stdout, /SCBE governed shell/);
});

test('rich shell supports config inspection without touching real home config', () => {
  const result = runCli(['shell'], { input: ':config\n:exit\n' });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /SCBE governed shell/);
  assert.match(result.stdout, /"provider": "ollama"/);
  assert.match(result.stdout, /"model": "llama3\.2"/);
});

test('tui.mjs exists and exports launchTui', async () => {
  const { pathToFileURL } = require('node:url');
  const tuiPath = path.resolve(__dirname, '..', 'bin', 'tui.mjs');
  assert.ok(fs.existsSync(tuiPath), 'bin/tui.mjs must exist');
  const m = await import(pathToFileURL(tuiPath).href);
  assert.equal(typeof m.launchTui, 'function', 'tui.mjs must export launchTui');
});
