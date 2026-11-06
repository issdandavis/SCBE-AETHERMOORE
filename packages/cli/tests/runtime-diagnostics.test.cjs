'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { spawnSync } = require('node:child_process');
const { processDiagnosis, probe } = require('../lib/process-diagnostics');
const { createShellResolver } = require('../lib/native-shell');
const { createCliHost } = require('../lib/cli-host');

test('distinguishes OS launch failures, timeouts, sign-in and service authorization', () => {
  for (const [child, expected] of [
    [{ error: { code: 'EACCES' } }, 'permission_denied'],
    [{ error: { code: 'ENOENT' } }, 'missing_executable'],
    [{ error: { code: 'EINVAL' } }, 'startup_failed'],
    [{ error: { code: 'ETIMEDOUT' } }, 'timeout'],
    [{ error: { code: 'ENOBUFS' } }, 'output_limit'],
    [{ status: 1, stderr: 'Get-CimInstance Access is denied 0x80041003' }, 'permission_denied'],
    [{ status: 1, stderr: 'Google OAuth invalid_grant: expired token' }, 'authentication_required'],
    [{ status: 1, stderr: 'HTTP 403: insufficient scopes' }, 'provider_access_denied'],
    [{ status: 0, stdout: 'permission denied is example text' }, 'ready'],
  ])
    assert.equal(processDiagnosis(child), expected);
});

test('probe is hidden, bounded and does not return raw secret-bearing output', () => {
  const row = probe(process.execPath, ['--version'], {
    spawn: (_exe, _args, options) => {
      assert.equal(options.shell, false);
      assert.equal(options.windowsHide, true);
      assert.equal(options.timeout, 2000);
      assert.equal(options.maxBuffer, 16384);
      return { status: 1, stderr: 'invalid_grant SECRET_MARKER' };
    },
  });
  assert.equal(row.status, 'authentication_required');
  assert.ok(!JSON.stringify(row).includes('SECRET_MARKER'));
});

test('PowerShell discovery records failures, falls back, caches and explicitly refreshes', () => {
  let calls = 0;
  const resolver = createShellResolver({
    platform: 'win32',
    env: { SCBE_POWERSHELL: 'blocked.exe', SystemRoot: 'C:\\Windows' },
    resolve: (name) => name,
    spawn: (exe, args, options) => {
      calls++;
      assert.equal(options.windowsHide, true);
      assert.ok(args.includes('-NoProfile'));
      return exe === 'blocked.exe' ? { error: { code: 'EACCES' } } : { status: 0, stdout: '7.6.4' };
    },
  });
  const report = resolver.inspect();
  assert.equal(report.selected, 'pwsh');
  assert.equal(report.attempts[0].status, 'permission_denied');
  assert.equal(report.attempts[1].version, '7.6.4');
  assert.equal(resolver.resolve(), 'pwsh');
  assert.equal(calls, 2);
  resolver.inspect(true);
  assert.equal(calls, 4);
});

test('no backend and unexpected successful output cannot masquerade as usable PowerShell', () => {
  const resolver = createShellResolver({
    platform: 'win32',
    env: {},
    resolve: (name) => name,
    spawn: () => ({ status: 0, stdout: 'a different program' }),
  });
  assert.equal(resolver.resolve(), null);
  assert.equal(resolver.inspect().status, 'shell_unavailable');
  assert.ok(resolver.inspect().attempts.every((row) => row.status === 'invalid_probe_output'));
});

test('owner extensions are inspected without executing their script or arguments', () => {
  const host = createCliHost({
    entries: [
      {
        name: 'node',
        executable: process.execPath,
        args: ['-e', 'throw Error("DO_NOT_RUN")'],
        description: 'Owner override',
      },
    ],
  });
  const row = host.diagnose().find((item) => item.name === 'node');
  assert.equal(row.status, 'not_probed');
  assert.equal(row.authentication, 'not_checked');
  assert.ok(!JSON.stringify(row).includes('DO_NOT_RUN'));
});

test('real command-session diagnosis correlates replies and does not claim account authentication', (t) => {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'geoseal-diagnostic-'));
  t.after(() => {
    assert.ok(path.resolve(folder).startsWith(path.resolve(os.tmpdir()) + path.sep));
    fs.rmSync(folder, { recursive: true, force: true });
  });
  const script = path.resolve(__dirname, '../bin/geoseal.js');
  const child = spawnSync(process.execPath, [script, 'shell', '--agent-json'], {
    input: '{"id":"d","op":"diagnose"}\n{"id":"s","op":"status"}\n',
    cwd: folder,
    encoding: 'utf8',
    windowsHide: true,
    timeout: 45000,
    env: {
      ...process.env,
      SCBE_HOME: folder,
      SCBE_PROVIDER: 'offline',
      SCBE_FORCE_SKIP_LIBOQS: '1',
    },
  });
  assert.equal(child.status, 0, child.stderr + child.stdout);
  const rows = child.stdout.trim().split('\n').map(JSON.parse);
  assert.deepEqual(
    rows.slice(1).map((row) => row.id),
    ['d', 's']
  );
  assert.equal(rows[1].result.schema_version, 'geoseal.runtime_diagnostics.v1');
  assert.match(rows[1].result.authentication, /not_checked/);
  assert.equal(rows[1].result.tools.find((tool) => tool.name === 'node').status, 'ready');
  assert.equal(rows[2].ok, true);
});
