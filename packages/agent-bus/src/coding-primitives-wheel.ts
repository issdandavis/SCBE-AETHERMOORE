/**
 * A small, typed instruction language for public, verifiable agent reasoning.
 *
 * DATA, BIND, BRANCH, and LOOP are the executable primitives. SEQUENCE is the
 * composition rule. Every concrete run is finite: fuel, loop iterations,
 * lexical bindings, depth, and trace size are bounded and included in a
 * hash-bound receipt. Universality applies only to the corresponding abstract
 * machine with unbounded storage and execution time.
 */

import {
  hashReasoningValue,
  type ArtifactPolicy,
  type ReasoningArtifactInput,
  type ReasoningTongue,
} from './reasoning-artifact-graph.js';

export const CODING_WHEEL_SCHEMA = 'scbe.coding_primitives_wheel.v1' as const;
export type WheelValue = number | boolean;
export type WheelPrimitive = 'DATA' | 'BIND' | 'BRANCH' | 'LOOP' | 'SEQUENCE';
export type WheelDataOperator =
  | 'add'
  | 'subtract'
  | 'multiply'
  | 'modulo'
  | 'greater_than'
  | 'equal';

export interface WheelLiteralExpression {
  kind: 'literal';
  value: WheelValue;
}

export interface WheelReadExpression {
  kind: 'read';
  name: string;
}

export interface WheelDataExpression {
  kind: 'data';
  operator: WheelDataOperator;
  left: WheelExpression;
  right: WheelExpression;
}

export interface WheelBindExpression {
  kind: 'bind';
  name: string;
  value: WheelExpression;
  body: WheelExpression;
}

export interface WheelBranchExpression {
  kind: 'branch';
  condition: WheelExpression;
  when_true: WheelExpression;
  when_false: WheelExpression;
}

export interface WheelLoopExpression {
  kind: 'loop';
  count: WheelExpression;
  initial: WheelExpression;
  accumulator: string;
  index: string;
  body: WheelExpression;
}

export interface WheelSequenceExpression {
  kind: 'sequence';
  expressions: WheelExpression[];
}

export type WheelExpression =
  | WheelLiteralExpression
  | WheelReadExpression
  | WheelDataExpression
  | WheelBindExpression
  | WheelBranchExpression
  | WheelLoopExpression
  | WheelSequenceExpression;

export interface CodingWheelProgram {
  schema_version: typeof CODING_WHEEL_SCHEMA;
  parameters: string[];
  body: WheelExpression;
}

export interface WheelExecutionLimits {
  max_steps: number;
  max_loop_iterations: number;
  max_bindings: number;
  max_depth: number;
  max_trace_events: number;
}

export interface WheelExecutionStats {
  node_evaluations: number;
  data_evaluations: number;
  bindings_created: number;
  branches_true: number;
  branches_false: number;
  loop_iterations: number;
  sequences_evaluated: number;
  maximum_depth: number;
  peak_bindings: number;
}

export interface WheelTraceEvent {
  sequence: number;
  path: string;
  node_kind: WheelExpression['kind'];
  primitive: WheelPrimitive;
  result: WheelValue;
  detail: string | null;
}

export type WheelExecutionErrorCode =
  | 'STEP_LIMIT'
  | 'LOOP_LIMIT'
  | 'DEPTH_LIMIT'
  | 'TRACE_LIMIT'
  | 'BINDING_LIMIT'
  | 'UNKNOWN_NAME'
  | 'TYPE_ERROR'
  | 'INTEGER_OVERFLOW'
  | 'INVALID_MODULUS'
  | 'INVALID_LOOP_COUNT';

export interface WheelExecutionFailure {
  code: WheelExecutionErrorCode;
  path: string;
  message: string;
}

export interface WheelExecutionReceipt {
  schema_version: 'scbe.coding_primitives_execution.v1';
  status: 'PASS' | 'REJECTED';
  semantics: 'finite-bounded-interpreter';
  universality_scope: 'abstract-unbounded-machine-only';
  program_sha256: string;
  token_stream_sha256: string;
  input_sha256: string;
  limits: WheelExecutionLimits;
  result: WheelValue | null;
  error: WheelExecutionFailure | null;
  stats: WheelExecutionStats;
  trace: WheelTraceEvent[];
  trace_sha256: string;
  receipt_sha256: string;
}

export interface WheelReceiptVerification {
  ok: boolean;
  errors: string[];
}

export interface WheelReceiptReexecution extends WheelReceiptVerification {
  execution_reproduced: boolean;
  reproduced_receipt_sha256: string | null;
}

export interface WheelReasoningArtifactOptions {
  id: string;
  parent_ids?: readonly string[];
  tongue: ReasoningTongue;
  feature_values: readonly number[];
  /** Required before a PASS receipt may become an allow artifact. */
  verification_inputs?: Readonly<Record<string, WheelValue>>;
  policy?: ArtifactPolicy;
  public_summary?: string;
  state_transition?: string;
  evidence_hashes?: readonly string[];
  provenance_hashes?: readonly string[];
}

