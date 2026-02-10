"use strict";
/**
 * Polly Pads - Fleet Mini-IDE System
 *
 * "Clone Trooper Field Upgrade Stations for AI Agents"
 *
 * Hot-swappable mini-IDEs that run on each AI agent in the fleet,
 * enabling real-time capability upgrades with SCBE security.
 *
 * @module fleet/polly-pads
 * @version 1.0.0
 * @author Issac Davis
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.defaultStore = exports.CapabilityStore = exports.createGuardDrone = exports.createResearchDrone = exports.createDeployDrone = exports.createCoderDrone = exports.createReconDrone = exports.DroneCore = void 0;
// Drone Core
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
// ============================================================================
// Quick Start Example
// ============================================================================
/**
 * @example
 * ```typescript
 * import {
 *   createReconDrone,
 *   defaultStore
 * } from 'scbe-aethermoore/fleet/polly-pads';
 *
 * // Create a RECON drone named "REX"
 * const rex = createReconDrone('REX');
 *
 * // Find compatible capabilities
 * const available = defaultStore.getCompatibleCapabilities(
 *   rex.spectralIdentity.tongue,
 *   rex.class,
 *   rex.trustRadius
 * );
 *
 * // Load browser-use capability
 * const browserUse = defaultStore.getCapability('browser-use');
 * if (browserUse) {
 *   const cap = defaultStore.toCapability(browserUse);
 *   rex.loadCapability(cap);
 * }
 *
 * // Check loadout
 * console.log(rex.loadout);
 * // => [{ id: 'browser-use', name: 'Browser Use', active: true, ... }]
 *
 * // Check Cymatic voxel access (your IP!)
 * const canAccess = rex.canAccessVoxel(0.5, 0.5);
 * console.log('Can access voxel:', canAccess);
 * ```
 */
//# sourceMappingURL=index.js.map