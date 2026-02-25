/**
 * @file companion.ts
 * @module game/companion
 * @layer Layer 5, Layer 12, Layer 13
 * @component Seal Entity — Companion System
 *
 * Companions are 21D canonical state vectors with behavioral evolution,
 * symbiotic graph topology, and fleet formation roles.
 * A2: Unitarity — state transitions preserve norm within tolerance.
 * A4: Symmetry — Hodge dual pairs receive 30% bond bonus.
 */

import {
  CanonicalState,
  defaultCanonicalState,
  stateToArray,
  DisciplineTrait,
  EmotionalState,
  FormationRole,
  EvolutionStage,
  EVOLUTION_THRESHOLDS,
  OVER_EVOLUTION_THRESHOLD,
  TongueCode,
  TongueVector,
  TONGUE_CODES,
  dominantTongue,
  tongueDistance,
  tongueNorm,
  EggType,
  BondType,
} from './types.js';

// ---------------------------------------------------------------------------
//  Companion (Seal Entity)
// ---------------------------------------------------------------------------

export interface Companion {
  /** Unique identifier */
  readonly id: string;

  /** Display name */
  name: string;

  /** Species/lineage identifier */
  readonly speciesId: string;

  /** The 21D canonical state — THIS IS the companion */
  state: CanonicalState;

  /** Current seal integrity (HP equivalent, 0-100) */
  sealIntegrity: number;

  /** Maximum seal integrity */
  maxSealIntegrity: number;

  /** Current drift level (distance from stable alignment) */
  driftLevel: number;

  /** Bond level with player (0-10) */
  bondLevel: number;

  /** Bond experience points toward next level */
  bondXP: number;

  /** Current formation role */
  formationRole: FormationRole;

  /** Discipline trait (develops from usage patterns) */
  disciplineTrait: DisciplineTrait;

  /** Emotional state (affects performance + evolution) */
  emotionalState: EmotionalState;

  /** Current evolution stage */
  evolutionStage: EvolutionStage;

  /** Evolution line (tracks the path taken) */
  evolutionLine: string[];

  /** Egg type this companion hatched from */
  eggOrigin: EggType;

  /** Bond type from egg origin */
  bondType: BondType;

  /** Scar count (losses, failed dungeons) — influences evolution */
  scarCount: number;

  /** Hollow exposure count (contact with 7th Tongue) */
  hollowExposure: number;

  /** Combat stats (derived from canonical state) */
  readonly derivedStats: DerivedCombatStats;
}

/** Stats derived from the 21D canonical state — never set directly */
export interface DerivedCombatStats {
  readonly speed: number;
  readonly insight: number;
  readonly perception: number;
  readonly riskTolerance: number;
  readonly entropyAffinity: number;
  readonly resilience: number;
  readonly proofPower: number;
  readonly authority: number;
}

// ---------------------------------------------------------------------------
//  Stat Derivation (canonical state → combat stats)
// ---------------------------------------------------------------------------

/**
 * Derive combat stats from the 21D canonical state.
 * These are COMPUTED, never assigned directly.
 */
export function deriveCombatStats(state: CanonicalState): DerivedCombatStats {
  return {
    speed: Math.max(0, Math.min(100, state.flux * 100)),
    insight: Math.max(0, Math.min(100, state.coherence_s * 100)),
    perception: Math.max(0, Math.min(100, state.coherence_tri * 100)),
    riskTolerance: Math.max(0, Math.min(100, state.risk * 100)),
    entropyAffinity: Math.max(0, Math.min(100, state.entropy_rate * 100)),
    resilience: Math.max(0, Math.min(100, state.stabilization * 100)),
    proofPower: Math.max(0, Math.min(100, state.radius * 100)),
    authority: Math.max(0, Math.min(100, state.harmonic_energy * 100)),
  };
}

// ---------------------------------------------------------------------------
//  Companion Factory
// ---------------------------------------------------------------------------

/**
 * Create a new companion from a hatched egg.
 *
 * @param id - Unique identifier
 * @param speciesId - Species lineage
 * @param name - Display name
 * @param eggType - Egg this hatched from
 * @param bondType - Bond type determined by egg
 * @param initialTongue - Starting tongue position
 */
