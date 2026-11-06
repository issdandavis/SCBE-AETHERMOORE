/** Stateful command/coordination protocol. Execution remains in the caller's existing gate. */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { planScbeCompassRoute, type ScbeCompassRoutePlan } from './hermes.js';

export const COMMAND_SESSION_SCHEMA = 'scbe.command_session.v1';
export const COMMAND_SESSION_OPERATIONS = {
  describe: { fields: [], purpose: 'Discover this protocol and its limits.' },
  status: { fields: [], purpose: 'Read working directory and geometric task context.' },
  diagnose: { fields: [], purpose: 'Run bounded local runtime checks; no sign-in or model calls.' },
  cd: { fields: ['path'], purpose: 'Change the session working directory using a literal path.' },
  geo: {
    fields: ['task'],
    purpose: 'Plan/set geometric task context; omit task to read, null to clear.',
  },
  run: { fields: ['command', 'timeout_ms'], purpose: 'Execute through the host command gate.' },
  tools: { fields: [], purpose: 'Discover named CLI tools registered by the host.' },
  tool: {
    fields: ['name', 'args', 'timeout_ms'],
    purpose: 'Execute a named CLI with literal arguments through the host command gate.',
  },
  bus: {
    fields: ['task'],
    purpose: 'Record local bus intake; this does not execute a tool or model.',
  },
} as const;

const stringField = (maxLength: number) => ({
  type: 'string',
  minLength: 1,
  maxLength,
  pattern: '\\S',
  not: { pattern: '\\u0000' },
});
const operationFields: Record<string, Record<string, unknown>> = {
  describe: {},
  status: {},
  diagnose: {},
  cd: { path: stringField(32768) },
  geo: { task: { anyOf: [stringField(16384), { type: 'null' }] } },
  run: {
    command: stringField(65536),
    timeout_ms: { type: 'integer', minimum: 1, maximum: 300000 },
  },
  bus: { task: stringField(16384) },
  tools: {},
  tool: {
    name: stringField(64),
    args: {
      type: 'array',
      maxItems: 256,
      items: { type: 'string', maxLength: 65536, not: { pattern: '\\u0000' } },
    },
    timeout_ms: { type: 'integer', minimum: 1, maximum: 300000 },
  },
};
export const COMMAND_SESSION_REQUEST_SCHEMA = {
  type: 'object',
  oneOf: Object.keys(COMMAND_SESSION_OPERATIONS).map((op) => ({
    type: 'object',
    additionalProperties: false,
    required: [
      'id',
      'op',
      ...(op === 'cd'
        ? ['path']
        : op === 'run'
          ? ['command']
          : op === 'tool'
            ? ['name', 'args']
            : []),
    ],
    properties: { id: stringField(128), op: { const: op }, ...operationFields[op] },
  })),
};

export interface CommandSessionState {
  id: string;
  cwd: string;
  sequence: number;
  geo: Pick<
    ScbeCompassRoutePlan,
    'task' | 'mode' | 'formation' | 'domain' | 'tier' | 'command_path'
  > | null;
}

export interface CommandSessionOptions {
  cwd?: string;
  listTools?: () => unknown;
  diagnose?: (context: { cwd: string }) => unknown | Promise<unknown>;
  executeTool?: (
    name: string,
    args: string[],
    context: { cwd: string; timeoutMs: number; geo: CommandSessionState['geo'] }
  ) =>
    | Promise<{ success: boolean; [key: string]: unknown }>
    | { success: boolean; [key: string]: unknown };
  execute?: (
    command: string,
    context: { cwd: string; timeoutMs: number; geo: CommandSessionState['geo'] }
  ) =>
    | Promise<{ success: boolean; [key: string]: unknown }>
    | { success: boolean; [key: string]: unknown };
  recordEvent?: (event: {
    task: string;
    seriesId: string;
    privacy: 'local_only';
    budgetCents: 0;
  }) => Promise<{ ok: boolean; [key: string]: unknown }> | { ok: boolean; [key: string]: unknown };
}

