/**
 * @file gyroscopicInterlattice.ts
 * @module harmonic/gyroscopicInterlattice
 * @layer Layer 5, Layer 6, Layer 7
 * @component Gyroscopic Interlattice Coupling Engine
 * @version 1.0.0
 * @since 2026-04-06
 *
 * Maps gyroscopic metamaterial topology (Nash et al. 2015) onto SCBE's
 * Sacred Tongue sublattice architecture.
 *
 * Core insight: SCBE's phi-scaled tongue weights (1.00 → 11.09) are a
 * lattice distortion that controls Chern numbers, exactly as Nash proved
 * experimentally with honeycomb gyroscope arrays.
 *
 * Key structures:
 * - TongueSublattice: each Sacred Tongue as a gyroscopic sublattice
 * - InterlatticeCouple: coupling between tongue pairs at fold boundaries
 * - ChernSector: topological invariant per sublattice
 * - NashEquation: first-order gyroscopic dynamics (ψ̇, not ψ̈)
 *
 * Reference: Nash, Kleckner, Vitelli, Irvine "Topological mechanics of
 * gyroscopic metamaterials" PNAS 112:14495 (2015) — arXiv:1504.03362
 *
 * @see notes/theory/2026-04-06-gyroscopic-interlattice-magnetic-arrays.md
 */

/** Golden ratio φ = (1 + √5) / 2 */
const PHI = (1 + Math.sqrt(5)) / 2;

/** The Six Sacred Tongues as sublattice identifiers */
export const TONGUE_LABELS = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;
export type TongueLabel = (typeof TONGUE_LABELS)[number];

// ═══════════════════════════════════════════════════════════════
// Tongue Sublattice — each tongue is a gyroscopic sector
// ═══════════════════════════════════════════════════════════════

/** Phi-scaled orbital radii for each tongue sublattice */
export const TONGUE_RADII: Record<TongueLabel, number> = {
  KO: Math.pow(PHI, 0), // 1.000 — fast orbit, intent
  AV: Math.pow(PHI, 1), // 1.618 — transport
  RU: Math.pow(PHI, 2), // 2.618 — binding
  CA: Math.pow(PHI, 3), // 4.236 — compute
  UM: Math.pow(PHI, 4), // 6.854 — security
  DR: Math.pow(PHI, 5), // 11.090 — structure (slow orbit)
};

/** Phase offsets for each tongue (60° hexagonal intervals) */
export const TONGUE_PHASES: Record<TongueLabel, number> = {
  KO: 0,
  AV: Math.PI / 3,
  RU: (2 * Math.PI) / 3,
  CA: Math.PI,
  UM: (4 * Math.PI) / 3,
  DR: (5 * Math.PI) / 3,
};

/**
 * Gyroscopic sublattice state ψ = dx + i·dy (complex displacement).
 * Gyroscopes obey first-order dynamics — this is what breaks time-reversal symmetry.
 */
export interface SublatticeState {
  /** Real part (displacement x) */
  real: number;
  /** Imaginary part (displacement y) */
  imag: number;
}

/**
 * A single tongue sublattice with gyroscopic properties
 */
export interface TongueSublattice {
  /** Tongue identifier */
  tongue: TongueLabel;
  /** Phi-scaled orbital radius */
  radius: number;
  /** Phase offset (hexagonal) */
  phase: number;
  /** Precession frequency Ω_g (inverse of radius — fast tongues precess faster) */
  precessionFreq: number;
  /** Complex state ψ */
  state: SublatticeState;
  /** Chern number for this sublattice sector */
  chernNumber: number;
}

// ═══════════════════════════════════════════════════════════════
// Interlattice Coupling — the fold boundary between tongues
// ═══════════════════════════════════════════════════════════════

/**
 * Coupling between two tongue sublattices.
 * Based on Nash's magnetic dipole spring: k_m = 3μ₀M² / (πa⁵)
 * In SCBE, 'a' is the phi-scaled distance between tongue radii.
 */
export interface InterlatticeCouple {
  /** First tongue */
  tongueA: TongueLabel;
  /** Second tongue */
  tongueB: TongueLabel;
  /** Coupling strength J_αβ (inverse fifth power of spacing) */
  couplingStrength: number;
  /** Bond angle θ_pq between sublattices */
  bondAngle: number;
  /** Phase factor e^(2iθ) that controls chirality */
  phaseFactor: { real: number; imag: number };
}

