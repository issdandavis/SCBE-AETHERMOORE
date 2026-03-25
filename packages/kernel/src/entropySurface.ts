/**
 * @file entropySurface.ts
 * @module harmonic/entropySurface
 * @layer Layer 12, Layer 13
 * @component Entropy Surface Defense — Semantic Nullification, Probing Detection, Leakage Budget
 * @version 1.0.0
 *
 * Implements "controlled entropy surface" defense:
 *
 *   1. Probing Detection: Distinguishes adversarial probing from legitimate use
 *      by analyzing query distribution entropy, temporal patterns, input-space
 *      coverage breadth, and repetition fingerprints.
 *
 *   2. Leakage Budget: Information-theoretic bound on how many useful bits
 *      the system emits under observation. A sliding-window rate limiter
 *      that degrades output signal when the budget is consumed.
 *
 *   3. Semantic Nullification: Computes the strength of "graceful adversarial
 *      degradation" — how much true signal to retain vs. replace with
 *      plausible-but-inert output. Under probing, the system converges
 *      to maximum entropy (uniform/uninformative) responses.
 *
 * Core insight: model extraction requires stable (input → output) mappings.
 * This layer ensures that under uncertainty or probing, outputs carry
 * near-zero mutual information with the true function, so surrogate
 * models converge to noise rather than behavior.
 *
 * Mathematical basis:
 *   - Signal retention:  σ(x) = 1 / (1 + e^{k(p - θ)})   (sigmoid gating)
 *   - Leakage rate:      λ(t) = Σ_{i∈W} I(x_i; y_i)      (mutual info estimate)
 *   - Nullification:     N(x) = (1 - σ) · U + σ · f(x)    (mixture with uniform)
 *
 * A4: Symmetry — Nullification is invariant to input permutation
 * A3: Causality — Leakage budget is monotonically consumed (time-ordered)
 */

import type { Vector6D } from './constants.js';
import { hyperbolicDistance6D, poincareNorm } from './chsfn.js';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

const EPSILON = 1e-10;
const LN2 = Math.LN2;

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/**
 * Signature of a potential probing attempt.
 */
export interface ProbingSignature {
  /** Shannon entropy of recent query distribution [0, 1] — low = systematic probing */
  queryEntropy: number;
  /** Temporal regularity score [0, 1] — high = machine-like timing */
  temporalRegularity: number;
  /** Input-space coverage breadth [0, 1] — high = systematic exploration */
  coverageBreadth: number;
  /** Repetition fingerprint [0, 1] — high = many near-duplicate queries */
  repetitionScore: number;
  /** Composite probing confidence [0, 1] */
  confidence: number;
  /** Classification */
  classification: 'LEGITIMATE' | 'AMBIGUOUS' | 'PROBING';
}

/**
 * Information leakage budget tracker.
 */
export interface LeakageBudget {
  /** Maximum allowable information bits in the window */
  totalBudget: number;
  /** Bits consumed so far in the current window */
  consumed: number;
  /** Remaining budget */
  remaining: number;
  /** Current instantaneous leak rate (bits per query) */
  currentRate: number;
  /** Whether the budget is exhausted */
  exhausted: boolean;
  /** Fraction of budget consumed [0, 1] */
  pressure: number;
}

/**
 * Semantic nullification directive.
 */
export interface NullificationDirective {
  /** Whether to apply nullification */
  active: boolean;
  /** Nullification strength [0, 1] — 0 = full signal, 1 = pure noise */
  strength: number;
  /** Entropy to inject (bits) */
  entropyInjection: number;
  /** Fraction of true signal to preserve [0, 1] */
  signalRetention: number;
  /** Reason code for audit trail */
  reason: string;
}

/**
 * Full entropy surface assessment.
 */
export interface EntropySurfaceAssessment {
  probing: ProbingSignature;
  leakage: LeakageBudget;
  nullification: NullificationDirective;
  /** Distance to entropy surface boundary in hyperspace */
  surfaceDistance: number;
  /** Overall defense posture */
  posture: 'TRANSPARENT' | 'GUARDED' | 'OPAQUE' | 'SILENT';
}

/**
 * A query observation for the entropy surface tracker.
 */
export interface QueryObservation {
  /** Input position in 6D Poincaré space */
  position: Vector6D;
  /** Timestamp in milliseconds */
  timestamp: number;
  /** Estimated mutual information of the response (bits) */
  responseMI: number;
}