export interface TritBandMeasurement {
  schema_version: 'scbe.trit_band_measurement.v1';
  width: number;
  states: number;
  bands: number;
  minimum_sum: number;
  maximum_sum: number;
  balanced_states: number;
  balanced_fraction: number;
  binary_balanced_at_this_width: boolean;
  neutral_enables_balance_at_odd_width: boolean;
  authority: 'combinatorial-count-only-not-capability-evidence';
}

export interface WaferGeometryMeasurement {
  schema_version: 'scbe.wafer_coordinate_measurement.v1';
  cells: 64;
  realms: [16, 16, 16, 16];
  bevel: 0.02;
  distance_pairs: number;
  poincare_hyperboloid_max_abs_error: number;
  hyperboloid_constraint_max_abs_error: number;
  rotation_max_delta_radius: number;
  authority: 'coordinate-consistency-only-not-reasoning-evidence';
}

const DATA_OPERATORS: readonly WheelDataOperator[] = [
  'add',
  'subtract',
  'multiply',
  'modulo',
  'greater_than',
  'equal',
];
const MAX_PROGRAM_TOKENS = 16_384;
const MAX_AST_NODES = 4096;
const MAX_AST_DEPTH = 256;
const MAX_PARAMETERS = 256;
const MAX_SEQUENCE_EXPRESSIONS = 1024;
const HARD_LIMITS: WheelExecutionLimits = {
  max_steps: 100_000,
  max_loop_iterations: 100_000,
  max_bindings: 4096,
  max_depth: 256,
  max_trace_events: 100_000,
};
const DEFAULT_LIMITS: WheelExecutionLimits = {
  max_steps: 10_000,
  max_loop_iterations: 10_000,
  max_bindings: 256,
  max_depth: 128,
  max_trace_events: 10_000,
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function requireExactKeys(
  value: Record<string, unknown>,
  expected: readonly string[],
  label: string
): void {
  const actual = Object.keys(value).sort();
  const wanted = [...expected].sort();
  if (actual.length !== wanted.length || actual.some((key, index) => key !== wanted[index])) {
    throw new Error(`${label} must contain exactly: ${wanted.join(', ')}`);
  }
}

function requireName(value: unknown, label = 'name'): asserts value is string {
  if (
    typeof value !== 'string' ||
    value.length === 0 ||
    value.trim() !== value ||
    Buffer.byteLength(value, 'utf8') > 128 ||
    /[\u0000-\u001f\u007f]/u.test(value)
  ) {
    throw new Error(
      `${label} must be a non-empty UTF-8 name of at most 128 bytes without controls`
    );
  }
}

function requireSafeInteger(value: unknown, label: string): asserts value is number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value)) {
    throw new Error(`${label} must be a safe integer`);
  }
}

function encodeName(name: string): string {
  requireName(name);
  return `id:${Buffer.from(name, 'utf8').toString('base64url')}`;
}

function decodeName(token: string): string {
  if (!token.startsWith('id:')) throw new Error('expected an encoded identifier token');
  const encoded = token.slice(3);
  const decoded = Buffer.from(encoded, 'base64url').toString('utf8');
  requireName(decoded);
  if (encodeName(decoded) !== token)
    throw new Error('identifier token is not canonical UTF-8 base64url');
  return decoded;
}

function primitiveOf(expression: WheelExpression): WheelPrimitive {
  if (expression.kind === 'bind') return 'BIND';
  if (expression.kind === 'branch') return 'BRANCH';
  if (expression.kind === 'loop') return 'LOOP';
  if (expression.kind === 'sequence') return 'SEQUENCE';
  return 'DATA';
}

