/**
 * @file dualRegimeScaling.ts
 * @module harmonic/dualRegimeScaling
 * @layer Layer 5-6 (patrol), Layer 12 (wall)
 * @component Dual-Regime Harmonic Scaling
 * @version 1.0.0
 *
 * Two complementary risk formulas for different governance horizons:
 *
 *   PATROL  H_p(d*, R) = R · π^(φ · d*)
 *     - Constant relative sensitivity: d/dd* ln(H_p) = φ·ln(π) ≈ 1.852
 *     - Baseline at d*=0 is R (always "on watch")
 *     - For Layers 5-6: continuous drift monitoring via Quasi-Dynamo
 *
 *   WALL    H_w(d, R)  = R^(d²)
 *     - Superexponential: d/dd ln(H_w) = 2d·ln(R) (grows with distance)
 *     - Identity at d=0: H_w(0,R) = 1 (zero drift = zero concern)
 *     - For Layer 12: hard governance gating (ALLOW/QUARANTINE/ESCALATE/DENY)
 *
 * The crossover distance where patrol sensitivity equals wall sensitivity:
 *   d_cross = φ·ln(π) / (2·ln(R))  ≈ 0.926 for R=e
 *
 * Below d_cross: patrol catches drift the wall ignores.
 * Above d_cross: wall punishes boundary approach superexponentially.
 */

const PHI = (1 + Math.sqrt(5)) / 2;
const LN_PI = Math.log(Math.PI);
const PHI_LN_PI = PHI * LN_PI; // ≈ 1.8522

/** Default scaling base (Euler's number) */
export const R_DEFAULT = Math.E;

/** Perfect Fifth scaling base */
export const R_FIFTH = 1.5;

// ═══════════════════════════════════════════════════════════
// PATROL FORMULA — Layer 5-6 drift monitoring
// ═══════════════════════════════════════════════════════════

/**
 * Patrol scaling: H_p(d*, R) = R · π^(φ · d*)
 *
 * Constant relative sensitivity — equally alarmed by drift at any distance.
 * Starts at R (not 1) at d*=0, meaning it's always "on watch".
 *
 * @param dStar Hyperbolic distance from safe center (d* ≥ 0)
 * @param R    Scaling base (default: e ≈ 2.718)
 * @returns    Risk amplification factor (≥ R)
 */
export function patrolScale(dStar: number, R: number = R_DEFAULT): number {
  const d = Math.max(0, dStar);
  return R * Math.pow(Math.PI, PHI * d);
}

/**
 * Relative sensitivity of patrol: d/dd* ln(H_p) = φ·ln(π) ≈ 1.852
 * Constant everywhere — this is the defining property.
 */
export function patrolSensitivity(): number {
  return PHI_LN_PI;
}

/**
 * Patrol risk amplification: risk' = baseRisk * H_p(d*, R)
 *
 * @param baseRisk Unamplified risk score [0, 1]
 * @param dStar    Hyperbolic distance
 * @param R        Scaling base
 * @returns        Amplified risk (clamped to [0, ∞))
 */
export function patrolAmplify(
  baseRisk: number,
  dStar: number,
  R: number = R_DEFAULT,
): number {
  return Math.max(0, baseRisk) * patrolScale(dStar, R);
}

// ═══════════════════════════════════════════════════════════
// WALL FORMULA — Layer 12 governance gating
// ═══════════════════════════════════════════════════════════

/**
 * Wall scaling: H_w(d, R) = R^(d²)
 *
 * Superexponential — quiet near center, catastrophic at boundary.
 * Identity at d=0: H_w(0,R) = 1 (zero drift = zero concern).
 *
 * @param d  Hyperbolic distance from safe center (d ≥ 0)
 * @param R  Scaling base (default: e ≈ 2.718)
 * @returns  Risk amplification factor (≥ 1)
 */
export function wallScale(d: number, R: number = R_DEFAULT): number {
  const dist = Math.max(0, d);
  return Math.pow(R, dist * dist);
}

/**
 * Relative sensitivity of wall: d/dd ln(H_w) = 2d·ln(R)
 * Grows linearly with distance — the wall gets steeper as you approach.
 *
 * @param d  Distance
 * @param R  Scaling base
 */
export function wallSensitivity(d: number, R: number = R_DEFAULT): number {
  return 2 * Math.max(0, d) * Math.log(R);
}

