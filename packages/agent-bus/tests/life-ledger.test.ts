/**
 * @file life-ledger.test.ts
 * Tests for per-agent life simulation — known/unknown detection,
 * alignment tracking, skills, career, groups, serialization.
 */

import { describe, expect, it } from 'vitest';
import {
  createLifeRecord,
  encounter,
  gainSkillXP,
  startCareer,
  endCareer,
  completeTask,
  joinGroup,
  leaveGroup,
  isKnown,
  getAlignmentScore,
  getKnownAgents,
  summarize,
  serializeLifeRecord,
  deserializeLifeRecord,
  type AgentLifeRecord,
} from '../src/index.js';

// ─── createLifeRecord ─────────────────────────────────────────────────────────

describe('createLifeRecord', () => {
  it('creates a record with empty known_agents', () => {
    const r = createLifeRecord('agent-0');
    expect(Object.keys(r.known_agents)).toHaveLength(0);
  });

  it('sets birth_ts to a recent timestamp', () => {
    const before = Date.now();
    const r = createLifeRecord('agent-0');
    expect(r.birth_ts).toBeGreaterThanOrEqual(before);
  });

  it('stores display_name when provided', () => {
    const r = createLifeRecord('agent-0', 'Polly');
    expect(r.display_name).toBe('Polly');
  });

  it('omits display_name when not provided', () => {
    const r = createLifeRecord('agent-0');
    expect('display_name' in r).toBe(false);
  });

  it('starts with zero encounter counts', () => {
    const r = createLifeRecord('agent-0');
    expect(r.total_encounters).toBe(0);
    expect(r.total_new_encounters).toBe(0);
  });
});

// ─── encounter / known-unknown detection ──────────────────────────────────────

describe('encounter — known/unknown detection', () => {
  it('first encounter is marked is_new=true', () => {
    const r = createLifeRecord('agent-0');
    const result = encounter(r, 'agent-1');
    expect(result.is_new).toBe(true);
  });

  it('second encounter with same agent is is_new=false', () => {
    const r = createLifeRecord('agent-0');
    encounter(r, 'agent-1');
    const result = encounter(r, 'agent-1');
    expect(result.is_new).toBe(false);
  });

  it('total_new_encounters increments only on first encounter', () => {
    const r = createLifeRecord('agent-0');
    encounter(r, 'agent-1');
    encounter(r, 'agent-1');
    encounter(r, 'agent-1');
    expect(r.total_new_encounters).toBe(1);
  });

  it('total_encounters increments on every encounter', () => {
    const r = createLifeRecord('agent-0');
    encounter(r, 'agent-1');
    encounter(r, 'agent-1');
    encounter(r, 'agent-2');
    expect(r.total_encounters).toBe(3);
  });

  it('interaction_count increments on repeat encounters', () => {
    const r = createLifeRecord('agent-0');
    encounter(r, 'agent-1');
    encounter(r, 'agent-1');
    encounter(r, 'agent-1');
    expect(r.known_agents['agent-1']!.interaction_count).toBe(3);
  });

  it('stores display_name on first encounter', () => {
    const r = createLifeRecord('agent-0');
    encounter(r, 'agent-1', undefined, 'Zara');
    expect(r.known_agents['agent-1']!.display_name).toBe('Zara');
  });

  it('updates display_name on repeat encounter', () => {
    const r = createLifeRecord('agent-0');
    encounter(r, 'agent-1', undefined, 'Old Name');
    encounter(r, 'agent-1', undefined, 'New Name');
    expect(r.known_agents['agent-1']!.display_name).toBe('New Name');
  });

  it('multiple different agents tracked independently', () => {
    const r = createLifeRecord('agent-0');
    encounter(r, 'agent-1');
    encounter(r, 'agent-2');
    encounter(r, 'agent-3');
    expect(Object.keys(r.known_agents)).toHaveLength(3);
    expect(r.total_new_encounters).toBe(3);
  });
});

// ─── alignment tracking ───────────────────────────────────────────────────────