/**
 * Configuration for the entropy surface defense.
 */
export interface EntropySurfaceConfig {
  /** Total leakage budget in bits (default: 128) */
  leakageBudgetBits: number;
  /** Sliding window size for rate computation (default: 50) */
  windowSize: number;
  /** Probing confidence threshold for AMBIGUOUS (default: 0.3) */
  probingThresholdLow: number;
  /** Probing confidence threshold for PROBING (default: 0.6) */
  probingThresholdHigh: number;
  /** Sigmoid steepness for signal gating (default: 10) */
  sigmoidK: number;
  /** Temporal regularity detection threshold in ms (default: 50) */
  timingJitterThreshold: number;
  /** Coverage breadth: minimum distinct bins to be "exploring" (default: 0.4) */
  coverageThreshold: number;
  /** Repetition distance threshold in hyperbolic space (default: 0.1) */
  repetitionDistThreshold: number;
}

export const DEFAULT_ENTROPY_SURFACE_CONFIG: Readonly<EntropySurfaceConfig> = {
  leakageBudgetBits: 128,
  windowSize: 50,
  probingThresholdLow: 0.3,
  probingThresholdHigh: 0.6,
  sigmoidK: 10,
  timingJitterThreshold: 50,
  coverageThreshold: 0.4,
  repetitionDistThreshold: 0.1,
};

// ═══════════════════════════════════════════════════════════════
// 1. Probing Detection
// ═══════════════════════════════════════════════════════════════

/**
 * Compute Shannon entropy of a discrete distribution.
 * Returns normalized value in [0, 1].
 */
export function shannonEntropy(counts: number[]): number {
  const total = counts.reduce((a, b) => a + b, 0);
  if (total === 0) return 0;

  let entropy = 0;
  for (const c of counts) {
    if (c > 0) {
      const p = c / total;
      entropy -= p * Math.log2(p);
    }
  }

  const maxEntropy = Math.log2(Math.max(counts.filter((c) => c > 0).length, 1));
  return maxEntropy > 0 ? entropy / maxEntropy : 0;
}

/**
 * Detect temporal regularity in query timing.
 *
 * Machine-generated probes tend to have low variance in inter-query
 * intervals. Human queries have high jitter.
 *
 * @returns Regularity score in [0, 1] — higher = more regular (suspicious)
 */
export function detectTemporalRegularity(
  timestamps: number[],
  jitterThreshold: number = 50
): number {
  if (timestamps.length < 3) return 0;

  const intervals: number[] = [];
  for (let i = 1; i < timestamps.length; i++) {
    intervals.push(timestamps[i] - timestamps[i - 1]);
  }

  // Coefficient of variation: std / mean
  const mean = intervals.reduce((a, b) => a + b, 0) / intervals.length;
  if (mean < EPSILON) return 1; // All at same time = maximally suspicious

  let variance = 0;
  for (const interval of intervals) {
    variance += (interval - mean) ** 2;
  }
  variance /= intervals.length;
  const std = Math.sqrt(variance);

  const cv = std / mean;

  // Low CV = regular timing = suspicious
  // Map CV to [0, 1]: sigmoid centered at jitterThreshold-normalized CV
  const normalizedCV = cv * mean / Math.max(jitterThreshold, 1);
  return 1 / (1 + normalizedCV);
}

/**
 * Compute input-space coverage breadth.
 *
 * Discretizes 6D positions into a grid and measures what fraction
 * of bins have been visited. High coverage = systematic exploration.
 *
 * @returns Coverage in [0, 1]
 */
export function computeCoverageBreadth(
  positions: Vector6D[],
  binCount: number = 5
): number {
  if (positions.length === 0) return 0;

  const visited = new Set<string>();

  for (const pos of positions) {
    const key = pos
      .map((v) => Math.min(binCount - 1, Math.max(0, Math.floor(((v + 1) / 2) * binCount))))
      .join(',');
    visited.add(key);
  }

  const maxBins = Math.pow(binCount, 6);
  return visited.size / maxBins;
}

/**
 * Compute repetition score: fraction of query pairs that are near-duplicates.
 *
 * @returns Score in [0, 1] — higher = more repetitive
 */
