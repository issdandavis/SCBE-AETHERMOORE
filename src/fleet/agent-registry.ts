/**
 * Agent Registry - Manages AI agent registration and lifecycle
 * 
 * @module fleet/agent-registry
 */

import { SpectralIdentityGenerator } from '../harmonic/spectral-identity';
import { TrustManager } from '../spaceTor/trust-manager';
import {
  AgentCapability,
  AgentStatus,
  FleetAgent,
  FleetEvent,
  GOVERNANCE_TIERS,
  GovernanceTier
} from './types';

/**
 * Agent registration options
 */
export interface AgentRegistrationOptions {
  name: string;
  description: string;
  provider: string;
  model: string;
  capabilities: AgentCapability[];
  maxConcurrentTasks?: number;
  maxGovernanceTier?: GovernanceTier;
  initialTrustVector?: number[];
  metadata?: Record<string, unknown>;
}

/**
 * Agent Registry
 * 
 * Manages the lifecycle of AI agents in the fleet with SCBE security integration.
 */
export class AgentRegistry {
  private agents: Map<string, FleetAgent> = new Map();
  private trustManager: TrustManager;
  private spectralGenerator: SpectralIdentityGenerator;
  private eventListeners: ((event: FleetEvent) => void)[] = [];
  
  constructor(trustManager?: TrustManager) {
    this.trustManager = trustManager || new TrustManager();
    this.spectralGenerator = new SpectralIdentityGenerator();
  }
  
  /**
   * Register a new agent
   */
  public registerAgent(options: AgentRegistrationOptions): FleetAgent {
    const id = this.generateAgentId(options.name, options.provider);
    
    if (this.agents.has(id)) {
      throw new Error(`Agent with ID ${id} already exists`);
    }
    
    // Initialize trust vector (default: neutral trust)
    const trustVector = options.initialTrustVector || [0.5, 0.5, 0.5, 0.5, 0.5, 0.5];
    
    // Validate trust vector
    if (trustVector.length !== 6) {
      throw new Error('Trust vector must have 6 dimensions');
    }
    
    // Generate spectral identity
    const spectralIdentity = this.spectralGenerator.generateIdentity(id, trustVector);
    
    // Compute initial trust score
    const trustScore = this.trustManager.computeTrustScore(id, trustVector);
    
    const agent: FleetAgent = {
      id,
      name: options.name,
      description: options.description,
      provider: options.provider,
      model: options.model,
      capabilities: options.capabilities,
      status: 'idle',
      trustVector,
      spectralIdentity,
      trustScore,
      maxConcurrentTasks: options.maxConcurrentTasks || 3,
      currentTaskCount: 0,
      maxGovernanceTier: options.maxGovernanceTier || 'RU',
      registeredAt: Date.now(),
      lastActiveAt: Date.now(),
      tasksCompleted: 0,
      successRate: 1.0,
      metadata: options.metadata
    };
    
    this.agents.set(id, agent);
    
    this.emitEvent({
      type: 'agent_registered',
      timestamp: Date.now(),
      agentId: id,
      data: {
        name: agent.name,
        provider: agent.provider,
        spectralHash: spectralIdentity.spectralHash,
        trustLevel: trustScore.level
      }
    });
    
    return agent;
  }
  
  /**
   * Get agent by ID
   */
  public getAgent(id: string): FleetAgent | undefined {
    return this.agents.get(id);
  }
  
  /**
   * Get all agents
   */
  public getAllAgents(): FleetAgent[] {
    return Array.from(this.agents.values());
  }
  
  /**
   * Get agents by status
   */
  public getAgentsByStatus(status: AgentStatus): FleetAgent[] {
    return this.getAllAgents().filter(a => a.status === status);
  }
  
  /**
   * Get agents by capability
   */
  public getAgentsByCapability(capability: AgentCapability): FleetAgent[] {
    return this.getAllAgents().filter(a => a.capabilities.includes(capability));
  }
  
  /**
   * Get agents by trust level
   */
  public getAgentsByTrustLevel(level: 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL'): FleetAgent[] {
    return this.getAllAgents().filter(a => a.trustScore?.level === level);
  }
  
