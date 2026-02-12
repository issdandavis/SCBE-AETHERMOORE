/**
 * @file temporalIntent.ts
 * @module harmonic/temporalIntent
 * @layer Layer 5, Layer 11, Layer 12, Layer 13
 * @component Temporal-Intent Harmonic Scaling
 * @version 3.2.4
 *
 * Extends the Harmonic Scaling Law with temporal intent accumulation:
 *
 *     H_eff(d, R, x) = R^(d² · x)
 *
 * Where:
 *     d = distance from safe operation (Poincaré ball, Layer 5)
 *     R = harmonic ratio (1.5 = perfect fifth)
 *     x = temporal intent factor derived from L11 + CPSE channels
 *
 * The 'x' factor aggregates existing metrics:
 *
 *     x(t) = f(d_tri(t), chaosdev(t), fractaldev(t), energydev(t))
 *
 * This makes security cost compound based on SUSTAINED adversarial behavior,
 * not just instantaneous distance. Brief deviations are forgiven; persistent
 * drift toward the boundary costs super-exponentially more over time.
 *
 * Integration with existing layers:
 *     - L5:  Hyperbolic distance provides 'd'
 *     - L11: Triadic Temporal Distance provides d_tri(t)
 *     - L12: Harmonic Wall now uses H_eff(d,R,x) instead of H(d,R)
 *     - CPSE: Chaos/fractal/energy deviation channels provide z_t
 *
 * "Security IS growth. Intent over time reveals truth."
 */

import type { Vector6D } from './constants.js';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

/** Harmonic ratio (perfect fifth) */
export const R_HARMONIC = 1.5;

/** Intent decay rate per time window (how fast old intent fades) */
export const INTENT_DECAY_RATE = 0.95;

/** Time window for intent accumulation (seconds) */
export const INTENT_WINDOW_SECONDS = 1.0;

/** Maximum intent accumulation before hard exile */
export const MAX_INTENT_ACCUMULATION = 10.0;

/** Trust threshold for exile (from AC-2.3.2) */
export const TRUST_EXILE_THRESHOLD = 0.3;

/** Consecutive low-trust rounds to trigger exile */
export const TRUST_EXILE_ROUNDS = 10;

// ═══════════════════════════════════════════════════════════════
// Intent State
// ═══════════════════════════════════════════════════════════════

/** Classification of agent's temporal intent */
export enum IntentState {
  /** x < 0.5 — consistently safe */
  BENIGN = 'benign',
  /** 0.5 <= x < 1.0 — normal operation */
  NEUTRAL = 'neutral',
  /** 1.0 <= x < 2.0 — concerning pattern */
  DRIFTING = 'drifting',
  /** x >= 2.0 — sustained adversarial behavior */
  ADVERSARIAL = 'adversarial',
  /** Null-space exile triggered */
  EXILED = 'exiled',
}

// ═══════════════════════════════════════════════════════════════
// Intent Sample
// ═══════════════════════════════════════════════════════════════

/** Single sample of distance/intent at a point in time */
export interface IntentSampleInput {
  /** Timestamp in ms (Date.now() compatible) */
  timestamp: number;
  /** Distance in Poincaré ball (0 to ~1) from L5 */
  distance: number;
  /** Rate of change of distance */
  velocity: number;
  /** CHARM value (-1 to 1) */
  harmony: number;
  /** Lyapunov-based chaos deviation (CPSE z-vector) */
  chaosdev?: number;
  /** Fractal dimension deviation */
  fractaldev?: number;
  /** Energy channel deviation */
  energydev?: number;
  /** Triadic temporal: immediate behavior */
  dTriImmediate?: number;
  /** Triadic temporal: medium-term pattern */
  dTriMedium?: number;
  /** Triadic temporal: long-term trajectory */
  dTriLong?: number;
}

/** Computed intent sample with derived metrics */
export interface IntentSample extends IntentSampleInput {
  /** Triadic temporal distance (L11) — geometric mean of 3 scales */
  dTri: number;
  /** Raw intent value for this sample */
  rawIntent: number;
}

/**
 * Compute triadic temporal distance (L11) — geometric mean of 3 time scales.
 */
export function computeDTri(
  immediate: number,
  medium: number,
  long: number
): number {
  return Math.cbrt(Math.abs(immediate) * Math.abs(medium) * Math.abs(long));
}

