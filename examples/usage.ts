import { createEnvelope, verifyEnvelope } from '../src/crypto/envelope.js';

async function main() {
  const envl = await createEnvelope({
    kid: process.env.SCBE_KMS_KID || 'key-v1',
    env: process.env.SCBE_ENV || 'prod',
    provider_id: process.env.SCBE_PROVIDER_ID || 'provider.example',
    model_id: process.env.SCBE_MODEL_ID || 'model.v1',
    intent_id: 'demo.intent',
    phase: 'request',
    ttlMs: 60_000,
    content_type: 'application/json',
    schema_hash: 'deadbeef',
    request_id: 'req-' + Math.random().toString(36).slice(2, 10),
    session_id: 'session-123',
    body: { hello: 'world' }
  });

  const out = await verifyEnvelope({ envelope: envl, session_id: 'session-123' });
  console.log('DECRYPTED:', out.body);
}

main().catch(e => {
  console.error('error', e.message);
  process.exit(1);
});
