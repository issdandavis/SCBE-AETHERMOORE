'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { Readable, Writable } = require('node:stream');
const { spawnSync } = require('node:child_process');
const test = require('node:test');
const {
  boundedLines,
  runCommandShell,
  humanRequest,
  MAX_REQUEST_BYTES,
} = require('../lib/command-shell');
const CLI = path.resolve(__dirname, '..', 'bin', 'geoseal.js');

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'geoseal-command-test-'));
  fs.mkdirSync(path.join(root, 'folder with spaces'));
  fs.writeFileSync(path.join(root, 'folder with spaces', 'example.txt'), 'fixture');
  t.after(() => {
    assert.ok(path.resolve(root).startsWith(path.resolve(os.tmpdir()) + path.sep));
    fs.rmSync(root, { recursive: true, force: true });
  });
  return root;
}

function invoke(root, args, input) {
  return spawnSync(process.execPath, [CLI, ...args], {
    cwd: root,
    input,
    encoding: 'utf8',
    timeout: 45000,
    windowsHide: true,
    env: {
      ...process.env,
      HOME: root,
      USERPROFILE: root,
      SCBE_HOME: path.join(root, '.scbe'),
      SCBE_FORCE_SKIP_LIBOQS: '1',
      SCBE_PROVIDER: 'offline',
      NO_COLOR: '1',
    },
  });
}

test('bounded framing keeps Unicode across chunks and recovers after an oversized request', async () => {
  const unicode = Buffer.from('"café"\r\n');
  const input = Readable.from([
    unicode.subarray(0, 5),
    unicode.subarray(5),
    Buffer.alloc(MAX_REQUEST_BYTES + 1, 65),
    Buffer.from('\n{}'),
  ]);
  const frames = [];
  for await (const frame of boundedLines(input)) frames.push(frame);
  assert.deepEqual(frames, [{ line: '"café"' }, { error: 'request_too_large' }, { line: '{}' }]);
});

test('agent stream drains all buffered requests after EOF, including malformed input', async (t) => {
  const root = fixture(t);
  let captured = '';
  const output = new Writable({
    write(chunk, _enc, done) {
      captured += chunk;
      done();
    },
  });
  const code = await runCommandShell({
    cwd: root,
    json: true,
    output,
    input: Readable.from([
      '{"id":"first","op":"run","command":"first"}\nnot-json\n' +
        '{"id":"second","op":"run","command":"second"}\n{"id":"last","op":"status"}\n',
    ]),
    execute: async (command) => {
      await new Promise((resolve) => setTimeout(resolve, 20));
      return { success: true, stdout: command };
    },
  });
  const rows = captured.trim().split('\n').map(JSON.parse);
  assert.equal(code, 1);
  assert.equal(rows[0].ready, true);
  assert.deepEqual(
    rows.slice(1).map((r) => r.id),
    ['first', null, 'second', 'last']
  );
  assert.equal(rows[2].error.code, 'invalid_json');
  assert.equal(rows.at(-1).ok, true);
});

test('real GeoSeal entry point runs a pipeline in the changed directory and carries geo context', (t) => {
  const root = fixture(t);
  const command =
    process.platform === 'win32'
      ? 'Get-ChildItem -File | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress'
      : 'printf "example.txt\\n" | sort';
  const input =
    [
      { id: 'cd', op: 'cd', path: 'folder with spaces' },
      { id: 'geo', op: 'geo', task: 'compile and test the code' },
      { id: 'run', op: 'run', command },
      { id: 'bus', op: 'bus' },
      { id: 'last', op: 'status' },
    ]
      .map(JSON.stringify)
      .join('\n') + '\n';
  const result = invoke(root, ['shell', '--agent-json'], input);
  assert.equal(result.status, 0, result.stderr + result.stdout);
  const rows = result.stdout.trim().split('\n').map(JSON.parse);
  assert.equal(rows.length, 6);
  assert.deepEqual(
    rows.slice(1).map((r) => r.id),
    ['cd', 'geo', 'run', 'bus', 'last']
  );
  assert.match(rows[3].result.stdout, /example.txt/);
  assert.equal(rows[3].result.coordination.domain, 'CA');
  assert.equal(rows[3].result.governance.allowed, true);
  assert.equal(rows[3].session.cwd, fs.realpathSync(path.join(root, 'folder with spaces')));
  assert.equal(rows[4].result.result.mode, 'local_receipt');
  assert.match(rows[4].result.receipt_id, /^evt_/);
  const historyDir = path.join(root, '.scbe', 'command-history');
  const historyFile = fs.readdirSync(historyDir)[0];
  const history = JSON.parse(fs.readFileSync(path.join(historyDir, historyFile), 'utf8').trim());
  assert.equal(history.coordination.domain, 'CA');
  assert.equal(history.command, command);
  assert.equal(history.stdout, undefined, 'full command output is not duplicated into history');
});

