/**
 * @file sacredEggs.ts
 * @module game/sacredEggs
 * @layer Layer 3, Layer 5
 * @component Sacred Egg Hatching — Behavioral Selection in B^6
 *
 * Eggs don't hatch randomly. They hatch when the player's accumulated
 * tongue experience hits specific regions in 6D tongue-space.
 * The egg you hatch reveals how you play.
 *
 * A4: Symmetry — Hodge dual eggs require symmetric pair balance.
 * A3: Causality — egg conditions are deterministic from history.
 */

import { TongueVector, TongueCode, TONGUE_CODES, EggType, BondType, tongueNorm } from './types.js';

// ---------------------------------------------------------------------------
//  Egg Condition Definitions
// ---------------------------------------------------------------------------

/** Condition function: takes tongue vector, returns true if region matched */
type EggCondition = (v: TongueVector) => boolean;

interface EggDefinition {
  readonly eggType: EggType;
  readonly name: string;
  readonly bondType: BondType;
  readonly dominantTongue: TongueCode | null;
  readonly condition: EggCondition;
  readonly description: string;
}

/** Helper: get tongue value by code from vector */
function tv(v: TongueVector, code: TongueCode): number {
  return v[TONGUE_CODES.indexOf(code)];
}

// ---------------------------------------------------------------------------
//  Mono-Tongue Eggs (dominant in one tongue)
// ---------------------------------------------------------------------------

const monoEggs: EggDefinition[] = [
  {
    eggType: 'mono_KO',
    name: 'Ember Egg',
    bondType: 'amplifier',
    dominantTongue: 'KO',
    condition: (v) => tv(v, 'KO') >= 0.6 && tv(v, 'KO') > 2 * tv(v, 'DR'),
    description: 'KO >= 0.6 AND KO > 2×DR',
  },
  {
    eggType: 'mono_AV',
    name: 'Gale Egg',
    bondType: 'scout',
    dominantTongue: 'AV',
    condition: (v) => tv(v, 'AV') >= 0.5 && tv(v, 'AV') > 1.5 * tv(v, 'UM'),
    description: 'AV >= 0.5 AND AV > 1.5×UM',
  },
  {
    eggType: 'mono_RU',
    name: 'Void Egg',
    bondType: 'disruptor',
    dominantTongue: 'RU',
    condition: (v) => tv(v, 'RU') >= 0.5 && tv(v, 'RU') > 1.5 * tv(v, 'CA'),
    description: 'RU >= 0.5 AND RU > 1.5×CA',
  },
  {
    eggType: 'mono_CA',
    name: 'Crystal Egg',
    bondType: 'processor',
    dominantTongue: 'CA',
    condition: (v) => tv(v, 'CA') >= 0.5 && tv(v, 'CA') > 1.5 * tv(v, 'RU'),
    description: 'CA >= 0.5 AND CA > 1.5×RU',
  },
  {
    eggType: 'mono_UM',
    name: 'Ward Egg',
    bondType: 'guardian',
    dominantTongue: 'UM',
    condition: (v) => tv(v, 'UM') >= 0.5 && tv(v, 'UM') > 1.5 * tv(v, 'AV'),
    description: 'UM >= 0.5 AND UM > 1.5×AV',
  },
  {
    eggType: 'mono_DR',
    name: 'Helix Egg',
    bondType: 'architect',
    dominantTongue: 'DR',
    condition: (v) => tv(v, 'DR') >= 0.5 && tv(v, 'DR') > 1.5 * tv(v, 'KO'),
    description: 'DR >= 0.5 AND DR > 1.5×KO',
  },
];

// ---------------------------------------------------------------------------
//  Hodge Dual Eggs (require pair balance)
// ---------------------------------------------------------------------------

const hodgeEggs: EggDefinition[] = [
  {
    eggType: 'hodge_eclipse',
    name: 'Eclipse Egg',
    bondType: 'harmonizer',
    dominantTongue: null,
    condition: (v) =>
      tv(v, 'KO') >= 0.4 && tv(v, 'DR') >= 0.4 && Math.abs(tv(v, 'KO') - tv(v, 'DR')) < 0.15,
    description: 'KO >= 0.4 AND DR >= 0.4 AND |KO-DR| < 0.15',
  },
  {
    eggType: 'hodge_storm',
    name: 'Storm Egg',
    bondType: 'balancer',
    dominantTongue: null,
    condition: (v) =>
      tv(v, 'AV') >= 0.4 && tv(v, 'UM') >= 0.4 && Math.abs(tv(v, 'AV') - tv(v, 'UM')) < 0.15,
    description: 'AV >= 0.4 AND UM >= 0.4 AND |AV-UM| < 0.15',
  },
  {
    eggType: 'hodge_paradox',
    name: 'Paradox Egg',
    bondType: 'synthesizer',
    dominantTongue: null,
    condition: (v) =>
      tv(v, 'RU') >= 0.4 && tv(v, 'CA') >= 0.4 && Math.abs(tv(v, 'RU') - tv(v, 'CA')) < 0.15,
    description: 'RU >= 0.4 AND CA >= 0.4 AND |RU-CA| < 0.15',
  },
];

