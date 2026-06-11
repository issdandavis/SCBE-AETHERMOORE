/**
 * @file battle.ts
 * @module aethermon/battle
 * @layer Layer 5, Layer 12, Layer 13
 * @component AETHERMON — Turn-Based Battle Engine
 *
 * Deterministic, seeded battle resolution. Damage stacks four
 * multipliers: alignment triangle (golden ratio φ / 1/φ), element wheel
 * (Sacred Tongues), same-element bonus (STAB), and crit/variance rolls.
 * Guarding halves incoming damage for the round.
 *
 * A2: HP is clamped to [0, maxHp] after every event.
 * A3: Identical (combatants, seed) ⇒ identical battle log.
 */

import type {
  BattleAction,
  BattleEvent,
  BattleState,
  Combatant,
  MonsterState,
  MoveDef,
  SpeciesDef,
} from './types.js';
import {
  CRIT_CHANCE,
  CRIT_MULTIPLIER,
  MAX_BATTLE_TURNS,
  STAB_BONUS,
  alignmentMultiplier,
  elementMultiplier,
} from './types.js';
import { getMove } from './moves.js';
import { getSpecies } from './species.js';
import { effectiveStats } from './monster.js';
import { chance, createRng, nextFloat, type Rng } from './rng.js';

// ---------------------------------------------------------------------------
//  Combatant construction
// ---------------------------------------------------------------------------

/**
 * Snapshot a tamed creature for battle. Mood nudges effective attack:
 * ×0.9 (miserable) to ×1.1 (delighted).
 */
export function toCombatant(monster: MonsterState): Combatant {
  const species = getSpecies(monster.speciesId);
  const stats = effectiveStats(monster);
  const moodFactor = 0.9 + 0.2 * (monster.care.mood / 100);
  stats.atk = Math.max(1, Math.floor(stats.atk * moodFactor));
  return {
    name: monster.nickname,
    speciesId: species.id,
    element: species.element,
    alignment: species.alignment,
    stats,
    moves: species.moves,
    level: monster.level,
    hp: stats.hp,
    guarding: false,
  };
}

/** Build a wild/arena combatant straight from a species at a level. */
export function wildCombatant(species: SpeciesDef, level: number, name?: string): Combatant {
  const scale = 1 + species.growth * (level - 1);
  const stats = {
    hp: Math.floor(species.baseStats.hp * scale),
    atk: Math.floor(species.baseStats.atk * scale),
    def: Math.floor(species.baseStats.def * scale),
    spd: Math.floor(species.baseStats.spd * scale),
  };
  return {
    name: name ?? `wild ${species.name}`,
    speciesId: species.id,
    element: species.element,
    alignment: species.alignment,
    stats,
    moves: species.moves,
    level,
    hp: stats.hp,
    guarding: false,
  };
}

// ---------------------------------------------------------------------------
//  Damage
// ---------------------------------------------------------------------------

/** Outcome of a single damage roll. */
export interface DamageRoll {
  readonly miss: boolean;
  readonly crit: boolean;
  readonly damage: number;
  readonly elementMult: number;
  readonly alignmentMult: number;
}

/**
 * Roll damage for one move. Multiplier stack:
 * raw = power × (atk/def) × 0.25 + 2
 * dmg = raw × alignment(φ|1|1/φ) × element(1.25|1|0.8) × STAB × crit × variance
 * Tuned so evenly matched creatures trade ~3–5 hits per knockout.
 */
