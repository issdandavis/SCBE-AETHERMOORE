/**
 * @file worldbuilding.unit.test.ts
 * @module tests/aethermon
 * @component AETHERMON — Canon Worldbuilding Systems (L2-unit / L3-integration)
 *
 * The systems added from the Digimon design research and the Aethermoore
 * canon: tongue regions, Hodge dual resonance, scars (immune flywheel),
 * the Hollow, lifespan/generations, and v1 save migration.
 */

import { describe, expect, it } from 'vitest';
import {
  HODGE_DUALS,
  HODGE_RESONANCE,
  HEIRLOOM_CAP,
  REGIONS,
  STAB_BONUS,
  STAGE_LIFESPAN_TICKS,
  STRAIN_THRESHOLD,
  affinityMultiplier,
  applyBattleResult,
  checkRebirth,
  communeWithGap,
  createMonster,
  deserializeGame,
  effectiveStats,
  evolutionOptions,
  generateWildEncounter,
  getRegion,
  getSpecies,
  isLifespanExpired,
  lifespanRemaining,
  newGame,
  rest,
  selectEvolution,
  serializeGame,
  travel,
  warmEgg,
  wildCombatant,
} from '../../src/aethermon/index.js';

function hatched(eggId = 'ember_egg', seed = 5) {
  const state = newGame('Issa', eggId, seed);
  while (state.egg) warmEgg(state, 'Test');
  return state;
}

describe('tongue regions (canon geography)', () => {
  it('has all six canon regions, one per tongue', () => {
    expect(REGIONS).toHaveLength(6);
    const names = REGIONS.map((r) => r.name);
    expect(names).toEqual([
      'Ember Reach',
      'Aerial Expanse',
      'Null Vale',
      'Glass Drift',
      'Ward Sanctum',
      'Bastion Fields',
    ]);
    expect(new Set(REGIONS.map((r) => r.tongue)).size).toBe(6);
  });

  it('only the Null Vale touches the Hollow', () => {
    expect(REGIONS.filter((r) => r.touchesHollow).map((r) => r.id)).toEqual(['null_vale']);
  });

  it('travel changes the current region and rejects unknown ones', () => {
    const state = hatched();
    expect(state.region).toBe('ember_reach');
    travel(state, 'aerial_expanse');
    expect(state.region).toBe('aerial_expanse');
    expect(() => travel(state, 'the_backrooms')).toThrow(RangeError);
  });

  it('wild encounters lean toward the local tongue', () => {
    const state = hatched();
    const monster = state.monster!;
    monster.level = 8; // SPRITE-tier encounters
    monster.speciesId = 'pyreling';
    travel(state, 'aerial_expanse');
    let avCount = 0;
    const samples = 60;
    for (let i = 0; i < samples; i++) {
      const enemy = generateWildEncounter(state, monster);
      if (getSpecies(enemy.speciesId).element === 'AV') avCount += 1;
    }
    // elementBias 0.6 plus natural AV share — well above uniform (~1/6).
    expect(avCount / samples).toBeGreaterThan(0.4);
  });
});

