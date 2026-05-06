import { spawn } from 'node:child_process';
import { createServer, request as httpRequest, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import * as path from 'node:path';
import { createInterface } from 'node:readline';

export type Privacy = 'local_only' | 'remote_ok';
export type TaskType = 'coding' | 'review' | 'research' | 'governance' | 'training' | 'general';

export interface AgentBusEvent {
  task: string;
  operationCommand?: string;
  taskType?: TaskType;
  seriesId?: string;
  privacy?: Privacy;
  budgetCents?: number;
  dispatch?: boolean;
  dispatchProvider?: string;
}

export interface AgentBusResult {
  schema_version: 'scbe-agentbus-pipe-result-v1';
  event_index: number;
  started_at: string;
  finished_at: string;
  ok: boolean;
  exit_code: number | null;
  stderr_tail: string;
  event: {
    task_sha256: string | null;
    task_chars: number;
    series_id: string;
    operation_command_chars: number;
  };
  result: unknown;
}

export interface RunnerOptions {
  repoRoot?: string;
  python?: string;
  continueOnError?: boolean;
}

export interface AgentBusServerOptions extends RunnerOptions {
  host?: string;
  port?: number;
}

export interface AgentBusServerHandle {
  server: Server;
  host: string;
  port: number;
  url: string;
}

export interface AgentBusClientOptions {
  baseUrl?: string;
}

export interface AgentBusUiOptions extends AgentBusClientOptions {
  stdin?: NodeJS.ReadableStream;
  stdout?: NodeJS.WritableStream;
}

const DEFAULT_REPO_ROOT = path.resolve(__dirname, '..', '..', '..');

function resolveRunner(repoRoot: string): string {
  return path.join(repoRoot, 'scripts', 'system', 'agentbus_pipe.mjs');
}

export async function runEvent(event: AgentBusEvent, options: RunnerOptions = {}): Promise<AgentBusResult> {
  const rows = await runBatch([event], options);
  if (!rows.length) {
    throw new Error('agent-bus runner returned no rows');
  }
  return rows[0];
}

export async function runBatch(events: AgentBusEvent[], options: RunnerOptions = {}): Promise<AgentBusResult[]> {
  if (!events.length) {
    throw new Error('agent-bus: events array is empty');
  }
  const repoRoot = path.resolve(options.repoRoot ?? DEFAULT_REPO_ROOT);
  const runner = resolveRunner(repoRoot);
  const args = ['--repo-root', repoRoot];
  if (options.python) {
    args.push('--python', options.python);
  }
  if (options.continueOnError) {
    args.push('--continue-on-error');
  }

  return new Promise<AgentBusResult[]>((resolve, reject) => {
    const child = spawn(process.execPath, [runner, ...args], {
      cwd: repoRoot,
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      stdout += String(chunk);
    });
    child.stderr.on('data', (chunk) => {
      stderr += String(chunk);
    });

    child.on('error', reject);
    child.on('close', (code) => {
      if (!stdout.trim()) {
        const err = new Error(`agent-bus runner produced no stdout (exit ${code})`);
        (err as Error & { stderr: string }).stderr = stderr.slice(-2000);
        reject(err);
        return;
      }
      try {
        const rows: AgentBusResult[] = stdout
          .split('\n')
          .map((line) => line.trim())
          .filter((line) => line.length > 0)
          .map((line) => JSON.parse(line) as AgentBusResult);
        resolve(rows);
      } catch (parseErr) {
        reject(parseErr);
      }
    });

    child.stdin.write(JSON.stringify(events));
    child.stdin.end();
  });
}

function readRequestBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    let raw = '';
    req.setEncoding('utf8');
    req.on('data', (chunk) => {
      raw += String(chunk);
      if (raw.length > 1024 * 1024) {
        reject(new Error('request body exceeds 1 MiB'));
        req.destroy();
      }
    });
    req.on('end', () => resolve(raw));
    req.on('error', reject);
  });
}

function writeJson(res: ServerResponse, status: number, payload: unknown): void {
  res.statusCode = status;
  res.setHeader('content-type', 'application/json; charset=utf-8');
  res.end(`${JSON.stringify(payload, null, 2)}\n`);
}

function parseEventPayload(raw: string): AgentBusEvent[] {
  const parsed = raw.trim() ? JSON.parse(raw) : {};
  if (Array.isArray(parsed)) return parsed as AgentBusEvent[];
  if (Array.isArray(parsed.items)) return parsed.items as AgentBusEvent[];
  if (parsed.event && typeof parsed.event === 'object') return [parsed.event as AgentBusEvent];
  return [parsed as AgentBusEvent];
}