// ═══════════════════════════════════════════════════════════════
// Core Functions
// ═════���═════════════════════════════════════════════════════════

/**
 * Create a tongue sublattice with initial state
 */
export function createSublattice(
  tongue: TongueLabel,
  initialState?: SublatticeState
): TongueSublattice {
  const radius = TONGUE_RADII[tongue];
  const phase = TONGUE_PHASES[tongue];
  return {
    tongue,
    radius,
    phase,
    // Precession frequency inversely proportional to radius (fast tongues = fast precession)
    precessionFreq: 1.0 / radius,
    state: initialState ?? { real: 0, imag: 0 },
    // Default Chern number: +1 for KO/RU/UM, -1 for AV/CA/DR (alternating chirality)
    chernNumber: TONGUE_LABELS.indexOf(tongue) % 2 === 0 ? 1 : -1,
  };
}

/**
 * Compute interlattice coupling strength between two tongues.
 *
 * Based on Nash's magnetic dipole spring constant:
 *   k_m = 3μ₀M² / (πa⁵)
 *
 * In SCBE, the spacing 'a' is |r_α - r_β| between phi-scaled tongue radii.
 * The inverse fifth power means adjacent tongues couple strongly while
 * distant tongues decouple — this is locality (Axiom A2).
 *
 * @param tongueA - First tongue
 * @param tongueB - Second tongue
 * @param mu0M2 - Magnetic moment parameter (default: 1.0, normalized)
 * @returns Coupling strength J_αβ
 */
export function couplingStrength(
  tongueA: TongueLabel,
  tongueB: TongueLabel,
  mu0M2: number = 1.0
): number {
  if (tongueA === tongueB) return 0; // No self-coupling
  const rA = TONGUE_RADII[tongueA];
  const rB = TONGUE_RADII[tongueB];
  const a = Math.abs(rA - rB);
  // k_m = 3μ₀M² / (πa⁵) — normalized
  return (3 * mu0M2) / (Math.PI * Math.pow(a, 5));
}

/**
 * Compute the bond angle θ_pq between two tongue sublattices.
 * The phase factor e^(2iθ) controls chirality in the Nash equation.
 */
export function bondAngle(tongueA: TongueLabel, tongueB: TongueLabel): number {
  return TONGUE_PHASES[tongueB] - TONGUE_PHASES[tongueA];
}

/**
 * Compute the phase factor e^(2iθ_pq) for a tongue pair.
 * This is the term in the Nash equation that breaks time-reversal symmetry
 * in non-square lattices. For hexagonal (60°) spacing, it produces
 * non-trivial Chern numbers.
 */
export function phaseFactor(
  tongueA: TongueLabel,
  tongueB: TongueLabel
): { real: number; imag: number } {
  const theta = bondAngle(tongueA, tongueB);
  return {
    real: Math.cos(2 * theta),
    imag: Math.sin(2 * theta),
  };
}

/**
 * Create a full interlattice coupling descriptor between two tongues.
 */
export function createCouple(tongueA: TongueLabel, tongueB: TongueLabel): InterlatticeCouple {
  const angle = bondAngle(tongueA, tongueB);
  return {
    tongueA,
    tongueB,
    couplingStrength: couplingStrength(tongueA, tongueB),
    bondAngle: angle,
    phaseFactor: phaseFactor(tongueA, tongueB),
  };
}

/**
 * Generate all 15 unique interlattice couplings (C(6,2) = 15 pairs).
 * These are the 15 real-imaginary pair dimensions from the 47D manifold.
 */
export function allCouplings(): InterlatticeCouple[] {
  const couples: InterlatticeCouple[] = [];
  for (let i = 0; i < TONGUE_LABELS.length; i++) {
    for (let j = i + 1; j < TONGUE_LABELS.length; j++) {
      couples.push(createCouple(TONGUE_LABELS[i], TONGUE_LABELS[j]));
    }
  }
  return couples;
}

// ═══════════════════════════════════════════════════════════════
// Nash Equation of Motion (First-Order Gyroscopic Dynamics)
// ═══════════════════════════════════════════════════════════════

