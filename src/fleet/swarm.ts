/**
 * Swarm Coordination System
 * 
 * Manages Polly dimensional swarm coordination between agent pads.
 * Implements coherence tracking, synchronization, and flux ODE dynamics.
 * 
 * Dimensional States:
 * - POLLY (ν ≈ 1.0): Full swarm participation
 * - QUASI (0.5 < ν < 1): Partial sync
 * - DEMI (0 < ν < 0.5): Minimal connection
 * - COLLAPSED (ν ≈ 0): Disconnected
 * 
 * @module fleet/swarm
 */

import { DimensionalState, getDimensionalState, PollyPad, PollyPadManager } from './polly-pad';
import { GovernanceTier } from './types';

/**
 * Swarm configuration
 */
export interface SwarmConfig {
  /** Swarm identifier */
  id: string;
  /** Swarm name */
  name: string;
  /** Minimum coherence threshold */
  minCoherence: number;
  /** Flux decay rate (per tick) */
  fluxDecayRate: number;
  /** Sync interval ms */
  syncIntervalMs: number;
  /** Maximum pads in swarm */
  maxPads: number;
}

/**
 * Swarm state snapshot
 */
export interface SwarmState {
  id: string;
  name: string;
  /** Pad IDs in this swarm */
  padIds: string[];
  /** Average flux coefficient */
  avgNu: number;
  /** Swarm coherence (0-1) */
  coherence: number;
  /** Dominant dimensional state */
  dominantState: DimensionalState;
  /** Sync timestamp */
  lastSync: number;
  /** Active pad count */
  activePads: number;
  /** Collapsed pad count */
  collapsedPads: number;
}

/**
 * Flux ODE parameters for dimensional dynamics
 * dν/dt = α(ν_target - ν) - β*decay + γ*coherence_boost
 */
export interface FluxODEParams {
  /** Attraction to target (α) */
  alpha: number;
  /** Natural decay rate (β) */
  beta: number;
  /** Coherence boost factor (γ) */
  gamma: number;
  /** Time step (dt) */
  dt: number;
}

/**
 * Default flux ODE parameters
 */
export const DEFAULT_FLUX_ODE: FluxODEParams = {
  alpha: 0.1,
  beta: 0.01,
  gamma: 0.05,
  dt: 1.0
};

/**
 * Swarm Coordinator
 * 
 * Manages dimensional flux coordination across agent pads.
 */
export class SwarmCoordinator {
  private swarms: Map<string, SwarmConfig> = new Map();
  private swarmPads: Map<string, Set<string>> = new Map(); // swarmId -> padIds
  private padManager: PollyPadManager;
  private fluxParams: FluxODEParams;
  private syncIntervals: Map<string, NodeJS.Timeout> = new Map();
  
  constructor(padManager: PollyPadManager, fluxParams: FluxODEParams = DEFAULT_FLUX_ODE) {
    this.padManager = padManager;
    this.fluxParams = fluxParams;
  }
  
  /**
   * Create a new swarm
   */
  public createSwarm(config: Omit<SwarmConfig, 'id'> & { id?: string }): SwarmConfig {
    const id = config.id || `swarm-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`;
    
    const swarm: SwarmConfig = {
      id,
      name: config.name,
      minCoherence: config.minCoherence ?? 0.5,
      fluxDecayRate: config.fluxDecayRate ?? 0.01,
      syncIntervalMs: config.syncIntervalMs ?? 5000,
      maxPads: config.maxPads ?? 10
    };
    
    this.swarms.set(id, swarm);
    this.swarmPads.set(id, new Set());
    
    return swarm;
  }
  
  /**
   * Get swarm by ID
   */
  public getSwarm(id: string): SwarmConfig | undefined {
    return this.swarms.get(id);
  }
  
  /**
   * Get all swarms
   */
  public getAllSwarms(): SwarmConfig[] {
    return Array.from(this.swarms.values());
  }
  
  /**
   * Add pad to swarm
   */
  public addPadToSwarm(swarmId: string, padId: string): boolean {
    const swarm = this.swarms.get(swarmId);
    const pads = this.swarmPads.get(swarmId);
    if (!swarm || !pads) return false;
    
    if (pads.size >= swarm.maxPads) return false;
    
    const pad = this.padManager.getPad(padId);
    if (!pad) return false;
    
    // Remove from previous swarm if any
    if (pad.swarmId) {
      this.removePadFromSwarm(pad.swarmId, padId);
    }
    
    pads.add(padId);
    
    // Update pad's swarm reference
    pad.swarmId = swarmId;
    pad.lastSwarmSync = Date.now();
    
    return true;
  }
  
