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
/** Harmonic ratio (perfect fifth) */
export declare const R_HARMONIC = 1.5;
/** Intent decay rate per time window (how fast old intent fades) */
export declare const INTENT_DECAY_RATE = 0.95;
/** Time window for intent accumulation (seconds) */
export declare const INTENT_WINDOW_SECONDS = 1;
/** Maximum intent accumulation before hard exile */
export declare const MAX_INTENT_ACCUMULATION = 10;
/** Trust threshold for exile (from AC-2.3.2) */
export declare const TRUST_EXILE_THRESHOLD = 0.3;
/** Consecutive low-trust rounds to trigger exile */
export declare const TRUST_EXILE_ROUNDS = 10;
/** Classification of agent's temporal intent */
export declare enum IntentState {
    /** x < 0.5 — consistently safe */
    BENIGN = "benign",
    /** 0.5 <= x < 1.0 — normal operation */
    NEUTRAL = "neutral",
    /** 1.0 <= x < 2.0 — concerning pattern */
    DRIFTING = "drifting",
    /** x >= 2.0 — sustained adversarial behavior */
    ADVERSARIAL = "adversarial",
    /** Null-space exile triggered */
    EXILED = "exiled"
}
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
export declare function computeDTri(immediate: number, medium: number, long: number): number;
/**
 * Compute raw intent from a single sample using L11 + CPSE metrics.
 *
 * x(t) = f(d_tri(t), chaosdev(t), fractaldev(t), energydev(t))
 */
export declare function computeRawIntent(input: IntentSampleInput): number;
/**
 * Build a full IntentSample from input, computing derived metrics.
 */
export declare function buildSample(input: IntentSampleInput): IntentSample;
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
/**
 * Create a fresh intent history for an agent.
 */
export declare function createIntentHistory(agentId: string, nowMs?: number): IntentHistoryState;
/**
 * Add a sample to intent history, updating accumulation, trust, and state.
 * Returns a new IntentHistoryState (immutable update).
 */
export declare function addSample(history: IntentHistoryState, distance: number, velocity?: number, harmony?: number, nowMs?: number): IntentHistoryState;
/**
 * Compute the x-factor for H(d,R)^x from an intent history.
 *
 * Returns a value typically between 0.5 and 3.0:
 *   - x < 1: Forgiving (brief deviation)
 *   - x = 1: Standard H(d,R)
 *   - x > 1: Compounding (sustained adversarial)
 */
export declare function computeXFactor(history: IntentHistoryState): number;
/**
 * Original Harmonic Wall: H(d, R) = R^(d²)
 */
export declare function harmonicWallBasic(d: number, R?: number): number;
/**
 * Extended Harmonic Wall with temporal intent: H_eff(d, R, x) = R^(d² · x)
 *
 * @param d — Distance from safe operation (0 to ~1 in Poincaré ball)
 * @param x — Intent persistence factor from computeXFactor
 * @param R — Harmonic ratio (default 1.5 = perfect fifth)
 * @returns Security cost multiplier (grows super-exponentially with sustained drift)
 */
export declare function harmonicWallTemporal(d: number, x: number, R?: number): number;
/**
 * Compare basic vs temporal harmonic wall at given distance and intent.
 */
export declare function compareScaling(d: number, x: number): {
    distance: number;
    xFactor: number;
    hBasic: number;
    hTemporal: number;
    amplification: number;
};
/** Decision thresholds from AC-2.3.4 */
export declare const ALLOW_THRESHOLD = 0.85;
export declare const QUARANTINE_THRESHOLD = 0.4;
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
export declare function computeOmega(history: IntentHistoryState, pqcValid?: boolean, triadicStable?: number, spectralScore?: number): OmegaResult;
/**
 * Get full status for an agent's intent history.
 */
export declare function getStatus(history: IntentHistoryState): {
    agentId: string;
    state: string;
    trustScore: number;
    accumulatedIntent: number;
    xFactor: number;
    lowTrustRounds: number;
    sampleCount: number;
    omega: number;
    decision: GateDecision;
};
/** Manages temporal intent histories for multiple agents */
export declare class TemporalSecurityGate {
    private histories;
    /** Get or create intent history for an agent */
    getOrCreate(agentId: string, nowMs?: number): IntentHistoryState;
    /** Record an observation for an agent */
    recordObservation(agentId: string, distance: number, velocity?: number, harmony?: number, nowMs?: number): IntentHistoryState;
    /** Compute Omega decision for an agent */
    computeOmega(agentId: string, pqcValid?: boolean, triadicStable?: number, spectralScore?: number): OmegaResult;
    /** Get full status for an agent */
    getStatus(agentId: string): ReturnType<typeof getStatus>;
    /** Get all tracked agent IDs */
    agentIds(): string[];
    /** Remove an agent's history */
    remove(agentId: string): boolean;
}
//# sourceMappingURL=temporalIntent.d.ts.map