/**
 * Polly Pads - Fleet Mini-IDE System + Mode Switching Workspaces
 *
 * Consolidated export surface for drone core, mode-switching systems,
 * closed-network comms, squad consensus, and mission coordination.
 * "Clone Trooper Field Upgrade Stations for AI Agents"
 *
 * Hot-swappable mini-IDEs that run on each AI agent in the fleet,
 * enabling real-time capability upgrades with SCBE security.
 *
 * Mode Switching: 6 specialist modes (Engineering, Navigation, Systems,
 * Science, Communications, Mission Planning) for autonomous operations
 * in Mars missions, disaster response, submarine ops, and autonomous fleets.
 *
 * @module fleet/polly-pads
 * @version 1.2.0
 * @author Issac Davis
 */

// Drone Core
export {
  DroneCore,
  createReconDrone,
  createCoderDrone,
  createDeployDrone,
  createResearchDrone,
  createGuardDrone,
  type DroneCoreConfig,
  type SacredTongue as DroneSacredTongue,
  type DroneClass,
  type FluxState,
  type TrustDecision,
  type SpectralIdentity,
  type Capability,
} from './drone-core.js';

// Capability Store
export {
  CapabilityStore,
  defaultStore,
  type CapabilityManifest,
  type CapabilityCategory,
  type StoreQuery,
} from './capability-store.js';

// Mode Pad
export {
  ModePad,
  type SacredTongue,
  type ModePadConfig,
  type MemoryEntry,
} from './mode-pad.js';

// Specialist Mode Registry (lightweight mode system)
// Specialist Modes (Dynamic Mode Switching) — legacy registry
export {
  ModeRegistry,
  ALL_MODE_IDS,
  type SpecialistModeId,
} from './specialist-modes.js';

// Specialist Modes (Refactored Mode Classes & Types)
export {
  type SpecialistMode as LegacySpecialistMode,
  type ModeTool as LegacyModeTool,
  type ModeState as LegacyModeState,
  type ModeSwitchEvent as LegacyModeSwitchEvent,
} from './specialist-modes.js';

// Full specialist mode classes + factories
// Closed Network (Air-Gapped Communications)
export {
  ClosedNetwork,
  DEFAULT_CLOSED_CONFIG,
  BLOCKED_NETWORKS,
  type NetworkChannel,
  type BlockedCategory,
  type NetworkMessage,
  type ClosedNetworkConfig,
} from './closed-network.js';

// Mission Coordinator (Smart Mode Assignment)
export {
  MissionCoordinator,
  type MissionPhase,
  type CrisisAssessment,
} from './mission-coordinator.js';

// Squad Coordination (Byzantine Consensus)
export {
  Squad,
  type ConsensusDecision,
  type SquadProposal,
  type SquadConfig,
} from './squad.js';

// Specialist Modes (Class-based implementations)
export {
  BaseMode,
  EngineeringMode,
  NavigationMode,
  SystemsMode,
  ScienceMode,
  CommunicationsMode,
  MissionPlanningMode,
  createMode,
  createAllModes,
  type SpecialistMode as ModeName,
  type ModeTool as ModeCatalogTool,
  type ModeActionResult,
  type ModeState as ModeRuntimeState,
  type ModeSwitchEvent as ModeTransitionEvent,
  type SquadVote,
  type CrisisType,
  type ModeAssignment,
  type ModeConfig,
  MODE_CONFIGS,
} from './modes/index.js';

// Closed Network (air-gapped comms)
export {
  ClosedNetwork,
  DEFAULT_CLOSED_CONFIG,
  BLOCKED_NETWORKS,
  type NetworkChannel,
  type BlockedCategory,
  type NetworkMessage,
  type ClosedNetworkConfig,
} from './closed-network.js';

// Squad Coordination (Byzantine consensus)
// Voxel Record Types (6D addressing + Byzantine quorum)
export {
  type Lang,
  type PadMode,
  type Decision,
  type Voxel6,
  type VoxelScope,
  type QuorumVote,
  type QuorumProof,
  type SacredEggSeal,
  type VoxelRecord,
  langToTongueCode,
  tongueCodeToLang,
  validateVoxelRecord,
} from './voxel-types.js';

// Decision Envelope (Mars-Grade Autonomy Boundaries)
export {
  EnvelopeManager,
  envelopeDecide,
  createEnvelope,
  validateEnvelope,
  matchAction,
  validateEmergencyKey,
  type EnvelopeBoundary,
  type MissionPhase as EnvelopeMissionPhase,
  type CommsState as EnvelopeCommsState,
  type ActionCategory,
  type EnvelopeRule,
  type DecisionEnvelope,
  type EnvelopeDecision,
} from './decision-envelope.js';

// Resource-Aware Harmonic Wall (Scarcity Multipliers)
export {
  scarcityMultiplier,
  combinedScarcity,
  resourceAwareHarmonicCost,
  resourceAwareDecide,
  predictResources,
  timeToCritical,
  ambientRiskScore,
  createDefaultResources,
  createResourceAwareUnit,
  type ResourceMetric,
  type ResourceState,
  type ResourceAwareUnitState,
  type ResourceAwareDecisionResult,
} from './resource-harmonic.js';

// Blackout MMR Audit Chain (Comms-Loss Resilient Logging)
export {
  MerkleAuditChain,
  BlackoutManager,
  hashEvent,
  type CommsState as BlackoutCommsState,
  type BlackoutEvent,
  type MMRNode,
  type MMRInclusionProof,
  type BlackoutRecord,
} from './blackout-audit.js';
