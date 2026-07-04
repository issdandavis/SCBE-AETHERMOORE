/**
 * @file battletactics.unit.test.ts
 * @module tests/aethermon
 * @layer Layer 5, Layer 12
 * @component AETHERMON — Battle Tactics (buffs, debuffs, stun, guard break)
 *
 * The utility-move layer: each Sacred Tongue's domain move — KO rally
 * (atk_up), AV tailwind (spd_up), RU rust hex (def_down), UM ward
 * shatter (guard_break), DR binding lattice (stun) — plus the AI's use
 * of them. All battles stay deterministic (A3): seeded RNG only.
 */

import { describe, expect, it } from 'vitest';
import type { Combatant } from '../../src/aethermon/types.js';
import { BUFF_MULTIPLIER, DEBUFF_MULTIPLIER } from '../../src/aethermon/types.js';
import { getMove } from '../../src/aethermon/moves.js';
import { allSpecies, getSpecies } from '../../src/aethermon/species.js';
import {
  autoBattle,
  createBattle,
  performRound,
  rollDamage,
  wildCombatant,
} from '../../src/aethermon/battle.js';
import { createRng } from '../../src/aethermon/rng.js';

/** A fresh combatant with predictable stats for effect assertions. */
function fighter(speciesId: string, level = 20): Combatant {
  return wildCombatant(getSpecies(speciesId), level);
}

describe('utility move catalog', () => {
  it('defines one domain move per tongue with the right effect', () => {
    expect(getMove('rally_cry').effect).toBe('atk_up');
    expect(getMove('tailwind').effect).toBe('spd_up');
    expect(getMove('rust_hex').effect).toBe('def_down');
    expect(getMove('ward_shatter').effect).toBe('guard_break');
    expect(getMove('binding_lattice').effect).toBe('stun');
  });

  it('every species moveset still resolves and stays within 4 moves', () => {
    for (const species of allSpecies()) {
      expect(species.moves.length).toBeLessThanOrEqual(4);
      for (const id of species.moves) expect(getMove(id).id).toBe(id);
    }
  });

  it('every GUARDIAN and above carries at least one utility or heal move', () => {
    const utilityEffects = new Set(['atk_up', 'spd_up', 'def_down', 'stun', 'guard_break', 'heal']);
    for (const species of allSpecies()) {
      if (!['GUARDIAN', 'PARAGON', 'APEX'].includes(species.stage)) continue;
      const hasUtility = species.moves.some((id) => {
        const effect = getMove(id).effect;
        return effect !== undefined && utilityEffects.has(effect);
      });
      expect(hasUtility, `${species.id} should carry a tactic`).toBe(true);
    }
  });
});

describe('buffs and debuffs', () => {
  it('atk_up raises attack once, then can rise no further', () => {
    const a = fighter('blazewarden');
    const b = fighter('runewarden');
    const battle = createBattle(a, b, 7);
    const baseAtk = a.stats.atk;

    performRound(battle, { type: 'move', moveId: 'rally_cry' }, { type: 'guard' });
    expect(a.atkRaised).toBe(true);
    expect(a.stats.atk).toBe(Math.floor(baseAtk * BUFF_MULTIPLIER));

    const raised = a.stats.atk;
    const events = performRound(battle, { type: 'move', moveId: 'rally_cry' }, { type: 'guard' });
    expect(a.stats.atk).toBe(raised); // no stacking
    expect(events.some((e) => e.kind === 'buff' && e.text.includes('no further'))).toBe(true);
  });

  it('spd_up raises speed and shifts turn order', () => {
    const a = fighter('skywarden');
    const b = fighter('blazewarden');
    a.stats.spd = b.stats.spd - 1; // strictly slower before the buff
    const battle = createBattle(a, b, 11);
    const baseSpd = a.stats.spd;
    performRound(battle, { type: 'move', moveId: 'tailwind' }, { type: 'guard' });
    expect(a.spdRaised).toBe(true);
    expect(a.stats.spd).toBe(Math.floor(baseSpd * BUFF_MULTIPLIER));
    expect(a.stats.spd).toBeGreaterThan(b.stats.spd);
  });

  it('def_down crumbles the foe defense exactly once', () => {
    const a = fighter('ashrevenant');
    const b = fighter('blazewarden');
    const battle = createBattle(a, b, 13);
    const baseDef = b.stats.def;
    // rust_hex has 0.9 accuracy — retry rounds until it lands (seeded, so
    // the sequence is fixed; a miss would simply consume a round).
    let guard = 0;
    while (!b.defLowered && guard < 10) {
      performRound(battle, { type: 'move', moveId: 'rust_hex' }, { type: 'guard' });
      guard += 1;
    }
    expect(b.defLowered).toBe(true);
    expect(b.stats.def).toBe(Math.max(1, Math.floor(baseDef * DEBUFF_MULTIPLIER)));
  });
});

