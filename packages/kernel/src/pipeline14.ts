/**
 * SCBE 14-Layer Pipeline - Complete TypeScript Implementation
 * ============================================================
 *
 * Direct mapping to mathematical specifications from proof document.
 * Each function matches the LaTeX specification exactly.
 *
 * Reference: scbe_proofs_complete.tex, scbe_14layer_reference.py
 *
 * @module harmonic/pipeline14
 * @version 3.0.0
 * @since 2026-01-20
 */

// =============================================================================
// LAYER 1: Complex State
// =============================================================================

/**
 * Layer 1: Complex State Construction
 *
 * Input: Time-dependent features t, dimension D
 * Output: c ∈ ℂ^D
 *
 * Constructs complex-valued state from amplitudes and phases.
 * A1: Map to complex space c = amplitudes × exp(i × phases)
 */
export function layer1ComplexState(t: number[], D: number): { real: number[]; imag: number[] } {
  const amplitudes: number[] = [];
  const phases: number[] = [];

  if (t.length >= 2 * D) {
    for (let i = 0; i < D; i++) {
      amplitudes.push(t[i]);
      phases.push(t[D + i]);
    }
  } else {
    // Handle shorter inputs with defaults
    for (let i = 0; i < D; i++) {
      amplitudes.push(i < t.length / 2 ? t[i] : 1.0);
      phases.push(i < t.length / 2 ? t[Math.floor(t.length / 2) + i] : 0.0);
    }
  }

  // c = amplitude * exp(i * phase) = amplitude * (cos(phase) + i*sin(phase))
  const real: number[] = [];
  const imag: number[] = [];

  for (let i = 0; i < D; i++) {
    real.push(amplitudes[i] * Math.cos(phases[i]));
    imag.push(amplitudes[i] * Math.sin(phases[i]));
  }

  return { real, imag };
}

// =============================================================================
// LAYER 2: Realification
// =============================================================================

/**
 * Layer 2: Realification (Complex → Real)
 *
 * Input: c ∈ ℂ^D
 * Output: x ∈ ℝ^{2D}
 *
 * Isometric embedding Φ_1: ℂ^D → ℝ^{2D}
 * A2: x = [Re(c), Im(c)]
 */
export type RealificationOrder = 'BLOCK_REAL_THEN_IMAG' | 'INTERLEAVED_REAL_IMAG';
export const L02_CANONICAL_ORDER: RealificationOrder = 'BLOCK_REAL_THEN_IMAG';

export function convertLayer2Realification(
  values: number[],
  source: RealificationOrder,
  target: RealificationOrder
): number[] {
  if (
    !Array.isArray(values) ||
    values.length === 0 ||
    values.length % 2 !== 0 ||
    !values.every(Number.isFinite)
  ) {
    throw new Error('L02 vector must be finite, non-empty, and even-length');
  }
  if (source === target) return values.slice();
  const width = values.length / 2;
  if (source === 'BLOCK_REAL_THEN_IMAG') {
    return values.slice(0, width).flatMap((real, index) => [real, values[width + index]]);
  }
  return [
    ...values.filter((_, index) => index % 2 === 0),
    ...values.filter((_, index) => index % 2 === 1),
  ];
}

export function layer2Realification(
  complex: { real: number[]; imag: number[] },
  order: RealificationOrder = L02_CANONICAL_ORDER
): number[] {
  if (complex.real.length !== complex.imag.length || complex.real.length === 0) {
    throw new Error('L02 real and imaginary coordinates must have equal non-zero width');
  }
  return convertLayer2Realification(
    [...complex.real, ...complex.imag],
    'BLOCK_REAL_THEN_IMAG',
    order
  );
}

// =============================================================================
// LAYER 3: Weighted Transform
// =============================================================================

/**
 * Layer 3: SPD Weighted Transform
 *
 * Input: x ∈ ℝ^n, G SPD matrix (optional)
 * Output: x_G = G^{1/2} · x
 *
 * A3: Applies symmetric positive-definite weighting using golden ratio.
 */
