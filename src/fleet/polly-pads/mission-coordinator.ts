/**
 * @file mission-coordinator.ts
 * @module fleet/polly-pads/mission-coordinator
 * @layer L13
 * @component Mission Coordinator - Smart Mode Assignment
 * @version 1.0.0
 *
 * Dynamically assigns specialist modes to Polly Pads based on
 * mission phase and crisis type. The "brain" that decides who
 * does what during autonomous operations.
 */

import { ModePad } from './mode-pad';
import { Squad } from './squad';
import {
  CrisisType,
  ModeAssignment,
  SpecialistMode,
} from './modes/types';
import type { SpecialistModeId } from './specialist-modes.js';

/**
 * Mission phase for mode assignment defaults.
 */
export type MissionPhase =
  | 'transit'
  | 'science_ops'
  | 'maintenance'
  | 'crisis'
  | 'earth_sync'
  | 'standby';

/**
 * Crisis assessment returned by the coordinator.
 */
export interface CrisisAssessment {
  /** Crisis type */
  type: CrisisType;
  /** Severity (0-1) */
  severity: number;
  /** Mode assignments for each pad */
  assignments: ModeAssignment[];
  /** Whether Earth contact is needed */
  requiresEarthContact: boolean;
  /** Estimated resolution time in minutes */
  estimatedResolutionMinutes: number;
  /** Timestamp */
  assessedAt: number;
}

/**
 * Phase configuration for default mode assignments.
 */
interface PhaseConfig {
  /** Default modes for the first N pads in the squad */
  defaultModes: SpecialistMode[];
  /** Description of this phase */
  description: string;
}

/**
 * Default mode assignments per mission phase.
 */
const PHASE_CONFIGS: Record<MissionPhase, PhaseConfig> = {
  transit: {
    defaultModes: ['navigation', 'navigation', 'systems', 'communications', 'mission_planning', 'systems'],
    description: 'In transit — navigation-heavy',
  },
  science_ops: {
    defaultModes: ['science', 'science', 'science', 'science', 'communications', 'systems'],
    description: 'Normal science operations — science-heavy',
  },
  maintenance: {
    defaultModes: ['engineering', 'engineering', 'systems', 'systems', 'communications', 'mission_planning'],
    description: 'Scheduled maintenance — engineering-heavy',
  },
  crisis: {
    defaultModes: ['engineering', 'systems', 'mission_planning', 'communications', 'navigation', 'science'],
    description: 'Crisis response — balanced coverage',
  },
  earth_sync: {
    defaultModes: ['communications', 'communications', 'science', 'mission_planning', 'systems', 'engineering'],
    description: 'Earth contact window — communications-heavy',
  },
  standby: {
    defaultModes: ['systems', 'systems', 'communications', 'mission_planning', 'science', 'engineering'],
    description: 'Low-power standby — monitoring-heavy',
  },
};

/**
 * Crisis-specific mode assignments.
 */
const CRISIS_ASSIGNMENTS: Record<CrisisType, {
  modes: SpecialistMode[];
  priorities: Array<ModeAssignment['priority']>;
  requiresEarth: boolean;
  estimatedMinutes: number;
}> = {
  equipment_failure: {
    modes: ['engineering', 'systems', 'mission_planning', 'communications', 'engineering', 'science'],
    priorities: ['critical', 'critical', 'high', 'medium', 'high', 'standby'],
    requiresEarth: false,
    estimatedMinutes: 60,
  },
  novel_discovery: {
    modes: ['science', 'science', 'science', 'communications', 'mission_planning', 'systems'],
    priorities: ['critical', 'critical', 'critical', 'high', 'medium', 'standby'],
    requiresEarth: true,
    estimatedMinutes: 120,
  },
  navigation_lost: {
    modes: ['navigation', 'navigation', 'systems', 'mission_planning', 'communications', 'engineering'],
    priorities: ['critical', 'critical', 'high', 'high', 'medium', 'standby'],
    requiresEarth: false,
    estimatedMinutes: 45,
  },
  communication_blackout: {
    modes: ['communications', 'communications', 'systems', 'mission_planning', 'science', 'engineering'],
    priorities: ['critical', 'critical', 'high', 'high', 'medium', 'standby'],
    requiresEarth: false,
    estimatedMinutes: 30,
  },
  power_critical: {
    modes: ['systems', 'systems', 'engineering', 'mission_planning', 'communications', 'navigation'],
    priorities: ['critical', 'critical', 'critical', 'high', 'medium', 'standby'],
    requiresEarth: true,
    estimatedMinutes: 90,
  },
  environmental_hazard: {
    modes: ['navigation', 'systems', 'science', 'mission_planning', 'communications', 'engineering'],
    priorities: ['critical', 'critical', 'high', 'high', 'medium', 'standby'],
    requiresEarth: false,
    estimatedMinutes: 30,
  },
};