export function rollDamage(
  attacker: Combatant,
  defender: Combatant,
  move: MoveDef,
  rng: Rng
): DamageRoll {
  if (nextFloat(rng) >= move.accuracy) {
    return { miss: true, crit: false, damage: 0, elementMult: 1, alignmentMult: 1 };
  }
  const raw = move.power * (attacker.stats.atk / Math.max(1, defender.stats.def)) * 0.25 + 2;
  const alignMult = alignmentMultiplier(attacker.alignment, defender.alignment);
  const elemMult = elementMultiplier(move.element, defender.element);
  const stab = move.element === attacker.element ? STAB_BONUS : 1.0;
  const crit = chance(rng, CRIT_CHANCE);
  const variance = 0.85 + 0.15 * nextFloat(rng);
  let damage = raw * alignMult * elemMult * stab * variance;
  if (crit) damage *= CRIT_MULTIPLIER;
  if (defender.guarding) damage *= 0.5;
  return {
    miss: false,
    crit,
    damage: Math.max(1, Math.floor(damage)),
    elementMult: elemMult,
    alignmentMult: alignMult,
  };
}

// ---------------------------------------------------------------------------
//  Battle state machine
// ---------------------------------------------------------------------------

/** Start a battle between two combatants with a deterministic seed. */
export function createBattle(a: Combatant, b: Combatant, seed: number): BattleState {
  return { a, b, turn: 0, over: false, winner: null, log: [], rngState: seed >>> 0 };
}

function combatant(state: BattleState, side: 'A' | 'B'): Combatant {
  return side === 'A' ? state.a : state.b;
}

function opponentOf(side: 'A' | 'B'): 'A' | 'B' {
  return side === 'A' ? 'B' : 'A';
}

/**
 * AI move policy: usually picks the highest expected-damage move
 * (power × accuracy × type multipliers), sometimes improvises; heals
 * when hurt and able.
 */
export function chooseAiAction(state: BattleState, side: 'A' | 'B'): BattleAction {
  const self = combatant(state, side);
  const foe = combatant(state, opponentOf(side));
  const rng = createRng(state.rngState);

  const healMoves = self.moves.filter((id) => getMove(id).effect === 'heal');
  if (healMoves.length > 0 && self.hp < self.stats.hp * 0.35 && chance(rng, 0.7)) {
    state.rngState = rng.state;
    return { type: 'move', moveId: healMoves[0] };
  }

  const attackMoves = self.moves.filter((id) => getMove(id).effect !== 'heal');
  if (attackMoves.length === 0) {
    state.rngState = rng.state;
    return { type: 'guard' };
  }
  if (chance(rng, 0.2)) {
    const idx = Math.floor(nextFloat(rng) * attackMoves.length);
    state.rngState = rng.state;
    return { type: 'move', moveId: attackMoves[idx] };
  }
  let best = attackMoves[0];
  let bestScore = -1;
  for (const id of attackMoves) {
    const move = getMove(id);
    const score =
      move.power *
      move.accuracy *
      alignmentMultiplier(self.alignment, foe.alignment) *
      elementMultiplier(move.element, foe.element) *
      (move.element === self.element ? STAB_BONUS : 1);
    if (score > bestScore) {
      bestScore = score;
      best = id;
    }
  }
  state.rngState = rng.state;
  return { type: 'move', moveId: best };
}

