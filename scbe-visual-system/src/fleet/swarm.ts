/**
 * Swarm Coordination System
 *
 * Implements ODE-based flux dynamics for managing swarm members
 * across dimensional states. The flux coefficient ν (nu) evolves
 * according to:
 *
 *   dν/dt = α(ν_target - ν) - β*decay + γ*coherence_boost
 *
 * Where:
 * - α: Attraction coefficient toward target state
 * - β: Natural decay coefficient
 * - γ: Coherence boost coefficient from nearby members
 *
 * @module fleet/swarm
 */

import {
  DimensionalState,
  FluxConfig,
  GovernanceTier,
  SwarmEvent,
  SwarmEventType,
  SwarmMemberState,
  DEFAULT_FLUX_CONFIG,
  getDimensionalState,
} from './types';
import { PollyPadManager } from './polly-pad';

/**
 * Swarm member with internal tracking
 */
interface TrackedMember extends SwarmMemberState {
  targetFlux: number;
  decayAccumulator: number;
}

/**
 * Swarm Coordinator - Manages fleet dynamics using ODE-based flux evolution
 */
export class SwarmCoordinator {
  private members: Map<string, TrackedMember> = new Map();
  private fluxConfig: FluxConfig;
  private padManager: PollyPadManager;
  private eventListeners: Array<(event: SwarmEvent) => void> = [];
  private simulationInterval: ReturnType<typeof setInterval> | null = null;

  constructor(config: Partial<FluxConfig> = {}, padManager?: PollyPadManager) {
    this.fluxConfig = { ...DEFAULT_FLUX_CONFIG, ...config };
    this.padManager = padManager || new PollyPadManager();
  }

  /**
   * Add a new member to the swarm
   */
  addMember(
    id: string,
    governanceTier: GovernanceTier,
    initialFlux: number = 1.0,
    position6D?: number[]
  ): SwarmMemberState {
    // Validate initial flux
    if (initialFlux < 0 || initialFlux > 1) {
      throw new Error(`Initial flux must be in [0, 1], got ${initialFlux}`);
    }

    const member: TrackedMember = {
      id,
      fluxCoefficient: initialFlux,
      dimensionalState: getDimensionalState(initialFlux),
      governanceTier,
      coherence: 1.0,
      lastUpdate: Date.now(),
      position6D: position6D || this.generateDefaultPosition(governanceTier),
      targetFlux: initialFlux,
      decayAccumulator: 0,
    };

    this.members.set(id, member);

    this.emitEvent({
      type: 'member_join',
      memberId: id,
      timestamp: Date.now(),
      newState: member.dimensionalState,
      fluxCoefficient: member.fluxCoefficient,
    });

    return this.toPublicState(member);
  }

  /**
   * Remove a member from the swarm
   */
  removeMember(id: string): boolean {
    const member = this.members.get(id);
    if (!member) {
      return false;
    }

    this.members.delete(id);

    this.emitEvent({
      type: 'member_leave',
      memberId: id,
      timestamp: Date.now(),
      previousState: member.dimensionalState,
      fluxCoefficient: member.fluxCoefficient,
    });

    return true;
  }

  /**
   * Get a member's current state
   */
  getMember(id: string): SwarmMemberState | undefined {
    const member = this.members.get(id);
    return member ? this.toPublicState(member) : undefined;
  }

  /**
   * Get all swarm members
   */
  getAllMembers(): SwarmMemberState[] {
    return Array.from(this.members.values()).map((m) => this.toPublicState(m));
  }

  /**
   * Set target flux for a member
   */
  setTargetFlux(memberId: string, targetFlux: number): void {
    const member = this.members.get(memberId);
    if (!member) {
      throw new Error(`Member ${memberId} not found`);
    }

    if (targetFlux < 0 || targetFlux > 1) {
      throw new Error(`Target flux must be in [0, 1], got ${targetFlux}`);
    }

    member.targetFlux = targetFlux;
  }

