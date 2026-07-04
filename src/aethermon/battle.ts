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
  BUFF_MULTIPLIER,
  CRIT_CHANCE,
  CRIT_MULTIPLIER,
  DEBUFF_MULTIPLIER,
  HODGE_DUALS,
  HODGE_RESONANCE,
  MAX_BATTLE_TURNS,
  MIN_WEIGHT,
  STAB_BONUS,
  STRAIN_THRESHOLD,
  WEIGHT_BATTLE_BURN,
  alignmentMultiplier,
  elementMultiplier,
} from './types.js';
import { getMove } from './moves.js';
import { getSpecies } from './species.js';
import { effectiveStats, tick } from './monster.js';
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
    stunned: false,
    atkRaised: false,
    spdRaised: false,
    defLowered: false,
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
    stunned: false,
    atkRaised: false,
    spdRaised: false,
    defLowered: false,
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
  /** True when the move spoke the attacker's Hodge dual tongue. */
  readonly resonance: boolean;
}

/**
 * Same-element bonus or Hodge-dual resonance for a move. STAB (×1.2)
 * when the move matches the attacker's tongue; resonance (×1.3, canon:
 * duals bond 30% stronger) when it matches the attacker's Hodge dual
 * (KO↔DR, AV↔UM, RU↔CA). Mutually exclusive by construction.
 */
export function affinityMultiplier(attacker: Combatant, move: MoveDef): number {
  if (move.element === attacker.element) return STAB_BONUS;
  if (HODGE_DUALS[attacker.element] === move.element) return HODGE_RESONANCE;
  return 1.0;
}

/**
 * Roll damage for one move. Multiplier stack:
 * raw = power × (atk/def) × 0.25 + 2
 * dmg = raw × alignment(φ|1|1/φ) × element(1.25|1|0.8) × affinity(STAB|resonance)
 *       × crit × variance
 * Tuned so evenly matched creatures trade ~3–5 hits per knockout.
 */
