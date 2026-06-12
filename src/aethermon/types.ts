/**
 * @file types.ts
 * @module aethermon/types
 * @layer Layer 3, Layer 13
 * @component AETHERMON — Core Type Definitions
 *
 * AETHERMON is a creature-raising game (virtual-pet battler) set in the
 * Aethermoore realm. Tamers hatch digital creatures from eggs, care for
 * them, train their stats, and battle through the Spiral Arena. How a
 * creature is raised — care mistakes, training focus, bond, discipline —
 * determines which branch of its evolution tree it takes.
 *
 * Elements are the six Sacred Tongues. Alignments form a golden-ratio
 * advantage triangle (AEGIS > VENOM > FLUX > AEGIS).
 */

import type { TongueCode } from '../game/types.js';

export type { TongueCode } from '../game/types.js';
export { TONGUE_CODES, TONGUE_NAMES, PHI } from '../game/types.js';

// ---------------------------------------------------------------------------
//  Stages
// ---------------------------------------------------------------------------

/** Growth stages, from egg to apex. */
export type Stage = 'EGG' | 'MOTE' | 'SPRITE' | 'GUARDIAN' | 'PARAGON' | 'APEX';

/** Stage order for progression checks. */
export const STAGE_ORDER: readonly Stage[] = [
  'EGG',
  'MOTE',
  'SPRITE',
  'GUARDIAN',
  'PARAGON',
  'APEX',
] as const;

/** Index of a stage in the canonical order. */
export function stageIndex(stage: Stage): number {
  return STAGE_ORDER.indexOf(stage);
}

/** Earliest level at which each stage can be reached. */
export const STAGE_MIN_LEVEL: Record<Stage, number> = {
  EGG: 1,
  MOTE: 1,
  SPRITE: 5,
  GUARDIAN: 12,
  PARAGON: 22,
  APEX: 35,
};

// ---------------------------------------------------------------------------
//  Alignment triangle
// ---------------------------------------------------------------------------

/**
 * Battle alignments. Advantage cycle (each beats the next):
 * AEGIS > VENOM > FLUX > AEGIS.
 */
export type Alignment = 'AEGIS' | 'VENOM' | 'FLUX';

/** Golden ratio φ — advantage multiplier. */
export const ALIGNMENT_ADVANTAGE = (1 + Math.sqrt(5)) / 2; // ≈ 1.618

/** 1/φ — disadvantage multiplier. */
export const ALIGNMENT_DISADVANTAGE = 2 / (1 + Math.sqrt(5)); // ≈ 0.618

/** Map of which alignment each alignment defeats. */
export const ALIGNMENT_BEATS: Record<Alignment, Alignment> = {
  AEGIS: 'VENOM',
  VENOM: 'FLUX',
  FLUX: 'AEGIS',
};

/**
 * Alignment damage multiplier for attacker vs defender.
 * φ when strong, 1/φ when weak, 1 otherwise.
 */
export function alignmentMultiplier(attacker: Alignment, defender: Alignment): number {
  if (ALIGNMENT_BEATS[attacker] === defender) return ALIGNMENT_ADVANTAGE;
  if (ALIGNMENT_BEATS[defender] === attacker) return ALIGNMENT_DISADVANTAGE;
  return 1.0;
}

// ---------------------------------------------------------------------------
//  Element wheel (Sacred Tongues)
// ---------------------------------------------------------------------------

