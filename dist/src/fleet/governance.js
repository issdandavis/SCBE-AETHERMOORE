"use strict";
/**
 * Sacred Tongue Governance - Roundtable consensus for critical operations
 *
 * @module fleet/governance
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.GovernanceManager = void 0;
const types_1 = require("./types");
/**
 * Sacred Tongue Governance Manager
 *
 * Implements roundtable consensus for critical operations using
 * the Six Sacred Tongues governance model.
 */
class GovernanceManager {
    sessions = new Map();
    registry;
    eventListeners = [];
    constructor(registry) {
        this.registry = registry;
    }
    /**
     * Create a new roundtable session
     */
    createRoundtable(options) {
        const id = this.generateSessionId();
        const tierReq = types_1.GOVERNANCE_TIERS[options.requiredTier];
        // Get eligible participants
        let participants;
        if (options.specificParticipants) {
            participants = options.specificParticipants;
        }
        else {
            const eligibleAgents = this.registry.getAgentsForTier(options.requiredTier);
            participants = eligibleAgents.map((a) => a.id);
        }
        if (participants.length < tierReq.requiredTongues) {
            throw new Error(`Not enough eligible agents for ${options.requiredTier} tier. ` +
                `Need ${tierReq.requiredTongues}, have ${participants.length}`);
        }
        const session = {
            id,
            topic: options.topic,
            taskId: options.taskId,
            participants,
            votes: new Map(),
            requiredConsensus: options.customConsensus ?? tierReq.requiredTongues / participants.length,
            status: 'active',
            createdAt: Date.now(),
            expiresAt: Date.now() + (options.timeoutMs || 300000), // 5 min default
        };
        this.sessions.set(id, session);
        this.emitEvent({
            type: 'roundtable_started',
            timestamp: Date.now(),
            data: {
                sessionId: id,
                topic: options.topic,
                participants: participants.length,
                requiredConsensus: session.requiredConsensus,
            },
        });
        return session;
    }
    /**
     * Get session by ID
     */
    getSession(id) {
        return this.sessions.get(id);
    }
    /**
     * Get active sessions
     */
    getActiveSessions() {
        const now = Date.now();
        return Array.from(this.sessions.values()).filter((s) => {
            if (s.status !== 'active')
                return false;
            if (s.expiresAt < now) {
                this.expireSession(s.id);
                return false;
            }
            return true;
        });
    }
    /**
     * Cast vote in a roundtable session
     */
    castVote(sessionId, agentId, vote) {
        const session = this.sessions.get(sessionId);
        if (!session) {
            throw new Error(`Session ${sessionId} not found`);
        }
        if (session.status !== 'active') {
            throw new Error(`Session ${sessionId} is ${session.status}`);
        }
        if (session.expiresAt < Date.now()) {
            this.expireSession(sessionId);
            throw new Error(`Session ${sessionId} has expired`);
        }
        if (!session.participants.includes(agentId)) {
            throw new Error(`Agent ${agentId} is not a participant in this session`);
        }
        if (session.votes.has(agentId)) {
            throw new Error(`Agent ${agentId} has already voted`);
        }
        // Verify agent trust level
        const agent = this.registry.getAgent(agentId);
        if (!agent) {
            throw new Error(`Agent ${agentId} not found`);
        }
        if (agent.status === 'suspended' || agent.status === 'quarantined') {
            throw new Error(`Agent ${agentId} is ${agent.status} and cannot vote`);
        }
        // Record vote
        session.votes.set(agentId, vote);
        this.emitEvent({
            type: 'roundtable_vote',
            timestamp: Date.now(),
            agentId,
            data: {
                sessionId,
                vote,
                currentVotes: session.votes.size,
                totalParticipants: session.participants.length,
            },
        });
        // Check if consensus reached
        const result = this.checkConsensus(session);
        return {
            success: true,
            sessionId,
            currentVotes: session.votes.size,
            requiredVotes: Math.ceil(session.participants.length * session.requiredConsensus),
            status: session.status,
        };
    }
    /**
     * Check if consensus has been reached
     */
    checkConsensus(session) {
        const approvals = Array.from(session.votes.values()).filter((v) => v === 'approve').length;
        const rejections = Array.from(session.votes.values()).filter((v) => v === 'reject').length;
        const totalVotes = session.votes.size;
        const requiredVotes = Math.ceil(session.participants.length * session.requiredConsensus);
        // Check for approval
        if (approvals >= requiredVotes) {
            session.status = 'approved';
            this.emitEvent({
                type: 'roundtable_concluded',
                timestamp: Date.now(),
                data: {
                    sessionId: session.id,
                    result: 'approved',
                    approvals,
                    rejections,
                    abstentions: totalVotes - approvals - rejections,
                },
            });
            return true;
        }
        // Check for rejection (majority reject)
        if (rejections > session.participants.length / 2) {
            session.status = 'rejected';
            this.emitEvent({
                type: 'roundtable_concluded',
                timestamp: Date.now(),
                data: {
                    sessionId: session.id,
                    result: 'rejected',
                    approvals,
                    rejections,
                    abstentions: totalVotes - approvals - rejections,
                },
            });
            return true;
        }
        // Check if all votes are in
        if (totalVotes === session.participants.length) {
            // Not enough approvals = rejected
            session.status = 'rejected';
            this.emitEvent({
                type: 'roundtable_concluded',
                timestamp: Date.now(),
                data: {
                    sessionId: session.id,
                    result: 'rejected',
                    reason: 'Insufficient approvals',
                    approvals,
                    rejections,
                    abstentions: totalVotes - approvals - rejections,
                },
            });
            return true;
        }
        return false;
    }
    /**
     * Expire a session
     */
    expireSession(sessionId) {
        const session = this.sessions.get(sessionId);
        if (!session || session.status !== 'active')
            return;
        session.status = 'expired';
        this.emitEvent({
            type: 'roundtable_concluded',
            timestamp: Date.now(),
            data: {
                sessionId,
                result: 'expired',
                votesReceived: session.votes.size,
                totalParticipants: session.participants.length,
            },
        });
    }
    /**
     * Get governance tier for an action
     */
    getRequiredTier(action) {
        const actionTiers = {
            // Read operations
            read: 'KO',
            list: 'KO',
            get: 'KO',
            search: 'KO',
            // Write operations
            create: 'AV',
            update: 'AV',
            write: 'AV',
            // Execute operations
            run: 'RU',
            execute: 'RU',
            test: 'RU',
            // Deploy operations
            deploy: 'CA',
            publish: 'CA',
            release: 'CA',
            // Admin operations
            configure: 'UM',
            admin: 'UM',
            manage: 'UM',
            // Critical operations
            delete: 'DR',
            destroy: 'DR',
            terminate: 'DR',
            rollback: 'DR',
        };
        // Find matching tier
        const lowerAction = action.toLowerCase();
        for (const [key, tier] of Object.entries(actionTiers)) {
            if (lowerAction.includes(key)) {
                return tier;
            }
        }
        // Default to RU (execute) for unknown actions
        return 'RU';
    }
    /**
     * Check if agent can perform action
     */
    canPerformAction(agentId, action) {
        const agent = this.registry.getAgent(agentId);
        if (!agent) {
            return {
                allowed: false,
                reason: 'Agent not found',
                requiredTier: 'KO',
                requiresRoundtable: false,
            };
        }
        const requiredTier = this.getRequiredTier(action);
        const tierOrder = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
        const requiredIndex = tierOrder.indexOf(requiredTier);
        const agentIndex = tierOrder.indexOf(agent.maxGovernanceTier);
        if (agentIndex < requiredIndex) {
            return {
                allowed: false,
                reason: `Agent tier ${agent.maxGovernanceTier} insufficient for ${requiredTier} action`,
                requiredTier,
                requiresRoundtable: false,
            };
        }
        // Check trust score
        const tierReq = types_1.GOVERNANCE_TIERS[requiredTier];
        const normalizedTrust = 1 - (agent.trustScore?.normalized || 1);
        if (normalizedTrust < tierReq.minTrustScore) {
            return {
                allowed: false,
                reason: `Trust score ${normalizedTrust.toFixed(2)} below required ${tierReq.minTrustScore}`,
                requiredTier,
                requiresRoundtable: false,
            };
        }
        // Check if roundtable required
        const requiresRoundtable = requiredTier === 'UM' || requiredTier === 'DR';
        return {
            allowed: true,
            requiredTier,
            requiresRoundtable,
        };
    }
    /**
     * Get governance statistics
     */
    getStatistics() {
        const sessions = Array.from(this.sessions.values());
        let totalVotes = 0;
        let approved = 0;
        let rejected = 0;
        let expired = 0;
        let active = 0;
        for (const session of sessions) {
            totalVotes += session.votes.size;
            switch (session.status) {
                case 'approved':
                    approved++;
                    break;
                case 'rejected':
                    rejected++;
                    break;
                case 'expired':
                    expired++;
                    break;
                case 'active':
                    active++;
                    break;
            }
        }
        return {
            totalSessions: sessions.length,
            activeSessions: active,
            approvedSessions: approved,
            rejectedSessions: rejected,
            expiredSessions: expired,
            avgVotesPerSession: sessions.length > 0 ? totalVotes / sessions.length : 0,
        };
    }
    /**
     * Subscribe to events
     */
    onEvent(listener) {
        this.eventListeners.push(listener);
        return () => {
            const index = this.eventListeners.indexOf(listener);
            if (index >= 0)
                this.eventListeners.splice(index, 1);
        };
    }
    /**
     * Generate session ID
     */
    generateSessionId() {
        const timestamp = Date.now().toString(36);
        const random = Math.random().toString(36).substring(2, 6);
        return `rt-${timestamp}-${random}`;
    }
    /**
     * Emit event
     */
    emitEvent(event) {
        for (const listener of this.eventListeners) {
            try {
                listener(event);
            }
            catch (e) {
                console.error('Event listener error:', e);
            }
        }
    }
}
exports.GovernanceManager = GovernanceManager;
//# sourceMappingURL=governance.js.map