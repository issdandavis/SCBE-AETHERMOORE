import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const childProcess = require('node:child_process');
const pluginPath = require.resolve('../plugins/governance-gate.cjs');

function loadPlugin() {
  delete require.cache[pluginPath];
  return require(pluginPath).plugin;
}

describe('governance-gate plugin', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('blocks event when GeoSeal returns nested DENY decision on non-zero exit', async () => {
    vi.spyOn(childProcess, 'spawnSync').mockReturnValue({
      status: 3,
      stdout: JSON.stringify({ decision: { decision: 'DENY', reason: 'blocked by policy' } }),
    });

    const plugin = loadPlugin();
    const result = await plugin.beforeRun({
      event: { task: 'x', privacy: 'hosted', taskType: 'operation' },
      runId: '12345678abcdefgh',
      startedAt: new Date().toISOString(),
    });

    expect(result).toBeNull();
  });

  it('fails open when legitimacy output is unavailable', async () => {
    vi.spyOn(childProcess, 'spawnSync').mockReturnValue({ status: 1, stdout: '' });

    const plugin = loadPlugin();
    const event = { task: 'x', privacy: 'hosted', taskType: 'operation' };
    const result = await plugin.beforeRun({
      event,
      runId: '12345678abcdefgh',
      startedAt: new Date().toISOString(),
    });

    expect(result).toEqual(event);
  });
});
