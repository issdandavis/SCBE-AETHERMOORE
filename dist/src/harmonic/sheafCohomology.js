"use strict";
/**
 * @file sheafCohomology.ts
 * @module harmonic/sheaf-cohomology
 * @layer Layer 9, Layer 10, Layer 12
 * @component Sheaf Cohomology for Lattices — Tarski Laplacian
 * @version 3.2.4
 *
 * Implements sheaf cohomology on cellular sheaves valued in complete lattices,
 * using the Tarski fixed-point approach:
 *
 *   TH^k(X; F) = Fix(id ∧ L_k) = Post(L_k)
 *
 * where L_k is the Tarski Laplacian — a meet-based diffusion operator on
 * lattice-valued cochains. This generalises vector-valued cellular sheaf
 * cohomology to non-linear settings (lattices with Galois connections).
 *
 * Key structures:
 *   - CompleteLattice<T>: bounded lattice with meet/join/top/bottom
 *   - GaloisConnection<A,B>: adjoint pair (lower ⊣ upper) between lattices
 *   - CellComplex: abstract cell complex (vertices, edges, faces)
 *   - CellularSheaf<T>: sheaf assigning lattice stalks + restriction maps
 *   - tarskiLaplacian: L_k operator via meet over cofaces
 *   - tarskiCohomology: TH^k via greatest post-fixpoint iteration
 *   - hodgeLaplacians: up/down Laplacians L_k^+, L_k^-
 *   - SheafCohomologyEngine: full pipeline integrating with SCBE lattices
 *
 * Mathematical axioms satisfied:
 *   - Symmetry (L5, L9-10): Galois connections preserve order structure
 *   - Composition (L1, L14): Pipeline integrity via sheaf functoriality
 *   - Unitarity (L2, L4): Norm-like coherence via lattice height
 *
 * @see Tarski's Fixed-Point Theorem (1955)
 * @see Curry, Ghrist, Robinson — "Cellular Sheaves of Lattices" (2023)
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.defaultSheafEngine = exports.SheafCohomologyEngine = exports.BooleanLattice = void 0;
exports.topCochain = topCochain;
exports.bottomCochain = bottomCochain;
exports.tarskiLaplacian = tarskiLaplacian;
exports.failToNoise = failToNoise;
exports.braidedTemporalDistance = braidedTemporalDistance;
exports.braidedMetaTime = braidedMetaTime;
exports.cohomologicalHarmonicWall = cohomologicalHarmonicWall;
exports.tarskiCohomology = tarskiCohomology;
exports.v2GlobalSections = v2GlobalSections;
exports.upLaplacian = upLaplacian;
exports.downLaplacian = downLaplacian;
exports.hodgeLaplacian = hodgeLaplacian;
exports.hodgeCohomology = hodgeCohomology;
exports.IntervalLattice = IntervalLattice;
exports.PowerSetLattice = PowerSetLattice;
exports.UnitIntervalLattice = UnitIntervalLattice;
exports.ProductLattice = ProductLattice;
exports.v2IdentityConnection = v2IdentityConnection;
exports.constantConnection = constantConnection;
exports.thresholdConnection = thresholdConnection;
exports.scalingConnection = scalingConnection;
exports.graphComplex = graphComplex;
exports.simplicialComplex = simplicialComplex;
exports.v2ConstantSheaf = v2ConstantSheaf;
exports.thresholdSheaf = thresholdSheaf;
exports.twistedSheaf = twistedSheaf;
exports.analyseCohomology = analyseCohomology;
exports.detectObstructions = detectObstructions;
const qcLattice_js_1 = require("./qcLattice.js");
/**
 * Create a cochain assigning top to every cell of dimension k.
 */
function topCochain(sheaf, dim) {
    const result = new Map();
    for (const cell of sheaf.complex.cells(dim)) {
        result.set(cell.id, sheaf.stalk(cell).top);
    }
    return result;
}
/**
 * Create a cochain assigning bottom to every cell of dimension k.
 */
