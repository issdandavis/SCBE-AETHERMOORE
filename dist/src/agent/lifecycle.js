"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.AgentMonitor = exports.AgentManager = void 0;
exports.isAgentDead = isAgentDead;
exports.createAgentManager = createAgentManager;
exports.createAgentConfig = createAgentConfig;
const crypto_1 = require("crypto");
const quantum_lattice_js_1 = require("../tokenizer/quantum-lattice.js");
const types_js_1 = require("./types.js");
// ============================================================================
// Agent Manager Class
// ============================================================================
/**
 * Manages agent lifecycle from initialization to shutdown
 */
class AgentManager {
    agent = null;
    heartbeatInterval = null;
    coherenceInterval = null;
    isShuttingDown = false;
    config;
    constructor(config = {}) {
        this.config = config;
    }
    /**
     * Initialize a new agent
     */
    async initialize(agentConfig) {
        if (this.agent) {
            throw new Error('Agent already initialized');
        }
        // Step 1: Generate PQC keypair
        const { publicKey, secretKey } = (0, quantum_lattice_js_1.generateLatticeKeypair)('ML-KEM-768');
        // Step 2: Register with Vault (if handler provided)
        let vaultRoleId = agentConfig.vaultRoleId;
        if (this.config.registerWithVault && !vaultRoleId) {
            vaultRoleId = await this.config.registerWithVault(agentConfig);
        }
        // Step 3: Calculate geometric properties
        const phase = (0, types_js_1.phaseToRadians)(agentConfig.tongue);
        const weight = (0, types_js_1.calculateTongueWeight)(agentConfig.tongue);
        const position = (0, types_js_1.generateInitialPosition)(agentConfig.tongue);
        // Step 4: Create agent object
        this.agent = {
            ...agentConfig,
            id: agentConfig.id || (0, crypto_1.randomUUID)(),
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
    getAgent() {
        return this.agent;
    }
    /**
     * Get agent health metrics
     */
    getHealth() {
        if (!this.agent)
            return null;
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
    async setStatus(newStatus) {
        if (!this.agent)
            return;
        const oldStatus = this.agent.status;
        if (oldStatus === newStatus)
            return;
        this.agent.status = newStatus;
        // Publish status change event
        const eventType = newStatus === 'quarantine'
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
    startHeartbeat() {
        if (this.heartbeatInterval)
            return;
        this.heartbeatInterval = setInterval(async () => {
            if (!this.agent || this.isShuttingDown)
                return;
            try {
                const heartbeat = this.createHeartbeat();
                await this.publishHeartbeat(heartbeat);
                if (this.config.handlers?.onHeartbeat) {
                    await this.config.handlers.onHeartbeat(heartbeat);
                }
            }
            catch (error) {
                if (this.config.handlers?.onError && this.agent) {
                    await this.config.handlers.onError(this.agent, error);
                }
            }
        }, types_js_1.HEARTBEAT_INTERVAL_MS);
    }
    /**
     * Start coherence decay interval
     */
    startCoherenceDecay() {
        if (this.coherenceInterval)
            return;
        this.coherenceInterval = setInterval(() => {
            if (!this.agent || this.isShuttingDown)
                return;
            // Decay coherence over time (simulates entropy)
            this.agent.coherence = Math.max(0, this.agent.coherence - types_js_1.COHERENCE_DECAY_RATE);
            // Update status based on coherence
            if (this.agent.coherence < 0.3 && this.agent.status === 'active') {
                this.setStatus('degraded');
            }
            else if (this.agent.coherence < 0.1) {
                this.setStatus('quarantine');
            }
        }, 1000);
    }
    /**
     * Create heartbeat payload
     */
    createHeartbeat() {
        if (!this.agent)
            throw new Error('Agent not initialized');
        const heartbeat = {
            agentId: this.agent.id,
            tongue: this.agent.tongue,
            position: this.agent.position,
            coherence: this.agent.coherence,
            status: this.agent.status,
            timestamp: Date.now(),
        };
        // Sign heartbeat if we have private key
        if (this.agent.keys.privateKey) {
            const { signature, tongueBinding } = (0, quantum_lattice_js_1.signWithTongueBinding)(Buffer.from(JSON.stringify(heartbeat)), this.agent.tongue, this.agent.keys.privateKey);
            heartbeat.signature = signature;
        }
        this.agent.lastHeartbeat = heartbeat.timestamp;
        return heartbeat;
    }
    /**
     * Publish heartbeat event
     */
    async publishHeartbeat(heartbeat) {
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
    async publishEvent(event) {
        if (this.config.publishEvent) {
            await this.config.publishEvent(event);
        }
    }
    /**
     * Refresh coherence (called after successful operations)
     */
    refreshCoherence(amount = 0.1) {
        if (!this.agent)
            return;
        this.agent.coherence = Math.min(1.0, this.agent.coherence + amount);
        if (this.agent.coherence >= 0.5 && this.agent.status === 'degraded') {
            this.setStatus('active');
        }
    }
    /**
     * Update agent position in Poincaré ball
     */
    updatePosition(newPosition) {
        if (!this.agent)
            return false;
        // Validate position is within Poincaré ball
        if ((0, types_js_1.poincareNorm)(newPosition) >= 1) {
            return false;
        }
        this.agent.position = newPosition;
        return true;
    }
    /**
     * Check and consume nonce (replay protection)
     */
    consumeNonce(nonce) {
        if (!this.agent)
            return false;
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
    async shutdown(timeoutMs = 30000) {
        if (!this.agent || this.isShuttingDown)
            return;
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
exports.AgentManager = AgentManager;
// ============================================================================
// Dead Agent Detection
// ============================================================================
/**
 * Check if an agent is dead based on heartbeat timeout
 */
function isAgentDead(agent, now = Date.now()) {
    return now - agent.lastHeartbeat > types_js_1.AGENT_TIMEOUT_MS;
}
/**
 * Monitor agents and detect dead ones
 */
class AgentMonitor {
    agents = new Map();
    checkInterval = null;
    onAgentDead;
    constructor(onAgentDead) {
        this.onAgentDead = onAgentDead;
    }
    /**
     * Register or update an agent
     */
    updateAgent(agent) {
        this.agents.set(agent.id, agent);
    }
    /**
     * Remove an agent
     */
    removeAgent(agentId) {
        this.agents.delete(agentId);
    }
    /**
     * Start monitoring
     */
    start(intervalMs = 10000) {
        if (this.checkInterval)
            return;
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
    stop() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
    }
    /**
     * Get all agents
     */
    getAgents() {
        return Array.from(this.agents.values());
    }
    /**
     * Get agents by status
     */
    getAgentsByStatus(status) {
        return this.getAgents().filter((a) => a.status === status);
    }
    /**
     * Get agents by tongue
     */
    getAgentsByTongue(tongue) {
        return this.getAgents().filter((a) => a.tongue === tongue);
    }
    /**
     * Get agents by IP tier
     */
    getAgentsByTier(tier) {
        return this.getAgents().filter((a) => a.ipTier === tier);
    }
}
exports.AgentMonitor = AgentMonitor;
// ============================================================================
// Factory Functions
// ============================================================================
/**
 * Create a new agent manager with default configuration
 */
function createAgentManager(config) {
    return new AgentManager(config);
}
/**
 * Create an agent configuration
 */
function createAgentConfig(tongue, ipTier, overrides) {
    return {
        id: (0, crypto_1.randomUUID)(),
        tongue,
        ipTier: ipTier ?? 'private',
        ...overrides,
    };
}
//# sourceMappingURL=lifecycle.js.map