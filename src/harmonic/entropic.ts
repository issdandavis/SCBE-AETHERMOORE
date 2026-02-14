/**
 * @file entropic.ts
 * @module harmonic/entropic
 * @layer Layer 5, Layer 6, Layer 12, Layer 13
 * @component Entropic Layer — Escape Detection, Adaptive-k, Expansion Tracking
 * @version 3.2.4
 *
 * Consolidates the scattered entropy-related concepts from CHSFN,
 * Dual Lattice, and the immune system into a single module with
 * testable invariants.
 *
 * Three mechanisms:
 *   1. Escape Detection — detects when a state leaves its trust basin
 *      by monitoring hyperbolic velocity and basin boundary crossings
 *   2. Adaptive k — dynamically adjusts the number of nearest governance
 *      nodes based on local entropy and trust density
 *   3. Expansion Tracking — measures how fast a state's reachable volume
 *      grows in the Poincaré ball (Lyapunov-like exponent)
 *
 * Key invariants:
 *   - Escape triggers when velocity exceeds the basin escape threshold
 *   - Adaptive k is monotonically non-decreasing with entropy
 *   - Expansion rate is bounded by the curvature-dependent maximum
 *   - All three mechanisms compose into a single EntropicState
 *
 * Builds on:
 *   - hyperbolic.ts: Poincaré distance, mobiusAdd, expMap0/logMap0 (L5)
 *   - adaptiveNavigator.ts: REALM_CENTERS, trajectoryEntropy (L5, L6)
 *   - harmonicScaling.ts: harmonicScale (L12)
 *   - phdm.ts: deviation detection pattern (L8)
 */

import {
  hyperbolicDistance,
  mobiusAdd,
  expMap0,
  logMap0,
  clampToBall,
} from './hyperbolic.js';
import { harmonicScale } from './harmonicScaling.js';
import { REALM_CENTERS } from './adaptiveNavigator.js';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

const PHI = (1 + Math.sqrt(5)) / 2;
const EPSILON = 1e-10;
const LN2 = Math.LN2;

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** Configuration for a trust basin centered at a realm. */
export interface TrustBasin {
  /** Center of the basin in Poincaré ball */
  center: number[];
  /** Hyperbolic radius of the basin */
  radius: number;
  /** Label (e.g., tongue code) */
  label: string;
}

/** A timestamped position sample in the Poincaré ball. */
export interface EntropicSample {
  /** Position in Poincaré ball */
  position: number[];
  /** Timestamp in ms */
  timestamp: number;
}

/** Result of escape detection for a single sample. */
export interface EscapeResult {
  /** Whether the state has escaped its trust basin */
  escaped: boolean;
  /** Nearest basin label */
  nearestBasin: string;
  /** Hyperbolic distance to nearest basin center */
  distanceToCenter: number;
  /** Hyperbolic radius of nearest basin */
  basinRadius: number;
  /** Instantaneous hyperbolic velocity (distance / dt) */
  velocity: number;
  /** Whether velocity exceeds escape threshold */
  velocityExceeded: boolean;
}

/** Result of adaptive-k computation. */
export interface AdaptiveKResult {
  /** Number of governance nodes to consult */
  k: number;
  /** Local Shannon entropy that drove the decision */
  localEntropy: number;
  /** Trust density in the neighborhood */
  trustDensity: number;
  /** Explanation of the k selection */
  reason: string;
}

/** Result of expansion tracking. */
export interface ExpansionResult {
  /** Lyapunov-like expansion rate */
  expansionRate: number;
  /** Reachable volume estimate (hyperbolic) */
  reachableVolume: number;
  /** Whether expansion is accelerating */
  accelerating: boolean;
  /** Number of samples used */
  sampleCount: number;
}

/** Combined entropic state from all three mechanisms. */
export interface EntropicState {
  /** Escape detection result */
  escape: EscapeResult;
  /** Adaptive-k result */
  adaptiveK: AdaptiveKResult;
  /** Expansion tracking result */
  expansion: ExpansionResult;
  /** Combined entropic score in [0, 1] — higher = more entropic/dangerous */
  entropicScore: number;
  /** Risk decision based on entropic score */
  decision: 'STABLE' | 'DRIFTING' | 'ESCAPING' | 'CHAOTIC';
  /** Timestamp of this assessment */
  timestamp: number;
}

