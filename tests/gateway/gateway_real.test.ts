/**
 * Gateway real-behavior tests — green must mean *working*, not faked.
 *
 * Asserts the properties the old placeholders violated:
 *  - the risk score is deterministic (no Math.random feeding ALLOW/DENY),
 *  - tampering the request changes the risk (the decision depends on input),
 *  - envelope signatures are real HMAC (a forged signature is rejected),
 *  - quantum key exchange returns a real ML-KEM-768 public key.
 */
import crypto from 'node:crypto';
import { afterEach, beforeEach, describe, it, expect } from 'vitest';
import { UnifiedSCBEGateway } from '../../src/gateway/unified-api.js';

describe('gateway real behavior (no fakes)', () => {
  const originalGatewaySecret = process.env.SCBE_GATEWAY_HMAC_SECRET;

  beforeEach(() => {
    process.env.SCBE_GATEWAY_HMAC_SECRET = 'gateway-real-test-secret';
  });

  afterEach(() => {
    if (originalGatewaySecret === undefined) {
      delete process.env.SCBE_GATEWAY_HMAC_SECRET;
    } else {
      process.env.SCBE_GATEWAY_HMAC_SECRET = originalGatewaySecret;
    }
  });

  it('authorize risk is deterministic (no Math.random)', async () => {
    const gw = new UnifiedSCBEGateway();
    const req = { agentId: 'a1', action: 'read', target: 'doc/x', tongues: ['KO' as const] };
    const d1 = await gw.authorize(req as never);
    const d2 = await gw.authorize(req as never);
    expect(d1.riskFactors.compositeRisk).toBe(d2.riskFactors.compositeRisk);
  });

  it('tampering the request changes the risk', async () => {
    const gw = new UnifiedSCBEGateway();
    const a = await gw.authorize({ agentId: 'a1', action: 'read', target: 'doc/x' } as never);
    const b = await gw.authorize({ agentId: 'a1', action: 'delete_all', target: 'doc/x' } as never);
    expect(a.riskFactors.compositeRisk).not.toBe(b.riskFactors.compositeRisk);
  });

  it('envelope signatures round-trip and reject forgery (real HMAC)', async () => {
    const gw = new UnifiedSCBEGateway();
    const env = await gw.encodeRWP({ hello: 'world' }, ['KO']);
    const ok = await gw.decodeRWP(env);
    expect(ok.valid).toBe(true);

    const forged = { ...env, signatures: { ...env.signatures, KO: 'sig_KO_forged' } };
    const bad = await gw.decodeRWP(forged as never);
    expect(bad.valid).toBe(false);
  });

  it('rejects independently forged envelopes that rely on the old public fallback secret', async () => {
    delete process.env.SCBE_GATEWAY_HMAC_SECRET;
    const payload = Buffer.from(JSON.stringify({ role: 'admin', action: 'delete_all' })).toString(
      'base64url'
    );
    const nonce = 'attacker-controlled-nonce';
    const fallbackKey = crypto
      .createHmac('sha256', 'scbe-gateway-dev-secret')
      .update('tongue-key:KO')
      .digest();
    const mac = crypto
      .createHmac('sha256', fallbackKey)
      .update(`KO:${payload}:${nonce}`)
      .digest('base64url');

    const gw = new UnifiedSCBEGateway();
    const decoded = await gw.decodeRWP({
      ver: '2.1',
      primaryTongue: 'KO',
      payload,
      signatures: { KO: `sig_KO_${mac}` },
      nonce,
      timestamp: Date.now(),
      aad: 'gateway=unified;tongues=KO',
    });

    expect(decoded.valid).toBe(false);
    expect(decoded.error).toMatch(/SCBE_GATEWAY_HMAC_SECRET/);
  });

  it('QKE returns a real ML-KEM-768 public key (1184 bytes)', async () => {
    const gw = new UnifiedSCBEGateway();
    const kex = await gw.initiateQuantumKeyExchange('peer1');
    expect(Buffer.from(kex.publicKey, 'base64').length).toBe(1184);
  });
});
