/**
 * Fleet Module - Swarm Coordination System
 *
 * Provides dimensional state management and ODE-based flux dynamics
 * for coordinating multi-agent swarms in the SCBE visual system.
 *
 * Key concepts:
 * - Dimensional States: POLLY, QUASI, DEMI, COLLAPSED based on flux ν
 * - Governance Tiers: KO, AV, RU, CA, UM, DR (Sacred Tongue alignment)
 * - PollyPads: Coordination points where members maintain full presence
 * - Flux ODE: dν/dt = α(ν_target - ν) - β*decay + γ*coherence_boost
 *
 * @module fleet
 */

// Types and utilities
export {
  // Types
  DimensionalState,
  FluxConfig,
  GovernanceTier,
  SwarmEvent,
  SwarmEventType,
  SwarmMemberState,
  // Constants
  DEFAULT_FLUX_CONFIG,
  DIMENSIONAL_THRESHOLDS,
  GOVERNANCE_DESCRIPTIONS,
  // Utility functions
  dimensionToGovernanceTier,
  getDimensionalState,
  getStateRange,
  governanceToDimensionIndex,
} from './types';

import type { FluxConfig, GovernanceTier } from './types';

// PollyPad management
export {
  DEFAULT_PAD_CONFIG,
  PollyPad,
  PollyPadConfig,
  PollyPadEvent,
  PollyPadManager,
  PollyPadStatistics,
} from './polly-pad';

import { PollyPad, PollyPadManager } from './polly-pad';

// Swarm coordination
export { SwarmCoordinator, SwarmStatistics } from './swarm';

import { SwarmCoordinator } from './swarm';

/**
 * Create a fully configured swarm coordinator with pad manager
 */
export function createSwarmCoordinator(
  fluxConfig?: Partial<FluxConfig>
): SwarmCoordinator {
  const padManager = new PollyPadManager();
  return new SwarmCoordinator(fluxConfig, padManager);
}

/**
 * Create a preconfigured swarm with one pad per governance tier
 */
export function createTieredSwarm(
  fluxConfig?: Partial<FluxConfig>
): {
  coordinator: SwarmCoordinator;
  pads: Record<GovernanceTier, PollyPad>;
} {
  const padManager = new PollyPadManager();
  const coordinator = new SwarmCoordinator(fluxConfig, padManager);

  const tiers: GovernanceTier[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
  const pads: Record<string, PollyPad> = {};

  for (const tier of tiers) {
    pads[tier] = padManager.createPad(`${tier} Pad`, tier);
  }

  return {
    coordinator,
    pads: pads as Record<GovernanceTier, PollyPad>,
  };
}
