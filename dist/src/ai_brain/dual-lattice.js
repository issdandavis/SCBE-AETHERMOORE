"use strict";
/**
 * @file dual-lattice.ts
 * @module ai_brain/dual-lattice
 * @layer Layer 4, Layer 5, Layer 9, Layer 12
 * @component Dual Lattice Architecture
 * @version 1.0.0
 * @since 2026-02-08
 *
 * Implements the Dual Lattice Architecture for quasicrystal-based AI security.
 *
 * Both projection modes operate simultaneously:
 *
 *   Static Lattice (6D → 3D): Structure Generation
 *     Creates the aperiodic polyhedral mesh
 *     Defines valid Hamiltonian paths
 *     Establishes the topology that adversaries cannot predict
 *
 *   Dynamic Lattice (3D → 6D → 3D): Runtime Transform
 *     Lifts thought vectors through the 6D space
 *     Applies phason shifts for security response
 *     Projects back with transformed aperiodic structure
 *
 * Key insight: Multiples of 2 and 1 → 3 create interference patterns
 * at 3x frequencies — natural for icosahedral/φ-based symmetry.
 *
 * The dual lattice harmonics produce mutual verification:
 * the static topology constrains the dynamic transform, and the
 * dynamic transform validates the static topology.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DualLatticeSystem = exports.DEFAULT_DUAL_LATTICE_CONFIG = void 0;
exports.staticProjection = staticProjection;
exports.generateAperiodicMesh = generateAperiodicMesh;
exports.applyPhasonShift = applyPhasonShift;
exports.dynamicTransform = dynamicTransform;
exports.estimateFractalDimension = estimateFractalDimension;
exports.latticeNorm6D = latticeNorm6D;
exports.latticeDistance3D = latticeDistance3D;
const types_js_1 = require("./types.js");
exports.DEFAULT_DUAL_LATTICE_CONFIG = {
    acceptanceRadius: 1.0 / types_js_1.PHI, // Golden ratio acceptance window
    phasonCoupling: 0.1,
    interferenceThreshold: 0.3,
    maxPhasonAmplitude: 0.5,
    coherenceThreshold: 0.6,
};
// ═══════════════════════════════════════════════════════════════
// Icosahedral Projection Matrices
// ═══════════════════════════════════════════════════════════════
/**
 * Build the 6×3 "physical" projection matrix (E_parallel).
 * Projects from 6D to the 3D physical subspace.
 */
function buildParallelProjection() {
    const c1 = Math.cos(0);
    const s1 = Math.sin(0);
    const c2 = Math.cos((2 * Math.PI) / 5);
    const s2 = Math.sin((2 * Math.PI) / 5);
    const c3 = Math.cos((4 * Math.PI) / 5);
    const s3 = Math.sin((4 * Math.PI) / 5);
    const c4 = Math.cos((6 * Math.PI) / 5);
    const s4 = Math.sin((6 * Math.PI) / 5);
    const c5 = Math.cos((8 * Math.PI) / 5);
    const s5 = Math.sin((8 * Math.PI) / 5);
    // 5-fold symmetric basis with golden ratio elevation
    const norm = Math.sqrt(2.0 / 5);
    return [
        [norm * c1, norm * c2, norm * c3, norm * c4, norm * c5, 0],
        [norm * s1, norm * s2, norm * s3, norm * s4, norm * s5, 0],
        [norm / types_js_1.PHI, norm / types_js_1.PHI, norm / types_js_1.PHI, norm / types_js_1.PHI, norm / types_js_1.PHI, norm * types_js_1.PHI],
    ];
}
/**
 * Build the 6×3 "perpendicular" projection matrix (E_perp).
 * Projects from 6D to the 3D internal (perpendicular) subspace.
 * Points in this subspace determine acceptance in the cut-and-project scheme.
 */