function symmetricMatrixSquareRoot(G: number[][], n: number): number[][] {
  if (!Array.isArray(G) || G.length !== n || n === 0) {
    throw new Error('G must be a non-empty square matrix matching x');
  }
  if (
    G.some(
      (row) =>
        !Array.isArray(row) || row.length !== n || row.some((value) => !Number.isFinite(value))
    )
  ) {
    throw new Error('G must be square and finite');
  }

  const scale = Math.max(...G.flat().map((value) => Math.abs(value)));
  const tolerance = 1e-12 * Math.max(scale, Number.MIN_VALUE);
  const A = G.map((row) => row.slice());
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      if (Math.abs(A[i][j] - A[j][i]) > tolerance) {
        throw new Error('G must be symmetric positive-definite');
      }
      const symmetric = 0.5 * (A[i][j] + A[j][i]);
      A[i][j] = symmetric;
      A[j][i] = symmetric;
    }
  }

  const eigenvectors: number[][] = Array.from({ length: n }, (_, i) =>
    Array.from({ length: n }, (_, j) => (i === j ? 1 : 0))
  );
  let converged = n === 1;
  const maxIterations = Math.max(32, 100 * n * n);
  for (let iteration = 0; iteration < maxIterations && !converged; iteration++) {
    let p = 0;
    let q = 1;
    let largest = 0;
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const magnitude = Math.abs(A[i][j]);
        if (magnitude > largest) {
          largest = magnitude;
          p = i;
          q = j;
        }
      }
    }
    if (largest <= tolerance) {
      converged = true;
      break;
    }

    const app = A[p][p];
    const aqq = A[q][q];
    const apq = A[p][q];
    const angle = 0.5 * Math.atan2(2 * apq, aqq - app);
    const c = Math.cos(angle);
    const s = Math.sin(angle);

    for (let i = 0; i < n; i++) {
      if (i === p || i === q) continue;
      const aip = A[i][p];
      const aiq = A[i][q];
      A[i][p] = A[p][i] = c * aip - s * aiq;
      A[i][q] = A[q][i] = s * aip + c * aiq;
    }
    A[p][p] = c * c * app - 2 * s * c * apq + s * s * aqq;
    A[q][q] = s * s * app + 2 * s * c * apq + c * c * aqq;
    A[p][q] = A[q][p] = 0;

    for (let i = 0; i < n; i++) {
      const vip = eigenvectors[i][p];
      const viq = eigenvectors[i][q];
      eigenvectors[i][p] = c * vip - s * viq;
      eigenvectors[i][q] = s * vip + c * viq;
    }
  }
  if (!converged) throw new Error('G eigendecomposition did not converge');

  const eigenvalues = A.map((row, index) => row[index]);
  if (eigenvalues.some((value) => !Number.isFinite(value) || value <= tolerance)) {
    throw new Error('G must be symmetric positive-definite');
  }
  const squareRoot = Array.from({ length: n }, () => new Array(n).fill(0));
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      for (let k = 0; k < n; k++) {
        squareRoot[i][j] += eigenvectors[i][k] * Math.sqrt(eigenvalues[k]) * eigenvectors[j][k];
      }
    }
  }
  return squareRoot;
}

export function layer3WeightedTransform(x: number[], G?: number[][]): number[] {
  const n = x.length;
  const D = Math.floor(n / 2);
  const PHI = 1.618033988749895;

  if (!G) {
    // Default: Golden ratio weighting
    const weights: number[] = [];
    let sumWeights = 0;

    for (let k = 0; k < D; k++) {
      const w = Math.pow(PHI, k);
      weights.push(w);
      sumWeights += w;
    }

    // Normalize weights
    for (let k = 0; k < D; k++) {
      weights[k] /= sumWeights;
    }

    // Apply sqrt(weights) as diagonal transform
    const result: number[] = [];
    for (let i = 0; i < n; i++) {
      const weightIdx = i % D;
      result.push(x[i] * Math.sqrt(weights[weightIdx]));
    }
    return result;
  }

  // A supplied metric uses its true symmetric matrix square root.
  // This preserves ||G^(1/2)x||^2 = x^T G x for every validated SPD G.
  const squareRoot = symmetricMatrixSquareRoot(G, n);
  return squareRoot.map((row) => row.reduce((sum, value, j) => sum + value * x[j], 0));
}

// =============================================================================
// LAYER 4: Poincaré Embedding
// =============================================================================

