"use strict";
/**
 * Task Dispatcher - Assigns tasks to agents based on trust and capability
 *
 * @module fleet/task-dispatcher
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.TaskDispatcher = void 0;
const types_1 = require("./types");
/**
 * Task Dispatcher
 *
 * Manages task queue and assigns tasks to appropriate agents.
 */
class TaskDispatcher {
    tasks = new Map();
    taskQueue = [];
    registry;
    eventListeners = [];
    constructor(registry) {
        this.registry = registry;
    }
    /**
     * Create a new task
     */
    createTask(options) {
        const id = this.generateTaskId();
        const tierReq = types_1.GOVERNANCE_TIERS[options.requiredTier];
        const task = {
            id,
            name: options.name,
            description: options.description,
            requiredCapability: options.requiredCapability,
            requiredTier: options.requiredTier,
            priority: options.priority || 'medium',
            status: 'pending',
            input: options.input,
            minTrustScore: options.minTrustScore ?? tierReq.minTrustScore,
            requiresApproval: options.requiresApproval ??
                (options.requiredTier === 'DR' || options.requiredTier === 'UM'),
            requiredApprovals: options.requiredApprovals ?? tierReq.requiredTongues,
            createdAt: Date.now(),
            timeoutMs: options.timeoutMs || 300000, // 5 minutes default
            retryCount: 0,
            maxRetries: options.maxRetries ?? 3,
        };
        this.tasks.set(id, task);
        this.addToQueue(id);
        this.emitEvent({
            type: 'task_created',
            timestamp: Date.now(),
            taskId: id,
            data: {
                name: task.name,
                priority: task.priority,
                requiredTier: task.requiredTier,
                requiresApproval: task.requiresApproval,
            },
        });
        return task;
    }
    /**
     * Get task by ID
     */
    getTask(id) {
        return this.tasks.get(id);
    }
    /**
     * Get all tasks
     */
    getAllTasks() {
        return Array.from(this.tasks.values());
    }
    /**
     * Get tasks by status
     */
    getTasksByStatus(status) {
        return this.getAllTasks().filter((t) => t.status === status);
    }
    /**
     * Get pending tasks in priority order
     */
    getPendingTasks() {
        return this.taskQueue
            .map((id) => this.tasks.get(id))
            .filter((t) => t !== undefined && t.status === 'pending')
            .sort((a, b) => types_1.PRIORITY_WEIGHTS[b.priority] - types_1.PRIORITY_WEIGHTS[a.priority]);
    }
    /**
     * Assign task to best available agent
     */
    assignTask(taskId) {
        const task = this.tasks.get(taskId);
        if (!task) {
            return { success: false, taskId, reason: 'Task not found' };
        }
        if (task.status !== 'pending') {
            return { success: false, taskId, reason: `Task is ${task.status}, not pending` };
        }
        // Find eligible agents
        const eligibleAgents = this.findEligibleAgents(task);
        if (eligibleAgents.length === 0) {
            return { success: false, taskId, reason: 'No eligible agents available' };
        }
        // Select best agent
        const bestAgent = this.selectBestAgent(eligibleAgents, task);
        // Check if approval is required
        if (task.requiresApproval) {
            task.status = 'awaiting_approval';
            task.approvalVotes = [];
            this.emitEvent({
                type: 'task_assigned',
                timestamp: Date.now(),
                taskId,
                agentId: bestAgent.id,
                data: {
                    status: 'awaiting_approval',
                    requiredApprovals: task.requiredApprovals,
                },
            });
            return {
                success: true,
                taskId,
                assignedAgentId: bestAgent.id,
                reason: 'Awaiting roundtable approval',
            };
        }
        // Assign directly
        return this.executeAssignment(task, bestAgent);
    }
    /**
     * Auto-assign all pending tasks
     */
    autoAssignPendingTasks() {
        const results = [];
        const pendingTasks = this.getPendingTasks();
        for (const task of pendingTasks) {
            const result = this.assignTask(task.id);
            results.push(result);
        }
        return results;
    }
    /**
     * Approve task (for roundtable consensus)
     */
    approveTask(taskId, agentId) {
        const task = this.tasks.get(taskId);
        if (!task || task.status !== 'awaiting_approval') {
            return false;
        }
        if (!task.approvalVotes) {
            task.approvalVotes = [];
        }
        if (task.approvalVotes.includes(agentId)) {
            return false; // Already voted
        }
        task.approvalVotes.push(agentId);
        this.emitEvent({
            type: 'roundtable_vote',
            timestamp: Date.now(),
            taskId,
            agentId,
            data: {
                vote: 'approve',
                currentVotes: task.approvalVotes.length,
                requiredVotes: task.requiredApprovals,
            },
        });
        // Check if we have enough approvals
        if (task.approvalVotes.length >= task.requiredApprovals) {
            const agent = this.registry.getAgent(task.assignedAgentId);
            if (agent) {
                this.executeAssignment(task, agent);
            }
        }
        return true;
    }
    /**
     * Complete task
     */
    completeTask(taskId, output) {
        const task = this.tasks.get(taskId);
        if (!task) {
            throw new Error(`Task ${taskId} not found`);
        }
        task.status = 'completed';
        task.output = output;
        task.completedAt = Date.now();
        // Update agent stats
        if (task.assignedAgentId) {
            this.registry.recordTaskCompletion(task.assignedAgentId, true);
        }
        this.removeFromQueue(taskId);
        this.emitEvent({
            type: 'task_completed',
            timestamp: Date.now(),
            taskId,
            agentId: task.assignedAgentId,
            data: {
                duration: task.completedAt - (task.startedAt || task.createdAt),
                output,
            },
        });
    }
    /**
     * Fail task
     */
    failTask(taskId, error) {
        const task = this.tasks.get(taskId);
        if (!task) {
            throw new Error(`Task ${taskId} not found`);
        }
        task.retryCount++;
        // Check if we should retry
        if (task.retryCount < task.maxRetries) {
            task.status = 'pending';
            task.assignedAgentId = undefined;
            task.startedAt = undefined;
            this.emitEvent({
                type: 'task_failed',
                timestamp: Date.now(),
                taskId,
                data: { error, retrying: true, retryCount: task.retryCount },
            });
            return;
        }
        // Final failure
        task.status = 'failed';
        task.error = error;
        task.completedAt = Date.now();
        // Update agent stats
        if (task.assignedAgentId) {
            this.registry.recordTaskCompletion(task.assignedAgentId, false);
        }
        this.removeFromQueue(taskId);
        this.emitEvent({
            type: 'task_failed',
            timestamp: Date.now(),
            taskId,
            agentId: task.assignedAgentId,
            data: { error, retrying: false },
        });
    }
    /**
     * Cancel task
     */
    cancelTask(taskId) {
        const task = this.tasks.get(taskId);
        if (!task) {
            throw new Error(`Task ${taskId} not found`);
        }
        task.status = 'cancelled';
        task.completedAt = Date.now();
        // Release agent if assigned
        if (task.assignedAgentId) {
            const agent = this.registry.getAgent(task.assignedAgentId);
            if (agent) {
                agent.currentTaskCount = Math.max(0, agent.currentTaskCount - 1);
                if (agent.currentTaskCount === 0) {
                    agent.status = 'idle';
                }
            }
        }
        this.removeFromQueue(taskId);
        this.emitEvent({
            type: 'task_cancelled',
            timestamp: Date.now(),
            taskId,
            agentId: task.assignedAgentId,
            data: {},
        });
    }
    /**
     * Get dispatcher statistics
     */
    getStatistics() {
        const tasks = this.getAllTasks();
        const byStatus = {
            pending: 0,
            assigned: 0,
            running: 0,
            completed: 0,
            failed: 0,
            cancelled: 0,
            awaiting_approval: 0,
        };
        const byPriority = {
            critical: 0,
            high: 0,
            medium: 0,
            low: 0,
        };
        let totalCompletionTime = 0;
        let completedCount = 0;
        for (const task of tasks) {
            byStatus[task.status]++;
            byPriority[task.priority]++;
            if (task.status === 'completed' && task.startedAt && task.completedAt) {
                totalCompletionTime += task.completedAt - task.startedAt;
                completedCount++;
            }
        }
        return {
            totalTasks: tasks.length,
            byStatus,
            byPriority,
            avgCompletionTimeMs: completedCount > 0 ? totalCompletionTime / completedCount : 0,
            queueLength: this.taskQueue.length,
        };
    }
    /**
     * Subscribe to events
     */
    onEvent(listener) {
        this.eventListeners.push(listener);
        return () => {
            const index = this.eventListeners.indexOf(listener);
            if (index >= 0)
                this.eventListeners.splice(index, 1);
        };
    }
    /**
     * Find agents eligible for a task
     */
    findEligibleAgents(task) {
        const allAgents = this.registry.getAllAgents();
        return allAgents.filter((agent) => {
            // Must have required capability
            if (!agent.capabilities.includes(task.requiredCapability))
                return false;
            // Must be available
            if (agent.status !== 'idle' && agent.status !== 'busy')
                return false;
            // Must have capacity
            if (agent.currentTaskCount >= agent.maxConcurrentTasks)
                return false;
            // Must meet governance tier
            const tierOrder = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
            const requiredIndex = tierOrder.indexOf(task.requiredTier);
            const agentIndex = tierOrder.indexOf(agent.maxGovernanceTier);
            if (agentIndex < requiredIndex)
                return false;
            // Must meet trust score
            const normalizedTrust = 1 - (agent.trustScore?.normalized || 1);
            if (normalizedTrust < task.minTrustScore)
                return false;
            return true;
        });
    }
    /**
     * Select best agent from eligible list
     */
    selectBestAgent(agents, task) {
        // Score each agent
        const scored = agents.map((agent) => {
            let score = 0;
            // Trust score (higher is better, but normalized is inverted)
            const trustScore = 1 - (agent.trustScore?.normalized || 0.5);
            score += trustScore * 40;
            // Success rate
            score += agent.successRate * 30;
            // Availability (fewer current tasks is better)
            const availability = 1 - agent.currentTaskCount / agent.maxConcurrentTasks;
            score += availability * 20;
            // Recency (more recent activity is better)
            const hoursSinceActive = (Date.now() - agent.lastActiveAt) / (1000 * 60 * 60);
            score += Math.max(0, 10 - hoursSinceActive);
            return { agent, score };
        });
        // Sort by score descending
        scored.sort((a, b) => b.score - a.score);
        return scored[0].agent;
    }
    /**
     * Execute task assignment
     */
    executeAssignment(task, agent) {
        try {
            this.registry.assignTask(agent.id);
            task.status = 'assigned';
            task.assignedAgentId = agent.id;
            task.startedAt = Date.now();
            this.emitEvent({
                type: 'task_assigned',
                timestamp: Date.now(),
                taskId: task.id,
                agentId: agent.id,
                data: {
                    agentName: agent.name,
                    trustLevel: agent.trustScore?.level,
                },
            });
            // Mark as running
            task.status = 'running';
            this.emitEvent({
                type: 'task_started',
                timestamp: Date.now(),
                taskId: task.id,
                agentId: agent.id,
                data: {},
            });
            return {
                success: true,
                taskId: task.id,
                assignedAgentId: agent.id,
            };
        }
        catch (error) {
            return {
                success: false,
                taskId: task.id,
                reason: error instanceof Error ? error.message : 'Assignment failed',
            };
        }
    }
    /**
     * Add task to queue
     */
    addToQueue(taskId) {
        if (!this.taskQueue.includes(taskId)) {
            this.taskQueue.push(taskId);
        }
    }
    /**
     * Remove task from queue
     */
    removeFromQueue(taskId) {
        const index = this.taskQueue.indexOf(taskId);
        if (index >= 0) {
            this.taskQueue.splice(index, 1);
        }
    }
    /**
     * Generate unique task ID
     */
    generateTaskId() {
        const timestamp = Date.now().toString(36);
        const random = Math.random().toString(36).substring(2, 8);
        return `task-${timestamp}-${random}`;
    }
    /**
     * Emit event
     */
    emitEvent(event) {
        for (const listener of this.eventListeners) {
            try {
                listener(event);
            }
            catch (e) {
                console.error('Event listener error:', e);
            }
        }
    }
}
exports.TaskDispatcher = TaskDispatcher;
//# sourceMappingURL=task-dispatcher.js.map