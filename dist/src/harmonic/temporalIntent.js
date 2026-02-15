"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.TemporalSecurityGate = exports.QUARANTINE_THRESHOLD = exports.ALLOW_THRESHOLD = exports.IntentState = exports.TRUST_EXILE_ROUNDS = exports.TRUST_EXILE_THRESHOLD = exports.MAX_INTENT_ACCUMULATION = exports.INTENT_WINDOW_SECONDS = exports.INTENT_DECAY_RATE = exports.R_HARMONIC = void 0;
exports.computeDTri = computeDTri;
exports.computeRawIntent = computeRawIntent;
exports.buildSample = buildSample;
exports.createIntentHistory = createIntentHistory;
exports.addSample = addSample;
exports.computeXFactor = computeXFactor;
exports.harmonicWallBasic = harmonicWallBasic;
exports.harmonicWallTemporal = harmonicWallTemporal;
exports.compareScaling = compareScaling;
exports.computeOmega = computeOmega;
exports.getStatus = getStatus;
// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
/** Harmonic ratio (perfect fifth) */
exports.R_HARMONIC = 1.5;
/** Intent decay rate per time window (how fast old intent fades) */
exports.INTENT_DECAY_RATE = 0.95;
/** Time window for intent accumulation (seconds) */
exports.INTENT_WINDOW_SECONDS = 1.0;
/** Maximum intent accumulation before hard exile */
exports.MAX_INTENT_ACCUMULATION = 10.0;
/** Trust threshold for exile (from AC-2.3.2) */
exports.TRUST_EXILE_THRESHOLD = 0.3;
/** Consecutive low-trust rounds to trigger exile */
exports.TRUST_EXILE_ROUNDS = 10;
// ═══════════════════════════════════════════════════════════════
// Intent State
// ═══════════════════════════════════════════════════════════════
/** Classification of agent's temporal intent */
var IntentState;
(function (IntentState) {
    /** x < 0.5 — consistently safe */
    IntentState["BENIGN"] = "benign";
    /** 0.5 <= x < 1.0 — normal operation */
    IntentState["NEUTRAL"] = "neutral";
    /** 1.0 <= x < 2.0 — concerning pattern */
    IntentState["DRIFTING"] = "drifting";
    /** x >= 2.0 — sustained adversarial behavior */
    IntentState["ADVERSARIAL"] = "adversarial";
    /** Null-space exile triggered */
    IntentState["EXILED"] = "exiled";
})(IntentState || (exports.IntentState = IntentState = {}));
/**
 * Compute triadic temporal distance (L11) — geometric mean of 3 time scales.
 */
function computeDTri(immediate, medium, long) {
    return Math.cbrt(Math.abs(immediate) * Math.abs(medium) * Math.abs(long));
}
/**
 * Compute raw intent from a single sample using L11 + CPSE metrics.
 *
 * x(t) = f(d_tri(t), chaosdev(t), fractaldev(t), energydev(t))
 */
