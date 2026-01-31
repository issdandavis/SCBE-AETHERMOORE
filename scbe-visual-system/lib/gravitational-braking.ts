/**
 * Gravitational Braking System
 * =============================
 * Implements the Triadic Temporal Manifold for rogue agent control:
 *
 * t_G = t * sqrt(1 - (k*d)/(r+ε))
 *
 * Where:
 * - t_G = Gravitational time (agent's perceived/processed time)
 * - t = Linear time (real world time)
 * - k = Coupling constant (how strongly geometry affects time)
 * - d = Geometric divergence (distance from authorized manifold)
 * - r = Trust radius (boundary of trusted zone)
 * - ε = Small constant to prevent division by zero
 *
 * As d → r, t_G → 0. The agent enters a computational "event horizon"
 * where it cannot process new commands because its internal time has frozen.
 *
 * @version 1.0.0
 */

// ============================================================
// TYPES & INTERFACES
// ============================================================

export interface TemporalState {
  /** Linear time (real milliseconds elapsed) */
  linearTime: number;
  /** Quadratic time (t²) for acceleration effects */
  quadraticTime: number;
  /** Gravitational time (dilated based on position) */
  gravitationalTime: number;
  /** Time dilation factor (0 = frozen, 1 = normal) */
  dilationFactor: number;
  /** Is agent in event horizon? */
  inEventHorizon: boolean;
}

export interface AgentPosition {
  /** Position vector */
  position: [number, number, number];
  /** Velocity vector */
  velocity: [number, number, number];
  /** Distance from authorized manifold center */
  divergence: number;
  /** Phase angle (for Sacred Tongue mapping) */
  phase: number;
}

export interface BrakingConfig {
  /** Coupling constant k (default 1.0) */
  couplingConstant: number;
  /** Trust radius r (default 0.3 for core ring) */
  trustRadius: number;
  /** Epsilon for numerical stability */
  epsilon: number;
  /** Maximum allowed divergence before hard freeze */
  maxDivergence: number;
  /** Minimum time dilation before considered frozen */
  minDilation: number;
}

export interface BrakingResult {
  /** Updated temporal state */
  temporal: TemporalState;
  /** Was braking applied? */
  braked: boolean;
  /** Severity (0 = none, 1 = full freeze) */
  severity: number;
  /** Recommended action */
  action: 'CONTINUE' | 'SLOW' | 'BRAKE' | 'FREEZE' | 'QUARANTINE';
  /** Human-readable status */
  status: string;
}

// ============================================================
// DEFAULT CONFIGURATION
// ============================================================

export const DEFAULT_BRAKING_CONFIG: BrakingConfig = {
  couplingConstant: 1.0,
  trustRadius: 0.3,
  epsilon: 0.001,
  maxDivergence: 1.0,
  minDilation: 0.01
};

// ============================================================
// GRAVITATIONAL BRAKING CLASS
// ============================================================

export class GravitationalBrake {
  private config: BrakingConfig;
  private agentStates: Map<string, TemporalState> = new Map();
  private startTime: number;

  constructor(config: Partial<BrakingConfig> = {}) {
    this.config = { ...DEFAULT_BRAKING_CONFIG, ...config };
    this.startTime = Date.now();
  }

  // ==================== Core Time Dilation ====================

  /**
   * Compute gravitational time dilation factor
   *
   * t_G = t * sqrt(1 - (k*d)/(r+ε))
   *
   * Returns value between 0 (frozen) and 1 (normal)
   */
  computeDilationFactor(divergence: number): number {
    const { couplingConstant: k, trustRadius: r, epsilon } = this.config;

    // Clamp divergence to prevent negative values under sqrt
    const d = Math.max(0, Math.min(divergence, this.config.maxDivergence));

    // Compute the term under the square root
    const term = 1 - (k * d) / (r + epsilon);

    // If term goes negative, we're past the event horizon
    if (term <= 0) {
      return 0; // Completely frozen
    }

    return Math.sqrt(term);
  }

