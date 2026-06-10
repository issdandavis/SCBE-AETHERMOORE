import { BackendClient, OperationRequest, SCHEMA_VERSION } from './BackendClient';

export interface ToolParam {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'json';
  description: string;
  required?: boolean;
}

export interface ToolDef {
  name: string;
  description: string;
  params: ToolParam[];
  run: (args: Record<string, unknown>) => Promise<unknown>;
}

export interface ToolBus {
  listTools(): ToolDef[];
  callTool(name: string, args: Record<string, unknown>): Promise<unknown>;
  register(def: ToolDef): void;
}

let _idSeq = 0;
function nextId(prefix: string): string {
  return `${prefix}-${Date.now()}-${++_idSeq}`;
}

function safeCalc(expr: string): number {
  if (!/^[\d\s+\-*/%.()]+$/.test(expr)) {
    throw new Error('Invalid expression: only digits and arithmetic operators allowed');
  }
  // eslint-disable-next-line no-new-func
  return Function(`'use strict'; return (${expr})`)() as number;
}

async function sha256(text: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

const VFS_KEY = 'aether-desktop:vfs';

function vfsLoad(): Map<string, string> {
  try {
    const raw = typeof localStorage !== 'undefined' ? localStorage.getItem(VFS_KEY) : null;
    return raw ? new Map(Object.entries(JSON.parse(raw) as Record<string, string>)) : new Map();
  } catch {
    return new Map();
  }
}

function vfsSave(vfs: Map<string, string>): void {
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(VFS_KEY, JSON.stringify(Object.fromEntries(vfs)));
    }
  } catch {
    // storage quota or SSR — silently no-op
  }
}

export function createToolBus(client: BackendClient): ToolBus {
  const registry = new Map<string, ToolDef>();
  const vfs = vfsLoad();

  function register(def: ToolDef): void {
    registry.set(def.name, def);
  }

  function listTools(): ToolDef[] {
    return Array.from(registry.values()).sort((a, b) => a.name.localeCompare(b.name));
  }

  async function callTool(name: string, args: Record<string, unknown>): Promise<unknown> {
    const def = registry.get(name);
    if (!def) throw new Error(`Unknown tool: ${name}`);
    return def.run(args);
  }

  // ── client-side tools ─────────────────────────────────────────────────────

  register({
    name: 'json.format',
    description: 'Pretty-print a JSON string',
    params: [
      { name: 'input', type: 'string', description: 'JSON string to format', required: true },
    ],
    async run(args) {
      return JSON.stringify(JSON.parse(args['input'] as string), null, 2);
    },
  });

  register({
    name: 'hash.sha256',
    description: 'Generate a SHA-256 hash of a string',
    params: [{ name: 'input', type: 'string', description: 'String to hash', required: true }],
    async run(args) {
      return sha256(args['input'] as string);
    },
  });

  register({
    name: 'math.calculate',
    description: 'Evaluate a safe arithmetic expression (digits and + - * / % only)',
    params: [
      { name: 'expr', type: 'string', description: 'Expression, e.g. "2 + 3 * 4"', required: true },
    ],
    async run(args) {
      return safeCalc(args['expr'] as string);
    },
  });

  register({
    name: 'text.count',
    description: 'Count chars, words, lines and estimate reading time',
    params: [{ name: 'text', type: 'string', description: 'Text to analyse', required: true }],
    async run(args) {
      const text = args['text'] as string;
      const chars = text.length;
      const words = text.trim() === '' ? 0 : text.trim().split(/\s+/).length;
      const lines = text.split('\n').length;
      const reading_time_sec = Math.ceil((words / 200) * 60);
      return { chars, words, lines, reading_time_sec };
    },
  });

  // ── virtual filesystem ────────────────────────────────────────────────────

  register({
    name: 'fs.list',
    description: 'List paths in the virtual filesystem',
    params: [],
    async run() {
      return Array.from(vfs.keys()).sort();
    },
  });

  register({
    name: 'fs.read',
    description: 'Read a file from the virtual filesystem',
    params: [{ name: 'path', type: 'string', description: 'File path', required: true }],
    async run(args) {
      const path = args['path'] as string;
      if (!vfs.has(path)) throw new Error(`File not found: ${path}`);
      return vfs.get(path);
    },
  });

  register({
    name: 'fs.write',
    description: 'Write a file to the virtual filesystem',
    params: [
      { name: 'path', type: 'string', description: 'File path', required: true },
      { name: 'content', type: 'string', description: 'File content', required: true },
    ],
    async run(args) {
      const path = args['path'] as string;
      const content = args['content'] as string;
      vfs.set(path, content);
      vfsSave(vfs);
      return { path, bytes: content.length };
    },
  });

  // ── backend-delegated tools ───────────────────────────────────────────────

  register({
    name: 'echo',
    description: 'Echo a message through the SCBE backend',
    params: [{ name: 'msg', type: 'string', description: 'Message to echo', required: true }],
    async run(args) {
      const req: OperationRequest = {
        schema_version: SCHEMA_VERSION,
        op: 'echo',
        args,
        request_id: nextId('echo'),
        origin: { kind: 'app', id: 'tool-console' },
        privacy: 'local_only',
      };
      const result = await client.runOp(req);
      if (!result.ok) throw new Error(result.error?.message ?? 'echo failed');
      return result.output;
    },
  });

  register({
    name: 'agent.plan',
    description: 'Turn a goal into numbered implementation steps via the LLM',
    params: [{ name: 'goal', type: 'string', description: 'Goal to plan', required: true }],
    async run(args) {
      const req: OperationRequest = {
        schema_version: SCHEMA_VERSION,
        op: 'llm.chat',
        args: {
          model: 'qwen2.5-coder:latest',
          messages: [
            {
              role: 'system',
              content:
                'You are a technical planning assistant. Given a goal, produce a numbered list of concrete implementation steps. Be brief.',
            },
            { role: 'user', content: `Plan: ${args['goal'] as string}` },
          ],
        },
        request_id: nextId('plan'),
        origin: { kind: 'agent', id: 'tool-console' },
        privacy: 'local_only',
      };
      const result = await client.runOp(req);
      if (!result.ok) throw new Error(result.error?.message ?? 'llm.chat failed');
      return result.output;
    },
  });

  return { listTools, callTool, register };
}
