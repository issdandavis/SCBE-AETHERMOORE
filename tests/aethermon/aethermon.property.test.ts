/**
 * @file aethermon.property.test.ts
 * @module tests/aethermon
 * @component AETHERMON — Property-Based Invariants (L4-property)
 *
 * Random-input proofs with fast-check:
 *  - battles always terminate, HP never goes negative
 *  - damage rolls are ≥ 1 on hit
 *  - care meters stay clamped under arbitrary action sequences
 *  - save/load is a lossless round trip after arbitrary play
 */

import { describe, expect, it } from 'vitest';
import * as fc from 'fast-check';
import {
  MAX_BATTLE_TURNS,
  MAX_LEVEL,
  allSpecies,
  autoBattle,
  createMonster,
  createRng,
  deserializeGame,
  feed,
  gainXp,
  generateWildEncounter,
  getMove,
  getSpecies,
  newGame,
  play,
  praise,
  recordBattleOutcome,
  rest,
  rollDamage,
  scold,
  serializeGame,
  tick,
  train,
  warmEgg,
  wildCombatant,
} from '../../src/aethermon/index.js';

const battleSpeciesIds = allSpecies()
  .filter((s) => s.stage !== 'EGG')
  .map((s) => s.id);

const speciesArb = fc.constantFrom(...battleSpeciesIds);
const levelArb = fc.integer({ min: 1, max: MAX_LEVEL });
const seedArb = fc.integer({ min: 0, max: 2 ** 31 - 1 });

describe('battle invariants (L4)', () => {
  it('every battle terminates with a result and clamped HP', () => {
    fc.assert(
      fc.property(speciesArb, speciesArb, levelArb, levelArb, seedArb, (sa, sb, la, lb, seed) => {
        const state = autoBattle(
          wildCombatant(getSpecies(sa), la),
          wildCombatant(getSpecies(sb), lb),
          seed
        );
        expect(state.over).toBe(true);
        expect(['A', 'B', 'DRAW']).toContain(state.winner);
        expect(state.turn).toBeGreaterThanOrEqual(1);
        expect(state.turn).toBeLessThanOrEqual(MAX_BATTLE_TURNS);
        expect(state.a.hp).toBeGreaterThanOrEqual(0);
        expect(state.b.hp).toBeGreaterThanOrEqual(0);
        expect(state.a.hp).toBeLessThanOrEqual(state.a.stats.hp);
        expect(state.b.hp).toBeLessThanOrEqual(state.b.stats.hp);
      }),
      { numRuns: 60 }
    );
  });

  it('damage on hit is always ≥ 1, even vs maximal defense', () => {
    const attackMoveIds = allSpecies()
      .flatMap((s) => s.moves)
      .filter((id) => getMove(id).effect !== 'heal');
    fc.assert(
      fc.property(
        speciesArb,
        speciesArb,
        levelArb,
        fc.constantFrom(...new Set(attackMoveIds)),
        seedArb,
        (sa, sb, level, moveId, seed) => {
          const attacker = wildCombatant(getSpecies(sa), 1);
          const defender = wildCombatant(getSpecies(sb), level);
          const roll = rollDamage(attacker, defender, getMove(moveId), createRng(seed));
          if (!roll.miss) expect(roll.damage).toBeGreaterThanOrEqual(1);
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe('care invariants (L4)', () => {
  type CareAction = 'feed' | 'rest' | 'play' | 'praise' | 'scold' | 'train' | 'tick';
  const actionArb = fc.constantFrom<CareAction>(
    'feed',
    'rest',
    'play',
    'praise',
    'scold',
    'train',
    'tick'
  );

  it('meters stay in [0,100] and mistakes only grow, under any action sequence', () => {
    fc.assert(
      fc.property(speciesArb, fc.array(actionArb, { maxLength: 80 }), (speciesId, actions) => {
        const monster = createMonster(speciesId, 'Prop');
        let mistakes = 0;
        for (const action of actions) {
          if (action === 'feed') feed(monster);
          else if (action === 'rest') rest(monster);
          else if (action === 'play') play(monster);
          else if (action === 'praise') praise(monster);
          else if (action === 'scold') scold(monster);
          else if (action === 'train') train(monster, 'atk');
          else tick(monster);
          const care = monster.care;
          for (const value of [care.hunger, care.energy, care.mood, care.bond, care.discipline]) {
            expect(value).toBeGreaterThanOrEqual(0);
            expect(value).toBeLessThanOrEqual(100);
          }
          expect(care.careMistakes).toBeGreaterThanOrEqual(mistakes);
          mistakes = care.careMistakes;
        }
      }),
      { numRuns: 60 }
    );
  });

  it('xp gain never overshoots the level cap', () => {
    fc.assert(
      fc.property(speciesArb, fc.integer({ min: 0, max: 5_000_000 }), (speciesId, xp) => {
        const monster = createMonster(speciesId, 'Prop');
        gainXp(monster, xp);
        expect(monster.level).toBeGreaterThanOrEqual(1);
        expect(monster.level).toBeLessThanOrEqual(MAX_LEVEL);
      }),
      { numRuns: 60 }
    );
  });
});

describe('persistence invariants (L4)', () => {
  it('save/load round-trips after arbitrary play sequences', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('ember_egg', 'cipher_egg', 'umbral_egg'),
        seedArb,
        fc.array(fc.integer({ min: 0, max: 3 }), { maxLength: 30 }),
        (eggId, seed, plays) => {
          const state = newGame('Prop', eggId, seed);
          while (state.egg) warmEgg(state, 'Prop');
          const monster = state.monster!;
          for (const step of plays) {
            if (step === 0) feed(monster);
            else if (step === 1) train(monster, 'spd');
            else if (step === 2) {
              const enemy = generateWildEncounter(state, monster);
              recordBattleOutcome(state, monster, enemy.level, true, false);
            } else rest(monster);
          }
          const restored = deserializeGame(serializeGame(state));
          expect(restored).toEqual(state);
          // RNG state survives the round trip → identical future encounters.
          const nextA = generateWildEncounter(state, monster);
          const nextB = generateWildEncounter(restored, restored.monster!);
          expect(nextB.speciesId).toBe(nextA.speciesId);
          expect(nextB.level).toBe(nextA.level);
        }
      ),
      { numRuns: 40 }
    );
  });
});
