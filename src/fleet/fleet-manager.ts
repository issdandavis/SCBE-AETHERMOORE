/**
 * Fleet Manager - Central orchestration for AI agent fleet
 *
 * Combines AgentRegistry, TaskDispatcher, and GovernanceManager
 * into a unified fleet management system with SCBE security.
 *
 * @module fleet/fleet-manager
 */

import { SpectralIdentityGenerator } from '../harmonic/spectral-identity';
import { TrustManager } from '../spaceTor/trust-manager';
import { AgentRegistrationOptions, AgentRegistry } from './agent-registry';
import { GovernanceManager, RoundtableOptions } from './governance';
import { PollyPad, PollyPadManager } from './polly-pad';
import { SwarmCoordinator } from './swarm';
import { TaskCreationOptions, TaskDispatcher } from './task-dispatcher';
import {
  AgentCapability,
  FleetAgent,
  FleetEvent,
  FleetStats,
  FleetTask,
  GovernanceTier,
} from './types';

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
export class FleetManager {
  private trustManager: TrustManager;
  private spectralGenerator: SpectralIdentityGenerator;
  private registry: AgentRegistry;
  private dispatcher: TaskDispatcher;
  private governance: GovernanceManager;
  private pollyPadManager?: PollyPadManager;
  private swarmCoordinator?: SwarmCoordinator;
  private config: FleetManagerConfig;
  private eventLog: FleetEvent[] = [];
  private eventListeners: ((event: FleetEvent) => void)[] = [];
  private healthCheckInterval?: NodeJS.Timeout;

