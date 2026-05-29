import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {
  registerTool,
  unregisterTool,
  listTools,
  getTool,
  clearTools,
  buildToolArgv,
  auditToolRegistry,
  type CliTool,
} from '../src/tools.js';
import { runEvent } from '../src/index.js';
import { enqueueEvent, processOneEvent, getEventStatus } from '../src/queue.js';
import { clearPlugins } from '../src/plugins.js';

describe('tool registry', () => {
  beforeEach(() => clearTools());

  it('registers and lists tools', () => {
    const tool: CliTool = { name: 'echo-task', command: 'node', args: ['-e', 'console.log("ok")'] };
    registerTool(tool);
    expect(listTools()).toHaveLength(1);
    expect(listTools()[0].name).toBe('echo-task');
  });

  it('replaces tools with the same name', () => {
    registerTool({ name: 'dup', command: 'node', args: ['a.js'] });
    registerTool({ name: 'dup', command: 'python', args: ['a.py'] });
    expect(listTools()).toHaveLength(1);
    expect(listTools()[0].command).toBe('python');
  });

  it('unregisters a tool', () => {
    registerTool({ name: 'x', command: 'node', args: [] });
    expect(unregisterTool('x')).toBe(true);
    expect(listTools()).toHaveLength(0);
    expect(unregisterTool('x')).toBe(false);
  });

  it('getTool returns registered tool', () => {
    registerTool({ name: 'y', command: 'node', args: ['y.js'] });
    expect(getTool('y')?.command).toBe('node');
    expect(getTool('missing')).toBeUndefined();
  });

  it('buildToolArgv substitutes template variables', () => {
    const tool: CliTool = {
      name: 'runner',
      command: 'node',
      args: ['run.js', '--task', '{task}', '--series', '{seriesId}', '--root', '{repoRoot}'],
    };
    const event = { task: 'hello world', seriesId: 'abc123' };
    const opts = { repoRoot: '/tmp/repo' };
    const { command, args } = buildToolArgv(tool, event, opts, 'run-id-1');
    expect(command).toBe('node');
    expect(args).toContain('hello world');
    expect(args).toContain('abc123');
    expect(args).toContain('/tmp/repo');
  });

  it('buildToolArgv uses run_id as seriesId when event.seriesId is absent', () => {
    const tool: CliTool = { name: 'x', command: 'echo', args: ['{seriesId}'] };
    const { args } = buildToolArgv(tool, { task: 't' }, {}, 'fallback-id');
    expect(args[0]).toBe('fallback-id');
  });

  it('buildToolArgv leaves unknown placeholders intact', () => {
    const tool: CliTool = { name: 'x', command: 'echo', args: ['{unknownVar}'] };
    const { args } = buildToolArgv(tool, { task: 't' }, {}, 'r1');
    expect(args[0]).toBe('{unknownVar}');
  });

  it('audits tools into patent-facing surfaces and env readiness', () => {
    const audit = auditToolRegistry([
      {
        name: 'geoseal-compile',
        description: 'Compile natural-language intent into a GeoSeal command plan',
        command: 'python',
        args: ['-m', 'src.geoseal_cli', 'compile', '{task}'],
      },
      {
        name: 'research-uspto',
        description: 'Search USPTO patent applications. Requires USPTO_ODP_API_KEY env var.',
        command: 'python',
        args: ['scripts/research_api_bus.py', '--api', 'uspto', '--query', '{task}'],
      },
    ]);

    expect(audit.schema_version).toBe('scbe.agent_bus.tool_registry_audit.v1');
    expect(audit.tool_count).toBe(2);
    expect(audit.surface_counts['hyperbolic-governance']).toBe(1);
    expect(audit.surface_counts['research-evidence']).toBe(1);
    expect(audit.missing_required_env['research-uspto']).toContain('USPTO_ODP_API_KEY');
  });
});

describe('queue: tool routing', () => {
  let queueRoot: string;

  beforeEach(() => {
    queueRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-bus-tools-test-'));
    process.env.SCBE_BUS_QUEUE_ROOT = queueRoot;
    clearTools();
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

  it('dispatches to a registered tool and captures stdout', async () => {
    registerTool({
      name: 'echo-json',
      command: 'node',
      args: ['-e', 'process.stdout.write(JSON.stringify({ok:true,task:{sha256:null}}))'],
    });

    const runId = enqueueEvent({ task: 'hi', tool: 'echo-json' }, {}, 0);
    await processOneEvent();

    const status = getEventStatus(runId);
    expect(status).not.toBeNull();
    expect(status!.status).toBe('completed');
    expect(status!.result?.ok).toBe(true);
  });

  it('returns failed when tool exits with non-zero', async () => {
    registerTool({
      name: 'exit-1',
      command: 'node',
      args: ['-e', 'process.exit(1)'],
    });

    const runId = enqueueEvent({ task: 'fail', tool: 'exit-1' }, {}, 0);
    await processOneEvent();

    const status = getEventStatus(runId);
    expect(status!.status).toBe('failed');
    expect(status!.result?.ok).toBe(false);
  });

  it('returns failed immediately for unknown tool name', async () => {
    const runId = enqueueEvent({ task: 'hi', tool: 'no-such-tool' }, {}, 0);
    await processOneEvent();

    const status = getEventStatus(runId);
    expect(status!.status).toBe('failed');
    expect(status!.result?.stderr_tail).toMatch(/unknown tool/);
  });

  it('task template variable is passed to tool args', async () => {
    // Tool writes its received args to stdout as JSON so we can assert on them
    registerTool({
      name: 'echo-task',
      command: 'node',
      args: [
        '-e',
        'const t=process.argv[1]; process.stdout.write(JSON.stringify({ok:true,task:{sha256:null,echo:t}}))',
        '{task}',
      ],
    });

    const runId = enqueueEvent({ task: 'my-special-task', tool: 'echo-task' }, {}, 0);
    await processOneEvent();

    const status = getEventStatus(runId);
    expect(status!.status).toBe('completed');
    const resultPayload = status!.result?.result as Record<string, unknown> | null;
    expect((resultPayload?.task as Record<string, unknown>)?.echo).toBe('my-special-task');
  });
});

describe('direct runEvent: tool routing', () => {
  beforeEach(() => {
    clearTools();
    clearPlugins();
  });

  it('dispatches direct events to registered tools', async () => {
    registerTool({
      name: 'direct-echo',
      command: 'node',
      args: [
        '-e',
        'const t=process.argv[1]; process.stdout.write(JSON.stringify({ok:true,echo:t}))',
        '{task}',
      ],
    });

    const result = await runEvent({ task: 'direct-task', tool: 'direct-echo' });

    expect(result.ok).toBe(true);
    expect(result.exit_code).toBe(0);
    const payload = result.result as Record<string, unknown>;
    expect(payload.tool).toBe('direct-echo');
    expect((payload.parsed as Record<string, unknown>).echo).toBe('direct-task');
  });

  it('fails direct events with unknown tools without falling through to Python agentbus', async () => {
    const result = await runEvent({ task: 'direct-task', tool: 'missing-tool' });

    expect(result.ok).toBe(false);
    expect(result.exit_code).toBeNull();
    expect(result.stderr_tail).toMatch(/unknown tool/);
  });
});
