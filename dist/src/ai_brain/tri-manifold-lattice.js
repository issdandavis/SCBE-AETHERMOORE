"use strict";
/**
 * @file tri-manifold-lattice.ts
 * @module ai_brain/tri-manifold-lattice
 * @layer Layer 5, Layer 11, Layer 12, Layer 14
 * @component Tri-Manifold Lattice — Temporal Harmonic Governance
 * @version 1.0.0
 * @since 2026-02-10
 *
 * Constructs a lattice over THREE temporal manifolds (immediate, memory,
 * governance), each sampling hyperbolic distance in the Poincaré ball at
 * different timescales. The triadic distance combines them via weighted
 * Euclidean norm, and the Harmonic Scaling Law H(d, R) = R^(d²) applies
 * super-exponential cost amplification across dimensions.
 *
 * Architecture:
 *
 *   Manifold 1 (Immediate):  Window W₁ — short-term drift detection
 *   Manifold 2 (Memory):     Window W₂ — medium-term pattern memory
 *   Manifold 3 (Governance): Window W_G — long-term policy enforcement
 *
 *   Triadic Distance:
 *     d_tri(t) = √(λ₁·d₁² + λ₂·d₂² + λ₃·d_G²)
 *     where λᵢ ≥ 0 and Σλᵢ = 1
 *
 *   Harmonic Scaling (super-exponential):
 *     H(d, R) = R^(d²)
 *     For R = 1.5 (perfect fifth):
 *       d=1: 1.5,  d=2: 5.06,  d=3: 38.44,  d=4: 656.84,  d=6: 2,184,164
 *
 *   Lattice Node: a point in the tri-manifold with:
 *     - 21D Poincaré embedding
 *     - Three temporal distance averages
 *     - Triadic distance (combined scalar)
 *     - Harmonic-scaled governance cost
 *
 * Properties:
 *   - d_tri is a weighted Euclidean norm: non-negative, positive-definite
 *   - d_tri = 0 ⟺ d₁ = d₂ = d_G = 0 (all windows report zero drift)
 *   - ∂d_tri/∂dᵢ = λᵢ·dᵢ / d_tri ≥ 0 (monotonic in each component)
 *   - H(d, R) × H(d, 1/R) = 1 (duality / phase cancellation)
 *   - H is super-exponential: grows faster than any single exponential
 *
 * Integration:
 *   - Uses hyperbolicDistanceSafe() from unified-state.ts
 *   - Uses safePoincareEmbed() for 21D → B²¹ embedding
 *   - Feeds into Hamiltonian Braid for governance decisions
 *   - Audio axis (L14) coherence modulates governance window
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.TriManifoldLattice = exports.TemporalWindow = exports.MAX_LATTICE_DEPTH = exports.DEFAULT_TRIADIC_WEIGHTS = exports.DEFAULT_WINDOW_SIZES = exports.HARMONIC_R = void 0;
exports.harmonicScale = harmonicScale;
exports.harmonicScaleInverse = harmonicScaleInverse;
exports.harmonicScaleTable = harmonicScaleTable;
exports.triadicDistance = triadicDistance;
exports.triadicPartial = triadicPartial;
const types_js_1 = require("./types.js");
const unified_state_js_1 = require("./unified-state.js");
// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
/** Default harmonic ratio: perfect fifth (3:2) from Pythagorean tuning */
exports.HARMONIC_R = 1.5;
/** Default temporal window sizes (in ticks/samples) */
exports.DEFAULT_WINDOW_SIZES = {
    immediate: 5, // W₁: last 5 samples — fast reaction
    memory: 25, // W₂: last 25 samples — pattern memory
    governance: 100, // W_G: last 100 samples — policy enforcement
};
/** Default triadic weights (λ₁, λ₂, λ₃), sum to 1 */
exports.DEFAULT_TRIADIC_WEIGHTS = {
    immediate: 0.5, // λ₁: fast signals weighted highest
    memory: 0.3, // λ₂: medium-term patterns
    governance: 0.2, // λ₃: slow governance drift
};
/** Maximum lattice depth before pruning old nodes */
exports.MAX_LATTICE_DEPTH = 1000;
// ═══════════════════════════════════════════════════════════════
// Harmonic Scaling Law
// ═══════════════════════════════════════════════════════════════
/**
 * Harmonic Scaling: H(d, R) = R^(d²)
 *
 * Super-exponential amplification where each dimension multiplies
 * complexity via pairwise interactions (d² exponent).
 *
 * Physical roots: helioseismology (solar oscillations scale as l²),
 * cymatics (Chladni plate modes scale as (m+2n)²).
 *
 * @param d - Number of dimensions (typically 1-6)
 * @param R - Harmonic ratio (default: 1.5, the perfect fifth)
 * @returns R^(d²) — the amplification factor
 */
