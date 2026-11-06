'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const HASH_SUITE = 'scbe_agent_multihash_v1';
const CHAIN_SCHEMA = 'scbe_chained_receipt_v1';
const GENESIS_ROOT = crypto
  .createHash('sha256')
  .update('SCBE-CHAINED-RECEIPT-v1/genesis', 'utf8')
  .digest('hex');
const MAX_LEDGER_BYTES = 32 * 1024 * 1024;
const LOCK_STALE_MS = 30_000;

function normalizeCanonical(value, seen = new WeakSet()) {
  if (value === null) return null;
  if (typeof value === 'string' || typeof value === 'boolean') return value;
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error('canonical JSON rejects non-finite numbers');
    return Object.is(value, -0) ? 0 : value;
  }
  if (typeof value === 'bigint') return { $bigint: value.toString(10) };
  if (Buffer.isBuffer(value)) return { $bytes_hex: value.toString('hex') };
  if (value instanceof Date) return { $date: value.toISOString() };
  if (typeof value !== 'object') throw new Error('canonical JSON rejects unsupported values');
  if (seen.has(value)) throw new Error('canonical JSON rejects cyclic values');

  seen.add(value);
  try {
    if (Array.isArray(value)) return value.map((item) => normalizeCanonical(item, seen));
    const output = {};
    for (const key of Object.keys(value).sort()) {
      const item = value[key];
      if (item === undefined || typeof item === 'function' || typeof item === 'symbol') continue;
      output[key] = normalizeCanonical(item, seen);
    }
    return output;
  } finally {
    seen.delete(value);
  }
}

function canonicalJson(value) {
  return JSON.stringify(normalizeCanonical(value));
}

function multiHashBytes(value) {
  const bytes = Buffer.isBuffer(value) ? value : Buffer.from(value);
  return {
    sha256: crypto.createHash('sha256').update(bytes).digest('hex'),
    sha3_256: crypto.createHash('sha3-256').update(bytes).digest('hex'),
    blake2s_256: crypto.createHash('blake2s256').update(bytes).digest('hex'),
    blake2b_512: crypto.createHash('blake2b512').update(bytes).digest('hex'),
  };
}

function multiHashJson(value) {
  return multiHashBytes(Buffer.from(canonicalJson(value), 'utf8'));
}

function multiHashRoot(hashes, domain = 'SCBE-MULTI-HASH-v1') {
  return crypto
    .createHash('sha256')
    .update(domain + '\0' + canonicalJson(hashes), 'utf8')
    .digest('hex');
}

function compoundHashRoot(hashes, domain = 'SCBE-COMPOUND-MULTI-HASH-v1') {
  const rootHashes = multiHashBytes(Buffer.from(domain + '\0' + canonicalJson(hashes), 'utf8'));
  return [
    'scbe-mh1',
    rootHashes.sha256,
    rootHashes.sha3_256,
    rootHashes.blake2s_256,
    rootHashes.blake2b_512,
  ].join(':');
}

