"use strict";
/**
 * SCBE Quasicrystal Lattice Module
 *
 * Implements quasicrystalline structures for the SCBE pipeline:
 * - Penrose tiling (5-fold symmetry)
 * - Fibonacci lattice
 * - Ammann-Beenker tiling (8-fold symmetry)
 * - Diffraction pattern analysis
 *
 * Quasicrystals are aperiodic but ordered structures that provide
 * unique mathematical properties useful for cryptographic applications.
 *
 * Key Properties:
 * - Self-similar at multiple scales
 * - Sharp diffraction peaks despite aperiodicity
 * - Golden ratio relationships (φ = (1+√5)/2)
 * - Higher-dimensional projections
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.defaultQCLattice = exports.QCLatticeProvider = exports.quasicrystalHash = exports.quasicrystalPotential = exports.nearestQCVertex = exports.scbeToQuasicrystal = exports.checkRotationalSymmetry = exports.diffractionPattern = exports.quasicrystal4to2 = exports.quasicrystal5to2 = exports.cutAndProject2D = exports.ammannBeenkerRhombus = exports.ammannBeenkerSquare = exports.penroseToLattice = exports.penroseTiling = exports.penroseInitial = exports.penroseDeflate = exports.penroseRhombus = exports.fibonacci2D = exports.fibonacci1D = exports.fibonacciWord = exports.fibonacciSequence = exports.PI_4 = exports.PI_5 = exports.SILVER_RATIO = exports.PHI_INV = exports.PHI = void 0;
// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
/** Golden ratio φ = (1+√5)/2 ≈ 1.618033988749895 */
exports.PHI = (1 + Math.sqrt(5)) / 2;
/** Inverse golden ratio 1/φ = φ - 1 ≈ 0.618033988749895 */
exports.PHI_INV = exports.PHI - 1;
/** Silver ratio δ = 1 + √2 ≈ 2.414213562373095 */
exports.SILVER_RATIO = 1 + Math.sqrt(2);
/** π/5 for 5-fold symmetry */
exports.PI_5 = Math.PI / 5;
/** π/4 for 8-fold symmetry */
exports.PI_4 = Math.PI / 4;
// ═══════════════════════════════════════════════════════════════
// Fibonacci Lattice
// ═══════════════════════════════════════════════════════════════
/**
 * Generate Fibonacci numbers up to n
 */
function fibonacciSequence(n) {
    const fib = [0, 1];
    for (let i = 2; i < n; i++) {
        fib[i] = fib[i - 1] + fib[i - 2];
    }
    return fib.slice(0, n);
}
exports.fibonacciSequence = fibonacciSequence;
/**
 * Generate Fibonacci word (S -> SL, L -> S)
 * Starting with S, produces: S, SL, SLS, SLSSL, SLSSLSLS, ...
 */
function fibonacciWord(generations) {
    let S = 'S';
    let L = 'L';
    for (let i = 0; i < generations; i++) {
        const newS = S + L;
        const newL = S;
        S = newS;
        L = newL;
    }
    return S;
}
exports.fibonacciWord = fibonacciWord;
/**
 * Generate 1D Fibonacci quasilattice
 *
 * Points are placed according to Fibonacci word:
 * S -> short interval (1)
 * L -> long interval (φ)
 */
function fibonacci1D(generations, a = 1) {
    const word = fibonacciWord(generations);
    const points = [0];
    let x = 0;
    for (const char of word) {
        const step = char === 'S' ? a : a * exports.PHI;
        x += step;
        points.push(x);
    }
    return points;
}
exports.fibonacci1D = fibonacci1D;
/**
 * Generate 2D Fibonacci lattice
 * Uses two 1D Fibonacci lattices rotated by golden angle
 */
