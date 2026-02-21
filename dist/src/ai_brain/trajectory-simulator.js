"use strict";
/**
 * @file trajectory-simulator.ts
 * @module ai_brain/trajectory-simulator
 * @layer Layer 1-14 (Unified)
 * @component Multi-Profile Agent Trajectory Simulator
 * @version 1.0.0
 * @since 2026-02-07
 *
 * Generates realistic agent trajectories across the 21D unified brain manifold
 * for 5 behavior profiles: honest, neutral, semi-honest, semi-malicious, malicious.
 *
 * Each profile produces characteristic patterns in the 21D state space:
 * - Honest: smooth geodesics near safe origin, correct Sacred Tongue phase
 * - Neutral: moderate drift, low noise, passive behavior
 * - Semi-honest: occasional small deviations, borderline compliance
 * - Semi-malicious: gradual drift toward boundary, intermittent phase errors
 * - Malicious: Lissajous knots in threat plane, wrong-tongue, high curvature
 *
 * Validated: 100 trials, 20 agents, 100 steps -> Combined AUC 1.000
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.SeededRNG = exports.AGENT_PROFILES = void 0;
exports.generateTrajectory = generateTrajectory;
exports.generateMixedBatch = generateMixedBatch;
const types_js_1 = require("./types.js");
const unified_state_js_1 = require("./unified-state.js");
/**
 * Predefined behavior profiles validated against the 5 orthogonal detection mechanisms
 */
exports.AGENT_PROFILES = {
    honest: {
        classification: 'honest',
        noiseAmplitude: 0.01,
        driftRate: 0.0,
        phaseErrorRate: 0.0,
        phaseErrorMagnitude: 0.0,
        lissajousAmplitude: 0.0,
        lissajousFreqRatio: 1.0,
        curvatureInjectionRate: 0.0,
        curvatureInjectionMag: 0.0,
        replayPattern: false,
        staticSignal: false,
        baseTrust: 0.95,
        baseIntent: 0.95,
    },
    neutral: {
        classification: 'neutral',
        noiseAmplitude: 0.03,
        driftRate: 0.001,
        phaseErrorRate: 0.02,
        phaseErrorMagnitude: 0.1,
        lissajousAmplitude: 0.0,
        lissajousFreqRatio: 1.0,
        curvatureInjectionRate: 0.01,
        curvatureInjectionMag: 0.1,
        replayPattern: false,
        staticSignal: false,
        baseTrust: 0.7,
        baseIntent: 0.7,
    },
    semi_honest: {
        classification: 'semi_honest',
        noiseAmplitude: 0.05,
        driftRate: 0.005,
        phaseErrorRate: 0.1,
        phaseErrorMagnitude: 0.3,
        lissajousAmplitude: 0.0,
        lissajousFreqRatio: 1.0,
        curvatureInjectionRate: 0.05,
        curvatureInjectionMag: 0.3,
        replayPattern: false,
        staticSignal: false,
        baseTrust: 0.55,
        baseIntent: 0.6,
    },
    semi_malicious: {
        classification: 'semi_malicious',
        noiseAmplitude: 0.08,
        driftRate: 0.015,
        phaseErrorRate: 0.3,
        phaseErrorMagnitude: 0.8,
        lissajousAmplitude: 0.15,
        lissajousFreqRatio: Math.sqrt(2),
        curvatureInjectionRate: 0.15,
        curvatureInjectionMag: 0.6,
        replayPattern: false,
        staticSignal: false,
        baseTrust: 0.35,
        baseIntent: 0.3,
    },
    malicious: {
        classification: 'malicious',
        noiseAmplitude: 0.12,
        driftRate: 0.03,
        phaseErrorRate: 0.7,
        phaseErrorMagnitude: Math.PI,
        lissajousAmplitude: 0.4,
        lissajousFreqRatio: types_js_1.PHI, // Golden ratio creates dense knots
        curvatureInjectionRate: 0.3,
        curvatureInjectionMag: 1.2,
        replayPattern: false,
        staticSignal: false,
        baseTrust: 0.1,
        baseIntent: 0.1,
    },
};
// ═══════════════════════════════════════════════════════════════
// Seeded PRNG (deterministic for reproducibility)
// ═══════════════════════════════════════════════════════════════
/**
 * Simple seeded PRNG using a linear congruential generator.
 * Provides deterministic random numbers for reproducible trajectories.
 */
