"use strict";
/**
 * @file chsfn.ts
 * @module harmonic/chsfn
 * @layer Layer 4, Layer 5, Layer 6, Layer 7, Layer 11, Layer 12
 * @component Cymatic-Hyperbolic Semantic Field Network
 * @version 3.2.4
 *
 * CHSFN — a governed geometric computation substrate where:
 *   - Nodes are cymatic nodal voxels (zero-sets of 6D Chladni field)
 *   - Connectivity is implied by shared zero-sets
 *   - Propagation is geodesic drift in negatively curved space
 *   - Memory lives in anti-nodes (negative space)
 *   - Governance is enforced by hyperbolic distance + harmonic scaling
 *
 * State space: S = H^6 × T^6 × R+
 *   H^6 = hyperbolic position (trust/realm geometry)
 *   T^6 = phase torus (one phase per tongue)
 *   R+  = latent mass / entropy budget
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_IMPEDANCE = exports.DEFAULT_MODES = void 0;
exports.cymaticField = cymaticField;
exports.cymaticGradient = cymaticGradient;
exports.isNearZeroSet = isNearZeroSet;
exports.antiNodeStrength = antiNodeStrength;
exports.poincareNorm = poincareNorm;
exports.projectIntoBall = projectIntoBall;
exports.hyperbolicDistance6D = hyperbolicDistance6D;
exports.tongueImpedanceAt = tongueImpedanceAt;
exports.isAccessible = isAccessible;
exports.energyFunctional = energyFunctional;
exports.energyGradient = energyGradient;
exports.driftStep = driftStep;
exports.triadicTemporalDistance = triadicTemporalDistance;
exports.quasiSphereVolume = quasiSphereVolume;
exports.effectiveCapacity = effectiveCapacity;
exports.accessCost = accessCost;
// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
/** Golden ratio */
const PHI = (1 + Math.sqrt(5)) / 2;
/** Small epsilon for numerical stability */
const EPSILON = 1e-10;
/**
 * Default modes — chosen so zero-sets are well-distributed.
 * Higher n/m = finer nodal structure = more addressable loci.
 */
exports.DEFAULT_MODES = {
    n: [3, 5, 7, 4, 6, 2],
    m: [2, 4, 3, 5, 1, 6],
};
/**
 * Compute 6D Chladni-style cymatic field value.
 *
 * Φ(x) = Σ_{i=1}^{6} cos(π·n_i·x_i) · Π_{j≠i} sin(π·m_j·x_j)
 *
 * Properties:
 * - Zero-sets (Φ = 0) are deterministic, reproducible access points
 * - Anti-nodes (|∇Φ| >> 0) are high-energy latent storage basins
 * - Small perturbations destroy access → natural tamper resistance
 * - Orthogonality is preserved across dimensions
 *
 * @param x - 6D position vector (each component in [0, 1])
 * @param modes - Modal indices (default: DEFAULT_MODES)
 * @returns Cymatic field value Φ(x)
 */
function cymaticField(x, modes = exports.DEFAULT_MODES) {
    let sum = 0;
    for (let i = 0; i < 6; i++) {
        const cosVal = Math.cos(Math.PI * modes.n[i] * x[i]);
        let sinProduct = 1;
        for (let j = 0; j < 6; j++) {
            if (j !== i) {
                sinProduct *= Math.sin(Math.PI * modes.m[j] * x[j]);
            }
        }
        sum += cosVal * sinProduct;
    }
    return sum;
}
/**
 * Compute the gradient ∇Φ of the cymatic field at position x.
 *
 * Used for:
 * - Detecting anti-nodes (|∇Φ| >> 0)
 * - Computing drift direction
 * - Phase sensitivity analysis
 *
 * @param x - 6D position vector
 * @param modes - Modal indices
 * @returns Gradient vector [∂Φ/∂x_0, ..., ∂Φ/∂x_5]
 */
