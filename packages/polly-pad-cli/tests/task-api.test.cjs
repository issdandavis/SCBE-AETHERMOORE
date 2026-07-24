'use strict';

const assert = require('node:assert');
const { spawn, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { TaskApiClient, isOwnedTaskApiUrl, validateTaskApiRun } = require('../lib/task-api-client');

const BIN = path.resolve(__dirname, '..', 'bin', 'polly.js');

function rawRun() {
  return {
    run_id: 'trun_polly_test',
    interaction_id: 'int_polly_test',
    status: 'completed',
    submitted_at: '2026-07-24T00:00:00Z',
    started_at: '2026-07-24T00:00:01Z',
    completed_at: '2026-07-24T00:00:02Z',
    input_sha256: '1'.repeat(64),
    output_sha256: '2'.repeat(64),
    result: { summary: 'Bounded result.' },
    error: null,
    basis: [
      {
        field: '/summary',
        confidence: 0.8,
        reasoning: 'Admitted source quote.',
        citations: [
          {
            title: 'Source',
            url: 'https://clay.local/source',
            content_sha256: '3'.repeat(64),
            quote: 'Bounded evidence.',
          },
        ],
      },
    ],
    metrics: { evidence_selected: 1 },
    disposition: {
      status: 'review_required',
      negative_example: false,
      do_not_promote_to_fact: true,
      reason: 'External review remains required.',
    },
  };
}

function runAsync(cwd, args) {
  return new Promise((resolve) => {
    const child = spawn('node', [BIN, ...args], { cwd, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      stdout += chunk;
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk;
    });
    child.on('close', (status) => resolve({ status, stdout, stderr }));
  });
}

async function fixtureServer() {
  const server = http.createServer((request, response) => {
    response.setHeader('content-type', 'application/json');
    if (request.method === 'POST' && request.url === '/v1/tasks/runs') {
      response.statusCode = 202;
      response.end(JSON.stringify(rawRun()));
      return;
    }
    if (request.method === 'GET' && request.url === '/v1/tasks/runs/trun_polly_test') {
      response.end(JSON.stringify(rawRun()));
      return;
    }
    response.statusCode = 404;
    response.end(JSON.stringify({ error: 'not_found' }));
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  return {
    server,
    url: `http://127.0.0.1:${address.port}`,
  };
}

test('Polly task API client enforces owned-network routing', () => {
  assert.strictEqual(isOwnedTaskApiUrl('http://127.0.0.1:8766'), true);
  assert.strictEqual(isOwnedTaskApiUrl('http://100.87.197.29:8766'), true);
  assert.strictEqual(isOwnedTaskApiUrl('https://example.com'), false);
  assert.throws(
    () => new TaskApiClient({ baseUrl: 'https://example.com' }),
    /loopback\/private\/Tailscale/
  );
});

test('Polly validator rejects unsupported output marked as reviewable', () => {
  const parsed = validateTaskApiRun({
    ...rawRun(),
    basis: [],
    disposition: {
      status: 'review_required',
      negative_example: false,
      do_not_promote_to_fact: true,
      reason: 'Unsupported promotion.',
    },
  });
  assert.strictEqual(parsed.ok, false);
  assert.match(parsed.errors.join(' '), /negative example/);
});

test('Polly validator rejects malformed evidence instead of counting it as support', () => {
  const run = rawRun();
  run.basis[0].citations[0].content_sha256 = 'not-a-hash';
  const parsed = validateTaskApiRun(run);
  assert.strictEqual(parsed.ok, false);
  assert.match(parsed.errors.join(' '), /content_sha256 is invalid/);
});

test('polly task submit persists the governed remote receipt', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'polly-task-api-'));
  const fixture = await fixtureServer();
  try {
    const init = spawnSync('node', [BIN, 'init', 'TaskApiTest'], {
      cwd: dir,
      encoding: 'utf8',
    });
    assert.strictEqual(init.status, 0, init.stderr);

    const submitted = await runAsync(dir, [
      'task',
      'submit',
      'verify',
      'this',
      'claim',
      '--url',
      fixture.url,
      '--json',
    ]);
    assert.strictEqual(submitted.status, 0, submitted.stderr);
    const run = JSON.parse(submitted.stdout);
    assert.strictEqual(run.run_id, 'trun_polly_test');
    assert.strictEqual(run.disposition.do_not_promote_to_fact, true);

    const pad = JSON.parse(fs.readFileSync(path.join(dir, '.polly', 'pad.json'), 'utf8'));
    assert.strictEqual(pad.tasks[0].remote_run_id, 'trun_polly_test');
    assert.strictEqual(pad.tasks[0].remote_disposition, 'review_required');
    assert.strictEqual(pad.tasks[0].do_not_promote_to_fact, true);

    const events = fs
      .readFileSync(path.join(dir, '.polly', 'audit.jsonl'), 'utf8')
      .trim()
      .split(/\r?\n/)
      .map(JSON.parse);
    assert.ok(events.some((event) => event.action === 'task.remote.submit'));
  } finally {
    await new Promise((resolve) => fixture.server.close(resolve));
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