  /**
   * Update coherence for a member
   */
  updateCoherence(memberId: string, coherence: number): void {
    const member = this.members.get(memberId);
    if (!member) {
      throw new Error(`Member ${memberId} not found`);
    }

    if (coherence < 0 || coherence > 1) {
      throw new Error(`Coherence must be in [0, 1], got ${coherence}`);
    }

    const previousCoherence = member.coherence;
    member.coherence = coherence;

    if (Math.abs(coherence - previousCoherence) > 0.1) {
      this.emitEvent({
        type: 'coherence_shift',
        memberId,
        timestamp: Date.now(),
        metadata: { previousCoherence, newCoherence: coherence },
      });
    }
  }

  /**
   * Evolve flux using Euler method
   * dν/dt = α(ν_target - ν) - β*decay + γ*coherence_boost
   */
  evolveFluxEuler(memberId: string): void {
    const member = this.members.get(memberId);
    if (!member) {
      return;
    }

    const { alpha, beta, gamma, dt } = this.fluxConfig;

    // Calculate coherence boost from pad
    const padBoost = this.padManager.calculateCoherenceBoost(memberId);
    const totalCoherenceBoost = member.coherence * (1 + padBoost);

    // Calculate flux derivative
    const attraction = alpha * (member.targetFlux - member.fluxCoefficient);
    const decay = beta * member.decayAccumulator;
    const coherenceBoost = gamma * totalCoherenceBoost;

    const dNuDt = attraction - decay + coherenceBoost;

    // Euler step
    const newFlux = Math.max(0, Math.min(1, member.fluxCoefficient + dNuDt * dt));

    // Update decay accumulator (increases when below target)
    if (member.fluxCoefficient < member.targetFlux) {
      member.decayAccumulator = Math.max(0, member.decayAccumulator - 0.01);
    } else {
      member.decayAccumulator = Math.min(1, member.decayAccumulator + 0.01);
    }

    this.updateMemberFlux(member, newFlux);
  }

  /**
   * Evolve flux using 4th-order Runge-Kutta for numerical stability
   */
  evolveFluxRK4(memberId: string): void {
    const member = this.members.get(memberId);
    if (!member) {
      return;
    }

    const { alpha, beta, gamma, dt } = this.fluxConfig;
    const padBoost = this.padManager.calculateCoherenceBoost(memberId);
    const totalCoherenceBoost = member.coherence * (1 + padBoost);

    // ODE function: f(ν) = α(ν_target - ν) - β*decay + γ*coherence
    const f = (nu: number) => {
      const attraction = alpha * (member.targetFlux - nu);
      const decay = beta * member.decayAccumulator;
      const coherenceBoost = gamma * totalCoherenceBoost;
      return attraction - decay + coherenceBoost;
    };

    // RK4 coefficients
    const k1 = f(member.fluxCoefficient);
    const k2 = f(member.fluxCoefficient + 0.5 * dt * k1);
    const k3 = f(member.fluxCoefficient + 0.5 * dt * k2);
    const k4 = f(member.fluxCoefficient + dt * k3);

    // RK4 step
    const newFlux = Math.max(
      0,
      Math.min(1, member.fluxCoefficient + (dt / 6) * (k1 + 2 * k2 + 2 * k3 + k4))
    );

    // Update decay accumulator
    if (member.fluxCoefficient < member.targetFlux) {
      member.decayAccumulator = Math.max(0, member.decayAccumulator - 0.01);
    } else {
      member.decayAccumulator = Math.min(1, member.decayAccumulator + 0.01);
    }

    this.updateMemberFlux(member, newFlux);
  }

  /**
   * Update member flux and check for state transitions
   */
  private updateMemberFlux(member: TrackedMember, newFlux: number): void {
    const previousState = member.dimensionalState;
    member.fluxCoefficient = newFlux;
    member.dimensionalState = getDimensionalState(newFlux);
    member.lastUpdate = Date.now();

    this.emitEvent({
      type: 'flux_update',
      memberId: member.id,
      timestamp: member.lastUpdate,
      fluxCoefficient: newFlux,
    });

    // Emit state change event if state changed
    if (member.dimensionalState !== previousState) {
      this.emitEvent({
        type: 'state_change',
        memberId: member.id,
        timestamp: member.lastUpdate,
        previousState,
        newState: member.dimensionalState,
        fluxCoefficient: newFlux,
      });
    }
  }

