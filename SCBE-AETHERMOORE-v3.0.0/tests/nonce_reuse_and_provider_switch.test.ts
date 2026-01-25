import { describe, it, expect, test } from 'vitest';
import { createEnvelope, verifyEnvelope } from '../src/crypto/envelope.js';

test('nonce prefix mismatch blocks reuse across sessions', async () => {
  const e1 = await createEnvelope({
    kid: 'key-v1', env: 'prod', provider_id: 'prov', model_id: 'm1', intent_id: 'i1',
    phase: 'request', ttlMs: 60_000, content_type: 'application/json', schema_hash: 'hash',
    request_id: 'r4', session_id: 'session-A', body: {x:1}
  });
  await expect(verifyEnvelope({ envelope: e1, session_id: 'session-B' })).rejects.toThrow('nonce/prefix');
});

test('mid-flight provider swap requires fresh envelope', async () => {
  const e1 = await createEnvelope({
    kid: 'key-v1', env: 'prod', provider_id: 'provA', model_id: 'm1', intent_id: 'i1',
    phase: 'request', ttlMs: 60_000, content_type: 'application/json', schema_hash: 'hash',
    request_id: 'r5', session_id: 's1', body: {x:1}
  });
  e1.aad.provider_id = 'provB';
  await expect(verifyEnvelope({ envelope: e1, session_id: 's1' })).rejects.toThrow();
});