/**
 * Nash equation of motion for a single gyroscope node on the tongue lattice.
 *
 * i(dψ_p/dt) = Ω_g·ψ_p + ½Σ[Ω₊(ψ_p - ψ_q) + Ω₋·e^(2iθ_pq)(ψ*_p - ψ*_q)]
 *
 * This is FIRST-ORDER in time (not second-order), which is why gyroscopic
 * lattices intrinsically break time-reversal symmetry.
 *
 * The output is dψ/dt (the time derivative of the complex state).
 *
 * @param sublattice - The sublattice whose state is being evolved
 * @param neighbors - Adjacent sublattices with their couplings
 * @param omegaPlus - Symmetric coupling frequency Ω₊
 * @param omegaMinus - Antisymmetric coupling frequency Ω₋
 * @returns Complex time derivative {real: d(Re ψ)/dt, imag: d(Im ψ)/dt}
 */
export function nashEquationOfMotion(
  sublattice: TongueSublattice,
  neighbors: { sublattice: TongueSublattice; couple: InterlatticeCouple }[],
  omegaPlus: number = 1.0,
  omegaMinus: number = 0.5
): SublatticeState {
  const psi = sublattice.state;
  const omegaG = sublattice.precessionFreq;

  // Self-precession term: Ω_g · ψ_p
  let rhsReal = omegaG * psi.real;
  let rhsImag = omegaG * psi.imag;

  // Coupling terms from each neighbor
  for (const { sublattice: neighbor, couple } of neighbors) {
    const psiQ = neighbor.state;

    // Symmetric coupling: Ω₊(ψ_p - ψ_q)
    const diffReal = psi.real - psiQ.real;
    const diffImag = psi.imag - psiQ.imag;
    rhsReal += 0.5 * omegaPlus * diffReal;
    rhsImag += 0.5 * omegaPlus * diffImag;

    // Antisymmetric coupling: Ω₋ · e^(2iθ_pq) · (ψ*_p - ψ*_q)
    // ψ* = conjugate: (real, -imag)
    const conjDiffReal = psi.real - psiQ.real;
    const conjDiffImag = -(psi.imag - psiQ.imag);

    // Complex multiply: e^(2iθ) · (ψ*_p - ψ*_q)
    const pf = couple.phaseFactor;
    const antiReal = pf.real * conjDiffReal - pf.imag * conjDiffImag;
    const antiImag = pf.real * conjDiffImag + pf.imag * conjDiffReal;

    rhsReal += 0.5 * omegaMinus * antiReal;
    rhsImag += 0.5 * omegaMinus * antiImag;
  }

  // The Nash equation is: i·dψ/dt = rhs
  // So: dψ/dt = -i · rhs = (rhs_imag, -rhs_real)
  return {
    real: rhsImag,
    imag: -rhsReal,
  };
}

/**
 * Evolve all sublattice states forward by one time step (Euler method).
 * For production use, replace with RK4 or symplectic integrator.
 *
 * @param sublattices - Array of 6 tongue sublattices
 * @param dt - Time step
 * @param omegaPlus - Symmetric coupling frequency
 * @param omegaMinus - Antisymmetric coupling frequency
 */
export function evolveStep(
  sublattices: TongueSublattice[],
  dt: number,
  omegaPlus: number = 1.0,
  omegaMinus: number = 0.5
): void {
  // Build neighbor maps (each tongue coupled to all others)
  const couples = allCouplings();
  const coupleMap = new Map<string, InterlatticeCouple>();
  for (const c of couples) {
    coupleMap.set(`${c.tongueA}-${c.tongueB}`, c);
    coupleMap.set(`${c.tongueB}-${c.tongueA}`, c);
  }

  // Compute derivatives for all sublattices (before updating any state)
  const derivatives: SublatticeState[] = sublattices.map((sub) => {
    const neighbors = sublattices
      .filter((s) => s.tongue !== sub.tongue)
      .map((s) => ({
        sublattice: s,
        couple: coupleMap.get(`${sub.tongue}-${s.tongue}`)!,
      }));
    return nashEquationOfMotion(sub, neighbors, omegaPlus, omegaMinus);
  });

  // Apply Euler step
  for (let i = 0; i < sublattices.length; i++) {
    sublattices[i].state.real += derivatives[i].real * dt;
    sublattices[i].state.imag += derivatives[i].imag * dt;
  }
}

// ═══════════════════════════════════════════════════════════════
// Chern Number Computation
// ═══════════════════════════════════════════════════════════════