function safeEqual(left, right) {
  const a = Buffer.from(String(left || ''), 'utf8');
  const b = Buffer.from(String(right || ''), 'utf8');
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function sameHashes(left, right) {
  if (!left || !right) return false;
  return ['sha256', 'sha3_256', 'blake2s_256', 'blake2b_512'].every((name) =>
    safeEqual(left[name], right[name])
  );
}

function buildChainedReceipt(payload, options = {}) {
  const sequence = Number(options.sequence || 1);
  if (!Number.isSafeInteger(sequence) || sequence < 1) throw new Error('invalid receipt sequence');
  const previousRoot = String(options.previousRoot || GENESIS_ROOT);
  const body = {
    schema_version: CHAIN_SCHEMA,
    receipt_type: String(options.receiptType || 'generic'),
    hash_suite: HASH_SUITE,
    sequence,
    previous_root: previousRoot,
    created_at: (options.now || new Date()).toISOString(),
    payload: normalizeCanonical(payload),
  };
  const payloadHashes = multiHashJson(body.payload);
  const envelope = { ...body, payload_hashes: payloadHashes };
  const envelopeHashes = multiHashJson(envelope);
  return {
    ...envelope,
    envelope_hashes: envelopeHashes,
    receipt_root: compoundHashRoot(envelopeHashes, 'SCBE-CHAINED-RECEIPT-v1/root'),
  };
}

function verifyChainedReceipt(receipt, expected = {}) {
  const errors = [];
  if (!receipt || receipt.schema_version !== CHAIN_SCHEMA)
    errors.push('unsupported receipt schema');
  if (receipt?.hash_suite !== HASH_SUITE) errors.push('unsupported hash suite');
  if (expected.sequence !== undefined && receipt?.sequence !== expected.sequence) {
    errors.push('sequence mismatch');
  }
  if (
    expected.previousRoot !== undefined &&
    !safeEqual(receipt?.previous_root, expected.previousRoot)
  ) {
    errors.push('previous root mismatch');
  }
  if (!errors.length) {
    const payloadHashes = multiHashJson(receipt.payload);
    if (!sameHashes(payloadHashes, receipt.payload_hashes)) errors.push('payload hash mismatch');
    const envelope = {
      schema_version: receipt.schema_version,
      receipt_type: receipt.receipt_type,
      hash_suite: receipt.hash_suite,
      sequence: receipt.sequence,
      previous_root: receipt.previous_root,
      created_at: receipt.created_at,
      payload: receipt.payload,
      payload_hashes: receipt.payload_hashes,
    };
    const envelopeHashes = multiHashJson(envelope);
    if (!sameHashes(envelopeHashes, receipt.envelope_hashes)) errors.push('envelope hash mismatch');
    const root = compoundHashRoot(envelopeHashes, 'SCBE-CHAINED-RECEIPT-v1/root');
    if (!safeEqual(root, receipt.receipt_root)) errors.push('receipt root mismatch');
  }
  return { ok: errors.length === 0, errors };
}

function legacyRoot(previousRoot, rawLine) {
  return crypto
    .createHash('sha256')
    .update('SCBE-LEGACY-RECEIPT-v1\0' + previousRoot + '\0' + rawLine, 'utf8')
    .digest('hex');
}

function readLedgerLines(filePath) {
  if (!fs.existsSync(filePath)) return [];
  const stat = fs.statSync(filePath);
  if (stat.size > MAX_LEDGER_BYTES) {
    throw new Error('receipt ledger exceeds the verification limit');
  }
  return fs
    .readFileSync(filePath, 'utf8')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function verifyReceiptFile(filePath) {
  const lines = readLedgerLines(filePath);
  let currentRoot = GENESIS_ROOT;
  let receiptCount = 0;
  let legacyCount = 0;
  let sawChain = false;
  const errors = [];
  const receipts = [];

  for (let index = 0; index < lines.length; index += 1) {
    let row;
    try {
      row = JSON.parse(lines[index]);
    } catch (_error) {
      errors.push('line ' + (index + 1) + ': invalid JSON');
      break;
    }
    if (row.schema_version !== CHAIN_SCHEMA) {
      if (sawChain) {
        errors.push('line ' + (index + 1) + ': legacy receipt after chained receipts');
        break;
      }
      legacyCount += 1;
      currentRoot = legacyRoot(currentRoot, lines[index]);
      continue;
    }
    sawChain = true;
    const expectedSequence = receiptCount + 1;
    const checked = verifyChainedReceipt(row, {
      sequence: expectedSequence,
      previousRoot: currentRoot,
    });
    if (!checked.ok) {
      errors.push('line ' + (index + 1) + ': ' + checked.errors.join(', '));
      break;
    }
    receiptCount += 1;
    currentRoot = row.receipt_root;
    receipts.push(row);
  }

  return {
    ok: errors.length === 0,
    file: filePath,
    lines: lines.length,
    legacy_receipts: legacyCount,
    chained_receipts: receiptCount,
    root: currentRoot,
    errors,
    receipts,
  };
}

function sleepSync(milliseconds) {
  const state = new Int32Array(new SharedArrayBuffer(4));
  Atomics.wait(state, 0, 0, milliseconds);
}

function withLedgerLock(filePath, callback) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const lockPath = filePath + '.lock';
  let handle = null;
  for (let attempt = 0; attempt < 50; attempt += 1) {
    try {
      handle = fs.openSync(lockPath, 'wx', 0o600);
      fs.writeFileSync(handle, JSON.stringify({ pid: process.pid, at: new Date().toISOString() }));
      break;
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
      try {
        if (Date.now() - fs.statSync(lockPath).mtimeMs > LOCK_STALE_MS) fs.unlinkSync(lockPath);
      } catch (_statError) {
        // Another writer may have released the lock between checks.
      }
      sleepSync(10);
    }
  }
  if (handle === null) throw new Error('receipt ledger is busy');
  try {
    return callback();
  } finally {
    try {
      fs.closeSync(handle);
    } finally {
      try {
        fs.unlinkSync(lockPath);
      } catch (_error) {
        // The lock may already have been cleared after a process interruption.
      }
    }
  }
}

function appendChainedReceipt(filePath, payload, options = {}) {
  return withLedgerLock(filePath, () => {
    const state = verifyReceiptFile(filePath);
    if (!state.ok)
      throw new Error('receipt ledger verification failed: ' + state.errors.join('; '));
    const receipt = buildChainedReceipt(payload, {
      receiptType: options.receiptType,
      now: options.now,
      sequence: state.chained_receipts + 1,
      previousRoot: state.root,
    });
    fs.appendFileSync(filePath, canonicalJson(receipt) + '\n', 'utf8');
    return receipt;
  });
}

module.exports = {
  HASH_SUITE,
  CHAIN_SCHEMA,
  GENESIS_ROOT,
  canonicalJson,
  multiHashBytes,
  multiHashJson,
  multiHashRoot,
  compoundHashRoot,
  sameHashes,
  buildChainedReceipt,
  verifyChainedReceipt,
  verifyReceiptFile,
  appendChainedReceipt,
};