/**
 * Layer 4: Poincaré Ball Embedding with Clamping
 *
 * Input: x_G ∈ ℝ^n
 * Output: u ∈ 𝔹^n (Poincaré ball)
 *
 * A4: Ψ_α(x) = tanh(α||x||) · x/||x|| with clamping to 𝔹^n_{1-ε}
 */
export function layer4PoincareEmbedding(
  xG: number[],
  alpha: number = 1.0,
  epsBall: number = 0.01
): number[] {
  const norm = Math.sqrt(xG.reduce((sum, val) => sum + val * val, 0));

  if (norm < 1e-12) {
    return new Array(xG.length).fill(0);
  }

  // Poincaré embedding: u = tanh(α||x||) · x/||x||
  const scaledNorm = Math.tanh(alpha * norm);
  const u = xG.map((val) => (scaledNorm * val) / norm);

  // A4: Clamping Π_ε: ensure ||u|| ≤ 1-ε
  const uNorm = Math.sqrt(u.reduce((sum, val) => sum + val * val, 0));
  const maxNorm = 1.0 - epsBall;

  if (uNorm > maxNorm) {
    return u.map((val) => (maxNorm * val) / uNorm);
  }

  return u;
}

// =============================================================================
// LAYER 5: Hyperbolic Distance
// =============================================================================

/**
 * Layer 5: Poincaré Ball Metric
 *
 * Input: u, v ∈ 𝔹^n
 * Output: d_ℍ(u, v) ∈ ℝ₊
 *
 * A5: d_ℍ(u,v) = arcosh(1 + 2||u-v||²/[(1-||u||²)(1-||v||²)])
 */
export function layer5HyperbolicDistance(u: number[], v: number[], eps: number = 1e-5): number {
  let diffNormSq = 0;
  let uNormSq = 0;
  let vNormSq = 0;

  for (let i = 0; i < u.length; i++) {
    const diff = u[i] - v[i];
    diffNormSq += diff * diff;
    uNormSq += u[i] * u[i];
    vNormSq += v[i] * v[i];
  }

  const uFactor = 1.0 - uNormSq;
  const vFactor = 1.0 - vNormSq;

  // Denominator bounded below by eps² due to clamping
  const denom = Math.max(uFactor * vFactor, eps * eps);
  const arg = 1.0 + (2.0 * diffNormSq) / denom;

  return Math.acosh(Math.max(arg, 1.0));
}

// =============================================================================
// LAYER 6: Breathing Transform
// =============================================================================

/**
 * Layer 6: Breathing Map (Diffeomorphism, NOT Isometry)
 *
 * Input: u ∈ 𝔹^n, breathing factor b ∈ [b_min, b_max]
 * Output: u_breathed ∈ 𝔹^n
 *
 * A6: T_breath(u) with radial rescaling (changes distances!)
 */
export function layer6BreathingTransform(
  u: number[],
  b: number,
  bMin: number = 0.5,
  bMax: number = 2.0
): number[] {
  // Clamp breathing factor
  b = Math.max(bMin, Math.min(bMax, b));

  const norm = Math.sqrt(u.reduce((sum, val) => sum + val * val, 0));

  if (norm < 1e-12) {
    return new Array(u.length).fill(0);
  }

  // Breathing: r ↦ tanh(b · arctanh(r))
  const clampedNorm = Math.min(norm, 0.9999);
  const artanhNorm = Math.atanh(clampedNorm);
  const newNorm = Math.tanh(b * artanhNorm);

  return u.map((val) => (newNorm * val) / norm);
}

// =============================================================================
// MÖBIUS TRANSFORMATIONS (Gyrovector Operations)
// =============================================================================

/**
 * Möbius (gyrovector) addition in the Poincaré ball model.
 * True hyperbolic isometry: d(u ⊕ v, w ⊕ v) = d(u, w)
 */