function harmonicScale(d, R = exports.HARMONIC_R) {
    if (d < 0)
        return 1; // No negative dimensions
    if (R <= 0)
        return 0; // Degenerate ratio
    return Math.pow(R, d * d);
}
/**
 * Inverse harmonic scaling for flux management / phase cancellation.
 * H(d, 1/R) = (1/R)^(d²)
 *
 * Property: harmonicScale(d, R) * harmonicScaleInverse(d, R) = 1
 */
function harmonicScaleInverse(d, R = exports.HARMONIC_R) {
    if (d < 0 || R <= 0)
        return 1;
    return Math.pow(1 / R, d * d);
}
/**
 * Harmonic scaling table for dimensions 1..maxD.
 * Useful for precomputation and visualization.
 */
function harmonicScaleTable(maxD, R = exports.HARMONIC_R) {
    const table = [];
    for (let d = 1; d <= maxD; d++) {
        const s = harmonicScale(d, R);
        table.push({ d, scale: s, logScale: Math.log(s) });
    }
    return table;
}
// ═══════════════════════════════════════════════════════════════
// Triadic Distance
// ═══════════════════════════════════════════════════════════════
/**
 * Triadic temporal distance: weighted Euclidean norm of 3 manifold distances.
 *
 * d_tri = √(λ₁·d₁² + λ₂·d₂² + λ₃·d_G²)
 *
 * Properties:
 *   - Non-negative (sum of squares under sqrt)
 *   - Positive-definite: d_tri = 0 ⟺ all dᵢ = 0
 *   - Monotonic in each component: ∂d_tri/∂dᵢ ≥ 0
 *
 * @param d1 - Immediate manifold distance
 * @param d2 - Memory manifold distance
 * @param dG - Governance manifold distance
 * @param weights - Triadic weights (must sum to 1)
 */
function triadicDistance(d1, d2, dG, weights = exports.DEFAULT_TRIADIC_WEIGHTS) {
    const sumSq = weights.immediate * d1 * d1 +
        weights.memory * d2 * d2 +
        weights.governance * dG * dG;
    return Math.sqrt(Math.max(0, sumSq));
}
/**
 * Partial derivative of triadic distance w.r.t. component i.
 * ∂d_tri/∂dᵢ = λᵢ·dᵢ / d_tri
 */
function triadicPartial(dI, lambdaI, dTri) {
    if (dTri < types_js_1.BRAIN_EPSILON)
        return 0;
    return (lambdaI * dI) / dTri;
}
// ═══════════════════════════════════════════════════════════════
// Temporal Window (Sliding Average)
// ═══════════════════════════════════════════════════════════════
/**
 * Sliding window for temporal manifold distance averaging.
 *
 * Maintains a fixed-size circular buffer of hyperbolic distances
 * and provides the windowed average d_k(t) = (1/W_k) Σ d_H(u(s), ℓ)
 */
class TemporalWindow {
    size;
    buffer;
    head = 0;
    count = 0;
    sum = 0;
    constructor(size) {
        this.size = size;
        if (size < 1)
            throw new Error('Window size must be >= 1');
        this.buffer = new Array(size).fill(0);
    }
    /** Push a new distance sample into the window. */
    push(distance) {
        if (this.count >= this.size) {
            // Remove oldest value
            this.sum -= this.buffer[this.head];
        }
        this.buffer[this.head] = distance;
        this.sum += distance;
        this.head = (this.head + 1) % this.size;
        if (this.count < this.size)
            this.count++;
    }
    /** Windowed average distance. */
    average() {
        if (this.count === 0)
            return 0;
        return this.sum / this.count;
    }
    /** Current sample count (may be < size during warmup). */
    filled() {
        return this.count;
    }
    /** Whether the window is fully warmed up. */
    isWarmedUp() {
        return this.count >= this.size;
    }
    /** Most recent distance sample. */
    latest() {
        if (this.count === 0)
            return 0;
        const idx = (this.head - 1 + this.size) % this.size;
        return this.buffer[idx];
    }
    /** Variance of distances in the window. */
    variance() {
        if (this.count < 2)
            return 0;
        const avg = this.average();
        let sumSq = 0;
        for (let i = 0; i < this.count; i++) {
            const diff = this.buffer[i] - avg;
            sumSq += diff * diff;
        }
        return sumSq / (this.count - 1);
    }
    /** Reset window to empty state. */
    reset() {
        this.buffer.fill(0);
        this.head = 0;
        this.count = 0;
        this.sum = 0;
    }
}
exports.TemporalWindow = TemporalWindow;
// ═══════════════════════════════════════════════════════════════
// Tri-Manifold Lattice
// ═══════════════════════════════════════════════════════════════
/**
 * Tri-Manifold Lattice: three temporal manifolds over the Poincaré ball.
 *
 * Each manifold samples hyperbolic distance at a different timescale,
 * then the triadic distance combines them into a single governance metric.
 * The harmonic scaling law amplifies this across dimensional space.
 *
 * Usage:
 *   const lattice = new TriManifoldLattice();
 *   const node = lattice.ingest(stateVector);
 *   console.log(node.triadicDistance);  // Combined temporal distance
 *   console.log(node.harmonicCost);     // Super-exponential governance cost
 */
