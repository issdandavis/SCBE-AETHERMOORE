/**
 * Swarm Coordination System
 *
 * Manages Polly dimensional swarm coordination between agent pads.
 * Implements coherence tracking, synchronization, and flux ODE dynamics.
 *
 * Dimensional States:
 * - POLLY (ν ≈ 1.0): Full swarm participation
 * - QUASI (0.5 < ν < 1): Partial sync
 * - DEMI (0 < ν < 0.5): Minimal connection
 * - COLLAPSED (ν ≈ 0): Disconnected
 *
 * @module fleet/swarm
 */
import { PollyPad, PollyPadManager } from './polly-pad';
import { DimensionalState, GovernanceTier } from './types';
/**
 * Swarm configuration
 */
export interface SwarmConfig {
    /** Swarm identifier */
    id: string;
    /** Swarm name */
    name: string;
    /** Minimum coherence threshold */
    minCoherence: number;
    /** Flux decay rate (per tick) */
    fluxDecayRate: number;
    /** Sync interval ms */
    syncIntervalMs: number;
    /** Maximum pads in swarm */
    maxPads: number;
}
/**
 * Swarm state snapshot
 */
export interface SwarmState {
    id: string;
    name: string;
    /** Pad IDs in this swarm */
    padIds: string[];
    /** Average flux coefficient */
    avgNu: number;
    /** Swarm coherence (0-1) */
    coherence: number;
    /** Dominant dimensional state */
    dominantState: DimensionalState;
    /** Sync timestamp */
    lastSync: number;
    /** Active pad count */
    activePads: number;
    /** Collapsed pad count */
    collapsedPads: number;
}
/**
 * Flux ODE parameters for dimensional dynamics
 * dν/dt = α(ν_target - ν) - β*decay + γ*coherence_boost
 */
export interface FluxODEParams {
    /** Attraction to target (α) */
    alpha: number;
    /** Natural decay rate (β) */
    beta: number;
    /** Coherence boost factor (γ) */
    gamma: number;
    /** Time step (dt) */
    dt: number;
}
/**
 * Default flux ODE parameters
 */
export declare const DEFAULT_FLUX_ODE: FluxODEParams;
/**
 * Swarm Coordinator
 *
 * Manages dimensional flux coordination across agent pads.
 */
export declare class SwarmCoordinator {
    private swarms;
    private swarmPads;
    private padManager;
    private fluxParams;
    private syncIntervals;
    constructor(padManager: PollyPadManager, fluxParams?: FluxODEParams);
    /**
     * Create a new swarm
     */
    createSwarm(config: Omit<SwarmConfig, 'id'> & {
        id?: string;
    }): SwarmConfig;
    /**
     * Get swarm by ID
     */
    getSwarm(id: string): SwarmConfig | undefined;
    /**
     * Get all swarms
     */
    getAllSwarms(): SwarmConfig[];
    /**
     * Add pad to swarm
     */
    addPadToSwarm(swarmId: string, padId: string): boolean;
    /**
     * Remove pad from swarm
     */
    removePadFromSwarm(swarmId: string, padId: string): boolean;
    /**
     * Get pads in swarm
     */
    getSwarmPads(swarmId: string): PollyPad[];
    /**
     * Get swarm state snapshot
     */
    getSwarmState(swarmId: string): SwarmState | undefined;
    /**
     * Synchronize swarm - update coherence scores
     */
    syncSwarm(swarmId: string): void;
    /**
     * Step flux dynamics using ODE
     * dν/dt = α(ν_target - ν) - β*decay + γ*coherence_boost
     */
    stepFluxODE(swarmId: string): void;
    /**
     * Boost pad flux (e.g., after successful task)
     */
    boostPadFlux(padId: string, amount?: number): void;
    /**
     * Decay pad flux (e.g., after failure or inactivity)
     */
    decayPadFlux(padId: string, amount?: number): void;
    /**
     * Collapse pad (set to COLLAPSED state)
     */
    collapsePad(padId: string): void;
    /**
     * Revive collapsed pad
     */
    revivePad(padId: string, targetNu?: number): void;
    /**
     * Start automatic sync for swarm
     */
    startAutoSync(swarmId: string): void;
    /**
     * Stop automatic sync for swarm
     */
    stopAutoSync(swarmId: string): void;
    /**
     * Get swarm statistics
     */
    getSwarmStats(swarmId: string): {
        totalPads: number;
        byState: Record<DimensionalState, number>;
        byTier: Record<GovernanceTier, number>;
        avgCoherence: number;
        avgNu: number;
        healthScore: number;
    } | undefined;
    /**
     * Shutdown coordinator
     */
    shutdown(): void;
}
//# sourceMappingURL=swarm.d.ts.map