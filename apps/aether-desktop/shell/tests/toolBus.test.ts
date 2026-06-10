import { describe, it, expect, vi } from 'vitest';
import { createToolBus } from '../src/toolBus';
import type { BackendClient, OperationResult } from '../src/BackendClient';

function mockClient(output: Record<string, unknown> = {}): BackendClient {
  return {
    runOp: vi.fn().mockResolvedValue({
      request_id: 'r1',
      ok: true,
      output,
      duration_ms: 1,
    } satisfies OperationResult),
    subscribeEvents: vi.fn(),
  };
}

describe('createToolBus', () => {
  it('lists all built-in tools sorted by name', () => {
    const bus = createToolBus(mockClient());
    const names = bus.listTools().map((t) => t.name);
    expect(names).toContain('agent.plan');
    expect(names).toContain('echo');
    expect(names).toContain('fs.list');
    expect(names).toContain('fs.read');
    expect(names).toContain('fs.write');
    expect(names).toContain('hash.sha256');
    expect(names).toContain('json.format');
    expect(names).toContain('math.calculate');
    expect(names).toContain('text.count');
    // sorted
    expect(names).toEqual([...names].sort());
  });

  it('throws for unknown tool', async () => {
    const bus = createToolBus(mockClient());
    await expect(bus.callTool('no.such.tool', {})).rejects.toThrow('Unknown tool: no.such.tool');
  });

  // ── json.format ─────────────────────────────────────────────────────────

  it('json.format pretty-prints valid JSON', async () => {
    const bus = createToolBus(mockClient());
    expect(await bus.callTool('json.format', { input: '{"a":1}' })).toBe('{\n  "a": 1\n}');
  });

  it('json.format throws on invalid JSON', async () => {
    const bus = createToolBus(mockClient());
    await expect(bus.callTool('json.format', { input: 'not-json' })).rejects.toThrow();
  });

  // ── hash.sha256 ──────────────────────────────────────────────────────────

  it('hash.sha256 returns 64-char lowercase hex', async () => {
    const bus = createToolBus(mockClient());
    const hash = (await bus.callTool('hash.sha256', { input: 'hello' })) as string;
    expect(hash).toHaveLength(64);
    expect(hash).toMatch(/^[0-9a-f]+$/);
  });

  it('hash.sha256 is deterministic', async () => {
    const bus = createToolBus(mockClient());
    const a = await bus.callTool('hash.sha256', { input: 'scbe' });
    const b = await bus.callTool('hash.sha256', { input: 'scbe' });
    expect(a).toBe(b);
  });

  // ── math.calculate ───────────────────────────────────────────────────────

  it('math.calculate evaluates arithmetic', async () => {
    const bus = createToolBus(mockClient());
    expect(await bus.callTool('math.calculate', { expr: '2 + 3 * 4' })).toBe(14);
  });

  it('math.calculate rejects non-arithmetic input', async () => {
    const bus = createToolBus(mockClient());
    await expect(bus.callTool('math.calculate', { expr: 'process.exit(1)' })).rejects.toThrow(
      'Invalid expression'
    );
  });

  // ── text.count ───────────────────────────────────────────────────────────

  it('text.count returns correct counts', async () => {
    const bus = createToolBus(mockClient());
    const r = (await bus.callTool('text.count', { text: 'hello world\nfoo' })) as Record<
      string,
      number
    >;
    expect(r['chars']).toBe(15);
    expect(r['words']).toBe(3);
    expect(r['lines']).toBe(2);
  });

  it('text.count handles empty string', async () => {
    const bus = createToolBus(mockClient());
    const r = (await bus.callTool('text.count', { text: '' })) as Record<string, number>;
    expect(r['words']).toBe(0);
    expect(r['chars']).toBe(0);
  });

  // ── virtual filesystem ───────────────────────────────────────────────────

  it('fs.write and fs.read round-trip', async () => {
    const bus = createToolBus(mockClient());
    await bus.callTool('fs.write', { path: '/tmp/hello.txt', content: 'world' });
    expect(await bus.callTool('fs.read', { path: '/tmp/hello.txt' })).toBe('world');
  });

  it('fs.list returns written paths sorted', async () => {
    const bus = createToolBus(mockClient());
    await bus.callTool('fs.write', { path: '/b.txt', content: '' });
    await bus.callTool('fs.write', { path: '/a.txt', content: '' });
    const list = (await bus.callTool('fs.list', {})) as string[];
    expect(list).toContain('/a.txt');
    expect(list).toContain('/b.txt');
    expect(list.indexOf('/a.txt')).toBeLessThan(list.indexOf('/b.txt'));
  });

  it('fs.read throws for missing file', async () => {
    const bus = createToolBus(mockClient());
    await expect(bus.callTool('fs.read', { path: '/nope.txt' })).rejects.toThrow(
      'File not found: /nope.txt'
    );
  });

  it('fs.write returns path and byte count', async () => {
    const bus = createToolBus(mockClient());
    const r = (await bus.callTool('fs.write', { path: '/x.txt', content: 'hi' })) as Record<
      string,
      unknown
    >;
    expect(r['path']).toBe('/x.txt');
    expect(r['bytes']).toBe(2);
  });

  // ── backend-delegated ────────────────────────────────────────────────────

  it('echo calls runOp with op=echo and returns output', async () => {
    const client = mockClient({ echo: 'hi', op: 'echo' });
    const bus = createToolBus(client);
    const result = await bus.callTool('echo', { msg: 'hi' });
    expect(client.runOp).toHaveBeenCalledOnce();
    const req = (client.runOp as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(req.op).toBe('echo');
    expect(result).toEqual({ echo: 'hi', op: 'echo' });
  });

  it('echo throws when backend returns ok=false', async () => {
    const client: BackendClient = {
      runOp: vi.fn().mockResolvedValue({
        request_id: 'r1',
        ok: false,
        error: { code: 'DENY', message: 'denied' },
        duration_ms: 1,
      } satisfies OperationResult),
      subscribeEvents: vi.fn(),
    };
    const bus = createToolBus(client);
    await expect(bus.callTool('echo', { msg: 'x' })).rejects.toThrow('denied');
  });

  // ── register ─────────────────────────────────────────────────────────────

  it('register adds a custom tool callable via callTool', async () => {
    const bus = createToolBus(mockClient());
    bus.register({
      name: 'custom.greet',
      description: 'test',
      params: [],
      async run() {
        return 'hello from custom';
      },
    });
    expect(await bus.callTool('custom.greet', {})).toBe('hello from custom');
    expect(bus.listTools().map((t) => t.name)).toContain('custom.greet');
  });
});
