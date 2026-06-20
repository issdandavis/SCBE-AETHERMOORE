'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const log = require('../lib/utterance-log.js');

function tmpLog() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-utt-'));
  return path.join(dir, 'utterance-log.jsonl');
}

const FIXED = new Date('2026-06-06T12:00:00.000Z');

test('logUtterance writes a redacted JSONL record', () => {
  const logPath = tmpLog();
  const ok = log.logUtterance(
    {
      utterance: '  scan   my repo  ',
      tool: 'scbe-antivirus',
      score: 0.91,
      decision: 'ROUTE',
      mode: 'ai',
    },
    { logPath, now: FIXED, enabled: true }
  );
  assert.equal(ok, true);
  const records = log.readLog(logPath);
  assert.equal(records.length, 1);
  const r = records[0];
  assert.equal(r.utterance, 'scan my repo'); // whitespace collapsed
  assert.equal(r.tool, 'scbe-antivirus');
  assert.equal(r.score, 0.91);
  assert.equal(r.decision, 'ROUTE');
  assert.equal(r.confirmed, false);
  assert.equal(r.ts, '2026-06-06T12:00:00.000Z');
  assert.equal(r.v, log.SCHEMA_VERSION);
});

test('redact scrubs emails, api keys, bearer tokens, long digit runs', () => {
  assert.match(log.redact('mail me at jane.doe@example.com'), /\[email\]/);
  assert.match(log.redact('key sk-ABCD1234efgh5678ijkl'), /\[secret\]/);
  assert.match(log.redact('ghp_0123456789abcdefghij token'), /\[secret\]/);
  assert.match(log.redact('use Bearer abcdef0123456789xyz now'), /\[token\]/);
  assert.match(log.redact('card 4111111111111111 please'), /\[number\]/);
  // a 40+ char opaque token is scrubbed; normal words survive
  assert.match(log.redact('hash ' + 'a'.repeat(48)), /\[token\]/);
  assert.equal(
    log.redact('search arxiv for hyperbolic embeddings'),
    'search arxiv for hyperbolic embeddings'
  );
});

test('opt-out via env and opts.enabled disables writes', () => {
  const logPath = tmpLog();
  assert.equal(log.logUtterance({ utterance: 'x', tool: 't' }, { logPath, enabled: false }), false);
  const prev = process.env.SCBE_NO_UTTERANCE_LOG;
  process.env.SCBE_NO_UTTERANCE_LOG = '1';
  try {
    assert.equal(log.isEnabled(), false);
    assert.equal(log.logUtterance({ utterance: 'x', tool: 't' }, { logPath }), false);
  } finally {
    if (prev === undefined) delete process.env.SCBE_NO_UTTERANCE_LOG;
    else process.env.SCBE_NO_UTTERANCE_LOG = prev;
  }
  assert.equal(fs.existsSync(logPath), false);
});

test('empty / whitespace / secret-only utterances are dropped', () => {
  const logPath = tmpLog();
  assert.equal(
    log.logUtterance({ utterance: '   ', tool: 't' }, { logPath, enabled: true }),
    false
  );
  assert.equal(log.logUtterance({ utterance: '', tool: 't' }, { logPath, enabled: true }), false);
  assert.equal(log.readLog(logPath).length, 0);
});

test('logUtterance never throws and returns false on bad path', () => {
  // a path whose parent cannot be created (file used as a directory component)
  const file = tmpLog();
  fs.writeFileSync(file, 'x');
  const bad = path.join(file, 'nested', 'log.jsonl');
  assert.doesNotThrow(() => {
    const ok = log.logUtterance(
      { utterance: 'hello there', tool: 't' },
      { logPath: bad, enabled: true }
    );
    assert.equal(ok, false);
  });
});

test('readLog skips corrupt lines, keeps valid ones', () => {
  const logPath = tmpLog();
  fs.mkdirSync(path.dirname(logPath), { recursive: true });
  fs.writeFileSync(
    logPath,
    '{"v":1,"utterance":"ok","tool":"a"}\nNOT JSON\n{"v":1,"utterance":"two","tool":"b"}\n'
  );
  const records = log.readLog(logPath);
  assert.equal(records.length, 2);
  assert.deepEqual(
    records.map((r) => r.tool),
    ['a', 'b']
  );
});

test('buildCorpus groups by tool, dedups, and honors filters', () => {
  const logPath = tmpLog();
  const w = (utterance, tool, score, decision, confirmed) =>
    log.logUtterance(
      { utterance, tool, score, decision, confirmed },
      { logPath, enabled: true, now: FIXED }
    );
  w('scan my repo', 'scbe-antivirus', 0.9, 'ROUTE', true);
  w('Scan My Repo', 'scbe-antivirus', 0.9, 'ROUTE', true); // dup (case-insensitive)
  w('check for malware', 'scbe-antivirus', 0.8, 'ROUTE', false);
  w('low confidence guess', 'scbe-antivirus', 0.2, 'ROUTE', false);
  w('what is the meaning of life', null, 0.05, 'REFUSE', false); // refused -> no label
  w('seal this payload', 'geoseal-seal', 0.95, 'ROUTE', true);

  const all = log.buildCorpus({ logPath });
  assert.deepEqual(all['scbe-antivirus'], [
    'scan my repo',
    'check for malware',
    'low confidence guess',
  ]);
  assert.deepEqual(all['geoseal-seal'], ['seal this payload']);
  assert.equal(Object.prototype.hasOwnProperty.call(all, 'null'), false);

  const confident = log.buildCorpus({ logPath, minScore: 0.5 });
  assert.equal(confident['scbe-antivirus'].length, 2); // 0.2 dropped

  const confirmed = log.buildCorpus({ logPath, confirmedOnly: true });
  assert.deepEqual(confirmed['scbe-antivirus'], ['scan my repo']);
});

test('buildCorpus maxPerTool keeps the most recent phrasings', () => {
  const logPath = tmpLog();
  for (const u of ['one', 'two', 'three']) {
    log.logUtterance({ utterance: u, tool: 't', decision: 'ROUTE' }, { logPath, enabled: true });
  }
  const corpus = log.buildCorpus({ logPath, maxPerTool: 2 });
  assert.deepEqual(corpus['t'], ['two', 'three']);
});

test('stats reports totals, per-tool counts, and date range', () => {
  const logPath = tmpLog();
  log.logUtterance(
    { utterance: 'a', tool: 'x', decision: 'ROUTE' },
    { logPath, enabled: true, now: FIXED }
  );
  log.logUtterance(
    { utterance: 'b', tool: 'x', decision: 'ROUTE' },
    { logPath, enabled: true, now: FIXED }
  );
  log.logUtterance(
    { utterance: 'c', tool: null, decision: 'REFUSE' },
    { logPath, enabled: true, now: FIXED }
  );
  const s = log.stats(logPath);
  assert.equal(s.total, 3);
  assert.equal(s.routed, 2);
  assert.equal(s.refused, 1);
  assert.equal(s.tools, 1);
  assert.equal(s.perTool.x, 2);
  assert.equal(s.first, '2026-06-06T12:00:00.000Z');
});
