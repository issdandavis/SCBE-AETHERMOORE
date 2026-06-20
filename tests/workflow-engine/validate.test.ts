import { describe, it, expect } from 'vitest';
import { SCHEMA_VERSION, validate, preview } from '../../packages/workflow-engine/src/index';
import type { WorkflowSpec } from '../../packages/workflow-engine/src/types';

describe('workflow-engine types', () => {
  it('exports the canonical schema version', () => {
    expect(SCHEMA_VERSION).toBe('scbe.operation.v1');
  });
});

// ── validate ──────────────────────────────────────────────────────────────────

const validSpec: WorkflowSpec = {
  id: 'test-workflow',
  trigger: { kind: 'manual' },
  steps: [
    { id: 'step-1', op: 'echo', args: {} },
    { id: 'step-2', op: 'llm.chat', args: { messages: [] } },
  ],
};

describe('validate', () => {
  it('returns empty errors for a valid spec', () => {
    expect(validate(validSpec)).toEqual([]);
  });

  it('errors when spec id is empty', () => {
    const errors = validate({ ...validSpec, id: '' });
    expect(errors).toContainEqual({ field: 'id', message: expect.stringContaining('empty') });
  });

  it('errors when steps is empty', () => {
    const errors = validate({ ...validSpec, steps: [] });
    expect(errors).toContainEqual({ field: 'steps', message: expect.stringContaining('empty') });
  });

  it('errors on duplicate step ids', () => {
    const errors = validate({
      ...validSpec,
      steps: [
        { id: 'dup', op: 'echo', args: {} },
        { id: 'dup', op: 'llm.chat', args: {} },
      ],
    });
    expect(errors.some((e) => e.step_id === 'dup' && e.field === 'id')).toBe(true);
  });

  it('errors when a step op is empty', () => {
    const errors = validate({
      ...validSpec,
      steps: [{ id: 'step-1', op: '', args: {} }],
    });
    expect(errors).toContainEqual({
      step_id: 'step-1',
      field: 'op',
      message: expect.stringContaining('empty'),
    });
  });
});

// ── preview ───────────────────────────────────────────────────────────────────

describe('preview', () => {
  it('returns one OperationRequest per step', () => {
    expect(preview(validSpec)).toHaveLength(2);
  });

  it('each request has the correct op', () => {
    const reqs = preview(validSpec);
    expect(reqs[0].op).toBe('echo');
    expect(reqs[1].op).toBe('llm.chat');
  });

  it('each request carries the step args', () => {
    const reqs = preview(validSpec);
    expect(reqs[0].args).toEqual({});
    expect(reqs[1].args).toEqual({ messages: [] });
  });

  it('each request has a unique non-empty request_id', () => {
    const reqs = preview(validSpec);
    expect(reqs[0].request_id).toBeTruthy();
    expect(reqs[1].request_id).toBeTruthy();
    expect(reqs[0].request_id).not.toBe(reqs[1].request_id);
  });

  it('each request has dry_run: true', () => {
    for (const req of preview(validSpec)) {
      expect(req.dry_run).toBe(true);
    }
  });

  it('returns empty array for spec with no steps', () => {
    expect(preview({ id: 'empty', trigger: { kind: 'manual' }, steps: [] })).toEqual([]);
  });
});
