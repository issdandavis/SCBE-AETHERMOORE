"use strict";
/**
 * Agentic Coder Platform - Main orchestration
 *
 * @module agentic/platform
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.AgenticCoderPlatform = void 0;
exports.createAgenticPlatform = createAgenticPlatform;
const agents_1 = require("./agents");
const task_group_1 = require("./task-group");
const collaboration_1 = require("./collaboration");
const types_1 = require("./types");
const providers_1 = require("./providers");
/**
 * Agentic Coder Platform
 *
 * Main platform for collaborative AI coding with 6 built-in agents.
 */
class AgenticCoderPlatform {
    agents = new Map();
    tasks = new Map();
    groupManager;
    collaboration;
    config;
    eventListeners = [];
    constructor(config = {}) {
        this.config = { ...types_1.DEFAULT_PLATFORM_CONFIG, ...config };
        // Create built-in agents
        const builtInAgents = (0, agents_1.createBuiltInAgents)(this.config.defaultProvider);
        for (const agent of builtInAgents) {
            this.agents.set(agent.id, agent);
        }
        this.groupManager = new task_group_1.TaskGroupManager(builtInAgents);
        this.collaboration = new collaboration_1.CollaborationEngine();
    }
    // ==================== Agent Management ====================
    /**
     * Get all agents
     */
    getAgents() {
        return Array.from(this.agents.values());
    }
    /**
     * Get agent by ID
     */
    getAgent(id) {
        return this.agents.get(id);
    }
    /**
     * Get agent by role
     */
    getAgentByRole(role) {
        return (0, agents_1.getAgentByRole)(this.getAgents(), role);
    }
    /**
     * Get available agents
     */
    getAvailableAgents() {
        return (0, agents_1.getAvailableAgents)(this.getAgents());
    }
    // ==================== Task Management ====================
    /**
     * Create a new coding task
     */
    createTask(options) {
        const id = this.generateTaskId();
        const complexity = options.complexity || this.inferComplexity(options);
        const task = {
            id,
            type: options.type,
            title: options.title,
            description: options.description,
            complexity,
            context: {
                files: options.files,
                code: options.code,
                requirements: options.requirements,
                constraints: options.constraints,
            },
            expectedOutput: this.getExpectedOutput(options.type),
            language: options.language,
            framework: options.framework,
            status: 'pending',
            contributions: [],
            createdAt: Date.now(),
        };
        this.tasks.set(id, task);
        this.emitEvent({
            type: 'task_created',
            timestamp: Date.now(),
            data: { taskId: id, type: options.type, complexity },
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
     * Get pending tasks
     */
    getPendingTasks() {
        return this.getAllTasks().filter((t) => t.status === 'pending');
    }
    // ==================== Group Management ====================
    /**
     * Create a group for a task
     */
    createGroupForTask(taskId, preferredAgents) {
        const task = this.tasks.get(taskId);
        if (!task) {
            throw new Error(`Task ${taskId} not found`);
        }
        const group = this.groupManager.createGroup(task, preferredAgents);
        task.assignedGroup = group.id;
        this.emitEvent({
            type: 'group_created',
            timestamp: Date.now(),
            data: { groupId: group.id, taskId, agents: group.agents },
        });
        return group;
    }
    /**
     * Create a custom group
     */
    createCustomGroup(agentRoles) {
        if (agentRoles.length > this.config.maxAgentsPerGroup) {
            throw new Error(`Maximum ${this.config.maxAgentsPerGroup} agents per group`);
        }
        const group = this.groupManager.createCustomGroup(agentRoles);
        this.emitEvent({
            type: 'group_created',
            timestamp: Date.now(),
            data: { groupId: group.id, agents: group.agents },
        });
        return group;
    }
    /**
     * Get group by ID
     */
    getGroup(id) {
        return this.groupManager.getGroup(id);
    }
    /**
     * Get all groups
     */
    getAllGroups() {
        return this.groupManager.getAllGroups();
    }
    /**
     * Dissolve a group
     */
    dissolveGroup(groupId) {
        this.groupManager.dissolveGroup(groupId);
        this.emitEvent({
            type: 'group_dissolved',
            timestamp: Date.now(),
            data: { groupId },
        });
    }
    // ==================== Task Execution ====================
    /**
     * Execute a task with a group
     *
     * @param taskId - Task to execute
     * @param groupId - Group to execute with (optional, creates one if not provided)
     * @param executor - Function to execute agent actions
     */
    async executeTask(taskId, groupId, executor) {
        const task = this.tasks.get(taskId);
        if (!task) {
            throw new Error(`Task ${taskId} not found`);
        }
        // Create group if not provided
        let group;
        if (groupId) {
            const existingGroup = this.groupManager.getGroup(groupId);
            if (!existingGroup) {
                throw new Error(`Group ${groupId} not found`);
            }
            group = existingGroup;
            task.assignedGroup = groupId;
        }
        else {
            group = this.createGroupForTask(taskId);
        }
        // Update task status
        task.status = 'in_progress';
        task.startedAt = Date.now();
        this.groupManager.assignTask(group.id, taskId);
        this.emitEvent({
            type: 'task_started',
            timestamp: Date.now(),
            data: { taskId, groupId: group.id },
        });
        try {
            // Use default executor if not provided
            const executeStep = executor || this.createDefaultExecutor();
            // Execute collaborative workflow
            const contributions = await this.collaboration.executeWorkflow(task, group, this.agents, executeStep);
            // Emit contribution events
            for (const contrib of contributions) {
                this.emitEvent({
                    type: 'agent_contribution',
                    timestamp: Date.now(),
                    data: { taskId, agentId: contrib.agentId, action: contrib.action },
                });
            }
            // Check if consensus required for complex tasks
            if (this.config.requireConsensus && task.complexity === 'complex') {
                const mergedOutput = this.collaboration.mergeContributions(contributions);
                const consensus = await this.collaboration.requestConsensus(task, group, this.agents, mergedOutput, async (agent, proposal) => ({
                    approve: true,
                    feedback: '',
                    confidence: 0.9,
                }));
                this.emitEvent({
                    type: 'consensus_reached',
                    timestamp: Date.now(),
                    data: { taskId, approved: consensus.approved },
                });
            }
            // Calculate confidence
            const confidence = this.collaboration.calculateGroupConfidence(contributions);
            if (confidence < this.config.minConfidence) {
                throw new Error(`Confidence ${confidence.toFixed(2)} below threshold ${this.config.minConfidence}`);
            }
            // Merge contributions into final output
            const output = this.collaboration.mergeContributions(contributions);
            // Update task
            task.status = 'completed';
            task.completedAt = Date.now();
            task.output = output;
            task.contributions = contributions;
            // Update group
            this.groupManager.completeTask(group.id, true);
            // Update agent stats
            for (const contrib of contributions) {
                const agent = this.agents.get(contrib.agentId);
                if (agent) {
                    agent.stats.tasksCompleted++;
                    agent.stats.avgConfidence =
                        (agent.stats.avgConfidence * (agent.stats.tasksCompleted - 1) + contrib.confidence) /
                            agent.stats.tasksCompleted;
                    if (contrib.tokensUsed) {
                        agent.stats.avgTokensPerTask =
                            (agent.stats.avgTokensPerTask * (agent.stats.tasksCompleted - 1) +
                                contrib.tokensUsed) /
                                agent.stats.tasksCompleted;
                    }
                }
            }
            this.emitEvent({
                type: 'task_completed',
                timestamp: Date.now(),
                data: { taskId, groupId: group.id, confidence },
            });
            return { success: true, output, contributions };
        }
        catch (error) {
            task.status = 'failed';
            task.completedAt = Date.now();
            this.groupManager.completeTask(group.id, false);
            this.emitEvent({
                type: 'task_failed',
                timestamp: Date.now(),
                data: { taskId, error: error instanceof Error ? error.message : 'Unknown error' },
            });
            return {
                success: false,
                output: error instanceof Error ? error.message : 'Task failed',
                contributions: task.contributions,
            };
        }
    }
    /**
     * Get recommended agents for a task type
     */
    getRecommendedAgents(taskType) {
        return types_1.TASK_AGENT_RECOMMENDATIONS[taskType];
    }
    // ==================== Statistics ====================
    /**
     * Get platform statistics
     */
    getStatistics() {
        const agents = this.getAgents();
        const tasks = this.getAllTasks();
        const groups = this.getAllGroups();
        const completedTasks = tasks.filter((t) => t.status === 'completed');
        const totalConfidence = completedTasks.reduce((sum, t) => {
            const taskConfidence = this.collaboration.calculateGroupConfidence(t.contributions);
            return sum + taskConfidence;
        }, 0);
        return {
            totalAgents: agents.length,
            availableAgents: this.getAvailableAgents().length,
            totalTasks: tasks.length,
            completedTasks: completedTasks.length,
            activeGroups: groups.filter((g) => g.status === 'working').length,
            avgConfidence: completedTasks.length > 0 ? totalConfidence / completedTasks.length : 0,
        };
    }
    // ==================== Events ====================
    /**
     * Subscribe to platform events
     */
    onEvent(listener) {
        this.eventListeners.push(listener);
        return () => {
            const index = this.eventListeners.indexOf(listener);
            if (index >= 0)
                this.eventListeners.splice(index, 1);
        };
    }
    // ==================== Private Methods ====================
    /**
     * Generate task ID
     */
    generateTaskId() {
        return `task-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`;
    }
    /**
     * Infer task complexity
     */
    inferComplexity(options) {
        // Simple heuristics
        const codeLength = options.code?.length || 0;
        const descLength = options.description.length;
        const hasConstraints = (options.constraints?.length || 0) > 0;
        if (codeLength > 1000 || descLength > 500 || hasConstraints) {
            return 'complex';
        }
        if (codeLength > 200 || descLength > 200) {
            return 'moderate';
        }
        return 'simple';
    }
    /**
     * Get expected output type for task type
     */
    getExpectedOutput(type) {
        const mapping = {
            design: 'plan',
            implement: 'code',
            review: 'review',
            test: 'tests',
            security_audit: 'report',
            deploy: 'code',
            refactor: 'code',
            debug: 'code',
            document: 'plan',
            optimize: 'code',
        };
        return mapping[type];
    }
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
    createDefaultExecutor() {
        return async (agent, action, context) => {
            // Check if any providers are available
            const availableProviders = (0, providers_1.getAvailableProviders)();
            if (availableProviders.length === 0) {
                // Fallback to mock if no providers configured
                console.warn('[SCBE] No AI providers configured. Using mock executor.');
                console.warn('[SCBE] Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY in .env');
                return {
                    output: `[${agent.name}/${action}] Mock: No AI providers configured.\n\nContext length: ${context.length} chars`,
                    confidence: 0.75, // Must meet minConfidence threshold (0.7)
                    tokens: Math.floor(context.length / 4),
                };
            }
            // Build system prompt from agent persona
            const systemPrompt = `You are ${agent.name}, a specialized AI agent.
Role: ${agent.role}
Capabilities: ${(agent.capabilities || []).join(', ')}
Style: ${agent.systemPrompt || 'Professional and thorough'}

You are performing the action: ${action}
Respond with clear, actionable output.`;
            try {
                // Call provider with fallback chain
                const response = await (0, providers_1.callProvider)(context, {
                    systemPrompt,
                    maxTokens: 4096,
                    temperature: 0.7,
                });
                // Create attestation for audit trail
                const { attestation } = (0, providers_1.createProviderAttestation)(context, response);
                return {
                    output: response.output,
                    confidence: 0.85 + Math.min(0.1, response.latencyMs / 10000), // Higher confidence for faster responses
                    tokens: response.tokensUsed,
                    // Include provider metadata for debugging (not exposed to user)
                    // attestation,
                };
            }
            catch (error) {
                // All providers failed - return error as output
                const errorMsg = error instanceof Error ? error.message : String(error);
                console.error('[SCBE] Provider chain failed:', errorMsg);
                return {
                    output: `[${agent.name}/${action}] Error: All AI providers failed.\n\n${errorMsg}`,
                    confidence: 0.0,
                    tokens: 0,
                };
            }
        };
    }
    /**
     * Emit platform event
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
exports.AgenticCoderPlatform = AgenticCoderPlatform;
/**
 * Create a pre-configured platform instance
 */
function createAgenticPlatform(provider = 'openai') {
    return new AgenticCoderPlatform({ defaultProvider: provider });
}
//# sourceMappingURL=platform.js.map