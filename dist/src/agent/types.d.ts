/**
 * Agent Types for SCBE-AETHERMOORE
 *
 * Defines agent structures with:
 * - Six Sacred Tongues identity
 * - Three-tier IP classification (Public/Private/Hidden)
 * - Poincaré ball positioning
 * - Quantum-safe cryptographic keys
 *
 * @module agent/types
 */
import { TongueCode } from '../tokenizer/ss1.js';
/** IP tier classification for network exposure */
export type IPTier = 'public' | 'private' | 'hidden';
/** Agent operational status */
export type AgentStatus = 'initializing' | 'active' | 'degraded' | 'offline' | 'quarantine';
/** Agent event types for Kafka pub/sub */
export type AgentEventType = 'agent.joined' | 'agent.heartbeat' | 'agent.leaving' | 'agent.offline' | 'agent.degraded' | 'agent.quarantine' | 'agent.recovered';
/** Golden ratio for tongue weight calculations */
export declare const GOLDEN_RATIO = 1.618033988749895;
/** Phase offsets for each tongue (degrees) */
export declare const TONGUE_PHASES: Record<TongueCode, number>;
/** Tongue indices for weight calculation (φⁿ) */
export declare const TONGUE_INDICES: Record<TongueCode, number>;
/** Default IP tier mapping for tongues */
export declare const TONGUE_IP_TIERS: Record<TongueCode, IPTier>;
/** Heartbeat interval in milliseconds */
export declare const HEARTBEAT_INTERVAL_MS = 5000;
/** Agent timeout threshold (no heartbeat) */
export declare const AGENT_TIMEOUT_MS = 15000;
/** Coherence decay rate per second */
export declare const COHERENCE_DECAY_RATE = 0.001;
/** 3D position in Poincaré ball (||pos|| < 1) */
export interface PoincarePosition {
    x: number;
    y: number;
    z: number;
}
/** Agent cryptographic keys */
export interface AgentKeys {
    /** ML-DSA-65 public key for signatures */
    publicKey: Buffer;
    /** ML-DSA-65 private key (only held by agent) */
    privateKey?: Buffer;
    /** ML-KEM public key for key encapsulation */
    kemPublicKey?: Buffer;
    /** ML-KEM private key (only held by agent) */
    kemPrivateKey?: Buffer;
}
/** Agent identity and configuration */
export interface AgentConfig {
    /** Unique agent identifier */
    id: string;
    /** Sacred Tongue identity */
    tongue: TongueCode;
    /** Network exposure tier */
    ipTier: IPTier;
    /** Vault AppRole ID for secret access */
    vaultRoleId?: string;
    /** Kafka topics to subscribe */
    kafkaTopics?: string[];
    /** Custom metadata */
    metadata?: Record<string, unknown>;
}
/** Full agent state */
export interface Agent extends AgentConfig {
    /** Position in Poincaré ball */
    position: PoincarePosition;
    /** Phase offset in radians */
    phase: number;
    /** Weight based on tongue (φⁿ) */
    weight: number;
    /** PHDM polyhedral coherence (0.0 - 1.0) */
    coherence: number;
    /** Last heartbeat timestamp (Unix ms) */
    lastHeartbeat: number;
    /** Operational status */
    status: AgentStatus;
    /** Cryptographic keys */
    keys: AgentKeys;
    /** Creation timestamp */
    createdAt: number;
    /** Session nonces (for replay protection) */
    usedNonces: Set<string>;
}
/** Heartbeat payload sent to swarm */
export interface AgentHeartbeat {
    agentId: string;
    tongue: TongueCode;
    position: PoincarePosition;
    coherence: number;
    status: AgentStatus;
    timestamp: number;
    /** Signed with agent's private key */
    signature?: string;
}
/** Agent event for Kafka publishing */
export interface AgentEvent<T = unknown> {
    type: AgentEventType;
    agentId: string;
    tongue: TongueCode;
    timestamp: number;
    payload: T;
    /** Tongue-bound signature */
    signature?: string;
    tongueBinding?: string;
}
/** BFT quorum configuration */
export interface BFTConfig {
    /** Total number of agents in consensus group */
    totalAgents: number;
    /** Maximum faulty agents tolerated (f) */
    maxFaulty: number;
    /** Required quorum for decisions (2f + 1) */
    quorum: number;
    /** Consensus timeout in milliseconds */
    timeoutMs: number;
}
/** Vote in BFT consensus */
export interface BFTVote {
    agentId: string;
    tongue: TongueCode;
    decision: 'ALLOW' | 'DENY' | 'QUARANTINE';
    confidence: number;
    timestamp: number;
    signature: string;
}
/** Consensus result */
export interface BFTConsensusResult {
    decision: 'ALLOW' | 'DENY' | 'QUARANTINE' | 'NO_QUORUM';
    votes: BFTVote[];
    quorumReached: boolean;
    consensusTimestamp: number;
}
/** Swarm state snapshot */
export interface SwarmState {
    agents: Map<string, Agent>;
    formation: 'dispersed' | 'convergent' | 'ring' | 'custom';
    centroid: PoincarePosition;
    averageCoherence: number;
    lastUpdate: number;
}
/** Formation target for swarm coordination */
export interface FormationTarget {
    formation: 'dispersed' | 'convergent' | 'ring' | 'custom';
    positions: Map<TongueCode, PoincarePosition>;
    transitionDuration: number;
}
/** Agent health metrics */
export interface AgentHealth {
    agentId: string;
    tongue: TongueCode;
    status: AgentStatus;
    coherence: number;
    uptimeMs: number;
    heartbeatsMissed: number;
    lastError?: string;
    lastErrorTimestamp?: number;
    memoryUsageMB?: number;
    cpuUsagePercent?: number;
}
/** Rogue detection result */
export interface RogueDetectionResult {
    agentId: string;
    isRogue: boolean;
    confidence: number;
    indicators: string[];
    recommendedAction: 'none' | 'monitor' | 'quarantine' | 'terminate';
}
/**
 * Calculate tongue weight using golden ratio
 */
export declare function calculateTongueWeight(tongue: TongueCode): number;
/**
 * Convert phase from degrees to radians
 */
export declare function phaseToRadians(tongue: TongueCode): number;
/**
 * Calculate Poincaré ball norm
 */
export declare function poincareNorm(pos: PoincarePosition): number;
/**
 * Validate position is within Poincaré ball
 */
export declare function isValidPoincarePosition(pos: PoincarePosition): boolean;
/**
 * Calculate hyperbolic distance between two points
 */
export declare function hyperbolicDistance(u: PoincarePosition, v: PoincarePosition): number;
/**
 * Calculate Harmonic Wall cost
 * score = 1 / (1 + d_H + 2 * phaseDeviation)
 */
export declare function harmonicWallCost(distance: number, phaseDeviation?: number): number;
/**
 * Generate initial position for tongue in Poincaré ball
 */
export declare function generateInitialPosition(tongue: TongueCode): PoincarePosition;
/**
 * Calculate BFT quorum from total agents
 */
export declare function calculateBFTQuorum(totalAgents: number): BFTConfig;
//# sourceMappingURL=types.d.ts.map