"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.ModePad = void 0;
const index_1 = require("./modes/index");
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
class ModePad {
    agentId;
    tongue;
    name;
    /** All 6 specialist mode instances */
    modes;
    /** Currently active mode */
    _currentMode = null;
    /** Current mode name */
    _currentModeName = null;
    /** Persistent memory (survives mode switches and reboots) */
    memory = [];
    /** Mode switch history for audit trail */
    switchHistory = [];
    /** Squad this pad belongs to */
    _squadId = null;
    /** Current governance tier */
    _tier;
    /** Creation timestamp */
    createdAt;
    constructor(config) {
        this.agentId = config.agentId;
        this.tongue = config.tongue;
        this.name = config.name || `Pad-${config.agentId}`;
        this._tier = config.initialTier || 'KO';
        this.createdAt = Date.now();
        // Initialize all 6 modes
        this.modes = (0, index_1.createAllModes)();
        // Activate default mode if specified
        if (config.defaultMode) {
            this.switchMode(config.defaultMode, 'initial_activation');
        }
    }
    // === Getters ===
    get currentMode() {
        return this._currentModeName;
    }
    get currentModeInstance() {
        return this._currentMode;
    }
    get tier() {
        return this._tier;
    }
    get squadId() {
        return this._squadId;
    }
    get memoryCount() {
        return this.memory.length;
    }
    get switchCount() {
        return this.switchHistory.length;
    }
    // === Mode Switching ===
    /**
     * Switch to a different specialist mode.
     *
     * Saves the current mode's state before switching, then activates the new mode
     * (restoring any previously saved state). Memory persists across all switches.
     */
    switchMode(modeName, reason) {
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
        const event = {
            from: previousMode,
            to: modeName,
            reason,
            timestamp: Date.now(),
            initiator: this.agentId,
        };
        this.switchHistory.push(event);
        // Store in memory
        this.storeMemory(`Switched to ${modeName} mode`, { event: 'mode_switch', from: previousMode, to: modeName, reason });
    }
    /**
     * Get the available modes and their configs.
     */
    getAvailableModes() {
        return Array.from(this.modes.entries()).map(([name, instance]) => ({
            mode: name,
            displayName: index_1.MODE_CONFIGS[name].displayName,
            active: instance.active,
        }));
    }
    /**
     * Get mode instance by name.
     */
    getMode(modeName) {
        return this.modes.get(modeName);
    }
    /**
     * Get mode statistics for all modes.
     */
    getModeStats() {
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
    executeAction(action, params = {}) {
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
    storeMemory(content, metadata = {}) {
        const entry = {
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
    searchMemory(query) {
        const lowerQuery = query.toLowerCase();
        return this.memory.filter((m) => m.content.toLowerCase().includes(lowerQuery) ||
            JSON.stringify(m.metadata).toLowerCase().includes(lowerQuery));
    }
    /**
     * Get recent memory entries.
     */
    getRecentMemory(limit = 20) {
        return this.memory.slice(-limit);
    }
    // === Squad Coordination ===
    /**
     * Join a squad.
     */
    joinSquad(squadId) {
        this._squadId = squadId;
        this.storeMemory(`Joined squad ${squadId}`, { event: 'squad_join', squadId });
    }
    /**
     * Leave current squad.
     */
    leaveSquad() {
        const oldSquad = this._squadId;
        this._squadId = null;
        if (oldSquad) {
            this.storeMemory(`Left squad ${oldSquad}`, { event: 'squad_leave', squadId: oldSquad });
        }
    }
    /**
     * Update governance tier.
     */
    setTier(tier) {
        this._tier = tier;
    }
    // === Audit ===
    /**
     * Get mode switch history.
     */
    getSwitchHistory(limit) {
        if (limit) {
            return this.switchHistory.slice(-limit);
        }
        return [...this.switchHistory];
    }
    // === Persistence ===
    /**
     * Serialize the pad state for persistence (survives reboots).
     */
    toJSON() {
        const modeStates = {};
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
    static fromJSON(data) {
        const pad = new ModePad({
            agentId: data.agentId,
            tongue: data.tongue,
            name: data.name,
            initialTier: data.tier,
        });
        // Restore memory
        if (Array.isArray(data.memory)) {
            pad.memory = data.memory;
        }
        // Restore switch history
        if (Array.isArray(data.switchHistory)) {
            pad.switchHistory = data.switchHistory;
        }
        // Restore squad
        if (data.squadId) {
            pad._squadId = data.squadId;
        }
        // Restore mode states
        const modeStates = data.modeStates;
        if (modeStates) {
            for (const [name, state] of Object.entries(modeStates)) {
                const mode = pad.modes.get(name);
                if (mode) {
                    mode.loadState(state);
                }
            }
        }
        // Reactivate current mode
        if (data.currentMode) {
            pad.switchMode(data.currentMode, 'restored_from_persistence');
        }
        return pad;
    }
}
exports.ModePad = ModePad;
//# sourceMappingURL=mode-pad.js.map