function serializeExpression(
  expression: unknown,
  tokens: string[],
  state: { nodes: number },
  depth: number
): void {
  if (depth > MAX_AST_DEPTH) throw new Error(`program depth exceeds ${MAX_AST_DEPTH}`);
  if (++state.nodes > MAX_AST_NODES)
    throw new Error(`program contains more than ${MAX_AST_NODES} nodes`);
  if (!isRecord(expression) || typeof expression.kind !== 'string') {
    throw new Error('wheel expression must be a typed object');
  }
  switch (expression.kind) {
    case 'literal': {
      requireExactKeys(expression, ['kind', 'value'], 'literal expression');
      if (typeof expression.value === 'boolean') {
        tokens.push(expression.value ? 'bool:1' : 'bool:0');
      } else {
        requireSafeInteger(expression.value, 'literal value');
        tokens.push(`num:${expression.value}`);
      }
      return;
    }
    case 'read':
      requireExactKeys(expression, ['kind', 'name'], 'read expression');
      requireName(expression.name);
      tokens.push('read', encodeName(expression.name));
      return;
    case 'data':
      requireExactKeys(expression, ['kind', 'operator', 'left', 'right'], 'data expression');
      if (!DATA_OPERATORS.includes(expression.operator as WheelDataOperator)) {
        throw new Error(`unknown DATA operator: ${String(expression.operator)}`);
      }
      tokens.push(`data:${expression.operator}`);
      serializeExpression(expression.left, tokens, state, depth + 1);
      serializeExpression(expression.right, tokens, state, depth + 1);
      return;
    case 'bind':
      requireExactKeys(expression, ['kind', 'name', 'value', 'body'], 'bind expression');
      requireName(expression.name);
      tokens.push('bind', encodeName(expression.name));
      serializeExpression(expression.value, tokens, state, depth + 1);
      serializeExpression(expression.body, tokens, state, depth + 1);
      return;
    case 'branch':
      requireExactKeys(
        expression,
        ['kind', 'condition', 'when_true', 'when_false'],
        'branch expression'
      );
      tokens.push('branch');
      serializeExpression(expression.condition, tokens, state, depth + 1);
      serializeExpression(expression.when_true, tokens, state, depth + 1);
      serializeExpression(expression.when_false, tokens, state, depth + 1);
      return;
    case 'loop':
      requireExactKeys(
        expression,
        ['kind', 'count', 'initial', 'accumulator', 'index', 'body'],
        'loop expression'
      );
      requireName(expression.accumulator, 'loop accumulator');
      requireName(expression.index, 'loop index');
      if (expression.accumulator === expression.index) {
        throw new Error('loop accumulator and index must use distinct names');
      }
      tokens.push('loop', encodeName(expression.accumulator), encodeName(expression.index));
      serializeExpression(expression.count, tokens, state, depth + 1);
      serializeExpression(expression.initial, tokens, state, depth + 1);
      serializeExpression(expression.body, tokens, state, depth + 1);
      return;
    case 'sequence': {
      requireExactKeys(expression, ['kind', 'expressions'], 'sequence expression');
      if (
        !Array.isArray(expression.expressions) ||
        expression.expressions.length === 0 ||
        expression.expressions.length > MAX_SEQUENCE_EXPRESSIONS
      ) {
        throw new Error(`sequence must contain 1..${MAX_SEQUENCE_EXPRESSIONS} expressions`);
      }
      tokens.push(`sequence:${expression.expressions.length}`);
      for (const child of expression.expressions) {
        serializeExpression(child, tokens, state, depth + 1);
      }
      return;
    }
    default:
      throw new Error(`unknown wheel expression kind: ${expression.kind}`);
  }
}

/** Serialize to an unambiguous, prefix-coded token stream. */
export function serializeCodingWheelProgram(program: CodingWheelProgram): string[] {
  if (!isRecord(program)) throw new Error('wheel program must be an object');
  requireExactKeys(program, ['schema_version', 'parameters', 'body'], 'wheel program');
  if (program.schema_version !== CODING_WHEEL_SCHEMA)
    throw new Error('unknown wheel program schema');
  if (!Array.isArray(program.parameters) || program.parameters.length > MAX_PARAMETERS) {
    throw new Error(`parameters must contain at most ${MAX_PARAMETERS} names`);
  }
  const parameters = program.parameters.map((name) => {
    requireName(name, 'parameter');
    return name;
  });
  if (new Set(parameters).size !== parameters.length) throw new Error('parameters must be unique');
  const tokens = ['wheel:v1', `parameters:${parameters.length}`, ...parameters.map(encodeName)];
  serializeExpression(program.body, tokens, { nodes: 0 }, 0);
  if (tokens.length > MAX_PROGRAM_TOKENS) {
    throw new Error(`program token stream exceeds ${MAX_PROGRAM_TOKENS} tokens`);
  }
  return tokens;
}

function parseUnsignedCount(token: string, prefix: string, maximum: number): number {
  if (!token.startsWith(prefix)) throw new Error(`expected ${prefix} token`);
  const text = token.slice(prefix.length);
  if (!/^(0|[1-9][0-9]*)$/u.test(text)) throw new Error(`non-canonical count token: ${token}`);
  const value = Number(text);
  if (!Number.isSafeInteger(value) || value > maximum) throw new Error(`count exceeds ${maximum}`);
  return value;
}