/**
 * Compute raw intent from a single sample using L11 + CPSE metrics.
 *
 * x(t) = f(d_tri(t), chaosdev(t), fractaldev(t), energydev(t))
 */
export function computeRawIntent(input: IntentSampleInput): number {
  const chaosdev = input.chaosdev ?? 0;
  const fractaldev = input.fractaldev ?? 0;
  const energydev = input.energydev ?? 0;
  const dTriImmediate = input.dTriImmediate ?? 0;
  const dTriMedium = input.dTriMedium ?? 0;
  const dTriLong = input.dTriLong ?? 0;

  // Velocity contribution (moving toward boundary is adversarial)
  const velocityFactor = Math.max(0, input.velocity) * 2.0;

  // Distance contribution (further out = more suspicious)
  const distanceFactor = input.distance ** 2;

  // Harmony dampening (high harmony reduces intent score)
  const harmonyDampening = (1 - input.harmony) / 2; // 0 to 1

  // CPSE deviation channels contribution
  const cpseFactor = (Math.abs(chaosdev) + Math.abs(fractaldev) + Math.abs(energydev)) / 3;

  // Triadic temporal contribution (L11)
  const triadicFactor = computeDTri(dTriImmediate, dTriMedium, dTriLong);

  const baseIntent = (velocityFactor + distanceFactor) * (0.5 + harmonyDampening);

  // Amplify by CPSE deviations and triadic distance
  return baseIntent * (1.0 + cpseFactor + triadicFactor);
}

/**
 * Build a full IntentSample from input, computing derived metrics.
 */
export function buildSample(input: IntentSampleInput): IntentSample {
  return {
    ...input,
    chaosdev: input.chaosdev ?? 0,
    fractaldev: input.fractaldev ?? 0,
    energydev: input.energydev ?? 0,
    dTriImmediate: input.dTriImmediate ?? 0,
    dTriMedium: input.dTriMedium ?? 0,
    dTriLong: input.dTriLong ?? 0,
    dTri: computeDTri(
      input.dTriImmediate ?? 0,
      input.dTriMedium ?? 0,
      input.dTriLong ?? 0
    ),
    rawIntent: computeRawIntent(input),
  };
}

// ═══════════════════════════════════════════════════════════════
// Intent History
// ═══════════════════════════════════════════════════════════════

/** Full state of an agent's intent history */
export interface IntentHistoryState {
  agentId: string;
  samples: IntentSample[];
  accumulatedIntent: number;
  trustScore: number;
  lowTrustRounds: number;
  state: IntentState;
  lastUpdateMs: number;
}

/** Maximum samples to retain */
const MAX_SAMPLES = 1000;

/**
 * Create a fresh intent history for an agent.
 */
export function createIntentHistory(agentId: string, nowMs?: number): IntentHistoryState {
  return {
    agentId,
    samples: [],
    accumulatedIntent: 0,
    trustScore: 1.0,
    lowTrustRounds: 0,
    state: IntentState.NEUTRAL,
    lastUpdateMs: nowMs ?? Date.now(),
  };
}

/**
 * Add a sample to intent history, updating accumulation, trust, and state.
 * Returns a new IntentHistoryState (immutable update).
 */
