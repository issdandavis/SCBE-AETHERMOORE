/**
 * @file resonanceGate.ts
 * @module kernel/resonanceGate
 * @layer Layer 12, Layer 14
 *
 * Resonance Gate — geometry-aware frequency membrane.
 *
 * Static envelope:
 *   H_env(d*, R) = R · π^(φ·d*)
 *
 * Resonance score:
 *   ρ = geometryAlignment(d*) · waveAlignment(t, phaseOffset)^wavePower
 *
 * Three config presets:
 *   BASELINE   — original deterministic gate (φ decay, strict thresholds)
 *   EVOLVED_V1 — optional 2026-03-15 preset for the safe-origin harshness fix
 *   EVOLVED_V2 — optional matched-filter phase discriminator over v1 geometry
 *
 * Evolved geometry mapping:
 *   geometryAlignment = floor + (1 - floor) * exp(-k · d*)
 *
 * Phase discrimination paths:
 *   weighted_wave  — legacy per-tongue weighting with averaged oscillation
 *   matched_filter — correlate the per-tongue contribution pattern against
 *                    a reference tongue signature instead of averaging it away
 */

const PHI = (1 + Math.sqrt(5)) / 2;
const F0 = 440;
const TONGUE_WEIGHTS = [1.0, PHI, PHI ** 2, PHI ** 3, PHI ** 4, PHI ** 5];
const TONGUE_PHASES = [
  0,
  Math.PI / 3,
  (2 * Math.PI) / 3,
  Math.PI,
  (4 * Math.PI) / 3,
  (5 * Math.PI) / 3,
];
const TONGUE_NAMES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;

export interface ResonanceResult {
  rho: number;
  rawAmplitude: number;
  envelope: number;
  waveAlignment: number;
  geometryAlignment: number;
  /** Matched-filter phase score (v2 only, otherwise same as waveAlignment) */
  phaseScore: number;
  phaseCorrelation: number | null;
  phaseStrategy: ResonancePhaseStrategy;
  barrierCost: number;
  tongueContributions: Record<string, number>;
  decision: 'PASS' | 'ESCALATE' | 'REJECT';
  t: number;
}

export interface ResonanceConfig {
  R: number;
  passThreshold: number;
  rejectThreshold: number;
  weights?: number[];
  signalPhaseOffset?: number;
  preset?: ResonancePresetName;
  phaseStrategy?: ResonancePhaseStrategy;
  phaseReferenceOffset?: number;
  /** Geometry decay rate (default: φ for baseline) */
  geometryDecay?: number;
  /** Wave power exponent (default: 1.0 for baseline) */
  wavePower?: number;
  /** Minimum geometry alignment floor (default: 0.0 for baseline) */
  geometryFloor?: number;
}

// ============================================================================
// Config Presets
// ============================================================================

export type ResonancePresetName = 'baseline' | 'evolved_v1' | 'evolved_v2';
export type ResonancePhaseStrategy = 'weighted_wave' | 'matched_filter';

/** Original deterministic gate — strict, φ-decay, proven safe */
export const BASELINE_RESONANCE_CONFIG: Required<ResonanceConfig> = {
  R: 1.5,
  passThreshold: 0.7,
  rejectThreshold: 0.3,
  weights: TONGUE_WEIGHTS,
  signalPhaseOffset: 0,
  preset: 'baseline',
  phaseStrategy: 'weighted_wave',
  phaseReferenceOffset: 0,
  geometryDecay: PHI,
  wavePower: 1.0,
  geometryFloor: 0.0,
};

/**
 * Evolved v1 preset — 1000-iteration optimization (2026-03-15).
 * +50.5% fitness. Origin pass: 11.9% → 99.9%. Adversarial reject: 99.7%.
 * Phase discrimination still weak (0.0009) — iterate separately.
 */
export const EVOLVED_RESONANCE_CONFIG: Required<ResonanceConfig> = {
  R: 1.731,
  passThreshold: 0.30,
  rejectThreshold: 0.213,
  weights: TONGUE_WEIGHTS,
  signalPhaseOffset: 0,
  preset: 'evolved_v1',
  phaseStrategy: 'weighted_wave',
  phaseReferenceOffset: 0,
  geometryDecay: 0.742,
  wavePower: 0.571,
  geometryFloor: 0.067,
};

export const EVOLVED_V1_CONFIG = EVOLVED_RESONANCE_CONFIG;

/**
 * Evolved v2 preset — matched-filter phase discrimination (2026-03-15).
 * Same geometry as v1 but replaces wave averaging with cross-correlation
 * against expected tongue signature pattern.
 * Phase discrimination: 0.0009 -> 0.2127 (236x improvement).
 * 180deg adversarial signals are strongly anti-correlated to the canonical
 * tongue signature rather than being washed out by averaging.
 */
