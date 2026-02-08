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

import {
  ModeActionResult,
  ModeConfig,
  ModeState,
  ModeTool,
  SpecialistMode,
  MODE_CONFIGS,
} from './types';

/**
 * Abstract base class for specialist modes.
 *
 * Each Polly Pad has 6 mode instances (one per specialist). Mode state
 * persists across switches — when you switch away and back, your previous
 * work is still there (like browser tabs).
 */
export abstract class BaseMode {
  readonly mode: SpecialistMode;
  readonly config: ModeConfig;

  /** Persisted state data (survives mode switches) */
  protected stateData: Record<string, unknown> = {};
  /** When this mode was last activated */
  protected lastActivatedAt: number = 0;
  /** When this mode was last deactivated */
  protected lastDeactivatedAt: number = 0;
  /** Total activation count */
  protected activations: number = 0;
  /** Cumulative time spent in this mode (ms) */
  protected cumulativeTimeMs: number = 0;
  /** Whether this mode is currently active */
  protected _active: boolean = false;
  /** Action history for this mode */
  protected actionHistory: ModeActionResult[] = [];

  constructor(mode: SpecialistMode) {
    this.mode = mode;
    this.config = MODE_CONFIGS[mode];
  }

  get active(): boolean {
    return this._active;
  }

  get displayName(): string {
    return this.config.displayName;
  }

  get tools(): ModeTool[] {
    return this.config.tools;
  }

  get totalTimeMs(): number {
    if (this._active && this.lastActivatedAt > 0) {
      return this.cumulativeTimeMs + (Date.now() - this.lastActivatedAt);
    }
    return this.cumulativeTimeMs;
  }

  /**
   * Activate this mode. Called when switching TO this mode.
   */
  activate(): void {
    this._active = true;
    this.lastActivatedAt = Date.now();
    this.activations++;
    this.onActivate();
  }

  /**
   * Deactivate this mode. Called when switching AWAY from this mode.
   * State is preserved for when the mode is reactivated.
   */
  deactivate(): void {
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
  executeAction(action: string, params: Record<string, unknown> = {}): ModeActionResult {
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
  saveState(): ModeState {
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
  loadState(state: ModeState): void {
    if (state.mode !== this.mode) return;
    this.stateData = { ...state.data };
    this.activations = state.activationCount;
    this.cumulativeTimeMs = state.totalTimeMs;
  }

  /**
   * Get recent action history.
   */
  getActionHistory(limit: number = 20): ModeActionResult[] {
    return this.actionHistory.slice(-limit);
  }

  /** Hook: called when mode is activated */
  protected abstract onActivate(): void;

  /** Hook: called when mode is deactivated */
  protected abstract onDeactivate(): void;

  /** Mode-specific action execution */
  protected abstract doExecuteAction(
    action: string,
    params: Record<string, unknown>
  ): ModeActionResult;
}
