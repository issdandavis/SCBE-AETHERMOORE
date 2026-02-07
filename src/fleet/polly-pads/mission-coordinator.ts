/**
 * @file mission-coordinator.ts
 * @module fleet/polly-pads/mission-coordinator
 * @layer Layer 13
 * @component Polly Pads — Mission Coordinator & Squad System
 * @version 1.0.0
 *
 * Dynamic mode assignment and Byzantine fault-tolerant squad coordination.
 * Manages 6-pad squads with 4/6 quorum for critical decisions.
 *
 * Formula: n ≥ 3f + 1 where f = max faulty agents
 * With n=6, f_max=1 (tolerates 1 malicious/broken pad)
 * Quorum = 4 (need 4/6 votes for critical, 3/6 for routine)
 */

import type { SpecialistModeId } from './specialist-modes.js';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** Crisis types that trigger mode reassignment */
export type CrisisType =
  | 'equipment_failure'
  | 'navigation_lost'
  | 'communication_blackout'
  | 'novel_discovery'
  | 'power_emergency'
  | 'environmental_hazard';

/** Vote decision */
export type VoteDecision = 'APPROVE' | 'REJECT' | 'DEFER';

/** A vote cast by a pad */
export interface Vote {
  padId: string;
  decision: VoteDecision;
  confidence: number;  // 0-1
  timestamp: number;
  reason?: string;
}

/** Voting session */
export interface VotingSession {
  id: string;
  proposal: string;
  proposerPadId: string;
  /** 'routine' = 3/6, 'critical' = 4/6, 'destructive' = 5/6 */
  severity: 'routine' | 'critical' | 'destructive';
  votes: Vote[];
  status: 'open' | 'approved' | 'rejected' | 'expired';
  createdAt: number;
  resolvedAt?: number;
  /** Timeout in ms (default 30s for autonomous, 300s if Earth available) */
  timeoutMs: number;
}

/** Squad member info */
export interface SquadMember {
  padId: string;
  currentMode: SpecialistModeId | null;
  healthy: boolean;
  lastHeartbeat: number;
}

/** Mode assignment map: padId → mode */
export type ModeAssignment = Map<string, SpecialistModeId>;

/** Consensus result */
export interface ConsensusResult {
  sessionId: string;
  approved: boolean;
  approveCount: number;
  rejectCount: number;
  deferCount: number;
  quorumMet: boolean;
  quorumRequired: number;
}

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

/** Byzantine fault tolerance parameters */
export const BFT = {
  /** Total pads per squad */
  SQUAD_SIZE: 6,
  /** Max tolerated faulty pads (n ≥ 3f + 1 → f = 1 for n = 6) */
  MAX_FAULTY: 1,
  /** Quorum thresholds by severity */
  QUORUM: {
    routine: 3,    // 3/6 = simple majority
    critical: 4,   // 4/6 = supermajority
    destructive: 5, // 5/6 = near-unanimous
  },
  /** Voting timeout (ms) */
  TIMEOUT_AUTONOMOUS: 30_000,    // 30s when no Earth contact
  TIMEOUT_WITH_EARTH: 300_000,   // 5min when Earth is available
} as const;

// ═══════════════════════════════════════════════════════════════
// Crisis Mode Templates
// ═══════════════════════════════════════════════════════════════

/** Pre-defined mode assignments for crisis types */
const CRISIS_TEMPLATES: Record<CrisisType, SpecialistModeId[]> = {
  // Need: 2 tech (eng + sys), 1 planner, 3 standby
  equipment_failure: [
    'engineering', 'systems', 'mission_planning',
    'engineering', 'science', 'communications',
  ],
  // Need: 2 nav, 1 systems, 1 planner, 2 standby
  navigation_lost: [
    'navigation', 'navigation', 'systems',
    'mission_planning', 'science', 'communications',
  ],
  // Need: 2 comms, 1 systems, 1 planner, 2 standby
  communication_blackout: [
    'communications', 'communications', 'systems',
    'mission_planning', 'engineering', 'science',
  ],
  // Need: 3 science, 1 comms, 2 standby
  novel_discovery: [
    'science', 'science', 'science',
    'communications', 'mission_planning', 'systems',
  ],
  // Need: 2 systems, 1 eng, 1 planner, 2 standby
  power_emergency: [
    'systems', 'systems', 'engineering',
    'mission_planning', 'communications', 'navigation',
  ],
  // Need: 2 nav, 1 eng, 1 systems, 2 standby
  environmental_hazard: [
    'navigation', 'engineering', 'systems',
    'mission_planning', 'navigation', 'communications',
  ],
};

