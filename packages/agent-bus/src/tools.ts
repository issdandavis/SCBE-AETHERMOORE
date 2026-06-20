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
  /**
   * Optional patent-facing surface tag. Used by audits and docs only; dispatch
   * stays driven by name/command/args.
   */
  patentSurface?: ToolPatentSurface;
  /** Optional environment variables required for live execution. */
  requiresEnv?: string[];
  /** Executable to spawn (e.g. 'node', 'python', 'npx'). */
  command: string;
  /**
   * Argument list. Strings containing `{task}`, `{seriesId}`, `{taskType}`,
   * `{privacy}`, or `{repoRoot}` are substituted at dispatch time.
   */
  args: string[];
}

export type ToolPatentSurface =
  | 'hyperbolic-governance'
  | 'bijective-transport'
  | 'runtime-persistence'
  | 'tamper-detection'
  | 'agent-harness'
  | 'research-evidence'
  | 'video-lattice'
  | 'atomic-tokenizer'
  | 'unknown';

export interface ToolAuditEntry {
  name: string;
  ok: boolean;
  command: string;
  argCount: number;
  patentSurface: ToolPatentSurface;
  missing: string[];
  requiredEnv: string[];
  envReady: boolean;
}

export interface ToolRegistryAudit {
  schema_version: 'scbe.agent_bus.tool_registry_audit.v1';
  generated_at: string;
  tool_count: number;
  ok: boolean;
  surface_counts: Record<ToolPatentSurface, number>;
  missing_description: string[];
  missing_required_env: Record<string, string[]>;
  tools: ToolAuditEntry[];
}

const registry = new Map<string, CliTool>();

function isUnsafeAutoDiscoveredTool(tool: CliTool): boolean {
  const args = tool.args.map((arg) => arg.trim());
  const invokesGeoSealExec =
    args.some((arg, index) => arg === '-m' && args[index + 1] === 'src.geoseal_cli') &&
    args.includes('exec');
  const passesTaskAsCommand = args.includes('{task}');
  return invokesGeoSealExec && passesTaskAsCommand;
}

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

function inferPatentSurface(tool: CliTool): ToolPatentSurface {
  if (tool.patentSurface) return tool.patentSurface;
  const haystack = `${tool.name} ${tool.description || ''} ${tool.args.join(' ')}`.toLowerCase();
  if (haystack.includes('research-')) return 'research-evidence';
  if (haystack.includes('video') || haystack.includes('lattice')) return 'video-lattice';
  if (haystack.includes('encode') || haystack.includes('tongues')) return 'bijective-transport';
  if (haystack.includes('verify') || haystack.includes('canonical')) return 'tamper-detection';
  if (haystack.includes('runtime') || haystack.includes('durable') || haystack.includes('state')) {
    return 'runtime-persistence';
  }
  if (haystack.includes('geoseal') || haystack.includes('governance')) {
    return 'hyperbolic-governance';
  }
  if (haystack.includes('cli') || haystack.includes('harness') || haystack.includes('agentbus')) {
    return 'agent-harness';
  }
  if (haystack.includes('token')) return 'atomic-tokenizer';
  return 'unknown';
}

function inferRequiredEnv(tool: CliTool): string[] {
  if (tool.requiresEnv && tool.requiresEnv.length > 0) return tool.requiresEnv;
  const haystack = `${tool.name} ${tool.description || ''}`.toLowerCase();
  if (haystack.includes('sam.gov')) return ['SAM_GOV_API_KEY'];
  if (haystack.includes('uspto')) return ['USPTO_ODP_API_KEY'];
  if (haystack.includes('github')) return ['GITHUB_TOKEN'];
  if (haystack.includes('huggingface') || haystack.includes('hf_')) return [];
  return [];
}

export function auditToolRegistry(tools: readonly CliTool[] = listTools()): ToolRegistryAudit {
  const surfaceCounts: Record<ToolPatentSurface, number> = {
    'hyperbolic-governance': 0,
    'bijective-transport': 0,
    'runtime-persistence': 0,
    'tamper-detection': 0,
    'agent-harness': 0,
    'research-evidence': 0,
    'video-lattice': 0,
    'atomic-tokenizer': 0,
    unknown: 0,
  };
  const missingDescription: string[] = [];
  const missingRequiredEnv: Record<string, string[]> = {};

  const entries = tools.map((tool) => {
    const missing: string[] = [];
    if (!tool.name || !tool.name.trim()) missing.push('name');
    if (!tool.command || !tool.command.trim()) missing.push('command');
    if (!Array.isArray(tool.args)) missing.push('args');
    if (!tool.description || !tool.description.trim()) {
      missing.push('description');
      missingDescription.push(tool.name || '<unnamed>');
    }

    const patentSurface = inferPatentSurface(tool);
    surfaceCounts[patentSurface] += 1;
    const requiredEnv = inferRequiredEnv(tool);
    const absentEnv = requiredEnv.filter((name) => !String(process.env[name] || '').trim());
    if (absentEnv.length > 0) {
      missingRequiredEnv[tool.name] = absentEnv;
    }

    return {
      name: tool.name,
      ok: missing.length === 0,
      command: tool.command,
      argCount: Array.isArray(tool.args) ? tool.args.length : 0,
      patentSurface,
      missing,
      requiredEnv,
      envReady: absentEnv.length === 0,
    };
  });

  return {
    schema_version: 'scbe.agent_bus.tool_registry_audit.v1',
    generated_at: new Date().toISOString(),
    tool_count: entries.length,
    ok: entries.every((entry) => entry.ok),
    surface_counts: surfaceCounts,
    missing_description: missingDescription,
    missing_required_env: missingRequiredEnv,
    tools: entries,
  };
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
        if (isUnsafeAutoDiscoveredTool(t)) {
          process.stderr.write(
            `[agent-bus] SCBE_BUS_TOOLS: skipping unsafe tool entry '${t.name}' (GeoSeal exec cannot receive {task} as a command)\n`
          );
          continue;
        }
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