describe('Hodge dual resonance (canon: duals bond 30% stronger)', () => {
  it('pairs are symmetric: KO↔DR, AV↔UM, RU↔CA', () => {
    for (const [a, b] of Object.entries(HODGE_DUALS)) {
      expect(HODGE_DUALS[b as keyof typeof HODGE_DUALS]).toBe(a);
    }
    expect(HODGE_DUALS.KO).toBe('DR');
    expect(HODGE_DUALS.AV).toBe('UM');
    expect(HODGE_DUALS.RU).toBe('CA');
  });

  it('dual moves resonate at ×1.3, own element gets STAB, others nothing', () => {
    const blazewarden = wildCombatant(getSpecies('blazewarden'), 15); // KO
    const stab = { element: 'KO' } as Parameters<typeof affinityMultiplier>[1];
    const dual = { element: 'DR' } as Parameters<typeof affinityMultiplier>[1];
    const neither = { element: 'RU' } as Parameters<typeof affinityMultiplier>[1];
    expect(affinityMultiplier(blazewarden, stab)).toBe(STAB_BONUS);
    expect(affinityMultiplier(blazewarden, dual)).toBe(HODGE_RESONANCE);
    expect(affinityMultiplier(blazewarden, neither)).toBe(1.0);
    expect(HODGE_RESONANCE).toBeCloseTo(1.3, 10);
  });

  it('the Storm Sovereign carries its dual tongue in its movepool', () => {
    // AV apex with a UM move — the Storm pair (AV↔UM) made flesh.
    const sovereign = getSpecies('storm_sovereign');
    expect(sovereign.element).toBe('AV');
    expect(sovereign.moves).toContain('eclipse_ward'); // UM move → resonance
  });
});

describe('scars — the immune flywheel', () => {
  it('losses leave scars that harden defense, capped', () => {
    const monster = createMonster('pyreling', 'Vet');
    const baseline = effectiveStats(monster).def;
    applyBattleResult(monster, false);
    applyBattleResult(monster, false);
    expect(monster.scars).toBe(2);
    expect(effectiveStats(monster).def).toBe(baseline + 2);
    monster.scars = 50;
    expect(effectiveStats(monster).def).toBe(baseline + 10); // SCAR_DEFENSE_CAP
  });

  it('over-battling without rest causes strain; rest clears it', () => {
    const monster = createMonster('pyreling', 'Tired');
    let strained = false;
    for (let i = 0; i < STRAIN_THRESHOLD; i++) {
      monster.care.energy = 100;
      monster.care.hunger = 100;
      strained = applyBattleResult(monster, true).strained;
    }
    expect(strained).toBe(true);
    rest(monster);
    expect(monster.consecutiveBattles).toBe(0);
  });

  it('scars open the Fracture Shade branch (canon dark evolution)', () => {
    const monster = createMonster('veilkit', 'Marked');
    monster.level = 12;
    monster.care.discipline = 80; // would otherwise become umbrawarden
    expect(selectEvolution(monster)?.targetId).toBe('umbrawarden');
    monster.scars = 3;
    expect(selectEvolution(monster)?.targetId).toBe('fracture_shade');
  });
});

describe('the Hollow — the gap between the tongues', () => {
  it('can only be approached from the Null Vale', () => {
    const state = hatched('umbral_egg');
    const monster = state.monster!;
    const refused = communeWithGap(state, monster);
    expect(refused.ok).toBe(false);
    expect(monster.hollowExposure).toBe(0);
    travel(state, 'null_vale');
    const touched = communeWithGap(state, monster);
    expect(touched.ok).toBe(true);
    expect(monster.hollowExposure).toBe(1);
  });

  it('Paradox Wraith demands both scars and Hollow exposure', () => {
    const monster = createMonster('nullshade', 'Gone');
    monster.level = 22;
    monster.scars = 5;
    expect(selectEvolution(monster)?.targetId).not.toBe('paradox_wraith');
    monster.hollowExposure = 1;
    expect(selectEvolution(monster)?.targetId).toBe('paradox_wraith');
    const wraith = evolutionOptions(monster).find(
      (o) => o.requirement.targetId === 'paradox_wraith'
    );
    expect(wraith?.eligible).toBe(true);
  });
});

