/**
 * Network Module - Space Combat Communications
 *
 * Implements secure, redundant routing for interplanetary communications
 * with quantum-resistant encryption and combat-grade reliability.
 *
 * Components:
 * - SpaceTorRouter: Onion routing with trust scoring and load balancing
 * - HybridSpaceCrypto: Hybrid classical/quantum-resistant encryption
 * - CombatNetwork: Multipath routing with path health monitoring
 */

export {
  SpaceTorRouter,
  type RelayNode
} from './space-tor-router.js';

export {
  HybridSpaceCrypto
} from './hybrid-crypto.js';

export {
  CombatNetwork,
  type TransmissionResult,
  type PathHealth,
  type AcknowledgmentConfig,
  type CombatNetworkConfig
} from './combat-network.js';
