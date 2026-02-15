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
/** Default harmonic ratio: perfect fifth (3:2) from Pythagorean tuning */
export declare const HARMONIC_R = 1.5;
/** Default temporal window sizes (in ticks/samples) */
export declare const DEFAULT_WINDOW_SIZES: {
    readonly immediate: 5;
    readonly memory: 25;
    readonly governance: 100;
};
/** Default triadic weights (λ₁, λ₂, λ₃), sum to 1 */
export declare const DEFAULT_TRIADIC_WEIGHTS: TriadicWeights;
/** Maximum lattice depth before pruning old nodes */
export declare const MAX_LATTICE_DEPTH = 1000;
/** Triadic weight configuration (must sum to 1) */
export interface TriadicWeights {
    immediate: number;
    memory: number;
    governance: number;
}
/** Configuration for the tri-manifold lattice */
export interface TriManifoldConfig {
    windowSizes?: {
        immediate?: number;
        memory?: number;
        governance?: number;
    };
    weights?: Partial<TriadicWeights>;
    harmonicR?: number;
    /** Reference point in Poincaré ball (default: origin) */
    referencePoint?: number[];
    /** Number of harmonic dimensions for scaling (default: 6, one per tongue) */
    harmonicDimensions?: number;
}
/** A single lattice node capturing the full tri-manifold state */
export interface LatticeNode {
    /** Monotonic tick counter */
    tick: number;
    /** Raw 21D state vector */
    rawState: number[];
    /** Poincaré ball embedding */
    embedded: number[];
    /** Hyperbolic distance from reference point */
    hyperbolicDist: number;
    /** Windowed average distances per manifold */
    manifoldDistances: {
        immediate: number;
        memory: number;
        governance: number;
    };
    /** Combined triadic distance */
    triadicDistance: number;
    /** Harmonic-scaled governance cost */
    harmonicCost: number;
    /** Norm of the Poincaré embedding (boundary proximity) */
    embeddedNorm: number;
    /** Wall-clock timestamp */
    timestamp: number;
}
/** Tri-manifold lattice snapshot for external consumption */
export interface LatticeSnapshot {
    tick: number;
    triadicDistance: number;
    harmonicCost: number;
    manifoldDistances: {
        immediate: number;
        memory: number;
        governance: number;
    };
    weights: TriadicWeights;
    nodeCount: number;
    driftVelocity: number;
}
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
export declare function harmonicScale(d: number, R?: number): number;
/**
 * Inverse harmonic scaling for flux management / phase cancellation.
 * H(d, 1/R) = (1/R)^(d²)
 *
 * Property: harmonicScale(d, R) * harmonicScaleInverse(d, R) = 1
 */
export declare function harmonicScaleInverse(d: number, R?: number): number;
/**
 * Harmonic scaling table for dimensions 1..maxD.
 * Useful for precomputation and visualization.
 */
export declare function harmonicScaleTable(maxD: number, R?: number): Array<{
    d: number;
    scale: number;
    logScale: number;
}>;
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
export declare function triadicDistance(d1: number, d2: number, dG: number, weights?: TriadicWeights): number;
/**
 * Partial derivative of triadic distance w.r.t. component i.
 * ∂d_tri/∂dᵢ = λᵢ·dᵢ / d_tri
 */
export declare function triadicPartial(dI: number, lambdaI: number, dTri: number): number;
/**
 * Sliding window for temporal manifold distance averaging.
 *
 * Maintains a fixed-size circular buffer of hyperbolic distances
 * and provides the windowed average d_k(t) = (1/W_k) Σ d_H(u(s), ℓ)
 */
export declare class TemporalWindow {
    readonly size: number;
    private buffer;
    private head;
    private count;
    private sum;
    constructor(size: number);
    /** Push a new distance sample into the window. */
    push(distance: number): void;
    /** Windowed average distance. */
    average(): number;
    /** Current sample count (may be < size during warmup). */
    filled(): number;
    /** Whether the window is fully warmed up. */
    isWarmedUp(): boolean;
    /** Most recent distance sample. */
    latest(): number;
    /** Variance of distances in the window. */
    variance(): number;
    /** Reset window to empty state. */
    reset(): void;
}
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
export declare class TriManifoldLattice {
    private readonly immediateWindow;
    private readonly memoryWindow;
    private readonly governanceWindow;
    private readonly weights;
    private readonly harmonicR;
    private readonly harmonicDimensions;
    private readonly referencePoint;
    private nodes;
    private tick;
    constructor(config?: TriManifoldConfig);
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
    ingest(rawState: number[]): LatticeNode;
    /**
     * Compute drift velocity: rate of change of triadic distance.
     * Uses finite difference of last two nodes.
     */
    driftVelocity(): number;
    /**
     * Compute drift acceleration (second derivative).
     * Positive = drift is accelerating (concerning).
     */
    driftAcceleration(): number;
    /** Get the current triadic distance (0 if no samples). */
    currentTriadicDistance(): number;
    /** Get the current harmonic cost (0 if no samples). */
    currentHarmonicCost(): number;
    /** Get the last N lattice nodes. */
    recentNodes(n: number): LatticeNode[];
    /** Current lattice snapshot. */
    snapshot(): LatticeSnapshot;
    /**
     * Check if lattice is in "resonance" — all three manifolds agree.
     *
     * When immediate, memory, and governance distances are similar,
     * the system is in a stable temporal resonance (good or bad).
     * Divergence between manifolds indicates temporal drift.
     *
     * @returns Resonance coefficient in [0, 1] where 1 = perfect agreement
     */
    temporalResonance(): number;
    /**
     * Detect temporal anomaly: immediate window diverges from governance.
     *
     * If d₁ >> d_G, something just changed that hasn't been seen before.
     * If d_G >> d₁, a past pattern is repeating that's currently quiet.
     *
     * @returns Anomaly score in [0, ∞). Values > 2 are significant.
     */
    temporalAnomaly(): number;
    /**
     * Compute the harmonic scaling table for visualization.
     * Returns H(d, R) for d = 1..maxD.
     */
    harmonicTable(maxD?: number): Array<{
        d: number;
        scale: number;
    }>;
    /**
     * Check the harmonic duality property:
     * H(d, R) * H(d, 1/R) should equal 1 for all d.
     */
    verifyDuality(d: number): {
        forward: number;
        inverse: number;
        product: number;
    };
    /** Total ticks ingested. */
    getTick(): number;
    /** Current weights (normalized). */
    getWeights(): TriadicWeights;
    /** Reset all windows and lattice state. */
    reset(): void;
}
//# sourceMappingURL=tri-manifold-lattice.d.ts.map