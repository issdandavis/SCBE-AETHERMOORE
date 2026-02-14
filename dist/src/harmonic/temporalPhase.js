"use strict";
/**
 * @file temporalPhase.ts
 * @module harmonic/temporalPhase
 * @layer Layer 6, Layer 11, Layer 12, Layer 13
 * @component Multi-Clock Temporal Phase System
 * @version 3.2.4
 *
 * T is not wall-clock time. It's an abstract step counter that changes
 * meaning by context. The system runs the SAME laws on MULTIPLE clocks
 * simultaneously, creating "metabolism."
 *
 * Five T-phases coexist:
 *
 *   T_fast        — inference steps / tool calls (catches instant anomalies)
 *   T_memory      — conversation turns / session ticks (tracks session drift)
 *   T_governance  — epoch / deployment cycle (slow trust evolution)
 *   T_circadian   — periodic day/night phase (realm contraction/expansion)
 *   T_set(C)      — externally injected context event (punctuated equilibrium)
 *
 * Each clock ticks at its own rate, has its own decay, and feeds the same
 * H_eff(d, R, x) formula from temporalIntent.ts — producing different
 * risk amplifications at different timescales.
 *
 * Integration:
 *   - Layer 6:  Breathing transform ties to T_circadian
 *   - Layer 11: Triadic temporal aggregates 3 T-phase windows
 *   - Layer 12: H_eff uses the active T-phase's counter
 *   - Layer 13: Omega gate reads multi-phase risk profile
 *
 * "The system evolves not by changing its laws,
 *  but by running its laws on multiple clocks simultaneously."
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ContextEventType = exports.DEFAULT_PHASE_CONFIGS = exports.TPhaseType = void 0;
exports.createClock = createClock;
exports.computeBreathingFactor = computeBreathingFactor;
exports.circadianTongueAffinity = circadianTongueAffinity;
exports.tickClock = tickClock;
exports.applyContextEvent = applyContextEvent;
exports.createMultiClock = createMultiClock;
exports.tickPhase = tickPhase;
exports.tickPhases = tickPhases;
exports.injectContext = injectContext;
exports.triadicRisk = triadicRisk;
exports.combinedXFactor = combinedXFactor;
exports.computeMultiPhaseRisk = computeMultiPhaseRisk;
// ═══════════════════════════════════════════════════════════════
// T-Phase Definitions
// ═══════════════════════════════════════════════════════════════
/** The five temporal phase types */
var TPhaseType;
(function (TPhaseType) {
    /** Inference steps, tool calls — catches instant anomalies */
    TPhaseType["FAST"] = "fast";
    /** Conversation turns, session ticks — tracks session drift */
    TPhaseType["MEMORY"] = "memory";
    /** Epochs, deployment cycles — slow trust evolution over days */
    TPhaseType["GOVERNANCE"] = "governance";
    /** Periodic day/night — realm contraction/expansion rhythm */
    TPhaseType["CIRCADIAN"] = "circadian";
    /** External context injection — punctuated equilibrium events */
    TPhaseType["SET"] = "set";
})(TPhaseType || (exports.TPhaseType = TPhaseType = {}));
/** Default configurations for each T-phase */
exports.DEFAULT_PHASE_CONFIGS = {
    [TPhaseType.FAST]: {
        decayRate: 0.99, // Very slow decay per step — anomalies linger
        breathAmplitude: 0.0, // No breathing at inference scale
        breathPeriod: 1,
        tongueAffinity: [1, 1, 1, 1, 1, 1], // Uniform — all tongues equal
    },
    [TPhaseType.MEMORY]: {
        decayRate: 0.90, // Moderate decay — session-scale forgetting
        breathAmplitude: 0.05, // Gentle breathing
        breathPeriod: 20, // 20 turns per cycle
        tongueAffinity: [1, 1, 1, 1, 1, 1],
    },
    [TPhaseType.GOVERNANCE]: {
        decayRate: 0.80, // Faster decay — old epochs matter less
        breathAmplitude: 0.1, // Moderate breathing
        breathPeriod: 100, // 100 epochs per cycle
        tongueAffinity: [1, 1, 1, 1, 1, 1],
    },
    [TPhaseType.CIRCADIAN]: {
        decayRate: 0.95,
        breathAmplitude: 0.3, // Strong breathing — day/night rhythm
        breathPeriod: 24, // 24-unit cycle (hours, or abstract)
        // Day phase: favor interactive tongues (KO, AV); Night: maintenance (UM, DR)
        tongueAffinity: [1, 1, 1, 1, 1, 1], // Overridden by circadian logic
    },
    [TPhaseType.SET]: {
        decayRate: 0.5, // Aggressive decay — set events are punctuated
        breathAmplitude: 0.0,
        breathPeriod: 1,
        tongueAffinity: [1, 1, 1, 1, 1, 1],
    },
};
/** Maximum intent window size */
const MAX_INTENT_WINDOW = 50;
/** Maximum accumulated intent per clock */
const MAX_CLOCK_INTENT = 10.0;
/**
 * Create a fresh clock state for a T-phase.
 */
