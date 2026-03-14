/**
 * @file zoom.test.ts
 * @module tests/conference
 *
 * Tests for Zoom integration and live event services.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ZoomService } from '../../conference-app/src/api/services/zoom';
import { liveEventBus } from '../../conference-app/src/api/services/liveEvents';

describe('ZoomService', () => {
  let service: ZoomService;

  beforeEach(() => {
    // Clear env vars so we get simulated mode
    delete process.env.ZOOM_ACCOUNT_ID;
    delete process.env.ZOOM_CLIENT_ID;
    delete process.env.ZOOM_CLIENT_SECRET;
    service = new ZoomService();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('reports not configured without env vars', () => {
    expect(service.isConfigured()).toBe(false);
  });

  it('creates a simulated meeting when not configured', async () => {
    const meeting = await service.createMeeting(
      'conf-123',
      'Test Conference',
      '2026-03-15T14:00:00Z',
      120,
      'curator@example.com'
    );

    expect(meeting.id).toBeGreaterThan(0);
    expect(meeting.joinUrl).toContain('simulated');
    expect(meeting.startUrl).toContain('simulated');
    expect(meeting.password).toBeTruthy();
    expect(meeting.topic).toBe('Test Conference');
    expect(meeting.hostEmail).toBe('curator@example.com');
  });

  it('retrieves created meeting by conference ID', async () => {
    await service.createMeeting('conf-456', 'Test', '2026-03-15T14:00:00Z', 60, 'a@b.com');

    const meeting = service.getMeeting('conf-456');
    expect(meeting).not.toBeNull();
    expect(meeting!.topic).toBe('Test');
  });

  it('returns null for non-existent conference', () => {
    expect(service.getMeeting('nonexistent')).toBeNull();
    expect(service.getJoinUrl('nonexistent')).toBeNull();
    expect(service.getStartUrl('nonexistent')).toBeNull();
  });

  it('provides separate join and start URLs', async () => {
    await service.createMeeting('conf-789', 'Test', '2026-03-15T14:00:00Z', 60, 'a@b.com');

    const joinUrl = service.getJoinUrl('conf-789');
    const startUrl = service.getStartUrl('conf-789');

    expect(joinUrl).toContain('/j/');
    expect(startUrl).toContain('/s/');
    expect(joinUrl).not.toBe(startUrl);
  });

  it('rejects malformed host emails before building the Zoom path', async () => {
    await expect(
      service.createMeeting('conf-900', 'Test', '2026-03-15T14:00:00Z', 60, '../../users/me')
    ).rejects.toThrow(/Invalid Zoom host email/);
  });

  it('encodes the validated host email in the Zoom API path', async () => {
    process.env.ZOOM_ACCOUNT_ID = 'acct';
    process.env.ZOOM_CLIENT_ID = 'client';
    process.env.ZOOM_CLIENT_SECRET = 'secret';
    service = new ZoomService();

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ access_token: 'token', expires_in: 3600 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 123456789,
          join_url: 'https://zoom.us/j/123456789',
          start_url: 'https://zoom.us/s/123456789',
          password: 'secretpw',
        }),
      });

    vi.stubGlobal('fetch', fetchMock as typeof fetch);

    const meeting = await service.createMeeting(
      'conf-901',
      'Encoded Test',
      '2026-03-15T14:00:00Z',
      60,
      'Curator+Ops@Example.com'
    );

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][0]).toBe(
      'https://api.zoom.us/v2/users/curator%2Bops%40example.com/meetings'
    );
    expect(meeting.hostEmail).toBe('curator+ops@example.com');
  });
});

describe('LiveEventBus', () => {
  it('emits events to subscribers', () => {
    const received: any[] = [];
    const unsub = liveEventBus.subscribe('conf-A', (event) => {
      received.push(event);
    });

    liveEventBus.emitChat('conf-A', 'user-1', 'Alice', 'Hello!');
    expect(received).toHaveLength(1);
    expect(received[0].type).toBe('chat:message');
    expect(received[0].payload.message).toBe('Hello!');

    unsub();
  });

  it('does not leak events between conferences', () => {
    const receivedA: any[] = [];
    const receivedB: any[] = [];

    const unsubA = liveEventBus.subscribe('conf-A', (e) => receivedA.push(e));
    const unsubB = liveEventBus.subscribe('conf-B', (e) => receivedB.push(e));

    liveEventBus.emitReaction('conf-A', 'user-1', 'fire');
    expect(receivedA).toHaveLength(1);
    expect(receivedB).toHaveLength(0);

    unsubA();
    unsubB();
  });

  it('stores recent events for late joiners', () => {
    // Emit some events
    liveEventBus.emitChat('conf-C', 'u1', 'Bob', 'msg 1');
    liveEventBus.emitChat('conf-C', 'u2', 'Eve', 'msg 2');

    const recent = liveEventBus.getRecent('conf-C', 10);
    expect(recent.length).toBeGreaterThanOrEqual(2);
  });

  it('emitNewCommit broadcasts commit:new event', () => {
    const received: any[] = [];
    const unsub = liveEventBus.subscribe('conf-D', (e) => received.push(e));

    liveEventBus.emitNewCommit('conf-D', 'Alice Investor', 'CoolProject', 25_000, '25k');

    expect(received).toHaveLength(1);
    expect(received[0].type).toBe('commit:new');
    expect(received[0].payload.amount).toBe(25_000);
    expect(received[0].payload.investorName).toBe('Alice Investor');

    unsub();
  });

  it('emitTickerUpdate broadcasts commit:ticker event', () => {
    const received: any[] = [];
    const unsub = liveEventBus.subscribe('conf-E', (e) => received.push(e));

    const ticker = [
      { projectId: 'p1', totalAmount: 50_000, commitCount: 3 },
      { projectId: 'p2', totalAmount: 25_000, commitCount: 1 },
    ];
    liveEventBus.emitTickerUpdate('conf-E', ticker);

    expect(received).toHaveLength(1);
    expect(received[0].type).toBe('commit:ticker');
    expect(received[0].payload.ticker).toEqual(ticker);

    unsub();
  });

  it('emitGovernanceAlert broadcasts governance:alert event', () => {
    const received: any[] = [];
    const unsub = liveEventBus.subscribe('conf-F', (e) => received.push(e));

    liveEventBus.emitGovernanceAlert('conf-F', 'proj-1', 'Suspicious link detected', 'high');

    expect(received).toHaveLength(1);
    expect(received[0].type).toBe('governance:alert');
    expect(received[0].payload.severity).toBe('high');

    unsub();
  });

  it('emitPhaseUpdate broadcasts phase:update event', () => {
    const received: any[] = [];
    const unsub = liveEventBus.subscribe('conf-G', (e) => received.push(e));

    liveEventBus.emitPhaseUpdate('conf-G', [
      { tongue: 'KO', phase: 0, score: 0.95 },
      { tongue: 'DR', phase: 300, score: 0.82 },
    ]);

    expect(received).toHaveLength(1);
    expect(received[0].type).toBe('phase:update');
    expect(received[0].payload.agents).toHaveLength(2);

    unsub();
  });

  it('unsubscribe stops receiving events', () => {
    const received: any[] = [];
    const unsub = liveEventBus.subscribe('conf-H', (e) => received.push(e));

    liveEventBus.emitChat('conf-H', 'u1', 'A', 'first');
    unsub();
    liveEventBus.emitChat('conf-H', 'u1', 'A', 'second');

    expect(received).toHaveLength(1);
  });

  it('reports correct subscriber count', () => {
    expect(liveEventBus.subscriberCount('conf-I')).toBe(0);

    const unsub1 = liveEventBus.subscribe('conf-I', () => {});
    const unsub2 = liveEventBus.subscribe('conf-I', () => {});
    expect(liveEventBus.subscriberCount('conf-I')).toBe(2);

    unsub1();
    expect(liveEventBus.subscriberCount('conf-I')).toBe(1);

    unsub2();
    expect(liveEventBus.subscriberCount('conf-I')).toBe(0);
  });
});