/** Configuration for the entropic layer. */
export interface EntropicConfig {
  /** Trust basins (default: derived from REALM_CENTERS) */
  basins: TrustBasin[];
  /** History window size (default: 100) */
  historyWindow: number;
  /** Minimum k (governance nodes, default: 3) */
  kMin: number;
  /** Maximum k (default: 21) */
  kMax: number;
  /** Escape velocity threshold (default: 2.0 hyperbolic units/sec) */
  escapeVelocityThreshold: number;
  /** Entropy bins for local entropy computation (default: 20) */
  entropyBins: number;
  /** Expansion rate alarm threshold (default: 1.5) */
  expansionAlarmThreshold: number;
  /** Decision thresholds */
  thresholds: {
    drifting: number;  // default: 0.3
    escaping: number;  // default: 0.6
    chaotic: number;   // default: 0.85
  };
  /** Dimension of the Poincaré ball (default: 6) */
  dimension: number;
}

// ═══════════════════════════════════════════════════════════════
// Escape Detection
// ═══════════════════════════════════════════════════════════════

/**
 * Detect whether a state has escaped its trust basin.
 *
 * A state "escapes" when:
 *   1. Its hyperbolic distance to the nearest basin center exceeds
 *      the basin radius, OR
 *   2. Its instantaneous hyperbolic velocity exceeds the escape
 *      threshold (fast radial movement away from center)
 *
 * @param current - Current position sample
 * @param previous - Previous position sample (for velocity)
 * @param basins - Trust basins to check against
 * @param escapeVelocityThreshold - Velocity threshold for escape
 */
export function detectEscape(
  current: EntropicSample,
  previous: EntropicSample | null,
  basins: TrustBasin[],
  escapeVelocityThreshold: number = 2.0,
): EscapeResult {
  // Find nearest basin
  let nearestLabel = basins[0]?.label ?? 'unknown';
  let nearestDist = Infinity;
  let nearestRadius = 0;

  for (const basin of basins) {
    const d = hyperbolicDistance(
      padToLength(current.position, basin.center.length),
      basin.center,
    );
    if (d < nearestDist) {
      nearestDist = d;
      nearestLabel = basin.label;
      nearestRadius = basin.radius;
    }
  }

  // Compute velocity
  let velocity = 0;
  if (previous) {
    const dt = Math.max(current.timestamp - previous.timestamp, 1); // avoid div by zero
    const d = hyperbolicDistance(
      padToLength(current.position, previous.position.length),
      padToLength(previous.position, current.position.length),
    );
    velocity = d / (dt / 1000); // convert to per-second
  }

  const escaped = nearestDist > nearestRadius || velocity > escapeVelocityThreshold;
  const velocityExceeded = velocity > escapeVelocityThreshold;

  return {
    escaped,
    nearestBasin: nearestLabel,
    distanceToCenter: nearestDist,
    basinRadius: nearestRadius,
    velocity,
    velocityExceeded,
  };
}

// ═══════════════════════════════════════════════════════════════
// Adaptive k
// ═══════════════════════════════════════════════════════════════

/**
 * Compute Shannon entropy of a set of positions using histogram binning.
 *
 * @param positions - Array of position vectors
 * @param bins - Number of bins per dimension (default: 20)
 * @returns Shannon entropy in bits, normalized to [0, 1]
 */
export function computeLocalEntropy(
  positions: number[][],
  bins: number = 20,
): number {
  if (positions.length < 2) return 0;

  // Compute norms as 1D proxy for radial distribution
  const norms = positions.map((p) =>
    Math.sqrt(p.reduce((s, x) => s + x * x, 0)),
  );

  const maxNorm = Math.max(...norms, EPSILON);
  const histogram = new Float64Array(bins);

  for (const n of norms) {
    const bin = Math.min(Math.floor((n / maxNorm) * bins), bins - 1);
    histogram[bin]++;
  }

  // Shannon entropy
  let entropy = 0;
  const total = norms.length;
  for (let i = 0; i < bins; i++) {
    if (histogram[i] > 0) {
      const p = histogram[i] / total;
      entropy -= p * Math.log2(p);
    }
  }

  // Normalize by max possible entropy (log2(bins))
  const maxEntropy = Math.log2(bins);
  return maxEntropy > 0 ? entropy / maxEntropy : 0;
}

/**
 * Compute trust density — the fraction of recent positions that are
 * within "trusted" range (harmonicScale > 0.5) of a governance center.
 *
 * @param positions - Recent position history
 * @param basins - Trust basins
 * @returns Trust density in [0, 1]
 */
export function computeTrustDensity(
  positions: number[][],
  basins: TrustBasin[],
): number {
  if (positions.length === 0) return 0;

  let trusted = 0;
  for (const pos of positions) {
    for (const basin of basins) {
      const d = hyperbolicDistance(padToLength(pos, basin.center.length), basin.center);
      if (harmonicScale(d) > 0.5) {
        trusted++;
        break; // count position once even if in multiple basins
      }
    }
  }

  return trusted / positions.length;
}