  /**
   * Get agents eligible for a governance tier
   */
  public getAgentsForTier(tier: GovernanceTier): FleetAgent[] {
    const tierReq = GOVERNANCE_TIERS[tier];
    const tierOrder: GovernanceTier[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
    const tierIndex = tierOrder.indexOf(tier);
    
    return this.getAllAgents().filter(agent => {
      // Must not be suspended or quarantined
      if (agent.status === 'suspended' || agent.status === 'quarantined') return false;
      
      // Check if agent's max tier is >= required tier
      const agentTierIndex = tierOrder.indexOf(agent.maxGovernanceTier);
      if (agentTierIndex < tierIndex) return false;
      
      // Check trust score - use trust level instead of raw normalized score
      // HIGH trust = eligible for all tiers
      // MEDIUM trust = eligible up to CA
      // LOW trust = eligible up to AV
      // CRITICAL trust = not eligible
      const trustLevel = agent.trustScore?.level || 'MEDIUM';
      if (trustLevel === 'CRITICAL') return false;
      if (trustLevel === 'LOW' && tierIndex > 1) return false; // Only KO, AV
      if (trustLevel === 'MEDIUM' && tierIndex > 3) return false; // Up to CA
      
      return true;
    });
  }
  
  /**
   * Update agent status
   */
  public updateAgentStatus(id: string, status: AgentStatus): void {
    const agent = this.agents.get(id);
    if (!agent) {
      throw new Error(`Agent ${id} not found`);
    }
    
    const oldStatus = agent.status;
    agent.status = status;
    agent.lastActiveAt = Date.now();
    
    this.emitEvent({
      type: status === 'suspended' ? 'agent_suspended' : 
            status === 'quarantined' ? 'agent_quarantined' : 'agent_updated',
      timestamp: Date.now(),
      agentId: id,
      data: { oldStatus, newStatus: status }
    });
  }
  
  /**
   * Update agent trust vector
   */
  public updateTrustVector(id: string, trustVector: number[]): void {
    const agent = this.agents.get(id);
    if (!agent) {
      throw new Error(`Agent ${id} not found`);
    }
    
    if (trustVector.length !== 6) {
      throw new Error('Trust vector must have 6 dimensions');
    }
    
    agent.trustVector = trustVector;
    agent.trustScore = this.trustManager.computeTrustScore(id, trustVector);
    agent.spectralIdentity = this.spectralGenerator.generateIdentity(id, trustVector);
    agent.lastActiveAt = Date.now();
    
    this.emitEvent({
      type: 'trust_updated',
      timestamp: Date.now(),
      agentId: id,
      data: {
        trustLevel: agent.trustScore.level,
        spectralHash: agent.spectralIdentity.spectralHash
      }
    });
    
    // Auto-quarantine if trust drops to CRITICAL (normalized > 0.7 means high deviation)
    if (agent.trustScore.level === 'CRITICAL' && agent.status !== 'quarantined') {
      agent.status = 'quarantined';
      this.emitEvent({
        type: 'agent_quarantined',
        timestamp: Date.now(),
        agentId: id,
        data: {
          reason: 'Critical trust level detected'
        }
      });
      this.emitEvent({
        type: 'security_alert',
        timestamp: Date.now(),
        agentId: id,
        data: {
          alert: 'Agent quarantined due to critical trust level',
          trustScore: agent.trustScore.normalized
        }
      });
    }
  }
  
  /**
   * Record task completion
   */
  public recordTaskCompletion(id: string, success: boolean): void {
    const agent = this.agents.get(id);
    if (!agent) {
      throw new Error(`Agent ${id} not found`);
    }
    
    agent.tasksCompleted++;
    agent.currentTaskCount = Math.max(0, agent.currentTaskCount - 1);
    agent.lastActiveAt = Date.now();
    
    // Update success rate (exponential moving average)
    const alpha = 0.1;
    agent.successRate = alpha * (success ? 1 : 0) + (1 - alpha) * agent.successRate;
    
    // Adjust trust based on success
    if (success) {
      // Boost trust slightly
      const boost = agent.trustVector.map(v => Math.min(1, v + 0.01));
      this.updateTrustVector(id, boost);
    } else {
      // Decrease trust
      const penalty = agent.trustVector.map(v => Math.max(0, v - 0.05));
      this.updateTrustVector(id, penalty);
    }
    
    // Update status if no more tasks
    if (agent.currentTaskCount === 0 && agent.status === 'busy') {
      agent.status = 'idle';
    }
  }
  
  /**
   * Assign task to agent
   */
  public assignTask(id: string): void {
    const agent = this.agents.get(id);
    if (!agent) {
      throw new Error(`Agent ${id} not found`);
    }
    
    if (agent.status === 'suspended' || agent.status === 'quarantined') {
      throw new Error(`Agent ${id} is ${agent.status} and cannot accept tasks`);
    }
    
    if (agent.currentTaskCount >= agent.maxConcurrentTasks) {
      throw new Error(`Agent ${id} is at maximum capacity`);
    }
    
    agent.currentTaskCount++;
    agent.status = 'busy';
    agent.lastActiveAt = Date.now();
  }
  
  /**
   * Remove agent from registry
   */
  public removeAgent(id: string): boolean {
    const agent = this.agents.get(id);
    if (!agent) return false;
    
    if (agent.currentTaskCount > 0) {
      throw new Error(`Cannot remove agent ${id} with active tasks`);
    }
    
    this.agents.delete(id);
    
    this.emitEvent({
      type: 'agent_removed',
      timestamp: Date.now(),
      agentId: id,
      data: { name: agent.name }
    });
    
    return true;
  }
  
  /**
   * Get registry statistics
   */
  public getStatistics(): {
    totalAgents: number;
    byStatus: Record<AgentStatus, number>;
    byTrustLevel: Record<string, number>;
    byProvider: Record<string, number>;
    avgSuccessRate: number;
  } {
    const agents = this.getAllAgents();
    
    const byStatus: Record<AgentStatus, number> = {
      idle: 0, busy: 0, offline: 0, suspended: 0, quarantined: 0
    };
    
    const byTrustLevel: Record<string, number> = {
      HIGH: 0, MEDIUM: 0, LOW: 0, CRITICAL: 0
    };
    
    const byProvider: Record<string, number> = {};
    let totalSuccessRate = 0;
    
    for (const agent of agents) {
      byStatus[agent.status]++;
      byTrustLevel[agent.trustScore?.level || 'MEDIUM']++;
      byProvider[agent.provider] = (byProvider[agent.provider] || 0) + 1;
      totalSuccessRate += agent.successRate;
    }
    
    return {
      totalAgents: agents.length,
      byStatus,
      byTrustLevel,
      byProvider,
      avgSuccessRate: agents.length > 0 ? totalSuccessRate / agents.length : 0
    };
  }
  
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
   * Generate unique agent ID
   */
  private generateAgentId(name: string, provider: string): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 6);
    const prefix = name.toLowerCase().replace(/[^a-z0-9]/g, '').substring(0, 8);
    return `${prefix}-${provider.substring(0, 3)}-${timestamp}-${random}`;
  }
  
  /**
   * Emit fleet event
   */
  private emitEvent(event: FleetEvent): void {
    for (const listener of this.eventListeners) {
      try {
        listener(event);
      } catch (e) {
        console.error('Event listener error:', e);
      }
    }
  }
}
