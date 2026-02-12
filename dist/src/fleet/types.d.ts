/**
 * Fleet Management Type Definitions
 *
 * @module fleet/types
 */
import { SpectralIdentity } from '../harmonic/spectral-identity';
import { TrustScore } from '../spaceTor/trust-manager';
/**
 * Agent capability categories
 */
export type AgentCapability = 'code_generation' | 'code_review' | 'testing' | 'documentation' | 'security_scan' | 'deployment' | 'monitoring' | 'data_analysis' | 'orchestration' | 'communication';
/**
 * Agent status
 */
export type AgentStatus = 'idle' | 'busy' | 'offline' | 'suspended' | 'quarantined';
/**
 * Task priority levels
 */
export type TaskPriority = 'critical' | 'high' | 'medium' | 'low';
/**
 * Task status
 */
export type TaskStatus = 'pending' | 'assigned' | 'running' | 'completed' | 'failed' | 'cancelled' | 'awaiting_approval';
/**
 * Sacred Tongue governance tier
 */
export type GovernanceTier = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
/**
 * Agent definition
 */
export interface FleetAgent {
    /** Unique agent identifier */
    id: string;
    /** Human-readable name */
    name: string;
    /** Agent description */
    description: string;
    /** AI provider (openai, anthropic, etc.) */
    provider: string;
    /** Model identifier */
    model: string;
    /** Agent capabilities */
    capabilities: AgentCapability[];
    /** Current status */
    status: AgentStatus;
    /** 6D trust vector (Sacred Tongues) */
    trustVector: number[];
    /** Spectral identity */
    spectralIdentity?: SpectralIdentity;
    /** Current trust score */
    trustScore?: TrustScore;
    /** Maximum concurrent tasks */
    maxConcurrentTasks: number;
    /** Current task count */
    currentTaskCount: number;
    /** Governance tier (max allowed) */
    maxGovernanceTier: GovernanceTier;
    /** Registration timestamp */
    registeredAt: number;
    /** Last activity timestamp */
    lastActiveAt: number;
    /** Total tasks completed */
    tasksCompleted: number;
    /** Success rate (0-1) */
    successRate: number;
    /** Metadata */
    metadata?: Record<string, unknown>;
}
/**
 * Task definition
 */
export interface FleetTask {
    /** Unique task identifier */
    id: string;
    /** Task name */
    name: string;
    /** Task description */
    description: string;
    /** Required capability */
    requiredCapability: AgentCapability;
    /** Required governance tier */
    requiredTier: GovernanceTier;
    /** Task priority */
    priority: TaskPriority;
    /** Current status */
    status: TaskStatus;
    /** Assigned agent ID */
    assignedAgentId?: string;
    /** Task input data */
    input: Record<string, unknown>;
    /** Task output data */
    output?: Record<string, unknown>;
    /** Error message if failed */
    error?: string;
    /** Minimum trust score required */
    minTrustScore: number;
    /** Requires roundtable approval */
    requiresApproval: boolean;
    /** Approval votes (agent IDs) */
    approvalVotes?: string[];
    /** Required approval count */
    requiredApprovals: number;
    /** Created timestamp */
    createdAt: number;
    /** Started timestamp */
    startedAt?: number;
    /** Completed timestamp */
    completedAt?: number;
    /** Timeout in milliseconds */
    timeoutMs: number;
    /** Retry count */
    retryCount: number;
    /** Max retries */
    maxRetries: number;
}
/**
 * Fleet statistics
 */
export interface FleetStats {
    /** Total registered agents */
    totalAgents: number;
    /** Agents by status */
    agentsByStatus: Record<AgentStatus, number>;
    /** Agents by trust level */
    agentsByTrustLevel: Record<string, number>;
    /** Total tasks */
    totalTasks: number;
    /** Tasks by status */
    tasksByStatus: Record<TaskStatus, number>;
    /** Average task completion time (ms) */
    avgCompletionTimeMs: number;
    /** Fleet-wide success rate */
    fleetSuccessRate: number;
    /** Active roundtable sessions */
    activeRoundtables: number;
}
/**
 * Roundtable session for consensus
 */
export interface RoundtableSession {
    /** Session ID */
    id: string;
    /** Topic/task being discussed */
    topic: string;
    /** Task ID if applicable */
    taskId?: string;
    /** Participating agent IDs */
    participants: string[];
    /** Votes cast */
    votes: Map<string, 'approve' | 'reject' | 'abstain'>;
    /** Required consensus (0-1) */
    requiredConsensus: number;
    /** Session status */
    status: 'active' | 'approved' | 'rejected' | 'expired';
    /** Created timestamp */
    createdAt: number;
    /** Expires timestamp */
    expiresAt: number;
}
/**
 * Fleet event types
 */
export type FleetEventType = 'agent_registered' | 'agent_updated' | 'agent_removed' | 'agent_suspended' | 'agent_quarantined' | 'task_created' | 'task_assigned' | 'task_started' | 'task_completed' | 'task_failed' | 'task_cancelled' | 'roundtable_started' | 'roundtable_vote' | 'roundtable_concluded' | 'trust_updated' | 'security_alert';
/**
 * Fleet event
 */
export interface FleetEvent {
    /** Event type */
    type: FleetEventType;
    /** Timestamp */
    timestamp: number;
    /** Related agent ID */
    agentId?: string;
    /** Related task ID */
    taskId?: string;
    /** Event data */
    data: Record<string, unknown>;
}
/**
 * Governance tier requirements
 */
export declare const GOVERNANCE_TIERS: Record<GovernanceTier, {
    minTrustScore: number;
    requiredTongues: number;
    description: string;
}>;
/**
 * Priority weights for task scheduling
 */
export declare const PRIORITY_WEIGHTS: Record<TaskPriority, number>;
/**
 * Dimensional state for Polly Pad flux
 * Based on the Polly/Quasi/Demi dimensional breathing system
 */
export type DimensionalState = 'POLLY' | 'QUASI' | 'DEMI' | 'COLLAPSED';
/**
 * Dimensional state thresholds
 */
export declare const DIMENSIONAL_THRESHOLDS: {
    POLLY: number;
    QUASI: number;
    DEMI: number;
    COLLAPSED: number;
};
/**
 * Get dimensional state from nu value
 */
export declare function getDimensionalState(nu: number): DimensionalState;
//# sourceMappingURL=types.d.ts.map