/**
 * @file wormholeTransport.ts
 * @module harmonic/wormholeTransport
 * @layer Layer 5, Layer 6, Layer 8
 * @component Wormhole Shortcut Transport
 * @version 1.0.0
 *
 * Einstein-Rosen bridge inspired shortcuts in hyperbolic space.
 * Enables "tunneling" between distant points in the Poincaré ball,
 * bypassing the exponentially growing geodesic paths near the boundary.
 *
 * A wormhole connects two "throat" points and provides O(1) transport
 * instead of traversing the full hyperbolic geodesic (which can be
 * exponentially long near the boundary).
 *
 * Key properties:
 * - Wormholes are bidirectional (symmetric throats)
 * - Each wormhole has a stability score based on trust vectors
 * - Transport through a wormhole preserves the immutable d_H metric
 *   (the shortcut is a topological feature, not a metric violation)
 * - Unstable wormholes collapse (decay to 0 stability over time)
 *
 * Use cases:
 * - Cross-realm agent communication (light ↔ shadow)
 * - Fast hyperpath routing in sparse octrees
 * - Fleet task delegation shortcuts
 */

const EPSILON = 1e-10;

/**
 * A wormhole connecting two points in hyperbolic space
 */
export interface Wormhole {
  /** Unique identifier */
  id: string;
  /** First throat position in Poincaré ball */
  throatA: number[];
  /** Second throat position in Poincaré ball */
  throatB: number[];
  /** Stability score ∈ (0, 1] — decays over time */
  stability: number;
  /** Creation timestamp (ms) */
  createdAt: number;
  /** Last traversal timestamp */
  lastTraversedAt: number;
  /** Half-life in seconds (how fast stability decays) */
  halfLife: number;
  /** Traversal count */
  traversals: number;
}

/**
 * Result of a wormhole transport
 */
export interface TransportResult {
  /** Destination point (the other throat) */
  destination: number[];
  /** Hyperbolic distance saved vs geodesic */
  distanceSaved: number;
  /** Wormhole stability at time of traversal */
  stabilityAtTraversal: number;
  /** Whether transport was successful */
  success: boolean;
}

function vecNorm(v: number[]): number {
  let sum = 0;
  for (const x of v) sum += x * x;
  return Math.sqrt(sum);
}

function vecSub(u: number[], v: number[]): number[] {
  return u.map((x, i) => x - v[i]);
}

function vecNormSq(v: number[]): number {
  let sum = 0;
  for (const x of v) sum += x * x;
  return sum;
}

function hyperbolicDist(u: number[], v: number[]): number {
  const diff = vecSub(u, v);
  const diffNormSq = vecNormSq(diff);
  const uFactor = Math.max(EPSILON, 1 - vecNormSq(u));
  const vFactor = Math.max(EPSILON, 1 - vecNormSq(v));
  const arg = 1 + (2 * diffNormSq) / (uFactor * vFactor);
  return Math.acosh(Math.max(1, arg));
}

/**
 * Wormhole network for managing shortcuts in hyperbolic space.
 */
export class WormholeNetwork {
  private wormholes: Map<string, Wormhole> = new Map();
  private nextId = 0;

  /**
   * Create a new wormhole between two points.
   *
   * @param throatA - First endpoint in Poincaré ball
   * @param throatB - Second endpoint in Poincaré ball
   * @param halfLife - Half-life in seconds (default: 300 = 5 min)
   * @returns The created wormhole
   */
  createWormhole(
    throatA: number[],
    throatB: number[],
    halfLife: number = 300
  ): Wormhole {
    const id = `wh-${this.nextId++}`;
    const now = Date.now();

    const wormhole: Wormhole = {
      id,
      throatA: [...throatA],
      throatB: [...throatB],
      stability: 1.0,
      createdAt: now,
      lastTraversedAt: now,
      halfLife,
      traversals: 0,
    };

    this.wormholes.set(id, wormhole);
    return wormhole;
  }

  /**
   * Get current stability of a wormhole (exponential decay).
   *
   * stability(t) = e^(-ln(2) · Δt / halfLife)
   *
   * @param wormhole - The wormhole
   * @param now - Current timestamp
   * @returns Current stability ∈ (0, 1]
   */
  getStability(wormhole: Wormhole, now: number = Date.now()): number {
    const deltaSeconds = (now - wormhole.createdAt) / 1000;
    return Math.exp(-Math.LN2 * deltaSeconds / wormhole.halfLife);
  }