// ---------------------------------------------------------------------------
//  Omni Egg (all tongues balanced)
// ---------------------------------------------------------------------------

const omniEgg: EggDefinition = {
  eggType: 'omni_prism',
  name: 'Prism Egg',
  bondType: 'nexus',
  dominantTongue: null,
  condition: (v) => v.every((val) => val >= 0.35),
  description: 'Every tongue >= 0.35',
};

// ---------------------------------------------------------------------------
//  All Eggs (evaluation order: omni first, then hodge, then mono)
// ---------------------------------------------------------------------------

const ALL_EGGS: readonly EggDefinition[] = [omniEgg, ...hodgeEggs, ...monoEggs];

// ---------------------------------------------------------------------------
//  Public API
// ---------------------------------------------------------------------------

export interface HatchResult {
  readonly eggType: EggType;
  readonly eggName: string;
  readonly bondType: BondType;
  readonly dominantTongue: TongueCode | null;
  readonly description: string;
}

/**
 * Check which eggs can hatch given a player's tongue accumulation vector.
 *
 * Evaluation order: Omni → Hodge → Mono (rarer eggs checked first).
 * Returns ALL matching eggs (player picks if multiple match).
 *
 * @param playerTongue - Player's accumulated tongue experience vector
 * @returns Array of hatchable eggs (empty if none qualify)
 */
export function checkHatchableEggs(playerTongue: TongueVector): HatchResult[] {
  const results: HatchResult[] = [];

  for (const egg of ALL_EGGS) {
    if (egg.condition(playerTongue)) {
      results.push({
        eggType: egg.eggType,
        eggName: egg.name,
        bondType: egg.bondType,
        dominantTongue: egg.dominantTongue,
        description: egg.description,
      });
    }
  }

  return results;
}

/**
 * Check if a specific egg type can hatch.
 */
export function canHatchEgg(playerTongue: TongueVector, eggType: EggType): boolean {
  const egg = ALL_EGGS.find((e) => e.eggType === eggType);
  if (!egg) return false;
  return egg.condition(playerTongue);
}

/**
 * Get the initial tongue position for a companion hatching from an egg.
 * The starting position is biased toward the egg's dominant tongue(s).
 */
export function eggStartingTongue(eggType: EggType): TongueVector {
  switch (eggType) {
    // Mono eggs: strong in dominant, weak elsewhere
    case 'mono_KO':
      return [0.6, 0.1, 0.1, 0.1, 0.1, 0.1];
    case 'mono_AV':
      return [0.1, 0.6, 0.1, 0.1, 0.1, 0.1];
    case 'mono_RU':
      return [0.1, 0.1, 0.6, 0.1, 0.1, 0.1];
    case 'mono_CA':
      return [0.1, 0.1, 0.1, 0.6, 0.1, 0.1];
    case 'mono_UM':
      return [0.1, 0.1, 0.1, 0.1, 0.6, 0.1];
    case 'mono_DR':
      return [0.1, 0.1, 0.1, 0.1, 0.1, 0.6];
    // Hodge eggs: balanced pair
    case 'hodge_eclipse':
      return [0.4, 0.1, 0.1, 0.1, 0.1, 0.4];
    case 'hodge_storm':
      return [0.1, 0.4, 0.1, 0.1, 0.4, 0.1];
    case 'hodge_paradox':
      return [0.1, 0.1, 0.4, 0.4, 0.1, 0.1];
    // Omni egg: balanced across all
    case 'omni_prism':
      return [0.35, 0.35, 0.35, 0.35, 0.35, 0.35];
  }
}

/**
 * Get all egg definitions (for UI display / codex).
 */
export function getAllEggDefinitions(): ReadonlyArray<{
  eggType: EggType;
  name: string;
  bondType: BondType;
  description: string;
}> {
  return ALL_EGGS.map((e) => ({
    eggType: e.eggType,
    name: e.name,
    bondType: e.bondType,
    description: e.description,
  }));
}
