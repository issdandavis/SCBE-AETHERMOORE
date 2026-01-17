import { createEnvelope, verifyEnvelope } from '../src/crypto/envelope.js';

test('AAD tamper fails auth (noise only)', async () => {
  const envl = await createEnvelope({
    kid: 'key-v1', env: 'prod',
    provider_id: 'prov', model_id: 'm1', intent_id: 'i1', phase: 'request',
    ttlMs: 60_000, content_type: 'application/json', schema_hash: 'hash',
    request_id: 'r1', session_id: 's1', body: {a:1}
  });
  // Flip 1 bit in AAD canonical string by changing ts
  envl.aad.ts = envl.aad.ts + 1;
  await expect(verifyEnvelope({ envelope: envl, session_id: 's1' })).rejects.toThrow();
});

test('Body tamper fails auth', async () => {
  const envl = await createEnvelope({
    kid: 'key-v1', env: 'prod',
    provider_id: 'prov', model_id: 'm1', intent_id: 'i1', phase: 'request',
    ttlMs: 60_000, content_type: 'application/json', schema_hash: 'hash',
    request_id: 'r2', session_id: 's1', body: {a:1}
  });
  // mutate ciphertext
  envl.ciphertext = envl.ciphertext.slice(0,-1) + (envl.ciphertext.slice(-1) === 'A' ? 'B' : 'A');
  await expect(verifyEnvelope({ envelope: envl, session_id: 's1' })).rejects.toThrow();
});

test('Timestamp skew rejected', async () => {
  const envl = await createEnvelope({
    kid: 'key-v1', env: 'prod',
    provider_id: 'prov', model_id: 'm1', intent_id: 'i1', phase: 'request',
    ttlMs: 60_000, content_type: 'application/json', schema_hash: 'hash',
    request_id: 'r3', session_id: 's1', body: {a:1}
  });
  // Force old ts
  envl.aad.ts = envl.aad.ts - (3 * 60 * 1000);
  await expect(verifyEnvelope({ envelope: envl, session_id: 's1' })).rejects.toThrow('skew/replay');
});
