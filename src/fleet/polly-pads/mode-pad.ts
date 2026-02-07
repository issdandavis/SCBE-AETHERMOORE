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
import {
  BaseMode,
  SpecialistMode,
  ModeState,
  ModeSwitchEvent,
  ModeActionResult,
  MODE_CONFIGS,
  createAllModes,
} from './modes/index';

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
export class ModePad {
  readonly agentId: string;
  readonly tongue: SacredTongue;
  readonly name: string;

  /** All 6 specialist mode instances */
  private modes: Map<SpecialistMode, BaseMode>;
  /** Currently active mode */
  private _currentMode: BaseMode | null = null;
  /** Current mode name */
  private _currentModeName: SpecialistMode | null = null;
  /** Persistent memory (survives mode switches and reboots) */
  private memory: MemoryEntry[] = [];
  /** Mode switch history for audit trail */
  private switchHistory: ModeSwitchEvent[] = [];
  /** Squad this pad belongs to */
  private _squadId: string | null = null;
  /** Current governance tier */
  private _tier: GovernanceTier;
  /** Creation timestamp */
  readonly createdAt: number;

  constructor(config: ModePadConfig) {
    this.agentId = config.agentId;
    this.tongue = config.tongue;
    this.name = config.name || `Pad-${config.agentId}`;
    this._tier = config.initialTier || 'KO';
    this.createdAt = Date.now();

    // Initialize all 6 modes
    this.modes = createAllModes();

    // Activate default mode if specified
    if (config.defaultMode) {
      this.switchMode(config.defaultMode, 'initial_activation');
    }
  }

  // === Getters ===

  get currentMode(): SpecialistMode | null {
    return this._currentModeName;
  }

  get currentModeInstance(): BaseMode | null {
    return this._currentMode;
  }

  get tier(): GovernanceTier {
    return this._tier;
  }

  get squadId(): string | null {
    return this._squadId;
  }

  get memoryCount(): number {
    return this.memory.length;
  }

  get switchCount(): number {
    return this.switchHistory.length;
  }

  // === Mode Switching ===

  /**
   * Switch to a different specialist mode.
   *
   * Saves the current mode's state before switching, then activates the new mode
   * (restoring any previously saved state). Memory persists across all switches.
   */
  switchMode(modeName: SpecialistMode, reason: string): void {
    const newMode = this.modes.get(modeName);
    if (!newMode) {
      throw new Error(`Unknown mode: ${modeName}`);
    }

    // Deactivate current mode (saves its state)
    if (this._currentMode) {
      this._currentMode.deactivate();
    }

    const previousMode = this._currentModeName;

    // Activate new mode
    newMode.activate();
    this._currentMode = newMode;
    this._currentModeName = modeName;

    // Record the switch event
    const event: ModeSwitchEvent = {
      from: previousMode,
      to: modeName,
      reason,
      timestamp: Date.now(),
      initiator: this.agentId,
    };
    this.switchHistory.push(event);

    // Store in memory
    this.storeMemory(
      `Switched to ${modeName} mode`,
      { event: 'mode_switch', from: previousMode, to: modeName, reason }
    );
  }

  /**
   * Get the available modes and their configs.
   */
  getAvailableModes(): Array<{ mode: SpecialistMode; displayName: string; active: boolean }> {
    return Array.from(this.modes.entries()).map(([name, instance]) => ({
      mode: name,
      displayName: MODE_CONFIGS[name].displayName,
      active: instance.active,
    }));
  }

  /**
   * Get mode instance by name.
   */
  getMode(modeName: SpecialistMode): BaseMode | undefined {
    return this.modes.get(modeName);
  }

  /**
   * Get mode statistics for all modes.
   */
  getModeStats(): Array<{ mode: SpecialistMode; activations: number; totalTimeMs: number }> {
    return Array.from(this.modes.entries()).map(([name, instance]) => {
      const state = instance.saveState();
      return {
        mode: name,
        activations: state.activationCount,
        totalTimeMs: state.totalTimeMs,
      };
    });
  }

  // === Actions ===

