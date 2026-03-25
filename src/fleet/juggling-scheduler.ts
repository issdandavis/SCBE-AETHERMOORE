/**
 * @file juggling-scheduler.ts
 * @module fleet/juggling-scheduler
 * @layer Layer 13 (Risk Decision)
 * @component Juggling Agent Coordination
 *
 * Models multi-agent task coordination as a physics juggling system.
 *
 * Core mapping:
 *   balls   → TaskCapsules (units of work in flight)
 *   hands   → AgentSlots (bounded execution capacity)
 *   throws  → structured handoffs with predicted catch windows
 *   arcs    → latency/deadline envelopes
 *   rhythm  → scheduler cadence / phase locking
 *   drops   → timeout / failure / lost context
 *   pattern → orchestration policy (siteswap notation)
 *
 * The scheduler enforces 7 juggling rules:
 *   1. Never throw to an unready hand
 *   2. Every throw needs a predicted catch window
 *   3. High-inertia tasks have fewer handoffs
 *   4. Higher arcs for risky tasks (more validation slack)
 *   5. Detect phase drift early
 *   6. Build interception paths (backup handlers)
 *   7. Ledger catches, not just throws
 */

import { FleetAgent, GovernanceTier, GOVERNANCE_TIERS, TaskPriority, PRIORITY_WEIGHTS } from './types';

// ---------------------------------------------------------------------------
// Enums & Constants
// ---------------------------------------------------------------------------

/** Flight state of a task capsule through the juggling system */
export enum FlightState {
  /** Held by an agent, not in transit */
  HELD = 'held',
  /** Thrown — in transit between agents */
  THROWN = 'thrown',
  /** Caught — receipt acknowledged by receiver */
  CAUGHT = 'caught',
  /** Undergoing validation before execution */
  VALIDATING = 'validating',
  /** Missed catch — recovery in progress */
  RECOVERING = 'recovering',
  /** Drop — timeout, failure, or corruption */
  DROPPED = 'dropped',
  /** Terminal — work complete */
  DONE = 'done',
}

/** Siteswap-like arc descriptor for handoff timing */
export type ArcHeight = 1 | 2 | 3 | 5 | 7;
// 1 = immediate cross-hand, 3 = short latency, 5 = validation slack, 7 = high-risk arc

/** Default scoring weights for assignment_score */
export const DEFAULT_SCORE_WEIGHTS = {
  reliability: 2.0,
  trustAlignment: 1.0,
  timeSlack: 0.5,
  inertiaPenalty: 1.5,
  riskPenalty: 1.2,
  loadPenalty: 2.0,
  latencyPenalty: 0.001,
} as const;

/** Decay constant for utility/recoverability over time: U(t) = U0 * e^(-lambda*t) */
export const DEFAULT_GRAVITY_LAMBDA = 0.05;

/** Maximum retry count before permanent drop */
export const MAX_RETRIES = 3;

/** Phase drift detection threshold (ratio of overdue to total in-flight) */
export const PHASE_DRIFT_THRESHOLD = 0.3;

// ---------------------------------------------------------------------------
// Core Types
// ---------------------------------------------------------------------------

/** Scoring weight configuration */
export interface ScoreWeights {
  reliability: number;
  trustAlignment: number;
  timeSlack: number;
  inertiaPenalty: number;
  riskPenalty: number;
  loadPenalty: number;
  latencyPenalty: number;
}

/**
 * TaskCapsule — a unit of work in flight through the juggling system.
 *
 * Carries its own flight plan: who can catch it, when it expires,
 * how costly it is to redirect, and what validation it requires.
 */
export interface TaskCapsule {
  /** Unique task identifier */
  taskId: string;

  /** Reference to the payload (not the payload itself — keeps capsules lightweight) */
  payloadRef: string;

  /** Priority weight (higher = more important) */
  priority: number;

  /** Trust score of the originating context [0, 1] */
  trustScore: number;

  /**
   * Inertia — how costly it is to redirect this task.
   * Derived from state size, context sensitivity, dependencies, irreversibility.
   * Range [0, 1] where 1 = maximum resistance to redirection.
   */
  inertia: number;

  /**
   * Risk level [0, 1].
   * High-risk tasks get higher arcs (more validation slack).
   */
  risk: number;

  /** Creation timestamp (ms) */
  createdAt: number;

  /**
   * Deadline timestamp (ms).
   * Gravity analog — recoverability decays exponentially toward this point.
   */
  deadlineAt: number;

  /** Current owner agent ID (null if unowned) */
  owner: string | null;

