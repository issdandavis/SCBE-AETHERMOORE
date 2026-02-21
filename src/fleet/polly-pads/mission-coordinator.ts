/**
 * @file mission-coordinator.ts
 * @module fleet/polly-pads/mission-coordinator
 *
 * Dual-surface coordinator module:
 * 1) Legacy coordinator for ModePad + Core Squad integration (`setPhase`, `handleCrisis`).
 * 2) Compatibility coordinator + BFT squad API used by v2 Polly Pad tests.
 */

import { ModePad } from './mode-pad';
import { Squad as CoreSquad } from './squad';
import { CrisisType, ModeAssignment, SpecialistMode } from './modes/types';

export type MissionPhase =
  | 'transit'
  | 'science_ops'
  | 'maintenance'
  | 'crisis'
  | 'earth_sync'
  | 'standby';

export interface CrisisAssessment {
  type: CrisisType;
  severity: number;
  assignments: ModeAssignment[];
  requiresEarthContact: boolean;
  estimatedResolutionMinutes: number;
  assessedAt: number;
}

interface PhaseConfig {
  defaultModes: SpecialistMode[];
  description: string;
}

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

// ---------------------------------------------------------------------------
// v2 compatibility voting types
// ---------------------------------------------------------------------------

export const BFT = {
  QUORUM: {
    routine: 3,
    critical: 4,
    destructive: 5,
  },
} as const;

export type VoteDecision = 'APPROVE' | 'REJECT' | 'DEFER';

export interface Vote {
  padId: string;
  decision: VoteDecision;
  confidence: number;
  timestamp: number;
}

export interface VotingSession {
  id: string;
  proposal: string;
  proposerId: string;
  severity: keyof typeof BFT.QUORUM;
  status: 'open' | 'approved' | 'rejected';
  votes: Vote[];
  createdAt: number;
}

export interface SquadMember {
  padId: string;
  healthy: boolean;
  lastHeartbeat: number;
}

export interface ConsensusResult {
  approved: boolean;
  approveCount: number;
  rejectCount: number;
  deferCount: number;
  quorumRequired: number;
}

export class Squad {
  readonly id: string;
  private readonly maxMembers = 6;
  private members = new Map<string, SquadMember>();
  private assignments = new Map<string, SpecialistMode>();
  private sessions = new Map<string, VotingSession>();

  constructor(id: string) {
    this.id = id;
  }

  addMember(padId: string): void {
    if (this.members.size >= this.maxMembers) {
      throw new Error('Squad is full');
    }
    this.members.set(padId, {
      padId,
      healthy: true,
      lastHeartbeat: Date.now(),
    });
  }

  getMembers(): SquadMember[] {
    return Array.from(this.members.values());
  }

  get healthyCount(): number {
    return this.getMembers().filter((m) => m.healthy).length;
  }

  get hasBftQuorum(): boolean {
    return this.members.size >= 4;
  }

  assignMode(padId: string, mode: SpecialistMode): void {
    if (!this.members.has(padId)) {
      throw new Error(`Unknown member ${padId}`);
    }
    this.assignments.set(padId, mode);
  }

  getAssignedMode(padId: string): SpecialistMode | null {
    return this.assignments.get(padId) ?? null;
  }