function applyAction(
  state: BattleState,
  side: 'A' | 'B',
  action: BattleAction,
  rng: Rng
): BattleEvent[] {
  const events: BattleEvent[] = [];
  const self = combatant(state, side);
  const foe = combatant(state, opponentOf(side));
  if (self.hp <= 0 || state.over) return events;

  if (action.type === 'guard') {
    self.guarding = true;
    events.push({
      turn: state.turn,
      actor: side,
      kind: 'guard',
      text: `${self.name} braces behind a ward.`,
    });
    return events;
  }

  const move = getMove(action.moveId);

  if (move.effect === 'heal') {
    const healed = Math.min(
      self.stats.hp - self.hp,
      Math.max(1, Math.floor((self.stats.hp * move.power) / 100))
    );
    self.hp += healed;
    events.push({
      turn: state.turn,
      actor: side,
      kind: 'heal',
      moveId: move.id,
      healed,
      text: `${self.name} uses ${move.name} and restores ${healed} HP.`,
    });
    return events;
  }

  const roll = rollDamage(self, foe, move, rng);
  if (roll.miss) {
    events.push({
      turn: state.turn,
      actor: side,
      kind: 'miss',
      moveId: move.id,
      text: `${self.name}'s ${move.name} misses!`,
    });
    return events;
  }

  foe.hp = Math.max(0, foe.hp - roll.damage);
  const tags: string[] = [];
  if (roll.crit) tags.push('CRIT!');
  if (roll.alignmentMult > 1 || roll.elementMult > 1) tags.push("it's super effective!");
  if (roll.alignmentMult < 1 || roll.elementMult < 1) tags.push("it's not very effective...");
  events.push({
    turn: state.turn,
    actor: side,
    kind: roll.crit ? 'crit' : 'move',
    moveId: move.id,
    damage: roll.damage,
    text: `${self.name} uses ${move.name} — ${roll.damage} damage. ${tags.join(' ')}`.trim(),
  });

  if (move.effect === 'drain' && roll.damage > 0) {
    const healed = Math.min(self.stats.hp - self.hp, Math.max(1, Math.floor(roll.damage / 2)));
    if (healed > 0) {
      self.hp += healed;
      events.push({
        turn: state.turn,
        actor: side,
        kind: 'drain',
        moveId: move.id,
        healed,
        text: `${self.name} siphons ${healed} HP.`,
      });
    }
  }

  if (foe.hp <= 0) {
    state.over = true;
    state.winner = side;
    events.push({
      turn: state.turn,
      actor: opponentOf(side),
      kind: 'faint',
      text: `${foe.name} collapses into stray data!`,
    });
  }
  return events;
}

/**
 * Resolve one round: both sides act in speed order (ties broken by RNG).
 * Returns the events generated this round.
 */
export function performRound(
  state: BattleState,
  actionA: BattleAction,
  actionB: BattleAction
): BattleEvent[] {
  if (state.over) return [];
  state.turn += 1;
  state.a.guarding = false;
  state.b.guarding = false;

  const rng = createRng(state.rngState);
  // Guards resolve first so they protect against this round's attacks.
  if (actionA.type === 'guard') state.a.guarding = true;
  if (actionB.type === 'guard') state.b.guarding = true;

  let order: Array<['A' | 'B', BattleAction]>;
  const aFirst =
    state.a.stats.spd > state.b.stats.spd ||
    (state.a.stats.spd === state.b.stats.spd && chance(rng, 0.5));
  order = aFirst
    ? [
        ['A', actionA],
        ['B', actionB],
      ]
    : [
        ['B', actionB],
        ['A', actionA],
      ];

  const events: BattleEvent[] = [];
  for (const [side, action] of order) {
    events.push(...applyAction(state, side, action, rng));
  }

  if (!state.over && state.turn >= MAX_BATTLE_TURNS) {
    state.over = true;
    state.winner = 'DRAW';
    events.push({
      turn: state.turn,
      actor: 'A',
      kind: 'faint',
      text: 'Both creatures stand exhausted — the battle is a draw.',
    });
  }

  state.rngState = rng.state;
  state.log.push(...events);
  return events;
}

/** Run a full AI-vs-AI battle to completion. */
export function autoBattle(a: Combatant, b: Combatant, seed: number): BattleState {
  const state = createBattle(a, b, seed);
  while (!state.over) {
    const actionA = chooseAiAction(state, 'A');
    const actionB = chooseAiAction(state, 'B');
    performRound(state, actionA, actionB);
  }
  return state;
}

// ---------------------------------------------------------------------------
//  Post-battle bookkeeping
// ---------------------------------------------------------------------------

/** Apply a battle result to the tamed creature's history and meters. */
export function applyBattleResult(monster: MonsterState, won: boolean): void {
  const care = monster.care;
  if (won) {
    monster.battlesWon += 1;
    care.mood = Math.min(100, care.mood + 10);
    care.bond = Math.min(100, care.bond + 5);
  } else {
    monster.battlesLost += 1;
    care.mood = Math.max(0, care.mood - 15);
  }
  care.energy = Math.max(0, care.energy - 10);
  care.hunger = Math.max(0, care.hunger - 10);
}
