/**
 * Agentic Coder Platform - Main orchestration
 *
 * @module agentic/platform
 */
import { BuiltInAgent, CodingTask, TaskGroup, AgentRole, CodingTaskType, TaskComplexity, AgentContribution, PlatformConfig } from './types';
/**
 * Task creation options
 */
export interface CreateTaskOptions {
    type: CodingTaskType;
    title: string;
    description: string;
    complexity?: TaskComplexity;
    code?: string;
    requirements?: string;
    files?: string[];
    constraints?: string[];
    language?: string;
    framework?: string;
    preferredAgents?: AgentRole[];
}
/**
 * Platform event types
 */
export type PlatformEventType = 'task_created' | 'task_started' | 'task_completed' | 'task_failed' | 'group_created' | 'group_dissolved' | 'agent_contribution' | 'consensus_reached';
/**
 * Platform event
 */
export interface PlatformEvent {
    type: PlatformEventType;
    timestamp: number;
    data: Record<string, unknown>;
}
/**
 * Agentic Coder Platform
 *
 * Main platform for collaborative AI coding with 6 built-in agents.
 */
export declare class AgenticCoderPlatform {
    private agents;
    private tasks;
    private groupManager;
    private collaboration;
    private config;
    private eventListeners;
    constructor(config?: Partial<PlatformConfig>);
    /**
     * Get all agents
     */
    getAgents(): BuiltInAgent[];
    /**
     * Get agent by ID
     */
    getAgent(id: string): BuiltInAgent | undefined;
    /**
     * Get agent by role
     */
    getAgentByRole(role: AgentRole): BuiltInAgent | undefined;
    /**
     * Get available agents
     */
    getAvailableAgents(): BuiltInAgent[];
    /**
     * Create a new coding task
     */
    createTask(options: CreateTaskOptions): CodingTask;
    /**
     * Get task by ID
     */
    getTask(id: string): CodingTask | undefined;
    /**
     * Get all tasks
     */
    getAllTasks(): CodingTask[];
    /**
     * Get pending tasks
     */
    getPendingTasks(): CodingTask[];
    /**
     * Create a group for a task
     */
    createGroupForTask(taskId: string, preferredAgents?: AgentRole[]): TaskGroup;
    /**
     * Create a custom group
     */
    createCustomGroup(agentRoles: AgentRole[]): TaskGroup;
    /**
     * Get group by ID
     */
    getGroup(id: string): TaskGroup | undefined;
    /**
     * Get all groups
     */
    getAllGroups(): TaskGroup[];
    /**
     * Dissolve a group
     */
    dissolveGroup(groupId: string): void;
    /**
     * Execute a task with a group
     *
     * @param taskId - Task to execute
     * @param groupId - Group to execute with (optional, creates one if not provided)
     * @param executor - Function to execute agent actions
     */
    executeTask(taskId: string, groupId?: string, executor?: (agent: BuiltInAgent, action: string, context: string) => Promise<{
        output: string;
        confidence: number;
        tokens?: number;
    }>): Promise<{
        success: boolean;
        output: string;
        contributions: AgentContribution[];
    }>;
    /**
     * Get recommended agents for a task type
     */
    getRecommendedAgents(taskType: CodingTaskType): AgentRole[];
    /**
     * Get platform statistics
     */
    getStatistics(): {
        totalAgents: number;
        availableAgents: number;
        totalTasks: number;
        completedTasks: number;
        activeGroups: number;
        avgConfidence: number;
    };
    /**
     * Subscribe to platform events
     */
    onEvent(listener: (event: PlatformEvent) => void): () => void;
    /**
     * Generate task ID
     */
    private generateTaskId;
    /**
     * Infer task complexity
     */
    private inferComplexity;
    /**
     * Get expected output type for task type
     */
    private getExpectedOutput;
    /**
     * Create default executor using configured AI providers
     *
     * Uses provider priority chain from SCBE_PROVIDER_PRIORITY env var.
     * Falls back through providers on failure if SCBE_PROVIDER_FALLBACK_ENABLED=true.
     *
     * Configure in .env:
     *   SCBE_PROVIDER_PRIORITY=anthropic,openai,google
     *   ANTHROPIC_API_KEY=sk-ant-...
     *   OPENAI_API_KEY=sk-...
     *   GOOGLE_API_KEY=AIza...
     */
    private createDefaultExecutor;
    /**
     * Emit platform event
     */
    private emitEvent;
}
/**
 * Create a pre-configured platform instance
 */
export declare function createAgenticPlatform(provider?: string): AgenticCoderPlatform;
//# sourceMappingURL=platform.d.ts.map