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
import { TaskCreationOptions, TaskDispatcher } from './task-dispatcher';
import {
    AgentCapability,
    FleetAgent,
    FleetEvent,
    FleetStats,
    FleetTask,
    GovernanceTier
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
      ...config
    };
    
    // Initialize core components
    this.trustManager = new TrustManager();
    this.spectralGenerator = new SpectralIdentityGenerator();
    this.registry = new AgentRegistry(this.trustManager);
    this.dispatcher = new TaskDispatcher(this.registry);
    this.governance = new GovernanceManager(this.registry);
    
    // Wire up event forwarding
    this.registry.onEvent(e => this.handleEvent(e));
    this.dispatcher.onEvent(e => this.handleEvent(e));
    this.governance.onEvent(e => this.handleEvent(e));
    
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
    return this.registry.registerAgent(options);
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
      activeRoundtables: governanceStats.activeSessions
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
        activeRoundtables: stats.activeRoundtables
      }
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
    return this.eventLog.filter(e => e.type === type).slice(-limit);
  }
  
  // ==================== Lifecycle ====================
  
  /**
   * Shutdown fleet manager
   */
  public shutdown(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
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
            metrics: health.metrics
          }
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
    initialTrustVector: [0.7, 0.6, 0.8, 0.5, 0.6, 0.4]
  });
  
  fleet.registerAgent({
    name: 'Security-Claude',
    description: 'Security analysis specialist using Claude',
    provider: 'anthropic',
    model: 'claude-3-opus',
    capabilities: ['security_scan', 'code_review', 'testing'],
    maxGovernanceTier: 'UM',
    initialTrustVector: [0.8, 0.7, 0.9, 0.6, 0.7, 0.5]
  });
  
  fleet.registerAgent({
    name: 'Deploy-Bot',
    description: 'Deployment automation agent',
    provider: 'openai',
    model: 'gpt-4o-mini',
    capabilities: ['deployment', 'monitoring'],
    maxGovernanceTier: 'CA',
    initialTrustVector: [0.6, 0.5, 0.7, 0.8, 0.5, 0.4]
  });
  
  fleet.registerAgent({
    name: 'Test-Runner',
    description: 'Automated testing agent',
    provider: 'anthropic',
    model: 'claude-3-sonnet',
    capabilities: ['testing', 'code_review'],
    maxGovernanceTier: 'RU',
    initialTrustVector: [0.5, 0.6, 0.7, 0.5, 0.6, 0.3]
  });
  
  return fleet;
}
