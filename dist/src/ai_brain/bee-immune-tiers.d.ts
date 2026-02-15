/**
 * @file bee-immune-tiers.ts
 * @module ai_brain/bee-immune-tiers
 * @layer Layer 12, Layer 13, Layer 14
 * @component Bee-Colony Tiered Immune System
 * @version 1.0.0
 * @since 2026-02-08
 *
 * Implements a bee-colony-inspired tiered immune system for AI agents.
 *
 * In a real bee colony, immunity operates across multiple tiers with
 * specialized castes:
 *
 *   Tier 1 (Propolis Barrier) - Passive mathematical boundaries
 *     Like the resinous coating bees build at the hive entrance.
 *     Enforces norm checks, dimension validation, and Poincare boundary.
 *
 *   Tier 2 (Hemocyte Response) - Individual agent immune tracking
 *     Like haemocytes in each bee's hemolymph.
 *     Wraps the existing ImmuneResponseSystem for per-agent suspicion.
 *
 *   Tier 3 (Social Grooming) - Neighbor-based anomaly detection
 *     Like nurse bees inspecting brood for disease.
 *     Agents inspect neighbors, perform "waggle dance" threat reporting.
 *
 *   Tier 4 (Colony Fever) - Global collective response
 *     Like the whole hive raising temperature to kill pathogens.
 *     Colony-wide alarm pheromone shifts ALL detection thresholds.
 *
 * Agent castes (bee-inspired roles):
 *   queen   - Central coordinator, sets global alarm pheromone level
 *   guard   - Entry-point validation, first line of defense
 *   nurse   - Monitors adjacent agents, performs hygienic behavior
 *   forager - Scouts external/new threats, brings intel back
 *   undertaker - Handles expelled/dead agents, cleanup duty
 *   worker  - Default caste, regular agent processing
 */
import { type RiskDecision } from './types.js';
import { ImmuneResponseSystem, type AgentImmuneStatus, type ImmuneConfig } from './immune-response.js';
/**
 * Agent caste determines its role in the colony immune system.
 *
 * - queen: Central coordinator (one per hive). Sets alarm pheromone level.
 * - guard: Entry validation. Checks agents at the "hive entrance" (system boundary).
 * - nurse: Inspects adjacent agents for anomalies. Reports via waggle dance.
 * - forager: Scouts external environments. Brings back threat intelligence.
 * - undertaker: Removes expelled agents, cleans up resources.
 * - worker: Default role. Processes tasks normally.
 */
export type AgentCaste = 'queen' | 'guard' | 'nurse' | 'forager' | 'undertaker' | 'worker';
/**
 * Caste capabilities and responsibilities
 */
export interface CasteProfile {
    /** Caste identifier */
    caste: AgentCaste;
    /** Trust multiplier (queen and guards get higher innate trust) */
    trustMultiplier: number;
    /** Inspection range (how many neighbors this caste can inspect) */
    inspectionRange: number;
    /** Whether this caste can trigger colony fever */
    canTriggerFever: boolean;
    /** Whether this caste can release agents from quarantine */
    canRelease: boolean;
    /** Whether this caste can expel agents */
    canExpel: boolean;
    /** Pheromone production rate (how loudly this caste signals threats) */
    pheromoneRate: number;
}
/**
 * Default caste profiles
 */
export declare const CASTE_PROFILES: Record<AgentCaste, CasteProfile>;
/**
 * A "waggle dance" encodes threat intelligence from one agent to the colony.
 *
 * In real bees, the waggle dance communicates direction, distance, and quality
 * of a food source. Here it communicates:
 * - Which dimensions the threat came from
 * - Threat magnitude
 * - Distance from the hive center (safe origin)
 */
export interface WaggleDance {
    /** Agent that performed the dance */
    dancerId: string;
    /** Caste of the dancer */
    dancerCaste: AgentCaste;
    /** Target agent being reported */
    targetId: string;
    /** Which dimensions showed anomaly (indices into 21D state) */
    anomalyDimensions: number[];
    /** Threat magnitude [0, 1] */
    magnitude: number;
    /** Distance from hive center (safe origin) */
    distanceFromCenter: number;
    /** Confidence of the report [0, 1] (weighted by caste) */
    confidence: number;
    /** Timestamp of dance */
    timestamp: number;
    /** Pheromone decay factor (how fast this info fades) */
    decayRate: number;
}
/**
 * Colony pheromone state (global immune posture)
 *
 * The balance between alarm and calm pheromones determines the
 * colony's overall defensive posture.
 */
export interface ColonyPheromoneState {
    /** Alarm pheromone level [0, 1] — triggers heightened vigilance */
    alarm: number;
    /** Calm pheromone (queen mandibular) [0, 1] — stabilization signal */
    calm: number;
    /** Net immune posture [-1, 1] where -1=relaxed, +1=maximum alert */
    posture: number;
    /** Whether colony fever is active */
    feverActive: boolean;
    /** Colony fever temperature multiplier (1.0 = normal, up to 3.0 in fever) */
    feverMultiplier: number;
    /** Number of active waggle dances in the last window */
    activeDances: number;
}
/**
 * Result from a single agent passing through all immune tiers
 */
