/**
 * Polly Pads - Fleet Mini-IDE System + Mode Switching Workspaces
 *
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
 * @version 1.1.0
 * @author Issac Davis
 */

// Drone Core (original)
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

// Mode Switching System
export {
  ModePad,
  type SacredTongue,
  type ModePadConfig,
  type MemoryEntry,
} from './mode-pad.js';
// Specialist Modes (Dynamic Mode Switching)
export {
  ModeRegistry,
  ALL_MODE_IDS,
  type SpecialistModeId,
  type SpecialistMode,
  type ModeTool,
  type ModeState,
  type ModeSwitchEvent,
} from './specialist-modes.js';

// Closed Network (Air-Gapped Communications)
export {
  ClosedNetwork,
  DEFAULT_CHANNELS,
  type NetworkChannel,
  type BlockedChannel,
  type NetworkMessage,
  type ChannelConfig,
  type NetworkStatus,
} from './closed-network.js';

// Mission Coordinator & Squad (Byzantine Consensus)
export {
  MissionCoordinator,
  Squad,
  BFT,
  type CrisisType,
  type VoteDecision,
  type Vote,
  type VotingSession,
  type SquadMember,
  type ModeAssignment,
  type ConsensusResult,
} from './mission-coordinator.js';

// ============================================================================
// Quick Start Example
// ============================================================================

// Specialist Modes
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
  type SpecialistMode,
  type ModeTool,
  type ModeActionResult,
  type ModeState,
  type ModeSwitchEvent,
  type SquadVote,
  type CrisisType,
  type ModeAssignment,
  type ModeConfig,
  MODE_CONFIGS,
} from './modes/index.js';

// Closed Network
export {
  ClosedNetwork,
  DEFAULT_CLOSED_CONFIG,
  BLOCKED_NETWORKS,
  type NetworkChannel,
  type BlockedCategory,
  type NetworkMessage,
  type ClosedNetworkConfig,
} from './closed-network.js';

// Squad Coordination (Byzantine Consensus)
export {
  Squad,
  type ConsensusDecision,
  type SquadProposal,
  type SquadConfig,
} from './squad.js';

// Mission Coordinator
export {
  MissionCoordinator,
  type MissionPhase,
  type CrisisAssessment,
} from './mission-coordinator.js';

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