function buildPerpProjection() {
    const c1 = Math.cos(0);
    const s1 = Math.sin(0);
    const c2p = Math.cos((4 * Math.PI) / 5);
    const s2p = Math.sin((4 * Math.PI) / 5);
    const c3p = Math.cos((8 * Math.PI) / 5);
    const s3p = Math.sin((8 * Math.PI) / 5);
    const c4p = Math.cos((12 * Math.PI) / 5);
    const s4p = Math.sin((12 * Math.PI) / 5);
    const c5p = Math.cos((16 * Math.PI) / 5);
    const s5p = Math.sin((16 * Math.PI) / 5);
    // Perpendicular projection uses doubled angles (2k instead of k)
    const norm = Math.sqrt(2.0 / 5);
    return [
        [norm * c1, norm * c2p, norm * c3p, norm * c4p, norm * c5p, 0],
        [norm * s1, norm * s2p, norm * s3p, norm * s4p, norm * s5p, 0],
        [norm * types_js_1.PHI, norm * types_js_1.PHI, norm * types_js_1.PHI, norm * types_js_1.PHI, norm * types_js_1.PHI, -norm / types_js_1.PHI],
    ];
}
const E_PARALLEL = buildParallelProjection();
const E_PERP = buildPerpProjection();
/**
 * Project a 6D vector to 3D using a projection matrix.
 */
function project6Dto3D(vec6, matrix) {
    let x = 0, y = 0, z = 0;
    for (let j = 0; j < 6; j++) {
        x += matrix[0][j] * vec6[j];
        y += matrix[1][j] * vec6[j];
        z += matrix[2][j] * vec6[j];
    }
    return { x, y, z };
}
/**
 * Lift a 3D point back to 6D using pseudoinverse of parallel projection.
 * Uses least-squares fit: x6 = E_par^T (E_par E_par^T)^{-1} x3
 *
 * Since E_par is not square, we use the Moore-Penrose pseudoinverse.
 */
function lift3Dto6D(point) {
    const x3 = [point.x, point.y, point.z];
    // E_par * E_par^T (3×3 matrix)
    const EET = [
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ];
    for (let i = 0; i < 3; i++) {
        for (let j = 0; j < 3; j++) {
            for (let k = 0; k < 6; k++) {
                EET[i][j] += E_PARALLEL[i][k] * E_PARALLEL[j][k];
            }
        }
    }
    // Invert 3×3 matrix
    const inv = invert3x3(EET);
    // E_par^T * inv * x3
    const temp = [0, 0, 0];
    for (let i = 0; i < 3; i++) {
        for (let j = 0; j < 3; j++) {
            temp[i] += inv[i][j] * x3[j];
        }
    }
    const result = [0, 0, 0, 0, 0, 0];
    for (let k = 0; k < 6; k++) {
        for (let i = 0; i < 3; i++) {
            result[k] += E_PARALLEL[i][k] * temp[i];
        }
    }
    return { components: result };
}
/**
 * Invert a 3×3 matrix using Cramer's rule.
 */
function invert3x3(m) {
    const a = m[0][0], b = m[0][1], c = m[0][2];
    const d = m[1][0], e = m[1][1], f = m[1][2];
    const g = m[2][0], h = m[2][1], k = m[2][2];
    const det = a * (e * k - f * h) - b * (d * k - f * g) + c * (d * h - e * g);
    if (Math.abs(det) < types_js_1.BRAIN_EPSILON) {
        // Near-singular: return identity
        return [
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
        ];
    }
    const invDet = 1 / det;
    return [
        [
            (e * k - f * h) * invDet,
            (c * h - b * k) * invDet,
            (b * f - c * e) * invDet,
        ],
        [
            (f * g - d * k) * invDet,
            (a * k - c * g) * invDet,
            (c * d - a * f) * invDet,
        ],
        [
            (d * h - e * g) * invDet,
            (b * g - a * h) * invDet,
            (a * e - b * d) * invDet,
        ],
    ];
}
// ═══════════════════════════════════════════════════════════════
// Static Lattice (6D → 3D): Structure Generation
// ═══════════════════════════════════════════════════════════════
/**
 * Project from 6D to 3D using the cut-and-project method.
 *
 * The "acceptance domain" in perpendicular space determines which
 * 6D lattice points produce valid 3D quasicrystal vertices.
 * Points outside the acceptance domain are rejected.
 */
function staticProjection(point6D, config = exports.DEFAULT_DUAL_LATTICE_CONFIG) {
    const vec = point6D.components;
    // Project to physical (parallel) subspace
    const point3D = project6Dto3D(vec, E_PARALLEL);
    // Project to perpendicular (internal) subspace
    const perp = project6Dto3D(vec, E_PERP);
    const perpComponent = [perp.x, perp.y, perp.z];
    // Check acceptance domain (icosahedral window)
    const perpNorm = Math.sqrt(perp.x * perp.x + perp.y * perp.y + perp.z * perp.z);
    const accepted = perpNorm <= config.acceptanceRadius;
    const boundaryDistance = Math.max(0, config.acceptanceRadius - perpNorm);
    // Tile type classification based on perpendicular distance
    // Thick rhombus: closer to center of acceptance domain
    // Thin rhombus: closer to boundary
    const tileType = perpNorm < config.acceptanceRadius / types_js_1.PHI ? 'thick' : 'thin';
    return {
        point3D,
        perpComponent,
        accepted,
        boundaryDistance,
        tileType,
    };
}
/**
 * Generate an aperiodic mesh of valid Hamiltonian path vertices.
 *
 * Scans integer lattice points in 6D and projects only those
 * within the acceptance domain, creating a quasicrystalline mesh.
 *
 * @param radius - Search radius in 6D (default: 3)
 * @param config - Lattice configuration
 * @returns Array of accepted 3D vertices with metadata
 */