function fibonacci2D(n, a = 1) {
    const points = [];
    const goldenAngle = 2 * Math.PI / (exports.PHI * exports.PHI);
    for (let i = 0; i < n; i++) {
        // Sunflower pattern using golden angle
        const r = a * Math.sqrt(i);
        const theta = i * goldenAngle;
        const x = r * Math.cos(theta);
        const y = r * Math.sin(theta);
        points.push({
            position: [x, y],
            index: [i, 0],
            weight: 1 / (1 + i * 0.01), // Decreasing weight
        });
    }
    return points;
}
exports.fibonacci2D = fibonacci2D;
// ═══════════════════════════════════════════════════════════════
// Penrose Tiling
// ═══════════════════════════════════════════════════════════════
/**
 * Generate vertices for a Penrose rhombus (P3 tiling)
 *
 * Thick rhombus: angles 72° and 108°
 * Thin rhombus: angles 36° and 144°
 */
function penroseRhombus(center, angle, size, isThick) {
    const halfAngle = isThick ? exports.PI_5 : exports.PI_5 / 2;
    const vertices = [];
    const directions = [angle, angle + halfAngle, angle + Math.PI, angle + Math.PI + halfAngle];
    for (let i = 0; i < 4; i++) {
        const r = i % 2 === 0 ? size : size * (isThick ? exports.PHI : exports.PHI_INV);
        vertices.push([
            center[0] + r * Math.cos(directions[i]),
            center[1] + r * Math.sin(directions[i]),
        ]);
    }
    return vertices;
}
exports.penroseRhombus = penroseRhombus;
/**
 * Penrose substitution rules
 * Deflates tiles into smaller tiles
 */
function penroseDeflate(tiles) {
    const newTiles = [];
    for (const tile of tiles) {
        if (tile.type === 'thick_rhombus') {
            // Thick rhombus -> 2 thick + 1 thin
            const scale = exports.PHI_INV;
            const [A, B, C, D] = tile.vertices;
            // Calculate midpoints and new vertices
            const E = lerpPoint(A, C, exports.PHI_INV);
            const F = lerpPoint(B, D, exports.PHI_INV);
            newTiles.push(createTile('thick_rhombus', [A, E, B, lerpPoint(A, B, 0.5)], tile.angle), createTile('thick_rhombus', [E, C, D, F], tile.angle + exports.PI_5), createTile('thin_rhombus', [E, F, B, lerpPoint(B, E, 0.5)], tile.angle - exports.PI_5));
        }
        else if (tile.type === 'thin_rhombus') {
            // Thin rhombus -> 1 thick + 1 thin
            const [A, B, C, D] = tile.vertices;
            const E = lerpPoint(A, C, exports.PHI_INV);
            newTiles.push(createTile('thick_rhombus', [A, E, B, lerpPoint(A, B, 0.5)], tile.angle), createTile('thin_rhombus', [E, C, D, lerpPoint(C, D, 0.5)], tile.angle + exports.PI_5));
        }
    }
    return newTiles;
}
exports.penroseDeflate = penroseDeflate;
/**
 * Generate initial Penrose tiles (decagon)
 */
function penroseInitial(center, size) {
    const tiles = [];
    // Create 5 thick rhombi forming a decagon
    for (let i = 0; i < 5; i++) {
        const angle = i * 2 * exports.PI_5;
        const vertices = penroseRhombus(center, angle, size, true);
        tiles.push(createTile('thick_rhombus', vertices, angle));
    }
    return tiles;
}
exports.penroseInitial = penroseInitial;
/**
 * Generate Penrose tiling with n deflation steps
 */
function penroseTiling(center, size, generations) {
    let tiles = penroseInitial(center, size);
    for (let i = 0; i < generations; i++) {
        tiles = penroseDeflate(tiles);
    }
    return tiles;
}
exports.penroseTiling = penroseTiling;
/**
 * Extract lattice points from Penrose tiling
 */
function penroseToLattice(tiles) {
    const pointMap = new Map();
    tiles.forEach((tile, tileIdx) => {
        tile.vertices.forEach((v, vIdx) => {
            const key = `${v[0].toFixed(8)},${v[1].toFixed(8)}`;
            if (!pointMap.has(key)) {
                pointMap.set(key, {
                    position: v,
                    index: [tileIdx, vIdx],
                    weight: tile.type === 'thick_rhombus' ? exports.PHI : 1,
                });
            }
        });
    });
    return Array.from(pointMap.values());
}
exports.penroseToLattice = penroseToLattice;
// ═══════════════════════════════════════════════════════════════
// Ammann-Beenker Tiling (8-fold symmetry)
// ═══════════════════════════════════════════════════════════════
/**
 * Generate Ammann-Beenker square tile
 */
