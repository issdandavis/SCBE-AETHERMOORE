/**
 * @file governanceSim.ts
 * @module harmonic/governance-sim
 * @layer Layer 5, Layer 12, Layer 13
 * @component Governance Simulation Helpers
 * @version 3.2.4
 *
 * Drop-in helpers for any physics sim or visualization that needs
 * true geodesic pull, always-on NK signals, BFT consensus gating,
 * and voxel commit with Sacred Egg HMAC signing.
 *
 * Four concrete upgrades over Euclidean sims:
 *   1. True metric pull (Poincaré ball / hyperbolic distance)
 *   2. NK shell signals every tick (freeze motion, not measurement)
 *   3. 6-agent BFT gate (n=6, f=1, threshold=4)
 *   4. commitVoxel() + key/payload contract + Sacred Egg HMAC
 *
 * ─── USAGE ───────────────────────────────────────────────────
 * Import individual helpers or use GovernanceSimState for turnkey
 * integration with any requestAnimationFrame loop.
 *
 * ─── PYTHON PARITY ───────────────────────────────────────────
 * Backend parity module: src/scbe_governance_math.py
 * Tests: tests/test_layer12_voxel.py (49 tests)
 */

import { createHmac } from 'crypto';
import type { Lang, Decision } from './scbe_voxel_types.js';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

/** Golden ratio φ */
const PHI = (1 + Math.sqrt(5)) / 2;

/** Base cost multiplier */
const COST_R = 1.0;

/** Coherence penalty factor */
const GAMMA = 1.0;

/** Maps ~[-3,3] world space into unit Poincaré ball */
const POINCARE_SCALE = 0.35;

const EPS = 1e-9;

/** BFT threshold: >= 3f+1 for f=1 with 6 agents */
export const DANGER_QUORUM = 4;

/** Commit voxel every N ticks (default) */
export const COMMIT_EVERY = 20;

/** Sacred Tongue identifiers */
const TONGUES: readonly Lang[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** 3D point in world space */
export interface Point3D {
  x: number;
  y: number;
  z: number;
}

/** 6D voxel bin indices */
export interface VoxelBase {
  X: number;
  Y: number;
  Z: number;
  V: number;
  P: number;
  S: number;
}

/** Full voxel record for commit */
export interface SimVoxelRecord {
  key: string;
  t: number;
  decision: Decision;
  base: VoxelBase;
  perLang: Record<Lang, string>;
  pos: Point3D;
  vel: Point3D;
  phases: Record<Lang, number>;
  weights: Record<Lang, number>;
  entropy: number;
  metrics: { coh: number; dStar: number; cost: number };
}

// ═══════════════════════════════════════════════════════════════
// Core Math
// ═══════════════════════════════════════════════════════════════

/** Clamp n to [lo, hi] */
export function clamp(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, n));
}

/** Wrap angle to (-π, π] */
export function wrapPi(a: number): number {
  let x = a;
  while (x <= -Math.PI) x += 2 * Math.PI;
  while (x > Math.PI) x -= 2 * Math.PI;
  return x;
}

/** Uniform bin quantizer. Returns bin index in [0, bins-1]. */
export function quantize(val: number, minv: number, maxv: number, bins: number): number {
  const v = clamp(val, minv, maxv);
  const t = maxv > minv ? (v - minv) / (maxv - minv) : 0;
  const q = Math.round(t * (bins - 1));
  return clamp(q, 0, bins - 1);
}

/**
 * NK-shell coherence from 6-tongue phase angles.
 *
 * C = (1/15) Σ_{i<j} cos(φ_i - φ_j)   ∈ [-1, 1]
 */
export function coherenceFromPhases(phases: Record<string, number>): number {
  let total = 0;
  let count = 0;
  for (let i = 0; i < TONGUES.length; i++) {
    for (let j = i + 1; j < TONGUES.length; j++) {
      total += Math.cos(phases[TONGUES[i]] - phases[TONGUES[j]]);
      count++;
    }
  }
  return count > 0 ? total / count : 0;
}

// ═══════════════════════════════════════════════════════════════
// Drift + Cost (Layer 12)
// ═══════════════════════════════════════════════════════════════

/**
 * Compute d* — hyperbolic drift distance with weight-imbalance penalty.
 *
 * d* = r · (1 + 1.5 · imbalance)
 */
export function driftStar(p: Point3D, weights: Record<string, number>): number {
  const r = Math.sqrt(p.x * p.x + p.y * p.y + p.z * p.z);
  const ws = Object.values(weights);
  const s = ws.reduce((a, b) => a + b, 0) || 1;
  const maxw = Math.max(...ws, 0);
  const imbalance = maxw / s;
  return r * (1 + 1.5 * imbalance);
}