  /** Ordered list of eligible next handlers */
  nextCandidates: string[];

  /** Fallback handlers if primary candidates miss (Rule 6: interception paths) */
  fallbackCandidates: string[];

  /** Current flight state */
  state: FlightState;

  /** Number of times this capsule has been re-thrown after a drop */
  retryCount: number;

  /** Quorum depth required for validation (1 = single validator) */
  requiredQuorum: number;

  /** SHA-256 integrity hash of the payload */
  integrityHash: string | null;

  /** Governance tier required to handle this task */
  requiredTier: GovernanceTier;

  /** Arc height — controls slack time vs throughput trade-off */
  arcHeight: ArcHeight;

  /** Timestamp of last state transition */
  lastTransitionAt: number;

  /** Provenance chain: [agentId, timestamp, state][] */
  provenance: Array<[string, number, FlightState]>;
}

/**
 * AgentSlot — an agent's execution capacity in the juggling system.
 *
 * Maps a FleetAgent's real capabilities into juggling terms:
 * catch capacity, current load, reliability, latency.
 */
export interface AgentSlot {
  /** Agent identifier (matches FleetAgent.id) */
  agentId: string;

  /** Roles this agent can fill */
  roles: string[];

  /** Maximum simultaneous tasks (catch capacity) */
  catchCapacity: number;

  /** Current number of held/validating tasks */
  currentLoad: number;

  /** Historical reliability [0, 1] — probability of successful catch */
  reliability: number;

  /** Trust domains this agent is authorized for */
  trustDomains: GovernanceTier[];

  /** Average latency in ms for this agent to acknowledge a catch */
  avgLatencyMs: number;

  /** Timestamp of last successful catch */
  lastCatchAt: number;

  /** Consecutive missed catches (phase drift indicator) */
  consecutiveMisses: number;
}

/**
 * HandoffReceipt — explicit ACK when an agent catches a task.
 * Rule 7: ledger catches, not just throws.
 */
export interface HandoffReceipt {
  /** Task capsule ID */
  taskId: string;

  /** Receiving agent */
  receiverId: string;

  /** Sending agent */
  senderId: string;

  /** Receipt timestamp */
  timestamp: number;

  /** Payload integrity verified */
  integrityVerified: boolean;

  /** Agent confirmed local feasibility */
  feasibilityConfirmed: boolean;

  /** Updated ownership record */
  newOwner: string;
}

/**
 * JugglingEvent — emitted by the scheduler for audit and observability.
 */
export interface JugglingEvent {
  type:
    | 'throw'
    | 'catch'
    | 'drop'
    | 'intercept'
    | 'validate'
    | 'complete'
    | 'phase_drift'
    | 'capacity_warning';
  taskId: string;
  agentId?: string;
  timestamp: number;
  data: Record<string, unknown>;
}

/**
 * SchedulerMetrics — real-time health of the juggling pattern.
 */
