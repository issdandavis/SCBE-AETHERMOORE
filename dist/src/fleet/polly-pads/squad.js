"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.Squad = void 0;
const closed_network_1 = require("./closed-network");
const DEFAULT_SQUAD_CONFIG = {
    maxPads: 6,
    maxFaulty: 1,
    quorum: 4,
    voteTimeoutMs: 30000,
};
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
class Squad {
    id;
    name;
    maxPads;
    maxFaulty;
    quorum;
    voteTimeoutMs;
    pads = new Map();
    proposals = new Map();
    network;
    constructor(config) {
        const merged = { ...DEFAULT_SQUAD_CONFIG, ...config };
        this.id = merged.id;
        this.name = merged.name;
        this.maxPads = merged.maxPads;
        this.maxFaulty = merged.maxFaulty;
        this.quorum = merged.quorum;
        this.voteTimeoutMs = merged.voteTimeoutMs;
        // Validate BFT constraint: n >= 3f + 1
        if (this.maxPads < 3 * this.maxFaulty + 1) {
            throw new Error(`BFT constraint violated: maxPads (${this.maxPads}) must be >= 3*maxFaulty+1 (${3 * this.maxFaulty + 1})`);
        }
        // Create a closed network for this squad
        this.network = new closed_network_1.ClosedNetwork();
    }
    // === Pad Management ===
    /**
     * Add a pad to the squad.
     */
    addPad(pad) {
        if (this.pads.size >= this.maxPads) {
            return false;
        }
        this.pads.set(pad.agentId, pad);
        pad.joinSquad(this.id);
        this.network.registerPad(pad.agentId);
        return true;
    }
    /**
     * Remove a pad from the squad.
     */
    removePad(agentId) {
        const pad = this.pads.get(agentId);
        if (!pad)
            return false;
        pad.leaveSquad();
        this.pads.delete(agentId);
        this.network.deregisterPad(agentId);
        return true;
    }
    /**
     * Get a pad by agent ID.
     */
    getPad(agentId) {
        return this.pads.get(agentId);
    }
    /**
     * Get all pads.
     */
    getAllPads() {
        return Array.from(this.pads.values());
    }
    /**
     * Get pads by current mode.
     */
    getPadsByMode(mode) {
        return this.getAllPads().filter((p) => p.currentMode === mode);
    }
    /**
     * Get squad size.
     */
    get size() {
        return this.pads.size;
    }
    // === Consensus ===
    /**
     * Submit a proposal for squad consensus.
     */
    propose(proposerId, options) {
        if (!this.pads.has(proposerId)) {
            throw new Error(`Pad ${proposerId} is not in this squad`);
        }
        const proposal = {
            id: `prop-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`,
            description: options.description,
            proposerId,
            category: options.category,
            data: options.data,
            votes: [],
            decision: null,
            createdAt: Date.now(),
            decidedAt: null,
        };
        this.proposals.set(proposal.id, proposal);
        // Broadcast proposal to squad
        this.network.broadcast(proposerId, {
            type: 'proposal',
            proposalId: proposal.id,
            description: options.description,
            category: options.category,
        });
        return proposal;
    }
    /**
     * Cast a vote on a proposal.
     */
    vote(proposalId, padId, decision, confidence) {
        const proposal = this.proposals.get(proposalId);
        if (!proposal) {
            throw new Error(`Proposal ${proposalId} not found`);
        }
        if (proposal.decision !== null) {
            throw new Error(`Proposal ${proposalId} already decided: ${proposal.decision}`);
        }
        if (!this.pads.has(padId)) {
            throw new Error(`Pad ${padId} is not in this squad`);
        }
        // Check for duplicate vote
        if (proposal.votes.some((v) => v.padId === padId)) {
            throw new Error(`Pad ${padId} has already voted on proposal ${proposalId}`);
        }
        const pad = this.pads.get(padId);
        const voteEntry = {
            padId,
            decision,
            confidence: Math.max(0, Math.min(1, confidence)),
            mode: pad.currentMode || 'science',
            timestamp: Date.now(),
        };
        proposal.votes.push(voteEntry);
        // Check if consensus reached
        this.checkConsensus(proposal);
        return proposal;
    }
    /**
     * Get a proposal by ID.
     */
    getProposal(proposalId) {
        return this.proposals.get(proposalId);
    }
    /**
     * Get all active (undecided) proposals.
     */
    getActiveProposals() {
        return Array.from(this.proposals.values()).filter((p) => p.decision === null);
    }
    /**
     * Get the closed network instance.
     */
    getNetwork() {
        return this.network;
    }
    // === Internal Consensus Logic ===
    /**
     * Check if a proposal has reached consensus.
     *
     * BFT consensus rules:
     * - APPROVED: >= quorum (4/6) APPROVE votes
     * - DENIED: > maxPads/2 (>3) DENY votes
     * - DEFERRED: All votes in, not enough to approve or deny
     * - NO_QUORUM: Timeout with insufficient votes
     */
    checkConsensus(proposal) {
        const approvals = proposal.votes.filter((v) => v.decision === 'APPROVE').length;
        const denials = proposal.votes.filter((v) => v.decision === 'DENY').length;
        const totalVotes = proposal.votes.length;
        const totalPads = this.pads.size;
        // Check for approval
        if (approvals >= this.quorum) {
            proposal.decision = 'APPROVED';
            proposal.decidedAt = Date.now();
            this.network.broadcast('system', {
                type: 'consensus_reached',
                proposalId: proposal.id,
                decision: 'APPROVED',
                approvals,
                denials,
            });
            return;
        }
        // Check for denial (majority deny)
        if (denials > totalPads / 2) {
            proposal.decision = 'DENIED';
            proposal.decidedAt = Date.now();
            this.network.broadcast('system', {
                type: 'consensus_reached',
                proposalId: proposal.id,
                decision: 'DENIED',
                approvals,
                denials,
            });
            return;
        }
        // All votes in but not enough approvals or denials
        if (totalVotes >= totalPads) {
            // If we have more deferrals, defer the decision
            const deferrals = proposal.votes.filter((v) => v.decision === 'DEFER').length;
            if (deferrals > approvals && deferrals > denials) {
                proposal.decision = 'DEFERRED';
            }
            else {
                // Not enough approvals = denied
                proposal.decision = 'DENIED';
            }
            proposal.decidedAt = Date.now();
        }
    }
    // === Statistics ===
    /**
     * Get squad statistics.
     */
    getStats() {
        const proposals = Array.from(this.proposals.values());
        const modeDist = {};
        for (const pad of this.pads.values()) {
            const mode = pad.currentMode || 'none';
            modeDist[mode] = (modeDist[mode] || 0) + 1;
        }
        return {
            padCount: this.pads.size,
            maxPads: this.maxPads,
            quorum: this.quorum,
            totalProposals: proposals.length,
            approved: proposals.filter((p) => p.decision === 'APPROVED').length,
            denied: proposals.filter((p) => p.decision === 'DENIED').length,
            deferred: proposals.filter((p) => p.decision === 'DEFERRED').length,
            pending: proposals.filter((p) => p.decision === null).length,
            modeDistribution: modeDist,
        };
    }
}
exports.Squad = Squad;
//# sourceMappingURL=squad.js.map