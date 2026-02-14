/**
 * @file types.ts
 * @module fleet/polly-pads/modes/types
 * @layer L13
 * @component Polly Pad Mode Switching
 * @version 1.0.0
 *
 * Type definitions for the 6 specialist modes that each Polly Pad can switch between.
 * Enables flexible role assignment for autonomous operations (Mars, submarine, disaster).
 */
/**
 * The 6 specialist modes available to each Polly Pad.
 *
 * Tech modes: engineering, navigation, systems
 * Non-tech modes: science, communications, mission_planning
 */
export type SpecialistMode = 'engineering' | 'navigation' | 'systems' | 'science' | 'communications' | 'mission_planning';
/**
 * Tool definition available within a specialist mode.
 */
export interface ModeTool {
    /** Unique tool identifier */
    id: string;
    /** Human-readable name */
    name: string;
    /** What the tool does */
    description: string;
    /** Tool category */
    category: 'diagnostic' | 'analysis' | 'planning' | 'communication' | 'execution' | 'monitoring';
}
/**
 * Result of a mode action execution.
 */
export interface ModeActionResult {
    /** Whether the action succeeded */
    success: boolean;
    /** Action identifier */
    action: string;
    /** Result data */
    data: Record<string, unknown>;
    /** Timestamp of execution */
    timestamp: number;
    /** Confidence score [0-1] */
    confidence: number;
    /** Error message if failed */
    error?: string;
}
/**
 * Persisted state for a specialist mode (survives mode switches).
 */
export interface ModeState {
    /** Mode identifier */
    mode: SpecialistMode;
    /** Serializable state data */
    data: Record<string, unknown>;
    /** When this state was last saved */
    savedAt: number;
    /** How many times this mode has been activated */
    activationCount: number;
    /** Total time spent in this mode (ms) */
    totalTimeMs: number;
}
/**
 * Mode switch event for audit trail.
 */
export interface ModeSwitchEvent {
    /** Previous mode (null if first activation) */
    from: SpecialistMode | null;
    /** New mode */
    to: SpecialistMode;
    /** Why the switch happened */
    reason: string;
    /** Timestamp */
    timestamp: number;
    /** Who initiated the switch (pad ID or 'coordinator') */
    initiator: string;
}
/**
 * Vote cast during Byzantine consensus.
 */
export interface SquadVote {
    /** Voting pad ID */
    padId: string;
    /** Decision */
    decision: 'APPROVE' | 'DENY' | 'DEFER';
    /** Confidence [0-1] */
    confidence: number;
    /** Current mode of the voting pad */
    mode: SpecialistMode;
    /** Timestamp */
    timestamp: number;
}
/**
 * Crisis types that trigger dynamic mode reassignment.
 */
export type CrisisType = 'equipment_failure' | 'novel_discovery' | 'navigation_lost' | 'communication_blackout' | 'power_critical' | 'environmental_hazard';
/**
 * Mode assignment plan for a crisis.
 */
export interface ModeAssignment {
    /** Pad ID */
    padId: string;
    /** Assigned mode */
    mode: SpecialistMode;
    /** Priority of this assignment */
    priority: 'critical' | 'high' | 'medium' | 'standby';
}
/**
 * Configuration for specialist mode metadata.
 */
export interface ModeConfig {
    /** Mode identifier */
    mode: SpecialistMode;
    /** Human-readable name */
    displayName: string;
    /** Mode description */
    description: string;
    /** Whether this is a tech or non-tech mode */
    category: 'tech' | 'non_tech';
    /** Available tools in this mode */
    tools: ModeTool[];
    /** Example tasks this mode handles */
    exampleTasks: string[];
}
/**
 * Static configuration for all 6 specialist modes.
 */
export declare const MODE_CONFIGS: Record<SpecialistMode, ModeConfig>;
//# sourceMappingURL=types.d.ts.map