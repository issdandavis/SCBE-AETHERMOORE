'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { spawnSync } = require('node:child_process');
const { createCliHost, resolveNative } = require('../lib/cli-host');
const { humanRequest, loadCommandBus } = require('../lib/command-shell');
const CLI = path.resolve(__dirname, '..', 'bin', 'geoseal.js');

function fixture(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'geoseal-cli-host-'));
  t.after(() => {
    assert.ok(path.resolve(directory).startsWith(path.resolve(os.tmpdir()) + path.sep));
    assert.ok(path.basename(directory).startsWith('geoseal-cli-host-'));
    fs.rmSync(directory, { recursive: true, force: true });
  });
  return directory;
}

function invoke(directory, requests) {
  const processResult = spawnSync(process.execPath, [CLI, 'shell', '--agent-json'], {
    cwd: directory,
    input: requests.map(JSON.stringify).join('\n') + '\n',
    encoding: 'utf8',
    timeout: 45000,
    windowsHide: true,
    maxBuffer: 4 * 1048576,
    env: {
      ...process.env,
      SCBE_HOME: path.join(directory, '.scbe'),
      SCBE_FORCE_SKIP_LIBOQS: '1',
      SCBE_PROVIDER: 'offline',
      NO_COLOR: '1',
    },
  });
  assert.equal(processResult.error, undefined);
  assert.equal(processResult.stderr, '');
  const rows = processResult.stdout.trim().split('\n').map(JSON.parse);
  assert.equal(rows.shift().ready, true);
  return { code: processResult.status, rows };
}

test('discovery requires no executor or provider; configuration is frozen per session', (t) => {
  const directory = fixture(t);
  const configPath = path.join(directory, 'tools.json');
  const config = {
    schema_version: 'geoseal.cli_tools.v1',
    tools: [
      {
        name: 'fixture',
        executable: process.execPath,
        args: ['--version'],
        description: 'Fixture CLI.',
      },
    ],
  };
  fs.writeFileSync(configPath, JSON.stringify(config));
  const host = createCliHost({ configPath });
  fs.writeFileSync(configPath, '{}');
  assert.equal(host.list().tools.find((tool) => tool.name === 'fixture').available, true);
  assert.throws(() => createCliHost({ configPath }), { code: 'invalid_tool_config' });
  assert.ok(host.list().tools.some((tool) => tool.name === 'node' && tool.available));
});

test('PATH resolution ignores relative entries and shell shims', (t) => {
  const directory = fixture(t);
  fs.writeFileSync(path.join(directory, 'fake.cmd'), '@echo unexpected');
  assert.equal(resolveNative('fake', { PATH: '.' }, 'win32'), null);
  assert.equal(resolveNative('fake', { PATH: directory }, 'win32'), null);
});

test('host resolves only registered tools and forwards unchanged argv to the gate', async (t) => {
  const directory = fixture(t);
  const args = ['prefix'];
  const host = createCliHost({
    entries: [{ name: 'fixture', executable: process.execPath, args, description: 'Fixture.' }],
    execute: (_command, context) => ({ success: true, ...context }),
  });
  args.push('mutation');
  const context = { cwd: directory, timeoutMs: 77, geo: { task: 'model a cube' } };
  const reply = await host.execute('fixture', ['a b', ''], context);
  assert.deepEqual(reply.invocation.args, ['prefix', 'a b', '']);
  assert.equal(reply.cwd, directory);
  assert.equal(reply.timeoutMs, 77);
  assert.deepEqual(reply.geo, context.geo);
  await assert.rejects(host.execute('unknown', [], context), { code: 'unknown_tool' });
});

test('tools share request IDs, validation, FIFO and cwd with shell commands', async (t) => {
  const directory = fixture(t);
  const { CommandSession } = loadCommandBus();
  const called = [];
  const session = new CommandSession({
    cwd: directory,
    listTools: () => [],
    executeTool: async (name) => {
      await new Promise((resolve) => setTimeout(resolve, 10));
      called.push(name);
      return { success: name !== 'failure' };
    },
    execute: () => {
      called.push('run');
      return { success: true };
    },
  });
  const requests = [
    { id: 'first', op: 'tool', name: 'failure', args: [] },
    { id: 'second', op: 'run', command: 'anything' },
    { id: 'first', op: 'tool', name: 'duplicate', args: [] },
    { id: 'bad', op: 'tool', name: 'invalid', args: [null] },
    { id: 'nul', op: 'tool', name: 'invalid', args: ['\0'] },
    { id: 'large', op: 'tool', name: 'invalid', args: ['x'.repeat(65537)] },
    { id: 'path', op: 'tool', name: 'invalid', args: [], executable: process.execPath },
    { id: 'timeout', op: 'tool', name: 'invalid', args: [], timeout_ms: 300001 },
    { id: 'last', op: 'tools' },
  ];
  const results = await Promise.all(requests.map((request) => session.dispatch(request)));
  assert.deepEqual(called, ['failure', 'run']);
  assert.equal(results[0].ok, false);
  assert.equal(results[1].ok, true);
  assert.equal(results[2].error.code, 'duplicate_request_id');
  for (const reply of results.slice(3, -1)) assert.equal(reply.error.code, 'invalid_request');
  assert.equal(results.at(-1).ok, true);
  assert.equal(results.at(-1).session.sequence, requests.length);
});

