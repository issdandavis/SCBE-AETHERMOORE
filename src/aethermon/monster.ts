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
import {
  DAY_TICKS,
  GLITCH_STAT_PENALTY,
  IDEAL_WEIGHT,
  MAX_LEVEL,
  MAX_TRAIN_BONUS,
  MIN_WEIGHT,
  NIGHT_START,
  RESIDUE_CAP,
  RESIDUE_INTERVAL,
  SCAR_DEFENSE_BONUS,
  SCAR_DEFENSE_CAP,
  STAGE_LIFESPAN_TICKS,
  STAT_KEYS,
  TRAIN_POINTS_PER_SESSION,
  WEIGHT_PER_FEED,
  WEIGHT_STAT_PENALTY,
  WEIGHT_TOLERANCE,
  WEIGHT_TRAIN_BURN,
} from './types.js';
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

/** Options for creating a creature (rebirth eggs pass these). */
export interface CreateMonsterOptions {
  /** Generation number (1 = first of the line). */
  generation?: number;
  /** Stats inherited from the previous generation. */
  heirloom?: Stats;
}

/** Create a fresh creature of the given species at level 1. */
export function createMonster(
  speciesId: string,
  nickname: string,
  options: CreateMonsterOptions = {}
): MonsterState {
  const species = getSpecies(speciesId); // validate id
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
    stageAgeTicks: 0,
    scars: 0,
    consecutiveBattles: 0,
    hollowExposure: 0,
    generation: options.generation ?? 1,
    heirloom: options.heirloom ?? { hp: 0, atk: 0, def: 0, spd: 0 },
    lineage: [speciesId],
    weightKb: IDEAL_WEIGHT[species.stage],
    residue: 0,
    glitched: false,
  };
}

// ---------------------------------------------------------------------------
//  Stats
// ---------------------------------------------------------------------------

/**
 * Effective stats: base scaled by level growth, plus flat training and
 * heirloom bonuses. stat(L) = floor(base * (1 + growth * (L - 1))) +
 * trainBonus + heirloom. Scars harden defense (immune memory, capped) —
 * the line gets stronger from the attacks it survives. Weight far from
 * the stage ideal drags SPD (over) or ATK (under); a glitched creature
 * sags across the board until patched.
 */
export function effectiveStats(monster: MonsterState): Stats {
  const species = getSpecies(monster.speciesId);
  const scale = 1 + species.growth * (monster.level - 1);
  const stat = (key: StatKey): number =>
    Math.floor(species.baseStats[key] * scale) + monster.trainBonus[key] + monster.heirloom[key];
  const stats = { hp: stat('hp'), atk: stat('atk'), def: stat('def'), spd: stat('spd') };
  stats.def += Math.min(SCAR_DEFENSE_CAP, monster.scars * SCAR_DEFENSE_BONUS);
  // A4: Clamping — weight/glitch penalties floor every stat at 1.
  const band = weightBand(monster);
  if (band === 'OVER') stats.spd = Math.max(1, Math.floor(stats.spd * WEIGHT_STAT_PENALTY));
  if (band === 'UNDER') stats.atk = Math.max(1, Math.floor(stats.atk * WEIGHT_STAT_PENALTY));
  if (monster.glitched) {
    for (const key of STAT_KEYS) {
      stats[key] = Math.max(1, Math.floor(stats[key] * GLITCH_STAT_PENALTY));
    }
  }
  return stats;
}

// ---------------------------------------------------------------------------
//  Daily life: clock & weight
// ---------------------------------------------------------------------------

/** Hour of the in-game day (0..DAY_TICKS-1), derived from age. */
export function hourOf(monster: MonsterState): number {
  return monster.ageTicks % DAY_TICKS;
}

/** True during night hours — the creature wants its bed. */
export function isNight(monster: MonsterState): boolean {
  return hourOf(monster) >= NIGHT_START;
}

/** Where the creature sits relative to its stage's ideal weight band. */
export type WeightBand = 'UNDER' | 'IDEAL' | 'OVER';

/** Classify current weight against the stage ideal ± tolerance. */
export function weightBand(monster: MonsterState): WeightBand {
  const ideal = IDEAL_WEIGHT[getSpecies(monster.speciesId).stage];
  if (monster.weightKb > ideal * (1 + WEIGHT_TOLERANCE)) return 'OVER';
  if (monster.weightKb < ideal * (1 - WEIGHT_TOLERANCE)) return 'UNDER';
  return 'IDEAL';
}

// ---------------------------------------------------------------------------
//  Lifespan (V-Pet rule: every form has its season)
// ---------------------------------------------------------------------------

/** Care ticks remaining before this form's lifespan ends. */
export function lifespanRemaining(monster: MonsterState): number {
  const species = getSpecies(monster.speciesId);
  return Math.max(0, STAGE_LIFESPAN_TICKS[species.stage] - monster.stageAgeTicks);
}

/**
 * True when the creature has outlived its current form. Evolving renews
 * the lifespan (power buys time); otherwise it returns to an egg and
 * the next generation inherits part of its strength.
 */
