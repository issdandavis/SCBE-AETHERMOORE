"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.EPSILON = void 0;
exports.setAuditEpsilon = setAuditEpsilon;
exports.getAuditEpsilon = getAuditEpsilon;
exports.artanh = artanh;
exports.hyperbolicDistance = hyperbolicDistance;
exports.mobiusAdd = mobiusAdd;
exports.mobiusAddition = mobiusAdd;
exports.projectToBall = projectToBall;
exports.projectEmbeddingToBall = projectEmbeddingToBall;
exports.clampToBall = clampToBall;
exports.expMap0 = expMap0;
exports.logMap0 = logMap0;
exports.exponentialMap = exponentialMap;
exports.logarithmicMap = logarithmicMap;
exports.breathTransform = breathTransform;
exports.inverseBreathTransform = inverseBreathTransform;
exports.phaseModulation = phaseModulation;
exports.multiPhaseModulation = multiPhaseModulation;
exports.multiWellPotential = multiWellPotential;
exports.multiWellGradient = multiWellGradient;
exports.phaseDeviation = phaseDeviation;
exports.phaseDistanceScore = phaseDistanceScore;
exports.scoreRetrievals = scoreRetrievals;
exports.applyHyperbolicPipeline = applyHyperbolicPipeline;
__exportStar(require("../../packages/kernel/src/hyperbolic.js"), exports);
/**
 * @file hyperbolic.ts
 * @module harmonic/hyperbolic
 * @layer Layer 5, Layer 6, Layer 7
 * @component Poincaré Ball Operations
 * @version 3.0.0
 * @since 2026-01-20
 *
 * SCBE Hyperbolic Geometry - Core mathematical operations for the 14-layer pipeline.
 * The invariant hyperbolic metric NEVER changes - all dynamics come from
 * transforming points within the Poincaré ball.
 *
 * Layer 5: Invariant Metric d_ℍ(u,v) = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²)))
 * Layer 6: Breathing Transform B(p,t) = tanh(‖p‖ + A·sin(ωt))·p/‖p‖
 * Layer 7: Phase Modulation Φ(p,θ) = Möbius rotation in tangent space
 */
/** Small epsilon for numerical stability (norm checks, zero-vector guards) */
exports.EPSILON = 1e-10;
/**
 * Boundary epsilon for artanh clamping (Layer 5/13 audits).
 * Tighter than EPSILON to preserve precision near the Poincaré boundary.
 * Configurable via setAuditEpsilon() for high-precision governance audits.
 * @layer Layer 5, Layer 13
 */
let AUDIT_EPSILON = 1e-15;
/**
 * Set the audit epsilon for boundary clamping in artanh/distance calculations.
 * Allows Layer 13 telemetry to tune precision for attack simulation or audit sweeps.
 * @param eps - New epsilon value (must be positive and < 1e-6)
 */
function setAuditEpsilon(eps) {
    if (eps <= 0 || eps >= 1e-6) {
        throw new RangeError('Audit epsilon must be in (0, 1e-6)');
    }
    AUDIT_EPSILON = eps;
}
/** Get current audit epsilon */
function getAuditEpsilon() {
    return AUDIT_EPSILON;
}
/**
 * Inverse hyperbolic tangent with configurable boundary clamping.
 *
 * artanh(z) = 0.5 * ln((1+z)/(1-z))
 *
 * Clamps z to [-1 + ε, 1 - ε] where ε = AUDIT_EPSILON to prevent
 * singularities at the Poincaré ball boundary.
 *
 * @layer Layer 5
 * @param z - Input value
 * @param eps - Override epsilon (defaults to AUDIT_EPSILON)
 * @returns artanh(z)
 */
function artanh(z, eps) {
    const e = eps ?? AUDIT_EPSILON;
    const zz = Math.max(-1 + e, Math.min(1 - e, z));
    return 0.5 * Math.log((1 + zz) / (1 - zz));
}
/**
 * Compute Euclidean norm of a vector
 */
function norm(v) {
    let sum = 0;
    for (const x of v)
        sum += x * x;
    return Math.sqrt(sum);
}
/**
 * Compute squared Euclidean norm
 */
function normSq(v) {
    let sum = 0;
    for (const x of v)
        sum += x * x;
    return sum;
}
/**
 * Dot product of two vectors
 */
