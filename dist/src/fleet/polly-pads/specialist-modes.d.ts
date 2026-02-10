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
/** The 6 specialist mode identifiers */
export type SpecialistModeId = 'engineering' | 'navigation' | 'systems' | 'science' | 'communications' | 'mission_planning';
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
/** All available specialist modes */
export declare const ALL_MODE_IDS: readonly SpecialistModeId[];
/**
 * Mode Registry — manages all 6 modes for a single pad.
 *
 * Preserves state across mode switches (each mode saves/loads its own state).
 */
export declare class ModeRegistry {
    private modes;
    private _currentMode;
    private _switchHistory;
    private _padId;
    constructor(padId: string);
    /** Current active mode ID */
    get currentModeId(): SpecialistModeId | null;
    /** Current active mode (full definition) */
    get currentMode(): SpecialistMode | null;
    /** Full switch history */
    get switchHistory(): readonly ModeSwitchEvent[];
    /**
     * Switch to a specialist mode.
     *
     * Saves current mode state before switching, loads target mode state.
     * Returns the ModeSwitchEvent for audit logging.
     */
    switchMode(targetMode: SpecialistModeId, reason: string): ModeSwitchEvent;
    /** Get a specific mode by ID */
    getMode(id: SpecialistModeId): SpecialistMode | undefined;
    /** Get all modes */
    getAllModes(): SpecialistMode[];
    /** Save data to current mode state */
    saveData(key: string, value: unknown): void;
    /** Load data from current mode state */
    loadData<T = unknown>(key: string): T | undefined;
    /** Get available tools in current mode */
    getAvailableTools(tier: SacredTongue): ModeTool[];
    /** Count switches */
    get switchCount(): number;
    /** Serialize for persistence */
    toJSON(): object;
}
//# sourceMappingURL=specialist-modes.d.ts.map