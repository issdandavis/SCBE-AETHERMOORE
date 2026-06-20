/**
 * @file errors.js
 * @module cli/lib/errors
 *
 * Canonical, machine-readable error contract for the `scbe` CLI.
 *
 * WHY THIS EXISTS
 * ---------------
 * An AI calling `scbe` as a tool needs to know *why* a call failed, not just
 * that it did. Previously failures printed free-form text to stderr — unparseable.
 * This module defines ONE error shape and emit helper so every failure path that
 * opts in produces the same structured object under `--json`:
 *
 *   {
 *     "schema_version": "scbe_error_v1",
 *     "ok": false,
 *     "error": { "code": "<stable-id>", "message": "...",
 *                "command"?: "...", "hint"?: "...",
 *                "suggestions"?: [...], "details"?: {...} }
 *   }
 *
 * `code` is a stable identifier an AI can branch on; `message` is human text.
 * The exit code is derived from the error code so success/failure is also
 * distinguishable without parsing.
 */

'use strict';

const ERROR_SCHEMA = 'scbe_error_v1';

/** Stable error codes. Add here (and to EXIT_FOR_CODE) — never inline a string. */
const ErrorCodes = {
  UNKNOWN_COMMAND: 'unknown_command',
  USAGE: 'usage',
  INVALID_ARGUMENT: 'invalid_argument',
  SOURCE_CHECKOUT_REQUIRED: 'source_checkout_required',
  EXECUTION_FAILED: 'execution_failed',
  INTERNAL: 'internal_error',
};

const EXIT_FOR_CODE = {
  unknown_command: 2,
  usage: 2,
  invalid_argument: 2,
  source_checkout_required: 2,
  execution_failed: 1,
  internal_error: 1,
};

/** Build the canonical error object (pure; no I/O). */
function buildError(spec) {
  const s = spec || {};
  const code = s.code || ErrorCodes.INTERNAL;
  const error = {
    code,
    message: String(s.message == null ? 'unknown error' : s.message),
  };
  if (s.command) error.command = String(s.command);
  if (s.hint) error.hint = String(s.hint);
  if (Array.isArray(s.suggestions) && s.suggestions.length)
    error.suggestions = s.suggestions.map(String);
  if (s.details && typeof s.details === 'object' && Object.keys(s.details).length)
    error.details = s.details;
  return { schema_version: ERROR_SCHEMA, ok: false, error };
}

/**
 * Emit a structured error. json -> JSON object on stdout (uniform with success
 * payloads); human -> a clean one-liner on stderr. Exits unless exit:false.
 */
function emitError(spec, opts) {
  const o = opts || {};
  const json = Boolean(o.json);
  const obj = buildError(spec);
  const code = obj.error.code;
  const exitCode = (spec && spec.exitCode) || EXIT_FOR_CODE[code] || 1;
  if (json) {
    process.stdout.write(`${JSON.stringify(obj, null, 2)}\n`);
  } else {
    let line = `scbe error [${code}]: ${obj.error.message}`;
    if (obj.error.hint) line += `\n  hint: ${obj.error.hint}`;
    if (obj.error.suggestions)
      line += `\n  did you mean: ${obj.error.suggestions.map((s) => `scbe ${s}`).join(', ')}`;
    process.stderr.write(`${line}\n`);
  }
  if (o.exit !== false) process.exit(exitCode);
  return obj;
}

/** The CLI's global convention: `--json` anywhere in argv selects machine output. */
function wantsJson(argv) {
  return Array.isArray(argv) && argv.includes('--json');
}

/**
 * Install global backstops so ANY uncaught throw / rejection becomes a structured
 * error under --json instead of a raw Node stack trace. Call once at startup.
 * In human mode set SCBE_DEBUG=1 to still see the stack.
 */
function installGlobalErrorHandlers(argv) {
  const json = wantsJson(argv);
  const command = Array.isArray(argv) ? argv[0] : undefined;
  const handle = (err) => {
    emitError(
      { code: ErrorCodes.INTERNAL, message: (err && err.message) || String(err), command },
      { json, exit: false }
    );
    if (!json && process.env.SCBE_DEBUG && err && err.stack) {
      process.stderr.write(`${err.stack}\n`);
    }
    process.exit(EXIT_FOR_CODE.internal_error);
  };
  process.on('uncaughtException', handle);
  process.on('unhandledRejection', (reason) =>
    handle(reason instanceof Error ? reason : new Error(String(reason)))
  );
}

/** Summary of the contract, embedded in `scbe tools` so AI callers can discover it. */
function errorContract() {
  return {
    schema_version: ERROR_SCHEMA,
    shape: '{ ok:false, error:{ code, message, command?, hint?, suggestions?, details? } }',
    codes: Object.values(ErrorCodes),
    note: 'Present on stdout when a command is invoked with --json and fails; exit code is non-zero.',
  };
}

module.exports = {
  ERROR_SCHEMA,
  ErrorCodes,
  EXIT_FOR_CODE,
  buildError,
  emitError,
  wantsJson,
  installGlobalErrorHandlers,
  errorContract,
};
