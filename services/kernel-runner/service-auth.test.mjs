import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { randomBytes } from 'node:crypto';
import {
  AUTH_VERSION,
  DECISION_VERSION,
  ReplayGuard,
  sha256Hex,
  signDecisionReceipt,
  signServiceRequest,
  verifyDecisionReceipt,
  verifyServiceRequest,
} from './service-auth.mjs';

const SERVICE_KEY = '0123456789abcdef0123456789abcdef';
const FIXED_TIMESTAMP = 1_700_000_000_000;
const FIXED_NONCE = 'ABCDEFGHIJKLMNOPQRSTUV';

function requestHeaders({
  body,
  path = '/api/run',
  timestampMs = Date.now(),
  nonce = randomBytes(18).toString('base64url'),
}) {
  return {
    'content-type': 'application/json',
    'x-scbe-auth-version': AUTH_VERSION,
    'x-scbe-timestamp': String(timestampMs),
    'x-scbe-nonce': nonce,
    'x-scbe-signature': signServiceRequest({
      secret: SERVICE_KEY,
      method: 'POST',
      path,
      timestampMs,
      nonce,
      body,
    }),
  };
}

test('HMAC matches the public Python/JavaScript test vector', () => {
  const signature = signServiceRequest({
    secret: SERVICE_KEY,
    method: 'POST',
    path: '/api/run',
    timestampMs: FIXED_TIMESTAMP,
    nonce: FIXED_NONCE,
    body: Buffer.from('x'),
  });
  assert.equal(signature, '791d5491861f47a3826e1136548c3cd0fc552f5954f3c2dacb0fac0292c0854a');
});

test('decision receipt matches the public Python/JavaScript test vector', () => {
  const signature = signDecisionReceipt({
    secret: SERVICE_KEY,
    requestMethod: 'POST',
    requestPath: '/api/run',
    requestDigest: sha256Hex(Buffer.from('x')),
    requestNonce: FIXED_NONCE,
    timestamp: '2026-09-19T12:34:56.000Z',
    action: 'ALLOW',
    confidence: 0.92,
    stateVector: { coherence: 1, energy: 0.75, drift: 0 },
    reason: 'Verification scores passed policy.',
  });
  assert.equal(
    signature,
    'd3bf7a3822ba5e783612e10840a960014d7ac95f494594c430d5aaa0cc1a1704'
  );
});

test('verification binds destination and rejects replay', () => {
  const body = Buffer.from('x');
  const headers = requestHeaders({ body, timestampMs: FIXED_TIMESTAMP, nonce: FIXED_NONCE });
  const replayGuard = new ReplayGuard();
  const first = verifyServiceRequest({
    secret: SERVICE_KEY,
    method: 'POST',
    path: '/api/run',
    body,
    headers,
    nowMs: FIXED_TIMESTAMP,
    replayGuard,
  });
  const replay = verifyServiceRequest({
    secret: SERVICE_KEY,
    method: 'POST',
    path: '/api/run',
    body,
    headers,
    nowMs: FIXED_TIMESTAMP,
    replayGuard,
  });
  const wrongPath = verifyServiceRequest({
    secret: SERVICE_KEY,
    method: 'POST',
    path: '/api/preflight',
    body,
    headers,
    nowMs: FIXED_TIMESTAMP,
    replayGuard: new ReplayGuard(),
  });

  assert.equal(first.ok, true);
  assert.equal(replay.code, 'service_request_replay');
  assert.equal(wrongPath.code, 'invalid_service_auth');
});

test('verification rejects stale requests and weak service secrets', () => {
  const body = Buffer.from('x');
  const headers = requestHeaders({ body, timestampMs: FIXED_TIMESTAMP, nonce: FIXED_NONCE });
  assert.equal(
    verifyServiceRequest({
      secret: SERVICE_KEY,
      method: 'POST',
      path: '/api/run',
      body,
      headers,
      nowMs: FIXED_TIMESTAMP + 60_001,
    }).code,
    'stale_service_request'
  );
  assert.equal(
    verifyServiceRequest({
      secret: 'short',
      method: 'POST',
      path: '/api/run',
      body,
      headers,
      nowMs: FIXED_TIMESTAMP,
    }).code,
    'service_auth_not_configured'
  );
});