/** Parse only canonical streams and reject truncation or trailing material. */
export function parseCodingWheelProgram(input: readonly string[]): CodingWheelProgram {
  if (!Array.isArray(input) || input.length < 3 || input.length > MAX_PROGRAM_TOKENS) {
    throw new Error('invalid wheel token stream length');
  }
  if (
    input.some((token) => typeof token !== 'string' || token.length === 0 || token.length > 256)
  ) {
    throw new Error('wheel tokens must be non-empty strings of at most 256 characters');
  }
  let cursor = 0;
  let nodes = 0;
  const take = (): string => {
    const token = input[cursor++];
    if (token === undefined) throw new Error('truncated wheel token stream');
    return token;
  };
  if (take() !== 'wheel:v1') throw new Error('unknown wheel token-stream version');
  const parameterCount = parseUnsignedCount(take(), 'parameters:', MAX_PARAMETERS);
  const parameters = Array.from({ length: parameterCount }, () => decodeName(take()));
  if (new Set(parameters).size !== parameters.length) throw new Error('parameters must be unique');

  const expression = (depth: number): WheelExpression => {
    if (depth > MAX_AST_DEPTH) throw new Error(`program depth exceeds ${MAX_AST_DEPTH}`);
    if (++nodes > MAX_AST_NODES)
      throw new Error(`program contains more than ${MAX_AST_NODES} nodes`);
    const token = take();
    if (token === 'bool:0' || token === 'bool:1') {
      return { kind: 'literal', value: token === 'bool:1' };
    }
    if (token.startsWith('num:')) {
      const text = token.slice(4);
      if (!/^-?(0|[1-9][0-9]*)$/u.test(text) || text === '-0') {
        throw new Error(`non-canonical integer token: ${token}`);
      }
      const value = Number(text);
      requireSafeInteger(value, 'numeric token');
      return { kind: 'literal', value };
    }
    if (token === 'read') return { kind: 'read', name: decodeName(take()) };
    if (token.startsWith('data:')) {
      const operator = token.slice(5) as WheelDataOperator;
      if (!DATA_OPERATORS.includes(operator)) throw new Error(`unknown DATA operator: ${operator}`);
      return { kind: 'data', operator, left: expression(depth + 1), right: expression(depth + 1) };
    }
    if (token === 'bind') {
      const name = decodeName(take());
      return { kind: 'bind', name, value: expression(depth + 1), body: expression(depth + 1) };
    }
    if (token === 'branch') {
      return {
        kind: 'branch',
        condition: expression(depth + 1),
        when_true: expression(depth + 1),
        when_false: expression(depth + 1),
      };
    }
    if (token === 'loop') {
      const accumulator = decodeName(take());
      const index = decodeName(take());
      if (accumulator === index) throw new Error('loop accumulator and index must be distinct');
      return {
        kind: 'loop',
        accumulator,
        index,
        count: expression(depth + 1),
        initial: expression(depth + 1),
        body: expression(depth + 1),
      };
    }
    if (token.startsWith('sequence:')) {
      const count = parseUnsignedCount(token, 'sequence:', MAX_SEQUENCE_EXPRESSIONS);
      if (count === 0) throw new Error('sequence must contain at least one expression');
      return {
        kind: 'sequence',
        expressions: Array.from({ length: count }, () => expression(depth + 1)),
      };
    }
    throw new Error(`unknown wheel token: ${token}`);
  };

  const program: CodingWheelProgram = {
    schema_version: CODING_WHEEL_SCHEMA,
    parameters,
    body: expression(0),
  };
  if (cursor !== input.length) throw new Error('trailing tokens are not part of the wheel program');
  const canonical = serializeCodingWheelProgram(program);
  if (canonical.some((token, index) => token !== input[index])) {
    throw new Error('wheel token stream is not canonical');
  }
  return program;
}

function normalizeLimits(input: Partial<WheelExecutionLimits>): WheelExecutionLimits {
  if (!isRecord(input)) throw new Error('wheel execution limits must be an object');
  const allowed = new Set(Object.keys(DEFAULT_LIMITS));
  const unknown = Object.keys(input).filter((key) => !allowed.has(key));
  if (unknown.length > 0) {
    throw new Error(`unknown wheel execution limit: ${unknown[0]}`);
  }
  const output: WheelExecutionLimits = { ...DEFAULT_LIMITS, ...input };
  for (const key of Object.keys(output) as (keyof WheelExecutionLimits)[]) {
    const value = output[key];
    if (!Number.isSafeInteger(value) || value < 1 || value > HARD_LIMITS[key]) {
      throw new Error(`${key} must be an integer in 1..${HARD_LIMITS[key]}`);
    }
  }
  if (output.max_trace_events < output.max_steps) {
    throw new Error('max_trace_events must cover every permitted evaluation step');
  }
  return output;
}

function normalizeInputs(
  program: CodingWheelProgram,
  input: Readonly<Record<string, WheelValue>>
): Map<string, WheelValue> {
  if (!isRecord(input)) throw new Error('wheel inputs must be an object');
  const actual = Object.keys(input).sort();
  const expected = [...program.parameters].sort();
  if (actual.length !== expected.length || actual.some((name, index) => name !== expected[index])) {
    throw new Error('wheel inputs must exactly match the declared parameters');
  }
  const environment = new Map<string, WheelValue>();
  for (const name of program.parameters) {
    const value = input[name];
    if (typeof value === 'number') requireSafeInteger(value, `input ${name}`);
    else if (typeof value !== 'boolean')
      throw new Error(`input ${name} must be a safe integer or boolean`);
    environment.set(name, value);
  }
  return environment;
}

class WheelRuntimeError extends Error {
  constructor(
    readonly code: WheelExecutionErrorCode,
    readonly path: string,
    message: string
  ) {
    super(message);
  }
}

function numeric(value: WheelValue, path: string): number {
  if (typeof value !== 'number')
    throw new WheelRuntimeError('TYPE_ERROR', path, 'operation requires an integer');
  return value;
}