  /**
   * Evolve all members for one time step
   */
  evolveAll(useRK4: boolean = false): void {
    for (const memberId of this.members.keys()) {
      if (useRK4) {
        this.evolveFluxRK4(memberId);
      } else {
        this.evolveFluxEuler(memberId);
      }
    }
  }

  /**
   * Start continuous simulation
   */
  startSimulation(intervalMs: number = 100, useRK4: boolean = false): void {
    if (this.simulationInterval) {
      this.stopSimulation();
    }

    this.simulationInterval = setInterval(() => {
      this.evolveAll(useRK4);
    }, intervalMs);
  }

  /**
   * Stop continuous simulation
   */
  stopSimulation(): void {
    if (this.simulationInterval) {
      clearInterval(this.simulationInterval);
      this.simulationInterval = null;
    }
  }

  /**
   * Get members by dimensional state
   */
  getMembersByState(state: DimensionalState): SwarmMemberState[] {
    return Array.from(this.members.values())
      .filter((m) => m.dimensionalState === state)
      .map((m) => this.toPublicState(m));
  }

  /**
   * Get members by governance tier
   */
  getMembersByTier(tier: GovernanceTier): SwarmMemberState[] {
    return Array.from(this.members.values())
      .filter((m) => m.governanceTier === tier)
      .map((m) => this.toPublicState(m));
  }

  /**
   * Calculate swarm statistics
   */
  getStatistics(): SwarmStatistics {
    const members = Array.from(this.members.values());

    const stateDistribution: Record<DimensionalState, number> = {
      POLLY: 0,
      QUASI: 0,
      DEMI: 0,
      COLLAPSED: 0,
    };

    const tierDistribution: Record<GovernanceTier, number> = {
      KO: 0,
      AV: 0,
      RU: 0,
      CA: 0,
      UM: 0,
      DR: 0,
    };

    let totalFlux = 0;
    let totalCoherence = 0;

    for (const member of members) {
      stateDistribution[member.dimensionalState]++;
      tierDistribution[member.governanceTier]++;
      totalFlux += member.fluxCoefficient;
      totalCoherence += member.coherence;
    }

    const count = members.length || 1;

    return {
      totalMembers: members.length,
      averageFlux: totalFlux / count,
      averageCoherence: totalCoherence / count,
      stateDistribution,
      tierDistribution,
      pollyRatio: stateDistribution.POLLY / count,
    };
  }

  /**
   * Get pad manager for direct pad operations
   */
  getPadManager(): PollyPadManager {
    return this.padManager;
  }

  /**
   * Subscribe to swarm events
   */
  onEvent(listener: (event: SwarmEvent) => void): () => void {
    this.eventListeners.push(listener);
    return () => {
      const index = this.eventListeners.indexOf(listener);
      if (index >= 0) {
        this.eventListeners.splice(index, 1);
      }
    };
  }

  /**
   * Convert tracked member to public state
   */
  private toPublicState(member: TrackedMember): SwarmMemberState {
    return {
      id: member.id,
      fluxCoefficient: member.fluxCoefficient,
      dimensionalState: member.dimensionalState,
      governanceTier: member.governanceTier,
      coherence: member.coherence,
      lastUpdate: member.lastUpdate,
      position6D: member.position6D,
    };
  }

  /**
   * Generate default 6D position based on governance tier
   */
  private generateDefaultPosition(tier: GovernanceTier): number[] {
    const tierIndex: Record<GovernanceTier, number> = {
      KO: 0,
      AV: 1,
      RU: 2,
      CA: 3,
      UM: 4,
      DR: 5,
    };

    const position = [0, 0, 0, 0, 0, 0];
    position[tierIndex[tier]] = 0.5; // Place at half-distance in governance dimension
    return position;
  }

  private emitEvent(event: SwarmEvent): void {
    for (const listener of this.eventListeners) {
      listener(event);
    }
  }
}

/**
 * Swarm statistics
 */
export interface SwarmStatistics {
  totalMembers: number;
  averageFlux: number;
  averageCoherence: number;
  stateDistribution: Record<DimensionalState, number>;
  tierDistribution: Record<GovernanceTier, number>;
  pollyRatio: number;
}