  constructor(config: FleetManagerConfig = {}) {
    this.config = {
      autoAssign: true,
      taskRetentionMs: 24 * 60 * 60 * 1000, // 24 hours
      healthCheckIntervalMs: 60000, // 1 minute
      enableSecurityAlerts: true,
      enablePollyPads: true,
      ...config,
    };

    // Initialize core components
    this.trustManager = new TrustManager();
    this.spectralGenerator = new SpectralIdentityGenerator();
    this.registry = new AgentRegistry(this.trustManager);
    this.dispatcher = new TaskDispatcher(this.registry);
    this.governance = new GovernanceManager(this.registry);

    // Initialize Polly Pad system if enabled
    if (this.config.enablePollyPads) {
      this.pollyPadManager = new PollyPadManager();
      this.swarmCoordinator = new SwarmCoordinator(this.pollyPadManager);

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
  public registerAgent(options: AgentRegistrationOptions): FleetAgent {
    const agent = this.registry.registerAgent(options);

    // Auto-create Polly Pad for agent
    if (this.pollyPadManager) {
      const pad = this.pollyPadManager.createPad(
        agent.id,
        `${agent.name}'s Pad`,
        options.maxGovernanceTier || 'KO',
        options.initialTrustVector || [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
      );

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
  public getAgent(id: string): FleetAgent | undefined {
    return this.registry.getAgent(id);
  }

  /**
   * Get all agents
   */
  public getAllAgents(): FleetAgent[] {
    return this.registry.getAllAgents();
  }

  /**
   * Get agents by capability
   */
  public getAgentsByCapability(capability: AgentCapability): FleetAgent[] {
    return this.registry.getAgentsByCapability(capability);
  }

  /**
   * Update agent trust vector
   */
  public updateAgentTrust(agentId: string, trustVector: number[]): void {
    this.registry.updateTrustVector(agentId, trustVector);
  }

  /**
   * Suspend an agent
   */
  public suspendAgent(agentId: string): void {
    this.registry.updateAgentStatus(agentId, 'suspended');
  }

  /**
   * Reactivate an agent
   */
  public reactivateAgent(agentId: string): void {
    this.registry.updateAgentStatus(agentId, 'idle');
  }

  /**
   * Remove an agent
   */
  public removeAgent(agentId: string): boolean {
    return this.registry.removeAgent(agentId);
  }

  // ==================== Task Management ====================

  /**
   * Create a new task
   */
  public createTask(options: TaskCreationOptions): FleetTask {
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
  public getTask(id: string): FleetTask | undefined {
    return this.dispatcher.getTask(id);
  }

  /**
   * Get all tasks
   */
  public getAllTasks(): FleetTask[] {
    return this.dispatcher.getAllTasks();
  }

  /**
   * Get pending tasks
   */
  public getPendingTasks(): FleetTask[] {
    return this.dispatcher.getPendingTasks();
  }

  /**
   * Manually assign a task
   */
  public assignTask(taskId: string) {
    return this.dispatcher.assignTask(taskId);
  }

  /**
   * Complete a task
   */
  public completeTask(taskId: string, output: Record<string, unknown>): void {
    this.dispatcher.completeTask(taskId, output);
  }

  /**
   * Fail a task
   */
  public failTask(taskId: string, error: string): void {
    this.dispatcher.failTask(taskId, error);
  }

  /**
   * Cancel a task
   */
  public cancelTask(taskId: string): void {
    this.dispatcher.cancelTask(taskId);
  }

  // ==================== Governance ====================

  /**
   * Create a roundtable session
   */
  public createRoundtable(options: RoundtableOptions) {
    return this.governance.createRoundtable(options);
  }

  /**
   * Cast vote in roundtable
   */
  public castVote(sessionId: string, agentId: string, vote: 'approve' | 'reject' | 'abstain') {
    return this.governance.castVote(sessionId, agentId, vote);
  }

  /**
   * Get active roundtable sessions
   */
  public getActiveRoundtables() {
    return this.governance.getActiveSessions();
  }

  /**
   * Check if agent can perform action
   */
  public canPerformAction(agentId: string, action: string) {
    return this.governance.canPerformAction(agentId, action);
  }

  /**
   * Get required governance tier for action
   */
  public getRequiredTier(action: string): GovernanceTier {
    return this.governance.getRequiredTier(action);
  }

  // ==================== Polly Pads ====================

  /**
   * Get Polly Pad for an agent
   */
  public getAgentPad(agentId: string): PollyPad | undefined {
    return this.pollyPadManager?.getPadByAgent(agentId);
  }

  /**
   * Get all Polly Pads
   */
  public getAllPads(): PollyPad[] {
    return this.pollyPadManager?.getAllPads() ?? [];
  }

  /**
   * Add note to agent's pad
   */
  public addPadNote(agentId: string, title: string, content: string, tags: string[] = []) {
    const pad = this.pollyPadManager?.getPadByAgent(agentId);
    if (!pad || !this.pollyPadManager) return undefined;

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
  public addPadSketch(
    agentId: string,
    name: string,
    data: string,
    type: 'diagram' | 'flowchart' | 'wireframe' | 'freehand' | 'architecture' = 'freehand'
  ) {
    const pad = this.pollyPadManager?.getPadByAgent(agentId);
    if (!pad || !this.pollyPadManager) return undefined;

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
  public addPadTool(
    agentId: string,
    name: string,
    description: string,
    type: 'snippet' | 'template' | 'script' | 'prompt' | 'config',
    content: string
  ) {
    const pad = this.pollyPadManager?.getPadByAgent(agentId);
    if (!pad || !this.pollyPadManager) return undefined;

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
  public recordPadTaskCompletion(agentId: string, success: boolean): void {
    const pad = this.pollyPadManager?.getPadByAgent(agentId);
    if (!pad || !this.pollyPadManager) return;

    this.pollyPadManager.recordTaskCompletion(pad.id, success);
  }

  /**
   * Audit an agent's pad
   */
  public auditPad(agentId: string, auditorId: string) {
    const pad = this.pollyPadManager?.getPadByAgent(agentId);
    if (!pad || !this.pollyPadManager) return undefined;

    return this.pollyPadManager.auditPad(pad.id, auditorId);
  }

  /**
   * Get pad statistics for an agent
   */
  public getPadStats(agentId: string) {
    const pad = this.pollyPadManager?.getPadByAgent(agentId);
    if (!pad || !this.pollyPadManager) return undefined;

    return this.pollyPadManager.getPadStats(pad.id);
  }

  /**
   * Get swarm coordinator
   */
  public getSwarmCoordinator(): SwarmCoordinator | undefined {
    return this.swarmCoordinator;
  }

  /**
   * Get Polly Pad manager
   */
  public getPollyPadManager(): PollyPadManager | undefined {
    return this.pollyPadManager;
  }

  // ==================== Fleet Statistics ====================

  /**
   * Get comprehensive fleet statistics
   */
  public getStatistics(): FleetStats {
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
  public getHealthStatus(): {
    healthy: boolean;
    issues: string[];
    metrics: Record<string, number>;
  } {
    const stats = this.getStatistics();
    const issues: string[] = [];

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
  public onEvent(listener: (event: FleetEvent) => void): () => void {
    this.eventListeners.push(listener);
    return () => {
      const index = this.eventListeners.indexOf(listener);
      if (index >= 0) this.eventListeners.splice(index, 1);
    };
  }

  /**
   * Get recent events
   */
  public getRecentEvents(limit: number = 100): FleetEvent[] {
    return this.eventLog.slice(-limit);
  }

  /**
   * Get events by type
   */
  public getEventsByType(type: FleetEvent['type'], limit: number = 50): FleetEvent[] {
    return this.eventLog.filter((e) => e.type === type).slice(-limit);
  }

  // ==================== Lifecycle ====================

  /**
   * Shutdown fleet manager
   */
  public shutdown(): void {
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
  private handleEvent(event: FleetEvent): void {
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
      } catch (e) {
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
  private startHealthChecks(): void {
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

/**
 * Create a pre-configured fleet manager with common agents
 */
export function createDefaultFleet(): FleetManager {
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
