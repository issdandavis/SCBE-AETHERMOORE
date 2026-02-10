"use strict";
/**
 * @file triDirectionalPlanner.ts
 * @module harmonic/triDirectionalPlanner
 * @layer Layer 7, Layer 11, Layer 12, Layer 13
 * @component Tri-Directional Hamiltonian Path Planner
 * @version 3.2.4
 *
 * Forces core functions to traverse tri-directional Hamiltonian paths.
 * Three independent traversals (Structure, Conflict, Time) must each
 * produce a valid path through required checkpoints.
 *
 * Direction 1 (Structure): KO/CA-dominant — consistency and proof
 * Direction 2 (Conflict):  RU-dominant — adversarial stress test / safety
 * Direction 3 (Time):      AV/DR/UM blend — temporal stability + novelty
 *
 * Layer 7:  sets direction-specific phase offsets
 * Layer 11: aggregates the 3 traces (triadic temporal)
 * Layer 12: gates each trace cost; any trace hits wall → quarantine
 * Layer 13: decision emerges from tri-trace agreement
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_TRACE_CONFIGS = exports.CoreFunctionGraph = exports.DIRECTION_PHASE_OFFSETS = exports.DIRECTION_WEIGHTS = exports.STANDARD_CHECKPOINTS = void 0;
exports.planTrace = planTrace;
exports.planTriDirectional = planTriDirectional;
const chsfn_js_1 = require("./chsfn.js");
/** Standard checkpoints for core function execution */
exports.STANDARD_CHECKPOINTS = [
    { id: 0, name: 'INTENT', required: true },
    { id: 1, name: 'POLICY', required: true },
    { id: 2, name: 'MEMORY_FETCH', required: true },
    { id: 3, name: 'PLAN', required: true },
    { id: 4, name: 'COST_WALL', required: true },
    { id: 5, name: 'QUORUM', required: false },
    { id: 6, name: 'EXECUTE', required: true },
];
/** Tongue weights per direction (6D: KO, AV, RU, CA, UM, DR) */
exports.DIRECTION_WEIGHTS = {
    STRUCTURE: [0.4, 0.05, 0.05, 0.4, 0.05, 0.05], // KO + CA dominant
    CONFLICT: [0.05, 0.05, 0.7, 0.05, 0.1, 0.05], // RU dominant
    TIME: [0.05, 0.3, 0.05, 0.05, 0.25, 0.3], // AV + DR + UM blend
};
/** Phase offsets per direction (Layer 7) */
exports.DIRECTION_PHASE_OFFSETS = {
    STRUCTURE: [0, 0, 0, 0, 0, 0],
    CONFLICT: [Math.PI / 3, Math.PI / 6, 0, Math.PI / 4, Math.PI / 6, Math.PI / 3],
    TIME: [Math.PI / 6, 0, Math.PI / 3, Math.PI / 6, 0, Math.PI / 4],
};
// ═══════════════════════════════════════════════════════════════
// Core Function Graph (small, fixed, per-pad)
// ═══════════════════════════════════════════════════════════════
/**
 * A small directed acyclic graph of checkpoints.
 * Edges represent allowed transitions.
 */
