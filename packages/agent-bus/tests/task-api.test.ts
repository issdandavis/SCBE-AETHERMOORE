import { createServer } from 'node:http';
import { afterEach, describe, expect, it } from 'vitest';
import {
  GOVERNED_TASK_SCHEMA_VERSION,
  TaskApiClient,
  isOwnedTaskApiUrl,
  parseTaskApiRun,
} from '../src/task-api.js';

const servers: ReturnType<typeof createServer>[] = [];

afterEach(async () => {
  await Promise.all(
    servers.splice(0).map(
      (server) =>
        new Promise<void>((resolve) => {
          server.close(() => resolve());
        })
    )
  );
});

function rawRun(status: 'queued' | 'completed' = 'queued') {
  const completed = status === 'completed';
  return {
    run_id: 'trun_agent_bus_test',
    interaction_id: 'int_agent_bus_test',
    status,
    submitted_at: '2026-07-24T00:00:00Z',
    started_at: completed ? '2026-07-24T00:00:01Z' : null,
    completed_at: completed ? '2026-07-24T00:00:02Z' : null,
    input_sha256: '1'.repeat(64),
    ...(completed ? { output_sha256: '2'.repeat(64) } : {}),
    result: completed ? { summary: 'Bounded result.' } : null,
    error: null,
    basis: completed
      ? [
          {
            field: '/summary',
            confidence: 0.8,
            reasoning: 'Admitted source quote.',
            citations: [
              {
                source_id: 'source_1',
                title: 'Source',
                url: 'https://clay.local/source',
                content_sha256: '3'.repeat(64),
                quote: 'Bounded evidence.',
              },
            ],
          },
        ]
      : [],
    metrics: completed ? { evidence_selected: 1 } : {},
    disposition: completed
      ? {
          status: 'review_required',
          negative_example: false,
          do_not_promote_to_fact: true,
          reason: 'Evidence exists, but review is still required.',
        }
      : {
          status: 'pending',
          negative_example: false,
          do_not_promote_to_fact: true,
          reason: 'Task has not completed its evidence check.',
        },
  };
}

async function startFixtureServer(): Promise<string> {
  let reads = 0;
  const server = createServer((request, response) => {
    response.setHeader('content-type', 'application/json');
    if (request.method === 'POST' && request.url === '/v1/tasks/runs') {
      response.statusCode = 202;
      response.end(JSON.stringify(rawRun('queued')));
      return;
    }
    if (request.method === 'GET' && request.url === '/v1/tasks/runs/trun_agent_bus_test') {
      reads += 1;
      response.end(JSON.stringify(rawRun(reads > 1 ? 'completed' : 'queued')));
      return;
    }
    response.statusCode = 404;
    response.end(JSON.stringify({ error: 'not_found' }));
  });
  servers.push(server);
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('fixture server failed');
  return `http://127.0.0.1:${address.port}`;
}

describe('TaskApiClient', () => {
  it('submits and waits for a governed local task run', async () => {
    const baseUrl = await startFixtureServer();
    const client = new TaskApiClient({ baseUrl, timeoutMs: 2_000 });

    const queued = await client.createRun({ objective: 'Verify the contract.' });
    expect(queued.schema_version).toBe(GOVERNED_TASK_SCHEMA_VERSION);
    expect(queued.status).toBe('queued');

    const completed = await client.waitForRun(queued.run_id, {
      timeoutMs: 2_000,
      pollIntervalMs: 5,
    });
    expect(completed.status).toBe('completed');
    expect(completed.disposition).toMatchObject({
      status: 'review_required',
      do_not_promote_to_fact: true,
    });
  });

  it('rejects fail-open output with no evidence', () => {
    const invalid = {
      ...rawRun('completed'),
      basis: [],
      disposition: {
        status: 'review_required',
        negative_example: false,
        do_not_promote_to_fact: true,
        reason: 'Unsupported promotion.',
      },
    };
    const parsed = parseTaskApiRun(invalid);

    expect(parsed.ok).toBe(false);
    if (!parsed.ok) expect(parsed.errors.join(' ')).toContain('negative example');
  });

  it('allows owned literals and denies public routing by default', () => {
    expect(isOwnedTaskApiUrl('http://127.0.0.1:8766')).toBe(true);
    expect(isOwnedTaskApiUrl('http://100.87.197.29:8766')).toBe(true);
    expect(isOwnedTaskApiUrl('https://example.com')).toBe(false);
    expect(() => new TaskApiClient({ baseUrl: 'https://example.com' })).toThrow(
      /loopback\/private\/Tailscale/
    );
  });
});