export interface TieredImmuneResult {
    /** Agent identifier */
    agentId: string;
    /** Agent's assigned caste */
    caste: AgentCaste;
    /** Tier 1: Propolis barrier result */
    propolis: {
        passed: boolean;
        normCheck: boolean;
        dimensionCheck: boolean;
        boundaryDistance: number;
    };
    /** Tier 2: Hemocyte (individual immune) result */
    hemocyte: AgentImmuneStatus;
    /** Tier 3: Social grooming result */
    grooming: {
        inspectedBy: string[];
        waggleDances: number;
        neighborConsensus: boolean;
        groomingScore: number;
    };
    /** Tier 4: Colony fever modifier */
    colonyFever: {
        feverActive: boolean;
        thresholdShift: number;
        amplifiedSuspicion: number;
    };
    /** Final decision after all tiers */
    finalDecision: RiskDecision;
    /** Effective trust score after all tier modifications */
    effectiveTrust: number;
}
export interface HiveImmuneConfig {
    /** Tier 1: Maximum allowed norm for state vectors */
    maxNorm: number;
    /** Tier 1: Required dimensionality */
    requiredDimensions: number;
    /** Tier 1: Poincare boundary epsilon */
    boundaryEpsilon: number;
    /** Tier 3: Minimum dances needed to affect suspicion */
    minDancesForEffect: number;
    /** Tier 3: Dance decay half-life (in steps) */
    danceDecayHalfLife: number;
    /** Tier 3: Dance confidence weight */
    danceConfidenceWeight: number;
    /** Tier 4: Alarm level that triggers colony fever */
    feverThreshold: number;
    /** Tier 4: Maximum fever multiplier */
    maxFeverMultiplier: number;
    /** Tier 4: Alarm decay rate per step (natural calming) */
    alarmDecayRate: number;
    /** Tier 4: Calm pheromone base level from queen */
    queenCalmBase: number;
    /** How many recent dances to keep */
    danceHistorySize: number;
}
export declare const DEFAULT_HIVE_CONFIG: HiveImmuneConfig;
/**
 * Bee-Colony Tiered Immune System
 *
 * Orchestrates four tiers of immune defense, inspired by the layered
 * immunity of a honeybee colony:
 *
 *   Tier 1: Propolis Barrier (passive mathematical filtering)
 *   Tier 2: Hemocyte Response (per-agent suspicion tracking)
 *   Tier 3: Social Grooming (neighbor-based anomaly detection)
 *   Tier 4: Colony Fever (global threshold adjustment)
 *
 * Each agent is assigned a caste that determines its role and
 * capabilities within the colony.
 */
export declare class HiveImmuneSystem {
    private readonly config;
    private readonly hemocytes;
    private readonly agentCastes;
    private dances;
    private pheromone;
    private stepCounter;
    constructor(config?: Partial<HiveImmuneConfig>, immuneConfig?: Partial<ImmuneConfig>);
    /** Assign a caste to an agent */
    assignCaste(agentId: string, caste: AgentCaste): void;
    /** Get an agent's caste (defaults to worker) */
    getCaste(agentId: string): AgentCaste;
    /** Get the caste profile for an agent */
    getCasteProfile(agentId: string): CasteProfile;
    /** Get all agents of a specific caste */
    getAgentsByCaste(caste: AgentCaste): string[];
    /**
     * Check if a state vector passes the propolis barrier.
     * This is the outermost defense — pure mathematical validation.
     *
     * @param state - The 21D state vector to validate
     * @returns Propolis check result
     */
    checkPropolis(state: number[]): TieredImmuneResult['propolis'];
    /**
     * Perform a waggle dance to report a threat.
     *
     * Any agent can dance, but the confidence is weighted by caste:
     * - Queen: 2.0x confidence (strongest signal)
     * - Guard: 1.5x
     * - Nurse: 1.0x
     * - Forager: 1.2x (good intelligence)
     * - Worker: 0.3x (weakest signal)
     */
    performWaggleDance(dancerId: string, targetId: string, anomalyDimensions: number[], magnitude: number, distanceFromCenter: number): WaggleDance;
    /**
     * Get all active (non-decayed) dances targeting a specific agent.
     */
    getActiveDancesFor(targetId: string): WaggleDance[];
    /**
     * Compute the social grooming score for an agent.
     * This aggregates all waggle dances targeting this agent,
     * weighted by confidence and decay.
     */
    computeGroomingScore(targetId: string): {
        inspectedBy: string[];
        waggleDances: number;
        neighborConsensus: boolean;
        groomingScore: number;
    };
    /**
     * Update the colony pheromone state and check for fever.
     *
     * Colony fever activates when alarm pheromone exceeds the threshold.
     * During fever, ALL detection thresholds are amplified (like bees
     * collectively raising hive temperature to kill pathogens).
     */
    updateColonyState(): ColonyPheromoneState;
    /**
     * Get the current colony pheromone state
     */
    getPheromoneState(): ColonyPheromoneState;
    /**
     * Process an agent through all four immune tiers.
     *
     * @param agentId - Agent to assess
     * @param state21D - Agent's 21D state vector
     * @param combinedScore - Detection combined score [0, 1]
     * @param flagCount - Number of detection mechanisms that flagged
     * @returns Complete tiered immune result
     */
    assess(agentId: string, state21D: number[], combinedScore: number, flagCount: number): TieredImmuneResult;
    /** Get the underlying hemocyte system */
    getHemocytes(): ImmuneResponseSystem;
    /** Get all waggle dances */
    getDances(): ReadonlyArray<WaggleDance>;
    /** Get colony statistics */
    getStats(): {
        totalAgents: number;
        casteCounts: Record<AgentCaste, number>;
        pheromone: ColonyPheromoneState;
        activeDances: number;
        hemocyteStats: ReturnType<ImmuneResponseSystem['getStats']>;
        step: number;
    };
    /** Reset the entire hive immune state */
    reset(): void;
}
//# sourceMappingURL=bee-immune-tiers.d.ts.map