  /**
   * Remove pad from swarm
   */
  public removePadFromSwarm(swarmId: string, padId: string): boolean {
    const pads = this.swarmPads.get(swarmId);
    if (!pads) return false;
    
    const removed = pads.delete(padId);
    
    if (removed) {
      const pad = this.padManager.getPad(padId);
      if (pad) {
        pad.swarmId = undefined;
        pad.coherenceScore = 1.0; // Reset to self-coherent
      }
    }
    
    return removed;
  }
  
  /**
   * Get pads in swarm
   */
  public getSwarmPads(swarmId: string): PollyPad[] {
    const padIds = this.swarmPads.get(swarmId);
    if (!padIds) return [];
    
    return Array.from(padIds)
      .map(id => this.padManager.getPad(id))
      .filter((p): p is PollyPad => p !== undefined);
  }
  
  /**
   * Get swarm state snapshot
   */
  public getSwarmState(swarmId: string): SwarmState | undefined {
    const swarm = this.swarms.get(swarmId);
    const padIds = this.swarmPads.get(swarmId);
    if (!swarm || !padIds) return undefined;
    
    const pads = this.getSwarmPads(swarmId);
    if (pads.length === 0) {
      return {
        id: swarmId,
        name: swarm.name,
        padIds: [],
        avgNu: 0,
        coherence: 0,
        dominantState: 'COLLAPSED',
        lastSync: Date.now(),
        activePads: 0,
        collapsedPads: 0
      };
    }
    
    // Calculate average flux
    const avgNu = pads.reduce((sum, p) => sum + p.nu, 0) / pads.length;
    
    // Calculate coherence (variance-based)
    const variance = pads.reduce((sum, p) => sum + Math.pow(p.nu - avgNu, 2), 0) / pads.length;
    const coherence = Math.max(0, 1 - Math.sqrt(variance) * 2);
    
    // Count states
    const stateCounts: Record<DimensionalState, number> = {
      POLLY: 0, QUASI: 0, DEMI: 0, COLLAPSED: 0
    };
    for (const pad of pads) {
      stateCounts[pad.dimensionalState]++;
    }
    
    // Find dominant state
    let dominantState: DimensionalState = 'COLLAPSED';
    let maxCount = 0;
    for (const [state, count] of Object.entries(stateCounts)) {
      if (count > maxCount) {
        maxCount = count;
        dominantState = state as DimensionalState;
      }
    }
    
    return {
      id: swarmId,
      name: swarm.name,
      padIds: Array.from(padIds),
      avgNu,
      coherence,
      dominantState,
      lastSync: Date.now(),
      activePads: stateCounts.POLLY + stateCounts.QUASI,
      collapsedPads: stateCounts.COLLAPSED
    };
  }
  
  /**
   * Synchronize swarm - update coherence scores
   */
  public syncSwarm(swarmId: string): void {
    const state = this.getSwarmState(swarmId);
    if (!state) return;
    
    const pads = this.getSwarmPads(swarmId);
    
    for (const pad of pads) {
      // Update coherence based on distance from swarm average
      const distance = Math.abs(pad.nu - state.avgNu);
      pad.coherenceScore = Math.max(0, 1 - distance);
      pad.lastSwarmSync = Date.now();
    }
  }
  
  /**
   * Step flux dynamics using ODE
   * dν/dt = α(ν_target - ν) - β*decay + γ*coherence_boost
   */
  public stepFluxODE(swarmId: string): void {
    const swarm = this.swarms.get(swarmId);
    const state = this.getSwarmState(swarmId);
    if (!swarm || !state) return;
    
    const pads = this.getSwarmPads(swarmId);
    const { alpha, beta, gamma, dt } = this.fluxParams;
    
    for (const pad of pads) {
      // Target is swarm average (attraction to consensus)
      const nuTarget = pad.targetNu ?? state.avgNu;
      
      // ODE: dν/dt = α(ν_target - ν) - β*decay + γ*coherence
      const attraction = alpha * (nuTarget - pad.nu);
      const decay = beta * swarm.fluxDecayRate;
      const coherenceBoost = gamma * state.coherence * (pad.coherenceScore > 0.5 ? 1 : -1);
      
      const dNu = (attraction - decay + coherenceBoost) * dt;
      
      // Update flux
      pad.nu = Math.max(0, Math.min(1, pad.nu + dNu));
      pad.dimensionalState = getDimensionalState(pad.nu);
      pad.fluxRate = Math.abs(dNu);
    }
  }
  