export interface CommandSessionReply {
  schema_version: typeof COMMAND_SESSION_SCHEMA;
  id: string | null;
  ok: boolean;
  session: CommandSessionState;
  result?: unknown;
  error?: { code: string; message: string };
}

class RequestError extends Error {
  constructor(
    public code: string,
    message: string
  ) {
    super(message);
  }
}

function text(value: unknown, name: string, max = 16384): string {
  if (typeof value !== 'string' || !value.trim() || value.length > max || value.includes('\0')) {
    throw new RequestError(
      'invalid_request',
      `${name} must be a nonempty string of at most ${max} characters.`
    );
  }
  return value;
}

function directory(target: string): string {
  const resolved = fs.realpathSync(target);
  if (!fs.statSync(resolved).isDirectory())
    throw new RequestError('invalid_directory', 'Path is not a directory.');
  return resolved;
}

export class CommandSession {
  private state: CommandSessionState;
  private tail: Promise<unknown> = Promise.resolve();
  private requestIds = new Set<string>();

  constructor(private options: CommandSessionOptions = {}) {
    this.state = {
      id: crypto.randomUUID(),
      cwd: directory(options.cwd || process.cwd()),
      sequence: 0,
      geo: null,
    };
  }

  snapshot(): CommandSessionState {
    return structuredClone(this.state);
  }

  describe() {
    return {
      schema_version: COMMAND_SESSION_SCHEMA,
      request: {
        id: 'nonempty string, max 128 characters',
        op: Object.keys(COMMAND_SESSION_OPERATIONS),
      },
      operations: COMMAND_SESSION_OPERATIONS,
      request_schema: structuredClone(COMMAND_SESSION_REQUEST_SCHEMA),
      ordering: 'FIFO; one response per request; EOF drains accepted work',
      request_ids: 'Unique within one session; duplicates are rejected.',
      limits: {
        request_bytes: 131072,
        command_characters: 65536,
        timeout_ms: 300000,
        output_bytes: 1048576,
      },
      persistence: {
        cwd: true,
        geo_context: true,
        native_shell_variables: false,
        across_process_restarts: false,
      },
      execution:
        'Native shell via the existing host gate. Geo routing metadata does not grant permission.',
      bus: 'Local intake receipt only; no tool/model/provider dispatch.',
      cli_host: {
        available: Boolean(this.options.listTools && this.options.executeTool),
        arguments:
          'Literal strings, max 256 entries and 65536 characters in total; shell syntax is data.',
        configuration:
          'Fixed by the host at session startup; requests cannot register executables.',
      },
    };
  }

  /** Serializes library callers too; a failed request cannot poison the queue. */
  dispatch(request: unknown): Promise<CommandSessionReply> {
    const next = this.tail.then(() => this.handle(request));
    this.tail = next.catch(() => undefined);
    return next;
  }

