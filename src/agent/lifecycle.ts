/**
 * Agent Lifecycle Management
 *
 * Handles agent initialization, heartbeat protocol, and graceful shutdown.
 *
 * Lifecycle stages:
 * 1. Initialization - Generate keys, register with Vault, join swarm
 * 2. Active - Send heartbeats, process requests, maintain coherence
 * 3. Shutdown - Announce departure, finish work, disconnect
 *
 * @module agent/lifecycle
 */

import { randomUUID, createHash } from 'crypto';
import { TongueCode } from '../tokenizer/ss1.js';
import { generateLatticeKeypair, signWithTongueBinding } from '../tokenizer/quantum-lattice.js';
import {
  Agent,
  AgentConfig,
  AgentEvent,
  AgentHeartbeat,
  AgentHealth,
  AgentStatus,
  IPTier,
  PoincarePosition,
  HEARTBEAT_INTERVAL_MS,
  AGENT_TIMEOUT_MS,
  COHERENCE_DECAY_RATE,
  calculateTongueWeight,
  phaseToRadians,
  generateInitialPosition,
  poincareNorm,
} from './types.js';

// ============================================================================
// Types
// ============================================================================

/** Lifecycle event handlers */
export interface LifecycleHandlers {
  onHeartbeat?: (heartbeat: AgentHeartbeat) => Promise<void>;
  onStatusChange?: (agent: Agent, oldStatus: AgentStatus, newStatus: AgentStatus) => Promise<void>;
  onError?: (agent: Agent, error: Error) => Promise<void>;
  onShutdown?: (agent: Agent) => Promise<void>;
}

/** Agent manager configuration */
export interface AgentManagerConfig {
  /** Kafka publish function */
  publishEvent?: (event: AgentEvent) => Promise<void>;
  /** Vault registration function */
  registerWithVault?: (config: AgentConfig) => Promise<string>;
  /** Custom handlers */
  handlers?: LifecycleHandlers;
}

// ============================================================================
// Agent Manager Class
// ============================================================================

/**
 * Manages agent lifecycle from initialization to shutdown
 */
export class AgentManager {
  private agent: Agent | null = null;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private coherenceInterval: ReturnType<typeof setInterval> | null = null;
  private isShuttingDown = false;
  private config: AgentManagerConfig;

  constructor(config: AgentManagerConfig = {}) {
    this.config = config;
  }

  /**
   * Initialize a new agent
   */
  async initialize(agentConfig: AgentConfig): Promise<Agent> {
    if (this.agent) {
      throw new Error('Agent already initialized');
    }

    // Step 1: Generate PQC keypair
    const { publicKey, secretKey } = generateLatticeKeypair('ML-KEM-768');

    // Step 2: Register with Vault (if handler provided)
    let vaultRoleId = agentConfig.vaultRoleId;
    if (this.config.registerWithVault && !vaultRoleId) {
      vaultRoleId = await this.config.registerWithVault(agentConfig);
    }

    // Step 3: Calculate geometric properties
    const phase = phaseToRadians(agentConfig.tongue);
    const weight = calculateTongueWeight(agentConfig.tongue);
    const position = generateInitialPosition(agentConfig.tongue);

    // Step 4: Create agent object
    this.agent = {
      ...agentConfig,
      id: agentConfig.id || randomUUID(),
      vaultRoleId,
      position,
      phase,
      weight,
      coherence: 1.0,
      lastHeartbeat: Date.now(),
      status: 'initializing',
      keys: {
        publicKey,
        privateKey: secretKey,
      },
      createdAt: Date.now(),
      usedNonces: new Set(),
    };

    // Step 5: Announce to swarm
    await this.publishEvent({
      type: 'agent.joined',
      agentId: this.agent.id,
      tongue: this.agent.tongue,
      timestamp: Date.now(),
      payload: {
        position: this.agent.position,
        phase: this.agent.phase,
        weight: this.agent.weight,
        ipTier: this.agent.ipTier,
        publicKey: this.agent.keys.publicKey.toString('hex'),
      },
    });

    // Step 6: Start heartbeat
    await this.setStatus('active');
    this.startHeartbeat();
    this.startCoherenceDecay();

    return this.agent;
  }

  /**
   * Get current agent
   */
  getAgent(): Agent | null {
    return this.agent;
  }

