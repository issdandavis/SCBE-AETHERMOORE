// @ts-nocheck
import { describe, expect, it } from 'vitest';

const frontdoor = await import('../../scripts/system/aetherbrowser_frontdoor.mjs');

function fakeAgent(overrides = {}) {
  const calls = [];
  const impl = (command, input) => {
    calls.push({ command, input });
    if (overrides[command]) return overrides[command](input, calls.length);
    if (command === 'doctor') {
      return { ok: true, command, exit_code: 0, stdout: { ok: true }, stderr: '' };
    }
    if (command === 'status') {
      return { ok: false, command, exit_code: 1, stdout: null, stderr: 'CDP not ready' };
    }
    if (command === 'start') {
      return { ok: true, command, exit_code: 0, stdout: { ok: true, reused: false }, stderr: '' };
    }
    if (command === 'open') {
      return { ok: true, command, exit_code: 0, stdout: { ok: true, title: 'Example' }, stderr: '' };
    }
    return { ok: false, command, exit_code: 1, stdout: null, stderr: 'unexpected command' };
  };
  return { calls, impl };
}

describe('aetherbrowser front door', () => {
  it('parses a conservative status-only default', () => {
    expect(frontdoor.parseFrontdoorArgs([])).toMatchObject({
      json: false,
      start: false,
      open: false,
      requireReady: false,
      target: 'github',
      port: 9333,
      writeReceipt: true,
    });
  });

  it('rejects ambiguous destinations', () => {
    expect(() =>
      frontdoor.parseFrontdoorArgs(['--target', 'github', '--url', 'https://example.com'])
    ).toThrow(/either --url or --target/i);
  });

  it('rejects unsafe URL schemes before reaching the browser agent', () => {
    expect(() => frontdoor.parseFrontdoorArgs(['--url', 'javascript:alert(1)'])).toThrow(/URL must start/i);
  });

  it('reports not-running status without launching Chrome by default', async () => {
    const agent = fakeAgent();
    const writes = [];
    const result = await frontdoor.runFrontdoor([], {
      runAgentImpl: agent.impl,
      mkdirImpl() {},
      writeFileImpl(path, body) {
        writes.push({ path, body });
      },
    });

    expect(result.ok).toBe(true);
    expect(result.ready).toBe(false);
    expect(agent.calls.map((call) => call.command)).toEqual(['doctor', 'status']);
    expect(writes).toHaveLength(1);
  });

  it('starts Chrome when requested and refreshes the status receipt', async () => {
    let statusCalls = 0;
    const agent = fakeAgent({
      status() {
        statusCalls += 1;
        if (statusCalls === 1) {
          return { ok: false, command: 'status', exit_code: 1, stdout: null, stderr: 'CDP not ready' };
        }
        return { ok: true, command: 'status', exit_code: 0, stdout: { ok: true, tabs: [] }, stderr: '' };
      },
    });

    const result = await frontdoor.runFrontdoor(['--start', '--target', 'github', '--no-receipt'], {
      runAgentImpl: agent.impl,
      mkdirImpl() {},
      writeFileImpl() {},
    });

    expect(result.ok).toBe(true);
    expect(result.ready).toBe(true);
    expect(agent.calls.map((call) => call.command)).toEqual(['doctor', 'status', 'start', 'status']);
    expect(agent.calls[2].input.target).toBe('github');
  });

  it('opens an explicit URL through the bounded agent lane', async () => {
    let statusCalls = 0;
    const agent = fakeAgent({
      status() {
        statusCalls += 1;
        if (statusCalls === 1) {
          return { ok: false, command: 'status', exit_code: 1, stdout: null, stderr: 'CDP not ready' };
        }
        return { ok: true, command: 'status', exit_code: 0, stdout: { ok: true, tabs: [{ title: 'Example' }] }, stderr: '' };
      },
    });

    const result = await frontdoor.runFrontdoor(['--open', '--url', 'https://example.com', '--no-receipt'], {
      runAgentImpl: agent.impl,
      mkdirImpl() {},
      writeFileImpl() {},
    });

    expect(result.ok).toBe(true);
    expect(result.open_result.ok).toBe(true);
    expect(agent.calls.map((call) => call.command)).toEqual(['doctor', 'status', 'start', 'open', 'status']);
    expect(agent.calls[2].input.url).toBe('https://example.com');
    expect(agent.calls[3].input.url).toBe('https://example.com');
  });

  it('fails the receipt when an open action fails', async () => {
    const agent = fakeAgent({
      status() {
        return { ok: true, command: 'status', exit_code: 0, stdout: { ok: true, tabs: [] }, stderr: '' };
      },
      open() {
        return { ok: false, command: 'open', exit_code: 1, stdout: null, stderr: 'navigation failed' };
      },
    });

    const result = await frontdoor.runFrontdoor(['--open', '--target', 'github', '--no-receipt'], {
      runAgentImpl: agent.impl,
      mkdirImpl() {},
      writeFileImpl() {},
    });

    expect(result.ok).toBe(false);
    expect(result.open_result.stderr).toContain('navigation failed');
    expect(agent.calls.map((call) => call.command)).toEqual(['doctor', 'status', 'open', 'status']);
  });
});
