/**
 * @file game.ts
 * @module aethermon/game
 * @layer Layer 13
 * @component AETHERMON — Game Orchestration (eggs, encounters, arena, saves)
 *
 * Ties the subsystems into a tamer's journey: warm an egg until it
 * hatches, raise the creature, fight wild encounters scaled to your
 * level, and climb the ten-rung Spiral Arena. Save files are plain JSON
 * and replay deterministically (RNG state is part of the save).
 */

import type { Combatant, EggState, GameState, MonsterState, ArenaRival, Stats } from './types.js';
import {
  HEIRLOOM_CAP,
  HEIRLOOM_FRACTION,
  IDEAL_WEIGHT,
  STAGE_ORDER,
  STAT_KEYS,
  WARMTH_TO_HATCH,
  stageIndex,
} from './types.js';
import { STARTER_EGG_IDS, allSpecies, getSpecies } from './species.js';
import { createMonster, gainXp, isLifespanExpired, tick, xpReward } from './monster.js';
import { wildCombatant } from './battle.js';
import { getRegion } from './regions.js';
import { chance, createRng, nextInt, pick } from './rng.js';

// ---------------------------------------------------------------------------
//  Arena ladder
// ---------------------------------------------------------------------------

/** The ten rungs of the Spiral Arena. Defeat them all to win the game. */
export const ARENA_LADDER: readonly ArenaRival[] = [
  { name: 'Pip', title: 'Gate Sweeper', speciesId: 'kindlemote', level: 3 },
  { name: 'Moss', title: 'Courtyard Scrapper', speciesId: 'gloomkit', level: 6 },
  { name: 'Tessa', title: 'Spiral Initiate', speciesId: 'bitling', level: 9 },
  { name: 'Brand', title: 'Ward Sergeant', speciesId: 'pyreling', level: 12 },
  { name: 'Echo', title: 'Cache Keeper', speciesId: 'cipherwarden', level: 16 },
  { name: 'Sable', title: 'Night Auditor', speciesId: 'nullshade', level: 20 },
  { name: 'Forge', title: 'Bastion Marshal', speciesId: 'runewarden', level: 24 },
  { name: 'Vesper', title: 'Dusk Regent', speciesId: 'duskmonarch', level: 29 },
  { name: 'Halcyon', title: 'Dawn Regent', speciesId: 'solarchon', level: 34 },
  { name: 'The Archivist', title: 'Arena Sovereign', speciesId: 'lattice_sovereign', level: 40 },
];

// ---------------------------------------------------------------------------
//  Game lifecycle
// ---------------------------------------------------------------------------

/** Begin a new game: pick a starter egg, get a fresh state. */
export function newGame(tamerName: string, eggSpeciesId: string, seed: number): GameState {
  if (!STARTER_EGG_IDS.includes(eggSpeciesId)) {
    throw new RangeError(`Not a starter egg: ${eggSpeciesId}`);
  }
  return {
    version: 3,
    tamerName,
    egg: { speciesId: eggSpeciesId, warmth: 0, generation: 1 },
    monster: null,
    arenaRank: 0,
    totalBattlesWon: 0,
    totalBattlesLost: 0,
    rngState: seed >>> 0,
    hallOfFame: [],
    region: 'ember_reach',
    generation: 1,
    lineageMemorial: [],
  };
}

/** Result of warming an egg. */
export interface WarmResult {
  readonly hatched: boolean;
  readonly message: string;
}

/** Warm the egg. After enough warmth it hatches into the egg's mote. */
export function warmEgg(state: GameState, nickname: string): WarmResult {
  const egg: EggState | null = state.egg;
  if (!egg) return { hatched: false, message: 'There is no egg to warm.' };
  egg.warmth += 1;
  if (egg.warmth < WARMTH_TO_HATCH) {
    const species = getSpecies(egg.speciesId);
    return {
      hatched: false,
      message: `You cradle the ${species.name}. It wobbles… (${egg.warmth}/${WARMTH_TO_HATCH})`,
    };
  }
  const eggSpecies = getSpecies(egg.speciesId);
  const moteId = eggSpecies.evolvesTo[0].targetId;
  state.monster = createMonster(moteId, nickname, {
    generation: egg.generation ?? state.generation,
    heirloom: egg.heirloom,
  });
  state.monster.lineage.unshift(eggSpecies.id);
  state.egg = null;
  const mote = getSpecies(moteId);
  const heir = egg.heirloom && STAT_KEYS.some((k) => (egg.heirloom as Stats)[k] > 0);
  return {
    hatched: true,
    message:
      `The ${eggSpecies.name} cracks open — ${nickname} the ${mote.name} is born!` +
      (heir ? ` Echoes of the last generation stir in it.` : ''),
  };
}