function generateAperiodicMesh(radius = 3, config = exports.DEFAULT_DUAL_LATTICE_CONFIG) {
    const results = [];
    const r = Math.floor(radius);
    // Scan a bounded region of the 6D integer lattice
    // For efficiency, only scan first 3 dimensions (extend later)
    for (let i = -r; i <= r; i++) {
        for (let j = -r; j <= r; j++) {
            for (let k = -r; k <= r; k++) {
                const point6D = {
                    components: [i, j, k, 0, 0, 0],
                };
                const result = staticProjection(point6D, config);
                if (result.accepted) {
                    results.push(result);
                }
            }
        }
    }
    return results;
}
// ═══════════════════════════════════════════════════════════════
// Dynamic Lattice (3D → 6D → 3D): Runtime Transform
// ═══════════════════════════════════════════════════════════════
/**
 * Apply a phason shift to a 6D lattice point.
 *
 * Phasons shift points in perpendicular space, causing some
 * to enter or leave the acceptance domain. This changes the
 * local tiling without affecting statistical properties.
 *
 * Security application: phason shifts can dynamically rearrange
 * the quasicrystal structure in response to threats, making
 * the topology a moving target.
 */
function applyPhasonShift(point6D, phason) {
    const vec = [...point6D.components];
    // The perpendicular projection defines which components to shift.
    // We modify the 6D point so its perpendicular projection shifts
    // by the desired amount.
    //
    // Since E_perp maps 6D → 3D, we need E_perp^T to lift the shift back.
    const shift = phason.perpShift;
    for (let k = 0; k < 6; k++) {
        for (let i = 0; i < 3; i++) {
            vec[k] += E_PERP[i][k] * shift[i] * phason.magnitude;
        }
    }
    return { components: vec };
}
/**
 * Execute the full dynamic lattice transform: 3D → 6D → 3D.
 *
 * 1. Lift the 3D thought vector to 6D using pseudoinverse
 * 2. Apply phason shift in 6D perpendicular space
 * 3. Project back to 3D with the transformed structure
 *
 * The displacement between original and re-projected points
 * is a security metric: large displacement = suspicious behavior.
 */
function dynamicTransform(point3D, phason, config = exports.DEFAULT_DUAL_LATTICE_CONFIG) {
    // Step 1: Lift 3D → 6D
    const lifted6D = lift3Dto6D(point3D);
    // Step 2: Apply phason shift in 6D
    const shifted6D = applyPhasonShift(lifted6D, phason);
    // Step 3: Project back 6D → 3D
    const projected3D = project6Dto3D(shifted6D.components, E_PARALLEL);
    // Compute displacement
    const dx = projected3D.x - point3D.x;
    const dy = projected3D.y - point3D.y;
    const dz = projected3D.z - point3D.z;
    const displacement = Math.sqrt(dx * dx + dy * dy + dz * dz);
    // Compute 3x frequency interference pattern
    // The dual lattice harmonics create interference at triple frequency
    const interferenceValue = computeTripleFrequencyInterference(lifted6D, shifted6D, point3D);
    // Check if aperiodic structure is preserved
    // If phason amplitude exceeds max, structure breaks
    const structurePreserved = phason.magnitude <= config.maxPhasonAmplitude;
    return {
        lifted6D,
        shifted6D,
        projected3D,
        displacement,
        interferenceValue,
        structurePreserved,
    };
}
/**
 * Compute the 3x frequency interference pattern.
 *
 * When both lattice modes are active simultaneously,
 * the harmonics create interference at 3× the fundamental frequency.
 * This is a consequence of icosahedral/φ-based symmetry where
 * multiples of 2 and 1 combine to 3.
 *
 * @returns Interference value in [-1, 1]
 */
