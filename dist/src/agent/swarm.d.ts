/**
 * Swarm Coordination in Poincaré Ball
 *
 * Implements agent swarm coordination using hyperbolic geometry:
 * - Formation control (dispersed, convergent, ring)
 * - Centroid calculation in hyperbolic space
 * - Byzantine fault tolerant consensus
 * - Rogue agent detection via PHDM coherence
 *
 * @module agent/swarm
 */
import { TongueCode } from '../tokenizer/ss1.js';
import { Agent, BFTConfig, BFTConsensusResult, BFTVote, FormationTarget, PoincarePosition, RogueDetectionResult, SwarmState } from './types.js';
/** Minimum coherence for healthy agent */
export declare const MIN_COHERENCE_THRESHOLD = 0.3;
/** Maximum hyperbolic distance before rogue suspicion */
export declare const MAX_HYPERBOLIC_DISTANCE = 2;
/** Rogue confidence threshold for quarantine */
export declare const ROGUE_QUARANTINE_THRESHOLD = 0.8;
/**
 * Möbius addition in Poincaré ball
 *
 * Computes u ⊕ v (hyperbolic addition)
 */
export declare function mobiusAdd(u: PoincarePosition, v: PoincarePosition): PoincarePosition;
/**
 * Scalar multiplication in Poincaré ball
 *
 * Computes t ⊗ v (hyperbolic scaling)
 */
export declare function mobiusScale(t: number, v: PoincarePosition): PoincarePosition;
/**
 * Compute weighted centroid in hyperbolic space
 *
 * Uses Einstein midpoint formula generalized to Poincaré ball
 */
export declare function hyperbolicCentroid(points: PoincarePosition[], weights?: number[]): PoincarePosition;
/**
 * Generate ring formation positions for all tongues
 */
export declare function generateRingFormation(radius?: number): Map<TongueCode, PoincarePosition>;
/**
 * Generate dispersed formation (spread across ball)
 */
export declare function generateDispersedFormation(): Map<TongueCode, PoincarePosition>;
/**
 * Generate convergent formation (clustered near center)
 */
export declare function generateConvergentFormation(): Map<TongueCode, PoincarePosition>;
/**
 * Create formation target
 */
export declare function createFormationTarget(formation: 'dispersed' | 'convergent' | 'ring', transitionDuration?: number): FormationTarget;
/**
 * Swarm coordinator for managing multiple agents
 */
export declare class SwarmCoordinator {
    private agents;
    private formation;
    /**
     * Add agent to swarm
     */
    addAgent(agent: Agent): void;
    /**
     * Remove agent from swarm
     */
    removeAgent(agentId: string): void;
    /**
     * Update agent position
     */
    updatePosition(agentId: string, position: PoincarePosition): boolean;
    /**
     * Get current swarm state
     */
    getState(): SwarmState;
    /**
     * Set formation and transition agents
     */
    setFormation(formation: 'dispersed' | 'convergent' | 'ring', onPositionUpdate?: (agentId: string, position: PoincarePosition) => Promise<void>): Promise<void>;
    /**
     * Get agents by tongue
     */
    getAgentsByTongue(tongue: TongueCode): Agent[];
    /**
     * Get active agent count
     */
    getActiveCount(): number;
}
/**
 * Collect votes for BFT consensus
 */
export declare function collectVotes(votes: BFTVote[], config: BFTConfig): BFTConsensusResult;
/**
 * Weight votes by tongue weight (φⁿ)
 */
export declare function weightedVoteCount(votes: BFTVote[]): number;
/**
 * Run BFT consensus with weighted votes
 */
export declare function runWeightedConsensus(votes: BFTVote[], config: BFTConfig): BFTConsensusResult;
/**
 * Detect if an agent is behaving as rogue
 *
 * Uses PHDM (Polyhedral Holographic Distance Metric) coherence
 * and hyperbolic distance from expected position
 */
export declare function detectRogueAgent(agent: Agent, swarmState: SwarmState, expectedPosition?: PoincarePosition): RogueDetectionResult;
/**
 * Quarantine a rogue agent
 */
export declare function quarantineAgent(agent: Agent): Agent;
//# sourceMappingURL=swarm.d.ts.map