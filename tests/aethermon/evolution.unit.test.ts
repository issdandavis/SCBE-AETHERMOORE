/**
 * @file evolution.unit.test.ts
 * @module tests/aethermon
 * @component AETHERMON — Branching Evolution (L2-unit)
 *
 * How you raise the creature decides the branch: good care vs neglect,
 * training focus, bond and discipline thresholds, and the fallback
 * guarantee that nothing ever gets stuck.
 */

import { describe, expect, it } from 'vitest';
import {
  createMonster,
  evolutionOptions,
  evolve,
  getSpecies,
  selectEvolution,
} from '../../src/aethermon/index.js';

describe('evolution gating', () => {
  it('cannot evolve below the stage minimum level', () => {
    const monster = createMonster('kindlemote', 'Cinder');
    monster.level = 4;
    expect(selectEvolution(monster)).toBeNull();
    monster.level = 5;
    expect(selectEvolution(monster)).not.toBeNull();
  });

  it('APEX creatures are terminal', () => {
    const monster = createMonster('radiant_sovereign', 'Sol');
    monster.level = 50;
    expect(selectEvolution(monster)).toBeNull();
    expect(evolve(monster)).toBeNull();
  });
});

describe('care-driven branching (kindlemote)', () => {
  it('well-raised kindlemote becomes pyreling', () => {
    const monster = createMonster('kindlemote', 'Cinder');
    monster.level = 5;
    monster.care.careMistakes = 0;
    expect(selectEvolution(monster)?.targetId).toBe('pyreling');
  });

  it('neglected kindlemote falls back to gnashling', () => {
    const monster = createMonster('kindlemote', 'Cinder');
    monster.level = 5;
    monster.care.careMistakes = 3;
    expect(selectEvolution(monster)?.targetId).toBe('gnashling');
  });
});

describe('training-driven branching (gnashling)', () => {
  it('ATK-focused training unlocks vexmaw', () => {
    const monster = createMonster('gnashling', 'Gnash');
    monster.level = 12;
    monster.trainBonus.atk = 15;
    expect(selectEvolution(monster)?.targetId).toBe('vexmaw');
  });

  it('without focus it falls back to ashrevenant', () => {
    const monster = createMonster('gnashling', 'Gnash');
    monster.level = 12;
    expect(selectEvolution(monster)?.targetId).toBe('ashrevenant');
  });
});

describe('stat-threshold branching (shademote → veilkit)', () => {
  it('requires bond and good care', () => {
    const monster = createMonster('shademote', 'Shade');
    monster.level = 5;
    monster.care.bond = 30;
    monster.care.careMistakes = 1;
    expect(selectEvolution(monster)?.targetId).toBe('veilkit');
    monster.care.bond = 5;
    expect(selectEvolution(monster)?.targetId).toBe('gloomkit');
  });

  it('explains blockers in evolution options', () => {
    const monster = createMonster('shademote', 'Shade');
    monster.level = 5;
    monster.care.bond = 0;
    const veilkit = evolutionOptions(monster).find((o) => o.requirement.targetId === 'veilkit');
    expect(veilkit?.eligible).toBe(false);
    expect(veilkit?.blockedBy.join(' ')).toContain('bond');
  });
});

describe('evolve()', () => {
  it('changes species, records lineage and refreshes meters', () => {
    const monster = createMonster('kindlemote', 'Cinder');
    monster.level = 5;
    monster.care.hunger = 20;
    monster.care.energy = 15;
    const result = evolve(monster);
    expect(result?.fromSpeciesId).toBe('kindlemote');
    expect(result?.toSpeciesId).toBe('pyreling');
    expect(monster.speciesId).toBe('pyreling');
    expect(monster.lineage).toEqual(['kindlemote', 'pyreling']);
    expect(monster.care.hunger).toBe(100);
    expect(monster.care.energy).toBe(100);
  });

  it('fallback chain always reaches APEX at max level', () => {
    const monster = createMonster('kindlemote', 'Cinder');
    monster.level = 50;
    let steps = 0;
    while (evolve(monster) !== null) {
      steps += 1;
      expect(steps).toBeLessThanOrEqual(10);
    }
    expect(getSpecies(monster.speciesId).stage).toBe('APEX');
    expect(monster.lineage).toHaveLength(steps + 1);
  });
});
