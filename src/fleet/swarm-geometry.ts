/**
 * @file swarm-geometry.ts
 * @module fleet/swarm-geometry
 * @layer L5, L12, L13
 * @component Swarm Geometry Layer — Centroidal Field
 * @version 3.2.4
 *
 * Formalizes spatial swarm dynamics as a centroidal force field.
 *
 * Motion equation per robot i:
 *   v_i = α·Cohesion(x_i, C) + β·Separation(x_i, neighbors) + γ·GoalVector + δ·DriftBounded
 *
 * Where:
 *   α, β = Law (fixed bounds, never exceed caps)
 *   γ   = Mission parameter (goal-directed)
 *   δ   = Flux (bounded exploration, see governed-drift.ts)
 *
 * @axiom Unitarity — Force magnitudes are norm-preserving under composition
 * @axiom Locality — Separation only acts within coupling radius
 */

/**
 * 2D/3D position vector
 */
export interface Vec {
  x: number;
  y: number;
  z: number;
}

/**
 * Force weight configuration — the "laws" of the swarm
 */
export interface ForceWeights {
  /** Cohesion weight α — attraction toward centroid */
  alpha: number;
  /** Separation weight β — repulsion from neighbors */
  beta: number;
  /** Goal weight γ — mission-directed force */
  gamma: number;
  /** Drift weight δ — bounded exploration */
  delta: number;
}

/**
 * Hard caps on force weights (law — never exceeded)
 */
export const FORCE_WEIGHT_CAPS: Readonly<ForceWeights> = {
  alpha: 2.0,
  beta: 3.0,
  gamma: 2.5,
  delta: 1.0,
};

/**
 * Default force weights (conservative starting point)
 */
export const DEFAULT_FORCE_WEIGHTS: Readonly<ForceWeights> = {
  alpha: 1.0,
  beta: 1.5,
  gamma: 1.0,
  delta: 0.3,
};

/**
 * Swarm geometry configuration
 */
export interface SwarmGeometryConfig {
  /** Force weights */
  weights: ForceWeights;
  /** Separation radius — agents within this distance trigger repulsion */
  separationRadius: number;
  /** Coupling radius — agents beyond this distance are invisible */
  couplingRadius: number;
  /** Maximum velocity magnitude (hard cap) */
  maxSpeed: number;
  /** Minimum separation distance (hard invariant — never violated) */
  minSeparation: number;
  /** Time step for integration */
  dt: number;
}

export const DEFAULT_GEOMETRY_CONFIG: Readonly<SwarmGeometryConfig> = {
  weights: { ...DEFAULT_FORCE_WEIGHTS },
  separationRadius: 2.0,
  couplingRadius: 10.0,
  maxSpeed: 5.0,
  minSeparation: 0.5,
  dt: 0.1,
};

/**
 * Per-robot spatial state
 */
export interface RobotSpatialState {
  id: string;
  position: Vec;
  velocity: Vec;
  /** Goal position (mission target) */
  goal: Vec | null;
  /** Current drift vector (set by GovernedDrift) */
  drift: Vec;
  /** Trust score [0,1] — used for weighting */
  trust: number;
}

/**
 * Computed force breakdown for telemetry/debugging
 */
export interface ForceBreakdown {
  cohesion: Vec;
  separation: Vec;
  goalForce: Vec;
  driftForce: Vec;
  resultant: Vec;
  /** Resultant magnitude before speed cap */
  rawMagnitude: number;
  /** Was speed-capped? */
  capped: boolean;
}

// ──────────────── Vector Math ────────────────

export function vecAdd(a: Vec, b: Vec): Vec {
  return { x: a.x + b.x, y: a.y + b.y, z: a.z + b.z };
}

export function vecSub(a: Vec, b: Vec): Vec {
  return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
}

export function vecScale(v: Vec, s: number): Vec {
  return { x: v.x * s, y: v.y * s, z: v.z * s };
}

export function vecMag(v: Vec): number {
  return Math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
}

export function vecNormalize(v: Vec): Vec {
  const m = vecMag(v);
  if (m < 1e-12) return { x: 0, y: 0, z: 0 };
  return vecScale(v, 1 / m);
}

export function vecDist(a: Vec, b: Vec): number {
  return vecMag(vecSub(a, b));
}

export const VEC_ZERO: Readonly<Vec> = { x: 0, y: 0, z: 0 };

// ──────────────── Core Geometry Engine ────────────────

/**
 * SwarmGeometry — centroidal force field for spatial swarm coordination.
 *
 * Computes forces per-robot and integrates motion with hard safety invariants.
 */