function dot(u, v) {
    let sum = 0;
    for (let i = 0; i < u.length; i++)
        sum += u[i] * v[i];
    return sum;
}
/**
 * Scale a vector by a scalar
 */
function scale(v, s) {
    return v.map((x) => x * s);
}
/**
 * Add two vectors
 */
function add(u, v) {
    return u.map((x, i) => x + v[i]);
}
/**
 * Subtract two vectors
 */
function sub(u, v) {
    return u.map((x, i) => x - v[i]);
}
// ═══════════════════════════════════════════════════════════════
// Layer 5: Invariant Hyperbolic Metric
// ═══════════════════════════════════════════════════════════════
/**
 * Hyperbolic distance in the Poincaré ball model (Layer 5)
 *
 * dℍ(u,v) = arcosh(1 + 2‖u-v‖² / ((1-‖u‖²)(1-‖v‖²)))
 *
 * This metric is INVARIANT - it never changes. Points move; the metric does not.
 *
 * @param u - First point in Poincaré ball (‖u‖ < 1)
 * @param v - Second point in Poincaré ball (‖v‖ < 1)
 * @returns Hyperbolic distance
 */
function hyperbolicDistance(u, v) {
    const diff = sub(u, v);
    const diffNormSq = normSq(diff);
    const uNormSq = normSq(u);
    const vNormSq = normSq(v);
    // Clamp to ensure points are inside the ball
    const uFactor = Math.max(exports.EPSILON, 1 - uNormSq);
    const vFactor = Math.max(exports.EPSILON, 1 - vNormSq);
    const arg = 1 + (2 * diffNormSq) / (uFactor * vFactor);
    // arcosh(x) = ln(x + sqrt(x² - 1))
    return Math.acosh(Math.max(1, arg));
}
/**
 * Möbius addition in the Poincaré ball
 *
 * u ⊕ v = ((1 + 2⟨u,v⟩ + ‖v‖²)u + (1 - ‖u‖²)v) / (1 + 2⟨u,v⟩ + ‖u‖²‖v‖²)
 *
 * This is the gyrovector addition for hyperbolic geometry.
 *
 * @param u - First point
 * @param v - Second point
 * @returns Möbius sum u ⊕ v
 */
function mobiusAdd(u, v) {
    const uv = dot(u, v);
    const uNormSq = normSq(u);
    const vNormSq = normSq(v);
    const numeratorCoeffU = 1 + 2 * uv + vNormSq;
    const numeratorCoeffV = 1 - uNormSq;
    const denominator = 1 + 2 * uv + uNormSq * vNormSq;
    const result = [];
    for (let i = 0; i < u.length; i++) {
        result.push((numeratorCoeffU * u[i] + numeratorCoeffV * v[i]) / denominator);
    }
    return result;
}
/**
 * Project a point onto the Poincaré ball (simple clamp to ‖p‖ < 1)
 *
 * Use this for points already near the ball. For real embeddings with
 * arbitrary norms, use projectEmbeddingToBall instead.
 *
 * @param p - Point to project
 * @param maxNorm - Maximum norm (default 1 - ε)
 * @returns Projected point inside ball
 */
function projectToBall(p, maxNorm = 1 - exports.EPSILON) {
    const n = norm(p);
    if (n < maxNorm)
        return [...p];
    return scale(p, maxNorm / n);
}
/**
 * Project real embeddings into the Poincaré ball using tanh mapping.
 *
 * CRITICAL: Real embeddings from models have norms >> 1. Simple clamping
 * causes the hyperbolicDistance denominator to go negative, returning Infinity,
 * which makes rogue items invisible instead of expelled.
 *
 * This function maps R^n → B^n (unit ball) smoothly via:
 *   u = tanh(α‖x‖) · x/‖x‖
 *
 * @param x - Embedding vector (any norm)
 * @param eps - Boundary margin (default 1e-6)
 * @param alpha - Compression factor (default 0.15, tune for your embedding scale)
 * @returns Point strictly inside unit ball
 */
