/**
 * @file index.ts
 * @module aethermon
 * @layer Layer 3, Layer 5, Layer 12, Layer 13
 * @component AETHERMON — Module Entry Point
 *
 * AETHERMON: a creature-raising virtual-pet battler set in the
 * Aethermoore realm. Hatch an egg, manage care meters, train stats,
 * branch through a 28-species evolution graph, and climb the Spiral
 * Arena. Play it: `npm run game:aethermon` (or `:demo`).
 */

// Core types & constants
export * from './types.js';

// Deterministic RNG
export { createRng, nextFloat, nextInt, chance, pick } from './rng.js';
export type { Rng } from './rng.js';

// Move catalog
export { MOVES, allMoveIds, getMove } from './moves.js';

// Species catalog & evolution graph
export { SPECIES, STARTER_EGG_IDS, allSpecies, speciesByStage, getSpecies } from './species.js';

// Regions of Aethermoore (canon geography)
export { REGIONS, REGION_IDS, getRegion } from './regions.js';
export type { RegionDef, RegionId } from './regions.js';

// Creature lifecycle (care, training, leveling, lifespan)
export {
  HUNGER_DECAY,
  ENERGY_DECAY,
  createMonster,
  effectiveStats,
  lifespanRemaining,
  isLifespanExpired,
  xpToNext,
  xpReward,
  gainXp,
  tick,
  feed,
  rest,
  play,
  praise,
  scold,
  train,
  dominantTrainedStat,
  describeCare,
  isStatKey,
} from './monster.js';
export type { CareResult, CreateMonsterOptions } from './monster.js';

// Branching evolution engine
export {
  evaluateRequirement,
  evolutionOptions,
  selectEvolution,
  evolve,
  maxHp,
} from './evolution.js';
export type { EvolutionOption, EvolutionResult } from './evolution.js';

// Battle engine
export {
  toCombatant,
  wildCombatant,
  affinityMultiplier,
  rollDamage,
  createBattle,
  chooseAiAction,
  performRound,
  autoBattle,
  applyBattleResult,
} from './battle.js';
export type { DamageRoll, BattleAftermath } from './battle.js';

// Game orchestration (eggs, regions, encounters, arena, generations, saves)
export {
  ARENA_LADDER,
  newGame,
  warmEgg,
  travel,
  communeWithGap,
  generateWildEncounter,
  nextArenaRival,
  arenaCombatant,
  recordBattleOutcome,
  isChampion,
  checkRebirth,
  serializeGame,
  deserializeGame,
} from './game.js';
export type { WarmResult, HollowResult, RebirthResult } from './game.js';