export function createCompanion(
  id: string,
  speciesId: string,
  name: string,
  eggType: EggType,
  bondType: BondType,
  initialTongue: TongueVector
): Companion {
  const state: CanonicalState = {
    ...defaultCanonicalState(),
    tonguePosition: initialTongue,
    radius: 0.1, // start at spark stage
  };

  return {
    id,
    speciesId,
    name,
    state,
    sealIntegrity: 100,
    maxSealIntegrity: 100,
    driftLevel: 0,
    bondLevel: 1,
    bondXP: 0,
    formationRole: 'storm',
    disciplineTrait: 'collaborative',
    emotionalState: 'content',
    evolutionStage: 'spark',
    evolutionLine: [speciesId],
    eggOrigin: eggType,
    bondType,
    scarCount: 0,
    hollowExposure: 0,
    get derivedStats() {
      return deriveCombatStats(this.state);
    },
  };
}

// ---------------------------------------------------------------------------
//  State Transitions
// ---------------------------------------------------------------------------

/**
 * Apply tongue experience to a companion's state.
 * Shifts tongue position toward the given tongue.
 * A2: Unitarity — magnitude preserved within ε.
 *
 * @param comp - Companion to modify (mutated in place)
 * @param tongue - Which tongue gained experience
 * @param amount - Experience magnitude (0-1)
 */
export function applyTongueExperience(comp: Companion, tongue: TongueCode, amount: number): void {
  const idx = TONGUE_CODES.indexOf(tongue);
  const pos = [...comp.state.tonguePosition] as TongueVector;

  // Shift toward this tongue
  const oldNorm = tongueNorm(pos);
  pos[idx] = Math.min(1.0, pos[idx] + amount * 0.1);

  // A2: Unitarity — renormalize if we grew too much
  const newNorm = tongueNorm(pos);
  if (newNorm > 0 && oldNorm > 0) {
    const targetNorm = Math.min(1.0, oldNorm + amount * 0.02);
    const scale = targetNorm / newNorm;
    for (let i = 0; i < 6; i++) pos[i] *= scale;
  }

  comp.state = { ...comp.state, tonguePosition: pos };
}

/**
 * Apply combat result to companion state.
 *
 * @param comp - Companion to modify
 * @param won - Whether the encounter was won
 * @param difficulty - Problem difficulty (1-10)
 */
export function applyCombatResult(comp: Companion, won: boolean, difficulty: number): void {
  const diffNorm = difficulty / 10;

  if (won) {
    // Grow radius (proof power) — faster for harder problems
    const radiusGain = 0.01 + diffNorm * 0.02;
    const newRadius = Math.min(1.0, comp.state.radius + radiusGain);

    // Improve coherence
    const cohGain = 0.005 + diffNorm * 0.01;

    comp.state = {
      ...comp.state,
      radius: newRadius,
      coherence_s: Math.min(1.0, comp.state.coherence_s + cohGain),
      stabilization: Math.min(1.0, comp.state.stabilization + cohGain * 0.5),
      harmonic_energy: Math.min(1.0, comp.state.harmonic_energy + 0.005),
    };

    // Bond XP
    comp.bondXP += 5 + difficulty;
  } else {
    // Scar event
    comp.scarCount++;

    // Entropy exposure
    const entropyGain = diffNorm * 0.03;
    comp.state = {
      ...comp.state,
      entropy_rate: Math.min(1.0, comp.state.entropy_rate + entropyGain),
      risk: Math.min(1.0, comp.state.risk + 0.01),
    };

    // Seal integrity damage
    comp.sealIntegrity = Math.max(0, comp.sealIntegrity - (10 + difficulty * 3));

    // Bond XP (less, but still some for shared hardship)
    comp.bondXP += 2;
  }

  // Check bond level up (10 XP per level)
  const xpForNext = comp.bondLevel * 10;
  if (comp.bondXP >= xpForNext && comp.bondLevel < 10) {
    comp.bondLevel++;
    comp.bondXP -= xpForNext;
  }

  // Update emotional state
  comp.emotionalState = deriveEmotionalState(comp);
}

/**
 * Apply drift (chaos exposure) to a companion.
 * High drift = volatile: powerful but risky.
 */