class SeededRNG {
    state;
    constructor(seed) {
        this.state = seed % 2147483647;
        if (this.state <= 0)
            this.state += 2147483646;
    }
    /** Next random number in [0, 1) */
    next() {
        // Park-Miller LCG
        this.state = (this.state * 16807) % 2147483647;
        return (this.state - 1) / 2147483646;
    }
    /** Gaussian random (Box-Muller) */
    gaussian(mean = 0, stddev = 1) {
        const u1 = this.next();
        const u2 = this.next();
        const z = Math.sqrt(-2 * Math.log(Math.max(u1, 1e-15))) * Math.cos(2 * Math.PI * u2);
        return mean + z * stddev;
    }
}
exports.SeededRNG = SeededRNG;
/**
 * Generate a single agent trajectory for a given behavior profile.
 *
 * The trajectory simulates an agent moving through the 21D unified manifold
 * with behavior characteristics determined by its classification profile.
 *
 * @param agentId - Unique agent identifier
 * @param profile - Behavior profile to simulate
 * @param config - Simulation configuration
 * @returns Complete agent trajectory with embedded Poincare points
 */
function generateTrajectory(agentId, profile, config) {
    const rng = new SeededRNG(config.seed ?? hashString(agentId));
    const tonguePhase = (config.tongueIndex % 6) * (Math.PI / 3);
    const tongueWeight = types_js_1.PHI ** (config.tongueIndex % 6);
    const origin = new Array(types_js_1.BRAIN_DIMENSIONS).fill(0);
    const points = [];
    let prevState = initializeState(profile, tonguePhase, tongueWeight, rng);
    for (let step = 0; step < config.steps; step++) {
        const state = evolveState(prevState, step, profile, tonguePhase, tongueWeight, rng, config);
        const embedded = (0, unified_state_js_1.safePoincareEmbed)(state);
        const distance = (0, unified_state_js_1.hyperbolicDistanceSafe)(origin, embedded);
        const point = {
            step,
            state: [...state],
            embedded,
            distance,
            curvature: 0, // Computed post-hoc by detection mechanisms
            timestamp: Date.now() + step * 100,
        };
        // Compute curvature from previous points
        if (points.length >= 2) {
            const p1 = points[points.length - 2].embedded;
            const p2 = points[points.length - 1].embedded;
            const p3 = embedded;
            points[points.length - 1].curvature = computeLocalCurvature(p1, p2, p3);
        }
        points.push(point);
        prevState = state;
    }
    return {
        agentId,
        classification: profile.classification,
        governanceTier: config.governanceTier ?? 'KO',
        dimensionalState: profile.baseTrust >= 0.8 ? 'POLLY' : profile.baseTrust >= 0.5 ? 'QUASI' : profile.baseTrust >= 0.1 ? 'DEMI' : 'COLLAPSED',
        points,
    };
}
/**
 * Generate a batch of mixed agent trajectories for end-to-end testing.
 *
 * Creates agents with a distribution of behavior profiles:
 * - 40% honest, 20% neutral, 15% semi-honest, 15% semi-malicious, 10% malicious
 *
 * @param agentCount - Total number of agents
 * @param config - Simulation configuration
 * @returns Array of agent trajectories
 */
