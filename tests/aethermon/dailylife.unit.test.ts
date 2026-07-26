/**
 * @file dailylife.unit.test.ts
 * @module tests/aethermon
 * @layer Layer 3, Layer 13
 * @component AETHERMON — Daily Life (sleep, weight, cleanup, sickness)
 *
 * V-Pet daily-life rules: the 24-tick day with a lights-out window,
 * weight economy (meals add, training burns, bands penalize), static
 * residue that must be swept, and the GLITCHED sickness that sags stats
 * until patched. All deterministic — no RNG anywhere in these systems.
 */

import { describe, expect, it } from 'vitest';
import {
  DAY_TICKS,
  GLITCH_STAT_PENALTY,
  IDEAL_WEIGHT,
  MIN_WEIGHT,
  NIGHT_START,
  RESIDUE_CAP,
  RESIDUE_INTERVAL,
  WEIGHT_PER_FEED,
  WEIGHT_TRAIN_BURN,
} from '../../src/aethermon/types.js';
import {
  cleanUp,
  createMonster,
  effectiveStats,
  feed,
  hourOf,
  isNight,
  patch,
  play,
  tick,
  train,
  tuckIn,
  weightBand,
} from '../../src/aethermon/monster.js';
import { applyBattleResult } from '../../src/aethermon/battle.js';
import { evolve } from '../../src/aethermon/evolution.js';
import { deserializeGame, newGame, serializeGame, warmEgg } from '../../src/aethermon/game.js';

function fresh() {
  return createMonster('kindlemote', 'Testling');
}

/** Advance to a given hour of the current day without care side effects. */
function setHour(monster: ReturnType<typeof fresh>, hour: number): void {
  monster.ageTicks = hour;
  monster.stageAgeTicks = hour;
}

describe('the in-game clock', () => {
  it('derives the hour from age and wraps daily', () => {
    const monster = fresh();
    expect(hourOf(monster)).toBe(0);
    setHour(monster, DAY_TICKS - 1);
    expect(hourOf(monster)).toBe(DAY_TICKS - 1);
    monster.ageTicks += 1;
    expect(hourOf(monster)).toBe(0);
  });

  it('night spans NIGHT_START to end of day', () => {
    const monster = fresh();
    setHour(monster, NIGHT_START - 1);
    expect(isNight(monster)).toBe(false);
    setHour(monster, NIGHT_START);
    expect(isNight(monster)).toBe(true);
    setHour(monster, DAY_TICKS - 1);
    expect(isNight(monster)).toBe(true);
  });

  it('staying awake past midnight costs a care mistake', () => {
    const monster = fresh();
    setHour(monster, DAY_TICKS - 1);
    const before = monster.care.careMistakes;
    tick(monster); // wraps to hour 0 while awake
    expect(monster.care.careMistakes).toBe(before + 1);
  });

  it('daytime ticks charge no all-nighter mistakes', () => {
    const monster = fresh();
    monster.care.hunger = 100;
    monster.care.energy = 100;
    setHour(monster, 5);
    tick(monster);
    expect(monster.care.careMistakes).toBe(0);
  });
});