function bottomCochain(sheaf, dim) {
    const result = new Map();
    for (const cell of sheaf.complex.cells(dim)) {
        result.set(cell.id, sheaf.stalk(cell).bottom);
    }
    return result;
}
// ═══════════════════════════════════════════════════════════════
// Tarski Laplacian
// ═══════════════════════════════════════════════════════════════
/**
 * Tarski Laplacian L_k acting on k-cochains.
 *
 * For each k-cell σ:
 *   (L_k x)_σ = ∧_{τ ∈ δσ} F^q_{σ→τ}( ∧_{σ' ∈ ∂τ} F^q_{σ'→τ} x_{σ'} )
 *
 * where δσ = cofaces of σ, ∂τ = faces of τ, and F^q = upper adjoint.
 *
 * This is a monotone operator on the product lattice of k-cochains,
 * so Tarski's theorem guarantees fixed points exist.
 */
function tarskiLaplacian(sheaf, dim, x) {
    const result = new Map();
    const kCells = sheaf.complex.cells(dim);
    for (const sigma of kCells) {
        const cofaces = sheaf.complex.cofaces(sigma);
        if (cofaces.length === 0) {
            // No cofaces: L_k x_σ = ⊤ (vacuous meet)
            result.set(sigma.id, sheaf.stalk(sigma).top);
            continue;
        }
        // Outer meet: ∧ over cofaces τ
        let outerMeet = sheaf.stalk(sigma).top;
        for (const tau of cofaces) {
            const faces = sheaf.complex.faces(tau);
            // Inner meet: ∧ over faces σ' of τ
            // Start with ⊤ in τ's stalk, meet with each restricted face value
            let innerMeet = sheaf.stalk(tau).top;
            for (const sigmaPrime of faces) {
                const xVal = x.get(sigmaPrime.id);
                if (xVal === undefined)
                    continue;
                // Apply restriction (lower adjoint) from face to coface stalk
                const conn = sheaf.restriction(sigmaPrime, tau);
                const restricted = conn.lower(xVal);
                innerMeet = sheaf.stalk(tau).meet(innerMeet, restricted);
            }
            // Pull back via upper adjoint from τ's stalk to σ's stalk
            const conn = sheaf.restriction(sigma, tau);
            const pulledBack = conn.upper(innerMeet);
            outerMeet = sheaf.stalk(sigma).meet(outerMeet, pulledBack);
        }
        result.set(sigma.id, outerMeet);
    }
    return result;
}
// FAIL-TO-NOISE
// ============================================================
/**
 * Fail-to-noise: produce a fixed-size output indistinguishable
 * from legitimate governance data when obstruction is detected.
 *
 * Uses obstruction degree + vertex count as deterministic seed.
 * Output is always `size` bytes regardless of input.
 */
function failToNoise(obstruction, size = 256) {
    const buf = new Uint8Array(size);
    // LCG seeded from obstruction — deterministic, reproducible
    let seed = (Math.floor(obstruction * 2147483647) | 1) >>> 0;
    for (let i = 0; i < size; i++) {
        seed = ((seed * 1103515245 + 12345) & 0x7fffffff) >>> 0;
        buf[i] = seed & 0xff;
    }
    return buf;
}
// ============================================================
// BRAIDED TEMPORAL DISTANCE (T-braiding integration)
// ============================================================
/**
 * Braided temporal distance: sum of pairwise hyperbolic distances
 * between temporal T-variants embedded in the Poincaré ball.
 *
 * For triadic (3 variants):
 *   d_b = d_H(T_i, T_m) + d_H(T_m, T_g) + d_H(T_g, T_i)
 *
 * For tetradic (4 variants):
 *   d_b = Σ_{all 6 pairs} d_H(T_a, T_b)
 *
 * Uses arcosh formula: d_H(u,v) = arcosh(1 + 2|u-v|² / ((1-|u|²)(1-|v|²)))
 *
 * @param variants - scalar values for each T in (-1, 1) (Poincaré ball)
 */
function braidedTemporalDistance(variants) {
    const n = variants.length;
    let total = 0;
    for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
            const u = Math.max(-0.999, Math.min(0.999, variants[i]));
            const v = Math.max(-0.999, Math.min(0.999, variants[j]));
            const diff2 = (u - v) * (u - v);
            const denom = (1 - u * u) * (1 - v * v);
            const arg = 1 + (2 * diff2) / Math.max(denom, 1e-15);
            total += Math.acosh(Math.max(1, arg));
        }
    }
    return total;
}
/**
 * Braided meta-time: T_b = T^(t+k) · intent · context · [1/t]
 *
 * Multiplicative braiding of temporal variants through the base T.
 *
 * @param T - base time constant
 * @param t - temporal exponent (memory variant)
 * @param intent - intent alignment scalar
 * @param context - governance context scalar
 * @param includePredictive - if true, includes T/t forecast term
 */