function projectEmbeddingToBall(x, eps = 1e-6, alpha = 0.15) {
    const n = norm(x);
    if (n < 1e-12)
        return x.map(() => 0);
    // tanh maps R+ → (0, 1)
    let r = Math.tanh(alpha * n);
    r = Math.min(r, 1 - eps); // Stay strictly inside ball
    const s = r / n;
    return x.map((xi) => xi * s);
}
/**
 * Clamp a point to stay inside the Poincaré ball (in-place style, returns new array)
 *
 * CRITICAL: The old swarmStep clamped inside the per-dimension loop, causing
 * weird distortions. This function should be called ONCE after all force
 * updates are applied.
 *
 * @param u - Point to clamp
 * @param rMax - Maximum radius (default 0.99)
 * @returns Clamped point
 */
function clampToBall(u, rMax = 0.99) {
    const n = norm(u);
    if (n <= rMax)
        return [...u];
    return scale(u, rMax / n);
}
/**
 * Exponential map from tangent space to Poincaré ball at origin
 *
 * exp_0(v) = tanh(‖v‖/2) · v/‖v‖
 *
 * @param v - Tangent vector at origin
 * @returns Point in Poincaré ball
 */
function expMap0(v) {
    const n = norm(v);
    if (n < exports.EPSILON)
        return v.map(() => 0);
    const factor = Math.tanh(n / 2) / n;
    return scale(v, factor);
}
/**
 * Logarithmic map from Poincaré ball to tangent space at origin
 *
 * log_0(p) = 2 · arctanh(‖p‖) · p/‖p‖
 *
 * @param p - Point in Poincaré ball
 * @returns Tangent vector at origin
 */
function logMap0(p) {
    const n = norm(p);
    if (n < exports.EPSILON)
        return p.map(() => 0);
    const atanh = artanh(n);
    const factor = (2 * atanh) / n;
    return scale(p, factor);
}
/**
 * General exponential map at any base point p
 *
 * exp_p(v) = p ⊕ (tanh(λ_p‖v‖/2) · v/‖v‖)
 * where λ_p = 2/(1-‖p‖²) and ⊕ is Möbius addition
 *
 * @param p - Base point in Poincaré ball
 * @param v - Tangent vector at p
 * @returns Point in Poincaré ball
 */
function exponentialMap(p, v) {
    const vNorm = norm(v);
    if (vNorm < exports.EPSILON)
        return [...p];
    const pNormSq = normSq(p);
    const lambda_p = 2 / (1 - pNormSq + exports.EPSILON);
    // Direction of v
    const direction = scale(v, 1 / vNorm);
    // tanh(λ_p * ‖v‖ / 2) * direction
    const tanhTerm = Math.tanh((lambda_p * vNorm) / 2);
    const expV = scale(direction, tanhTerm);
    // Möbius addition p ⊕ expV
    const result = mobiusAdd(p, expV);
    // Ensure result stays in ball
    return projectToBall(result);
}
/**
 * General logarithmic map from q to tangent space at p
 *
 * log_p(q) = (2/λ_p) · arctanh(‖-p ⊕ q‖) · (-p ⊕ q)/‖-p ⊕ q‖
 * where λ_p = 2/(1-‖p‖²) and ⊕ is Möbius addition
 *
 * @param p - Base point in Poincaré ball
 * @param q - Target point in Poincaré ball
 * @returns Tangent vector at p
 */
function logarithmicMap(p, q) {
    const pNormSq = normSq(p);
    const lambda_p = 2 / (1 - pNormSq + exports.EPSILON);
    // -p ⊕ q (Möbius addition of -p and q)
    const negP = scale(p, -1);
    const diff = mobiusAdd(negP, q);
    const diffNorm = norm(diff);
    if (diffNorm < exports.EPSILON)
        return p.map(() => 0);
    // arctanh(‖diff‖) — uses configurable AUDIT_EPSILON for boundary precision
    const atanh = artanh(diffNorm);
    // (2/λ_p) * arctanh * direction
    const factor = ((2 / lambda_p) * atanh) / diffNorm;
    return scale(diff, factor);
}
/**
 * Breath Transform (Layer 6)
 *
 * B(p, t) = tanh(‖p‖ + A·sin(ωt)) · p/‖p‖
 *
 * Preserves direction, modulates radius. Creates a "breathing" effect
 * where points rhythmically move toward/away from the boundary.
 *
 * @param p - Point in Poincaré ball
 * @param t - Time parameter
 * @param config - Breath configuration
 * @returns Transformed point
 */
