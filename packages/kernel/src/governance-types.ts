/**
 * @file governance-types.ts
 * @module kernel/governance-types
 * @layer Layer 13
 * @component Governance Type Definitions
 * @version 3.2.4
 *
 * Canonical governance types extracted from fleet/types.ts into the kernel.
 * These are pure type aliases with zero dependencies — they belong in the
 * kernel so that brain, fleet, and app can all import them without
 * circular dependencies.
 */

/**
 * Sacred Tongue governance tier — ascending trust levels.
 * Each tongue maps to a governance authority level.
 */
export type GovernanceTier = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/**
 * Dimensional state — determined by flux parameter nu.
 *
 * - POLLY:     nu >= 0.8 — Full dimensional access
 * - QUASI:     nu >= 0.5 — Partial dimensional access
 * - DEMI:      nu >= 0.1 — Minimal dimensional access
 * - COLLAPSED: nu < 0.1  — No dimensional access
 */
export type DimensionalState = 'POLLY' | 'QUASI' | 'DEMI' | 'COLLAPSED';

/**
 * Get the DimensionalState for a given flux parameter nu.
 */
export function getDimensionalState(nu: number): DimensionalState {
  if (nu >= 0.8) return 'POLLY';
  if (nu >= 0.5) return 'QUASI';
  if (nu >= 0.1) return 'DEMI';
  return 'COLLAPSED';
}
