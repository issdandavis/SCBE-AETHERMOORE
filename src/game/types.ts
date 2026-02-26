/**
 * @file types.ts
 * @module game/types
 * @layer Layer 3, Layer 5, Layer 12, Layer 13
 * @component Spiral Forge RPG — Core Type Definitions
 *
 * All game types grounded in SCBE 21D canonical state and Sacred Tongues.
 * Companions ARE canonical state vectors, not a separate bolted-on system.
 */

// ---------------------------------------------------------------------------
//  Sacred Tongues (re-exported for game context)
// ---------------------------------------------------------------------------

/** The six Sacred Tongues — governance dimensions */
export type TongueCode = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/** All tongue codes in canonical order */
export const TONGUE_CODES: readonly TongueCode[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;

/** Golden ratio φ = (1+√5)/2 */
export const PHI = (1 + Math.sqrt(5)) / 2;

/** Tongue weights scaled by φ powers */
export const TONGUE_WEIGHTS: Record<TongueCode, number> = {
  KO: 1.0,
  AV: PHI, // ~1.618
  RU: PHI ** 2, // ~2.618
  CA: PHI ** 3, // ~4.236
  UM: PHI ** 4, // ~6.854
  DR: PHI ** 5, // ~11.09
};

/** Full tongue names */
export const TONGUE_NAMES: Record<TongueCode, string> = {
  KO: "Kor'aelin",
  AV: 'Avali',
  RU: 'Runethic',
  CA: 'Cassisivadan',
  UM: 'Umbroth',
  DR: 'Draumric',
};

/** Tongue descriptions for gameplay */
export const TONGUE_ROLES: Record<TongueCode, string> = {
  KO: 'Command — initiative, force, origin',
  AV: 'Transport — movement, binding, flight',
  RU: 'Entropy — chaos, risk, connection',
  CA: 'Compute — analysis, encryption, logic',
  UM: 'Security — defense, erasure, wards',
  DR: 'Structure — authentication, verification, form',
};

/**
 * Hodge dual pairs: tongues that form complementary partners.
 * In Cl(4,0): e_ij ∧ e_kl = e_1234 (the pseudoscalar).
 * Hodge duals bond 30% stronger in the symbiotic network.
 */
export const HODGE_DUAL_PAIRS: ReadonlyArray<[TongueCode, TongueCode]> = [
  ['KO', 'DR'], // e₁₂ ∧ e₃₄ — Command ↔ Structure
  ['AV', 'UM'], // e₁₃ ∧ e₂₄ — Transport ↔ Security
  ['RU', 'CA'], // e₁₄ ∧ e₂₃ — Entropy ↔ Compute
];

// ---------------------------------------------------------------------------
//  6D Tongue Vector
// ---------------------------------------------------------------------------

/** A point in R^6 tongue-space. Order: [KO, AV, RU, CA, UM, DR] */
export type TongueVector = [number, number, number, number, number, number];

/** Create a zero tongue vector */
export function zeroTongueVector(): TongueVector {
  return [0, 0, 0, 0, 0, 0];
}

/** Get the tongue index for a code */
export function tongueIndex(code: TongueCode): number {
  return TONGUE_CODES.indexOf(code);
}

/** Get the dominant tongue from a vector */
export function dominantTongue(v: TongueVector): TongueCode {
  let maxIdx = 0;
  for (let i = 1; i < 6; i++) {
    if (v[i] > v[maxIdx]) maxIdx = i;
  }
  return TONGUE_CODES[maxIdx];
}

/** L2 norm of a tongue vector */
export function tongueNorm(v: TongueVector): number {
  return Math.sqrt(v.reduce((sum, x) => sum + x * x, 0));
}

/** Euclidean distance between two tongue vectors */
export function tongueDistance(a: TongueVector, b: TongueVector): number {
  return Math.sqrt(a.reduce((sum, x, i) => sum + (x - b[i]) ** 2, 0));
}

// ---------------------------------------------------------------------------
//  21D Canonical State Vector
// ---------------------------------------------------------------------------

/**
 * The 21D canonical state that drives everything.
 * Block A (0-5): Tongue Position in R^6
 * Block B (6-11): Phase Angles in R^6
 * Block C (12-20): Telemetry in R^9
 */
export interface CanonicalState {
  /** Block A: Tongue position (R^6) — elemental alignment, visual color, audio chord */
  readonly tonguePosition: TongueVector;

  /** Block B: Phase angles (R^6) — combat timing, microtonal pitch, octave */
  readonly phaseAngles: TongueVector;

  /** Block C: Telemetry (R^9) */
  readonly flux: number; // [12] → combat Speed
  readonly coherence_s: number; // [13] → Insight (reveal hidden constraints)
  readonly coherence_bi: number; // [14] → emotional state
  readonly coherence_tri: number; // [15] → Perception (detect traps)
  readonly risk: number; // [16] → Risk Tolerance (SCBE cost modifier)
  readonly entropy_rate: number; // [17] → Entropy Affinity (CaseSplit effectiveness)
  readonly stabilization: number; // [18] → Resilience (resist trap damage)
  readonly radius: number; // [19] → Proof Power (damage on correct transforms)
  readonly harmonic_energy: number; // [20] → Authority (governance weight)
}

/** Create a default canonical state */
export function defaultCanonicalState(): CanonicalState {
  return {
    tonguePosition: zeroTongueVector(),
    phaseAngles: [0, 0, 0, 0, 0, 0],
    flux: 0.5,
    coherence_s: 0.5,
    coherence_bi: 0.5,
    coherence_tri: 0.5,
    risk: 0.3,
    entropy_rate: 0.1,
    stabilization: 0.5,
    radius: 0.1,
    harmonic_energy: 0.0,
  };
}

/** Flatten canonical state to a 21-element array */
export function stateToArray(s: CanonicalState): number[] {
  return [
    ...s.tonguePosition,
    ...s.phaseAngles,
    s.flux,
    s.coherence_s,
    s.coherence_bi,
    s.coherence_tri,
    s.risk,
    s.entropy_rate,
    s.stabilization,
    s.radius,
    s.harmonic_energy,
  ];
}

/** Reconstruct canonical state from a 21-element array */
export function arrayToState(arr: number[]): CanonicalState {
  if (arr.length !== 21) throw new RangeError(`Expected 21 elements, got ${arr.length}`);
  return {
    tonguePosition: arr.slice(0, 6) as TongueVector,
    phaseAngles: arr.slice(6, 12) as TongueVector,
    flux: arr[12],
    coherence_s: arr[13],
    coherence_bi: arr[14],
    coherence_tri: arr[15],
    risk: arr[16],
    entropy_rate: arr[17],
    stabilization: arr[18],
    radius: arr[19],
    harmonic_energy: arr[20],
  };
}

// ---------------------------------------------------------------------------
//  Risk / Governance
// ---------------------------------------------------------------------------

/** Risk decision tiers (L13) */
export type RiskDecision = 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';

/** Governance tier requirements aligned with fleet types */
export const GOVERNANCE_TIER_MIN_TRUST: Record<TongueCode, number> = {
  KO: 0.1,
  AV: 0.3,
  RU: 0.5,
  CA: 0.7,
  UM: 0.85,
  DR: 0.95,
};

// ---------------------------------------------------------------------------
//  Companion Types
// ---------------------------------------------------------------------------

/** Discipline traits — develop from HOW you use companions */
export type DisciplineTrait =
  | 'careful_verifier'
  | 'fast_heuristic'
  | 'collaborative'
  | 'solo'
  | 'risk_tolerant'
  | 'guardian';

/** Emotional states — affect performance + evolution */
export type EmotionalState =
  | 'content'
  | 'excited'
  | 'anxious'
  | 'determined'
  | 'exhausted'
  | 'corrupted'
  | 'transcendent';

/** Formation roles (fleet doctrines) */
export type FormationRole = 'storm' | 'phalanx' | 'lance' | 'web';

/** Formation bonuses */
export const FORMATION_BONUSES: Record<
  FormationRole,
  { damage: number; defense: number; speed: number; minLambda2: number }
> = {
  storm: { damage: 1.4, defense: 0.7, speed: 1.2, minLambda2: 0 },
  phalanx: { damage: 0.8, defense: 1.5, speed: 0.8, minLambda2: 0.3 },
  lance: { damage: 1.6, defense: 0.6, speed: 1.0, minLambda2: 0.3 },
  web: { damage: 1.0, defense: 1.0, speed: 1.0, minLambda2: 0.6 },
};

/** Evolution stage names (NOT Digimon stages — our own naming) */
export type EvolutionStage = 'spark' | 'form' | 'prime' | 'apex' | 'transcendent';

/** Radius thresholds for evolution stages */
export const EVOLUTION_THRESHOLDS: Record<EvolutionStage, number> = {
  spark: 0.0,
  form: 0.3,
  prime: 0.5,
  apex: 0.7,
  transcendent: 0.85,
};

/** Over-evolution instability threshold */
export const OVER_EVOLUTION_THRESHOLD = 0.95;

// ---------------------------------------------------------------------------
//  Egg Types
// ---------------------------------------------------------------------------

/** Egg categories */
export type EggType =
  | 'mono_KO'
  | 'mono_AV'
  | 'mono_RU'
  | 'mono_CA'
  | 'mono_UM'
  | 'mono_DR'
  | 'hodge_eclipse' // KO+DR
  | 'hodge_storm' // AV+UM
  | 'hodge_paradox' // RU+CA
  | 'omni_prism'; // all

/** Bond types from egg origin */
export type BondType =
  | 'amplifier'
  | 'scout'
  | 'disruptor'
  | 'processor'
  | 'guardian'
  | 'architect'
  | 'harmonizer'
  | 'balancer'
  | 'synthesizer'
  | 'nexus';

// ---------------------------------------------------------------------------
//  Combat Types
// ---------------------------------------------------------------------------

/** Mathematical transform actions (player attacks) */
export type TransformAction =
  | 'normalize'
  | 'substitute'
  | 'complete_square'
  | 'factor'
  | 'bound'
  | 'invariant_check'
  | 'case_split'
  | 'contradiction_probe'
  | 'differentiate'
  | 'integrate'
  | 'apply_theorem';

/** Transform risk levels */
export const TRANSFORM_RISK: Record<TransformAction, 'low' | 'medium' | 'high'> = {
  normalize: 'low',
  substitute: 'medium',
  complete_square: 'low',
  factor: 'medium',
  bound: 'low',
  invariant_check: 'low',
  case_split: 'medium',
  contradiction_probe: 'high',
  differentiate: 'medium',
  integrate: 'high',
  apply_theorem: 'medium',
};

/** Problem entity (a "monster") */
export interface ProblemEntity {
  readonly problemId: string;
  readonly topic: string;
  readonly statement: string;
  readonly constraints: string[];
  readonly solutionCheck: { type: 'symbolic' | 'numeric'; expected: string };
  readonly trapSignatures: string[];
  readonly difficulty: number; // 1-10
  readonly tongueAffinity: TongueCode; // which tongue domain
}

/** Oracle verification result */
export interface OracleResult {
  readonly valid: boolean;
  readonly type?: 'correct' | 'lost_solutions' | 'extraneous_roots' | 'invalid_step';
  readonly reward: number;
  readonly explanation?: string;
}

// ---------------------------------------------------------------------------
//  Player Skill Tree
// ---------------------------------------------------------------------------

/** Skill tree path (one per tongue) */
export type SkillPath = 'command' | 'compute' | 'entropy' | 'structure' | 'transport' | 'security';

/** Mapping from tongue to skill path */
export const TONGUE_TO_PATH: Record<TongueCode, SkillPath> = {
  KO: 'command',
  AV: 'transport',
  RU: 'entropy',
  CA: 'compute',
  UM: 'security',
  DR: 'structure',
};

/** A single skill node in the tree */
export interface SkillNode {
  readonly id: string;
  readonly path: SkillPath;
  readonly name: string;
  readonly description: string;
  readonly tier: number; // 1-5
  readonly cost: number; // skill points
  readonly prerequisites: string[]; // skill node IDs
  readonly effect: SkillEffect;
}

/** What a skill does when unlocked */
export interface SkillEffect {
  readonly type: 'stat_bonus' | 'ability_unlock' | 'passive' | 'formation_bonus';
  readonly target: string;
  readonly value: number;
}

// ---------------------------------------------------------------------------
//  Region / World
// ---------------------------------------------------------------------------

/** Tongue-region definitions */
export interface TongueRegion {
  readonly id: string;
  readonly name: string;
  readonly tongue: TongueCode;
  readonly palette: { primary: string; secondary: string; accent: string };
  readonly architectureStyle: string;
  readonly floorRange: [number, number]; // tower floors accessible from this region
  readonly description: string;
}

/** Tower floor definition */
export interface TowerFloor {
  readonly floor: number;
  readonly mathDomain: string;
  readonly rank: string;
  readonly encounters: number;
  readonly miniBoss: boolean;
  readonly boss: boolean;
  readonly region: string;
}

// ---------------------------------------------------------------------------
//  Synesthesia Mapping
// ---------------------------------------------------------------------------

/** Color/audio mapping for a tongue */
export interface SynesthesiaMapping {
  readonly tongue: TongueCode;
  readonly hue: number; // degrees 0-360
  readonly hexColor: string;
  readonly note: string;
  readonly frequency: number; // Hz
  readonly instrumentFamily: string;
}

export const SYNESTHESIA_MAP: Record<TongueCode, SynesthesiaMapping> = {
  KO: {
    tongue: 'KO',
    hue: 0,
    hexColor: '#DC3C3C',
    note: 'A',
    frequency: 220,
    instrumentFamily: 'brass',
  },
  AV: {
    tongue: 'AV',
    hue: 60,
    hexColor: '#DCB43C',
    note: 'B',
    frequency: 247,
    instrumentFamily: 'strings',
  },
  RU: {
    tongue: 'RU',
    hue: 120,
    hexColor: '#3CDC78',
    note: 'C#',
    frequency: 277,
    instrumentFamily: 'synth',
  },
  CA: {
    tongue: 'CA',
    hue: 180,
    hexColor: '#3CDCDC',
    note: 'D#',
    frequency: 311,
    instrumentFamily: 'piano',
  },
  UM: {
    tongue: 'UM',
    hue: 240,
    hexColor: '#3C3CDC',
    note: 'F',
    frequency: 349,
    instrumentFamily: 'choir',
  },
  DR: {
    tongue: 'DR',
    hue: 300,
    hexColor: '#DC3CDC',
    note: 'G',
    frequency: 392,
    instrumentFamily: 'harp',
  },
};

// ---------------------------------------------------------------------------
//  Event Logging (Training Data)
// ---------------------------------------------------------------------------

/** Game event for training pipeline */
export interface GameEvent {
  readonly eventId: string;
  readonly timestamp: number;
  readonly agentId: string; // player or AI agent ID
  readonly eventType:
    | 'transform_applied'
    | 'problem_solved'
    | 'problem_failed'
    | 'evolution_triggered'
    | 'egg_hatched'
    | 'formation_changed'
    | 'codex_query'
    | 'floor_cleared'
    | 'tower_defense_wave'
    | 'bond_event';
  readonly data: Record<string, unknown>;
  readonly scbeDecision: RiskDecision;
  readonly scbeCost: number;
}

/** Dataset tier for training pipeline */
export type DatasetTier = 'raw' | 'quarantined' | 'approved';
