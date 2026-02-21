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
export { DroneCore, createReconDrone, createCoderDrone, createDeployDrone, createResearchDrone, createGuardDrone, type DroneCoreConfig, type SacredTongue as DroneSacredTongue, type DroneClass, type FluxState, type TrustDecision, type SpectralIdentity, type Capability, } from './drone-core.js';
export { CapabilityStore, defaultStore, type CapabilityManifest, type CapabilityCategory, type StoreQuery, } from './capability-store.js';
export { ModePad, type SacredTongue, type ModePadConfig, type MemoryEntry, } from './mode-pad.js';
export { ModeRegistry, ALL_MODE_IDS, type SpecialistModeId, } from './specialist-modes.js';
export { type SpecialistMode as LegacySpecialistMode, type ModeTool as LegacyModeTool, type ModeState as LegacyModeState, type ModeSwitchEvent as LegacyModeSwitchEvent, } from './specialist-modes.js';
export { ClosedNetwork, DEFAULT_CLOSED_CONFIG, BLOCKED_NETWORKS, type NetworkChannel, type BlockedCategory, type NetworkMessage, type ClosedNetworkConfig, } from './closed-network.js';
export { MissionCoordinator, type MissionPhase, type CrisisAssessment, } from './mission-coordinator.js';
export { Squad, type ConsensusDecision, type SquadProposal, type SquadConfig, } from './squad.js';
export { BaseMode, EngineeringMode, NavigationMode, SystemsMode, ScienceMode, CommunicationsMode, MissionPlanningMode, createMode, createAllModes, type SpecialistMode as ModeName, type ModeTool as ModeCatalogTool, type ModeActionResult, type ModeState as ModeRuntimeState, type ModeSwitchEvent as ModeTransitionEvent, type SquadVote, type CrisisType, type ModeAssignment, type ModeConfig, MODE_CONFIGS, } from './modes/index.js';
export { type Lang, type PadMode, type Decision, type Voxel6, type VoxelScope, type QuorumVote, type QuorumProof, type SacredEggSeal, type VoxelRecord, langToTongueCode, tongueCodeToLang, validateVoxelRecord, } from './voxel-types.js';
//# sourceMappingURL=index.d.ts.map