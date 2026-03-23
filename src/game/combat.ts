/**
 * @file combat.ts
 * @module game/combat
 * @layer Layer 5, Layer 12
 * @component Dual Combat System — Cl(4,0) Bivector Type Advantage
 *
 * Type advantage computed from Clifford algebra Cl(4,0) bivector commutators.
 * NO lookup table. Every matchup is geometrically computed.
 * A4: Symmetry — [F_A, F_B] = -[F_B, F_A] (antisymmetry preserved).
 */

import {
  TongueCode,
  TongueVector,
  TONGUE_CODES,
  TransformAction,
  TRANSFORM_RISK,
  ProblemEntity,
  OracleResult,
  FormationRole,
  FORMATION_BONUSES,
  RiskDecision,
} from './types.js';
import type { Companion } from './companion.js';
import { deriveCombatStats } from './companion.js';

// ---------------------------------------------------------------------------
//  Cl(4,0) Bivector Basis
// ---------------------------------------------------------------------------

/**
 * Basis bivectors in Cl(4,0): C(4,2) = 6 elements.
 * Each tongue maps to one bivector.
 *
 * KO → e₁₂, AV → e₁₃, RU → e₁₄, CA → e₂₃, UM → e₂₄, DR → e₃₄
 *
 * Representation: each bivector as a 4x4 antisymmetric matrix.
 * e_ij has +1 at (i,j) and -1 at (j,i).
 */

type Matrix4 = number[][];

/** Create a 4x4 zero matrix */
function zeros4(): Matrix4 {
  return [
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
  ];
}

/** Basis bivector e_ij (0-indexed i, j) */
function basisBivector(i: number, j: number): Matrix4 {
  const m = zeros4();
  m[i][j] = 1;
  m[j][i] = -1;
  return m;
}

/** The 6 basis bivectors mapped to tongue codes */
const BIVECTOR_BASIS: Record<TongueCode, Matrix4> = {
  KO: basisBivector(0, 1), // e₁₂
  AV: basisBivector(0, 2), // e₁₃
  RU: basisBivector(0, 3), // e₁₄
  CA: basisBivector(1, 2), // e₂₃
  UM: basisBivector(1, 3), // e₂₄
  DR: basisBivector(2, 3), // e₃₄
};

// ---------------------------------------------------------------------------
//  Matrix Operations
// ---------------------------------------------------------------------------

function matAdd(a: Matrix4, b: Matrix4): Matrix4 {
  return a.map((row, i) => row.map((v, j) => v + b[i][j]));
}

function matSub(a: Matrix4, b: Matrix4): Matrix4 {
  return a.map((row, i) => row.map((v, j) => v - b[i][j]));
}

function matMul(a: Matrix4, b: Matrix4): Matrix4 {
  const c = zeros4();
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 4; j++) {
      for (let k = 0; k < 4; k++) {
        c[i][j] += a[i][k] * b[k][j];
      }
    }
  }
  return c;
}

function matScale(m: Matrix4, s: number): Matrix4 {
  return m.map((row) => row.map((v) => v * s));
}

/** Frobenius norm */
function matNorm(m: Matrix4): number {
  let sum = 0;
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 4; j++) {
      sum += m[i][j] * m[i][j];
    }
  }
  return Math.sqrt(sum);
}

/** Matrix inner product (Frobenius) */
function matInner(a: Matrix4, b: Matrix4): number {
  let sum = 0;
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 4; j++) {
      sum += a[i][j] * b[i][j];
    }
  }
  return sum;
}

/** Commutator [A, B] = AB - BA */
function commutator(a: Matrix4, b: Matrix4): Matrix4 {
  return matSub(matMul(a, b), matMul(b, a));
}

// ---------------------------------------------------------------------------
//  Tongue Vector → Bivector
// ---------------------------------------------------------------------------

/**
 * Convert a TongueVector to a bivector (linear combination of basis).
 * F = Σᵢ vᵢ · eᵢ
 */