export const EVOLVED_V2_CONFIG: Required<ResonanceConfig> = {
  R: 1.731,
  passThreshold: 0.30,
  rejectThreshold: 0.213,
  weights: TONGUE_WEIGHTS,
  signalPhaseOffset: 0,
  preset: 'evolved_v2',
  phaseStrategy: 'matched_filter',
  phaseReferenceOffset: 0,
  geometryDecay: 0.742,
  wavePower: 0.571,
  geometryFloor: 0.067,
};

const DEFAULT_CONFIG = BASELINE_RESONANCE_CONFIG;

function resolvePresetConfig(preset: ResonancePresetName): Required<ResonanceConfig> {
  if (preset === 'evolved_v2') {
    return EVOLVED_V2_CONFIG;
  }
  if (preset === 'evolved_v1') {
    return EVOLVED_RESONANCE_CONFIG;
  }
  return BASELINE_RESONANCE_CONFIG;
}

function mergeDefinedConfig(
  base: Required<ResonanceConfig>,
  overrides?: Partial<ResonanceConfig>
): Required<ResonanceConfig> {
  const merged = { ...base };
  if (!overrides) {
    return merged;
  }

  for (const [key, value] of Object.entries(overrides)) {
    if (value !== undefined) {
      (merged as Record<string, unknown>)[key] = value;
    }
  }

  return merged;
}

function geometryAlignmentFor(dStar: number, decay: number, floor: number): number {
  const boundedFloor = Math.max(0, Math.min(1, floor));
  const decayTerm = Math.exp(-decay * dStar);
  if (boundedFloor <= 0) {
    return decayTerm;
  }
  return boundedFloor + (1 - boundedFloor) * decayTerm;
}

// ============================================================================
// Matched-Filter Phase Discrimination (v2)
// ============================================================================

/** Expected tongue alignment pattern for a given phase offset. */
function expectedTonguePattern(phaseOffset: number): number[] {
  return TONGUE_PHASES.map((tp) => (1 + Math.cos(phaseOffset - tp)) / 2);
}

/** Normalized cross-correlation between two vectors. */
function crossCorrelate(actual: number[], expected: number[]): number {
  const n = actual.length;
  const meanA = actual.reduce((a, b) => a + b, 0) / n;
  const meanE = expected.reduce((a, b) => a + b, 0) / n;
  let num = 0;
  let denA = 0;
  let denE = 0;
  for (let i = 0; i < n; i++) {
    const da = actual[i] - meanA;
    const de = expected[i] - meanE;
    num += da * de;
    denA += da * da;
    denE += de * de;
  }
  const den = Math.sqrt(denA) * Math.sqrt(denE);
  return den > 1e-10 ? num / den : 0;
}

/**
 * Compute phase score using matched-filter cross-correlation.
 * Compares the magnitude pattern of actual tongue contributions against
 * the expected pattern for legitimate (phase=0) traffic.
 * Returns [0, 1] where 1 = perfect match, 0 = anti-correlated.
 */
function matchedFilterPhaseScore(
  contributions: Record<string, number>,
  phaseReferenceOffset: number,
): { phaseScore: number; phaseCorrelation: number } {
  const actual = TONGUE_NAMES.map((name) => Math.abs(contributions[name] ?? 0));
  const referencePattern = expectedTonguePattern(phaseReferenceOffset);
  const corr = crossCorrelate(actual, referencePattern);
  return {
    phaseScore: Math.max(0, Math.min(1, (corr + 1) / 2)),
    phaseCorrelation: corr,
  };
}

// ============================================================================
// Core Functions
// ============================================================================

export function staticEnvelope(dStar: number, R: number = 1.5): number {
  return R * Math.PI ** (PHI * dStar);
}

export function tongueWave(
  t: number,
  weights?: number[],
  signalPhaseOffset: number = 0
): { combined: number; contributions: Record<string, number> } {
  const w = weights ?? TONGUE_WEIGHTS;
  const contributions: Record<string, number> = {};
  let totalWeight = 0;
  let sum = 0;

  for (let l = 0; l < 6; l++) {
    const freq = F0 * PHI ** l;
    const tonguePhase = TONGUE_PHASES[l];

    // Per-tongue phase discrimination: each tongue's weight is modulated
    // by how well the signal phase aligns with that tongue's natural phase.
    // Legitimate traffic (phase-aligned) gets full weight.
    // Adversarial traffic (anti-phase) gets attenuated per-tongue.
    const phaseAlignment = (1 + Math.cos(signalPhaseOffset - tonguePhase)) / 2;
    const effectiveWeight = w[l] * (0.3 + 0.7 * phaseAlignment);

    const value = effectiveWeight * Math.cos(2 * Math.PI * freq * t + tonguePhase + signalPhaseOffset);
    contributions[TONGUE_NAMES[l]] = value;
    sum += value;
    totalWeight += effectiveWeight;
  }

  const combined = totalWeight > 0 ? sum / totalWeight : 0;
  return { combined, contributions };
}