export class SwarmGeometry {
  private config: SwarmGeometryConfig;
  private robots: Map<string, RobotSpatialState> = new Map();
  /** No-go zones: circles/spheres that robots must not enter */
  private noGoZones: Array<{ center: Vec; radius: number }> = [];

  constructor(config: Partial<SwarmGeometryConfig> = {}) {
    this.config = {
      ...DEFAULT_GEOMETRY_CONFIG,
      ...config,
      weights: {
        ...DEFAULT_GEOMETRY_CONFIG.weights,
        ...config.weights,
      },
    };
    // Enforce weight caps at construction
    this.enforceWeightCaps();
  }

  /** Clamp weights to hard caps — law, never violated */
  private enforceWeightCaps(): void {
    const w = this.config.weights;
    w.alpha = Math.min(Math.abs(w.alpha), FORCE_WEIGHT_CAPS.alpha);
    w.beta = Math.min(Math.abs(w.beta), FORCE_WEIGHT_CAPS.beta);
    w.gamma = Math.min(Math.abs(w.gamma), FORCE_WEIGHT_CAPS.gamma);
    w.delta = Math.min(Math.abs(w.delta), FORCE_WEIGHT_CAPS.delta);
  }

  // ── Robot Management ──

  public addRobot(state: RobotSpatialState): void {
    this.robots.set(state.id, { ...state });
  }

  public removeRobot(id: string): boolean {
    return this.robots.delete(id);
  }

  public getRobot(id: string): RobotSpatialState | undefined {
    return this.robots.get(id);
  }

  public getRobots(): RobotSpatialState[] {
    return Array.from(this.robots.values());
  }

  public getRobotCount(): number {
    return this.robots.size;
  }

  // ── No-Go Zones ──

  public addNoGoZone(center: Vec, radius: number): void {
    this.noGoZones.push({ center, radius });
  }

  public clearNoGoZones(): void {
    this.noGoZones.length = 0;
  }

  // ── Centroid ──

  /**
   * Compute global centroid C = (1/N) Σ x_i
   * Trust-weighted: C = Σ(τ_i · x_i) / Σ(τ_i)
   */
  public computeCentroid(): Vec {
    const bots = this.getRobots();
    if (bots.length === 0) return { ...VEC_ZERO };

    let totalTrust = 0;
    let cx = 0,
      cy = 0,
      cz = 0;

    for (const bot of bots) {
      const t = Math.max(bot.trust, 1e-10);
      cx += bot.position.x * t;
      cy += bot.position.y * t;
      cz += bot.position.z * t;
      totalTrust += t;
    }

    return {
      x: cx / totalTrust,
      y: cy / totalTrust,
      z: cz / totalTrust,
    };
  }

  // ── Force Computation ──

  /**
   * Compute cohesion force: attraction toward centroid C.
   * F_cohesion = normalize(C - x_i) · ||C - x_i||
   * Linear attraction — stronger the further away.
   */
  public computeCohesion(robot: RobotSpatialState, centroid: Vec): Vec {
    const diff = vecSub(centroid, robot.position);
    const dist = vecMag(diff);
    if (dist < 1e-12) return { ...VEC_ZERO };
    // Linear scaling with distance
    return vecScale(vecNormalize(diff), dist);
  }

  /**
   * Compute separation force: repulsion from neighbors within separation radius.
   * F_separation = Σ_j (normalize(x_i - x_j) / ||x_i - x_j||)
   * Inverse-distance repulsion — stronger when closer.
   */
  public computeSeparation(robot: RobotSpatialState): Vec {
    let fx = 0,
      fy = 0,
      fz = 0;

    for (const other of this.robots.values()) {
      if (other.id === robot.id) continue;

      const dist = vecDist(robot.position, other.position);
      if (dist < 1e-12 || dist > this.config.separationRadius) continue;

      // Inverse-distance repulsion (stronger when closer)
      const diff = vecSub(robot.position, other.position);
      const norm = vecNormalize(diff);
      const strength = 1.0 / dist;

      fx += norm.x * strength;
      fy += norm.y * strength;
      fz += norm.z * strength;
    }

    return { x: fx, y: fy, z: fz };
  }

  /**
   * Compute goal force: attraction toward mission target.
   * F_goal = normalize(goal - x_i) · min(||goal - x_i||, 1)
   * Capped linear attraction.
   */
  public computeGoalForce(robot: RobotSpatialState): Vec {
    if (!robot.goal) return { ...VEC_ZERO };

    const diff = vecSub(robot.goal, robot.position);
    const dist = vecMag(diff);
    if (dist < 1e-12) return { ...VEC_ZERO };

    // Capped at magnitude 1 to prevent goal-dominance
    const strength = Math.min(dist, 1.0);
    return vecScale(vecNormalize(diff), strength);
  }