function braidedMetaTime(T, t, intent, context, includePredictive = false) {
    const k = includePredictive ? 2 : 2;
    const base = Math.pow(Math.max(1e-10, T), t + k) * intent * context;
    if (includePredictive && Math.abs(t) > 1e-10) {
        return base / t;
    }
    return base;
}
// ============================================================
// COHOMOLOGICAL HARMONIC WALL
// ============================================================
/**
 * Cohomological harmonic wall: combines obstruction degree with
 * the existing H(d, R) = R^(d²) super-exponential scaling.
 *
 * The obstruction degree from Tarski cohomology maps to an
 * effective dimension d*, which feeds into the harmonic wall.
 * Result: adversarial temporal disagreement gets exponentially
 * amplified into governance cost.
 *
 * @param obstruction - [0,1] from detectPolicyObstruction
 * @param maxDimension - maximum effective dimension (default: 6, one per tongue)
 * @param R - harmonic ratio (default: 1.5, perfect fifth)
 */
function cohomologicalHarmonicWall(obstruction, maxDimension = 6, R = 1.5) {
    // Map obstruction [0,1] → effective dimension [0, maxDimension]
    const dStar = obstruction * maxDimension;
    // H(d*, R) = R^(d*²)
    return Math.pow(R, dStar * dStar);
}
/**
 * Compute Tarski cohomology TH^k(X; F) as the greatest post-fixpoint of L_k.
 *
 * Algorithm:
 *   1. Start with x₀ = ⊤ (top cochain)
 *   2. Iterate x_{t+1} = x_t ∧ L_k(x_t)
 *   3. Converges in ≤ h steps where h = lattice height
 *
 * TH^0(X; F) = Γ(X; F) = global sections.
 *
 * @param sheaf The cellular sheaf
 * @param dim Cochain dimension k
 * @param maxIter Maximum iterations (default: lattice height + 10)
 * @returns CohomologyResult with fixed-point cochains
 */
function tarskiCohomology(sheaf, dim, maxIter) {
    const h = sheaf.lattice.height();
    const limit = maxIter ?? h + 10;
    // Start at ⊤
    let current = topCochain(sheaf, dim);
    let iterations = 0;
    for (let t = 0; t < limit; t++) {
        iterations++;
        const laplacianResult = tarskiLaplacian(sheaf, dim, current);
        // x_{t+1} = x_t ∧ L_k(x_t)
        const next = new Map();
        let changed = false;
        for (const cell of sheaf.complex.cells(dim)) {
            const xVal = current.get(cell.id);
            const lVal = laplacianResult.get(cell.id);
            const lattice = sheaf.stalk(cell);
            const meetVal = lattice.meet(xVal, lVal);
            next.set(cell.id, meetVal);
            if (!lattice.eq(meetVal, xVal)) {
                changed = true;
            }
        }
        current = next;
        if (!changed) {
            return { cochains: current, iterations, converged: true, degree: dim };
        }
    }
    return { cochains: current, iterations, converged: false, degree: dim };
}
/**
 * Compute global sections Γ(X; F) = TH^0(X; F).
 * These are assignments to vertices consistent across all edges.
 */
function v2GlobalSections(sheaf) {
    return tarskiCohomology(sheaf, 0);
}
// ═══════════════════════════════════════════════════════════════
// Hodge-Style Laplacians: L_k^+ and L_k^-
// ═══════════════════════════════════════════════════════════════
/**
 * Up-Laplacian L_k^+ (diffusion to cofaces only).
 * Acts on k-cochains using (k+1)-dimensional incidence.
 */
