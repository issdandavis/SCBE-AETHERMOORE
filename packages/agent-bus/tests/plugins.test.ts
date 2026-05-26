import { describe, it, expect, beforeEach } from 'vitest';
import {
  registerPlugin,
  unregisterPlugin,
  listPlugins,
  clearPlugins,
  runBeforeRunPlugins,
  runAfterRunPlugins,
  type BusPlugin,
  type BusPluginContext,
} from '../src/plugins.js';
import type { AgentBusEvent } from '../src/index.js';

describe('plugin system', () => {
  beforeEach(() => clearPlugins());

  it('registers and lists plugins', () => {
    const p: BusPlugin = { name: 'test-plugin', beforeRun: async (ctx) => ctx.event };
    registerPlugin(p);
    expect(listPlugins()).toHaveLength(1);
    expect(listPlugins()[0].name).toBe('test-plugin');
  });

  it('replaces plugins with the same name', () => {
    registerPlugin({ name: 'dup', beforeRun: async (ctx) => ctx.event });
    registerPlugin({ name: 'dup', afterRun: async () => {} });
    expect(listPlugins()).toHaveLength(1);
    expect(listPlugins()[0].beforeRun).toBeUndefined();
    expect(listPlugins()[0].afterRun).toBeDefined();
  });

  it('unregisters a plugin', () => {
    registerPlugin({ name: 'a', beforeRun: async (ctx) => ctx.event });
    expect(unregisterPlugin('a')).toBe(true);
    expect(listPlugins()).toHaveLength(0);
    expect(unregisterPlugin('a')).toBe(false);
  });

  it('beforeRun allows events by default', async () => {
    const event: AgentBusEvent = { task: 'test' };
    const ctx: BusPluginContext = { event, runId: 'r1', startedAt: new Date().toISOString() };
    const result = await runBeforeRunPlugins(ctx);
    expect(result).toEqual(event);
  });

  it('beforeRun can deny events', async () => {
    const event: AgentBusEvent = { task: 'test' };
    registerPlugin({
      name: 'gate',
      beforeRun: async () => null,
    });
    const ctx: BusPluginContext = { event, runId: 'r1', startedAt: new Date().toISOString() };
    const result = await runBeforeRunPlugins(ctx);
    expect(result).toBeNull();
  });

  it('beforeRun can mutate events', async () => {
    const event: AgentBusEvent = { task: 'test' };
    registerPlugin({
      name: 'mutator',
      beforeRun: async (ctx) => ({ ...ctx.event, taskType: 'review' }),
    });
    const ctx: BusPluginContext = { event, runId: 'r1', startedAt: new Date().toISOString() };
    const result = await runBeforeRunPlugins(ctx);
    expect(result?.taskType).toBe('review');
  });

  it('afterRun runs without throwing', async () => {
    let called = false;
    registerPlugin({
      name: 'logger',
      afterRun: async () => { called = true; },
    });
    const event: AgentBusEvent = { task: 'test' };
    const ctx: BusPluginContext = { event, runId: 'r1', startedAt: new Date().toISOString() };
    await runAfterRunPlugins(ctx);
    expect(called).toBe(true);
  });

  it('afterRun errors are swallowed', async () => {
    registerPlugin({
      name: 'thrower',
      afterRun: async () => { throw new Error('boom'); },
    });
    const event: AgentBusEvent = { task: 'test' };
    const ctx: BusPluginContext = { event, runId: 'r1', startedAt: new Date().toISOString() };
    await expect(runAfterRunPlugins(ctx)).resolves.toBeUndefined();
  });
});
