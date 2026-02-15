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

import type { PadMode, Decision, Lang, Voxel6 } from '../harmonic/scbe_voxel_types.js';
import { PAD_MODES, PAD_MODE_TONGUE } from '../harmonic/scbe_voxel_types.js';
import { scbeDecide, type SCBEThresholds, DEFAULT_THRESHOLDS } from '../harmonic/voxelRecord.js';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** Code zone: SAFE (execution) or HOT (exploratory) */
export type CodeZone = 'SAFE' | 'HOT';

/** Tool categories available per pad */
export type ToolCategory =
  | 'build'
  | 'deploy'
  | 'map'
  | 'proximity'
  | 'radio'
  | 'encrypt'
  | 'hypothesis'
  | 'experiment'
  | 'telemetry'
  | 'config'
  | 'policy'
  | 'goals'
  | 'constraints'
  | 'plan_only';

/** Allowed tools per PadMode × CodeZone */
export const PAD_TOOL_MATRIX: Record<PadMode, Record<CodeZone, readonly ToolCategory[]>> = {
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

// ═══════════════════════════════════════════════════════════════
// Unit State
// ═══════════════════════════════════════════════════════════════

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
export function createUnitState(
  unitId: string,
  x: number = 0,
  y: number = 0,
  z: number = 0,
  overrides?: Partial<UnitState>
): UnitState {
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

// ═══════════════════════════════════════════════════════════════
// Polly Pad (per-unit, per-mode workspace)
// ═══════════════════════════════════════════════════════════════

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
export function createPadRuntime(
  unitId: string,
  mode: PadMode,
  thresholds: SCBEThresholds = DEFAULT_THRESHOLDS
): PadRuntime {
  const zone: CodeZone = 'HOT';
  return {
    unitId,
    mode,
    zone,
    tongue: PAD_MODE_TONGUE[mode],
    tools: PAD_TOOL_MATRIX[mode][zone],
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
export function canPromoteToSafe(
  pad: PadRuntime,
  state: UnitState,
  quorumVotes?: number
): boolean {
  const decision = scbeDecide(state.dStar, state.coherence, state.hEff, pad.thresholds);
  if (decision !== 'ALLOW') return false;
  if (quorumVotes !== undefined && quorumVotes < 4) return false;
  return true;
}

/**
 * Promote a pad from HOT → SAFE, updating its available tools.
 *
 * @returns New pad runtime in SAFE zone, or null if not promotable
 */
export function promotePad(
  pad: PadRuntime,
  state: UnitState,
  quorumVotes?: number
): PadRuntime | null {
  if (!canPromoteToSafe(pad, state, quorumVotes)) return null;
  return {
    ...pad,
    zone: 'SAFE',
    tools: PAD_TOOL_MATRIX[pad.mode]['SAFE'],
  };
}

/**
 * Demote a pad from SAFE → HOT (on coherence drop, etc).
 */
export function demotePad(pad: PadRuntime): PadRuntime {
  return {
    ...pad,
    zone: 'HOT',
    tools: PAD_TOOL_MATRIX[pad.mode]['HOT'],
  };
}

/**
 * Get the tools currently available to a pad.
 */
export function getAvailableTools(pad: PadRuntime): readonly ToolCategory[] {
  return PAD_TOOL_MATRIX[pad.mode][pad.zone];
}

/**
 * Route a task to appropriate tools based on pad mode + zone.
 *
 * @returns Comma-separated tool string (e.g. "tools:build,tools:deploy")
 */
export function routeTask(pad: PadRuntime): string {
  return pad.tools.map((t) => `tools:${t}`).join(',');
}

// ═══════════════════════════════════════════════════════════════
// Squad Space (shared + quorum-gated)
// ═══════════════════════════════════════════════════════════════

/** Euclidean distance between two units */
export function unitDistance(a: UnitState, b: UnitState): number {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2);
}

/** Squad space: overlay of multiple units' quasi-spheres */
export class SquadSpace {
  readonly squadId: string;
  private units: Map<string, UnitState> = new Map();

  constructor(squadId: string) {
    this.squadId = squadId;
  }

  /** Register or update a unit */
  setUnit(state: UnitState): void {
    this.units.set(state.unitId, state);
  }

  /** Remove a unit */
  removeUnit(unitId: string): void {
    this.units.delete(unitId);
  }

  /** Get a unit by ID */
  getUnit(unitId: string): UnitState | undefined {
    return this.units.get(unitId);
  }

  /** Get all unit IDs */
  getUnitIds(): string[] {
    return Array.from(this.units.keys());
  }

  /** Get unit count */
  get size(): number {
    return this.units.size;
  }

  /**
   * Compute proximity graph: which units are within radius of each other.
   *
   * @param radius - Max distance for neighbor relation
   * @returns Map from unitId → list of neighbor unitIds
   */
  neighbors(radius: number): Map<string, string[]> {
    const ids = Array.from(this.units.keys());
    const result = new Map<string, string[]>();
    for (const id of ids) result.set(id, []);

    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const a = this.units.get(ids[i])!;
        const b = this.units.get(ids[j])!;
        if (unitDistance(a, b) <= radius) {
          result.get(ids[i])!.push(ids[j]);
          result.get(ids[j])!.push(ids[i]);
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
  findLeader(): string | undefined {
    let bestId: string | undefined;
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
  quorumOk(votes: number, n: number = 6, threshold: number = 4): boolean {
    // BFT rule: n >= 3f + 1 where f = floor((n - 1) / 3)
    // For n=6: f=1, threshold=3f+1=4
    const f = Math.floor((n - 1) / 3);
    return votes >= threshold && n >= 3 * f + 1 && threshold >= 2 * f + 1;
  }

  /**
   * Compute squad-level coherence: average coherence of all units.
   */
  averageCoherence(): number {
    if (this.units.size === 0) return 0;
    let sum = 0;
    for (const state of this.units.values()) sum += state.coherence;
    return sum / this.units.size;
  }

  /**
   * Compute risk field: map of unit positions → SCBE decision.
   *
   * @param thresholds - SCBE thresholds
   * @returns Map from unitId → Decision
   */
  riskField(thresholds: SCBEThresholds = DEFAULT_THRESHOLDS): Map<string, Decision> {
    const result = new Map<string, Decision>();
    for (const [id, state] of this.units) {
      result.set(id, scbeDecide(state.dStar, state.coherence, state.hEff, thresholds));
    }
    return result;
  }
}

// ═══════════════════════════════════════════════════════════════
// Unit Runtime (all 6 pads + squad membership)
// ═══════════════════════════════════════════════════════════════

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
export function createUnitRuntime(
  unitId: string,
  squadId: string,
  position: [number, number, number] = [0, 0, 0],
  thresholds: SCBEThresholds = DEFAULT_THRESHOLDS
): UnitRuntime {
  const state = createUnitState(unitId, position[0], position[1], position[2]);
  const pads = new Map<PadMode, PadRuntime>();

  for (const mode of PAD_MODES) {
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
export function padNamespaceKey(
  unitId: string,
  padMode: PadMode,
  lang: Lang,
  epoch: number
): string {
  return `${unitId}:${padMode}:${lang}:${epoch}`;
}
