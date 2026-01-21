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
export type AgentCapability = 
  | 'code_generation'
  | 'code_review'
  | 'testing'
  | 'documentation'
  | 'security_scan'
  | 'deployment'
  | 'monitoring'
  | 'data_analysis'
  | 'orchestration'
  | 'communication';

/**
 * Agent status
 */
export type AgentStatus = 
  | 'idle'
  | 'busy'
  | 'offline'
  | 'suspended'
  | 'quarantined';

/**
 * Task priority levels
 */
export type TaskPriority = 'critical' | 'high' | 'medium' | 'low';

/**
 * Task status
 */
export type TaskStatus = 
  | 'pending'
  | 'assigned'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'awaiting_approval';

/**
 * Sacred Tongue governance tier
 */
export type GovernanceTier = 
  | 'KO'   // Read-only operations
  | 'AV'   // Write operations
  | 'RU'   // Execute operations
  | 'CA'   // Deploy operations
  | 'UM'   // Admin operations
  | 'DR';  // Critical/destructive operations

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
export type FleetEventType = 
  | 'agent_registered'
  | 'agent_updated'
  | 'agent_removed'
  | 'agent_suspended'
  | 'agent_quarantined'
  | 'task_created'
  | 'task_assigned'
  | 'task_started'
  | 'task_completed'
  | 'task_failed'
  | 'task_cancelled'
  | 'roundtable_started'
  | 'roundtable_vote'
  | 'roundtable_concluded'
  | 'trust_updated'
  | 'security_alert';

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
export const GOVERNANCE_TIERS: Record<GovernanceTier, {
  minTrustScore: number;
  requiredTongues: number;
  description: string;
}> = {
  KO: { minTrustScore: 0.1, requiredTongues: 1, description: 'Read-only operations' },
  AV: { minTrustScore: 0.3, requiredTongues: 2, description: 'Write operations' },
  RU: { minTrustScore: 0.5, requiredTongues: 3, description: 'Execute operations' },
  CA: { minTrustScore: 0.7, requiredTongues: 4, description: 'Deploy operations' },
  UM: { minTrustScore: 0.85, requiredTongues: 5, description: 'Admin operations' },
  DR: { minTrustScore: 0.95, requiredTongues: 6, description: 'Critical/destructive operations' }
};

/**
 * Priority weights for task scheduling
 */
export const PRIORITY_WEIGHTS: Record<TaskPriority, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1
};
