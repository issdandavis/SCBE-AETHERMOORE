/**
 * @file unified-kernel.ts
 * @module ai_brain/unified-kernel
 * @layer Layer 1-14 (Unified Spine)
 * @component Canonical State + Pipeline Runner
 * @version 1.0.0
 * @since 2026-02-08
 *
 * The unified kernel/spine that ties all SCBE-AETHERMOORE subsystems
 * into one coherent runtime architecture.
 *
 * Architecture:
 *   1. Canonical State: Single truth struct (B^n × T^k product manifold)
 *   2. Module Contracts: Hard interfaces for each subsystem
 *   3. Pipeline Runner: 9-step runtime loop orchestrating all modules
 *
 * Modules:
 *   A. PHDM (AetherBrain) → Deterministic Controller
 *   B. SCBE 14-Layer → Metric/Telemetry Engine
 *   C. Dual-Lattice → Structure + Runtime Transform
 *   D. Spiralverse Torus → Write Gate + Recall Index
 *   E. HYDRA → Distributed Ordering + Multi-Agent Coordination
 *
 * The runtime loop:
 *   1. Propose (candidate action)
 *   2. Score (SCBE metrics)
 *   3. Transform topology (Dual-Lattice phason response)
 *   4. Decide (PHDM controller gate)
 *   5. Execute (if ALLOW/TRANSFORM)
 *   6. Memory write attempt (Torus gate)
 *   7. Penalty & breathing (flux contraction, stutter)
 *   8. Audit (hashchain seal)
 *   9. Broadcast (HYDRA ordering, if swarm)
 */
import { type CombinedAssessment } from './types.js';
import { type PHDMMonitorResult, type PHDMCoreConfig, PHDMCore } from './phdm-core.js';
import { type FluxState, type FluxConfig, FluxStateManager } from './flux-states.js';
import { type ImmuneState, ImmuneResponseSystem } from './immune-response.js';
import { type DualLatticeResult, type DualLatticeConfig, DualLatticeSystem } from './dual-lattice.js';
import { type DualTernarySpectrum, type DualTernaryConfig, DualTernarySystem } from './dual-ternary.js';
import { BrainAuditLogger } from './audit.js';
/**
 * Torus coordinates for cyclic memory/time/context.
 * Lives on T^k (k-dimensional torus).
 */
export interface TorusCoordinates {
    /** Domain/topic angle [0, 2π) */
    readonly theta: number;
    /** Sequence/time angle [0, 2π) — monotone rotation */
    readonly phi: number;
    /** Polarity angle [0, 2π) */
    readonly rho: number;
    /** Authority class angle [0, 2π) */
    readonly sigma: number;
}
/**
 * Penalty state for governance enforcement.
 */
export interface PenaltyState {
    /** Consecutive failure count */
    failCount: number;
    /** Time dilation delay (stutter factor, 1.0 = normal) */
    tauDelay: number;
    /** Timestamp of last penalty application */
    lastPenaltyAt: number;
    /** Accumulated snap events (torus write rejections) */
    snapCount: number;
}
/**
 * The canonical state object: everything plugs into this.
 *
 * Product manifold: B^n × T^k
 *   - Governance lives in B^n (hyperbolic Poincaré ball)
 *   - Memory recurrence lives in T^k (torus)
 *
 * Every module reads/writes through this struct.
 */
export interface CanonicalState {
    /** Agent identifier */
    readonly agentId: string;
    /** Timestamp step counter */
    step: number;
    /** Hyperbolic governance position (21D brain state in Poincaré ball) */
    hyp: number[];
    /** Torus coordinates for cyclic memory */
    torus: TorusCoordinates;
    /** Fractional dimension flux [0, 1] */
    flux: number;
    /** Current flux state tier */
    fluxState: FluxState;
    /** Dual lattice state snapshot */
    lattice: {
        /** Last static projection acceptance */
        staticAccepted: boolean;
        /** Last dynamic displacement */
        dynamicDisplacement: number;
        /** Cross-verification coherence */
        coherence: number;
        /** Whether dual lattice validated this step */
        validated: boolean;
    };
    /** Object-capability tokens / scopes */
    capabilities: Set<string>;
    /** Tamper-evident audit log anchor (last hash) */
    auditAnchor: string;
    /** Penalty state */
    penalties: PenaltyState;
    /** Immune system state */
    immuneState: ImmuneState;
}
/**
 * A proposed action from the LLM/generator.
 */