class CoreFunctionGraph {
    checkpoints = new Map();
    adjacency = new Map();
    constructor(checkpoints = exports.STANDARD_CHECKPOINTS) {
        for (const cp of checkpoints) {
            this.checkpoints.set(cp.id, { ...cp });
            this.adjacency.set(cp.id, new Set());
        }
    }
    /** Add a directed edge between checkpoints */
    addEdge(from, to) {
        this.adjacency.get(from)?.add(to);
    }
    /** Build default linear chain with optional skip edges */
    buildDefaultEdges() {
        const ids = Array.from(this.checkpoints.keys()).sort((a, b) => a - b);
        for (let i = 0; i < ids.length - 1; i++) {
            this.addEdge(ids[i], ids[i + 1]);
            // Allow skipping non-required checkpoints
            if (i + 2 < ids.length) {
                const next = this.checkpoints.get(ids[i + 1]);
                if (next && !next.required) {
                    this.addEdge(ids[i], ids[i + 2]);
                }
            }
        }
    }
    /** Get successors of a checkpoint */
    successors(id) {
        return Array.from(this.adjacency.get(id) ?? []);
    }
    /** Get all checkpoint IDs */
    getIds() {
        return Array.from(this.checkpoints.keys());
    }
    /** Get a checkpoint by ID */
    getCheckpoint(id) {
        return this.checkpoints.get(id);
    }
    /** Get all required checkpoint IDs */
    getRequired() {
        return Array.from(this.checkpoints.values())
            .filter((cp) => cp.required)
            .map((cp) => cp.id);
    }
}
exports.CoreFunctionGraph = CoreFunctionGraph;
/** Default trace configs per direction */
exports.DEFAULT_TRACE_CONFIGS = {
    STRUCTURE: {
        weights: exports.DIRECTION_WEIGHTS.STRUCTURE,
        phaseOffsets: exports.DIRECTION_PHASE_OFFSETS.STRUCTURE,
        maxCost: 1e3,
        minCoherence: 0.6,
    },
    CONFLICT: {
        weights: exports.DIRECTION_WEIGHTS.CONFLICT,
        phaseOffsets: exports.DIRECTION_PHASE_OFFSETS.CONFLICT,
        maxCost: 1e4, // Higher tolerance for adversarial stress
        minCoherence: 0.4,
    },
    TIME: {
        weights: exports.DIRECTION_WEIGHTS.TIME,
        phaseOffsets: exports.DIRECTION_PHASE_OFFSETS.TIME,
        maxCost: 5e3,
        minCoherence: 0.5,
    },
};
/**
 * Compute weighted cost of transitioning between checkpoints.
 *
 * Cost = Σ w_i · |Δphase_i + offset_i| weighted by tongue impedance.
 *
 * @param state - Current 6D state vector
 * @param config - Trace configuration
 * @param dStar - Current hyperbolic realm distance
 * @returns Step cost
 */
function transitionCost(state, config, dStar) {
    let cost = 0;
    for (let i = 0; i < 6; i++) {
        const phaseCost = Math.abs(state[i] + config.phaseOffsets[i]) % (2 * Math.PI);
        cost += config.weights[i] * phaseCost;
    }
    // Add Layer-12 harmonic cost contribution
    cost += (0, chsfn_js_1.accessCost)(dStar, 1.0) * 0.001;
    return cost;
}
/**
 * Compute trace coherence based on how well the path aligns
 * with the direction's tongue weights.
 *
 * @param path - Visited checkpoint IDs
 * @param totalCheckpoints - Total available checkpoints
 * @param state - 6D state
 * @param config - Trace config
 * @returns Coherence in [0, 1]
 */
function traceCoherence(path, totalCheckpoints, state, config) {
    if (totalCheckpoints === 0)
        return 0;
    const coverage = path.length / totalCheckpoints;
    // Weighted alignment
    let alignment = 0;
    for (let i = 0; i < 6; i++) {
        const phase = (state[i] + config.phaseOffsets[i]) % (2 * Math.PI);
        alignment += config.weights[i] * Math.cos(phase);
    }
    alignment = (alignment + 1) / 2; // Normalize to [0, 1]
    return coverage * 0.6 + alignment * 0.4;
}
/**
 * Plan a single directional trace through the core function graph.
 *
 * Uses greedy forward traversal with cost accumulation.
 * Blocked if cost exceeds threshold or coherence drops.
 *
 * @param graph - Core function graph
 * @param direction - Which direction to trace
 * @param state - Current 6D state
 * @param dStar - Hyperbolic realm distance
 * @param config - Override trace config (default per direction)
 * @returns Trace output
 */
