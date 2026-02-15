"use strict";
/**
 * @file mission-coordinator.ts
 * @module fleet/polly-pads/mission-coordinator
 *
 * Dual-surface coordinator module:
 * 1) Legacy coordinator for ModePad + Core Squad integration (`setPhase`, `handleCrisis`).
 * 2) Compatibility coordinator + BFT squad API used by v2 Polly Pad tests.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.MissionCoordinator = exports.Squad = exports.BFT = void 0;
const PHASE_CONFIGS = {
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
const CRISIS_ASSIGNMENTS = {
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
exports.BFT = {
    QUORUM: {
        routine: 3,
        critical: 4,
        destructive: 5,
    },
};
class Squad {
    id;
    maxMembers = 6;
    members = new Map();
    assignments = new Map();
    sessions = new Map();
    constructor(id) {
        this.id = id;
    }
    addMember(padId) {
        if (this.members.size >= this.maxMembers) {
            throw new Error('Squad is full');
        }
        this.members.set(padId, {
            padId,
            healthy: true,
            lastHeartbeat: Date.now(),
        });
    }
    getMembers() {
        return Array.from(this.members.values());
    }
    get healthyCount() {
        return this.getMembers().filter((m) => m.healthy).length;
    }
    get hasBftQuorum() {
        return this.members.size >= 4;
    }
    assignMode(padId, mode) {
        if (!this.members.has(padId)) {
            throw new Error(`Unknown member ${padId}`);
        }
        this.assignments.set(padId, mode);
    }
    getAssignedMode(padId) {
        return this.assignments.get(padId) ?? null;
    }
    createVotingSession(proposal, proposerId, severity) {
        const session = {
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
    castVote(sessionId, vote) {
        const session = this.sessions.get(sessionId);
        if (!session)
            throw new Error(`Unknown session ${sessionId}`);
        if (session.status !== 'open')
            throw new Error('session already closed');
        const member = this.members.get(vote.padId);
        if (!member || !member.healthy)
            throw new Error('pad is not a healthy member');
        if (session.votes.some((v) => v.padId === vote.padId))
            throw new Error('pad already voted');
        session.votes.push(vote);
    }
    checkConsensus(sessionId) {
        const session = this.sessions.get(sessionId);
        if (!session)
            throw new Error(`Unknown session ${sessionId}`);
        const approveCount = session.votes.filter((v) => v.decision === 'APPROVE').length;
        const rejectCount = session.votes.filter((v) => v.decision === 'REJECT').length;
        const deferCount = session.votes.filter((v) => v.decision === 'DEFER').length;
        const quorumRequired = exports.BFT.QUORUM[session.severity];
        const approved = approveCount >= quorumRequired;
        const rejectThreshold = this.members.size - quorumRequired + 1;
        if (approved)
            session.status = 'approved';
        else if (rejectCount >= rejectThreshold)
            session.status = 'rejected';
        return { approved, approveCount, rejectCount, deferCount, quorumRequired };
    }
    getSession(sessionId) {
        return this.sessions.get(sessionId) ?? null;
    }
    checkHealth(staleThresholdMs) {
        const now = Date.now();
        const unhealthy = [];
        for (const member of this.members.values()) {
            if (now - member.lastHeartbeat > staleThresholdMs) {
                member.healthy = false;
                unhealthy.push(member.padId);
            }
        }
        return unhealthy;
    }
}
exports.Squad = Squad;
const COORDINATOR_CRISIS_MODES = {
    equipment_failure: ['engineering', 'systems', 'mission_planning', 'communications', 'engineering', 'science'],
    novel_discovery: ['science', 'science', 'science', 'communications', 'mission_planning', 'systems'],
    navigation_lost: ['navigation', 'navigation', 'systems', 'mission_planning', 'communications', 'engineering'],
    communication_blackout: ['communications', 'communications', 'systems', 'mission_planning', 'science', 'engineering'],
    power_critical: ['systems', 'systems', 'engineering', 'mission_planning', 'communications', 'navigation'],
    power_emergency: ['systems', 'systems', 'engineering', 'mission_planning', 'communications', 'navigation'],
    environmental_hazard: ['navigation', 'systems', 'science', 'mission_planning', 'communications', 'engineering'],
};
class MissionCoordinator {
    legacySquad;
    squads = new Map();
    _currentPhase = 'standby';
    _activeCrisis = null;
    phaseHistory = [];
    crisisHistory = [];
    constructor(squad) {
        this.legacySquad = squad ?? null;
    }
    // -------------------------------------------------------------------------
    // Legacy API (used by polly-pad-modes tests)
    // -------------------------------------------------------------------------
    get currentPhase() {
        return this._currentPhase;
    }
    get activeCrisis() {
        return this._activeCrisis;
    }
    setPhase(phase) {
        if (!this.legacySquad)
            throw new Error('Legacy squad not configured');
        this._currentPhase = phase;
        this._activeCrisis = null;
        this.phaseHistory.push({ phase, timestamp: Date.now() });
        const config = PHASE_CONFIGS[phase];
        const pads = this.legacySquad.getAllPads();
        return pads.map((pad, i) => {
            const mode = config.defaultModes[i] || 'science';
            pad.switchMode(mode, `Phase: ${phase}`);
            return {
                padId: pad.agentId,
                mode,
                priority: i < 2 ? 'high' : 'medium',
            };
        });
    }
    handleCrisis(crisisType, severity = 0.5) {
        if (!this.legacySquad)
            throw new Error('Legacy squad not configured');
        this._currentPhase = 'crisis';
        const crisisConfig = CRISIS_ASSIGNMENTS[crisisType];
        const pads = this.legacySquad.getAllPads();
        const assignments = pads.map((pad, i) => {
            const mode = crisisConfig.modes[i] || 'science';
            const priority = crisisConfig.priorities[i] || 'standby';
            pad.switchMode(mode, `Crisis: ${crisisType} (severity: ${severity})`);
            return {
                padId: pad.agentId,
                mode,
                priority,
            };
        });
        const assessment = {
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
    resolveCrisis(returnPhase = 'science_ops') {
        this._activeCrisis = null;
        return this.setPhase(returnPhase);
    }
    assessCrisis(crisisType, severity = 0.5) {
        if (!this.legacySquad)
            throw new Error('Legacy squad not configured');
        const crisisConfig = CRISIS_ASSIGNMENTS[crisisType];
        const pads = this.legacySquad.getAllPads();
        const assignments = pads.map((pad, i) => ({
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
    getPhaseConfig(phase) {
        return PHASE_CONFIGS[phase];
    }
    getCrisisHistory() {
        return [...this.crisisHistory];
    }
    getPhaseHistory() {
        return [...this.phaseHistory];
    }
    // -------------------------------------------------------------------------
    // v2 compatibility API (used by polly-pads-v2 tests)
    // -------------------------------------------------------------------------
    registerSquad(squad) {
        this.squads.set(squad.id, squad);
    }
    assignDefaultModes(squadId, mode) {
        const squad = this.squads.get(squadId);
        if (!squad)
            throw new Error(`Unknown squad: ${squadId}`);
        for (const member of squad.getMembers()) {
            if (member.healthy) {
                squad.assignMode(member.padId, mode);
            }
        }
    }
    getRecommendedAssignment(squadId, crisisType) {
        const squad = this.squads.get(squadId);
        if (!squad)
            throw new Error(`Unknown squad: ${squadId}`);
        const modes = COORDINATOR_CRISIS_MODES[crisisType];
        const assignment = new Map();
        const healthyMembers = squad.getMembers().filter((m) => m.healthy);
        healthyMembers.forEach((member, idx) => {
            assignment.set(member.padId, modes[idx] ?? 'science');
        });
        return assignment;
    }
    executeCrisisReassignment(squadId, crisisType, immediate) {
        const squad = this.squads.get(squadId);
        if (!squad)
            throw new Error(`Unknown squad: ${squadId}`);
        const assignment = this.getRecommendedAssignment(squadId, crisisType);
        if (immediate) {
            this.applyAssignment(squadId, assignment);
            return { assignment };
        }
        const session = squad.createVotingSession(`Crisis reassignment: ${crisisType}`, 'coordinator', 'critical');
        return { assignment, session };
    }
    applyAssignment(squadId, assignment) {
        const squad = this.squads.get(squadId);
        if (!squad)
            throw new Error(`Unknown squad: ${squadId}`);
        for (const [padId, mode] of assignment) {
            squad.assignMode(padId, mode);
        }
    }
}
exports.MissionCoordinator = MissionCoordinator;
//# sourceMappingURL=mission-coordinator.js.map