/**
 * @file index.ts
 * @module game
 * @layer All Layers
 * @component Spiral Forge RPG — Module Entry Point
 *
 * Exports all game subsystems for use by Godot client, API endpoints,
 * and training pipeline.
 */

// Core types
export * from './types.js';

// Companion system (21D canonical state entities)
export {
  createCompanion,
  deriveCombatStats,
  applyTongueExperience,
  applyCombatResult,
  applyDrift,
  restCompanion,
  currentEvolutionStage,
  checkEvolution,
  isOverEvolved,
  updateDisciplineTrait,
} from './companion.js';
export type { Companion, DerivedCombatStats } from './companion.js';

// Combat system (Cl(4,0) bivector type advantage)
export {
  tongueToBivector,
  computeTypeAdvantage,
  companionTypeAdvantage,
  calculateDamage,
  createEncounter,
  applyTransform,
  evaluateTransformRisk,
  calculateFormationEffectiveness,
} from './combat.js';
export type { MathEncounterState } from './combat.js';

// Sacred egg hatching (behavioral selection in B^6)
export {
  checkHatchableEggs,
  canHatchEgg,
  eggStartingTongue,
  getAllEggDefinitions,
} from './sacredEggs.js';
export type { HatchResult } from './sacredEggs.js';

// Branching evolution system
export {
  getAvailableEvolutions,
  evolveCompanion,
  getAllEvolutionTrees,
} from './evolution.js';
export type { EvolutionPath } from './evolution.js';

// Symbiotic network (graph Laplacian topology)
export { SymbioticNetwork } from './symbioticNetwork.js';
export type { NetworkBonuses } from './symbioticNetwork.js';

// Player skill tree (6 paths × 4 tiers)
export {
  createSkillState,
  getSkillsForPath,
  getSkill,
  canUnlockSkill,
  unlockSkill,
  getHarmonyAbilities,
  totalSkillCount,
  getAllSkills,
} from './skillTree.js';
export type { PlayerSkillState } from './skillTree.js';

// Tongue regions & tower floors
export {
  REGIONS,
  getRegionByTongue,
  getRegionById,
  getTowerFloor,
  getRank,
  getFloorRange,
} from './regions.js';

// Codex terminal (SCBE-gated internet access)
export { CodexTerminal } from './codexTerminal.js';
export type { CodexRequest, CodexEvaluation, CodexCategory } from './codexTerminal.js';
