"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.BaseMode = void 0;
const types_1 = require("./types");
/**
 * Abstract base class for specialist modes.
 *
 * Each Polly Pad has 6 mode instances (one per specialist). Mode state
 * persists across switches — when you switch away and back, your previous
 * work is still there (like browser tabs).
 */
class BaseMode {
    mode;
    config;
    /** Persisted state data (survives mode switches) */
    stateData = {};
    /** When this mode was last activated */
    lastActivatedAt = 0;
    /** When this mode was last deactivated */
    lastDeactivatedAt = 0;
    /** Total activation count */
    activations = 0;
    /** Cumulative time spent in this mode (ms) */
    cumulativeTimeMs = 0;
    /** Whether this mode is currently active */
    _active = false;
    /** Action history for this mode */
    actionHistory = [];
    constructor(mode) {
        this.mode = mode;
        this.config = types_1.MODE_CONFIGS[mode];
    }
    get active() {
        return this._active;
    }
    get displayName() {
        return this.config.displayName;
    }
    get tools() {
        return this.config.tools;
    }
    get totalTimeMs() {
        if (this._active && this.lastActivatedAt > 0) {
            return this.cumulativeTimeMs + (Date.now() - this.lastActivatedAt);
        }
        return this.cumulativeTimeMs;
    }
    /**
     * Activate this mode. Called when switching TO this mode.
     */
    activate() {
        this._active = true;
        this.lastActivatedAt = Date.now();
        this.activations++;
        this.onActivate();
    }
    /**
     * Deactivate this mode. Called when switching AWAY from this mode.
     * State is preserved for when the mode is reactivated.
     */
    deactivate() {
        if (this._active && this.lastActivatedAt > 0) {
            this.cumulativeTimeMs += Date.now() - this.lastActivatedAt;
        }
        this._active = false;
        this.lastDeactivatedAt = Date.now();
        this.onDeactivate();
    }
    /**
     * Execute a mode-specific action.
     */
    executeAction(action, params = {}) {
        if (!this._active) {
            return {
                success: false,
                action,
                data: {},
                timestamp: Date.now(),
                confidence: 0,
                error: `Mode ${this.mode} is not active`,
            };
        }
        const result = this.doExecuteAction(action, params);
        this.actionHistory.push(result);
        // Keep history bounded
        if (this.actionHistory.length > 200) {
            this.actionHistory = this.actionHistory.slice(-100);
        }
        return result;
    }
    /**
     * Get the current mode state for persistence.
     */
    saveState() {
        return {
            mode: this.mode,
            data: { ...this.stateData },
            savedAt: Date.now(),
            activationCount: this.activations,
            totalTimeMs: this.totalTimeMs,
        };
    }
    /**
     * Restore mode state from persistence.
     */
    loadState(state) {
        if (state.mode !== this.mode)
            return;
        this.stateData = { ...state.data };
        this.activations = state.activationCount;
        this.cumulativeTimeMs = state.totalTimeMs;
    }
    /**
     * Get recent action history.
     */
    getActionHistory(limit = 20) {
        return this.actionHistory.slice(-limit);
    }
}
exports.BaseMode = BaseMode;
//# sourceMappingURL=base-mode.js.map