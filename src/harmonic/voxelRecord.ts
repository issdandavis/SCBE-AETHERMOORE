/**
 * @file voxelRecord.ts
 * @module harmonic/voxelRecord
 * @layer Layer 1, Layer 12, Layer 13
 * @component Voxel Record Operations
 * @version 3.2.4
 *
 * Deterministic CubeId generation, payload digest computation,
 * quorum validation, and SCBE decision gating for VoxelRecords.
 */

import { createHash } from 'crypto';
import { canonicalize } from '../crypto/jcs.js';
import {
  type Lang,
  type PadMode,
  type Voxel6,
  type Decision,
  type VoxelRecord,
  type QuorumProof,
  type QuorumVote,
  type SacredEggSeal,
} from './scbe_voxel_types.js';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

/** Golden ratio φ for harmonic scaling */
const PHI = (1 + Math.sqrt(5)) / 2;

/** Default SCBE governance thresholds */
export interface SCBEThresholds {
  /** Max H_eff for ALLOW (default 1e3) */
  allowMaxCost: number;
  /** Max H_eff for QUARANTINE (default 1e6) */
  quarantineMaxCost: number;
  /** Min coherence for ALLOW (default 0.55) */
  allowMinCoherence: number;
  /** Min coherence for QUARANTINE (default 0.25) */
  quarantineMinCoherence: number;
  /** Max d* for ALLOW (default 1.2) */
  allowMaxDrift: number;
  /** Max d* for QUARANTINE (default 2.2) */
  quarantineMaxDrift: number;
}

export const DEFAULT_THRESHOLDS: Readonly<SCBEThresholds> = {
  allowMaxCost: 1e3,
  quarantineMaxCost: 1e6,
  allowMinCoherence: 0.55,
  quarantineMinCoherence: 0.25,
  allowMaxDrift: 1.2,
  quarantineMaxDrift: 2.2,
};

/** Visible-spectrum bounds used for continuous gate visualization. */
const SPECTRUM_MIN_NM = 380;
const SPECTRUM_MAX_NM = 700;

/** Continuous spectrum band labels. */
export type SpectrumBand = 'violet' | 'blue' | 'green' | 'yellow' | 'orange' | 'red';

/** Continuous spectrum state labels for pressure near the decision wall. */
export type SpectrumState = 'stable' | 'pressured' | 'near_break' | 'breaking';

/** Component pressures that feed the continuous spectrum overlay. */
export interface SpectrumPressureComponents {
  coherencePressure: number;
  driftPressure: number;
  costPressure: number;
}

/**
 * Continuous gate overlay that sits beside the discrete L13 decision.
 *
 * This does not replace ALLOW / QUARANTINE / DENY. It exposes where the
 * current state sits on a continuous pressure spectrum so downstream systems
 * (audio, UI, telemetry) can reason about edge behavior without weakening
 * deterministic enforcement.
 */
export interface SpectrumGate {
  /** The authoritative discrete governance result from scbeDecide(). */
  discreteDecision: Decision;
  /** Continuous pressure ০ [0,1], where 0=safe center and 1=break point. */
  pressure: number;
  /** Visible-spectrum projection of pressure in nanometers. */
  wavelengthNm: number;
  /** Coarse color band for the projected wavelength. */
  band: SpectrumBand;
  /** Human-readable state label for the pressure region. */
  state: SpectrumState;
  /** Component-level contribution to the final pressure. */
  components: SpectrumPressureComponents;
}

/** Per-band projection helper for audio or multi-channel overlays. */
export interface SpectrumBandProjection {
  bandIndex: number;
  pressure: number;
  wavelengthNm: number;
  band: SpectrumBand;
  state: SpectrumState;
}

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function risingPressure(value: number, safeMax: number, dangerMax: number): number {
  if (value <= safeMax) return 0;
  if (value >= dangerMax) return 1;
  return clamp01((value - safeMax) / (dangerMax - safeMax));
}

function fallingPressure(value: number, safeMin: number, dangerMin: number): number {
  if (value >= safeMin) return 0;
  if (value <= dangerMin) return 1;
  return clamp01((safeMin - value) / (safeMin - dangerMin));
}

