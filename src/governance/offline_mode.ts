// ─────────────────────────────────────────────────────────────────
// SCBE-AETHERMOORE — Offline Mode
// src/governance/offline_mode.ts
//
// Interfaces, trust state machine, and fail-closed policy map.
// Aligns with OFS v1.0.0 and the Law vs Flux Manifest pattern.
// ─────────────────────────────────────────────────────────────────

import { ml_dsa65 } from '@noble/post-quantum/ml-dsa.js';
import { ml_kem768 } from '@noble/post-quantum/ml-kem.js';
import { sha512 } from '@noble/hashes/sha2.js';

// ═══════════════════════════════════════════════════════════════
// §1  Enumerations
// ═══════════════════════════════════════════════════════════════

export enum OfflineMode {
  O0_Online = 'O0',
  O1_Disconnected = 'O1',
  O2_AirGapped = 'O2',
  O3_Intermittent = 'O3',
}

export enum TrustState {
  T0_Trusted = 'T0',
  T1_TimeUntrusted = 'T1',
  T2_ManifestStale = 'T2',
  T3_KeyRolloverReq = 'T3',
  T4_IntegrityDegraded = 'T4',
}

export enum Decision {
  ALLOW = 'ALLOW',
  DENY = 'DENY',
  QUARANTINE = 'QUARANTINE',
  DEFER = 'DEFER',
}

// ═══════════════════════════════════════════════════════════════
// §2  Core Interfaces
// ═══════════════════════════════════════════════════════════════

export interface ImmutableLaws {
  readonly metric_signature: string;
  readonly tongues_set: ReadonlyArray<string>;
  readonly geometry_model: string;
  readonly layer_behaviors: Readonly<Record<number, string>>;
  readonly laws_hash: Uint8Array; // SHA-512 of canonical JSON (without this field)
}

export interface FluxManifest {
  manifest_id: string;
  epoch_id: string;
  valid_from: bigint; // monotonic ns
  valid_until: bigint; // monotonic ns
  policy_weights: Record<string, number>;
  thresholds: Record<string, number>;
  curvature_params: Record<string, number>;
  required_keys: string[]; // fingerprints
  signature: Uint8Array; // ML-DSA-65
}

export interface GovernanceScalars {
  mm_coherence: number;
  mm_conflict: number;
  mm_drift: number;
  wall_cost: number;
  trust_level: TrustState;
}

export interface EnforcementRequest {
  action: string;
  subject: string;
  object: string;
  payload_hash: Uint8Array;
}

export interface EnforcementContext {
  modality_embeddings: Float64Array | null;
  last_epoch_id: string;
  laws_hash: Uint8Array;
  manifest_id: string;
  state_root: Uint8Array; // SHA-512(audit_root ‖ voxel_root)
}

export interface DecisionCapsule {
  inputs_hash: Uint8Array;
  laws_hash: Uint8Array;
  manifest_hash: Uint8Array;
  state_root: Uint8Array;
  decision: Decision;
  reason_codes: string[];
  timestamp_monotonic: bigint;
  signature: Uint8Array;
}

export interface DecisionResult {
  decision: Decision;
  reason_codes: string[];
  governance_scalars: GovernanceScalars;
  proof: DecisionCapsule;
}

export interface AuditEvent {
  event_id: string;
  prev_hash: Uint8Array;
  event_data: Uint8Array;
  event_hash: Uint8Array; // SHA-512(prev_hash ‖ event_data)
  signature: Uint8Array; // ML-DSA-65(event_hash)
}

export interface LocalKeySet {
  signing_secret: Uint8Array;
  signing_public: Uint8Array;
  kem_secret: Uint8Array;
  kem_public: Uint8Array;
  fingerprints: string[];
}

// ═══════════════════════════════════════════════════════════════
// §3  PQ Crypto Helpers
// ═══════════════════════════════════════════════════════════════