describe('alignment tracking', () => {
  it('no alignment score before any encounter', () => {
    const r = createLifeRecord('agent-0');
    expect(getAlignmentScore(r, 'agent-1')).toBeNull();
  });

  it('positive signal produces positive alignment on first encounter', () => {
    const r = createLifeRecord('agent-0');
    const result = encounter(r, 'agent-1', 1.0);
    expect(result.alignment_score).toBeGreaterThan(0);
  });

  it('negative signal produces negative alignment', () => {
    const r = createLifeRecord('agent-0');
    const result = encounter(r, 'agent-1', -1.0);
    expect(result.alignment_score).toBeLessThan(0);
  });

  it('alignment stays in [-1, 1] after many positive signals', () => {
    const r = createLifeRecord('agent-0');
    for (let i = 0; i < 20; i++) encounter(r, 'agent-1', 1.0);
    const score = getAlignmentScore(r, 'agent-1')!;
    expect(score).toBeLessThanOrEqual(1);
    expect(score).toBeGreaterThanOrEqual(-1);
  });

  it('early interactions outweigh later ones (1/sqrt(n) decay)', () => {
    const r1 = createLifeRecord('a');
    const r2 = createLifeRecord('b');
    // r1: moderate positive first, then neutral — stays at ~0.5
    encounter(r1, 'x', 0.5);
    for (let i = 0; i < 10; i++) encounter(r1, 'x', 0.0);
    // r2: neutral first, then small positives — accumulates to ~0.43 (below 0.5)
    encounter(r2, 'x', 0.0);
    for (let i = 0; i < 10; i++) encounter(r2, 'x', 0.1);
    // r1 should have higher alignment: first encounter (1/sqrt(1)=full weight) dominates
    expect(getAlignmentScore(r1, 'x')!).toBeGreaterThan(getAlignmentScore(r2, 'x')!);
  });

  it('alignment_delta is 0 when no signal provided', () => {
    const r = createLifeRecord('agent-0');
    const result = encounter(r, 'agent-1');
    expect(result.alignment_delta).toBe(0);
  });
});

// ─── isKnown ──────────────────────────────────────────────────────────────────

describe('isKnown', () => {
  it('returns false before any encounter', () => {
    const r = createLifeRecord('agent-0');
    expect(isKnown(r, 'agent-1')).toBe(false);
  });

  it('returns true after encounter', () => {
    const r = createLifeRecord('agent-0');
    encounter(r, 'agent-1');
    expect(isKnown(r, 'agent-1')).toBe(true);
  });

  it('does not affect other agents', () => {
    const r = createLifeRecord('agent-0');
    encounter(r, 'agent-1');
    expect(isKnown(r, 'agent-2')).toBe(false);
  });
});

// ─── skills ───────────────────────────────────────────────────────────────────

describe('gainSkillXP', () => {
  it('creates new skill at level 0 with given xp', () => {
    const r = createLifeRecord('agent-0');
    const sk = gainSkillXP(r, 'governance', 50);
    expect(sk.xp).toBe(50);
    expect(sk.level).toBe(0);
  });

  it('level advances at 100 xp intervals', () => {
    const r = createLifeRecord('agent-0');
    gainSkillXP(r, 'navigation', 100);
    expect(r.skills['navigation']!.level).toBe(1);
    gainSkillXP(r, 'navigation', 100);
    expect(r.skills['navigation']!.level).toBe(2);
  });

  it('level soft-caps at 100', () => {
    const r = createLifeRecord('agent-0');
    gainSkillXP(r, 'overdrive', 999_999);
    expect(r.skills['overdrive']!.level).toBe(100);
  });

  it('negative xp reduces xp but not below 0', () => {
    const r = createLifeRecord('agent-0');
    gainSkillXP(r, 'nav', 50);
    gainSkillXP(r, 'nav', -100);
    expect(r.skills['nav']!.xp).toBe(0);
  });

  it('multiple skills tracked independently', () => {
    const r = createLifeRecord('agent-0');
    gainSkillXP(r, 'skill-a', 100);
    gainSkillXP(r, 'skill-b', 200);
    expect(r.skills['skill-a']!.level).toBe(1);
    expect(r.skills['skill-b']!.level).toBe(2);
  });
});

// ─── career ───────────────────────────────────────────────────────────────────

describe('career', () => {
  it('startCareer adds entry with joined_ts', () => {
    const r = createLifeRecord('agent-0');
    const before = Date.now();
    startCareer(r, 'navigator');
    expect(r.career[0]!.role).toBe('navigator');
    expect(r.career[0]!.joined_ts).toBeGreaterThanOrEqual(before);
    expect(r.career[0]!.left_ts).toBeUndefined();
  });

  it('endCareer sets left_ts on matching role', () => {
    const r = createLifeRecord('agent-0');
    startCareer(r, 'navigator');
    const result = endCareer(r, 'navigator');
    expect(result).toBe(true);
    expect(r.career[0]!.left_ts).toBeDefined();
  });

  it('endCareer returns false for nonexistent role', () => {
    const r = createLifeRecord('agent-0');
    expect(endCareer(r, 'ghost-role')).toBe(false);
  });

  it('completeTask increments tasks_completed', () => {
    const r = createLifeRecord('agent-0');
    startCareer(r, 'pilot');
    completeTask(r, 'pilot');
    completeTask(r, 'pilot');
    expect(r.career[0]!.tasks_completed).toBe(2);
  });

  it('completeTask returns false for inactive role', () => {
    const r = createLifeRecord('agent-0');
    expect(completeTask(r, 'ghost-role')).toBe(false);
  });
});

