/**
 * @file evolution.ts
 * @module game/evolution
 * @layer Layer 5, Layer 12
 * @component Branching Evolution — Behavioral Selection in R^6
 *
 * Evolution determined by tongue distribution, drift exposure, fleet usage,
 * scar events, and hollow interaction. NOT level thresholds.
 *
 * A3: Causality — evolution is deterministic from behavioral history.
 */

import {
  TongueCode,
  TongueVector,
  TONGUE_CODES,
  EvolutionStage,
  DisciplineTrait,
  EggType,
} from './types.js';
import type { Companion } from './companion.js';

// ---------------------------------------------------------------------------
//  Evolution Path Definitions
// ---------------------------------------------------------------------------

export interface EvolutionPath {
  /** Unique ID for this evolution target */
  readonly targetSpeciesId: string;

  /** Display name */
  readonly name: string;

  /** Required evolution stage to trigger */
  readonly requiredStage: EvolutionStage;

  /** Minimum values in tongue position (null = no requirement) */
  readonly tongueRequirements: Partial<Record<TongueCode, number>>;

  /** Required discipline trait (null = any) */
  readonly requiredTrait: DisciplineTrait | null;

  /** Minimum bond level */
  readonly minBondLevel: number;

  /** Minimum scar count (losses required for some dark evolutions) */
  readonly minScars: number;

  /** Minimum hollow exposure (late game, 7th tongue contact) */
  readonly minHollowExposure: number;

  /** Maximum drift level (some evolutions require stability) */
  readonly maxDrift: number;

  /** Minimum drift level (some evolutions require volatility) */
  readonly minDrift: number;

  /** Required egg origin (null = any) */
  readonly requiredEggOrigin: EggType | null;

  /** Description for codex */
  readonly description: string;
}

// ---------------------------------------------------------------------------
//  Evolution Tree Registry
// ---------------------------------------------------------------------------

/**
 * All evolution paths. Keyed by source species ID.
 * Each source can have multiple paths — that's the branching.
 */
const EVOLUTION_TREES: Map<string, EvolutionPath[]> = new Map();

function registerPaths(sourceSpecies: string, paths: EvolutionPath[]): void {
  EVOLUTION_TREES.set(sourceSpecies, paths);
}

// ---------------------------------------------------------------------------
//  Crysling Line (CA base, Crystal Egg)
// ---------------------------------------------------------------------------

registerPaths('crysling', [
  {
    targetSpeciesId: 'logicwyrm',
    name: 'Logicwyrm',
    requiredStage: 'form',
    tongueRequirements: { CA: 0.5 },
    requiredTrait: 'careful_verifier',
    minBondLevel: 2,
    minScars: 0,
    minHollowExposure: 0,
    maxDrift: 0.3,
    minDrift: 0,
    requiredEggOrigin: null,
    description: 'Pure logic mastery. Methodical and precise.',
  },
  {
    targetSpeciesId: 'prism_sentinel',
    name: 'Prism Sentinel',
    requiredStage: 'form',
    tongueRequirements: { CA: 0.3, UM: 0.3 },
    requiredTrait: null,
    minBondLevel: 3,
    minScars: 0,
    minHollowExposure: 0,
    maxDrift: 0.4,
    minDrift: 0,
    requiredEggOrigin: null,
    description: 'Balanced compute and security. A guardian of proofs.',
  },
  {
    targetSpeciesId: 'fracture_shade',
    name: 'Fracture Shade',
    requiredStage: 'form',
    tongueRequirements: { CA: 0.3, RU: 0.25 },
    requiredTrait: 'risk_tolerant',
    minBondLevel: 1,
    minScars: 3,
    minHollowExposure: 0,
    maxDrift: 1.0,
    minDrift: 0.3,
    requiredEggOrigin: null,
    description: 'Corrupted by entropy. Powerful but unstable.',
  },
]);

// Second-tier Crysling evolutions
registerPaths('logicwyrm', [
  {
    targetSpeciesId: 'axiom_dragon',
    name: 'Axiom Dragon',
    requiredStage: 'prime',
    tongueRequirements: { CA: 0.7 },
    requiredTrait: 'careful_verifier',
    minBondLevel: 5,
    minScars: 0,
    minHollowExposure: 0,
    maxDrift: 0.2,
    minDrift: 0,
    requiredEggOrigin: null,
    description: 'Peak logic. Proofs flow like breath.',
  },
]);

registerPaths('prism_sentinel', [
  {
    targetSpeciesId: 'proof_aegis',
    name: 'Proof Aegis',
    requiredStage: 'prime',
    tongueRequirements: { CA: 0.5, UM: 0.5 },
    requiredTrait: 'guardian',
    minBondLevel: 5,
    minScars: 0,
    minHollowExposure: 0,
    maxDrift: 0.3,
    minDrift: 0,
    requiredEggOrigin: null,
    description: 'Hodge harmony achieved. Impenetrable defense through verified logic.',
  },
]);