/**
 * Layer 12 super-exponential cost.
 *
 * H(d*, C) = R · π^(φ · d*) · (1 + γ · (1 - C))
 */
export function layer12Cost(dStar: number, coherence: number): number {
  const base = COST_R * Math.pow(Math.PI, PHI * dStar);
  return base * (1 + GAMMA * (1 - coherence));
}

// ═══════════════════════════════════════════════════════════════
// Poincaré Ball Geometry (3D projection)
// ═══════════════════════════════════════════════════════════════

function normSq(p: Point3D): number {
  return p.x * p.x + p.y * p.y + p.z * p.z;
}

function toBall(p: Point3D): Point3D {
  return {
    x: p.x * POINCARE_SCALE,
    y: p.y * POINCARE_SCALE,
    z: p.z * POINCARE_SCALE,
  };
}

/**
 * Poincaré ball distance (3D). Maps world-space points into the ball
 * via POINCARE_SCALE before computing.
 *
 * d(u,v) = acosh(1 + 2|u-v|² / ((1-|u|²)(1-|v|²)))
 */
export function poincareDist(a: Point3D, b: Point3D): number {
  const u = toBall(a);
  const v = toBall(b);
  const u2 = normSq(u);
  const v2 = normSq(v);
  const dx = u.x - v.x;
  const dy = u.y - v.y;
  const dz = u.z - v.z;
  const du2 = dx * dx + dy * dy + dz * dz;
  const denom = Math.max((1 - u2) * (1 - v2), EPS);
  const arg = 1 + (2 * du2) / denom;
  return Math.acosh(Math.max(arg, 1));
}

/**
 * Inverse conformal factor 1/λ² where λ = 2/(1-‖u‖²).
 *
 * Use to scale forces: geodesic pull = Euclidean_force × invMetricFactor.
 * Near origin: ~0.25 (moderate). Near boundary: → 0 (forces shrink).
 */
export function invMetricFactor(at: Point3D): number {
  const u = toBall(at);
  const u2 = normSq(u);
  const lam = 2 / Math.max(1 - u2, 1e-6);
  return 1 / (lam * lam);
}

// ═══════════════════════════════════════════════════════════════
// BFT Consensus (6 agents, f=1, threshold=4)
// ═══════════════════════════════════════════════════════════════

/**
 * Single agent's local risk vote.
 *
 * risk = cost · (1 + 0.6·phaseDelta) · (1 + 0.15·w) · (1 + 0.5·(1-C))
 */
export function localVote(
  lang: Lang,
  cost: number,
  coherence: number,
  phases: Record<string, number>,
  weights: Record<string, number>,
  denyCost: number = 50,
  quarantineCost: number = 12,
): Decision {
  const allPhases = Object.values(phases);
  const meanPhase = allPhases.length > 0
    ? allPhases.reduce((a, b) => a + b, 0) / allPhases.length
    : 0;
  const phaseDelta = Math.abs(wrapPi((phases[lang] ?? 0) - meanPhase)) / Math.PI;
  const w = weights[lang] ?? 0.5;

  const risk =
    cost * (1 + 0.6 * phaseDelta) * (1 + 0.15 * w) * (1 + 0.5 * (1 - coherence));

  if (risk > denyCost) return 'DENY';
  if (risk > quarantineCost) return 'QUARANTINE';
  return 'ALLOW';
}

/**
 * BFT consensus gate (n=6, f=1, threshold≥4).
 *
 * Requires ≥4 votes for QUARANTINE or DENY; otherwise ALLOW.
 * One faulty agent cannot lock the fleet.
 */
export function bftConsensus(votes: Record<string, Decision>): Decision {
  let deny = 0;
  let quar = 0;
  for (const v of Object.values(votes)) {
    if (v === 'DENY') deny++;
    else if (v === 'QUARANTINE') quar++;
  }
  if (deny >= DANGER_QUORUM) return 'DENY';
  if (quar >= DANGER_QUORUM) return 'QUARANTINE';
  return 'ALLOW';
}

/**
 * Run a full BFT governance tick: compute all 6 local votes + consensus.
 *
 * Call this every tick in updatePhysics(). Returns the consensus decision
 * and per-tongue votes for logging.
 */
export function governanceTick(
  cost: number,
  coherence: number,
  phases: Record<string, number>,
  weights: Record<string, number>,
): { decision: Decision; votes: Record<Lang, Decision> } {
  const votes = {} as Record<Lang, Decision>;
  for (const L of TONGUES) {
    votes[L] = localVote(L, cost, coherence, phases, weights);
  }
  return { decision: bftConsensus(votes), votes };
}