function logarithmicPressure(value: number, safeMax: number, dangerMax: number): number {
  const v = Math.log10(Math.max(value, 1e-12));
  const safe = Math.log10(Math.max(safeMax, 1e-12));
  const danger = Math.log10(Math.max(dangerMax, 1e-12));
  return risingPressure(v, safe, danger);
}

/** Convert normalized pressure into a visible-spectrum wavelength. */
export function pressureToWavelength(pressure: number): number {
  const p = clamp01(pressure);
  return SPECTRUM_MIN_NM + p * (SPECTRUM_MAX_NM - SPECTRUM_MIN_NM);
}

/** Map wavelength to a coarse visible-spectrum band label. */
export function wavelengthToBand(wavelengthNm: number): SpectrumBand {
  if (wavelengthNm < 450) return 'violet';
  if (wavelengthNm < 495) return 'blue';
  if (wavelengthNm < 570) return 'green';
  if (wavelengthNm < 590) return 'yellow';
  if (wavelengthNm < 620) return 'orange';
  return 'red';
}

/** Map normalized pressure to a state label near the wall. */
export function pressureToSpectrumState(pressure: number): SpectrumState {
  const p = clamp01(pressure);
  if (p < 0.2) return 'stable';
  if (p < 0.5) return 'pressured';
  if (p < 0.8) return 'near_break';
  return 'breaking';
}

/**
 * Compute normalized component pressures from the existing SCBE thresholds.
 *
 * Cost uses a log scale because harmonic cost spans orders of magnitude.
 */
export function computeSpectrumPressure(
  dStar: number,
  coherence: number,
  hEff: number,
  thresholds: SCBEThresholds = DEFAULT_THRESHOLDS
): SpectrumPressureComponents & { pressure: number } {
  const coherencePressure = fallingPressure(
    coherence,
    thresholds.allowMinCoherence,
    thresholds.quarantineMinCoherence
  );
  const driftPressure = risingPressure(dStar, thresholds.allowMaxDrift, thresholds.quarantineMaxDrift);
  const costPressure = logarithmicPressure(
    hEff,
    thresholds.allowMaxCost,
    thresholds.quarantineMaxCost
  );

  // Conservative blend: strongest failing component dominates, but retain
  // some contribution from the average so the curve moves smoothly.
  const pressure = clamp01(
    Math.max(coherencePressure, driftPressure, costPressure) * 0.7 +
      ((coherencePressure + driftPressure + costPressure) / 3) * 0.3
  );

  return { coherencePressure, driftPressure, costPressure, pressure };
}

/**
 * Compute a continuous spectrum overlay beside the discrete L13 decision.
 */
export function computeSpectrumGate(
  dStar: number,
  coherence: number,
  hEff: number,
  thresholds: SCBEThresholds = DEFAULT_THRESHOLDS
): SpectrumGate {
  const discreteDecision = scbeDecide(dStar, coherence, hEff, thresholds);
  const { pressure, coherencePressure, driftPressure, costPressure } = computeSpectrumPressure(
    dStar,
    coherence,
    hEff,
    thresholds
  );
  const wavelengthNm = pressureToWavelength(pressure);

  return {
    discreteDecision,
    pressure,
    wavelengthNm,
    band: wavelengthToBand(wavelengthNm),
    state: pressureToSpectrumState(pressure),
    components: {
      coherencePressure,
      driftPressure,
      costPressure,
    },
  };
}

/**
 * Project arbitrary normalized per-band pressures into the visible spectrum.
 *
 * Useful for experimental audio-band gating without changing the core SCBE
 * decision envelope.
 */
export function projectBandPressuresToSpectrum(pressures: number[]): SpectrumBandProjection[] {
  return pressures.map((pressure, bandIndex) => {
    const p = clamp01(pressure);
    const wavelengthNm = pressureToWavelength(p);
    return {
      bandIndex,
      pressure: p,
      wavelengthNm,
      band: wavelengthToBand(wavelengthNm),
      state: pressureToSpectrumState(p),
    };
  });
}

// ═══════════════════════════════════════════════════════════════
// CubeId + Digest (deterministic, canonical)
// ═══════════════════════════════════════════════════════════════

