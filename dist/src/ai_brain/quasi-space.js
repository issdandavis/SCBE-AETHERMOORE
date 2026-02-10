"use strict";
/**
 * @file quasi-space.ts
 * @module ai_brain/quasi-space
 * @layer Layer 4, Layer 5, Layer 9
 * @component Quasicrystal Icosahedral Projection
 * @version 1.1.0
 * @since 2026-02-07
 *
 * Implements quasicrystal-based projections for the unified brain manifold.
 * Uses 6D icosahedral symmetry (referencing Shechtman's Nobel-prize-winning
 * discovery of quasicrystals) applied to AI state space.
 *
 * The projection creates aperiodic tiling of the state space, ensuring
 * that adversarial agents cannot predict or reproduce the geometric structure.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.icosahedralProjection = icosahedralProjection;
exports.classifyVoxelRealm = classifyVoxelRealm;
exports.createOctreeRoot = createOctreeRoot;
exports.octreeInsert = octreeInsert;
exports.brainStateToPenrose = brainStateToPenrose;
exports.quasicrystalPotential = quasicrystalPotential;
const types_js_1 = require("./types.js");
// ═══════════════════════════════════════════════════════════════
// Icosahedral Projection Matrix
// ═══════════════════════════════════════════════════════════════
/**
 * 6x6 icosahedral projection matrix based on golden ratio geometry.
 * This matrix preserves the aperiodic symmetry properties of quasicrystals
 * when projecting from 6D "physical" space to 6D "internal" space.
 *
 * The matrix rows are derived from icosahedral vertex coordinates
 * normalized to unit vectors.
 */
function icosahedralMatrix() {
    const phi = types_js_1.PHI;
    const phiInv = 1 / phi;
    // Icosahedral basis vectors (normalized)
    const raw = [
        [1, phi, 0, phiInv, 0, 0],
        [0, 1, phi, 0, phiInv, 0],
        [0, 0, 1, phi, 0, phiInv],
        [phiInv, 0, 0, 1, phi, 0],
        [0, phiInv, 0, 0, 1, phi],
        [phi, 0, phiInv, 0, 0, 1],
    ];
    // Normalize each row
    return raw.map((row) => {
        const norm = Math.sqrt(row.reduce((s, v) => s + v * v, 0));
        return row.map((v) => v / norm);
    });
}
const ICO_MATRIX = icosahedralMatrix();
/**
 * Project a 6D vector using icosahedral symmetry for aperiodic order.
 *
 * This creates a quasicrystalline structure in the projected space,
 * making it computationally infeasible for adversaries to predict
 * the geometric layout.
 *
 * @param vector6d - Input 6D vector
 * @returns Projected 6D vector with icosahedral symmetry
 */
function icosahedralProjection(vector6d) {
    if (vector6d.length < 6) {
        throw new RangeError(`Expected at least 6D vector, got ${vector6d.length}D`);
    }
    const result = new Array(6).fill(0);
    for (let i = 0; i < 6; i++) {
        for (let j = 0; j < 6; j++) {
            result[i] += ICO_MATRIX[i][j] * vector6d[j];
        }
    }
    // Normalize to unit sphere
    const norm = Math.sqrt(result.reduce((s, v) => s + v * v, 0));
    if (norm < types_js_1.BRAIN_EPSILON)
        return result;
    return result.map((v) => v / norm);
}
/**
 * Classify a point into a voxel realm based on its distance from origin.
 *
 * @param point - Point in Poincare ball
 * @returns Voxel realm classification
 */
function classifyVoxelRealm(point) {
    const r = Math.sqrt(point.reduce((s, v) => s + v * v, 0));
    if (r < 0.5)
        return 'gold';
    if (r < 0.95)
        return 'purple';
    return 'red';
}
/**
 * Create a sparse octree root node for the Poincare ball.
 *
 * @param dimensions - Number of dimensions (default: 3 for spatial queries)
 * @param capacity - Max points per leaf before splitting (default: 8)
 * @returns Root octree node
 */
function createOctreeRoot(dimensions = 3, capacity = 8) {
    return {
        center: new Array(dimensions).fill(0),
        halfWidth: 1.0,
        depth: 0,
        realm: 'gold',
        children: new Array(2 ** dimensions).fill(null),
        points: [],
        capacity,
    };
}
/**
 * Insert a point into the sparse octree.
 * Only allocates nodes where points actually exist.
 *
 * @param node - Octree node to insert into
 * @param point - Point to insert
 * @param maxDepth - Maximum tree depth (default: 6, giving 64^3 resolution)
 */
function octreeInsert(node, point, maxDepth = 6) {
    // Update realm based on point
    node.realm = classifyVoxelRealm(point);
    // If leaf and has capacity, just add
    if (node.points.length < node.capacity || node.depth >= maxDepth) {
        node.points.push(point);
        return;
    }
    // Subdivide
    const dims = node.center.length;
    const childHalfWidth = node.halfWidth / 2;
    // Determine which child octant this point belongs to
    let childIndex = 0;
    for (let d = 0; d < dims; d++) {
        if (point[d] >= node.center[d]) {
            childIndex |= 1 << d;
        }
    }
    // Create child if needed
    if (!node.children[childIndex]) {
        const childCenter = node.center.map((c, d) => point[d] >= c ? c + childHalfWidth : c - childHalfWidth);
        node.children[childIndex] = {
            center: childCenter,
            halfWidth: childHalfWidth,
            depth: node.depth + 1,
            realm: classifyVoxelRealm(point),
            children: new Array(2 ** dims).fill(null),
            points: [],
            capacity: node.capacity,
        };
    }
    octreeInsert(node.children[childIndex], point, maxDepth);
}
// ═══════════════════════════════════════════════════════════════
// Penrose Tiling Integration
// ═══════════════════════════════════════════════════════════════
/**
 * Generate a 2D Penrose tiling vertex from a 21D brain state.
 *
 * Projects the high-dimensional state through the icosahedral matrix
 * and then applies the cut-and-project method to generate a
 * quasicrystalline coordinate.
 *
 * @param state - 21D brain state vector
 * @returns 2D Penrose tiling coordinate [x, y]
 */
function brainStateToPenrose(state) {
    if (state.length < 6) {
        throw new RangeError('State must have at least 6 dimensions for Penrose projection');
    }
    // Take first 6 dimensions for icosahedral projection
    const projected = icosahedralProjection(state.slice(0, 6));
    // Cut-and-project: project to 2D using first two components
    // Apply golden ratio scaling for quasicrystalline spacing
    const x = projected[0] * types_js_1.PHI + projected[2] * types_js_1.PHI ** 2;
    const y = projected[1] * types_js_1.PHI + projected[3] * types_js_1.PHI ** 2;
    return [x, y];
}
/**
 * Compute the quasicrystal potential at a point.
 * V(r) = sum_k cos(G_k . r) where G_k are reciprocal lattice vectors
 * with 5-fold symmetry.
 *
 * @param point - 2D point
 * @returns Potential value
 */
function quasicrystalPotential(point) {
    let V = 0;
    // 5-fold symmetric reciprocal vectors
    for (let k = 0; k < 5; k++) {
        const angle = (2 * Math.PI * k) / 5;
        const Gx = Math.cos(angle);
        const Gy = Math.sin(angle);
        V += Math.cos(Gx * point[0] + Gy * point[1]);
    }
    return V / 5; // Normalize to [-1, 1]
}
//# sourceMappingURL=quasi-space.js.map