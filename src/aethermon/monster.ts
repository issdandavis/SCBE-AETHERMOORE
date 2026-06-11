/**
 * @file monster.ts
 * @module aethermon/monster
 * @layer Layer 3, Layer 12
 * @component AETHERMON — Creature Lifecycle (care, training, leveling)
 *
 * The virtual-pet core. Every player action advances one care tick;
 * hunger and energy decay each tick, and letting either hit zero costs a
 * care mistake — which permanently shapes the evolution tree (see
 * evolution.ts).
 *
 * A4: All meters are clamped to [0, 100]; stats are clamped to caps.
 */

import type { CareState, MonsterState, StatKey, Stats } from './types.js';
import { MAX_LEVEL, MAX_TRAIN_BONUS, STAT_KEYS, TRAIN_POINTS_PER_SESSION } from './types.js';
import { getSpecies } from './species.js';

// ---------------------------------------------------------------------------
//  Tick economy
// ---------------------------------------------------------------------------

/** Hunger lost per care tick. */
export const HUNGER_DECAY = 6;
/** Energy lost per care tick. */
export const ENERGY_DECAY = 4;

/** Clamp helper for care meters. */
function clamp100(x: number): number {
  return Math.max(0, Math.min(100, x));
}

// ---------------------------------------------------------------------------
//  Creation
// ---------------------------------------------------------------------------

let nextMonsterSerial = 1;

/** Create a fresh creature of the given species at level 1. */
export function createMonster(speciesId: string, nickname: string): MonsterState {
  getSpecies(speciesId); // validate id
  return {
    id: `mon_${Date.now().toString(36)}_${nextMonsterSerial++}`,
    nickname,
    speciesId,
    level: 1,
    xp: 0,
    trainBonus: { hp: 0, atk: 0, def: 0, spd: 0 },
    trainCounts: { hp: 0, atk: 0, def: 0, spd: 0 },
    care: {
      hunger: 80,
      energy: 80,
      mood: 70,
      bond: 10,
      discipline: 10,
      careMistakes: 0,
      starving: false,
      exhausted: false,
    },
    battlesWon: 0,
    battlesLost: 0,
    ageTicks: 0,
    lineage: [speciesId],
  };
}

// ---------------------------------------------------------------------------
//  Stats
// ---------------------------------------------------------------------------

/**
 * Effective stats: base scaled by level growth, plus the flat training
 * bonus. stat(L) = floor(base * (1 + growth * (L - 1))) + bonus
 * (Flat bonus keeps training meaningful without compounding with level.)
 */
export function effectiveStats(monster: MonsterState): Stats {
  const species = getSpecies(monster.speciesId);
  const scale = 1 + species.growth * (monster.level - 1);
  const stat = (key: StatKey): number =>
    Math.floor(species.baseStats[key] * scale) + monster.trainBonus[key];
  return { hp: stat('hp'), atk: stat('atk'), def: stat('def'), spd: stat('spd') };
}

// ---------------------------------------------------------------------------
//  XP / leveling
// ---------------------------------------------------------------------------

/** XP required to advance from `level` to `level + 1`. */
export function xpToNext(level: number): number {
  return Math.floor(30 * Math.pow(level, 1.5));
}

/** XP awarded for defeating an enemy of the given level. */
export function xpReward(enemyLevel: number): number {
  return 20 + enemyLevel * 12;
}

/**
 * Grant XP, applying level-ups (possibly several). Returns levels gained.
 */
export function gainXp(monster: MonsterState, amount: number): number {
  if (amount < 0) throw new RangeError('XP amount must be non-negative');
  let gained = 0;
  monster.xp += amount;
  while (monster.level < MAX_LEVEL && monster.xp >= xpToNext(monster.level)) {
    monster.xp -= xpToNext(monster.level);
    monster.level += 1;
    gained += 1;
  }
  if (monster.level >= MAX_LEVEL) monster.xp = 0;
  return gained;
}

// ---------------------------------------------------------------------------
//  Care tick
// ---------------------------------------------------------------------------

/**
 * Advance one care tick: hunger/energy decay, and crossing zero on either
 * meter records a care mistake (once per episode — refeeding resets it).
 */
export function tick(monster: MonsterState): void {
  const care = monster.care;
  monster.ageTicks += 1;
  care.hunger = clamp100(care.hunger - HUNGER_DECAY);
  care.energy = clamp100(care.energy - ENERGY_DECAY);

  if (care.hunger <= 0 && !care.starving) {
    care.starving = true;
    care.careMistakes += 1;
    care.mood = clamp100(care.mood - 10);
  }
  if (care.energy <= 0 && !care.exhausted) {
    care.exhausted = true;
    care.careMistakes += 1;
    care.mood = clamp100(care.mood - 10);
  }
}

// ---------------------------------------------------------------------------
//  Care actions (each advances one tick)
// ---------------------------------------------------------------------------