export interface ProposedAction {
    /** Action type identifier */
    readonly type: string;
    /** 21D state vector associated with this action */
    readonly stateVector: number[];
    /** Optional metadata */
    readonly meta?: Record<string, unknown>;
}
/**
 * Metric bundle produced by SCBE 14-layer scoring.
 * Produces scores; does NOT decide.
 */
export interface MetricBundle {
    /** Hyperbolic distance from safe center */
    hyperbolicDistance: number;
    /** Phase deviation [0, 1] */
    phaseDeviation: number;
    /** Spectral coherence [0, 1] */
    spectralCoherence: number;
    /** Decimal drift magnitude */
    driftMagnitude: number;
    /** Combined risk score [0, 1] */
    combinedRiskScore: number;
    /** Combined assessment from 5 detection mechanisms */
    assessment: CombinedAssessment;
}
/**
 * Memory event for torus write gate.
 */
export interface MemoryEvent {
    /** Event content hash */
    readonly contentHash: string;
    /** Semantic domain class */
    readonly domain: number;
    /** Sequence number (monotone) */
    readonly sequence: number;
    /** Polarity (+1 affirm, -1 negate, 0 neutral) */
    readonly polarity: number;
    /** Authority level [0, 1] */
    readonly authority: number;
}
/**
 * Result from the torus memory write gate.
 */
export interface MemoryWriteResult {
    /** Whether the event was committed */
    committed: boolean;
    /** Updated torus coordinates (if committed) */
    newTorus: TorusCoordinates;
    /** Whether a snap (contradiction) was detected */
    snap: boolean;
    /** Divergence score if snap occurred */
    divergence: number;
}
/**
 * Kernel decision — the output of the PHDM gate.
 */
export type KernelDecision = 'ALLOW' | 'TRANSFORM' | 'BLOCK';
/**
 * Result of a single pipeline step.
 */
export interface PipelineStepResult {
    /** Step number */
    step: number;
    /** The proposed action that was evaluated */
    action: ProposedAction;
    /** SCBE metric bundle */
    metrics: MetricBundle;
    /** Dual lattice analysis */
    latticeResult: DualLatticeResult;
    /** Dual ternary spectrum */
    ternarySpectrum: DualTernarySpectrum;
    /** Kernel decision */
    decision: KernelDecision;
    /** Memory write result (if action was allowed) */
    memoryResult: MemoryWriteResult | null;
    /** Whether penalties were applied */
    penaltyApplied: boolean;
    /** Updated canonical state */
    state: CanonicalState;
    /** Audit hash for this step */
    auditHash: string;
}
export interface KernelConfig {
    /** PHDM controller config */
    phdm: Partial<PHDMCoreConfig>;
    /** Flux state config */
    flux: Partial<FluxConfig>;
    /** Dual lattice config */
    dualLattice: Partial<DualLatticeConfig>;
    /** Dual ternary config */
    dualTernary: Partial<DualTernaryConfig>;
    /** Risk threshold for BLOCK decision */
    blockThreshold: number;
    /** Risk threshold for TRANSFORM decision */
    transformThreshold: number;
    /** Penalty stutter multiplier per snap */
    stutterMultiplier: number;
    /** Flux contraction per snap event */
    fluxContractionPerSnap: number;
    /** Max stutter delay factor */
    maxStutterDelay: number;
    /** Memory divergence threshold for snap detection */
    snapDivergenceThreshold: number;
    /** Capability tiers based on flux state */
    capabilityTiers: Record<FluxState, string[]>;
}
export declare const DEFAULT_KERNEL_CONFIG: KernelConfig;
/**
 * Torus Write Gate — decides whether a memory event can be committed
 * to the toroidal geometry.
 *
 * Semantic projection for torus coordinates:
 *   θ = domain/topic/predicate class
 *   φ = sequence/time (monotone rotation)
 *   ρ = polarity
 *   σ = authority class
 *
 * On contradiction (high divergence), emits snap=true which triggers
 * PHDM penalties (time dilation / flux contraction).
 */