// ---------------------------------------------------------------------------
//  Regions & the Hollow
// ---------------------------------------------------------------------------

/** Travel to another region of Aethermoore. */
export function travel(state: GameState, regionId: string): string {
  const region = getRegion(regionId); // validates
  state.region = region.id;
  return `You cross into ${region.name}. ${region.description}`;
}

/** Result of communing with the Hollow. */
export interface HollowResult {
  readonly ok: boolean;
  readonly message: string;
}

/**
 * Commune with the gap between the tongues. Only possible where the
 * region touches the Hollow (Null Vale). Marks the creature — the keys
 * to certain dark evolutions — at a real cost to its spirit.
 */
export function communeWithGap(state: GameState, monster: MonsterState): HollowResult {
  const region = getRegion(state.region);
  if (!region.touchesHollow) {
    return {
      ok: false,
      message: `The tongues all speak here. The gap cannot be reached from ${region.name}.`,
    };
  }
  tick(monster);
  monster.hollowExposure += 1;
  monster.care.mood = Math.max(0, monster.care.mood - 10);
  monster.care.discipline = Math.min(100, monster.care.discipline + 5);
  return {
    ok: true,
    message:
      `${monster.nickname} stares into the place where no tongue claims authority. ` +
      `Something stares back. (Hollow exposure: ${monster.hollowExposure})`,
  };
}

// ---------------------------------------------------------------------------
//  Encounters
// ---------------------------------------------------------------------------

/**
 * Generate a wild encounter near the creature's level: a random species
 * at the same stage (or one below), level within ±2. Encounters lean
 * toward the current region's tongue (the local fauna speaks the local
 * language).
 */
export function generateWildEncounter(state: GameState, monster: MonsterState): Combatant {
  const rng = createRng(state.rngState);
  const species = getSpecies(monster.speciesId);
  const region = getRegion(state.region);
  const myStage = stageIndex(species.stage);
  const minStage = Math.max(1, myStage - 1); // never eggs
  let candidates = allSpecies().filter((s) => {
    const idx = stageIndex(s.stage);
    return idx >= minStage && idx <= Math.max(1, myStage);
  });
  const locals = candidates.filter((s) => s.element === region.tongue);
  if (locals.length > 0 && chance(rng, region.elementBias)) {
    candidates = locals;
  }
  const wildSpecies = pick(rng, candidates);
  const level = Math.max(1, monster.level + nextInt(rng, -2, 2));
  const result = wildCombatant(wildSpecies, level);
  state.rngState = rng.state;
  return result;
}

/** The next arena rival, or null if the ladder is cleared. */
export function nextArenaRival(state: GameState): ArenaRival | null {
  return state.arenaRank < ARENA_LADDER.length ? ARENA_LADDER[state.arenaRank] : null;
}

/** Build the combatant for an arena rival. */
export function arenaCombatant(rival: ArenaRival): Combatant {
  const species = getSpecies(rival.speciesId);
  return wildCombatant(species, rival.level, `${rival.name}'s ${species.name}`);
}

/**
 * Record the outcome of a battle at game level: XP, win/loss tallies and
 * arena progression. Returns levels gained.
 */
export function recordBattleOutcome(
  state: GameState,
  monster: MonsterState,
  enemyLevel: number,
  won: boolean,
  wasArena: boolean
): number {
  let levels = 0;
  if (won) {
    state.totalBattlesWon += 1;
    levels = gainXp(monster, xpReward(enemyLevel));
    if (wasArena) state.arenaRank += 1;
  } else {
    state.totalBattlesLost += 1;
    levels = gainXp(monster, Math.floor(xpReward(enemyLevel) / 4));
  }
  return levels;
}

/** True once the final arena rival has been defeated. */
export function isChampion(state: GameState): boolean {
  return state.arenaRank >= ARENA_LADDER.length;
}

// ---------------------------------------------------------------------------
//  Lifespan & generations (V-Pet rule: every form has its season)
// ---------------------------------------------------------------------------

/** What the line keeps when a generation ends. */
export interface RebirthResult {
  readonly memorialEntry: string;
  readonly eggSpeciesId: string;
  readonly heirloom: Stats;
  readonly nextGeneration: number;
}

