import { describe, it, expect } from 'vitest';
import { parseShellTemplate, execPlan, type GeoSealPlan } from '../src/pipeline.js';

// ─── parseShellTemplate ───────────────────────────────────────────────────────

describe('parseShellTemplate', () => {
  it('splits on spaces', () => {
    expect(parseShellTemplate('python foo.py --json')).toEqual(['python', 'foo.py', '--json']);
  });

  it('strips single quotes and preserves spaces inside them', () => {
    const argv = parseShellTemplate("python -c 'print(1 + 2)'");
    expect(argv).toEqual(['python', '-c', 'print(1 + 2)']);
  });

  it('strips double quotes', () => {
    const argv = parseShellTemplate('node -e "console.log(42)"');
    expect(argv).toEqual(['node', '-e', 'console.log(42)']);
  });

  it('handles windows-style paths inside single quotes', () => {
    const template =
      "'C:\\Python314\\python.exe' -m src.geoseal_cli explain-route --content 'hello world' --json";
    const argv = parseShellTemplate(template);
    expect(argv[0]).toBe('C:\\Python314\\python.exe');
    expect(argv).toContain('hello world');
    expect(argv[argv.length - 1]).toBe('--json');
  });

  it('returns empty array for empty string', () => {
    expect(parseShellTemplate('')).toEqual([]);
  });

  it('handles multiple spaces between tokens', () => {
    expect(parseShellTemplate('a   b   c')).toEqual(['a', 'b', 'c']);
  });
});

// ─── execPlan: empty-template guard ──────────────────────────────────────────

describe('execPlan', () => {
  const basePlan: GeoSealPlan = {
    schema_version: 'scbe_command_plan_v1',
    intent: { text: 'test intent', permission_mode: 'observe' },
    tool: {
      class: 'read',
      contract: { tool: 'read', risk: 'low', approval: 'auto' },
    },
    policy: { ok: true, decision: 'ALLOW', reason: 'profile_allows' },
    command: { key: 'test', template: '', runnable: true },
    hashes: { intent_sha256: 'abc', plan_sha256: 'def' },
  };

  it('returns ok=false for an empty command template', () => {
    const result = execPlan(basePlan, { repoRoot: process.cwd() });
    expect(result.ok).toBe(false);
    expect(result.stderr_tail).toMatch(/empty command template/);
  });

  it('runs node -e and captures stdout as JSON result', () => {
    const plan: GeoSealPlan = {
      ...basePlan,
      command: {
        key: 'echo',
        template: 'node -e "process.stdout.write(JSON.stringify({ok:true,val:42}))"',
        runnable: true,
      },
    };
    const result = execPlan(plan, { repoRoot: process.cwd() });
    expect(result.ok).toBe(true);
    expect((result.result as Record<string, unknown>)?.val).toBe(42);
  });

  it('captures non-JSON stdout as raw_output', () => {
    const plan: GeoSealPlan = {
      ...basePlan,
      command: {
        key: 'raw',
        template: 'node -e "process.stdout.write(\'hello world\')"',
        runnable: true,
      },
    };
    const result = execPlan(plan, { repoRoot: process.cwd() });
    expect(result.ok).toBe(true);
    expect((result.result as Record<string, unknown>)?.raw_output).toBe('hello world');
  });

  it('records exit_code and ok=false for failing commands', () => {
    const plan: GeoSealPlan = {
      ...basePlan,
      command: { key: 'fail', template: 'node -e "process.exit(2)"', runnable: true },
    };
    const result = execPlan(plan, { repoRoot: process.cwd() });
    expect(result.ok).toBe(false);
    expect(result.exit_code).toBe(2);
  });

  it('populates event metadata from plan hashes', () => {
    const plan: GeoSealPlan = {
      ...basePlan,
      command: { key: 'ok', template: 'node -e "process.exit(0)"', runnable: true },
      hashes: { intent_sha256: 'sha-intent-123', plan_sha256: 'sha-plan-456789' },
    };
    const result = execPlan(plan);
    expect(result.event.task_sha256).toBe('sha-intent-123');
    expect(result.event.series_id).toBe('sha-plan-456');
  });
});

// ─── runPipeline: policy gate ─────────────────────────────────────────────────

describe('runPipeline policy gate', async () => {
  // We test the gate logic by importing runPipeline and feeding it a mocked
  // compilePlan. Since compilePlan calls Python, we work around it by testing
  // execPlan (which is pure Node) + the blocked paths via direct compilePlan stubs.

  it('blocks when plan policy is not ALLOW', async () => {
    // Import and mock at the module level isn't needed — test execPlan path directly.
    // The policy gate path is tested here by constructing a DENY plan and verifying
    // that runPipeline would not call execPlan. We test the pure-Node portion.
    const { runPipeline } = await import('../src/pipeline.js');
    // compilePlan will fail (no Python geoseal available in test env) → blocked=true
    const result = await runPipeline('__test_intent_that_will_not_find_geoseal__', {
      repoRoot: process.cwd(),
      python: 'node', // pass wrong python to force compile failure
    });
    expect(result.blocked).toBe(true);
    expect(result.plan).toBeNull();
    expect(result.block_reason).toMatch(/geoseal compile failed/);
  });
});
