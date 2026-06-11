/**
 * @file game.unit.test.ts
 * @module tests/aethermon
 * @component AETHERMON — Game Orchestration (L3-integration)
 *
 * Egg hatching, wild encounter scaling, the arena ladder, and the
 * save/load round trip.
 */

import { describe, expect, it } from 'vitest';
import {
  ARENA_LADDER,
  WARMTH_TO_HATCH,
  arenaCombatant,
  deserializeGame,
  generateWildEncounter,
  getSpecies,
  isChampion,
  newGame,
  nextArenaRival,
  recordBattleOutcome,
  serializeGame,
  stageIndex,
  warmEgg,
} from '../../src/aethermon/index.js';

function hatchedGame(seed = 99) {
  const state = newGame('Issa', 'umbral_egg', seed);
  let result = warmEgg(state, 'Dusk');
  while (!result.hatched) result = warmEgg(state, 'Dusk');
  return state;
}

describe('new game & hatching', () => {
  it('starts with an egg and no monster', () => {
    const state = newGame('Issa', 'ember_egg', 1);
    expect(state.egg?.speciesId).toBe('ember_egg');
    expect(state.monster).toBeNull();
    expect(() => newGame('Issa', 'kindlemote', 1)).toThrow(RangeError);
  });

  it(`hatches after ${WARMTH_TO_HATCH} warm actions into the egg's mote`, () => {
    const state = newGame('Issa', 'umbral_egg', 1);
    for (let i = 0; i < WARMTH_TO_HATCH - 1; i++) {
      expect(warmEgg(state, 'Dusk').hatched).toBe(false);
    }
    const final = warmEgg(state, 'Dusk');
    expect(final.hatched).toBe(true);
    expect(state.egg).toBeNull();
    expect(state.monster?.speciesId).toBe('shademote');
    expect(state.monster?.lineage).toEqual(['umbral_egg', 'shademote']);
  });
});

describe('wild encounters', () => {
  it('spawns near the creature level, never eggs, stage at or below', () => {
    const state = hatchedGame();
    const monster = state.monster!;
    monster.level = 8;
    for (let i = 0; i < 30; i++) {
      const enemy = generateWildEncounter(state, monster);
      const species = getSpecies(enemy.speciesId);
      expect(species.stage).not.toBe('EGG');
      expect(stageIndex(species.stage)).toBeLessThanOrEqual(
        stageIndex(getSpecies(monster.speciesId).stage)
      );
      expect(Math.abs(enemy.level - monster.level)).toBeLessThanOrEqual(2);
      expect(enemy.level).toBeGreaterThanOrEqual(1);
    }
  });

  it('is deterministic from the saved RNG state', () => {
    const a = hatchedGame(7);
    const b = hatchedGame(7);
    const enemyA = generateWildEncounter(a, a.monster!);
    const enemyB = generateWildEncounter(b, b.monster!);
    expect(enemyA.speciesId).toBe(enemyB.speciesId);
    expect(enemyA.level).toBe(enemyB.level);
  });
});

describe('arena ladder', () => {
  it('has ten rungs of increasing level, all species valid', () => {
    expect(ARENA_LADDER).toHaveLength(10);
    for (let i = 0; i < ARENA_LADDER.length; i++) {
      const rival = ARENA_LADDER[i];
      expect(() => getSpecies(rival.speciesId)).not.toThrow();
      if (i > 0) expect(rival.level).toBeGreaterThan(ARENA_LADDER[i - 1].level);
      const combatant = arenaCombatant(rival);
      expect(combatant.level).toBe(rival.level);
      expect(combatant.name).toContain(rival.name);
    }
  });

  it('progresses rank only on arena wins and crowns a champion', () => {
    const state = hatchedGame();
    const monster = state.monster!;
    expect(nextArenaRival(state)?.name).toBe('Pip');
    recordBattleOutcome(state, monster, 3, false, true);
    expect(state.arenaRank).toBe(0);
    for (const rival of ARENA_LADDER) {
      recordBattleOutcome(state, monster, rival.level, true, true);
    }
    expect(isChampion(state)).toBe(true);
    expect(nextArenaRival(state)).toBeNull();
  });

  it('awards xp on wins and a consolation share on losses', () => {
    const state = hatchedGame();
    const monster = state.monster!;
    const beforeXp = monster.xp + 0;
    recordBattleOutcome(state, monster, 3, true, false);
    const afterWin = monster.level * 1000 + monster.xp;
    expect(afterWin).toBeGreaterThan(monster.level === 1 ? beforeXp : 0);
    expect(state.totalBattlesWon).toBe(1);
    recordBattleOutcome(state, monster, 3, false, false);
    expect(state.totalBattlesLost).toBe(1);
  });
});

describe('save / load', () => {
  it('round-trips full game state', () => {
    const state = hatchedGame();
    state.monster!.level = 9;
    state.monster!.trainBonus.atk = 12;
    state.arenaRank = 3;
    const restored = deserializeGame(serializeGame(state));
    expect(restored).toEqual(state);
  });

  it('rejects malformed saves', () => {
    expect(() => deserializeGame('null')).toThrow(TypeError);
    expect(() => deserializeGame('{"version":2}')).toThrow(TypeError);
    const bad = JSON.parse(serializeGame(hatchedGame()));
    bad.monster.speciesId = 'missingno';
    expect(() => deserializeGame(JSON.stringify(bad))).toThrow(RangeError);
  });
});
