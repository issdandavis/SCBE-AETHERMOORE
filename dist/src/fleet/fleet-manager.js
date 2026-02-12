"use strict";
/**
 * Fleet Manager - Central orchestration for AI agent fleet
 *
 * Combines AgentRegistry, TaskDispatcher, and GovernanceManager
 * into a unified fleet management system with SCBE security.
 *
 * @module fleet/fleet-manager
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.FleetManager = void 0;
exports.createDefaultFleet = createDefaultFleet;
const spectral_identity_1 = require("../harmonic/spectral-identity");
const trust_manager_1 = require("../spaceTor/trust-manager");
const agent_registry_1 = require("./agent-registry");
const governance_1 = require("./governance");
const polly_pad_1 = require("./polly-pad");
const swarm_1 = require("./swarm");
const task_dispatcher_1 = require("./task-dispatcher");
/**
 * Fleet Manager
 *
 * Central orchestration hub for managing AI agent fleets with
 * SCBE security integration.
 */
class FleetManager {
    trustManager;
    spectralGenerator;
    registry;
    dispatcher;
    governance;
    pollyPadManager;
    swarmCoordinator;
    config;
    eventLog = [];
    eventListeners = [];
    healthCheckInterval;
    constructor(config = {}) {
        this.config = {
            autoAssign: true,
            taskRetentionMs: 24 * 60 * 60 * 1000, // 24 hours
            healthCheckIntervalMs: 60000, // 1 minute
            enableSecurityAlerts: true,
            enablePollyPads: true,
            ...config,
        };
        // Initialize core components
        this.trustManager = new trust_manager_1.TrustManager();
        this.spectralGenerator = new spectral_identity_1.SpectralIdentityGenerator();
        this.registry = new agent_registry_1.AgentRegistry(this.trustManager);
        this.dispatcher = new task_dispatcher_1.TaskDispatcher(this.registry);
        this.governance = new governance_1.GovernanceManager(this.registry);
        // Initialize Polly Pad system if enabled
        if (this.config.enablePollyPads) {
            this.pollyPadManager = new polly_pad_1.PollyPadManager();
            this.swarmCoordinator = new swarm_1.SwarmCoordinator(this.pollyPadManager);
            // Create default swarm if specified
            if (this.config.defaultSwarmId) {
                this.swarmCoordinator.createSwarm({
                    id: this.config.defaultSwarmId,
                    name: 'Default Fleet Swarm',
                    minCoherence: 0.5,
                    fluxDecayRate: 0.01,
                    syncIntervalMs: 5000,
                    maxPads: 50,
                });
                this.swarmCoordinator.startAutoSync(this.config.defaultSwarmId);
            }
        }
        // Wire up event forwarding
        this.registry.onEvent((e) => this.handleEvent(e));
        this.dispatcher.onEvent((e) => this.handleEvent(e));
        this.governance.onEvent((e) => this.handleEvent(e));
        // Start health checks
        if (this.config.healthCheckIntervalMs) {
            this.startHealthChecks();
        }
    }
    // ==================== Agent Management ====================
    /**
     * Register a new agent
     */
    registerAgent(options) {
        const agent = this.registry.registerAgent(options);
        // Auto-create Polly Pad for agent
        if (this.pollyPadManager) {
            const pad = this.pollyPadManager.createPad(agent.id, `${agent.name}'s Pad`, options.maxGovernanceTier || 'KO', options.initialTrustVector || [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]);
            // Add to default swarm if configured
            if (this.swarmCoordinator && this.config.defaultSwarmId) {
                this.swarmCoordinator.addPadToSwarm(this.config.defaultSwarmId, pad.id);
            }
        }
        return agent;
    }
    /**
     * Get agent by ID
     */
    getAgent(id) {
        return this.registry.getAgent(id);
    }
    /**
     * Get all agents
     */
    getAllAgents() {
        return this.registry.getAllAgents();
    }
    /**
     * Get agents by capability
     */
    getAgentsByCapability(capability) {
        return this.registry.getAgentsByCapability(capability);
    }
    /**
     * Update agent trust vector
     */
    updateAgentTrust(agentId, trustVector) {
        this.registry.updateTrustVector(agentId, trustVector);
    }
    /**
     * Suspend an agent
     */
    suspendAgent(agentId) {
        this.registry.updateAgentStatus(agentId, 'suspended');
    }
    /**
     * Reactivate an agent
     */
    reactivateAgent(agentId) {
        this.registry.updateAgentStatus(agentId, 'idle');
    }
    /**
     * Remove an agent
     */
    removeAgent(agentId) {
        return this.registry.removeAgent(agentId);
    }
    // ==================== Task Management ====================
    /**
     * Create a new task
     */
    createTask(options) {
        const task = this.dispatcher.createTask(options);
        // Auto-assign if enabled
        if (this.config.autoAssign) {
            this.dispatcher.assignTask(task.id);
        }
        return task;
    }
    /**
     * Get task by ID
     */
    getTask(id) {
        return this.dispatcher.getTask(id);
    }
    /**
     * Get all tasks
     */
    getAllTasks() {
        return this.dispatcher.getAllTasks();
    }
    /**
     * Get pending tasks
     */
    getPendingTasks() {
        return this.dispatcher.getPendingTasks();
    }
    /**
     * Manually assign a task
     */
    assignTask(taskId) {
        return this.dispatcher.assignTask(taskId);
    }
    /**
     * Complete a task
     */
    completeTask(taskId, output) {
        this.dispatcher.completeTask(taskId, output);
    }
    /**
     * Fail a task
     */
    failTask(taskId, error) {
        this.dispatcher.failTask(taskId, error);
    }
    /**
     * Cancel a task
     */
    cancelTask(taskId) {
        this.dispatcher.cancelTask(taskId);
    }
    // ==================== Governance ====================
    /**
     * Create a roundtable session
     */
    createRoundtable(options) {
        return this.governance.createRoundtable(options);
    }
    /**
     * Cast vote in roundtable
     */
    castVote(sessionId, agentId, vote) {
        return this.governance.castVote(sessionId, agentId, vote);
    }
    /**
     * Get active roundtable sessions
     */
    getActiveRoundtables() {
        return this.governance.getActiveSessions();
    }
    /**
     * Check if agent can perform action
     */
    canPerformAction(agentId, action) {
        return this.governance.canPerformAction(agentId, action);
    }
    /**
     * Get required governance tier for action
     */
    getRequiredTier(action) {
        return this.governance.getRequiredTier(action);
    }
    // ==================== Polly Pads ====================
    /**
     * Get Polly Pad for an agent
     */
    getAgentPad(agentId) {
        return this.pollyPadManager?.getPadByAgent(agentId);
    }
    /**
     * Get all Polly Pads
     */
    getAllPads() {
        return this.pollyPadManager?.getAllPads() ?? [];
    }
    /**
     * Add note to agent's pad
     */
    addPadNote(agentId, title, content, tags = []) {
        const pad = this.pollyPadManager?.getPadByAgent(agentId);
        if (!pad || !this.pollyPadManager)
            return undefined;
        return this.pollyPadManager.addNote(pad.id, {
            title,
            content,
            tags,
            shared: false,
        });
    }
    /**
     * Add sketch to agent's pad
     */
    addPadSketch(agentId, name, data, type = 'freehand') {
        const pad = this.pollyPadManager?.getPadByAgent(agentId);
        if (!pad || !this.pollyPadManager)
            return undefined;
        return this.pollyPadManager.addSketch(pad.id, {
            name,
            data,
            type,
            shared: false,
        });
    }
    /**
     * Add tool to agent's pad
     */
    addPadTool(agentId, name, description, type, content) {
        const pad = this.pollyPadManager?.getPadByAgent(agentId);
        if (!pad || !this.pollyPadManager)
            return undefined;
        return this.pollyPadManager.addTool(pad.id, {
            name,
            description,
            type,
            content,
        });
    }
    /**
     * Record task completion on agent's pad
     */
    recordPadTaskCompletion(agentId, success) {
        const pad = this.pollyPadManager?.getPadByAgent(agentId);
        if (!pad || !this.pollyPadManager)
            return;
        this.pollyPadManager.recordTaskCompletion(pad.id, success);
    }
    /**
     * Audit an agent's pad
     */
    auditPad(agentId, auditorId) {
        const pad = this.pollyPadManager?.getPadByAgent(agentId);
        if (!pad || !this.pollyPadManager)
            return undefined;
        return this.pollyPadManager.auditPad(pad.id, auditorId);
    }
    /**
     * Get pad statistics for an agent
     */
    getPadStats(agentId) {
        const pad = this.pollyPadManager?.getPadByAgent(agentId);
        if (!pad || !this.pollyPadManager)
            return undefined;
        return this.pollyPadManager.getPadStats(pad.id);
    }
    /**
     * Get swarm coordinator
     */
    getSwarmCoordinator() {
        return this.swarmCoordinator;
    }
    /**
     * Get Polly Pad manager
     */
    getPollyPadManager() {
        return this.pollyPadManager;
    }
    // ==================== Fleet Statistics ====================
    /**
     * Get comprehensive fleet statistics
     */
    getStatistics() {
        const registryStats = this.registry.getStatistics();
        const dispatcherStats = this.dispatcher.getStatistics();
        const governanceStats = this.governance.getStatistics();
        return {
            totalAgents: registryStats.totalAgents,
            agentsByStatus: registryStats.byStatus,
            agentsByTrustLevel: registryStats.byTrustLevel,
            totalTasks: dispatcherStats.totalTasks,
            tasksByStatus: dispatcherStats.byStatus,
            avgCompletionTimeMs: dispatcherStats.avgCompletionTimeMs,
            fleetSuccessRate: registryStats.avgSuccessRate,
            activeRoundtables: governanceStats.activeSessions,
        };
    }
    /**
     * Get fleet health status
     */
    getHealthStatus() {
        const stats = this.getStatistics();
        const issues = [];
        // Check for issues
        if (stats.agentsByStatus.quarantined > 0) {
            issues.push(`${stats.agentsByStatus.quarantined} agent(s) quarantined`);
        }
        if (stats.agentsByTrustLevel.CRITICAL > 0) {
            issues.push(`${stats.agentsByTrustLevel.CRITICAL} agent(s) with critical trust`);
        }
        if (stats.fleetSuccessRate < 0.8) {
            issues.push(`Fleet success rate below 80%: ${(stats.fleetSuccessRate * 100).toFixed(1)}%`);
        }
        const pendingTasks = stats.tasksByStatus.pending || 0;
        if (pendingTasks > 10) {
            issues.push(`${pendingTasks} tasks pending assignment`);
        }
        return {
            healthy: issues.length === 0,
            issues,
            metrics: {
                totalAgents: stats.totalAgents,
                activeAgents: stats.agentsByStatus.idle + stats.agentsByStatus.busy,
                pendingTasks,
                successRate: stats.fleetSuccessRate,
                activeRoundtables: stats.activeRoundtables,
            },
        };
    }
    // ==================== Event Management ====================
    /**
     * Subscribe to fleet events
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
     * Get recent events
     */
    getRecentEvents(limit = 100) {
        return this.eventLog.slice(-limit);
    }
    /**
     * Get events by type
     */
    getEventsByType(type, limit = 50) {
        return this.eventLog.filter((e) => e.type === type).slice(-limit);
    }
    // ==================== Lifecycle ====================
    /**
     * Shutdown fleet manager
     */
    shutdown() {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
        }
        // Shutdown swarm coordinator
        if (this.swarmCoordinator) {
            this.swarmCoordinator.shutdown();
        }
        // Cancel all pending tasks
        for (const task of this.getPendingTasks()) {
            this.cancelTask(task.id);
        }
    }
    // ==================== Private Methods ====================
    /**
     * Handle internal events
     */
    handleEvent(event) {
        // Log event
        this.eventLog.push(event);
        // Trim log if too large
        if (this.eventLog.length > 10000) {
            this.eventLog = this.eventLog.slice(-5000);
        }
        // Forward to listeners
        for (const listener of this.eventListeners) {
            try {
                listener(event);
            }
            catch (e) {
                console.error('Event listener error:', e);
            }
        }
        // Handle security alerts
        if (this.config.enableSecurityAlerts && event.type === 'security_alert') {
            console.warn('[FLEET SECURITY ALERT]', event.data);
        }
    }
    /**
     * Start health check interval
     */
    startHealthChecks() {
        this.healthCheckInterval = setInterval(() => {
            const health = this.getHealthStatus();
            if (!health.healthy) {
                this.handleEvent({
                    type: 'security_alert',
                    timestamp: Date.now(),
                    data: {
                        alert: 'Fleet health check failed',
                        issues: health.issues,
                        metrics: health.metrics,
                    },
                });
            }
        }, this.config.healthCheckIntervalMs);
    }
}
exports.FleetManager = FleetManager;
/**
 * Create a pre-configured fleet manager with common agents
 */
