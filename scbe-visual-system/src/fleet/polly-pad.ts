/**
 * PollyPad Management System
 *
 * PollyPads are dimensional staging areas where swarm members
 * maintain full presence (POLLY state) before engaging in tasks.
 * They serve as coordination points in the 6D PHDM space.
 *
 * @module fleet/polly-pad
 */

import {
  DimensionalState,
  GovernanceTier,
  SwarmMemberState,
  getDimensionalState,
  governanceToDimensionIndex,
} from './types';

/**
 * PollyPad configuration
 */
export interface PollyPadConfig {
  /** Maximum members allowed in pad */
  capacity: number;
  /** Minimum coherence required to enter */
  coherenceThreshold: number;
  /** Flux boost provided by pad */
  fluxBoost: number;
  /** Position in 6D space */
  position6D: number[];
}

/**
 * PollyPad instance representing a coordination point
 */
export interface PollyPad {
  id: string;
  name: string;
  governanceTier: GovernanceTier;
  config: PollyPadConfig;
  members: Set<string>;
  createdAt: number;
  active: boolean;
}

/**
 * Default pad configuration
 */
export const DEFAULT_PAD_CONFIG: PollyPadConfig = {
  capacity: 6,
  coherenceThreshold: 0.7,
  fluxBoost: 0.1,
  position6D: [0, 0, 0, 0, 0, 0],
};

/**
 * PollyPad Manager - Handles creation and management of PollyPads
 */
export class PollyPadManager {
  private pads: Map<string, PollyPad> = new Map();
  private memberPadMap: Map<string, string> = new Map();
  private eventListeners: Array<(event: PollyPadEvent) => void> = [];