export function mobiusAdd(u: number[], v: number[], eps: number = 1e-10): number[] {
  const u2 = u.reduce((sum, val) => sum + val * val, 0);
  const v2 = v.reduce((sum, val) => sum + val * val, 0);
  const uv = u.reduce((sum, val, i) => sum + val * v[i], 0);

  // Lorentz factor γ_u
  const gammaU = 1.0 / Math.sqrt(1.0 - u2 + eps);

  // Coefficients
  const coeffU = gammaU * (1.0 + gammaU * uv + v2);
  const coeffV = 1.0 - gammaU * gammaU * u2;

  let denom = 1.0 + 2.0 * gammaU * uv + gammaU * gammaU * u2 * v2;
  denom = Math.max(denom, eps);

  const result = u.map((uVal, i) => (coeffU * uVal + coeffV * v[i]) / denom);

  // Numerical safety: clamp if floating-point pushed it to boundary
  const resultNorm = Math.sqrt(result.reduce((sum, val) => sum + val * val, 0));
  if (resultNorm >= 1.0 - 1e-8) {
    const scale = 0.99999999 / resultNorm;
    return result.map((val) => val * scale);
  }

  return result;
}

/**
 * Apply orthogonal rotation Q in the Poincaré ball.
 */
export function mobiusRotate(u: number[], Q: number[][]): number[] {
  const n = u.length;
  const result: number[] = new Array(n).fill(0);

  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      result[i] += Q[i][j] * u[j];
    }
  }

  // Safety clamp
  const norm = Math.sqrt(result.reduce((sum, val) => sum + val * val, 0));
  if (norm >= 1.0 - 1e-8) {
    const scale = 0.99999999 / norm;
    return result.map((val) => val * scale);
  }

  return result;
}

// =============================================================================
// LAYER 7: Phase Transform
// =============================================================================

/**
 * Layer 7: Phase Transform (True Isometry)
 *
 * Input: u ∈ 𝔹^n, shift a ∈ 𝔹^n, rotation Q ∈ O(n)
 * Output: ũ = t_a ∘ R_Q(u) using Möbius operations
 *
 * A7: Uses correct Möbius addition (gyrovector) for distance preservation.
 */
export type PhaseCompositionOrder = 'ROTATE_THEN_TRANSLATE' | 'TRANSLATE_THEN_ROTATE';
export const L07_CANONICAL_ORDER: PhaseCompositionOrder = 'ROTATE_THEN_TRANSLATE';

export function adaptLayer7Shift(
  shift: number[],
  Q: number[][],
  source: PhaseCompositionOrder,
  target: PhaseCompositionOrder
): number[] {
  const n = shift.length;
  if (n === 0 || Q.length !== n || Q.some((row) => row.length !== n)) {
    throw new Error('L07 shift and rotation dimensions differ');
  }
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      let dot = 0;
      for (let k = 0; k < n; k++) dot += Q[k][i] * Q[k][j];
      if (Math.abs(dot - (i === j ? 1 : 0)) > 1e-9)
        throw new Error('L07 rotation must be orthogonal');
    }
  }
  if (source === target) return shift.slice();
  if (source === 'TRANSLATE_THEN_ROTATE') {
    return Q.map((row) => row.reduce((sum, value, index) => sum + value * shift[index], 0));
  }
  return Q.map((_, column) => Q.reduce((sum, row, index) => sum + row[column] * shift[index], 0));
}

export function layer7PhaseTransform(
  u: number[],
  a: number[],
  Q: number[][],
  compositionOrder: PhaseCompositionOrder = L07_CANONICAL_ORDER
): number[] {
  const canonicalShift =
    compositionOrder === L07_CANONICAL_ORDER
      ? a
      : adaptLayer7Shift(a, Q, compositionOrder, L07_CANONICAL_ORDER);
  // Step 1: Apply rotation Q (rotation about origin preserves distance)
  const uRotated = mobiusRotate(u, Q);

  // Step 2: Translate by a using Möbius addition
  return mobiusAdd(canonicalShift, uRotated);
}

// =============================================================================
// LAYER 8: Realm Distance
// =============================================================================

/**
 * Layer 8: Minimum Distance to Realm Centers
 *
 * Input: u ∈ 𝔹^n, realm centers {μ_k} ⊂ 𝔹^n_{1-ε}
 * Output: d* = min_k d_ℍ(u, μ_k)
 *
 * A8: Computes proximity to known safe regions.
 */
export function layer8RealmDistance(
  u: number[],
  realms: number[][],
  eps: number = 1e-5
): { dStar: number; distances: number[] } {
  const distances = realms.map((mu) => layer5HyperbolicDistance(u, mu, eps));
  const dStar = Math.min(...distances);
  return { dStar, distances };
}

// =============================================================================
// LAYER 9: Spectral Coherence
// =============================================================================

