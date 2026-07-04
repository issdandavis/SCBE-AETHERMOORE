/**
 * @file evolution.ts
 * @module aethermon/evolution
 * @layer Layer 5, Layer 13
 * @component AETHERMON — Branching Evolution Engine
 *
 * Decides which evolution edge a creature takes. Requirements on an edge
 * are AND-combined; among all satisfied edges the highest priority wins
 * (catalog order breaks ties). The `fallback` edge only requires the
 * minimum level, so any creature that reaches the level can always
 * evolve — how it was raised decides *into what*.
 *
 * A3: Causality — the outcome is a pure function of the creature's
 * recorded history (no randomness).
 */

import type { EvolutionRequirement, MonsterState } from './types.js';
import { IDEAL_WEIGHT } from './types.js';
import { getSpecies } from './species.js';
import { dominantTrainedStat, effectiveStats } from './monster.js';

/** Why an edge is or isn't available, for UI display. */
export interface EvolutionOption {
  readonly requirement: EvolutionRequirement;
  readonly eligible: boolean;
  readonly blockedBy: string[];
}

/** Evaluate a single evolution edge against a creature's history. */
export function evaluateRequirement(
  monster: MonsterState,
  req: EvolutionRequirement
): EvolutionOption {
  const blockedBy: string[] = [];
  if (monster.level < req.minLevel) blockedBy.push(`needs level ${req.minLevel}`);

  if (!req.fallback) {
    const care = monster.care;
    if (req.maxCareMistakes !== undefined && care.careMistakes > req.maxCareMistakes) {
      blockedBy.push(`too many care mistakes (max ${req.maxCareMistakes})`);
    }
    if (req.minCareMistakes !== undefined && care.careMistakes < req.minCareMistakes) {
      blockedBy.push(`needs ${req.minCareMistakes}+ care mistakes`);
    }
    if (req.minBond !== undefined && care.bond < req.minBond) {
      blockedBy.push(`needs bond ${req.minBond}+`);
    }
    if (req.minDiscipline !== undefined && care.discipline < req.minDiscipline) {
      blockedBy.push(`needs discipline ${req.minDiscipline}+`);
    }
    if (req.minBattlesWon !== undefined && monster.battlesWon < req.minBattlesWon) {
      blockedBy.push(`needs ${req.minBattlesWon}+ battle wins`);
    }
    if (req.dominantStat !== undefined && dominantTrainedStat(monster) !== req.dominantStat) {
      blockedBy.push(`needs ${req.dominantStat.toUpperCase()}-focused training`);
    }
    if (req.minScars !== undefined && monster.scars < req.minScars) {
      blockedBy.push(`needs ${req.minScars}+ battle scars`);
    }
    if (req.minHollowExposure !== undefined && monster.hollowExposure < req.minHollowExposure) {
      blockedBy.push(`needs to touch the Hollow (Null Vale)`);
    }
  }

  return { requirement: req, eligible: blockedBy.length === 0, blockedBy };
}

/** All evolution options for a creature, eligible or not. */
export function evolutionOptions(monster: MonsterState): EvolutionOption[] {
  const species = getSpecies(monster.speciesId);
  return species.evolvesTo.map((req) => evaluateRequirement(monster, req));
}

/**
 * The edge the creature would take right now, or null if it cannot
 * evolve yet (level too low) or is terminal (APEX).
 */
export function selectEvolution(monster: MonsterState): EvolutionRequirement | null {
  const eligible = evolutionOptions(monster).filter((o) => o.eligible);
  if (eligible.length === 0) return null;
  eligible.sort((x, y) => y.requirement.priority - x.requirement.priority);
  return eligible[0].requirement;
}

/** Result of an evolution, for the UI. */
export interface EvolutionResult {
  readonly fromSpeciesId: string;
  readonly toSpeciesId: string;
  readonly fromName: string;
  readonly toName: string;
}

/**
 * Evolve the creature along its selected edge. Mutates the monster:
 * species changes, care meters refresh, lineage is recorded. Training
 * bonuses, scars and level carry over. The care-mistake counter resets —
 * every stage is a fresh test — and the new form's lifespan begins.
 * Returns null if no edge is eligible.
 */
export function evolve(monster: MonsterState): EvolutionResult | null {
  const edge = selectEvolution(monster);
  if (!edge) return null;
  const from = getSpecies(monster.speciesId);
  const to = getSpecies(edge.targetId);

  monster.speciesId = to.id;
  monster.lineage.push(to.id);
  monster.stageAgeTicks = 0; // new form, new lifespan
  // Evolution is taxing but invigorating: full meters, mood spike.
  monster.care.hunger = 100;
  monster.care.energy = 100;
  monster.care.mood = Math.min(100, monster.care.mood + 20);
  monster.care.careMistakes = 0; // fresh test for the new form
  monster.care.starving = false;
  monster.care.exhausted = false;
  // The body reformats: weight snaps to the new form's ideal and any
  // static corruption is overwritten. (Residue stays on the floor.)
  monster.weightKb = IDEAL_WEIGHT[to.stage];
  monster.glitched = false;

  return { fromSpeciesId: from.id, toSpeciesId: to.id, fromName: from.name, toName: to.name };
}

/**
 * Highest possible HP at the creature's current form — convenience for
 * battle setup and UI.
 */
export function maxHp(monster: MonsterState): number {
  return effectiveStats(monster).hp;
}
