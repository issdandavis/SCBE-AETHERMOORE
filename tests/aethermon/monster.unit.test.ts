/**
 * @file monster.unit.test.ts
 * @module tests/aethermon
 * @component AETHERMON — Creature Lifecycle (L2-unit)
 *
 * Care meters, training economy, starvation episodes, and the XP curve.
 */

import { describe, expect, it } from 'vitest';
import {
  HUNGER_DECAY,
  MAX_LEVEL,
  MAX_TRAIN_BONUS,
  createMonster,
  dominantTrainedStat,
  effectiveStats,
  feed,
  gainXp,
  play,
  praise,
  rest,
  scold,
  tick,
  train,
  xpToNext,
} from '../../src/aethermon/index.js';

describe('creature creation', () => {
  it('creates a level-1 creature with healthy meters', () => {
    const monster = createMonster('kindlemote', 'Cinder');
    expect(monster.level).toBe(1);
    expect(monster.care.hunger).toBe(80);
    expect(monster.care.careMistakes).toBe(0);
    expect(monster.lineage).toEqual(['kindlemote']);
  });

  it('rejects unknown species', () => {
    expect(() => createMonster('agumon', 'Nope')).toThrow(RangeError);
  });
});

describe('care meters', () => {
  it('feeding restores hunger and clamps at 100', () => {
    const monster = createMonster('kindlemote', 'Cinder');
    monster.care.hunger = 30;
    const result = feed(monster);
    expect(result.ok).toBe(true);
    // tick decays first, then +40
    expect(monster.care.hunger).toBe(30 - HUNGER_DECAY + 40);
    monster.care.hunger = 99;
    expect(feed(monster).ok).toBe(false); // stuffed
  });

  it('starvation counts one care mistake per episode', () => {
    const monster = createMonster('kindlemote', 'Cinder');
    monster.care.hunger = 5;
    tick(monster); // crosses to 0 → mistake
    expect(monster.care.careMistakes).toBe(1);
    tick(monster); // still starving, same episode
    tick(monster);
    expect(monster.care.careMistakes).toBe(1);
    feed(monster); // episode ends
    monster.care.hunger = 5;
    tick(monster); // new episode
    expect(monster.care.careMistakes).toBe(2);
  });

  it('exhaustion also costs a care mistake', () => {
    const monster = createMonster('kindlemote', 'Cinder');
    monster.care.energy = 3;
    tick(monster);
    expect(monster.care.careMistakes).toBe(1);
    rest(monster);
    expect(monster.care.exhausted).toBe(false);
  });

  it('play, praise and scold move mood, bond and discipline as designed', () => {
    const monster = createMonster('kindlemote', 'Cinder');
    const mood = monster.care.mood;
    const bond = monster.care.bond;
    play(monster);
    expect(monster.care.mood).toBe(Math.min(100, mood + 15));
    expect(monster.care.bond).toBe(bond + 5);
    const discipline = monster.care.discipline;
    scold(monster);
    expect(monster.care.discipline).toBe(discipline + 10);
    praise(monster);
    expect(monster.care.discipline).toBe(discipline + 10 - 3);
  });
});

describe('training', () => {
  it('adds permanent stat points and tracks counts', () => {
    const monster = createMonster('kindlemote', 'Cinder');
    const result = train(monster, 'atk');
    expect(result.ok).toBe(true);
    expect(monster.trainBonus.atk).toBe(3);
    expect(monster.trainCounts.atk).toBe(1);
  });

  it('refuses training when too tired and caps at MAX_TRAIN_BONUS', () => {
    const monster = createMonster('kindlemote', 'Cinder');
    monster.care.energy = 5;
    expect(train(monster, 'atk').ok).toBe(false);
    monster.care.energy = 100;
    monster.trainBonus.atk = MAX_TRAIN_BONUS;
    expect(train(monster, 'atk').ok).toBe(false);
    expect(monster.trainBonus.atk).toBe(MAX_TRAIN_BONUS);
  });

  it('detects dominant training profiles', () => {
    const monster = createMonster('kindlemote', 'Cinder');
    expect(dominantTrainedStat(monster)).toBe('balanced');
    monster.trainBonus.atk = 12;
    monster.trainBonus.def = 3;
    monster.trainBonus.spd = 3;
    expect(dominantTrainedStat(monster)).toBe('atk');
    monster.trainBonus.def = 12;
    monster.trainBonus.spd = 12;
    expect(dominantTrainedStat(monster)).toBe('balanced');
  });
});

describe('stats and leveling', () => {
  it('effective stats grow with level and training', () => {
    const monster = createMonster('kindlemote', 'Cinder');
    const atLevel1 = effectiveStats(monster);
    monster.level = 10;
    const atLevel10 = effectiveStats(monster);
    expect(atLevel10.hp).toBeGreaterThan(atLevel1.hp);
    expect(atLevel10.atk).toBeGreaterThan(atLevel1.atk);
    monster.trainBonus.atk = 10;
    expect(effectiveStats(monster).atk).toBeGreaterThan(atLevel10.atk);
  });

  it('xp curve is increasing and gainXp applies multi-level-ups', () => {
    expect(xpToNext(2)).toBeGreaterThan(xpToNext(1));
    const monster = createMonster('kindlemote', 'Cinder');
    const gained = gainXp(monster, xpToNext(1) + xpToNext(2));
    expect(gained).toBe(2);
    expect(monster.level).toBe(3);
  });

  it('never exceeds MAX_LEVEL', () => {
    const monster = createMonster('kindlemote', 'Cinder');
    gainXp(monster, 10_000_000);
    expect(monster.level).toBe(MAX_LEVEL);
    expect(monster.xp).toBe(0);
    expect(() => gainXp(monster, -1)).toThrow(RangeError);
  });
});