function cymaticGradient(x, modes = exports.DEFAULT_MODES) {
    const grad = [0, 0, 0, 0, 0, 0];
    for (let k = 0; k < 6; k++) {
        let partialK = 0;
        for (let i = 0; i < 6; i++) {
            if (i === k) {
                // Derivative of cos(π·n_i·x_i) term: -π·n_i·sin(π·n_i·x_i) · Π_{j≠i} sin(...)
                const dCos = -Math.PI * modes.n[i] * Math.sin(Math.PI * modes.n[i] * x[i]);
                let sinProduct = 1;
                for (let j = 0; j < 6; j++) {
                    if (j !== i) {
                        sinProduct *= Math.sin(Math.PI * modes.m[j] * x[j]);
                    }
                }
                partialK += dCos * sinProduct;
            }
            else {
                // Derivative of sin(π·m_k·x_k) in the product for term i
                const cosVal = Math.cos(Math.PI * modes.n[i] * x[i]);
                const dSin = Math.PI * modes.m[k] * Math.cos(Math.PI * modes.m[k] * x[k]);
                let sinProduct = 1;
                for (let j = 0; j < 6; j++) {
                    if (j !== i && j !== k) {
                        sinProduct *= Math.sin(Math.PI * modes.m[j] * x[j]);
                    }
                }
                partialK += cosVal * dSin * sinProduct;
            }
        }
        grad[k] = partialK;
    }
    return grad;
}
/**
 * Check if a position is near a cymatic zero-set (nodal surface).
 *
 * @param x - 6D position
 * @param tolerance - Threshold for |Φ(x)| ≈ 0 (default 0.01)
 * @param modes - Modal indices
 * @returns true if position is on or near a nodal surface
 */
function isNearZeroSet(x, tolerance = 0.01, modes = exports.DEFAULT_MODES) {
    return Math.abs(cymaticField(x, modes)) < tolerance;
}
/**
 * Compute anti-node strength (gradient magnitude).
 *
 * High values → latent mass basins suitable for concealed storage.
 * Low values → near nodal surfaces (addressable access points).
 *
 * @param x - 6D position
 * @param modes - Modal indices
 * @returns |∇Φ(x)|
 */
function antiNodeStrength(x, modes = exports.DEFAULT_MODES) {
    const grad = cymaticGradient(x, modes);
    let sum = 0;
    for (let i = 0; i < 6; i++)
        sum += grad[i] * grad[i];
    return Math.sqrt(sum);
}
/** Default impedance — neutral (unity weights) */
exports.DEFAULT_IMPEDANCE = {
    KO: 1.0,
    AV: 1.0,
    RU: 1.0,
    CA: 1.0,
    DR: 1.0,
    UM: 1.0,
};
/**
 * Compute the norm of a position within the Poincaré ball.
 *
 * @param p - 6D position
 * @returns ‖p‖ (Euclidean norm, always < 1 in valid state)
 */
function poincareNorm(p) {
    let sum = 0;
    for (let i = 0; i < 6; i++)
        sum += p[i] * p[i];
    return Math.sqrt(sum);
}
/**
 * Project a point into the Poincaré ball (clamp ‖p‖ < 1 - ε).
 *
 * @param p - 6D position (may be outside ball)
 * @param maxNorm - Maximum allowed norm (default 0.999)
 * @returns Projected position inside the ball
 */
function projectIntoBall(p, maxNorm = 0.999) {
    const n = poincareNorm(p);
    if (n < maxNorm)
        return [...p];
    const scale = maxNorm / (n + EPSILON);
    return p.map((x) => x * scale);
}
/**
 * Hyperbolic distance in the 6D Poincaré ball.
 *
 * d_H(u, v) = arcosh(1 + 2‖u-v‖² / ((1-‖u‖²)(1-‖v‖²)))
 *
 * @param u - First point (‖u‖ < 1)
 * @param v - Second point (‖v‖ < 1)
 * @returns Hyperbolic distance d_H
 */
function hyperbolicDistance6D(u, v) {
    let diffSq = 0;
    let uSq = 0;
    let vSq = 0;
    for (let i = 0; i < 6; i++) {
        const d = u[i] - v[i];
        diffSq += d * d;
        uSq += u[i] * u[i];
        vSq += v[i] * v[i];
    }
    const denom = (1 - uSq) * (1 - vSq);
    if (denom <= 0)
        return Infinity;
    const arg = 1 + (2 * diffSq) / Math.max(denom, EPSILON);
    return Math.acosh(Math.max(arg, 1));
}
/**
 * Compute tongue impedance at a position.
 *
 * impedance_tongue(θ, p) = |θ_tongue - expected_phase(p)| / π
 *
 * Returns a value in [0, 1]. Below threshold ε → node is decodable.
 * Above ε → node is semantically inaccessible.
 *
 * @param state - CHSFN state
 * @param tongueIndex - Which tongue (0=KO, 1=AV, 2=RU, 3=CA, 4=DR, 5=UM)
 * @param impedance - Tongue impedance weights
 * @returns Impedance in [0, 1]
 */