describe('tucking in', () => {
  it('is refused during the day', () => {
    const monster = fresh();
    setHour(monster, 10);
    const result = tuckIn(monster);
    expect(result.ok).toBe(false);
    expect(hourOf(monster)).toBe(10); // no time passed
  });

  it('sleeps to dawn: full energy, strain reset, no midnight mistake', () => {
    const monster = fresh();
    setHour(monster, NIGHT_START);
    monster.care.energy = 12;
    monster.consecutiveBattles = 3;
    const mistakes = monster.care.careMistakes;
    const result = tuckIn(monster);
    expect(result.ok).toBe(true);
    expect(hourOf(monster)).toBe(0);
    expect(monster.care.energy).toBe(100);
    expect(monster.consecutiveBattles).toBe(0);
    expect(monster.care.careMistakes).toBe(mistakes); // sleeping ≠ all-nighter
  });

  it('rewards a prompt bedtime with bond', () => {
    const early = fresh();
    setHour(early, NIGHT_START);
    const earlyBond = early.care.bond;
    tuckIn(early);
    expect(early.care.bond).toBe(earlyBond + 3);

    const late = fresh();
    setHour(late, DAY_TICKS - 1);
    const lateBond = late.care.bond;
    tuckIn(late);
    expect(late.care.bond).toBe(lateBond);
  });

  it('burns hunger at half rate while asleep', () => {
    const monster = fresh();
    setHour(monster, NIGHT_START);
    monster.care.hunger = 100;
    tuckIn(monster); // skips DAY_TICKS - NIGHT_START ticks
    const skip = DAY_TICKS - NIGHT_START;
    expect(monster.care.hunger).toBe(100 - Math.floor((6 * skip) / 2));
  });

  it('still counts starving if it sleeps through an empty stomach', () => {
    const monster = fresh();
    setHour(monster, NIGHT_START);
    monster.care.hunger = 2;
    const mistakes = monster.care.careMistakes;
    tuckIn(monster);
    expect(monster.care.hunger).toBe(0);
    expect(monster.care.careMistakes).toBe(mistakes + 1);
  });
});

describe('weight economy', () => {
  it('hatches at the stage ideal', () => {
    const monster = fresh();
    expect(monster.weightKb).toBe(IDEAL_WEIGHT.MOTE);
    expect(weightBand(monster)).toBe('IDEAL');
  });

  it('meals add weight, training burns it', () => {
    const monster = fresh();
    const start = monster.weightKb;
    monster.care.hunger = 40;
    feed(monster);
    expect(monster.weightKb).toBe(start + WEIGHT_PER_FEED);
    train(monster, 'atk');
    expect(monster.weightKb).toBe(start + WEIGHT_PER_FEED - WEIGHT_TRAIN_BURN);
  });

  it('battles burn a little weight and never go below the floor', () => {
    const monster = fresh();
    monster.weightKb = MIN_WEIGHT;
    applyBattleResult(monster, true);
    expect(monster.weightKb).toBe(MIN_WEIGHT);
  });

  it('overweight drags speed; underweight drags attack', () => {
    const monster = fresh();
    const ideal = effectiveStats(monster);

    monster.weightKb = IDEAL_WEIGHT.MOTE * 2;
    expect(weightBand(monster)).toBe('OVER');
    const heavy = effectiveStats(monster);
    expect(heavy.spd).toBeLessThan(ideal.spd);
    expect(heavy.atk).toBe(ideal.atk);

    monster.weightKb = MIN_WEIGHT;
    expect(weightBand(monster)).toBe('UNDER');
    const thin = effectiveStats(monster);
    expect(thin.atk).toBeLessThan(ideal.atk);
    expect(thin.spd).toBe(ideal.spd);
  });

  it('evolution reformats the body to the new stage ideal', () => {
    const monster = fresh();
    monster.level = 10;
    monster.weightKb = 40;
    const result = evolve(monster);
    expect(result).not.toBeNull();
    expect(monster.weightKb).toBe(IDEAL_WEIGHT.SPRITE);
  });
});

describe('static residue & cleaning', () => {
  it('sheds on a fixed rhythm up to the cap', () => {
    const monster = fresh();
    monster.care.hunger = 100;
    monster.care.energy = 100;
    for (let i = 0; i < RESIDUE_INTERVAL; i++) tick(monster);
    expect(monster.residue).toBe(1);
    for (let i = 0; i < RESIDUE_INTERVAL * RESIDUE_CAP; i++) tick(monster);
    expect(monster.residue).toBe(RESIDUE_CAP);
  });

  it('shedding onto a full floor glitches the creature once', () => {
    const monster = fresh();
    monster.residue = RESIDUE_CAP;
    monster.ageTicks = RESIDUE_INTERVAL - 1; // next tick lands on the rhythm
    const mistakes = monster.care.careMistakes;
    tick(monster);
    expect(monster.glitched).toBe(true);
    expect(monster.care.careMistakes).toBe(mistakes + 1);
    // Already glitched: no second mistake on the next overflow.
    monster.ageTicks = RESIDUE_INTERVAL * 2 - 1;
    tick(monster);
    expect(monster.care.careMistakes).toBe(mistakes + 1);
  });

  it('cleaning sweeps the floor; a clean pen refuses the action', () => {
    const monster = fresh();
    expect(cleanUp(monster).ok).toBe(false);
    monster.residue = 2;
    const result = cleanUp(monster);
    expect(result.ok).toBe(true);
    expect(monster.residue).toBe(0);
  });
});

