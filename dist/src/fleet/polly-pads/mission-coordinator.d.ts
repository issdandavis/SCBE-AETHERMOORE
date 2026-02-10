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
import { Squad } from './squad';
import { CrisisType, ModeAssignment, SpecialistMode } from './modes/types';
/**
 * Mission phase for mode assignment defaults.
 */
export type MissionPhase = 'transit' | 'science_ops' | 'maintenance' | 'crisis' | 'earth_sync' | 'standby';
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
export declare class MissionCoordinator {
    private squad;
    private _currentPhase;
    private _activeCrisis;
    private phaseHistory;
    private crisisHistory;
    constructor(squad: Squad);
    get currentPhase(): MissionPhase;
    get activeCrisis(): CrisisAssessment | null;
    /**
     * Set the mission phase and assign default modes to all pads.
     */
    setPhase(phase: MissionPhase): ModeAssignment[];
    /**
     * Handle a crisis by dynamically reassigning modes.
     *
     * @param crisisType The type of crisis detected
     * @param severity Severity score (0-1)
     * @returns Crisis assessment with mode assignments
     */
    handleCrisis(crisisType: CrisisType, severity?: number): CrisisAssessment;
    /**
     * Resolve the current crisis and return to a specified phase.
     */
    resolveCrisis(returnPhase?: MissionPhase): ModeAssignment[];
    /**
     * Get the recommended mode assignments for a crisis type (without applying).
     */
    assessCrisis(crisisType: CrisisType, severity?: number): CrisisAssessment;
    /**
     * Get the mode distribution for a given phase.
     */
    getPhaseConfig(phase: MissionPhase): PhaseConfig;
    /**
     * Get crisis history.
     */
    getCrisisHistory(): CrisisAssessment[];
    /**
     * Get phase history.
     */
    getPhaseHistory(): Array<{
        phase: MissionPhase;
        timestamp: number;
    }>;
}
export {};
//# sourceMappingURL=mission-coordinator.d.ts.map