function tongueImpedanceAt(state, tongueIndex, impedance = exports.DEFAULT_IMPEDANCE) {
    const tongues = ['KO', 'AV', 'RU', 'CA', 'DR', 'UM'];
    const weight = impedance[tongues[tongueIndex]];
    // Expected phase: golden-ratio spacing
    const expectedPhase = (2 * Math.PI * tongueIndex) / 6;
    const phaseDiff = Math.abs(state.phase[tongueIndex] - expectedPhase);
    const normalizedDiff = (phaseDiff % (2 * Math.PI)) / Math.PI;
    return Math.min(normalizedDiff * weight, 1.0);
}
/**
 * Check if a node is semantically accessible (decodable).
 *
 * A node is accessible only when:
 * 1. The correct tongue is applied (impedance < threshold)
 * 2. Hyperbolic distance from origin is below threshold
 * 3. Cymatic phase is coherent (field value near zero-set)
 *
 * @param state - Current CHSFN state
 * @param tongueIndex - Tongue to apply
 * @param maxImpedance - Max allowed impedance (default 0.3)
 * @param maxDistance - Max hyperbolic distance from origin (default 3.0)
 * @param cymaticTolerance - Tolerance for zero-set check (default 0.1)
 * @param modes - Cymatic modes
 * @returns true if node is accessible
 */
function isAccessible(state, tongueIndex, maxImpedance = 0.3, maxDistance = 3.0, cymaticTolerance = 0.1, modes = exports.DEFAULT_MODES) {
    const origin = [0, 0, 0, 0, 0, 0];
    const dist = hyperbolicDistance6D(state.position, origin);
    if (dist > maxDistance)
        return false;
    const imp = tongueImpedanceAt(state, tongueIndex);
    if (imp > maxImpedance)
        return false;
    return isNearZeroSet(state.position, cymaticTolerance, modes);
}
// ═══════════════════════════════════════════════════════════════
// Adiabatic Drift (State Evolution)
// ═══════════════════════════════════════════════════════════════
/**
 * Energy functional E(p, θ, μ) for drift computation.
 *
 * Combines:
 * - Hyperbolic distance from origin (trust cost)
 * - Phase misalignment (tongue impedance)
 * - Cymatic field intensity (nodal accessibility)
 * - Latent mass contribution
 *
 * @param state - Current CHSFN state
 * @param impedance - Tongue weights
 * @param modes - Cymatic modes
 * @returns Energy value E
 */
function energyFunctional(state, impedance = exports.DEFAULT_IMPEDANCE, modes = exports.DEFAULT_MODES) {
    const origin = [0, 0, 0, 0, 0, 0];
    const dist = hyperbolicDistance6D(state.position, origin);
    // Phase misalignment energy
    let phaseCost = 0;
    for (let i = 0; i < 6; i++) {
        phaseCost += tongueImpedanceAt(state, i, impedance);
    }
    phaseCost /= 6;
    // Cymatic field intensity
    const fieldValue = cymaticField(state.position, modes);
    // Latent mass drag
    const massCost = 1.0 / (1.0 + state.mass);
    return dist + phaseCost + Math.abs(fieldValue) * 0.5 + massCost;
}
/**
 * Compute energy gradient ∇_H E for adiabatic drift.
 *
 * dp/dτ = -∇_H E(p, θ, μ)
 *
 * This is not signal passing — it is geodesic drift.
 * States evolve by flowing down the energy landscape.
 *
 * @param state - Current CHSFN state
 * @param impedance - Tongue weights
 * @param modes - Cymatic modes
 * @returns Gradient of E with respect to position
 */
