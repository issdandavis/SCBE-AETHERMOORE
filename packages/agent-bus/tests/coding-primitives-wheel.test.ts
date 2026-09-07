import { describe, expect, it } from 'vitest';
import { decode, encode } from '../../../src/tokenizer/ss1.js';
import {
  CODING_WHEEL_SCHEMA,
  appendReasoningArtifact,
  createReasoningArtifactGraph,
  executeCodingWheelProgram,
  hashReasoningValue,
  measureTritBands,
  measureWaferGeometry,
  parseCodingWheelProgram,
  reexecuteCodingWheelReceipt,
  serializeCodingWheelProgram,
  verifyCodingWheelReceipt,
  verifyReasoningArtifactGraph,
  wheelReceiptToReasoningArtifact,
  type BijectiveViewCodec,
  type CodingWheelProgram,
  type WheelDataOperator,
  type WheelExpression,
  type WheelExecutionLimits,
  type WheelExecutionReceipt,
} from '../src/index.js';

const literal = (value: number | boolean): WheelExpression => ({ kind: 'literal', value });
const read = (name: string): WheelExpression => ({ kind: 'read', name });
const data = (
  operator: WheelDataOperator,
  left: WheelExpression,
  right: WheelExpression
): WheelExpression => ({ kind: 'data', operator, left, right });
const program = (parameters: string[], body: WheelExpression): CodingWheelProgram => ({
  schema_version: CODING_WHEEL_SCHEMA,
  parameters,
  body,
});

const sacredTongueCodec: BijectiveViewCodec = {
  encode(tongue, canonical) {
    const encoded = encode(canonical, tongue, false);
    return encoded.length ? encoded.split(/\s+/u) : [];
  },
  decode(tongue, tokens) {
    return decode(tokens.join(' '), tongue);
  },
};

function factorialProgram(): CodingWheelProgram {
  return program(['n'], {
    kind: 'loop',
    count: read('n'),
    initial: literal(1),
    accumulator: 'product',
    index: 'position',
    body: data('multiply', read('product'), data('add', read('position'), literal(1))),
  });
}

describe('coding primitives wheel codec', () => {
  it('round-trips all five syntax forms with reserved-looking and Unicode names', () => {
    const source = program(['branch', 'φ lane'], {
      kind: 'bind',
      name: 'loop',
      value: data('add', read('branch'), read('φ lane')),
      body: {
        kind: 'sequence',
        expressions: [
          read('loop'),
          {
            kind: 'branch',
            condition: data('greater_than', read('loop'), literal(0)),
            when_true: {
              kind: 'loop',
              count: literal(2),
              initial: read('loop'),
              accumulator: 'acc',
              index: 'i',
              body: data('add', read('acc'), read('i')),
            },
            when_false: literal(0),
          },
        ],
      },
    });
    const tokens = serializeCodingWheelProgram(source);

    expect(parseCodingWheelProgram(tokens)).toEqual(source);
    expect(tokens).toContain('id:YnJhbmNo');
    expect(tokens).not.toContain('φ lane');
  });

  it('rejects trailing tokens, non-canonical numbers, and truncated programs', () => {
    const tokens = serializeCodingWheelProgram(program([], literal(1)));
    expect(() => parseCodingWheelProgram([...tokens, 'num:2'])).toThrow(/trailing tokens/);
    expect(() => parseCodingWheelProgram(['wheel:v1', 'parameters:0', 'num:01'])).toThrow(
      /non-canonical integer/
    );
    expect(() => parseCodingWheelProgram(['wheel:v1', 'parameters:0', 'branch', 'bool:1'])).toThrow(
      /truncated/
    );
  });

  it('rejects extra object fields instead of silently dropping them from the token stream', () => {
    const malformed = {
      schema_version: CODING_WHEEL_SCHEMA,
      parameters: [],
      body: { kind: 'literal', value: 1, ignored: 'unsafe' },
    } as unknown as CodingWheelProgram;
    expect(() => serializeCodingWheelProgram(malformed)).toThrow(
      /literal expression must contain exactly/
    );
  });
});