function upLaplacian(sheaf, dim, x) {
    // Same as tarskiLaplacian — uses cofaces
    return tarskiLaplacian(sheaf, dim, x);
}
/**
 * Down-Laplacian L_k^- (diffusion from faces only).
 * Acts on k-cochains using (k-1)-dimensional incidence.
 *
 * For each k-cell σ:
 *   (L_k^- x)_σ = ∨_{ρ ∈ ∂σ} F_{ρ→σ}^lower( ∨_{σ' ∈ δρ} F_{σ'→ρ... } )
 *
 * Uses join (∨) instead of meet, giving the dual operator.
 */
function downLaplacian(sheaf, dim, x) {
    const result = new Map();
    const kCells = sheaf.complex.cells(dim);
    for (const sigma of kCells) {
        const facesList = sheaf.complex.faces(sigma);
        if (facesList.length === 0) {
            result.set(sigma.id, sheaf.stalk(sigma).bottom);
            continue;
        }
        // Outer join: ∨ over faces ρ of σ
        let outerJoin = sheaf.stalk(sigma).bottom;
        for (const rho of facesList) {
            const cofaces = sheaf.complex.cofaces(rho);
            // Inner join: ∨ over cofaces σ' of ρ
            let innerJoin = sheaf.stalk(rho).bottom;
            for (const sigmaPrime of cofaces) {
                const xVal = x.get(sigmaPrime.id);
                if (xVal === undefined)
                    continue;
                // Pull back from σ' to ρ via upper adjoint
                const conn = sheaf.restriction(rho, sigmaPrime);
                const restricted = conn.upper(xVal);
                innerJoin = sheaf.stalk(rho).join(innerJoin, restricted);
            }
            // Push forward from ρ to σ via lower adjoint
            const conn = sheaf.restriction(rho, sigma);
            const pushed = conn.lower(innerJoin);
            outerJoin = sheaf.stalk(sigma).join(outerJoin, pushed);
        }
        result.set(sigma.id, outerJoin);
    }
    return result;
}
/**
 * Hodge Laplacian L_k = L_k^+ ∧ L_k^- (meet of up and down).
 */
function hodgeLaplacian(sheaf, dim, x) {
    const up = upLaplacian(sheaf, dim, x);
    const down = downLaplacian(sheaf, dim, x);
    const result = new Map();
    for (const cell of sheaf.complex.cells(dim)) {
        const uVal = up.get(cell.id);
        const dVal = down.get(cell.id);
        result.set(cell.id, sheaf.stalk(cell).meet(uVal, dVal));
    }
    return result;
}
/**
 * Hodge cohomology HH^k via greatest post-fixpoint of Hodge Laplacian.
 */
function hodgeCohomology(sheaf, dim, maxIter) {
    const h = sheaf.lattice.height();
    const limit = maxIter ?? h + 10;
    let current = topCochain(sheaf, dim);
    let iterations = 0;
    for (let t = 0; t < limit; t++) {
        iterations++;
        const hodgeResult = hodgeLaplacian(sheaf, dim, current);
        const next = new Map();
        let changed = false;
        for (const cell of sheaf.complex.cells(dim)) {
            const xVal = current.get(cell.id);
            const hVal = hodgeResult.get(cell.id);
            const lattice = sheaf.stalk(cell);
            const meetVal = lattice.meet(xVal, hVal);
            next.set(cell.id, meetVal);
            if (!lattice.eq(meetVal, xVal)) {
                changed = true;
            }
        }
        current = next;
        if (!changed) {
            return { cochains: current, iterations, converged: true, degree: dim };
        }
    }
    return { cochains: current, iterations, converged: false, degree: dim };
}
// ═══════════════════════════════════════════════════════════════
// Concrete Lattice Implementations
// ═══════════════════════════════════════════════════════════════
/**
 * Boolean lattice {false, true} with ∧ = AND, ∨ = OR.
 * Height = 1. The simplest complete lattice.
 */
exports.BooleanLattice = {
    top: true,
    bottom: false,
    meet: (a, b) => a && b,
    join: (a, b) => a || b,
    leq: (a, b) => !a || b, // a ≤ b iff a → b
    eq: (a, b) => a === b,
    height: () => 1,
};
/**
 * Bounded integer interval lattice [lo, hi] with min/max.
 * Height = hi - lo.
 */