export function isLifespanExpired(monster: MonsterState): boolean {
  return lifespanRemaining(monster) <= 0;
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
 * Waking ticks also shed static residue on a fixed rhythm (an overflowing
 * pen glitches the creature), press on the mood of a glitched creature,
 * and charge a care mistake for staying awake past midnight.
 */
export function tick(monster: MonsterState): void {
  const care = monster.care;
  const wasNight = isNight(monster);
  monster.ageTicks += 1;
  monster.stageAgeTicks += 1;
  care.hunger = clamp100(care.hunger - HUNGER_DECAY);
  care.energy = clamp100(care.energy - ENERGY_DECAY);
  if (monster.glitched) care.mood = clamp100(care.mood - 2);

  // Static sheds on a fixed rhythm; shedding onto a full floor corrupts
  // the creature. Neglecting the pen is the mistake, not the shedding.
  if (monster.ageTicks % RESIDUE_INTERVAL === 0) {
    if (monster.residue >= RESIDUE_CAP) {
      if (!monster.glitched) {
        monster.glitched = true;
        care.careMistakes += 1;
        care.mood = clamp100(care.mood - 10);
      }
    } else {
      monster.residue += 1;
    }
  }

  // All-nighter: awake past midnight (V-Pet lights-out rule).
  if (wasNight && hourOf(monster) === 0) {
    care.careMistakes += 1;
    care.mood = clamp100(care.mood - 10);
    care.energy = clamp100(care.energy - 20);
  }

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

/** Feed: +40 hunger, +5 mood, +weight. Overfeeding annoys it instead (no tick). */
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
  monster.weightKb += WEIGHT_PER_FEED;
  return { ok: true, message: `${monster.nickname} devours the data-ration. Hunger restored.` };
}

/** Rest: +50 energy. Also resets battle strain. */
export function rest(monster: MonsterState): CareResult {
  tick(monster);
  monster.care.energy = clamp100(monster.care.energy + 50);
  monster.care.exhausted = false;
  monster.consecutiveBattles = 0;
  return { ok: true, message: `${monster.nickname} curls up and recharges.` };
}

/** Play: +15 mood, +5 bond, costs energy and a little hunger. */
export function play(monster: MonsterState): CareResult {
  const care = monster.care;
  if (monster.glitched) {
    return { ok: false, message: `${monster.nickname} flickers weakly — it needs a patch first.` };
  }
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
 * energy, hunger and weight, builds a little bond and discipline.
 */
export function train(monster: MonsterState, stat: StatKey): CareResult {
  const care = monster.care;
  if (monster.glitched) {
    return { ok: false, message: `${monster.nickname} is too glitchy to train — patch it first.` };
  }
  if (care.energy < 15) {
    return { ok: false, message: `${monster.nickname} is too exhausted to train.` };
  }
  tick(monster);
  care.energy = clamp100(care.energy - 15);
  care.hunger = clamp100(care.hunger - 10);
  care.bond = clamp100(care.bond + 2);
  care.discipline = clamp100(care.discipline + 1);
  // A4: Clamping — weight never drops below MIN_WEIGHT.
  monster.weightKb = Math.max(MIN_WEIGHT, monster.weightKb - WEIGHT_TRAIN_BURN);
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
//  Daily life actions
// ---------------------------------------------------------------------------

/** Sweep the pen: clears all static residue. */
export function cleanUp(monster: MonsterState): CareResult {
  if (monster.residue === 0) {
    return { ok: false, message: `The pen is already spotless.` };
  }
  tick(monster);
  monster.residue = 0;
  monster.care.mood = clamp100(monster.care.mood + 3);
  return {
    ok: true,
    message: `You sweep the static residue clear. ${monster.nickname} chirps approval.`,
  };
}

/**
 * Apply a patch: cures a glitched creature. The patch fixes the creature,
 * not the pen — over a full static floor the cure warns that corruption
 * will return unless the residue is swept.
 */
export function patch(monster: MonsterState): CareResult {
  if (!monster.glitched) {
    return { ok: false, message: `${monster.nickname} is running clean — no patch needed.` };
  }
  tick(monster);
  monster.glitched = false;
  monster.care.mood = clamp100(monster.care.mood + 5);
  if (monster.residue >= RESIDUE_CAP) {
    return {
      ok: true,
      message:
        `You apply a patch. ${monster.nickname} steadies — but the floor is still ` +
        `buried in static. Sweep it, or the corruption will return.`,
    };
  }
  return {
    ok: true,
    message: `You apply a patch. ${monster.nickname}'s static clears; it hums steadily again.`,
  };
}

/**
 * Tuck in for the night (only during night hours): time skips to dawn.
 * Sleep is gentle — hunger burns at half rate and no residue sheds —
 * and it fully restores energy and battle strain. Tucking in promptly
 * (within the first two night hours) builds bond: it loves its routine.
 * Sleeping through an empty stomach still counts as starving on wake.
 */
export function tuckIn(monster: MonsterState): CareResult {
  const hour = hourOf(monster);
  const care = monster.care;
  if (hour < NIGHT_START) {
    return {
      ok: false,
      message: `${monster.nickname} isn't sleepy yet — night falls at hour ${NIGHT_START}.`,
    };
  }
  const promptly = hour <= NIGHT_START + 1;
  const skip = DAY_TICKS - hour;
  monster.ageTicks += skip;
  monster.stageAgeTicks += skip;
  care.hunger = clamp100(care.hunger - Math.floor((HUNGER_DECAY * skip) / 2));
  care.energy = 100;
  care.exhausted = false;
  monster.consecutiveBattles = 0;
  care.mood = clamp100(care.mood + 5);
  if (promptly) care.bond = clamp100(care.bond + 3);
  if (care.hunger <= 0 && !care.starving) {
    care.starving = true;
    care.careMistakes += 1;
    care.mood = clamp100(care.mood - 10);
  }
  return {
    ok: true,
    message:
      `${monster.nickname} curls up and sleeps until dawn.` +
      (promptly ? ' It loves its routine.' : ''),
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