  /**
   * Get agent health metrics
   */
  getHealth(): AgentHealth | null {
    if (!this.agent) return null;

    return {
      agentId: this.agent.id,
      tongue: this.agent.tongue,
      status: this.agent.status,
      coherence: this.agent.coherence,
      uptimeMs: Date.now() - this.agent.createdAt,
      heartbeatsMissed: 0, // Calculated by external monitor
    };
  }

  /**
   * Set agent status with event publishing
   */
  private async setStatus(newStatus: AgentStatus): Promise<void> {
    if (!this.agent) return;

    const oldStatus = this.agent.status;
    if (oldStatus === newStatus) return;

    this.agent.status = newStatus;

    // Publish status change event
    const eventType =
      newStatus === 'quarantine'
        ? 'agent.quarantine'
        : newStatus === 'degraded'
          ? 'agent.degraded'
          : newStatus === 'offline'
            ? 'agent.offline'
            : 'agent.recovered';

    await this.publishEvent({
      type: eventType,
      agentId: this.agent.id,
      tongue: this.agent.tongue,
      timestamp: Date.now(),
      payload: { oldStatus, newStatus },
    });

    // Call handler if provided
    if (this.config.handlers?.onStatusChange) {
      await this.config.handlers.onStatusChange(this.agent, oldStatus, newStatus);
    }
  }

  /**
   * Start heartbeat interval
   */
  private startHeartbeat(): void {
    if (this.heartbeatInterval) return;

    this.heartbeatInterval = setInterval(async () => {
      if (!this.agent || this.isShuttingDown) return;

      try {
        const heartbeat = this.createHeartbeat();
        await this.publishHeartbeat(heartbeat);

        if (this.config.handlers?.onHeartbeat) {
          await this.config.handlers.onHeartbeat(heartbeat);
        }
      } catch (error) {
        if (this.config.handlers?.onError && this.agent) {
          await this.config.handlers.onError(this.agent, error as Error);
        }
      }
    }, HEARTBEAT_INTERVAL_MS);
  }

  /**
   * Start coherence decay interval
   */
  private startCoherenceDecay(): void {
    if (this.coherenceInterval) return;

    this.coherenceInterval = setInterval(() => {
      if (!this.agent || this.isShuttingDown) return;

      // Decay coherence over time (simulates entropy)
      this.agent.coherence = Math.max(0, this.agent.coherence - COHERENCE_DECAY_RATE);

      // Update status based on coherence
      if (this.agent.coherence < 0.3 && this.agent.status === 'active') {
        this.setStatus('degraded');
      } else if (this.agent.coherence < 0.1) {
        this.setStatus('quarantine');
      }
    }, 1000);
  }

  /**
   * Create heartbeat payload
   */
  private createHeartbeat(): AgentHeartbeat {
    if (!this.agent) throw new Error('Agent not initialized');

    const heartbeat: AgentHeartbeat = {
      agentId: this.agent.id,
      tongue: this.agent.tongue,
      position: this.agent.position,
      coherence: this.agent.coherence,
      status: this.agent.status,
      timestamp: Date.now(),
    };

    // Sign heartbeat if we have private key
    if (this.agent.keys.privateKey) {
      const { signature, tongueBinding } = signWithTongueBinding(
        Buffer.from(JSON.stringify(heartbeat)),
        this.agent.tongue,
        this.agent.keys.privateKey
      );
      heartbeat.signature = signature;
    }

    this.agent.lastHeartbeat = heartbeat.timestamp;
    return heartbeat;
  }

  /**
   * Publish heartbeat event
   */
  private async publishHeartbeat(heartbeat: AgentHeartbeat): Promise<void> {
    await this.publishEvent({
      type: 'agent.heartbeat',
      agentId: heartbeat.agentId,
      tongue: heartbeat.tongue,
      timestamp: heartbeat.timestamp,
      payload: heartbeat,
      signature: heartbeat.signature,
    });
  }

  /**
   * Publish event to Kafka
   */
  private async publishEvent(event: AgentEvent): Promise<void> {
    if (this.config.publishEvent) {
      await this.config.publishEvent(event);
    }
  }

  /**
   * Refresh coherence (called after successful operations)
   */
  refreshCoherence(amount = 0.1): void {
    if (!this.agent) return;

    this.agent.coherence = Math.min(1.0, this.agent.coherence + amount);

    if (this.agent.coherence >= 0.5 && this.agent.status === 'degraded') {
      this.setStatus('active');
    }
  }