function ammannBeenkerSquare(center, angle, size) {
    const vertices = [];
    for (let i = 0; i < 4; i++) {
        const theta = angle + i * Math.PI / 2;
        vertices.push([
            center[0] + size * Math.cos(theta),
            center[1] + size * Math.sin(theta),
        ]);
    }
    return vertices;
}
exports.ammannBeenkerSquare = ammannBeenkerSquare;
/**
 * Generate Ammann-Beenker rhombus (45° acute angle)
 */
function ammannBeenkerRhombus(center, angle, size) {
    const vertices = [];
    const halfAngle = Math.PI / 8;
    const r1 = size;
    const r2 = size / Math.cos(Math.PI / 8);
    for (let i = 0; i < 4; i++) {
        const isLong = i % 2 === 1;
        const theta = angle + i * Math.PI / 2 + (isLong ? halfAngle : 0);
        const r = isLong ? r2 : r1;
        vertices.push([
            center[0] + r * Math.cos(theta),
            center[1] + r * Math.sin(theta),
        ]);
    }
    return vertices;
}
exports.ammannBeenkerRhombus = ammannBeenkerRhombus;
// ═══════════════════════════════════════════════════════════════
// Cut-and-Project Method
// ═══════════════════════════════════════════════════════════════
/**
 * Generate quasicrystal via cut-and-project method
 *
 * Projects points from a higher-dimensional lattice (Z^n)
 * onto a lower-dimensional irrational subspace.
 */
function cutAndProject2D(nDimensions, range, windowRadius = 1) {
    const points = [];
    // Projection matrix rows (irrational slopes)
    const projMatrix = [];
    for (let d = 0; d < 2; d++) {
        projMatrix[d] = [];
        for (let i = 0; i < nDimensions; i++) {
            projMatrix[d][i] = Math.cos(2 * Math.PI * (d * nDimensions + i + 1) / (2 * nDimensions));
        }
    }
    // Internal space projection
    const intMatrix = [];
    for (let d = 0; d < nDimensions - 2; d++) {
        intMatrix[d] = [];
        for (let i = 0; i < nDimensions; i++) {
            intMatrix[d][i] = Math.sin(2 * Math.PI * (d * nDimensions + i + 1) / (2 * nDimensions));
        }
    }
    // Generate points from lattice
    const generateLattice = (indices, dim) => {
        if (dim === nDimensions) {
            // Check if point is in acceptance window
            let inWindow = true;
            for (let d = 0; d < nDimensions - 2 && inWindow; d++) {
                let coord = 0;
                for (let i = 0; i < nDimensions; i++) {
                    coord += intMatrix[d][i] * indices[i];
                }
                if (Math.abs(coord) > windowRadius) {
                    inWindow = false;
                }
            }
            if (inWindow) {
                // Project to physical space
                const pos = [0, 0];
                for (let d = 0; d < 2; d++) {
                    for (let i = 0; i < nDimensions; i++) {
                        pos[d] += projMatrix[d][i] * indices[i];
                    }
                }
                points.push({
                    position: pos,
                    index: [indices[0], indices[1]],
                    weight: 1 / (1 + norm2(indices) * 0.01),
                });
            }
            return;
        }
        for (let i = -range; i <= range; i++) {
            generateLattice([...indices, i], dim + 1);
        }
    };
    generateLattice([], 0);
    return points;
}
exports.cutAndProject2D = cutAndProject2D;
/**
 * Generate 5D -> 2D quasicrystal (Penrose-like)
 */
function quasicrystal5to2(range, windowRadius = 1) {
    return cutAndProject2D(5, range, windowRadius);
}
exports.quasicrystal5to2 = quasicrystal5to2;
/**
 * Generate 4D -> 2D quasicrystal (Ammann-Beenker-like)
 */