function checkedInteger(value: number, path: string): number {
  if (!Number.isSafeInteger(value)) {
    throw new WheelRuntimeError(
      'INTEGER_OVERFLOW',
      path,
      'DATA result exceeded safe integer bounds'
    );
  }
  return value;
}

/** Execute a finite program and return a complete, hash-bound public trace. */
export function executeCodingWheelProgram(
  program: CodingWheelProgram,
  input: Readonly<Record<string, WheelValue>>,
  requestedLimits: Partial<WheelExecutionLimits> = {}
): WheelExecutionReceipt {
  const tokens = serializeCodingWheelProgram(program);
  const limits = normalizeLimits(requestedLimits);
  const initial = normalizeInputs(program, input);
  if (initial.size > limits.max_bindings) throw new Error('declared inputs exceed max_bindings');
  const stats: WheelExecutionStats = {
    node_evaluations: 0,
    data_evaluations: 0,
    bindings_created: 0,
    branches_true: 0,
    branches_false: 0,
    loop_iterations: 0,
    sequences_evaluated: 0,
    maximum_depth: 0,
    peak_bindings: initial.size,
  };
  const trace: WheelTraceEvent[] = [];

  const consume = (expression: WheelExpression, depth: number, path: string): void => {
    if (depth > limits.max_depth)
      throw new WheelRuntimeError('DEPTH_LIMIT', path, 'maximum evaluation depth exceeded');
    if (stats.node_evaluations >= limits.max_steps) {
      throw new WheelRuntimeError('STEP_LIMIT', path, 'evaluation fuel exhausted');
    }
    if (trace.length >= limits.max_trace_events) {
      throw new WheelRuntimeError('TRACE_LIMIT', path, 'trace capacity exhausted');
    }
    stats.node_evaluations += 1;
    stats.maximum_depth = Math.max(stats.maximum_depth, depth);
    if (primitiveOf(expression) === 'DATA') stats.data_evaluations += 1;
  };

  const record = (
    expression: WheelExpression,
    path: string,
    result: WheelValue,
    detail: string | null
  ): WheelValue => {
    trace.push({
      sequence: trace.length,
      path,
      node_kind: expression.kind,
      primitive: primitiveOf(expression),
      result,
      detail,
    });
    return result;
  };

  const evaluate = (
    expression: WheelExpression,
    environment: ReadonlyMap<string, WheelValue>,
    depth: number,
    path: string
  ): WheelValue => {
    consume(expression, depth, path);
    switch (expression.kind) {
      case 'literal':
        return record(expression, path, expression.value, null);
      case 'read': {
        const value = environment.get(expression.name);
        if (value === undefined && !environment.has(expression.name)) {
          throw new WheelRuntimeError('UNKNOWN_NAME', path, `unknown binding: ${expression.name}`);
        }
        return record(expression, path, value!, expression.name);
      }
      case 'data': {
        const left = evaluate(expression.left, environment, depth + 1, `${path}.left`);
        const right = evaluate(expression.right, environment, depth + 1, `${path}.right`);
        let result: WheelValue;
        switch (expression.operator) {
          case 'add':
            result = checkedInteger(numeric(left, path) + numeric(right, path), path);
            break;
          case 'subtract':
            result = checkedInteger(numeric(left, path) - numeric(right, path), path);
            break;
          case 'multiply':
            result = checkedInteger(numeric(left, path) * numeric(right, path), path);
            break;
          case 'modulo': {
            const divisor = numeric(right, path);
            if (divisor === 0)
              throw new WheelRuntimeError('INVALID_MODULUS', path, 'modulo by zero');
            result = checkedInteger(numeric(left, path) % divisor, path);
            break;
          }
          case 'greater_than':
            result = numeric(left, path) > numeric(right, path);
            break;
          case 'equal':
            if (typeof left !== typeof right) {
              throw new WheelRuntimeError(
                'TYPE_ERROR',
                path,
                'equal requires operands of the same type'
              );
            }
            result = left === right;
            break;
        }
        return record(expression, path, result, expression.operator);
      }
      case 'bind': {
        const value = evaluate(expression.value, environment, depth + 1, `${path}.value`);
        const child = new Map(environment);
        child.set(expression.name, value);
        if (child.size > limits.max_bindings) {
          throw new WheelRuntimeError('BINDING_LIMIT', path, 'lexical binding capacity exceeded');
        }
        stats.bindings_created += 1;
        stats.peak_bindings = Math.max(stats.peak_bindings, child.size);
        const result = evaluate(expression.body, child, depth + 1, `${path}.body`);
        return record(expression, path, result, expression.name);
      }
      case 'branch': {
        const condition = evaluate(
          expression.condition,
          environment,
          depth + 1,
          `${path}.condition`
        );
        if (typeof condition !== 'boolean') {
          throw new WheelRuntimeError('TYPE_ERROR', path, 'BRANCH condition must be boolean');
        }
        const selected = condition ? 'when_true' : 'when_false';
        if (condition) stats.branches_true += 1;
        else stats.branches_false += 1;
        const result = evaluate(
          expression[selected],
          environment,
          depth + 1,
          `${path}.${selected}`
        );
        return record(expression, path, result, selected);
      }
      case 'loop': {
        const count = evaluate(expression.count, environment, depth + 1, `${path}.count`);
        if (typeof count !== 'number' || !Number.isSafeInteger(count) || count < 0) {
          throw new WheelRuntimeError(
            'INVALID_LOOP_COUNT',
            path,
            'LOOP count must be a non-negative integer'
          );
        }
        let accumulator = evaluate(expression.initial, environment, depth + 1, `${path}.initial`);
        for (let index = 0; index < count; index += 1) {
          if (stats.loop_iterations >= limits.max_loop_iterations) {
            throw new WheelRuntimeError('LOOP_LIMIT', path, 'LOOP iteration budget exhausted');
          }
          stats.loop_iterations += 1;
          const child = new Map(environment);
          child.set(expression.accumulator, accumulator);
          child.set(expression.index, index);
          if (child.size > limits.max_bindings) {
            throw new WheelRuntimeError('BINDING_LIMIT', path, 'LOOP bindings exceed capacity');
          }
          stats.peak_bindings = Math.max(stats.peak_bindings, child.size);
          accumulator = evaluate(expression.body, child, depth + 1, `${path}.body[${index}]`);
        }
        return record(expression, path, accumulator, `iterations:${count}`);
      }
      case 'sequence': {
        stats.sequences_evaluated += 1;
        let result: WheelValue = false;
        for (let index = 0; index < expression.expressions.length; index += 1) {
          result = evaluate(
            expression.expressions[index]!,
            environment,
            depth + 1,
            `${path}.expressions[${index}]`
          );
        }
        return record(expression, path, result, `expressions:${expression.expressions.length}`);
      }
    }
  };

  let status: WheelExecutionReceipt['status'] = 'PASS';
  let result: WheelValue | null = null;
  let error: WheelExecutionFailure | null = null;
  try {
    result = evaluate(program.body, initial, 0, '$');
  } catch (caught) {
    if (!(caught instanceof WheelRuntimeError)) throw caught;
    status = 'REJECTED';
    error = { code: caught.code, path: caught.path, message: caught.message };
  }
  const body = {
    schema_version: 'scbe.coding_primitives_execution.v1' as const,
    status,
    semantics: 'finite-bounded-interpreter' as const,
    universality_scope: 'abstract-unbounded-machine-only' as const,
    program_sha256: hashReasoningValue(program),
    token_stream_sha256: hashReasoningValue(tokens),
    input_sha256: hashReasoningValue(program.parameters.map((name) => [name, initial.get(name)])),
    limits,
    result,
    error,
    stats,
    trace,
    trace_sha256: hashReasoningValue(trace),
  };
  return { ...body, receipt_sha256: hashReasoningValue(body) };
}

