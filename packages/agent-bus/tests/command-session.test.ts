import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { CommandSession } from '../src/command-session.js';
import { createLocalEventResult } from '../src/local-event.js';

const roots: string[] = [];
function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-command-session-'));
  roots.push(root);
  fs.mkdirSync(path.join(root, 'folder with spaces'));
  return root;
}
afterEach(() => {
  for (const root of roots.splice(0)) {
    if (!path.resolve(root).startsWith(path.resolve(os.tmpdir()) + path.sep))
      throw new Error('Invalid fixture path');
    fs.rmSync(root, { recursive: true, force: true });
  }
});

describe('command session', () => {
  it('diagnoses the current directory, validates fields and preserves the queue', async () => {
    const root = fixture();
    const session = new CommandSession({
      cwd: root,
      diagnose: ({ cwd }) => ({ cwd, status: 'degraded' }),
    });
    expect((await session.dispatch({ id: 'cd-d', op: 'cd', path: 'folder with spaces' })).ok).toBe(
      true
    );
    const reply = await session.dispatch({ id: 'd', op: 'diagnose' });
    expect(reply).toMatchObject({
      ok: true,
      result: { status: 'degraded', cwd: fs.realpathSync(path.join(root, 'folder with spaces')) },
    });
    expect((await session.dispatch({ id: 'bad-d', op: 'diagnose', command: 'no' })).ok).toBe(false);
    expect((await session.dispatch({ id: 'next-d', op: 'status' })).ok).toBe(true);
    expect(
      (await new CommandSession({ cwd: root }).dispatch({ id: 'none', op: 'diagnose' })).error?.code
    ).toBe('diagnostics_unavailable');
  });
  it('orders delayed work, directory changes and geo context without changing process cwd', async () => {
    const root = fixture();
    const initialCwd = process.cwd();
    const seen: unknown[] = [];
    const session = new CommandSession({
      cwd: root,
      execute: async (command, context) => {
        await new Promise((resolve) => setTimeout(resolve, 15));
        seen.push({ command, ...context });
        return { success: true, stdout: command };
      },
    });
    const replies = await Promise.all([
      session.dispatch({ id: 'first', op: 'run', command: 'first' }),
      session.dispatch({ id: 'cd', op: 'cd', path: 'folder with spaces' }),
      session.dispatch({ id: 'geo', op: 'geo', task: 'compile and test the code' }),
      session.dispatch({ id: 'second', op: 'run', command: 'second' }),
    ]);
    expect(replies.map((r) => r.id)).toEqual(['first', 'cd', 'geo', 'second']);
    expect(replies.map((r) => r.session.sequence)).toEqual([1, 2, 3, 4]);
    expect(replies.every((r) => r.ok)).toBe(true);
    expect(seen[0]).toMatchObject({ cwd: fs.realpathSync(root), geo: null });
    expect(seen[1]).toMatchObject({
      cwd: fs.realpathSync(path.join(root, 'folder with spaces')),
      geo: { domain: 'CA' },
    });
    expect(process.cwd()).toBe(initialCwd);
    expect(replies[0].session.geo).toBeNull();
  });

  it('preserves cwd on failed cd and recovers after an executor exception', async () => {
    const root = fixture();
    const session = new CommandSession({
      cwd: root,
      execute: () => {
        throw new Error('executor stopped');
      },
    });
    const results = await Promise.all([
      session.dispatch({ id: 'bad-cd', op: 'cd', path: 'missing' }),
      session.dispatch({ id: 'bad-run', op: 'run', command: 'test' }),
      session.dispatch({ id: 'status', op: 'status' }),
    ]);
    expect(results.map((r) => r.ok)).toEqual([false, false, true]);
    expect(results[2].session.cwd).toBe(fs.realpathSync(root));
    expect(results[1].error?.message).toBe('executor stopped');
  });

  it('rejects duplicate request ids so agent correlation stays unambiguous', async () => {
    const session = new CommandSession({ cwd: fixture() });
    const first = await session.dispatch({ id: 'same-id', op: 'status' });
    const duplicate = await session.dispatch({ id: 'same-id', op: 'describe' });
    const next = await session.dispatch({ id: 'different-id', op: 'status' });
    expect(first.ok).toBe(true);
    expect(duplicate).toMatchObject({
      id: 'same-id',
      ok: false,
      error: { code: 'duplicate_request_id' },
    });
    expect(next.ok).toBe(true);
  });

  it('keeps ordered identity and sequence under a 500-request burst', async () => {
    const session = new CommandSession({ cwd: fixture() });
    const replies = await Promise.all(
      Array.from({ length: 500 }, (_, index) =>
        session.dispatch({ id: `burst-${index}`, op: 'status' })
      )
    );
    expect(replies.map((reply) => reply.id)).toEqual(
      Array.from({ length: 500 }, (_, index) => `burst-${index}`)
    );
    expect(replies.map((reply) => reply.session.sequence)).toEqual(
      Array.from({ length: 500 }, (_, index) => index + 1)
    );
  });

  it('returns real refusal and nonzero outcomes unchanged even when geo context is set', async () => {
    let calls = 0;
    const session = new CommandSession({
      cwd: fixture(),
      execute: () => {
        calls += 1;
        return { success: false, exit_code: 126, governance: { allowed: false } };
      },
    });
    await session.dispatch({ id: 'geo', op: 'geo', task: 'compile the code' });
    const result = await session.dispatch({
      id: 'blocked',
      op: 'run',
      command: 'harmless fixture',
    });
    expect(result.ok).toBe(false);
    expect(result.result).toMatchObject({ exit_code: 126, governance: { allowed: false } });
    expect(calls).toBe(1);
  });

  it.each([
    null,
    [],
    { id: 'bad', op: 'run', command: 'test', permission: 'sudo' },
    { id: 'bad', op: 'run', command: 'test', timeout_ms: 0 },
    { id: 'bad', op: 'run', command: 'test', timeout_ms: 300001 },
    { id: 'bad', op: 'run', command: 'test', timeout_ms: '30' },
    { id: 'bad', op: '__proto__' },
    { id: '', op: 'status' },
    { id: 'bad', op: 'bus', task: 'test', tool: 'unregistered' },
  ])('rejects invalid input before execution: %j', async (request) => {
    const session = new CommandSession({
      cwd: fixture(),
      execute: () => {
        throw new Error('must not execute');
      },
    });
    const reply = await session.dispatch(request);
    expect(reply.ok).toBe(false);
    expect(reply.error?.message).not.toBe('must not execute');
  });

  it('records offline bus intake for the geo task and can clear that context', async () => {
    const session = new CommandSession({ cwd: fixture(), recordEvent: createLocalEventResult });
    await session.dispatch({ id: 'geo', op: 'geo', task: 'review the compiler code' });
    const reply = await session.dispatch({ id: 'bus', op: 'bus' });
    expect(reply.ok).toBe(true);
    expect(reply.result).toMatchObject({
      receipt_id: expect.any(String),
      result: { mode: 'local_receipt' },
    });
    await session.dispatch({ id: 'clear', op: 'geo', task: null });
    expect(session.snapshot().geo).toBeNull();
    expect((await session.dispatch({ id: 'empty', op: 'bus' })).ok).toBe(false);
  });

  it('advertises native variable persistence limits and refuses missing executor', async () => {
    const session = new CommandSession({ cwd: fixture() });
    expect(session.describe().persistence.native_shell_variables).toBe(false);
    const reply = await session.dispatch({ id: 'run', op: 'run', command: 'test' });
    expect(reply.error?.code).toBe('executor_unavailable');
  });
});
