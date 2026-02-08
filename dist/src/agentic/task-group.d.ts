/**
 * Task Group - Manages groups of 1-3 agents working together
 *
 * @module agentic/task-group
 */
import { AgentRole, BuiltInAgent, CodingTask, CodingTaskType, TaskComplexity, TaskGroup } from './types';
/**
 * Task Group Manager
 *
 * Creates and manages groups of agents for collaborative coding tasks.
 */
export declare class TaskGroupManager {
    private groups;
    private agents;
    constructor(agents: BuiltInAgent[]);
    /**
     * Create a task group for a specific task
     */
    createGroup(task: CodingTask, preferredAgents?: AgentRole[]): TaskGroup;
    /**
     * Create a custom group with specific agents
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
     * Get active groups
     */
    getActiveGroups(): TaskGroup[];
    /**
     * Assign task to group
     */
    assignTask(groupId: string, taskId: string): void;
    /**
     * Complete task for group
     */
    completeTask(groupId: string, success: boolean): void;
    /**
     * Dissolve a group and release agents
     */
    dissolveGroup(groupId: string): void;
    /**
     * Get agents in a group
     */
    getGroupAgents(groupId: string): BuiltInAgent[];
    /**
     * Get lead agent for a group (first agent)
     */
    getLeadAgent(groupId: string): BuiltInAgent | undefined;
    /**
     * Recommend group composition for a task
     */
    recommendGroup(taskType: CodingTaskType, complexity: TaskComplexity): AgentRole[];
    /**
     * Select agents for a group
     */
    private selectAgents;
    /**
     * Get available agent by role
     */
    private getAvailableAgentByRole;
    /**
     * Generate group ID
     */
    private generateGroupId;
    /**
     * Generate group name from agents
     */
    private generateGroupName;
    /**
     * Get collaboration mode for group size
     */
    private getModeForSize;
}
//# sourceMappingURL=task-group.d.ts.map