export function addSample(
  history: IntentHistoryState,
  distance: number,
  velocity: number = 0,
  harmony: number = 0,
  nowMs?: number
): IntentHistoryState {
  const now = nowMs ?? Date.now();

  const sample = buildSample({
    timestamp: now,
    distance,
    velocity,
    harmony,
  });

  // Append sample (cap at MAX_SAMPLES)
  const samples =
    history.samples.length >= MAX_SAMPLES
      ? [...history.samples.slice(1), sample]
      : [...history.samples, sample];

  // Apply decay to accumulated intent
  const timeDeltaSec = (now - history.lastUpdateMs) / 1000;
  const decayFactor = Math.pow(INTENT_DECAY_RATE, timeDeltaSec / INTENT_WINDOW_SECONDS);
  let accumulatedIntent = history.accumulatedIntent * decayFactor + sample.rawIntent;
  accumulatedIntent = Math.min(accumulatedIntent, MAX_INTENT_ACCUMULATION);

  // Update trust score
  let trustScore = history.trustScore;
  let lowTrustRounds = history.lowTrustRounds;
  if (samples.length >= 5) {
    const recent = samples.slice(-10);
    const avgDistance = recent.reduce((s, s2) => s + s2.distance, 0) / recent.length;
    let trustChange = -0.1 * avgDistance - 0.05 * accumulatedIntent;
    if (accumulatedIntent < 0.5 && avgDistance < 0.3) {
      trustChange += 0.02;
    }
    trustScore = Math.max(0, Math.min(1, trustScore + trustChange));
  }

  if (trustScore < TRUST_EXILE_THRESHOLD) {
    lowTrustRounds = lowTrustRounds + 1;
  } else {
    lowTrustRounds = 0;
  }

  // Classify intent state
  let state: IntentState;
  if (lowTrustRounds >= TRUST_EXILE_ROUNDS) {
    state = IntentState.EXILED;
  } else if (accumulatedIntent < 0.5) {
    state = IntentState.BENIGN;
  } else if (accumulatedIntent < 1.0) {
    state = IntentState.NEUTRAL;
  } else if (accumulatedIntent < 2.0) {
    state = IntentState.DRIFTING;
  } else {
    state = IntentState.ADVERSARIAL;
  }

  return {
    agentId: history.agentId,
    samples,
    accumulatedIntent,
    trustScore,
    lowTrustRounds,
    state,
    lastUpdateMs: now,
  };
}

/**
 * Compute the x-factor for H(d,R)^x from an intent history.
 *
 * Returns a value typically between 0.5 and 3.0:
 *   - x < 1: Forgiving (brief deviation)
 *   - x = 1: Standard H(d,R)
 *   - x > 1: Compounding (sustained adversarial)
 */
export function computeXFactor(history: IntentHistoryState): number {
  const baseX = 0.5 + history.accumulatedIntent * 0.25;
  const trustModifier = 1.0 + (1.0 - history.trustScore);
  return Math.min(3.0, baseX * trustModifier);
}

// ═══════════════════════════════════════════════════════════════
// Extended Harmonic Wall
// ═══════════════════════════════════════════════════════════════

/**
 * Original Harmonic Wall: H(d, R) = R^(d²)
 */
export function harmonicWallBasic(d: number, R: number = R_HARMONIC): number {
  return Math.pow(R, d * d);
}

/**
 * Extended Harmonic Wall with temporal intent: H_eff(d, R, x) = R^(d² · x)
 *
 * @param d — Distance from safe operation (0 to ~1 in Poincaré ball)
 * @param x — Intent persistence factor from computeXFactor
 * @param R — Harmonic ratio (default 1.5 = perfect fifth)
 * @returns Security cost multiplier (grows super-exponentially with sustained drift)
 */
export function harmonicWallTemporal(d: number, x: number, R: number = R_HARMONIC): number {
  return Math.pow(R, d * d * x);
}

/**
 * Compare basic vs temporal harmonic wall at given distance and intent.
 */
export function compareScaling(
  d: number,
  x: number
): { distance: number; xFactor: number; hBasic: number; hTemporal: number; amplification: number } {
  const hBasic = harmonicWallBasic(d);
  const hTemporal = harmonicWallTemporal(d, x);
  return {
    distance: d,
    xFactor: x,
    hBasic,
    hTemporal,
    amplification: hBasic > 0 ? hTemporal / hBasic : Infinity,
  };
}

// ═══════════════════════════════════════════════════════════════
// Temporal Security Gate (Layer 13 Integration)
// ═══════════════════════════════════════════════════════════════

/** Decision thresholds from AC-2.3.4 */
export const ALLOW_THRESHOLD = 0.85;
export const QUARANTINE_THRESHOLD = 0.40;

/** Possible gate decisions */
export type GateDecision = 'ALLOW' | 'QUARANTINE' | 'DENY' | 'EXILE';

/** Result of Omega computation */
export interface OmegaResult {
  omega: number;
  decision: GateDecision;
  xFactor: number;
  hTemporal: number;
  harmScore: number;
  driftFactor: number;
  state: IntentState;
}

