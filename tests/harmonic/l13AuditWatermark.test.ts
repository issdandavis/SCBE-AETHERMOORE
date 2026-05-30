/**
 * @file l13AuditWatermark.test.ts
 * @module harmonic/l13-audit-watermark
 * @layer Layer 13
 *
 * Regression tests for the AuditLedger O(1) integrity watermark fix.
 * Before this fix, DECIDE() called ledger.verify() (O(n) ML-DSA-65 verifies)
 * on every call. At 100 entries that cost ~221ms; the target is p99 < 100ms.
 *
 * Design: events appended by DECIDE() are integrity-guaranteed by construction
 * (we hold the signing key). The watermark starts true and stays true across
 * normal appends. verifyAndSetWatermark() is for the restore-from-storage path.
 */

import { describe, it, expect } from 'vitest';
import {
  PQCrypto,
  AuditLedger,
  DECIDE,
  computeLawsHash,
  buildManifest,
  type ImmutableLaws,
  type FluxManifest,
  type LocalKeySet,
  type OfflineRuntime,
  type EnforcementRequest,
} from '../../src/governance/offline_mode.js';

// ─── helpers ─────────────────────────────────────────────────────────────────

function makeRuntime(ledgerSeedEntries = 0): OfflineRuntime {
  const sk = PQCrypto.generateSigningKeys();
  const kem = PQCrypto.generateKEMKeys();
  const enc = new TextEncoder();

  const lawsBase = {
    metric_signature: 'H14',
    tongues_set: ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'],
    geometry_model: 'poincare_ball',
    layer_behaviors: {},
  } as const;
  const laws: ImmutableLaws = {
    ...lawsBase,
    laws_hash: computeLawsHash(lawsBase),
  };

  const manifest: FluxManifest = buildManifest(
    {
      manifest_id: 'm1',
      epoch_id: 'e1',
      valid_from: 0n,
      valid_until: BigInt(Date.now() * 1_000_000) + 3_600_000_000_000n,
      policy_weights: {},
      thresholds: {},
      curvature_params: {},
      required_keys: [PQCrypto.fingerprint(sk.publicKey)],
    },
    sk.secretKey
  );

  const keys: LocalKeySet = {
    signing_secret: sk.secretKey,
    signing_public: sk.publicKey,
    kem_secret: kem.secretKey,
    kem_public: kem.publicKey,
    fingerprints: [PQCrypto.fingerprint(sk.publicKey)],
  };

  const ledger = new AuditLedger(sk.secretKey);
  for (let i = 0; i < ledgerSeedEntries; i++) {
    ledger.append(enc.encode(`seed_event_${i}`));
  }

  return {
    laws,
    manifest,
    keys,
    ledger,
    voxelRoot: PQCrypto.hash(enc.encode('voxel')),
    nowMono: BigInt(Date.now() * 1_000_000),
    signerPubKey: sk.publicKey,
    computeMMX: () => ({ mm_coherence: 0.9, mm_conflict: 0.1, mm_drift: 0.05, wall_cost: 0.3 }),
  };
}

const TEST_REQUEST: EnforcementRequest = {
  action: 'cmd.run',
  subject: 'user',
  object: 'file',
  payload_hash: PQCrypto.hash(new TextEncoder().encode('payload')),
};

// ─── watermark unit tests ─────────────────────────────────────────────────────

describe('AuditLedger.isIntact watermark', () => {
  it('starts true on empty ledger', () => {
    const sk = PQCrypto.generateSigningKeys();
    const ledger = new AuditLedger(sk.secretKey);
    expect(ledger.isIntact).toBe(true);
  });

  it('stays true after multiple appends (we hold the key)', () => {
    const sk = PQCrypto.generateSigningKeys();
    const ledger = new AuditLedger(sk.secretKey);
    const enc = new TextEncoder();
    for (let i = 0; i < 50; i++) {
      ledger.append(enc.encode(`event_${i}`));
      expect(ledger.isIntact).toBe(true);
    }
  });

  it('verify() still does full O(n) chain verification', () => {
    const sk = PQCrypto.generateSigningKeys();
    const ledger = new AuditLedger(sk.secretKey);
    const enc = new TextEncoder();
    for (let i = 0; i < 10; i++) ledger.append(enc.encode(`event_${i}`));
    expect(ledger.verify(sk.publicKey)).toBe(true);
  });

  it('verifyAndSetWatermark() sets watermark based on full verification', () => {
    const sk = PQCrypto.generateSigningKeys();
    const sk2 = PQCrypto.generateSigningKeys();
    const ledger = new AuditLedger(sk.secretKey);
    const enc = new TextEncoder();
    for (let i = 0; i < 5; i++) ledger.append(enc.encode(`event_${i}`));

    // Verifying with correct key → true
    expect(ledger.verifyAndSetWatermark(sk.publicKey)).toBe(true);
    expect(ledger.isIntact).toBe(true);

    // Verifying with wrong key → false, watermark updates
    expect(ledger.verifyAndSetWatermark(sk2.publicKey)).toBe(false);
    expect(ledger.isIntact).toBe(false);
  });
});

// ─── DECIDE() latency regression ─────────────────────────────────────────────

describe('DECIDE() p99 latency with large ledger', () => {
  it(
    'p99 < 100ms with 150-entry ledger across 100 calls',
    { timeout: 30_000 },
    () => {
      const rt = makeRuntime(150);
      const latencies: number[] = [];

      for (let i = 0; i < 100; i++) {
        rt.nowMono = BigInt(Date.now() * 1_000_000);
        const t0 = performance.now();
        DECIDE(TEST_REQUEST, rt);
        latencies.push(performance.now() - t0);
      }

      latencies.sort((a, b) => a - b);
      const p99 = latencies[Math.floor(latencies.length * 0.99)]!;
      const p95 = latencies[Math.floor(latencies.length * 0.95)]!;

      expect(p99).toBeLessThan(100);
      expect(p95).toBeLessThan(75);
    },
  );

  it('DECIDE() returns ALLOW for clean request', () => {
    const rt = makeRuntime(0);
    rt.nowMono = BigInt(Date.now() * 1_000_000);
    const result = DECIDE(TEST_REQUEST, rt);
    expect(result.decision).toBe('ALLOW');
    expect(result.reason_codes).toHaveLength(0);
  });

  it('ledger grows correctly — each DECIDE appends one event', () => {
    const rt = makeRuntime(0);
    for (let i = 0; i < 10; i++) {
      rt.nowMono = BigInt(Date.now() * 1_000_000);
      DECIDE(TEST_REQUEST, rt);
    }
    expect(rt.ledger.length).toBe(10);
    expect(rt.ledger.isIntact).toBe(true);
  });

  it('audit chain passes full verify after 100 DECIDE calls', () => {
    const rt = makeRuntime(0);
    for (let i = 0; i < 100; i++) {
      rt.nowMono = BigInt(Date.now() * 1_000_000);
      DECIDE(TEST_REQUEST, rt);
    }
    // The full O(n) verify should still pass — chain is correct by construction
    expect(rt.ledger.verify(rt.keys.signing_public)).toBe(true);
  });
});
