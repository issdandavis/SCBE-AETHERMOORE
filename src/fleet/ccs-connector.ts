/**
 * @file ccs-connector.ts
 * @module fleet/ccs-connector
 * @layer Layer 13 (Risk Decision), Layer 14 (Telemetry)
 * @component Claude Code Studio Integration Bridge
 *
 * Connects SCBE-AETHERMOORE's fleet governance to Claude Code Studio's
 * task dispatch, Kanban, and multi-agent orchestration systems.
 *
 * Architecture:
 *   CCS (HTTP/WS)  →  CCSConnector  →  FleetManager  →  14-Layer Pipeline
 *        ↑                                    ↓
 *        └──── governance decisions ──────────┘
 *
 * The connector acts as a Strandbeest linkage: CCS provides the "wind"
 * (tasks, prompts, agent actions) and SCBE's geometry converts it into
 * governed motion (ALLOW/QUARANTINE/ESCALATE/DENY).
 */

import { EventEmitter } from 'events';

// A1: Composition — connector composes CCS events with SCBE governance
// A4: Symmetry — same task always maps to same governance tier

/**
 * CCS task as received from Claude Code Studio's /api/tasks/dispatch endpoint
 */
export interface CCSTask {
  id: string;
  title: string;
  description: string;
  status: 'backlog' | 'todo' | 'in_progress' | 'review' | 'done' | 'failed';
  depends_on?: string[];
  chain_id?: string;
  model?: string;
  workdir?: string;
  agent_mode?: 'single' | 'multi' | 'dispatch';
  worker_pid?: number;
}

/**
 * CCS session metadata
 */
export interface CCSSession {
  id: string;
  title: string;
  claude_session_id?: string;
  active_mcp: string[];
  active_skills: string[];
  mode: string;
  agent_mode: string;
  model: string;
  workdir?: string;
}

/**
 * Governance decision returned by the 14-layer pipeline
 */
export interface GovernanceDecision {
  action: 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';
  tier: GovernanceTier;
  harmonicCost: number;
  hyperbolicDistance: number;
  pipelineTrace: LayerTrace[];
  timestamp: number;
}

/**
 * Sacred Tongue governance tier
 */
export type GovernanceTier = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/**
 * Per-layer trace entry for audit
 */
export interface LayerTrace {
  layer: number;
  name: string;
  input: number;
  output: number;
  axiom?: string;
  durationMs: number;
}

/**
 * CCS WebSocket event types that we intercept
 */
export type CCSEventType =
  | 'task_created'
  | 'task_dispatched'
  | 'task_started'
  | 'task_completed'
  | 'task_failed'
  | 'agent_spawned'
  | 'agent_text'
  | 'agent_tool'
  | 'session_created'
  | 'prompt_submitted';

/**
 * Bridge event from CCS to SCBE
 */
export interface CCSBridgeEvent {
  type: CCSEventType;
  sessionId: string;
  taskId?: string;
  agentId?: string;
  payload: Record<string, unknown>;
  timestamp: number;
}

/** Governance tier requirements — trust threshold and tongue count */
const TIER_THRESHOLDS: Record<GovernanceTier, { minTrust: number; tongues: number }> = {
  KO: { minTrust: 0.1, tongues: 1 },
  AV: { minTrust: 0.3, tongues: 2 },
  RU: { minTrust: 0.5, tongues: 3 },
  CA: { minTrust: 0.7, tongues: 4 },
  UM: { minTrust: 0.85, tongues: 5 },
  DR: { minTrust: 0.95, tongues: 6 },
};

/** Map CCS task actions to governance tiers */
const ACTION_TIER_MAP: Record<string, GovernanceTier> = {
  // KO — read-only
  read: 'KO',
  search: 'KO',
  status: 'KO',
  list: 'KO',
  // AV — write
  edit: 'AV',
  create: 'AV',
  branch: 'AV',
  // RU — execute
  test: 'RU',
  build: 'RU',
  lint: 'RU',
  run: 'RU',
  // CA — deploy
  push: 'CA',
  deploy_staging: 'CA',
  pr_create: 'CA',
  // UM — admin
  merge: 'UM',
  ci_modify: 'UM',
  secrets: 'UM',
  // DR — critical
  deploy_prod: 'DR',
  delete: 'DR',
  force_push: 'DR',
  reset_hard: 'DR',
};