function IntervalLattice(lo, hi) {
    return {
        top: hi,
        bottom: lo,
        meet: (a, b) => Math.min(a, b),
        join: (a, b) => Math.max(a, b),
        leq: (a, b) => a <= b,
        eq: (a, b) => a === b,
        height: () => hi - lo,
    };
}
/**
 * Power-set lattice over n elements, represented as bitmasks.
 * Meet = intersection, Join = union, ⊤ = full set, ⊥ = empty set.
 * Height = n.
 */
function PowerSetLattice(n) {
    const full = (1 << n) - 1;
    return {
        top: full,
        bottom: 0,
        meet: (a, b) => a & b,
        join: (a, b) => a | b,
        leq: (a, b) => (a & b) === a, // a ⊆ b
        eq: (a, b) => a === b,
        height: () => n,
    };
}
/**
 * Unit interval lattice [0, 1] with min/max, discretised to `steps` levels.
 * Useful for fuzzy/probabilistic sheaves.
 * Height = steps.
 */
function UnitIntervalLattice(steps = 100) {
    const clamp = (v) => Math.max(0, Math.min(1, v));
    const quantise = (v) => Math.round(clamp(v) * steps) / steps;
    return {
        top: 1,
        bottom: 0,
        meet: (a, b) => quantise(Math.min(a, b)),
        join: (a, b) => quantise(Math.max(a, b)),
        leq: (a, b) => quantise(a) <= quantise(b) + 1e-12,
        eq: (a, b) => Math.abs(quantise(a) - quantise(b)) < 1e-12,
        height: () => steps,
    };
}
/**
 * Product lattice L₁ × L₂ with component-wise meet/join.
 */
function ProductLattice(l1, l2) {
    return {
        top: [l1.top, l2.top],
        bottom: [l1.bottom, l2.bottom],
        meet: (a, b) => [l1.meet(a[0], b[0]), l2.meet(a[1], b[1])],
        join: (a, b) => [l1.join(a[0], b[0]), l2.join(a[1], b[1])],
        leq: (a, b) => l1.leq(a[0], b[0]) && l2.leq(a[1], b[1]),
        eq: (a, b) => l1.eq(a[0], b[0]) && l2.eq(a[1], b[1]),
        height: () => l1.height() + l2.height(),
    };
}
// ═══════════════════════════════════════════════════════════════
// Concrete Galois Connections
// ═══════════════════════════════════════════════════════════════
/** Identity connection: both adjoints are identity */
function v2IdentityConnection() {
    return { lower: (a) => a, upper: (b) => b };
}
/** Constant connection: lower maps everything to a fixed element */
function constantConnection(lattice, value) {
    return {
        lower: () => value,
        upper: () => lattice.top,
    };
}
/**
 * Threshold connection for interval lattices:
 *   lower(a) = a ≥ threshold ? a : bottom
 *   upper(b) = b
 */
function thresholdConnection(threshold, lattice) {
    return {
        lower: (a) => (a >= threshold ? a : lattice.bottom),
        upper: (b) => b,
    };
}
/**
 * Scaling connection for unit-interval lattice:
 *   lower(a) = clamp(a * scale)
 *   upper(b) = clamp(b / scale)
 */
function scalingConnection(scale) {
    const clamp01 = (v) => Math.max(0, Math.min(1, v));
    return {
        lower: (a) => clamp01(a * scale),
        upper: (b) => clamp01(b / (scale || 1)),
    };
}
// ═══════════════════════════════════════════════════════════════
// Cell Complex Builders
// ═══════════════════════════════════════════════════════════════
/**
 * Build a cell complex from an undirected graph (vertices + edges).
 * Vertices are 0-cells, edges are 1-cells.
 */