// ═══════════════════════════════════════════════════════════════
// Voxel Key Encoding
// ═══════════════════════════════════════════════════════════════

/** Base-36 encode with 2-char zero-padded output */
function b36(n: number): string {
  const val = Math.max(0, Math.floor(n));
  return val.toString(36).padStart(2, '0');
}

/**
 * Deterministic base-36 voxel key.
 *
 * Format: qr:{D}:{X}:{Y}:{Z}:{V}:{P}:{S}
 */
export function encodeVoxelKey(base: VoxelBase, decision: Decision): string {
  return [
    'qr',
    decision[0],
    b36(base.X),
    b36(base.Y),
    b36(base.Z),
    b36(base.V),
    b36(base.P),
    b36(base.S),
  ].join(':');
}

// ═══════════════════════════════════════════════════════════════
// Sacred Egg HMAC Signing
// ═══════════════════════════════════════════════════════════════

/**
 * Sign a voxel record payload with Sacred Egg HMAC-SHA256.
 *
 * Uses Node.js crypto for server-side. For browser, use the
 * WebCrypto subtle API version (eggSignBrowser).
 */
export function eggSign(eggKeyBytes: Buffer, payload: string): string {
  return createHmac('sha256', eggKeyBytes).update(payload, 'utf-8').digest('hex');
}

/**
 * Commit a voxel record with optional Sacred Egg signing.
 *
 * Override this with your actual backend call (Redis/RocksDB/S3).
 * Returns the record key and optional signature.
 */
export function commitVoxel(
  rec: SimVoxelRecord,
  eggKeyBytes?: Buffer,
): { key: string; sig?: string } {
  const payload = JSON.stringify(rec);
  const sig = eggKeyBytes ? eggSign(eggKeyBytes, payload) : undefined;
  return { key: rec.key, sig };
}

// ═══════════════════════════════════════════════════════════════
// Turnkey: GovernanceSimState
// ═══════════════════════════════════════════════════════════════

/**
 * All-in-one governance state for a sim tick.
 *
 * Call `tick()` every frame. It:
 * 1. Computes NK coherence
 * 2. Computes d* with Poincaré distance from origin
 * 3. Computes Layer 12 cost
 * 4. Runs BFT governance (6 local votes + consensus)
 * 5. Returns { decision, motionAllowed, metrics }
 *
 * Use `shouldCommit(tick)` to check if it's time to commit a voxel.
 */
export class GovernanceSimState {
  decision: Decision = 'ALLOW';
  coherence = 1;
  dStar = 0;
  cost = 1;
  votes: Record<Lang, Decision> = {
    KO: 'ALLOW',
    AV: 'ALLOW',
    RU: 'ALLOW',
    CA: 'ALLOW',
    UM: 'ALLOW',
    DR: 'ALLOW',
  };

  /**
   * Run a full governance tick.
   *
   * @param pos - Current 3D position in world space
   * @param phases - Current Sacred Tongue phase angles
   * @param weights - Current tongue weights
   * @returns { decision, motionAllowed, coh, dStar, cost, votes }
   */
  tick(
    pos: Point3D,
    phases: Record<string, number>,
    weights: Record<string, number>,
  ): {
    decision: Decision;
    motionAllowed: boolean;
    coh: number;
    dStar: number;
    cost: number;
    votes: Record<Lang, Decision>;
  } {
    this.coherence = coherenceFromPhases(phases);

    // d* via Poincaré distance from origin
    const d0 = poincareDist(pos, { x: 0, y: 0, z: 0 });
    const ws = Object.values(weights);
    const s = ws.reduce((a, b) => a + b, 0) || 1;
    const maxw = Math.max(...ws, 0);
    this.dStar = d0 * (1 + 1.5 * (maxw / s));

    this.cost = layer12Cost(this.dStar, this.coherence);

    const { decision, votes } = governanceTick(
      this.cost,
      this.coherence,
      phases,
      weights,
    );
    this.decision = decision;
    this.votes = votes;

    return {
      decision,
      motionAllowed: decision === 'ALLOW',
      coh: this.coherence,
      dStar: this.dStar,
      cost: this.cost,
      votes,
    };
  }

  /** Check if it's time to commit a voxel record. */
  shouldCommit(tickNumber: number, interval: number = COMMIT_EVERY): boolean {
    return tickNumber > 0 && tickNumber % interval === 0;
  }
}