export declare function torusWriteGate(current: TorusCoordinates, event: MemoryEvent, threshold: number): MemoryWriteResult;
/**
 * Score a proposed action using SCBE 14-layer metrics.
 * Produces scores only — does NOT decide.
 */
export declare function computeMetrics(state: number[], phdmResult: PHDMMonitorResult | null): MetricBundle;
/**
 * The Unified Kernel — single runtime loop that orchestrates
 * all SCBE-AETHERMOORE subsystems.
 *
 * Runtime loop (9 steps):
 *   1. Propose: receive candidate action
 *   2. Score: SCBE metrics (produces scores, doesn't decide)
 *   3. Transform topology: Dual-Lattice phason response
 *   4. Decide: PHDM controller gate
 *   5. Execute: if ALLOW/TRANSFORM
 *   6. Memory write: Torus gate
 *   7. Penalty & breathing: flux contraction, stutter
 *   8. Audit: hashchain seal
 *   9. Broadcast: HYDRA ordering (if swarm)
 */
export declare class UnifiedKernel {
    private readonly config;
    private readonly phdm;
    private readonly fluxManager;
    private readonly immune;
    private readonly dualLattice;
    private readonly dualTernary;
    private readonly auditLogger;
    /** Per-agent canonical states */
    private readonly states;
    /** Ordered event log (HYDRA-compatible) */
    private readonly orderedLog;
    constructor(config?: Partial<KernelConfig>);
    /**
     * Initialize canonical state for an agent.
     */
    initializeAgent(agentId: string, initialState?: number[]): CanonicalState;
    /**
     * Get the current canonical state for an agent.
     */
    getState(agentId: string): CanonicalState | undefined;
    /**
     * Process a proposed action through the full 9-step pipeline.
     *
     * This is the single control loop that uses all parts in the right order.
     */
    processAction(agentId: string, action: ProposedAction, memoryEvent?: MemoryEvent): PipelineStepResult;
    /**
     * The PHDM gate: deterministic decision given (S, action, metrics, lattice).
     *
     * Must be deterministic given the same inputs.
     * Enforces: boundedness, capabilities, barrier functions.
     */
    private gate;
    /**
     * Apply penalties based on decision outcome and memory snaps.
     *
     * On snap or high risk:
     *   - Increase τ_delay (stutter)
     *   - Contract ν (flux shift toward QUASI/DEMI)
     *   - Increment fail count
     */
    private applyPenalties;
    /** Get the ordered event log (HYDRA-compatible). */
    getOrderedLog(): ReadonlyArray<PipelineStepResult>;
    /** Get all agent states. */
    getAllStates(): Map<string, CanonicalState>;
    /** Get the audit logger. */
    getAuditLogger(): BrainAuditLogger;
    /** Get the PHDM core. */
    getPHDM(): PHDMCore;
    /** Get the flux manager. */
    getFluxManager(): FluxStateManager;
    /** Get the immune system. */
    getImmuneSystem(): ImmuneResponseSystem;
    /** Get the dual lattice system. */
    getDualLattice(): DualLatticeSystem;
    /** Get the dual ternary system. */
    getDualTernary(): DualTernarySystem;
    /**
     * Compute a deterministic state hash for HYDRA convergence verification.
     * All agents processing the same ordered events should arrive at the same hash.
     */
    computeStateHash(agentId: string): string;
    /** Reset all state (for testing). */
    reset(): void;
}
//# sourceMappingURL=unified-kernel.d.ts.map