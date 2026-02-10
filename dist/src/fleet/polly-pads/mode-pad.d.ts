/**
 * @file mode-pad.ts
 * @module fleet/polly-pads/mode-pad
 * @layer L13
 * @component Polly Pad with Mode Switching
 * @version 1.0.0
 *
 * Personal AI workspace with 6 specialist modes. Each pad can switch between
 * modes dynamically based on mission needs. Memory persists across mode switches
 * and reboots.
 *
 * Designed for: Mars missions, disaster response, submarine ops, autonomous fleets.
 */
import { GovernanceTier } from '../types';
import { BaseMode, SpecialistMode, ModeSwitchEvent, ModeActionResult } from './modes/index';
/**
 * Sacred Tongue assignment for domain separation.
 */
export type SacredTongue = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
/**
 * Configuration for creating a ModePad.
 */
export interface ModePadConfig {
    /** Unique agent ID */
    agentId: string;
    /** Sacred Tongue for domain separation */
    tongue: SacredTongue;
    /** Optional display name */
    name?: string;
    /** Default mode to start in */
    defaultMode?: SpecialistMode;
    /** Initial governance tier */
    initialTier?: GovernanceTier;
}
/**
 * Memory entry that persists across mode switches and reboots.
 */
export interface MemoryEntry {
    /** Unique memory ID */
    id: string;
    /** Memory content */
    content: string;
    /** Metadata tags */
    metadata: Record<string, unknown>;
    /** When this memory was created */
    createdAt: number;
    /** Which mode created this memory */
    createdInMode: SpecialistMode;
}
/**
 * ModePad — Personal AI Workspace with Mode Switching
 *
 * Each AI agent gets one of these as their personal workspace.
 * Supports 6 specialist modes, persistent memory, and squad coordination.
 *
 * @example
 * ```typescript
 * const pad = new ModePad({ agentId: 'ALPHA-001', tongue: 'KO' });
 *
 * // Start in science mode
 * pad.switchMode('science', 'Normal operations');
 * pad.executeAction('collect_sample', { location: 'crater_rim' });
 *
 * // Crisis: switch to engineering
 * pad.switchMode('engineering', 'Wheel motor failure detected');
 * const plan = pad.executeAction('generate_repair_plan', { component: 'wheel_motor_2' });
 *
 * // Switch back — science state preserved
 * pad.switchMode('science', 'Crisis resolved');
 * ```
 */
export declare class ModePad {
    readonly agentId: string;
    readonly tongue: SacredTongue;
    readonly name: string;
    /** All 6 specialist mode instances */
    private modes;
    /** Currently active mode */
    private _currentMode;
    /** Current mode name */
    private _currentModeName;
    /** Persistent memory (survives mode switches and reboots) */
    private memory;
    /** Mode switch history for audit trail */
    private switchHistory;
    /** Squad this pad belongs to */
    private _squadId;
    /** Current governance tier */
    private _tier;
    /** Creation timestamp */
    readonly createdAt: number;
    constructor(config: ModePadConfig);
    get currentMode(): SpecialistMode | null;
    get currentModeInstance(): BaseMode | null;
    get tier(): GovernanceTier;
    get squadId(): string | null;
    get memoryCount(): number;
    get switchCount(): number;
    /**
     * Switch to a different specialist mode.
     *
     * Saves the current mode's state before switching, then activates the new mode
     * (restoring any previously saved state). Memory persists across all switches.
     */
    switchMode(modeName: SpecialistMode, reason: string): void;
    /**
     * Get the available modes and their configs.
     */
    getAvailableModes(): Array<{
        mode: SpecialistMode;
        displayName: string;
        active: boolean;
    }>;
    /**
     * Get mode instance by name.
     */
    getMode(modeName: SpecialistMode): BaseMode | undefined;
    /**
     * Get mode statistics for all modes.
     */
    getModeStats(): Array<{
        mode: SpecialistMode;
        activations: number;
        totalTimeMs: number;
    }>;
    /**
     * Execute an action in the current mode.
     */
    executeAction(action: string, params?: Record<string, unknown>): ModeActionResult;
    /**
     * Store a memory entry. Memory persists across all mode switches.
     */
    storeMemory(content: string, metadata?: Record<string, unknown>): MemoryEntry;
    /**
     * Search memory entries.
     */
    searchMemory(query: string): MemoryEntry[];
    /**
     * Get recent memory entries.
     */
    getRecentMemory(limit?: number): MemoryEntry[];
    /**
     * Join a squad.
     */
    joinSquad(squadId: string): void;
    /**
     * Leave current squad.
     */
    leaveSquad(): void;
    /**
     * Update governance tier.
     */
    setTier(tier: GovernanceTier): void;
    /**
     * Get mode switch history.
     */
    getSwitchHistory(limit?: number): ModeSwitchEvent[];
    /**
     * Serialize the pad state for persistence (survives reboots).
     */
    toJSON(): Record<string, unknown>;
    /**
     * Restore pad state from persistence.
     */
    static fromJSON(data: Record<string, unknown>): ModePad;
}
//# sourceMappingURL=mode-pad.d.ts.map