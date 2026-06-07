/**
 * @file sync-pipeline.test.ts
 * Tests the scheduled/combined catchup behavior for sync pipelines.
 */

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { SyncManager, getPipelineState } from '../src/sync-pipeline.js';

let stateRoot = '';

beforeEach(() => {
  stateRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-sync-pipeline-'));
  process.env.SCBE_SYNC_STATE_ROOT = stateRoot;
});

afterEach(() => {
  delete process.env.SCBE_SYNC_STATE_ROOT;
  fs.rmSync(stateRoot, { recursive: true, force: true });
});

describe('SyncManager', () => {
  it('replays a failed job as a combined catchup tick', async () => {
    const manager = new SyncManager();
    const seen: Array<{ jobType: string; catchupJobId?: string }> = [];
    let calls = 0;

    manager.register({
      name: 'awards',
      intervalMs: 60_000,
      handler: async (ctx) => {
        seen.push({ jobType: ctx.jobType, catchupJobId: ctx.catchupJobId });
        calls += 1;
        return calls === 1 ? { ok: false, detail: 'upstream timeout' } : { ok: true };
      },
    });

    await manager.tick('awards');
    let state = getPipelineState('awards');
    expect(state.pending_catchup_job_id).toBeTruthy();
    expect(state.jobs.at(-1)?.status).toBe('failed');

    await manager.tick('awards');
    state = getPipelineState('awards');
    expect(state.pending_catchup_job_id).toBeNull();
    expect(state.jobs.at(-1)?.type).toBe('combined');
    expect(state.jobs.at(-1)?.status).toBe('completed');
    expect(seen[0]).toEqual({ jobType: 'scheduled', catchupJobId: undefined });
    expect(seen[1].jobType).toBe('combined');
    expect(seen[1].catchupJobId).toBe(state.jobs[0].id);
  });
});