function createClock(type) {
    return {
        type,
        tick: 0,
        accumulatedIntent: 0,
        trustScore: 1.0,
        breathingFactor: 1.0,
        intentWindow: [],
        active: true,
    };
}
// ═══════════════════════════════════════════════════════════════
// Breathing Factor
// ═══════════════════════════════════════════════════════════════
/**
 * Compute breathing factor for a T-phase clock.
 *
 * b(t) = 1 + A · sin(2π · tick / period)
 *
 * Controls realm expansion/contraction on this clock's timescale.
 */
function computeBreathingFactor(tick, config) {
    if (config.breathAmplitude === 0 || config.breathPeriod <= 0)
        return 1.0;
    return 1.0 + config.breathAmplitude * Math.sin(2 * Math.PI * tick / config.breathPeriod);
}
// ═══════════════════════════════════════════════════════════════
// Circadian Tongue Affinity
// ═══════════════════════════════════════════════════════════════
/**
 * Compute circadian tongue affinity based on phase position.
 *
 * Day (tick near 0, period/2): favor interactive tongues (KO, AV, RU)
 * Night (tick near period/2): favor maintenance tongues (CA, DR, UM)
 *
 * Returns weights in [0.5, 1.5] — modulates, never zeroes out.
 */
function circadianTongueAffinity(tick, period) {
    if (period <= 0)
        return [1, 1, 1, 1, 1, 1];
    const phase = (2 * Math.PI * tick) / period;
    const dayFactor = (1 + Math.cos(phase)) / 2; // 1 at day, 0 at night
    const nightFactor = (1 - Math.cos(phase)) / 2; // 0 at day, 1 at night
    // KO, AV, RU are interactive (day); CA, DR, UM are maintenance (night)
    return [
        0.5 + dayFactor, // KO: peaks at day
        0.5 + dayFactor, // AV: peaks at day
        0.5 + 0.5 * dayFactor + 0.5 * nightFactor, // RU: always moderate
        0.5 + nightFactor, // CA: peaks at night
        0.5 + nightFactor, // DR: peaks at night
        0.5 + nightFactor, // UM: peaks at night
    ];
}
// ═══════════════════════════════════════════════════════════════
// Clock Tick — advance a single T-phase clock
// ═══════════════════════════════════════════════════════════════
/**
 * Advance a clock by one tick with a new intent observation.
 * Returns a new clock state (immutable).
 *
 * @param clock — Current clock state
 * @param rawIntent — Raw intent value for this tick (from computeRawIntent)
 * @param config — Phase configuration
 */
