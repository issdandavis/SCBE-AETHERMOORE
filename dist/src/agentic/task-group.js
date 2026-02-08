"use strict";
/**
 * Task Group - Manages groups of 1-3 agents working together
 *
 * @module agentic/task-group
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.TaskGroupManager = void 0;
const types_1 = require("./types");
/**
 * Task Group Manager
 *
 * Creates and manages groups of agents for collaborative coding tasks.
 */
class TaskGroupManager {
    groups = new Map();
    agents = new Map();
    constructor(agents) {
        for (const agent of agents) {
            this.agents.set(agent.id, agent);
        }
    }
    /**
     * Create a task group for a specific task
     */
    createGroup(task, preferredAgents) {
        // Determine group size based on complexity
        const mode = types_1.COMPLEXITY_GROUP_SIZE[task.complexity];
        const groupSize = mode === 'solo' ? 1 : mode === 'pair' ? 2 : 3;
        // Get recommended agents for this task type
        const recommended = preferredAgents || types_1.TASK_AGENT_RECOMMENDATIONS[task.type];
        // Select available agents
        const selectedAgents = this.selectAgents(recommended, groupSize);
        if (selectedAgents.length === 0) {
            throw new Error('No available agents for this task');
        }
        const id = this.generateGroupId();
        const group = {
            id,
            name: this.generateGroupName(selectedAgents),
            agents: selectedAgents.map((a) => a.id),
            currentTask: task.id,
            mode: this.getModeForSize(selectedAgents.length),
            status: 'idle',
            tasksCompleted: 0,
            successRate: 1.0,
            createdAt: Date.now(),
        };
        // Mark agents as busy
        for (const agent of selectedAgents) {
            agent.status = 'busy';
            agent.currentGroup = id;
        }
        this.groups.set(id, group);
        return group;
    }
    /**
     * Create a custom group with specific agents
     */
    createCustomGroup(agentRoles) {
        if (agentRoles.length < 1 || agentRoles.length > 3) {
            throw new Error('Group must have 1-3 agents');
        }
        const selectedAgents = [];
        for (const role of agentRoles) {
            const agent = this.getAvailableAgentByRole(role);
            if (!agent) {
                throw new Error(`No available agent for role: ${role}`);
            }
            selectedAgents.push(agent);
        }
        const id = this.generateGroupId();
        const group = {
            id,
            name: this.generateGroupName(selectedAgents),
            agents: selectedAgents.map((a) => a.id),
            mode: this.getModeForSize(selectedAgents.length),
            status: 'idle',
            tasksCompleted: 0,
            successRate: 1.0,
            createdAt: Date.now(),
        };
        // Mark agents as busy
        for (const agent of selectedAgents) {
            agent.status = 'busy';
            agent.currentGroup = id;
        }
        this.groups.set(id, group);
        return group;
    }
    /**
     * Get group by ID
     */
    getGroup(id) {
        return this.groups.get(id);
    }
    /**
     * Get all groups
     */
    getAllGroups() {
        return Array.from(this.groups.values());
    }
    /**
     * Get active groups
     */
    getActiveGroups() {
        return this.getAllGroups().filter((g) => g.status === 'working' || g.status === 'reviewing');
    }
    /**
     * Assign task to group
     */
    assignTask(groupId, taskId) {
        const group = this.groups.get(groupId);
        if (!group) {
            throw new Error(`Group ${groupId} not found`);
        }
        group.currentTask = taskId;
        group.status = 'working';
    }
    /**
     * Complete task for group
     */
    completeTask(groupId, success) {
        const group = this.groups.get(groupId);
        if (!group) {
            throw new Error(`Group ${groupId} not found`);
        }
        group.tasksCompleted++;
        group.currentTask = undefined;
        group.status = 'idle';
        // Update success rate
        const alpha = 0.2;
        group.successRate = alpha * (success ? 1 : 0) + (1 - alpha) * group.successRate;
    }
    /**
     * Dissolve a group and release agents
     */
    dissolveGroup(groupId) {
        const group = this.groups.get(groupId);
        if (!group)
            return;
        // Release agents
        for (const agentId of group.agents) {
            const agent = this.agents.get(agentId);
            if (agent) {
                agent.status = 'available';
                agent.currentGroup = undefined;
            }
        }
        this.groups.delete(groupId);
    }
    /**
     * Get agents in a group
     */
    getGroupAgents(groupId) {
        const group = this.groups.get(groupId);
        if (!group)
            return [];
        return group.agents
            .map((id) => this.agents.get(id))
            .filter((a) => a !== undefined);
    }
    /**
     * Get lead agent for a group (first agent)
     */
    getLeadAgent(groupId) {
        const agents = this.getGroupAgents(groupId);
        return agents[0];
    }
    /**
     * Recommend group composition for a task
     */
    recommendGroup(taskType, complexity) {
        const recommended = types_1.TASK_AGENT_RECOMMENDATIONS[taskType];
        const mode = types_1.COMPLEXITY_GROUP_SIZE[complexity];
        const size = mode === 'solo' ? 1 : mode === 'pair' ? 2 : 3;
        return recommended.slice(0, size);
    }
    /**
     * Select agents for a group
     */
    selectAgents(roles, maxSize) {
        const selected = [];
        for (const role of roles) {
            if (selected.length >= maxSize)
                break;
            const agent = this.getAvailableAgentByRole(role);
            if (agent && !selected.includes(agent)) {
                selected.push(agent);
            }
        }
        return selected;
    }
    /**
     * Get available agent by role
     */
    getAvailableAgentByRole(role) {
        for (const agent of this.agents.values()) {
            if (agent.role === role && agent.status === 'available') {
                return agent;
            }
        }
        return undefined;
    }
    /**
     * Generate group ID
     */
    generateGroupId() {
        const timestamp = Date.now().toString(36);
        const random = Math.random().toString(36).substring(2, 6);
        return `grp-${timestamp}-${random}`;
    }
    /**
     * Generate group name from agents
     */
    generateGroupName(agents) {
        if (agents.length === 1) {
            return `Solo-${agents[0].name}`;
        }
        return agents.map((a) => a.name).join('-');
    }
    /**
     * Get collaboration mode for group size
     */
    getModeForSize(size) {
        if (size === 1)
            return 'solo';
        if (size === 2)
            return 'pair';
        return 'trio';
    }
}
exports.TaskGroupManager = TaskGroupManager;
//# sourceMappingURL=task-group.js.map