describe('the GLITCHED sickness', () => {
  it('sags every stat until patched', () => {
    const monster = fresh();
    const healthy = effectiveStats(monster);
    monster.glitched = true;
    const sick = effectiveStats(monster);
    for (const key of ['hp', 'atk', 'def', 'spd'] as const) {
      expect(sick[key]).toBe(Math.max(1, Math.floor(healthy[key] * GLITCH_STAT_PENALTY)));
    }
    patch(monster);
    expect(monster.glitched).toBe(false);
    expect(effectiveStats(monster)).toEqual(healthy);
  });

  it('refuses training and play while glitched', () => {
    const monster = fresh();
    monster.glitched = true;
    expect(train(monster, 'atk').ok).toBe(false);
    expect(play(monster).ok).toBe(false);
  });

  it('patching a healthy creature is a no-op', () => {
    const monster = fresh();
    expect(patch(monster).ok).toBe(false);
  });

  it('patching over a full static floor warns that the cure will not hold', () => {
    const monster = fresh();
    monster.glitched = true;
    monster.residue = RESIDUE_CAP;
    const result = patch(monster);
    expect(result.ok).toBe(true);
    expect(monster.glitched).toBe(false);
    expect(result.message).toMatch(/sweep/i);
  });

  it('over-battling without rest corrupts the creature', () => {
    const monster = fresh();
    let glitchedByStrain = false;
    for (let i = 0; i < 4; i++) {
      glitchedByStrain = applyBattleResult(monster, true).glitchedByStrain || glitchedByStrain;
    }
    expect(monster.glitched).toBe(true);
    expect(glitchedByStrain).toBe(true);
  });
});

describe('save v3', () => {
  it('new games start at version 3 with daily-life fields', () => {
    const state = newGame('Tamer', 'ember_egg', 7);
    while (state.egg) warmEgg(state, 'Kid');
    expect(state.version).toBe(3);
    expect(state.monster?.weightKb).toBe(IDEAL_WEIGHT.MOTE);
    expect(state.monster?.residue).toBe(0);
    expect(state.monster?.glitched).toBe(false);
  });

  it('migrates version-2 saves with sane daily-life defaults', () => {
    const state = newGame('Tamer', 'ember_egg', 7);
    while (state.egg) warmEgg(state, 'Kid');
    const v2 = JSON.parse(serializeGame(state)) as Record<string, unknown>;
    v2.version = 2;
    const monster = v2.monster as Record<string, unknown>;
    delete monster.weightKb;
    delete monster.residue;
    delete monster.glitched;

    const migrated = deserializeGame(JSON.stringify(v2));
    expect(migrated.version).toBe(3);
    expect(migrated.monster?.weightKb).toBe(IDEAL_WEIGHT.MOTE);
    expect(migrated.monster?.residue).toBe(0);
    expect(migrated.monster?.glitched).toBe(false);
  });

  it('round-trips daily-life state exactly', () => {
    const state = newGame('Tamer', 'gale_egg', 11);
    while (state.egg) warmEgg(state, 'Gust');
    const monster = state.monster!;
    monster.residue = 2;
    monster.weightKb = 17;
    monster.glitched = true;
    const restored = deserializeGame(serializeGame(state));
    expect(restored).toEqual(state);
  });
});