function graphComplex(numVertices, edges) {
    const vertices = Array.from({ length: numVertices }, (_, i) => ({
        dim: 0,
        id: i,
    }));
    const edgeCells = edges.map((_, i) => ({
        dim: 1,
        id: i,
    }));
    // Build adjacency
    const vertexCofaces = new Map();
    const edgeFaces = new Map();
    for (let i = 0; i < numVertices; i++) {
        vertexCofaces.set(i, []);
    }
    for (let e = 0; e < edges.length; e++) {
        const [u, v] = edges[e];
        vertexCofaces.get(u).push(e);
        vertexCofaces.get(v).push(e);
        edgeFaces.set(e, [u, v]);
    }
    return {
        cells(dim) {
            if (dim === 0)
                return vertices;
            if (dim === 1)
                return edgeCells;
            return [];
        },
        maxDim() {
            return edges.length > 0 ? 1 : 0;
        },
        faces(cell) {
            if (cell.dim === 1) {
                return (edgeFaces.get(cell.id) ?? []).map((id) => ({ dim: 0, id }));
            }
            return [];
        },
        cofaces(cell) {
            if (cell.dim === 0) {
                return (vertexCofaces.get(cell.id) ?? []).map((id) => ({ dim: 1, id }));
            }
            return [];
        },
        incidence(face, coface) {
            if (face.dim !== 0 || coface.dim !== 1)
                return 0;
            const fcs = edgeFaces.get(coface.id);
            if (!fcs)
                return 0;
            if (fcs[0] === face.id)
                return 1;
            if (fcs[1] === face.id)
                return -1;
            return 0;
        },
    };
}
/**
 * Build a simplicial complex from triangles (vertices + edges + 2-faces).
 */
function simplicialComplex(numVertices, edges, triangles) {
    const base = graphComplex(numVertices, edges);
    const faceCells = triangles.map((_, i) => ({ dim: 2, id: i }));
    // Map each triangle to its edges
    const edgeIndex = new Map();
    for (let e = 0; e < edges.length; e++) {
        const [u, v] = edges[e];
        edgeIndex.set(`${Math.min(u, v)}-${Math.max(u, v)}`, e);
    }
    const triangleEdges = new Map();
    const edgeTriangles = new Map();
    for (let e = 0; e < edges.length; e++) {
        edgeTriangles.set(e, []);
    }
    for (let t = 0; t < triangles.length; t++) {
        const [a, b, c] = triangles[t];
        const triEdges = [];
        for (const [u, v] of [
            [a, b],
            [b, c],
            [a, c],
        ]) {
            const key = `${Math.min(u, v)}-${Math.max(u, v)}`;
            const eid = edgeIndex.get(key);
            if (eid !== undefined) {
                triEdges.push(eid);
                edgeTriangles.get(eid).push(t);
            }
        }
        triangleEdges.set(t, triEdges);
    }
    return {
        cells(dim) {
            if (dim === 2)
                return faceCells;
            return base.cells(dim);
        },
        maxDim() {
            return triangles.length > 0 ? 2 : base.maxDim();
        },
        faces(cell) {
            if (cell.dim === 2) {
                return (triangleEdges.get(cell.id) ?? []).map((id) => ({ dim: 1, id }));
            }
            return base.faces(cell);
        },
        cofaces(cell) {
            if (cell.dim === 1) {
                return (edgeTriangles.get(cell.id) ?? []).map((id) => ({ dim: 2, id }));
            }
            return base.cofaces(cell);
        },
        incidence(face, coface) {
            if (face.dim === 1 && coface.dim === 2) {
                const fcs = triangleEdges.get(coface.id);
                return fcs && fcs.includes(face.id) ? 1 : 0;
            }
            return base.incidence(face, coface);
        },
    };
}
// ═══════════════════════════════════════════════════════════════
// Sheaf Constructors
// ═══════════════════════════════════════════════════════════════
/**
 * Constant sheaf: every stalk is the same lattice, every restriction is identity.
 */
function v2ConstantSheaf(complex, lattice) {
    return {
        lattice,
        complex,
        stalk: () => lattice,
        restriction: () => v2IdentityConnection(),
    };
}
/**
 * Threshold sheaf on a graph: edges enforce agreement above a threshold.
 * If a vertex value is below threshold, the edge restriction maps it to ⊥.
 */
function thresholdSheaf(complex, lattice, threshold) {
    return {
        lattice,
        complex,
        stalk: () => lattice,
        restriction: () => thresholdConnection(threshold, lattice),
    };
}
/**
 * Twisted sheaf: each edge has a custom scaling factor.
 * Useful for modelling trust decay or risk amplification across graph.
 */
