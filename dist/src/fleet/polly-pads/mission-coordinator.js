"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.MissionCoordinator = void 0;
/**
 * Default mode assignments per mission phase.
 */
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
/**
 * Crisis-specific mode assignments.
 */
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
class MissionCoordinator {
    squad;
    _currentPhase = 'standby';
    _activeCrisis = null;
    phaseHistory = [];
    crisisHistory = [];
    constructor(squad) {
        this.squad = squad;
    }
    get currentPhase() {
        return this._currentPhase;
    }
    get activeCrisis() {
        return this._activeCrisis;
    }
    /**
     * Set the mission phase and assign default modes to all pads.
     */
    setPhase(phase) {
        this._currentPhase = phase;
        this._activeCrisis = null;
        this.phaseHistory.push({ phase, timestamp: Date.now() });
        const config = PHASE_CONFIGS[phase];
        const pads = this.squad.getAllPads();
        const assignments = [];
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
    handleCrisis(crisisType, severity = 0.5) {
        this._currentPhase = 'crisis';
        const crisisConfig = CRISIS_ASSIGNMENTS[crisisType];
        const pads = this.squad.getAllPads();
        const assignments = [];
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
    /**
     * Resolve the current crisis and return to a specified phase.
     */
    resolveCrisis(returnPhase = 'science_ops') {
        this._activeCrisis = null;
        return this.setPhase(returnPhase);
    }
    /**
     * Get the recommended mode assignments for a crisis type (without applying).
     */
    assessCrisis(crisisType, severity = 0.5) {
        const crisisConfig = CRISIS_ASSIGNMENTS[crisisType];
        const pads = this.squad.getAllPads();
        const assignments = [];
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
    getPhaseConfig(phase) {
        return PHASE_CONFIGS[phase];
    }
    /**
     * Get crisis history.
     */
    getCrisisHistory() {
        return [...this.crisisHistory];
    }
    /**
     * Get phase history.
     */
    getPhaseHistory() {
        return [...this.phaseHistory];
    }
}
exports.MissionCoordinator = MissionCoordinator;
//# sourceMappingURL=mission-coordinator.js.map