// ═══════════════════════════════════════════════════════════════
// Squad
// ═══════════════════════════════════════════════════════════════

/**
 * Squad — A group of 6 Polly Pads with Byzantine fault tolerance.
 *
 * Manages:
 * - Member registration and health tracking
 * - Byzantine consensus voting (4/6 quorum for critical)
 * - Mode assignment and reassignment
 */
export class Squad {
  readonly id: string;
  private members: Map<string, SquadMember> = new Map();
  private sessions: Map<string, VotingSession> = new Map();
  private _modeAssignments: Map<string, SpecialistModeId> = new Map();

  constructor(id: string) {
    this.id = id;
  }

  /** Get all squad members */
  getMembers(): SquadMember[] {
    return Array.from(this.members.values());
  }

  /** Get healthy member count */
  get healthyCount(): number {
    return this.getMembers().filter((m) => m.healthy).length;
  }

  /** Whether squad has enough healthy members for BFT */
  get hasBftQuorum(): boolean {
    return this.healthyCount >= BFT.SQUAD_SIZE - BFT.MAX_FAULTY;
  }

  /** Current mode assignments */
  get modeAssignments(): ReadonlyMap<string, SpecialistModeId> {
    return this._modeAssignments;
  }

  /** Register a pad as squad member */
  addMember(padId: string): void {
    if (this.members.size >= BFT.SQUAD_SIZE) {
      throw new Error(`Squad ${this.id} is full (max ${BFT.SQUAD_SIZE})`);
    }
    this.members.set(padId, {
      padId,
      currentMode: null,
      healthy: true,
      lastHeartbeat: Date.now(),
    });
  }

  /** Remove a member */
  removeMember(padId: string): void {
    this.members.delete(padId);
    this._modeAssignments.delete(padId);
  }

  /** Update member heartbeat */
  heartbeat(padId: string): void {
    const member = this.members.get(padId);
    if (member) {
      member.lastHeartbeat = Date.now();
      member.healthy = true;
    }
  }

  /** Mark unhealthy members (no heartbeat within timeout) */
  checkHealth(timeoutMs: number = 60_000): string[] {
    const now = Date.now();
    const unhealthy: string[] = [];
    for (const [padId, member] of this.members) {
      if (now - member.lastHeartbeat > timeoutMs) {
        member.healthy = false;
        unhealthy.push(padId);
      }
    }
    return unhealthy;
  }

  // ─── Mode Assignment ───

  /** Assign a mode to a pad */
  assignMode(padId: string, mode: SpecialistModeId): void {
    const member = this.members.get(padId);
    if (!member) throw new Error(`Pad ${padId} not in squad ${this.id}`);
    member.currentMode = mode;
    this._modeAssignments.set(padId, mode);
  }

  /** Get mode assignment for a pad */
  getAssignedMode(padId: string): SpecialistModeId | null {
    return this._modeAssignments.get(padId) ?? null;
  }

  // ─── Voting ───

  /**
   * Create a voting session.
   */
  createVotingSession(
    proposal: string,
    proposerPadId: string,
    severity: VotingSession['severity'],
    earthAvailable: boolean = false
  ): VotingSession {
    const session: VotingSession = {
      id: `vote-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`,
      proposal,
      proposerPadId,
      severity,
      votes: [],
      status: 'open',
      createdAt: Date.now(),
      timeoutMs: earthAvailable ? BFT.TIMEOUT_WITH_EARTH : BFT.TIMEOUT_AUTONOMOUS,
    };
    this.sessions.set(session.id, session);
    return session;
  }

  /**
   * Cast a vote in a session.
   */
  castVote(sessionId: string, vote: Vote): void {
    const session = this.sessions.get(sessionId);
    if (!session) throw new Error(`Session ${sessionId} not found`);
    if (session.status !== 'open') throw new Error(`Session ${sessionId} is ${session.status}`);

    // Prevent double-voting
    if (session.votes.some((v) => v.padId === vote.padId)) {
      throw new Error(`Pad ${vote.padId} already voted in ${sessionId}`);
    }

    // Verify voter is a healthy squad member
    const member = this.members.get(vote.padId);
    if (!member?.healthy) {
      throw new Error(`Pad ${vote.padId} is not a healthy squad member`);
    }

    session.votes.push(vote);

    // Check if consensus reached
    this.checkConsensus(sessionId);
  }