function computeRawIntent(input) {
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
function buildSample(input) {
    return {
        ...input,
        chaosdev: input.chaosdev ?? 0,
        fractaldev: input.fractaldev ?? 0,
        energydev: input.energydev ?? 0,
        dTriImmediate: input.dTriImmediate ?? 0,
        dTriMedium: input.dTriMedium ?? 0,
        dTriLong: input.dTriLong ?? 0,
        dTri: computeDTri(input.dTriImmediate ?? 0, input.dTriMedium ?? 0, input.dTriLong ?? 0),
        rawIntent: computeRawIntent(input),
    };
}
/** Maximum samples to retain */
const MAX_SAMPLES = 1000;
/**
 * Create a fresh intent history for an agent.
 */
function createIntentHistory(agentId, nowMs) {
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
function addSample(history, distance, velocity = 0, harmony = 0, nowMs) {
    const now = nowMs ?? Date.now();
    const sample = buildSample({
        timestamp: now,
        distance,
        velocity,
        harmony,
    });
    // Append sample (cap at MAX_SAMPLES)
    const samples = history.samples.length >= MAX_SAMPLES
        ? [...history.samples.slice(1), sample]
        : [...history.samples, sample];
    // Apply decay to accumulated intent
    const timeDeltaSec = (now - history.lastUpdateMs) / 1000;
    const decayFactor = Math.pow(exports.INTENT_DECAY_RATE, timeDeltaSec / exports.INTENT_WINDOW_SECONDS);
    let accumulatedIntent = history.accumulatedIntent * decayFactor + sample.rawIntent;
    accumulatedIntent = Math.min(accumulatedIntent, exports.MAX_INTENT_ACCUMULATION);
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
    if (trustScore < exports.TRUST_EXILE_THRESHOLD) {
        lowTrustRounds = lowTrustRounds + 1;
    }
    else {
        lowTrustRounds = 0;
    }
    // Classify intent state
    let state;
    if (lowTrustRounds >= exports.TRUST_EXILE_ROUNDS) {
        state = IntentState.EXILED;
    }
    else if (accumulatedIntent < 0.5) {
        state = IntentState.BENIGN;
    }
    else if (accumulatedIntent < 1.0) {
        state = IntentState.NEUTRAL;
    }
    else if (accumulatedIntent < 2.0) {
        state = IntentState.DRIFTING;
    }
    else {
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
function computeXFactor(history) {
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
function harmonicWallBasic(d, R = exports.R_HARMONIC) {
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
function harmonicWallTemporal(d, x, R = exports.R_HARMONIC) {
    return Math.pow(R, d * d * x);
}
/**
 * Compare basic vs temporal harmonic wall at given distance and intent.
 */
function compareScaling(d, x) {
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
exports.ALLOW_THRESHOLD = 0.85;
exports.QUARANTINE_THRESHOLD = 0.40;
/**
 * Compute Omega decision score using temporal intent scaling.
 *
 * Ω = pqc_valid × harm_score × drift_factor × triadic_stable × spectral_score
 *
 * Where:
 *   harm_score  = 1 / (1 + log(H(d, R)^x))   (inverted: higher = safer)
 *   drift_factor = 1 - accumulated_intent / MAX
 */
function computeOmega(history, pqcValid = true, triadicStable = 1.0, spectralScore = 1.0) {
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
    const d = history.samples.length > 0
        ? history.samples[history.samples.length - 1].distance
        : 0;
    const x = computeXFactor(history);
    const hTemporal = harmonicWallTemporal(d, x);
    // Invert for harm_score (lower H = higher score = safer)
    const harmScore = 1.0 / (1.0 + Math.log(Math.max(1.0, hTemporal)));
    // Drift factor from accumulated intent
    const driftFactor = 1.0 - history.accumulatedIntent / exports.MAX_INTENT_ACCUMULATION;
    // PQC factor
    const pqcFactor = pqcValid ? 1.0 : 0.0;
    // Compute Omega
    const omega = pqcFactor * harmScore * driftFactor * triadicStable * spectralScore;
    // Decision
    let decision;
    if (omega > exports.ALLOW_THRESHOLD) {
        decision = 'ALLOW';
    }
    else if (omega > exports.QUARANTINE_THRESHOLD) {
        decision = 'QUARANTINE';
    }
    else {
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
function getStatus(history) {
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
class TemporalSecurityGate {
    histories = new Map();
    /** Get or create intent history for an agent */
    getOrCreate(agentId, nowMs) {
        let h = this.histories.get(agentId);
        if (!h) {
            h = createIntentHistory(agentId, nowMs);
            this.histories.set(agentId, h);
        }
        return h;
    }
    /** Record an observation for an agent */
    recordObservation(agentId, distance, velocity = 0, harmony = 0, nowMs) {
        const current = this.getOrCreate(agentId, nowMs);
        const updated = addSample(current, distance, velocity, harmony, nowMs);
        this.histories.set(agentId, updated);
        return updated;
    }
    /** Compute Omega decision for an agent */
    computeOmega(agentId, pqcValid, triadicStable, spectralScore) {
        return computeOmega(this.getOrCreate(agentId), pqcValid, triadicStable, spectralScore);
    }
    /** Get full status for an agent */
    getStatus(agentId) {
        return getStatus(this.getOrCreate(agentId));
    }
    /** Get all tracked agent IDs */
    agentIds() {
        return Array.from(this.histories.keys());
    }
    /** Remove an agent's history */
    remove(agentId) {
        return this.histories.delete(agentId);
    }
}
exports.TemporalSecurityGate = TemporalSecurityGate;
//# sourceMappingURL=temporalIntent.js.map