export function tongueToBivector(v: TongueVector): Matrix4 {
  let result = zeros4();
  for (let i = 0; i < 6; i++) {
    result = matAdd(result, matScale(BIVECTOR_BASIS[TONGUE_CODES[i]], v[i]));
  }
  return result;
}

// ---------------------------------------------------------------------------
//  Type Advantage (Geometric)
// ---------------------------------------------------------------------------

/**
 * Compute type advantage between two tongue vectors using Cl(4,0) commutator.
 *
 * Δ = ⟨[F_A, F_B], F_A − F_B⟩ / (‖[F_A,F_B]‖ · ‖F_A − F_B‖)
 *
 * Returns:
 *   Δ > 0 → A has advantage
 *   Δ < 0 → B has advantage
 *   |Δ| = strength of advantage (0 to 1)
 *
 * Properties:
 *   - Antisymmetric: advantage(A,B) = -advantage(B,A)
 *   - Continuous: small changes → small effect changes
 *   - Phase-sensitive: same tongue can differ by phase angles
 *   - NOT a lookup table
 */
export function computeTypeAdvantage(a: TongueVector, b: TongueVector): number {
  const fA = tongueToBivector(a);
  const fB = tongueToBivector(b);

  const comm = commutator(fA, fB);
  const diff = matSub(fA, fB);

  const commNorm = matNorm(comm);
  const diffNorm = matNorm(diff);

  // Avoid division by zero (identical vectors have no advantage)
  if (commNorm < 1e-12 || diffNorm < 1e-12) return 0;

  const delta = matInner(comm, diff) / (commNorm * diffNorm);

  // Clamp to [-1, 1]
  return Math.max(-1, Math.min(1, delta));
}

/**
 * Compute type advantage between two companions.
 */
export function companionTypeAdvantage(attacker: Companion, defender: Companion): number {
  return computeTypeAdvantage(attacker.state.tonguePosition, defender.state.tonguePosition);
}

// ---------------------------------------------------------------------------
//  Damage Calculation
// ---------------------------------------------------------------------------

/**
 * Calculate damage for an overworld attack.
 *
 * @param baseDamage - Raw damage value
 * @param typeAdvantage - Δ from computeTypeAdvantage
 * @param proofPower - Attacker's proof power (0-100)
 * @param resilience - Defender's resilience (0-100)
 * @returns Final damage (always >= 1)
 */
export function calculateDamage(
  baseDamage: number,
  typeAdvantage: number,
  proofPower: number,
  resilience: number
): number {
  // Type advantage multiplier: 0.5x to 1.5x
  const typeMul = 1.0 + typeAdvantage * 0.5;

  // Proof power multiplier: 0.8x to 1.5x
  const proofMul = 0.8 + (proofPower / 100) * 0.7;

  // Resilience reduction: 0% to 40%
  const resReduce = 1.0 - (resilience / 100) * 0.4;

  const finalDamage = baseDamage * typeMul * proofMul * resReduce;
  return Math.max(1, Math.round(finalDamage));
}

// ---------------------------------------------------------------------------
//  Transform System (Math Combat)
// ---------------------------------------------------------------------------

/** State of a math-monster encounter */
export interface MathEncounterState {
  problem: ProblemEntity;
  currentExpression: string;
  transformsApplied: TransformAction[];
  uncertaintyReduced: number; // 0 to 1 (1 = fully solved)
  trapHits: number;
  totalReward: number;
  scbeCostAccumulated: number;
  resolved: boolean;
}

/**
 * Create a new math encounter state from a problem entity.
 */
export function createEncounter(problem: ProblemEntity): MathEncounterState {
  return {
    problem,
    currentExpression: problem.statement,
    transformsApplied: [],
    uncertaintyReduced: 0,
    trapHits: 0,
    totalReward: 0,
    scbeCostAccumulated: 0,
    resolved: false,
  };
}

