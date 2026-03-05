/**
 * @file useLiveEvents.ts
 * @module conference/frontend/hooks
 *
 * Hook for consuming Server-Sent Events from the live conference stream.
 * Auto-reconnects on disconnect. Provides typed event handlers.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import type { LiveEvent, LiveEventType } from '../../shared/types/index.js';

interface LiveEventsState {
  connected: boolean;
  viewerCount: number;
  events: LiveEvent[];
  chatMessages: Array<{ userId: string; displayName: string; message: string; timestamp: string }>;
  reactions: Array<{ emoji: string; timestamp: string }>;
  ticker: Array<{ projectId: string; totalAmount: number; commitCount: number }>;
  latestCommit: { investorName: string; projectTitle: string; amount: number; tier: string } | null;
}

export function useLiveEvents(conferenceId: string | undefined, token: string | null) {
  const [state, setState] = useState<LiveEventsState>({
    connected: false,
    viewerCount: 0,
    events: [],
    chatMessages: [],
    reactions: [],
    ticker: [],
    latestCommit: null,
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (!conferenceId || !token) return;

    // SSE doesn't support custom headers, so we pass the token as a query param
    const url = `/api/zoom/conferences/${conferenceId}/events?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setState(prev => ({ ...prev, connected: true }));
    };

    es.onerror = () => {
      setState(prev => ({ ...prev, connected: false }));
      // Auto-reconnect is handled by the browser's EventSource implementation
    };

    // Viewer count
    es.addEventListener('viewers', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setState(prev => ({ ...prev, viewerCount: data.count }));
    });

    // New soft-commit
    es.addEventListener('commit:new', (e: MessageEvent) => {
      const event: LiveEvent = JSON.parse(e.data);
      const payload = event.payload as any;
      setState(prev => ({
        ...prev,
        events: [...prev.events.slice(-99), event],
        latestCommit: {
          investorName: payload.investorName,
          projectTitle: payload.projectTitle,
          amount: payload.amount,
          tier: payload.tier,
        },
      }));
    });

    // Ticker update
    es.addEventListener('commit:ticker', (e: MessageEvent) => {
      const event: LiveEvent = JSON.parse(e.data);
      const payload = event.payload as any;
      setState(prev => ({ ...prev, ticker: payload.ticker }));
    });

    // Chat messages
    es.addEventListener('chat:message', (e: MessageEvent) => {
      const event: LiveEvent = JSON.parse(e.data);
      const payload = event.payload as any;
      setState(prev => ({
        ...prev,
        chatMessages: [...prev.chatMessages.slice(-99), {
          userId: payload.userId,
          displayName: payload.displayName,
          message: payload.message,
          timestamp: event.timestamp,
        }],
      }));
    });

    // Reactions
    es.addEventListener('reaction', (e: MessageEvent) => {
      const event: LiveEvent = JSON.parse(e.data);
      const payload = event.payload as any;
      setState(prev => ({
        ...prev,
        reactions: [...prev.reactions.slice(-20), {
          emoji: payload.emoji,
          timestamp: event.timestamp,
        }],
      }));
    });

    // Slot transitions
    es.addEventListener('slot:start', (e: MessageEvent) => {
      const event: LiveEvent = JSON.parse(e.data);
      setState(prev => ({ ...prev, events: [...prev.events.slice(-99), event] }));
    });

    es.addEventListener('slot:end', (e: MessageEvent) => {
      const event: LiveEvent = JSON.parse(e.data);
      setState(prev => ({ ...prev, events: [...prev.events.slice(-99), event] }));
    });

    // Governance alerts
    es.addEventListener('governance:alert', (e: MessageEvent) => {
      const event: LiveEvent = JSON.parse(e.data);
      setState(prev => ({ ...prev, events: [...prev.events.slice(-99), event] }));
    });

    return () => {
      es.close();
    };
  }, [conferenceId, token]);

  useEffect(() => {
    const cleanup = connect();
    return () => {
      cleanup?.();
      eventSourceRef.current?.close();
    };
  }, [connect]);

  return state;
}
