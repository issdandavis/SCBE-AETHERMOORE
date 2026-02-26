/**
 * @file skillTree.ts
 * @module game/skillTree
 * @layer Layer 3, Layer 12
 * @component Player Skill Tree — 6 Paths (One Per Tongue)
 *
 * Player is NOT a passive trainer. Player is a hybrid fighter/mage/commander.
 * Multi-path allowed: distribute points across all 6 paths.
 */

import { SkillNode, SkillPath, SkillEffect, TongueCode, TONGUE_TO_PATH } from './types.js';

// ---------------------------------------------------------------------------
//  Skill Definitions
// ---------------------------------------------------------------------------

const ALL_SKILLS: SkillNode[] = [
  // =========== COMMAND PATH (KO) ===========
  {
    id: 'cmd_initiative',
    path: 'command',
    name: 'First Strike',
    description: 'Always act first in formation battles.',
    tier: 1,
    cost: 1,
    prerequisites: [],
    effect: { type: 'stat_bonus', target: 'initiative', value: 10 },
  },
  {
    id: 'cmd_swap',
    path: 'command',
    name: 'Formation Swap',
    description: 'Change formation mid-turn without penalty.',
    tier: 2,
    cost: 2,
    prerequisites: ['cmd_initiative'],
    effect: { type: 'ability_unlock', target: 'formation_swap', value: 1 },
  },
  {
    id: 'cmd_rally',
    path: 'command',
    name: 'Rally Cry',
    description: 'Boost all companion speed by 15% for 3 turns.',
    tier: 3,
    cost: 3,
    prerequisites: ['cmd_swap'],
    effect: { type: 'ability_unlock', target: 'rally_cry', value: 1 },
  },
  {
    id: 'cmd_sovereign',
    path: 'command',
    name: 'Sovereign Command',
    description: 'Companions act twice per turn (once per battle).',
    tier: 4,
    cost: 5,
    prerequisites: ['cmd_rally'],
    effect: { type: 'ability_unlock', target: 'sovereign_command', value: 1 },
  },

  // =========== COMPUTE PATH (CA) ===========
  {
    id: 'cmp_analysis',
    path: 'compute',
    name: 'Analysis Pulse',
    description: 'Reveal one hidden constraint on a problem.',
    tier: 1,
    cost: 1,
    prerequisites: [],
    effect: { type: 'ability_unlock', target: 'analysis_pulse', value: 1 },
  },
  {
    id: 'cmp_cooldown',
    path: 'compute',
    name: 'Cooldown Reduction',
    description: 'All transform cooldowns reduced by 20%.',
    tier: 2,
    cost: 2,
    prerequisites: ['cmp_analysis'],
    effect: { type: 'stat_bonus', target: 'cooldown_reduction', value: 20 },
  },
  {
    id: 'cmp_chain',
    path: 'compute',
    name: 'Combo Chain',
    description: 'Consecutive correct transforms deal +10% each.',
    tier: 3,
    cost: 3,
    prerequisites: ['cmp_cooldown'],
    effect: { type: 'passive', target: 'combo_chain', value: 10 },
  },
  {
    id: 'cmp_encrypt',
    path: 'compute',
    name: 'Encryption Shield',
    description: 'Problems cannot mutate while this is active.',
    tier: 4,
    cost: 5,
    prerequisites: ['cmp_chain'],
    effect: { type: 'ability_unlock', target: 'encryption_shield', value: 1 },
  },

  // =========== ENTROPY PATH (RU) ===========
  {
    id: 'ent_gamble',
    path: 'entropy',
    name: 'Entropy Gamble',
    description: '+50% reward or -50% reward. Coin flip.',
    tier: 1,
    cost: 1,
    prerequisites: [],
    effect: { type: 'ability_unlock', target: 'entropy_gamble', value: 1 },
  },
  {
    id: 'ent_chaos',
    path: 'entropy',
    name: 'Chaos Bolt',
    description: 'Deal damage based on accumulated drift.',
    tier: 2,
    cost: 2,
    prerequisites: ['ent_gamble'],
    effect: { type: 'ability_unlock', target: 'chaos_bolt', value: 1 },
  },
  {
    id: 'ent_corrupt',
    path: 'entropy',
    name: 'Corruption Harness',
    description: 'Convert 50% of trap damage into energy.',
    tier: 3,
    cost: 3,
    prerequisites: ['ent_chaos'],
    effect: { type: 'passive', target: 'corruption_harness', value: 50 },
  },
  {
    id: 'ent_void',
    path: 'entropy',
    name: 'Void Burst',
    description: 'Sacrifice 30% seal integrity for massive AoE damage.',
    tier: 4,
    cost: 5,
    prerequisites: ['ent_corrupt'],
    effect: { type: 'ability_unlock', target: 'void_burst', value: 1 },
  },

  // =========== STRUCTURE PATH (DR) ===========
  {
    id: 'str_guard',
    path: 'structure',
    name: 'Guard Counter',
    description: 'After blocking, next attack deals +30% damage.',
    tier: 1,
    cost: 1,
    prerequisites: [],
    effect: { type: 'passive', target: 'guard_counter', value: 30 },
  },
  {
    id: 'str_terrain',
    path: 'structure',
    name: 'Terrain Wall',
    description: 'Place a barrier that blocks 2 attacks.',
    tier: 2,
    cost: 2,
    prerequisites: ['str_guard'],
    effect: { type: 'ability_unlock', target: 'terrain_wall', value: 1 },
  },
  {
    id: 'str_verify',
    path: 'structure',
    name: 'Verification Shield',
    description: 'Auto-verify one transform per encounter (no cost).',
    tier: 3,
    cost: 3,
    prerequisites: ['str_terrain'],
    effect: { type: 'passive', target: 'auto_verify', value: 1 },
  },
  {
    id: 'str_fort',
    path: 'structure',
    name: 'Fractal Fortress',
    description: 'All companions gain +40% defense for 3 turns.',
    tier: 4,
    cost: 5,
    prerequisites: ['str_verify'],
    effect: { type: 'ability_unlock', target: 'fractal_fortress', value: 1 },
  },

  // =========== TRANSPORT PATH (AV) ===========
  {
    id: 'trn_dash',
    path: 'transport',
    name: 'Phase Dash',
    description: 'Instant reposition. Invulnerable during dash.',
    tier: 1,
    cost: 1,
    prerequisites: [],
    effect: { type: 'ability_unlock', target: 'phase_dash', value: 1 },
  },
  {
    id: 'trn_blink',
    path: 'transport',
    name: 'Blink',
    description: 'Teleport to any visible tile (10 tile range).',
    tier: 2,
    cost: 2,
    prerequisites: ['trn_dash'],
    effect: { type: 'ability_unlock', target: 'blink', value: 10 },
  },
  {
    id: 'trn_reposition',
    path: 'transport',
    name: 'Party Reposition',
    description: 'Move all companions to adjacent tiles.',
    tier: 3,
    cost: 3,
    prerequisites: ['trn_blink'],
    effect: { type: 'ability_unlock', target: 'party_reposition', value: 1 },
  },
  {
    id: 'trn_escape',
    path: 'transport',
    name: 'Rift Escape',
    description: 'Instantly exit any dungeon (no penalty).',
    tier: 4,
    cost: 5,
    prerequisites: ['trn_reposition'],
    effect: { type: 'ability_unlock', target: 'rift_escape', value: 1 },
  },

  // =========== SECURITY PATH (UM) ===========
  {
    id: 'sec_reflect',
    path: 'security',
    name: 'Reflect Barrier',
    description: 'Reflect 20% of incoming damage back.',
    tier: 1,
    cost: 1,
    prerequisites: [],
    effect: { type: 'passive', target: 'reflect', value: 20 },
  },
  {
    id: 'sec_cleanse',
    path: 'security',
    name: 'Cleanse Drift',
    description: 'Remove all drift from one companion.',
    tier: 2,
    cost: 2,
    prerequisites: ['sec_reflect'],
    effect: { type: 'ability_unlock', target: 'cleanse_drift', value: 1 },
  },
  {
    id: 'sec_heal',
    path: 'security',
    name: 'Seal Mend',
    description: 'Restore 30% seal integrity to one companion.',
    tier: 3,
    cost: 3,
    prerequisites: ['sec_cleanse'],
    effect: { type: 'ability_unlock', target: 'seal_mend', value: 30 },
  },
  {
    id: 'sec_ward',
    path: 'security',
    name: 'Ward Sanctum',
    description: 'Create a zone where corruption cannot spread.',
    tier: 4,
    cost: 5,
    prerequisites: ['sec_heal'],
    effect: { type: 'ability_unlock', target: 'ward_sanctum', value: 1 },
  },
];

