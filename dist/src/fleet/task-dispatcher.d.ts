/**
 * Task Dispatcher - Assigns tasks to agents based on trust and capability
 *
 * @module fleet/task-dispatcher
 */
import { AgentRegistry } from './agent-registry';
import { AgentCapability, FleetEvent, FleetTask, GovernanceTier, TaskPriority, TaskStatus } from './types';
/**
 * Task creation options
 */
export interface TaskCreationOptions {
    name: string;
    description: string;
    requiredCapability: AgentCapability;
    requiredTier: GovernanceTier;
    priority?: TaskPriority;
    input: Record<string, unknown>;
    minTrustScore?: number;
    requiresApproval?: boolean;
    requiredApprovals?: number;
    timeoutMs?: number;
    maxRetries?: number;
}
/**
 * Task assignment result
 */
export interface TaskAssignmentResult {
    success: boolean;
    taskId: string;
    assignedAgentId?: string;
    reason?: string;
}
/**
 * Task Dispatcher
 *
 * Manages task queue and assigns tasks to appropriate agents.
 */
export declare class TaskDispatcher {
    private tasks;
    private taskQueue;
    private registry;
    private eventListeners;
    constructor(registry: AgentRegistry);
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
     * Get tasks by status
     */
    getTasksByStatus(status: TaskStatus): FleetTask[];
    /**
     * Get pending tasks in priority order
     */
    getPendingTasks(): FleetTask[];
    /**
     * Assign task to best available agent
     */
    assignTask(taskId: string): TaskAssignmentResult;
    /**
     * Auto-assign all pending tasks
     */
    autoAssignPendingTasks(): TaskAssignmentResult[];
    /**
     * Approve task (for roundtable consensus)
     */
    approveTask(taskId: string, agentId: string): boolean;
    /**
     * Complete task
     */
    completeTask(taskId: string, output: Record<string, unknown>): void;
    /**
     * Fail task
     */
    failTask(taskId: string, error: string): void;
    /**
     * Cancel task
     */
    cancelTask(taskId: string): void;
    /**
     * Get dispatcher statistics
     */
    getStatistics(): {
        totalTasks: number;
        byStatus: Record<TaskStatus, number>;
        byPriority: Record<TaskPriority, number>;
        avgCompletionTimeMs: number;
        queueLength: number;
    };
    /**
     * Subscribe to events
     */
    onEvent(listener: (event: FleetEvent) => void): () => void;
    /**
     * Find agents eligible for a task
     */
    private findEligibleAgents;
    /**
     * Select best agent from eligible list
     */
    private selectBestAgent;
    /**
     * Execute task assignment
     */
    private executeAssignment;
    /**
     * Add task to queue
     */
    private addToQueue;
    /**
     * Remove task from queue
     */
    private removeFromQueue;
    /**
     * Generate unique task ID
     */
    private generateTaskId;
    /**
     * Emit event
     */
    private emitEvent;
}
//# sourceMappingURL=task-dispatcher.d.ts.map