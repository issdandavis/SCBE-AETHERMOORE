import { describe, expect, it } from 'vitest';
import {
  GOVERNED_TASK_SCHEMA_VERSION,
  GovernedTaskRun,
  normalizeTaskLabRun,
  sealGovernedTaskRun,
  sha256TaskValue,
  validateGovernedTaskRun,
  verifyGovernedTaskRunSeal,
} from '../../src/agentic/governed-task';

function supportedRun(): Record<string, unknown> {
  const result = { summary: 'The admitted source supports the bounded claim.' };
  return {
    run_id: 'trun_test_supported',
    interaction_id: 'int_test',
    status: 'completed',
    submitted_at: '2026-07-24T00:00:00Z',
    started_at: '2026-07-24T00:00:01Z',
    completed_at: '2026-07-24T00:00:02Z',
    input_sha256: '1'.repeat(64),
    output_sha256: sha256TaskValue(result),
    result,
    error: null,
    metrics: { evidence_selected: 1 },
    basis: [
      {
        field: '/summary',
        confidence: 0.75,
        reasoning: 'Lexical evidence synthesis from an admitted source.',
        citations: [
          {
            source_id: 'src_1',
            title: 'Bounded source',
            url: 'https://clay.local/source',
            content_sha256: '2'.repeat(64),
            quote: 'This is the admitted evidence quote.',
          },
        ],
      },
    ],
    disposition: {
      status: 'review_required',
      negative_example: false,
      do_not_promote_to_fact: true,
      reason: 'Evidence exists, but the output still requires review.',
    },
  };
}

describe('governed task contract', () => {
  it('normalizes a task-lab run and seals it deterministically', () => {
    const normalized = normalizeTaskLabRun(supportedRun());
    expect(normalized.schema_version).toBe(GOVERNED_TASK_SCHEMA_VERSION);
    expect(validateGovernedTaskRun(normalized)).toMatchObject({ ok: true, errors: [] });

    const first = sealGovernedTaskRun(normalized);
    const second = sealGovernedTaskRun(normalized);
    expect(first.contract_sha256).toBe(second.contract_sha256);
    expect(verifyGovernedTaskRunSeal(first)).toBe(true);
  });

  it('accepts unsupported output only as a fail-closed negative example', () => {
    const result = { summary: 'A positive-sounding unsupported claim.' };
    const negative = normalizeTaskLabRun({
      ...supportedRun(),
      run_id: 'trun_test_negative',
      result,
      output_sha256: sha256TaskValue(result),
      basis: [
        {
          field: '/summary',
          confidence: 0,
          reasoning: 'No admissible evidence supported this field.',
          citations: [],
        },
      ],
      disposition: {
        status: 'failed_evidence_check',
        negative_example: true,
        do_not_promote_to_fact: true,
        reason: 'Retain only as a negative example.',
      },
    });

    expect(validateGovernedTaskRun(negative).ok).toBe(true);
    expect(negative.disposition.negative_example).toBe(true);
  });

  it('rejects promotion or review status when evidence is absent', () => {
    const invalid = {
      ...normalizeTaskLabRun(supportedRun()),
      basis: [],
      disposition: {
        status: 'review_required',
        negative_example: false,
        do_not_promote_to_fact: false,
        reason: 'Pretend the claim passed.',
      },
    } as unknown as GovernedTaskRun;
    const checked = validateGovernedTaskRun(invalid);

    expect(checked.ok).toBe(false);
    expect(checked.errors.join(' ')).toContain('do_not_promote_to_fact');
    expect(checked.errors.join(' ')).toContain('failed_evidence_check');
  });

  it('normalizes cancellation without promoting partial output', () => {
    const cancelled = normalizeTaskLabRun({
      ...supportedRun(),
      run_id: 'trun_test_cancelled',
      status: 'cancelled',
      completed_at: '2026-07-24T00:00:01Z',
      output_sha256: undefined,
      result: null,
      basis: [],
      disposition: {
        status: 'pending',
        negative_example: false,
        do_not_promote_to_fact: true,
        reason: 'Task has not completed its evidence check.',
      },
    });

    expect(cancelled.disposition).toMatchObject({
      status: 'cancelled',
      negative_example: true,
      do_not_promote_to_fact: true,
    });
  });
});