class TriManifoldLattice {
    // Three temporal manifold windows
    immediateWindow;
    memoryWindow;
    governanceWindow;
    // Configuration
    weights;
    harmonicR;
    harmonicDimensions;
    referencePoint;
    // Lattice state
    nodes = [];
    tick = 0;
    constructor(config) {
        const ws = config?.windowSizes ?? {};
        this.immediateWindow = new TemporalWindow(ws.immediate ?? exports.DEFAULT_WINDOW_SIZES.immediate);
        this.memoryWindow = new TemporalWindow(ws.memory ?? exports.DEFAULT_WINDOW_SIZES.memory);
        this.governanceWindow = new TemporalWindow(ws.governance ?? exports.DEFAULT_WINDOW_SIZES.governance);
        // Merge weights, normalize to sum=1
        const rawW = {
            immediate: config?.weights?.immediate ?? exports.DEFAULT_TRIADIC_WEIGHTS.immediate,
            memory: config?.weights?.memory ?? exports.DEFAULT_TRIADIC_WEIGHTS.memory,
            governance: config?.weights?.governance ?? exports.DEFAULT_TRIADIC_WEIGHTS.governance,
        };
        const wSum = rawW.immediate + rawW.memory + rawW.governance;
        this.weights = {
            immediate: rawW.immediate / wSum,
            memory: rawW.memory / wSum,
            governance: rawW.governance / wSum,
        };
        this.harmonicR = config?.harmonicR ?? exports.HARMONIC_R;
        this.harmonicDimensions = config?.harmonicDimensions ?? 6; // 6 tongues
        this.referencePoint = config?.referencePoint ?? new Array(types_js_1.BRAIN_DIMENSIONS).fill(0);
    }
    /**
     * Ingest a new 21D state vector into the lattice.
     *
     * 1. Embeds into Poincaré ball
     * 2. Computes hyperbolic distance from reference
     * 3. Pushes to all three temporal windows
     * 4. Computes triadic distance and harmonic cost
     *
     * @param rawState - 21D state vector (pre-Poincaré)
     * @returns The new lattice node with all computed metrics
     */
    ingest(rawState) {
        this.tick++;
        // Embed into Poincaré ball
        const embedded = (0, unified_state_js_1.safePoincareEmbed)(rawState);
        const refEmbedded = (0, unified_state_js_1.safePoincareEmbed)(this.referencePoint);
        const embeddedNorm = (0, unified_state_js_1.vectorNorm)(embedded);
        // Hyperbolic distance from reference point
        const hDist = (0, unified_state_js_1.hyperbolicDistanceSafe)(embedded, refEmbedded);
        // Push to all three temporal windows
        this.immediateWindow.push(hDist);
        this.memoryWindow.push(hDist);
        this.governanceWindow.push(hDist);
        // Windowed averages
        const d1 = this.immediateWindow.average();
        const d2 = this.memoryWindow.average();
        const dG = this.governanceWindow.average();
        // Triadic distance
        const dTri = triadicDistance(d1, d2, dG, this.weights);
        // Harmonic scaling: apply super-exponential cost
        // Scale triadic distance by H(dim, R) where dim = harmonicDimensions
        const hScale = harmonicScale(this.harmonicDimensions, this.harmonicR);
        const harmonicCost = dTri * hScale;
        const node = {
            tick: this.tick,
            rawState: [...rawState],
            embedded,
            hyperbolicDist: hDist,
            manifoldDistances: {
                immediate: d1,
                memory: d2,
                governance: dG,
            },
            triadicDistance: dTri,
            harmonicCost,
            embeddedNorm,
            timestamp: Date.now(),
        };
        // Store node (with depth pruning)
        this.nodes.push(node);
        if (this.nodes.length > exports.MAX_LATTICE_DEPTH) {
            this.nodes = this.nodes.slice(-exports.MAX_LATTICE_DEPTH);
        }
        return node;
    }
    /**
     * Compute drift velocity: rate of change of triadic distance.
     * Uses finite difference of last two nodes.
     */
    driftVelocity() {
        if (this.nodes.length < 2)
            return 0;
        const curr = this.nodes[this.nodes.length - 1];
        const prev = this.nodes[this.nodes.length - 2];
        return curr.triadicDistance - prev.triadicDistance;
    }
    /**
     * Compute drift acceleration (second derivative).
     * Positive = drift is accelerating (concerning).
     */
    driftAcceleration() {
        if (this.nodes.length < 3)
            return 0;
        const n = this.nodes.length;
        const d2 = this.nodes[n - 1].triadicDistance;
        const d1 = this.nodes[n - 2].triadicDistance;
        const d0 = this.nodes[n - 3].triadicDistance;
        return (d2 - 2 * d1 + d0); // discrete second derivative
    }
    /** Get the current triadic distance (0 if no samples). */
    currentTriadicDistance() {
        if (this.nodes.length === 0)
            return 0;
        return this.nodes[this.nodes.length - 1].triadicDistance;
    }
    /** Get the current harmonic cost (0 if no samples). */
    currentHarmonicCost() {
        if (this.nodes.length === 0)
            return 0;
        return this.nodes[this.nodes.length - 1].harmonicCost;
    }
    /** Get the last N lattice nodes. */
    recentNodes(n) {
        return this.nodes.slice(-n);
    }
    /** Current lattice snapshot. */
    snapshot() {
        const latest = this.nodes[this.nodes.length - 1];
        return {
            tick: this.tick,
            triadicDistance: latest?.triadicDistance ?? 0,
            harmonicCost: latest?.harmonicCost ?? 0,
            manifoldDistances: latest?.manifoldDistances ?? { immediate: 0, memory: 0, governance: 0 },
            weights: { ...this.weights },
            nodeCount: this.nodes.length,
            driftVelocity: this.driftVelocity(),
        };
    }
    /**
     * Check if lattice is in "resonance" — all three manifolds agree.
     *
     * When immediate, memory, and governance distances are similar,
     * the system is in a stable temporal resonance (good or bad).
     * Divergence between manifolds indicates temporal drift.
     *
     * @returns Resonance coefficient in [0, 1] where 1 = perfect agreement
     */
    temporalResonance() {
        if (this.nodes.length === 0)
            return 1; // No data = trivially resonant
        const latest = this.nodes[this.nodes.length - 1];
        const { immediate: d1, memory: d2, governance: dG } = latest.manifoldDistances;
        const avg = (d1 + d2 + dG) / 3;
        if (avg < types_js_1.BRAIN_EPSILON)
            return 1; // All near zero = perfect resonance
        const variance = ((d1 - avg) ** 2 + (d2 - avg) ** 2 + (dG - avg) ** 2) / 3;
        // Map variance to [0, 1] resonance. Variance 0 → resonance 1.
        return 1 / (1 + variance / (avg * avg));
    }
    /**
     * Detect temporal anomaly: immediate window diverges from governance.
     *
     * If d₁ >> d_G, something just changed that hasn't been seen before.
     * If d_G >> d₁, a past pattern is repeating that's currently quiet.
     *
     * @returns Anomaly score in [0, ∞). Values > 2 are significant.
     */
    temporalAnomaly() {
        if (this.nodes.length === 0)
            return 0;
        const latest = this.nodes[this.nodes.length - 1];
        const { immediate: d1, governance: dG } = latest.manifoldDistances;
        const denom = Math.max(dG, types_js_1.BRAIN_EPSILON);
        return Math.abs(d1 - dG) / denom;
    }
    /**
     * Compute the harmonic scaling table for visualization.
     * Returns H(d, R) for d = 1..maxD.
     */
    harmonicTable(maxD = 6) {
        return harmonicScaleTable(maxD, this.harmonicR);
    }
    /**
     * Check the harmonic duality property:
     * H(d, R) * H(d, 1/R) should equal 1 for all d.
     */
    verifyDuality(d) {
        const fwd = harmonicScale(d, this.harmonicR);
        const inv = harmonicScaleInverse(d, this.harmonicR);
        return { forward: fwd, inverse: inv, product: fwd * inv };
    }
    /** Total ticks ingested. */
    getTick() {
        return this.tick;
    }
    /** Current weights (normalized). */
    getWeights() {
        return { ...this.weights };
    }
    /** Reset all windows and lattice state. */
    reset() {
        this.immediateWindow.reset();
        this.memoryWindow.reset();
        this.governanceWindow.reset();
        this.nodes = [];
        this.tick = 0;
    }
}
exports.TriManifoldLattice = TriManifoldLattice;
//# sourceMappingURL=tri-manifold-lattice.js.map