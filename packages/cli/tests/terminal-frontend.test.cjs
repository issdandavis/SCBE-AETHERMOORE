'use strict';

const assert = require('node:assert/strict');
const { spawn, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');
const ESC = '\x1b';

// The `scbe desktop` subsystem is backed by packages/polly-pad-os, an R&D
// package that is intentionally NOT shipped on main / in the published CLI
// package (see CLAUDE.md push policy). When it is absent the command degrades
// honestly (exit 0, package_exists:false), so these backing-dependent tests
// skip rather than fail. A full source checkout that has the package runs them
// for real.
const DESKTOP_BACKING = fs.existsSync(
  path.resolve(__dirname, '..', '..', 'polly-pad-os', 'package.json')
);
const DESKTOP_SKIP = DESKTOP_BACKING
  ? false
  : 'requires packages/polly-pad-os (full source checkout, not shipped on main)';

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

async function withBrowserFixture(run) {
  const fixtureCode = [
    "const http = require('node:http');",
    "const html = '<!doctype html><html><head><title>SCBE Browser Fixture</title></head><body><main><h1>SCBE browser fixture</h1></main></body></html>';",
    "const server = http.createServer((_req, res) => { res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }); res.end(html); });",
    "server.listen(0, '127.0.0.1', () => process.stdout.write(String(server.address().port) + '\\n'));",
    "process.on('SIGTERM', () => server.close(() => process.exit(0)));",
  ].join('');
  const fixture = spawn(process.execPath, ['-e', fixtureCode], {
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const port = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('browser fixture did not start')), 5_000);
    fixture.once('error', reject);
    fixture.stdout.once('data', (chunk) => {
      clearTimeout(timer);
      resolve(Number.parseInt(String(chunk).trim(), 10));
    });
  });
  try {
    return await run(`http://127.0.0.1:${port}/`);
  } finally {
    fixture.kill();
  }
}

function skipWhenBrowserIsAbsent(t, result) {
  const output = `${result.stdout || ''}\n${result.stderr || ''}`;
  const systemLaunchWasAttempted = output.includes('executablePath=');
  const runtimeIsAbsent = output.includes('No Playwright runtime available');
  const bundledBrowserIsAbsent = output.includes("Executable doesn't exist at");
  if (runtimeIsAbsent || (!systemLaunchWasAttempted && bundledBrowserIsAbsent)) {
    t.skip('requires a local Chromium-compatible browser executable');
    return true;
  }
  return false;
}

test('help documents the terminal frontend and short aliases', () => {
  const result = runCli(['--help']);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /scbe terminal\s+Compact terminal front end/);
  assert.match(result.stdout, /scbe advisor\s+"suggest next step"/);
  assert.match(result.stdout, /scbe terminal tui/);
  assert.match(result.stdout, /scbe terminal --json/);
  assert.match(result.stdout, /scbe terminal bench/);
  assert.match(result.stdout, /scbe term\s+Short alias for terminal/);
  assert.match(result.stdout, /scbe desktop\s+Portable desktop subsystem/);
  assert.match(result.stdout, /scbe actions\s+List true action bundles/);
  assert.match(result.stdout, /scbe action desktop\.open\s+Run one action bundle/);
  assert.match(result.stdout, /scbe format --dry-run/);
  assert.match(result.stdout, /scbe prepush --dry-run/);
  assert.match(result.stdout, /scbe commit -m/);
  assert.match(result.stdout, /scbe exec npm test/);
  assert.match(result.stdout, /scbe x git status --short/);
});

test('bare scbe opens the conversational agent instead of the terminal panel or manual', () => {
  const result = runCli([]);

  assert.equal(result.status, 0, result.stderr);
  assert.doesNotMatch(result.stdout, new RegExp(ESC));
  assert.match(result.stdout, /SCBE agent/);
  assert.match(result.stdout, /you ›/);
  assert.doesNotMatch(result.stdout, /SCBE TERMINAL|Quick nav/);
  assert.doesNotMatch(result.stdout, /scbe-aethermoore-cli/);
});