  /**
   * Update agent position in Poincaré ball
   */
  updatePosition(newPosition: PoincarePosition): boolean {
    if (!this.agent) return false;

    // Validate position is within Poincaré ball
    if (poincareNorm(newPosition) >= 1) {
      return false;
    }

    this.agent.position = newPosition;
    return true;
  }

  /**
   * Check and consume nonce (replay protection)
   */
  consumeNonce(nonce: string): boolean {
    if (!this.agent) return false;

    if (this.agent.usedNonces.has(nonce)) {
      return false; // Replay detected
    }

    this.agent.usedNonces.add(nonce);

    // Prune old nonces (keep last 10000)
    if (this.agent.usedNonces.size > 10000) {
      const entries = Array.from(this.agent.usedNonces);
      this.agent.usedNonces = new Set(entries.slice(-10000));
    }

    return true;
  }

  /**
   * Graceful shutdown
   */
  async shutdown(timeoutMs = 30000): Promise<void> {
    if (!this.agent || this.isShuttingDown) return;

    this.isShuttingDown = true;

    // Stop intervals
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    if (this.coherenceInterval) {
      clearInterval(this.coherenceInterval);
      this.coherenceInterval = null;
    }

    // Announce departure
    await this.publishEvent({
      type: 'agent.leaving',
      agentId: this.agent.id,
      tongue: this.agent.tongue,
      timestamp: Date.now(),
      payload: {
        reason: 'graceful_shutdown',
        uptimeMs: Date.now() - this.agent.createdAt,
      },
    });

    // Call shutdown handler
    if (this.config.handlers?.onShutdown) {
      await Promise.race([
        this.config.handlers.onShutdown(this.agent),
        new Promise((resolve) => setTimeout(resolve, timeoutMs)),
      ]);
    }

    this.agent.status = 'offline';
    this.agent = null;
  }
}

// ============================================================================
// Dead Agent Detection
// ============================================================================

/**
 * Check if an agent is dead based on heartbeat timeout
 */
export function isAgentDead(agent: Agent, now = Date.now()): boolean {
  return now - agent.lastHeartbeat > AGENT_TIMEOUT_MS;
}

/**
 * Monitor agents and detect dead ones
 */
export class AgentMonitor {
  private agents: Map<string, Agent> = new Map();
  private checkInterval: ReturnType<typeof setInterval> | null = null;
  private onAgentDead?: (agent: Agent) => Promise<void>;

  constructor(onAgentDead?: (agent: Agent) => Promise<void>) {
    this.onAgentDead = onAgentDead;
  }

  /**
   * Register or update an agent
   */
  updateAgent(agent: Agent): void {
    this.agents.set(agent.id, agent);
  }

  /**
   * Remove an agent
   */
  removeAgent(agentId: string): void {
    this.agents.delete(agentId);
  }

  /**
   * Start monitoring
   */
  start(intervalMs = 10000): void {
    if (this.checkInterval) return;

    this.checkInterval = setInterval(async () => {
      const now = Date.now();

      for (const [agentId, agent] of this.agents) {
        if (isAgentDead(agent, now) && agent.status !== 'offline') {
          agent.status = 'offline';

          if (this.onAgentDead) {
            await this.onAgentDead(agent);
          }
        }
      }
    }, intervalMs);
  }

  /**
   * Stop monitoring
   */
  stop(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
  }

  /**
   * Get all agents
   */
  getAgents(): Agent[] {
    return Array.from(this.agents.values());
  }

  /**
   * Get agents by status
   */
  getAgentsByStatus(status: AgentStatus): Agent[] {
    return this.getAgents().filter((a) => a.status === status);
  }

  /**
   * Get agents by tongue
   */
  getAgentsByTongue(tongue: TongueCode): Agent[] {
    return this.getAgents().filter((a) => a.tongue === tongue);
  }

  /**
   * Get agents by IP tier
   */
  getAgentsByTier(tier: IPTier): Agent[] {
    return this.getAgents().filter((a) => a.ipTier === tier);
  }
}

// ============================================================================
// Factory Functions
// ============================================================================

/**
 * Create a new agent manager with default configuration
 */
export function createAgentManager(config?: AgentManagerConfig): AgentManager {
  return new AgentManager(config);
}

/**
 * Create an agent configuration
 */
export function createAgentConfig(
  tongue: TongueCode,
  ipTier?: IPTier,
  overrides?: Partial<AgentConfig>
): AgentConfig {
  return {
    id: randomUUID(),
    tongue,
    ipTier: ipTier ?? 'private',
    ...overrides,
  };
}