export const PQCrypto = {
  generateSigningKeys(seed?: Uint8Array) {
    const keys = seed ? ml_dsa65.keygen(seed) : ml_dsa65.keygen();
    return { publicKey: keys.publicKey, secretKey: keys.secretKey };
  },

  sign(secretKey: Uint8Array, message: Uint8Array): Uint8Array {
    return ml_dsa65.sign(secretKey, message);
  },

  verify(publicKey: Uint8Array, message: Uint8Array, signature: Uint8Array): boolean {
    return ml_dsa65.verify(publicKey, message, signature);
  },

  generateKEMKeys(seed?: Uint8Array) {
    const keys = seed ? ml_kem768.keygen(seed) : ml_kem768.keygen();
    return { publicKey: keys.publicKey, secretKey: keys.secretKey };
  },

  encapsulate(publicKey: Uint8Array) {
    return ml_kem768.encapsulate(publicKey);
  },

  decapsulate(cipherText: Uint8Array, secretKey: Uint8Array): Uint8Array {
    return ml_kem768.decapsulate(cipherText, secretKey);
  },

  hash(data: Uint8Array): Uint8Array {
    return sha512(data);
  },

  fingerprint(publicKey: Uint8Array): string {
    const h = sha512(publicKey);
    return Array.from(h.slice(0, 16))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join(':');
  },
} as const;

// ═══════════════════════════════════════════════════════════════
// §4  Trust State Machine
// ═══════════════════════════════════════════════════════════════

export interface TrustContext {
  keys_valid: boolean;
  time_trusted: boolean;
  manifest_current: boolean;
  key_rotation_needed: boolean;
  integrity_ok: boolean;
}

export function evaluateTrustState(ctx: TrustContext): TrustState {
  if (!ctx.integrity_ok) return TrustState.T4_IntegrityDegraded;
  if (ctx.key_rotation_needed) return TrustState.T3_KeyRolloverReq;
  if (!ctx.manifest_current) return TrustState.T2_ManifestStale;
  if (!ctx.time_trusted) return TrustState.T1_TimeUntrusted;
  return TrustState.T0_Trusted;
}

// ═══════════════════════════════════════════════════════════════
// §5  Fail-Closed Policy Map
// ═══════════════════════════════════════════════════════════════

export interface PolicyThresholds {
  coherence_min: number;
  conflict_max: number;
  drift_max: number;
  wall_cost_max: number;
}

const BASE_THRESHOLDS: PolicyThresholds = {
  coherence_min: 0.6,
  conflict_max: 0.3,
  drift_max: 0.2,
  wall_cost_max: 0.8,
};

const STALE_FACTOR = 1.5;
const STRICT_FACTOR = 1.25;

export function getThresholdsForState(trust: TrustState, manifest?: FluxManifest): PolicyThresholds {
  const base: PolicyThresholds = manifest
    ? {
        coherence_min: manifest.thresholds['coherence_min'] ?? BASE_THRESHOLDS.coherence_min,
        conflict_max: manifest.thresholds['conflict_max'] ?? BASE_THRESHOLDS.conflict_max,
        drift_max: manifest.thresholds['drift_max'] ?? BASE_THRESHOLDS.drift_max,
        wall_cost_max: manifest.thresholds['wall_cost_max'] ?? BASE_THRESHOLDS.wall_cost_max,
      }
    : { ...BASE_THRESHOLDS };

  switch (trust) {
    case TrustState.T0_Trusted:
      return base;
    case TrustState.T1_TimeUntrusted:
      return {
        coherence_min: Math.min(base.coherence_min * STRICT_FACTOR, 1.0),
        conflict_max: base.conflict_max / STRICT_FACTOR,
        drift_max: base.drift_max / STRICT_FACTOR,
        wall_cost_max: base.wall_cost_max / STRICT_FACTOR,
      };
    case TrustState.T2_ManifestStale:
      return {
        coherence_min: Math.min(base.coherence_min * STALE_FACTOR, 1.0),
        conflict_max: base.conflict_max / STALE_FACTOR,
        drift_max: base.drift_max / STALE_FACTOR,
        wall_cost_max: base.wall_cost_max / STALE_FACTOR,
      };
    case TrustState.T3_KeyRolloverReq:
      return {
        coherence_min: 0.99,
        conflict_max: 0.01,
        drift_max: 0.01,
        wall_cost_max: 0.05,
      };
    case TrustState.T4_IntegrityDegraded:
      return {
        coherence_min: Number.POSITIVE_INFINITY,
        conflict_max: 0,
        drift_max: 0,
        wall_cost_max: 0,
      };
  }
}

// ═══════════════════════════════════════════════════════════════
// §6  Fail-Closed Gate
// ═══════════════════════════════════════════════════════════════