test('terminal --json emits parseable frontend state for agents', () => {
  const result = runCli(['terminal', '--json']);

  assert.equal(result.status, 0, result.stderr);
  assert.doesNotMatch(result.stdout, new RegExp(ESC));
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_terminal_frontend_v1');
  assert.equal(payload.title, 'SCBE Terminal Frontend');
  assert.equal(payload.launch.advisor, 'scbe advisor "<request>"');
  assert.ok(payload.launch.headless.includes('agent-json'));
  assert.equal(payload.launch.token_exec, 'scbe x <program> [args...]');
  assert.deepEqual(payload.aliases, []);
  assert.ok(payload.quick_commands.some((entry) => entry.command === 'scbe term'));
  assert.ok(payload.quick_commands.some((entry) => entry.command === 'scbe advisor "<request>"'));
  assert.ok(
    payload.quick_commands.some(
      (entry) => entry.command === 'scbe desktop browse https://example.com --json'
    )
  );
  assert.ok(
    payload.quick_commands.some((entry) => entry.command === 'scbe desktop capture --json')
  );
  assert.ok(payload.quick_commands.some((entry) => entry.command === 'scbe actions'));
  assert.ok(payload.quick_commands.some((entry) => entry.command === 'scbe x <cmd>'));
  assert.ok(payload.quick_commands.some((entry) => entry.command === 'scbe alias g <cmd>'));
  assert.ok(payload.modes.some((entry) => entry.id === 'token_exec'));
  assert.ok(payload.modes.some((entry) => entry.id === 'advisor'));
  assert.ok(payload.actions.some((entry) => entry.id === 'terminal.panel'));
  assert.ok(payload.actions.some((entry) => entry.id === 'desktop.open'));
  assert.ok(payload.actions.some((entry) => entry.id === 'desktop.browser-open'));
  assert.ok(payload.actions.some((entry) => entry.id === 'desktop.capture'));
  assert.match(payload.action_history_path, /scbe-actions[\\/]+history\.jsonl$/);
  assert.equal(payload.natural_language.autocorrect, true);
  assert.equal(typeof payload.natural_language.word_count, 'number');
  assert.ok(payload.command_grammar.some((entry) => entry.syntax === '/advisor <request>'));
  assert.ok(payload.command_grammar.some((entry) => entry.syntax === '/browser <url>'));
  assert.ok(payload.command_grammar.some((entry) => entry.syntax === '/capture [url]'));
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

test('x uses PowerShell semantics on Windows', { skip: process.platform !== 'win32' }, () => {
  const binDir = path.resolve(__dirname, '..', 'bin');
  const result = runCli(['x', '--json', 'Get-ChildItem', '-Name', binDir]);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_terminal_run_v1');
  assert.match(payload.command, /^Get-ChildItem -Name /);
  assert.equal(payload.success, true);
  assert.match(payload.stdout_preview, /scbe\.js/);
});

test('terminal alias renders compact human navigation without ANSI under NO_COLOR', () => {
  const result = runCli(['term']);

  assert.equal(result.status, 0, result.stderr);
  assert.doesNotMatch(result.stdout, new RegExp(ESC));
  assert.match(result.stdout, /SCBE TERMINAL/);
  assert.match(result.stdout, /Quick nav/);
  assert.match(result.stdout, /Action cards/);
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

test('desktop subsystem emits portable desktop status JSON', { skip: DESKTOP_SKIP }, () => {
  const result = runCli(['desktop', '--json']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_portable_desktop_status_v1');
  assert.match(payload.desktop_root, /packages[\\/]+polly-pad-os$/);
  assert.equal(payload.package_name, 'polly-pad-os');
  assert.ok(payload.app_count >= 80);
  assert.equal(payload.launcher_commands.open, 'scbe desktop open');
});

test('desktop subsystem emits app capability benchmark JSON', { skip: DESKTOP_SKIP }, () => {
  const result = runCli(['desktop', 'app-bench', '--json']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_polly_app_capability_benchmark_v1');
  assert.equal(payload.summary.total, 82);
  assert.equal(payload.summary.real, 4);
  assert.equal(payload.summary.runtime_open_passed, payload.summary.runtime_open_total);
  assert.equal(payload.summary.component_mapped_passed, payload.summary.component_mapped_total);
  assert.ok(payload.summary.download_ready > 0);
  assert.ok(payload.goals.some((goal) => goal.id === 'g3-download-ready-backlog'));
  assert.ok(
    payload.tasks.some((task) => task.app_id === 'browser' && task.capability_status === 'real')
  );
  assert.ok(
    payload.tasks.some(
      (task) => task.app_id === 'codeeditor' && task.capability_status === 'download-ready'
    )
  );
});

test('desktop subsystem can open a real browser page as JSON', async (t) => {
  await withBrowserFixture(async (url) => {
    const result = runCli(['desktop', 'browse', url, '--json'], {
      timeout: 45_000,
    });

    if (skipWhenBrowserIsAbsent(t, result)) return;
    assert.equal(result.status, 0, result.stderr);
    const payload = JSON.parse(result.stdout);
    assert.equal(payload.schema_version, 'scbe_browser_page_v1');
    assert.equal(payload.success, true);
    assert.equal(payload.title, 'SCBE Browser Fixture');
    assert.equal(payload.final_url || payload.requested_url, url);
    assert.ok(payload.bytes > 0);
  });
});

test('desktop subsystem can capture a real page as JSON', async (t) => {
  await withBrowserFixture(async (url) => {
    const result = runCli(['desktop', 'capture', url, '--json'], {
      timeout: 45_000,
    });

    if (skipWhenBrowserIsAbsent(t, result)) return;
    assert.equal(result.status, 0, result.stderr);
    const payload = JSON.parse(result.stdout);
    assert.equal(payload.schema_version, 'scbe_screen_capture_v1');
    assert.equal(payload.success, true);
    assert.equal(payload.url, url);
    assert.ok(payload.bytes > 0);
  });
});

test(
  'desktop subsystem dry-runs open and pack without launching a browser',
  { skip: DESKTOP_SKIP },
  () => {
    const open = runCli(['desktop', 'open', '--dry-run', '--json', '--port', '3111']);
    assert.equal(open.status, 0, open.stderr);
    const openPayload = JSON.parse(open.stdout);
    assert.equal(openPayload.schema_version, 'scbe_portable_desktop_open_v1');
    assert.equal(openPayload.url, 'http://127.0.0.1:3111/');
    assert.equal(openPayload.bridge_url, 'http://127.0.0.1:3678');
    assert.match(openPayload.bridge_command, /desktop_subsystem\.cjs bridge --port 3678/);
    assert.equal(openPayload.dry_run, true);

    const pack = runCli(['desktop', 'pack', '--dry-run', '--json']);
    assert.equal(pack.status, 0, pack.stderr);
    const packPayload = JSON.parse(pack.stdout);
    assert.equal(packPayload.schema_version, 'scbe_portable_desktop_pack_v1');
    assert.match(packPayload.out_path, /scbe-portable-desktop\.zip$/);
    assert.equal(packPayload.dry_run, true);
  }
);

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

test('rich shell slash advisor uses the one-shot advisor lane', () => {
  const result = runCli(['shell'], {
    input: '/advisor suggest the next command\n:exit\n',
    env: { SCBE_MOCK_RESPONSE: 'advisor says use scbe test' },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /SCBE advisor/);
  assert.match(result.stdout, /advisor says use scbe test/);
});

test('rich shell slash browser uses the real browser capture lane', async (t) => {
  await withBrowserFixture(async (url) => {
    const result = runCli(['shell'], {
      input: `/browser ${url}\n:exit\n`,
      timeout: 45_000,
    });

    if (skipWhenBrowserIsAbsent(t, result)) return;
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /\[browser\].*desktop .*browse .*127\.0\.0\.1/i);
    assert.match(result.stdout, /SCBE Browser Fixture/);
    assert.doesNotMatch(result.stdout + result.stderr, /ParserError|Unexpected token|not recognized/);
  });
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
