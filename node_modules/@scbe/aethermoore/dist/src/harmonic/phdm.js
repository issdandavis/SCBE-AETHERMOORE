"use strict";
/**
 * Polyhedral Hamiltonian Defense Manifold (PHDM)
 *
 * Topological intrusion detection using graph theory and differential geometry.
 * Traverses 16 canonical polyhedra in a Hamiltonian path, generating cryptographic
 * keys while monitoring for deviations from the expected geodesic curve in 6D space.
 *
 * @module harmonic/phdm
 */
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
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.PolyhedralHamiltonianDefenseManifold = exports.PHDMDeviationDetector = exports.CubicSpline6D = exports.computeCentroid = exports.distance6D = exports.PHDMHamiltonianPath = exports.CANONICAL_POLYHEDRA = exports.serializePolyhedron = exports.topologicalHash = exports.isValidTopology = exports.eulerCharacteristic = void 0;
const crypto = __importStar(require("crypto"));
/**
 * Compute Euler characteristic: χ = V - E + F = 2(1-g)
 */
function eulerCharacteristic(poly) {
    return poly.vertices - poly.edges + poly.faces;
}
exports.eulerCharacteristic = eulerCharacteristic;
/**
 * Verify topological validity: χ = 2(1-g)
 */
function isValidTopology(poly) {
    const chi = eulerCharacteristic(poly);
    const expected = 2 * (1 - poly.genus);
    return chi === expected;
}
exports.isValidTopology = isValidTopology;
/**
 * Generate topological hash (SHA256) for tamper detection
 */
function topologicalHash(poly) {
    const data = `${poly.name}:${poly.vertices}:${poly.edges}:${poly.faces}:${poly.genus}`;
    return crypto.createHash('sha256').update(data).digest('hex');
}
exports.topologicalHash = topologicalHash;
/**
 * Serialize polyhedron for HMAC input
 */
function serializePolyhedron(poly) {
    const chi = eulerCharacteristic(poly);
    const hash = topologicalHash(poly);
    const data = `${poly.name}|V=${poly.vertices}|E=${poly.edges}|F=${poly.faces}|χ=${chi}|g=${poly.genus}|hash=${hash}`;
    return Buffer.from(data, 'utf-8');
}
exports.serializePolyhedron = serializePolyhedron;
/**
 * 16 Canonical Polyhedra
 */
exports.CANONICAL_POLYHEDRA = [
    // Platonic Solids (5)
    { name: 'Tetrahedron', vertices: 4, edges: 6, faces: 4, genus: 0 },
    { name: 'Cube', vertices: 8, edges: 12, faces: 6, genus: 0 },
    { name: 'Octahedron', vertices: 6, edges: 12, faces: 8, genus: 0 },
    { name: 'Dodecahedron', vertices: 20, edges: 30, faces: 12, genus: 0 },
    { name: 'Icosahedron', vertices: 12, edges: 30, faces: 20, genus: 0 },
    // Archimedean Solids (3)
    { name: 'Truncated Tetrahedron', vertices: 12, edges: 18, faces: 8, genus: 0 },
    { name: 'Cuboctahedron', vertices: 12, edges: 24, faces: 14, genus: 0 },
    { name: 'Icosidodecahedron', vertices: 30, edges: 60, faces: 32, genus: 0 },
    // Kepler-Poinsot (2) - Non-convex star polyhedra
    { name: 'Small Stellated Dodecahedron', vertices: 12, edges: 30, faces: 12, genus: 4 },
    { name: 'Great Dodecahedron', vertices: 12, edges: 30, faces: 12, genus: 4 },
    // Toroidal (2) - genus 1
    { name: 'Szilassi', vertices: 7, edges: 21, faces: 14, genus: 1 },
    { name: 'Csaszar', vertices: 7, edges: 21, faces: 14, genus: 1 },
    // Johnson Solids (2)
    { name: 'Pentagonal Bipyramid', vertices: 7, edges: 15, faces: 10, genus: 0 },
    { name: 'Triangular Cupola', vertices: 9, edges: 15, faces: 8, genus: 0 },
    // Rhombic (2)
    { name: 'Rhombic Dodecahedron', vertices: 14, edges: 24, faces: 12, genus: 0 },
    { name: 'Bilinski Dodecahedron', vertices: 8, edges: 18, faces: 12, genus: 0 },
];
/**
 * Hamiltonian Path through polyhedra with HMAC chaining
 */