  private async handle(raw: unknown): Promise<CommandSessionReply> {
    this.state.sequence += 1;
    let id: string | null = null;
    try {
      if (!raw || typeof raw !== 'object' || Array.isArray(raw))
        throw new RequestError('invalid_request', 'Expected an object.');
      const request = raw as Record<string, unknown>;
      id = text(request.id, 'id', 128);
      if (this.requestIds.has(id))
        throw new RequestError(
          'duplicate_request_id',
          `Request id has already been used in this session: ${id}`
        );
      this.requestIds.add(id);
      const op = text(request.op, 'op', 32);
      if (!Object.hasOwn(COMMAND_SESSION_OPERATIONS, op))
        throw new RequestError('unknown_operation', `Unknown operation: ${op}`);
      const spec = COMMAND_SESSION_OPERATIONS[op as keyof typeof COMMAND_SESSION_OPERATIONS];
      const fields = new Set<string>(['id', 'op', ...spec.fields]);
      if (Object.keys(request).some((key) => !fields.has(key)))
        throw new RequestError('invalid_request', `Unexpected field for ${op}.`);
      let result: unknown;
      let ok = true;
      switch (op) {
        case 'describe':
          result = this.describe();
          break;
        case 'status':
          result = this.snapshot();
          break;
        case 'diagnose':
          if (!this.options.diagnose)
            throw new RequestError(
              'diagnostics_unavailable',
              'No diagnostics provider is connected.'
            );
          result = await this.options.diagnose({ cwd: this.state.cwd });
          break;
        case 'cd': {
          const target = text(request.path, 'path', 32768);
          // Assign only after resolution/stat succeed; process.cwd is never changed.
          const resolved = directory(path.resolve(this.state.cwd, target));
          this.state.cwd = resolved;
          result = { cwd: resolved };
          break;
        }
        case 'geo': {
          if (request.task === null) this.state.geo = null;
          else if (request.task !== undefined) {
            const plan = planScbeCompassRoute(text(request.task, 'task'));
            const { task, mode, formation, domain, tier, command_path } = plan;
            this.state.geo = { task, mode, formation, domain, tier, command_path };
            result = plan;
          }
          if (result === undefined) result = this.snapshot().geo;
          break;
        }
        case 'tools':
          if (!this.options.listTools)
            throw new RequestError('tools_unavailable', 'No CLI catalog is connected.');
          result = await this.options.listTools();
          break;
        case 'tool':
        case 'run': {
          const timeout = request.timeout_ms ?? 30000;
          if (!Number.isInteger(timeout) || Number(timeout) < 1 || Number(timeout) > 300000) {
            throw new RequestError(
              'invalid_request',
              'timeout_ms must be an integer between 1 and 300000.'
            );
          }
          const context = {
            cwd: this.state.cwd,
            timeoutMs: Number(timeout),
            geo: this.snapshot().geo,
          };
          let execution;
          if (op === 'tool') {
            const name = text(request.name, 'name', 64);
            const args = request.args;
            if (
              !Array.isArray(args) ||
              args.length > 256 ||
              args.some((arg) => typeof arg !== 'string' || arg.includes('\0')) ||
              args.reduce((total, arg) => total + arg.length, 0) > 65536
            )
              throw new RequestError(
                'invalid_request',
                'args must be at most 256 literal strings, totaling at most 65536 characters, without NUL.'
              );
            if (!this.options.executeTool)
              throw new RequestError(
                'executor_unavailable',
                'No governed CLI executor is connected.'
              );
            execution = await this.options.executeTool(name, [...args], context);
          } else {
            const command = text(request.command, 'command', 65536);
            if (!this.options.execute)
              throw new RequestError('executor_unavailable', 'No governed executor is connected.');
            execution = await this.options.execute(command, context);
          }
          if (!execution || typeof execution.success !== 'boolean')
            throw new RequestError('invalid_execution_result', 'Executor omitted success.');
          result = execution;
          ok = execution.success;
          break;
        }
        case 'bus': {
          const task = text(request.task ?? this.state.geo?.task, 'task');
          if (!this.options.recordEvent)
            throw new RequestError('bus_unavailable', 'No local bus is connected.');
          const receipt = await this.options.recordEvent({
            task,
            seriesId: this.state.id,
            privacy: 'local_only',
            budgetCents: 0,
          });
          if (!receipt || typeof receipt.ok !== 'boolean')
            throw new RequestError('invalid_bus_result', 'Bus omitted ok.');
          result = receipt;
          ok = receipt.ok;
          break;
        }
      }
      return { schema_version: COMMAND_SESSION_SCHEMA, id, ok, session: this.snapshot(), result };
    } catch (error) {
      const e = error as Error & { code?: string };
      return {
        schema_version: COMMAND_SESSION_SCHEMA,
        id,
        ok: false,
        session: this.snapshot(),
        error: { code: e.code || 'operation_failed', message: e.message || 'Operation failed.' },
      };
    }
  }
}