  /**
   * Execute an action in the current mode.
   */
  executeAction(action: string, params: Record<string, unknown> = {}): ModeActionResult {
    if (!this._currentMode || !this._currentModeName) {
      return {
        success: false,
        action,
        data: {},
        timestamp: Date.now(),
        confidence: 0,
        error: 'No mode is currently active. Call switchMode() first.',
      };
    }

    return this._currentMode.executeAction(action, params);
  }

  // === Memory ===

  /**
   * Store a memory entry. Memory persists across all mode switches.
   */
  storeMemory(content: string, metadata: Record<string, unknown> = {}): MemoryEntry {
    const entry: MemoryEntry = {
      id: `mem-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`,
      content,
      metadata: {
        ...metadata,
        timestamp: Date.now(),
      },
      createdAt: Date.now(),
      createdInMode: this._currentModeName || 'science',
    };

    this.memory.push(entry);

    // Keep memory bounded
    if (this.memory.length > 1000) {
      this.memory = this.memory.slice(-500);
    }

    return entry;
  }

  /**
   * Search memory entries.
   */
  searchMemory(query: string): MemoryEntry[] {
    const lowerQuery = query.toLowerCase();
    return this.memory.filter(
      (m) =>
        m.content.toLowerCase().includes(lowerQuery) ||
        JSON.stringify(m.metadata).toLowerCase().includes(lowerQuery)
    );
  }

  /**
   * Get recent memory entries.
   */
  getRecentMemory(limit: number = 20): MemoryEntry[] {
    return this.memory.slice(-limit);
  }

  // === Squad Coordination ===

  /**
   * Join a squad.
   */
  joinSquad(squadId: string): void {
    this._squadId = squadId;
    this.storeMemory(`Joined squad ${squadId}`, { event: 'squad_join', squadId });
  }

  /**
   * Leave current squad.
   */
  leaveSquad(): void {
    const oldSquad = this._squadId;
    this._squadId = null;
    if (oldSquad) {
      this.storeMemory(`Left squad ${oldSquad}`, { event: 'squad_leave', squadId: oldSquad });
    }
  }

  /**
   * Update governance tier.
   */
  setTier(tier: GovernanceTier): void {
    this._tier = tier;
  }

  // === Audit ===

  /**
   * Get mode switch history.
   */
  getSwitchHistory(limit?: number): ModeSwitchEvent[] {
    if (limit) {
      return this.switchHistory.slice(-limit);
    }
    return [...this.switchHistory];
  }

  // === Persistence ===

  /**
   * Serialize the pad state for persistence (survives reboots).
   */
  toJSON(): Record<string, unknown> {
    const modeStates: Record<string, ModeState> = {};
    for (const [name, instance] of this.modes) {
      modeStates[name] = instance.saveState();
    }

    return {
      agentId: this.agentId,
      tongue: this.tongue,
      name: this.name,
      tier: this._tier,
      currentMode: this._currentModeName,
      squadId: this._squadId,
      memory: this.memory,
      switchHistory: this.switchHistory,
      modeStates,
      createdAt: this.createdAt,
      savedAt: Date.now(),
    };
  }

  /**
   * Restore pad state from persistence.
   */
  static fromJSON(data: Record<string, unknown>): ModePad {
    const pad = new ModePad({
      agentId: data.agentId as string,
      tongue: data.tongue as SacredTongue,
      name: data.name as string,
      initialTier: data.tier as GovernanceTier,
    });

    // Restore memory
    if (Array.isArray(data.memory)) {
      pad.memory = data.memory as MemoryEntry[];
    }

    // Restore switch history
    if (Array.isArray(data.switchHistory)) {
      pad.switchHistory = data.switchHistory as ModeSwitchEvent[];
    }

    // Restore squad
    if (data.squadId) {
      pad._squadId = data.squadId as string;
    }

    // Restore mode states
    const modeStates = data.modeStates as Record<string, ModeState> | undefined;
    if (modeStates) {
      for (const [name, state] of Object.entries(modeStates)) {
        const mode = pad.modes.get(name as SpecialistMode);
        if (mode) {
          mode.loadState(state);
        }
      }
    }

    // Reactivate current mode
    if (data.currentMode) {
      pad.switchMode(data.currentMode as SpecialistMode, 'restored_from_persistence');
    }

    return pad;
  }
}
