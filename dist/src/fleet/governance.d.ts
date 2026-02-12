/**
 * Sacred Tongue Governance - Roundtable consensus for critical operations
 *
 * @module fleet/governance
 */
import { AgentRegistry } from './agent-registry';
import { FleetEvent, GovernanceTier, RoundtableSession } from './types';
/**
 * Roundtable creation options
 */
export interface RoundtableOptions {
    topic: string;
    taskId?: string;
    requiredTier: GovernanceTier;
    customConsensus?: number;
    timeoutMs?: number;
    specificParticipants?: string[];
}
/**
 * Vote result
 */
export interface VoteResult {
    success: boolean;
    sessionId: string;
    currentVotes: number;
    requiredVotes: number;
    status: RoundtableSession['status'];
}
/**
 * Sacred Tongue Governance Manager
 *
 * Implements roundtable consensus for critical operations using
 * the Six Sacred Tongues governance model.
 */
export declare class GovernanceManager {
    private sessions;
    private registry;
    private eventListeners;
    constructor(registry: AgentRegistry);
    /**
     * Create a new roundtable session
     */
    createRoundtable(options: RoundtableOptions): RoundtableSession;
    /**
     * Get session by ID
     */
    getSession(id: string): RoundtableSession | undefined;
    /**
     * Get active sessions
     */
    getActiveSessions(): RoundtableSession[];
    /**
     * Cast vote in a roundtable session
     */
    castVote(sessionId: string, agentId: string, vote: 'approve' | 'reject' | 'abstain'): VoteResult;
    /**
     * Check if consensus has been reached
     */
    private checkConsensus;
    /**
     * Expire a session
     */
    private expireSession;
    /**
     * Get governance tier for an action
     */
    getRequiredTier(action: string): GovernanceTier;
    /**
     * Check if agent can perform action
     */
    canPerformAction(agentId: string, action: string): {
        allowed: boolean;
        reason?: string;
        requiredTier: GovernanceTier;
        requiresRoundtable: boolean;
    };
    /**
     * Get governance statistics
     */
    getStatistics(): {
        totalSessions: number;
        activeSessions: number;
        approvedSessions: number;
        rejectedSessions: number;
        expiredSessions: number;
        avgVotesPerSession: number;
    };
    /**
     * Subscribe to events
     */
    onEvent(listener: (event: FleetEvent) => void): () => void;
    /**
     * Generate session ID
     */
    private generateSessionId;
    /**
     * Emit event
     */
    private emitEvent;
}
//# sourceMappingURL=governance.d.ts.map