/**
 * @file sync-pipeline.ts
 * @module agent-bus/sync-pipeline
 *
 * Multi-pipeline sync scheduler with failure-catchup.
 *
 * Pattern (Thought Industries diagram):
 *   - N named pipelines run on independent schedules.
 *   - A failed job is NOT retried immediately — the next scheduled tick
 *     runs a "combined" job that replays the missed work alongside the current run.
 *   - Each pipeline tracks its own lag independently.
 *   - An observer can query which pipelines are current vs. lagging.
 *
 *              0:00     ~5:00     ~10:00    ~15:00
 *   Awards   [ Job1✓ ] [ Job2✗ ] [Job3+2✓] ...
 *   Users    [ Job1✓ ] [ Job2✓ ] [ Job3✓ ] ...
 *   AssignSub[ Job1✗ ] [Job2+1✓] [ Job3✓ ] ...
 */

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

// ─── Types ────────────────────────────────────────────────────────────────────

export type SyncJobType = 'scheduled' | 'combined';
export type SyncJobStatus = 'running' | 'completed' | 'failed';

/** Context passed to a pipeline handler on each tick. */
export interface SyncContext {
  pipelineId: string;
  jobId: string;
  /** 'combined' means this tick is also replaying a prior failed job. */
  jobType: SyncJobType;
  /** Set when jobType === 'combined' — the ID of the job being replayed. */
  catchupJobId?: string;
  scheduledAt: string;
}

export interface SyncJobResult {
  ok: boolean;
  detail?: string;
}

export interface SyncPipelineDefinition {
  name: string;
  /** How often to schedule a tick (ms). */
  intervalMs: number;
  handler: (ctx: SyncContext) => Promise<SyncJobResult>;
}

export interface SyncJobRecord {
  id: string;
  pipeline: string;
  type: SyncJobType;
  catchup_job_id?: string;
  status: SyncJobStatus;
  scheduled_at: string;
  started_at: string;
  finished_at?: string;
  ok?: boolean;
  detail?: string;
}

export interface SyncPipelineState {
  schema_version: 'scbe.sync_pipeline.v1';
  pipeline: string;
  last_successful_job_id: string | null;
  last_successful_at: string | null;
  /** Job ID that needs to be replayed on the next tick. */
  pending_catchup_job_id: string | null;
  /** Rolling log of recent jobs (capped at 32). */
  jobs: SyncJobRecord[];
}

/** Observer-facing pipeline status — mirrors what the analyst sees in the diagram. */
export interface SyncPipelineStatus {
  pipeline: string;
  /** True if the last successful sync is within 2× the pipeline's intervalMs. */
  current: boolean;
  /** How long since last success (ms), null if never succeeded. */
  lag_ms: number | null;
  last_successful_at: string | null;
  pending_catchup: boolean;
  last_job?: Pick<SyncJobRecord, 'id' | 'type' | 'status' | 'finished_at'>;
}

// ─── State persistence ────────────────────────────────────────────────────────

const JOB_LOG_CAP = 32;

function stateDir(): string {
  return path.resolve(process.env.SCBE_SYNC_STATE_ROOT || '.aethermoor-bus/sync-pipelines');
}

function statePath(pipelineName: string): string {
  const safe = pipelineName.replace(/[^a-z0-9_-]/gi, '-').slice(0, 64);
  return path.join(stateDir(), `${safe}.json`);
}

function loadState(pipelineName: string): SyncPipelineState {
  const p = statePath(pipelineName);
  if (!fs.existsSync(p)) {
    return {
      schema_version: 'scbe.sync_pipeline.v1',
      pipeline: pipelineName,
      last_successful_job_id: null,
      last_successful_at: null,
      pending_catchup_job_id: null,
      jobs: [],
    };
  }
  return JSON.parse(fs.readFileSync(p, 'utf8')) as SyncPipelineState;
}

function saveState(state: SyncPipelineState): void {
  const p = statePath(state.pipeline);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, `${JSON.stringify(state, null, 2)}\n`, 'utf8');
}

function appendJob(state: SyncPipelineState, job: SyncJobRecord): SyncPipelineState {
  const jobs = [...state.jobs, job].slice(-JOB_LOG_CAP);
  return { ...state, jobs };
}

// ─── Core tick ────────────────────────────────────────────────────────────────

function makeJobId(): string {
  return `${Date.now().toString(36)}-${crypto.randomBytes(3).toString('hex')}`;
}

/**
 * Execute one scheduled tick for a pipeline.
 *
 * If a prior job failed, this tick runs a combined job that supplies both
 * the catchup context and the new scheduled context to the handler.
 * The handler decides what to do with both (e.g. fetch a wider time window).
 */