export function computeRepetitionScore(
  positions: Vector6D[],
  distThreshold: number = 0.1
): number {
  if (positions.length < 2) return 0;

  let nearPairs = 0;
  let totalPairs = 0;

  for (let i = 0; i < positions.length; i++) {
    for (let j = i + 1; j < positions.length; j++) {
      totalPairs++;
      const d = hyperbolicDistance6D(positions[i], positions[j]);
      if (d < distThreshold) {
        nearPairs++;
      }
    }
  }

  return totalPairs > 0 ? nearPairs / totalPairs : 0;
}

/**
 * Analyze query history to detect adversarial probing.
 *
 * Combines four independent signals:
 * 1. Query distribution entropy (low = structured probing)
 * 2. Temporal regularity (high = automated)
 * 3. Coverage breadth (high = systematic exploration)
 * 4. Repetition (high = resampling for variance estimation)
 *
 * @param observations - Recent query history
 * @param config - Defense configuration
 * @returns ProbingSignature
 */
export function detectProbing(
  observations: QueryObservation[],
  config: EntropySurfaceConfig = DEFAULT_ENTROPY_SURFACE_CONFIG
): ProbingSignature {
  if (observations.length < 2) {
    return {
      queryEntropy: 1,
      temporalRegularity: 0,
      coverageBreadth: 0,
      repetitionScore: 0,
      confidence: 0,
      classification: 'LEGITIMATE',
    };
  }

  const positions = observations.map((o) => o.position);
  const timestamps = observations.map((o) => o.timestamp);

  // 1. Query distribution entropy
  // Discretize positions and count per bin
  const binCount = 5;
  const binCounts = new Map<string, number>();
  for (const pos of positions) {
    const key = pos
      .map((v) => Math.min(binCount - 1, Math.max(0, Math.floor(((v + 1) / 2) * binCount))))
      .join(',');
    binCounts.set(key, (binCounts.get(key) ?? 0) + 1);
  }
  const queryEntropy = shannonEntropy([...binCounts.values()]);

  // 2. Temporal regularity
  const temporalRegularity = detectTemporalRegularity(timestamps, config.timingJitterThreshold);

  // 3. Coverage breadth
  const coverageBreadth = computeCoverageBreadth(positions, binCount);

  // 4. Repetition
  const repetitionScore = computeRepetitionScore(positions, config.repetitionDistThreshold);

  // Composite probing confidence
  // Low entropy + high regularity + high coverage + high repetition = probing
  const entropySignal = 1 - queryEntropy; // Invert: low entropy → high signal
  const confidence = Math.min(
    1,
    0.25 * entropySignal +
    0.25 * temporalRegularity +
    0.25 * Math.min(coverageBreadth / Math.max(config.coverageThreshold, EPSILON), 1) +
    0.25 * repetitionScore
  );

  let classification: ProbingSignature['classification'];
  if (confidence >= config.probingThresholdHigh) {
    classification = 'PROBING';
  } else if (confidence >= config.probingThresholdLow) {
    classification = 'AMBIGUOUS';
  } else {
    classification = 'LEGITIMATE';
  }

  return {
    queryEntropy,
    temporalRegularity,
    coverageBreadth,
    repetitionScore,
    confidence,
    classification,
  };
}

// ═══════════════════════════════════════════════════════════════
// 2. Information Leakage Budget
// ═══════════════════════════════════════════════════════════════

/**
 * Estimate mutual information of a response.
 *
 * Uses the response's distance from the "null response" (uniform/origin)
 * as a proxy for information content. Responses near the origin of
 * the output space carry less information.
 *
 * I(x; y) ≈ log2(1 + d_H(y, 0)) where d_H is hyperbolic distance
 *
 * @param responsePosition - Output position in Poincaré space
 * @returns Estimated mutual information in bits
 */
export function estimateResponseMI(responsePosition: Vector6D): number {
  const origin: Vector6D = [0, 0, 0, 0, 0, 0];
  const dist = hyperbolicDistance6D(responsePosition, origin);
  return Math.log2(1 + dist);
}

/**
 * Compute the current leakage budget state.
 *
 * Tracks cumulative information emitted over a sliding window.
 * A3: Causality — budget consumption is monotonic within each window.
 *
 * @param observations - Query history with response MI estimates
 * @param config - Defense configuration
 * @returns LeakageBudget
 */
