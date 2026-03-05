/**
 * @file liveEvents.ts
 * @module conference/api/services
 *
 * WebSocket-based real-time event layer for live conferences.
 *
 * Broadcasts events to all connected clients in a conference room:
 * - Soft-commit ticker updates (FOMO-inducing live feed)
 * - Slot transitions (start/end of presentations)
 * - Chat messages and reactions
 * - Governance alerts (mid-stream QUARANTINE triggers)
 * - HYDRA phase updates (agent synchronization visualization)
 *
 * Uses native Node WebSocket (ws) or Server-Sent Events fallback.
 */

import type { LiveEvent, LiveEventType } from '../../shared/types/index.js';

// ═══════════════════════════════════════════════════════════════
// Event Bus (in-process pub/sub)
// ═══════════════════════════════════════════════════════════════

type EventHandler = (event: LiveEvent) => void;

class LiveEventBus {
  /** conferenceId -> Set of handlers */
  private rooms: Map<string, Set<EventHandler>> = new Map();
  /** Recent events per conference for late-joiners */
  private recentEvents: Map<string, LiveEvent[]> = new Map();
  private readonly MAX_RECENT = 50;

  /**
   * Subscribe to events for a conference room.
   * Returns an unsubscribe function.
   */
  subscribe(conferenceId: string, handler: EventHandler): () => void {
    if (!this.rooms.has(conferenceId)) {
      this.rooms.set(conferenceId, new Set());
    }
    this.rooms.get(conferenceId)!.add(handler);

    return () => {
      this.rooms.get(conferenceId)?.delete(handler);
      if (this.rooms.get(conferenceId)?.size === 0) {
        this.rooms.delete(conferenceId);
      }
    };
  }

  /**
   * Broadcast an event to all subscribers in a conference room.
   */
  emit(event: LiveEvent): void {
    // Store in recent buffer
    if (!this.recentEvents.has(event.conferenceId)) {
      this.recentEvents.set(event.conferenceId, []);
    }
    const recent = this.recentEvents.get(event.conferenceId)!;
    recent.push(event);
    if (recent.length > this.MAX_RECENT) {
      recent.shift();
    }

    // Dispatch to handlers
    const handlers = this.rooms.get(event.conferenceId);
    if (handlers) {
      for (const handler of handlers) {
        try {
          handler(event);
        } catch (e) {
          console.error('[liveEvents] Handler error:', e);
        }
      }
    }
  }

  /**
   * Get recent events for late-joining clients.
   */
  getRecent(conferenceId: string, limit: number = 20): LiveEvent[] {
    const recent = this.recentEvents.get(conferenceId) ?? [];
    return recent.slice(-limit);
  }

  /**
   * Get subscriber count for a conference room.
   */
  subscriberCount(conferenceId: string): number {
    return this.rooms.get(conferenceId)?.size ?? 0;
  }

  // ═══════════════════════════════════════════════════════════
  // Convenience emitters
  // ═══════════════════════════════════════════════════════════

  emitSlotStart(conferenceId: string, slotId: string, projectTitle: string): void {
    this.emit({
      type: 'slot:start',
      conferenceId,
      timestamp: new Date().toISOString(),
      payload: { slotId, projectTitle },
    });
  }

  emitSlotEnd(conferenceId: string, slotId: string, projectTitle: string): void {
    this.emit({
      type: 'slot:end',
      conferenceId,
      timestamp: new Date().toISOString(),
      payload: { slotId, projectTitle },
    });
  }

  emitNewCommit(
    conferenceId: string,
    investorName: string,
    projectTitle: string,
    amount: number,
    tier: string
  ): void {
    this.emit({
      type: 'commit:new',
      conferenceId,
      timestamp: new Date().toISOString(),
      payload: { investorName, projectTitle, amount, tier },
    });
  }

  emitTickerUpdate(
    conferenceId: string,
    ticker: Array<{ projectId: string; totalAmount: number; commitCount: number }>
  ): void {
    this.emit({
      type: 'commit:ticker',
      conferenceId,
      timestamp: new Date().toISOString(),
      payload: { ticker },
    });
  }

  emitReaction(conferenceId: string, userId: string, emoji: string): void {
    this.emit({
      type: 'reaction',
      conferenceId,
      timestamp: new Date().toISOString(),
      payload: { userId, emoji },
    });
  }

  emitChat(conferenceId: string, userId: string, displayName: string, message: string): void {
    this.emit({
      type: 'chat:message',
      conferenceId,
      timestamp: new Date().toISOString(),
      payload: { userId, displayName, message },
    });
  }

  emitGovernanceAlert(conferenceId: string, projectId: string, alert: string, severity: string): void {
    this.emit({
      type: 'governance:alert',
      conferenceId,
      timestamp: new Date().toISOString(),
      payload: { projectId, alert, severity },
    });
  }

  emitPhaseUpdate(
    conferenceId: string,
    agents: Array<{ tongue: string; phase: number; score: number }>
  ): void {
    this.emit({
      type: 'phase:update',
      conferenceId,
      timestamp: new Date().toISOString(),
      payload: { agents },
    });
  }
}

/** Singleton event bus */
export const liveEventBus = new LiveEventBus();
