/**
 * @file offline_mode.test.ts
 * @module governance/offline_mode
 * @layer L13 Governance
 *
 * Tests for the offline governance decision engine:
 * - Trust state machine (§1)
 * - Policy thresholds (§2)
 * - Fail-closed gate (§3)
 * - Manifest staleness (§4)
 * - PQCrypto key generation (§5)
 * - AuditLedger hash chain (§6)
 * - DECIDE integration (§7)
 *
 * NOTE: §6-§7 use fresh PQCrypto.generateSigningKeys() per test.
 * @noble/post-quantum performs strict Uint8Array realm checks, so
 * keys must be generated and consumed within the same module scope.
 */

import { describe, it, expect } from 'vitest';
import { sha512 } from '@noble/hashes/sha2.js';
import { ml_dsa65 } from '@noble/post-quantum/ml-dsa.js';
import {
  evaluateTrustState,
  getThresholdsForState,
  failClosedGate,
  isManifestStale,
  AuditLedger,
  PQCrypto,
  DECIDE,
  Decision,
  TrustState,
  resolveManifestConflict,
  verifyManifest,
  type TrustContext,
  type FailClosedCheck,
  type FluxManifest,
  type ImmutableLaws,
  type EnforcementRequest,
  type OfflineRuntime,
  type LocalKeySet,
  type EnforcementContext,
  type GovernanceScalars,
} from '../../src/governance/offline_mode.js';

// ─── Helpers ───────────────────────────────────────────────────

function allTrusted(): TrustContext {
  return {
    keys_valid: true,
    time_trusted: true,
    manifest_current: true,
    key_rotation_needed: false,
    integrity_ok: true,
  };
}

function allPassCheck(): FailClosedCheck {
  return {
    laws_present: true,
    laws_hash_valid: true,
    manifest_present: true,
    manifest_sig_ok: true,
    keys_present: true,
    audit_intact: true,
    voxel_root_ok: true,
  };
}

function canonicalStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map((v) => canonicalStringify(v)).join(',')}]`;
  const record = value as Record<string, unknown>;
  const keys = Object.keys(record).sort();
  const body = keys.map((k) => `${JSON.stringify(k)}:${canonicalStringify(record[k])}`).join(',');
  return `{${body}}`;
}

// ─── §1 Trust State Machine ─────────────────────────────────

describe('evaluateTrustState', () => {
  it('returns T0_Trusted when all checks pass', () => {
    expect(evaluateTrustState(allTrusted())).toBe(TrustState.T0_Trusted);
  });

  it('returns T1_TimeUntrusted when time is not trusted', () => {
    expect(evaluateTrustState({ ...allTrusted(), time_trusted: false })).toBe(
      TrustState.T1_TimeUntrusted
    );
  });

  it('returns T2_ManifestStale when manifest is not current', () => {
    expect(evaluateTrustState({ ...allTrusted(), manifest_current: false })).toBe(
      TrustState.T2_ManifestStale
    );
  });

  it('returns T3_KeyRolloverReq when key rotation needed', () => {
    expect(evaluateTrustState({ ...allTrusted(), key_rotation_needed: true })).toBe(
      TrustState.T3_KeyRolloverReq
    );
  });

  it('returns T4_IntegrityDegraded when integrity fails', () => {
    expect(evaluateTrustState({ ...allTrusted(), integrity_ok: false })).toBe(
      TrustState.T4_IntegrityDegraded
    );
  });

  it('T4 takes priority over T3', () => {
    expect(
      evaluateTrustState({ ...allTrusted(), integrity_ok: false, key_rotation_needed: true })
    ).toBe(TrustState.T4_IntegrityDegraded);
  });

  it('T3 takes priority over T2', () => {
    expect(
      evaluateTrustState({ ...allTrusted(), key_rotation_needed: true, manifest_current: false })
    ).toBe(TrustState.T3_KeyRolloverReq);
  });

  it('T2 takes priority over T1', () => {
    expect(
      evaluateTrustState({ ...allTrusted(), manifest_current: false, time_trusted: false })
    ).toBe(TrustState.T2_ManifestStale);
  });
});

// ─── §2 Policy Thresholds ───────────────────────────────────

describe('getThresholdsForState', () => {
  it('returns base thresholds for T0_Trusted', () => {
    const t = getThresholdsForState(TrustState.T0_Trusted);
    expect(t.coherence_min).toBeCloseTo(0.6);
    expect(t.conflict_max).toBeCloseTo(0.3);
    expect(t.drift_max).toBeCloseTo(0.2);
    expect(t.wall_cost_max).toBeCloseTo(0.8);
  });

  it('tightens thresholds for T1_TimeUntrusted (STRICT_FACTOR=1.25)', () => {
    const t = getThresholdsForState(TrustState.T1_TimeUntrusted);
    expect(t.coherence_min).toBeCloseTo(0.75);
    expect(t.conflict_max).toBeCloseTo(0.24);
    expect(t.drift_max).toBeCloseTo(0.16);
    expect(t.wall_cost_max).toBeCloseTo(0.64);
  });

  it('tightens thresholds further for T2_ManifestStale (STALE_FACTOR=1.5)', () => {
    const t = getThresholdsForState(TrustState.T2_ManifestStale);
    expect(t.coherence_min).toBeCloseTo(0.9);
    expect(t.conflict_max).toBeCloseTo(0.2);
    expect(t.drift_max).toBeCloseTo(0.133);
    expect(t.wall_cost_max).toBeCloseTo(0.533);
  });

  it('near-zero thresholds for T3_KeyRolloverReq', () => {
    const t = getThresholdsForState(TrustState.T3_KeyRolloverReq);
    expect(t.coherence_min).toBe(0.99);
    expect(t.conflict_max).toBe(0.01);
    expect(t.drift_max).toBe(0.01);
    expect(t.wall_cost_max).toBe(0.05);
  });

  it('impossible thresholds for T4_IntegrityDegraded (always DENY)', () => {
    const t = getThresholdsForState(TrustState.T4_IntegrityDegraded);
    expect(t.coherence_min).toBe(Number.POSITIVE_INFINITY);
    expect(t.conflict_max).toBe(0);
    expect(t.drift_max).toBe(0);
    expect(t.wall_cost_max).toBe(0);
  });

  it('uses manifest thresholds when provided', () => {
    const manifest = {
      thresholds: { coherence_min: 0.8, conflict_max: 0.1, drift_max: 0.05, wall_cost_max: 0.5 },
    } as unknown as FluxManifest;
    const t = getThresholdsForState(TrustState.T0_Trusted, manifest);
    expect(t.coherence_min).toBe(0.8);
    expect(t.conflict_max).toBe(0.1);
  });

  it('falls back to base when manifest threshold missing', () => {
    const manifest = { thresholds: {} } as unknown as FluxManifest;
    const t = getThresholdsForState(TrustState.T0_Trusted, manifest);
    expect(t.coherence_min).toBeCloseTo(0.6);
    expect(t.conflict_max).toBeCloseTo(0.3);
  });
});

// ─── §3 Fail-Closed Gate ────────────────────────────────────

describe('failClosedGate', () => {
  it('passes when all checks OK', () => {
    expect(failClosedGate(allPassCheck(), 'any.action')).toEqual({ pass: true });
  });

  it('blocks when laws missing', () => {
    const r = failClosedGate({ ...allPassCheck(), laws_present: false }, 'data.write');
    expect(r.pass).toBe(false);
    expect(r.reason).toBe('LAWS_MISSING_OR_CORRUPT');
  });

  it('blocks when laws hash invalid', () => {
    const r = failClosedGate({ ...allPassCheck(), laws_hash_valid: false }, 'data.write');
    expect(r.pass).toBe(false);
    expect(r.reason).toBe('LAWS_MISSING_OR_CORRUPT');
  });

  it('blocks when manifest not present', () => {
    const r = failClosedGate({ ...allPassCheck(), manifest_present: false }, 'data.write');
    expect(r.pass).toBe(false);
    expect(r.reason).toBe('MANIFEST_INVALID');
  });

  it('blocks when manifest signature invalid', () => {
    const r = failClosedGate({ ...allPassCheck(), manifest_sig_ok: false }, 'data.write');
    expect(r.pass).toBe(false);
    expect(r.reason).toBe('MANIFEST_INVALID');
  });

  it('blocks when keys missing', () => {
    const r = failClosedGate({ ...allPassCheck(), keys_present: false }, 'data.write');
    expect(r.pass).toBe(false);
    expect(r.reason).toBe('KEYS_MISSING');
  });

  it('blocks when audit corrupted', () => {
    const r = failClosedGate({ ...allPassCheck(), audit_intact: false }, 'data.write');
    expect(r.pass).toBe(false);
    expect(r.reason).toBe('AUDIT_CORRUPTED');
  });

  it('blocks when voxel root mismatched', () => {
    const r = failClosedGate({ ...allPassCheck(), voxel_root_ok: false }, 'data.write');
    expect(r.pass).toBe(false);
    expect(r.reason).toBe('VOXEL_ROOT_MISMATCH');
  });

  it('allows safe ops even when integrity compromised', () => {
    for (const op of ['config.read', 'audit.export', 'diagnostics.run']) {
      const r = failClosedGate({ ...allPassCheck(), laws_present: false }, op);
      expect(r.pass).toBe(true);
      expect(r.reason).toBe('LAWS_MISSING_OR_CORRUPT');
    }
  });

  it('blocks unsafe ops when any check fails', () => {
    const r = failClosedGate({ ...allPassCheck(), laws_present: false }, 'data.delete');
    expect(r.pass).toBe(false);
  });

  it('checks are evaluated in priority order (laws > manifest > keys > audit > voxel)', () => {
    // With multiple failures, the first check's reason wins
    const r = failClosedGate(
      { ...allPassCheck(), laws_present: false, keys_present: false },
      'data.write'
    );
    expect(r.reason).toBe('LAWS_MISSING_OR_CORRUPT');
  });
});

// ─── §4 Manifest Staleness ─────────────────────────────────

describe('isManifestStale', () => {
  it('returns false when nowMonotonic is before valid_until', () => {
    expect(isManifestStale({ valid_until: 2000n } as FluxManifest, 1000n)).toBe(false);
  });

  it('returns false when nowMonotonic equals valid_until', () => {
    expect(isManifestStale({ valid_until: 1000n } as FluxManifest, 1000n)).toBe(false);
  });

  it('returns true when nowMonotonic exceeds valid_until', () => {
    expect(isManifestStale({ valid_until: 1000n } as FluxManifest, 1001n)).toBe(true);
  });
});

// ─── §5 PQCrypto Key Generation ─────────────────────────────

describe('PQCrypto', () => {
  it('generateSigningKeys returns correct-size ML-DSA-65 keys', () => {
    const keys = PQCrypto.generateSigningKeys();
    expect(keys.secretKey.length).toBe(4032);
    expect(keys.publicKey.length).toBe(1952);
  });

  it('generateKEMKeys returns correct-size ML-KEM-768 keys', () => {
    const keys = PQCrypto.generateKEMKeys();
    expect(keys.secretKey.length).toBe(2400);
    expect(keys.publicKey.length).toBe(1184);
  });

  it('hash produces 64-byte SHA-512 digest', () => {
    const h = PQCrypto.hash(new Uint8Array([1, 2, 3]));
    expect(h.length).toBe(64);
  });

  it('hash is deterministic', () => {
    const data = new TextEncoder().encode('test');
    const a = PQCrypto.hash(data);
    const b = PQCrypto.hash(data);
    expect(Buffer.from(a).toString('hex')).toBe(Buffer.from(b).toString('hex'));
  });

  it('fingerprint produces colon-separated hex from first 16 bytes', () => {
    const keys = PQCrypto.generateSigningKeys();
    const fp = PQCrypto.fingerprint(keys.publicKey);
    expect(fp).toMatch(/^[0-9a-f]{2}(:[0-9a-f]{2}){15}$/);
  });

  it('fingerprint is deterministic for same key', () => {
    const keys = PQCrypto.generateSigningKeys();
    const a = PQCrypto.fingerprint(keys.publicKey);
    const b = PQCrypto.fingerprint(keys.publicKey);
    expect(a).toBe(b);
  });

  it('different keys produce different fingerprints', () => {
    const k1 = PQCrypto.generateSigningKeys();
    const k2 = PQCrypto.generateSigningKeys();
    expect(PQCrypto.fingerprint(k1.publicKey)).not.toBe(PQCrypto.fingerprint(k2.publicKey));
  });
});

// ─── §6 AuditLedger Structure ──────────────────────────────
// NOTE: AuditLedger.append/verify require PQCrypto.sign() which hits
// the vitest Uint8Array realm boundary issue with @noble/post-quantum.
// We test the structure and behavior that doesn't require signing.

describe('AuditLedger', () => {
  it('starts with length 0 and 64-byte zero root', () => {
    // Constructor only stores the key, doesn't sign anything yet
    const fakeKey = new Uint8Array(4032); // Correct size for ML-DSA-65
    const ledger = new AuditLedger(fakeKey);
    expect(ledger.length).toBe(0);
    expect(ledger.root.length).toBe(64);
    expect(ledger.root.every((b) => b === 0)).toBe(true);
  });

  it('getEvents returns empty array for new ledger', () => {
    const fakeKey = new Uint8Array(4032);
    const ledger = new AuditLedger(fakeKey);
    expect(ledger.getEvents()).toHaveLength(0);
  });

  it('eventsSince(0) returns empty for new ledger', () => {
    const fakeKey = new Uint8Array(4032);
    const ledger = new AuditLedger(fakeKey);
    expect(ledger.eventsSince(0)).toHaveLength(0);
  });

  it('verify returns true for empty chain regardless of public key', () => {
    const fakeKey = new Uint8Array(4032);
    const ledger = new AuditLedger(fakeKey);
    // Empty chain always verifies
    expect(ledger.verify(new Uint8Array(1952))).toBe(true);
  });
});

// ─── §7 Decision Enumerations ───────────────────────────────

describe('Decision enum', () => {
  it('has all four decision types', () => {
    expect(Decision.ALLOW).toBe('ALLOW');
    expect(Decision.DENY).toBe('DENY');
    expect(Decision.QUARANTINE).toBe('QUARANTINE');
    expect(Decision.DEFER).toBe('DEFER');
  });
});

describe('TrustState enum', () => {
  it('has all five trust states with correct codes', () => {
    expect(TrustState.T0_Trusted).toBe('T0');
    expect(TrustState.T1_TimeUntrusted).toBe('T1');
    expect(TrustState.T2_ManifestStale).toBe('T2');
    expect(TrustState.T3_KeyRolloverReq).toBe('T3');
    expect(TrustState.T4_IntegrityDegraded).toBe('T4');
  });
});

// ─── §8 resolveManifestConflict ──────────────────────────────
// NOTE: PQCrypto.sign/verify hit vitest Uint8Array realm boundary with
// @noble/post-quantum. We use Uint8Array.from() to re-wrap keys into the
// test module's realm so that the library's instanceof checks pass.

/**
 * Generate keys and sign directly using the test module's ml_dsa65 import.
 * This avoids the vitest Uint8Array realm boundary issue that occurs when
 * keys generated through one module instance are passed to sign/verify
 * in another module instance.
 */
function testKeygen() {
  return ml_dsa65.keygen();
}
function testSign(secretKey: Uint8Array, message: Uint8Array): Uint8Array {
  return ml_dsa65.sign(message, secretKey);
}

describe('resolveManifestConflict', () => {
  function makeManifest(
    epochId: string,
    keys: { secretKey: Uint8Array; publicKey: Uint8Array }
  ): FluxManifest {
    const m: Omit<FluxManifest, 'signature'> = {
      manifest_id: `m-${epochId}`,
      epoch_id: epochId,
      valid_from: 0n,
      valid_until: 999999999n,
      policy_weights: {},
      thresholds: {},
      curvature_params: {},
      required_keys: [],
    };
    const canonical = canonicalStringify({
      manifest_id: m.manifest_id,
      epoch_id: m.epoch_id,
      valid_from: m.valid_from.toString(),
      valid_until: m.valid_until.toString(),
      policy_weights: m.policy_weights,
      thresholds: m.thresholds,
      curvature_params: m.curvature_params,
      required_keys: m.required_keys,
    });
    const payload = new TextEncoder().encode(canonical);
    const signature = testSign(keys.secretKey, payload);
    return { ...m, signature };
  }

  it('returns a when only a is valid', () => {
    const keys = testKeygen();
    const a = makeManifest('1', keys);
    const b = makeManifest('2', keys);
    b.signature = new Uint8Array(b.signature.length);
    expect(resolveManifestConflict(a, b, keys.publicKey)).toBe(a);
  });

  it('returns b when only b is valid', () => {
    const keys = testKeygen();
    const a = makeManifest('1', keys);
    const b = makeManifest('2', keys);
    a.signature = new Uint8Array(a.signature.length);
    expect(resolveManifestConflict(a, b, keys.publicKey)).toBe(b);
  });

  it('throws BOTH_MANIFESTS_INVALID when neither is valid', () => {
    const keys = testKeygen();
    const a = makeManifest('1', keys);
    const b = makeManifest('2', keys);
    a.signature = new Uint8Array(a.signature.length);
    b.signature = new Uint8Array(b.signature.length);
    expect(() => resolveManifestConflict(a, b, keys.publicKey)).toThrow('BOTH_MANIFESTS_INVALID');
  });

  it('returns manifest with higher epoch when both valid', () => {
    const keys = testKeygen();
    const a = makeManifest('100', keys);
    const b = makeManifest('200', keys);
    expect(resolveManifestConflict(a, b, keys.publicKey)).toBe(b);
    expect(resolveManifestConflict(b, a, keys.publicKey)).toBe(b);
  });

  it('returns a when epochs are equal (>= comparison)', () => {
    const keys = testKeygen();
    const a = makeManifest('100', keys);
    const b = makeManifest('100', keys);
    expect(resolveManifestConflict(a, b, keys.publicKey)).toBe(a);
  });
});

// ─── §9 verifyManifest ───────────────────────────────────────

describe('verifyManifest', () => {
  it('returns true for correctly signed manifest', () => {
    const keys = testKeygen();
    const m: Omit<FluxManifest, 'signature'> = {
      manifest_id: 'test-m',
      epoch_id: '1',
      valid_from: 0n,
      valid_until: 999n,
      policy_weights: {},
      thresholds: {},
      curvature_params: {},
      required_keys: [],
    };
    const canonical = canonicalStringify({
      manifest_id: m.manifest_id,
      epoch_id: m.epoch_id,
      valid_from: m.valid_from.toString(),
      valid_until: m.valid_until.toString(),
      policy_weights: m.policy_weights,
      thresholds: m.thresholds,
      curvature_params: m.curvature_params,
      required_keys: m.required_keys,
    });
    const payload = new TextEncoder().encode(canonical);
    const signature = testSign(keys.secretKey, payload);
    expect(verifyManifest({ ...m, signature }, keys.publicKey)).toBe(true);
  });

  it('returns false for tampered signature', () => {
    const keys = testKeygen();
    const manifest: FluxManifest = {
      manifest_id: 'test-m',
      epoch_id: '1',
      valid_from: 0n,
      valid_until: 999n,
      policy_weights: {},
      thresholds: {},
      curvature_params: {},
      required_keys: [],
      signature: new Uint8Array(4627),
    };
    expect(verifyManifest(manifest, keys.publicKey)).toBe(false);
  });
});

// ─── §10 DECIDE Integration ─────────────────────────────────

describe('DECIDE', () => {
  function buildRuntime(
    overrides: {
      mmx?: Partial<Omit<GovernanceScalars, 'trust_level'>>;
      manifestStale?: boolean;
    } = {}
  ): OfflineRuntime {
    const sigKeys = testKeygen();
    const kemKeys = PQCrypto.generateKEMKeys();

    const laws: ImmutableLaws = {
      metric_signature: 'harmonic_v3',
      tongues_set: ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'],
      geometry_model: 'poincare_ball',
      layer_behaviors: { 12: 'harmonic_scale' },
      laws_hash: new Uint8Array(64),
    };
    const lawsCanonical = canonicalStringify({
      metric_signature: laws.metric_signature,
      tongues_set: laws.tongues_set,
      geometry_model: laws.geometry_model,
      layer_behaviors: laws.layer_behaviors,
    });
    (laws as { laws_hash: Uint8Array }).laws_hash = PQCrypto.hash(
      new TextEncoder().encode(lawsCanonical)
    );

    const manifestBase = {
      manifest_id: 'test-manifest',
      epoch_id: '1',
      valid_from: 0n,
      valid_until: overrides.manifestStale ? 0n : 999999999n,
      policy_weights: {},
      thresholds: {},
      curvature_params: {},
      required_keys: [],
    };
    const mCanonical = canonicalStringify({
      manifest_id: manifestBase.manifest_id,
      epoch_id: manifestBase.epoch_id,
      valid_from: manifestBase.valid_from.toString(),
      valid_until: manifestBase.valid_until.toString(),
      policy_weights: manifestBase.policy_weights,
      thresholds: manifestBase.thresholds,
      curvature_params: manifestBase.curvature_params,
      required_keys: manifestBase.required_keys,
    });
    const mPayload = new TextEncoder().encode(mCanonical);
    const manifest: FluxManifest = {
      ...manifestBase,
      signature: testSign(sigKeys.secretKey, mPayload),
    };

    const defaultMMX = {
      mm_coherence: 0.9,
      mm_conflict: 0.05,
      mm_drift: 0.05,
      wall_cost: 0.1,
    };

    return {
      laws,
      manifest,
      keys: {
        signing_secret: sigKeys.secretKey,
        signing_public: sigKeys.publicKey,
        kem_secret: kemKeys.secretKey,
        kem_public: kemKeys.publicKey,
        fingerprints: [PQCrypto.fingerprint(sigKeys.publicKey)],
      },
      ledger: new AuditLedger(sigKeys.secretKey),
      voxelRoot: PQCrypto.hash(new Uint8Array([1])),
      nowMono: 100n,
      signerPubKey: sigKeys.publicKey,
      computeMMX: () => ({ ...defaultMMX, ...overrides.mmx }),
    };
  }

  const request: EnforcementRequest = {
    action: 'data.write',
    subject: 'agent-1',
    object: 'resource-1',
    payload_hash: PQCrypto.hash(new Uint8Array([42])),
  };

  it('returns ALLOW when all checks pass and scalars are within thresholds', () => {
    const rt = buildRuntime();
    const result = DECIDE(request, rt);
    expect(result.decision).toBe(Decision.ALLOW);
    expect(result.reason_codes).toHaveLength(0);
    expect(result.proof).toBeDefined();
    expect(result.proof.signature).toBeInstanceOf(Uint8Array);
  });

  it('returns QUARANTINE for single threshold violation', () => {
    const rt = buildRuntime({ mmx: { mm_coherence: 0.1 } });
    const result = DECIDE(request, rt);
    expect(result.decision).toBe(Decision.QUARANTINE);
    expect(result.reason_codes).toContain('LOW_COHERENCE');
    expect(result.reason_codes).toHaveLength(1);
  });

  it('returns DENY for multiple threshold violations', () => {
    const rt = buildRuntime({ mmx: { mm_coherence: 0.1, mm_conflict: 0.9 } });
    const result = DECIDE(request, rt);
    expect(result.decision).toBe(Decision.DENY);
    expect(result.reason_codes).toContain('LOW_COHERENCE');
    expect(result.reason_codes).toContain('HIGH_CONFLICT');
  });

  it('returns DEFER when manifest is stale and scalars pass', () => {
    const rt = buildRuntime({ manifestStale: true });
    const result = DECIDE(request, rt);
    expect(result.decision).toBe(Decision.DEFER);
    expect(result.reason_codes).toContain('MANIFEST_STALE');
  });

  it('appends to audit ledger on each decision', () => {
    const rt = buildRuntime();
    expect(rt.ledger.length).toBe(0);
    DECIDE(request, rt);
    expect(rt.ledger.length).toBe(1);
    DECIDE(request, rt);
    expect(rt.ledger.length).toBe(2);
  });

  it('includes governance scalars with trust level in result', () => {
    const rt = buildRuntime();
    const result = DECIDE(request, rt);
    expect(result.governance_scalars.trust_level).toBe(TrustState.T0_Trusted);
    expect(result.governance_scalars.mm_coherence).toBe(0.9);
  });
});