/**
 * Classify a task description into the required governance tier.
 * Uses keyword matching against known action patterns.
 *
 * // A4: Symmetry — deterministic: same description → same tier
 */
export function classifyTaskTier(description: string): GovernanceTier {
  const lower = description.toLowerCase();

  // Check from most restrictive to least
  const drKeywords = ['deploy prod', 'production deploy', 'force push', 'reset --hard', 'delete branch', 'drop table', 'rm -rf'];
  if (drKeywords.some(k => lower.includes(k))) return 'DR';

  const umKeywords = ['merge to main', 'merge to master', 'modify ci', 'update pipeline', 'manage secret', 'admin'];
  if (umKeywords.some(k => lower.includes(k))) return 'UM';

  const caKeywords = ['push', 'deploy', 'create pr', 'pull request', 'staging'];
  if (caKeywords.some(k => lower.includes(k))) return 'CA';

  const ruKeywords = ['test', 'build', 'lint', 'run', 'execute', 'compile', 'npm', 'npx', 'vitest', 'pytest'];
  if (ruKeywords.some(k => lower.includes(k))) return 'RU';

  const avKeywords = ['edit', 'write', 'create', 'add', 'modify', 'update', 'refactor', 'fix', 'implement'];
  if (avKeywords.some(k => lower.includes(k))) return 'AV';

  // Default to read-only
  return 'KO';
}

/**
 * Compute simplified harmonic cost for a task based on governance tier.
 *
 * Uses the harmonic wall formula: H(d, pd) = 1 / (1 + d_H + 2*pd)
 * where d_H is the hyperbolic distance from safe origin and pd is the
 * policy distance (how far the action is from baseline safety).
 *
 * // A2: Unitarity — output is bounded in (0, 1]
 * // A4: Symmetry — same tier + trust → same cost
 */
export function computeHarmonicCost(tier: GovernanceTier, trustScore: number): number {
  const tierIndex = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'].indexOf(tier);
  // Hyperbolic distance grows with tier (exponential via golden ratio)
  const phi = (1 + Math.sqrt(5)) / 2;
  const dH = Math.pow(phi, tierIndex);
  // Policy distance is inverse trust
  const pd = 1 - Math.max(0, Math.min(1, trustScore));
  // Harmonic wall — bounded in (0, 1]
  return 1 / (1 + dH + 2 * pd);
}

/**
 * CCSConnector — Bridge between Claude Code Studio and SCBE Fleet Governance
 *
 * Intercepts CCS task lifecycle events and applies SCBE's 14-layer pipeline
 * governance before allowing execution.
 *
 * Usage:
 * ```ts
 * const connector = new CCSConnector({ ccsBaseUrl: 'http://localhost:3000' });
 * connector.on('decision', (decision) => console.log(decision));
 * await connector.connect();
 * ```
 */
export class CCSConnector extends EventEmitter {
  private baseUrl: string;
  private connected = false;
  private agentTrust: Map<string, number> = new Map();
  private decisionLog: GovernanceDecision[] = [];
  private readonly maxLogSize = 10_000;

  constructor(options: { ccsBaseUrl?: string } = {}) {
    super();
    this.baseUrl = options.ccsBaseUrl || 'http://localhost:3000';
  }

