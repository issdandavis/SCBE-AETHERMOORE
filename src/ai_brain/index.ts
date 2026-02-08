/**
 * @file index.ts
 * @module ai_brain
 * @layer Layer 1-14 (Unified)
 * @component AI Brain Mapping Module
 * @version 1.2.0
 * @since 2026-02-07
 *
 * Complete AI Brain Mapping - Multi-Vectored Quasi-Space Architecture
 * with Lattice Mesh Integration.
 *
 * Unifies all SCBE-AETHERMOORE components into a single coherent "AI brain"
 * architecture operating across a 21D manifold.
 *
 * Components:
 * - Unified Brain State (21D): SCBE(6) + Navigation(6) + Cognitive(3) + Semantic(3) + Swarm(3)
 * - 5 Orthogonal Detection Mechanisms (combined AUC: 1.000)
 * - BFT Consensus (corrected: 3f+1 formula)
 * - Quasicrystal Icosahedral Projection
 * - Cryptographic Audit Logger
 * - Trajectory Simulator (multi-profile agent behavior)
 * - Immune Response System (GeoSeal suspicion/quarantine)
 * - Flux State Management (POLLY/QUASI/DEMI/COLLAPSED tiered access)
 * - Swarm Formation Coordination (geometric governance formations)
 * - Brain Integration Pipeline (end-to-end unified pipeline)
 */

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

export {
  BRAIN_DIMENSIONS,
  BRAIN_EPSILON,
  DEFAULT_BRAIN_CONFIG,
  PHI,
  POINCARE_MAX_NORM,
  type AgentTrajectory,
  type BrainAuditEvent,
  type BrainConfig,
  type BrainStateComponents,
  type CognitivePosition,
  type CombinedAssessment,
  type DetectionMechanism,
  type DetectionResult,
  type NavigationVector,
  type RiskDecision,
  type SCBEContext,
  type SemanticPhase,
  type SwarmCoordination,
  type TrajectoryPoint,
} from './types.js';

// ═══════════════════════════════════════════════════════════════
// Unified Brain State (21D Manifold)
// ═══════════════════════════════════════════════════════════════

export {
  UnifiedBrainState,
  applyGoldenWeighting,
  euclideanDistance,
  goldenWeightProduct,
  hyperbolicDistanceSafe,
  mobiusAddSafe,
  safePoincareEmbed,
  vectorNorm,
} from './unified-state.js';

// ═══════════════════════════════════════════════════════════════
// Detection Mechanisms
// ═══════════════════════════════════════════════════════════════

export {
  detectCurvatureAccumulation,
  detectDecimalDrift,
  detectPhaseDistance,
  detectSixTonic,
  detectThreatLissajous,
  runCombinedDetection,
} from './detection.js';

// ═══════════════════════════════════════════════════════════════
// BFT Consensus
// ═══════════════════════════════════════════════════════════════

export { BFTConsensus, type ConsensusResult, type ConsensusVote } from './bft-consensus.js';

// ═══════════════════════════════════════════════════════════════
// Quasi-Space Projection
// ═══════════════════════════════════════════════════════════════

export {
  brainStateToPenrose,
  classifyVoxelRealm,
  createOctreeRoot,
  icosahedralProjection,
  octreeInsert,
  quasicrystalPotential,
  type OctreeNode,
  type VoxelRealm,
} from './quasi-space.js';

// ═══════════════════════════════════════════════════════════════
// Audit Logger
// ═══════════════════════════════════════════════════════════════

export { BrainAuditLogger } from './audit.js';

// ═══════════════════════════════════════════════════════════════
// Trajectory Simulator
// ═══════════════════════════════════════════════════════════════

export {
  AGENT_PROFILES,
  SeededRNG,
  generateMixedBatch,
  generateTrajectory,
  type AgentProfile,
  type SimulationConfig,
} from './trajectory-simulator.js';

// ═══════════════════════════════════════════════════════════════
// Immune Response System
// ═══════════════════════════════════════════════════════════════

export {
  DEFAULT_IMMUNE_CONFIG,
  ImmuneResponseSystem,
  type AgentImmuneStatus,
  type ImmuneConfig,
  type ImmuneEvent,
  type ImmuneState,
} from './immune-response.js';

// ═══════════════════════════════════════════════════════════════
// Flux State Management
// ═══════════════════════════════════════════════════════════════

export {
  DEFAULT_FLUX_CONFIG,
  FluxStateManager,
  POLYHEDRA,
  type AgentFluxRecord,
  type FluxConfig,
  type FluxState,
  type PolyhedronAccess,
  type PolyhedronCategory,
} from './flux-states.js';

// ═══════════════════════════════════════════════════════════════
// Swarm Formation Coordination
// ═══════════════════════════════════════════════════════════════

export {
  DEFAULT_SWARM_CONFIG,
  SwarmFormationManager,
  type FormationPosition,
  type FormationType,
  type SwarmConfig,
  type SwarmFormation,
} from './swarm-formation.js';

// ═══════════════════════════════════════════════════════════════
// Brain Integration Pipeline
// ═══════════════════════════════════════════════════════════════

export {
  BrainIntegrationPipeline,
  DEFAULT_INTEGRATION_CONFIG,
  type AgentAssessment,
  type EndToEndResult,
  type IntegrationConfig,
  type TrialResult,
} from './brain-integration.js';