/**
 * MissionCoordinator — Smart Mode Assignment
 *
 * Dynamically assigns specialist modes to Polly Pads in a squad based on
 * the current mission phase or crisis type.
 *
 * @example
 * ```typescript
 * const coordinator = new MissionCoordinator(squad);
 *
 * // Normal science operations
 * coordinator.setPhase('science_ops');
 *
 * // Crisis hits!
 * const assessment = coordinator.handleCrisis('equipment_failure', 0.7);
 * // Pads are reassigned: 2 engineering, 1 systems, 1 planner, 1 comms, 1 standby
 *
 * // Crisis resolved
 * coordinator.setPhase('science_ops');
 * ```
 */
export class MissionCoordinator {
  private squad: Squad;
  private _currentPhase: MissionPhase = 'standby';
  private _activeCrisis: CrisisAssessment | null = null;
  private phaseHistory: Array<{ phase: MissionPhase; timestamp: number }> = [];
  private crisisHistory: CrisisAssessment[] = [];

  constructor(squad: Squad) {
    this.squad = squad;
  }

  get currentPhase(): MissionPhase {
    return this._currentPhase;
  }

  get activeCrisis(): CrisisAssessment | null {
    return this._activeCrisis;
  }

  /**
   * Set the mission phase and assign default modes to all pads.
   */
  setPhase(phase: MissionPhase): ModeAssignment[] {
    this._currentPhase = phase;
    this._activeCrisis = null;
    this.phaseHistory.push({ phase, timestamp: Date.now() });

    const config = PHASE_CONFIGS[phase];
    const pads = this.squad.getAllPads();
    const assignments: ModeAssignment[] = [];

    for (let i = 0; i < pads.length; i++) {
      const mode = config.defaultModes[i] || 'science';
      pads[i].switchMode(mode, `Phase: ${phase}`);
      assignments.push({
        padId: pads[i].agentId,
        mode,
        priority: i < 2 ? 'high' : 'medium',
      });
    }

    return assignments;
  }

  /**
   * Handle a crisis by dynamically reassigning modes.
   *
   * @param crisisType The type of crisis detected
   * @param severity Severity score (0-1)
   * @returns Crisis assessment with mode assignments
   */
  handleCrisis(crisisType: CrisisType, severity: number = 0.5): CrisisAssessment {
    this._currentPhase = 'crisis';

    const crisisConfig = CRISIS_ASSIGNMENTS[crisisType];
    const pads = this.squad.getAllPads();
    const assignments: ModeAssignment[] = [];

    for (let i = 0; i < pads.length; i++) {
      const mode = crisisConfig.modes[i] || 'science';
      const priority = crisisConfig.priorities[i] || 'standby';

      pads[i].switchMode(mode, `Crisis: ${crisisType} (severity: ${severity})`);
      assignments.push({
        padId: pads[i].agentId,
        mode,
        priority,
      });
    }

    const assessment: CrisisAssessment = {
      type: crisisType,
      severity: Math.max(0, Math.min(1, severity)),
      assignments,
      requiresEarthContact: crisisConfig.requiresEarth,
      estimatedResolutionMinutes: crisisConfig.estimatedMinutes * (0.5 + severity),
      assessedAt: Date.now(),
    };

    this._activeCrisis = assessment;
    this.crisisHistory.push(assessment);

    return assessment;
  }

  /**
   * Resolve the current crisis and return to a specified phase.
   */
  resolveCrisis(returnPhase: MissionPhase = 'science_ops'): ModeAssignment[] {
    this._activeCrisis = null;
    return this.setPhase(returnPhase);
  }

  /**
   * Get the recommended mode assignments for a crisis type (without applying).
   */
  assessCrisis(crisisType: CrisisType, severity: number = 0.5): CrisisAssessment {
    const crisisConfig = CRISIS_ASSIGNMENTS[crisisType];
    const pads = this.squad.getAllPads();
    const assignments: ModeAssignment[] = [];

    for (let i = 0; i < pads.length; i++) {
      assignments.push({
        padId: pads[i].agentId,
        mode: crisisConfig.modes[i] || 'science',
        priority: crisisConfig.priorities[i] || 'standby',
      });
    }

    return {
      type: crisisType,
      severity: Math.max(0, Math.min(1, severity)),
      assignments,
      requiresEarthContact: crisisConfig.requiresEarth,
      estimatedResolutionMinutes: crisisConfig.estimatedMinutes * (0.5 + severity),
      assessedAt: Date.now(),
    };
  }

  /**
   * Get the mode distribution for a given phase.
   */
  getPhaseConfig(phase: MissionPhase): PhaseConfig {
    return PHASE_CONFIGS[phase];
  }

  /**
   * Get crisis history.
   */
  getCrisisHistory(): CrisisAssessment[] {
    return [...this.crisisHistory];
  }

  /**
   * Get phase history.
   */
  getPhaseHistory(): Array<{ phase: MissionPhase; timestamp: number }> {
    return [...this.phaseHistory];
      }

// ═══════════════════════════════════════════════════════════════
// Types

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
