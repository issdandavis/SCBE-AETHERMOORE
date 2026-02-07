/**
 * @file specialist-modes.ts
 * @module fleet/polly-pads/specialist-modes
 * @layer Layer 13
 * @component Polly Pads — Specialist Mode System
 * @version 1.0.0
 *
 * Dynamic mode switching for Polly Pads. Each pad can switch between
 * 6 specialist modes based on mission needs, enabling flexible team
 * composition without fixed role assignment.
 *
 * Modes:
 *   Engineering   — Repair, diagnostics, hardware
 *   Navigation    — Pathfinding, terrain, SLAM
 *   Systems       — Power, sensors, subsystem health
 *   Science       — Analysis, discovery, hypothesis
 *   Communications — Liaison, reporting, Earth sync
 *   MissionPlanning — Risk assessment, strategy, validation
 */

import type { SacredTongue } from './drone-core.js';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** The 6 specialist mode identifiers */
export type SpecialistModeId =
  | 'engineering'
  | 'navigation'
  | 'systems'
  | 'science'
  | 'communications'
  | 'mission_planning';

/** Tool available within a mode */
export interface ModeTool {
  name: string;
  description: string;
  /** Minimum governance tier to use this tool */
  minTier: SacredTongue;
}

/** Mode state that persists across switches */
export interface ModeState {
  /** Mode-specific key-value data */
  data: Record<string, unknown>;
  /** Timestamp of last save */
  savedAt: number;
}

/** Specialist mode definition */
export interface SpecialistMode {
  id: SpecialistModeId;
  name: string;
  description: string;
  /** Category: tech or non-tech */
  category: 'tech' | 'non_tech';
  /** Available tools in this mode */
  tools: ModeTool[];
  /** Saved state (persists across mode switches) */
  state: ModeState;
}

/** Mode switch event for audit trail */
export interface ModeSwitchEvent {
  padId: string;
  fromMode: SpecialistModeId | null;
  toMode: SpecialistModeId;
  reason: string;
  timestamp: number;
}

// ═══════════════════════════════════════════════════════════════
// Mode Definitions
// ═══════════════════════════════════════════════════════════════

/** Engineering mode — repair, diagnostics, hardware */
function createEngineeringMode(): SpecialistMode {
  return {
    id: 'engineering',
    name: 'Engineering',
    description: 'Repair & diagnostics specialist',
    category: 'tech',
    tools: [
      { name: 'schematics', description: 'Hardware schematics viewer', minTier: 'KO' },
      { name: 'repair_procedures', description: 'Step-by-step repair guides', minTier: 'AV' },
      { name: 'diagnostics', description: 'Component diagnostic suite', minTier: 'RU' },
      { name: 'field_repair', description: 'Execute field repairs', minTier: 'CA' },
      { name: 'component_fabrication', description: 'In-situ fabrication control', minTier: 'UM' },
    ],
    state: { data: {}, savedAt: 0 },
  };
}

/** Navigation mode — pathfinding, terrain, SLAM */
function createNavigationMode(): SpecialistMode {
  return {
    id: 'navigation',
    name: 'Navigation',
    description: 'Pathfinding & terrain specialist',
    category: 'tech',
    tools: [
      { name: 'terrain_map', description: 'Terrain analysis & mapping', minTier: 'KO' },
      { name: 'path_planner', description: 'Route planning algorithms', minTier: 'AV' },
      { name: 'obstacle_detection', description: 'Real-time obstacle avoidance', minTier: 'RU' },
      { name: 'slam', description: 'Simultaneous localization & mapping', minTier: 'RU' },
      { name: 'dead_reckoning', description: 'GPS-denied navigation', minTier: 'CA' },
    ],
    state: { data: {}, savedAt: 0 },
  };
}

/** Systems mode — power, sensors, subsystem health */
function createSystemsMode(): SpecialistMode {
  return {
    id: 'systems',
    name: 'Systems',
    description: 'Power & sensor specialist',
    category: 'tech',
    tools: [
      { name: 'power_monitor', description: 'Battery & solar panel telemetry', minTier: 'KO' },
      { name: 'sensor_health', description: 'Sensor calibration & health', minTier: 'AV' },
      { name: 'subsystem_logs', description: 'Subsystem log analysis', minTier: 'RU' },
      { name: 'power_allocation', description: 'Dynamic power redistribution', minTier: 'CA' },
      { name: 'emergency_shutdown', description: 'Controlled subsystem shutdown', minTier: 'UM' },
    ],
    state: { data: {}, savedAt: 0 },
  };
}

/** Science mode — analysis, discovery, hypothesis */
function createScienceMode(): SpecialistMode {
  return {
    id: 'science',
    name: 'Science',
    description: 'Analysis & discovery specialist',
    category: 'non_tech',
    tools: [
      { name: 'spectrometer', description: 'Spectrometer data analysis', minTier: 'KO' },
      { name: 'sample_catalog', description: 'Sample cataloging & search', minTier: 'AV' },
      { name: 'hypothesis_engine', description: 'Hypothesis generation & testing', minTier: 'RU' },
      { name: 'lab_protocols', description: 'Lab experiment procedures', minTier: 'RU' },
      { name: 'publication_draft', description: 'Draft scientific reports', minTier: 'CA' },
    ],
    state: { data: {}, savedAt: 0 },
  };
}