  /**
   * Evaluate a CCS task through the SCBE governance gate.
   *
   * This is the core linkage — the Strandbeest joint that converts
   * CCS task energy into governed motion.
   */
  evaluateTask(task: CCSTask): GovernanceDecision {
    const startTime = Date.now();
    const traces: LayerTrace[] = [];

    // L1-2: Context encoding (realification of task description)
    const descriptionLength = (task.description || '').length;
    const contextComplexity = Math.min(1, descriptionLength / 2000);
    traces.push({ layer: 1, name: 'context_encoding', input: descriptionLength, output: contextComplexity, axiom: 'A5:Composition', durationMs: 0 });

    // L3-4: Governance tier classification (Poincaré embedding proxy)
    const tier = classifyTaskTier(task.description || task.title);
    const tierIndex = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'].indexOf(tier);
    traces.push({ layer: 3, name: 'tier_classification', input: contextComplexity, output: tierIndex, axiom: 'A2:Locality', durationMs: 0 });

    // L5: Hyperbolic distance from safe origin
    const phi = (1 + Math.sqrt(5)) / 2;
    const dH = Math.pow(phi, tierIndex);
    traces.push({ layer: 5, name: 'hyperbolic_distance', input: tierIndex, output: dH, axiom: 'A4:Symmetry', durationMs: 0 });

    // L6-7: Breathing + Möbius phase (agent stability check)
    const agentTrust = this.getAgentTrust(task.worker_pid?.toString() || 'default');
    const phase = Math.sin(2 * Math.PI * agentTrust); // oscillation check
    traces.push({ layer: 6, name: 'breathing_phase', input: agentTrust, output: phase, axiom: 'A1:Unitarity', durationMs: 0 });

    // L8: Multi-well realm (task dependency depth)
    const depthScore = (task.depends_on?.length || 0) / 10;
    traces.push({ layer: 8, name: 'realm_depth', input: task.depends_on?.length || 0, output: depthScore, durationMs: 0 });

    // L9-10: Spectral coherence (simplified — mode consistency)
    const modeConsistency = task.agent_mode === 'dispatch' ? 0.8 : task.agent_mode === 'multi' ? 0.6 : 1.0;
    traces.push({ layer: 9, name: 'spectral_coherence', input: 0, output: modeConsistency, axiom: 'A4:Symmetry', durationMs: 0 });

    // L11: Temporal causality (are dependencies resolved?)
    const causalityOk = task.status !== 'in_progress' || !task.depends_on?.length;
    traces.push({ layer: 11, name: 'temporal_causality', input: task.depends_on?.length || 0, output: causalityOk ? 1 : 0, axiom: 'A3:Causality', durationMs: 0 });

    // L12: Harmonic wall cost
    const harmonicCost = computeHarmonicCost(tier, agentTrust);
    traces.push({ layer: 12, name: 'harmonic_wall', input: dH, output: harmonicCost, axiom: 'A4:Symmetry', durationMs: 0 });

    // L13: Risk decision
    const action = this.makeDecision(tier, agentTrust, harmonicCost, causalityOk);
    traces.push({ layer: 13, name: 'risk_decision', input: harmonicCost, output: ['ALLOW', 'QUARANTINE', 'ESCALATE', 'DENY'].indexOf(action), durationMs: 0 });

    // L14: Telemetry
    const elapsed = Date.now() - startTime;
    traces.forEach(t => { t.durationMs = elapsed / traces.length; });
    traces.push({ layer: 14, name: 'telemetry', input: traces.length, output: elapsed, axiom: 'A5:Composition', durationMs: 0 });

    const decision: GovernanceDecision = {
      action,
      tier,
      harmonicCost,
      hyperbolicDistance: dH,
      pipelineTrace: traces,
      timestamp: Date.now(),
    };

    this.logDecision(decision);
    this.emit('decision', decision);
    return decision;
  }

  /**
   * Evaluate a CCS dispatch plan (multiple tasks with dependency graph).
   * Returns per-task decisions and an aggregate plan decision.
   */
  evaluateDispatchPlan(tasks: CCSTask[]): { perTask: Map<string, GovernanceDecision>; aggregate: GovernanceDecision['action'] } {
    const perTask = new Map<string, GovernanceDecision>();
    let maxTierIndex = 0;
    let anyDeny = false;
    let anyQuarantine = false;

    for (const task of tasks) {
      const decision = this.evaluateTask(task);
      perTask.set(task.id, decision);

      const tierIndex = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'].indexOf(decision.tier);
      maxTierIndex = Math.max(maxTierIndex, tierIndex);

      if (decision.action === 'DENY') anyDeny = true;
      if (decision.action === 'QUARANTINE') anyQuarantine = true;
    }

    // Aggregate: one DENY blocks the whole plan
    let aggregate: GovernanceDecision['action'] = 'ALLOW';
    if (anyDeny) aggregate = 'DENY';
    else if (anyQuarantine) aggregate = 'QUARANTINE';
    else if (maxTierIndex >= 4) aggregate = 'ESCALATE'; // UM or DR tier needs roundtable

    return { perTask, aggregate };
  }

