const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');

function tempWorkspace() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-longform-cli-'));
}

function runCli(args, options = {}) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-longform-home-'));
  const env = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
    NO_COLOR: '1',
  };
  return spawnSync(process.execPath, [CLI, ...args], {
    cwd: options.cwd || tempWorkspace(),
    input: options.input || '',
    encoding: 'utf8',
    timeout: options.timeout || 15_000,
    env,
  });
}

function parseJson(result) {
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

test('scbe do creates a durable squad landing with a valid hash chain', () => {
  const cwd = tempWorkspace();
  const result = runCli(
    [
      'do',
      'build the browser benchmark adapter and prove it',
      '--squad',
      '--loops',
      '6',
      '--land',
      'every-stage',
      '--resume-policy',
      'latest-safe',
      '--backend',
      'local-jsonl',
      '--json',
    ],
    { cwd }
  );
  const body = parseJson(result);

  assert.equal(body.schema_version, 'scbe.longform.do.v1');
  assert.equal(body.status, 'landed');
  assert.equal(body.squad, true);
  assert.equal(body.spawned.length, 4);
  assert.equal(body.ledger.ok, true);
  assert.equal(body.ledger.count, 6);
  assert.match(body.landing_hash, /^[a-f0-9]{64}$/);
  assert.ok(fs.existsSync(body.ledger_path));

  const status = parseJson(runCli(['work', 'status', '--workflow', body.workflow_id, '--json'], { cwd }));
  assert.equal(status.ledger.ok, true);
  assert.equal(status.ledger.count, 6);
  assert.equal(status.ledger.head_hash, body.landing_hash);
});

test('work init, agent spawn, and land create share one workflow ledger', () => {
  const cwd = tempWorkspace();
  const init = parseJson(
    runCli(['work', 'init', '--objective', 'cross language compile lane', '--workflow', 'wf-cross', '--json'], {
      cwd,
    })
  );
  assert.equal(init.workflow_id, 'wf-cross');
  assert.match(init.event_hash, /^[a-f0-9]{64}$/);

  const agent = parseJson(
    runCli(
      [
        'agent',
        'spawn',
        '--workflow',
        'wf-cross',
        '--role',
        'tester',
        '--mandate',
        'prove translation fixtures',
        '--allowed-tools',
        'read,test,verify',
        '--json',
      ],
      { cwd }
    )
  );
  assert.equal(agent.role, 'tester');
  assert.deepEqual(agent.allowed_tools, ['read', 'test', 'verify']);

  const landing = parseJson(
    runCli(
      [
        'land',
        'create',
        '--workflow',
        'wf-cross',
        '--summary',
        'fixtures verified and next foothold recorded',
        '--stage',
        'verify',
        '--json',
      ],
      { cwd }
    )
  );
  assert.equal(landing.status, 'landed');
  assert.match(landing.landing_hash, /^[a-f0-9]{64}$/);

  const status = parseJson(runCli(['work', 'status', '--workflow', 'wf-cross', '--json'], { cwd }));
  assert.equal(status.ledger.ok, true);
  assert.equal(status.ledger.count, 3);
  assert.equal(status.ledger.head_hash, landing.landing_hash);
});

test('work status reports empty state without creating files', () => {
  const cwd = tempWorkspace();
  const status = parseJson(runCli(['work', 'status', '--json'], { cwd }));

  assert.equal(status.status, 'empty');
  assert.equal(status.workflow_id, null);
  assert.equal(fs.existsSync(path.join(cwd, '.scbe', 'longform')), false);
});