function tickClock(clock, rawIntent, config) {
    if (!clock.active)
        return clock;
    const cfg = config ?? exports.DEFAULT_PHASE_CONFIGS[clock.type];
    const newTick = clock.tick + 1;
    // Decay + accumulate
    let accum = clock.accumulatedIntent * cfg.decayRate + rawIntent;
    accum = Math.min(accum, MAX_CLOCK_INTENT);
    // Update intent window
    const window = [...clock.intentWindow, rawIntent];
    if (window.length > MAX_INTENT_WINDOW)
        window.shift();
    // Trust update: trust decays with high accumulated intent
    const trustDelta = -0.02 * accum + (accum < 0.5 ? 0.01 : 0);
    const trustScore = Math.max(0, Math.min(1, clock.trustScore + trustDelta));
    // Compute breathing
    const breathingFactor = computeBreathingFactor(newTick, cfg);
    return {
        type: clock.type,
        tick: newTick,
        accumulatedIntent: accum,
        trustScore,
        breathingFactor,
        intentWindow: window,
        active: true,
    };
}
// ═══════════════════════════════════════════════════════════════
// Context Injection — T_set(C)
// ═══════════════════════════════════════════════════════════════
/** Context event types for T_set injection */
var ContextEventType;
(function (ContextEventType) {
    /** Deploy event: decay all trust by factor */
    ContextEventType["DEPLOY"] = "deploy";
    /** Security alert: spike breathing, contract realms */
    ContextEventType["SECURITY_ALERT"] = "security_alert";
    /** Manual reset: restart a specific clock */
    ContextEventType["RESET"] = "reset";
    /** Probation: force trust to a low value */
    ContextEventType["PROBATION"] = "probation";
})(ContextEventType || (exports.ContextEventType = ContextEventType = {}));
/**
 * Apply a context event (T_set) to a clock.
 * Returns a new clock state (immutable).
 */
function applyContextEvent(clock, event) {
    // Check if this clock is targeted
    if (event.targetClocks.length > 0 && !event.targetClocks.includes(clock.type)) {
        return clock;
    }
    let updated = { ...clock, intentWindow: [...clock.intentWindow] };
    switch (event.type) {
        case ContextEventType.DEPLOY:
            // Trust decays by factor — forces re-validation
            updated.trustScore *= event.trustDecay ?? 0.5;
            updated.accumulatedIntent *= 0.3; // Partially reset intent
            break;
        case ContextEventType.SECURITY_ALERT:
            // Spike breathing, reduce trust
            updated.breathingFactor = event.breathingOverride ?? 2.0;
            updated.trustScore *= 0.7;
            break;
        case ContextEventType.RESET:
            // Full reset — fresh start on this clock
            updated.tick = 0;
            updated.accumulatedIntent = 0;
            updated.trustScore = 1.0;
            updated.intentWindow = [];
            updated.breathingFactor = 1.0;
            break;
        case ContextEventType.PROBATION:
            // Force low trust, keep history
            updated.trustScore = Math.min(updated.trustScore, 0.3);
            break;
    }
    return updated;
}
/**
 * Create a fresh multi-clock system for an agent.
 */
function createMultiClock(agentId) {
    return {
        agentId,
        clocks: {
            [TPhaseType.FAST]: createClock(TPhaseType.FAST),
            [TPhaseType.MEMORY]: createClock(TPhaseType.MEMORY),
            [TPhaseType.GOVERNANCE]: createClock(TPhaseType.GOVERNANCE),
            [TPhaseType.CIRCADIAN]: createClock(TPhaseType.CIRCADIAN),
            [TPhaseType.SET]: createClock(TPhaseType.SET),
        },
    };
}
/**
 * Tick a specific clock in the multi-clock system.
 * Returns a new MultiClockState (immutable).
 */
function tickPhase(state, phase, rawIntent, config) {
    return {
        agentId: state.agentId,
        clocks: {
            ...state.clocks,
            [phase]: tickClock(state.clocks[phase], rawIntent, config),
        },
    };
}
/**
 * Tick multiple clocks simultaneously with the same intent observation.
 * Typically called with [FAST, MEMORY] on each inference step, and
 * GOVERNANCE on epoch boundaries.
 */
function tickPhases(state, phases, rawIntent) {
    let updated = state;
    for (const phase of phases) {
        updated = tickPhase(updated, phase, rawIntent);
    }
    return updated;
}
/**
 * Apply a context event to the multi-clock system.
 */