  /**
   * Find the nearest wormhole throat to a given point.
   *
   * @param point - Query point in Poincaré ball
   * @param minStability - Minimum stability threshold (default: 0.1)
   * @param now - Current timestamp
   * @returns Nearest wormhole and which throat is closer, or null
   */
  findNearest(
    point: number[],
    minStability: number = 0.1,
    now: number = Date.now()
  ): { wormhole: Wormhole; throat: 'A' | 'B'; distance: number } | null {
    let nearest: { wormhole: Wormhole; throat: 'A' | 'B'; distance: number } | null = null;

    for (const wh of this.wormholes.values()) {
      const stability = this.getStability(wh, now);
      if (stability < minStability) continue;

      const distA = hyperbolicDist(point, wh.throatA);
      const distB = hyperbolicDist(point, wh.throatB);

      const closer = distA <= distB ? 'A' : 'B';
      const closerDist = Math.min(distA, distB);

      if (!nearest || closerDist < nearest.distance) {
        nearest = { wormhole: wh, throat: closer as 'A' | 'B', distance: closerDist };
      }
    }

    return nearest;
  }

  /**
   * Transport a point through a wormhole.
   *
   * If the point is near throat A, it emerges at throat B (and vice versa).
   * The transport preserves the topological invariant: d_H through the wormhole
   * is the sum of distances to each throat (not the full geodesic).
   *
   * @param point - Source point
   * @param wormholeId - Wormhole to traverse
   * @param now - Current timestamp
   * @returns Transport result
   */
  transport(
    point: number[],
    wormholeId: string,
    now: number = Date.now()
  ): TransportResult {
    const wh = this.wormholes.get(wormholeId);
    if (!wh) {
      return { destination: point, distanceSaved: 0, stabilityAtTraversal: 0, success: false };
    }

    const stability = this.getStability(wh, now);
    if (stability < 0.05) {
      // Wormhole has collapsed
      this.wormholes.delete(wormholeId);
      return { destination: point, distanceSaved: 0, stabilityAtTraversal: stability, success: false };
    }

    // Determine which throat is closer
    const distA = hyperbolicDist(point, wh.throatA);
    const distB = hyperbolicDist(point, wh.throatB);

    const entryThroat = distA <= distB ? wh.throatA : wh.throatB;
    const exitThroat = distA <= distB ? wh.throatB : wh.throatA;
    const entryDist = Math.min(distA, distB);

    // Direct geodesic distance (expensive path)
    const directDist = hyperbolicDist(point, exitThroat);

    // Wormhole path: distance to entry throat + 0 (through wormhole) = just entry distance
    const distanceSaved = Math.max(0, directDist - entryDist);

    // Update traversal stats
    wh.lastTraversedAt = now;
    wh.traversals += 1;

    return {
      destination: [...exitThroat],
      distanceSaved,
      stabilityAtTraversal: stability,
      success: true,
    };
  }

  /**
   * Compute the effective distance between two points,
   * considering available wormhole shortcuts.
   *
   * effectiveDist = min(directDist, min_wh(d(point, throatEntry) + d(throatExit, target)))
   *
   * @param source - Source point
   * @param target - Target point
   * @param now - Current timestamp
   * @returns Effective distance (potentially much shorter than geodesic)
   */
  effectiveDistance(
    source: number[],
    target: number[],
    now: number = Date.now()
  ): number {
    const directDist = hyperbolicDist(source, target);
    let bestDist = directDist;

    for (const wh of this.wormholes.values()) {
      const stability = this.getStability(wh, now);
      if (stability < 0.1) continue;

      // Try A→B direction
      const viaAB = hyperbolicDist(source, wh.throatA) + hyperbolicDist(wh.throatB, target);
      // Try B→A direction
      const viaBA = hyperbolicDist(source, wh.throatB) + hyperbolicDist(wh.throatA, target);

      bestDist = Math.min(bestDist, viaAB, viaBA);
    }

    return bestDist;
  }

  /**
   * Prune collapsed wormholes (stability below threshold).
   *
   * @param minStability - Minimum stability to keep (default: 0.05)
   * @param now - Current timestamp
   * @returns Number of wormholes pruned
   */
  prune(minStability: number = 0.05, now: number = Date.now()): number {
    let pruned = 0;
    for (const [id, wh] of this.wormholes) {
      if (this.getStability(wh, now) < minStability) {
        this.wormholes.delete(id);
        pruned++;
      }
    }
    return pruned;
  }

  /**
   * Get all active wormholes.
   */
  getAll(): Wormhole[] {
    return Array.from(this.wormholes.values());
  }

  /**
   * Get the total number of wormholes.
   */
  get size(): number {
    return this.wormholes.size;
  }
}
