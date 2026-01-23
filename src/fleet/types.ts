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

// ==================== Polly Pad Types ====================

/**
 * Dimensional state for Polly Pad flux
 * Based on the Polly/Quasi/Demi dimensional breathing system
 */
export type DimensionalState = 'POLLY' | 'QUASI' | 'DEMI' | 'COLLAPSED';

/**
 * Polly Pad note entry
 */
export interface PadNote {
  /** Unique note ID */
  id: string;

  /** Note title */
  title: string;

  /** Note content (markdown supported) */
  content: string;

  /** Created timestamp */
  createdAt: number;

  /** Last modified timestamp */
  modifiedAt: number;

  /** Tags for organization */
  tags: string[];

  /** Is pinned */
  pinned: boolean;
}

/**
 * Polly Pad sketch entry (visual drawings)
 */
export interface PadSketch {
  /** Unique sketch ID */
  id: string;

  /** Sketch name */
  name: string;

  /** SVG or canvas data */
  data: string;

  /** Sketch type */
  type: 'freehand' | 'diagram' | 'flowchart' | 'architecture';

  /** Created timestamp */
  createdAt: number;

  /** Dimensions */
  width: number;
  height: number;
}

/**
 * Polly Pad tool configuration
 */
export interface PadTool {
  /** Tool ID */
  id: string;

  /** Tool name */
  name: string;

  /** Tool description */
  description: string;

  /** Tool configuration */
  config: Record<string, unknown>;

  /** Is tool enabled */
  enabled: boolean;

  /** Last used timestamp */
  lastUsedAt?: number;

  /** Usage count */
  usageCount: number;
}

/**
 * Audit entry for Polly Pad
 */
export interface PadAuditEntry {
  /** Audit ID */
  id: string;

  /** Timestamp */
  timestamp: number;

  /** Action performed */
  action: 'note_created' | 'note_edited' | 'note_deleted' |
          'sketch_created' | 'sketch_edited' | 'sketch_deleted' |
          'tool_added' | 'tool_removed' | 'tool_configured' |
          'pad_reviewed' | 'pad_flagged' | 'pad_cleared';

  /** Details */
  details: Record<string, unknown>;

  /** Reviewer agent ID (if audited) */
  reviewerId?: string;
}

/**
 * Polly Pad - Personal workspace for each agent
 *
 * Like a Kindle for AI agents - a place to take notes,
 * draw sketches, save tools, and grow over time.
 * Audited by governance like students at school.
 */
export interface PollyPad {
  /** Pad ID (matches agent ID) */
  id: string;

  /** Agent ID this pad belongs to */
  agentId: string;

  /** Pad display name */
  name: string;

  // === Dimensional Flux State ===

  /** Nu value (0.0 - 1.0) for dimensional participation */
  nu: number;

  /** Current dimensional state */
  dimensionalState: DimensionalState;

  /** Flux rate (how fast nu changes) */
  fluxRate: number;

  /** Target nu value (for flux ODE) */
  targetNu: number;

  // === Workspace Contents ===

  /** Notes created by agent */
  notes: PadNote[];

  /** Sketches/diagrams created by agent */
  sketches: PadSketch[];

  /** Tools configured by agent */
  tools: PadTool[];

  // === Swarm Coordination ===

  /** Swarm ID this pad belongs to */
  swarmId?: string;

  /** Coherence score with swarm (0-1) */
  coherenceScore: number;

  /** Last swarm sync timestamp */
  lastSwarmSync: number;

  // === Governance ===

  /** Sacred Tongue tier (matches agent) */
  tier: GovernanceTier;

  /** 6D trust vector (synced from agent) */
  trustVector: number[];

  // === Audit Trail ===

  /** Audit log */
  auditLog: PadAuditEntry[];

  /** Audit status */
  auditStatus: 'clean' | 'flagged' | 'restricted';

  /** Last audit timestamp */
  lastAuditAt?: number;

  /** Last auditor agent ID */
  lastAuditorId?: string;

  // === Timestamps ===

  /** Created timestamp */
  createdAt: number;

  /** Last activity timestamp */
  lastActiveAt: number;

  // === Metadata ===

  /** Custom metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Swarm definition for Polly Pad coordination
 */
export interface PollySwarm {
  /** Swarm ID */
  id: string;

  /** Swarm name */
  name: string;

  /** Pad IDs in this swarm */
  padIds: string[];

  /** Collective coherence (average of all pad coherence scores) */
  coherence: number;

  /** Effective dimension (sum of all nu values) */
  effectiveDimension: number;

  /** Swarm purpose/focus */
  purpose: string;

  /** Created timestamp */
  createdAt: number;

  /** Last sync timestamp */
  lastSyncAt: number;
}

/**
 * Polly Pad event types
 */
export type PollyPadEventType =
  | 'pad_created'
  | 'pad_updated'
  | 'pad_archived'
  | 'note_added'
  | 'note_updated'
  | 'note_removed'
  | 'sketch_added'
  | 'sketch_updated'
  | 'sketch_removed'
  | 'tool_added'
  | 'tool_configured'
  | 'tool_removed'
  | 'flux_changed'
  | 'swarm_joined'
  | 'swarm_left'
  | 'swarm_synced'
  | 'audit_started'
  | 'audit_completed'
  | 'audit_flagged';

/**
 * Polly Pad event
 */
export interface PollyPadEvent {
  /** Event type */
  type: PollyPadEventType;

  /** Timestamp */
  timestamp: number;

  /** Pad ID */
  padId: string;

  /** Agent ID */
  agentId: string;

  /** Event data */
  data: Record<string, unknown>;
}

/**
 * Dimensional state thresholds
 */
export const DIMENSIONAL_THRESHOLDS = {
  POLLY: 0.8,    // nu >= 0.8 = Full participation
  QUASI: 0.5,    // 0.5 <= nu < 0.8 = Partial participation
  DEMI: 0.1,     // 0.1 <= nu < 0.5 = Minimal participation
  COLLAPSED: 0   // nu < 0.1 = Offline/archived
};

/**
 * Get dimensional state from nu value
 */
export function getDimensionalState(nu: number): DimensionalState {
  if (nu >= DIMENSIONAL_THRESHOLDS.POLLY) return 'POLLY';
  if (nu >= DIMENSIONAL_THRESHOLDS.QUASI) return 'QUASI';
  if (nu >= DIMENSIONAL_THRESHOLDS.DEMI) return 'DEMI';
  return 'COLLAPSED';
}