test('real headless entry preserves empty/Unicode/metacharacter argv and changed cwd', (t) => {
  const directory = fixture(t);
  const childDir = path.join(directory, 'working directory');
  fs.mkdirSync(childDir);
  const script = path.join(directory, 'echo.cjs');
  fs.writeFileSync(
    script,
    'console.log(JSON.stringify({args:process.argv.slice(2),cwd:process.cwd()}));'
  );
  const args = [
    '',
    'a b',
    '"quoted"',
    "it's",
    'café 六',
    '$(1+1)',
    '; echo BAD',
    '| echo BAD',
    'trailing\\',
  ];
  const result = invoke(directory, [
    { id: 'cd', op: 'cd', path: childDir },
    { id: 'geo', op: 'geo', task: 'build a model' },
    { id: 'tool', op: 'tool', name: 'node', args: [script, ...args] },
    { id: 'list', op: 'tools' },
  ]);
  assert.equal(result.code, 0);
  const receipt = result.rows[2].result;
  assert.deepEqual(JSON.parse(receipt.stdout), { args, cwd: childDir });
  assert.equal(receipt.tool, 'node');
  assert.equal(receipt.governance.allowed, true);
  assert.equal(receipt.coordination.task, 'build a model');
  assert.equal(result.rows[3].ok, true);
});

test('real tool failures, timeouts, output limits and denied commands leave session usable', (t) => {
  const directory = fixture(t);
  const result = invoke(directory, [
    { id: 'bad', op: 'tool', name: 'node', args: ['-e', 'process.exit(7)'] },
    {
      id: 'timeout',
      op: 'tool',
      name: 'node',
      args: ['-e', 'setTimeout(()=>{},10000)'],
      timeout_ms: 200,
    },
    {
      id: 'output',
      op: 'tool',
      name: 'node',
      args: ['-e', "process.stdout.write('x'.repeat(2097152))"],
    },
    { id: 'deny', op: 'tool', name: 'node', args: ['-e', 'Remove-Item -Recurse'] },
    { id: 'last', op: 'status' },
  ]);
  assert.equal(result.code, 1);
  assert.equal(result.rows[0].result.exit_code, 7);
  assert.equal(result.rows[1].ok, false);
  assert.equal(result.rows[1].result.process_error, 'ETIMEDOUT');
  assert.equal(result.rows[2].result.output_truncated, true);
  assert.ok(Buffer.byteLength(result.rows[2].result.stdout) <= 1048576);
  assert.equal(result.rows[3].ok, false);
  assert.equal(result.rows[3].result.failure.kind, 'governance_block');
  assert.equal(result.rows.at(-1).ok, true);
});

test('owner-configured CLI runs through actual entry, missing tools return a correlated error', (t) => {
  const directory = fixture(t);
  const scbe = path.join(directory, '.scbe');
  fs.mkdirSync(scbe);
  fs.writeFileSync(
    path.join(scbe, 'geoseal-tools.json'),
    JSON.stringify({
      schema_version: 'geoseal.cli_tools.v1',
      tools: [
        {
          name: 'my-cli',
          executable: process.execPath,
          args: ['-e', "console.log('configured')"],
          description: 'Test CLI.',
        },
        {
          name: 'absent',
          executable: path.join(directory, 'missing.exe'),
          args: [],
          description: 'Unavailable.',
        },
      ],
    })
  );
  const result = invoke(directory, [
    { id: 'mine', op: 'tool', name: 'my-cli', args: [] },
    { id: 'absent', op: 'tool', name: 'absent', args: [] },
  ]);
  assert.equal(result.rows[0].result.stdout.trim(), 'configured');
  assert.equal(result.rows[1].id, 'absent');
  assert.equal(result.rows[1].error.code, 'tool_unavailable');
});

test('human tool syntax uses JSON argument boundaries and bad syntax stays a request', () => {
  assert.deepEqual(humanRequest('tool git ["status","--short"]', 'a'), {
    id: 'a',
    op: 'tool',
    name: 'git',
    args: ['status', '--short'],
  });
  assert.equal(humanRequest('tool git not-json', 'b').args, null);
});

test(
  'native tool timeout stops a descendant that demonstrably started',
  { skip: process.platform !== 'win32' },
  (t) => {
    const directory = fixture(t);
    const marker = path.join(directory, 'descendant-survived.txt');
    const leaf = path.join(directory, 'leaf.cjs');
    const parent = path.join(directory, 'parent.cjs');
    fs.writeFileSync(
      leaf,
      `console.log('child-ready'); setTimeout(() => require('node:fs').writeFileSync(${JSON.stringify(marker)}, 'survived'), 1000);`
    );
    fs.writeFileSync(
      parent,
      `require('node:child_process').spawn(process.execPath, [${JSON.stringify(leaf)}], {stdio:'inherit',windowsHide:true}); setTimeout(()=>{},5000);`
    );
    const result = invoke(directory, [
      { id: 'tree', op: 'tool', name: 'node', args: [parent], timeout_ms: 500 },
    ]);
    assert.equal(result.rows[0].result.process_error, 'ETIMEDOUT');
    assert.match(result.rows[0].result.stdout, /child-ready/);
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 1200);
    assert.equal(fs.existsSync(marker), false, 'timed-out tool left a running child');
  }
);