/** Result text from a care action, for the UI. */
export interface CareResult {
  readonly ok: boolean;
  readonly message: string;
}

/** Feed: +40 hunger, +5 mood. Overfeeding annoys it instead (no tick). */
export function feed(monster: MonsterState): CareResult {
  const care = monster.care;
  if (care.hunger >= 95) {
    care.mood = clamp100(care.mood - 5);
    return { ok: false, message: `${monster.nickname} is stuffed and refuses the meal.` };
  }
  tick(monster);
  care.hunger = clamp100(care.hunger + 40);
  care.mood = clamp100(care.mood + 5);
  care.starving = false;
  return { ok: true, message: `${monster.nickname} devours the data-ration. Hunger restored.` };
}

/** Rest: +50 energy. */
export function rest(monster: MonsterState): CareResult {
  tick(monster);
  monster.care.energy = clamp100(monster.care.energy + 50);
  monster.care.exhausted = false;
  return { ok: true, message: `${monster.nickname} curls up and recharges.` };
}

/** Play: +15 mood, +5 bond, costs energy and a little hunger. */
export function play(monster: MonsterState): CareResult {
  const care = monster.care;
  if (care.energy < 10) {
    return { ok: false, message: `${monster.nickname} is too tired to play.` };
  }
  tick(monster);
  care.energy = clamp100(care.energy - 10);
  care.mood = clamp100(care.mood + 15);
  care.bond = clamp100(care.bond + 5);
  return { ok: true, message: `${monster.nickname} bounces happily around you.` };
}

/** Praise: +10 mood, +8 bond, -3 discipline (spoiling). */
export function praise(monster: MonsterState): CareResult {
  const care = monster.care;
  tick(monster);
  care.mood = clamp100(care.mood + 10);
  care.bond = clamp100(care.bond + 8);
  care.discipline = clamp100(care.discipline - 3);
  return { ok: true, message: `${monster.nickname} glows with pride.` };
}

/** Scold: +10 discipline, -8 mood, -2 bond. */
export function scold(monster: MonsterState): CareResult {
  const care = monster.care;
  tick(monster);
  care.discipline = clamp100(care.discipline + 10);
  care.mood = clamp100(care.mood - 8);
  care.bond = clamp100(care.bond - 2);
  return { ok: true, message: `${monster.nickname} straightens up, chastened.` };
}

/**
 * Train a stat: permanent +3 to its training bonus (capped), costs
 * energy and hunger, builds a little bond and discipline.
 */
export function train(monster: MonsterState, stat: StatKey): CareResult {
  const care = monster.care;
  if (care.energy < 15) {
    return { ok: false, message: `${monster.nickname} is too exhausted to train.` };
  }
  tick(monster);
  care.energy = clamp100(care.energy - 15);
  care.hunger = clamp100(care.hunger - 10);
  care.bond = clamp100(care.bond + 2);
  care.discipline = clamp100(care.discipline + 1);
  const before = monster.trainBonus[stat];
  monster.trainBonus[stat] = Math.min(MAX_TRAIN_BONUS, before + TRAIN_POINTS_PER_SESSION);
  monster.trainCounts[stat] += 1;
  const gained = monster.trainBonus[stat] - before;
  if (gained === 0) {
    return { ok: false, message: `${monster.nickname}'s ${stat.toUpperCase()} is maxed out.` };
  }
  return {
    ok: true,
    message: `${monster.nickname} drills hard. ${stat.toUpperCase()} +${gained}!`,
  };
}

// ---------------------------------------------------------------------------
//  Derived profile
// ---------------------------------------------------------------------------

/**
 * Which training bonus dominates: a stat dominates when its bonus is at
 * least 1.5× every other stat's bonus (and non-zero); otherwise balanced.
 * HP training never dominates — it counts toward balance only.
 */
export function dominantTrainedStat(monster: MonsterState): 'atk' | 'def' | 'spd' | 'balanced' {
  const combat: Array<'atk' | 'def' | 'spd'> = ['atk', 'def', 'spd'];
  for (const key of combat) {
    const value = monster.trainBonus[key];
    if (value === 0) continue;
    const others = combat.filter((k) => k !== key);
    if (others.every((k) => value >= 1.5 * Math.max(1, monster.trainBonus[k]))) {
      return key;
    }
  }
  return 'balanced';
}

/** Human-readable care summary for the UI. */
export function describeCare(care: CareState): string {
  const meter = (label: string, value: number): string => `${label} ${value}/100`;
  return [
    meter('Hunger', care.hunger),
    meter('Energy', care.energy),
    meter('Mood', care.mood),
    meter('Bond', care.bond),
    meter('Discipline', care.discipline),
    `Mistakes ${care.careMistakes}`,
  ].join(' | ');
}

/** Validate a stat key from user input. */
export function isStatKey(value: string): value is StatKey {
  return (STAT_KEYS as readonly string[]).includes(value);
}