describe('bounded wheel execution', () => {
  it('executes DATA, BIND, BRANCH, LOOP, and SEQUENCE with a deterministic receipt', () => {
    const body: WheelExpression = {
      kind: 'bind',
      name: 'fact',
      value: factorialProgram().body,
      body: {
        kind: 'sequence',
        expressions: [
          data('equal', read('fact'), literal(720)),
          {
            kind: 'branch',
            condition: data('greater_than', read('fact'), literal(700)),
            when_true: read('fact'),
            when_false: literal(0),
          },
        ],
      },
    };
    const source = program(['n'], body);
    const first = executeCodingWheelProgram(source, { n: 6 });
    const second = executeCodingWheelProgram(source, { n: 6 });

    expect(first).toEqual(second);
    expect(first).toMatchObject({
      status: 'PASS',
      result: 720,
      error: null,
      semantics: 'finite-bounded-interpreter',
      universality_scope: 'abstract-unbounded-machine-only',
    });
    expect(first.stats.loop_iterations).toBe(6);
    expect(first.stats.bindings_created).toBe(1);
    expect(first.stats.branches_true).toBe(1);
    expect(first.stats.sequences_evaluated).toBe(1);
    expect(first.trace).toHaveLength(first.stats.node_evaluations);
    expect(first.trace.at(-1)).toMatchObject({ primitive: 'BIND', result: 720, path: '$' });
    expect(verifyCodingWheelReceipt(source, first)).toEqual({ ok: true, errors: [] });
  });

  it('evaluates only the selected BRANCH arm', () => {
    const source = program([], {
      kind: 'branch',
      condition: literal(true),
      when_true: literal(7),
      when_false: data('modulo', literal(1), literal(0)),
    });
    const receipt = executeCodingWheelProgram(source, {});

    expect(receipt.status).toBe('PASS');
    expect(receipt.result).toBe(7);
    expect(receipt.trace.some((event) => event.path.includes('when_false'))).toBe(false);
  });

  it('returns a hash-bound rejection receipt when loop fuel is exhausted', () => {
    const receipt = executeCodingWheelProgram(
      factorialProgram(),
      { n: 20 },
      {
        max_steps: 100,
        max_trace_events: 100,
        max_loop_iterations: 3,
      }
    );

    expect(receipt).toMatchObject({
      status: 'REJECTED',
      result: null,
      error: { code: 'LOOP_LIMIT', path: '$' },
    });
    expect(receipt.stats.loop_iterations).toBe(3);
    expect(receipt.receipt_sha256).toMatch(/^[a-f0-9]{64}$/u);
  });

  it('rejects type confusion, overflow, and a false Turing-completeness shortcut', () => {
    const typeError = executeCodingWheelProgram(
      program([], {
        kind: 'branch',
        condition: literal(1),
        when_true: literal(1),
        when_false: literal(0),
      }),
      {}
    );
    const overflow = executeCodingWheelProgram(
      program([], data('add', literal(Number.MAX_SAFE_INTEGER), literal(1))),
      {}
    );

    expect(typeError.error?.code).toBe('TYPE_ERROR');
    expect(overflow.error?.code).toBe('INTEGER_OVERFLOW');
    expect(overflow.universality_scope).toBe('abstract-unbounded-machine-only');
  });

  it('requires exact declared inputs and enough trace capacity for the fuel budget', () => {
    expect(() => executeCodingWheelProgram(program(['x'], read('x')), {})).toThrow(/exactly match/);
    expect(() =>
      executeCodingWheelProgram(program([], literal(1)), {}, { max_steps: 10, max_trace_events: 9 })
    ).toThrow(/cover every permitted/);
    expect(() =>
      executeCodingWheelProgram(program([], literal(1)), {}, {
        max_steps: 10,
        max_trace_events: 10,
        hidden_limit: 1,
      } as unknown as Partial<WheelExecutionLimits>)
    ).toThrow(/unknown wheel execution limit/);
  });
});