/**
 * Verify receipt structure and public checksums without re-executing.
 *
 * This detects accidental changes. It is not execution authority: a caller can
 * recompute every public checksum after fabricating a different result.
 */
export function verifyCodingWheelReceipt(
  program: CodingWheelProgram,
  receipt: WheelExecutionReceipt
): WheelReceiptVerification {
  const errors: string[] = [];
  const add = (message: string): void => {
    if (!errors.includes(message)) errors.push(message);
  };
  try {
    const tokens = serializeCodingWheelProgram(program);
    if (receipt.schema_version !== 'scbe.coding_primitives_execution.v1')
      add('invalid receipt schema');
    if (receipt.semantics !== 'finite-bounded-interpreter') add('invalid execution semantics');
    if (receipt.universality_scope !== 'abstract-unbounded-machine-only') {
      add('invalid universality boundary');
    }
    if (hashReasoningValue(program) !== receipt.program_sha256) add('program hash mismatch');
    if (hashReasoningValue(tokens) !== receipt.token_stream_sha256)
      add('token stream hash mismatch');
    if (hashReasoningValue(receipt.trace) !== receipt.trace_sha256) add('trace hash mismatch');
    const { receipt_sha256: claimed, ...body } = receipt;
    if (hashReasoningValue(body) !== claimed) add('receipt hash mismatch');

    try {
      const normalized = normalizeLimits(receipt.limits);
      if (hashReasoningValue(normalized) !== hashReasoningValue(receipt.limits)) {
        add('receipt limits are not canonical');
      }
    } catch {
      add('invalid receipt limits');
    }
    const statisticValues = Object.values(receipt.stats);
    if (
      statisticValues.length !== 9 ||
      statisticValues.some((value) => !Number.isSafeInteger(value) || value < 0)
    ) {
      add('invalid execution statistics');
    }
    if (
      receipt.trace.some(
        (event, index) =>
          event.sequence !== index ||
          typeof event.path !== 'string' ||
          event.path.length === 0 ||
          !Number.isSafeInteger(event.sequence)
      )
    ) {
      add('invalid trace sequence');
    }
    if (receipt.status === 'PASS') {
      if (receipt.error !== null || receipt.result === null)
        add('PASS receipt has inconsistent result fields');
      if (receipt.trace.length !== receipt.stats.node_evaluations) {
        add('PASS receipt does not trace every evaluation');
      }
      if (receipt.trace.at(-1)?.path !== '$') add('PASS receipt lacks a completed root event');
    } else if (receipt.status === 'REJECTED') {
      if (receipt.error === null || receipt.result !== null) {
        add('REJECTED receipt has inconsistent result fields');
      }
      if (receipt.trace.length > receipt.stats.node_evaluations) {
        add('rejection trace exceeds evaluated nodes');
      }
    } else {
      add('invalid receipt status');
    }
  } catch (caught) {
    add(`receipt verification failed: ${(caught as Error).message}`);
  }
  return { ok: errors.length === 0, errors };
}

