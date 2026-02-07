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
export type SpecialistMode =
  | 'engineering'
  | 'navigation'
  | 'systems'
  | 'science'
  | 'communications'
  | 'mission_planning';

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
export type CrisisType =
  | 'equipment_failure'
  | 'novel_discovery'
  | 'navigation_lost'
  | 'communication_blackout'
  | 'power_critical'
  | 'environmental_hazard';

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
export const MODE_CONFIGS: Record<SpecialistMode, ModeConfig> = {
  engineering: {
    mode: 'engineering',
    displayName: 'Engineering',
    description: 'Repair & diagnostics specialist',
    category: 'tech',
    tools: [
      {
        id: 'schematics',
        name: 'Schematics Viewer',
        description: 'View and analyze equipment schematics',
        category: 'diagnostic',
      },
      {
        id: 'repair_procedures',
        name: 'Repair Procedures',
        description: 'Step-by-step repair instructions',
        category: 'execution',
      },
      {
        id: 'diagnostic_tools',
        name: 'Diagnostic Tools',
        description: 'Run diagnostic checks on equipment',
        category: 'diagnostic',
      },
      {
        id: 'parts_inventory',
        name: 'Parts Inventory',
        description: 'Track available spare parts',
        category: 'monitoring',
      },
    ],
    exampleTasks: ['Fix broken motor', 'Patch leak', 'Recalibrate sensor'],
  },
  navigation: {
    mode: 'navigation',
    displayName: 'Navigation',
    description: 'Pathfinding & terrain analysis specialist',
    category: 'tech',
    tools: [
      {
        id: 'maps',
        name: 'Map System',
        description: 'Terrain and navigation maps',
        category: 'analysis',
      },
      {
        id: 'path_algorithms',
        name: 'Path Algorithms',
        description: 'A*, Dijkstra, and terrain-aware routing',
        category: 'planning',
      },
      {
        id: 'slam',
        name: 'SLAM',
        description: 'Simultaneous Localization and Mapping',
        category: 'analysis',
      },
      {
        id: 'obstacle_detector',
        name: 'Obstacle Detector',
        description: 'Identify and classify terrain obstacles',
        category: 'diagnostic',
      },
    ],
    exampleTasks: ['Route planning', 'Obstacle avoidance', 'Terrain analysis'],
  },
  systems: {
    mode: 'systems',
    displayName: 'Systems',
    description: 'Power & sensor monitoring specialist',
    category: 'tech',
    tools: [
      {
        id: 'telemetry',
        name: 'Telemetry Dashboard',
        description: 'Real-time system telemetry',
        category: 'monitoring',
      },
      {
        id: 'system_logs',
        name: 'System Logs',
        description: 'Access and analyze system logs',
        category: 'diagnostic',
      },
      {
        id: 'power_models',
        name: 'Power Models',
        description: 'Battery and power consumption modeling',
        category: 'analysis',
      },
      {
        id: 'sensor_health',
        name: 'Sensor Health',
        description: 'Monitor sensor calibration and health',
        category: 'monitoring',
      },
    ],
    exampleTasks: ['Battery management', 'Sensor health check', 'Subsystem monitoring'],
  },
  science: {
    mode: 'science',
    displayName: 'Science',
    description: 'Analysis & discovery specialist',
    category: 'non_tech',
    tools: [
      {
        id: 'spectrometer',
        name: 'Spectrometer Data',
        description: 'Analyze spectrometer readings',
        category: 'analysis',
      },
      {
        id: 'lab_protocols',
        name: 'Lab Protocols',
        description: 'Standard laboratory procedures',
        category: 'execution',
      },
      {
        id: 'sample_database',
        name: 'Sample Database',
        description: 'Catalog and search collected samples',
        category: 'analysis',
      },
      {
        id: 'hypothesis_engine',
        name: 'Hypothesis Engine',
        description: 'Generate and test scientific hypotheses',
        category: 'planning',
      },
    ],
    exampleTasks: ['Sample analysis', 'Data interpretation', 'Hypothesis testing'],
  },
  communications: {
    mode: 'communications',
    displayName: 'Communications',
    description: 'Liaison & reporting specialist',
    category: 'non_tech',
    tools: [
      {
        id: 'radio_protocols',
        name: 'Radio Protocols',
        description: 'UHF/deep-space communication protocols',
        category: 'communication',
      },
      {
        id: 'encryption',
        name: 'Encryption Suite',
        description: 'Message encryption and verification',
        category: 'execution',
      },
      {
        id: 'message_queue',
        name: 'Message Queue',
        description: 'Queue messages for delayed transmission',
        category: 'communication',
      },
      {
        id: 'status_reporter',
        name: 'Status Reporter',
        description: 'Generate formatted status reports',
        category: 'communication',
      },
    ],
    exampleTasks: ['Earth sync', 'Squad messaging', 'Status reports'],
  },
  mission_planning: {
    mode: 'mission_planning',
    displayName: 'Mission Planning',
    description: 'Strategy & validation specialist',
    category: 'non_tech',
    tools: [
      {
        id: 'risk_matrix',
        name: 'Risk Matrix',
        description: 'Assess and visualize mission risks',
        category: 'planning',
      },
      {
        id: 'timeline',
        name: 'Mission Timeline',
        description: 'Track and adjust mission timeline',
        category: 'planning',
      },
      {
        id: 'constraints',
        name: 'Constraints Engine',
        description: 'Evaluate resource and safety constraints',
        category: 'analysis',
      },
      {
        id: 'decision_validator',
        name: 'Decision Validator',
        description: 'Validate proposed decisions against mission objectives',
        category: 'planning',
      },
    ],
    exampleTasks: ['Risk assessment', 'Objective prioritization', 'Decision validation'],
  },
};
