/**
 * @file life-ledger.ts
 * @module agent-bus/life-ledger
 * @layer Cross-layer agent lifecycle
 * @component LifeLedger — AI agent life simulation
 *
 * Per-agent persistent identity ledger.
 * Key capability: O(1) known/unknown person detection — each agent carries
 * a signed record of every agent they have ever encountered.
 *
 * Alignment, careers, skills, and group membership accrete over time.
 * This is the biographical record that persists across sessions.
 */

// ─── Types ───────────────────────────────────────────────────────────────────

export interface AgentIdentity {
  id: string;
  display_name?: string;
  first_seen_ts: number;
  last_seen_ts: number;
  interaction_count: number;
}

export interface SkillLevel {
  name: string;
  xp: number;
  level: number;
}

export interface CareerEntry {
  role: string;
  joined_ts: number;
  left_ts?: number;
  tasks_completed: number;
}

export interface AgentLifeRecord {
  agent_id: string;
  display_name?: string;
  birth_ts: number;
  /** O(1) known/unknown check — keyed by encountered agent_id. */
  known_agents: Record<string, AgentIdentity>;
  /** Per-relationship alignment score in [-1, 1]. */
  alignment_scores: Record<string, number>;
  skills: Record<string, SkillLevel>;
  career: CareerEntry[];
  groups: string[];
  total_encounters: number;
  total_new_encounters: number;
}

export interface EncounterResult {
  /** True when this agent_id has never been seen before — the ledger's main primitive. */
  is_new: boolean;
  identity: AgentIdentity;
  alignment_score: number;
  alignment_delta: number;
}

export interface LifeSummary {
  agent_id: string;
  display_name?: string;
  age_ms: number;
  known_count: number;
  top_skills: SkillLevel[];
  current_role?: string;
  groups: string[];
  total_encounters: number;
  total_new_encounters: number;
  avg_alignment: number;
}

// ─── Create ───────────────────────────────────────────────────────────────────

export function createLifeRecord(agent_id: string, display_name?: string): AgentLifeRecord {
  return {
    agent_id,
    ...(display_name !== undefined ? { display_name } : {}),
    birth_ts: Date.now(),
    known_agents: {},
    alignment_scores: {},
    skills: {},
    career: [],
    groups: [],
    total_encounters: 0,
    total_new_encounters: 0,
  };
}

// ─── Encounter ────────────────────────────────────────────────────────────────

/**
 * Record an encounter with another agent.
 * Returns `is_new: true` on first contact — the signal that this is an unknown person.
 *
 * Alignment update: early interactions have outsized weight (1/sqrt(n) decay),
 * so the first contact sets the baseline tone. Later interactions converge it.
 */
export function encounter(
  record: AgentLifeRecord,
  encountered_id: string,
  alignment_signal?: number,
  display_name?: string
): EncounterResult {
  const now = Date.now();
  const is_new = !(encountered_id in record.known_agents);

  if (is_new) {
    record.known_agents[encountered_id] = {
      id: encountered_id,
      ...(display_name !== undefined ? { display_name } : {}),
      first_seen_ts: now,
      last_seen_ts: now,
      interaction_count: 1,
    };
    record.total_new_encounters++;
  } else {
    const identity = record.known_agents[encountered_id]!;
    identity.last_seen_ts = now;
    identity.interaction_count++;
    if (display_name !== undefined) identity.display_name = display_name;
  }
  record.total_encounters++;

  let alignment_delta = 0;
  if (alignment_signal !== undefined) {
    const clamped = Math.max(-1, Math.min(1, alignment_signal));
    const n = record.known_agents[encountered_id]!.interaction_count;
    // 1/sqrt(n) decay: first encounter fully weights, later ones average in
    const weight = 1 / Math.sqrt(n);
    const prev = record.alignment_scores[encountered_id] ?? 0;
    alignment_delta = clamped * weight;
    record.alignment_scores[encountered_id] = Math.max(-1, Math.min(1, prev + alignment_delta));
  }

  return {
    is_new,
    identity: { ...record.known_agents[encountered_id]! },
    alignment_score: record.alignment_scores[encountered_id] ?? 0,
    alignment_delta,
  };
}

// ─── Skills ───────────────────────────────────────────────────────────────────