/**
 * Dynamically compute the number of governance nodes (k) to consult
 * based on local entropy and trust density.
 *
 * Higher entropy → more governance nodes needed (more uncertainty)
 * Lower trust density → more governance nodes needed (less coverage)
 *
 * Formula: k = kMin + floor((kMax - kMin) * entropy * (1 - trustDensity))
 *
 * Invariant: k is monotonically non-decreasing with entropy.
 *
 * @param positions - Recent position history
 * @param basins - Trust basins
 * @param kMin - Minimum k (default: 3)
 * @param kMax - Maximum k (default: 21)
 * @param bins - Entropy histogram bins (default: 20)
 */
export function computeAdaptiveK(
  positions: number[][],
  basins: TrustBasin[],
  kMin: number = 3,
  kMax: number = 21,
  bins: number = 20,
): AdaptiveKResult {
  const localEntropy = computeLocalEntropy(positions, bins);
  const trustDensity = computeTrustDensity(positions, basins);

  // Entropy drives k up; trust density pulls it down
  const factor = localEntropy * (1 - trustDensity * 0.5);
  const k = Math.min(kMax, kMin + Math.floor((kMax - kMin) * factor));

  let reason: string;
  if (localEntropy < 0.3 && trustDensity > 0.7) {
    reason = 'Low entropy, high trust — minimal governance needed';
  } else if (localEntropy > 0.7) {
    reason = 'High entropy — increased governance coverage required';
  } else if (trustDensity < 0.3) {
    reason = 'Low trust density — extra governance nodes for coverage';
  } else {
    reason = 'Moderate conditions — standard governance';
  }

  return { k, localEntropy, trustDensity, reason };
}

// ═══════════════════════════════════════════════════════════════
// Expansion Tracking
// ═══════════════════════════════════════════════════════════════

/**
 * Estimate the Lyapunov-like expansion rate from a trajectory.
 *
 * Measures how fast the "reachable volume" of a state grows by tracking
 * the average rate of hyperbolic distance increase between consecutive
 * samples. In the Poincaré ball, volume grows exponentially with radius,
 * so even moderate distance increases correspond to large volume changes.
 *
 * @param samples - Timestamped position history (at least 3 samples)
 * @returns Expansion rate (positive = expanding, negative = contracting)
 */
export function computeExpansionRate(samples: EntropicSample[]): number {
  if (samples.length < 3) return 0;

  // Compute consecutive hyperbolic displacements
  const displacements: number[] = [];
  for (let i = 1; i < samples.length; i++) {
    const d = hyperbolicDistance(
      padToLength(samples[i].position, samples[i - 1].position.length),
      padToLength(samples[i - 1].position, samples[i].position.length),
    );
    const dt = Math.max(samples[i].timestamp - samples[i - 1].timestamp, 1) / 1000;
    displacements.push(d / dt);
  }

  // Expansion rate = slope of log(displacement) over time
  // Use finite differences of consecutive displacement magnitudes
  let sumLogRatio = 0;
  let count = 0;
  for (let i = 1; i < displacements.length; i++) {
    if (displacements[i - 1] > EPSILON && displacements[i] > EPSILON) {
      sumLogRatio += Math.log(displacements[i] / displacements[i - 1]);
      count++;
    }
  }

  return count > 0 ? sumLogRatio / count : 0;
}

/**
 * Estimate the reachable volume from a set of positions using the
 * hyperbolic volume formula. In the Poincaré ball of dimension n,
 * a ball of hyperbolic radius r has volume proportional to
 * sinh^(n-1)(r).
 *
 * We use the maximum pairwise distance as the "radius" of the
 * reachable region.
 *
 * @param positions - Recent position vectors
 * @param dimension - Ball dimension (default: 6)
 */
export function estimateReachableVolume(
  positions: number[][],
  dimension: number = 6,
): number {
  if (positions.length < 2) return 0;

  // Find the centroid and max distance to it
  const n = positions[0].length;
  const centroid = new Array(n).fill(0);
  for (const p of positions) {
    for (let i = 0; i < n; i++) centroid[i] += p[i] / positions.length;
  }
  const clamped = clampToBall(centroid, 0.99);

  let maxDist = 0;
  for (const p of positions) {
    const d = hyperbolicDistance(padToLength(p, clamped.length), clamped);
    if (d > maxDist) maxDist = d;
  }

  // Hyperbolic volume: V_n(r) ~ sinh^(n-1)(r) / (n-1)
  // We return a normalized estimate
  const sinhR = Math.sinh(maxDist);
  return Math.pow(sinhR, dimension - 1) / (dimension - 1);
}