/**
 * Wall risk amplification: risk' = baseRisk * H_w(d, R)
 *
 * @param baseRisk Unamplified risk score [0, 1]
 * @param d        Hyperbolic distance
 * @param R        Scaling base
 * @returns        Amplified risk
 */
export function wallAmplify(
  baseRisk: number,
  d: number,
  R: number = R_DEFAULT,
): number {
  return Math.max(0, baseRisk) * wallScale(d, R);
}

// ═══════════════════════════════════════════════════════════
// REGIME CROSSOVER
// ═══════════════════════════════════════════════════════════

/**
 * Crossover distance where patrol and wall sensitivities are equal.
 *
 *   φ·ln(π) = 2·d_cross·ln(R)
 *   d_cross = φ·ln(π) / (2·ln(R))
 *
 * Below this: patrol is more sensitive (catches micro-drift).
 * Above this: wall is more sensitive (punishes boundary approach).
 *
 * @param R Scaling base (must be > 1)
 * @returns Crossover distance
 */
export function crossoverDistance(R: number = R_DEFAULT): number {
  const lnR = Math.log(R);
  if (lnR <= 0) {
    return Infinity; // No crossover for R ≤ 1
  }
  return PHI_LN_PI / (2 * lnR);
}

/**
 * Identify the active regime at a given distance.
 *
 * @returns 'patrol' if d < crossover, 'wall' if d ≥ crossover
 */
export function activeRegime(
  d: number,
  R: number = R_DEFAULT,
): 'patrol' | 'wall' {
  return d < crossoverDistance(R) ? 'patrol' : 'wall';
}

// ═══════════════════════════════════════════════════════════
// UNIFIED DUAL-REGIME SCALING
// ═══════════════════════════════════════════════════════════

/**
 * Risk decision tiers (Layer 13).
 */
export type RiskDecision = 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';

export interface DualRegimeResult {
  /** Distance from safe center */
  distance: number;
  /** Active regime */
  regime: 'patrol' | 'wall';
  /** Crossover distance for reference */
  crossover: number;
  /** Patrol-regime amplification factor */
  patrolH: number;
  /** Wall-regime amplification factor */
  wallH: number;
  /** Combined risk amplification (uses active regime) */
  activeH: number;
  /** Amplified risk score */
  amplifiedRisk: number;
  /** Risk decision */
  decision: RiskDecision;
  /** Patrol relative sensitivity (constant) */
  patrolSens: number;
  /** Wall relative sensitivity at this distance */
  wallSens: number;
}

/** Default governance thresholds */
export interface GovernanceThresholds {
  /** Below this: ALLOW */
  allow: number;
  /** Below this: QUARANTINE (above allow) */
  quarantine: number;
  /** Below this: ESCALATE (above quarantine) */
  escalate: number;
  /** Above this: DENY */
  // deny is implicit (≥ escalate)
}

const DEFAULT_THRESHOLDS: GovernanceThresholds = {
  allow: 0.3,
  quarantine: 0.6,
  escalate: 0.85,
};

function classifyRisk(
  amplifiedRisk: number,
  thresholds: GovernanceThresholds,
): RiskDecision {
  if (amplifiedRisk < thresholds.allow) return 'ALLOW';
  if (amplifiedRisk < thresholds.quarantine) return 'QUARANTINE';
  if (amplifiedRisk < thresholds.escalate) return 'ESCALATE';
  return 'DENY';
}

/**
 * Compute dual-regime risk assessment.
 *
 * Uses patrol scaling below the crossover distance (drift monitoring),
 * and wall scaling at/above the crossover (governance gating).
 *
 * The patrol formula starts at R (always watching), while the wall formula
 * has identity at d=0 (dormant until drift begins). The combined system
 * provides continuous coverage: patrol catches micro-drift early, wall
 * enforces hard boundaries.
 *
 * @param baseRisk   Raw risk score [0, 1]
 * @param distance   Hyperbolic distance from safe center
 * @param R          Scaling base (default: e)
 * @param thresholds Governance decision thresholds
 * @returns          Full dual-regime assessment
 */