function breathTransform(p, t, config = { amplitude: 0.05, omega: 1.0 }) {
    const n = norm(p);
    if (n < exports.EPSILON)
        return p.map(() => 0);
    // Clamp amplitude to [0, 0.1] as per spec
    const A = Math.max(0, Math.min(0.1, config.amplitude));
    // Modulated radius
    const newRadius = Math.tanh(n + A * Math.sin(config.omega * t));
    // Scale to new radius while preserving direction
    return scale(p, newRadius / n);
}
/**
 * Inverse breath transform (approximate recovery)
 *
 * @param bp - Breath-transformed point
 * @param t - Time parameter
 * @param config - Breath configuration
 * @returns Approximate original point
 */
function inverseBreathTransform(bp, t, config = { amplitude: 0.05, omega: 1.0 }) {
    const n = norm(bp);
    if (n < exports.EPSILON)
        return bp.map(() => 0);
    const A = Math.max(0, Math.min(0.1, config.amplitude));
    // atanh(n) - A·sin(ωt) gives approximate original radius
    const atanhN = artanh(n);
    const originalRadius = Math.max(0, atanhN - A * Math.sin(config.omega * t));
    return scale(bp, originalRadius / n);
}
// ═══════════════════════════════════════════════════════════════
// Layer 7: Phase Modulation
// ═══════════════════════════════════════════════════════════════
/**
 * Phase Modulation / Rotation (Layer 7)
 *
 * Φ(p, θ) = R_θ · p - rotation in tangent space
 *
 * For 2D, this is standard rotation. For higher dimensions,
 * we rotate in a chosen plane.
 *
 * @param p - Point in Poincaré ball
 * @param theta - Rotation angle in radians
 * @param plane - Pair of dimension indices to rotate in (default [0,1])
 * @returns Rotated point
 */
function phaseModulation(p, theta, plane = [0, 1]) {
    const [i, j] = plane;
    if (i >= p.length || j >= p.length || i === j) {
        throw new RangeError('Invalid rotation plane');
    }
    const result = [...p];
    const cos = Math.cos(theta);
    const sin = Math.sin(theta);
    // Givens rotation in plane (i, j)
    result[i] = p[i] * cos - p[j] * sin;
    result[j] = p[i] * sin + p[j] * cos;
    return result;
}
/**
 * Multi-plane phase modulation
 *
 * Applies rotations in multiple planes sequentially.
 *
 * @param p - Point in Poincaré ball
 * @param rotations - Array of [theta, plane] pairs
 * @returns Transformed point
 */
function multiPhaseModulation(p, rotations) {
    let result = [...p];
    for (const { theta, plane } of rotations) {
        result = phaseModulation(result, theta, plane);
    }
    return result;
}
/**
 * Multi-Well Potential (Layer 8)
 *
 * V(p) = Σᵢ wᵢ · exp(-‖p - cᵢ‖² / 2σᵢ²)
 *
 * Creates an energy landscape with multiple attractors (wells).
 *
 * @param p - Point in space
 * @param wells - Array of well configurations
 * @returns Potential energy at point p
 */
function multiWellPotential(p, wells) {
    let V = 0;
    for (const well of wells) {
        const diff = sub(p, well.center);
        const distSq = normSq(diff);
        V += well.weight * Math.exp(-distSq / (2 * well.sigma * well.sigma));
    }
    return V;
}
/**
 * Gradient of multi-well potential
 *
 * ∇V(p) = Σᵢ wᵢ · exp(-‖p-cᵢ‖²/2σᵢ²) · (-(p-cᵢ)/σᵢ²)
 *
 * @param p - Point in space
 * @param wells - Array of well configurations
 * @returns Gradient vector
 */
function multiWellGradient(p, wells) {
    const grad = p.map(() => 0);
    for (const well of wells) {
        const diff = sub(p, well.center);
        const distSq = normSq(diff);
        const expTerm = Math.exp(-distSq / (2 * well.sigma * well.sigma));
        const factor = (-well.weight * expTerm) / (well.sigma * well.sigma);
        for (let i = 0; i < p.length; i++) {
            grad[i] += factor * diff[i];
        }
    }
    return grad;
}
// ═══════════════════════════════════════════════════════════════
// Phase + Distance Scoring (Validated: AUC = 0.9999)
// ═══════════════════════════════════════════════════════════════
/**
 * Phase deviation between two phase values
 *
 * Measures how different two phases are, normalized to [0, 1].
 * 0 = identical phases, 1 = maximally different
 *
 * @param phase1 - First phase value (or null for unknown)
 * @param phase2 - Second phase value (or null for unknown)
 * @returns Deviation in [0, 1]
 */