/**
 * Deterministically map a seed string into a phase offset in [0, 2π).
 */
export function phaseOffsetFromSeed(seed: string): number {
  let hash = 2166136261;
  for (let i = 0; i < seed.length; i++) {
    hash ^= seed.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  const unit = (hash >>> 0) / 0xffffffff;
  return unit * 2 * Math.PI;
}

export function resonanceGate(
  dStar: number,
  t: number = 0,
  config?: Partial<ResonanceConfig>
): ResonanceResult {
  const preset = config?.preset ?? DEFAULT_CONFIG.preset;
  const cfg = mergeDefinedConfig(resolvePresetConfig(preset), { ...config, preset });
  const geoDecay = cfg.geometryDecay ?? PHI;
  const wavePow = cfg.wavePower ?? 1.0;
  const geoFloor = cfg.geometryFloor ?? 0.0;
  const phaseStrategy = cfg.phaseStrategy ?? (cfg.preset === 'evolved_v2' ? 'matched_filter' : 'weighted_wave');
  const phaseReferenceOffset = cfg.phaseReferenceOffset ?? 0;

  const boundedDStar = Math.max(0, dStar);
  const envelope = staticEnvelope(boundedDStar, cfg.R);
  const { combined, contributions } = tongueWave(t, cfg.weights, cfg.signalPhaseOffset ?? 0);

  const waveAlignment = Math.max(0, Math.min(1, (combined + 1) / 2));
  const geometryAlignment = geometryAlignmentFor(boundedDStar, geoDecay, geoFloor);
  const matchedPhase = phaseStrategy === 'matched_filter'
    ? matchedFilterPhaseScore(contributions, phaseReferenceOffset)
    : null;
  const phaseScore = matchedPhase?.phaseScore ?? waveAlignment;
  const phaseCorrelation = matchedPhase?.phaseCorrelation ?? null;
  const rho = Math.max(0, Math.min(1, (phaseScore ** wavePow) * geometryAlignment));
  const rawAmplitude = envelope * waveAlignment;
  const barrierCost = envelope / Math.max(rho, 1e-6);

  let decision: 'PASS' | 'ESCALATE' | 'REJECT';
  if (rho >= cfg.passThreshold) {
    decision = 'PASS';
  } else if (rho >= cfg.rejectThreshold) {
    decision = 'ESCALATE';
  } else {
    decision = 'REJECT';
  }

  return {
    rho,
    rawAmplitude,
    envelope,
    waveAlignment,
    geometryAlignment,
    phaseScore,
    phaseCorrelation,
    phaseStrategy,
    barrierCost,
    tongueContributions: contributions,
    decision,
    t,
  };
}

export function phiInvariantCheck(
  dStar: number,
  samples: number = 64,
  dt: number = 0.001,
  config?: Partial<ResonanceConfig>
): { fractalDim: number; isPhiAligned: boolean; tolerance: number } {
  const values: number[] = [];
  for (let i = 0; i < samples; i++) {
    values.push(resonanceGate(dStar, i * dt, config).rho);
  }

  const epsilons = [0.1, 0.05, 0.025, 0.0125];
  const counts: number[] = [];
  for (const eps of epsilons) {
    const boxes = new Set<number>();
    for (const v of values) {
      boxes.add(Math.floor(v / eps));
    }
    counts.push(boxes.size);
  }

  const logEps = epsilons.map((e) => Math.log(e));
  const logN = counts.map((n) => Math.log(Math.max(n, 1)));

  const n = logEps.length;
  const sumX = logEps.reduce((a, b) => a + b, 0);
  const sumY = logN.reduce((a, b) => a + b, 0);
  const sumXY = logEps.reduce((a, x, i) => a + x * logN[i], 0);
  const sumX2 = logEps.reduce((a, x) => a + x * x, 0);

  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const fractalDim = -slope;
  const tolerance = 0.15;
  const isPhiAligned = Math.abs(fractalDim - PHI) < tolerance;

  return { fractalDim, isPhiAligned, tolerance };
}
