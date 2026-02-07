/**
 * @file types.ts
 * @module ai_brain/types
 * @layer Layer 1-14 (Unified)
 * @component AI Brain Mapping Type Definitions
 * @version 1.1.0
 * @since 2026-02-07
 *
 * Core type definitions for the Multi-Vectored Quasi-Space Architecture.
 * Defines the 21D unified brain state manifold and supporting types.
 *
 * Dimensions:
 *   SCBE Context (6D): device, location, network, behavior, time, intent
 *   Dual Lattice Navigation (6D): x, y, z, time, priority, confidence
 *   PHDM Cognitive Position (3D): polyhedral x, y, z
 *   Sacred Tongues Semantic Phase (3D): active tongue, phase angle, weight
 *   Swarm Coordination (3D): trust score, byzantine votes, spectral coherence
 */

import type { GovernanceTier, DimensionalState } from '../fleet/types.js';

/** Total dimensionality of the unified brain manifold */
export const BRAIN_DIMENSIONS = 21;

/** Golden ratio constant */
export const PHI = (1 + Math.sqrt(5)) / 2;

/** Small epsilon for numerical stability */
export const BRAIN_EPSILON = 1e-10;

/** Maximum norm for Poincare ball containment */
export const POINCARE_MAX_NORM = 1 - 1e-8;

// ═══════════════════════════════════════════════════════════════
// 21D Brain State Vector Components
// ═══════════════════════════════════════════════════════════════

/**
 * SCBE Core context (6D) - Layers 1-2
 */
export interface SCBEContext {
  /** Device trust score [0, 1] */
  deviceTrust: number;
  /** Location trust score [0, 1] */
  locationTrust: number;
  /** Network trust score [0, 1] */
  networkTrust: number;
  /** Behavioral score [0, 1] */
  behaviorScore: number;
  /** Time-of-day normalized [0, 1] */
  timeOfDay: number;
  /** Intent alignment [0, 1] */
  intentAlignment: number;
}

/**
 * Dual Lattice navigation vector (6D)
 */
export interface NavigationVector {
  /** X position in hyperbolic space */
  x: number;
  /** Y position in hyperbolic space */
  y: number;
  /** Z position in hyperbolic space */
  z: number;
  /** Timestamp (normalized) */
  time: number;
  /** Priority level [0, 1] */
  priority: number;
  /** Confidence score [0, 1] */
  confidence: number;
}

/**
 * PHDM cognitive position (3D) in quasicrystal space
 */
export interface CognitivePosition {
  /** Polyhedral X coordinate */
  px: number;
  /** Polyhedral Y coordinate */
  py: number;
  /** Polyhedral Z coordinate */
  pz: number;
}

/**
 * Sacred Tongues semantic phase (3D)
 */
export interface SemanticPhase {
  /** Active tongue index (0-5 for KO, AV, RU, CA, UM, DR) */
  activeTongue: number;
  /** Phase angle in radians [0, 2pi) */
  phaseAngle: number;
  /** Tongue weight (golden ratio weighted) */
  tongueWeight: number;
}

/**
 * Swarm coordination state (3D)
 */
export interface SwarmCoordination {
  /** Trust score from swarm consensus [0, 1] */
  trustScore: number;
  /** Byzantine vote count (normalized) */
  byzantineVotes: number;
  /** Spectral coherence [0, 1] */
  spectralCoherence: number;
}

// ═══════════════════════════════════════════════════════════════
// Unified Brain State
// ═══════════════════════════════════════════════════════════════

/**
 * Complete 21D brain state vector
 */
export interface BrainStateComponents {
  /** SCBE core context (6D) */
  scbeContext: SCBEContext;
  /** Dual Lattice navigation (6D) */
  navigation: NavigationVector;
  /** PHDM cognitive position (3D) */
  cognitivePosition: CognitivePosition;
  /** Sacred Tongues semantic phase (3D) */
  semanticPhase: SemanticPhase;
  /** Swarm coordination (3D) */
  swarmCoordination: SwarmCoordination;
}

/**
 * Risk decision levels (Layer 13)
 */
export type RiskDecision = 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';

