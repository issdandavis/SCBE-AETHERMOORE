"use strict";
/**
 * @file polly-pad-runtime.ts
 * @module fleet/polly-pad-runtime
 * @layer Layer 8, Layer 12, Layer 13
 * @component Polly Pad Runtime — Dual-Zone Squad Workspaces
 * @version 3.2.4
 *
 * Extends Polly Pads into full agent runtimes with:
 * - Dual code zones (HOT exploratory + SAFE execution)
 * - Squad code space (shared, quorum-gated memory)
 * - Proximity tracking (decimal / geodesic)
 * - Per-pad AI code assistance with tool gating
 * - SCBE decision gating for zone promotion
 *
 * Each unit/drone/AI has 6 Polly Pads (one per PadMode),
 * each with its own assistant, memory namespace, and safety envelope.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.SquadSpace = exports.PAD_TOOL_MATRIX = void 0;
exports.createUnitState = createUnitState;
exports.createPadRuntime = createPadRuntime;
exports.canPromoteToSafe = canPromoteToSafe;
exports.promotePad = promotePad;
exports.demotePad = demotePad;
exports.getAvailableTools = getAvailableTools;
exports.routeTask = routeTask;
exports.unitDistance = unitDistance;
exports.createUnitRuntime = createUnitRuntime;
exports.padNamespaceKey = padNamespaceKey;
const scbe_voxel_types_js_1 = require("../harmonic/scbe_voxel_types.js");
const voxelRecord_js_1 = require("../harmonic/voxelRecord.js");
/** Allowed tools per PadMode × CodeZone */
exports.PAD_TOOL_MATRIX = {
    ENGINEERING: {
        SAFE: ['build', 'deploy', 'config'],
        HOT: ['plan_only', 'build'],
    },
    NAVIGATION: {
        SAFE: ['map', 'proximity'],
        HOT: ['plan_only', 'map'],
    },
    SYSTEMS: {
        SAFE: ['telemetry', 'config', 'policy'],
        HOT: ['plan_only', 'telemetry'],
    },
    SCIENCE: {
        SAFE: ['hypothesis', 'experiment'],
        HOT: ['plan_only', 'hypothesis'],
    },
    COMMS: {
        SAFE: ['radio', 'encrypt'],
        HOT: ['plan_only', 'radio'],
    },
    MISSION: {
        SAFE: ['goals', 'constraints', 'policy'],
        HOT: ['plan_only', 'goals'],
    },
};
/** Create a UnitState with defaults */
function createUnitState(unitId, x = 0, y = 0, z = 0, overrides) {
    return {
        unitId,
        x,
        y,
        z,
        vx: 0,
        vy: 0,
        vz: 0,
        coherence: 1.0,
        dStar: 0,
        hEff: 0,
        ...overrides,
    };
}
/**
 * Create a Polly Pad runtime for a unit.
 *
 * All pads start in HOT zone (exploratory). Promotion to SAFE
 * requires SCBE ALLOW decision + optional quorum.
 */
function createPadRuntime(unitId, mode, thresholds = voxelRecord_js_1.DEFAULT_THRESHOLDS) {
    const zone = 'HOT';
    return {
        unitId,
        mode,
        zone,
        tongue: scbe_voxel_types_js_1.PAD_MODE_TONGUE[mode],
        tools: exports.PAD_TOOL_MATRIX[mode][zone],
        thresholds,
    };
}
/**
 * Check if a pad can promote from HOT → SAFE.
 *
 * Promotion requires:
 * 1. SCBE decision == ALLOW
 * 2. H_eff < allow_max_cost
 * 3. coherence >= allow_min_coherence
 * 4. Optional: ≥4/6 squad quorum
 *
 * @returns true if promotion is allowed
 */
function canPromoteToSafe(pad, state, quorumVotes) {
    const decision = (0, voxelRecord_js_1.scbeDecide)(state.dStar, state.coherence, state.hEff, pad.thresholds);
    if (decision !== 'ALLOW')
        return false;
    if (quorumVotes !== undefined && quorumVotes < 4)
        return false;
    return true;
}
/**
 * Promote a pad from HOT → SAFE, updating its available tools.
 *
 * @returns New pad runtime in SAFE zone, or null if not promotable
 */
function promotePad(pad, state, quorumVotes) {
    if (!canPromoteToSafe(pad, state, quorumVotes))
        return null;
    return {
        ...pad,
        zone: 'SAFE',
        tools: exports.PAD_TOOL_MATRIX[pad.mode]['SAFE'],
    };
}
/**
 * Demote a pad from SAFE → HOT (on coherence drop, etc).
 */
function demotePad(pad) {
    return {
        ...pad,
        zone: 'HOT',
        tools: exports.PAD_TOOL_MATRIX[pad.mode]['HOT'],
    };
}
/**
 * Get the tools currently available to a pad.
 */
function getAvailableTools(pad) {
    return exports.PAD_TOOL_MATRIX[pad.mode][pad.zone];
}
/**
 * Route a task to appropriate tools based on pad mode + zone.
 *
 * @returns Comma-separated tool string (e.g. "tools:build,tools:deploy")
 */