// ---------------------------------------------------------------------------
//  Player Skill State
// ---------------------------------------------------------------------------

export interface PlayerSkillState {
  /** Available skill points */
  availablePoints: number;

  /** Unlocked skill IDs */
  unlockedSkills: Set<string>;

  /** Points invested per path */
  pathPoints: Record<SkillPath, number>;
}

/** Create initial skill state */
export function createSkillState(): PlayerSkillState {
  return {
    availablePoints: 0,
    unlockedSkills: new Set(),
    pathPoints: {
      command: 0,
      compute: 0,
      entropy: 0,
      structure: 0,
      transport: 0,
      security: 0,
    },
  };
}

// ---------------------------------------------------------------------------
//  Public API
// ---------------------------------------------------------------------------

/**
 * Get all skills for a given path.
 */
export function getSkillsForPath(path: SkillPath): SkillNode[] {
  return ALL_SKILLS.filter((s) => s.path === path);
}

/**
 * Get a skill by ID.
 */
export function getSkill(id: string): SkillNode | undefined {
  return ALL_SKILLS.find((s) => s.id === id);
}

/**
 * Check if a skill can be unlocked.
 */
export function canUnlockSkill(state: PlayerSkillState, skillId: string): boolean {
  const skill = getSkill(skillId);
  if (!skill) return false;
  if (state.unlockedSkills.has(skillId)) return false;
  if (state.availablePoints < skill.cost) return false;

  // Check prerequisites
  for (const prereq of skill.prerequisites) {
    if (!state.unlockedSkills.has(prereq)) return false;
  }

  return true;
}

