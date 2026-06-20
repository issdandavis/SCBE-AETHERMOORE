/**
 * @file battle.unit.test.ts
 * @module tests/aethermon
 * @component AETHERMON — Battle Engine (L2-unit)
 *
 * Golden-ratio alignment triangle, Sacred Tongue element wheel,
 * deterministic seeded battles, guard mechanics, and post-battle
 * bookkeeping.
 */

import { describe, expect, it } from 'vitest';
import {
  ALIGNMENT_ADVANTAGE,
  ALIGNMENT_DISADVANTAGE,
  ELEMENT_ADVANTAGE,
  ELEMENT_DISADVANTAGE,
  MAX_BATTLE_TURNS,
  alignmentMultiplier,
  applyBattleResult,
  autoBattle,
  createMonster,
  createRng,
  elementMultiplier,
  getMove,
  getSpecies,
  rollDamage,
  toCombatant,
  wildCombatant,
} from '../../src/aethermon/index.js';

describe('type multipliers', () => {
  it('alignment triangle: AEGIS > VENOM > FLUX > AEGIS at φ / 1/φ', () => {
    expect(alignmentMultiplier('AEGIS', 'VENOM')).toBeCloseTo(ALIGNMENT_ADVANTAGE, 10);
    expect(alignmentMultiplier('VENOM', 'FLUX')).toBeCloseTo(ALIGNMENT_ADVANTAGE, 10);
    expect(alignmentMultiplier('FLUX', 'AEGIS')).toBeCloseTo(ALIGNMENT_ADVANTAGE, 10);
    expect(alignmentMultiplier('VENOM', 'AEGIS')).toBeCloseTo(ALIGNMENT_DISADVANTAGE, 10);
    expect(alignmentMultiplier('AEGIS', 'AEGIS')).toBe(1);
    // φ and 1/φ are exact inverses
    expect(ALIGNMENT_ADVANTAGE * ALIGNMENT_DISADVANTAGE).toBeCloseTo(1, 10);
  });

  it('element wheel: each tongue beats the next, loses to the previous', () => {
    expect(elementMultiplier('KO', 'AV')).toBe(ELEMENT_ADVANTAGE);
    expect(elementMultiplier('DR', 'KO')).toBe(ELEMENT_ADVANTAGE);
    expect(elementMultiplier('KO', 'DR')).toBe(ELEMENT_DISADVANTAGE);
    expect(elementMultiplier('KO', 'RU')).toBe(1);
    expect(elementMultiplier('UM', 'UM')).toBe(1);
  });
});

describe('damage rolls', () => {
  const attacker = () => wildCombatant(getSpecies('blazewarden'), 15);
  const defender = () => wildCombatant(getSpecies('runewarden'), 15);

  it('deals at least 1 damage on a hit and is deterministic per seed', () => {
    const move = getMove('command_burst');
    const a = rollDamage(attacker(), defender(), move, createRng(7));
    const b = rollDamage(attacker(), defender(), move, createRng(7));
    expect(a).toEqual(b);
    if (!a.miss) expect(a.damage).toBeGreaterThanOrEqual(1);
  });

  it('guarding roughly halves damage', () => {
    const move = getMove('command_burst');
    const open = defender();
    const guarded = defender();
    guarded.guarding = true;
    // Find a seed where the move hits without a crit.
    let seed = 1;
    let openRoll = rollDamage(attacker(), open, move, createRng(seed));
    while (openRoll.miss || openRoll.crit) {
      seed += 1;
      openRoll = rollDamage(attacker(), open, move, createRng(seed));
    }
    const guardedRoll = rollDamage(attacker(), guarded, move, createRng(seed));
    expect(guardedRoll.damage).toBeLessThan(openRoll.damage);
    expect(guardedRoll.damage).toBeLessThanOrEqual(Math.floor(openRoll.damage / 2) + 1);
  });
});

describe('autoBattle', () => {
  it('is fully deterministic for a given seed', () => {
    const run = () =>
      autoBattle(
        wildCombatant(getSpecies('pyreling'), 8),
        wildCombatant(getSpecies('gloomkit'), 8),
        1234
      );
    const first = run();
    const second = run();
    expect(first.winner).toBe(second.winner);
    expect(first.turn).toBe(second.turn);
    expect(first.log.map((e) => e.text)).toEqual(second.log.map((e) => e.text));
  });

  it('terminates with a winner or draw and non-negative HP', () => {
    for (let seed = 0; seed < 25; seed++) {
      const state = autoBattle(
        wildCombatant(getSpecies('cipherwarden'), 14),
        wildCombatant(getSpecies('nullshade'), 14),
        seed
      );
      expect(state.over).toBe(true);
      expect(['A', 'B', 'DRAW']).toContain(state.winner);
      expect(state.turn).toBeLessThanOrEqual(MAX_BATTLE_TURNS);
      expect(state.a.hp).toBeGreaterThanOrEqual(0);
      expect(state.b.hp).toBeGreaterThanOrEqual(0);
    }
  });

  it('a much stronger creature reliably wins', () => {
    let wins = 0;
    for (let seed = 0; seed < 10; seed++) {
      const state = autoBattle(
        wildCombatant(getSpecies('solarchon'), 30),
        wildCombatant(getSpecies('kindlemote'), 2),
        seed
      );
      if (state.winner === 'A') wins += 1;
    }
    expect(wins).toBe(10);
  });
});

describe('combatant snapshots & bookkeeping', () => {
  it('toCombatant reflects mood in effective attack', () => {
    const happy = createMonster('pyreling', 'Sunny');
    happy.care.mood = 100;
    const sad = createMonster('pyreling', 'Gloomy');
    sad.care.mood = 0;
    expect(toCombatant(happy).stats.atk).toBeGreaterThan(toCombatant(sad).stats.atk);
  });

  it('wildCombatant stats scale with level', () => {
    const low = wildCombatant(getSpecies('bitling'), 5);
    const high = wildCombatant(getSpecies('bitling'), 20);
    expect(high.stats.hp).toBeGreaterThan(low.stats.hp);
    expect(high.stats.atk).toBeGreaterThan(low.stats.atk);
  });

  it('applyBattleResult updates record, drains meters and ages the creature', () => {
    const monster = createMonster('pyreling', 'Sunny');
    const energy = monster.care.energy;
    const age = monster.ageTicks;
    const aftermath = applyBattleResult(monster, true);
    expect(monster.battlesWon).toBe(1);
    // One care tick passes (-4 energy), then battle fatigue (-10).
    expect(monster.care.energy).toBe(energy - 14);
    expect(monster.ageTicks).toBe(age + 1);
    expect(aftermath.scarred).toBe(false);
    const lossAftermath = applyBattleResult(monster, false);
    expect(monster.battlesLost).toBe(1);
    expect(lossAftermath.scarred).toBe(true);
    expect(monster.scars).toBe(1);
  });
});
