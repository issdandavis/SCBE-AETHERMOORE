/**
 * @file tools.ts
 * @module agent-bus/tools
 *
 * CLI tool registry for the SCBE Agent Bus.
 *
 * Tools are named executables the bus can dispatch to instead of (or alongside)
 * the default scbe-system-cli.py. This lets any CLI command become a first-class
 * bus target without modifying core dispatch logic.
 *
 * Template variables substituted in `args` at dispatch time:
 *   {task}          — event.task
 *   {seriesId}      — event.seriesId or run_id
 *   {taskType}      — event.taskType or 'general'
 *   {privacy}       — event.privacy or 'local_only'
 *   {repoRoot}      — resolved repoRoot from RunOptions
 */

import fs from 'node:fs';
import path from 'node:path';
import type { AgentBusEvent, RunOptions } from './index.js';

export interface CliTool {
  /** Unique name used in AgentBusEvent.tool to route to this tool. */
  name: string;
  /** Human-readable description for `tools list`. */
  description?: string;
  /** Executable to spawn (e.g. 'node', 'python', 'npx'). */
  command: string;
  /**
   * Argument list. Strings containing `{task}`, `{seriesId}`, `{taskType}`,
   * `{privacy}`, or `{repoRoot}` are substituted at dispatch time.
   */
  args: string[];
}

const registry = new Map<string, CliTool>();

/** Register a tool. Idempotent by name — re-registering replaces the previous entry. */
export function registerTool(tool: CliTool): void {
  registry.set(tool.name, tool);
}

/** Remove a tool by name. Returns true if removed, false if not found. */
export function unregisterTool(name: string): boolean {
  return registry.delete(name);
}

/** List all registered tools. */
export function listTools(): readonly CliTool[] {
  return Array.from(registry.values());
}

/** Look up a tool by name. */
export function getTool(name: string): CliTool | undefined {
  return registry.get(name);
}

/** Clear all tools. Useful in tests. */
export function clearTools(): void {
  registry.clear();
}

/** Substitute template variables in a single arg string. */
function substituteArg(arg: string, vars: Record<string, string>): string {
  return arg.replace(/\{(\w+)\}/g, (_, key) => vars[key] ?? `{${key}}`);
}

/** Build the final argv for a tool dispatch. */
export function buildToolArgv(
  tool: CliTool,
  event: AgentBusEvent,
  options: RunOptions,
  runId: string
): { command: string; args: string[] } {
  const repoRoot = options.repoRoot || process.cwd();
  const vars: Record<string, string> = {
    task: event.task,
    seriesId: event.seriesId || runId,
    taskType: event.taskType || 'general',
    privacy: event.privacy || 'local_only',
    repoRoot,
  };
  return {
    command: tool.command,
    args: tool.args.map((a) => substituteArg(a, vars)),
  };
}

/**
 * Load tools from a JSON file referenced by SCBE_BUS_TOOLS env var.
 * The file must be a JSON array of CliTool objects.
 *
 * Example:
 *   SCBE_BUS_TOOLS=./my-tools.json
 *
 * Where my-tools.json:
 *   [{"name":"lint","command":"npx","args":["eslint","{repoRoot}/src"],"description":"Run linter"}]
 */
export function autoDiscoverTools(): void {
  const env = (process.env.SCBE_BUS_TOOLS || '').trim();
  if (!env) return;
  try {
    const resolved = path.resolve(env);
    const raw = fs.readFileSync(resolved, 'utf8');
    const tools = JSON.parse(raw) as unknown;
    if (!Array.isArray(tools)) {
      process.stderr.write(`[agent-bus] SCBE_BUS_TOOLS: ${env} must contain a JSON array\n`);
      return;
    }
    for (const t of tools as CliTool[]) {
      if (typeof t.name === 'string' && typeof t.command === 'string' && Array.isArray(t.args)) {
        registerTool(t);
      } else {
        process.stderr.write(
          `[agent-bus] SCBE_BUS_TOOLS: skipping invalid tool entry (requires name, command, args)\n`
        );
      }
    }
  } catch (err) {
    process.stderr.write(
      `[agent-bus] SCBE_BUS_TOOLS load error (${env}): ${err instanceof Error ? err.message : String(err)}\n`
    );
  }
}