  createVotingSession(
    proposal: string,
    proposerId: string,
    severity: keyof typeof BFT.QUORUM
  ): VotingSession {
    const session: VotingSession = {
      id: `vote-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
      proposal,
      proposerId,
      severity,
      status: 'open',
      votes: [],
      createdAt: Date.now(),
    };
    this.sessions.set(session.id, session);
    return session;
  }

  castVote(sessionId: string, vote: Vote): void {
    const session = this.sessions.get(sessionId);
    if (!session) throw new Error(`Unknown session ${sessionId}`);
    if (session.status !== 'open') throw new Error('session already closed');

    const member = this.members.get(vote.padId);
    if (!member || !member.healthy) throw new Error('pad is not a healthy member');
    if (session.votes.some((v) => v.padId === vote.padId)) throw new Error('pad already voted');

    session.votes.push(vote);
  }

  checkConsensus(sessionId: string): ConsensusResult {
    const session = this.sessions.get(sessionId);
    if (!session) throw new Error(`Unknown session ${sessionId}`);

    const approveCount = session.votes.filter((v) => v.decision === 'APPROVE').length;
    const rejectCount = session.votes.filter((v) => v.decision === 'REJECT').length;
    const deferCount = session.votes.filter((v) => v.decision === 'DEFER').length;
    const quorumRequired = BFT.QUORUM[session.severity];

    const approved = approveCount >= quorumRequired;
    const rejectThreshold = this.members.size - quorumRequired + 1;

    if (approved) session.status = 'approved';
    else if (rejectCount >= rejectThreshold) session.status = 'rejected';

    return { approved, approveCount, rejectCount, deferCount, quorumRequired };
  }

  getSession(sessionId: string): VotingSession | null {
    return this.sessions.get(sessionId) ?? null;
  }

  checkHealth(staleThresholdMs: number): string[] {
    const now = Date.now();
    const unhealthy: string[] = [];
    for (const member of this.members.values()) {
      if (now - member.lastHeartbeat > staleThresholdMs) {
        member.healthy = false;
        unhealthy.push(member.padId);
      }
    }
    return unhealthy;
  }
}

const COORDINATOR_CRISIS_MODES: Record<CrisisType | 'power_emergency', SpecialistMode[]> = {
  equipment_failure: ['engineering', 'systems', 'mission_planning', 'communications', 'engineering', 'science'],
  novel_discovery: ['science', 'science', 'science', 'communications', 'mission_planning', 'systems'],
  navigation_lost: ['navigation', 'navigation', 'systems', 'mission_planning', 'communications', 'engineering'],
  communication_blackout: ['communications', 'communications', 'systems', 'mission_planning', 'science', 'engineering'],
  power_critical: ['systems', 'systems', 'engineering', 'mission_planning', 'communications', 'navigation'],
  power_emergency: ['systems', 'systems', 'engineering', 'mission_planning', 'communications', 'navigation'],
  environmental_hazard: ['navigation', 'systems', 'science', 'mission_planning', 'communications', 'engineering'],
};

export class MissionCoordinator {
  private legacySquad: CoreSquad | null;
  private squads = new Map<string, Squad>();

  private _currentPhase: MissionPhase = 'standby';
  private _activeCrisis: CrisisAssessment | null = null;
  private phaseHistory: Array<{ phase: MissionPhase; timestamp: number }> = [];
  private crisisHistory: CrisisAssessment[] = [];

  constructor(squad?: CoreSquad) {
    this.legacySquad = squad ?? null;
  }

  // -------------------------------------------------------------------------
  // Legacy API (used by polly-pad-modes tests)
  // -------------------------------------------------------------------------
  get currentPhase(): MissionPhase {
    return this._currentPhase;
  }

  get activeCrisis(): CrisisAssessment | null {
    return this._activeCrisis;
  }

  setPhase(phase: MissionPhase): ModeAssignment[] {
    if (!this.legacySquad) throw new Error('Legacy squad not configured');
    this._currentPhase = phase;
    this._activeCrisis = null;
    this.phaseHistory.push({ phase, timestamp: Date.now() });

    const config = PHASE_CONFIGS[phase];
    const pads = this.legacySquad.getAllPads();
    return pads.map((pad: ModePad, i: number) => {
      const mode = config.defaultModes[i] || 'science';
      pad.switchMode(mode, `Phase: ${phase}`);
      return {
        padId: pad.agentId,
        mode,
        priority: i < 2 ? 'high' : 'medium',
      };
    });
  }

  handleCrisis(crisisType: CrisisType, severity = 0.5): CrisisAssessment {
    if (!this.legacySquad) throw new Error('Legacy squad not configured');
    this._currentPhase = 'crisis';

    const crisisConfig = CRISIS_ASSIGNMENTS[crisisType];
    const pads = this.legacySquad.getAllPads();
    const assignments = pads.map((pad: ModePad, i: number) => {
      const mode = crisisConfig.modes[i] || 'science';
      const priority = crisisConfig.priorities[i] || 'standby';
      pad.switchMode(mode, `Crisis: ${crisisType} (severity: ${severity})`);
      return {
        padId: pad.agentId,
        mode,
        priority,
      } as ModeAssignment;
    });

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

  resolveCrisis(returnPhase: MissionPhase = 'science_ops'): ModeAssignment[] {
    this._activeCrisis = null;
    return this.setPhase(returnPhase);
  }

  assessCrisis(crisisType: CrisisType, severity = 0.5): CrisisAssessment {
    if (!this.legacySquad) throw new Error('Legacy squad not configured');
    const crisisConfig = CRISIS_ASSIGNMENTS[crisisType];
    const pads = this.legacySquad.getAllPads();
    const assignments = pads.map((pad: ModePad, i: number) => ({
      padId: pad.agentId,
      mode: crisisConfig.modes[i] || 'science',
      priority: crisisConfig.priorities[i] || 'standby',
    }));

    return {
      type: crisisType,
      severity: Math.max(0, Math.min(1, severity)),
      assignments,
      requiresEarthContact: crisisConfig.requiresEarth,
      estimatedResolutionMinutes: crisisConfig.estimatedMinutes * (0.5 + severity),
      assessedAt: Date.now(),
    };
  }

  getPhaseConfig(phase: MissionPhase): PhaseConfig {
    return PHASE_CONFIGS[phase];
  }

  getCrisisHistory(): CrisisAssessment[] {
    return [...this.crisisHistory];
  }

  getPhaseHistory(): Array<{ phase: MissionPhase; timestamp: number }> {
    return [...this.phaseHistory];
  }

  // -------------------------------------------------------------------------
  // v2 compatibility API (used by polly-pads-v2 tests)
  // -------------------------------------------------------------------------

  registerSquad(squad: Squad): void {
    this.squads.set(squad.id, squad);
  }

  assignDefaultModes(squadId: string, mode: SpecialistMode): void {
    const squad = this.squads.get(squadId);
    if (!squad) throw new Error(`Unknown squad: ${squadId}`);

    for (const member of squad.getMembers()) {
      if (member.healthy) {
        squad.assignMode(member.padId, mode);
      }
    }
  }

  getRecommendedAssignment(
    squadId: string,
    crisisType: CrisisType | 'power_emergency'
  ): Map<string, SpecialistMode> {
    const squad = this.squads.get(squadId);
    if (!squad) throw new Error(`Unknown squad: ${squadId}`);

    const modes = COORDINATOR_CRISIS_MODES[crisisType];
    const assignment = new Map<string, SpecialistMode>();
    const healthyMembers = squad.getMembers().filter((m) => m.healthy);

    healthyMembers.forEach((member, idx) => {
      assignment.set(member.padId, modes[idx] ?? 'science');
    });

    return assignment;
  }

  executeCrisisReassignment(
    squadId: string,
    crisisType: CrisisType | 'power_emergency',
    immediate: boolean
  ): { assignment: Map<string, SpecialistMode>; session?: VotingSession } {
    const squad = this.squads.get(squadId);
    if (!squad) throw new Error(`Unknown squad: ${squadId}`);

    const assignment = this.getRecommendedAssignment(squadId, crisisType);
    if (immediate) {
      this.applyAssignment(squadId, assignment);
      return { assignment };
    }

    const session = squad.createVotingSession(
      `Crisis reassignment: ${crisisType}`,
      'coordinator',
      'critical'
    );

    return { assignment, session };
  }

  applyAssignment(squadId: string, assignment: Map<string, SpecialistMode>): void {
    const squad = this.squads.get(squadId);
    if (!squad) throw new Error(`Unknown squad: ${squadId}`);

    for (const [padId, mode] of assignment) {
      squad.assignMode(padId, mode);
    }
  }
}
