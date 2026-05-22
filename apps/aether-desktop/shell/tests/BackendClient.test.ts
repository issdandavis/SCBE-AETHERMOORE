import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createBackendClient, SCHEMA_VERSION } from '../src/BackendClient';

describe('BackendClient', () => {
    beforeEach(() => {
        vi.stubGlobal('fetch', vi.fn());
        const MockWS = vi.fn(function (this: Record<string, unknown>) {
            this['onmessage'] = null;
            this['close'] = vi.fn();
        });
        vi.stubGlobal('WebSocket', MockWS);
    });

    it('runOp POSTs to /v1/op with the correct body', async () => {
        const mockResult = { request_id: 'r1', ok: true, output: {}, duration_ms: 1 };
        (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
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

        expect(global.fetch).toHaveBeenCalledWith(
            'http://localhost:8001/v1/op',
            expect.objectContaining({ method: 'POST' })
        );
        expect(result.ok).toBe(true);
    });

    it('subscribeEvents opens a WebSocket to /v1/events', () => {
        const client = createBackendClient('http://localhost:8001');
        const unsub = client.subscribeEvents('r2', () => {}, () => {});
        expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8001/v1/events?request_id=r2');
        unsub();
    });
});