/**
 * Layer 9: Spectral Coherence via FFT
 *
 * Input: Time-domain signal
 * Output: S_spec ∈ [0,1]
 *
 * A9: Power at |frequency| < cutoff / total power (cycles/sample).
 * Default cutoff 0.25 is half Nyquist. Count both conjugate bins.
 * Missing input returns 0.5; supplied silence returns 0.0. eps is applied
 * after amplitude normalization, in normalized power units.
 */
export function layer9SpectralCoherence(
  signal: number[] | null,
  eps: number = 1e-5,
  lowFrequencyCutoff: number = 0.25
): number {
  if (!Number.isFinite(eps) || eps < 0) {
    throw new Error('eps must be finite and nonnegative');
  }
  if (!Number.isFinite(lowFrequencyCutoff) || lowFrequencyCutoff <= 0 || lowFrequencyCutoff > 0.5) {
    throw new Error('lowFrequencyCutoff must be in (0, 0.5]');
  }
  if (!signal || signal.length === 0) {
    return 0.5;
  }

  if (!signal.every(Number.isFinite)) {
    throw new Error('signal must contain finite numbers');
  }
  const amplitude = signal.reduce((largest, value) => Math.max(largest, Math.abs(value)), 0);
  if (amplitude === 0) return 0;
  const normalized = signal.map((value) => value / amplitude);
  // Simple DFT power spectrum (no external FFT library needed).
  const N = signal.length;
  let lowEnergy = 0;
  let totalEnergy = 0;

  for (let k = 0; k < N; k++) {
    let realSum = 0;
    let imagSum = 0;
    for (let n = 0; n < N; n++) {
      const angle = (-2 * Math.PI * k * n) / N;
      realSum += normalized[n] * Math.cos(angle);
      imagSum += normalized[n] * Math.sin(angle);
    }
    const power = realSum * realSum + imagSum * imagSum;
    totalEnergy += power;
    if (Math.min(k, N - k) / N < lowFrequencyCutoff) lowEnergy += power;
  }

  const sSpec = lowEnergy / (totalEnergy + eps);

  return Math.max(0, Math.min(1, sSpec));
}

export type ObservationStatus = 'OBSERVED' | 'MISSING' | 'SILENT' | 'TOO_SHORT';
export interface SpectralObservation {
  status: ObservationStatus;
  score: number | null;
  decisionValue: number;
  sampleRateHz: number;
  cutoffHz: number;
}

export function layer9SpectralObservation(
  signal: number[] | null,
  eps: number = 1e-5,
  sampleRateHz: number = 1.0,
  lowFrequencyCutoff: number = 0.25
): SpectralObservation {
  const cutoffHz = sampleRateHz * lowFrequencyCutoff;
  if (
    !Number.isFinite(sampleRateHz) ||
    sampleRateHz <= 0 ||
    !(cutoffHz > 0 && cutoffHz < sampleRateHz / 2)
  ) {
    throw new Error('L09 requires positive sample rate and a cutoff below Nyquist');
  }
  if (!signal || signal.length === 0) {
    return { status: 'MISSING', score: null, decisionValue: 0.5, sampleRateHz, cutoffHz };
  }
  if (!signal.every(Number.isFinite)) throw new Error('L09 signal must be finite');
  if (signal.every((value) => value === 0)) {
    return { status: 'SILENT', score: 0, decisionValue: 0, sampleRateHz, cutoffHz };
  }
  if (signal.length < 4) {
    return { status: 'TOO_SHORT', score: null, decisionValue: 0.5, sampleRateHz, cutoffHz };
  }
  const score = layer9SpectralCoherence(signal, eps, lowFrequencyCutoff);
  return { status: 'OBSERVED', score, decisionValue: score, sampleRateHz, cutoffHz };
}

// =============================================================================
// LAYER 10: Spin Coherence
// =============================================================================

/**
 * Layer 10: Spin Coherence
 *
 * Input: Phase array (or complex phasors as {real, imag})
 * Output: C_spin ∈ [0,1]
 *
 * A10: Mean resultant length of unit phasors.
 */
