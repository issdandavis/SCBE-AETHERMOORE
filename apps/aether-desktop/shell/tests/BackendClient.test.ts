/// <reference types="vite/client" />

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createBackendClient, SCHEMA_VERSION } from '../src/BackendClient';

let fetchMock: ReturnType<typeof vi.fn>;
let WebSocketMock: ReturnType<typeof vi.fn>;

describe('BackendClient', () => {
  beforeEach(() => {
    fetchMock = vi.fn();
    WebSocketMock = vi.fn(function (this: Record<string, unknown>) {
      this['onmessage'] = null;
      this['close'] = vi.fn();
    });
    vi.stubGlobal('fetch', fetchMock);
    vi.stubGlobal('WebSocket', WebSocketMock);
  });

  it('runOp POSTs to /v1/op with the correct body', async () => {
    const mockResult = { request_id: 'r1', ok: true, output: {}, duration_ms: 1 };
    fetchMock.mockResolvedValue({
      json: async () => mockResult,
    });

    const client = createBackendClient('http://localhost:8001');
    const result = await client.runOp({
      schema_version: SCHEMA_VERSION,
      op: 'echo',
      args: { msg: 'hi' },
      request_id: 'r1',
      origin: { kind: 'app', id: 'test' },
      privacy: 'local_only',
    });

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8001/v1/op',
      expect.objectContaining({ method: 'POST' })
    );
    expect(result.ok).toBe(true);
  });

  it('subscribeEvents opens a WebSocket to /v1/events', () => {
    const client = createBackendClient('http://localhost:8001');
    const subscription = client.subscribeEvents(
      'r2',
      () => {},
      () => {}
    );
    expect(WebSocketMock).toHaveBeenCalledWith('ws://localhost:8001/v1/events?request_id=r2');
    subscription.unsubscribe();
  });

  it('subscribeEvents exposes a readiness promise before dispatch', async () => {
    const client = createBackendClient('http://localhost:8001');
    const subscription = client.subscribeEvents(
      'r3',
      () => {},
      () => {}
    );
    const wsInstance = WebSocketMock.mock.instances[0] as Record<string, unknown>;

    expect(typeof wsInstance['onopen']).toBe('function');
    (wsInstance['onopen'] as () => void)();

    await expect(subscription.ready).resolves.toBeUndefined();
    subscription.unsubscribe();
  });

  it('keeps shell apps from bypassing BackendClient with direct fetch calls', () => {
    const sources = import.meta.glob('../src/**/*.{ts,tsx}', {
      query: '?raw',
      import: 'default',
      eager: true,
    }) as Record<string, string>;
    const offenders = Object.entries(sources)
      .filter(([path]) => !path.endsWith('/BackendClient.ts'))
      .filter(([, text]) => text.includes('fetch(') || text.includes('new WebSocket('))
      .map(([path]) => path);

    expect(offenders).toEqual([]);
  });
});
