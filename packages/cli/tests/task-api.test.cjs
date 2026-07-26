'use strict';

const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const BIN = path.resolve(__dirname, '..', 'bin', 'scbe-task.js');

function run(args) {
  return spawnSync('node', [BIN, ...args], { encoding: 'utf8' });
}

function writeRun(overrides = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-task-cli-'));
  const file = path.join(dir, 'run.json');
  fs.writeFileSync(
    file,
    JSON.stringify({
      run_id: 'trun_cli_test',
      interaction_id: 'int_cli_test',
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
          confidence: 0.75,
          reasoning: 'Admitted source quote.',
          citations: [
            {
              source_id: 'source_1',
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
      ...overrides,
    })
  );
  return { dir, file };
}

test('scbe-task help is available without a running task service', () => {
  const result = run(['help']);
  assert.strictEqual(result.status, 0);
  assert.match(result.stdout, /governed async task client/);
});

test('scbe-task validates a fail-closed task run', () => {
  const fixture = writeRun();
  try {
    const result = run(['validate', fixture.file, '--json']);
    assert.strictEqual(result.status, 0, result.stderr);
    const parsed = JSON.parse(result.stdout);
    assert.strictEqual(parsed.ok, true);
    assert.strictEqual(parsed.data.schema_version, 'scbe.governed-task-run.v1');
    assert.strictEqual(parsed.data.disposition.do_not_promote_to_fact, true);
  } finally {
    fs.rmSync(fixture.dir, { recursive: true, force: true });
  }
});

test('scbe-task rejects unsupported output marked review_required', () => {
  const fixture = writeRun({
    basis: [],
    disposition: {
      status: 'review_required',
      negative_example: false,
      do_not_promote_to_fact: true,
      reason: 'Unsupported promotion.',
    },
  });
  try {
    const result = run(['validate', fixture.file, '--json']);
    assert.strictEqual(result.status, 2);
    const parsed = JSON.parse(result.stdout);
    assert.strictEqual(parsed.ok, false);
    assert.match(parsed.errors.join(' '), /negative example/);
  } finally {
    fs.rmSync(fixture.dir, { recursive: true, force: true });
  }
});