/**
 * Detection mechanism type identifiers
 */
export type DetectionMechanism =
  | 'phase_distance'
  | 'curvature_accumulation'
  | 'threat_lissajous'
  | 'decimal_drift'
  | 'six_tonic';

/**
 * Detection result from a single mechanism
 */
export interface DetectionResult {
  /** Which mechanism produced this result */
  mechanism: DetectionMechanism;
  /** Anomaly score [0, 1] where 1 = highly anomalous */
  score: number;
  /** Whether this mechanism flagged the input */
  flagged: boolean;
  /** Attack types this mechanism detects */
  detectedAttackTypes: string[];
  /** Additional metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Combined detection assessment from all 5 mechanisms
 */
export interface CombinedAssessment {
  /** Individual detection results */
  detections: DetectionResult[];
  /** Combined anomaly score [0, 1] */
  combinedScore: number;
  /** Overall risk decision */
  decision: RiskDecision;
  /** Whether any mechanism flagged the input */
  anyFlagged: boolean;
  /** Count of flagging mechanisms */
  flagCount: number;
  /** Timestamp of assessment */
  timestamp: number;
}

/**
 * Agent trajectory point in the unified manifold
 */
export interface TrajectoryPoint {
  /** Step index */
  step: number;
  /** 21D state vector */
  state: number[];
  /** Embedded Poincare ball position */
  embedded: number[];
  /** Hyperbolic distance from safe origin */
  distance: number;
  /** Curvature at this point */
  curvature: number;
  /** Timestamp */
  timestamp: number;
}

/**
 * Agent trajectory (sequence of state transitions)
 */
export interface AgentTrajectory {
  /** Agent identifier */
  agentId: string;
  /** Agent classification */
  classification: 'honest' | 'neutral' | 'semi_honest' | 'semi_malicious' | 'malicious';
  /** Governance tier */
  governanceTier: GovernanceTier;
  /** Dimensional state */
  dimensionalState: DimensionalState;
  /** Trajectory points */
  points: TrajectoryPoint[];
  /** Combined assessment */
  assessment?: CombinedAssessment;
}

/**
 * Audit event for the unified brain
 */
export interface BrainAuditEvent {
  /** Event timestamp */
  timestamp: number;
  /** Layer where event occurred (1-14) */
  layer: number;
  /** Event type */
  eventType:
    | 'state_transition'
    | 'detection_alert'
    | 'boundary_violation'
    | 'consensus_vote'
    | 'risk_decision'
    | 'quarantine_action';
  /** Magnitude of state change */
  stateDelta: number;
  /** Distance from Poincare boundary */
  boundaryDistance: number;
  /** Event-specific metadata */
  metadata: Record<string, unknown>;
}

/**
 * Brain manifold configuration
 */
export interface BrainConfig {
  /** Poincare ball boundary epsilon (default: 1e-8) */
  boundaryEpsilon?: number;
  /** Detection threshold for individual mechanisms (default: 0.7) */
  detectionThreshold?: number;
  /** Combined score threshold for QUARANTINE (default: 0.5) */
  quarantineThreshold?: number;
  /** Combined score threshold for ESCALATE (default: 0.7) */
  escalateThreshold?: number;
  /** Combined score threshold for DENY (default: 0.9) */
  denyThreshold?: number;
  /** Maximum Byzantine faults to tolerate (default: 1) */
  maxByzantineFaults?: number;
  /** Curvature accumulation window size (default: 10) */
  curvatureWindow?: number;
  /** 6-tonic reference frequency in Hz (default: 440) */
  referenceFrequency?: number;
  /** Harmonic wall base ratio R (default: 1.5) */
  harmonicR?: number;
}

/**
 * Default brain configuration
 */
export const DEFAULT_BRAIN_CONFIG: Required<BrainConfig> = {
  boundaryEpsilon: 1e-8,
  detectionThreshold: 0.7,
  quarantineThreshold: 0.5,
  escalateThreshold: 0.7,
  denyThreshold: 0.9,
  maxByzantineFaults: 1,
  curvatureWindow: 10,
  referenceFrequency: 440,
  harmonicR: 1.5,
};