/**
 * Compute deterministic CubeId from addressing fields.
 *
 * cubeId = sha256(canonical({lang, voxel, epoch, padMode}))
 *
 * Uses JCS (RFC 8785) canonicalization for stability.
 */
export function computeCubeId(lang: Lang, voxel: Voxel6, epoch: number, padMode: PadMode): string {
  const payload = { lang, voxel: Array.from(voxel), epoch, padMode };
  const canonical = canonicalize(payload);
  return createHash('sha256').update(canonical, 'utf-8').digest('hex');
}

/**
 * Compute payload digest from ciphertext bytes.
 *
 * payloadDigest = sha256(payloadCiphertextBytes)
 */
export function computePayloadDigest(payloadCiphertext: string): string {
  const bytes = Buffer.from(payloadCiphertext, 'base64');
  return createHash('sha256').update(bytes).digest('hex');
}

/**
 * Compute the agent signature payload hash.
 *
 * sigPayload = sha256(cubeId || payloadDigest || epoch || padMode)
 *
 * Agents sign this to cast a quorum vote.
 */
export function computeSignaturePayload(
  cubeId: string,
  payloadDigest: string,
  epoch: number,
  padMode: PadMode
): string {
  const combined = `${cubeId}${payloadDigest}${epoch}${padMode}`;
  return createHash('sha256').update(combined, 'utf-8').digest('hex');
}

// ═══════════════════════════════════════════════════════════════
// SCBE Decision (L13)
// ═══════════════════════════════════════════════════════════════

/**
 * Compute SCBE risk decision from governance state.
 *
 * Decision hierarchy:
 *   DENY if coherence < quarantine_min OR hEff > quarantine_max OR dStar > quarantine_max
 *   ALLOW if coherence >= allow_min AND hEff <= allow_max AND dStar <= allow_max
 *   QUARANTINE otherwise
 */
export function scbeDecide(
  dStar: number,
  coherence: number,
  hEff: number,
  thresholds: SCBEThresholds = DEFAULT_THRESHOLDS
): Decision {
  if (coherence < thresholds.quarantineMinCoherence) return 'DENY';
  if (hEff > thresholds.quarantineMaxCost) return 'DENY';
  if (dStar > thresholds.quarantineMaxDrift) return 'DENY';

  if (
    coherence >= thresholds.allowMinCoherence &&
    hEff <= thresholds.allowMaxCost &&
    dStar <= thresholds.allowMaxDrift
  ) {
    return 'ALLOW';
  }

  return 'QUARANTINE';
}

/**
 * Compute effective harmonic cost H(d*, R).
 *
 * H(d*, R) = R · π^(φ · d*)
 *
 * This is the Layer-12 event horizon: cost grows super-exponentially
 * with hyperbolic realm distance, making adversarial access infeasible.
 */
export function harmonicCost(dStar: number, R: number = 1.5): number {
  return R * Math.pow(Math.PI, PHI * dStar);
}

// ═══════════════════════════════════════════════════════════════
// Quorum Validation (Byzantine, n=6, f=1, threshold=4)
// ═══════════════════════════════════════════════════════════════

/**
 * Validate a quorum proof against a VoxelRecord.
 *
 * Checks:
 * 1. n=6, f=1, threshold=4
 * 2. ≥threshold votes present
 * 3. All votes reference the same digest
 * 4. All agent IDs are unique
 * 5. All digests match the record's payloadDigest
 */
export function validateQuorum(
  quorum: QuorumProof,
  expectedDigest: string
): { valid: boolean; matchingVotes: number; reason?: string } {
  if (quorum.n !== 6) {
    return { valid: false, matchingVotes: 0, reason: 'n must be 6' };
  }
  if (quorum.f !== 1) {
    return { valid: false, matchingVotes: 0, reason: 'f must be 1' };
  }
  if (quorum.threshold !== 4) {
    return { valid: false, matchingVotes: 0, reason: 'threshold must be 4' };
  }

  if (quorum.votes.length < quorum.threshold) {
    return {
      valid: false,
      matchingVotes: quorum.votes.length,
      reason: `insufficient votes: ${quorum.votes.length}/${quorum.threshold}`,
    };
  }

  // Check uniqueness of agent IDs
  const agentIds = new Set(quorum.votes.map((v) => v.agentId));
  if (agentIds.size !== quorum.votes.length) {
    return { valid: false, matchingVotes: 0, reason: 'duplicate agent IDs' };
  }

  // Count matching digests
  const matchingVotes = quorum.votes.filter((v) => v.digest === expectedDigest).length;

  if (matchingVotes < quorum.threshold) {
    return {
      valid: false,
      matchingVotes,
      reason: `digest mismatch: ${matchingVotes}/${quorum.threshold} matching`,
    };
  }

  return { valid: true, matchingVotes };
}

