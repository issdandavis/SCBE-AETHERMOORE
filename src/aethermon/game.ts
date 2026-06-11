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

import type { Combatant, EggState, GameState, MonsterState, ArenaRival } from './types.js';
import { STAGE_ORDER, WARMTH_TO_HATCH, stageIndex } from './types.js';
import { STARTER_EGG_IDS, allSpecies, getSpecies } from './species.js';
import { createMonster, gainXp, xpReward } from './monster.js';
import { wildCombatant } from './battle.js';
import { createRng, nextInt, pick } from './rng.js';

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
    version: 1,
    tamerName,
    egg: { speciesId: eggSpeciesId, warmth: 0 },
    monster: null,
    arenaRank: 0,
    totalBattlesWon: 0,
    totalBattlesLost: 0,
    rngState: seed >>> 0,
    hallOfFame: [],
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
  state.monster = createMonster(moteId, nickname);
  state.monster.lineage.unshift(eggSpecies.id);
  state.egg = null;
  const mote = getSpecies(moteId);
  return {
    hatched: true,
    message: `The ${eggSpecies.name} cracks open — ${nickname} the ${mote.name} is born!`,
  };
}

// ---------------------------------------------------------------------------
//  Encounters
// ---------------------------------------------------------------------------

/**
 * Generate a wild encounter near the creature's level: a random species
 * at the same stage (or one below), level within ±2.
 */
export function generateWildEncounter(state: GameState, monster: MonsterState): Combatant {
  const rng = createRng(state.rngState);
  const species = getSpecies(monster.speciesId);
  const myStage = stageIndex(species.stage);
  const minStage = Math.max(1, myStage - 1); // never eggs
  const candidates = allSpecies().filter((s) => {
    const idx = stageIndex(s.stage);
    return idx >= minStage && idx <= Math.max(1, myStage);
  });
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
//  Save / load
// ---------------------------------------------------------------------------

/** Serialize game state to a JSON string. */
export function serializeGame(state: GameState): string {
  return JSON.stringify(state, null, 2);
}

/** Parse and validate a save file. Throws on malformed input. */
export function deserializeGame(json: string): GameState {
  const raw: unknown = JSON.parse(json);
  if (typeof raw !== 'object' || raw === null) throw new TypeError('Save is not an object');
  const state = raw as GameState;
  if (state.version !== 1)
    throw new TypeError(`Unsupported save version: ${String(state.version)}`);
  if (typeof state.tamerName !== 'string') throw new TypeError('Save missing tamerName');
  if (typeof state.rngState !== 'number') throw new TypeError('Save missing rngState');
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