  /**
   * Create a new PollyPad
   */
  createPad(
    name: string,
    governanceTier: GovernanceTier,
    config: Partial<PollyPadConfig> = {}
  ): PollyPad {
    const id = `pad_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // Position pad at the governance tier's dimensional vertex
    const dimIndex = governanceToDimensionIndex(governanceTier);
    const position6D = [0, 0, 0, 0, 0, 0];
    position6D[dimIndex] = 1.0; // Place at unit distance in governance dimension

    const pad: PollyPad = {
      id,
      name,
      governanceTier,
      config: {
        ...DEFAULT_PAD_CONFIG,
        ...config,
        position6D: config.position6D || position6D,
      },
      members: new Set(),
      createdAt: Date.now(),
      active: true,
    };

    this.pads.set(id, pad);
    this.emitEvent({ type: 'pad_created', padId: id, timestamp: Date.now() });

    return pad;
  }

  /**
   * Get a pad by ID
   */
  getPad(padId: string): PollyPad | undefined {
    return this.pads.get(padId);
  }

  /**
   * Get all active pads
   */
  getActivePads(): PollyPad[] {
    return Array.from(this.pads.values()).filter((p) => p.active);
  }

  /**
   * Get pads by governance tier
   */
  getPadsByTier(tier: GovernanceTier): PollyPad[] {
    return Array.from(this.pads.values()).filter(
      (p) => p.active && p.governanceTier === tier
    );
  }

  /**
   * Add a member to a pad
   */
  addMember(padId: string, member: SwarmMemberState): boolean {
    const pad = this.pads.get(padId);
    if (!pad || !pad.active) {
      return false;
    }

    // Check capacity
    if (pad.members.size >= pad.config.capacity) {
      this.emitEvent({
        type: 'member_rejected',
        padId,
        memberId: member.id,
        reason: 'capacity_full',
        timestamp: Date.now(),
      });
      return false;
    }

    // Check coherence threshold
    if (member.coherence < pad.config.coherenceThreshold) {
      this.emitEvent({
        type: 'member_rejected',
        padId,
        memberId: member.id,
        reason: 'coherence_insufficient',
        timestamp: Date.now(),
      });
      return false;
    }

    // Remove from previous pad if any
    const previousPadId = this.memberPadMap.get(member.id);
    if (previousPadId) {
      this.removeMember(previousPadId, member.id);
    }

    pad.members.add(member.id);
    this.memberPadMap.set(member.id, padId);

    this.emitEvent({
      type: 'member_joined',
      padId,
      memberId: member.id,
      timestamp: Date.now(),
    });

    return true;
  }

  /**
   * Remove a member from a pad
   */
  removeMember(padId: string, memberId: string): boolean {
    const pad = this.pads.get(padId);
    if (!pad) {
      return false;
    }

    if (pad.members.has(memberId)) {
      pad.members.delete(memberId);
      this.memberPadMap.delete(memberId);

      this.emitEvent({
        type: 'member_left',
        padId,
        memberId,
        timestamp: Date.now(),
      });

      return true;
    }

    return false;
  }

  /**
   * Get the pad a member is currently in
   */
  getMemberPad(memberId: string): PollyPad | undefined {
    const padId = this.memberPadMap.get(memberId);
    return padId ? this.pads.get(padId) : undefined;
  }

  /**
   * Calculate flux boost for a member based on pad membership
   */
  calculateFluxBoost(memberId: string): number {
    const pad = this.getMemberPad(memberId);
    if (!pad) {
      return 0;
    }

    // Boost scales with number of members (collaboration effect)
    const memberCount = pad.members.size;
    const collaborationFactor = Math.log2(memberCount + 1) / Math.log2(pad.config.capacity + 1);

    return pad.config.fluxBoost * (1 + collaborationFactor);
  }

  /**
   * Calculate coherence boost from pad interaction
   */
  calculateCoherenceBoost(memberId: string): number {
    const pad = this.getMemberPad(memberId);
    if (!pad || pad.members.size <= 1) {
      return 0;
    }

    // Coherence boost from nearby members
    const memberCount = pad.members.size;
    return 0.05 * (memberCount - 1);
  }

  /**
   * Deactivate a pad
   */
  deactivatePad(padId: string): void {
    const pad = this.pads.get(padId);
    if (!pad) {
      return;
    }

    // Remove all members
    for (const memberId of pad.members) {
      this.memberPadMap.delete(memberId);
    }
    pad.members.clear();
    pad.active = false;

    this.emitEvent({
      type: 'pad_deactivated',
      padId,
      timestamp: Date.now(),
    });
  }

  /**
   * Get pad statistics
   */
  getStatistics(): PollyPadStatistics {
    const activePads = this.getActivePads();
    const totalMembers = Array.from(this.memberPadMap.keys()).length;

    const tierDistribution: Record<GovernanceTier, number> = {
      KO: 0,
      AV: 0,
      RU: 0,
      CA: 0,
      UM: 0,
      DR: 0,
    };

    for (const pad of activePads) {
      tierDistribution[pad.governanceTier]++;
    }

    return {
      totalPads: this.pads.size,
      activePads: activePads.length,
      totalMembers,
      averageOccupancy:
        activePads.length > 0
          ? totalMembers / activePads.reduce((sum, p) => sum + p.config.capacity, 0)
          : 0,
      tierDistribution,
    };
  }

  /**
   * Subscribe to pad events
   */
  onEvent(listener: (event: PollyPadEvent) => void): () => void {
    this.eventListeners.push(listener);
    return () => {
      const index = this.eventListeners.indexOf(listener);
      if (index >= 0) {
        this.eventListeners.splice(index, 1);
      }
    };
  }

  private emitEvent(event: PollyPadEvent): void {
    for (const listener of this.eventListeners) {
      listener(event);
    }
  }
}

/**
 * PollyPad event types
 */
export interface PollyPadEvent {
  type:
    | 'pad_created'
    | 'pad_deactivated'
    | 'member_joined'
    | 'member_left'
    | 'member_rejected';
  padId: string;
  memberId?: string;
  reason?: string;
  timestamp: number;
}

/**
 * PollyPad statistics
 */
export interface PollyPadStatistics {
  totalPads: number;
  activePads: number;
  totalMembers: number;
  averageOccupancy: number;
  tierDistribution: Record<GovernanceTier, number>;
}