export function computeLeakageBudget(
  observations: QueryObservation[],
  config: EntropySurfaceConfig = DEFAULT_ENTROPY_SURFACE_CONFIG
): LeakageBudget {
  const window = observations.slice(-config.windowSize);

  let consumed = 0;
  for (const obs of window) {
    consumed += obs.responseMI;
  }

  const remaining = Math.max(0, config.leakageBudgetBits - consumed);
  const currentRate = window.length > 0 ? consumed / window.length : 0;
  const exhausted = remaining <= 0;
  const pressure = Math.min(1, consumed / Math.max(config.leakageBudgetBits, EPSILON));

  return {
    totalBudget: config.leakageBudgetBits,
    consumed,
    remaining,
    currentRate,
    exhausted,
    pressure,
  };
}

// ═══════════════════════════════════════════════════════════════
// 3. Semantic Nullification
// ═══════════════════════════════════════════════════════════════

/**
 * Sigmoid gating function.
 *
 * Maps probing pressure to signal retention via:
 *   σ(p) = 1 / (1 + e^{k(p - θ)})
 *
 * When probing pressure p exceeds threshold θ, retention drops to ~0.
 * When p is well below θ, retention stays at ~1.
 *
 * @param pressure - Combined probing + leakage pressure [0, 1]
 * @param k - Steepness of the sigmoid (higher = sharper cutoff)
 * @param theta - Threshold center (default: 0.5)
 * @returns Signal retention in [0, 1]
 */
export function sigmoidGate(
  pressure: number,
  k: number = 10,
  theta: number = 0.5
): number {
  return 1 / (1 + Math.exp(k * (pressure - theta)));
}

/**
 * Compute the semantic nullification directive.
 *
 * Determines how much true signal to preserve vs. replace with
 * plausible noise, based on probing detection and leakage budget.
 *
 * The nullified output is:
 *   N(x) = σ · f(x) + (1 - σ) · U
 *
 * where σ is the signal retention, f(x) is the true output,
 * and U is a uniform/maximum-entropy placeholder.
 *
 * @param probing - Probing detection result
 * @param leakage - Leakage budget state
 * @param config - Defense configuration
 * @returns NullificationDirective
 */
export function computeNullification(
  probing: ProbingSignature,
  leakage: LeakageBudget,
  config: EntropySurfaceConfig = DEFAULT_ENTROPY_SURFACE_CONFIG
): NullificationDirective {
  // Combined pressure: max of probing confidence and leakage pressure
  // This ensures either signal alone can trigger nullification
  const pressure = Math.max(probing.confidence, leakage.pressure);

  // Signal retention via sigmoid gate
  const signalRetention = sigmoidGate(pressure, config.sigmoidK);

  // Nullification strength is complement of retention
  const strength = 1 - signalRetention;

  // Entropy injection proportional to nullification strength
  // Maximum injection = remaining budget capacity (don't over-inject)
  const entropyInjection = strength * Math.max(leakage.remaining, 0);

  // Active if strength exceeds minimal threshold
  const active = strength > 0.05;

  // Reason code for audit
  let reason: string;
  if (leakage.exhausted) {
    reason = 'BUDGET_EXHAUSTED';
  } else if (probing.classification === 'PROBING') {
    reason = 'PROBING_DETECTED';
  } else if (probing.classification === 'AMBIGUOUS') {
    reason = 'AMBIGUOUS_INTENT';
  } else if (leakage.pressure > 0.5) {
    reason = 'BUDGET_PRESSURE';
  } else {
    reason = 'NOMINAL';
  }

  return {
    active,
    strength,
    entropyInjection,
    signalRetention,
    reason,
  };
}

// ═══════════════════════════════════════════════════════════════
// 4. Entropy Surface Distance
// ═══════════════════════════════════════════════════════════════

/**
 * Compute distance to the entropy surface boundary.
 *
 * The entropy surface is the manifold in hyperspace where
 * nullification strength transitions from 0 to 1. Points
 * inside the surface (negative distance) receive full signal;
 * points outside (positive distance) receive nullified output.
 *
 * Distance is measured in combined probing-leakage pressure space.
 *
 * @param probing - Probing detection result
 * @param leakage - Leakage budget state
 * @param theta - Surface threshold (default: 0.5)
 * @returns Signed distance (negative = inside safe zone, positive = nullified zone)
 */