function createDefaultFleet() {
    const fleet = new FleetManager();
    // Register common agent types
    fleet.registerAgent({
        name: 'CodeGen-GPT4',
        description: 'Code generation specialist using GPT-4',
        provider: 'openai',
        model: 'gpt-4o',
        capabilities: ['code_generation', 'code_review', 'documentation'],
        maxGovernanceTier: 'CA',
        initialTrustVector: [0.7, 0.6, 0.8, 0.5, 0.6, 0.4],
    });
    fleet.registerAgent({
        name: 'Security-Claude',
        description: 'Security analysis specialist using Claude',
        provider: 'anthropic',
        model: 'claude-3-opus',
        capabilities: ['security_scan', 'code_review', 'testing'],
        maxGovernanceTier: 'UM',
        initialTrustVector: [0.8, 0.7, 0.9, 0.6, 0.7, 0.5],
    });
    fleet.registerAgent({
        name: 'Deploy-Bot',
        description: 'Deployment automation agent',
        provider: 'openai',
        model: 'gpt-4o-mini',
        capabilities: ['deployment', 'monitoring'],
        maxGovernanceTier: 'CA',
        initialTrustVector: [0.6, 0.5, 0.7, 0.8, 0.5, 0.4],
    });
    fleet.registerAgent({
        name: 'Test-Runner',
        description: 'Automated testing agent',
        provider: 'anthropic',
        model: 'claude-3-sonnet',
        capabilities: ['testing', 'code_review'],
        maxGovernanceTier: 'RU',
        initialTrustVector: [0.5, 0.6, 0.7, 0.5, 0.6, 0.3],
    });
    return fleet;
}
//# sourceMappingURL=fleet-manager.js.map