test('nonzero native exit returns failure but the next request still runs', (t) => {
  const root = fixture(t);
  const result = invoke(
    root,
    ['shell', '--agent-json'],
    [
      { id: 'fail', op: 'run', command: 'node -e "process.exit(7)"' },
      { id: 'next', op: 'status' },
    ]
      .map(JSON.stringify)
      .join('\n')
  );
  const rows = result.stdout.trim().split('\n').map(JSON.parse);
  assert.equal(result.status, 1, result.stderr);
  assert.equal(rows[1].result.exit_code, 7);
  assert.equal(rows[1].ok, false);
  assert.equal(rows[2].id, 'next');
  assert.equal(rows[2].ok, true);
});

test(
  'command gate refusal survives geo context without executing the payload',
  { skip: process.platform !== 'win32' },
  (t) => {
    const root = fixture(t);
    const result = invoke(
      root,
      ['shell', '--agent-json'],
      [
        { id: 'geo', op: 'geo', task: 'compile the code' },
        { id: 'gate', op: 'run', command: "Invoke-Expression 'Write-Output SHOULD_NOT_RUN'" },
      ]
        .map(JSON.stringify)
        .join('\n')
    );
    const rows = result.stdout.trim().split('\n').map(JSON.parse);
    assert.equal(result.status, 1, result.stderr);
    assert.equal(rows[2].result.exit_code, 126);
    assert.equal(rows[2].result.governance.allowed, false);
    assert.equal(rows[2].result.stdout, undefined);
  }
);

test('human shell preserves literal paths and native command text', () => {
  assert.deepEqual(humanRequest('cd "folder with spaces"', '1'), {
    id: '1',
    op: 'cd',
    path: 'folder with spaces',
  });
  const command = 'Get-ChildItem | Where-Object { $_.Length -gt 0 }';
  assert.equal(humanRequest(command, '2').command, command);
  assert.deepEqual(humanRequest('ask explain this', '3'), { control: 'ask', text: 'explain this' });
});

test('bare GeoSeal starts the command shell without a model or banner on piped input', (t) => {
  const root = fixture(t);
  const result = invoke(root, [], 'cd "folder with spaces"\npwd\nexit\n');
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /folder with spaces/);
  assert.doesNotMatch(result.stdout, /you ›|provider|GeoSeal command shell/);
});

test('describe is machine-readable and reports operation fields and persistence limits', (t) => {
  const root = fixture(t);
  const result = invoke(root, ['shell', '--describe'], '');
  assert.equal(result.status, 0, result.stderr);
  const packet = JSON.parse(result.stdout);
  assert.deepEqual(packet.operations.run.fields, ['command', 'timeout_ms']);
  assert.equal(packet.persistence.native_shell_variables, false);
  assert.equal(packet.limits.output_bytes, 1048576);
});

test('legacy model-proposal protocol also drains requests buffered during a delayed turn', (t) => {
  const root = fixture(t);
  const cli = path.resolve(__dirname, '..', 'bin', 'scbe.js');
  const result = spawnSync(process.execPath, [cli, 'shell', '--agent-json'], {
    cwd: root,
    encoding: 'utf8',
    timeout: 15000,
    windowsHide: true,
    input: [1, 2, 3]
      .map((n) => JSON.stringify({ instruction: `inspect fixture ${n}`, reset_context: true }))
      .join('\n'),
    env: {
      ...process.env,
      HOME: root,
      USERPROFILE: root,
      SCBE_HOME: path.join(root, '.scbe'),
      SCBE_FORCE_SKIP_LIBOQS: '1',
      SCBE_MOCK_RESPONSE: '<cmd>echo fixture</cmd>',
      SCBE_MOCK_RESPONSE_DELAY_MS: '50',
      SCBE_AGENT_JSON_SKIP_GOVERNANCE: '1',
    },
  });
  assert.equal(result.status, 0, result.stderr);
  const rows = result.stdout.trim().split('\n').map(JSON.parse);
  assert.equal(rows.length, 4, result.stdout);
  assert.equal(rows[0].ready, true);
  assert.deepEqual(
    rows.slice(1).map((r) => r.board.objective),
    ['inspect fixture 1', 'inspect fixture 2', 'inspect fixture 3']
  );
});

