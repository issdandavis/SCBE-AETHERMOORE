import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {
  enqueueEvent,
  getEventStatus,
  getQueueStatus,
  processOneEvent,
  drainQueue,
  startQueueWorker,
  type QueuedEvent,
} from '../src/queue.js';
import { clearPlugins, registerPlugin } from '../src/plugins.js';

describe('queue', () => {
  let queueRoot: string;

  beforeEach(() => {
    queueRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-bus-queue-test-'));
    process.env.SCBE_BUS_QUEUE_ROOT = queueRoot;
    clearPlugins();
  });

  afterEach(() => {
    try {
      fs.rmSync(queueRoot, { recursive: true, force: true });
    } catch {
      // tolerate
    }
    delete process.env.SCBE_BUS_QUEUE_ROOT;
  });

  it('enqueues an event and returns a run_id', () => {
    const runId = enqueueEvent({ task: 'hello' }, { repoRoot: process.cwd() });
    expect(typeof runId).toBe('string');
    expect(runId.length).toBeGreaterThan(0);
  });

  it('getEventStatus finds pending events', () => {
    const runId = enqueueEvent({ task: 'hello' }, {});
    const status = getEventStatus(runId);
    expect(status).not.toBeNull();
    expect(status!.run_id).toBe(runId);
    expect(status!.status).toBe('pending');
  });

  it('getQueueStatus reports pending count', () => {
    enqueueEvent({ task: 'a' }, {});
    enqueueEvent({ task: 'b' }, {});
    const status = getQueueStatus();
    expect(status.pending).toBe(2);
    expect(status.running).toBe(0);
    expect(status.completed).toBe(0);
  });

  it('processOneEvent returns false when queue is empty', async () => {
    const didWork = await processOneEvent();
    expect(didWork).toBe(false);
  });

  it('processOneEvent handles a bad scbe-system-cli.py gracefully', async () => {
    // The event will fail because scbe-system-cli.py doesn't exist in tmpdir,
    // but it should still move to completed/failed.
    const runId = enqueueEvent({ task: 'hello' }, { repoRoot: process.cwd() }, 0);
    const didWork = await processOneEvent();
    expect(didWork).toBe(true);

    const status = getEventStatus(runId);
    expect(status).not.toBeNull();
    expect(status!.status).toBe('failed');
    expect(status!.result).toBeDefined();
    expect(status!.result!.ok).toBe(false);
  });

  it('plugin beforeRun can deny an event', async () => {
    registerPlugin({
      name: 'deny-all',
      beforeRun: async () => null,
    });
    const runId = enqueueEvent({ task: 'hello' }, { repoRoot: process.cwd() });
    await processOneEvent();

    const status = getEventStatus(runId);
    expect(status!.status).toBe('completed');
    expect(status!.result!.ok).toBe(false);
    expect(status!.result!.exit_code).toBe(403);
  });

  it('drainQueue processes all pending events', async () => {
    enqueueEvent({ task: 'a' }, { repoRoot: process.cwd() });
    enqueueEvent({ task: 'b' }, { repoRoot: process.cwd() });
    await drainQueue();
    const status = getQueueStatus();
    expect(status.pending).toBe(0);
    expect(status.completed + status.failed).toBe(2);
  });

  it('startQueueWorker polls repeatedly', async () => {
    enqueueEvent({ task: 'a' }, { repoRoot: process.cwd() });
    const handle = startQueueWorker(100);

    // Wait for worker to pick it up. Full-suite Windows runs can starve this
    // timeout briefly, so poll the queue state instead of relying on one sleep.
    const deadline = Date.now() + 2_000;
    let status = getQueueStatus();
    while (Date.now() < deadline) {
      status = getQueueStatus();
      if (status.pending === 0 && status.completed + status.failed === 1) break;
      await new Promise((resolve) => setTimeout(resolve, 50));
    }

    handle.stop();

    expect(status.pending).toBe(0);
    expect(status.completed + status.failed).toBe(1);
  });

  it('processOneEvent routes pipeline taskType through runPipeline', async () => {
    const fakeDir = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-bus-fake-geoseal-'));
    const fakeJs = path.join(fakeDir, 'fake-geoseal.js');
    const fakePlan = {
      schema_version: 'scbe_command_plan_v1',
      intent: { text: 'list files in current directory', permission_mode: 'observe' },
      tool: { class: 'read', contract: { tool: 'read', risk: 'low', approval: 'auto' } },
      policy: { ok: true, decision: 'ALLOW', reason: 'test_fake_geoseal' },
      command: {
        key: 'fake',
        template:
          'node -e "process.stdout.write(JSON.stringify({ok:true,source:\'fake-geoseal\'}))"',
        runnable: true,
      },
      hashes: { intent_sha256: 'fake-intent', plan_sha256: 'fake-plan-123456' },
    };
    fs.writeFileSync(
      fakeJs,
      `if (process.argv[2] === 'compile') process.stdout.write(${JSON.stringify(
        JSON.stringify(fakePlan)
      )}); else process.exit(2);\n`,
      'utf8'
    );
    const fakeBin =
      process.platform === 'win32'
        ? path.join(fakeDir, 'fake-geoseal.cmd')
        : path.join(fakeDir, 'fake-geoseal');
    if (process.platform === 'win32') {
      fs.writeFileSync(fakeBin, `@echo off\r\nnode "%~dp0fake-geoseal.js" %*\r\n`, 'utf8');
    } else {
      fs.writeFileSync(fakeBin, `#!/usr/bin/env sh\nnode "$0.js" "$@"\n`, 'utf8');
      fs.chmodSync(fakeBin, 0o755);
    }

    const repoRoot = process.env.SCBE_REPO_ROOT || process.cwd();
    const runId = enqueueEvent(
      { task: 'list files in current directory', taskType: 'pipeline' },
      { repoRoot, geosealBin: fakeBin }
    );
    await processOneEvent();

    const status = getEventStatus(runId);
    expect(status!.status).toBe('completed');
    // Pipeline should compile, get ALLOW, and execute successfully
    expect(status!.result!.ok).toBe(true);
    expect(status!.result!.result).toBeTruthy();
  });
});