test('replay cache saturation fails closed without evicting live nonces', () => {
  const replayGuard = new ReplayGuard({ windowMs: 1_000, maxEntries: 1 });
  const first = replayGuard.consume('first-live-nonce', FIXED_TIMESTAMP);
  const saturated = replayGuard.consume('second-live-nonce', FIXED_TIMESTAMP);
  const replay = replayGuard.consume('first-live-nonce', FIXED_TIMESTAMP);
  const afterExpiry = replayGuard.consume(
    'second-live-nonce',
    FIXED_TIMESTAMP + 1_001
  );

  assert.deepEqual(first, { ok: true, code: 'service_request_fresh' });
  assert.deepEqual(saturated, {
    ok: false,
    code: 'service_replay_cache_full',
  });
  assert.deepEqual(replay, { ok: false, code: 'service_request_replay' });
  assert.deepEqual(afterExpiry, { ok: true, code: 'service_request_fresh' });
});

process.env.KERNEL_RUNNER_SHARED_SECRET = SERVICE_KEY;
const { app } = await import(`./server.mjs?security-test=${Date.now()}`);
let server;
let baseUrl;

before(async () => {
  await new Promise((resolve) => {
    server = app.listen(0, '127.0.0.1', resolve);
  });
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  if (!server) return;
  await new Promise((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
});

const allowedPayload = {
  packageJson: {
    name: 'auth-test',
    version: '1.0.0',
    private: true,
    scripts: { test: 'node index.js' },
  },
  files: {
    'index.js': `console.log('authenticated preflight');\n${'// padding\n'.repeat(20)}`,
  },
  runCommand: 'npm test',
};

test('protected runner routes reject unsigned requests', async () => {
  const response = await fetch(`${baseUrl}/api/preflight`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(allowedPayload),
  });
  assert.equal(response.status, 401);
  assert.equal((await response.json()).error, 'invalid_service_auth');
});

test('protected runner routes accept one signed request and reject its replay', async () => {
  const path = '/api/preflight';
  const body = JSON.stringify(allowedPayload);
  const headers = requestHeaders({ body: Buffer.from(body), path });
  const first = await fetch(`${baseUrl}${path}`, { method: 'POST', headers, body });
  const replay = await fetch(`${baseUrl}${path}`, { method: 'POST', headers, body });

  assert.equal(first.status, 200);
  const responseBody = await first.json();
  const decision = responseBody.decision_record;
  assert.equal(decision.action, 'ALLOW');
  assert.equal(decision.signature_version, DECISION_VERSION);
  assert.equal(decision.request_method, 'POST');
  assert.equal(decision.request_path, path);
  assert.equal(decision.request_digest, sha256Hex(Buffer.from(body)));
  assert.equal(decision.request_nonce, headers['x-scbe-nonce']);
  assert.equal(
    verifyDecisionReceipt({
      secret: SERVICE_KEY,
      signature: decision.signature,
      requestMethod: decision.request_method,
      requestPath: decision.request_path,
      requestDigest: decision.request_digest,
      requestNonce: decision.request_nonce,
      timestamp: decision.timestamp,
      action: decision.action,
      confidence: decision.confidence,
      stateVector: responseBody.state_vector,
      reason: decision.reason,
    }),
    true
  );
  assert.equal(
    verifyDecisionReceipt({
      secret: SERVICE_KEY,
      signature: decision.signature,
      requestMethod: decision.request_method,
      requestPath: '/api/run',
      requestDigest: decision.request_digest,
      requestNonce: decision.request_nonce,
      timestamp: decision.timestamp,
      action: decision.action,
      confidence: decision.confidence,
      stateVector: responseBody.state_vector,
      reason: decision.reason,
    }),
    false
  );
  assert.equal(replay.status, 409);
  assert.equal((await replay.json()).error, 'service_request_replay');
});

test('protected runner routes reject a body changed after signing', async () => {
  const path = '/api/preflight';
  const signedBody = JSON.stringify(allowedPayload);
  const changedBody = JSON.stringify({ ...allowedPayload, runCommand: 'npm run changed' });
  const response = await fetch(`${baseUrl}${path}`, {
    method: 'POST',
    headers: requestHeaders({ body: Buffer.from(signedBody), path }),
    body: changedBody,
  });
  assert.equal(response.status, 401);
  assert.equal((await response.json()).error, 'invalid_service_auth');
});
