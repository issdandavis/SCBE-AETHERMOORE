import { describe, it, expect, test, vi } from 'vitest';
import { createEnvelope, verifyEnvelope } from '../src/crypto/envelope.js';

test('session mismatch blocks reuse across sessions (HIGH-001 fix: key derivation binding)', async () => {
  const e1 = await createEnvelope({
    kid: 'key-v1',
    env: 'prod',
    provider_id: 'prov',
    model_id: 'm1',
    intent_id: 'i1',
    phase: 'request',
    ttlMs: 60_000,
    content_type: 'application/json',
    schema_hash: 'hash',
    request_id: 'r4',
    session_id: 'session-A',
    body: { x: 1 },
  });
  // Session binding now via key derivation instead of nonce prefix
  // Different session_id derives different key, causing auth failure
  await expect(verifyEnvelope({ envelope: e1, session_id: 'session-B' })).rejects.toThrow(
    'auth-failed'
  );
});

test('mid-flight provider swap requires fresh envelope', async () => {
  const e1 = await createEnvelope({
    kid: 'key-v1',
    env: 'prod',
    provider_id: 'provA',
    model_id: 'm1',
    intent_id: 'i1',
    phase: 'request',
    ttlMs: 60_000,
    content_type: 'application/json',
    schema_hash: 'hash',
    request_id: 'r5',
    session_id: 's1',
    body: { x: 1 },
  });
  e1.aad.provider_id = 'provB';
  await expect(verifyEnvelope({ envelope: e1, session_id: 's1' })).rejects.toThrow();
});

test('expired envelope rejected (HIGH-002 fix: TTL enforcement)', async () => {
  // Create envelope with 100ms TTL
  const e1 = await createEnvelope({
    kid: 'key-v1',
    env: 'prod',
    provider_id: 'prov',
    model_id: 'm1',
    intent_id: 'i1',
    phase: 'request',
    ttlMs: 100, // 100ms TTL
    content_type: 'application/json',
    schema_hash: 'hash',
    request_id: 'r6-ttl-test',
    session_id: 's1',
    body: { x: 1 },
  });

  // Verify works immediately
  const result = await verifyEnvelope({ envelope: e1, session_id: 's1' });
  expect(result.body).toEqual({ x: 1 });

  // Wait for TTL to expire
  await new Promise((resolve) => setTimeout(resolve, 150));

  // Create a new envelope with same params but different request_id (to avoid replay)
  const e2 = await createEnvelope({
    kid: 'key-v1',
    env: 'prod',
    provider_id: 'prov',
    model_id: 'm1',
    intent_id: 'i1',
    phase: 'request',
    ttlMs: 100, // 100ms TTL
    content_type: 'application/json',
    schema_hash: 'hash',
    request_id: 'r7-ttl-test',
    session_id: 's1',
    body: { x: 2 },
  });

  // Manually backdate the timestamp to simulate expiration
  e2.aad.ts = Date.now() - 200; // 200ms in the past

  // Should reject as expired
  await expect(verifyEnvelope({ envelope: e2, session_id: 's1' })).rejects.toThrow('expired');
});

test('envelope within TTL window accepted', async () => {
  const e1 = await createEnvelope({
    kid: 'key-v1',
    env: 'prod',
    provider_id: 'prov',
    model_id: 'm1',
    intent_id: 'i1',
    phase: 'request',
    ttlMs: 60_000, // 60 second TTL
    content_type: 'application/json',
    schema_hash: 'hash',
    request_id: 'r8-ttl-valid',
    session_id: 's1',
    body: { valid: true },
  });

  // Should verify successfully within TTL window
  const result = await verifyEnvelope({ envelope: e1, session_id: 's1' });
  expect(result.body).toEqual({ valid: true });
});