export function layer10SpinCoherence(phases: number[]): number {
  if (phases.length === 0) {
    return 0.5;
  }

  // Convert phases to unit phasors and compute mean
  let realSum = 0;
  let imagSum = 0;

  for (const phase of phases) {
    realSum += Math.cos(phase);
    imagSum += Math.sin(phase);
  }

  realSum /= phases.length;
  imagSum /= phases.length;

  // Mean phasor magnitude
  const cSpin = Math.sqrt(realSum * realSum + imagSum * imagSum);
  return Math.max(0, Math.min(1, cSpin));
}

// =============================================================================
// LAYER 11: Triadic Temporal Aggregation
// =============================================================================

/**
 * Layer 11: Triadic Temporal Distance
 *
 * Input: Recent (d1), mid-term (d2), global (dG) distances
 * Output: d_tri ∈ [0,1]
 *
 * A11: d_tri = √(λ₁d₁² + λ₂d₂² + λ₃d_G²) / d_scale
 */
export function layer11TriadicTemporal(
  d1: number,
  d2: number,
  dG: number,
  lambda1: number = 0.33,
  lambda2: number = 0.34,
  lambda3: number = 0.33,
  dScale: number = 1.0
): number {
  // Verify weights sum to 1
  const sum = lambda1 + lambda2 + lambda3;
  if (Math.abs(sum - 1.0) > 1e-6) {
    throw new Error(`Lambdas must sum to 1, got ${sum}`);
  }

  const dTri = Math.sqrt(lambda1 * d1 * d1 + lambda2 * d2 * d2 + lambda3 * dG * dG);

  // Normalize to [0,1]
  return Math.min(1.0, dTri / dScale);
}

// =============================================================================
// LAYER 12: Harmonic Scaling
// =============================================================================

/**
 * Layer 12: Harmonic Scaling (Bounded)
 *
 * Input: Distance d_H, phase deviation
 * Output: score = 1 / (1 + d_H + 2 * phaseDeviation)
 *
 * A12: Bounded risk scoring. Returns safety score in (0, 1].
 * Replaces R^(d²) which caused numerical collapse on subtle attacks.
 */
export function layer12HarmonicScaling(d: number, phaseDeviation: number = 0): number {
  return 1 / (1 + d + 2 * phaseDeviation);
}

// =============================================================================
// LAYER 13: Risk Decision
// =============================================================================

export type Decision = 'ALLOW' | 'QUARANTINE' | 'DENY';

/**
 * Layer 13: Three-Way Risk Decision
 *
 * Input: Base risk, harmonic score H ∈ (0, 1]
 * Output: Decision ∈ {ALLOW, QUARANTINE, DENY}
 *
 * A13: Risk' = Risk_base / H (amplified by inverse of safety score).
 * H close to 1 = safe (minimal amplification), H close to 0 = dangerous.
 */
export function layer13RiskDecision(
  riskBase: number,
  H: number,
  theta1: number = 0.33,
  theta2: number = 0.67
): { decision: Decision; riskPrime: number } {
  const riskPrime = riskBase / Math.max(H, 1e-10);

  let decision: Decision;
  if (riskPrime < theta1) {
    decision = 'ALLOW';
  } else if (riskPrime < theta2) {
    decision = 'QUARANTINE';
  } else {
    decision = 'DENY';
  }

  return { decision, riskPrime };
}

// =============================================================================
// LAYER 14: Audio Axis
// =============================================================================

export type TelemetryEnvelope =
  | { kind: 'L14A_AUDIO_COHERENCE_INPUT'; scalar: number; samples: null; executionOrder: 'PRE_L13' }
  | {
      kind: 'L14B_VERDICT_SONIFICATION_OUTPUT';
      scalar: null;
      samples: number[];
      executionOrder: 'POST_L13';
    };

export function audioCoherenceTelemetry(score: number): TelemetryEnvelope {
  if (!Number.isFinite(score) || score < 0 || score > 1)
    throw new Error('L14A requires a bounded scalar');
  return {
    kind: 'L14A_AUDIO_COHERENCE_INPUT',
    scalar: score,
    samples: null,
    executionOrder: 'PRE_L13',
  };
}

export function verdictSonificationTelemetry(samples: number[]): TelemetryEnvelope {
  if (
    !samples.length ||
    !samples.every((value) => Number.isFinite(value) && Math.abs(value) <= 1 + 1e-12)
  ) {
    throw new Error('L14B requires a finite, non-empty, unit-amplitude waveform');
  }
  return {
    kind: 'L14B_VERDICT_SONIFICATION_OUTPUT',
    scalar: null,
    samples: samples.slice(),
    executionOrder: 'POST_L13',
  };
}

