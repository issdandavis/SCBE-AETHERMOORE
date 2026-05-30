'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const { tmpdir } = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const BIN = path.resolve(__dirname, '..', 'bin', 'polly.js');

function run(tempDir, args, env) {
  return spawnSync('node', [BIN, ...args], {
    cwd: tempDir,
    env: Object.assign({}, process.env, env || {}),
    encoding: 'utf8',
  });
}

function mktemp() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'polly-test-'));
}

function cleanup(dir) {
  try {
    fs.rmSync(dir, { recursive: true, force: true });
  } catch (_) {}
}

// ---------------------------------------------------------------------------
// Test 1: polly init creates .polly/pad.json
// ---------------------------------------------------------------------------
test('polly init creates .polly/pad.json', () => {
  const dir = mktemp();
  try {
    const result = run(dir, ['init', 'TestPad']);
    assert.strictEqual(result.status, 0, 'exit code should be 0\nstdout: ' + result.stdout + '\nstderr: ' + result.stderr);
    const padPath = path.join(dir, '.polly', 'pad.json');
    assert.ok(fs.existsSync(padPath), '.polly/pad.json should exist');
    const pad = JSON.parse(fs.readFileSync(padPath, 'utf8'));
    assert.strictEqual(pad.name, 'TestPad', 'pad.name should be TestPad');
    assert.strictEqual(pad.schema_version, 'polly_pad_v1', 'schema_version should be polly_pad_v1');
    const auditPath = path.join(dir, '.polly', 'audit.jsonl');
    assert.ok(fs.existsSync(auditPath), '.polly/audit.jsonl should exist');
    const firstReceipt = JSON.parse(fs.readFileSync(auditPath, 'utf8').trim());
    assert.strictEqual(firstReceipt.action, 'workspace.init');
    assert.strictEqual(firstReceipt.prev_hash, '0'.repeat(64));
    assert.match(firstReceipt.event_hash, /^[a-f0-9]{64}$/);
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 2: polly status outputs JSON with --json
// ---------------------------------------------------------------------------
test('polly status outputs JSON with --json', () => {
  const dir = mktemp();
  try {
    const initResult = run(dir, ['init', 'StatusTest']);
    assert.strictEqual(initResult.status, 0, 'init should succeed');

    const statusResult = run(dir, ['status', '--json']);
    assert.strictEqual(statusResult.status, 0, 'status exit code should be 0\nstdout: ' + statusResult.stdout + '\nstderr: ' + statusResult.stderr);
    let parsed;
    assert.doesNotThrow(() => {
      parsed = JSON.parse(statusResult.stdout);
    }, 'status --json output should be valid JSON');
    assert.ok(parsed.schema_version, 'should have schema_version');
    assert.strictEqual(parsed.name, 'StatusTest');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 3: polly task add then list
// ---------------------------------------------------------------------------
test('polly task add then list', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'TaskTest']);
    const addResult = run(dir, ['task', 'add', 'hello', 'world']);
    assert.strictEqual(addResult.status, 0, 'task add should succeed\nstdout: ' + addResult.stdout + '\nstderr: ' + addResult.stderr);

    const statusResult = run(dir, ['status', '--json']);
    assert.strictEqual(statusResult.status, 0, 'status should succeed');
    const pad = JSON.parse(statusResult.stdout);
    assert.ok(Array.isArray(pad.tasks), 'tasks should be an array');
    const task = pad.tasks.find((t) => t.text === 'hello world');
    assert.ok(task, 'should find task with text "hello world"');
    assert.strictEqual(task.state, 'pending');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 4: polly task done marks completed
// ---------------------------------------------------------------------------
test('polly task done marks completed', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'DoneTest']);
    run(dir, ['task', 'add', 'finish this task']);

    // Get the task id
    const statusBefore = run(dir, ['status', '--json']);
    const padBefore = JSON.parse(statusBefore.stdout);
    const taskId = padBefore.tasks[0].id;
    assert.ok(taskId, 'task id should exist');

    const doneResult = run(dir, ['task', 'done', taskId]);
    assert.strictEqual(doneResult.status, 0, 'task done should succeed\nstdout: ' + doneResult.stdout + '\nstderr: ' + doneResult.stderr);

    const statusAfter = run(dir, ['status', '--json']);
    const padAfter = JSON.parse(statusAfter.stdout);
    const task = padAfter.tasks.find((t) => t.id === taskId);
    assert.strictEqual(task.state, 'done', 'task state should be done');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 5: polly runs returns empty list initially
// ---------------------------------------------------------------------------
test('polly runs returns empty list initially', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'RunsTest']);
    const runsResult = run(dir, ['runs', '--json']);
    assert.strictEqual(runsResult.status, 0, 'runs should succeed\nstdout: ' + runsResult.stdout + '\nstderr: ' + runsResult.stderr);
    let parsed;
    assert.doesNotThrow(() => {
      parsed = JSON.parse(runsResult.stdout);
    }, 'runs --json should be valid JSON');
    assert.ok(Array.isArray(parsed), 'runs output should be an array');
    assert.strictEqual(parsed.length, 0, 'runs should be empty initially');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 6: polly doctor exits 0
// ---------------------------------------------------------------------------
test('polly doctor exits 0', () => {
  const dir = mktemp();
  try {
    const result = run(dir, ['doctor']);
    assert.strictEqual(result.status, 0, 'doctor should exit 0\nstdout: ' + result.stdout + '\nstderr: ' + result.stderr);
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 7: polly --version prints version
// ---------------------------------------------------------------------------
test('polly --version prints version', () => {
  const dir = mktemp();
  try {
    const result = run(dir, ['--version']);
    assert.strictEqual(result.status, 0, '--version should exit 0');
    assert.ok(result.stdout.includes('polly v'), 'output should include "polly v"');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 8: polly snapshot creates snapshot file
// ---------------------------------------------------------------------------
test('polly snapshot creates snapshot file', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'SnapTest']);
    const snapResult = run(dir, ['snapshot']);
    assert.strictEqual(snapResult.status, 0, 'snapshot should exit 0\nstdout: ' + snapResult.stdout + '\nstderr: ' + snapResult.stderr);

    const snapsDir = path.join(dir, '.polly', 'snapshots');
    assert.ok(fs.existsSync(snapsDir), '.polly/snapshots should exist');
    const files = fs.readdirSync(snapsDir).filter((f) => f.endsWith('.json'));
    assert.ok(files.length > 0, 'should have at least one snapshot file');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 9: polly ask can force free/local-only routing before template fallback
// ---------------------------------------------------------------------------
test('polly ask respects POLLY_DISABLE_PAID_APIS fallback', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'FreeOnlyAskTest']);
    const result = run(dir, ['ask', 'make a short checklist', '--json'], {
      POLLY_DISABLE_TERMINAL_ROUTER: '1',
      POLLY_DISABLE_OLLAMA: '1',
      POLLY_DISABLE_PAID_APIS: '1',
      ANTHROPIC_API_KEY: '',
      OPENAI_API_KEY: '',
    });
    assert.strictEqual(result.status, 0, 'ask should succeed\nstdout: ' + result.stdout + '\nstderr: ' + result.stderr);
    const payload = JSON.parse(result.stdout);
    assert.strictEqual(payload.model_used, 'template');
    assert.strictEqual(payload.source, 'fallback');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 10: polly audit verify validates receipt chain
// ---------------------------------------------------------------------------
test('polly audit verify validates receipt chain', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'AuditTest']);
    run(dir, ['task', 'add', 'audit this']);
    run(dir, ['task', 'done', 'task-001']);

    const verifyResult = run(dir, ['audit', 'verify', '--json']);
    assert.strictEqual(
      verifyResult.status,
      0,
      'audit verify should succeed\nstdout: ' + verifyResult.stdout + '\nstderr: ' + verifyResult.stderr
    );
    const verified = JSON.parse(verifyResult.stdout);
    assert.strictEqual(verified.ok, true);
    assert.strictEqual(verified.count, 3);

    const listResult = run(dir, ['audit', 'list', '--json']);
    assert.strictEqual(listResult.status, 0, 'audit list should succeed');
    const events = JSON.parse(listResult.stdout);
    assert.deepStrictEqual(
      events.map((event) => event.action),
      ['workspace.init', 'task.add', 'task.done']
    );
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 11: polly audit verify fails on tampered receipt
// ---------------------------------------------------------------------------
test('polly audit verify fails on tampered receipt', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'TamperTest']);
    const auditPath = path.join(dir, '.polly', 'audit.jsonl');
    const event = JSON.parse(fs.readFileSync(auditPath, 'utf8').trim());
    event.subject = 'tampered';
    fs.writeFileSync(auditPath, JSON.stringify(event) + '\n', 'utf8');

    const verifyResult = run(dir, ['audit', 'verify', '--json']);
    assert.strictEqual(verifyResult.status, 2, 'tampered audit should exit 2');
    const verified = JSON.parse(verifyResult.stdout);
    assert.strictEqual(verified.ok, false);
    assert.strictEqual(verified.broken_at, 1);
    assert.strictEqual(verified.reason, 'event hash mismatch');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 11: polly tools list shows governed tools when POLLY_TOOLS_JSON is set
// ---------------------------------------------------------------------------
test('polly tools list shows governed tools when POLLY_TOOLS_JSON is set', async (t) => {
  // Create a minimal tools.json in temp dir
  const tmpTools = path.join(tmpdir(), 'polly-tools-test-' + Date.now() + '.json');
  fs.writeFileSync(
    tmpTools,
    JSON.stringify([{ name: 'test-tool', description: 'A test governed tool', command: 'echo', args: ['hello', '{task}'] }])
  );

  const result = spawnSync('node', [BIN, 'tools', 'list', '--json'], {
    encoding: 'utf8',
    env: Object.assign({}, process.env, { POLLY_TOOLS_JSON: tmpTools }),
  });

  fs.unlinkSync(tmpTools);

  assert.strictEqual(result.status, 0);
  const data = JSON.parse(result.stdout);
  assert.ok(Array.isArray(data.tools));
  assert.ok(data.tools.some((t) => t.name === 'test-tool'));
  assert.ok(data.tools.some((t) => t.kind === 'governed'));
});

// ---------------------------------------------------------------------------
// Test 12: polly tools inspect unknown tool exits 1
// ---------------------------------------------------------------------------
test('polly tools inspect unknown tool exits 1', async (t) => {
  const result = spawnSync('node', [BIN, 'tools', 'inspect', 'no-such-tool-xyz'], {
    encoding: 'utf8',
  });
  assert.strictEqual(result.status, 1);
});

// ---------------------------------------------------------------------------
// Test 13: polly tools run dry-run shows command without executing
// ---------------------------------------------------------------------------
test('polly tools run dry-run shows command without executing', async (t) => {
  const tmpTools = path.join(tmpdir(), 'polly-tools-dry-' + Date.now() + '.json');
  fs.writeFileSync(
    tmpTools,
    JSON.stringify([{ name: 'echo-tool', description: 'Echo test', command: 'echo', args: ['hello', '{task}'] }])
  );

  const result = spawnSync('node', [BIN, 'tools', 'run', 'echo-tool', '--dry-run', '--input', 'world', '--json'], {
    encoding: 'utf8',
    env: Object.assign({}, process.env, { POLLY_TOOLS_JSON: tmpTools }),
  });

  fs.unlinkSync(tmpTools);

  assert.strictEqual(result.status, 0);
  const data = JSON.parse(result.stdout);
  assert.strictEqual(data.dry_run, true);
  assert.deepStrictEqual(data.args, ['hello', 'world']);
  assert.strictEqual(data.unresolved_placeholders.length, 0);
});

// ---------------------------------------------------------------------------
// Test 11: polly cross pack/unpack round-trips UTF-8 through hex
// ---------------------------------------------------------------------------
test('polly cross pack/unpack round-trips UTF-8 through hex', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'CrossPackTest']);
    const source = 'def add(x, y): return x + y';
    const packResult = run(dir, ['cross', 'pack', '--text', source, '--lang', 'python']);
    assert.strictEqual(packResult.status, 0, 'cross pack should exit 0\nstdout: ' + packResult.stdout + '\nstderr: ' + packResult.stderr);
    const packet = JSON.parse(packResult.stdout);
    assert.strictEqual(packet.schema_version, 'polly_cross_packet_v1');
    assert.strictEqual(packet.language, 'python');
    assert.strictEqual(Buffer.from(packet.hex, 'hex').toString('utf8'), source);
    assert.match(packet.sha256, /^[a-f0-9]{64}$/);
    assert.match(packet.semantic_hex, /^[a-f0-9]{12}$/);
    assert.notStrictEqual(packet.semantic_hex, '000000000000');

    const unpackResult = run(dir, ['cross', 'unpack', '--hex', packet.hex, '--json']);
    assert.strictEqual(unpackResult.status, 0, 'cross unpack should exit 0');
    const unpacked = JSON.parse(unpackResult.stdout);
    assert.strictEqual(unpacked.text, source);
    assert.strictEqual(unpacked.verified_sha256, packet.sha256);

    const auditResult = run(dir, ['audit', 'list', '--json']);
    const events = JSON.parse(auditResult.stdout);
    assert.ok(events.some((event) => event.action === 'cross.pack'));
    assert.ok(events.some((event) => event.action === 'cross.unpack'));
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 12: polly cross op broadcasts bounded operation templates
// ---------------------------------------------------------------------------
test('polly cross op broadcasts bounded operation templates', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'CrossOpTest']);
    const result = run(dir, ['cross', 'op', 'add', '--json']);
    assert.strictEqual(result.status, 0, 'cross op should exit 0\nstdout: ' + result.stdout + '\nstderr: ' + result.stderr);
    const payload = JSON.parse(result.stdout);
    assert.strictEqual(payload.schema_version, 'polly_cross_op_v1');
    assert.strictEqual(payload.translations.python, 'result = x + y');
    assert.strictEqual(payload.translations.rust, 'let result = x + y;');
    assert.strictEqual(Buffer.from(payload.packets.python.hex, 'hex').toString('utf8'), payload.translations.python);
    assert.match(payload.packets.typescript.semantic_hex, /^[a-f0-9]{12}$/);
    assert.notStrictEqual(payload.packets.typescript.semantic_hex, '000000000000');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 13: polly cross op can target one language
// ---------------------------------------------------------------------------
test('polly cross op can target one language', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'CrossTargetTest']);
    const result = run(dir, ['cross', 'op', 'xor', '--to', 'go', '--json']);
    assert.strictEqual(result.status, 0, 'cross op --to should exit 0');
    const payload = JSON.parse(result.stdout);
    assert.deepStrictEqual(Object.keys(payload.translations), ['go']);
    assert.strictEqual(payload.translations.go, 'result := x ^ y');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 17: polly cross exec dry-run emits templates without executing
// ---------------------------------------------------------------------------
test('polly cross exec dry-run emits templates without executing', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'CrossExecDryTest']);
    const result = run(dir, ['cross', 'exec', 'add', '--x', '5', '--y', '3', '--dry-run', '--json']);
    assert.strictEqual(result.status, 0, 'cross exec --dry-run should exit 0\nstdout: ' + result.stdout + '\nstderr: ' + result.stderr);
    const payload = JSON.parse(result.stdout);
    assert.strictEqual(payload.dry_run, true);
    assert.strictEqual(payload.op, 'add');
    assert.strictEqual(payload.x, 5);
    assert.strictEqual(payload.y, 3);
    assert.ok(Array.isArray(payload.langs), 'langs should be an array');
    assert.ok(payload.langs.includes('javascript'), 'langs should include javascript');
    assert.ok(typeof payload.templates === 'object', 'templates should be present');
    assert.ok(payload.templates.python, 'python template should be present');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 18: polly cross exec runs javascript and returns output 17
// ---------------------------------------------------------------------------
test('polly cross exec runs javascript and returns output 17', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'CrossExecJSTest']);
    const result = run(dir, ['cross', 'exec', 'add', '--x', '10', '--y', '7', '--lang', 'javascript', '--json']);
    assert.strictEqual(result.status, 0, 'cross exec javascript should exit 0\nstdout: ' + result.stdout + '\nstderr: ' + result.stderr);
    const payload = JSON.parse(result.stdout);
    assert.strictEqual(payload.schema_version, 'polly_cross_exec_v1');
    assert.strictEqual(payload.op, 'add');
    assert.strictEqual(payload.x, 10);
    assert.strictEqual(payload.y, 7);
    assert.ok(Array.isArray(payload.results), 'results should be an array');
    const jsResult = payload.results.find((r) => r.lang === 'javascript');
    assert.ok(jsResult, 'javascript result should exist');
    assert.strictEqual(jsResult.ok, true, 'javascript should succeed');
    assert.strictEqual(jsResult.output, '17', 'javascript add(10,7) should output 17');
    assert.ok(payload.consistency, 'consistency should be present');
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 19: polly cross exec python and javascript agree on xor when python exists
// ---------------------------------------------------------------------------
test('polly cross exec python and javascript agree on xor when python exists', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'CrossExecConsistencyTest']);
    const result = run(dir, ['cross', 'exec', 'xor', '--x', '12', '--y', '10', '--langs', 'all', '--json']);
    assert.strictEqual(result.status, 0, 'cross exec xor should exit 0\nstdout: ' + result.stdout + '\nstderr: ' + result.stderr);
    const payload = JSON.parse(result.stdout);
    assert.strictEqual(payload.schema_version, 'polly_cross_exec_v1');
    assert.strictEqual(payload.op, 'xor');
    assert.ok(Array.isArray(payload.results));

    const jsResult = payload.results.find((r) => r.lang === 'javascript');
    assert.ok(jsResult && jsResult.ok, 'javascript xor should succeed');
    assert.strictEqual(jsResult.output, '6', 'javascript xor(12,10) should be 6');

    const pyResult = payload.results.find((r) => r.lang === 'python');
    if (pyResult && pyResult.ok) {
      assert.strictEqual(pyResult.output, '6', 'python xor(12,10) should be 6');
      assert.strictEqual(payload.consistency.consensus, 'full', 'python and javascript should agree on xor');
    }
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 20: polly cross bench pathfinding compares Dijkstra, A*, and compass
// ---------------------------------------------------------------------------
test('polly cross bench pathfinding compares Dijkstra, A*, and compass', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'CrossBenchPathTest']);
    const result = run(dir, ['cross', 'bench', 'pathfinding', '--json']);
    assert.strictEqual(result.status, 0, 'cross bench pathfinding should exit 0\nstdout: ' + result.stdout + '\nstderr: ' + result.stderr);
    const payload = JSON.parse(result.stdout);
    assert.strictEqual(payload.schema_version, 'polly_route_bench_v1');
    assert.strictEqual(payload.benchmark, 'multi_field_pathfinding');
    assert.deepStrictEqual(payload.algorithms.map((entry) => entry.mode), ['dijkstra', 'astar', 'compass']);
    assert.ok(payload.algorithms.every((entry) => entry.ok), 'all algorithms should find a route');

    const dijkstra = payload.algorithms.find((entry) => entry.mode === 'dijkstra');
    const astar = payload.algorithms.find((entry) => entry.mode === 'astar');
    const compass = payload.algorithms.find((entry) => entry.mode === 'compass');
    assert.ok(dijkstra.expansions >= astar.expansions, 'A* should expand no more nodes than Dijkstra');
    assert.ok(compass.expansions <= dijkstra.expansions, 'compass route should not expand more than Dijkstra');
    assert.ok(payload.fields.geometric.includes('x'));
    assert.ok(payload.fields.semantic.includes('height-change'));

    const auditResult = run(dir, ['audit', 'list', '--json']);
    const events = JSON.parse(auditResult.stdout);
    assert.ok(events.some((event) => event.action === 'cross.bench.pathfinding'));
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 21: polly cross patch builds and applies a verified line patch
// ---------------------------------------------------------------------------
test('polly cross patch builds and applies a verified line patch', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'CrossPatchTest']);
    const filePath = path.join(dir, 'calc.py');
    fs.writeFileSync(filePath, 'result = x - y\nprint(result)', 'utf8');

    const result = run(dir, ['cross', 'patch', '--file', filePath, '--text', 'result = x + y\nprint(result)', '--apply']);
    assert.strictEqual(result.status, 0, 'cross patch should exit 0\nstdout: ' + result.stdout + '\nstderr: ' + result.stderr);
    const payload = JSON.parse(result.stdout);
    assert.strictEqual(payload.schema_version, 'polly_cross_patch_v1');
    assert.strictEqual(payload.verified_apply, true);
    assert.strictEqual(payload.applied, true);
    assert.strictEqual(payload.patch.start_line, 1);
    assert.strictEqual(fs.readFileSync(filePath, 'utf8'), 'result = x + y\nprint(result)');

    const auditResult = run(dir, ['audit', 'list', '--json']);
    const events = JSON.parse(auditResult.stdout);
    assert.ok(events.some((event) => event.action === 'cross.patch.applied'));
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 22: polly cross bundle packages multiple language files
// ---------------------------------------------------------------------------
test('polly cross bundle packages multiple language files', () => {
  const dir = mktemp();
  try {
    run(dir, ['init', 'CrossBundleTest']);
    const pyPath = path.join(dir, 'calc.py');
    const jsPath = path.join(dir, 'calc.js');
    const outPath = path.join(dir, 'bundle.json');
    fs.writeFileSync(pyPath, 'result = x + y', 'utf8');
    fs.writeFileSync(jsPath, 'const result = x + y;', 'utf8');

    const result = run(dir, ['cross', 'bundle', '--files', pyPath + ',' + jsPath, '--out', outPath]);
    assert.strictEqual(result.status, 0, 'cross bundle should exit 0\nstdout: ' + result.stdout + '\nstderr: ' + result.stderr);
    const payload = JSON.parse(result.stdout);
    assert.strictEqual(payload.schema_version, 'polly_cross_bundle_v1');
    assert.strictEqual(payload.files.length, 2);
    assert.match(payload.aggregate_hash, /^[a-f0-9]{64}$/);
    assert.ok(fs.existsSync(outPath), 'bundle should be written to --out path');
    assert.strictEqual(JSON.parse(fs.readFileSync(outPath, 'utf8')).aggregate_hash, payload.aggregate_hash);

    const langs = payload.files.map((entry) => entry.language).sort();
    assert.deepStrictEqual(langs, ['javascript', 'python']);
  } finally {
    cleanup(dir);
  }
});

