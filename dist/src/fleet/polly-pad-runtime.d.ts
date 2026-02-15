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
import type { PadMode, Decision, Lang } from '../harmonic/scbe_voxel_types.js';
import { type SCBEThresholds } from '../harmonic/voxelRecord.js';
/** Code zone: SAFE (execution) or HOT (exploratory) */
export type CodeZone = 'SAFE' | 'HOT';
/** Tool categories available per pad */
export type ToolCategory = 'build' | 'deploy' | 'map' | 'proximity' | 'radio' | 'encrypt' | 'hypothesis' | 'experiment' | 'telemetry' | 'config' | 'policy' | 'goals' | 'constraints' | 'plan_only';
/** Allowed tools per PadMode × CodeZone */
export declare const PAD_TOOL_MATRIX: Record<PadMode, Record<CodeZone, readonly ToolCategory[]>>;
/** Physical + governance state of a single unit/drone */
export interface UnitState {
    /** Unique unit identifier */
    unitId: string;
    /** 3D position */
    x: number;
    y: number;
    z: number;
    /** 3D velocity */
    vx: number;
    vy: number;
    vz: number;
    /** NK coherence [0, 1] */
    coherence: number;
    /** Hyperbolic realm distance */
    dStar: number;
    /** Effective harmonic cost */
    hEff: number;
}
/** Create a UnitState with defaults */
export declare function createUnitState(unitId: string, x?: number, y?: number, z?: number, overrides?: Partial<UnitState>): UnitState;
/** A single Polly Pad with dual code zones */
export interface PadRuntime {
    /** Owning unit */
    unitId: string;
    /** Pad operational mode */
    mode: PadMode;
    /** Current code zone */
    zone: CodeZone;
    /** Sacred Tongue for this pad's namespace */
    tongue: Lang;
    /** Available tools in current zone */
    tools: readonly ToolCategory[];
    /** SCBE thresholds for zone promotion */
    thresholds: SCBEThresholds;
}
/**
 * Create a Polly Pad runtime for a unit.
 *
 * All pads start in HOT zone (exploratory). Promotion to SAFE
 * requires SCBE ALLOW decision + optional quorum.
 */
export declare function createPadRuntime(unitId: string, mode: PadMode, thresholds?: SCBEThresholds): PadRuntime;
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
export declare function canPromoteToSafe(pad: PadRuntime, state: UnitState, quorumVotes?: number): boolean;
/**
 * Promote a pad from HOT → SAFE, updating its available tools.
 *
 * @returns New pad runtime in SAFE zone, or null if not promotable
 */
export declare function promotePad(pad: PadRuntime, state: UnitState, quorumVotes?: number): PadRuntime | null;
/**
 * Demote a pad from SAFE → HOT (on coherence drop, etc).
 */
export declare function demotePad(pad: PadRuntime): PadRuntime;
/**
 * Get the tools currently available to a pad.
 */
export declare function getAvailableTools(pad: PadRuntime): readonly ToolCategory[];
/**
 * Route a task to appropriate tools based on pad mode + zone.
 *
 * @returns Comma-separated tool string (e.g. "tools:build,tools:deploy")
 */
export declare function routeTask(pad: PadRuntime): string;
/** Euclidean distance between two units */
export declare function unitDistance(a: UnitState, b: UnitState): number;
/** Squad space: overlay of multiple units' quasi-spheres */
export declare class SquadSpace {
    readonly squadId: string;
    private units;
    constructor(squadId: string);
    /** Register or update a unit */
    setUnit(state: UnitState): void;
    /** Remove a unit */
    removeUnit(unitId: string): void;
    /** Get a unit by ID */
    getUnit(unitId: string): UnitState | undefined;
    /** Get all unit IDs */
    getUnitIds(): string[];
    /** Get unit count */
    get size(): number;
    /**
     * Compute proximity graph: which units are within radius of each other.
     *
     * @param radius - Max distance for neighbor relation
     * @returns Map from unitId → list of neighbor unitIds
     */
    neighbors(radius: number): Map<string, string[]>;
    /**
     * Find the consensus topic leader: unit with lowest hEff + highest coherence.
     *
     * Leader = argmin(hEff - coherence * 1000)
     *
     * @returns Leader unit ID, or undefined if squad is empty
     */
    findLeader(): string | undefined;
    /**
     * Check Byzantine quorum for squad-level commit.
     *
     * @param votes - Number of agreeing votes
     * @param n - Total agents (default 6)
     * @param threshold - Required votes (default 4, BFT: 3f+1)
     * @returns true if quorum is met
     */
    quorumOk(votes: number, n?: number, threshold?: number): boolean;
    /**
     * Compute squad-level coherence: average coherence of all units.
     */
    averageCoherence(): number;
    /**
     * Compute risk field: map of unit positions → SCBE decision.
     *
     * @param thresholds - SCBE thresholds
     * @returns Map from unitId → Decision
     */
    riskField(thresholds?: SCBEThresholds): Map<string, Decision>;
}
/** Complete unit runtime: 6 pads + state + squad link */
export interface UnitRuntime {
    /** Unit state (position, velocity, governance) */
    state: UnitState;
    /** Six Polly Pads, one per mode */
    pads: Map<PadMode, PadRuntime>;
    /** Squad membership */
    squadId: string;
}
/**
 * Create a complete unit runtime with all 6 Polly Pads.
 *
 * @param unitId - Unique unit identifier
 * @param squadId - Squad this unit belongs to
 * @param position - Initial 3D position [x, y, z]
 * @param thresholds - SCBE thresholds for all pads
 * @returns UnitRuntime with 6 HOT pads
 */
export declare function createUnitRuntime(unitId: string, squadId: string, position?: [number, number, number], thresholds?: SCBEThresholds): UnitRuntime;
/**
 * Generate a voxel namespace key for a pad's memory.
 *
 * Key format: (unitId, padMode, lang, epoch)
 * This ensures the same "thought" can exist in different Pads without contamination.
 */
export declare function padNamespaceKey(unitId: string, padMode: PadMode, lang: Lang, epoch: number): string;
//# sourceMappingURL=polly-pad-runtime.d.ts.map