export interface FailClosedCheck {
  laws_present: boolean;
  laws_hash_valid: boolean;
  manifest_present: boolean;
  manifest_sig_ok: boolean;
  keys_present: boolean;
  audit_intact: boolean;
  voxel_root_ok: boolean;
}

const SAFE_OPS = new Set(['config.read', 'audit.export', 'diagnostics.run']);

export function failClosedGate(
  check: FailClosedCheck,
  action: string,
): { pass: boolean; reason?: string } {
  if (!check.laws_present || !check.laws_hash_valid) {
    return { pass: SAFE_OPS.has(action), reason: 'LAWS_MISSING_OR_CORRUPT' };
  }
  if (!check.manifest_present || !check.manifest_sig_ok) {
    return { pass: SAFE_OPS.has(action), reason: 'MANIFEST_INVALID' };
  }
  if (!check.keys_present) {
    return { pass: SAFE_OPS.has(action), reason: 'KEYS_MISSING' };
  }
  if (!check.audit_intact) {
    return { pass: SAFE_OPS.has(action), reason: 'AUDIT_CORRUPTED' };
  }
  if (!check.voxel_root_ok) {
    return { pass: SAFE_OPS.has(action), reason: 'VOXEL_ROOT_MISMATCH' };
  }
  return { pass: true };
}

// ═══════════════════════════════════════════════════════════════
// §7  Manifest Verification & Staleness
// ═══════════════════════════════════════════════════════════════

export function verifyManifest(manifest: FluxManifest, signerPublicKey: Uint8Array): boolean {
  const payload = canonicalManifestBytes(manifest);
  return PQCrypto.verify(signerPublicKey, payload, manifest.signature);
}

export function isManifestStale(manifest: FluxManifest, nowMonotonic: bigint): boolean {
  return nowMonotonic > manifest.valid_until;
}

function canonicalManifestBytes(m: FluxManifest): Uint8Array {
  const obj = {
    manifest_id: m.manifest_id,
    epoch_id: m.epoch_id,
    valid_from: m.valid_from.toString(),
    valid_until: m.valid_until.toString(),
    policy_weights: m.policy_weights,
    thresholds: m.thresholds,
    curvature_params: m.curvature_params,
    required_keys: m.required_keys,
  };
  return encodeCanonical(obj);
}

function canonicalLawsBytes(laws: ImmutableLaws): Uint8Array {
  const obj = {
    metric_signature: laws.metric_signature,
    tongues_set: laws.tongues_set,
    geometry_model: laws.geometry_model,
    layer_behaviors: laws.layer_behaviors,
  };
  return encodeCanonical(obj);
}

// ═══════════════════════════════════════════════════════════════
// §8  Audit Ledger (Hash Chain)
// ═══════════════════════════════════════════════════════════════

export class AuditLedger {
  private chain: AuditEvent[] = [];
  private head_hash: Uint8Array = new Uint8Array(64);

  constructor(private signingKey: Uint8Array) {}

  get root(): Uint8Array {
    return this.head_hash;
  }

  get length(): number {
    return this.chain.length;
  }

  append(eventData: Uint8Array): AuditEvent {
    const prev = this.head_hash;
    const combined = concatBytes(prev, eventData);
    const event_hash = PQCrypto.hash(combined);
    const signature = PQCrypto.sign(this.signingKey, event_hash);

    const event: AuditEvent = {
      event_id: `evt_${this.chain.length}`,
      prev_hash: prev,
      event_data: eventData,
      event_hash,
      signature,
    };

    this.chain.push(event);
    this.head_hash = event_hash;
    return event;
  }

  verify(signerPublicKey: Uint8Array): boolean {
    let expected_prev = new Uint8Array(64);
    for (const evt of this.chain) {
      const recomputed = PQCrypto.hash(concatBytes(expected_prev, evt.event_data));
      if (!bytesEqual(recomputed, evt.event_hash)) return false;
      if (!PQCrypto.verify(signerPublicKey, evt.event_hash, evt.signature)) return false;
      expected_prev = evt.event_hash;
    }
    return true;
  }

  getEvents(): ReadonlyArray<AuditEvent> {
    return this.chain;
  }

  eventsSince(index: number): AuditEvent[] {
    return this.chain.slice(index);
  }
}

// ═══════════════════════════════════════════════════════════════
// §9  Decision Capsule Builder
// ═══════════════════════════════════════════════════════════════