  /**
   * Get drift force (already computed externally by GovernedDrift).
   * Just passes through with δ weight applied.
   */
  public computeDriftForce(robot: RobotSpatialState): Vec {
    return { ...robot.drift };
  }

  /**
   * Compute full force breakdown for a single robot.
   *
   * v_i = α·Cohesion(x_i, C) + β·Separation(x_i, neighbors) + γ·GoalVector + δ·DriftBounded
   */
  public computeForces(robotId: string): ForceBreakdown | null {
    const robot = this.robots.get(robotId);
    if (!robot) return null;

    const centroid = this.computeCentroid();
    const w = this.config.weights;

    const cohesion = vecScale(this.computeCohesion(robot, centroid), w.alpha);
    const separation = vecScale(this.computeSeparation(robot), w.beta);
    const goalForce = vecScale(this.computeGoalForce(robot), w.gamma);
    const driftForce = vecScale(this.computeDriftForce(robot), w.delta);

    // Sum all forces
    let resultant = vecAdd(vecAdd(cohesion, separation), vecAdd(goalForce, driftForce));
    const rawMagnitude = vecMag(resultant);

    // Speed cap (hard invariant)
    let capped = false;
    if (rawMagnitude > this.config.maxSpeed) {
      resultant = vecScale(vecNormalize(resultant), this.config.maxSpeed);
      capped = true;
    }

    return {
      cohesion,
      separation,
      goalForce,
      driftForce,
      resultant,
      rawMagnitude,
      capped,
    };
  }

  // ── Integration ──

  /**
   * Step the simulation forward by dt.
   * Applies forces, updates positions, enforces hard invariants.
   */
  public step(): Map<string, ForceBreakdown> {
    const breakdowns = new Map<string, ForceBreakdown>();
    const updates: Array<{ id: string; newPos: Vec; newVel: Vec }> = [];

    // Phase 1: Compute all forces
    for (const robot of this.robots.values()) {
      const fb = this.computeForces(robot.id);
      if (!fb) continue;
      breakdowns.set(robot.id, fb);

      const newVel = fb.resultant;
      const newPos = vecAdd(robot.position, vecScale(newVel, this.config.dt));
      updates.push({ id: robot.id, newPos, newVel });
    }

    // Phase 2: Apply updates with invariant enforcement
    for (const { id, newPos, newVel } of updates) {
      const robot = this.robots.get(id);
      if (!robot) continue;

      let pos = { ...newPos };

      // Hard invariant: no-go zone enforcement
      for (const zone of this.noGoZones) {
        const d = vecDist(pos, zone.center);
        if (d < zone.radius) {
          // Project to boundary
          const dir = vecNormalize(vecSub(pos, zone.center));
          pos = vecAdd(zone.center, vecScale(dir, zone.radius + 0.01));
        }
      }

      // Hard invariant: minimum separation enforcement
      for (const other of this.robots.values()) {
        if (other.id === id) continue;
        const d = vecDist(pos, other.position);
        if (d < this.config.minSeparation && d > 1e-12) {
          const dir = vecNormalize(vecSub(pos, other.position));
          pos = vecAdd(other.position, vecScale(dir, this.config.minSeparation));
        }
      }

      robot.position = pos;
      robot.velocity = newVel;
    }

    return breakdowns;
  }

  /**
   * Get neighbors within coupling radius for a given robot.
   */
  public getNeighbors(robotId: string): RobotSpatialState[] {
    const robot = this.robots.get(robotId);
    if (!robot) return [];

    const neighbors: RobotSpatialState[] = [];
    for (const other of this.robots.values()) {
      if (other.id === robotId) continue;
      if (vecDist(robot.position, other.position) <= this.config.couplingRadius) {
        neighbors.push(other);
      }
    }
    return neighbors;
  }

  /**
   * Check if a position violates any no-go zone.
   */
  public isInNoGoZone(pos: Vec): boolean {
    for (const zone of this.noGoZones) {
      if (vecDist(pos, zone.center) < zone.radius) return true;
    }
    return false;
  }

  /**
   * Get swarm spread — max distance from centroid.
   */
  public getSwarmSpread(): number {
    const centroid = this.computeCentroid();
    let maxDist = 0;
    for (const robot of this.robots.values()) {
      maxDist = Math.max(maxDist, vecDist(robot.position, centroid));
    }
    return maxDist;
  }

  /**
   * Get config (read-only copy).
   */
  public getConfig(): Readonly<SwarmGeometryConfig> {
    return { ...this.config, weights: { ...this.config.weights } };
  }
}
