/**
 * @file typescriptDebugHarness.ts
 * @module game/typescriptDebugHarness
 *
 * Deterministic TypeScript snippet runner for game-debugger style training receipts.
 */

import vm from 'node:vm';
import ts from 'typescript';

export type DebugReceiptStatus = 'passed' | 'compile_error' | 'runtime_error' | 'timeout';

export interface DebugScenario<TInput = unknown, TState = Record<string, unknown>> {
  readonly id: string;
  readonly source: string;
  readonly input: TInput;
  readonly initialState: TState;
  readonly timeoutMs?: number;
}

export interface StateChange {
  readonly path: string;
  readonly before: unknown;
  readonly after: unknown;
}

export interface DebugReceipt {
  readonly scenarioId: string;
  readonly status: DebugReceiptStatus;
  readonly result: unknown;
  readonly finalState: unknown;
  readonly logs: readonly string[];
  readonly stateChanges: readonly StateChange[];
  readonly diagnostics: readonly string[];
  readonly error: string | null;
  readonly durationMs: number;
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') {
    return JSON.stringify(value);
  }
  return JSON.stringify(value, Object.keys(value as object).sort());
}

function collectStateChanges(before: unknown, after: unknown, prefix = 'state'): StateChange[] {
  if (Object.is(before, after)) {
    return [];
  }

  const beforeIsArray = Array.isArray(before);
  const afterIsArray = Array.isArray(after);
  const beforeIsObject = before !== null && typeof before === 'object' && !beforeIsArray;
  const afterIsObject = after !== null && typeof after === 'object' && !afterIsArray;

  if (beforeIsArray || afterIsArray) {
    if (!beforeIsArray || !afterIsArray) {
      return [{ path: prefix, before, after }];
    }
    const beforeArray = before as unknown[];
    const afterArray = after as unknown[];
    const length = Math.max(beforeArray.length, afterArray.length);
    return Array.from({ length }, (_, index) =>
      collectStateChanges(beforeArray[index], afterArray[index], `${prefix}.${index}`)
    ).flat();
  }

  if (!beforeIsObject || !afterIsObject) {
    return stableStringify(before) === stableStringify(after)
      ? []
      : [{ path: prefix, before, after }];
  }

  const beforeRecord = before as Record<string, unknown>;
  const afterRecord = after as Record<string, unknown>;
  const keys = Array.from(new Set([...Object.keys(beforeRecord), ...Object.keys(afterRecord)])).sort();

  return keys.flatMap((key) =>
    collectStateChanges(beforeRecord[key], afterRecord[key], `${prefix}.${key}`)
  );
}

function compileTypeScript(source: string): { code: string; diagnostics: string[]; hasError: boolean } {
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      strict: true,
      esModuleInterop: true,
    },
    reportDiagnostics: true,
  });

  const diagnostics = (output.diagnostics ?? []).map((diagnostic) =>
    ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n')
  );
  const hasError = (output.diagnostics ?? []).some(
    (diagnostic) => diagnostic.category === ts.DiagnosticCategory.Error
  );

  return { code: output.outputText, diagnostics, hasError };
}

function normalizeError(error: unknown): string {
  if (error instanceof Error) {
    return `${error.name}: ${error.message}`;
  }
  return String(error);
}

/**
 * Run one TypeScript "game turn" and return a receipt suitable for eval/training.
 *
 * The snippet must define either `function evaluate(input, state)` or
 * `export function evaluate(input, state)`. The state is JSON-cloned before
 * execution so state diffs are deterministic and serializable.
 */
export function runTypeScriptDebugScenario(scenario: DebugScenario): DebugReceipt {
  const started = Date.now();
  const diagnostics: string[] = [];
  const logs: string[] = [];
  const beforeState = cloneJson(scenario.initialState);
  const state = cloneJson(scenario.initialState);
  const input = cloneJson(scenario.input);
  const timeoutMs = scenario.timeoutMs ?? 250;

  const compiled = compileTypeScript(scenario.source);
  diagnostics.push(...compiled.diagnostics);

  if (compiled.hasError) {
    return {
      scenarioId: scenario.id,
      status: 'compile_error',
      result: null,
      finalState: state,
      logs,
      stateChanges: [],
      diagnostics,
      error: diagnostics.join('; ') || 'TypeScript compile error',
      durationMs: Date.now() - started,
    };
  }

  const sandbox: Record<string, unknown> = {
    console: {
      log: (...parts: unknown[]) => logs.push(parts.map(String).join(' ')),
      warn: (...parts: unknown[]) => logs.push(`WARN ${parts.map(String).join(' ')}`),
      error: (...parts: unknown[]) => logs.push(`ERROR ${parts.map(String).join(' ')}`),
    },
    module: { exports: {} },
    exports: {},
    __input: input,
    __state: state,
    __result: undefined,
  };
  sandbox.exports = (sandbox.module as { exports: Record<string, unknown> }).exports;

  const script = new vm.Script(
    `${compiled.code}
const __candidate = typeof evaluate === "function" ? evaluate : module.exports.evaluate;
if (typeof __candidate !== "function") {
  throw new Error("Snippet must define evaluate(input, state).");
}
__result = __candidate(__input, __state);`
  );

  try {
    script.runInNewContext(sandbox, {
      timeout: timeoutMs,
      contextName: `scbe-debug-${scenario.id}`,
    });
  } catch (error) {
    const message = normalizeError(error);
    const status: DebugReceiptStatus = message.includes('Script execution timed out')
      ? 'timeout'
      : 'runtime_error';
    return {
      scenarioId: scenario.id,
      status,
      result: null,
      finalState: state,
      logs,
      stateChanges: collectStateChanges(beforeState, state),
      diagnostics,
      error: message,
      durationMs: Date.now() - started,
    };
  }

  return {
    scenarioId: scenario.id,
    status: 'passed',
    result: sandbox.__result,
    finalState: state,
    logs,
    stateChanges: collectStateChanges(beforeState, state),
    diagnostics,
    error: null,
    durationMs: Date.now() - started,
  };
}

export function receiptToSftPair(receipt: DebugReceipt): { instruction: string; response: string } {
  return {
    instruction:
      `Review TypeScript game-debug receipt ${receipt.scenarioId}. ` +
      'Explain whether the candidate code should be approved, retried, or rejected.',
    response: JSON.stringify(
      {
        scenario_id: receipt.scenarioId,
        decision: receipt.status === 'passed' ? 'approve' : 'retry',
        status: receipt.status,
        error: receipt.error,
        state_changes: receipt.stateChanges,
        logs: receipt.logs,
      },
      null,
      2
    ),
  };
}