/**
 * Re-run a receipt from its declared inputs and limits.
 *
 * A successful result proves reproducibility in this interpreter invocation;
 * cross-host identity still requires a trusted ledger or digital signature.
 */
export function reexecuteCodingWheelReceipt(
  program: CodingWheelProgram,
  receipt: WheelExecutionReceipt,
  input: Readonly<Record<string, WheelValue>>
): WheelReceiptReexecution {
  const structural = verifyCodingWheelReceipt(program, receipt);
  if (!structural.ok) {
    return {
      ...structural,
      execution_reproduced: false,
      reproduced_receipt_sha256: null,
    };
  }
  try {
    const reproduced = executeCodingWheelProgram(program, input, receipt.limits);
    if (reproduced.receipt_sha256 !== receipt.receipt_sha256) {
      return {
        ok: false,
        errors: ['receipt execution could not be reproduced from the supplied inputs'],
        execution_reproduced: false,
        reproduced_receipt_sha256: reproduced.receipt_sha256,
      };
    }
    return {
      ok: true,
      errors: [],
      execution_reproduced: true,
      reproduced_receipt_sha256: reproduced.receipt_sha256,
    };
  } catch (caught) {
    return {
      ok: false,
      errors: [`receipt re-execution failed: ${(caught as Error).message}`],
      execution_reproduced: false,
      reproduced_receipt_sha256: null,
    };
  }
}

/** Convert a run receipt into a compact artifact suitable for the reasoning DAG. */
export function wheelReceiptToReasoningArtifact(
  program: CodingWheelProgram,
  receipt: WheelExecutionReceipt,
  options: WheelReasoningArtifactOptions
): ReasoningArtifactInput {
  const tokens = serializeCodingWheelProgram(program);
  const verified = verifyCodingWheelReceipt(program, receipt);
  if (!verified.ok) throw new Error(`invalid wheel receipt: ${verified.errors[0]}`);
  if (tokens.length > 4096)
    throw new Error('wheel program exceeds reasoning-graph syntax capacity');
  const policy =
    options.policy ??
    (receipt.status === 'PASS' && options.verification_inputs !== undefined
      ? 'allow'
      : 'quarantine');
  if (receipt.status !== 'PASS' && policy === 'allow') {
    throw new Error('a rejected wheel execution cannot create an allow artifact');
  }
  let executionAuthority: 'structural-checksum-only' | 'deterministic-reexecution' =
    'structural-checksum-only';
  if (policy === 'allow') {
    if (options.verification_inputs === undefined) {
      throw new Error(
        'an allow artifact requires verification_inputs for deterministic re-execution'
      );
    }
    const reproduced = reexecuteCodingWheelReceipt(program, receipt, options.verification_inputs);
    if (!reproduced.ok) {
      throw new Error(`wheel receipt lacks execution authority: ${reproduced.errors[0]}`);
    }
    executionAuthority = 'deterministic-reexecution';
  }
  const compact = {
    schema_version: 'scbe.coding_primitives_artifact.v1',
    receipt_sha256: receipt.receipt_sha256,
    program_sha256: receipt.program_sha256,
    token_stream_sha256: receipt.token_stream_sha256,
    input_sha256: receipt.input_sha256,
    status: receipt.status,
    result: receipt.result,
    error: receipt.error,
    stats: receipt.stats,
    trace_sha256: receipt.trace_sha256,
    execution_authority: executionAuthority,
  };
  return {
    id: options.id,
    parent_ids: [...(options.parent_ids ?? [])],
    tongue: options.tongue,
    canonical_bytes: new TextEncoder().encode(JSON.stringify(compact)),
    public_summary:
      options.public_summary ??
      `Coding wheel execution ${receipt.status.toLowerCase()} after ${receipt.stats.node_evaluations} node evaluations`,
    state_transition:
      options.state_transition ??
      (receipt.status === 'PASS'
        ? `bounded program produced ${String(receipt.result)}`
        : `bounded program rejected at ${receipt.error?.path ?? '$'}`),
    syntax_tokens: tokens,
    feature_values: [...options.feature_values],
    policy,
    evidence_hashes: [
      ...new Set([
        ...(executionAuthority === 'deterministic-reexecution' ? [receipt.receipt_sha256] : []),
        ...(options.evidence_hashes ?? []),
      ]),
    ],
    provenance_hashes: [
      ...new Set([
        ...(executionAuthority === 'structural-checksum-only' ? [receipt.receipt_sha256] : []),
        receipt.program_sha256,
        receipt.token_stream_sha256,
        ...(options.provenance_hashes ?? []),
      ]),
    ],
  };
}