// ═══════════════════════════════════════════════════════════════
// VoxelRecord Builder
// ═══════════════════════════════════════════════════════════════

/** Parameters for building a VoxelRecord */
export interface VoxelRecordParams {
  lang: Lang;
  voxel: Voxel6;
  epoch: number;
  padMode: PadMode;
  coherence: number;
  dStar: number;
  /** Raw plaintext payload (will be "encrypted" as base64) */
  payload: string;
  /** Egg ID for the Sacred Egg seal */
  eggId: string;
  /** Optional tags */
  tags?: string[];
  /** Optional parent cubeIds */
  parents?: string[];
  /** SCBE thresholds override */
  thresholds?: SCBEThresholds;
}

/**
 * Build a complete VoxelRecord from parameters.
 *
 * Computes:
 * - cubeId (deterministic from addressing)
 * - hEff (harmonic cost from dStar)
 * - decision (SCBE L13)
 * - payloadCiphertext (base64 placeholder — real AEAD in production)
 * - payloadDigest (sha256 of ciphertext bytes)
 * - seal (Sacred Egg metadata)
 */
export function buildVoxelRecord(params: VoxelRecordParams): VoxelRecord {
  const {
    lang,
    voxel,
    epoch,
    padMode,
    coherence,
    dStar,
    payload,
    eggId,
    tags,
    parents,
    thresholds = DEFAULT_THRESHOLDS,
  } = params;

  const cubeId = computeCubeId(lang, voxel, epoch, padMode);
  const hEff = harmonicCost(dStar);
  const decision = scbeDecide(dStar, coherence, hEff, thresholds);

  // Placeholder encryption — in production, use AEAD with egg key
  const payloadCiphertext = Buffer.from(payload, 'utf-8').toString('base64');
  const payloadDigest = computePayloadDigest(payloadCiphertext);

  // Build AAD as hash of header fields
  const headerHash = createHash('sha256')
    .update(canonicalize({ lang, voxel: Array.from(voxel), epoch, padMode, coherence, dStar }))
    .digest('hex');

  const seal: SacredEggSeal = {
    eggId,
    kdf: 'pi_phi',
    dStar,
    coherence,
    nonce: createHash('sha256').update(`${cubeId}:${Date.now()}`).digest('hex').slice(0, 24),
    aad: headerHash,
  };

  return {
    version: 1,
    lang,
    voxel,
    epoch,
    padMode,
    coherence,
    dStar,
    hEff,
    decision,
    cubeId,
    payloadDigest,
    seal,
    payloadCiphertext,
    ...(tags && { tags }),
    ...(parents && { parents }),
  };
}

/**
 * Create a simulated quorum proof for a record.
 *
 * In production, each agent independently computes and signs.
 * This creates a valid stub for n=6, f=1, threshold=4.
 *
 * @param cubeId - The record's cubeId
 * @param payloadDigest - The record's payloadDigest
 * @param epoch - The record's epoch
 * @param padMode - The record's padMode
 * @param agentCount - Number of agreeing agents (default 4)
 */
export function simulateQuorum(
  cubeId: string,
  payloadDigest: string,
  epoch: number,
  padMode: PadMode,
  agentCount: number = 4
): QuorumProof {
  const sigPayload = computeSignaturePayload(cubeId, payloadDigest, epoch, padMode);
  const now = Date.now();

  const votes: QuorumVote[] = Array.from({ length: agentCount }, (_, i) => ({
    agentId: `agent-${i + 1}`,
    digest: payloadDigest,
    sig: createHash('sha256')
      .update(`${sigPayload}:agent-${i + 1}`)
      .digest('hex'),
    ts: now + i,
  }));

  return {
    n: 6,
    f: 1,
    threshold: 4,
    votes,
  };
}
