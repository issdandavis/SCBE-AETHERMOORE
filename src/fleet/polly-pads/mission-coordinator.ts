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
}