/**
 * Compute Omega decision score using temporal intent scaling.
 *
 * Ω = pqc_valid × harm_score × drift_factor × triadic_stable × spectral_score
 *
 * Where:
 *   harm_score  = 1 / (1 + log(H(d, R)^x))   (inverted: higher = safer)
 *   drift_factor = 1 - accumulated_intent / MAX
 */
export function computeOmega(
  history: IntentHistoryState,
  pqcValid: boolean = true,
  triadicStable: number = 1.0,
  spectralScore: number = 1.0
): OmegaResult {
  // Exile check
  if (history.state === IntentState.EXILED) {
    return {
      omega: 0,
      decision: 'EXILE',
      xFactor: computeXFactor(history),
      hTemporal: Infinity,
      harmScore: 0,
      driftFactor: 0,
      state: IntentState.EXILED,
    };
  }

  // Get latest distance
  const d =
    history.samples.length > 0
      ? history.samples[history.samples.length - 1].distance
      : 0;

  const x = computeXFactor(history);
  const hTemporal = harmonicWallTemporal(d, x);

  // Invert for harm_score (lower H = higher score = safer)
  const harmScore = 1.0 / (1.0 + Math.log(Math.max(1.0, hTemporal)));

  // Drift factor from accumulated intent
  const driftFactor = 1.0 - history.accumulatedIntent / MAX_INTENT_ACCUMULATION;

  // PQC factor
  const pqcFactor = pqcValid ? 1.0 : 0.0;

  // Compute Omega
  const omega = pqcFactor * harmScore * driftFactor * triadicStable * spectralScore;

  // Decision
  let decision: GateDecision;
  if (omega > ALLOW_THRESHOLD) {
    decision = 'ALLOW';
  } else if (omega > QUARANTINE_THRESHOLD) {
    decision = 'QUARANTINE';
  } else {
    decision = 'DENY';
  }

  return {
    omega,
    decision,
    xFactor: x,
    hTemporal,
    harmScore,
    driftFactor,
    state: history.state,
  };
}

/**
 * Get full status for an agent's intent history.
 */
export function getStatus(history: IntentHistoryState): {
  agentId: string;
  state: string;
  trustScore: number;
  accumulatedIntent: number;
  xFactor: number;
  lowTrustRounds: number;
  sampleCount: number;
  omega: number;
  decision: GateDecision;
} {
  const result = computeOmega(history);
  return {
    agentId: history.agentId,
    state: history.state,
    trustScore: history.trustScore,
    accumulatedIntent: history.accumulatedIntent,
    xFactor: result.xFactor,
    lowTrustRounds: history.lowTrustRounds,
    sampleCount: history.samples.length,
    omega: result.omega,
    decision: result.decision,
  };
}

// ═══════════════════════════════════════════════════════════════
// Multi-Agent Gate (manages histories for many agents)
// ═══════════════════════════════════════════════════════════════

/** Manages temporal intent histories for multiple agents */
export class TemporalSecurityGate {
  private histories: Map<string, IntentHistoryState> = new Map();

  /** Get or create intent history for an agent */
  getOrCreate(agentId: string, nowMs?: number): IntentHistoryState {
    let h = this.histories.get(agentId);
    if (!h) {
      h = createIntentHistory(agentId, nowMs);
      this.histories.set(agentId, h);
    }
    return h;
  }

  /** Record an observation for an agent */
  recordObservation(
    agentId: string,
    distance: number,
    velocity: number = 0,
    harmony: number = 0,
    nowMs?: number
  ): IntentHistoryState {
    const current = this.getOrCreate(agentId, nowMs);
    const updated = addSample(current, distance, velocity, harmony, nowMs);
    this.histories.set(agentId, updated);
    return updated;
  }

  /** Compute Omega decision for an agent */
  computeOmega(
    agentId: string,
    pqcValid?: boolean,
    triadicStable?: number,
    spectralScore?: number
  ): OmegaResult {
    return computeOmega(this.getOrCreate(agentId), pqcValid, triadicStable, spectralScore);
  }

  /** Get full status for an agent */
  getStatus(agentId: string): ReturnType<typeof getStatus> {
    return getStatus(this.getOrCreate(agentId));
  }

  /** Get all tracked agent IDs */
  agentIds(): string[] {
    return Array.from(this.histories.keys());
  }

  /** Remove an agent's history */
  remove(agentId: string): boolean {
    return this.histories.delete(agentId);
  }
}