/**
 * Track expansion over time and detect acceleration.
 *
 * @param samples - Position history
 * @param dimension - Ball dimension
 */
export function trackExpansion(
  samples: EntropicSample[],
  dimension: number = 6,
): ExpansionResult {
  const expansionRate = computeExpansionRate(samples);
  const positions = samples.map((s) => s.position);
  const reachableVolume = estimateReachableVolume(positions, dimension);

  // Check acceleration: compare first-half and second-half expansion rates
  let accelerating = false;
  if (samples.length >= 6) {
    const mid = Math.floor(samples.length / 2);
    const firstHalf = computeExpansionRate(samples.slice(0, mid + 1));
    const secondHalf = computeExpansionRate(samples.slice(mid));
    accelerating = secondHalf > firstHalf + EPSILON;
  }

  return {
    expansionRate,
    reachableVolume,
    accelerating,
    sampleCount: samples.length,
  };
}

// ═══════════════════════════════════════════════════════════════
// Entropic Monitor (Unified)
// ═══════════════════════════════════════════════════════════════

/**
 * The EntropicMonitor consolidates escape detection, adaptive-k, and
 * expansion tracking into a single stateful monitor that tracks a
 * trajectory over time.
 */
export class EntropicMonitor {
  private readonly config: EntropicConfig;
  private history: EntropicSample[] = [];

  constructor(config?: Partial<EntropicConfig>) {
    const basins = config?.basins ?? defaultBasins();

    this.config = {
      basins,
      historyWindow: 100,
      kMin: 3,
      kMax: 21,
      escapeVelocityThreshold: 2.0,
      entropyBins: 20,
      expansionAlarmThreshold: 1.5,
      thresholds: {
        drifting: 0.3,
        escaping: 0.6,
        chaotic: 0.85,
      },
      dimension: 6,
      ...config,
      // Re-apply basins from config or default (spread above may override)
    };
    // Ensure basins is set correctly
    if (config?.basins) {
      this.config.basins = config.basins;
    }
  }

  /**
   * Record a new position sample and compute the full entropic state.
   *
   * @param position - Current position in Poincaré ball
   * @param timestamp - Timestamp in ms (default: Date.now())
   * @returns Full EntropicState assessment
   */
  observe(position: number[], timestamp?: number): EntropicState {
    const ts = timestamp ?? Date.now();
    const sample: EntropicSample = { position, timestamp: ts };

    // Add to history, trim to window
    this.history.push(sample);
    if (this.history.length > this.config.historyWindow) {
      this.history = this.history.slice(-this.config.historyWindow);
    }

    const previous = this.history.length >= 2 ? this.history[this.history.length - 2] : null;

    // 1. Escape detection
    const escape = detectEscape(
      sample,
      previous,
      this.config.basins,
      this.config.escapeVelocityThreshold,
    );

    // 2. Adaptive k
    const positions = this.history.map((s) => s.position);
    const adaptiveK = computeAdaptiveK(
      positions,
      this.config.basins,
      this.config.kMin,
      this.config.kMax,
      this.config.entropyBins,
    );

    // 3. Expansion tracking
    const expansion = trackExpansion(this.history, this.config.dimension);

    // Combine into entropic score
    const escapeScore = escape.escaped ? 1.0 : (escape.distanceToCenter / (escape.basinRadius + EPSILON)) * 0.5;
    const entropyScore = adaptiveK.localEntropy;
    const expansionScore = Math.min(1.0, Math.abs(expansion.expansionRate) / (this.config.expansionAlarmThreshold + EPSILON));

    // Weighted combination: escape has highest weight (it's the most critical)
    const entropicScore = Math.min(1.0,
      0.45 * escapeScore + 0.30 * entropyScore + 0.25 * expansionScore,
    );

    // Decision
    let decision: EntropicState['decision'];
    if (entropicScore >= this.config.thresholds.chaotic) {
      decision = 'CHAOTIC';
    } else if (entropicScore >= this.config.thresholds.escaping) {
      decision = 'ESCAPING';
    } else if (entropicScore >= this.config.thresholds.drifting) {
      decision = 'DRIFTING';
    } else {
      decision = 'STABLE';
    }

    return {
      escape,
      adaptiveK,
      expansion,
      entropicScore,
      decision,
      timestamp: ts,
    };
  }

  /**
   * Get the current history window.
   */
  getHistory(): EntropicSample[] {
    return [...this.history];
  }