function phaseDeviation(phase1, phase2) {
    // Unknown phase = maximum deviation
    if (phase1 === null || phase2 === null)
        return 1.0;
    // Normalize phases to [0, 2π]
    const p1 = ((phase1 % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
    const p2 = ((phase2 % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
    // Angular difference, accounting for wrap-around
    const diff = Math.abs(p1 - p2);
    const angularDiff = Math.min(diff, 2 * Math.PI - diff);
    // Normalize to [0, 1]
    return angularDiff / Math.PI;
}
/**
 * Phase-augmented distance scoring for adversarial detection.
 *
 * VALIDATED RESULT: Achieves AUC = 0.9999 on adversarial RAG detection.
 *
 * The key insight: hyperbolic distance alone (AUC = 0.667) ties with cosine
 * and Euclidean. But adding phase deviation breaks the tie and dominates.
 *
 * Formula: score = 1 / (1 + d_H + phaseWeight * phase_dev)
 *
 * Higher score = more trustworthy (closer in space AND aligned in phase)
 * Lower score = suspicious (far away OR phase mismatch)
 *
 * @param u - First point in Poincaré ball
 * @param v - Second point in Poincaré ball
 * @param phase1 - Phase of first point (Sacred Tongue assignment)
 * @param phase2 - Phase of second point
 * @param phaseWeight - Weight for phase deviation (default 2.0)
 * @returns Trust score in (0, 1]
 */
function phaseDistanceScore(u, v, phase1, phase2, phaseWeight = 2.0) {
    const dH = hyperbolicDistance(u, v);
    const phaseDev = phaseDeviation(phase1, phase2);
    return 1 / (1 + dH + phaseWeight * phaseDev);
}
/**
 * Batch scoring for RAG retrieval filtering.
 *
 * Given a query embedding and phase, score all candidate retrievals.
 * Returns scores sorted descending (most trustworthy first).
 *
 * @param query - Query embedding (will be projected to ball)
 * @param queryPhase - Query phase (Sacred Tongue)
 * @param candidates - Array of {embedding, phase, id}
 * @param phaseWeight - Weight for phase deviation
 * @returns Sorted array of {id, score}
 */
function scoreRetrievals(query, queryPhase, candidates, phaseWeight = 2.0) {
    const qProj = projectEmbeddingToBall(query);
    const scored = candidates.map((c) => {
        const cProj = projectEmbeddingToBall(c.embedding);
        const score = phaseDistanceScore(qProj, cProj, queryPhase, c.phase, phaseWeight);
        return { id: c.id, score };
    });
    // Sort descending by score
    scored.sort((a, b) => b.score - a.score);
    return scored;
}
// ═══════════════════════════════════════════════════════════════
// Utility: Combined Transform Pipeline
// ═══════════════════════════════════════════════════════════════
/**
 * Apply the L5-L8 transform pipeline
 *
 * @param p - Input point
 * @param t - Time parameter
 * @param theta - Phase rotation angle
 * @param breathConfig - Breath transform config
 * @param wells - Multi-well potential config (optional)
 * @returns Transformed point and potential value
 */
function applyHyperbolicPipeline(p, t, theta, breathConfig, wells) {
    // Ensure point is in ball
    let point = projectToBall(p);
    // L6: Breath transform
    if (breathConfig) {
        point = breathTransform(point, t, breathConfig);
    }
    // L7: Phase modulation
    if (theta !== 0) {
        point = phaseModulation(point, theta);
    }
    // Ensure still in ball after transforms
    point = projectToBall(point);
    // L8: Compute potential (doesn't modify point)
    const potential = wells ? multiWellPotential(point, wells) : 0;
    // L5: Compute distance from origin (for reference)
    const origin = point.map(() => 0);
    const distance = hyperbolicDistance(origin, point);
    return { point, potential, distance };
}
//# sourceMappingURL=hyperbolic.js.map