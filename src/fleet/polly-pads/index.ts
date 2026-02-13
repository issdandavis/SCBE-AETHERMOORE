/**
 * Polly Pads - Fleet Mini-IDE System + Mode Switching Workspaces
 *
 * Consolidated export surface for drone core, mode-switching systems,
 * closed-network comms, squad consensus, and mission coordination.
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
export {
  ModeRegistry,
  ALL_MODE_IDS,
  type SpecialistModeId,
  type SpecialistMode,
  type ModeTool,
  type ModeState,
  type ModeSwitchEvent,
} from './specialist-modes.js';

// Full specialist mode classes + factories
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
