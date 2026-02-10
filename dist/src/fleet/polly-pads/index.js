"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.BLOCKED_NETWORKS = exports.DEFAULT_CLOSED_CONFIG = exports.MODE_CONFIGS = exports.createAllModes = exports.createMode = exports.MissionPlanningMode = exports.CommunicationsMode = exports.ScienceMode = exports.SystemsMode = exports.NavigationMode = exports.EngineeringMode = exports.BaseMode = exports.BFT = exports.Squad = exports.MissionCoordinator = exports.DEFAULT_CHANNELS = exports.ClosedNetwork = exports.ALL_MODE_IDS = exports.ModeRegistry = exports.ModePad = exports.defaultStore = exports.CapabilityStore = exports.createGuardDrone = exports.createResearchDrone = exports.createDeployDrone = exports.createCoderDrone = exports.createReconDrone = exports.DroneCore = void 0;
exports.validateVoxelRecord = exports.tongueCodeToLang = exports.langToTongueCode = exports.BLOCKED_NETWORKS = exports.DEFAULT_CLOSED_CONFIG = exports.MODE_CONFIGS = exports.createAllModes = exports.createMode = exports.MissionPlanningMode = exports.CommunicationsMode = exports.ScienceMode = exports.SystemsMode = exports.NavigationMode = exports.EngineeringMode = exports.BaseMode = exports.BFT = exports.Squad = exports.MissionCoordinator = exports.DEFAULT_CHANNELS = exports.ClosedNetwork = exports.ALL_MODE_IDS = exports.ModeRegistry = exports.ModePad = exports.defaultStore = exports.CapabilityStore = exports.createGuardDrone = exports.createResearchDrone = exports.createDeployDrone = exports.createCoderDrone = exports.createReconDrone = exports.DroneCore = void 0;
// Drone Core (original)
var drone_core_js_1 = require("./drone-core.js");
Object.defineProperty(exports, "DroneCore", { enumerable: true, get: function () { return drone_core_js_1.DroneCore; } });
Object.defineProperty(exports, "createReconDrone", { enumerable: true, get: function () { return drone_core_js_1.createReconDrone; } });
Object.defineProperty(exports, "createCoderDrone", { enumerable: true, get: function () { return drone_core_js_1.createCoderDrone; } });
Object.defineProperty(exports, "createDeployDrone", { enumerable: true, get: function () { return drone_core_js_1.createDeployDrone; } });
Object.defineProperty(exports, "createResearchDrone", { enumerable: true, get: function () { return drone_core_js_1.createResearchDrone; } });
Object.defineProperty(exports, "createGuardDrone", { enumerable: true, get: function () { return drone_core_js_1.createGuardDrone; } });
// Capability Store
var capability_store_js_1 = require("./capability-store.js");
Object.defineProperty(exports, "CapabilityStore", { enumerable: true, get: function () { return capability_store_js_1.CapabilityStore; } });
Object.defineProperty(exports, "defaultStore", { enumerable: true, get: function () { return capability_store_js_1.defaultStore; } });
// Mode Switching System
var mode_pad_js_1 = require("./mode-pad.js");
Object.defineProperty(exports, "ModePad", { enumerable: true, get: function () { return mode_pad_js_1.ModePad; } });
// Specialist Modes (Dynamic Mode Switching)
var specialist_modes_js_1 = require("./specialist-modes.js");
Object.defineProperty(exports, "ModeRegistry", { enumerable: true, get: function () { return specialist_modes_js_1.ModeRegistry; } });
Object.defineProperty(exports, "ALL_MODE_IDS", { enumerable: true, get: function () { return specialist_modes_js_1.ALL_MODE_IDS; } });
// Closed Network (Air-Gapped Communications)
var closed_network_js_1 = require("./closed-network.js");
Object.defineProperty(exports, "ClosedNetwork", { enumerable: true, get: function () { return closed_network_js_1.ClosedNetwork; } });
Object.defineProperty(exports, "DEFAULT_CHANNELS", { enumerable: true, get: function () { return closed_network_js_1.DEFAULT_CHANNELS; } });
// Mission Coordinator & Squad (Byzantine Consensus)
var mission_coordinator_js_1 = require("./mission-coordinator.js");
Object.defineProperty(exports, "MissionCoordinator", { enumerable: true, get: function () { return mission_coordinator_js_1.MissionCoordinator; } });
Object.defineProperty(exports, "Squad", { enumerable: true, get: function () { return mission_coordinator_js_1.Squad; } });
Object.defineProperty(exports, "BFT", { enumerable: true, get: function () { return mission_coordinator_js_1.BFT; } });
// ============================================================================
// Quick Start Example
// ============================================================================
// Specialist Modes
var index_js_1 = require("./modes/index.js");
Object.defineProperty(exports, "BaseMode", { enumerable: true, get: function () { return index_js_1.BaseMode; } });
Object.defineProperty(exports, "EngineeringMode", { enumerable: true, get: function () { return index_js_1.EngineeringMode; } });
Object.defineProperty(exports, "NavigationMode", { enumerable: true, get: function () { return index_js_1.NavigationMode; } });
Object.defineProperty(exports, "SystemsMode", { enumerable: true, get: function () { return index_js_1.SystemsMode; } });
Object.defineProperty(exports, "ScienceMode", { enumerable: true, get: function () { return index_js_1.ScienceMode; } });
Object.defineProperty(exports, "CommunicationsMode", { enumerable: true, get: function () { return index_js_1.CommunicationsMode; } });
Object.defineProperty(exports, "MissionPlanningMode", { enumerable: true, get: function () { return index_js_1.MissionPlanningMode; } });
Object.defineProperty(exports, "createMode", { enumerable: true, get: function () { return index_js_1.createMode; } });
Object.defineProperty(exports, "createAllModes", { enumerable: true, get: function () { return index_js_1.createAllModes; } });
Object.defineProperty(exports, "MODE_CONFIGS", { enumerable: true, get: function () { return index_js_1.MODE_CONFIGS; } });
// Closed Network
var closed_network_js_2 = require("./closed-network.js");
Object.defineProperty(exports, "ClosedNetwork", { enumerable: true, get: function () { return closed_network_js_2.ClosedNetwork; } });
Object.defineProperty(exports, "DEFAULT_CLOSED_CONFIG", { enumerable: true, get: function () { return closed_network_js_2.DEFAULT_CLOSED_CONFIG; } });
Object.defineProperty(exports, "BLOCKED_NETWORKS", { enumerable: true, get: function () { return closed_network_js_2.BLOCKED_NETWORKS; } });
// Squad Coordination (Byzantine Consensus)
var squad_js_1 = require("./squad.js");
Object.defineProperty(exports, "Squad", { enumerable: true, get: function () { return squad_js_1.Squad; } });
// Mission Coordinator
var mission_coordinator_js_2 = require("./mission-coordinator.js");
Object.defineProperty(exports, "MissionCoordinator", { enumerable: true, get: function () { return mission_coordinator_js_2.MissionCoordinator; } });
// Voxel Record Types (6D addressing + Byzantine quorum)
var voxel_types_js_1 = require("./voxel-types.js");
Object.defineProperty(exports, "langToTongueCode", { enumerable: true, get: function () { return voxel_types_js_1.langToTongueCode; } });
Object.defineProperty(exports, "tongueCodeToLang", { enumerable: true, get: function () { return voxel_types_js_1.tongueCodeToLang; } });
Object.defineProperty(exports, "validateVoxelRecord", { enumerable: true, get: function () { return voxel_types_js_1.validateVoxelRecord; } });
//# sourceMappingURL=index.js.map