'use strict';

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const { createToolRegistry } = require('../lib/tool-registry');

function makeTemp(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function removeTemp(target) {
  const resolved = path.resolve(target);
  const tempRoot = `${path.resolve(os.tmpdir())}${path.sep}`;
  assert.ok(resolved.startsWith(tempRoot), `refusing to remove non-temp path: ${resolved}`);
  fs.rmSync(resolved, { recursive: true, force: true });
}

function killExactProcess(pid) {
  if (!Number.isSafeInteger(pid) || pid <= 0) return;
  if (process.platform === 'win32') {
    const taskkill = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'taskkill.exe');
    spawnSync(taskkill, ['/PID', String(pid), '/T', '/F'], {
      shell: false,
      windowsHide: true,
      stdio: 'ignore',
    });
    return;
  }
  try {
    process.kill(pid, 'SIGKILL');
  } catch (_error) {
    // It was already terminated by the code under test.
  }
}

function shellQuote(value) {
  const text = String(value);
  if (process.platform === 'win32') return `"${text.replace(/"/g, '""')}"`;
  return `'${text.replace(/'/g, `'"'"'`)}'`;
}

test('search_text treats regex metacharacters as literal text by default', async (t) => {
  const workspace = makeTemp('scbe-tool-search-literal-');
  t.after(() => removeTemp(workspace));
  fs.writeFileSync(path.join(workspace, 'sample.txt'), 'literal [a-z]+ token\nalpha token\n', 'utf8');
  const registry = createToolRegistry({ workspaceRoot: workspace });

  const result = await registry.execute('search_text', { query: '[a-z]+', path: '.' });

  assert.equal(result.mode, 'literal');
  assert.deepEqual(result.matches.map((match) => match.line), [1]);
});

test('search_text accepts ordinary bounded regexes and rejects catastrophic forms', async (t) => {
  const workspace = makeTemp('scbe-tool-search-regex-');
  t.after(() => removeTemp(workspace));
  fs.writeFileSync(path.join(workspace, 'sample.txt'), 'alpha-42\nbeta\n', 'utf8');
  const registry = createToolRegistry({ workspaceRoot: workspace });

  const safe = await registry.execute('search_text', {
    query: '^alpha-[0-9]{2}$',
    regex: true,
  });
  assert.equal(safe.mode, 'regex');
  assert.deepEqual(safe.matches.map((match) => match.line), [1]);

  await assert.rejects(
    registry.execute('search_text', { query: '(a+)+$', regex: true }),
    /unsafe regex: quantified groups/
  );
  await assert.rejects(
    registry.execute('search_text', { query: '(a|aa)+$', regex: true }),
    /unsafe regex: quantified groups/
  );
});

test('run_command timeout terminates descendants instead of leaving a background process', async (t) => {
  const workspace = makeTemp('scbe-tool-process-tree-');
  const childScript = path.join(workspace, 'child.cjs');
  const parentScript = path.join(workspace, 'parent.cjs');
  const marker = path.join(workspace, 'descendant-survived.txt');
  let descendantPid = null;
  t.after(() => {
    killExactProcess(descendantPid);
    removeTemp(workspace);
  });

  fs.writeFileSync(
    childScript,
    "const fs = require('node:fs'); setTimeout(() => fs.writeFileSync(process.argv[2], 'survived'), 700); setInterval(() => {}, 1000);\n",
    'utf8'
  );
  fs.writeFileSync(
    parentScript,
    "const { spawn } = require('node:child_process'); const child = spawn(process.execPath, [process.argv[2], process.argv[3]], { stdio: 'ignore' }); console.log('CHILD_PID=' + child.pid); setInterval(() => {}, 1000);\n",
    'utf8'
  );

  const registry = createToolRegistry({ workspaceRoot: workspace });
  const result = await registry.execute('run_command', {
    command: [process.execPath, parentScript, childScript, marker].map(shellQuote).join(' '),
    timeout_ms: 150,
  });
  const match = result.stdout.match(/CHILD_PID=(\d+)/);
  descendantPid = match ? Number(match[1]) : null;

  assert.equal(result.ok, false);
  assert.equal(result.timedOut, true);
  assert.ok(descendantPid > 0, `expected descendant PID in stdout, got: ${result.stdout}`);
  await new Promise((resolve) => setTimeout(resolve, 900));
  assert.equal(fs.existsSync(marker), false, 'descendant survived the command timeout');
});
