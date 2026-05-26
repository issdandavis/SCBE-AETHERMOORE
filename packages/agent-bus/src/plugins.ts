/**
 * @file plugins.ts
 * @module agent-bus/plugins
 *
 * Plugin middleware system for the SCBE Agent Bus.
 *
 * Plugins can hook into the event lifecycle without modifying core code:
 *   - beforeRun: inspect, mutate, or deny events before execution
 *   - afterRun: inspect results, emit side effects, write receipts
 *
 * Plugins are registered via registerPlugin() at runtime or auto-discovered
 * from the SCBE_BUS_PLUGINS environment variable.
 */

import type { AgentBusEvent, AgentBusResult } from './index.js';

export interface BusPluginContext {
  /** The event being processed. Mutable by beforeRun hooks. */
  event: AgentBusEvent;
  /** Result of the event, populated after execution for afterRun hooks. */
  result?: AgentBusResult;
  /** Workspace root if the event references one. */
  workspaceRoot?: string;
  /** Unique run identifier. */
  runId: string;
  /** ISO timestamp when the run started. */
  startedAt: string;
}

export interface BusPlugin {
  /** Unique plugin name. Used for logging and ordering. */
  name: string;
  /**
   * Called before an event is executed.
   * Return the (possibly mutated) event to allow execution.
   * Return null to DENY the event — the bus returns a blocked result immediately.
   * Throw an error to convert it into a failed result.
   */
  beforeRun?(ctx: BusPluginContext): Promise<AgentBusEvent | null>;
  /**
   * Called after an event finishes (success or failure).
   * Cannot mutate the result, but can emit side effects (receipts, logs, metrics).
   */
  afterRun?(ctx: BusPluginContext): Promise<void>;
}

const registry: BusPlugin[] = [];

/** Register a plugin. Idempotent by name — re-registering replaces the previous instance. */
export function registerPlugin(plugin: BusPlugin): void {
  const idx = registry.findIndex((p) => p.name === plugin.name);
  if (idx >= 0) registry[idx] = plugin;
  else registry.push(plugin);
}

/** Remove a plugin by name. */
export function unregisterPlugin(name: string): boolean {
  const idx = registry.findIndex((p) => p.name === name);
  if (idx >= 0) {
    registry.splice(idx, 1);
    return true;
  }
  return false;
}

/** List registered plugins. */
export function listPlugins(): readonly BusPlugin[] {
  return registry.slice();
}

/** Clear all plugins. Useful in tests. */
export function clearPlugins(): void {
  registry.length = 0;
}

/**
 * Auto-discover plugins from the SCBE_BUS_PLUGINS environment variable.
 * Format: comma-separated absolute or relative module paths.
 * Each module must export a BusPlugin as default or as `plugin`.
 *
 * Example:
 *   SCBE_BUS_PLUGINS=./my-plugin.js,./authorship-gate.js
 */
export async function autoDiscoverPlugins(): Promise<void> {
  const env = process.env.SCBE_BUS_PLUGINS || '';
  if (!env.trim()) return;
  const paths = env
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  for (const modPath of paths) {
    try {
      const mod = await import(modPath);
      const plugin: BusPlugin | undefined = mod.default || mod.plugin;
      if (plugin && typeof plugin.name === 'string') {
        registerPlugin(plugin);
      } else {
        process.stderr.write(
          `[agent-bus] SCBE_BUS_PLUGINS: ${modPath} does not export a valid BusPlugin (missing 'name')\n`
        );
      }
    } catch (err) {
      process.stderr.write(
        `[agent-bus] SCBE_BUS_PLUGINS: failed to load ${modPath}: ${
          err instanceof Error ? err.message : String(err)
        }\n`
      );
    }
  }
}

/**
 * Run the beforeRun hook across all registered plugins.
 * Returns the mutated event, or null if any plugin denied it.
 */
export async function runBeforeRunPlugins(ctx: BusPluginContext): Promise<AgentBusEvent | null> {
  let currentEvent = ctx.event;
  for (const plugin of registry) {
    if (!plugin.beforeRun) continue;
    const result = await plugin.beforeRun({ ...ctx, event: currentEvent });
    if (result === null) {
      return null;
    }
    currentEvent = result;
  }
  return currentEvent;
}

/**
 * Run the afterRun hook across all registered plugins.
 * Errors are logged but never thrown — afterRun is best-effort.
 */
export async function runAfterRunPlugins(ctx: BusPluginContext): Promise<void> {
  for (const plugin of registry) {
    if (!plugin.afterRun) continue;
    try {
      await plugin.afterRun(ctx);
    } catch (err) {
      process.stderr.write(
        `[agent-bus] plugin '${plugin.name}' afterRun error: ${
          err instanceof Error ? err.message : String(err)
        }\n`
      );
    }
  }
}
