/**
 * @file base-mode.ts
 * @module fleet/polly-pads/modes/base-mode
 * @layer L13
 * @component Polly Pad Mode Switching
 * @version 1.0.0
 *
 * Base class for all 6 specialist modes. Each mode has its own tools,
 * persisted state, and action execution capability.
 */
import { ModeActionResult, ModeConfig, ModeState, ModeTool, SpecialistMode } from './types';
/**
 * Abstract base class for specialist modes.
 *
 * Each Polly Pad has 6 mode instances (one per specialist). Mode state
 * persists across switches — when you switch away and back, your previous
 * work is still there (like browser tabs).
 */
export declare abstract class BaseMode {
    readonly mode: SpecialistMode;
    readonly config: ModeConfig;
    /** Persisted state data (survives mode switches) */
    protected stateData: Record<string, unknown>;
    /** When this mode was last activated */
    protected lastActivatedAt: number;
    /** When this mode was last deactivated */
    protected lastDeactivatedAt: number;
    /** Total activation count */
    protected activations: number;
    /** Cumulative time spent in this mode (ms) */
    protected cumulativeTimeMs: number;
    /** Whether this mode is currently active */
    protected _active: boolean;
    /** Action history for this mode */
    protected actionHistory: ModeActionResult[];
    constructor(mode: SpecialistMode);
    get active(): boolean;
    get displayName(): string;
    get tools(): ModeTool[];
    get totalTimeMs(): number;
    /**
     * Activate this mode. Called when switching TO this mode.
     */
    activate(): void;
    /**
     * Deactivate this mode. Called when switching AWAY from this mode.
     * State is preserved for when the mode is reactivated.
     */
    deactivate(): void;
    /**
     * Execute a mode-specific action.
     */
    executeAction(action: string, params?: Record<string, unknown>): ModeActionResult;
    /**
     * Get the current mode state for persistence.
     */
    saveState(): ModeState;
    /**
     * Restore mode state from persistence.
     */
    loadState(state: ModeState): void;
    /**
     * Get recent action history.
     */
    getActionHistory(limit?: number): ModeActionResult[];
    /** Hook: called when mode is activated */
    protected abstract onActivate(): void;
    /** Hook: called when mode is deactivated */
    protected abstract onDeactivate(): void;
    /** Mode-specific action execution */
    protected abstract doExecuteAction(action: string, params: Record<string, unknown>): ModeActionResult;
}
//# sourceMappingURL=base-mode.d.ts.map