async function runTick(def: SyncPipelineDefinition): Promise<void> {
  let state = loadState(def.name);

  const jobId = makeJobId();
  const scheduledAt = new Date().toISOString();
  const jobType: SyncJobType = state.pending_catchup_job_id ? 'combined' : 'scheduled';
  const catchupJobId = state.pending_catchup_job_id ?? undefined;

  const ctx: SyncContext = {
    pipelineId: def.name,
    jobId,
    jobType,
    catchupJobId,
    scheduledAt,
  };

  const startedAt = new Date().toISOString();
  const jobRecord: SyncJobRecord = {
    id: jobId,
    pipeline: def.name,
    type: jobType,
    catchup_job_id: catchupJobId,
    status: 'running',
    scheduled_at: scheduledAt,
    started_at: startedAt,
  };

  state = appendJob(state, jobRecord);
  saveState(state);

  let result: SyncJobResult;
  try {
    result = await def.handler(ctx);
  } catch (err) {
    result = {
      ok: false,
      detail: err instanceof Error ? err.message : String(err),
    };
  }

  const finishedAt = new Date().toISOString();
  const finalRecord: SyncJobRecord = {
    ...jobRecord,
    status: result.ok ? 'completed' : 'failed',
    finished_at: finishedAt,
    ok: result.ok,
    detail: result.detail,
  };

  // Replace the running record with the final one
  const jobs = state.jobs.map((j) => (j.id === jobId ? finalRecord : j));

  if (result.ok) {
    state = {
      ...state,
      jobs,
      last_successful_job_id: jobId,
      last_successful_at: finishedAt,
      // Clear catchup on success — the combined run resolved it
      pending_catchup_job_id: null,
    };
  } else {
    // On failure, park this job as the next catchup target.
    // If a catchup was already pending and this combined run also failed,
    // keep the ORIGINAL catchup job so the chain stays anchored to the
    // first missed sync point.
    state = {
      ...state,
      jobs,
      pending_catchup_job_id: catchupJobId ?? jobId,
    };
  }

  saveState(state);
}

// ─── SyncManager ─────────────────────────────────────────────────────────────

/**
 * Manages a fleet of named sync pipelines, each on its own schedule.
 *
 * @example
 * const manager = new SyncManager();
 *
 * manager.register({
 *   name: 'awards',
 *   intervalMs: 5 * 60_000,
 *   handler: async (ctx) => {
 *     // ctx.jobType === 'combined' means also replay ctx.catchupJobId window
 *     await syncAwards(ctx);
 *     return { ok: true };
 *   },
 * });
 *
 * manager.register({ name: 'users',            intervalMs: 5 * 60_000, handler: syncUsers });
 * manager.register({ name: 'assignment_submissions', intervalMs: 5 * 60_000, handler: syncSubs });
 *
 * manager.start();
 *
 * // Later — observer query:
 * const snapshot = manager.status();
 * snapshot.forEach(s => console.log(s.pipeline, s.current ? 'OK' : `LAG ${s.lag_ms}ms`));
 *
 * manager.stop();
 */
export class SyncManager {
  private readonly _defs = new Map<string, SyncPipelineDefinition>();
  private readonly _timers = new Map<string, ReturnType<typeof setInterval>>();
  private readonly _running = new Set<string>();

  register(def: SyncPipelineDefinition): this {
    if (this._timers.has(def.name)) {
      throw new Error(`SyncManager: pipeline '${def.name}' is already running — stop() first`);
    }
    this._defs.set(def.name, def);
    return this;
  }

  unregister(name: string): this {
    this._defs.delete(name);
    return this;
  }

  /** Start all registered pipelines. Each fires immediately, then on its interval. */
  start(): this {
    for (const [name, def] of this._defs) {
      if (this._timers.has(name)) continue;
      // Fire immediately then schedule
      void this._fire(def);
      const timer = setInterval(() => void this._fire(def), def.intervalMs);
      this._timers.set(name, timer);
    }
    return this;
  }

  /** Stop all running intervals. In-flight ticks finish naturally. */
  stop(): this {
    for (const [name, timer] of this._timers) {
      clearInterval(timer);
      this._timers.delete(name);
    }
    return this;
  }

  /**
   * Manually trigger a tick for a specific pipeline (useful for testing or
   * forcing a catchup run outside the normal schedule).
   */
  async tick(name: string): Promise<void> {
    const def = this._defs.get(name);
    if (!def) throw new Error(`SyncManager: unknown pipeline '${name}'`);
    await this._fire(def);
  }

  /** Observer query — returns current status for all registered pipelines. */
  status(): SyncPipelineStatus[] {
    const now = Date.now();
    return Array.from(this._defs.values()).map((def) => {
      const state = loadState(def.name);
      const lastJob = state.jobs.at(-1);
      const lagMs = state.last_successful_at
        ? now - new Date(state.last_successful_at).getTime()
        : null;
      const current = lagMs !== null && lagMs <= def.intervalMs * 2;
      return {
        pipeline: def.name,
        current,
        lag_ms: lagMs,
        last_successful_at: state.last_successful_at,
        pending_catchup: state.pending_catchup_job_id !== null,
        last_job: lastJob
          ? {
              id: lastJob.id,
              type: lastJob.type,
              status: lastJob.status,
              finished_at: lastJob.finished_at,
            }
          : undefined,
      };
    });
  }

  /** Status for a single pipeline. Returns null if not registered. */
  pipelineStatus(name: string): SyncPipelineStatus | null {
    return this.status().find((s) => s.pipeline === name) ?? null;
  }

  private async _fire(def: SyncPipelineDefinition): Promise<void> {
    if (this._running.has(def.name)) return; // previous tick still in-flight
    this._running.add(def.name);
    try {
      await runTick(def);
    } finally {
      this._running.delete(def.name);
    }
  }
}

// ─── Standalone helpers ────────────────────────────────────────────────────────

/** Load the persisted state for a pipeline (read-only observer use). */
export function getPipelineState(pipelineName: string): SyncPipelineState {
  return loadState(pipelineName);
}

/** Reset a pipeline's state (clears lag and catchup — use for fresh starts). */
export function resetPipelineState(pipelineName: string): void {
  const p = statePath(pipelineName);
  if (fs.existsSync(p)) fs.unlinkSync(p);
}
