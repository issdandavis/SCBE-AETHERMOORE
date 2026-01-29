/**
 * Swarm Deployment Formations
 * ===========================
 *
 * Geometric formation algorithms for agent positioning in 3D Poincaré ball.
 *
 * Formation Types:
 * - Hexagonal Ring: Default, symmetric, 60° spacing
 * - Tetrahedral: 3D depth, fault-tolerant
 * - Concentric Rings: Hierarchical, IP tier mapping
 * - Adaptive Scatter: Dynamic, self-organizing, jam-resistant
 *
 * @module fleet/formations
 * @version 1.0.0
 * @since 2026-01-29
 */

import { TongueID } from '../spiralverse/types';

/**
 * 3D position vector
 */
export type Position3D = [number, number, number];

/**
 * Agent position with metadata
 */
export interface AgentPosition {
  agentId: string;
  tongue: TongueID;
  position: Position3D;
  /** Distance from origin (0-1 in Poincaré ball) */
  radius: number;
  /** Angle in radians (for ring formations) */
  angle?: number;
  /** Layer/ring index (for concentric formations) */
  layer?: number;
}

/**
 * Formation type
 */
export type FormationType = 'hexagonal' | 'tetrahedral' | 'concentric' | 'scatter';

/**
 * Formation configuration
 */
export interface FormationConfig {
  /** Formation type */
  type: FormationType;
  /** Base radius for positioning (default: 0.3) */
  radius?: number;
  /** Inner radius for concentric (default: 0.2) */
  innerRadius?: number;
  /** Outer radius for concentric (default: 0.5) */
  outerRadius?: number;
  /** Number of layers for concentric (default: 2) */
  layers?: number;
  /** Z-axis spread for tetrahedral (default: 1.633) */
  zSpread?: number;
}

/**
 * Scatter dynamics configuration
 */
export interface ScatterConfig {
  /** Repulsion threshold distance */
  repulsionThreshold: number;
  /** Repulsion strength */
  repulsionStrength: number;
  /** Attraction to center strength */
  attractionStrength: number;
  /** Random drift sigma */
  driftSigma: number;
  /** Time step */
  dt: number;
  /** Boundary bounce factor (how far from edge to stay) */
  boundaryFactor: number;
}

/**
 * Default scatter configuration
 */
export const DEFAULT_SCATTER_CONFIG: ScatterConfig = {
  repulsionThreshold: 0.2,
  repulsionStrength: 0.1,
  attractionStrength: 0.1,
  driftSigma: 0.02,
  dt: 0.1,
  boundaryFactor: 0.95,
};

/**
 * Sacred Tongue ordering for formations
 */
export const TONGUE_ORDER: TongueID[] = ['ko', 'av', 'ru', 'ca', 'um', 'dr'];

/**
 * Calculate Euclidean distance between two 3D points
 */