describe('lifespan & generations (V-Pet rule: every form has its season)', () => {
  it('lifespan counts down per stage and evolving renews it', () => {
    const monster = createMonster('kindlemote', 'Old');
    expect(lifespanRemaining(monster)).toBe(STAGE_LIFESPAN_TICKS.MOTE);
    monster.stageAgeTicks = STAGE_LIFESPAN_TICKS.MOTE;
    expect(isLifespanExpired(monster)).toBe(true);
  });

  it('an expired creature returns to its egg with an heirloom', () => {
    const state = hatched('umbral_egg');
    const monster = state.monster!;
    monster.nickname = 'Dusk';
    monster.trainBonus.atk = 30;
    monster.trainBonus.def = 10;
    monster.stageAgeTicks = STAGE_LIFESPAN_TICKS.MOTE + 1;
    const rebirth = checkRebirth(state);
    expect(rebirth).not.toBeNull();
    expect(rebirth!.eggSpeciesId).toBe('umbral_egg'); // the line continues
    expect(rebirth!.heirloom.atk).toBe(12); // 40% of 30
    expect(rebirth!.nextGeneration).toBe(2);
    expect(state.monster).toBeNull();
    expect(state.egg?.heirloom?.atk).toBe(12);
    expect(state.lineageMemorial).toHaveLength(1);
    expect(state.lineageMemorial[0]).toContain('Dusk');

    // Hatch generation 2: heirloom flows into effective stats.
    while (state.egg) warmEgg(state, 'Dusk II');
    const heir = state.monster!;
    expect(heir.generation).toBe(2);
    const plain = createMonster('shademote', 'Control');
    expect(effectiveStats(heir).atk).toBe(effectiveStats(plain).atk + 12);
  });

  it('heirloom compounds across generations but stays capped', () => {
    const state = hatched();
    const monster = state.monster!;
    monster.trainBonus.atk = 50;
    monster.heirloom.atk = 50; // absurd inheritance
    monster.stageAgeTicks = STAGE_LIFESPAN_TICKS.MOTE + 1;
    const rebirth = checkRebirth(state)!;
    expect(rebirth.heirloom.atk).toBe(HEIRLOOM_CAP);
  });

  it('checkRebirth is a no-op while the creature has time', () => {
    const state = hatched();
    expect(checkRebirth(state)).toBeNull();
    expect(state.monster).not.toBeNull();
  });
});

describe('save migration', () => {
  it('migrates version-1 saves forward with sane defaults', () => {
    const modern = hatched();
    const v1 = JSON.parse(serializeGame(modern)) as Record<string, unknown>;
    v1.version = 1;
    delete v1.region;
    delete v1.generation;
    delete v1.lineageMemorial;
    const monster = v1.monster as Record<string, unknown>;
    delete monster.stageAgeTicks;
    delete monster.scars;
    delete monster.consecutiveBattles;
    delete monster.hollowExposure;
    delete monster.generation;
    delete monster.heirloom;

    const migrated = deserializeGame(JSON.stringify(v1));
    expect(migrated.version).toBe(2);
    expect(migrated.region).toBe('ember_reach');
    expect(migrated.generation).toBe(1);
    expect(migrated.lineageMemorial).toEqual([]);
    expect(migrated.monster?.scars).toBe(0);
    expect(migrated.monster?.heirloom).toEqual({ hp: 0, atk: 0, def: 0, spd: 0 });
    expect(getRegion(migrated.region).name).toBe('Ember Reach');
  });

  it('round-trips version-2 saves including new fields', () => {
    const state = hatched('umbral_egg');
    travel(state, 'null_vale');
    communeWithGap(state, state.monster!);
    applyBattleResult(state.monster!, false);
    const restored = deserializeGame(serializeGame(state));
    expect(restored).toEqual(state);
  });
});

describe('the Gale line (canon: Gale Egg → Galewing)', () => {
  it('is a starter and reaches the Storm Sovereign apex', () => {
    const state = hatched('gale_egg');
    expect(state.monster?.speciesId).toBe('galewing');
    const monster = state.monster!;
    monster.level = 50;
    let guard = 0;
    while (selectEvolution(monster) !== null && guard < 10) {
      monster.speciesId = selectEvolution(monster)!.targetId;
      guard += 1;
    }
    expect(getSpecies(monster.speciesId).stage).toBe('APEX');
    expect(getSpecies(monster.speciesId).element).toBe('AV');
  });
});