registerPaths('fracture_shade', [
  {
    targetSpeciesId: 'paradox_wraith',
    name: 'Paradox Wraith',
    requiredStage: 'prime',
    tongueRequirements: { RU: 0.4, CA: 0.4 },
    requiredTrait: 'risk_tolerant',
    minBondLevel: 3,
    minScars: 5,
    minHollowExposure: 1,
    maxDrift: 1.0,
    minDrift: 0.5,
    requiredEggOrigin: null,
    description: 'Born from paradox. Weaponizes contradiction.',
  },
]);

// ---------------------------------------------------------------------------
//  Emberspark Line (KO base, Ember Egg)
// ---------------------------------------------------------------------------

registerPaths('emberspark', [
  {
    targetSpeciesId: 'origin_drake',
    name: 'Origin Drake',
    requiredStage: 'form',
    tongueRequirements: { KO: 0.5 },
    requiredTrait: 'solo',
    minBondLevel: 2,
    minScars: 0,
    minHollowExposure: 0,
    maxDrift: 0.3,
    minDrift: 0,
    requiredEggOrigin: null,
    description: 'Pure command mastery. Initiative incarnate.',
  },
  {
    targetSpeciesId: 'phase_phoenix',
    name: 'Phase Phoenix',
    requiredStage: 'form',
    tongueRequirements: { KO: 0.3, DR: 0.3 },
    requiredTrait: 'collaborative',
    minBondLevel: 3,
    minScars: 0,
    minHollowExposure: 0,
    maxDrift: 0.4,
    minDrift: 0,
    requiredEggOrigin: null,
    description: 'Command meets structure. Verification through force.',
  },
  {
    targetSpeciesId: 'null_ember',
    name: 'Null Ember',
    requiredStage: 'form',
    tongueRequirements: { KO: 0.3 },
    requiredTrait: null,
    minBondLevel: 1,
    minScars: 2,
    minHollowExposure: 3,
    maxDrift: 1.0,
    minDrift: 0.4,
    requiredEggOrigin: null,
    description: 'Touched by the Hollow Tongue. Origin corrupted.',
  },
]);

registerPaths('origin_drake', [
  {
    targetSpeciesId: 'command_sovereign',
    name: 'Command Sovereign',
    requiredStage: 'apex',
    tongueRequirements: { KO: 0.8 },
    requiredTrait: 'solo',
    minBondLevel: 7,
    minScars: 0,
    minHollowExposure: 0,
    maxDrift: 0.2,
    minDrift: 0,
    requiredEggOrigin: null,
    description: 'Absolute authority. All formations obey.',
  },
]);

registerPaths('phase_phoenix', [
  {
    targetSpeciesId: 'eclipse_wyrm',
    name: 'Eclipse Wyrm',
    requiredStage: 'apex',
    tongueRequirements: { KO: 0.5, DR: 0.5 },
    requiredTrait: null,
    minBondLevel: 5,
    minScars: 0,
    minHollowExposure: 0,
    maxDrift: 0.3,
    minDrift: 0,
    requiredEggOrigin: 'hodge_eclipse',
    description: 'Hodge dual harmony. Command and Structure unified.',
  },
]);

// ---------------------------------------------------------------------------
//  Galewing Line (AV base, Gale Egg)
// ---------------------------------------------------------------------------

registerPaths('galewing', [
  {
    targetSpeciesId: 'drift_hawk',
    name: 'Drift Hawk',
    requiredStage: 'form',
    tongueRequirements: { AV: 0.5 },
    requiredTrait: 'fast_heuristic',
    minBondLevel: 2,
    minScars: 0,
    minHollowExposure: 0,
    maxDrift: 0.4,
    minDrift: 0,
    requiredEggOrigin: null,
    description: 'Speed incarnate. Repositions the whole fleet.',
  },
  {
    targetSpeciesId: 'ward_wind',
    name: 'Ward Wind',
    requiredStage: 'form',
    tongueRequirements: { AV: 0.3, UM: 0.3 },
    requiredTrait: 'guardian',
    minBondLevel: 3,
    minScars: 0,
    minHollowExposure: 0,
    maxDrift: 0.3,
    minDrift: 0,
    requiredEggOrigin: null,
    description: 'Transport meets security. Wind-carried wards.',
  },
]);

// ---------------------------------------------------------------------------
//  Voidmote Line (RU base, Void Egg)
// ---------------------------------------------------------------------------

registerPaths('voidmote', [
  {
    targetSpeciesId: 'entropy_serpent',
    name: 'Entropy Serpent',
    requiredStage: 'form',
    tongueRequirements: { RU: 0.5 },
    requiredTrait: 'risk_tolerant',
    minBondLevel: 2,
    minScars: 2,
    minHollowExposure: 0,
    maxDrift: 1.0,
    minDrift: 0.2,
    requiredEggOrigin: null,
    description: 'Chaos distilled. Every attack is a gamble.',
  },
  {
    targetSpeciesId: 'null_weaver',
    name: 'Null Weaver',
    requiredStage: 'form',
    tongueRequirements: { RU: 0.3, CA: 0.3 },
    requiredTrait: null,
    minBondLevel: 3,
    minScars: 0,
    minHollowExposure: 0,
    maxDrift: 0.5,
    minDrift: 0,
    requiredEggOrigin: null,
    description: 'Entropy controlled by compute. Paradox synthesizer.',
  },
]);