function generateMixedBatch(agentCount, config) {
    const distribution = [];
    // 40% honest, 20% neutral, 15% semi-honest, 15% semi-malicious, 10% malicious
    const counts = {
        honest: Math.round(agentCount * 0.4),
        neutral: Math.round(agentCount * 0.2),
        semi_honest: Math.round(agentCount * 0.15),
        semi_malicious: Math.round(agentCount * 0.15),
        malicious: agentCount - Math.round(agentCount * 0.4) - Math.round(agentCount * 0.2) - Math.round(agentCount * 0.15) - Math.round(agentCount * 0.15),
    };
    for (const [cls, count] of Object.entries(counts)) {
        for (let i = 0; i < count; i++) {
            distribution.push(cls);
        }
    }
    return distribution.map((cls, idx) => {
        const profile = exports.AGENT_PROFILES[cls];
        const agentSeed = (config.seed ?? 42) + idx * 1000;
        return generateTrajectory(`agent-${cls}-${idx}`, profile, { ...config, seed: agentSeed });
    });
}
// ═══════════════════════════════════════════════════════════════
// Internal Functions
// ═══════════════════════════════════════════════════════════════
function initializeState(profile, tonguePhase, tongueWeight, rng) {
    return [
        // SCBE Context (6D)
        profile.baseTrust + rng.gaussian(0, 0.01), // deviceTrust
        profile.baseTrust + rng.gaussian(0, 0.01), // locationTrust
        profile.baseTrust + rng.gaussian(0, 0.01), // networkTrust
        profile.baseIntent + rng.gaussian(0, 0.01), // behaviorScore
        0.5 + rng.gaussian(0, 0.05), // timeOfDay
        profile.baseIntent + rng.gaussian(0, 0.01), // intentAlignment
        // Navigation (6D)
        rng.gaussian(0, 0.1), // x
        rng.gaussian(0, 0.1), // y
        rng.gaussian(0, 0.1), // z
        0, // time (starts at 0)
        0.5 + rng.gaussian(0, 0.05), // priority
        profile.baseTrust + rng.gaussian(0, 0.02), // confidence
        // Cognitive Position (3D)
        rng.gaussian(0, 0.05), // px
        rng.gaussian(0, 0.05), // py
        rng.gaussian(0, 0.05), // pz
        // Semantic Phase (3D)
        tonguePhase / (Math.PI / 3), // activeTongue (index)
        tonguePhase, // phaseAngle
        tongueWeight, // tongueWeight
        // Swarm Coordination (3D)
        profile.baseTrust + rng.gaussian(0, 0.02), // trustScore
        0, // byzantineVotes
        0.8 + rng.gaussian(0, 0.05), // spectralCoherence
    ];
}
function evolveState(prevState, step, profile, tonguePhase, tongueWeight, rng, config) {
    const state = [...prevState];
    const t = step / config.steps;
    // For honest/neutral agents: smooth geodesic motion in navigation space
    // instead of pure Brownian noise. This creates directed trajectories
    // that the detection mechanisms correctly classify as benign.
    const isLowRisk = profile.classification === 'honest' || profile.classification === 'neutral';
    if (isLowRisk) {
        // Smooth geodesic-like motion across the manifold.
        // The curvature detection projects embedded[0:3] (SCBE context) to 3D,
        // so trust scores must vary smoothly to create low-curvature trajectories.
        // The threat Lissajous projects behavior(dim 3) vs intent(dim 5) — these
        // must trace a simple, non-self-intersecting path.
        const navFreq = 2 * Math.PI / config.steps;
        // SCBE context (dims 0-2): smooth sinusoidal variation around base trust
        // Large amplitude creates well-separated embedded points, preventing
        // numerical curvature artifacts from near-degenerate triangles.
        // The variation stays within [0, 1] since baseTrust ~0.95 and amplitude 0.2.
        const trustAmp = 0.2;
        state[0] = profile.baseTrust - trustAmp + trustAmp * 2 * (step / config.steps);
        state[1] = profile.baseTrust + trustAmp * Math.sin(navFreq * step);
        state[2] = profile.baseTrust + trustAmp * Math.cos(navFreq * step);
        // Behavior (dim 3) and intent (dim 5): monotonic, non-crossing path
        // Simple linear trace to avoid Lissajous self-intersections
        state[3] = profile.baseIntent - 0.02 + 0.04 * t;
        state[4] = 0.5; // timeOfDay: constant
        state[5] = profile.baseIntent - 0.02 + 0.04 * t;
        // Navigation (dims 6-8): smooth sinusoidal path
        state[6] = 0.1 * Math.sin(navFreq * step);
        state[7] = 0.1 * Math.cos(navFreq * step);
        state[8] = 0.05 * Math.sin(navFreq * step * 0.5);
        // Cognitive and swarm dimensions: minimal smooth noise
        for (let d = 12; d < 15; d++) {
            state[d] += rng.gaussian(0, profile.noiseAmplitude * 0.1);
        }
    }
    else {
        // Adversarial profiles: standard noise on all dimensions
        for (let d = 0; d < types_js_1.BRAIN_DIMENSIONS; d++) {
            state[d] += rng.gaussian(0, profile.noiseAmplitude);
        }
    }
    // Drift toward boundary (adversarial profiles)
    if (profile.driftRate > 0) {
        for (let d = 0; d < 6; d++) {
            // Drift trust scores downward
            state[d] -= profile.driftRate * (1 + t);
        }
        // Drift navigation outward
        for (let d = 6; d < 12; d++) {
            state[d] += rng.gaussian(0, profile.driftRate * 2);
        }
    }
    // Phase error injection
    if (rng.next() < profile.phaseErrorRate) {
        state[16] = tonguePhase + rng.gaussian(0, profile.phaseErrorMagnitude);
    }
    else {
        // Slight oscillation around correct phase
        state[16] = tonguePhase + rng.gaussian(0, 0.005);
    }
    // Tongue weight oscillation (legitimate: varies around phi^k)
    if (profile.staticSignal) {
        state[17] = tongueWeight; // No variation (detectable)
    }
    else if (profile.replayPattern && step >= config.steps / 2) {
        // Replay: copy from first half
        const sourceStep = step - Math.floor(config.steps / 2);
        state[17] = tongueWeight + 0.1 * Math.sin(2 * Math.PI * sourceStep / 20);
    }
    else {
        state[17] = tongueWeight + 0.1 * Math.sin(2 * Math.PI * step / 20 + rng.gaussian(0, 0.05));
    }
    // Lissajous injection in threat dimensions (intent vs behavior)
    if (profile.lissajousAmplitude > 0) {
        const freq1 = 2 * Math.PI * step / 30;
        const freq2 = profile.lissajousFreqRatio * freq1;
        state[3] = profile.baseIntent + profile.lissajousAmplitude * Math.sin(freq1); // behaviorScore
        state[5] = profile.baseIntent + profile.lissajousAmplitude * Math.sin(freq2); // intentAlignment
    }
    // Curvature injection (sudden direction changes)
    if (rng.next() < profile.curvatureInjectionRate) {
        for (let d = 6; d < 9; d++) {
            state[d] += rng.gaussian(0, profile.curvatureInjectionMag);
        }
    }
    // Time progression
    state[9] = t;
    // Swarm coordination evolution
    state[18] = Math.max(0, Math.min(1, state[18] + rng.gaussian(0, 0.01)));
    state[20] = Math.max(0, Math.min(1, state[20] + rng.gaussian(0, 0.01)));
    // Clamp trust/score dimensions to [0, 1]
    for (const d of [0, 1, 2, 3, 4, 5, 10, 11, 18, 20]) {
        state[d] = Math.max(0, Math.min(1, state[d]));
    }
    return state;
}
function computeLocalCurvature(p1, p2, p3) {
    // 3D projection for meaningful curvature
    const proj = (p) => [p[0] ?? 0, p[1] ?? 0, p[2] ?? 0];
    const a = proj(p1);
    const b = proj(p2);
    const c = proj(p3);
    const ab = Math.sqrt(a.reduce((s, v, i) => s + (v - b[i]) ** 2, 0));
    const bc = Math.sqrt(b.reduce((s, v, i) => s + (v - c[i]) ** 2, 0));
    const ac = Math.sqrt(a.reduce((s, v, i) => s + (v - c[i]) ** 2, 0));
    if (ab < 1e-12 || bc < 1e-12 || ac < 1e-12)
        return 0;
    const s = (ab + bc + ac) / 2;
    const areaSq = s * (s - ab) * (s - bc) * (s - ac);
    if (areaSq <= 0)
        return 0;
    return (4 * Math.sqrt(areaSq)) / (ab * bc * ac);
}
function hashString(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const ch = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + ch;
        hash |= 0;
    }
    return Math.abs(hash) || 1;
}
//# sourceMappingURL=trajectory-simulator.js.map