test('native output is explicitly bounded and reports truncation', (t) => {
  const root = fixture(t);
  const result = invoke(
    root,
    ['shell', '--agent-json'],
    JSON.stringify({
      id: 'large',
      op: 'run',
      command: 'node -e "console.log(String.fromCharCode(120).repeat(1500000))"',
    })
  );
  const rows = result.stdout.trim().split('\n').map(JSON.parse);
  assert.equal(rows[1].result.output_truncated, true, result.stderr);
  assert.ok(Buffer.byteLength(rows[1].result.stdout + rows[1].result.stderr) <= 1048576);
});

test(
  'timeout and missing cmdlet fail without closing the session',
  { skip: process.platform !== 'win32' },
  (t) => {
    const root = fixture(t);
    const result = invoke(
      root,
      ['shell', '--agent-json'],
      [
        { id: 'timeout', op: 'run', command: 'Start-Sleep -Seconds 3', timeout_ms: 100 },
        { id: 'missing', op: 'run', command: 'Get-ScbeNonexistentFixtureCommand' },
        { id: 'alive', op: 'status' },
      ]
        .map(JSON.stringify)
        .join('\n')
    );
    const rows = result.stdout.trim().split('\n').map(JSON.parse);
    assert.equal(rows[1].ok, false);
    assert.equal(rows[1].result.process_error, 'ETIMEDOUT');
    assert.equal(rows[2].ok, false);
    assert.equal(rows[3].ok, true);
  }
);

test('timeout terminates the native command descendant tree', (t) => {
  const root = fixture(t);
  const marker = path.join(root, 'descendant-survived.txt');
  const leaf = path.join(root, 'timeout-leaf.cjs');
  const parent = path.join(root, 'timeout-parent.cjs');
  fs.writeFileSync(
    leaf,
    `setTimeout(() => require('node:fs').writeFileSync(${JSON.stringify(marker)}, 'survived'), 800);\n`
  );
  fs.writeFileSync(
    parent,
    `const { spawn } = require('node:child_process');\n` +
      `spawn(process.execPath, [${JSON.stringify(leaf)}], { stdio: 'ignore', windowsHide: true });\n` +
      `setTimeout(() => {}, 5000);\n`
  );
  const command = `node ${JSON.stringify(parent)}`;
  const result = invoke(
    root,
    ['shell', '--agent-json'],
    `${JSON.stringify({ id: 'timeout-tree', op: 'run', command, timeout_ms: 200 })}\n`
  );
  assert.equal(result.status, 1, result.stderr + result.stdout);
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 1200);
  assert.equal(fs.existsSync(marker), false, 'a timed-out command left a descendant running');
});

test('structured protocol preserves 500 correlated replies under burst input', (t) => {
  const root = fixture(t);
  const count = 500;
  const input =
    Array.from({ length: count }, (_, index) =>
      JSON.stringify({ id: `burst-${index}`, op: 'status' })
    ).join('\n') + '\n';
  const result = invoke(root, ['shell', '--agent-json'], input);
  assert.equal(result.status, 0, result.stderr + result.stdout);
  const rows = result.stdout.trim().split('\n').map(JSON.parse);
  assert.equal(rows.length, count + 1);
  assert.deepEqual(
    rows.slice(1).map((row) => row.id),
    Array.from({ length: count }, (_, index) => `burst-${index}`)
  );
  assert.deepEqual(
    rows.slice(1).map((row) => row.session.sequence),
    Array.from({ length: count }, (_, index) => index + 1)
  );
});

test('structured protocol rejects duplicate ids and continues the session', (t) => {
  const root = fixture(t);
  const input = [
    { id: 'once', op: 'status' },
    { id: 'once', op: 'describe' },
    { id: 'after', op: 'status' },
  ]
    .map(JSON.stringify)
    .join('\n');
  const result = invoke(root, ['shell', '--agent-json'], input);
  assert.equal(result.status, 1, result.stderr + result.stdout);
  const rows = result.stdout.trim().split('\n').map(JSON.parse);
  assert.equal(rows[1].ok, true);
  assert.deepEqual(rows[2].error, {
    code: 'duplicate_request_id',
    message: 'Request id has already been used in this session: once',
  });
  assert.equal(rows[3].id, 'after');
  assert.equal(rows[3].ok, true);
});

test('shell help exits and unknown flags fail instead of opening a different mode', (t) => {
  const root = fixture(t);
  const help = invoke(root, ['shell', '--help'], '');
  assert.equal(help.status, 0, help.stderr);
  assert.match(help.stdout, /GeoSeal command shell/);
  const unknown = invoke(root, ['shell', '--agent-jsoon'], '');
  assert.equal(unknown.status, 2);
  assert.match(unknown.stderr, /unknown option/);
});