export function rollDamage(
  attacker: Combatant,
  defender: Combatant,
  move: MoveDef,
  rng: Rng
): DamageRoll {
  if (nextFloat(rng) >= move.accuracy) {
    return {
      miss: true,
      crit: false,
      damage: 0,
      elementMult: 1,
      alignmentMult: 1,
      resonance: false,
    };
  }
  const raw = move.power * (attacker.stats.atk / Math.max(1, defender.stats.def)) * 0.25 + 2;
  const alignMult = alignmentMultiplier(attacker.alignment, defender.alignment);
  const elemMult = elementMultiplier(move.element, defender.element);
  const affinity = affinityMultiplier(attacker, move);
  const resonance = affinity === HODGE_RESONANCE;
  const crit = chance(rng, CRIT_CHANCE);
  const variance = 0.85 + 0.15 * nextFloat(rng);
  let damage = raw * alignMult * elemMult * affinity * variance;
  if (crit) damage *= CRIT_MULTIPLIER;
  // guard_break slips past the ward entirely (and shatters it — see applyAction).
  if (defender.guarding && move.effect !== 'guard_break') damage *= 0.5;
  return {
    miss: false,
    crit,
    damage: Math.max(1, Math.floor(damage)),
    elementMult: elemMult,
    alignmentMult: alignMult,
    resonance,
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
 * when hurt and able; opens with a useful utility move (buff, bind,
 * crumble) in the early turns.
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

  // Utility openers — only ones that would do something right now.
  const usefulUtility = self.moves.filter((id) => {
    const move = getMove(id);
    if (move.effect === 'atk_up') return !self.atkRaised;
    if (move.effect === 'spd_up') return !self.spdRaised && self.stats.spd <= foe.stats.spd;
    if (move.effect === 'def_down') return !foe.defLowered;
    if (move.effect === 'stun') return !foe.stunned;
    return false;
  });
  if (usefulUtility.length > 0 && state.turn < 4 && chance(rng, 0.45)) {
    const idx = Math.floor(nextFloat(rng) * usefulUtility.length);
    state.rngState = rng.state;
    return { type: 'move', moveId: usefulUtility[idx] };
  }

  // Damaging moves only — spent utilities would be wasted turns.
  const attackMoves = self.moves.filter((id) => {
    const move = getMove(id);
    return move.effect !== 'heal' && move.power > 0;
  });
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
      affinityMultiplier(self, move);
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

  // A stunned creature loses this action (the binding releases after).
  if (self.stunned) {
    self.stunned = false;
    self.guarding = false;
    events.push({
      turn: state.turn,
      actor: side,
      kind: 'immobile',
      text: `${self.name} is bound by the lattice and cannot move!`,
    });
    return events;
  }

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

  if (move.effect === 'atk_up' || move.effect === 'spd_up') {
    const stat = move.effect === 'atk_up' ? 'atk' : 'spd';
    const flag = move.effect === 'atk_up' ? 'atkRaised' : 'spdRaised';
    if (self[flag]) {
      events.push({
        turn: state.turn,
        actor: side,
        kind: 'buff',
        moveId: move.id,
        text: `${self.name} uses ${move.name} — but its ${stat.toUpperCase()} can rise no further.`,
      });
      return events;
    }
    self[flag] = true;
    self.stats[stat] = Math.max(1, Math.floor(self.stats[stat] * BUFF_MULTIPLIER));
    events.push({
      turn: state.turn,
      actor: side,
      kind: 'buff',
      moveId: move.id,
      text: `${self.name} uses ${move.name} — its ${stat.toUpperCase()} surges!`,
    });
    return events;
  }

  if (move.effect === 'def_down') {
    if (nextFloat(rng) >= move.accuracy) {
      events.push({
        turn: state.turn,
        actor: side,
        kind: 'miss',
        moveId: move.id,
        text: `${self.name}'s ${move.name} misses!`,
      });
      return events;
    }
    if (foe.defLowered) {
      events.push({
        turn: state.turn,
        actor: side,
        kind: 'debuff',
        moveId: move.id,
        text: `${self.name} uses ${move.name} — but ${foe.name}'s guard is already crumbled.`,
      });
      return events;
    }
    foe.defLowered = true;
    foe.stats.def = Math.max(1, Math.floor(foe.stats.def * DEBUFF_MULTIPLIER));
    events.push({
      turn: state.turn,
      actor: side,
      kind: 'debuff',
      moveId: move.id,
      text: `${self.name} uses ${move.name} — ${foe.name}'s DEF crumbles!`,
    });
    return events;
  }

  if (move.effect === 'stun') {
    if (nextFloat(rng) >= move.accuracy) {
      events.push({
        turn: state.turn,
        actor: side,
        kind: 'miss',
        moveId: move.id,
        text: `${self.name}'s ${move.name} misses!`,
      });
      return events;
    }
    if (foe.stunned) {
      events.push({
        turn: state.turn,
        actor: side,
        kind: 'stun',
        moveId: move.id,
        text: `${self.name} uses ${move.name} — but ${foe.name} is already bound.`,
      });
      return events;
    }
    foe.stunned = true;
    events.push({
      turn: state.turn,
      actor: side,
      kind: 'stun',
      moveId: move.id,
      text: `${self.name} uses ${move.name} — ${foe.name} is seized by crystal bonds!`,
    });
    return events;
  }

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
  if (move.effect === 'guard_break' && foe.guarding) {
    foe.guarding = false;
    tags.push('the ward shatters!');
  }
  if (roll.crit) tags.push('CRIT!');
  if (roll.resonance) tags.push('dual resonance!');
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
  // Guards resolve first so they protect against this round's attacks —
  // unless the guard is stunned: bound limbs cannot brace.
  if (actionA.type === 'guard' && !state.a.stunned) state.a.guarding = true;
  if (actionB.type === 'guard' && !state.b.stunned) state.b.guarding = true;

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

/** Outcome details from post-battle bookkeeping, for the UI. */
export interface BattleAftermath {
  /** A scar was earned (loss — immune memory hardens). */
  readonly scarred: boolean;
  /** The creature fought past its limit (V-Pet over-battling rule). */
  readonly strained: boolean;
  /** Over-battling just corrupted it — it needs a patch. */
  readonly glitchedByStrain: boolean;
}

/**
 * Apply a battle result to the tamed creature's history and meters.
 * A battle takes time (one care tick — creatures age in the arena) and
 * burns a little weight. Losses leave scars (immune memory: +DEF,
 * capped, and keys to dark evolutions). Battling repeatedly without
 * rest causes strain — and strain corrupts: the creature glitches.
 */
export function applyBattleResult(monster: MonsterState, won: boolean): BattleAftermath {
  const care = monster.care;
  tick(monster);
  monster.consecutiveBattles += 1;
  // A4: Clamping — weight never drops below MIN_WEIGHT.
  monster.weightKb = Math.max(MIN_WEIGHT, monster.weightKb - WEIGHT_BATTLE_BURN);
  let scarred = false;
  if (won) {
    monster.battlesWon += 1;
    care.mood = Math.min(100, care.mood + 10);
    care.bond = Math.min(100, care.bond + 5);
  } else {
    monster.battlesLost += 1;
    monster.scars += 1;
    scarred = true;
    care.mood = Math.max(0, care.mood - 15);
  }
  care.energy = Math.max(0, care.energy - 10);
  care.hunger = Math.max(0, care.hunger - 10);

  const strained = monster.consecutiveBattles >= STRAIN_THRESHOLD;
  let glitchedByStrain = false;
  if (strained) {
    care.energy = Math.max(0, care.energy - 15);
    care.mood = Math.max(0, care.mood - 10);
    if (!monster.glitched) {
      monster.glitched = true;
      glitchedByStrain = true;
    }
  }
  return { scarred, strained, glitchedByStrain };
}