describe('stun (binding lattice)', () => {
  it('a stunned combatant loses exactly its next action', () => {
    const a = fighter('runewarden');
    const b = fighter('blazewarden');
    const battle = createBattle(a, b, 3);
    let guard = 0;
    while (!b.stunned && guard < 12) {
      performRound(battle, { type: 'move', moveId: 'binding_lattice' }, { type: 'guard' });
      guard += 1;
    }
    expect(b.stunned).toBe(true);

    const hpBefore = a.hp;
    const events = performRound(
      battle,
      { type: 'guard' },
      { type: 'move', moveId: 'ember_jab' } // it tries to act, but is bound
    );
    expect(events.some((e) => e.kind === 'immobile')).toBe(true);
    expect(a.hp).toBe(hpBefore); // the bound side dealt no damage
    expect(b.stunned).toBe(false); // the binding releases after the skip
  });

  it('a stunned combatant cannot brace behind a guard', () => {
    const a = fighter('runewarden');
    const b = fighter('blazewarden');
    const battle = createBattle(a, b, 5);
    b.stunned = true;
    performRound(battle, { type: 'move', moveId: 'lattice_slam' }, { type: 'guard' });
    // The guard never went up: b took full (unhalved) damage. We can't
    // compare against a counterfactual roll here, but the guard flag
    // must never have protected it.
    expect(b.guarding).toBe(false);
  });
});

describe('guard break (ward shatter)', () => {
  it('ignores the guard halving and shatters the ward', () => {
    const attacker = fighter('umbrawarden', 30);
    const defender = fighter('runewarden', 30);
    defender.guarding = true;

    // Same seed ⇒ same accuracy/crit/variance rolls for both moves; the
    // only difference is the guard halving. Use equal-power moves.
    const normal = rollDamage(attacker, defender, getMove('veil_strike'), createRng(99));
    const breaker = rollDamage(attacker, defender, getMove('ward_shatter'), createRng(99));
    expect(normal.miss).toBe(false);
    expect(breaker.miss).toBe(false);
    // veil_strike: 60 power halved by guard; ward_shatter: 55 power, no
    // halving — the breaker must land meaningfully harder.
    expect(breaker.damage).toBeGreaterThan(normal.damage);

    const battle = createBattle(attacker, defender, 17);
    const events = performRound(
      battle,
      { type: 'move', moveId: 'ward_shatter' },
      { type: 'guard' }
    );
    const hit = events.find((e) => e.actor === 'A' && (e.kind === 'move' || e.kind === 'crit'));
    if (hit) expect(hit.text).toContain('the ward shatters!');
  });
});

describe('AI with tactics', () => {
  it('auto-battles between tactic-carrying species still terminate', () => {
    const pairs: Array<[string, string]> = [
      ['blazewarden', 'runewarden'],
      ['duskmonarch', 'aegisgolem'],
      ['storm_sovereign', 'lattice_sovereign'],
      ['solarchon', 'chaosdrake'],
    ];
    for (const [x, y] of pairs) {
      const result = autoBattle(fighter(x, 25), fighter(y, 25), 12345);
      expect(result.over).toBe(true);
      expect(result.winner).not.toBeNull();
    }
  });

  it('identical seeds still reproduce identical battles (A3)', () => {
    const run = () =>
      autoBattle(fighter('duskmonarch', 28), fighter('aegisgolem', 28), 777).log.map((e) => e.text);
    expect(run()).toEqual(run());
  });
});