/** Element wheel order — each element is strong against the next. */
export const ELEMENT_WHEEL: readonly TongueCode[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;

/** Multiplier when a move's element is strong against the defender's. */
export const ELEMENT_ADVANTAGE = 1.25;

/** Multiplier when a move's element is weak against the defender's. */
export const ELEMENT_DISADVANTAGE = 0.8;

/** Same-element attack bonus (move element matches attacker element). */
export const STAB_BONUS = 1.2;

/** Element damage multiplier for a move element vs defender element. */
export function elementMultiplier(moveElement: TongueCode, defenderElement: TongueCode): number {
  const i = ELEMENT_WHEEL.indexOf(moveElement);
  const j = ELEMENT_WHEEL.indexOf(defenderElement);
  if ((i + 1) % 6 === j) return ELEMENT_ADVANTAGE;
  if ((j + 1) % 6 === i) return ELEMENT_DISADVANTAGE;
  return 1.0;
}

// ---------------------------------------------------------------------------
//  Hodge dual pairs (canon: Cl(4,0) — e_ij ∧ e_kl = e_1234)
// ---------------------------------------------------------------------------

/**
 * Hodge dual partner of each tongue. Canon: "Hodge duals bond 30%
 * stronger" — KO↔DR (Command↔Structure), AV↔UM (Transport↔Security),
 * RU↔CA (Entropy↔Compute).
 */
export const HODGE_DUALS: Record<TongueCode, TongueCode> = {
  KO: 'DR',
  DR: 'KO',
  AV: 'UM',
  UM: 'AV',
  RU: 'CA',
  CA: 'RU',
};

/**
 * Damage multiplier when a creature uses a move of its Hodge dual
 * element — the dual carries it almost as well as its own voice.
 */
export const HODGE_RESONANCE = 1.3;

/** Canon synesthesia: the musical note each tongue sounds as. */
export const TONGUE_NOTES: Record<TongueCode, string> = {
  KO: 'A',
  AV: 'B',
  RU: 'C#',
  CA: 'D#',
  UM: 'F',
  DR: 'G',
};

// ---------------------------------------------------------------------------
//  Stats
// ---------------------------------------------------------------------------

/** Trainable stat keys. */
export type StatKey = 'hp' | 'atk' | 'def' | 'spd';

/** All stat keys in canonical order. */
export const STAT_KEYS: readonly StatKey[] = ['hp', 'atk', 'def', 'spd'] as const;

/** A full stat block. */
export interface Stats {
  hp: number;
  atk: number;
  def: number;
  spd: number;
}

/** Maximum training bonus per stat. */
export const MAX_TRAIN_BONUS = 50;

/** Stat points gained per training session. */
export const TRAIN_POINTS_PER_SESSION = 3;

/** Level cap. */
export const MAX_LEVEL = 50;

// ---------------------------------------------------------------------------
//  Moves
// ---------------------------------------------------------------------------

/** Special move effects. */
export type MoveEffect = 'drain' | 'heal';

/** A battle move definition. */
export interface MoveDef {
  readonly id: string;
  readonly name: string;
  readonly element: TongueCode;
  /** Attack power, or heal percentage (of max HP) for 'heal' moves. */
  readonly power: number;
  /** Hit chance in [0, 1]. Heal moves always succeed. */
  readonly accuracy: number;
  readonly effect?: MoveEffect;
  readonly description: string;
}

// ---------------------------------------------------------------------------
//  Species & evolution
// ---------------------------------------------------------------------------

/** Stat-dominance profile used by evolution requirements. */
export type DominantStat = 'atk' | 'def' | 'spd' | 'balanced';

/**
 * One edge in the evolution graph. All present requirements must hold
 * (logical AND). Exactly one edge per species is the `fallback`, which
 * requires only the minimum level — so every creature can always evolve.
 */
export interface EvolutionRequirement {
  readonly targetId: string;
  readonly minLevel: number;
  /** Edge taken when nothing better qualifies. Only minLevel applies. */
  readonly fallback: boolean;
  /** Higher priority wins when several edges qualify. */
  readonly priority: number;
  readonly maxCareMistakes?: number;
  readonly minCareMistakes?: number;
  readonly minBond?: number;
  readonly minDiscipline?: number;
  readonly minBattlesWon?: number;
  /** Which training bonus must be strictly largest ('balanced' = no bonus > 1.5× another). */
  readonly dominantStat?: DominantStat;
  /** Battle scars carried (canon: losses leave marks that gate dark paths). */
  readonly minScars?: number;
  /** Contact with the Hollow — the gap between the tongues (Null Vale). */
  readonly minHollowExposure?: number;
}

/** A species (one node in the evolution graph). */
export interface SpeciesDef {
  readonly id: string;
  readonly name: string;
  readonly stage: Stage;
  readonly element: TongueCode;
  readonly alignment: Alignment;
  /** Base stats at level 1 (before growth and training). */
  readonly baseStats: Stats;
  /** Per-level stat growth factor. */
  readonly growth: number;
  /** Move ids available to this species (max 4). */
  readonly moves: readonly string[];
  /** Evolution edges out of this species (empty = terminal). */
  readonly evolvesTo: readonly EvolutionRequirement[];
  /** Flavor text shown in the codex. */
  readonly lore: string;
}

// ---------------------------------------------------------------------------
//  Monster (creature instance)
// ---------------------------------------------------------------------------

/** Care meters and history that drive evolution branching. */
export interface CareState {
  /** 0–100. Hits 0 → starving → care mistake. */
  hunger: number;
  /** 0–100. Hits 0 → exhausted → care mistake. */
  energy: number;
  /** 0–100. Affects battle variance and flavor. */
  mood: number;
  /** 0–100. Built by play/praise/wins. */
  bond: number;
  /** 0–100. Built by scolding and training. */
  discipline: number;
  /** Total accumulated care mistakes. */
  careMistakes: number;
  /** Internal flags so one starvation episode counts once. */
  starving: boolean;
  exhausted: boolean;
}

/** A living creature instance owned by a tamer. */
export interface MonsterState {
  readonly id: string;
  nickname: string;
  speciesId: string;
  level: number;
  xp: number;
  /** Permanent training bonuses added to base stats. */
  trainBonus: Stats;
  /** Times each stat was trained (drives dominantStat checks). */
  trainCounts: Stats;
  care: CareState;
  battlesWon: number;
  battlesLost: number;
  /** Total care ticks lived. */
  ageTicks: number;
  /** Ticks lived in the current stage (drives lifespan). */
  stageAgeTicks: number;
  /**
   * Battle scars — immune memory. Each loss leaves a scar; scars harden
   * defense (capped) and gate dark evolutions. The system gets stronger
   * from attacks.
   */
  scars: number;
  /** Battles since the last proper rest (drives strain). */
  consecutiveBattles: number;
  /** Contact with the Hollow, the gap between the tongues. */
  hollowExposure: number;
  /** Which generation of the tamer's line this creature is. */
  generation: number;
  /** Stats inherited from the previous generation at hatch. */
  heirloom: Stats;
  /** Species ids this creature has passed through. */
  lineage: string[];
}

/**
 * Battles fought without resting. At STRAIN_THRESHOLD and beyond, each
 * battle strains the creature (V-Pet rule: over-battling causes harm).
 */
export const STRAIN_THRESHOLD = 4;

/** Defense gained per scar (immune memory). */
export const SCAR_DEFENSE_BONUS = 1;

/** Maximum defense gained from scars. */
export const SCAR_DEFENSE_CAP = 10;

/**
 * Lifespan per stage, in care ticks. When a creature has lived this
 * long in its current stage without evolving, it returns to an egg —
 * and the next generation inherits part of its strength.
 */
export const STAGE_LIFESPAN_TICKS: Record<Stage, number> = {
  EGG: Number.POSITIVE_INFINITY,
  MOTE: 140,
  SPRITE: 180,
  GUARDIAN: 220,
  PARAGON: 260,
  APEX: 320,
};

/** Fraction of training bonuses inherited by the next generation. */
export const HEIRLOOM_FRACTION = 0.4;

/** Cap on inherited heirloom points per stat (keeps lines honest). */
export const HEIRLOOM_CAP = 30;

// ---------------------------------------------------------------------------
//  Battle
// ---------------------------------------------------------------------------

/** A battle-ready snapshot of a creature. */
export interface Combatant {
  readonly name: string;
  readonly speciesId: string;
  readonly element: TongueCode;
  readonly alignment: Alignment;
  readonly stats: Stats;
  readonly moves: readonly string[];
  readonly level: number;
  hp: number;
  guarding: boolean;
}

/** Player/AI battle action. */
export type BattleAction = { type: 'move'; moveId: string } | { type: 'guard' };

/** One entry in the battle log. */
export interface BattleEvent {
  readonly turn: number;
  readonly actor: 'A' | 'B';
  readonly kind: 'move' | 'guard' | 'miss' | 'crit' | 'drain' | 'heal' | 'faint';
  readonly moveId?: string;
  readonly damage?: number;
  readonly healed?: number;
  readonly text: string;
}

/** Mutable battle state. */
export interface BattleState {
  readonly a: Combatant;
  readonly b: Combatant;
  turn: number;
  over: boolean;
  winner: 'A' | 'B' | 'DRAW' | null;
  log: BattleEvent[];
  rngState: number;
}

/** Battles end in a draw after this many turns. */
export const MAX_BATTLE_TURNS = 100;

/** Base critical-hit chance. */
export const CRIT_CHANCE = 1 / 16;

/** Critical-hit damage multiplier. */
export const CRIT_MULTIPLIER = 1.5;

// ---------------------------------------------------------------------------
//  Game state
// ---------------------------------------------------------------------------

/** An unhatched egg. */
export interface EggState {
  speciesId: string;
  /** Warmth accumulated; hatches at WARMTH_TO_HATCH. */
  warmth: number;
  /** Stats inherited from the previous generation (rebirth eggs). */
  heirloom?: Stats;
  /** Generation this egg will hatch into (1 = first). */
  generation?: number;
}

/** Warm actions required to hatch an egg. */
export const WARMTH_TO_HATCH = 3;

/** Arena opponent definition. */
export interface ArenaRival {
  readonly name: string;
  readonly speciesId: string;
  readonly level: number;
  readonly title: string;
}

/** Top-level save-game state. */
export interface GameState {
  readonly version: 2;
  tamerName: string;
  egg: EggState | null;
  monster: MonsterState | null;
  /** Index of the next arena rival to face. */
  arenaRank: number;
  totalBattlesWon: number;
  totalBattlesLost: number;
  /** Deterministic RNG state. */
  rngState: number;
  /** Names of creatures that reached APEX. */
  hallOfFame: string[];
  /** Current region of Aethermoore (affects wild encounters). */
  region: string;
  /** Generation counter for the tamer's creature line. */
  generation: number;
  /** Memorial of past generations: "name the Species (Gen N)". */
  lineageMemorial: string[];
}
