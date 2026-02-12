/**
 * Fleet Manager - Central orchestration for AI agent fleet
 *
 * Combines AgentRegistry, TaskDispatcher, and GovernanceManager
 * into a unified fleet management system with SCBE security.
 *
 * @module fleet/fleet-manager
 */
import { AgentRegistrationOptions } from './agent-registry';
import { RoundtableOptions } from './governance';
import { PollyPad, PollyPadManager } from './polly-pad';
import { SwarmCoordinator } from './swarm';
import { TaskCreationOptions } from './task-dispatcher';
import { AgentCapability, FleetAgent, FleetEvent, FleetStats, FleetTask, GovernanceTier } from './types';
/**
 * Fleet Manager Configuration
 */
export interface FleetManagerConfig {
    /** Auto-assign tasks when created */
    autoAssign?: boolean;
    /** Auto-cleanup completed tasks after ms */
    taskRetentionMs?: number;
    /** Health check interval ms */
    healthCheckIntervalMs?: number;
    /** Enable security alerts */
    enableSecurityAlerts?: boolean;
    /** Enable Polly Pads for agents */
    enablePollyPads?: boolean;
    /** Auto-create swarm for new agents */
    defaultSwarmId?: string;
}
/**
 * Fleet Manager
 *
 * Central orchestration hub for managing AI agent fleets with
 * SCBE security integration.
 */
export declare class FleetManager {
    private trustManager;
    private spectralGenerator;
    private registry;
    private dispatcher;
    private governance;
    private pollyPadManager?;
    private swarmCoordinator?;
    private config;
    private eventLog;
    private eventListeners;
    private healthCheckInterval?;
    constructor(config?: FleetManagerConfig);
    /**
     * Register a new agent
     */
    registerAgent(options: AgentRegistrationOptions): FleetAgent;
    /**
     * Get agent by ID
     */
    getAgent(id: string): FleetAgent | undefined;
    /**
     * Get all agents
     */
    getAllAgents(): FleetAgent[];
    /**
     * Get agents by capability
     */
    getAgentsByCapability(capability: AgentCapability): FleetAgent[];
    /**
     * Update agent trust vector
     */
    updateAgentTrust(agentId: string, trustVector: number[]): void;
    /**
     * Suspend an agent
     */
    suspendAgent(agentId: string): void;
    /**
     * Reactivate an agent
     */
    reactivateAgent(agentId: string): void;
    /**
     * Remove an agent
     */
    removeAgent(agentId: string): boolean;
    /**
     * Create a new task
     */
    createTask(options: TaskCreationOptions): FleetTask;
    /**
     * Get task by ID
     */
    getTask(id: string): FleetTask | undefined;
    /**
     * Get all tasks
     */
    getAllTasks(): FleetTask[];
    /**
     * Get pending tasks
     */
    getPendingTasks(): FleetTask[];
    /**
     * Manually assign a task
     */
    assignTask(taskId: string): import("./task-dispatcher").TaskAssignmentResult;
    /**
     * Complete a task
     */
    completeTask(taskId: string, output: Record<string, unknown>): void;
    /**
     * Fail a task
     */
    failTask(taskId: string, error: string): void;
    /**
     * Cancel a task
     */
    cancelTask(taskId: string): void;
    /**
     * Create a roundtable session
     */
    createRoundtable(options: RoundtableOptions): import("./types").RoundtableSession;
    /**
     * Cast vote in roundtable
     */
    castVote(sessionId: string, agentId: string, vote: 'approve' | 'reject' | 'abstain'): import("./governance").VoteResult;
    /**
     * Get active roundtable sessions
     */
    getActiveRoundtables(): import("./types").RoundtableSession[];
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
     * Get required governance tier for action
     */
    getRequiredTier(action: string): GovernanceTier;
    /**
     * Get Polly Pad for an agent
     */
    getAgentPad(agentId: string): PollyPad | undefined;
    /**
     * Get all Polly Pads
     */
    getAllPads(): PollyPad[];
    /**
     * Add note to agent's pad
     */
    addPadNote(agentId: string, title: string, content: string, tags?: string[]): import("./polly-pad").PadNote | undefined;
    /**
     * Add sketch to agent's pad
     */
    addPadSketch(agentId: string, name: string, data: string, type?: 'diagram' | 'flowchart' | 'wireframe' | 'freehand' | 'architecture'): import("./polly-pad").PadSketch | undefined;
    /**
     * Add tool to agent's pad
     */
    addPadTool(agentId: string, name: string, description: string, type: 'snippet' | 'template' | 'script' | 'prompt' | 'config', content: string): import("./polly-pad").PadTool | undefined;
    /**
     * Record task completion on agent's pad
     */
    recordPadTaskCompletion(agentId: string, success: boolean): void;
    /**
     * Audit an agent's pad
     */
    auditPad(agentId: string, auditorId: string): import("./polly-pad").AuditEntry | undefined;
    /**
     * Get pad statistics for an agent
     */
    getPadStats(agentId: string): {
        tier: GovernanceTier;
        tierName: string;
        xp: number;
        xpToNext: number;
        progress: number;
        tasksCompleted: number;
        successRate: number;
        toolsCreated: number;
        milestonesAchieved: number;
        dimensionalState: import("./types").DimensionalState;
        nu: number;
    } | undefined;
    /**
     * Get swarm coordinator
     */
    getSwarmCoordinator(): SwarmCoordinator | undefined;
    /**
     * Get Polly Pad manager
     */
    getPollyPadManager(): PollyPadManager | undefined;
    /**
     * Get comprehensive fleet statistics
     */
    getStatistics(): FleetStats;
    /**
     * Get fleet health status
     */
    getHealthStatus(): {
        healthy: boolean;
        issues: string[];
        metrics: Record<string, number>;
    };
    /**
     * Subscribe to fleet events
     */
    onEvent(listener: (event: FleetEvent) => void): () => void;
    /**
     * Get recent events
     */
    getRecentEvents(limit?: number): FleetEvent[];
    /**
     * Get events by type
     */
    getEventsByType(type: FleetEvent['type'], limit?: number): FleetEvent[];
    /**
     * Shutdown fleet manager
     */
    shutdown(): void;
    /**
     * Handle internal events
     */
    private handleEvent;
    /**
     * Start health check interval
     */
    private startHealthChecks;
}
/**
 * Create a pre-configured fleet manager with common agents
 */
export declare function createDefaultFleet(): FleetManager;
//# sourceMappingURL=fleet-manager.d.ts.map