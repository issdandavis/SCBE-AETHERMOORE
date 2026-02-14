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
/** The five temporal phase types */
export declare enum TPhaseType {
    /** Inference steps, tool calls — catches instant anomalies */
    FAST = "fast",
    /** Conversation turns, session ticks — tracks session drift */
    MEMORY = "memory",
    /** Epochs, deployment cycles — slow trust evolution over days */
    GOVERNANCE = "governance",
    /** Periodic day/night — realm contraction/expansion rhythm */
    CIRCADIAN = "circadian",
    /** External context injection — punctuated equilibrium events */
    SET = "set"
}
/** Configuration for a single T-phase clock */
export interface TPhaseConfig {
    /** Decay rate per tick (0-1, how fast old intent fades on this clock) */
    decayRate: number;
    /** Breathing amplitude for this phase (0 = no breathing) */
    breathAmplitude: number;
    /** Breathing period in ticks (for circadian: maps to day/night cycle) */
    breathPeriod: number;
    /** Tongue affinity weights during this phase [KO, AV, RU, CA, DR, UM] */
    tongueAffinity: [number, number, number, number, number, number];
}
/** Default configurations for each T-phase */
export declare const DEFAULT_PHASE_CONFIGS: Record<TPhaseType, TPhaseConfig>;
/** State of a single T-phase clock */
export interface TPhaseClockState {
    type: TPhaseType;
    /** Current tick counter for this clock */
    tick: number;
    /** Accumulated intent on this clock's timescale */
    accumulatedIntent: number;
    /** Trust score on this clock's timescale */
    trustScore: number;
    /** Current breathing factor b(t) for this phase */
    breathingFactor: number;
    /** History of recent intent values on this clock (for triadic windowing) */
    intentWindow: number[];
    /** Whether this clock is active */
    active: boolean;
}
/**
 * Create a fresh clock state for a T-phase.
 */
export declare function createClock(type: TPhaseType): TPhaseClockState;
/**
 * Compute breathing factor for a T-phase clock.
 *
 * b(t) = 1 + A · sin(2π · tick / period)
 *
 * Controls realm expansion/contraction on this clock's timescale.
 */
export declare function computeBreathingFactor(tick: number, config: TPhaseConfig): number;
/**
 * Compute circadian tongue affinity based on phase position.
 *
 * Day (tick near 0, period/2): favor interactive tongues (KO, AV, RU)
 * Night (tick near period/2): favor maintenance tongues (CA, DR, UM)
 *
 * Returns weights in [0.5, 1.5] — modulates, never zeroes out.
 */
export declare function circadianTongueAffinity(tick: number, period: number): [number, number, number, number, number, number];
/**
 * Advance a clock by one tick with a new intent observation.
 * Returns a new clock state (immutable).
 *
 * @param clock — Current clock state
 * @param rawIntent — Raw intent value for this tick (from computeRawIntent)
 * @param config — Phase configuration
 */
export declare function tickClock(clock: TPhaseClockState, rawIntent: number, config?: TPhaseConfig): TPhaseClockState;
/** Context event types for T_set injection */
export declare enum ContextEventType {
    /** Deploy event: decay all trust by factor */
    DEPLOY = "deploy",
    /** Security alert: spike breathing, contract realms */
    SECURITY_ALERT = "security_alert",
    /** Manual reset: restart a specific clock */
    RESET = "reset",
    /** Probation: force trust to a low value */
    PROBATION = "probation"
}
/** A context injection event */
export interface ContextEvent {
    type: ContextEventType;
    /** Which clocks to affect (empty = all) */
    targetClocks: TPhaseType[];
    /** Multiplicative trust decay (0-1); e.g., 0.5 = halve all trust */
    trustDecay?: number;
    /** Override breathing factor temporarily */
    breathingOverride?: number;
}
/**
 * Apply a context event (T_set) to a clock.
 * Returns a new clock state (immutable).
 */
export declare function applyContextEvent(clock: TPhaseClockState, event: ContextEvent): TPhaseClockState;
/** Complete multi-clock state for one agent */
export interface MultiClockState {
    agentId: string;
    clocks: Record<TPhaseType, TPhaseClockState>;
}
/**
 * Create a fresh multi-clock system for an agent.
 */
export declare function createMultiClock(agentId: string): MultiClockState;
/**
 * Tick a specific clock in the multi-clock system.
 * Returns a new MultiClockState (immutable).
 */
export declare function tickPhase(state: MultiClockState, phase: TPhaseType, rawIntent: number, config?: TPhaseConfig): MultiClockState;
/**
 * Tick multiple clocks simultaneously with the same intent observation.
 * Typically called with [FAST, MEMORY] on each inference step, and
 * GOVERNANCE on epoch boundaries.
 */
export declare function tickPhases(state: MultiClockState, phases: TPhaseType[], rawIntent: number): MultiClockState;
/**
 * Apply a context event to the multi-clock system.
 */
export declare function injectContext(state: MultiClockState, event: ContextEvent): MultiClockState;
/** Risk profile across all T-phases */
export interface MultiPhaseRisk {
    /** Per-phase accumulated intent */
    phaseIntents: Record<TPhaseType, number>;
    /** Per-phase trust scores */
    phaseTrust: Record<TPhaseType, number>;
    /** Triadic risk: aggregation of fast + memory + governance */
    triadicRisk: number;
    /** Combined x-factor across all phases (for H_eff) */
    combinedXFactor: number;
    /** Circadian tongue affinity at current tick */
    tongueAffinity: [number, number, number, number, number, number];
    /** Active breathing factor (from circadian clock) */
    breathingFactor: number;
    /** Strictest decision across all phases */
    decision: 'ALLOW' | 'QUARANTINE' | 'DENY' | 'EXILE';
}
/**
 * Compute triadic risk from three T-phase windows.
 *
 * d_tri = (λ₁·I_fast^φ + λ₂·I_memory^φ + λ₃·I_governance^φ)^(1/φ)
 *
 * Uses golden-ratio exponents so no single timescale can be zeroed out.
 */
export declare function triadicRisk(iFast: number, iMemory: number, iGovernance: number, lambda1?: number, lambda2?: number, lambda3?: number): number;
/**
 * Compute combined x-factor from all clocks.
 *
 * x = 0.5 + 0.15·triadic + 0.1·I_circadian
 *     × (1 + (1 - min_trust))
 *
 * Capped at 3.0. The minimum trust across all clocks amplifies x.
 */
export declare function combinedXFactor(state: MultiClockState): number;
/**
 * Compute the full multi-phase risk profile.
 */
export declare function computeMultiPhaseRisk(state: MultiClockState): MultiPhaseRisk;
//# sourceMappingURL=temporalPhase.d.ts.map