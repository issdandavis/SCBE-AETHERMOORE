"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.ModeRegistry = exports.ALL_MODE_IDS = void 0;
// ═══════════════════════════════════════════════════════════════
// Mode Definitions
// ═══════════════════════════════════════════════════════════════
/** Engineering mode — repair, diagnostics, hardware */
function createEngineeringMode() {
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
function createNavigationMode() {
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
function createSystemsMode() {
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
function createScienceMode() {
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
function createCommunicationsMode() {
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
function createMissionPlanningMode() {
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
exports.ALL_MODE_IDS = [
    'engineering',
    'navigation',
    'systems',
    'science',
    'communications',
    'mission_planning',
];
/** Factory map for creating fresh mode instances */
const MODE_FACTORIES = {
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
class ModeRegistry {
    modes = new Map();
    _currentMode = null;
    _switchHistory = [];
    _padId;
    constructor(padId) {
        this._padId = padId;
        // Initialize all 6 modes
        for (const id of exports.ALL_MODE_IDS) {
            this.modes.set(id, MODE_FACTORIES[id]());
        }
    }
    /** Current active mode ID */
    get currentModeId() {
        return this._currentMode;
    }
    /** Current active mode (full definition) */
    get currentMode() {
        return this._currentMode ? this.modes.get(this._currentMode) ?? null : null;
    }
    /** Full switch history */
    get switchHistory() {
        return this._switchHistory;
    }
    /**
     * Switch to a specialist mode.
     *
     * Saves current mode state before switching, loads target mode state.
     * Returns the ModeSwitchEvent for audit logging.
     */
    switchMode(targetMode, reason) {
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
        const event = {
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
    getMode(id) {
        return this.modes.get(id);
    }
    /** Get all modes */
    getAllModes() {
        return Array.from(this.modes.values());
    }
    /** Save data to current mode state */
    saveData(key, value) {
        if (!this._currentMode)
            throw new Error('No active mode');
        const mode = this.modes.get(this._currentMode);
        mode.state.data[key] = value;
        mode.state.savedAt = Date.now();
    }
    /** Load data from current mode state */
    loadData(key) {
        if (!this._currentMode)
            return undefined;
        const mode = this.modes.get(this._currentMode);
        return mode.state.data[key];
    }
    /** Get available tools in current mode */
    getAvailableTools(tier) {
        if (!this._currentMode)
            return [];
        const mode = this.modes.get(this._currentMode);
        const tierOrder = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
        const tierIndex = tierOrder.indexOf(tier);
        return mode.tools.filter((t) => tierOrder.indexOf(t.minTier) <= tierIndex);
    }
    /** Count switches */
    get switchCount() {
        return this._switchHistory.length;
    }
    /** Serialize for persistence */
    toJSON() {
        const modes = {};
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
exports.ModeRegistry = ModeRegistry;
//# sourceMappingURL=specialist-modes.js.map