function twistedSheaf(complex, lattice, edgeScales) {
    return {
        lattice,
        complex,
        stalk: () => lattice,
        restriction: (_face, coface) => {
            const scale = edgeScales.get(coface.id) ?? 1;
            return scalingConnection(scale);
        },
    };
}
/**
 * Analyse a cohomology result and produce diagnostics.
 */
function analyseCohomology(result, lattice) {
    let maxEl = lattice.bottom;
    let minEl = lattice.top;
    let nonTrivialCount = 0;
    let firstValue;
    let allSame = true;
    for (const [, value] of result.cochains) {
        if (!lattice.eq(value, lattice.bottom)) {
            nonTrivialCount++;
        }
        if (lattice.leq(maxEl, value)) {
            maxEl = value;
        }
        if (lattice.leq(value, minEl)) {
            minEl = value;
        }
        if (firstValue === undefined) {
            firstValue = value;
        }
        else if (!lattice.eq(value, firstValue)) {
            allSame = false;
        }
    }
    // Height utilisation for numeric lattices: approximate
    const h = lattice.height();
    let heightUtil = 0;
    if (h > 0 && typeof maxEl === 'number' && typeof minEl === 'number') {
        const top = lattice.top;
        const bot = lattice.bottom;
        const range = top - bot;
        heightUtil = range > 0 ? (maxEl - minEl) / range : 0;
    }
    return {
        bettiNumber: nonTrivialCount,
        maxElement: maxEl,
        minElement: minEl,
        isGloballyConsistent: allSame,
        heightUtilisation: heightUtil,
    };
}
/**
 * Detect obstructions to global consistency in a sheaf.
 * Compares TH^0 (global sections) against vertex assignments to find
 * where local data fails to glue.
 */
function detectObstructions(sheaf, localAssignment) {
    const obstructions = [];
    const edges = sheaf.complex.cells(1);
    for (const edge of edges) {
        const facesList = sheaf.complex.faces(edge);
        if (facesList.length < 2)
            continue;
        const [v0, v1] = facesList;
        const val0 = localAssignment.get(v0.id);
        const val1 = localAssignment.get(v1.id);
        if (val0 === undefined || val1 === undefined)
            continue;
        const conn0 = sheaf.restriction(v0, edge);
        const conn1 = sheaf.restriction(v1, edge);
        // Restrict both vertex values to the edge stalk
        const r0 = conn0.lower(val0);
        const r1 = conn1.lower(val1);
        const edgeLattice = sheaf.stalk(edge);
        // If restrictions don't agree, there's an obstruction
        if (!edgeLattice.eq(r0, r1)) {
            // Severity: distance between the two restrictions relative to lattice height
            const meetVal = edgeLattice.meet(r0, r1);
            const joinVal = edgeLattice.join(r0, r1);
            let severity = 0;
            if (typeof meetVal === 'number' && typeof joinVal === 'number') {
                const range = edgeLattice.top - edgeLattice.bottom;
                severity = range > 0 ? (joinVal - meetVal) / range : 1;
            }
            else {
                severity = edgeLattice.eq(meetVal, edgeLattice.bottom) ? 1 : 0.5;
            }
            obstructions.push({
                cells: [v0, v1, edge],
                severity,
                description: `Obstruction at edge ${edge.id}: vertices ${v0.id} and ${v1.id} disagree`,
            });
        }
    }
    return obstructions;
}
const DEFAULT_SHEAF_CONFIG = {
    latticeSteps: 100,
    maxIterations: 120,
    obstructionThreshold: 0.5,
    harmonicCoupling: qcLattice_js_1.PHI,
};
/**
 * SCBE Sheaf Cohomology Engine.
 *
 * Integrates Tarski cohomology with the 14-layer pipeline:
 * - Builds a graph complex from SCBE 6D vector topology
 * - Assigns lattice-valued stalks capturing safety scores
 * - Computes TH^0 (global consensus) and TH^1 (obstruction detection)
 * - Maps obstructions to risk amplification for Layer 12/13
 *
 * Usage:
 *   const engine = new SheafCohomologyEngine();
 *   const result = engine.analyseVectorField(vectors, edges);
 */
