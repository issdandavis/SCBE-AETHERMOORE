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
import { TongueCode } from '../tokenizer/ss1.js';
import { Agent, AgentConfig, AgentEvent, AgentHeartbeat, AgentHealth, AgentStatus, IPTier, PoincarePosition } from './types.js';
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
/**
 * Manages agent lifecycle from initialization to shutdown
 */
export declare class AgentManager {
    private agent;
    private heartbeatInterval;
    private coherenceInterval;
    private isShuttingDown;
    private config;
    constructor(config?: AgentManagerConfig);
    /**
     * Initialize a new agent
     */
    initialize(agentConfig: AgentConfig): Promise<Agent>;
    /**
     * Get current agent
     */
    getAgent(): Agent | null;
    /**
     * Get agent health metrics
     */
    getHealth(): AgentHealth | null;
    /**
     * Set agent status with event publishing
     */
    private setStatus;
    /**
     * Start heartbeat interval
     */
    private startHeartbeat;
    /**
     * Start coherence decay interval
     */
    private startCoherenceDecay;
    /**
     * Create heartbeat payload
     */
    private createHeartbeat;
    /**
     * Publish heartbeat event
     */
    private publishHeartbeat;
    /**
     * Publish event to Kafka
     */
    private publishEvent;
    /**
     * Refresh coherence (called after successful operations)
     */
    refreshCoherence(amount?: number): void;
    /**
     * Update agent position in Poincaré ball
     */
    updatePosition(newPosition: PoincarePosition): boolean;
    /**
     * Check and consume nonce (replay protection)
     */
    consumeNonce(nonce: string): boolean;
    /**
     * Graceful shutdown
     */
    shutdown(timeoutMs?: number): Promise<void>;
}
/**
 * Check if an agent is dead based on heartbeat timeout
 */
export declare function isAgentDead(agent: Agent, now?: number): boolean;
/**
 * Monitor agents and detect dead ones
 */
export declare class AgentMonitor {
    private agents;
    private checkInterval;
    private onAgentDead?;
    constructor(onAgentDead?: (agent: Agent) => Promise<void>);
    /**
     * Register or update an agent
     */
    updateAgent(agent: Agent): void;
    /**
     * Remove an agent
     */
    removeAgent(agentId: string): void;
    /**
     * Start monitoring
     */
    start(intervalMs?: number): void;
    /**
     * Stop monitoring
     */
    stop(): void;
    /**
     * Get all agents
     */
    getAgents(): Agent[];
    /**
     * Get agents by status
     */
    getAgentsByStatus(status: AgentStatus): Agent[];
    /**
     * Get agents by tongue
     */
    getAgentsByTongue(tongue: TongueCode): Agent[];
    /**
     * Get agents by IP tier
     */
    getAgentsByTier(tier: IPTier): Agent[];
}
/**
 * Create a new agent manager with default configuration
 */
export declare function createAgentManager(config?: AgentManagerConfig): AgentManager;
/**
 * Create an agent configuration
 */
export declare function createAgentConfig(tongue: TongueCode, ipTier?: IPTier, overrides?: Partial<AgentConfig>): AgentConfig;
//# sourceMappingURL=lifecycle.d.ts.map