/**
 * Layer 14: Audio Telemetry Coherence
 *
 * Input: Audio frame (time-domain waveform)
 * Output: S_audio ∈ [0,1]
 *
 * A14: Instantaneous phase stability via Hilbert transform approximation.
 */
export function layer14AudioAxis(audio: number[] | null, eps: number = 1e-5): number {
  if (!audio || audio.length === 0) {
    return 0.5;
  }

  // Simplified Hilbert transform approximation using DFT
  const N = audio.length;
  const phases: number[] = [];

  // Compute analytic signal phase approximation
  for (let i = 1; i < N; i++) {
    // Simple phase difference approximation
    const phaseDiff = Math.atan2(audio[i] - audio[i - 1], 1);
    phases.push(phaseDiff);
  }

  if (phases.length === 0) {
    return 0.5;
  }

  // Phase derivative stability
  let sumDiff = 0;
  let sumDiffSq = 0;
  for (const p of phases) {
    sumDiff += p;
    sumDiffSq += p * p;
  }

  const mean = sumDiff / phases.length;
  const variance = sumDiffSq / phases.length - mean * mean;
  const stdDev = Math.sqrt(Math.max(0, variance));

  const stability = 1.0 / (1.0 + stdDev + eps);
  return Math.max(0, Math.min(1, stability));
}

// =============================================================================
// FULL 14-LAYER PIPELINE
// =============================================================================

export interface Pipeline14Config {
  D?: number;
  alpha?: number;
  epsBall?: number;
  breathingFactor?: number;
  R?: number;
  theta1?: number;
  theta2?: number;
  // Risk weights (must sum to 1)
  wD?: number; // Distance weight
  wC?: number; // Coherence weight
  wS?: number; // Spin weight
  wTau?: number; // Temporal weight
  wA?: number; // Audio weight
  // Historical data for Layer 11
  dMidTerm?: number;
  dLongTerm?: number;
}

export interface Pipeline14Result {
  decision: Decision;
  riskPrime: number;
  layers: {
    l1_complex: { real: number[]; imag: number[] };
    l2_real: number[];
    l2_coordinateOrder: RealificationOrder;
    l3_weighted: number[];
    l4_poincare: number[];
    l5_distance: number;
    l6_breathed: number[];
    l7_transformed: number[];
    l7_compositionOrder: PhaseCompositionOrder;
    l8_realmDist: number;
    l9_spectral: number;
    l9_observation: SpectralObservation;
    l10_spin: number;
    l11_triadic: number;
    l12_harmonic: number;
    l13_decision: Decision;
    l14_audio: number;
    l14_telemetry: TelemetryEnvelope;
  };
  riskComponents: {
    riskBase: number;
    H: number;
  };
}

/**
 * Execute full 14-layer SCBE pipeline.
 *
 * @param t - Input features (time-dependent context)
 * @param config - Pipeline configuration
 * @returns Comprehensive metrics dictionary
 */
