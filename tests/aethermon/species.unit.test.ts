/**
 * @file species.unit.test.ts
 * @module tests/aethermon
 * @component AETHERMON — Species Catalog Integrity (L2-unit)
 *
 * The evolution graph must be sound: every edge resolves, stages only
 * step forward, every species always has a way to evolve (fallback), and
 * every line can be walked from egg to APEX.
 */

import { describe, expect, it } from 'vitest';
import {
  MOVES,
  SPECIES,
  STAGE_MIN_LEVEL,
  STAGE_ORDER,
  STARTER_EGG_IDS,
  allSpecies,
  getSpecies,
  speciesByStage,
  stageIndex,
} from '../../src/aethermon/index.js';

describe('species catalog integrity', () => {
  it('has unique ids matching map keys', () => {
    const ids = allSpecies().map((s) => s.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const id of ids) expect(SPECIES.get(id)?.id).toBe(id);
  });

  it('covers all six stages', () => {
    for (const stage of STAGE_ORDER) {
      expect(speciesByStage(stage).length).toBeGreaterThan(0);
    }
  });

  it('every evolution edge targets an existing species exactly one stage up', () => {
    for (const species of allSpecies()) {
      for (const edge of species.evolvesTo) {
        const target = getSpecies(edge.targetId);
        expect(stageIndex(target.stage)).toBe(stageIndex(species.stage) + 1);
      }
    }
  });

  it('evolution minLevel matches the target stage minimum', () => {
    for (const species of allSpecies()) {
      for (const edge of species.evolvesTo) {
        const target = getSpecies(edge.targetId);
        expect(edge.minLevel).toBe(STAGE_MIN_LEVEL[target.stage]);
      }
    }
  });

  it('every non-terminal species has exactly one fallback edge', () => {
    for (const species of allSpecies()) {
      if (species.evolvesTo.length === 0) {
        expect(species.stage).toBe('APEX');
        continue;
      }
      const fallbacks = species.evolvesTo.filter((e) => e.fallback);
      expect(fallbacks, species.id).toHaveLength(1);
    }
  });

  it('all APEX species are terminal', () => {
    for (const species of speciesByStage('APEX')) {
      expect(species.evolvesTo).toHaveLength(0);
    }
  });

  it('all species moves exist; non-eggs carry 1–4 moves, eggs none', () => {
    for (const species of allSpecies()) {
      for (const moveId of species.moves) {
        expect(MOVES.has(moveId), `${species.id} → ${moveId}`).toBe(true);
      }
      if (species.stage === 'EGG') {
        expect(species.moves).toHaveLength(0);
      } else {
        expect(species.moves.length).toBeGreaterThanOrEqual(1);
        expect(species.moves.length).toBeLessThanOrEqual(4);
      }
    }
  });

  it('every non-egg species is reachable from a starter egg', () => {
    const reachable = new Set<string>(STARTER_EGG_IDS);
    const queue = [...STARTER_EGG_IDS];
    while (queue.length > 0) {
      const id = queue.shift()!;
      for (const edge of getSpecies(id).evolvesTo) {
        if (!reachable.has(edge.targetId)) {
          reachable.add(edge.targetId);
          queue.push(edge.targetId);
        }
      }
    }
    for (const species of allSpecies()) {
      expect(reachable.has(species.id), species.id).toBe(true);
    }
  });

  it('every starter egg line can reach an APEX', () => {
    for (const eggId of STARTER_EGG_IDS) {
      const seen = new Set<string>([eggId]);
      const queue = [eggId];
      let reachesApex = false;
      while (queue.length > 0) {
        const species = getSpecies(queue.shift()!);
        if (species.stage === 'APEX') reachesApex = true;
        for (const edge of species.evolvesTo) {
          if (!seen.has(edge.targetId)) {
            seen.add(edge.targetId);
            queue.push(edge.targetId);
          }
        }
      }
      expect(reachesApex, eggId).toBe(true);
    }
  });

  it('base stats and growth rise with stage along every edge', () => {
    for (const species of allSpecies()) {
      if (species.stage === 'EGG') continue;
      for (const edge of species.evolvesTo) {
        const target = getSpecies(edge.targetId);
        expect(target.baseStats.hp).toBeGreaterThan(species.baseStats.hp);
        expect(target.growth).toBeGreaterThanOrEqual(species.growth);
      }
    }
  });

  it('getSpecies throws on unknown id', () => {
    expect(() => getSpecies('missingno')).toThrow(RangeError);
  });
});