// ---------------------------------------------------------------------------
//  Wardling Line (UM base, Ward Egg)
// ---------------------------------------------------------------------------

registerPaths('wardling', [
  {
    targetSpeciesId: 'shield_sage',
    name: 'Shield Sage',
    requiredStage: 'form',
    tongueRequirements: { UM: 0.5 },
    requiredTrait: 'guardian',
    minBondLevel: 3,
    minScars: 0,
    minHollowExposure: 0,
    maxDrift: 0.2,
    minDrift: 0,
    requiredEggOrigin: null,
    description: 'Pure defense. Cleanses all corruption in range.',
  },
]);

// ---------------------------------------------------------------------------
//  Helixite Line (DR base, Helix Egg)
// ---------------------------------------------------------------------------

registerPaths('helixite', [
  {
    targetSpeciesId: 'fractal_golem',
    name: 'Fractal Golem',
    requiredStage: 'form',
    tongueRequirements: { DR: 0.5 },
    requiredTrait: 'careful_verifier',
    minBondLevel: 2,
    minScars: 0,
    minHollowExposure: 0,
    maxDrift: 0.2,
    minDrift: 0,
    requiredEggOrigin: null,
    description: 'Living verification. Terrain bends to its will.',
  },
  {
    targetSpeciesId: 'auth_tower',
    name: 'Auth Tower',
    requiredStage: 'form',
    tongueRequirements: { DR: 0.3, KO: 0.3 },
    requiredTrait: null,
    minBondLevel: 3,
    minScars: 0,
    minHollowExposure: 0,
    maxDrift: 0.3,
    minDrift: 0,
    requiredEggOrigin: null,
    description: 'Structure meets command. Walking authentication gate.',
  },
]);

// ---------------------------------------------------------------------------
//  Public API
// ---------------------------------------------------------------------------

/**
 * Get available evolution paths for a companion.
 * Checks all conditions against current companion state.
 */
export function getAvailableEvolutions(companion: Companion): EvolutionPath[] {
  const paths = EVOLUTION_TREES.get(companion.speciesId);
  if (!paths) return [];

  return paths.filter((path) => {
    // Check stage
    if (companion.evolutionStage !== path.requiredStage && !isStageAtLeast(companion.evolutionStage, path.requiredStage)) {
      return false;
    }

    // Check tongue requirements
    for (const [tongue, minVal] of Object.entries(path.tongueRequirements) as [TongueCode, number][]) {
      const idx = TONGUE_CODES.indexOf(tongue);
      if (companion.state.tonguePosition[idx] < minVal) return false;
    }

    // Check discipline trait
    if (path.requiredTrait && companion.disciplineTrait !== path.requiredTrait) return false;

    // Check bond level
    if (companion.bondLevel < path.minBondLevel) return false;

    // Check scars
    if (companion.scarCount < path.minScars) return false;

    // Check hollow exposure
    if (companion.hollowExposure < path.minHollowExposure) return false;

    // Check drift
    if (companion.driftLevel > path.maxDrift) return false;
    if (companion.driftLevel < path.minDrift) return false;

    // Check egg origin
    if (path.requiredEggOrigin && companion.eggOrigin !== path.requiredEggOrigin) return false;

    return true;
  });
}

/**
 * Execute an evolution. Mutates the companion in place.
 * Returns true if successful, false if path not available.
 */
export function evolveCompanion(companion: Companion, targetSpeciesId: string): boolean {
  const available = getAvailableEvolutions(companion);
  const path = available.find((p) => p.targetSpeciesId === targetSpeciesId);
  if (!path) return false;

  // Record evolution in lineage
  companion.evolutionLine.push(targetSpeciesId);

  // Update species (note: companion.speciesId is readonly, so we
  // return a new companion in practice — but for the game state
  // we update via the mutable wrapper)
  (companion as { speciesId: string }).speciesId = targetSpeciesId;
  companion.evolutionStage = path.requiredStage;
  companion.name = path.name;

  // Evolution boosts max seal integrity
  companion.maxSealIntegrity += 20;
  companion.sealIntegrity = companion.maxSealIntegrity;

  // Emotional burst
  companion.emotionalState = 'transcendent';

  return true;
}

/**
 * Get all registered evolution trees (for codex/UI display).
 */
export function getAllEvolutionTrees(): Map<string, EvolutionPath[]> {
  return new Map(EVOLUTION_TREES);
}

// ---------------------------------------------------------------------------
//  Helpers
// ---------------------------------------------------------------------------

const STAGE_ORDER: EvolutionStage[] = ['spark', 'form', 'prime', 'apex', 'transcendent'];

function isStageAtLeast(current: EvolutionStage, required: EvolutionStage): boolean {
  return STAGE_ORDER.indexOf(current) >= STAGE_ORDER.indexOf(required);
}