function quasicrystal4to2(range, windowRadius = 1) {
    return cutAndProject2D(4, range, windowRadius);
}
exports.quasicrystal4to2 = quasicrystal4to2;
// ═══════════════════════════════════════════════════════════════
// Diffraction Pattern Analysis
// ═══════════════════════════════════════════════════════════════
/**
 * Calculate diffraction pattern for a set of lattice points
 *
 * The structure factor is: S(k) = |Σⱼ exp(i k·rⱼ)|²
 */
function diffractionPattern(points, kRange, resolution) {
    const peaks = [];
    const dk = kRange / resolution;
    for (let kx = -resolution; kx <= resolution; kx++) {
        for (let ky = -resolution; ky <= resolution; ky++) {
            const k = [kx * dk, ky * dk];
            // Calculate structure factor
            let re = 0, im = 0;
            for (const p of points) {
                const phase = k[0] * p.position[0] + k[1] * p.position[1];
                re += p.weight * Math.cos(phase);
                im += p.weight * Math.sin(phase);
            }
            const intensity = re * re + im * im;
            if (intensity > 0.1 * points.length) {
                peaks.push({
                    k,
                    intensity,
                    order: Math.round(Math.sqrt(kx * kx + ky * ky)),
                });
            }
        }
    }
    // Sort by intensity
    peaks.sort((a, b) => b.intensity - a.intensity);
    return peaks.slice(0, 100); // Top 100 peaks
}
exports.diffractionPattern = diffractionPattern;
/**
 * Check for n-fold rotational symmetry in diffraction pattern
 */
function checkRotationalSymmetry(peaks, n, tolerance = 0.1) {
    const angleStep = 2 * Math.PI / n;
    let matchScore = 0;
    let totalScore = 0;
    for (const peak of peaks) {
        const peakAngle = Math.atan2(peak.k[1], peak.k[0]);
        const peakRadius = Math.sqrt(peak.k[0] ** 2 + peak.k[1] ** 2);
        // Check for matching peak at rotated positions
        for (let rot = 1; rot < n; rot++) {
            const targetAngle = peakAngle + rot * angleStep;
            const targetK = [
                peakRadius * Math.cos(targetAngle),
                peakRadius * Math.sin(targetAngle),
            ];
            // Find closest peak
            let minDist = Infinity;
            let matchIntensity = 0;
            for (const other of peaks) {
                const dist = Math.sqrt((other.k[0] - targetK[0]) ** 2 + (other.k[1] - targetK[1]) ** 2);
                if (dist < minDist) {
                    minDist = dist;
                    matchIntensity = other.intensity;
                }
            }
            totalScore += peak.intensity;
            if (minDist < tolerance * peakRadius) {
                matchScore += Math.min(peak.intensity, matchIntensity);
            }
        }
    }
    const score = totalScore > 0 ? matchScore / totalScore : 0;
    return { hasSymmetry: score > 0.8, score };
}
exports.checkRotationalSymmetry = checkRotationalSymmetry;
// ═══════════════════════════════════════════════════════════════
// Integration with SCBE Pipeline
// ═══════════════════════════════════════════════════════════════
/**
 * Convert 6D SCBE vector to quasicrystal position
 * Uses golden ratio projection
 */
function scbeToQuasicrystal(v) {
    // Project 6D to 2D using icosahedral projection
    const projMatrix = [
        [1, exports.PHI, 0, exports.PHI, -1, 0],
        [exports.PHI, 0, 1, 0, exports.PHI, -1],
    ];
    const pos = [0, 0];
    for (let d = 0; d < 2; d++) {
        for (let i = 0; i < 6; i++) {
            pos[d] += projMatrix[d][i] * v[i] / Math.sqrt(2 + exports.PHI);
        }
    }
    return {
        position: pos,
        index: [0, 0],
        weight: norm6(v),
    };
}
exports.scbeToQuasicrystal = scbeToQuasicrystal;
/**
 * Find nearest quasicrystal vertex to a point
 */