function computeTripleFrequencyInterference(original6D, shifted6D, anchor3D) {
    // Dot product of original and shifted in 6D (correlation)
    let dotProd = 0;
    let normA = 0;
    let normB = 0;
    for (let i = 0; i < 6; i++) {
        dotProd += original6D.components[i] * shifted6D.components[i];
        normA += original6D.components[i] * original6D.components[i];
        normB += shifted6D.components[i] * shifted6D.components[i];
    }
    const normProduct = Math.sqrt(normA * normB);
    if (normProduct < types_js_1.BRAIN_EPSILON)
        return 0;
    const correlation = dotProd / normProduct;
    // 3× frequency modulation from anchor point
    const anchorPhase = anchor3D.x * types_js_1.PHI + anchor3D.y * types_js_1.PHI * types_js_1.PHI + anchor3D.z / types_js_1.PHI;
    // The interference pattern at triple frequency
    return correlation * Math.cos(3 * anchorPhase);
}
// ═══════════════════════════════════════════════════════════════
// Dual Lattice System (Both Modes Active)
// ═══════════════════════════════════════════════════════════════
/**
 * Dual Lattice System — both projection modes operating simultaneously.
 *
 * The static lattice provides the structure; the dynamic lattice
 * transforms within that structure. Cross-verification between
 * the two ensures mathematical consistency.
 */
class DualLatticeSystem {
    config;
    staticMesh = null;
    stepCounter = 0;
    constructor(config = {}) {
        this.config = { ...exports.DEFAULT_DUAL_LATTICE_CONFIG, ...config };
    }
    /**
     * Initialize the static mesh (one-time topology generation).
     * Call this once; the mesh defines the Hamiltonian path topology.
     */
    initializeMesh(radius = 3) {
        this.staticMesh = generateAperiodicMesh(radius, this.config);
        return this.staticMesh;
    }
    /**
     * Get the cached static mesh.
     */
    getMesh() {
        return this.staticMesh;
    }
    /**
     * Process a 21D brain state through the dual lattice system.
     *
     * Both lattice modes run simultaneously:
     * 1. Static: Take 6D subspace, project to 3D, check acceptance
     * 2. Dynamic: Take projected 3D, lift → shift → reproject
     * 3. Cross-verify both results for coherence
     *
     * @param state21D - 21D brain state vector
     * @param phason - Phason shift for dynamic response
     * @returns Combined dual lattice result
     */
    process(state21D, phason) {
        this.stepCounter++;
        if (state21D.length < 6) {
            throw new RangeError(`Expected at least 6D state, got ${state21D.length}D`);
        }
        // Extract 6D subspace (navigation dimensions 6-11 from brain state)
        const nav6D = {
            components: [
                state21D.length > 6 ? state21D[6] : state21D[0],
                state21D.length > 7 ? state21D[7] : state21D[1],
                state21D.length > 8 ? state21D[8] : state21D[2],
                state21D.length > 9 ? state21D[9] : state21D[3],
                state21D.length > 10 ? state21D[10] : state21D[4],
                state21D.length > 11 ? state21D[11] : state21D[5],
            ],
        };
        // ═══ Static Lattice (6D → 3D) ═══
        const staticResult = staticProjection(nav6D, this.config);
        // ═══ Dynamic Lattice (3D → 6D → 3D) ═══
        const dynamicResult = dynamicTransform(staticResult.point3D, phason, this.config);
        // ═══ Cross-Verification ═══
        const coherence = this.computeCoherence(staticResult, dynamicResult);
        // 3× frequency interference from both lattices combined
        const tripleFrequencyInterference = dynamicResult.interferenceValue;
        // Validation: both lattices must agree above threshold
        const validated = staticResult.accepted &&
            dynamicResult.structurePreserved &&
            coherence >= this.config.coherenceThreshold;
        return {
            static: staticResult,
            dynamic: dynamicResult,
            coherence,
            tripleFrequencyInterference,
            validated,
        };
    }
    /**
     * Create a security-responsive phason shift based on threat level.
     *
     * Higher threat → larger phason amplitude → more topology rearrangement.
     * This makes the quasicrystal structure a moving target that adapts
     * to the current threat landscape.
     */
    createThreatPhason(threatLevel, anomalyDimensions = []) {
        const clampedThreat = Math.max(0, Math.min(1, threatLevel));
        const magnitude = clampedThreat * this.config.maxPhasonAmplitude * this.config.phasonCoupling;
        // Derive shift direction from anomaly dimensions
        let px = 0, py = 0, pz = 0;
        if (anomalyDimensions.length > 0) {
            for (const dim of anomalyDimensions) {
                const angle = (2 * Math.PI * dim) / 21; // Map dim index to angle
                px += Math.cos(angle);
                py += Math.sin(angle);
                pz += Math.cos(angle * types_js_1.PHI);
            }
            const norm = Math.sqrt(px * px + py * py + pz * pz);
            if (norm > types_js_1.BRAIN_EPSILON) {
                px /= norm;
                py /= norm;
                pz /= norm;
            }
        }
        else {
            // Default shift direction based on golden angle
            const angle = this.stepCounter * 2 * Math.PI / types_js_1.PHI;
            px = Math.cos(angle);
            py = Math.sin(angle);
            pz = Math.cos(angle / types_js_1.PHI);
        }
        return {
            perpShift: [px, py, pz],
            magnitude,
            phase: Math.atan2(py, px),
        };
    }
    /**
     * Compute cross-verification coherence between static and dynamic results.
     *
     * Checks that the dynamic transform preserves the static topology's
     * essential properties (acceptance, tiling, boundary relationships).
     */
    computeCoherence(staticResult, dynamicResult) {
        // Factor 1: Displacement should be small for safe operations
        // Small displacement → high coherence
        const displacementScore = 1 / (1 + dynamicResult.displacement * 5);
        // Factor 2: Structure preservation
        const structureScore = dynamicResult.structurePreserved ? 1.0 : 0.0;
        // Factor 3: Static acceptance (accepted = topology valid)
        const acceptanceScore = staticResult.accepted ? 1.0 : 0.3;
        // Factor 4: Interference pattern should be moderate (not saturated)
        const interferenceScore = 1 - Math.abs(dynamicResult.interferenceValue) * 0.5;
        // Weighted combination
        return (displacementScore * 0.35 +
            structureScore * 0.25 +
            acceptanceScore * 0.25 +
            interferenceScore * 0.15);
    }
    /** Get the current step counter */
    getStep() {
        return this.stepCounter;
    }
    /** Reset the system state (keeps mesh) */
    reset() {
        this.stepCounter = 0;
    }
    /** Full reset including mesh */
    fullReset() {
        this.stepCounter = 0;
        this.staticMesh = null;
    }
}
exports.DualLatticeSystem = DualLatticeSystem;
// ═══════════════════════════════════════════════════════════════
// Utility Functions
// ═══════════════════════════════════════════════════════════════
/**
 * Compute the Hausdorff (fractal) dimension estimate for a set of
 * projected lattice points using box-counting.
 *
 * For a perfect quasicrystal, D ≈ 2 (fills 2D plane).
 * Phason disorder can push D to non-integer values.
 */