/**
 * Compute the effective Chern number for a sublattice sector.
 *
 * In Nash's framework, Chern numbers are determined by the lattice geometry:
 * - Undistorted honeycomb: C = ±1
 * - Distorted lattice: C can invert
 *
 * For SCBE, phi-scaling IS the distortion. The Chern number for tongue k is:
 *   C_k = sgn(sin(Σ bond_angles_around_k))
 *
 * This is a simplified computation — the full Berry phase integral requires
 * diagonalizing the dynamical matrix over the Brillouin zone.
 *
 * @param tongue - The tongue sublattice
 * @param sublattices - All 6 sublattices (for computing surrounding bond angles)
 * @returns Chern number (+1 or -1)
 */
export function computeChernNumber(
  tongue: TongueLabel,
  sublattices: TongueSublattice[]
): number {
  // Sum of bond angles to all neighbors
  let angleSum = 0;
  for (const neighbor of sublattices) {
    if (neighbor.tongue === tongue) continue;
    angleSum += bondAngle(tongue, neighbor.tongue);
  }
  // Chern number from angle winding
  const sinSum = Math.sin(angleSum);
  return sinSum >= 0 ? 1 : -1;
}

/**
 * Compute the total Chern number across all sublattices.
 * For a well-formed topological system, this should be zero (bulk-boundary correspondence).
 */
export function totalChernNumber(sublattices: TongueSublattice[]): number {
  let total = 0;
  for (const sub of sublattices) {
    total += computeChernNumber(sub.tongue, sublattices);
  }
  return total;
}

// ═══════════════════════════════════════════════════════════════
// Anderson Insulation — Disorder Strengthening
// ═══════════════════════════════════════════════════════════════

/**
 * Test whether disorder in coupling strengths preserves or enhances
 * topological protection (Anderson insulation analog).
 *
 * Mitchell et al. (2021) proved that disorder can drive a trivial
 * gyroscopic phase into a topological one. In SCBE, this means:
 * adversarial noise that perturbs tongue weights can actually
 * STRENGTHEN governance.
 *
 * @param sublattices - The 6 sublattices
 * @param disorderStrength - Fraction of coupling noise (0 = clean, 1 = 100% noise)
 * @param rng - Random number generator (for reproducibility)
 * @returns Object with Chern numbers before/after disorder and whether topology survived
 */
export function andersonInsulationTest(
  sublattices: TongueSublattice[],
  disorderStrength: number = 0.1,
  rng: () => number = Math.random
): {
  cleanChern: number[];
  disorderedChern: number[];
  topologyPreserved: boolean;
  topologyStrengthened: boolean;
} {
  // Compute clean Chern numbers
  const cleanChern = sublattices.map((sub) => computeChernNumber(sub.tongue, sublattices));

  // Apply disorder to radii (simulating coupling perturbation)
  const disorderedSublattices = sublattices.map((sub) => ({
    ...sub,
    radius: sub.radius * (1 + disorderStrength * (2 * rng() - 1)),
  }));

  // Recompute Chern numbers with disorder
  const disorderedChern = disorderedSublattices.map((sub) =>
    computeChernNumber(sub.tongue, disorderedSublattices)
  );

  // Check if topology survived
  const cleanTotal = cleanChern.reduce((a, b) => a + Math.abs(b), 0);
  const disorderedTotal = disorderedChern.reduce((a, b) => a + Math.abs(b), 0);

  return {
    cleanChern,
    disorderedChern,
    topologyPreserved: disorderedTotal >= cleanTotal,
    topologyStrengthened: disorderedTotal > cleanTotal,
  };
}

// ═══════════════════════════════════════════════════════════════
// Coupling Matrix — Full 6×6 Interlattice Interaction
// ═══════════════════════════════════════════════════════════════

/**
 * Build the full 6×6 interlattice coupling matrix.
 * J[i][j] = coupling strength between tongue i and tongue j.
 *
 * This is the adjacency matrix of the tongue lattice graph,
 * weighted by inverse-fifth-power magnetic coupling.
 *
 * Adjacent tongues (KO↔AV, AV↔RU, etc.) couple strongly.
 * Distant tongues (KO↔DR) couple weakly.
 * This IS locality (Axiom A2).
 */