// ─── groups ───────────────────────────────────────────────────────────────────

describe('groups', () => {
  it('joinGroup adds group_id', () => {
    const r = createLifeRecord('agent-0');
    const result = joinGroup(r, 'scbe-fleet');
    expect(result).toBe(true);
    expect(r.groups).toContain('scbe-fleet');
  });

  it('joinGroup is idempotent — returns false on duplicate', () => {
    const r = createLifeRecord('agent-0');
    joinGroup(r, 'scbe-fleet');
    const result = joinGroup(r, 'scbe-fleet');
    expect(result).toBe(false);
    expect(r.groups.filter((g) => g === 'scbe-fleet')).toHaveLength(1);
  });

  it('leaveGroup removes group_id', () => {
    const r = createLifeRecord('agent-0');
    joinGroup(r, 'scbe-fleet');
    const result = leaveGroup(r, 'scbe-fleet');
    expect(result).toBe(true);
    expect(r.groups).not.toContain('scbe-fleet');
  });

  it('leaveGroup returns false for nonexistent group', () => {
    const r = createLifeRecord('agent-0');
    expect(leaveGroup(r, 'ghost-group')).toBe(false);
  });

  it('multiple groups tracked independently', () => {
    const r = createLifeRecord('agent-0');
    joinGroup(r, 'fleet-alpha');
    joinGroup(r, 'fleet-beta');
    leaveGroup(r, 'fleet-alpha');
    expect(r.groups).toContain('fleet-beta');
    expect(r.groups).not.toContain('fleet-alpha');
  });
});

// ─── summarize ────────────────────────────────────────────────────────────────

describe('summarize', () => {
  it('known_count reflects number of encountered agents', () => {
    const r = createLifeRecord('agent-0');
    encounter(r, 'a1');
    encounter(r, 'a2');
    encounter(r, 'a3');
    const s = summarize(r);
    expect(s.known_count).toBe(3);
  });

  it('top_skills sorted by level descending', () => {
    const r = createLifeRecord('agent-0');
    gainSkillXP(r, 'alpha', 300);
    gainSkillXP(r, 'beta', 100);
    gainSkillXP(r, 'gamma', 200);
    const s = summarize(r);
    expect(s.top_skills[0]!.name).toBe('alpha');
    expect(s.top_skills[1]!.name).toBe('gamma');
    expect(s.top_skills[2]!.name).toBe('beta');
  });

  it('top_skills capped at 5 entries', () => {
    const r = createLifeRecord('agent-0');
    for (let i = 0; i < 8; i++) gainSkillXP(r, `skill-${i}`, 100 * (i + 1));
    const s = summarize(r);
    expect(s.top_skills.length).toBeLessThanOrEqual(5);
  });

  it('current_role present when career is active', () => {
    const r = createLifeRecord('agent-0');
    startCareer(r, 'navigator');
    const s = summarize(r);
    expect(s.current_role).toBe('navigator');
  });

  it('current_role absent after career ends', () => {
    const r = createLifeRecord('agent-0');
    startCareer(r, 'navigator');
    endCareer(r, 'navigator');
    const s = summarize(r);
    expect(s.current_role).toBeUndefined();
  });

  it('avg_alignment is 0 when no encounters with signals', () => {
    const r = createLifeRecord('agent-0');
    encounter(r, 'a1');
    const s = summarize(r);
    expect(s.avg_alignment).toBe(0);
  });
});

// ─── serialization ────────────────────────────────────────────────────────────

describe('serialize / deserialize', () => {
  it('round-trips a complete life record', () => {
    const r = createLifeRecord('agent-0', 'Polly');
    encounter(r, 'agent-1', 0.5, 'Zara');
    gainSkillXP(r, 'navigation', 250);
    startCareer(r, 'navigator');
    joinGroup(r, 'scbe-fleet');

    const json = serializeLifeRecord(r);
    const restored = deserializeLifeRecord(json);

    expect(restored.agent_id).toBe('agent-0');
    expect(restored.display_name).toBe('Polly');
    expect(restored.known_agents['agent-1']!.display_name).toBe('Zara');
    expect(restored.skills['navigation']!.level).toBe(2);
    expect(restored.groups).toContain('scbe-fleet');
  });

  it('deserialize handles record with missing optional fields gracefully', () => {
    const minimal = JSON.stringify({ agent_id: 'x', birth_ts: 0, known_agents: {} });
    const r = deserializeLifeRecord(minimal);
    expect(r.groups).toEqual([]);
    expect(r.skills).toEqual({});
    expect(r.career).toEqual([]);
    expect(r.total_encounters).toBe(0);
  });

  it('serialized form is valid JSON', () => {
    const r = createLifeRecord('agent-0');
    const json = serializeLifeRecord(r);
    expect(() => JSON.parse(json)).not.toThrow();
  });
});