// ---------------------------------------------------------------------------
// Test 23: polly cross bench translate returns correct schema
// ---------------------------------------------------------------------------
test('polly cross bench translate returns correct schema', async () => {
  const result = spawnSync('node', [BIN, 'cross', 'bench', 'translate', '--json'], {
    encoding: 'utf8',
    timeout: 180000,
    env: { ...process.env },
  });
  assert.strictEqual(result.status, 0, 'bench translate should exit 0\n' + result.stderr);
  const data = JSON.parse(result.stdout);
  assert.strictEqual(data.schema_version, 'polly_cross_bench_v1');
  assert.ok(typeof data.execution_match_rate === 'number');
  assert.ok(Array.isArray(data.results));
  assert.ok(data.results.length >= 5);
});

// ---------------------------------------------------------------------------
// Test 24: polly cross bench translate --dry-run verifies fixture translations
// ---------------------------------------------------------------------------
test('polly cross bench translate --dry-run verifies fixture translations', async () => {
  const result = spawnSync('node', [BIN, 'cross', 'bench', 'translate', '--dry-run', '--json'], {
    encoding: 'utf8',
    timeout: 60000,
    env: { ...process.env, POLLY_DISABLE_TERMINAL_ROUTER: '1' },
  });
  assert.strictEqual(result.status, 0, 'bench translate dry-run should exit 0\n' + result.stderr);
  const data = JSON.parse(result.stdout);
  assert.strictEqual(data.schema_version, 'polly_cross_bench_v1');
  assert.strictEqual(data.execution_match_rate, 1);
  const palindrome = data.results.find((entry) => entry.id === 'bench_palindrome');
  assert.ok(palindrome, 'palindrome bench result should exist');
  assert.strictEqual(palindrome.model, 'fixture');
  assert.strictEqual(palindrome.exec_match, true);
});

// ---------------------------------------------------------------------------
// Test 25: polly cross translate --dry-run shows prompt
// ---------------------------------------------------------------------------
test('polly cross translate --dry-run shows prompt', () => {
  const result = spawnSync(
    'node',
    [BIN, 'cross', 'translate', '--from', 'python', '--to', 'javascript', '--text', 'def add(x, y): return x + y', '--dry-run', '--json'],
    { encoding: 'utf8' }
  );
  assert.strictEqual(result.status, 0);
  const data = JSON.parse(result.stdout);
  assert.strictEqual(data.dry_run, true);
  assert.ok(data.prompt && data.prompt.length > 0);
});