/**
 * Unlock a skill. Mutates state in place.
 * Returns true if successful.
 */
export function unlockSkill(state: PlayerSkillState, skillId: string): boolean {
  if (!canUnlockSkill(state, skillId)) return false;

  const skill = getSkill(skillId)!;
  state.availablePoints -= skill.cost;
  state.unlockedSkills.add(skillId);
  state.pathPoints[skill.path] += skill.cost;

  return true;
}

/**
 * Check if a "harmony" ability is available.
 * Harmony abilities unlock when both tongues of a Hodge dual pair
 * have at least 3 points invested.
 */
export function getHarmonyAbilities(state: PlayerSkillState): string[] {
  const harmonies: string[] = [];

  if (state.pathPoints.command >= 3 && state.pathPoints.structure >= 3) {
    harmonies.push('ko_dr_harmony'); // Command + Structure
  }
  if (state.pathPoints.transport >= 3 && state.pathPoints.security >= 3) {
    harmonies.push('av_um_harmony'); // Transport + Security
  }
  if (state.pathPoints.entropy >= 3 && state.pathPoints.compute >= 3) {
    harmonies.push('ru_ca_harmony'); // Entropy + Compute
  }

  return harmonies;
}

/**
 * Get the total number of skills.
 */
export function totalSkillCount(): number {
  return ALL_SKILLS.length;
}

/**
 * Get all skills (for codex/UI).
 */
export function getAllSkills(): readonly SkillNode[] {
  return ALL_SKILLS;
}