function energyGradient(state, impedance = exports.DEFAULT_IMPEDANCE, modes = exports.DEFAULT_MODES) {
    const h = 1e-5;
    const grad = [0, 0, 0, 0, 0, 0];
    const e0 = energyFunctional(state, impedance, modes);
    for (let i = 0; i < 6; i++) {
        const shifted = {
            ...state,
            position: [...state.position],
        };
        shifted.position[i] += h;
        shifted.position = projectIntoBall(shifted.position);
        const e1 = energyFunctional(shifted, impedance, modes);
        grad[i] = (e1 - e0) / h;
    }
    return grad;
}
/**
 * Perform one step of adiabatic drift.
 *
 * dp/dτ = -∇_H E(p, θ, μ)
 *
 * The state drifts toward lower energy (safer, more coherent regions).
 * Drift intersecting cymatic zero-sets reveals stored semantics.
 *
 * @param state - Current state
 * @param stepSize - Integration step size (default 0.01)
 * @param impedance - Tongue weights
 * @param modes - Cymatic modes
 * @returns New state after one drift step
 */
function driftStep(state, stepSize = 0.01, impedance = exports.DEFAULT_IMPEDANCE, modes = exports.DEFAULT_MODES) {
    const grad = energyGradient(state, impedance, modes);
    const newPos = [0, 0, 0, 0, 0, 0];
    for (let i = 0; i < 6; i++) {
        newPos[i] = state.position[i] - stepSize * grad[i];
    }
    // Mass decays slightly per step (entropy)
    const newMass = state.mass * (1 - stepSize * 0.01);
    return {
        position: projectIntoBall(newPos),
        phase: [...state.phase],
        mass: Math.max(newMass, EPSILON),
    };
}
// ═══════════════════════════════════════════════════════════════
// Triadic Temporal Aggregation (Layer 11)
// ═══════════════════════════════════════════════════════════════
/**
 * Compute triadic temporal distance.
 *
 * d_tri(t) = (λ₁·d₁^φ + λ₂·d₂^φ + λ₃·d_G^φ)^(1/φ)
 *
 * Three independent distances (past, present, governance) are
 * aggregated with golden-ratio exponents. This ensures:
 * - No linear temporal collapse
 * - Governance time is irreducible
 * - Temporal attacks explode geometrically
 *
 * @param d1 - Past distance
 * @param d2 - Present distance
 * @param dG - Governance distance
 * @param lambda1 - Weight for past (default 0.3)
 * @param lambda2 - Weight for present (default 0.5)
 * @param lambda3 - Weight for governance (default 0.2)
 * @returns Aggregated triadic distance
 */
function triadicTemporalDistance(d1, d2, dG, lambda1 = 0.3, lambda2 = 0.5, lambda3 = 0.2) {
    const sum = lambda1 * Math.pow(Math.max(d1, EPSILON), PHI) +
        lambda2 * Math.pow(Math.max(d2, EPSILON), PHI) +
        lambda3 * Math.pow(Math.max(dG, EPSILON), PHI);
    return Math.pow(sum, 1 / PHI);
}
// ═══════════════════════════════════════════════════════════════
// Quasi-Sphere Volume & Capacity
// ═══════════════════════════════════════════════════════════════
/**
 * Hyperbolic volume growth in 6D: V(r) ~ e^{5r}
 *
 * @param radius - Hyperbolic radius
 * @returns Approximate volume proportional to e^{5r}
 */
function quasiSphereVolume(radius) {
    return Math.exp(5 * radius);
}
/**
 * Effective storage capacity of the quasi-sphere.
 *
 * C ~ e^{5r} × tongueEntropy × temporalLayers
 *
 * Negative space doubles effective capacity because anti-nodes
 * encode latent superpositions, and dormant voxels cost nothing.
 *
 * @param radius - Hyperbolic radius
 * @param tongueEntropy - Entropy per tongue (default 8 bits)
 * @param temporalLayers - Number of temporal layers (default 3)
 * @returns Effective capacity (arbitrary units)
 */
function effectiveCapacity(radius, tongueEntropy = 8, temporalLayers = 3) {
    return quasiSphereVolume(radius) * tongueEntropy * temporalLayers * 2; // ×2 for negative space
}
/**
 * Access cost at a given hyperbolic distance.
 *
 * H(d*, R) = R · π^(φ·d*)
 *
 * This is the Layer-12 event horizon. Unauthorized semantic access
 * requires global phase coherence across tongues and traversal of
 * exponentially expensive hyperbolic distances.
 *
 * @param dStar - Hyperbolic realm distance
 * @param R - Base cost ratio (default 1.5)
 * @returns Access cost
 */
function accessCost(dStar, R = 1.5) {
    return R * Math.pow(Math.PI, PHI * dStar);
}
//# sourceMappingURL=chsfn.js.map