export function buildCapsule(
  request: EnforcementRequest,
  context: EnforcementContext,
  manifest: FluxManifest,
  decision: Decision,
  reasons: string[],
  signingKey: Uint8Array,
  nowMono: bigint,
): DecisionCapsule {
  const payload = {
    request: {
      action: request.action,
      subject: request.subject,
      object: request.object,
      payload_hash: toHex(request.payload_hash),
    },
    context: {
      last_epoch_id: context.last_epoch_id,
      laws_hash: toHex(context.laws_hash),
      manifest_id: context.manifest_id,
      state_root: toHex(context.state_root),
      modality_embeddings: context.modality_embeddings
        ? Array.from(context.modality_embeddings)
        : null,
    },
  };
  const inputs_hash = PQCrypto.hash(encodeCanonical(payload));
  const manifest_hash = PQCrypto.hash(canonicalManifestBytes(manifest));

  const capsuleSigPayload = encodeCanonical({
    inputs_hash: toHex(inputs_hash),
    laws_hash: toHex(context.laws_hash),
    manifest_hash: toHex(manifest_hash),
    state_root: toHex(context.state_root),
    decision,
    reason_codes: reasons,
    timestamp_monotonic: nowMono.toString(),
  });
  const signature = PQCrypto.sign(signingKey, PQCrypto.hash(capsuleSigPayload));

  return {
    inputs_hash,
    laws_hash: context.laws_hash,
    manifest_hash,
    state_root: context.state_root,
    decision,
    reason_codes: reasons,
    timestamp_monotonic: nowMono,
    signature,
  };
}

// ═══════════════════════════════════════════════════════════════
// §10  Governance DECIDE
// ═══════════════════════════════════════════════════════════════

export interface OfflineRuntime {
  laws: ImmutableLaws;
  manifest: FluxManifest;
  keys: LocalKeySet;
  ledger: AuditLedger;
  voxelRoot: Uint8Array;
  nowMono: bigint;
  signerPubKey: Uint8Array;
  computeMMX(
    request: EnforcementRequest,
    context: EnforcementContext,
  ): Omit<GovernanceScalars, 'trust_level'>;
}

export function DECIDE(request: EnforcementRequest, runtime: OfflineRuntime): DecisionResult {
  const fc: FailClosedCheck = {
    laws_present: !!runtime.laws,
    laws_hash_valid: bytesEqual(PQCrypto.hash(canonicalLawsBytes(runtime.laws)), runtime.laws.laws_hash),
    manifest_present: !!runtime.manifest,
    manifest_sig_ok: verifyManifest(runtime.manifest, runtime.signerPubKey),
    keys_present: !!runtime.keys && runtime.keys.fingerprints.length > 0,
    audit_intact:
      runtime.ledger.length === 0 || runtime.ledger.verify(runtime.keys.signing_public),
    voxel_root_ok: runtime.voxelRoot.length > 0,
  };

  const gate = failClosedGate(fc, request.action);
  if (!gate.pass) {
    const reasons = [gate.reason ?? 'FAIL_CLOSED'];
    const ctx = makeContext(runtime);
    const capsule = buildCapsule(
      request,
      ctx,
      runtime.manifest,
      Decision.DENY,
      reasons,
      runtime.keys.signing_secret,
      runtime.nowMono,
    );
    runtime.ledger.append(encodeCanonical(capsule));
    return {
      decision: Decision.DENY,
      reason_codes: reasons,
      governance_scalars: zeroScalars(TrustState.T4_IntegrityDegraded),
      proof: capsule,
    };
  }

  const ctx = makeContext(runtime);

  const trustCtx: TrustContext = {
    keys_valid: fc.keys_present,
    time_trusted: true,
    manifest_current: !isManifestStale(runtime.manifest, runtime.nowMono),
    key_rotation_needed: false,
    integrity_ok: fc.audit_intact && fc.voxel_root_ok,
  };
  const trust = evaluateTrustState(trustCtx);

  const raw = runtime.computeMMX(request, ctx);
  const scalars: GovernanceScalars = { ...raw, trust_level: trust };

  const thresholds = getThresholdsForState(trust, runtime.manifest);
  const reasons: string[] = [];

  if (scalars.mm_coherence < thresholds.coherence_min) reasons.push('LOW_COHERENCE');
  if (scalars.mm_conflict > thresholds.conflict_max) reasons.push('HIGH_CONFLICT');
  if (scalars.mm_drift > thresholds.drift_max) reasons.push('EXCESSIVE_DRIFT');
  if (scalars.wall_cost > thresholds.wall_cost_max) reasons.push('WALL_COST_EXCEEDED');

  let decision: Decision;
  if (trust === TrustState.T4_IntegrityDegraded) {
    decision = Decision.QUARANTINE;
    reasons.push('INTEGRITY_DEGRADED');
  } else if (trust === TrustState.T3_KeyRolloverReq && reasons.length > 0) {
    decision = Decision.DENY;
    reasons.push('KEY_ROLLOVER_REQUIRED');
  } else if (reasons.length >= 2) {
    decision = Decision.DENY;
  } else if (reasons.length === 1) {
    decision = Decision.QUARANTINE;
  } else if (trust === TrustState.T2_ManifestStale) {
    decision = Decision.DEFER;
    reasons.push('MANIFEST_STALE');
  } else {
    decision = Decision.ALLOW;
  }

  const capsule = buildCapsule(
    request,
    ctx,
    runtime.manifest,
    decision,
    reasons,
    runtime.keys.signing_secret,
    runtime.nowMono,
  );
  runtime.ledger.append(encodeCanonical(capsule));

  return {
    decision,
    reason_codes: reasons,
    governance_scalars: scalars,
    proof: capsule,
  };
}