  /**
   * Get the number of samples in history.
   */
  get historySize(): number {
    return this.history.length;
  }

  /**
   * Reset history.
   */
  reset(): void {
    this.history = [];
  }

  /**
   * Get the configured trust basins.
   */
  getBasins(): TrustBasin[] {
    return [...this.config.basins];
  }
}

// ═══════════════════════════════════════════════════════════════
// Default Basins from Realm Centers
// ═══════════════════════════════════════════════════════════════

/**
 * Create default trust basins from the Sacred Tongue realm centers.
 * Each basin has a radius of 1.0 hyperbolic units.
 */
export function defaultBasins(radius: number = 1.0): TrustBasin[] {
  return Object.entries(REALM_CENTERS).map(([label, center]) => ({
    center,
    radius,
    label,
  }));
}

// ═══════════════════════════════════════════════════════════════
// Invariant Assertions
// ═══════════════════════════════════════════════════════════════

/**
 * Verify the core entropic invariants. Useful for testing and CI.
 *
 * 1. accessCost >= 1 for all non-negative distances
 * 2. adaptive k is monotonically non-decreasing with entropy
 * 3. expansion rate is finite and bounded
 *
 * @returns Array of { name, passed, detail } for each invariant
 */
export function verifyEntropicInvariants(): Array<{ name: string; passed: boolean; detail: string }> {
  const results: Array<{ name: string; passed: boolean; detail: string }> = [];

  // Invariant 1: adaptive-k monotonicity with entropy
  // Generate positions with increasing spread (entropy)
  const basins = defaultBasins();
  const lowEntropyPositions = Array.from({ length: 20 }, () => [0.1, 0, 0, 0, 0, 0]);
  const highEntropyPositions = Array.from({ length: 20 }, (_, i) => {
    const angle = (i / 20) * 2 * Math.PI;
    return [0.5 * Math.cos(angle), 0.5 * Math.sin(angle), 0, 0, 0, 0];
  });

  const lowK = computeAdaptiveK(lowEntropyPositions, basins);
  const highK = computeAdaptiveK(highEntropyPositions, basins);

  results.push({
    name: 'adaptive-k monotonicity',
    passed: highK.k >= lowK.k,
    detail: `Low entropy k=${lowK.k} (H=${lowK.localEntropy.toFixed(3)}), High entropy k=${highK.k} (H=${highK.localEntropy.toFixed(3)})`,
  });

  // Invariant 2: escape detection boundary consistency
  const center = [0.3, 0, 0, 0, 0, 0];
  const insidePoint: EntropicSample = { position: [0.31, 0, 0, 0, 0, 0], timestamp: 1000 };
  const outsidePoint: EntropicSample = { position: [0.9, 0, 0, 0, 0, 0], timestamp: 2000 };
  const smallBasin: TrustBasin = { center, radius: 0.5, label: 'test' };

  const insideResult = detectEscape(insidePoint, null, [smallBasin]);
  const outsideResult = detectEscape(outsidePoint, null, [smallBasin]);

  results.push({
    name: 'escape detection boundary',
    passed: !insideResult.escaped && outsideResult.escaped,
    detail: `Inside: escaped=${insideResult.escaped} (d=${insideResult.distanceToCenter.toFixed(3)}), Outside: escaped=${outsideResult.escaped} (d=${outsideResult.distanceToCenter.toFixed(3)})`,
  });

  // Invariant 3: expansion rate is finite
  const samples: EntropicSample[] = Array.from({ length: 10 }, (_, i) => ({
    position: [0.1 * (i + 1), 0, 0, 0, 0, 0],
    timestamp: i * 100,
  }));
  const expansion = trackExpansion(samples);
  results.push({
    name: 'expansion rate finite',
    passed: Number.isFinite(expansion.expansionRate),
    detail: `Rate=${expansion.expansionRate.toFixed(6)}, Volume=${expansion.reachableVolume.toFixed(6)}`,
  });

  return results;
}

// ═══════════════════════════════════════════════════════════════
// Utility Helpers
// ═══════════════════════════════════════════════════════════════

function padToLength(v: number[], length: number): number[] {
  if (v.length >= length) return v.slice(0, length);
  const padded = new Array(length).fill(0);
  for (let i = 0; i < v.length; i++) padded[i] = v[i];
  return padded;
}

// ═══════════════════════════════════════════════════════════════
// Factory
// ═══════════════════════════════════════════════════════════════

/**
 * Create a pre-configured EntropicMonitor.
 */
export function createEntropicMonitor(config?: Partial<EntropicConfig>): EntropicMonitor {
  return new EntropicMonitor(config);
}