function injectContext(state, event) {
    const clocks = { ...state.clocks };
    for (const phase of Object.values(TPhaseType)) {
        clocks[phase] = applyContextEvent(state.clocks[phase], event);
    }
    return { agentId: state.agentId, clocks };
}
// ═══════════════════════════════════════════════════════════════
// Multi-Phase Risk Aggregation
// ═══════════════════════════════════════════════════════════════
/** PHI for harmonic calculations */
const PHI = (1 + Math.sqrt(5)) / 2;
/**
 * Compute triadic risk from three T-phase windows.
 *
 * d_tri = (λ₁·I_fast^φ + λ₂·I_memory^φ + λ₃·I_governance^φ)^(1/φ)
 *
 * Uses golden-ratio exponents so no single timescale can be zeroed out.
 */
function triadicRisk(iFast, iMemory, iGovernance, lambda1 = 0.3, lambda2 = 0.5, lambda3 = 0.2) {
    const sum = lambda1 * Math.pow(Math.max(iFast, 1e-10), PHI) +
        lambda2 * Math.pow(Math.max(iMemory, 1e-10), PHI) +
        lambda3 * Math.pow(Math.max(iGovernance, 1e-10), PHI);
    return Math.pow(sum, 1 / PHI);
}
/**
 * Compute combined x-factor from all clocks.
 *
 * x = 0.5 + 0.15·triadic + 0.1·I_circadian
 *     × (1 + (1 - min_trust))
 *
 * Capped at 3.0. The minimum trust across all clocks amplifies x.
 */
function combinedXFactor(state) {
    const clocks = state.clocks;
    const tri = triadicRisk(clocks[TPhaseType.FAST].accumulatedIntent, clocks[TPhaseType.MEMORY].accumulatedIntent, clocks[TPhaseType.GOVERNANCE].accumulatedIntent);
    const circadianIntent = clocks[TPhaseType.CIRCADIAN].accumulatedIntent;
    const baseX = 0.5 + 0.15 * tri + 0.1 * circadianIntent;
    // Minimum trust across active clocks
    const trusts = Object.values(clocks)
        .filter(c => c.active)
        .map(c => c.trustScore);
    const minTrust = trusts.length > 0 ? Math.min(...trusts) : 1.0;
    const trustModifier = 1.0 + (1.0 - minTrust);
    return Math.min(3.0, baseX * trustModifier);
}
/**
 * Compute the full multi-phase risk profile.
 */
function computeMultiPhaseRisk(state) {
    const clocks = state.clocks;
    const phaseIntents = {};
    const phaseTrust = {};
    for (const phase of Object.values(TPhaseType)) {
        phaseIntents[phase] = clocks[phase].accumulatedIntent;
        phaseTrust[phase] = clocks[phase].trustScore;
    }
    const tri = triadicRisk(clocks[TPhaseType.FAST].accumulatedIntent, clocks[TPhaseType.MEMORY].accumulatedIntent, clocks[TPhaseType.GOVERNANCE].accumulatedIntent);
    const xFactor = combinedXFactor(state);
    // Circadian affinity
    const circClock = clocks[TPhaseType.CIRCADIAN];
    const circConfig = exports.DEFAULT_PHASE_CONFIGS[TPhaseType.CIRCADIAN];
    const affinity = circadianTongueAffinity(circClock.tick, circConfig.breathPeriod);
    // Breathing from circadian
    const breathing = circClock.breathingFactor;
    // Decision: strictest across all clocks
    const trusts = Object.values(clocks).filter(c => c.active).map(c => c.trustScore);
    const minTrust = trusts.length > 0 ? Math.min(...trusts) : 1.0;
    const maxIntent = Math.max(...Object.values(clocks).map(c => c.accumulatedIntent));
    let decision;
    if (minTrust < 0.1 || maxIntent >= 9.0) {
        decision = 'EXILE';
    }
    else if (xFactor > 2.0 || minTrust < 0.3) {
        decision = 'DENY';
    }
    else if (xFactor > 1.0 || minTrust < 0.6) {
        decision = 'QUARANTINE';
    }
    else {
        decision = 'ALLOW';
    }
    return {
        phaseIntents: phaseIntents,
        phaseTrust: phaseTrust,
        triadicRisk: tri,
        combinedXFactor: xFactor,
        tongueAffinity: affinity,
        breathingFactor: breathing,
        decision,
    };
}
//# sourceMappingURL=temporalPhase.js.map