class SheafCohomologyEngine {
    config;
    lattice;
    constructor(config) {
        this.config = { ...DEFAULT_SHEAF_CONFIG, ...config };
        this.lattice = UnitIntervalLattice(this.config.latticeSteps);
    }
    /**
     * Analyse a field of 6D vectors connected by edges.
     * Each vector is projected to a safety score in [0, 1] via its norm.
     * Edges carry scaling connections weighted by PHI-based distances.
     *
     * @param vectors Array of 6D vectors (vertex data)
     * @param edges Pairs of vertex indices forming edges
     * @returns Full sheaf analysis with cohomology and obstructions
     */
    analyseVectorField(vectors, edges) {
        // Build complex
        const complex = graphComplex(vectors.length, edges);
        // Compute safety scores from vector norms
        const safetyScores = vectors.map((v) => {
            const normSq = v.reduce((s, x) => s + x * x, 0);
            // Map norm to [0, 1]: closer to origin = safer
            return Math.exp(-normSq);
        });
        // Compute edge scales based on vector distances
        const edgeScales = new Map();
        for (let e = 0; e < edges.length; e++) {
            const [i, j] = edges[e];
            const dist = Math.sqrt(vectors[i].reduce((s, x, k) => s + (x - vectors[j][k]) ** 2, 0));
            // Scale by golden ratio coupling: closer vectors → stronger connection
            const scale = Math.exp(-dist * this.config.harmonicCoupling);
            edgeScales.set(e, Math.max(0.01, Math.min(1, scale)));
        }
        // Build twisted sheaf
        const sheaf = twistedSheaf(complex, this.lattice, edgeScales);
        // Build local assignment from safety scores
        const localAssignment = new Map();
        for (let i = 0; i < vectors.length; i++) {
            localAssignment.set(i, Math.max(0, Math.min(1, safetyScores[i])));
        }
        // Compute cohomology
        const th0 = tarskiCohomology(sheaf, 0, this.config.maxIterations);
        const th1 = complex.maxDim() >= 1
            ? tarskiCohomology(sheaf, 1, this.config.maxIterations)
            : { cochains: new Map(), iterations: 0, converged: true, degree: 1 };
        const hh0 = hodgeCohomology(sheaf, 0, this.config.maxIterations);
        // Detect obstructions
        const obstructions = detectObstructions(sheaf, localAssignment);
        // Diagnostics
        const diagnostics = analyseCohomology(th0, this.lattice);
        // Coherence score
        const totalSeverity = obstructions.reduce((s, o) => s + o.severity, 0);
        const maxPossibleSeverity = Math.max(1, edges.length);
        const coherenceScore = Math.max(0, 1 - totalSeverity / maxPossibleSeverity);
        // Risk amplification: obstruction severity scaled by harmonic coupling
        const significantObstructions = obstructions.filter((o) => o.severity >= this.config.obstructionThreshold);
        const riskAmplification = significantObstructions.length > 0
            ? Math.pow(this.config.harmonicCoupling, significantObstructions.reduce((s, o) => s + o.severity * o.severity, 0))
            : 1;
        return {
            globalSections: th0,
            firstCohomology: th1,
            hodgeSections: hh0,
            obstructions,
            diagnostics,
            coherenceScore,
            riskAmplification,
        };
    }
    /**
     * Quick coherence check: returns true if the vector field has no
     * significant obstructions (all local data glues globally).
     */
    isCoherent(vectors, edges) {
        const result = this.analyseVectorField(vectors, edges);
        return result.coherenceScore >= 1 - 1e-10;
    }
    /**
     * Compute the Euler characteristic of the cohomology:
     *   χ = Σ (-1)^k · |TH^k|
     *
     * For a graph (max dim 1): χ = |TH^0| - |TH^1|
     */
    eulerCharacteristic(analysis) {
        const th0Count = analysis.diagnostics.bettiNumber;
        let th1Count = 0;
        for (const [, value] of analysis.firstCohomology.cochains) {
            if (!this.lattice.eq(value, this.lattice.bottom)) {
                th1Count++;
            }
        }
        return th0Count - th1Count;
    }
}
exports.SheafCohomologyEngine = SheafCohomologyEngine;
/**
 * Default sheaf cohomology engine with standard configuration.
 */
exports.defaultSheafEngine = new SheafCohomologyEngine();
//# sourceMappingURL=sheafCohomology.js.map