describe('reasoning graph bridge', () => {
  it('places a successful execution in the public DAG with a reversible tongue view', () => {
    const source = factorialProgram();
    const receipt = executeCodingWheelProgram(source, { n: 5 });
    const input = wheelReceiptToReasoningArtifact(source, receipt, {
      id: 'factorial-5',
      tongue: 'RU',
      feature_values: [receipt.stats.node_evaluations, receipt.stats.loop_iterations, 0],
      verification_inputs: { n: 5 },
    });
    const graph = appendReasoningArtifact(
      createReasoningArtifactGraph('wheel-fixture', ['steps', 'iterations', 'risk']),
      input,
      sacredTongueCodec
    );

    expect(input.policy).toBe('allow');
    expect(input.evidence_hashes).toContain(receipt.receipt_sha256);
    expect(graph.nodes['factorial-5']?.view_tokens.length).toBeGreaterThan(0);
    expect(verifyReasoningArtifactGraph(graph, { codec: sacredTongueCodec })).toMatchObject({
      ok: true,
      errors: [],
    });
  });

  it('keeps an unreproduced PASS quarantined and refuses an allow override', () => {
    const source = factorialProgram();
    const receipt = executeCodingWheelProgram(source, { n: 4 });
    const quarantined = wheelReceiptToReasoningArtifact(source, receipt, {
      id: 'unreproduced-pass',
      tongue: 'KO',
      feature_values: [1],
    });

    expect(quarantined.policy).toBe('quarantine');
    expect(quarantined.evidence_hashes).not.toContain(receipt.receipt_sha256);
    expect(quarantined.provenance_hashes).toContain(receipt.receipt_sha256);
    expect(() =>
      wheelReceiptToReasoningArtifact(source, receipt, {
        id: 'unearned-allow',
        tongue: 'KO',
        feature_values: [1],
        policy: 'allow',
      })
    ).toThrow(/requires verification_inputs/);
  });

  it('defaults rejected execution to quarantine and refuses an allow override', () => {
    const source = program([], data('modulo', literal(3), literal(0)));
    const receipt = executeCodingWheelProgram(source, {});
    const quarantined = wheelReceiptToReasoningArtifact(source, receipt, {
      id: 'failed-modulus',
      tongue: 'KO',
      feature_values: [1],
    });

    expect(quarantined.policy).toBe('quarantine');
    expect(() =>
      wheelReceiptToReasoningArtifact(source, receipt, {
        id: 'unsafe-allow',
        tongue: 'KO',
        feature_values: [1],
        policy: 'allow',
      })
    ).toThrow(/cannot create an allow artifact/);
  });

  it('detects a changed receipt before it becomes graph evidence', () => {
    const source = factorialProgram();
    const receipt = executeCodingWheelProgram(source, { n: 3 });
    const changed = { ...receipt, result: 999 };
    expect(() =>
      wheelReceiptToReasoningArtifact(source, changed, {
        id: 'changed',
        tongue: 'AV',
        feature_values: [0],
      })
    ).toThrow(/receipt hash mismatch/);
    expect(verifyCodingWheelReceipt(source, changed)).toMatchObject({
      ok: false,
      errors: expect.arrayContaining(['receipt hash mismatch']),
    });
  });

  it('rejects a self-consistent forged receipt by reproducing the execution', () => {
    const source = factorialProgram();
    const receipt = executeCodingWheelProgram(source, { n: 3 });
    const trace = receipt.trace.map((event) =>
      event.path === '$' ? { ...event, result: 999 } : event
    );
    const forgedBody = {
      ...receipt,
      result: 999,
      trace,
      trace_sha256: hashReasoningValue(trace),
    };
    const { receipt_sha256: _discarded, ...body } = forgedBody;
    const forged: WheelExecutionReceipt = {
      ...body,
      receipt_sha256: hashReasoningValue(body),
    };

    expect(verifyCodingWheelReceipt(source, forged)).toEqual({ ok: true, errors: [] });
    expect(reexecuteCodingWheelReceipt(source, forged, { n: 3 })).toMatchObject({
      ok: false,
      execution_reproduced: false,
      errors: expect.arrayContaining([
        'receipt execution could not be reproduced from the supplied inputs',
      ]),
    });
    expect(() =>
      wheelReceiptToReasoningArtifact(source, forged, {
        id: 'forged-result',
        tongue: 'AV',
        feature_values: [0],
        policy: 'allow',
        verification_inputs: { n: 3 },
      })
    ).toThrow(/lacks execution authority/);
  });
});

describe('wheel representation measurements', () => {
  it('reproduces the six-trit state, band, and balanced counts exactly', () => {
    expect(measureTritBands(6)).toMatchObject({
      states: 729,
      bands: 13,
      minimum_sum: -6,
      maximum_sum: 6,
      balanced_states: 141,
      binary_balanced_at_this_width: true,
      neutral_enables_balance_at_odd_width: false,
    });
    expect(measureTritBands(6).balanced_fraction).toBeCloseTo(141 / 729, 15);
    expect(measureTritBands(5)).toMatchObject({
      binary_balanced_at_this_width: false,
      neutral_enables_balance_at_odd_width: true,
    });
  });

  it('recomputes disk/sheet and rotation consistency without treating it as capability evidence', () => {
    const measured = measureWaferGeometry();

    expect(measured.cells).toBe(64);
    expect(measured.realms).toEqual([16, 16, 16, 16]);
    expect(measured.distance_pairs).toBe(2016);
    expect(measured.poincare_hyperboloid_max_abs_error).toBeLessThan(1e-11);
    expect(measured.hyperboloid_constraint_max_abs_error).toBeLessThan(1e-11);
    expect(measured.rotation_max_delta_radius).toBeLessThan(1e-15);
    expect(measured.authority).toBe('coordinate-consistency-only-not-reasoning-evidence');
  });
});
