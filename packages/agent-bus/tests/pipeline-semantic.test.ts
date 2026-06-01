/**
 * Semantic enrichment tests for the GeoSeal pipeline.
 *
 * Tests that compilePlan attaches a DecompositionResult to the returned plan,
 * and that runPipeline escalates ALLOW plans whose intent carries a
 * governance_steer discourse profile.
 *
 * spawnSync is mocked at the module level so these tests run without a real
 * GeoSeal CLI or Python installation. The mock is isolated to this file —
 * it does not affect the existing pipeline.test.ts environment.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { GeoSealPlan } from '../src/pipeline.js';

// ─── spawnSync mock ───────────────────────────────────────────────────────────
// Must be declared before the first import that pulls in pipeline.ts.

const mockSpawnSync = vi.fn();

vi.mock('node:child_process', () => ({
  spawnSync: (...args: unknown[]) => mockSpawnSync(...args),
  spawn: vi.fn(),
}));

// Import pipeline after the mock is registered.
const { compilePlan, runPipeline } = await import('../src/pipeline.js');

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fakePlanJson(overrides: Partial<GeoSealPlan> = {}): string {
  const base: GeoSealPlan = {
    schema_version: 'scbe_command_plan_v1',
    intent: { text: 'test intent', permission_mode: 'observe' },
    tool: { class: 'read', contract: { tool: 'read', risk: 'low', approval: 'auto' } },
    policy: { ok: true, decision: 'ALLOW', reason: 'profile_allows' },
    command: { key: 'test', template: '', runnable: false },
    hashes: { intent_sha256: 'aaa', plan_sha256: 'bbb' },
    ...overrides,
  };
  return JSON.stringify(base);
}

function successResult(stdout: string) {
  return { status: 0, stdout, stderr: '' };
}

function failResult() {
  return { status: 1, stdout: '', stderr: 'error' };
}

// ─── compilePlan: semantic attachment ────────────────────────────────────────

describe('compilePlan: semantic attachment', () => {
  const originalGeoSealBin = process.env.SCBE_GEOSEAL_BIN;

  beforeEach(() => {
    mockSpawnSync.mockReset();
    if (originalGeoSealBin === undefined) {
      delete process.env.SCBE_GEOSEAL_BIN;
    } else {
      process.env.SCBE_GEOSEAL_BIN = originalGeoSealBin;
    }
  });

  it('attaches semantic field when intent matches discourse atoms', () => {
    // "Let me explain / for example / similarly" → ANNOUNCE + EXPAND → long_turn
    const intent =
      'Let me explain the situation. For example, here is what happened. Similarly, this is a pattern.';
    mockSpawnSync.mockReturnValue(successResult(fakePlanJson()));
    const plan = compilePlan(intent, { repoRoot: process.cwd() });
    expect(plan).not.toBeNull();
    expect(plan!.semantic).toBeDefined();
    expect(plan!.semantic!.tokenCount).toBeGreaterThan(0);
  });

  it('attaches discourseProfile on the semantic field', () => {
    const intent = 'Let me explain the situation. For example, here is what happened.';
    mockSpawnSync.mockReturnValue(successResult(fakePlanJson()));
    const plan = compilePlan(intent, { repoRoot: process.cwd() });
    expect(plan!.semantic!.discourseProfile).toBe('long_turn');
  });

  it('attaches semantic = governance_steer when PIVOT + BLOCK present', () => {
    // "But the request was denied. However, the barrier blocked it."
    const intent = 'But the request was denied. However, the barrier blocked it.';
    mockSpawnSync.mockReturnValue(successResult(fakePlanJson()));
    const plan = compilePlan(intent, { repoRoot: process.cwd() });
    expect(plan!.semantic!.discourseProfile).toBe('governance_steer');
  });

  it('omits semantic field when no atoms match (pure numeric input)', () => {
    // A string with no surface-form matches at all
    mockSpawnSync.mockReturnValue(successResult(fakePlanJson()));
    const plan = compilePlan('123 456 789', { repoRoot: process.cwd() });
    // tokenCount === 0 → no semantic field
    expect(plan).not.toBeNull();
    expect(plan!.semantic).toBeUndefined();
  });

  it('returns null and does not call decompose when spawnSync fails', () => {
    mockSpawnSync.mockReturnValue(failResult());
    const plan = compilePlan('anything', { repoRoot: process.cwd() });
    expect(plan).toBeNull();
  });

  it('uses explicit geoseal binary before repo-local discovery', () => {
    mockSpawnSync.mockReturnValueOnce(successResult(fakePlanJson()));
    const plan = compilePlan('compile this through explicit geoseal', {
      repoRoot: process.cwd(),
      geosealBin: 'mock-geoseal',
    });
    expect(plan).not.toBeNull();
    expect(mockSpawnSync).toHaveBeenCalledTimes(1);
    expect(mockSpawnSync.mock.calls[0]?.[0]).toBe('mock-geoseal');
    expect(mockSpawnSync.mock.calls[0]?.[1]).toEqual([
      'compile',
      '--json',
      'compile this through explicit geoseal',
    ]);
  });

  it('falls back to an installed geoseal binary when repo-local compile fails', () => {
    process.env.SCBE_GEOSEAL_BIN = 'mock-geoseal';
    mockSpawnSync
      .mockReturnValueOnce(failResult())
      .mockReturnValueOnce(successResult(fakePlanJson()));
    const plan = compilePlan('compile this through installed geoseal', {
      repoRoot: process.cwd(),
    });
    expect(plan).not.toBeNull();
    expect(mockSpawnSync).toHaveBeenCalledTimes(2);
    expect(mockSpawnSync.mock.calls[1]?.[0]).toBe('mock-geoseal');
    expect(mockSpawnSync.mock.calls[1]?.[1]).toEqual([
      'compile',
      '--json',
      'compile this through installed geoseal',
    ]);
  });

  it('plan.semantic.atoms includes expected atom IDs for governance intent', () => {
    const intent = 'But the system threw an error. Actually the request was denied.';
    mockSpawnSync.mockReturnValue(successResult(fakePlanJson()));
    const plan = compilePlan(intent, { repoRoot: process.cwd() });
    const atomIds = new Set(plan!.semantic!.atoms.map((a) => a.semanticId));
    expect(atomIds.has('PIVOT')).toBe(true);
    expect(atomIds.has('BLOCK')).toBe(true);
  });
});

// ─── runPipeline: governance_steer auto-escalation ───────────────────────────

describe('runPipeline: governance_steer escalation', () => {
  beforeEach(() => mockSpawnSync.mockReset());

  it('blocks an ALLOW plan when intent discourse profile is governance_steer', async () => {
    // GeoSeal says ALLOW, but the intent contains PIVOT+BLOCK
    const intent = 'But the system threw an error. However, the request was denied at the gateway.';
    mockSpawnSync.mockReturnValue(
      successResult(
        fakePlanJson({ command: { key: 'test', template: 'node -e "1"', runnable: true } })
      )
    );
    const result = await runPipeline(intent, { repoRoot: process.cwd() });
    expect(result.blocked).toBe(true);
    expect(result.semantic_escalation).toBe('governance_steer');
    expect(result.block_reason).toMatch(/governance_steer/);
    expect(result.plan).not.toBeNull();
  });

  it('includes the compiled plan in the blocked result (auditable)', async () => {
    const intent = 'But the error was blocked. However, the exception was denied.';
    mockSpawnSync.mockReturnValue(
      successResult(
        fakePlanJson({ command: { key: 'run', template: 'node -e "1"', runnable: true } })
      )
    );
    const result = await runPipeline(intent, { repoRoot: process.cwd() });
    // Plan is preserved so operators can audit what would have run
    expect(result.plan).not.toBeNull();
    expect(result.plan!.policy.decision).toBe('ALLOW');
    expect(result.plan!.semantic?.discourseProfile).toBe('governance_steer');
  });

  it('does NOT escalate a normal ALLOW plan (no governance_steer)', async () => {
    // A pure coding intent with no discourse markers
    const intent = 'compile the TypeScript files and run the tests';
    mockSpawnSync.mockReturnValue(
      successResult(
        fakePlanJson({
          command: {
            key: 'run',
            template: 'node -e "process.stdout.write(JSON.stringify({ok:true}))"',
            runnable: true,
          },
        })
      )
    );
    const result = await runPipeline(intent, { repoRoot: process.cwd() });
    // No governance_steer → should execute (or fail on non-runnable, not escalate)
    expect(result.semantic_escalation).toBeUndefined();
    if (result.blocked) {
      // If blocked for other reasons (circuit open, runnable=false, etc.) that's fine
      // — just not for semantic_escalation
      expect(result.block_reason).not.toMatch(/governance_steer/);
    }
  });

  it('policy DENY takes priority over semantic escalation', async () => {
    // Even with governance_steer, if GeoSeal already DENYs it, policy reason shows
    const intent = 'But the error was blocked at the barrier';
    mockSpawnSync.mockReturnValue(
      successResult(
        fakePlanJson({
          policy: { ok: false, decision: 'DENY', reason: 'tool_class_blocked' },
          command: { key: 'run', template: 'node -e "1"', runnable: true },
        })
      )
    );
    const result = await runPipeline(intent, { repoRoot: process.cwd() });
    expect(result.blocked).toBe(true);
    expect(result.block_reason).toMatch(/policy DENY/);
    // semantic_escalation is NOT set — the policy gate fired first
    expect(result.semantic_escalation).toBeUndefined();
  });

  it('compile failure path still works (no regression)', async () => {
    mockSpawnSync.mockReturnValue(failResult());
    const result = await runPipeline('anything', { repoRoot: process.cwd() });
    expect(result.blocked).toBe(true);
    expect(result.plan).toBeNull();
    expect(result.block_reason).toMatch(/geoseal compile failed/);
  });
});