function estimateFractalDimension(points, scales = [1.0, 0.5, 0.25, 0.125]) {
    if (points.length < 2)
        return 0;
    const logN = [];
    const logInvEps = [];
    for (const eps of scales) {
        // Count boxes of size eps that contain at least one point
        const boxes = new Set();
        for (const p of points) {
            const bx = Math.floor(p.x / eps);
            const by = Math.floor(p.y / eps);
            const bz = Math.floor(p.z / eps);
            boxes.add(`${bx},${by},${bz}`);
        }
        if (boxes.size > 0) {
            logN.push(Math.log(boxes.size));
            logInvEps.push(Math.log(1 / eps));
        }
    }
    if (logN.length < 2)
        return 0;
    // Linear regression: D = slope of log(N) vs log(1/eps)
    let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
    const n = logN.length;
    for (let i = 0; i < n; i++) {
        sumX += logInvEps[i];
        sumY += logN[i];
        sumXY += logInvEps[i] * logN[i];
        sumX2 += logInvEps[i] * logInvEps[i];
    }
    const denom = n * sumX2 - sumX * sumX;
    if (Math.abs(denom) < types_js_1.BRAIN_EPSILON)
        return 0;
    return (n * sumXY - sumX * sumY) / denom;
}
/**
 * Compute the lattice norm (L2) of a 6D vector.
 */
function latticeNorm6D(point) {
    let sum = 0;
    for (const c of point.components) {
        sum += c * c;
    }
    return Math.sqrt(sum);
}
/**
 * Compute the lattice distance between two 3D points.
 */
function latticeDistance3D(a, b) {
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    const dz = a.z - b.z;
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
}
//# sourceMappingURL=dual-lattice.js.map