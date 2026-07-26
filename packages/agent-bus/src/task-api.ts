import { isIP } from 'node:net';
import { z } from 'zod';

export const GOVERNED_TASK_SCHEMA_VERSION = 'scbe.governed-task-run.v1' as const;
export const TASK_API_DEFAULT_URL = 'http://127.0.0.1:8766' as const;

const Sha256Schema = z.string().regex(/^[a-f0-9]{64}$/);
const TaskStatusSchema = z.enum(['queued', 'running', 'completed', 'failed', 'cancelled']);
const DispositionStatusSchema = z.enum([
  'pending',
  'review_required',
  'failed_evidence_check',
  'failed_execution',
  'cancelled',
]);

export const TaskCitationSchema = z.object({
  source_id: z.string().optional(),
  title: z.string().min(1),
  url: z.string().url(),
  content_sha256: Sha256Schema,
  quote: z.string().min(1),
});

export const TaskFieldBasisSchema = z.object({
  field: z.string().min(1),
  confidence: z.number().min(0).max(1),
  citations: z.array(TaskCitationSchema),
  reasoning: z.string().min(1),
});

export const TaskDispositionSchema = z.object({
  status: DispositionStatusSchema,
  negative_example: z.boolean(),
  do_not_promote_to_fact: z.literal(true),
  reason: z.string().min(1),
});

export const GovernedTaskRunSchema = z
  .object({
    schema_version: z.literal(GOVERNED_TASK_SCHEMA_VERSION),
    run_id: z.string().min(1),
    interaction_id: z.string().min(1),
    status: TaskStatusSchema,
    submitted_at: z.string().min(1),
    started_at: z.string().nullable(),
    completed_at: z.string().nullable(),
    input_sha256: Sha256Schema,
    output_sha256: Sha256Schema.optional(),
    result: z.unknown().nullable(),
    error: z.unknown().nullable(),
    basis: z.array(TaskFieldBasisSchema),
    metrics: z.record(z.string(), z.unknown()),
    disposition: TaskDispositionSchema,
    seal: z.record(z.string(), z.unknown()).optional(),
    completion_seal: z.record(z.string(), z.unknown()).optional(),
    webhook_delivery: z.unknown().nullable().optional(),
  })
  .passthrough()
  .superRefine((run, context) => {
    const citationCount = run.basis.reduce((count, field) => count + field.citations.length, 0);
    if (run.status === 'completed') {
      if (!run.output_sha256) {
        context.addIssue({
          code: 'custom',
          path: ['output_sha256'],
          message: 'completed runs require output_sha256',
        });
      }
      if (
        citationCount > 0 &&
        (run.disposition.status !== 'review_required' || run.disposition.negative_example !== false)
      ) {
        context.addIssue({
          code: 'custom',
          path: ['disposition'],
          message: 'evidence-backed completion must remain review_required',
        });
      }
      if (
        citationCount === 0 &&
        (run.disposition.status !== 'failed_evidence_check' ||
          run.disposition.negative_example !== true)
      ) {
        context.addIssue({
          code: 'custom',
          path: ['disposition'],
          message: 'completion without evidence must remain a negative example',
        });
      }
    }
    if (
      run.status === 'failed' &&
      (run.disposition.status !== 'failed_execution' || run.disposition.negative_example !== true)
    ) {
      context.addIssue({
        code: 'custom',
        path: ['disposition'],
        message: 'failed execution must remain a negative example',
      });
    }
    if (
      run.status === 'cancelled' &&
      (run.disposition.status !== 'cancelled' || run.disposition.negative_example !== true)
    ) {
      context.addIssue({
        code: 'custom',
        path: ['disposition'],
        message: 'cancelled run must remain non-promotable',
      });
    }
  });

export type GovernedTaskRun = z.infer<typeof GovernedTaskRunSchema>;
export type TaskFieldBasis = z.infer<typeof TaskFieldBasisSchema>;

export type TaskRunParseResult =
  { ok: true; data: GovernedTaskRun } | { ok: false; errors: string[]; raw: unknown };

export interface TaskApiClientOptions {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
  /**
   * Public hosts are denied by default. Enable only for an explicitly trusted
   * HTTPS deployment. Loopback, RFC1918, link-local, and Tailscale literals
   * remain available without this flag.
   */
  allowPublicNetwork?: boolean;
}

export interface WaitForTaskRunOptions {
  timeoutMs?: number;
  pollIntervalMs?: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function normalizeCancelledDisposition(run: Record<string, unknown>): Record<string, unknown> {
  const disposition = isRecord(run.disposition) ? run.disposition : {};
  if (run.status !== 'cancelled' || disposition.status !== 'pending') return run;
  return {
    ...run,
    disposition: {
      status: 'cancelled',
      negative_example: true,
      do_not_promote_to_fact: true,
      reason: 'Cancelled runs are not eligible for factual training.',
    },
  };
}

export function parseTaskApiRun(raw: unknown): TaskRunParseResult {
  if (!isRecord(raw)) return { ok: false, errors: ['task run must be an object'], raw };
  const normalized = normalizeCancelledDisposition({
    ...raw,
    schema_version: GOVERNED_TASK_SCHEMA_VERSION,
  });
  const parsed = GovernedTaskRunSchema.safeParse(normalized);
  if (parsed.success) return { ok: true, data: parsed.data };
  return {
    ok: false,
    errors: parsed.error.issues.map(
      (issue) => `${issue.path.join('.') || '<root>'}: ${issue.message}`
    ),
    raw,
  };
}

function isOwnedIpv4(host: string): boolean {
  const octets = host.split('.').map(Number);
  if (octets.length !== 4 || octets.some((part) => !Number.isInteger(part))) return false;
  const [first, second] = octets;
  return (
    first === 10 ||
    first === 127 ||
    (first === 169 && second === 254) ||
    (first === 172 && second >= 16 && second <= 31) ||
    (first === 192 && second === 168) ||
    (first === 100 && second >= 64 && second <= 127)
  );
}

export function isOwnedTaskApiUrl(value: string): boolean {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    return false;
  }
  if (!['http:', 'https:'].includes(parsed.protocol)) return false;
  const host = parsed.hostname.replace(/^\[|\]$/g, '').toLowerCase();
  if (host === 'localhost') return true;
  const family = isIP(host);
  if (family === 4) return isOwnedIpv4(host);
  if (family === 6) {
    return (
      host === '::1' || host.startsWith('fc') || host.startsWith('fd') || host.startsWith('fe80:')
    );
  }
  return false;
}