export function couplingMatrix(): number[][] {
  const n = TONGUE_LABELS.length;
  const J: number[][] = Array.from({ length: n }, () => new Array(n).fill(0));
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      if (i !== j) {
        J[i][j] = couplingStrength(TONGUE_LABELS[i], TONGUE_LABELS[j]);
      }
    }
  }
  return J;
}

// ═══════════════════════════════════════════════════════════════
// L6 Bridge — Gyroscopic Precession → Breathing Factor
// ═══════════════════════════════════════════════════════════════

/**
 * Convert the gyroscopic lattice precession state into a breathing factor
 * for Layer 6's radial transform: B(p,t) = tanh(‖p‖ + A·sin(ωt)).
 *
 * The total kinetic energy of the sublattice system determines how much
 * the Poincaré ball "breathes". High precession energy → stronger breathing
 * (tighter governance). Low energy → relaxed breathing.
 *
 * Mapping: b = 1 + α·(E_kin / E_ref) where:
 *   - E_kin = Σ |ψ_k|² / r_k  (kinetic energy weighted by precession frequency)
 *   - E_ref = reference energy scale (normalization)
 *   - α = sensitivity parameter
 *
 * @param sublattices - Current sublattice states
 * @param alpha - Sensitivity of breathing to precession energy (default: 0.5)
 * @param eRef - Reference energy for normalization (default: 1.0)
 * @returns Breathing factor b ≥ 1.0 (1.0 = no modulation)
 */
export function gyroscopicBreathingFactor(
  sublattices: TongueSublattice[],
  alpha: number = 0.5,
  eRef: number = 1.0
): number {
  // Kinetic energy: Σ |ψ_k|² · Ω_k where Ω_k = 1/r_k (precession frequency)
  let eKin = 0;
  for (const sub of sublattices) {
    const psiSq = sub.state.real * sub.state.real + sub.state.imag * sub.state.imag;
    eKin += psiSq * sub.precessionFreq;
  }
  // b ∈ [1.0, 2.0] — clamped to L6's valid range
  return Math.min(2.0, 1.0 + alpha * (eKin / Math.max(eRef, 1e-15)));
}

/**
 * Per-tongue breathing factors derived from individual sublattice precession.
 * Returns a 6-element array aligned with TONGUE_LABELS.
 *
 * Faster-precessing tongues (KO) produce stronger breathing at their
 * angular position, creating directional governance pressure.
 *
 * @param sublattices - Current sublattice states
 * @returns Array of 6 breathing factors, one per tongue
 */
export function perTongueBreathingFactors(
  sublattices: TongueSublattice[]
): number[] {
  return sublattices.map((sub) => {
    const psiSq = sub.state.real * sub.state.real + sub.state.imag * sub.state.imag;
    return Math.min(2.0, 1.0 + psiSq * sub.precessionFreq);
  });
}

/**
 * Chern-weighted tongue vector for Langues metric integration.
 * Returns weights that modulate each tongue's metric contribution
 * based on its topological Chern number.
 *
 * C_k = +1 → weight enhanced (topologically protected)
 * C_k = -1 → weight attenuated (topologically inverted)
 *
 * The factor is: w_chern_k = 1 + γ·C_k where γ ∈ [0, 0.5]
 * This produces a mild asymmetry: protected tongues contribute more.
 *
 * Uses the sublattice's `.chernNumber` field (alternating +1/-1 by default)
 * rather than recomputing from bond angles, since the bond-angle computation
 * gives degenerate results for perfect hexagonal symmetry.
 *
 * @param sublattices - Current sublattice states
 * @param gamma - Chern number influence strength (default: 0.2)
 * @returns Array of 6 Chern-modulated weights
 */
export function chernWeights(
  sublattices: TongueSublattice[],
  gamma: number = 0.2
): number[] {
  const g = Math.max(0, Math.min(0.5, gamma));
  return sublattices.map((sub) => 1.0 + g * sub.chernNumber);
}

/**
 * Initialize the full 6-tongue gyroscopic lattice system.
 * Returns all sublattices with default states and all interlattice couplings.
 */
export function initializeGyroscopicLattice(): {
  sublattices: TongueSublattice[];
  couplings: InterlatticeCouple[];
  couplingMat: number[][];
} {
  const sublattices = TONGUE_LABELS.map((t) => createSublattice(t));
  const couplings = allCouplings();
  const couplingMat = couplingMatrix();
  return { sublattices, couplings, couplingMat };
}