  /**
   * Boost pad flux (e.g., after successful task)
   */
  public boostPadFlux(padId: string, amount: number = 0.1): void {
    const pad = this.padManager.getPad(padId);
    if (!pad) return;
    
    pad.nu = Math.min(1, pad.nu + amount);
    pad.dimensionalState = getDimensionalState(pad.nu);
  }
  
  /**
   * Decay pad flux (e.g., after failure or inactivity)
   */
  public decayPadFlux(padId: string, amount: number = 0.05): void {
    const pad = this.padManager.getPad(padId);
    if (!pad) return;
    
    pad.nu = Math.max(0, pad.nu - amount);
    pad.dimensionalState = getDimensionalState(pad.nu);
  }
  
  /**
   * Collapse pad (set to COLLAPSED state)
   */
  public collapsePad(padId: string): void {
    const pad = this.padManager.getPad(padId);
    if (!pad) return;
    
    pad.nu = 0;
    pad.dimensionalState = 'COLLAPSED';
    pad.fluxRate = 0;
    pad.targetNu = undefined;
  }
  
  /**
   * Revive collapsed pad
   */
  public revivePad(padId: string, targetNu: number = 0.5): void {
    const pad = this.padManager.getPad(padId);
    if (!pad) return;
    
    pad.nu = 0.1; // Start at DEMI
    pad.targetNu = targetNu;
    pad.fluxRate = 0.02;
    pad.dimensionalState = 'DEMI';
  }
  
  /**
   * Start automatic sync for swarm
   */
  public startAutoSync(swarmId: string): void {
    const swarm = this.swarms.get(swarmId);
    if (!swarm) return;
    
    // Clear existing interval
    this.stopAutoSync(swarmId);
    
    const interval = setInterval(() => {
      this.syncSwarm(swarmId);
      this.stepFluxODE(swarmId);
    }, swarm.syncIntervalMs);
    
    this.syncIntervals.set(swarmId, interval);
  }
  
  /**
   * Stop automatic sync for swarm
   */
  public stopAutoSync(swarmId: string): void {
    const interval = this.syncIntervals.get(swarmId);
    if (interval) {
      clearInterval(interval);
      this.syncIntervals.delete(swarmId);
    }
  }
  
  /**
   * Get swarm statistics
   */
  public getSwarmStats(swarmId: string): {
    totalPads: number;
    byState: Record<DimensionalState, number>;
    byTier: Record<GovernanceTier, number>;
    avgCoherence: number;
    avgNu: number;
    healthScore: number;
  } | undefined {
    const pads = this.getSwarmPads(swarmId);
    if (pads.length === 0) return undefined;
    
    const byState: Record<DimensionalState, number> = {
      POLLY: 0, QUASI: 0, DEMI: 0, COLLAPSED: 0
    };
    const byTier: Record<GovernanceTier, number> = {
      KO: 0, AV: 0, RU: 0, CA: 0, UM: 0, DR: 0
    };
    
    let totalCoherence = 0;
    let totalNu = 0;
    
    for (const pad of pads) {
      byState[pad.dimensionalState]++;
      byTier[pad.tier]++;
      totalCoherence += pad.coherenceScore;
      totalNu += pad.nu;
    }
    
    const avgCoherence = totalCoherence / pads.length;
    const avgNu = totalNu / pads.length;
    
    // Health score: weighted combination
    const healthScore = (
      avgCoherence * 0.3 +
      avgNu * 0.3 +
      (byState.POLLY / pads.length) * 0.2 +
      (1 - byState.COLLAPSED / pads.length) * 0.2
    );
    
    return {
      totalPads: pads.length,
      byState,
      byTier,
      avgCoherence,
      avgNu,
      healthScore
    };
  }
  
  /**
   * Shutdown coordinator
   */
  public shutdown(): void {
    for (const swarmId of this.syncIntervals.keys()) {
      this.stopAutoSync(swarmId);
    }
  }
}