export interface SchedulerMetrics {
  /** Total capsules currently in flight (THROWN state) */
  inFlight: number;
  /** Total capsules held by agents */
  held: number;
  /** Total drops in the current window */
  drops: number;
  /** Total successful catches in the current window */
  catches: number;
  /** Phase drift ratio (overdue / total in-flight) */
  phaseDrift: number;
  /** Average arc time (ms) across recent handoffs */
  avgArcTimeMs: number;
  /** System cadence health [0, 1] */
  cadenceHealth: number;
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

/**
 * Compute the assignment score for a (task, agent) pair.
 *
 * score = w1 * reliability
 *       + w2 * trustAlignment
 *       + w3 * timeSlack
 *       - w4 * inertia
 *       - w5 * risk * mismatch
 *       - w6 * loadRatio
 *       - w7 * latency
 *
 * Higher score = better assignment.
 */
export function assignmentScore(
  task: TaskCapsule,
  agent: AgentSlot,
  now: number,
  weights: ScoreWeights = DEFAULT_SCORE_WEIGHTS,
): number {
  const timeLeft = Math.max(task.deadlineAt - now, 1e-3);
  const loadRatio = agent.currentLoad / Math.max(agent.catchCapacity, 1);

  // Trust alignment: how well the agent's tier matches the task requirement
  const tierOrder: GovernanceTier[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
  const requiredIdx = tierOrder.indexOf(task.requiredTier);
  const maxAgentIdx = Math.max(...agent.trustDomains.map((t) => tierOrder.indexOf(t)));
  const mismatch = maxAgentIdx >= requiredIdx ? 0 : (requiredIdx - maxAgentIdx) / tierOrder.length;

  return (
    weights.reliability * agent.reliability +
    weights.trustAlignment * task.trustScore -
    weights.inertiaPenalty * task.inertia -
    weights.riskPenalty * task.risk * (mismatch + 0.1) -
    weights.loadPenalty * loadRatio -
    weights.latencyPenalty * agent.avgLatencyMs +
    weights.timeSlack * Math.log1p(timeLeft / 1000)
  );
}

/**
 * Compute recoverability of a task at time `now`.
 * U(t) = e^(-lambda * elapsed_seconds)
 * Returns [0, 1] where 1 = fully recoverable, 0 = expired.
 */
export function recoverability(task: TaskCapsule, now: number, lambda: number = DEFAULT_GRAVITY_LAMBDA): number {
  const elapsedSec = Math.max(now - task.createdAt, 0) / 1000;
  return Math.exp(-lambda * elapsedSec);
}

// ---------------------------------------------------------------------------
// Agent Slot Factory
// ---------------------------------------------------------------------------

/**
 * Create an AgentSlot from a FleetAgent.
 * Bridges existing fleet types into juggling terms.
 */
export function agentSlotFromFleet(agent: FleetAgent): AgentSlot {
  const tierOrder: GovernanceTier[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
  const maxIdx = tierOrder.indexOf(agent.maxGovernanceTier);
  const trustDomains = tierOrder.slice(0, maxIdx + 1) as GovernanceTier[];

  return {
    agentId: agent.id,
    roles: agent.capabilities,
    catchCapacity: agent.maxConcurrentTasks,
    currentLoad: agent.currentTaskCount,
    reliability: agent.successRate,
    trustDomains,
    avgLatencyMs: 100, // default; refined by scheduler over time
    lastCatchAt: agent.lastActiveAt,
    consecutiveMisses: 0,
  };
}

// ---------------------------------------------------------------------------
// Arc Height Selection
// ---------------------------------------------------------------------------

/**
 * Select arc height based on task risk and inertia.
 * Rule 4: higher arcs for risky tasks (more validation slack).
 * Rule 3: high-inertia tasks get moderate arcs (fewer handoffs).
 */
export function selectArcHeight(risk: number, inertia: number): ArcHeight {
  const composite = 0.6 * risk + 0.4 * inertia;
  if (composite >= 0.8) return 7;
  if (composite >= 0.6) return 5;
  if (composite >= 0.3) return 3;
  if (composite >= 0.1) return 2;
  return 1;
}

// ---------------------------------------------------------------------------
// TaskCapsule Factory
// ---------------------------------------------------------------------------

export interface CreateCapsuleOptions {
  taskId: string;
  payloadRef: string;
  priority?: TaskPriority;
  trustScore?: number;
  inertia?: number;
  risk?: number;
  deadlineMs?: number;
  nextCandidates?: string[];
  fallbackCandidates?: string[];
  requiredQuorum?: number;
  requiredTier?: GovernanceTier;
  integrityHash?: string | null;
}

/**
 * Create a new TaskCapsule with sensible defaults.
 */
export function createCapsule(opts: CreateCapsuleOptions): TaskCapsule {
  const now = Date.now();
  const priority = PRIORITY_WEIGHTS[opts.priority ?? 'medium'];
  const risk = opts.risk ?? 0.2;
  const inertia = opts.inertia ?? 0.2;

  return {
    taskId: opts.taskId,
    payloadRef: opts.payloadRef,
    priority,
    trustScore: opts.trustScore ?? 0.5,
    inertia,
    risk,
    createdAt: now,
    deadlineAt: now + (opts.deadlineMs ?? 30_000),
    owner: null,
    nextCandidates: opts.nextCandidates ?? [],
    fallbackCandidates: opts.fallbackCandidates ?? [],
    state: FlightState.HELD,
    retryCount: 0,
    requiredQuorum: opts.requiredQuorum ?? 1,
    integrityHash: opts.integrityHash ?? null,
    requiredTier: opts.requiredTier ?? 'KO',
    arcHeight: selectArcHeight(risk, inertia),
    lastTransitionAt: now,
    provenance: [],
  };
}

// ---------------------------------------------------------------------------
// Juggling Scheduler
// ---------------------------------------------------------------------------

/**
 * JugglingScheduler — governed task-flight coordinator.
 *
 * Work capsules move between specialized agents along predicted arcs,
 * with explicit catches, bounded capacity, phase timing, and recovery
 * on missed handoffs.
 */
export class JugglingScheduler {
  private capsules: Map<string, TaskCapsule> = new Map();
  private agents: Map<string, AgentSlot> = new Map();
  private eventLog: JugglingEvent[] = [];
  private receiptLog: HandoffReceipt[] = [];
  private weights: ScoreWeights;
  private gravityLambda: number;

  constructor(weights: ScoreWeights = DEFAULT_SCORE_WEIGHTS, gravityLambda: number = DEFAULT_GRAVITY_LAMBDA) {
    this.weights = weights;
    this.gravityLambda = gravityLambda;
  }

  // ---- Agent Management ----

  /** Register an agent slot */
  registerAgent(slot: AgentSlot): void {
    this.agents.set(slot.agentId, slot);
  }

  /** Register from FleetAgent */
  registerFleetAgent(agent: FleetAgent): void {
    this.registerAgent(agentSlotFromFleet(agent));
  }

  /** Remove an agent. Any tasks held by it enter RECOVERING. */
  removeAgent(agentId: string): TaskCapsule[] {
    this.agents.delete(agentId);
    const orphaned: TaskCapsule[] = [];
    for (const capsule of this.capsules.values()) {
      if (capsule.owner === agentId && capsule.state !== FlightState.DONE) {
        this.transition(capsule, FlightState.RECOVERING);
        capsule.owner = null;
        orphaned.push(capsule);
      }
    }
    return orphaned;
  }

  /** Get agent slot */
  getAgent(agentId: string): AgentSlot | undefined {
    return this.agents.get(agentId);
  }

  // ---- Capsule Management ----

  /** Add a capsule to the scheduler */
  addCapsule(capsule: TaskCapsule): void {
    this.capsules.set(capsule.taskId, capsule);
  }

  /** Get capsule by ID */
  getCapsule(taskId: string): TaskCapsule | undefined {
    return this.capsules.get(taskId);
  }

  /** Get all capsules in a given state */
  getCapsulesByState(state: FlightState): TaskCapsule[] {
    return Array.from(this.capsules.values()).filter((c) => c.state === state);
  }

  // ---- Core Scheduling ----

  /**
   * Rule 1 & 2: Find the best agent for a capsule.
   * Never throw to an unready hand. Every throw needs a predicted catch window.
   */
  findBestReceiver(capsule: TaskCapsule): AgentSlot | null {
    const now = Date.now();
    const candidates = capsule.nextCandidates.length > 0
      ? capsule.nextCandidates
          .map((id) => this.agents.get(id))
          .filter((a): a is AgentSlot => a !== undefined)
      : Array.from(this.agents.values());

    // Rule 1: filter to agents that can actually catch
    const eligible = candidates.filter((a) => this.canCatch(a, capsule, now));

    if (eligible.length === 0) {
      // Rule 6: try fallback / interception candidates
      const fallbacks = capsule.fallbackCandidates
        .map((id) => this.agents.get(id))
        .filter((a): a is AgentSlot => a !== undefined)
        .filter((a) => this.canCatch(a, capsule, now));

      if (fallbacks.length === 0) return null;
      return this.pickBest(fallbacks, capsule, now);
    }

    return this.pickBest(eligible, capsule, now);
  }

  /**
   * Throw a capsule to the best available agent.
   * Returns the HandoffReceipt on success, null if no receiver available.
   */
  throwCapsule(taskId: string): HandoffReceipt | null {
    const capsule = this.capsules.get(taskId);
    if (!capsule) return null;

    const receiver = this.findBestReceiver(capsule);
    if (!receiver) {
      // No available hand — mark recovering if not already
      if (capsule.state !== FlightState.DROPPED) {
        this.transition(capsule, FlightState.RECOVERING);
      }
      return null;
    }

    const senderId = capsule.owner ?? '__scheduler__';
    const now = Date.now();

    // Transition to THROWN
    this.transition(capsule, FlightState.THROWN);

    // Simulate catch (in a real system this would be async with timeout)
    this.transition(capsule, FlightState.CAUGHT);
    capsule.owner = receiver.agentId;
    receiver.currentLoad++;
    receiver.consecutiveMisses = 0;
    receiver.lastCatchAt = now;

    // Record provenance
    capsule.provenance.push([receiver.agentId, now, FlightState.CAUGHT]);

    // Build receipt (Rule 7: ledger catches)
    const receipt: HandoffReceipt = {
      taskId: capsule.taskId,
      receiverId: receiver.agentId,
      senderId,
      timestamp: now,
      integrityVerified: capsule.integrityHash !== null,
      feasibilityConfirmed: true,
      newOwner: receiver.agentId,
    };
    this.receiptLog.push(receipt);

    this.emit({
      type: 'catch',
      taskId: capsule.taskId,
      agentId: receiver.agentId,
      timestamp: now,
      data: { senderId, arcHeight: capsule.arcHeight },
    });

    // If quorum > 1, enter VALIDATING
    if (capsule.requiredQuorum > 1) {
      this.transition(capsule, FlightState.VALIDATING);
    }

    return receipt;
  }

  /**
   * Mark a capsule as complete. Frees the agent's slot.
   */
  completeCapsule(taskId: string): boolean {
    const capsule = this.capsules.get(taskId);
    if (!capsule) return false;

    const agent = capsule.owner ? this.agents.get(capsule.owner) : null;
    if (agent && agent.currentLoad > 0) {
      agent.currentLoad--;
    }

    this.transition(capsule, FlightState.DONE);
    capsule.provenance.push([capsule.owner ?? '__none__', Date.now(), FlightState.DONE]);

    this.emit({
      type: 'complete',
      taskId,
      agentId: capsule.owner ?? undefined,
      timestamp: Date.now(),
      data: { retryCount: capsule.retryCount },
    });

    return true;
  }

  /**
   * Handle a drop: increment retry, attempt re-throw or permanent drop.
   * Rule 3: high-inertia tasks should not be bounced repeatedly.
   */
  handleDrop(taskId: string): HandoffReceipt | null {
    const capsule = this.capsules.get(taskId);
    if (!capsule) return null;

    // Free previous owner's slot
    if (capsule.owner) {
      const prevAgent = this.agents.get(capsule.owner);
      if (prevAgent) {
        if (prevAgent.currentLoad > 0) prevAgent.currentLoad--;
        prevAgent.consecutiveMisses++;
      }
    }

    capsule.retryCount++;
    capsule.owner = null;

    this.emit({
      type: 'drop',
      taskId,
      timestamp: Date.now(),
      data: { retryCount: capsule.retryCount },
    });

    // Rule 3: high-inertia tasks with too many retries → permanent drop
    if (capsule.retryCount >= MAX_RETRIES || (capsule.inertia > 0.7 && capsule.retryCount >= 2)) {
      this.transition(capsule, FlightState.DROPPED);
      return null;
    }

    // Try re-throw (Rule 6: interception)
    this.transition(capsule, FlightState.RECOVERING);
    return this.throwCapsule(taskId);
  }

  // ---- Phase Monitoring ----

  /**
   * Rule 5: Detect phase drift.
   * Returns the ratio of overdue in-flight capsules.
   */
  detectPhaseDrift(): number {
    const now = Date.now();
    const inFlight = this.getCapsulesByState(FlightState.THROWN);
    const recovering = this.getCapsulesByState(FlightState.RECOVERING);
    const all = [...inFlight, ...recovering];

    if (all.length === 0) return 0;

    const overdue = all.filter((c) => now > c.deadlineAt).length;
    const drift = overdue / all.length;

    if (drift >= PHASE_DRIFT_THRESHOLD) {
      this.emit({
        type: 'phase_drift',
        taskId: '__system__',
        timestamp: now,
        data: { drift, overdueCount: overdue, totalInFlight: all.length },
      });
    }

    return drift;
  }

  /**
   * Check agents for capacity warnings.
   * Emits events when load exceeds 80% of catch capacity.
   */
  checkCapacity(): void {
    const now = Date.now();
    for (const agent of this.agents.values()) {
      const ratio = agent.currentLoad / Math.max(agent.catchCapacity, 1);
      if (ratio >= 0.8) {
        this.emit({
          type: 'capacity_warning',
          taskId: '__system__',
          agentId: agent.agentId,
          timestamp: now,
          data: { loadRatio: ratio, currentLoad: agent.currentLoad, capacity: agent.catchCapacity },
        });
      }
    }
  }

  // ---- Metrics ----

  /** Get current scheduler health metrics */
  getMetrics(): SchedulerMetrics {
    const now = Date.now();
    const allCapsules = Array.from(this.capsules.values());

    const inFlight = allCapsules.filter((c) => c.state === FlightState.THROWN).length;
    const held = allCapsules.filter(
      (c) => c.state === FlightState.HELD || c.state === FlightState.CAUGHT || c.state === FlightState.VALIDATING,
    ).length;
    const drops = allCapsules.filter((c) => c.state === FlightState.DROPPED).length;
    const done = allCapsules.filter((c) => c.state === FlightState.DONE).length;

    // Compute average arc time from receipts
    let avgArcTimeMs = 0;
    if (this.receiptLog.length > 0) {
      const recentReceipts = this.receiptLog.slice(-50);
      const arcTimes = recentReceipts.map((r) => {
        const capsule = this.capsules.get(r.taskId);
        return capsule ? r.timestamp - capsule.createdAt : 0;
      });
      avgArcTimeMs = arcTimes.reduce((a, b) => a + b, 0) / arcTimes.length;
    }

    const drift = this.detectPhaseDrift();
    const total = allCapsules.length || 1;

    return {
      inFlight,
      held,
      drops,
      catches: done,
      phaseDrift: drift,
      avgArcTimeMs,
      cadenceHealth: Math.max(0, 1 - drift - drops / total),
    };
  }

  // ---- Batch Operations ----

  /**
   * Tick the scheduler: expire overdue capsules, attempt recovery, check phase.
   * Call this on a regular cadence (e.g., every 500ms–2s).
   */
  tick(): SchedulerMetrics {
    const now = Date.now();

    // Expire overdue capsules
    for (const capsule of this.capsules.values()) {
      if (capsule.state === FlightState.DONE || capsule.state === FlightState.DROPPED) continue;

      if (now > capsule.deadlineAt) {
        this.handleDrop(capsule.taskId);
      }
    }

    // Attempt to assign unowned capsules
    for (const capsule of this.getCapsulesByState(FlightState.HELD)) {
      if (!capsule.owner) {
        this.throwCapsule(capsule.taskId);
      }
    }

    // Retry recovering capsules
    for (const capsule of this.getCapsulesByState(FlightState.RECOVERING)) {
      this.throwCapsule(capsule.taskId);
    }

    this.checkCapacity();
    return this.getMetrics();
  }

  // ---- Siteswap Pattern Encoding ----

  /**
   * Encode a capsule's journey as a siteswap-like string.
   * Numbers = arc heights, Q = quorum gate, x = cross-agent.
   */
  encodeSiteswap(taskId: string): string {
    const capsule = this.capsules.get(taskId);
    if (!capsule) return '';

    const parts: string[] = [];
    for (const [agentId, , state] of capsule.provenance) {
      if (state === FlightState.CAUGHT) {
        parts.push(`${capsule.arcHeight}`);
      } else if (state === FlightState.VALIDATING) {
        parts.push(`${capsule.arcHeight}Q`);
      } else if (state === FlightState.DONE) {
        parts.push('0');
      }
    }
    return parts.join(' -> ');
  }

  // ---- Event System ----

  /** Get all events (for audit/ledger) */
  getEvents(): readonly JugglingEvent[] {
    return this.eventLog;
  }

  /** Get all receipts (Rule 7) */
  getReceipts(): readonly HandoffReceipt[] {
    return this.receiptLog;
  }

  /** Clear event log (for testing / rotation) */
  clearEvents(): void {
    this.eventLog = [];
  }

  // ---- Internal ----

  /** Check if an agent can catch a capsule (Rule 1) */
  private canCatch(agent: AgentSlot, capsule: TaskCapsule, now: number): boolean {
    // Capacity check
    if (agent.currentLoad >= agent.catchCapacity) return false;

    // Deadline check — agent must be able to receive before expiry
    if (now + agent.avgLatencyMs > capsule.deadlineAt) return false;

    // Governance tier check
    const tierOrder: GovernanceTier[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
    const requiredIdx = tierOrder.indexOf(capsule.requiredTier);
    const maxAgentIdx = Math.max(...agent.trustDomains.map((t) => tierOrder.indexOf(t)));
    if (maxAgentIdx < requiredIdx) return false;

    return true;
  }

  /** Pick the best agent from an eligible set */
  private pickBest(eligible: AgentSlot[], capsule: TaskCapsule, now: number): AgentSlot {
    let best = eligible[0];
    let bestScore = -Infinity;

    for (const agent of eligible) {
      const score = assignmentScore(capsule, agent, now, this.weights);
      if (score > bestScore) {
        bestScore = score;
        best = agent;
      }
    }

    return best;
  }

  /** Transition a capsule to a new state */
  private transition(capsule: TaskCapsule, newState: FlightState): void {
    capsule.state = newState;
    capsule.lastTransitionAt = Date.now();
  }

  /** Emit a juggling event */
  private emit(event: JugglingEvent): void {
    this.eventLog.push(event);
  }
}