// ═══════════════════════════════════════════════════════════════
// §11  O3 Sync Types
// ═══════════════════════════════════════════════════════════════

export interface SyncPayload {
  capsules: DecisionCapsule[];
  audit_events: AuditEvent[];
  voxel_deltas: Array<{ id: Uint8Array; data: Uint8Array }>;
  manifest_request?: { current_epoch: string };
}

export interface SyncResult {
  accepted_capsules: number;
  accepted_events: number;
  accepted_voxels: number;
  new_manifest?: FluxManifest;
}

export function resolveManifestConflict(
  a: FluxManifest,
  b: FluxManifest,
  signerPub: Uint8Array,
): FluxManifest {
  const aValid = verifyManifest(a, signerPub);
  const bValid = verifyManifest(b, signerPub);
  if (aValid && !bValid) return a;
  if (bValid && !aValid) return b;
  if (!aValid && !bValid) throw new Error('BOTH_MANIFESTS_INVALID');

  const aEpoch = parseEpochId(a.epoch_id);
  const bEpoch = parseEpochId(b.epoch_id);
  return aEpoch >= bEpoch ? a : b;
}

// ═══════════════════════════════════════════════════════════════
// §12  Utility Functions
// ═══════════════════════════════════════════════════════════════

function parseEpochId(epoch: string): bigint {
  const digits = epoch.replace(/[^0-9]/g, '');
  return digits.length > 0 ? BigInt(digits) : 0n;
}

function concatBytes(...arrays: Uint8Array[]): Uint8Array {
  const len = arrays.reduce((s, a) => s + a.length, 0);
  const out = new Uint8Array(len);
  let off = 0;
  for (const a of arrays) {
    out.set(a, off);
    off += a.length;
  }
  return out;
}

function bytesEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i]! ^ b[i]!;
  return diff === 0;
}

function toHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

function encodeCanonical(value: unknown): Uint8Array {
  return new TextEncoder().encode(canonicalStringify(value));
}

function canonicalStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((v) => canonicalStringify(v)).join(',')}]`;
  }
  const record = value as Record<string, unknown>;
  const keys = Object.keys(record).sort();
  const body = keys
    .map((k) => `${JSON.stringify(k)}:${canonicalStringify(record[k])}`)
    .join(',');
  return `{${body}}`;
}

function zeroScalars(trust: TrustState): GovernanceScalars {
  return {
    mm_coherence: 0,
    mm_conflict: 1,
    mm_drift: 1,
    wall_cost: 1,
    trust_level: trust,
  };
}

function makeContext(rt: OfflineRuntime): EnforcementContext {
  return {
    modality_embeddings: null,
    last_epoch_id: rt.manifest.epoch_id,
    laws_hash: rt.laws.laws_hash,
    manifest_id: rt.manifest.manifest_id,
    state_root: PQCrypto.hash(concatBytes(rt.ledger.root, rt.voxelRoot)),
  };
}

