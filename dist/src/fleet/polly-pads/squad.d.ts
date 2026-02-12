/**
 * @file squad.ts
 * @module fleet/polly-pads/squad
 * @layer L13
 * @component Squad Coordination with Byzantine Consensus
 * @version 1.0.0
 *
 * 6 Polly Pads form a Byzantine fault-tolerant squad.
 * Uses n=6, f_max=1, quorum=4 (4/6 votes for critical decisions).
 * Formula: n >= 3f + 1 where f = max faulty agents.
 */
import { ModePad } from './mode-pad';
import { ClosedNetwork } from './closed-network';
import { SpecialistMode, SquadVote } from './modes/types';
/**
 * Consensus decision result.
 */
export type ConsensusDecision = 'APPROVED' | 'DENIED' | 'DEFERRED' | 'NO_QUORUM';
/**
 * Proposal submitted to the squad for consensus.
 */
export interface SquadProposal {
    /** Unique proposal ID */
    id: string;
    /** What is being proposed */
    description: string;
    /** Who proposed it */
    proposerId: string;
    /** Proposal category */
    category: 'action' | 'mode_switch' | 'navigation' | 'repair' | 'abort';
    /** Data associated with the proposal */
    data: Record<string, unknown>;
    /** Votes cast */
    votes: SquadVote[];
    /** Final decision */
    decision: ConsensusDecision | null;
    /** When proposed */
    createdAt: number;
    /** When decided */
    decidedAt: number | null;
}
/**
 * Squad configuration.
 */
export interface SquadConfig {
    /** Squad identifier */
    id: string;
    /** Display name */
    name: string;
    /** Maximum pads (default: 6) */
    maxPads: number;
    /** Maximum tolerated faulty pads (default: 1) */
    maxFaulty: number;
    /** Quorum size (default: 4) — must be >= 3*maxFaulty + 1 */
    quorum: number;
    /** Vote timeout in ms (default: 30000) */
    voteTimeoutMs: number;
}
/**
 * Squad — Byzantine Fault-Tolerant Team of Polly Pads
 *
 * Coordinates 6 pads with BFT consensus for autonomous decisions.
 * Tolerates 1 malicious or broken pad (n >= 3f + 1 where f=1, n=6).
 *
 * @example
 * ```typescript
 * const squad = new Squad({
 *   id: 'MARS-SQUAD-1',
 *   name: 'Rover Alpha Squad',
 * });
 *
 * // Add 6 pads
 * squad.addPad(padAlpha);
 * squad.addPad(padBeta);
 * // ...
 *
 * // Submit a proposal for consensus
 * const proposal = squad.propose(padAlpha.agentId, {
 *   description: 'Continue on 5 wheels',
 *   category: 'repair',
 *   data: { component: 'wheel_motor_2', option: 'option_a' },
 * });
 *
 * // Each pad votes
 * squad.vote(proposal.id, padAlpha.agentId, 'APPROVE', 0.8);
 * squad.vote(proposal.id, padBeta.agentId, 'APPROVE', 0.7);
 * // ... 4 approvals needed
 *
 * // Check decision
 * const result = squad.getProposal(proposal.id);
 * console.log(result.decision); // 'APPROVED'
 * ```
 */
export declare class Squad {
    readonly id: string;
    readonly name: string;
    readonly maxPads: number;
    readonly maxFaulty: number;
    readonly quorum: number;
    readonly voteTimeoutMs: number;
    private pads;
    private proposals;
    private network;
    constructor(config: Partial<SquadConfig> & {
        id: string;
        name: string;
    });
    /**
     * Add a pad to the squad.
     */
    addPad(pad: ModePad): boolean;
    /**
     * Remove a pad from the squad.
     */
    removePad(agentId: string): boolean;
    /**
     * Get a pad by agent ID.
     */
    getPad(agentId: string): ModePad | undefined;
    /**
     * Get all pads.
     */
    getAllPads(): ModePad[];
    /**
     * Get pads by current mode.
     */
    getPadsByMode(mode: SpecialistMode): ModePad[];
    /**
     * Get squad size.
     */
    get size(): number;
    /**
     * Submit a proposal for squad consensus.
     */
    propose(proposerId: string, options: {
        description: string;
        category: SquadProposal['category'];
        data: Record<string, unknown>;
    }): SquadProposal;
    /**
     * Cast a vote on a proposal.
     */
    vote(proposalId: string, padId: string, decision: SquadVote['decision'], confidence: number): SquadProposal;
    /**
     * Get a proposal by ID.
     */
    getProposal(proposalId: string): SquadProposal | undefined;
    /**
     * Get all active (undecided) proposals.
     */
    getActiveProposals(): SquadProposal[];
    /**
     * Get the closed network instance.
     */
    getNetwork(): ClosedNetwork;
    /**
     * Check if a proposal has reached consensus.
     *
     * BFT consensus rules:
     * - APPROVED: >= quorum (4/6) APPROVE votes
     * - DENIED: > maxPads/2 (>3) DENY votes
     * - DEFERRED: All votes in, not enough to approve or deny
     * - NO_QUORUM: Timeout with insufficient votes
     */
    private checkConsensus;
    /**
     * Get squad statistics.
     */
    getStats(): {
        padCount: number;
        maxPads: number;
        quorum: number;
        totalProposals: number;
        approved: number;
        denied: number;
        deferred: number;
        pending: number;
        modeDistribution: Record<string, number>;
    };
}
//# sourceMappingURL=squad.d.ts.map