/** Award XP in a skill. Level increases every 100 XP, soft-capped at 100. */
export function gainSkillXP(record: AgentLifeRecord, skill_name: string, xp: number): SkillLevel {
  if (!(skill_name in record.skills)) {
    record.skills[skill_name] = { name: skill_name, xp: 0, level: 0 };
  }
  const skill = record.skills[skill_name]!;
  skill.xp = Math.max(0, skill.xp + xp);
  skill.level = Math.min(100, Math.floor(skill.xp / 100));
  return { ...skill };
}

// ─── Career ───────────────────────────────────────────────────────────────────

export function startCareer(record: AgentLifeRecord, role: string): CareerEntry {
  const entry: CareerEntry = { role, joined_ts: Date.now(), tasks_completed: 0 };
  record.career.push(entry);
  return { ...entry };
}

export function endCareer(record: AgentLifeRecord, role: string): boolean {
  const entry = [...record.career]
    .reverse()
    .find((e) => e.role === role && e.left_ts === undefined);
  if (!entry) return false;
  entry.left_ts = Date.now();
  return true;
}

export function completeTask(record: AgentLifeRecord, role: string): boolean {
  const entry = [...record.career]
    .reverse()
    .find((e) => e.role === role && e.left_ts === undefined);
  if (!entry) return false;
  entry.tasks_completed++;
  return true;
}

// ─── Groups ───────────────────────────────────────────────────────────────────

export function joinGroup(record: AgentLifeRecord, group_id: string): boolean {
  if (record.groups.includes(group_id)) return false;
  record.groups.push(group_id);
  return true;
}

export function leaveGroup(record: AgentLifeRecord, group_id: string): boolean {
  const idx = record.groups.indexOf(group_id);
  if (idx === -1) return false;
  record.groups.splice(idx, 1);
  return true;
}

// ─── Queries ──────────────────────────────────────────────────────────────────

export function isKnown(record: AgentLifeRecord, agent_id: string): boolean {
  return agent_id in record.known_agents;
}

export function getAlignmentScore(record: AgentLifeRecord, agent_id: string): number | null {
  return agent_id in record.alignment_scores ? (record.alignment_scores[agent_id] ?? null) : null;
}

export function getKnownAgents(record: AgentLifeRecord): AgentIdentity[] {
  return Object.values(record.known_agents);
}

export function getCurrentRole(record: AgentLifeRecord): string | undefined {
  return [...record.career].reverse().find((e) => e.left_ts === undefined)?.role;
}

export function summarize(record: AgentLifeRecord): LifeSummary {
  const now = Date.now();
  const skills = Object.values(record.skills).sort((a, b) => b.level - a.level);
  const alignmentValues = Object.values(record.alignment_scores);
  const avgAlignment =
    alignmentValues.length > 0
      ? alignmentValues.reduce((s, v) => s + v, 0) / alignmentValues.length
      : 0;
  const currentRole = getCurrentRole(record);

  return {
    agent_id: record.agent_id,
    ...(record.display_name !== undefined ? { display_name: record.display_name } : {}),
    age_ms: now - record.birth_ts,
    known_count: Object.keys(record.known_agents).length,
    top_skills: skills.slice(0, 5),
    ...(currentRole !== undefined ? { current_role: currentRole } : {}),
    groups: [...record.groups],
    total_encounters: record.total_encounters,
    total_new_encounters: record.total_new_encounters,
    avg_alignment: parseFloat(avgAlignment.toFixed(4)),
  };
}

// ─── Serialization ────────────────────────────────────────────────────────────

export function serializeLifeRecord(record: AgentLifeRecord): string {
  return JSON.stringify(record, null, 2);
}

export function deserializeLifeRecord(json: string): AgentLifeRecord {
  const parsed = JSON.parse(json) as AgentLifeRecord;
  // migration safety: ensure all required fields exist
  if (!parsed.groups) parsed.groups = [];
  if (!parsed.skills) parsed.skills = {};
  if (!parsed.career) parsed.career = [];
  if (!parsed.known_agents) parsed.known_agents = {};
  if (!parsed.alignment_scores) parsed.alignment_scores = {};
  if (typeof parsed.total_encounters !== 'number') parsed.total_encounters = 0;
  if (typeof parsed.total_new_encounters !== 'number') parsed.total_new_encounters = 0;
  return parsed;
}