  /**
   * Check if consensus has been reached on a session.
   */
  checkConsensus(sessionId: string): ConsensusResult {
    const session = this.sessions.get(sessionId);
    if (!session) throw new Error(`Session ${sessionId} not found`);

    const quorumRequired = BFT.QUORUM[session.severity];
    const approveCount = session.votes.filter((v) => v.decision === 'APPROVE').length;
    const rejectCount = session.votes.filter((v) => v.decision === 'REJECT').length;
    const deferCount = session.votes.filter((v) => v.decision === 'DEFER').length;

    const quorumMet = approveCount >= quorumRequired;
    const rejected = rejectCount > BFT.SQUAD_SIZE - quorumRequired;

    if (quorumMet && session.status === 'open') {
      session.status = 'approved';
      session.resolvedAt = Date.now();
    } else if (rejected && session.status === 'open') {
      session.status = 'rejected';
      session.resolvedAt = Date.now();
    } else if (Date.now() - session.createdAt > session.timeoutMs && session.status === 'open') {
      session.status = 'expired';
      session.resolvedAt = Date.now();
    }

    return {
      sessionId,
      approved: session.status === 'approved',
      approveCount,
      rejectCount,
      deferCount,
      quorumMet,
      quorumRequired,
    };
  }

  /** Get a voting session by ID */
  getSession(sessionId: string): VotingSession | undefined {
    return this.sessions.get(sessionId);
  }

  /** Get all active sessions */
  getActiveSessions(): VotingSession[] {
    return Array.from(this.sessions.values()).filter((s) => s.status === 'open');
  }
}

// ═══════════════════════════════════════════════════════════════
// Mission Coordinator
// ═══════════════════════════════════════════════════════════════

/**
 * MissionCoordinator — Dynamically assigns modes to squad pads based
 * on mission phase and crisis events.
 *
 * Integrates with the Squad voting system for consensus on
 * mode reassignment during crises.
 */
export class MissionCoordinator {
  private squads: Map<string, Squad> = new Map();

  /** Register a squad */
  registerSquad(squad: Squad): void {
    this.squads.set(squad.id, squad);
  }

  /** Get a squad by ID */
  getSquad(squadId: string): Squad | undefined {
    return this.squads.get(squadId);
  }

  /**
   * Get the recommended mode assignments for a crisis type.
   *
   * Returns a map of padId → recommended mode, using the
   * crisis template. Only assigns to healthy members.
   */
  getRecommendedAssignment(
    squadId: string,
    crisisType: CrisisType
  ): ModeAssignment {
    const squad = this.squads.get(squadId);
    if (!squad) throw new Error(`Squad ${squadId} not found`);

    const template = CRISIS_TEMPLATES[crisisType];
    const healthyMembers = squad.getMembers().filter((m) => m.healthy);
    const assignment: ModeAssignment = new Map();

    for (let i = 0; i < healthyMembers.length && i < template.length; i++) {
      assignment.set(healthyMembers[i].padId, template[i]);
    }

    return assignment;
  }

  /**
   * Execute a crisis mode reassignment.
   *
   * Creates a voting session, applies if approved (or immediately
   * if no time for voting in autonomous mode).
   *
   * @param squadId - Target squad
   * @param crisisType - Type of crisis
   * @param immediate - Skip voting (autonomous emergency mode)
   * @returns The mode assignment applied (or null if rejected)
   */
  executeCrisisReassignment(
    squadId: string,
    crisisType: CrisisType,
    immediate: boolean = false
  ): { assignment: ModeAssignment; session?: VotingSession } {
    const squad = this.squads.get(squadId);
    if (!squad) throw new Error(`Squad ${squadId} not found`);

    const assignment = this.getRecommendedAssignment(squadId, crisisType);

    if (!immediate) {
      // Create voting session for the reassignment
      const members = squad.getMembers().filter((m) => m.healthy);
      if (members.length === 0) throw new Error('No healthy members');

      const session = squad.createVotingSession(
        `Crisis reassignment: ${crisisType}`,
        members[0].padId,
        'critical'
      );
      return { assignment, session };
    }

    // Immediate: apply without vote
    for (const [padId, mode] of assignment) {
      squad.assignMode(padId, mode);
    }

    return { assignment };
  }

  /**
   * Apply an approved mode assignment to a squad.
   */
  applyAssignment(squadId: string, assignment: ModeAssignment): void {
    const squad = this.squads.get(squadId);
    if (!squad) throw new Error(`Squad ${squadId} not found`);

    for (const [padId, mode] of assignment) {
      squad.assignMode(padId, mode);
    }
  }

  /**
   * Assign default science modes to all members (normal operations).
   */
  assignDefaultModes(squadId: string, defaultMode: SpecialistModeId = 'science'): void {
    const squad = this.squads.get(squadId);
    if (!squad) throw new Error(`Squad ${squadId} not found`);

    for (const member of squad.getMembers()) {
      if (member.healthy) {
        squad.assignMode(member.padId, defaultMode);
      }
    }
  }
}