export function euclideanDistance(a: Position3D, b: Position3D): number {
  const dx = a[0] - b[0];
  const dy = a[1] - b[1];
  const dz = a[2] - b[2];
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

/**
 * Calculate vector norm
 */
export function norm(v: Position3D): number {
  return Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
}

/**
 * Normalize vector to unit length
 */
export function normalize(v: Position3D): Position3D {
  const n = norm(v);
  if (n === 0) return [0, 0, 0];
  return [v[0] / n, v[1] / n, v[2] / n];
}

/**
 * Calculate hyperbolic distance in Poincaré ball
 * d_H = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
 */
export function hyperbolicDistance(a: Position3D, b: Position3D): number {
  const normA = norm(a);
  const normB = norm(b);

  // Clamp to ball interior
  if (normA >= 1 || normB >= 1) {
    return Infinity;
  }

  const diff: Position3D = [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const diffNormSq = diff[0] * diff[0] + diff[1] * diff[1] + diff[2] * diff[2];

  const denominator = (1 - normA * normA) * (1 - normB * normB);
  const argument = 1 + (2 * diffNormSq) / denominator;

  return Math.acosh(argument);
}

/**
 * Project point back into Poincaré ball if outside
 */
export function projectToBall(pos: Position3D, maxRadius: number = 0.95): Position3D {
  const r = norm(pos);
  if (r >= maxRadius) {
    const scale = maxRadius / r;
    return [pos[0] * scale, pos[1] * scale, pos[2] * scale];
  }
  return pos;
}

// =============================================================================
// FORMATION ALGORITHMS
// =============================================================================

/**
 * Generate hexagonal ring formation
 *
 * All 6 agents positioned at equal 60° intervals in a flat ring.
 *
 * ```
 *       Agent 5 (DR)
 *            •
 *           / \
 *          /   \
 * Agent 0 •     • Agent 4
 *  (KO)    \   /    (UM)
 *           \ /
 *       CENTER
 *           / \
 *          /   \
 * Agent 1 •     • Agent 3
 *  (AV)    \   /    (CA)
 *           \ /
 *            •
 *       Agent 2 (RU)
 * ```
 *
 * @param agentIds - Array of 6 agent IDs
 * @param radius - Distance from center (default: 0.3)
 * @returns Array of agent positions
 */
export function hexagonalFormation(
  agentIds: string[],
  radius: number = 0.3
): AgentPosition[] {
  const positions: AgentPosition[] = [];

  for (let i = 0; i < Math.min(agentIds.length, 6); i++) {
    const angle = i * ((2 * Math.PI) / 6); // 60° spacing
    const x = radius * Math.cos(angle);
    const y = radius * Math.sin(angle);
    const z = 0.0; // Flat ring

    positions.push({
      agentId: agentIds[i],
      tongue: TONGUE_ORDER[i],
      position: [x, y, z],
      radius,
      angle,
    });
  }

  return positions;
}

/**
 * Generate tetrahedral formation (3D)
 *
 * 4 vertices of tetrahedron + 2 extra agents at different z-levels.
 * Provides maximal 3D separation for fault tolerance.
 *
 * @param agentIds - Array of 6 agent IDs
 * @param radius - Base radius (default: 0.3)
 * @param zSpread - Z-axis spread factor (default: 1.633)
 * @returns Array of agent positions
 */
export function tetrahedralFormation(
  agentIds: string[],
  radius: number = 0.3,
  zSpread: number = 1.633
): AgentPosition[] {
  const positions: Position3D[] = [
    [radius, 0.0, 0.0], // Agent 0 (KO)
    [-radius / 2, radius * 0.866, 0.0], // Agent 1 (AV)
    [-radius / 2, -radius * 0.866, 0.0], // Agent 2 (RU)
    [0.0, 0.0, radius * zSpread], // Agent 3 (CA) - top
    [0.1, 0.1, -radius * 0.5], // Agent 4 (UM) - below
    [-0.1, -0.1, -radius * 0.5], // Agent 5 (DR) - below
  ];

  return positions.slice(0, agentIds.length).map((pos, i) => ({
    agentId: agentIds[i],
    tongue: TONGUE_ORDER[i],
    position: projectToBall(pos),
    radius: norm(pos),
  }));
}

/**
 * Generate concentric rings formation (hierarchical)
 *
 * Inner ring: High-priority agents (KO, AV, RU)
 * Outer ring: Lower-priority agents (CA, UM, DR)
 *
 * Maps naturally to IP tiers: inner = hidden, outer = public
 *
 * @param agentIds - Array of 6 agent IDs
 * @param innerRadius - Inner ring radius (default: 0.2)
 * @param outerRadius - Outer ring radius (default: 0.5)
 * @returns Array of agent positions
 */
export function concentricFormation(
  agentIds: string[],
  innerRadius: number = 0.2,
  outerRadius: number = 0.5
): AgentPosition[] {
  const positions: AgentPosition[] = [];

  // Inner ring (3 agents: KO, AV, RU)
  for (let i = 0; i < 3 && i < agentIds.length; i++) {
    const angle = i * ((2 * Math.PI) / 3);
    const x = innerRadius * Math.cos(angle);
    const y = innerRadius * Math.sin(angle);

    positions.push({
      agentId: agentIds[i],
      tongue: TONGUE_ORDER[i],
      position: [x, y, 0.0],
      radius: innerRadius,
      angle,
      layer: 0,
    });
  }

  // Outer ring (3 agents: CA, UM, DR)
  for (let i = 3; i < 6 && i < agentIds.length; i++) {
    const angle = (i - 3) * ((2 * Math.PI) / 3) + Math.PI / 3; // Offset by 60°
    const x = outerRadius * Math.cos(angle);
    const y = outerRadius * Math.sin(angle);

    positions.push({
      agentId: agentIds[i],
      tongue: TONGUE_ORDER[i],
      position: [x, y, 0.0],
      radius: outerRadius,
      angle,
      layer: 1,
    });
  }

  return positions;
}

/**
 * Initialize scatter formation with random positions
 *
 * Agents start at random positions within a sphere of given radius.
 *
 * @param agentIds - Array of agent IDs
 * @param maxRadius - Maximum initial radius (default: 0.4)
 * @returns Array of agent positions
 */
export function initScatterFormation(
  agentIds: string[],
  maxRadius: number = 0.4
): AgentPosition[] {
  return agentIds.map((agentId, i) => {
    // Random spherical coordinates
    const r = Math.random() * maxRadius;
    const theta = Math.random() * 2 * Math.PI;
    const phi = Math.acos(2 * Math.random() - 1);

    const x = r * Math.sin(phi) * Math.cos(theta);
    const y = r * Math.sin(phi) * Math.sin(theta);
    const z = r * Math.cos(phi);

    return {
      agentId,
      tongue: TONGUE_ORDER[i % 6],
      position: [x, y, z] as Position3D,
      radius: r,
    };
  });
}

/**
 * Agent state for scatter dynamics
 */
export interface ScatterAgent {
  id: string;
  tongue: TongueID;
  position: Position3D;
  /** Phase for tongue-specific behavior (0 to 2π) */
  phase: number;
  /** Weight for repulsion calculation */
  weight: number;
}

/**
 * Step adaptive scatter dynamics
 *
 * Implements physics-based self-organization:
 * 1. Repulsion from nearby agents
 * 2. Attraction to swarm center
 * 3. Random drift (Brownian motion)
 * 4. Boundary projection
 *
 * @param agents - Current agent states
 * @param config - Scatter configuration
 * @returns Updated agent states
 */
export function stepScatterDynamics(
  agents: ScatterAgent[],
  config: ScatterConfig = DEFAULT_SCATTER_CONFIG
): ScatterAgent[] {
  const center = calculateCenter(agents.map((a) => a.position));

  return agents.map((agent) => {
    const force: Position3D = [0, 0, 0];

    // 1. Repulsion from nearby agents
    for (const other of agents) {
      if (other.id === agent.id) continue;

      const dist = euclideanDistance(agent.position, other.position);
      if (dist < config.repulsionThreshold && dist > 0) {
        // Direction away from other agent
        const direction = normalize([
          agent.position[0] - other.position[0],
          agent.position[1] - other.position[1],
          agent.position[2] - other.position[2],
        ]);

        // Repulsion strength = phase-weighted
        const strength = agent.weight * Math.sin(agent.phase) * config.repulsionStrength;
        force[0] += strength * direction[0];
        force[1] += strength * direction[1];
        force[2] += strength * direction[2];
      }
    }

    // 2. Attraction to swarm center
    const toCenter: Position3D = [
      center[0] - agent.position[0],
      center[1] - agent.position[1],
      center[2] - agent.position[2],
    ];
    force[0] += config.attractionStrength * toCenter[0];
    force[1] += config.attractionStrength * toCenter[1];
    force[2] += config.attractionStrength * toCenter[2];

    // 3. Random drift (Gaussian noise approximation using Box-Muller)
    const u1 = Math.random();
    const u2 = Math.random();
    const gaussian = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    force[0] += config.driftSigma * gaussian;
    force[1] += config.driftSigma * gaussian;
    force[2] += config.driftSigma * gaussian;

    // 4. Update position (Euler integration)
    const newPos: Position3D = [
      agent.position[0] + force[0] * config.dt,
      agent.position[1] + force[1] * config.dt,
      agent.position[2] + force[2] * config.dt,
    ];

    // 5. Project back into Poincaré ball
    const projectedPos = projectToBall(newPos, config.boundaryFactor);

    // 6. Update phase (slow rotation)
    const newPhase = (agent.phase + 0.01) % (2 * Math.PI);

    return {
      ...agent,
      position: projectedPos,
      phase: newPhase,
    };
  });
}

/**
 * Calculate center of mass
 */
export function calculateCenter(positions: Position3D[]): Position3D {
  if (positions.length === 0) return [0, 0, 0];

  const sum: Position3D = [0, 0, 0];
  for (const pos of positions) {
    sum[0] += pos[0];
    sum[1] += pos[1];
    sum[2] += pos[2];
  }

  return [sum[0] / positions.length, sum[1] / positions.length, sum[2] / positions.length];
}

/**
 * Calculate swarm spread (average distance from center)
 */
export function calculateSpread(positions: Position3D[]): number {
  if (positions.length === 0) return 0;

  const center = calculateCenter(positions);
  let totalDist = 0;

  for (const pos of positions) {
    totalDist += euclideanDistance(pos, center);
  }

  return totalDist / positions.length;
}

/**
 * Calculate minimum pairwise distance
 */
export function calculateMinDistance(positions: Position3D[]): number {
  if (positions.length < 2) return Infinity;

  let minDist = Infinity;

  for (let i = 0; i < positions.length; i++) {
    for (let j = i + 1; j < positions.length; j++) {
      const dist = euclideanDistance(positions[i], positions[j]);
      if (dist < minDist) {
        minDist = dist;
      }
    }
  }

  return minDist;
}

// =============================================================================
// FORMATION MANAGER
// =============================================================================

/**
 * Formation state
 */
export interface FormationState {
  type: FormationType;
  positions: AgentPosition[];
  config: FormationConfig;
  /** For scatter: current agent states */
  scatterAgents?: ScatterAgent[];
  /** Metrics */
  metrics: {
    spread: number;
    minDistance: number;
    coherence: number;
  };
  createdAt: number;
  updatedAt: number;
}

/**
 * Formation Manager
 *
 * Manages formation state and transitions between formation types.
 */
export class FormationManager {
  private formations: Map<string, FormationState> = new Map();

  /**
   * Create a new formation
   *
   * @param swarmId - Swarm identifier
   * @param agentIds - Agent IDs to position
   * @param config - Formation configuration
   * @returns Initial formation state
   */
  public createFormation(
    swarmId: string,
    agentIds: string[],
    config: FormationConfig
  ): FormationState {
    let positions: AgentPosition[];
    let scatterAgents: ScatterAgent[] | undefined;

    switch (config.type) {
      case 'hexagonal':
        positions = hexagonalFormation(agentIds, config.radius ?? 0.3);
        break;

      case 'tetrahedral':
        positions = tetrahedralFormation(
          agentIds,
          config.radius ?? 0.3,
          config.zSpread ?? 1.633
        );
        break;

      case 'concentric':
        positions = concentricFormation(
          agentIds,
          config.innerRadius ?? 0.2,
          config.outerRadius ?? 0.5
        );
        break;

      case 'scatter':
        positions = initScatterFormation(agentIds, config.radius ?? 0.4);
        scatterAgents = positions.map((p, i) => ({
          id: p.agentId,
          tongue: p.tongue,
          position: p.position,
          phase: (i * Math.PI) / 3, // Stagger initial phases
          weight: 1.0,
        }));
        break;

      default:
        positions = hexagonalFormation(agentIds, config.radius ?? 0.3);
    }

    const positionVectors = positions.map((p) => p.position);
    const state: FormationState = {
      type: config.type,
      positions,
      config,
      scatterAgents,
      metrics: {
        spread: calculateSpread(positionVectors),
        minDistance: calculateMinDistance(positionVectors),
        coherence: 1.0,
      },
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    this.formations.set(swarmId, state);
    return state;
  }

  /**
   * Get formation state
   */
  public getFormation(swarmId: string): FormationState | undefined {
    return this.formations.get(swarmId);
  }

  /**
   * Switch formation type
   *
   * Transitions agents from current positions to new formation.
   *
   * @param swarmId - Swarm identifier
   * @param newType - New formation type
   * @param config - Optional new configuration
   * @returns Updated formation state
   */
  public switchFormation(
    swarmId: string,
    newType: FormationType,
    config?: Partial<FormationConfig>
  ): FormationState | undefined {
    const current = this.formations.get(swarmId);
    if (!current) return undefined;

    const agentIds = current.positions.map((p) => p.agentId);
    const newConfig: FormationConfig = {
      ...current.config,
      ...config,
      type: newType,
    };

    return this.createFormation(swarmId, agentIds, newConfig);
  }

  /**
   * Step scatter dynamics (for scatter formations)
   *
   * @param swarmId - Swarm identifier
   * @param config - Optional scatter configuration
   * @returns Updated formation state
   */
  public stepScatter(
    swarmId: string,
    config?: Partial<ScatterConfig>
  ): FormationState | undefined {
    const state = this.formations.get(swarmId);
    if (!state || state.type !== 'scatter' || !state.scatterAgents) {
      return undefined;
    }

    const scatterConfig = { ...DEFAULT_SCATTER_CONFIG, ...config };
    state.scatterAgents = stepScatterDynamics(state.scatterAgents, scatterConfig);

    // Update positions from scatter agents
    state.positions = state.scatterAgents.map((agent, i) => ({
      agentId: agent.id,
      tongue: agent.tongue,
      position: agent.position,
      radius: norm(agent.position),
    }));

    // Update metrics
    const positionVectors = state.positions.map((p) => p.position);
    state.metrics = {
      spread: calculateSpread(positionVectors),
      minDistance: calculateMinDistance(positionVectors),
      coherence: this.calculateFormationCoherence(state),
    };

    state.updatedAt = Date.now();
    return state;
  }

  /**
   * Calculate formation coherence
   *
   * Based on how well agents maintain expected distances.
   */
  private calculateFormationCoherence(state: FormationState): number {
    const positions = state.positions.map((p) => p.position);
    if (positions.length < 2) return 1.0;

    // For scatter, coherence is based on spread stability
    if (state.type === 'scatter') {
      const spread = calculateSpread(positions);
      // Coherent if spread is between 0.1 and 0.5
      if (spread < 0.1) return spread / 0.1;
      if (spread > 0.5) return Math.max(0, 1 - (spread - 0.5) / 0.5);
      return 1.0;
    }

    // For fixed formations, coherence is based on distance from ideal
    const expectedRadius = state.config.radius ?? 0.3;
    let totalDeviation = 0;

    for (const pos of state.positions) {
      const deviation = Math.abs(pos.radius - expectedRadius);
      totalDeviation += deviation;
    }

    const avgDeviation = totalDeviation / positions.length;
    return Math.max(0, 1 - avgDeviation / expectedRadius);
  }

  /**
   * Get agent position
   */
  public getAgentPosition(swarmId: string, agentId: string): AgentPosition | undefined {
    const state = this.formations.get(swarmId);
    if (!state) return undefined;
    return state.positions.find((p) => p.agentId === agentId);
  }

  /**
   * Update single agent position (for manual adjustment)
   */
  public updateAgentPosition(
    swarmId: string,
    agentId: string,
    newPosition: Position3D
  ): boolean {
    const state = this.formations.get(swarmId);
    if (!state) return false;

    const idx = state.positions.findIndex((p) => p.agentId === agentId);
    if (idx === -1) return false;

    const projected = projectToBall(newPosition);
    state.positions[idx].position = projected;
    state.positions[idx].radius = norm(projected);

    // Update scatter agent if applicable
    if (state.scatterAgents) {
      const scatterIdx = state.scatterAgents.findIndex((a) => a.id === agentId);
      if (scatterIdx !== -1) {
        state.scatterAgents[scatterIdx].position = projected;
      }
    }

    // Recalculate metrics
    const positionVectors = state.positions.map((p) => p.position);
    state.metrics = {
      spread: calculateSpread(positionVectors),
      minDistance: calculateMinDistance(positionVectors),
      coherence: this.calculateFormationCoherence(state),
    };

    state.updatedAt = Date.now();
    return true;
  }

  /**
   * Get distance matrix between all agents
   */
  public getDistanceMatrix(
    swarmId: string,
    metric: 'euclidean' | 'hyperbolic' = 'euclidean'
  ): number[][] | undefined {
    const state = this.formations.get(swarmId);
    if (!state) return undefined;

    const positions = state.positions.map((p) => p.position);
    const n = positions.length;
    const matrix: number[][] = [];

    for (let i = 0; i < n; i++) {
      matrix[i] = [];
      for (let j = 0; j < n; j++) {
        if (i === j) {
          matrix[i][j] = 0;
        } else if (metric === 'hyperbolic') {
          matrix[i][j] = hyperbolicDistance(positions[i], positions[j]);
        } else {
          matrix[i][j] = euclideanDistance(positions[i], positions[j]);
        }
      }
    }

    return matrix;
  }

  /**
   * Delete formation
   */
  public deleteFormation(swarmId: string): boolean {
    return this.formations.delete(swarmId);
  }

  /**
   * Get all formation states
   */
  public getAllFormations(): Map<string, FormationState> {
    return new Map(this.formations);
  }
}

/**
 * Global formation manager instance
 */
let globalFormationManager: FormationManager | null = null;

/**
 * Get global formation manager
 */
export function getFormationManager(): FormationManager {
  if (!globalFormationManager) {
    globalFormationManager = new FormationManager();
  }
  return globalFormationManager;
}
