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
import type { Vector6D } from './constants.js';
/** Direction identity for tri-directional planning */
export type TraceDirection = 'STRUCTURE' | 'CONFLICT' | 'TIME';
/** Result of a single trace */
export type TraceResult = 'VALID' | 'DEVIATION' | 'BLOCKED';
/** Final tri-directional decision */
export type TriDecision = 'ALLOW' | 'QUARANTINE' | 'DENY';
/** A checkpoint in the core function graph */
export interface Checkpoint {
    /** Unique checkpoint ID */
    id: number;
    /** Human-readable name */
    name: string;
    /** Required: must be visited for valid traversal */
    required: boolean;
}
/** Standard checkpoints for core function execution */
export declare const STANDARD_CHECKPOINTS: readonly Checkpoint[];
/** Tongue weights per direction (6D: KO, AV, RU, CA, UM, DR) */
export declare const DIRECTION_WEIGHTS: Record<TraceDirection, Vector6D>;
/** Phase offsets per direction (Layer 7) */
export declare const DIRECTION_PHASE_OFFSETS: Record<TraceDirection, Vector6D>;
/** Single trace result with details */
export interface TraceOutput {
    /** Which direction this trace followed */
    direction: TraceDirection;
    /** Trace result */
    result: TraceResult;
    /** Path taken (checkpoint IDs in order) */
    path: number[];
    /** Required checkpoints that were visited */
    visitedRequired: number[];
    /** Required checkpoints that were missed */
    missedRequired: number[];
    /** Accumulated cost along the trace */
    cost: number;
    /** Coherence of the trace (0-1) */
    coherence: number;
}
/** Complete tri-directional result */
export interface TriDirectionalResult {
    /** Individual trace outputs */
    traces: [TraceOutput, TraceOutput, TraceOutput];
    /** Aggregated triadic distance (Layer 11) */
    triadicDistance: number;
    /** Final decision (Layer 13) */
    decision: TriDecision;
    /** Number of valid traces (0-3) */
    validCount: number;
    /** Agreement metric: how similar the three paths are (0-1) */
    agreement: number;
}
/**
 * A small directed acyclic graph of checkpoints.
 * Edges represent allowed transitions.
 */
export declare class CoreFunctionGraph {
    private checkpoints;
    private adjacency;
    constructor(checkpoints?: readonly Checkpoint[]);
    /** Add a directed edge between checkpoints */
    addEdge(from: number, to: number): void;
    /** Build default linear chain with optional skip edges */
    buildDefaultEdges(): void;
    /** Get successors of a checkpoint */
    successors(id: number): number[];
    /** Get all checkpoint IDs */
    getIds(): number[];
    /** Get a checkpoint by ID */
    getCheckpoint(id: number): Checkpoint | undefined;
    /** Get all required checkpoint IDs */
    getRequired(): number[];
}
/** Configuration for a single trace */
export interface TraceConfig {
    /** Direction-specific tongue weights */
    weights: Vector6D;
    /** Phase offsets for Layer 7 modulation */
    phaseOffsets: Vector6D;
    /** Max cost before trace is blocked */
    maxCost: number;
    /** Min coherence for valid trace */
    minCoherence: number;
}
/** Default trace configs per direction */
export declare const DEFAULT_TRACE_CONFIGS: Record<TraceDirection, TraceConfig>;
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
export declare function planTrace(graph: CoreFunctionGraph, direction: TraceDirection, state: Vector6D, dStar: number, config?: TraceConfig): TraceOutput;
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
export declare function planTriDirectional(graph: CoreFunctionGraph, state: Vector6D, dStar: number, configs?: Partial<Record<TraceDirection, TraceConfig>>): TriDirectionalResult;
//# sourceMappingURL=triDirectionalPlanner.d.ts.map