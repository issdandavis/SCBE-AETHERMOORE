/**
 * Agent Registry - Manages AI agent registration and lifecycle
 *
 * @module fleet/agent-registry
 */
import { TrustManager } from '../spaceTor/trust-manager';
import { AgentCapability, AgentStatus, FleetAgent, FleetEvent, GovernanceTier } from './types';
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
export declare class AgentRegistry {
    private agents;
    private trustManager;
    private spectralGenerator;
    private eventListeners;
    constructor(trustManager?: TrustManager);
    /**
     * Register a new agent
     */
    registerAgent(options: AgentRegistrationOptions): FleetAgent;
    /**
     * Get agent by ID
     */
    getAgent(id: string): FleetAgent | undefined;
    /**
     * Get all agents
     */
    getAllAgents(): FleetAgent[];
    /**
     * Get agents by status
     */
    getAgentsByStatus(status: AgentStatus): FleetAgent[];
    /**
     * Get agents by capability
     */
    getAgentsByCapability(capability: AgentCapability): FleetAgent[];
    /**
     * Get agents by trust level
     */
    getAgentsByTrustLevel(level: 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL'): FleetAgent[];
    /**
     * Get agents eligible for a governance tier
     */
    getAgentsForTier(tier: GovernanceTier): FleetAgent[];
    /**
     * Update agent status
     */
    updateAgentStatus(id: string, status: AgentStatus): void;
    /**
     * Update agent trust vector
     */
    updateTrustVector(id: string, trustVector: number[]): void;
    /**
     * Record task completion
     */
    recordTaskCompletion(id: string, success: boolean): void;
    /**
     * Assign task to agent
     */
    assignTask(id: string): void;
    /**
     * Remove agent from registry
     */
    removeAgent(id: string): boolean;
    /**
     * Get registry statistics
     */
    getStatistics(): {
        totalAgents: number;
        byStatus: Record<AgentStatus, number>;
        byTrustLevel: Record<string, number>;
        byProvider: Record<string, number>;
        avgSuccessRate: number;
    };
    /**
     * Subscribe to fleet events
     */
    onEvent(listener: (event: FleetEvent) => void): () => void;
    /**
     * Generate unique agent ID
     */
    private generateAgentId;
    /**
     * Emit fleet event
     */
    private emitEvent;
}
//# sourceMappingURL=agent-registry.d.ts.map