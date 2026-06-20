/**
 * @file tool-factory.ts
 * @module agent-bus/tool-factory
 *
 * Self-registration surface: validate a tool spec, verify its command exists,
 * and write it into tools.json atomically (temp-file → rename).
 *
 * Deliberately does NOT include a "generate spec from description" path. That
 * inference layer is deferred until the register/validate/list surface is proven
 * correct. Guessed specs that look valid but don't run are worse than no spec.
 *
 * Schema contract (ToolSpec):
 *   name         — /^[a-z][a-z0-9-]+$/ — kebab-case, min 2 chars after first
 *   description  — non-empty string
 *   command      — "python" | "node"
 *   args         — non-empty string[], at least one element contains "{task}"
 *   patentSurface — optional string
 *
 * Extra keys are rejected at validation time.
 */

import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import path from 'node:path';

// ─── Public types ────────────────────────────────────────────────────────────

export const ALLOWED_COMMANDS = ['python', 'node'] as const;
export type ToolCommand = (typeof ALLOWED_COMMANDS)[number];

export interface ToolSpec {
  name: string;
  description: string;
  command: ToolCommand;
  args: string[];
  patentSurface?: string;
}

export const KNOWN_PATENT_SURFACES = [
  'bijective-transport',
  'agent-harness',
  'atomic-tokenizer',
] as const;
export type KnownPatentSurface = (typeof KNOWN_PATENT_SURFACES)[number];

export interface ValidationResult {
  ok: boolean;
  errors: string[];
  spec?: ToolSpec;
}

export interface VerificationResult {
  ok: boolean;
  skipped: boolean;
  reason: string;
}

export interface RegistrationResult {
  schema_version: 'scbe.agent_bus.tool_factory.v1';
  ok: boolean;
  name: string;
  action: 'registered' | 'rejected';
  errors: string[];
  verification: VerificationResult;
  tools_count_after: number;
}

export interface ListResult {
  schema_version: 'scbe.agent_bus.tool_factory.list.v1';
  tools_count: number;
  tools: Array<Pick<ToolSpec, 'name' | 'command' | 'patentSurface'> & { description_head: string }>;
}

// ─── Validation ──────────────────────────────────────────────────────────────

const NAME_RE = /^[a-z][a-z0-9-]+$/;
const ALLOWED_KEYS = new Set(['name', 'description', 'command', 'args', 'patentSurface']);

export function validateToolSpec(raw: unknown): ValidationResult {
  const errors: string[] = [];

  if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) {
    return { ok: false, errors: ['spec must be a JSON object'] };
  }

  const obj = raw as Record<string, unknown>;

  // Reject unknown keys
  for (const key of Object.keys(obj)) {
    if (!ALLOWED_KEYS.has(key)) {
      errors.push(
        `unknown key: ${JSON.stringify(key)} — only ${[...ALLOWED_KEYS].join(', ')} allowed`
      );
    }
  }

  // name
  if (typeof obj.name !== 'string' || !obj.name) {
    errors.push('name must be a non-empty string');
  } else if (!NAME_RE.test(obj.name)) {
    errors.push(
      `name ${JSON.stringify(obj.name)} must match /^[a-z][a-z0-9-]+$/ (lowercase kebab, min 2 chars)`
    );
  }

  // description
  if (typeof obj.description !== 'string' || !obj.description.trim()) {
    errors.push('description must be a non-empty string');
  }

  // command
  if (!ALLOWED_COMMANDS.includes(obj.command as ToolCommand)) {
    errors.push(`command must be one of: ${ALLOWED_COMMANDS.join(', ')}`);
  }

  // args
  if (!Array.isArray(obj.args) || obj.args.length === 0) {
    errors.push('args must be a non-empty array');
  } else {
    for (let i = 0; i < obj.args.length; i++) {
      if (typeof obj.args[i] !== 'string') {
        errors.push(`args[${i}] must be a string`);
      }
    }
    const hasTaskPlaceholder = obj.args.some((a) => typeof a === 'string' && a.includes('{task}'));
    if (!hasTaskPlaceholder) {
      errors.push('args must contain at least one element with the "{task}" placeholder');
    }
  }

  // patentSurface (optional)
  if (obj.patentSurface !== undefined && typeof obj.patentSurface !== 'string') {
    errors.push('patentSurface must be a string if provided');
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }

  return {
    ok: true,
    errors: [],
    spec: {
      name: obj.name as string,
      description: (obj.description as string).trim(),
      command: obj.command as ToolCommand,
      args: obj.args as string[],
      ...(obj.patentSurface !== undefined && { patentSurface: obj.patentSurface as string }),
    },
  };
}

// ─── Verification (pre-registration) ─────────────────────────────────────────

/**
 * Verify that the command target exists before registering.
 * For `python` with a file path as first non-flag arg: check file exists.
 * For `python -m module`: attempt a dry import.
 * For `node` with a .cjs/.js/.mjs path: check file exists.
 * If neither pattern matches, returns skipped=true (don't block unusual specs).
 */