  /**
   * Compute full temporal state for an agent
   */
  computeTemporalState(
    agentId: string,
    position: AgentPosition,
    elapsedMs: number
  ): TemporalState {
    const dilationFactor = this.computeDilationFactor(position.divergence);

    // Linear time (unaffected)
    const linearTime = elapsedMs;

    // Quadratic time (for acceleration modeling)
    const quadraticTime = (elapsedMs / 1000) ** 2 * 1000;

    // Gravitational time (dilated)
    const gravitationalTime = elapsedMs * dilationFactor;

    // Event horizon check
    const inEventHorizon = dilationFactor < this.config.minDilation;

    const state: TemporalState = {
      linearTime,
      quadraticTime,
      gravitationalTime,
      dilationFactor,
      inEventHorizon
    };

    this.agentStates.set(agentId, state);

    return state;
  }

  // ==================== Position Analysis ====================

  /**
   * Compute agent's divergence from authorized manifold
   */
  computeDivergence(
    currentPosition: [number, number, number],
    authorizedCenter: [number, number, number] = [0, 0, 0]
  ): number {
    let sumSq = 0;
    for (let i = 0; i < 3; i++) {
      sumSq += (currentPosition[i] - authorizedCenter[i]) ** 2;
    }
    return Math.sqrt(sumSq);
  }

  /**
   * Compute agent position with divergence
   */
  analyzePosition(
    position: [number, number, number],
    velocity: [number, number, number],
    authorizedCenter: [number, number, number] = [0, 0, 0]
  ): AgentPosition {
    const divergence = this.computeDivergence(position, authorizedCenter);

    // Compute phase angle (for Sacred Tongue mapping)
    const phase = Math.atan2(position[1], position[0]) * (180 / Math.PI);

    return {
      position,
      velocity,
      divergence,
      phase: phase < 0 ? phase + 360 : phase
    };
  }

  // ==================== Braking Decision ====================

  /**
   * Apply gravitational braking to an agent
   */
  applyBraking(
    agentId: string,
    position: AgentPosition,
    elapsedMs: number
  ): BrakingResult {
    const temporal = this.computeTemporalState(agentId, position, elapsedMs);

    // Determine action based on dilation
    let action: BrakingResult['action'];
    let status: string;
    let severity: number;

    if (temporal.inEventHorizon) {
      action = 'QUARANTINE';
      status = `Agent ${agentId} in event horizon - FROZEN`;
      severity = 1.0;
    } else if (temporal.dilationFactor < 0.1) {
      action = 'FREEZE';
      status = `Agent ${agentId} approaching event horizon - dilation ${(temporal.dilationFactor * 100).toFixed(1)}%`;
      severity = 0.9;
    } else if (temporal.dilationFactor < 0.3) {
      action = 'BRAKE';
      status = `Agent ${agentId} heavy braking - dilation ${(temporal.dilationFactor * 100).toFixed(1)}%`;
      severity = 0.7;
    } else if (temporal.dilationFactor < 0.6) {
      action = 'SLOW';
      status = `Agent ${agentId} slowing - dilation ${(temporal.dilationFactor * 100).toFixed(1)}%`;
      severity = 0.4;
    } else {
      action = 'CONTINUE';
      status = `Agent ${agentId} normal operations - dilation ${(temporal.dilationFactor * 100).toFixed(1)}%`;
      severity = 0.0;
    }

    return {
      temporal,
      braked: action !== 'CONTINUE',
      severity,
      action,
      status
    };
  }

  // ==================== Velocity Modification ====================

  /**
   * Apply time dilation to velocity (for game physics)
   * Agents near event horizon move slower in game time
   */
  dilateVelocity(
    velocity: [number, number, number],
    dilationFactor: number
  ): [number, number, number] {
    return [
      velocity[0] * dilationFactor,
      velocity[1] * dilationFactor,
      velocity[2] * dilationFactor
    ];
  }