/** Count the exact sum bands for width balanced-trit channels. */
export function measureTritBands(width: number): TritBandMeasurement {
  if (!Number.isSafeInteger(width) || width < 1 || width > 20) {
    throw new Error('trit width must be an integer in 1..20');
  }
  let counts = new Map<number, number>([[0, 1]]);
  for (let position = 0; position < width; position += 1) {
    const next = new Map<number, number>();
    for (const [sum, count] of counts) {
      for (const trit of [-1, 0, 1]) next.set(sum + trit, (next.get(sum + trit) ?? 0) + count);
    }
    counts = next;
  }
  const states = 3 ** width;
  const balancedStates = counts.get(0) ?? 0;
  return {
    schema_version: 'scbe.trit_band_measurement.v1',
    width,
    states,
    bands: counts.size,
    minimum_sum: Math.min(...counts.keys()),
    maximum_sum: Math.max(...counts.keys()),
    balanced_states: balancedStates,
    balanced_fraction: balancedStates / states,
    binary_balanced_at_this_width: width % 2 === 0,
    neutral_enables_balance_at_odd_width: width % 2 === 1,
    authority: 'combinatorial-count-only-not-capability-evidence',
  };
}

function poincareDistance(
  left: readonly [number, number],
  right: readonly [number, number]
): number {
  const leftNorm = left[0] ** 2 + left[1] ** 2;
  const rightNorm = right[0] ** 2 + right[1] ** 2;
  const difference = (left[0] - right[0]) ** 2 + (left[1] - right[1]) ** 2;
  return Math.acosh(Math.max(1, 1 + (2 * difference) / ((1 - leftNorm) * (1 - rightNorm))));
}

function diskToHyperboloid(point: readonly [number, number]): readonly [number, number, number] {
  const norm = point[0] ** 2 + point[1] ** 2;
  const denominator = 1 - norm;
  return [(1 + norm) / denominator, (2 * point[0]) / denominator, (2 * point[1]) / denominator];
}

function hyperboloidDistance(
  left: readonly [number, number, number],
  right: readonly [number, number, number]
): number {
  const lorentz = left[0] * right[0] - left[1] * right[1] - left[2] * right[2];
  return Math.acosh(Math.max(1, lorentz));
}

/** Recompute the fixed 64-cell coordinate-model checks used by the wafer view. */
export function measureWaferGeometry(): WaferGeometryMeasurement {
  const bevel = 0.02 as const;
  const maximumRadius = 1 - bevel;
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));
  const disk: [number, number][] = [];
  for (let opcode = 0; opcode < 64; opcode += 1) {
    const realm = opcode >> 4;
    const index = opcode & 15;
    const radius = maximumRadius * Math.sqrt((realm + (index + 0.5) / 16) / 4);
    const angle = goldenAngle * opcode;
    disk.push([radius * Math.cos(angle), radius * Math.sin(angle)]);
  }
  const sheet = disk.map(diskToHyperboloid);
  let distanceError = 0;
  let constraintError = 0;
  let rotationError = 0;
  const rotation = Math.PI / 7;
  for (let index = 0; index < disk.length; index += 1) {
    const [x, y] = disk[index]!;
    const [x0, x1, x2] = sheet[index]!;
    constraintError = Math.max(constraintError, Math.abs(-x0 * x0 + x1 * x1 + x2 * x2 + 1));
    const radius = Math.hypot(x, y);
    const rotated = [
      x * Math.cos(rotation) - y * Math.sin(rotation),
      x * Math.sin(rotation) + y * Math.cos(rotation),
    ];
    rotationError = Math.max(rotationError, Math.abs(Math.hypot(...rotated) - radius));
    for (let other = index + 1; other < disk.length; other += 1) {
      distanceError = Math.max(
        distanceError,
        Math.abs(
          poincareDistance(disk[index]!, disk[other]!) -
            hyperboloidDistance(sheet[index]!, sheet[other]!)
        )
      );
    }
  }
  return {
    schema_version: 'scbe.wafer_coordinate_measurement.v1',
    cells: 64,
    realms: [16, 16, 16, 16],
    bevel,
    distance_pairs: (64 * 63) / 2,
    poincare_hyperboloid_max_abs_error: distanceError,
    hyperboloid_constraint_max_abs_error: constraintError,
    rotation_max_delta_radius: rotationError,
    authority: 'coordinate-consistency-only-not-reasoning-evidence',
  };
}