export function dualRegimeScale(
  baseRisk: number,
  distance: number,
  R: number = R_DEFAULT,
  thresholds: GovernanceThresholds = DEFAULT_THRESHOLDS,
): DualRegimeResult {
  const d = Math.max(0, distance);
  const cross = crossoverDistance(R);
  const regime = d < cross ? 'patrol' : 'wall';

  const pH = patrolScale(d, R);
  const wH = wallScale(d, R);
  const activeH = regime === 'patrol' ? pH : wH;

  const risk = Math.max(0, baseRisk);
  const amplifiedRisk = risk * activeH;

  return {
    distance: d,
    regime,
    crossover: cross,
    patrolH: pH,
    wallH: wH,
    activeH,
    amplifiedRisk,
    decision: classifyRisk(amplifiedRisk, thresholds),
    patrolSens: patrolSensitivity(),
    wallSens: wallSensitivity(d, R),
  };
}

/**
 * Smooth dual-regime scaling using sigmoid blend at crossover.
 *
 * Instead of a hard switch at d_cross, blends patrol and wall with:
 *   σ(x) = 1 / (1 + e^(-k(d - d_cross)))
 *   H_blend = (1 - σ) * H_patrol + σ * H_wall
 *
 * @param d         Distance
 * @param R         Scaling base
 * @param sharpness Sigmoid steepness (higher = sharper transition, default 10)
 */
export function blendedScale(
  d: number,
  R: number = R_DEFAULT,
  sharpness: number = 10,
): number {
  const dist = Math.max(0, d);
  const cross = crossoverDistance(R);
  const sigma = 1 / (1 + Math.exp(-sharpness * (dist - cross)));
  return (1 - sigma) * patrolScale(dist, R) + sigma * wallScale(dist, R);
}

/**
 * Blended risk amplification with smooth regime transition.
 */
export function blendedAmplify(
  baseRisk: number,
  d: number,
  R: number = R_DEFAULT,
  sharpness: number = 10,
): number {
  return Math.max(0, baseRisk) * blendedScale(d, R, sharpness);
}

// ═══════════════════════════════════════════════════════════
// TONGUE-WEIGHTED BRAIDED SCALING
// ═══════════════════════════════════════════════════════════

/** LWS weights (linear — base operations) */
export const LWS_WEIGHTS: Record<string, number> = {
  KO: 1.0,
  AV: 1.125,
  RU: 1.25,
  CA: 1.333,
  UM: 1.5,
  DR: 1.667,
};

/** PHDM weights (φⁿ — crisis/governance scaling) */
export const PHDM_WEIGHTS: Record<string, number> = {
  KO: 1.0,
  AV: PHI,
  RU: PHI ** 2,
  CA: PHI ** 3,
  UM: PHI ** 4,
  DR: PHI ** 5,
};

/** Tongue codes in canonical order */
export const TONGUE_CODES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;
export type TongueCode = (typeof TONGUE_CODES)[number];

/** Per-tongue drift observation */
export interface TongueDrift {
  /** Per-tongue hyperbolic distance from safe center */
  distances: Record<TongueCode, number>;
  /** Optional per-tongue drift velocity (Δd/Δt) from DriftTracker */
  velocities?: Record<TongueCode, number>;
}

/** Tongue-weighted braided scaling result */
export interface BraidedScaleResult {
  /** Per-tongue patrol amplification */
  tonguePatrol: Record<TongueCode, number>;
  /** Per-tongue weighted patrol (patrol * tongue_weight) */
  tongueWeightedPatrol: Record<TongueCode, number>;
  /** Aggregate weighted distance (Langues metric) */
  aggregateDistance: number;
  /** Wall amplification on aggregate distance */
  wallH: number;
  /** Braided combined amplification */
  braidedH: number;
  /** Weight system used */
  weightSystem: 'lws' | 'phdm';
  /** Per-tongue risk decisions */
  tongueDecisions: Record<TongueCode, RiskDecision>;
  /** Aggregate risk decision */
  aggregateDecision: RiskDecision;
  /** Amplified risk (base * braided) */
  amplifiedRisk: number;
  /** Dominant tongue (highest weighted patrol) */
  dominantTongue: TongueCode;
  /** Drift velocity factor (1.0 if no velocities provided) */
  driftVelocityFactor: number;
}