class PHDMHamiltonianPath {
    polyhedra;
    keys = [];
    constructor(polyhedra = exports.CANONICAL_POLYHEDRA) {
        this.polyhedra = polyhedra;
    }
    /**
     * Compute Hamiltonian path with sequential HMAC chaining
     * K_{i+1} = HMAC-SHA256(K_i, Serialize(P_i))
     */
    computePath(masterKey) {
        this.keys = [masterKey];
        for (let i = 0; i < this.polyhedra.length; i++) {
            const poly = this.polyhedra[i];
            const currentKey = this.keys[i];
            const polyData = serializePolyhedron(poly);
            // K_{i+1} = HMAC-SHA256(K_i, Serialize(P_i))
            const hmac = crypto.createHmac('sha256', currentKey);
            hmac.update(polyData);
            const nextKey = hmac.digest();
            this.keys.push(nextKey);
        }
        return this.keys;
    }
    /**
     * Verify path integrity
     */
    verifyPath(masterKey, expectedFinalKey) {
        const computedKeys = this.computePath(masterKey);
        const finalKey = computedKeys[computedKeys.length - 1];
        return crypto.timingSafeEqual(finalKey, expectedFinalKey);
    }
    /**
     * Get key at specific step
     */
    getKey(step) {
        if (step < 0 || step >= this.keys.length)
            return null;
        return this.keys[step];
    }
    /**
     * Get polyhedron at specific step
     */
    getPolyhedron(step) {
        if (step < 0 || step >= this.polyhedra.length)
            return null;
        return this.polyhedra[step];
    }
}
exports.PHDMHamiltonianPath = PHDMHamiltonianPath;
/**
 * Convert Point6D to array
 */
function point6DToArray(p) {
    return [p.x1, p.x2, p.x3, p.x4, p.x5, p.x6];
}
/**
 * Convert array to Point6D
 */
function arrayToPoint6D(arr) {
    return {
        x1: arr[0] || 0,
        x2: arr[1] || 0,
        x3: arr[2] || 0,
        x4: arr[3] || 0,
        x5: arr[4] || 0,
        x6: arr[5] || 0,
    };
}
/**
 * Euclidean distance in 6D space
 */
function distance6D(p1, p2) {
    const dx1 = p1.x1 - p2.x1;
    const dx2 = p1.x2 - p2.x2;
    const dx3 = p1.x3 - p2.x3;
    const dx4 = p1.x4 - p2.x4;
    const dx5 = p1.x5 - p2.x5;
    const dx6 = p1.x6 - p2.x6;
    return Math.sqrt(dx1 * dx1 + dx2 * dx2 + dx3 * dx3 + dx4 * dx4 + dx5 * dx5 + dx6 * dx6);
}
exports.distance6D = distance6D;
/**
 * Compute centroid of polyhedron in 6D space
 * Maps topological properties to 6D coordinates
 */
function computeCentroid(poly) {
    const chi = eulerCharacteristic(poly);
    return {
        x1: poly.vertices / 30.0, // Normalized vertices
        x2: poly.edges / 60.0, // Normalized edges
        x3: poly.faces / 32.0, // Normalized faces
        x4: chi / 2.0, // Euler characteristic
        x5: poly.genus, // Genus
        x6: Math.log(poly.vertices + poly.edges + poly.faces), // Complexity
    };
}
exports.computeCentroid = computeCentroid;
/**
 * Cubic spline interpolation in 6D
 */
