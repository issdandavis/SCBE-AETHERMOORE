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

// Drone Core
export {
  DroneCore,
  createReconDrone,
  createCoderDrone,
  createDeployDrone,
  createResearchDrone,
  createGuardDrone,
  type DroneCoreConfig,
  type SacredTongue,
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
