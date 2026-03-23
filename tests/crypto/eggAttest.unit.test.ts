/**
 * @file eggAttest.unit.test.ts
 * @module tests/crypto/eggAttest
 * @layer Layer 1, Layer 13
 *
 * Unit tests for the Egg Attestation validator.
 * Tier: L2-unit
 */

import { describe, it, expect } from 'vitest';
import {
  validateEggAttest,
  allGatesPassed,
  type EggAttestPacket,
  type GateResults,
} from '../../src/crypto/eggAttestValidator.js';

/** Canonical valid packet matching the spec example. */
function makeValidPacket(overrides?: Partial<EggAttestPacket>): EggAttestPacket {
  return {
    spec: 'SCBE-AETHERMOORE/egg-attest@v1',
    agent_id: 'hkdf://H1+ctx->ed25519:7f2ac3',
    ritual: {
      intent_sha256: 'b7b10000000000000000000000000000000000000000000000000000000000e9',
      tongue_quorum: {
        k: 4,
        n: 6,
        phi_weights: [0.618, 0.382, 0.618, 0.382, 0.618, 0.382],
      },
      geoseal: {
        scheme: 'GeoSeal@v2',
        region: 'Poincare-B(0.42,0.17)',
        proof: 'zkp:abc123',
      },
      timebox: {
        t0: new Date(Date.now() - 60_000).toISOString(), // 1 min ago
        delta_s: 900, // 15 min window
      },
    },
    anchors: {
      H0_envelope: 'sha3-256:ab12ef',
      H1_merkle_root: 'sha3-256:77aa19',
      pq_sigs: [
        { alg: 'ML-DSA-65', signer: 'tongue:KO', sig: 'uZk...' },
        { alg: 'Falcon-1024', signer: 'tongue:AV', sig: 'pQ5...' },
      ],
      h2_external: {
        sigstore_bundle: 'base64:abc',
        sbom_digest: 'sha256:deadbeef',
      },
    },
    gates: {
      syntax: 'pass',
      integrity: 'pass',
      quorum: { pass: true, k: 4, weighted_phi: 1.0 },
      geo_time: 'pass',
      policy: { decision: 'allow', risk: 0.07 },
    },
    hatch: {
      boot_epoch: 0,
      kdf: 'HKDF-SHA3',
      boot_key_fp: 'fp:01c9aa',
      attestation_A0: 'cose-sign1:abc123',
    },
    signature: {
      alg: 'COSI-threshold-PQ',
      signers: ['KO', 'AV', 'RU', 'CA'],
      sig: 'AAECAwQF',
    },
    ...overrides,
  };
}

describe('EggAttestValidator', () => {
  it('accepts a valid canonical packet', () => {
    const result = validateEggAttest(makeValidPacket());
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it('rejects unknown spec version', () => {
    const pkt = makeValidPacket({ spec: 'SCBE/egg@v99' as any });
    const result = validateEggAttest(pkt);
    expect(result.valid).toBe(false);
    expect(result.errors[0].path).toBe('spec');
  });

  it('rejects agent_id without hkdf:// prefix', () => {
    const pkt = makeValidPacket({ agent_id: 'ed25519:abc' });
    const result = validateEggAttest(pkt);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.path === 'agent_id')).toBe(true);
  });

  it('rejects k > n in tongue quorum', () => {
    const pkt = makeValidPacket();
    pkt.ritual.tongue_quorum.k = 7;
    pkt.ritual.tongue_quorum.n = 6;
    // Also fix gate quorum k to match
    pkt.gates.quorum.k = 7;
    const result = validateEggAttest(pkt);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.path === 'ritual.tongue_quorum')).toBe(true);
  });

  it('rejects mismatched phi_weights length', () => {
    const pkt = makeValidPacket();
    pkt.ritual.tongue_quorum.phi_weights = [0.5, 0.5]; // n=6, only 2 weights
    const result = validateEggAttest(pkt);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.path === 'ritual.tongue_quorum.phi_weights')).toBe(true);
  });

  it('rejects expired timebox', () => {
    const pkt = makeValidPacket();
    pkt.ritual.timebox.t0 = '2020-01-01T00:00:00Z';
    pkt.ritual.timebox.delta_s = 60;
    const result = validateEggAttest(pkt);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.path === 'ritual.timebox')).toBe(true);
  });

  it('allows non-expired timebox with explicit now', () => {
    const pkt = makeValidPacket();
    pkt.ritual.timebox.t0 = '2026-03-23T12:00:00Z';
    pkt.ritual.timebox.delta_s = 900;
    // Set "now" to 5 min after t0
    const refTime = new Date('2026-03-23T12:05:00Z').getTime();
    const result = validateEggAttest(pkt, refTime);
    expect(result.errors.filter((e) => e.path === 'ritual.timebox')).toHaveLength(0);
  });

  it('rejects duplicate PQ signers', () => {
    const pkt = makeValidPacket();
    pkt.anchors.pq_sigs = [
      { alg: 'ML-DSA-65', signer: 'tongue:KO', sig: 'a' },
      { alg: 'Falcon-1024', signer: 'tongue:KO', sig: 'b' },
    ];
    const result = validateEggAttest(pkt);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.path === 'anchors.pq_sigs')).toBe(true);
  });

  it('rejects allow decision when gates failed', () => {
    const pkt = makeValidPacket();
    pkt.gates.integrity = 'fail';
    // policy still says allow — inconsistent
    const result = validateEggAttest(pkt);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.path === 'gates')).toBe(true);
  });

  it('rejects risk outside [0,1]', () => {
    const pkt = makeValidPacket();
    pkt.gates.policy.risk = 1.5;
    const result = validateEggAttest(pkt);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.path === 'gates.policy.risk')).toBe(true);
  });

  it('rejects gate quorum k mismatch with ritual k', () => {
    const pkt = makeValidPacket();
    pkt.gates.quorum.k = 3; // ritual says k=4
    const result = validateEggAttest(pkt);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.path === 'gates.quorum.k')).toBe(true);
  });

  it('rejects invalid boot_key_fp prefix', () => {
    const pkt = makeValidPacket();
    pkt.hatch.boot_key_fp = 'key:abc';
    const result = validateEggAttest(pkt);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.path === 'hatch.boot_key_fp')).toBe(true);
  });
});

describe('allGatesPassed', () => {
  it('returns true when all gates pass with allow', () => {
    const gates: GateResults = {
      syntax: 'pass',
      integrity: 'pass',
      quorum: { pass: true, k: 4, weighted_phi: 1.0 },
      geo_time: 'pass',
      policy: { decision: 'allow', risk: 0.05 },
    };
    expect(allGatesPassed(gates)).toBe(true);
  });

  it('returns false when policy is quarantine', () => {
    const gates: GateResults = {
      syntax: 'pass',
      integrity: 'pass',
      quorum: { pass: true, k: 4, weighted_phi: 1.0 },
      geo_time: 'pass',
      policy: { decision: 'quarantine', risk: 0.4 },
    };
    expect(allGatesPassed(gates)).toBe(false);
  });

  it('returns false when any gate fails', () => {
    const gates: GateResults = {
      syntax: 'pass',
      integrity: 'fail',
      quorum: { pass: true, k: 4, weighted_phi: 1.0 },
      geo_time: 'pass',
      policy: { decision: 'allow', risk: 0.01 },
    };
    expect(allGatesPassed(gates)).toBe(false);
  });
});