function normalizeBaseUrl(value: string, allowPublicNetwork: boolean): string {
  const parsed = new URL(value);
  if (!isOwnedTaskApiUrl(parsed.toString())) {
    if (!allowPublicNetwork || parsed.protocol !== 'https:') {
      throw new Error('task API URL must be loopback/private/Tailscale, or explicit trusted HTTPS');
    }
  }
  parsed.pathname = parsed.pathname.replace(/\/+$/, '');
  parsed.search = '';
  parsed.hash = '';
  return parsed.toString().replace(/\/$/, '');
}

export class TaskApiClient {
  readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;
  private readonly timeoutMs: number;

  constructor(options: TaskApiClientOptions = {}) {
    this.baseUrl = normalizeBaseUrl(
      options.baseUrl || process.env.SCBE_TASK_API_URL || TASK_API_DEFAULT_URL,
      options.allowPublicNetwork === true
    );
    this.fetchImpl = options.fetchImpl || fetch;
    this.timeoutMs = Math.max(100, options.timeoutMs || 15_000);
  }

  private async request(pathname: string, init: RequestInit = {}): Promise<unknown> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await this.fetchImpl(`${this.baseUrl}${pathname}`, {
        ...init,
        headers: {
          ...(init.body ? { 'content-type': 'application/json' } : {}),
          ...(init.headers || {}),
        },
        signal: controller.signal,
      });
      const text = await response.text();
      let body: unknown = {};
      if (text) {
        try {
          body = JSON.parse(text);
        } catch {
          throw new Error(`task API returned non-JSON HTTP ${response.status}`);
        }
      }
      if (!response.ok) {
        const detail = isRecord(body)
          ? String(body.message || body.error || response.statusText)
          : response.statusText;
        throw new Error(`task API HTTP ${response.status}: ${detail}`);
      }
      return body;
    } finally {
      clearTimeout(timer);
    }
  }

  private parseRun(raw: unknown): GovernedTaskRun {
    const parsed = parseTaskApiRun(raw);
    if (!parsed.ok) throw new Error(`invalid task API run: ${parsed.errors.join('; ')}`);
    return parsed.data;
  }

  async health(): Promise<unknown> {
    return this.request('/v1/health');
  }

  async capabilities(): Promise<unknown> {
    return this.request('/v1/capabilities');
  }

  async createRun(payload: Record<string, unknown>): Promise<GovernedTaskRun> {
    return this.parseRun(
      await this.request('/v1/tasks/runs', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    );
  }

  async getRun(runId: string): Promise<GovernedTaskRun> {
    return this.parseRun(await this.request(`/v1/tasks/runs/${encodeURIComponent(runId)}`));
  }

  async listRuns(limit = 100): Promise<GovernedTaskRun[]> {
    const body = await this.request(`/v1/tasks/runs?limit=${Math.max(1, Math.min(500, limit))}`);
    if (!isRecord(body) || !Array.isArray(body.runs)) {
      throw new Error('task API run list is malformed');
    }
    return body.runs.map((run) => this.parseRun(run));
  }

  async getBasis(runId: string): Promise<TaskFieldBasis[]> {
    const body = await this.request(`/v1/tasks/runs/${encodeURIComponent(runId)}/basis`);
    if (!isRecord(body) || !Array.isArray(body.basis)) {
      throw new Error('task API basis response is malformed');
    }
    return z.array(TaskFieldBasisSchema).parse(body.basis);
  }

  async cancelRun(runId: string): Promise<GovernedTaskRun> {
    return this.parseRun(
      await this.request(`/v1/tasks/runs/${encodeURIComponent(runId)}/cancel`, {
        method: 'POST',
        body: '{}',
      })
    );
  }

  async createGroup(payload: { tasks: Array<Record<string, unknown>>; metadata?: unknown }) {
    return this.request('/v1/tasks/groups', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getInteraction(interactionId: string): Promise<unknown> {
    return this.request(`/v1/interactions/${encodeURIComponent(interactionId)}`);
  }

  async waitForRun(runId: string, options: WaitForTaskRunOptions = {}): Promise<GovernedTaskRun> {
    const timeoutMs = Math.max(100, options.timeoutMs || 60_000);
    const pollIntervalMs = Math.max(10, options.pollIntervalMs || 100);
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const run = await this.getRun(runId);
      if (['completed', 'failed', 'cancelled'].includes(run.status)) return run;
      await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
    }
    throw new Error(`task run ${runId} did not finish within ${timeoutMs}ms`);
  }
}
