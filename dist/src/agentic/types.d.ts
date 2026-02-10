/**
 * Agentic Coder Platform Types
 *
 * @module agentic/types
 */
import { GovernanceTier } from '../fleet/types';
import { SpectralIdentity } from '../harmonic/spectral-identity';
/**
 * Built-in agent roles (aligned with Sacred Tongues)
 */
export type AgentRole = 'architect' | 'coder' | 'reviewer' | 'tester' | 'security' | 'deployer';
/**
 * Agent role to Sacred Tongue mapping
 */
export declare const ROLE_TONGUE_MAP: Record<AgentRole, string>;
/**
 * Agent role to governance tier mapping
 */
export declare const ROLE_TIER_MAP: Record<AgentRole, GovernanceTier>;
/**
 * Coding task types
 */
export type CodingTaskType = 'design' | 'implement' | 'review' | 'test' | 'security_audit' | 'deploy' | 'refactor' | 'debug' | 'document' | 'optimize';
/**
 * Task complexity levels
 */
export type TaskComplexity = 'simple' | 'moderate' | 'complex';
/**
 * Collaboration mode
 */
export type CollaborationMode = 'solo' | 'pair' | 'trio';
/**
 * Agent contribution to a task
 */
export interface AgentContribution {
    agentId: string;
    role: AgentRole;
    action: string;
    output: string;
    confidence: number;
    timestamp: number;
    tokensUsed?: number;
}
/**
 * Coding task definition
 */
export interface CodingTask {
    id: string;
    type: CodingTaskType;
    title: string;
    description: string;
    complexity: TaskComplexity;
    /** Input context (code, requirements, etc.) */
    context: {
        files?: string[];
        code?: string;
        requirements?: string;
        constraints?: string[];
    };
    /** Expected output format */
    expectedOutput: 'code' | 'review' | 'tests' | 'report' | 'plan';
    /** Language/framework */
    language?: string;
    framework?: string;
    /** Task status */
    status: 'pending' | 'in_progress' | 'review' | 'completed' | 'failed';
    /** Assigned agent group */
    assignedGroup?: string;
    /** Contributions from agents */
    contributions: AgentContribution[];
    /** Final output */
    output?: string;
    /** Timestamps */
    createdAt: number;
    startedAt?: number;
    completedAt?: number;
}
/**
 * Task group (1-3 agents working together)
 */
export interface TaskGroup {
    id: string;
    name: string;
    /** Agent IDs in this group (1-3) */
    agents: string[];
    /** Current task being worked on */
    currentTask?: string;
    /** Collaboration mode */
    mode: CollaborationMode;
    /** Group status */
    status: 'idle' | 'working' | 'reviewing' | 'blocked';
    /** Tasks completed by this group */
    tasksCompleted: number;
    /** Group success rate */
    successRate: number;
    /** Created timestamp */
    createdAt: number;
}
/**
 * Built-in agent definition
 */
export interface BuiltInAgent {
    id: string;
    role: AgentRole;
    name: string;
    description: string;
    /** AI provider and model */
    provider: string;
    model: string;
    /** System prompt for this agent */
    systemPrompt: string;
    /** Specializations */
    specializations: string[];
    /** Agent capabilities */
    capabilities?: string[];
    /** Trust vector (6D Sacred Tongue) */
    trustVector: number[];
    /** Spectral identity */
    spectralIdentity?: SpectralIdentity;
    /** Current status */
    status: 'available' | 'busy' | 'offline';
    /** Current group assignment */
    currentGroup?: string;
    /** Statistics */
    stats: {
        tasksCompleted: number;
        avgConfidence: number;
        avgTokensPerTask: number;
    };
}
/**
 * Collaboration message between agents
 */
export interface CollaborationMessage {
    id: string;
    groupId: string;
    taskId: string;
    fromAgent: string;
    toAgent?: string;
    type: 'request' | 'response' | 'feedback' | 'handoff' | 'consensus';
    content: string;
    metadata?: Record<string, unknown>;
    timestamp: number;
}
/**
 * Platform configuration
 */
export interface PlatformConfig {
    /** Maximum agents per group */
    maxAgentsPerGroup: number;
    /** Maximum concurrent tasks */
    maxConcurrentTasks: number;
    /** Default AI provider */
    defaultProvider: string;
    /** Enable consensus for complex tasks */
    requireConsensus: boolean;
    /** Minimum confidence threshold */
    minConfidence: number;
}
/**
 * Default platform configuration
 */
export declare const DEFAULT_PLATFORM_CONFIG: PlatformConfig;
/**
 * Task type to recommended agents mapping
 */
export declare const TASK_AGENT_RECOMMENDATIONS: Record<CodingTaskType, AgentRole[]>;
/**
 * Complexity to group size mapping
 */
export declare const COMPLEXITY_GROUP_SIZE: Record<TaskComplexity, CollaborationMode>;
//# sourceMappingURL=types.d.ts.map