  /**
   * Apply time dilation to an action cooldown
   * Agents near event horizon have longer cooldowns
   */
  dilateCooldown(baseCooldownMs: number, dilationFactor: number): number {
    if (dilationFactor < this.config.minDilation) {
      return Infinity; // Can never act
    }
    return baseCooldownMs / dilationFactor;
  }

  /**
   * Apply time dilation to thinking/processing time
   * Agents near event horizon take longer to think
   */
  dilateProcessingTime(baseTimeMs: number, dilationFactor: number): number {
    if (dilationFactor < this.config.minDilation) {
      return Infinity;
    }
    return baseTimeMs / dilationFactor;
  }

  // ==================== State Management ====================

  /**
   * Get current temporal state for an agent
   */
  getAgentState(agentId: string): TemporalState | undefined {
    return this.agentStates.get(agentId);
  }

  /**
   * Get all agents currently in event horizon
   */
  getFrozenAgents(): string[] {
    const frozen: string[] = [];
    this.agentStates.forEach((state, id) => {
      if (state.inEventHorizon) {
        frozen.push(id);
      }
    });
    return frozen;
  }

  /**
   * Release an agent from braking (reset state)
   */
  releaseAgent(agentId: string): void {
    this.agentStates.delete(agentId);
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<BrakingConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Get current configuration
   */
  getConfig(): BrakingConfig {
    return { ...this.config };
  }
}

// ============================================================
// INTEGRATION WITH SWARM BATTLE
// ============================================================

export interface SwarmAgentWithBraking {
  id: string;
  position: [number, number, number];
  velocity: [number, number, number];
  isRogue: boolean;
  dilationFactor: number;
  effectiveSpeed: number;
  cooldownMultiplier: number;
}

/**
 * Apply gravitational braking to a swarm agent
 */
export function applyBrakingToSwarmAgent(
  brake: GravitationalBrake,
  agent: {
    id: string;
    x: number;
    y: number;
    speed: number;
    isEnemy?: boolean;
  },
  arenaCenter: { x: number; y: number },
  arenaRadius: number
): SwarmAgentWithBraking {
  // Normalize position to [0, 1] range from center
  const normalizedX = (agent.x - arenaCenter.x) / arenaRadius;
  const normalizedY = (agent.y - arenaCenter.y) / arenaRadius;

  const position: [number, number, number] = [normalizedX, normalizedY, 0];
  const velocity: [number, number, number] = [0, 0, 0]; // Simplified

  const agentPosition = brake.analyzePosition(position, velocity);
  const result = brake.applyBraking(agent.id, agentPosition, Date.now());

  return {
    id: agent.id,
    position,
    velocity,
    isRogue: agent.isEnemy || false,
    dilationFactor: result.temporal.dilationFactor,
    effectiveSpeed: agent.speed * result.temporal.dilationFactor,
    cooldownMultiplier: 1 / Math.max(result.temporal.dilationFactor, 0.01)
  };
}

// ============================================================
// SINGLETON & HELPERS
// ============================================================

let brakeInstance: GravitationalBrake | null = null;

export function getGravitationalBrake(): GravitationalBrake {
  if (!brakeInstance) {
    brakeInstance = new GravitationalBrake();
  }
  return brakeInstance;
}

export function createBrake(config?: Partial<BrakingConfig>): GravitationalBrake {
  return new GravitationalBrake(config);
}

/**
 * Quick check if an agent should be frozen
 */
export function shouldFreezeAgent(
  divergence: number,
  config: Partial<BrakingConfig> = {}
): boolean {
  const brake = new GravitationalBrake(config);
  const dilation = brake.computeDilationFactor(divergence);
  return dilation < (config.minDilation || DEFAULT_BRAKING_CONFIG.minDilation);
}