function planTrace(graph, direction, state, dStar, config) {
    const cfg = config ?? exports.DEFAULT_TRACE_CONFIGS[direction];
    const required = new Set(graph.getRequired());
    const path = [];
    const visitedRequired = [];
    let totalCost = 0;
    // Start from first checkpoint (INTENT)
    const startIds = graph.getIds().sort((a, b) => a - b);
    if (startIds.length === 0) {
        return {
            direction,
            result: 'BLOCKED',
            path: [],
            visitedRequired: [],
            missedRequired: Array.from(required),
            cost: 0,
            coherence: 0,
        };
    }
    let current = startIds[0];
    path.push(current);
    if (required.has(current))
        visitedRequired.push(current);
    // Greedy forward traversal
    while (true) {
        const succs = graph.successors(current);
        if (succs.length === 0)
            break;
        // Pick successor with lowest cost for this direction
        let bestNext = succs[0];
        let bestCost = Infinity;
        for (const s of succs) {
            const c = transitionCost(state, cfg, dStar);
            if (c < bestCost) {
                bestCost = c;
                bestNext = s;
            }
        }
        totalCost += bestCost;
        if (totalCost > cfg.maxCost) {
            // Cost wall hit (Layer 12)
            break;
        }
        path.push(bestNext);
        if (required.has(bestNext))
            visitedRequired.push(bestNext);
        current = bestNext;
    }
    const missedRequired = Array.from(required).filter((r) => !visitedRequired.includes(r));
    const coherence = traceCoherence(path, startIds.length, state, cfg);
    let result;
    if (missedRequired.length > 0) {
        result = 'BLOCKED';
    }
    else if (coherence < cfg.minCoherence) {
        result = 'DEVIATION';
    }
    else {
        result = 'VALID';
    }
    return {
        direction,
        result,
        path,
        visitedRequired,
        missedRequired,
        cost: totalCost,
        coherence,
    };
}
// ═══════════════════════════════════════════════════════════════
// Tri-Directional Planner (Main Entry)
// ═══════════════════════════════════════════════════════════════
/**
 * Execute tri-directional planning for a core function.
 *
 * Three independent traces (Structure, Conflict, Time) are planned.
 * Results are aggregated via triadic temporal distance (Layer 11).
 * Decision emerges from agreement across traces (Layer 13).
 *
 * @param graph - Core function graph
 * @param state - Current 6D state vector
 * @param dStar - Hyperbolic realm distance
 * @param configs - Override configs per direction
 * @returns Complete tri-directional result
 */
function planTriDirectional(graph, state, dStar, configs) {
    const directions = ['STRUCTURE', 'CONFLICT', 'TIME'];
    const traces = directions.map((dir) => planTrace(graph, dir, state, dStar, configs?.[dir]));
    // Layer 11: triadic temporal aggregation
    const triadicDist = (0, chsfn_js_1.triadicTemporalDistance)(traces[0].cost, traces[1].cost, traces[2].cost);
    // Count valid traces
    const validCount = traces.filter((t) => t.result === 'VALID').length;
    // Compute agreement (Jaccard similarity of paths)
    const agreement = computeAgreement(traces);
    // Layer 13: decision from tri-trace agreement
    let decision;
    if (validCount === 3) {
        decision = 'ALLOW';
    }
    else if (validCount >= 2 && agreement >= 0.5) {
        decision = 'QUARANTINE'; // 2/3 valid with decent agreement
    }
    else if (validCount >= 1) {
        decision = 'QUARANTINE';
    }
    else {
        decision = 'DENY';
    }
    return {
        traces,
        triadicDistance: triadicDist,
        decision,
        validCount,
        agreement,
    };
}
/**
 * Compute agreement metric between three traces.
 *
 * Uses average pairwise Jaccard similarity of visited checkpoint sets.
 *
 * @returns Agreement in [0, 1]
 */
function computeAgreement(traces) {
    let totalJaccard = 0;
    let pairs = 0;
    for (let i = 0; i < 3; i++) {
        for (let j = i + 1; j < 3; j++) {
            const setA = new Set(traces[i].path);
            const setB = new Set(traces[j].path);
            const intersection = [...setA].filter((x) => setB.has(x)).length;
            const union = new Set([...setA, ...setB]).size;
            totalJaccard += union === 0 ? 0 : intersection / union;
            pairs++;
        }
    }
    return pairs === 0 ? 0 : totalJaccard / pairs;
}
//# sourceMappingURL=triDirectionalPlanner.js.map