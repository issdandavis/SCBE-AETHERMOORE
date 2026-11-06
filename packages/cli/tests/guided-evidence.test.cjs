'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const {
  appendChainedReceipt,
  canonicalJson,
  multiHashJson,
  verifyReceiptFile,
} = require('../lib/multi-hash-receipt');
const {
  evidenceDirectory,
  runGuidedEvidenceRoute,
  searchEvidencePackets,
  verifyEvidencePacket,
} = require('../lib/guided-evidence');
const { appendReceipt, receiptPath, verifyReceiptLedger } = require('../lib/session-store');

function makeTemp(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function removeTemp(target) {
  const resolved = path.resolve(target);
  const tempRoot = path.resolve(os.tmpdir()) + path.sep;
  assert.ok(resolved.startsWith(tempRoot), 'refusing to remove non-temp path: ' + resolved);
  fs.rmSync(resolved, { recursive: true, force: true });
}

test('multi-hash receipts are canonical, chained, and tamper evident', (t) => {
  const root = makeTemp('scbe-multihash-');
  t.after(() => removeTemp(root));
  const ledger = path.join(root, 'receipts.jsonl');

  assert.equal(canonicalJson({ z: 1, a: 2 }), canonicalJson({ a: 2, z: 1 }));
  const hashes = multiHashJson({ evidence: 'same bytes' });
  assert.deepEqual(Object.keys(hashes), ['sha256', 'sha3_256', 'blake2s_256', 'blake2b_512']);
  assert.equal(hashes.sha256.length, 64);
  assert.equal(hashes.sha3_256.length, 64);
  assert.equal(hashes.blake2s_256.length, 64);
  assert.equal(hashes.blake2b_512.length, 128);

  const first = appendChainedReceipt(ledger, { event: 'first' }, { receiptType: 'test' });
  const second = appendChainedReceipt(ledger, { event: 'second' }, { receiptType: 'test' });
  assert.equal(first.sequence, 1);
  assert.match(first.receipt_root, /^scbe-mh1:/);
  assert.equal(first.receipt_root.split(':').length, 5);
  assert.equal(second.sequence, 2);
  assert.equal(second.previous_root, first.receipt_root);
  assert.equal(verifyReceiptFile(ledger).ok, true);

  const tampered = path.join(root, 'tampered.jsonl');
  const rows = fs
    .readFileSync(ledger, 'utf8')
    .trim()
    .split(/\r?\n/)
    .map((line) => JSON.parse(line));
  rows[0].payload.event = 'changed';
  fs.writeFileSync(tampered, rows.map((row) => JSON.stringify(row)).join('\n') + '\n', 'utf8');
  const checked = verifyReceiptFile(tampered);
  assert.equal(checked.ok, false);
  assert.match(checked.errors.join(' '), /hash mismatch/);
});

test('agent tool receipts use the multi-hash chain and anchor legacy rows', (t) => {
  const workspaceRoot = makeTemp('scbe-tool-receipt-work-');
  const home = makeTemp('scbe-tool-receipt-home-');
  t.after(() => {
    removeTemp(workspaceRoot);
    removeTemp(home);
  });
  const filePath = receiptPath(workspaceRoot, { home });
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(
    filePath,
    JSON.stringify({ schema_version: 'scbe_agent_tool_receipt_v1', args_sha256: 'legacy' }) + '\n',
    'utf8'
  );

  const first = appendReceipt(
    workspaceRoot,
    {
      session_id: 'test-session',
      tool: 'read_file',
      kind: 'read',
      decision: 'ALLOW',
      ok: true,
      args: { path: 'README.md' },
      result: { ok: true },
    },
    { home, now: new Date('2026-10-29T00:00:00.000Z') }
  );
  const second = appendReceipt(
    workspaceRoot,
    {
      session_id: 'test-session',
      tool: 'search_text',
      kind: 'read',
      decision: 'ALLOW',
      ok: true,
      args: { query: 'receipt' },
      result: { ok: true, matches: 2 },
    },
    { home, now: new Date('2026-10-29T00:00:01.000Z') }
  );

  assert.equal(first.payload.schema_version, 'scbe_agent_tool_event_v2');
  assert.equal(first.payload.args_hashes.sha256, first.payload.args_sha256);
  assert.equal(second.previous_root, first.receipt_root);
  const verified = verifyReceiptLedger(workspaceRoot, { home });
  assert.equal(verified.ok, true);
  assert.equal(verified.legacy_receipts, 1);
  assert.equal(verified.chained_receipts, 2);
});

test('guided evidence stores full source material off-context and returns verifiable compact links', async (t) => {
  const workspaceRoot = makeTemp('scbe-evidence-work-');
  const home = makeTemp('scbe-evidence-home-');
  t.after(() => {
    removeTemp(workspaceRoot);
    removeTemp(home);
  });
  fs.writeFileSync(
    path.join(workspaceRoot, 'architecture.md'),
    'Guided evidence packets keep full search results outside the model context.\n',
    'utf8'
  );

  const longAbstract = 'bounded evidence detail '.repeat(250);
  const sourceRunner = async ({ source }) => {
    if (source === 'workspace') {
      return {
        ok: true,
        api: source,
        count: 1,
        results: [
          {
            title: 'architecture.md:1',
            summary: 'Guided evidence packets keep full results outside context.',
            url: 'workspace://architecture.md#L1',
          },
        ],
      };
    }
    if (source === 'semantic_scholar' || source === 'crossref') {
      return {
        ok: true,
        api: source,
        count: 1,
        results: [
          {
            title: 'Tamper Evident Context Packets for Guided Agents',
            doi: '10.1000/guided-packet',
            abstract: longAbstract,
            url: 'https://example.test/guided-packet',
          },
        ],
      };
    }
    return {
      ok: true,
      api: source,
      count: 1,
      results: [
        {
          name: 'example/guided-agent',
          description: longAbstract,
          url: 'https://github.com/example/guided-agent',
        },
      ],
    };
  };

  const compact = await runGuidedEvidenceRoute({
    workspaceRoot,
    home,
    objective: 'guided agent evidence packets and multi hash receipts',
    route: 'cross-check',
    limit: 2,
    tokenBudget: 800,
    packetId: 'packet-test',
    now: new Date('2026-10-29T01:02:03.000Z'),
    sourceRunner,
  });

  assert.equal(compact.ok, true);
  assert.equal(compact.packet_id, 'packet-test');
  assert.equal(compact.retrieval.raw_results_in_prompt, false);
  assert.ok(compact.evidence.length >= 2);
  assert.ok(compact.evidence.every((row) => row.id && row.proof_root));
  assert.ok(compact.cross_checks.some((row) => row.sources.includes('semantic_scholar')));
  assert.equal(compact.receipt.packet_hashes.blake2b_512.length, 128);
  assert.ok(compact.context_metrics.raw_characters > compact.context_metrics.returned_characters);
  assert.doesNotMatch(JSON.stringify(compact), /bounded evidence detail bounded evidence detail/);

  const searched = searchEvidencePackets(workspaceRoot, 'guided receipts', { home });
  assert.equal(searched.ok, true);
  assert.equal(searched.matches[0].packet_id, 'packet-test');

  const verified = verifyEvidencePacket(workspaceRoot, 'packet-test', { home });
  assert.equal(verified.ok, true, JSON.stringify(verified));
  assert.equal(verified.artifacts.length, 4);

  const artifact = path.join(
    evidenceDirectory(workspaceRoot, { home }),
    'artifacts',
    'packet-test',
    'semantic_scholar.json'
  );
  const changed = JSON.parse(fs.readFileSync(artifact, 'utf8'));
  changed.response.results[0].title = 'tampered title';
  fs.writeFileSync(artifact, JSON.stringify(changed, null, 2) + '\n', 'utf8');
  const rejected = verifyEvidencePacket(workspaceRoot, 'packet-test', { home });
  assert.equal(rejected.ok, false);
  assert.match(rejected.errors.join(' '), /artifacts failed verification/);
});
