/**
 * Fleet Types and Dimensional State Management
 *
 * Defines dimensional states based on flux coefficient ν (nu):
 * - POLLY: Full dimensional presence (ν ≈ 1)
 * - QUASI: Partial dimensional engagement (0.5 < ν < 1)
 * - DEMI: Reduced dimensional footprint (0 < ν < 0.5)
 * - COLLAPSED: Minimal dimensional presence (ν ≈ 0)
 *
 * @module fleet/types
 */

/**
 * Dimensional state representing flux coefficient ranges
 */
export type DimensionalState = 'POLLY' | 'QUASI' | 'DEMI' | 'COLLAPSED';

/**
 * Governance tiers aligned with Sacred Tongues
 * Maps to the 6 dimensions of PHDM space
 */
export type GovernanceTier = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/**
 * Sacred Tongue descriptions for governance
 */
export const GOVERNANCE_DESCRIPTIONS: Record<GovernanceTier, string> = {
  KO: 'Kosmic Order - Strategic oversight and architectural governance',
  AV: 'Aetheric Vision - Review and quality assurance governance',
  RU: 'Runic Understanding - Testing and validation governance',
  CA: 'Causal Action - Implementation and execution governance',
  UM: 'Umbral Mystery - Security and risk governance',
  DR: 'Draconic Resonance - Deployment and operations governance',
};

/**
 * Dimensional state thresholds
 */
export const DIMENSIONAL_THRESHOLDS = {
  POLLY_MIN: 0.9,
  QUASI_MIN: 0.5,
  DEMI_MIN: 0.1,
  COLLAPSED_MAX: 0.1,
} as const;

/**
 * Flux dynamics configuration
 */
export interface FluxConfig {
  /** Attraction coefficient toward target */
  alpha: number;
  /** Decay coefficient */
  beta: number;
  /** Coherence boost coefficient */
  gamma: number;
  /** Time step for ODE integration */
  dt: number;
}

/**
 * Default flux configuration
 */
export const DEFAULT_FLUX_CONFIG: FluxConfig = {
  alpha: 0.3,
  beta: 0.05,
  gamma: 0.15,
  dt: 0.1,
};

/**
 * Swarm member state
 */
export interface SwarmMemberState {
  id: string;
  fluxCoefficient: number;
  dimensionalState: DimensionalState;
  governanceTier: GovernanceTier;
  coherence: number;
  lastUpdate: number;
  position6D?: number[];
}

/**
 * Swarm event types
 */
export type SwarmEventType =
  | 'state_change'
  | 'flux_update'
  | 'member_join'
  | 'member_leave'
  | 'coherence_shift'
  | 'governance_change';

/**
 * Swarm event payload
 */
export interface SwarmEvent {
  type: SwarmEventType;
  memberId: string;
  timestamp: number;
  previousState?: DimensionalState;
  newState?: DimensionalState;
  fluxCoefficient?: number;
  metadata?: Record<string, unknown>;
}

/**
 * Get dimensional state from flux coefficient
 *
 * @param nu - Flux coefficient (0 to 1)
 * @returns Corresponding dimensional state
 */
export function getDimensionalState(nu: number): DimensionalState {
  if (nu < 0 || nu > 1) {
    throw new Error(`Flux coefficient must be in [0, 1], got ${nu}`);
  }

  if (nu >= DIMENSIONAL_THRESHOLDS.POLLY_MIN) {
    return 'POLLY';
  } else if (nu >= DIMENSIONAL_THRESHOLDS.QUASI_MIN) {
    return 'QUASI';
  } else if (nu >= DIMENSIONAL_THRESHOLDS.DEMI_MIN) {
    return 'DEMI';
  } else {
    return 'COLLAPSED';
  }
}

/**
 * Get flux coefficient range for a dimensional state
 */
export function getStateRange(state: DimensionalState): { min: number; max: number } {
  switch (state) {
    case 'POLLY':
      return { min: DIMENSIONAL_THRESHOLDS.POLLY_MIN, max: 1.0 };
    case 'QUASI':
      return { min: DIMENSIONAL_THRESHOLDS.QUASI_MIN, max: DIMENSIONAL_THRESHOLDS.POLLY_MIN };
    case 'DEMI':
      return { min: DIMENSIONAL_THRESHOLDS.DEMI_MIN, max: DIMENSIONAL_THRESHOLDS.QUASI_MIN };
    case 'COLLAPSED':
      return { min: 0.0, max: DIMENSIONAL_THRESHOLDS.DEMI_MIN };
  }
}

/**
 * Map governance tier to PHDM dimension index
 */
export function governanceToDimensionIndex(tier: GovernanceTier): number {
  const mapping: Record<GovernanceTier, number> = {
    KO: 0,
    AV: 1,
    RU: 2,
    CA: 3,
    UM: 4,
    DR: 5,
  };
  return mapping[tier];
}

/**
 * Get governance tier from dimension index
 */
export function dimensionToGovernanceTier(index: number): GovernanceTier {
  const tiers: GovernanceTier[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
  if (index < 0 || index >= 6) {
    throw new Error(`Dimension index must be 0-5, got ${index}`);
  }
  return tiers[index];
}
