import { createEnvelope, verifyEnvelope } from '../src/crypto/envelope.js';

test('create/verify within budget under normal load', async () => {
  const envl = await createEnvelope({
    kid: 'key-v1', env: 'prod', provider_id: 'prov', model_id: 'm1', intent_id: 'i1',
    phase: 'request', ttlMs: 60_000, content_type: 'application/json', schema_hash: 'hash',
    request_id: 'r6', session_id: 's1', body: {payload: 'x'.repeat(512)}
  });
  const t0 = performance.now();
  await verifyEnvelope({ envelope: envl, session_id: 's1' });
  const dt = performance.now() - t0;
  expect(dt).toBeLessThan(25);
});