class CubicSpline6D {
    points;
    t;
    constructor(points) {
        this.points = points;
        this.t = Array.from({ length: points.length }, (_, i) => i / (points.length - 1));
    }
    /**
     * Evaluate spline at parameter t ∈ [0, 1]
     */
    evaluate(t) {
        if (t <= 0)
            return this.points[0];
        if (t >= 1)
            return this.points[this.points.length - 1];
        // Find segment
        let i = 0;
        while (i < this.t.length - 1 && this.t[i + 1] < t) {
            i++;
        }
        // Local parameter within segment
        const t0 = this.t[i];
        const t1 = this.t[i + 1];
        const localT = (t - t0) / (t1 - t0);
        // Cubic Hermite interpolation
        const p0 = this.points[i];
        const p1 = this.points[i + 1];
        // Hermite basis functions
        const h00 = 2 * localT ** 3 - 3 * localT ** 2 + 1;
        const h10 = localT ** 3 - 2 * localT ** 2 + localT;
        const h01 = -2 * localT ** 3 + 3 * localT ** 2;
        const h11 = localT ** 3 - localT ** 2;
        // Tangents (finite differences)
        const m0 = this.getTangent(i);
        const m1 = this.getTangent(i + 1);
        return {
            x1: h00 * p0.x1 + h10 * m0.x1 + h01 * p1.x1 + h11 * m1.x1,
            x2: h00 * p0.x2 + h10 * m0.x2 + h01 * p1.x2 + h11 * m1.x2,
            x3: h00 * p0.x3 + h10 * m0.x3 + h01 * p1.x3 + h11 * m1.x3,
            x4: h00 * p0.x4 + h10 * m0.x4 + h01 * p1.x4 + h11 * m1.x4,
            x5: h00 * p0.x5 + h10 * m0.x5 + h01 * p1.x5 + h11 * m1.x5,
            x6: h00 * p0.x6 + h10 * m0.x6 + h01 * p1.x6 + h11 * m1.x6,
        };
    }
    /**
     * Compute tangent at point i using finite differences
     */
    getTangent(i) {
        if (i === 0) {
            // Forward difference
            return {
                x1: this.points[1].x1 - this.points[0].x1,
                x2: this.points[1].x2 - this.points[0].x2,
                x3: this.points[1].x3 - this.points[0].x3,
                x4: this.points[1].x4 - this.points[0].x4,
                x5: this.points[1].x5 - this.points[0].x5,
                x6: this.points[1].x6 - this.points[0].x6,
            };
        }
        else if (i === this.points.length - 1) {
            // Backward difference
            return {
                x1: this.points[i].x1 - this.points[i - 1].x1,
                x2: this.points[i].x2 - this.points[i - 1].x2,
                x3: this.points[i].x3 - this.points[i - 1].x3,
                x4: this.points[i].x4 - this.points[i - 1].x4,
                x5: this.points[i].x5 - this.points[i - 1].x5,
                x6: this.points[i].x6 - this.points[i - 1].x6,
            };
        }
        else {
            // Central difference
            return {
                x1: (this.points[i + 1].x1 - this.points[i - 1].x1) / 2,
                x2: (this.points[i + 1].x2 - this.points[i - 1].x2) / 2,
                x3: (this.points[i + 1].x3 - this.points[i - 1].x3) / 2,
                x4: (this.points[i + 1].x4 - this.points[i - 1].x4) / 2,
                x5: (this.points[i + 1].x5 - this.points[i - 1].x5) / 2,
                x6: (this.points[i + 1].x6 - this.points[i - 1].x6) / 2,
            };
        }
    }
    /**
     * Compute first derivative γ'(t)
     */
    derivative(t, h = 0.001) {
        const p1 = this.evaluate(t - h);
        const p2 = this.evaluate(t + h);
        return {
            x1: (p2.x1 - p1.x1) / (2 * h),
            x2: (p2.x2 - p1.x2) / (2 * h),
            x3: (p2.x3 - p1.x3) / (2 * h),
            x4: (p2.x4 - p1.x4) / (2 * h),
            x5: (p2.x5 - p1.x5) / (2 * h),
            x6: (p2.x6 - p1.x6) / (2 * h),
        };
    }
    /**
     * Compute second derivative γ''(t)
     */
    secondDerivative(t, h = 0.001) {
        const d1 = this.derivative(t - h, h);
        const d2 = this.derivative(t + h, h);
        return {
            x1: (d2.x1 - d1.x1) / (2 * h),
            x2: (d2.x2 - d1.x2) / (2 * h),
            x3: (d2.x3 - d1.x3) / (2 * h),
            x4: (d2.x4 - d1.x4) / (2 * h),
            x5: (d2.x5 - d1.x5) / (2 * h),
            x6: (d2.x6 - d1.x6) / (2 * h),
        };
    }
    /**
     * Compute curvature κ(t) = |γ''(t)| / |γ'(t)|²
     */
    curvature(t) {
        const d1 = this.derivative(t);
        const d2 = this.secondDerivative(t);
        const d1Mag = Math.sqrt(d1.x1 ** 2 + d1.x2 ** 2 + d1.x3 ** 2 + d1.x4 ** 2 + d1.x5 ** 2 + d1.x6 ** 2);
        const d2Mag = Math.sqrt(d2.x1 ** 2 + d2.x2 ** 2 + d2.x3 ** 2 + d2.x4 ** 2 + d2.x5 ** 2 + d2.x6 ** 2);
        if (d1Mag < 1e-10)
            return 0;
        return d2Mag / (d1Mag ** 2);
    }
}
exports.CubicSpline6D = CubicSpline6D;
class PHDMDeviationDetector {
    geodesic;
    snapThreshold;
    curvatureThreshold;
    deviationHistory = [];
    constructor(polyhedra = exports.CANONICAL_POLYHEDRA, snapThreshold = 0.1, curvatureThreshold = 0.5) {
        // Compute centroids for all polyhedra
        const centroids = polyhedra.map(computeCentroid);
        // Create geodesic curve through centroids
        this.geodesic = new CubicSpline6D(centroids);
        this.snapThreshold = snapThreshold;
        this.curvatureThreshold = curvatureThreshold;
    }
    /**
     * Detect intrusion at time t
     */
    detect(state, t) {
        // Expected position on geodesic
        const expected = this.geodesic.evaluate(t);
        // Deviation from geodesic
        const deviation = distance6D(state, expected);
        // Threat velocity (rate of deviation change)
        this.deviationHistory.push(deviation);
        if (this.deviationHistory.length > 10) {
            this.deviationHistory.shift();
        }
        const threatVelocity = this.deviationHistory.length > 1
            ? this.deviationHistory[this.deviationHistory.length - 1] -
                this.deviationHistory[this.deviationHistory.length - 2]
            : 0;
        // Curvature at current position
        const curvature = this.geodesic.curvature(t);
        // Intrusion detection
        const isIntrusion = deviation > this.snapThreshold ||
            curvature > this.curvatureThreshold;
        // 1-0 rhythm pattern (1=safe, 0=intrusion)
        const rhythmBit = isIntrusion ? '0' : '1';
        return {
            isIntrusion,
            deviation,
            threatVelocity,
            curvature,
            rhythmPattern: rhythmBit,
            timestamp: Date.now(),
        };
    }
    /**
     * Simulate attack scenarios
     */
    simulateAttack(attackType, intensity = 1.0) {
        const results = [];
        const steps = 16;
        for (let i = 0; i < steps; i++) {
            const t = i / (steps - 1);
            let state = this.geodesic.evaluate(t);
            // Apply attack
            switch (attackType) {
                case 'deviation':
                    // Add random noise
                    state.x1 += (Math.random() - 0.5) * intensity;
                    state.x2 += (Math.random() - 0.5) * intensity;
                    break;
                case 'skip':
                    // Skip a polyhedron (jump ahead)
                    if (i === 4) {
                        const tSkip = (i + 2) / (steps - 1);
                        state = this.geodesic.evaluate(tSkip);
                    }
                    break;
                case 'curvature':
                    // Manipulate path curvature
                    state.x3 += Math.sin(t * Math.PI * 4) * intensity;
                    state.x4 += Math.cos(t * Math.PI * 4) * intensity;
                    break;
            }
            results.push(this.detect(state, t));
        }
        return results;
    }
    /**
     * Generate full rhythm pattern from results
     */
    static getRhythmPattern(results) {
        return results.map(r => r.rhythmPattern).join('');
    }
}
exports.PHDMDeviationDetector = PHDMDeviationDetector;
/**
 * Complete PHDM system
 */
class PolyhedralHamiltonianDefenseManifold {
    path;
    detector;
    constructor(polyhedra = exports.CANONICAL_POLYHEDRA, snapThreshold = 0.1, curvatureThreshold = 0.5) {
        this.path = new PHDMHamiltonianPath(polyhedra);
        this.detector = new PHDMDeviationDetector(polyhedra, snapThreshold, curvatureThreshold);
    }
    /**
     * Initialize with master key
     */
    initialize(masterKey) {
        return this.path.computePath(masterKey);
    }
    /**
     * Monitor state at time t
     */
    monitor(state, t) {
        return this.detector.detect(state, t);
    }
    /**
     * Simulate attack
     */
    simulateAttack(attackType, intensity = 1.0) {
        return this.detector.simulateAttack(attackType, intensity);
    }
    /**
     * Get polyhedra
     */
    getPolyhedra() {
        return exports.CANONICAL_POLYHEDRA;
    }
}
exports.PolyhedralHamiltonianDefenseManifold = PolyhedralHamiltonianDefenseManifold;
//# sourceMappingURL=phdm.js.map