export function applyDrift(comp: Companion, amount: number): void {
  comp.driftLevel = Math.min(1.0, Math.max(0, comp.driftLevel + amount));

  // Drift affects coherence negatively but can boost flux
  comp.state = {
    ...comp.state,
    coherence_s: Math.max(0, comp.state.coherence_s - amount * 0.1),
    flux: Math.min(1.0, comp.state.flux + amount * 0.05),
  };
}

/**
 * Rest/heal a companion — reduces drift, restores integrity.
 */
export function restCompanion(comp: Companion, amount: number): void {
  comp.sealIntegrity = Math.min(comp.maxSealIntegrity, comp.sealIntegrity + amount * 20);
  comp.driftLevel = Math.max(0, comp.driftLevel - amount * 0.1);
  comp.state = {
    ...comp.state,
    coherence_bi: Math.min(1.0, comp.state.coherence_bi + amount * 0.05),
  };
  comp.emotionalState = deriveEmotionalState(comp);
}

// ---------------------------------------------------------------------------
//  Emotional State Derivation
// ---------------------------------------------------------------------------

function deriveEmotionalState(comp: Companion): EmotionalState {
  if (comp.driftLevel > 0.8) return 'corrupted';
  if (comp.state.radius > OVER_EVOLUTION_THRESHOLD) return 'transcendent';
  if (comp.sealIntegrity < 20) return 'exhausted';
  if (comp.driftLevel > 0.5) return 'anxious';
  if (comp.state.radius > 0.7 && comp.bondLevel >= 5) return 'determined';
  if (comp.bondXP > 0 && comp.sealIntegrity > 80) return 'excited';
  return 'content';
}

// ---------------------------------------------------------------------------
//  Evolution Check
// ---------------------------------------------------------------------------

/**
 * Determine the current evolution stage from radius.
 */
export function currentEvolutionStage(radius: number): EvolutionStage {
  if (radius >= EVOLUTION_THRESHOLDS.transcendent) return 'transcendent';
  if (radius >= EVOLUTION_THRESHOLDS.apex) return 'apex';
  if (radius >= EVOLUTION_THRESHOLDS.prime) return 'prime';
  if (radius >= EVOLUTION_THRESHOLDS.form) return 'form';
  return 'spark';
}

/**
 * Check if a companion is ready to evolve.
 * Returns the new stage or null if no evolution available.
 */
export function checkEvolution(comp: Companion): EvolutionStage | null {
  const newStage = currentEvolutionStage(comp.state.radius);
  if (newStage !== comp.evolutionStage) {
    return newStage;
  }
  return null;
}

/**
 * Check if companion is over-evolved (unstable).
 * Over-evolved companions may disobey, mutate, or drift.
 */
export function isOverEvolved(comp: Companion): boolean {
  return comp.state.radius > OVER_EVOLUTION_THRESHOLD;
}

// ---------------------------------------------------------------------------
//  Discipline Trait Development
// ---------------------------------------------------------------------------

/**
 * Update discipline trait based on cumulative usage patterns.
 *
 * @param comp - Companion to update
 * @param verifyCount - Number of times used for verification
 * @param soloCount - Number of solo combat encounters
 * @param teamCount - Number of team/fleet encounters
 * @param riskCount - Number of high-risk actions taken
 */
export function updateDisciplineTrait(
  comp: Companion,
  verifyCount: number,
  soloCount: number,
  teamCount: number,
  riskCount: number
): void {
  const total = verifyCount + soloCount + teamCount + riskCount;
  if (total < 10) return; // need enough data

  const verifyRatio = verifyCount / total;
  const soloRatio = soloCount / total;
  const teamRatio = teamCount / total;
  const riskRatio = riskCount / total;

  if (verifyRatio > 0.4) comp.disciplineTrait = 'careful_verifier';
  else if (soloRatio > 0.4) comp.disciplineTrait = 'solo';
  else if (teamRatio > 0.4) comp.disciplineTrait = 'collaborative';
  else if (riskRatio > 0.4) comp.disciplineTrait = 'risk_tolerant';
  else if (comp.sealIntegrity > 90 && comp.state.stabilization > 0.7)
    comp.disciplineTrait = 'guardian';
  else comp.disciplineTrait = 'fast_heuristic';
}