function routeTask(pad) {
    return pad.tools.map((t) => `tools:${t}`).join(',');
}
// ═══════════════════════════════════════════════════════════════
// Squad Space (shared + quorum-gated)
// ═══════════════════════════════════════════════════════════════
/** Euclidean distance between two units */
function unitDistance(a, b) {
    return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2);
}
/** Squad space: overlay of multiple units' quasi-spheres */
class SquadSpace {
    squadId;
    units = new Map();
    constructor(squadId) {
        this.squadId = squadId;
    }
    /** Register or update a unit */
    setUnit(state) {
        this.units.set(state.unitId, state);
    }
    /** Remove a unit */
    removeUnit(unitId) {
        this.units.delete(unitId);
    }
    /** Get a unit by ID */
    getUnit(unitId) {
        return this.units.get(unitId);
    }
    /** Get all unit IDs */
    getUnitIds() {
        return Array.from(this.units.keys());
    }
    /** Get unit count */
    get size() {
        return this.units.size;
    }
    /**
     * Compute proximity graph: which units are within radius of each other.
     *
     * @param radius - Max distance for neighbor relation
     * @returns Map from unitId → list of neighbor unitIds
     */
    neighbors(radius) {
        const ids = Array.from(this.units.keys());
        const result = new Map();
        for (const id of ids)
            result.set(id, []);
        for (let i = 0; i < ids.length; i++) {
            for (let j = i + 1; j < ids.length; j++) {
                const a = this.units.get(ids[i]);
                const b = this.units.get(ids[j]);
                if (unitDistance(a, b) <= radius) {
                    result.get(ids[i]).push(ids[j]);
                    result.get(ids[j]).push(ids[i]);
                }
            }
        }
        return result;
    }
    /**
     * Find the consensus topic leader: unit with lowest hEff + highest coherence.
     *
     * Leader = argmin(hEff - coherence * 1000)
     *
     * @returns Leader unit ID, or undefined if squad is empty
     */
    findLeader() {
        let bestId;
        let bestScore = Infinity;
        for (const [id, state] of this.units) {
            const score = state.hEff - state.coherence * 1000;
            if (score < bestScore) {
                bestScore = score;
                bestId = id;
            }
        }
        return bestId;
    }
    /**
     * Check Byzantine quorum for squad-level commit.
     *
     * @param votes - Number of agreeing votes
     * @param n - Total agents (default 6)
     * @param threshold - Required votes (default 4, BFT: 3f+1)
     * @returns true if quorum is met
     */
    quorumOk(votes, n = 6, threshold = 4) {
        // BFT rule: n >= 3f + 1 where f = floor((n - 1) / 3)
        // For n=6: f=1, threshold=3f+1=4
        const f = Math.floor((n - 1) / 3);
        return votes >= threshold && n >= 3 * f + 1 && threshold >= 2 * f + 1;
    }
    /**
     * Compute squad-level coherence: average coherence of all units.
     */
    averageCoherence() {
        if (this.units.size === 0)
            return 0;
        let sum = 0;
        for (const state of this.units.values())
            sum += state.coherence;
        return sum / this.units.size;
    }
    /**
     * Compute risk field: map of unit positions → SCBE decision.
     *
     * @param thresholds - SCBE thresholds
     * @returns Map from unitId → Decision
     */
    riskField(thresholds = voxelRecord_js_1.DEFAULT_THRESHOLDS) {
        const result = new Map();
        for (const [id, state] of this.units) {
            result.set(id, (0, voxelRecord_js_1.scbeDecide)(state.dStar, state.coherence, state.hEff, thresholds));
        }
        return result;
    }
}
exports.SquadSpace = SquadSpace;
/**
 * Create a complete unit runtime with all 6 Polly Pads.
 *
 * @param unitId - Unique unit identifier
 * @param squadId - Squad this unit belongs to
 * @param position - Initial 3D position [x, y, z]
 * @param thresholds - SCBE thresholds for all pads
 * @returns UnitRuntime with 6 HOT pads
 */
function createUnitRuntime(unitId, squadId, position = [0, 0, 0], thresholds = voxelRecord_js_1.DEFAULT_THRESHOLDS) {
    const state = createUnitState(unitId, position[0], position[1], position[2]);
    const pads = new Map();
    for (const mode of scbe_voxel_types_js_1.PAD_MODES) {
        pads.set(mode, createPadRuntime(unitId, mode, thresholds));
    }
    return { state, pads, squadId };
}
/**
 * Generate a voxel namespace key for a pad's memory.
 *
 * Key format: (unitId, padMode, lang, epoch)
 * This ensures the same "thought" can exist in different Pads without contamination.
 */
function padNamespaceKey(unitId, padMode, lang, epoch) {
    return `${unitId}:${padMode}:${lang}:${epoch}`;
}
//# sourceMappingURL=polly-pad-runtime.js.map