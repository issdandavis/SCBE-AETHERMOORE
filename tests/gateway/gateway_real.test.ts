/**
 * Gateway real-behavior tests — green must mean *working*, not faked.
 *
 * Asserts the properties the old placeholders violated:
 *  - the risk score is deterministic (no Math.random feeding ALLOW/DENY),
 *  - tampering the request changes the risk (the decision depends on input),
 *  - envelope signatures are real HMAC (a forged signature is rejected),
 *  - quantum key exchange returns a real ML-KEM-768 public key.
 */
import { describe, it, expect } from 'vitest';
import { UnifiedSCBEGateway } from '../../src/gateway/unified-api.js';

describe('gateway real behavior (no fakes)', () => {
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

  it('QKE returns a real ML-KEM-768 public key (1184 bytes)', async () => {
    const gw = new UnifiedSCBEGateway();
    const kex = await gw.initiateQuantumKeyExchange('peer1');
    expect(Buffer.from(kex.publicKey, 'base64').length).toBe(1184);
  });
});
