/**
 * @file swarm-formation.ts
 * @module ai_brain/swarm-formation
 * @layer Layer 10, Layer 13
 * @component Swarm Formation Coordination
 * @version 1.0.0
 * @since 2026-02-07
 *
 * Implements swarm coordination primitives for multi-agent governance
 * in the unified brain manifold. Agents organize into geometric formations
 * that encode both spatial relationships and trust dynamics.
 *
 * Formation types:
 * - Defensive Circle: Equal-distance ring around a protected asset
 * - Investigation Wedge: Focused probing of suspicious activity
 * - Pursuit Line: Tracking a moving adversary
 * - Consensus Ring: BFT voting formation with spatial weighting
 * - Patrol Grid: Area coverage for continuous monitoring
 *
 * Trust-weighted influence ensures that higher-trust agents have more
 * impact on swarm decisions, while maintaining geometric coherence.
 */
import { type RiskDecision } from './types.js';
/**
 * Swarm formation type
 */
export type FormationType = 'defensive_circle' | 'investigation_wedge' | 'pursuit_line' | 'consensus_ring' | 'patrol_grid';
/**
 * Position assignment within a formation
 */
export interface FormationPosition {
    /** Agent identifier */
    agentId: string;
    /** Assigned position in formation (normalized [0, 1]) */
    positionIndex: number;
    /** 21D target position vector */
    targetPosition: number[];
    /** Current 21D position vector */
    currentPosition: number[];
    /** Trust weight for influence calculations */
    trustWeight: number;
    /** Role within formation */
    role: 'leader' | 'wing' | 'support' | 'reserve';
    /** Distance to formation center */
    distanceToCenter: number;
}
/**
 * Active swarm formation
 */
export interface SwarmFormation {
    /** Formation identifier */
    id: string;
    /** Formation type */
    type: FormationType;
    /** Formation center point (21D) */
    center: number[];
    /** Formation radius in hyperbolic space */
    radius: number;
    /** Agent positions */
    positions: FormationPosition[];
    /** Formation health [0, 1] */
    health: number;
    /** Formation coherence (how well agents maintain positions) */
    coherence: number;
    /** Formation purpose / reason */
    purpose: string;
    /** Risk decision this formation is enforcing */
    enforcingDecision?: RiskDecision;
    /** Creation timestamp */
    createdAt: number;
}
/**
 * Swarm formation configuration
 */
export interface SwarmConfig {
    /** Default formation radius */
    defaultRadius: number;
    /** Minimum agents for a formation */
    minAgents: number;
    /** Maximum agents per formation */
    maxAgents: number;
    /** Position tolerance (how close agents must be to target) */
    positionTolerance: number;
    /** Coherence decay rate per step */
    coherenceDecay: number;
    /** Trust weight exponent (higher = more trust influence) */
    trustExponent: number;
}
/**
 * Default swarm configuration
 */
export declare const DEFAULT_SWARM_CONFIG: SwarmConfig;
/**
 * Swarm Formation Coordinator
 *
 * Manages geometric formations of agents in the unified brain manifold.
 * Each formation encodes both spatial relationships and trust dynamics,
 * enabling coordinated governance responses to threats.
 */
export declare class SwarmFormationManager {
    private formations;
    private nextFormationId;
    private readonly config;
    constructor(config?: Partial<SwarmConfig>);
    /**
     * Create a defensive circle formation around a center point.
     * Agents are placed at equal angular intervals on a hyperbolic circle.
     *
     * @param agents - Array of { agentId, currentPosition, trustScore }
     * @param center - Center point to defend (21D)
     * @param radius - Circle radius in hyperbolic space
     * @param purpose - Why this formation was created
     * @returns Created formation
     */
    createDefensiveCircle(agents: Array<{
        agentId: string;
        currentPosition: number[];
        trustScore: number;
    }>, center: number[], radius?: number, purpose?: string): SwarmFormation;
    /**
     * Create an investigation wedge focused on a target point.
     * Higher-trust agents form the leading edge.
     *
     * @param agents - Agents sorted by trust (highest first)
     * @param target - Target point to investigate (21D)
     * @param origin - Formation origin point (21D)
     * @param purpose - Investigation reason
     * @returns Created formation
     */
    createInvestigationWedge(agents: Array<{
        agentId: string;
        currentPosition: number[];
        trustScore: number;
    }>, target: number[], origin: number[], purpose?: string): SwarmFormation;
    /**
     * Create a consensus ring for BFT voting.
     * Agents are positioned based on their voting weight.
     *
     * @param agents - Agents participating in consensus
     * @param center - Center of consensus ring (21D)
     * @param purpose - What is being voted on
     * @returns Created formation
     */
    createConsensusRing(agents: Array<{
        agentId: string;
        currentPosition: number[];
        trustScore: number;
    }>, center: number[], purpose?: string): SwarmFormation;
    /**
     * Compute formation health.
     * Health = weighted average of how close agents are to their target positions.
     *
     * @param formationId - Formation to evaluate
     * @returns Health value [0, 1]
     */
    computeHealth(formationId: string): number;
    /**
     * Compute formation coherence.
     * Coherence measures how well the formation maintains its geometric structure.
     *
     * @param formationId - Formation to evaluate
     * @returns Coherence value [0, 1]
     */
    computeCoherence(formationId: string): number;
    /**
     * Update agent positions within a formation.
     *
     * @param formationId - Formation to update
     * @param agentPositions - Map of agentId -> current 21D position
     */
    updatePositions(formationId: string, agentPositions: Map<string, number[]>): void;
    /**
     * Compute trust-weighted influence of the formation on a risk decision.
     * Returns a weighted vote based on agent trust scores and positions.
     */
    computeWeightedVote(formationId: string): {
        allow: number;
        deny: number;
        total: number;
    };
    /**
     * Get a formation by ID
     */
    getFormation(formationId: string): SwarmFormation | undefined;
    /**
     * Get all active formations
     */
    getAllFormations(): SwarmFormation[];
    /**
     * Dissolve a formation
     */
    dissolveFormation(formationId: string): boolean;
    /**
     * Get formation count
     */
    get formationCount(): number;
    private registerFormation;
}
//# sourceMappingURL=swarm-formation.d.ts.map