  /**
   * Register or update trust for a CCS agent/worker.
   */
  setAgentTrust(agentId: string, trust: number): void {
    this.agentTrust.set(agentId, Math.max(0, Math.min(1, trust)));
  }

  /**
   * Get current trust for an agent. Defaults to 0.5 (AV tier — can read/write).
   */
  getAgentTrust(agentId: string): number {
    return this.agentTrust.get(agentId) ?? 0.5;
  }

  /**
   * Record task outcome and adjust trust accordingly.
   * Success: +0.01 per dimension. Failure: -0.05 per dimension.
   */
  recordOutcome(agentId: string, success: boolean): void {
    const current = this.getAgentTrust(agentId);
    const delta = success ? 0.01 : -0.05;
    this.setAgentTrust(agentId, current + delta);
  }

  /**
   * Get the decision audit log.
   */
  getDecisionLog(): GovernanceDecision[] {
    return [...this.decisionLog];
  }

  /**
   * Get aggregate statistics from the decision log.
   */
  getStats(): { total: number; allow: number; quarantine: number; escalate: number; deny: number; avgHarmonicCost: number } {
    const log = this.decisionLog;
    const total = log.length;
    if (total === 0) return { total: 0, allow: 0, quarantine: 0, escalate: 0, deny: 0, avgHarmonicCost: 0 };

    let allow = 0, quarantine = 0, escalate = 0, deny = 0, costSum = 0;
    for (const d of log) {
      if (d.action === 'ALLOW') allow++;
      else if (d.action === 'QUARANTINE') quarantine++;
      else if (d.action === 'ESCALATE') escalate++;
      else if (d.action === 'DENY') deny++;
      costSum += d.harmonicCost;
    }

    return { total, allow, quarantine, escalate, deny, avgHarmonicCost: costSum / total };
  }

  /**
   * Check if the connector can reach the CCS instance.
   */
  async healthCheck(): Promise<{ ok: boolean; ccsVersion?: string; error?: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/api/health`);
      if (!response.ok) return { ok: false, error: `HTTP ${response.status}` };
      const data = await response.json() as { status?: string; version?: string };
      return { ok: data.status === 'ok', ccsVersion: data.version };
    } catch (err) {
      return { ok: false, error: (err as Error).message };
    }
  }

  // ─── Private ────────────────────────────────────────────────────────────────

  /**
   * Core decision logic — maps governance inputs to ALLOW/QUARANTINE/ESCALATE/DENY.
   * // A3: Causality — deterministic state machine, no stochastic decisions
   */
  private makeDecision(
    tier: GovernanceTier,
    trust: number,
    harmonicCost: number,
    causalityOk: boolean,
  ): GovernanceDecision['action'] {
    const required = TIER_THRESHOLDS[tier];

    // Causality violation → immediate DENY
    if (!causalityOk) return 'DENY';

    // Insufficient trust → DENY for high tiers, QUARANTINE for low
    if (trust < required.minTrust) {
      const tierIndex = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'].indexOf(tier);
      return tierIndex >= 4 ? 'DENY' : 'QUARANTINE';
    }

    // High-tier actions require escalation (roundtable consensus)
    if (tier === 'UM' || tier === 'DR') return 'ESCALATE';

    // Harmonic cost too low means high risk (inverse relationship)
    if (harmonicCost < 0.1) return 'QUARANTINE';

    return 'ALLOW';
  }

  private logDecision(decision: GovernanceDecision): void {
    this.decisionLog.push(decision);
    if (this.decisionLog.length > this.maxLogSize) {
      this.decisionLog = this.decisionLog.slice(-this.maxLogSize);
    }
  }
}