export function surfaceDistance(
  probing: ProbingSignature,
  leakage: LeakageBudget,
  theta: number = 0.5
): number {
  const pressure = Math.max(probing.confidence, leakage.pressure);
  return pressure - theta;
}

// ═══════════════════════════════════════════════════════════════
// 5. Unified Assessment
// ═══════════════════════════════════════════════════════════════

/**
 * Perform a full entropy surface defense assessment.
 *
 * Combines probing detection, leakage budget tracking, and
 * semantic nullification into a unified defense posture.
 *
 * @param observations - Query history
 * @param config - Defense configuration
 * @returns EntropySurfaceAssessment
 */
export function assessEntropySurface(
  observations: QueryObservation[],
  config: EntropySurfaceConfig = DEFAULT_ENTROPY_SURFACE_CONFIG
): EntropySurfaceAssessment {
  const probing = detectProbing(observations, config);
  const leakage = computeLeakageBudget(observations, config);
  const nullification = computeNullification(probing, leakage, config);
  const dist = surfaceDistance(probing, leakage);

  // Defense posture
  let posture: EntropySurfaceAssessment['posture'];
  if (nullification.strength > 0.9 || leakage.exhausted) {
    posture = 'SILENT';        // Near-zero information emission
  } else if (nullification.strength > 0.5) {
    posture = 'OPAQUE';        // Heavily degraded output
  } else if (nullification.active) {
    posture = 'GUARDED';       // Partial signal degradation
  } else {
    posture = 'TRANSPARENT';   // Full signal, normal operation
  }

  return {
    probing,
    leakage,
    nullification,
    surfaceDistance: dist,
    posture,
  };
}

// ═══════════════════════════════════════════════════════════════
// 6. Stateful Tracker
// ═══════════════════════════════════════════════════════════════

/**
 * Stateful entropy surface tracker.
 *
 * Maintains a sliding window of query observations and provides
 * real-time assessment of the defense posture. Thread-safe for
 * single-writer, multiple-reader patterns.
 */
export class EntropySurfaceTracker {
  private observations: QueryObservation[] = [];
  private readonly config: EntropySurfaceConfig;
  private _lastAssessment: EntropySurfaceAssessment | null = null;

  constructor(config: Partial<EntropySurfaceConfig> = {}) {
    this.config = { ...DEFAULT_ENTROPY_SURFACE_CONFIG, ...config };
  }

  /**
   * Record a new query observation.
   *
   * @param position - Query position in 6D Poincaré space
   * @param responseMI - Estimated mutual information of the response (bits)
   * @param timestamp - Query timestamp (default: Date.now())
   * @returns Updated assessment
   */
  observe(
    position: Vector6D,
    responseMI: number,
    timestamp: number = Date.now()
  ): EntropySurfaceAssessment {
    this.observations.push({ position, timestamp, responseMI });

    // Trim to 2x window to keep memory bounded but allow coverage analysis
    const maxHistory = this.config.windowSize * 2;
    if (this.observations.length > maxHistory) {
      this.observations = this.observations.slice(-maxHistory);
    }

    this._lastAssessment = assessEntropySurface(this.observations, this.config);
    return this._lastAssessment;
  }

  /** Get the last computed assessment without recording a new observation. */
  get lastAssessment(): EntropySurfaceAssessment | null {
    return this._lastAssessment;
  }

  /** Current number of observations in the window. */
  get observationCount(): number {
    return this.observations.length;
  }

  /** Reset the tracker to initial state. */
  reset(): void {
    this.observations = [];
    this._lastAssessment = null;
  }

  /**
   * Apply nullification to a response vector.
   *
   * Mixes the true response with a uniform (origin) response
   * according to the current nullification strength.
   *
   * N(y) = σ · y + (1 - σ) · 0  =  σ · y
   *
   * In Poincaré space, scaling toward origin reduces information content.
   *
   * @param response - True response vector in 6D
   * @returns Nullified response vector
   */
  nullify(response: Vector6D): Vector6D {
    if (!this._lastAssessment || !this._lastAssessment.nullification.active) {
      return response;
    }

    const sigma = this._lastAssessment.nullification.signalRetention;
    return response.map((v) => v * sigma) as Vector6D;
  }
}