/** Communications mode — liaison, reporting, Earth sync */
function createCommunicationsMode(): SpecialistMode {
  return {
    id: 'communications',
    name: 'Communications',
    description: 'Liaison & reporting specialist',
    category: 'non_tech',
    tools: [
      { name: 'message_queue', description: 'Outgoing message queue', minTier: 'KO' },
      { name: 'radio_protocols', description: 'UHF/deep-space radio protocols', minTier: 'AV' },
      { name: 'encryption', description: 'Sacred Tongue message encryption', minTier: 'RU' },
      { name: 'earth_sync', description: 'Earth contact synchronization', minTier: 'CA' },
      { name: 'emergency_beacon', description: 'SOS beacon activation', minTier: 'DR' },
    ],
    state: { data: {}, savedAt: 0 },
  };
}

/** Mission Planning mode — risk assessment, strategy, validation */
function createMissionPlanningMode(): SpecialistMode {
  return {
    id: 'mission_planning',
    name: 'Mission Planning',
    description: 'Strategy & validation specialist',
    category: 'non_tech',
    tools: [
      { name: 'risk_matrix', description: 'Risk assessment matrices', minTier: 'KO' },
      { name: 'timeline', description: 'Mission timeline management', minTier: 'AV' },
      { name: 'constraint_solver', description: 'Multi-constraint optimization', minTier: 'RU' },
      { name: 'scenario_sim', description: 'What-if scenario simulation', minTier: 'CA' },
      { name: 'abort_criteria', description: 'Mission abort evaluation', minTier: 'UM' },
    ],
    state: { data: {}, savedAt: 0 },
  };
}

// ═══════════════════════════════════════════════════════════════
// Mode Registry
// ═══════════════════════════════════════════════════════════════

/** All available specialist modes */
export const ALL_MODE_IDS: readonly SpecialistModeId[] = [
  'engineering',
  'navigation',
  'systems',
  'science',
  'communications',
  'mission_planning',
] as const;

/** Factory map for creating fresh mode instances */
const MODE_FACTORIES: Record<SpecialistModeId, () => SpecialistMode> = {
  engineering: createEngineeringMode,
  navigation: createNavigationMode,
  systems: createSystemsMode,
  science: createScienceMode,
  communications: createCommunicationsMode,
  mission_planning: createMissionPlanningMode,
};

/**
 * Mode Registry — manages all 6 modes for a single pad.
 *
 * Preserves state across mode switches (each mode saves/loads its own state).
 */
export class ModeRegistry {
  private modes: Map<SpecialistModeId, SpecialistMode> = new Map();
  private _currentMode: SpecialistModeId | null = null;
  private _switchHistory: ModeSwitchEvent[] = [];
  private _padId: string;

  constructor(padId: string) {
    this._padId = padId;
    // Initialize all 6 modes
    for (const id of ALL_MODE_IDS) {
      this.modes.set(id, MODE_FACTORIES[id]());
    }
  }

  /** Current active mode ID */
  get currentModeId(): SpecialistModeId | null {
    return this._currentMode;
  }

  /** Current active mode (full definition) */
  get currentMode(): SpecialistMode | null {
    return this._currentMode ? this.modes.get(this._currentMode) ?? null : null;
  }

  /** Full switch history */
  get switchHistory(): readonly ModeSwitchEvent[] {
    return this._switchHistory;
  }

  /**
   * Switch to a specialist mode.
   *
   * Saves current mode state before switching, loads target mode state.
   * Returns the ModeSwitchEvent for audit logging.
   */
  switchMode(targetMode: SpecialistModeId, reason: string): ModeSwitchEvent {
    const target = this.modes.get(targetMode);
    if (!target) {
      throw new Error(`Unknown mode: ${targetMode}`);
    }

    // Save current mode state
    if (this._currentMode) {
      const current = this.modes.get(this._currentMode);
      if (current) {
        current.state.savedAt = Date.now();
      }
    }

    const event: ModeSwitchEvent = {
      padId: this._padId,
      fromMode: this._currentMode,
      toMode: targetMode,
      reason,
      timestamp: Date.now(),
    };

    this._currentMode = targetMode;
    this._switchHistory.push(event);

    return event;
  }

  /** Get a specific mode by ID */
  getMode(id: SpecialistModeId): SpecialistMode | undefined {
    return this.modes.get(id);
  }

  /** Get all modes */
  getAllModes(): SpecialistMode[] {
    return Array.from(this.modes.values());
  }

  /** Save data to current mode state */
  saveData(key: string, value: unknown): void {
    if (!this._currentMode) throw new Error('No active mode');
    const mode = this.modes.get(this._currentMode)!;
    mode.state.data[key] = value;
    mode.state.savedAt = Date.now();
  }

  /** Load data from current mode state */
  loadData<T = unknown>(key: string): T | undefined {
    if (!this._currentMode) return undefined;
    const mode = this.modes.get(this._currentMode)!;
    return mode.state.data[key] as T | undefined;
  }

  /** Get available tools in current mode */
  getAvailableTools(tier: SacredTongue): ModeTool[] {
    if (!this._currentMode) return [];
    const mode = this.modes.get(this._currentMode)!;
    const tierOrder: SacredTongue[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
    const tierIndex = tierOrder.indexOf(tier);
    return mode.tools.filter((t) => tierOrder.indexOf(t.minTier) <= tierIndex);
  }

  /** Count switches */
  get switchCount(): number {
    return this._switchHistory.length;
  }

  /** Serialize for persistence */
  toJSON(): object {
    const modes: Record<string, unknown> = {};
    for (const [id, mode] of this.modes) {
      modes[id] = { state: mode.state };
    }
    return {
      padId: this._padId,
      currentMode: this._currentMode,
      modes,
      switchHistory: this._switchHistory,
    };
  }
}
