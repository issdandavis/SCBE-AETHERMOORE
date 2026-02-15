/**
 * @file flux-states.ts
 * @module ai_brain/flux-states
 * @layer Layer 6, Layer 8, Layer 13
 * @component PHDM Flux State Management
 * @version 1.0.0
 * @since 2026-02-07
 *
 * Manages PHDM (Polyhedral Hamiltonian Defense Manifold) flux states
 * that control tiered access to the brain manifold.
 *
 * Flux states determine what capabilities an agent has:
 * - POLLY (nu >= 0.8): Full access to all 16 polyhedra, complete cognitive processing
 * - QUASI (0.5 <= nu < 0.8): Partial access, cortex polyhedra restricted
 * - DEMI (0.1 <= nu < 0.5): Minimal access, only core Platonic solids
 * - COLLAPSED (nu < 0.1): Limbic-only, no cognitive processing
 *
 * The flux value (nu) evolves based on agent behavior, trust scores,
 * and immune system state. This creates a dynamic access control system
 * where access rights are earned through demonstrated trustworthiness.
 */
import type { ImmuneState } from './immune-response.js';
/**
 * Dimensional flux state (matches fleet/types.ts DimensionalState)
 */
export type FluxState = 'POLLY' | 'QUASI' | 'DEMI' | 'COLLAPSED';
/**
 * PHDM polyhedron categories and their flux requirements
 */
export interface PolyhedronAccess {
    /** Polyhedron name */
    name: string;
    /** Category (core/cortex/subconscious/cerebellum/connectome) */
    category: PolyhedronCategory;
    /** Minimum flux value required for access */
    minFlux: number;
    /** Cognitive function this polyhedron provides */
    cognitiveFunction: string;
}
export type PolyhedronCategory = 'core' | 'cortex' | 'subconscious' | 'cerebellum' | 'connectome';
/**
 * The 16 canonical polyhedra with their access requirements
 */
export declare const POLYHEDRA: PolyhedronAccess[];
/**
 * Flux evolution configuration
 */
export interface FluxConfig {
    /** Mean reversion rate toward equilibrium */
    meanReversionRate: number;
    /** Equilibrium flux value (based on long-term trust) */
    equilibriumFlux: number;
    /** Oscillation amplitude (sinusoidal breathing) */
    oscillationAmplitude: number;
    /** Oscillation frequency */
    oscillationFrequency: number;
    /** Immune state penalty mapping */
    immunePenalties: Record<ImmuneState, number>;
    /** Trust boost rate (positive reinforcement) */
    trustBoostRate: number;
}
/**
 * Default flux configuration
 */
export declare const DEFAULT_FLUX_CONFIG: FluxConfig;
/**
 * Per-agent flux state record
 */
export interface AgentFluxRecord {
    /** Agent identifier */
    agentId: string;
    /** Current flux value [0, 1] */
    nu: number;
    /** Current flux state */
    state: FluxState;
    /** Accessible polyhedra at current flux level */
    accessiblePolyhedra: string[];
    /** Effective dimensionality (sum of accessible polyhedra vertex counts, normalized) */
    effectiveDimensionality: number;
    /** Flux velocity (rate of change) */
    velocity: number;
    /** Time step counter */
    timeStep: number;
}
/**
 * PHDM Flux State Manager
 *
 * Manages the dimensional flux states for all agents in the brain manifold.
 * Flux values evolve dynamically based on:
 * - Mean reversion toward trust-determined equilibrium
 * - Sinusoidal oscillation (breathing dimension flux)
 * - Immune state penalties
 * - Trust score positive reinforcement
 *
 * Flux evolution follows:
 *   dnu/dt = kappa * (nu_bar - nu) + sigma * sin(Omega * t) - penalty
 */
export declare class FluxStateManager {
    private agents;
    private readonly config;
    constructor(config?: Partial<FluxConfig>);
    /**
     * Initialize or update an agent's flux state.
     *
     * @param agentId - Agent identifier
     * @param initialNu - Initial flux value (default: 0.5)
     * @returns Flux record
     */
    initializeAgent(agentId: string, initialNu?: number): AgentFluxRecord;
    /**
     * Evolve an agent's flux state by one time step.
     *
     * Implements the ODE:
     *   dnu/dt = kappa * (nu_bar - nu) + sigma * sin(Omega * t) - penalty
     *
     * Where:
     * - kappa = mean reversion rate
     * - nu_bar = equilibrium flux (from trust score)
     * - sigma = oscillation amplitude
     * - Omega = oscillation frequency
     * - penalty = immune state penalty
     *
     * @param agentId - Agent to evolve
     * @param trustScore - Current trust score [0, 1]
     * @param immuneState - Current immune state
     * @param dt - Time step size (default: 1)
     * @returns Updated flux record
     */
    evolve(agentId: string, trustScore: number, immuneState: ImmuneState, dt?: number): AgentFluxRecord;
    /**
     * Get the current flux record for an agent
     */
    getAgentFlux(agentId: string): AgentFluxRecord | undefined;
    /**
     * Get all agents in a specific flux state
     */
    getAgentsByState(state: FluxState): AgentFluxRecord[];
    /**
     * Check if an agent can access a specific polyhedron
     */
    canAccess(agentId: string, polyhedronName: string): boolean;
    /**
     * Get the governance capabilities for a flux state
     */
    getCapabilities(state: FluxState): {
        canProcess: boolean;
        canPlan: boolean;
        canCreate: boolean;
        canSelfDiagnose: boolean;
        maxCognitiveLayers: number;
    };
    /**
     * Get summary statistics
     */
    getStats(): {
        total: number;
        byState: Record<FluxState, number>;
        avgFlux: number;
        avgDimensionality: number;
    };
    private nuToState;
    private getAccessiblePolyhedra;
    private computeEffectiveDimensionality;
}
//# sourceMappingURL=flux-states.d.ts.map