/**
 * If the creature's current form has run out its lifespan, it returns
 * to its line's egg. The tamer keeps a memorial entry, and the next
 * generation inherits HEIRLOOM_FRACTION of accumulated training (plus
 * the previous heirloom), capped per stat — mastery survives death.
 * Returns null while the creature still has time.
 */
export function checkRebirth(state: GameState): RebirthResult | null {
  const monster = state.monster;
  if (!monster || !isLifespanExpired(monster)) return null;
  const species = getSpecies(monster.speciesId);
  const heirloom: Stats = { hp: 0, atk: 0, def: 0, spd: 0 };
  for (const key of STAT_KEYS) {
    heirloom[key] = Math.min(
      HEIRLOOM_CAP,
      Math.floor((monster.trainBonus[key] + monster.heirloom[key]) * HEIRLOOM_FRACTION)
    );
  }
  const firstAncestor = monster.lineage[0];
  const eggSpeciesId = STARTER_EGG_IDS.includes(firstAncestor) ? firstAncestor : 'ember_egg';
  const memorialEntry =
    `${monster.nickname} the ${species.name} ` +
    `(Gen ${monster.generation}, lived ${monster.ageTicks} ticks)`;
  state.lineageMemorial.push(memorialEntry);
  state.generation += 1;
  state.egg = { speciesId: eggSpeciesId, warmth: 0, heirloom, generation: state.generation };
  state.monster = null;
  return { memorialEntry, eggSpeciesId, heirloom, nextGeneration: state.generation };
}

// ---------------------------------------------------------------------------
//  Save / load
// ---------------------------------------------------------------------------

/** Serialize game state to a JSON string. */
export function serializeGame(state: GameState): string {
  return JSON.stringify(state, null, 2);
}

/** Migrate a version-1 save (pre-regions/generations) in place. */
function migrateV1(state: GameState): void {
  const mutable = state as unknown as Record<string, unknown>;
  mutable.version = 2;
  mutable.region = mutable.region ?? 'ember_reach';
  mutable.generation = mutable.generation ?? 1;
  mutable.lineageMemorial = mutable.lineageMemorial ?? [];
  if (state.monster !== null) {
    const monster = state.monster as unknown as Record<string, unknown>;
    monster.stageAgeTicks = monster.stageAgeTicks ?? 0;
    monster.scars = monster.scars ?? 0;
    monster.consecutiveBattles = monster.consecutiveBattles ?? 0;
    monster.hollowExposure = monster.hollowExposure ?? 0;
    monster.generation = monster.generation ?? 1;
    monster.heirloom = monster.heirloom ?? { hp: 0, atk: 0, def: 0, spd: 0 };
  }
  if (state.egg) {
    state.egg.generation = state.egg.generation ?? 1;
  }
}

/** Migrate a version-2 save (pre-daily-life) in place. */
function migrateV2(state: GameState): void {
  const mutable = state as unknown as Record<string, unknown>;
  mutable.version = 3;
  if (state.monster !== null) {
    const monster = state.monster as unknown as Record<string, unknown>;
    const stage = getSpecies(state.monster.speciesId).stage;
    monster.weightKb = monster.weightKb ?? IDEAL_WEIGHT[stage];
    monster.residue = monster.residue ?? 0;
    monster.glitched = monster.glitched ?? false;
  }
}

/**
 * Parse and validate a save file. Version-1 and -2 saves are migrated
 * forward. Throws on malformed input.
 */
export function deserializeGame(json: string): GameState {
  const raw: unknown = JSON.parse(json);
  if (typeof raw !== 'object' || raw === null) throw new TypeError('Save is not an object');
  const state = raw as GameState;
  const version = state.version as number;
  if (version !== 1 && version !== 2 && version !== 3) {
    throw new TypeError(`Unsupported save version: ${String(version)}`);
  }
  if (typeof state.tamerName !== 'string') throw new TypeError('Save missing tamerName');
  if (typeof state.rngState !== 'number') throw new TypeError('Save missing rngState');
  if (version === 1) migrateV1(state);
  if (version <= 2) migrateV2(state);
  getRegion(state.region); // validates region exists
  if (state.monster !== null) {
    getSpecies(state.monster.speciesId); // validates species exists
    if (!STAGE_ORDER.includes(getSpecies(state.monster.speciesId).stage)) {
      throw new TypeError('Save has invalid species stage');
    }
  }
  if (state.egg !== null && state.egg !== undefined) {
    getSpecies(state.egg.speciesId);
  }
  return state;
}
