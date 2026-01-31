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

// ============================================================================
// Core Types
// ============================================================================

/** IP tier classification for network exposure */
export type IPTier = 'public' | 'private' | 'hidden';

/** Agent operational status */
export type AgentStatus = 'initializing' | 'active' | 'degraded' | 'offline' | 'quarantine';

/** Agent event types for Kafka pub/sub */
export type AgentEventType =
  | 'agent.joined'
  | 'agent.heartbeat'
  | 'agent.leaving'
  | 'agent.offline'
  | 'agent.degraded'
  | 'agent.quarantine'
  | 'agent.recovered';

// ============================================================================
// Constants
// ============================================================================

/** Golden ratio for tongue weight calculations */
export const GOLDEN_RATIO = 1.6180339887498949;

/** Phase offsets for each tongue (degrees) */
export const TONGUE_PHASES: Record<TongueCode, number> = {
  KO: 0,
  AV: 60,
  RU: 120,
  CA: 180,
  UM: 240,
  DR: 300,
};

/** Tongue indices for weight calculation (φⁿ) */
export const TONGUE_INDICES: Record<TongueCode, number> = {
  KO: 0,
  AV: 1,
  RU: 2,
  CA: 3,
  UM: 4,
  DR: 5,
};

/** Default IP tier mapping for tongues */
export const TONGUE_IP_TIERS: Record<TongueCode, IPTier> = {
  KO: 'public', // Control/Orchestration - public gateway
  AV: 'private', // Transport/Init - internal mesh
  RU: 'private', // Policy/Rules - internal mesh
  CA: 'private', // Compute/Encryption - internal mesh
  UM: 'hidden', // Security/Redaction - air-gapped
  DR: 'hidden', // Schema/Auth - air-gapped
};

/** Heartbeat interval in milliseconds */
export const HEARTBEAT_INTERVAL_MS = 5000;

/** Agent timeout threshold (no heartbeat) */
export const AGENT_TIMEOUT_MS = 15000;

/** Coherence decay rate per second */
export const COHERENCE_DECAY_RATE = 0.001;

// ============================================================================
// Interfaces
// ============================================================================

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

// ============================================================================
// Byzantine Fault Tolerance
// ============================================================================

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

// ============================================================================
// Swarm Coordination
// ============================================================================

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

// ============================================================================
// Health & Monitoring
// ============================================================================

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

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Calculate tongue weight using golden ratio
 */
export function calculateTongueWeight(tongue: TongueCode): number {
  return Math.pow(GOLDEN_RATIO, TONGUE_INDICES[tongue]);
}

/**
 * Convert phase from degrees to radians
 */
export function phaseToRadians(tongue: TongueCode): number {
  return (TONGUE_PHASES[tongue] * Math.PI) / 180;
}

/**
 * Calculate Poincaré ball norm
 */
export function poincareNorm(pos: PoincarePosition): number {
  return Math.sqrt(pos.x * pos.x + pos.y * pos.y + pos.z * pos.z);
}

/**
 * Validate position is within Poincaré ball
 */
export function isValidPoincarePosition(pos: PoincarePosition): boolean {
  return poincareNorm(pos) < 1;
}

/**
 * Calculate hyperbolic distance between two points
 */
export function hyperbolicDistance(u: PoincarePosition, v: PoincarePosition): number {
  const uNorm = poincareNorm(u);
  const vNorm = poincareNorm(v);

  if (uNorm >= 1 || vNorm >= 1) {
    return Infinity;
  }

  const diffX = u.x - v.x;
  const diffY = u.y - v.y;
  const diffZ = u.z - v.z;
  const diffNormSq = diffX * diffX + diffY * diffY + diffZ * diffZ;

  const denominator = (1 - uNorm * uNorm) * (1 - vNorm * vNorm);
  const argument = 1 + (2 * diffNormSq) / denominator;

  return Math.acosh(argument);
}

/**
 * Calculate Harmonic Wall cost
 */
export function harmonicWallCost(distance: number, R = Math.E): number {
  return Math.pow(R, distance * distance);
}

/**
 * Generate initial position for tongue in Poincaré ball
 */
export function generateInitialPosition(tongue: TongueCode): PoincarePosition {
  const phase = phaseToRadians(tongue);
  const radius = 0.3 + Math.random() * 0.3; // 0.3 to 0.6 from center

  return {
    x: radius * Math.cos(phase),
    y: radius * Math.sin(phase),
    z: (Math.random() - 0.5) * 0.2, // Small z variation
  };
}

/**
 * Calculate BFT quorum from total agents
 */
export function calculateBFTQuorum(totalAgents: number): BFTConfig {
  // BFT requires 3f + 1 agents to tolerate f faults
  // quorum = 2f + 1
  const maxFaulty = Math.floor((totalAgents - 1) / 3);
  const quorum = 2 * maxFaulty + 1;

  return {
    totalAgents,
    maxFaulty,
    quorum,
    timeoutMs: 5000,
  };
}