export function createAgentBusServer(options: AgentBusServerOptions = {}): Server {
  const server = createServer(async (req, res) => {
    try {
      const method = req.method || 'GET';
      const url = new URL(req.url || '/', 'http://127.0.0.1');
      if (method === 'GET' && url.pathname === '/health') {
        writeJson(res, 200, {
          schema_version: 'scbe-agent-bus-backend-health-v1',
          ok: true,
          service: 'scbe-agent-bus',
          routes: ['/health', '/v1/events', '/v1/batch'],
        });
        return;
      }
      if (method === 'POST' && (url.pathname === '/v1/events' || url.pathname === '/v1/batch')) {
        const events = parseEventPayload(await readRequestBody(req));
        const results = await runBatch(events, {
          repoRoot: options.repoRoot,
          python: options.python,
          continueOnError: options.continueOnError || url.pathname === '/v1/batch',
        });
        writeJson(res, results.every((row) => row.ok) ? 200 : 500, {
          schema_version: 'scbe-agent-bus-backend-result-v1',
          ok: results.every((row) => row.ok),
          count: results.length,
          results,
        });
        return;
      }
      writeJson(res, 404, {
        schema_version: 'scbe-agent-bus-backend-error-v1',
        ok: false,
        error: 'not_found',
        routes: ['/health', '/v1/events', '/v1/batch'],
      });
    } catch (err) {
      writeJson(res, 500, {
        schema_version: 'scbe-agent-bus-backend-error-v1',
        ok: false,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  });
  return server;
}

export async function startAgentBusServer(options: AgentBusServerOptions = {}): Promise<AgentBusServerHandle> {
  const host = options.host || '127.0.0.1';
  const port = options.port ?? 8787;
  const server = createAgentBusServer(options);
  await new Promise<void>((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, host, () => {
      server.off('error', reject);
      resolve();
    });
  });
  return { server, host, port, url: `http://${host}:${port}` };
}

export function postAgentBusEvent(event: AgentBusEvent, options: AgentBusClientOptions = {}): Promise<unknown> {
  const baseUrl = options.baseUrl || 'http://127.0.0.1:8787';
  const url = new URL('/v1/events', baseUrl);
  const body = JSON.stringify(event);
  return new Promise((resolve, reject) => {
    const req = httpRequest(
      url,
      {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'content-length': String(Buffer.byteLength(body)),
        },
      },
      (res) => {
        let raw = '';
        res.setEncoding('utf8');
        res.on('data', (chunk) => {
          raw += String(chunk);
        });
        res.on('end', () => {
          try {
            resolve(JSON.parse(raw));
          } catch {
            resolve(raw);
          }
        });
      }
    );
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

function askLine(rl: ReturnType<typeof createInterface>, prompt: string): Promise<string> {
  return new Promise((resolve) => rl.question(prompt, (answer) => resolve(String(answer || '').trim())));
}

export async function runAgentBusTerminalUi(options: AgentBusUiOptions = {}): Promise<void> {
  const input = options.stdin || process.stdin;
  const output = options.stdout || process.stdout;
  const baseUrl = options.baseUrl || 'http://127.0.0.1:8787';
  const rl = createInterface({ input, output });
  try {
    output.write('SCBE Agent Bus Terminal UI\n');
    output.write(`Backend: ${baseUrl}\n\n`);
    while (true) {
      output.write('1. Send governed task\n');
      output.write('2. Health check\n');
      output.write('0. Exit\n');
      const choice = await askLine(rl, '\nSelect: ');
      if (choice === '0' || choice.toLowerCase() === 'exit') return;
      if (choice === '2') {
        const health = await fetch(`${baseUrl.replace(/\/+$/, '')}/health`).then((res) => res.json());
        output.write(`${JSON.stringify(health, null, 2)}\n\n`);
        continue;
      }
      if (choice !== '1') {
        output.write('Unknown selection.\n\n');
        continue;
      }
      const task = await askLine(rl, 'Task: ');
      const taskType = (await askLine(rl, 'Task type [general]: ')) || 'general';
      const result = await postAgentBusEvent(
        {
          task,
          taskType: taskType as TaskType,
          privacy: 'local_only',
          dispatchProvider: 'offline',
          dispatch: true,
        },
        { baseUrl }
      );
      output.write(`${JSON.stringify(result, null, 2)}\n\n`);
    }
  } finally {
    rl.close();
  }
}

export const SCHEMA_VERSION = 'scbe-agentbus-pipe-result-v1' as const;