function nearestQCVertex(point, lattice) {
    let minDist = Infinity;
    let nearest = lattice[0];
    for (const lp of lattice) {
        const dist = Math.sqrt((point[0] - lp.position[0]) ** 2 +
            (point[1] - lp.position[1]) ** 2);
        if (dist < minDist) {
            minDist = dist;
            nearest = lp;
        }
    }
    return { nearest, distance: minDist };
}
exports.nearestQCVertex = nearestQCVertex;
/**
 * Calculate quasicrystal potential energy
 * Used for multi-well potential in SCBE Layer 8
 */
function quasicrystalPotential(position, lattice, sigma = 0.5) {
    let V = 0;
    for (const lp of lattice) {
        const dx = position[0] - lp.position[0];
        const dy = position[1] - lp.position[1];
        const distSq = dx * dx + dy * dy;
        V += lp.weight * Math.exp(-distSq / (2 * sigma * sigma));
    }
    return V;
}
exports.quasicrystalPotential = quasicrystalPotential;
/**
 * Quasicrystal-based hash function
 * Maps input bytes to quasicrystal lattice positions
 */
function quasicrystalHash(input, lattice) {
    const path = [];
    let current = [0, 0];
    for (const byte of input) {
        // Map byte to angle and radius
        const angle = (byte / 256) * 2 * Math.PI;
        const radius = ((byte % 16) + 1) * 0.1;
        // Move in quasicrystal space
        current = [
            current[0] + radius * Math.cos(angle) * exports.PHI,
            current[1] + radius * Math.sin(angle),
        ];
        // Snap to nearest lattice point
        const { nearest } = nearestQCVertex(current, lattice);
        path.push(nearest);
        current = nearest.position;
    }
    return { hash: current, path };
}
exports.quasicrystalHash = quasicrystalHash;
// ═══════════════════════════════════════════════════════════════
// Helper Functions
// ═══════════════════════════════════════════════════════════════
function lerpPoint(a, b, t) {
    return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])];
}
function createTile(type, vertices, angle) {
    const center = [
        vertices.reduce((sum, v) => sum + v[0], 0) / vertices.length,
        vertices.reduce((sum, v) => sum + v[1], 0) / vertices.length,
    ];
    return { type, vertices, center, angle };
}
function norm2(v) {
    return Math.sqrt(v.reduce((sum, x) => sum + x * x, 0));
}
function norm6(v) {
    return Math.sqrt(v.reduce((sum, x) => sum + x * x, 0));
}
// ═══════════════════════════════════════════════════════════════
// QC Lattice Provider for SCBE Integration
// ═══════════════════════════════════════════════════════════════
/**
 * Quasicrystal Lattice Provider
 */
class QCLatticeProvider {
    lattice = [];
    config;
    constructor(config = {}) {
        this.config = {
            a: config.a ?? 1.0,
            generations: config.generations ?? 4,
            resolution: config.resolution ?? 32,
        };
        this.generateLattice();
    }
    /**
     * Generate the quasicrystal lattice
     */
    generateLattice() {
        const tiles = penroseTiling([0, 0], this.config.a, this.config.generations);
        this.lattice = penroseToLattice(tiles);
    }
    /**
     * Get all lattice points
     */
    getPoints() {
        return this.lattice;
    }
    /**
     * Map SCBE 6D vector to quasicrystal position
     */
    mapVector(v) {
        return scbeToQuasicrystal(v);
    }
    /**
     * Find nearest vertex
     */
    findNearest(point) {
        return nearestQCVertex(point, this.lattice);
    }
    /**
     * Calculate potential at position
     */
    potential(position, sigma) {
        return quasicrystalPotential(position, this.lattice, sigma);
    }
    /**
     * Compute diffraction pattern
     */
    diffraction(kRange) {
        return diffractionPattern(this.lattice, kRange, this.config.resolution);
    }
    /**
     * Check rotational symmetry
     */
    checkSymmetry(n) {
        const peaks = this.diffraction(10);
        return checkRotationalSymmetry(peaks, n);
    }
    /**
     * Hash input using quasicrystal walk
     */
    hash(input) {
        return quasicrystalHash(input, this.lattice);
    }
}
exports.QCLatticeProvider = QCLatticeProvider;
/**
 * Default QC lattice provider instance
 */
exports.defaultQCLattice = new QCLatticeProvider();
//# sourceMappingURL=qcLattice.js.map