export function scbe14LayerPipeline(t: number[], config: Pipeline14Config = {}): Pipeline14Result {
  const {
    D = 6,
    alpha = 1.0,
    epsBall = 0.01,
    breathingFactor = 1.0,
    R = Math.E,
    theta1 = 0.33,
    theta2 = 0.67,
    wD = 0.2,
    wC = 0.2,
    wS = 0.2,
    wTau = 0.2,
    wA = 0.2,
    dMidTerm,
    dLongTerm,
  } = config;

  const n = 2 * D;

  // Initialize default realms
  const scaling = 0.8 / Math.sqrt(n);
  const realms: number[][] = [
    new Array(n).fill(0),
    new Array(n).fill(scaling * 0.2),
    new Array(n).fill(scaling * 0.3),
    new Array(n).fill(scaling * 0.1),
  ];

  // Default phase shift and rotation
  const phaseShift = new Array(n).fill(0);
  const rotation: number[][] = [];
  for (let i = 0; i < n; i++) {
    rotation.push(new Array(n).fill(0));
    rotation[i][i] = 1; // Identity matrix
  }

  // === LAYER 1: Complex State ===
  const l1_complex = layer1ComplexState(t, D);

  // === LAYER 2: Realification ===
  const l2_real = layer2Realification(l1_complex, L02_CANONICAL_ORDER);

  // === LAYER 3: Weighted Transform ===
  const l3_weighted = layer3WeightedTransform(l2_real);

  // === LAYER 4: Poincaré Embedding ===
  const l4_poincare = layer4PoincareEmbedding(l3_weighted, alpha, epsBall);

  // === LAYER 5: Hyperbolic Distance (to origin) ===
  const origin = new Array(n).fill(0);
  const l5_distance = layer5HyperbolicDistance(l4_poincare, origin);

  // === LAYER 6: Breathing Transform ===
  const l6_breathed = layer6BreathingTransform(l4_poincare, breathingFactor);

  // === LAYER 7: Phase Transform ===
  const l7_transformed = layer7PhaseTransform(
    l6_breathed,
    phaseShift,
    rotation,
    L07_CANONICAL_ORDER
  );

  // === LAYER 8: Realm Distance ===
  const { dStar: l8_realmDist } = layer8RealmDistance(l7_transformed, realms);

  // === LAYER 9: Spectral Coherence ===
  const l9_observation = layer9SpectralObservation(t);
  const l9_spectral = l9_observation.decisionValue;

  // === LAYER 10: Spin Coherence ===
  // Use phases from L1 for spin coherence
  const phases = t.length >= D ? t.slice(D, 2 * D) : t;
  const l10_spin = layer10SpinCoherence(phases);

  // === LAYER 11: Triadic Temporal ===
  // Use provided historical distances or fallback to current
  const l11_triadic = layer11TriadicTemporal(
    l8_realmDist,
    dMidTerm ?? l8_realmDist,
    dLongTerm ?? l8_realmDist
  );

  // === LAYER 12: Harmonic Scaling ===
  const l12_harmonic = layer12HarmonicScaling(l8_realmDist);

  // === LAYER 14: Audio Axis ===
  const l14_audio = layer14AudioAxis(t);
  const l14_telemetry = audioCoherenceTelemetry(l14_audio);

  // === Compute Base Risk ===
  // Verify weights sum to 1.0 (approx)
  const weightSum = wD + wC + wS + wTau + wA;
  const scale = Math.abs(weightSum - 1.0) < 1e-6 ? 1.0 : 1.0 / weightSum;

  const riskBase =
    scale *
    (wD * l8_realmDist +
      wC * (1 - l9_spectral) +
      wS * (1 - l10_spin) +
      wTau * l11_triadic +
      wA * (1 - l14_audio));

  // === LAYER 13: Risk Decision ===
  const { decision: l13_decision, riskPrime } = layer13RiskDecision(
    riskBase,
    l12_harmonic,
    theta1,
    theta2
  );

  return {
    decision: l13_decision,
    riskPrime,
    layers: {
      l1_complex,
      l2_real,
      l2_coordinateOrder: L02_CANONICAL_ORDER,
      l3_weighted,
      l4_poincare,
      l5_distance,
      l6_breathed,
      l7_transformed,
      l7_compositionOrder: L07_CANONICAL_ORDER,
      l8_realmDist,
      l9_spectral,
      l9_observation,
      l10_spin,
      l11_triadic,
      l12_harmonic,
      l13_decision,
      l14_audio,
      l14_telemetry,
    },
    riskComponents: {
      riskBase,
      H: l12_harmonic,
    },
  };
}

// =============================================================================
// EXPORTS SUMMARY
// =============================================================================

export {
  layer1ComplexState as complexState,
  layer2Realification as realification,
  layer3WeightedTransform as weightedTransform,
  layer4PoincareEmbedding as poincareEmbedding,
  layer5HyperbolicDistance as hyperbolicDistance,
  layer6BreathingTransform as breathingTransform,
  layer7PhaseTransform as phaseTransform,
  layer8RealmDistance as realmDistance,
  layer9SpectralCoherence as spectralCoherence,
  layer10SpinCoherence as spinCoherence,
  layer11TriadicTemporal as triadicTemporal,
  layer12HarmonicScaling as harmonicScaling,
  layer13RiskDecision as riskDecision,
  layer14AudioAxis as audioAxis,
};