/**
 * Apply a transform to a math encounter.
 * Returns the oracle result and updated encounter state.
 *
 * In production, the oracle calls SymPy. Here we provide
 * the structural framework + cost gating.
 */
export function applyTransform(
  encounter: MathEncounterState,
  action: TransformAction,
  oracleResult: OracleResult
): MathEncounterState {
  const risk = TRANSFORM_RISK[action];

  // SCBE cost gating — higher risk actions cost more
  const riskCosts: Record<string, number> = { low: 0.1, medium: 0.3, high: 0.6 };
  const cost = riskCosts[risk];

  // Repeated same action escalates cost
  const repeatCount = encounter.transformsApplied.filter((t) => t === action).length;
  const repeatPenalty = repeatCount * 0.1;

  const totalCost = cost + repeatPenalty;

  const updated: MathEncounterState = {
    ...encounter,
    transformsApplied: [...encounter.transformsApplied, action],
    scbeCostAccumulated: encounter.scbeCostAccumulated + totalCost,
    totalReward: encounter.totalReward + oracleResult.reward,
  };

  if (oracleResult.valid) {
    updated.uncertaintyReduced = Math.min(
      1.0,
      encounter.uncertaintyReduced + 0.2 + oracleResult.reward * 0.1
    );
    if (updated.uncertaintyReduced >= 1.0) {
      updated.resolved = true;
    }
  } else {
    // Trap hit
    updated.trapHits = encounter.trapHits + 1;
  }

  return updated;
}

/**
 * Evaluate an SCBE risk decision for a transform action.
 * Layer 12: H(d,pd) = 1/(1+d+2*pd)
 * Layer 13: ALLOW/QUARANTINE/DENY
 */
export function evaluateTransformRisk(
  action: TransformAction,
  encounter: MathEncounterState,
  companionRiskTolerance: number
): RiskDecision {
  const risk = TRANSFORM_RISK[action];
  const riskCosts: Record<string, number> = { low: 0.1, medium: 0.4, high: 0.8 };
  const baseCost = riskCosts[risk];

  // Factor in accumulated cost and trap history
  const d = baseCost + encounter.scbeCostAccumulated * 0.2;
  const pd = encounter.trapHits * 0.15;

  // L12: Harmonic score
  const hScore = 1 / (1 + d + 2 * pd);

  // L13: Decision based on score and companion's risk tolerance
  const threshold = companionRiskTolerance / 100;

  if (hScore > 0.7) return 'ALLOW';
  if (hScore > 0.4) return 'QUARANTINE';
  if (hScore > 0.2 && threshold > 0.5) return 'ESCALATE';
  return 'DENY';
}

// ---------------------------------------------------------------------------
//  Formation Combat
// ---------------------------------------------------------------------------

/**
 * Calculate formation effectiveness for a fleet of companions.
 *
 * @param companions - Fleet members
 * @param formation - Formation type
 * @param lambda2 - Algebraic connectivity (from symbiotic network)
 * @returns Effectiveness multipliers for the formation
 */
export function calculateFormationEffectiveness(
  companions: Companion[],
  formation: FormationRole,
  lambda2: number
): { damage: number; defense: number; speed: number; valid: boolean } {
  const bonuses = FORMATION_BONUSES[formation];

  // Check minimum λ₂ requirement
  if (lambda2 < bonuses.minLambda2) {
    return { damage: 0.5, defense: 0.5, speed: 0.5, valid: false };
  }

  // Base bonuses from formation
  let damage = bonuses.damage;
  let defense = bonuses.defense;
  let speed = bonuses.speed;

  // Scale with λ₂ (network cohesion bonus)
  const cohesionBonus = Math.min(0.3, lambda2 * 0.2);
  damage += cohesionBonus;
  defense += cohesionBonus;
  speed += cohesionBonus;

  // Average companion authority adds governance weight
  const avgAuthority =
    companions.reduce((sum, c) => sum + c.state.harmonic_energy, 0) / companions.length;
  damage += avgAuthority * 0.1;

  return { damage, defense, speed, valid: true };
}