export function verifyToolSpec(spec: ToolSpec, repoRoot: string): VerificationResult {
  if (spec.command === 'node') {
    const scriptArg = spec.args.find((a) => /\.(cjs|js|mjs)$/.test(a));
    if (scriptArg) {
      const full = path.resolve(repoRoot, scriptArg);
      if (!existsSync(full)) {
        return { ok: false, skipped: false, reason: `node script not found: ${full}` };
      }
    }
    return { ok: true, skipped: scriptArg === undefined, reason: 'node script exists' };
  }

  if (spec.command === 'python') {
    // -m module pattern
    const mIdx = spec.args.indexOf('-m');
    if (mIdx !== -1 && spec.args[mIdx + 1]) {
      const moduleName = spec.args[mIdx + 1];
      const python = process.env.PYTHON ?? (process.platform === 'win32' ? 'python' : 'python3');
      const probe = spawnSync(
        python,
        [
          '-c',
          `import importlib.util; assert importlib.util.find_spec(${JSON.stringify(moduleName)}) is not None`,
        ],
        { cwd: repoRoot, encoding: 'utf8', timeout: 8_000 }
      );
      if (probe.status !== 0) {
        return {
          ok: false,
          skipped: false,
          reason: `python module not importable: ${moduleName} (${probe.stderr.trim().split('\n').pop() ?? ''})`,
        };
      }
      return { ok: true, skipped: false, reason: `python module importable: ${moduleName}` };
    }

    // Direct script path (skip flags that start with -)
    const scriptArg = spec.args.find((a) => !a.startsWith('-') && a.endsWith('.py'));
    if (scriptArg) {
      const full = path.resolve(repoRoot, scriptArg);
      if (!existsSync(full)) {
        return { ok: false, skipped: false, reason: `python script not found: ${full}` };
      }
      return { ok: true, skipped: false, reason: `python script exists: ${full}` };
    }

    return { ok: true, skipped: true, reason: 'no verifiable script path found in args; skipping' };
  }

  return { ok: true, skipped: true, reason: 'unknown command; skipping verification' };
}

// ─── Registry read/write ─────────────────────────────────────────────────────

function readRegistry(toolsJsonPath: string): ToolSpec[] {
  const raw = readFileSync(toolsJsonPath, 'utf8');
  return JSON.parse(raw) as ToolSpec[];
}

function writeRegistryAtomic(toolsJsonPath: string, tools: ToolSpec[]): void {
  const tmp = toolsJsonPath + '.tmp';
  writeFileSync(tmp, JSON.stringify(tools, null, 2) + '\n', 'utf8');
  // Re-read to confirm it round-trips before committing
  const roundTrip = JSON.parse(readFileSync(tmp, 'utf8')) as ToolSpec[];
  if (roundTrip.length !== tools.length) {
    throw new Error(
      `tools.json atomic write sanity-check failed: wrote ${tools.length} tools, re-read ${roundTrip.length}`
    );
  }
  renameSync(tmp, toolsJsonPath);
}

// ─── Public API ──────────────────────────────────────────────────────────────

/**
 * Register a new tool in tools.json.
 *
 * @param spec      Already-validated ToolSpec (run validateToolSpec first)
 * @param toolsJsonPath  Absolute path to tools.json
 * @param repoRoot  Repo root for resolving relative script paths in verify
 * @param skipVerify  Skip pre-registration file/import check (default false)
 */
export function registerTool(
  spec: ToolSpec,
  toolsJsonPath: string,
  repoRoot: string,
  skipVerify = false
): RegistrationResult {
  const base: Omit<RegistrationResult, 'tools_count_after'> = {
    schema_version: 'scbe.agent_bus.tool_factory.v1',
    ok: false,
    name: spec.name,
    action: 'rejected',
    errors: [],
    verification: { ok: true, skipped: true, reason: 'not run' },
  };

  // Check duplicate
  const existing = readRegistry(toolsJsonPath);
  if (existing.some((t) => t.name === spec.name)) {
    return {
      ...base,
      errors: [`tool name already registered: ${spec.name}`],
      tools_count_after: existing.length,
    };
  }

  // Verify command target
  const verification = skipVerify
    ? { ok: true, skipped: true, reason: 'skipped by caller' }
    : verifyToolSpec(spec, repoRoot);

  if (!verification.ok) {
    return {
      ...base,
      errors: [`pre-registration verification failed: ${verification.reason}`],
      verification,
      tools_count_after: existing.length,
    };
  }

  // Atomic write
  const updated = [...existing, spec];
  writeRegistryAtomic(toolsJsonPath, updated);

  return {
    schema_version: 'scbe.agent_bus.tool_factory.v1',
    ok: true,
    name: spec.name,
    action: 'registered',
    errors: [],
    verification,
    tools_count_after: updated.length,
  };
}

/**
 * List all registered tools. Read-only, no side effects.
 */
export function listTools(toolsJsonPath: string): ListResult {
  const tools = readRegistry(toolsJsonPath);
  return {
    schema_version: 'scbe.agent_bus.tool_factory.list.v1',
    tools_count: tools.length,
    tools: tools.map((t) => ({
      name: t.name,
      command: t.command,
      ...(t.patentSurface !== undefined && { patentSurface: t.patentSurface }),
      description_head: t.description.split('.')[0]!.slice(0, 80),
    })),
  };
}

/**
 * Remove a tool from tools.json by name.
 * Returns ok=false if the name was not found.
 */
export function unregisterTool(
  name: string,
  toolsJsonPath: string
): { ok: boolean; tools_count_after: number; error?: string } {
  const existing = readRegistry(toolsJsonPath);
  const filtered = existing.filter((t) => t.name !== name);
  if (filtered.length === existing.length) {
    return { ok: false, tools_count_after: existing.length, error: `tool not found: ${name}` };
  }
  writeRegistryAtomic(toolsJsonPath, filtered);
  return { ok: true, tools_count_after: filtered.length };
}