/**
 * Tongue-weighted braided scaling.
 *
 * Combines per-tongue patrol signals with aggregate wall enforcement,
 * braided through Sacred Tongue weights and decimal drift velocities.
 *
 * The braiding formula:
 *   H_braid = α · Σ_tongue(w_tongue · H_patrol(d_tongue)) / Σ(w_tongue)
 *           + (1-α) · H_wall(d_aggregate)
 *
 * where:
 *   α = sigmoid blend based on aggregate distance vs crossover
 *   d_aggregate = √(Σ w_tongue · d_tongue²) (weighted Langues metric)
 *   drift velocities optionally modulate α (faster drift → more wall)
 *
 * @param baseRisk     Raw risk [0, 1]
 * @param tongueDrift  Per-tongue distances (and optional velocities)
 * @param weightSystem 'lws' for base ops, 'phdm' for crisis
 * @param R            Scaling base
 * @param thresholds   Governance thresholds
 */
export function braidedScale(
  baseRisk: number,
  tongueDrift: TongueDrift,
  weightSystem: 'lws' | 'phdm' = 'lws',
  R: number = R_DEFAULT,
  thresholds: GovernanceThresholds = { allow: 0.3, quarantine: 0.6, escalate: 0.85 },
): BraidedScaleResult {
  const weights = weightSystem === 'lws' ? LWS_WEIGHTS : PHDM_WEIGHTS;
  const risk = Math.max(0, baseRisk);

  // Per-tongue patrol
  const tonguePatrol = {} as Record<TongueCode, number>;
  const tongueWeightedPatrol = {} as Record<TongueCode, number>;
  const tongueDecisions = {} as Record<TongueCode, RiskDecision>;

  let weightedPatrolSum = 0;
  let weightSum = 0;
  let weightedDistSqSum = 0;

  for (const tg of TONGUE_CODES) {
    const d = Math.max(0, tongueDrift.distances[tg] ?? 0);
    const w = weights[tg];

    tonguePatrol[tg] = patrolScale(d, R);
    tongueWeightedPatrol[tg] = w * tonguePatrol[tg];
    weightedPatrolSum += tongueWeightedPatrol[tg];
    weightSum += w;

    // Langues metric: weighted squared distances
    weightedDistSqSum += w * d * d;

    // Per-tongue decision (patrol-based)
    const tongueRisk = risk * tonguePatrol[tg];
    tongueDecisions[tg] = classifyRisk(tongueRisk, thresholds);
  }

  // Aggregate weighted distance (Langues metric)
  const aggregateDistance = Math.sqrt(weightedDistSqSum / weightSum);

  // Wall on aggregate
  const wH = wallScale(aggregateDistance, R);

  // Drift velocity factor: faster drift → bias toward wall
  let driftVelocityFactor = 1.0;
  if (tongueDrift.velocities) {
    let maxVel = 0;
    for (const tg of TONGUE_CODES) {
      maxVel = Math.max(maxVel, Math.abs(tongueDrift.velocities[tg] ?? 0));
    }
    // Velocity > 1 biases toward wall, < 1 biases toward patrol
    driftVelocityFactor = 1 + Math.tanh(maxVel - 0.5);
  }

  // Braid: sigmoid blend at crossover, velocity-adjusted
  const cross = crossoverDistance(R);
  const effectiveD = aggregateDistance * driftVelocityFactor;
  const alpha = 1 / (1 + Math.exp(-10 * (effectiveD - cross)));

  // Normalized weighted patrol average
  const avgWeightedPatrol = weightedPatrolSum / weightSum;

  // Braided H: patrol-dominant below crossover, wall-dominant above
  const braidedH = (1 - alpha) * avgWeightedPatrol + alpha * wH;

  const amplifiedRisk = risk * braidedH;

  // Find dominant tongue (highest weighted patrol)
  let dominantTongue: TongueCode = 'KO';
  let maxWeightedPatrol = 0;
  for (const tg of TONGUE_CODES) {
    if (tongueWeightedPatrol[tg] > maxWeightedPatrol) {
      maxWeightedPatrol = tongueWeightedPatrol[tg];
      dominantTongue = tg;
    }
  }

  return {
    tonguePatrol,
    tongueWeightedPatrol,
    aggregateDistance,
    wallH: wH,
    braidedH,
    weightSystem,
    tongueDecisions,
    aggregateDecision: classifyRisk(amplifiedRisk, thresholds),
    amplifiedRisk,
    dominantTongue,
    driftVelocityFactor,
  };
}
