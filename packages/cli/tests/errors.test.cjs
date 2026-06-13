'use strict';

/**
 * Tests for the structured error contract (lib/errors.js) and its wiring into
 * the CLI: unknown-command path, the global uncaught-exception backstop, and the
 * manifest advertising the contract.
 *
 * Run: node --test packages/cli/tests/errors.test.cjs
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const {
  ERROR_SCHEMA,
  ErrorCodes,
  EXIT_FOR_CODE,
  buildError,
  wantsJson,
  errorContract,
} = require('../lib/errors');
const { buildToolsManifest } = require('../lib/tools-manifest');

const SCBE_BIN = path.join(__dirname, '..', 'bin', 'scbe.js');
const ERR_MOD = path.join(__dirname, '..', 'lib', 'errors.js');

test('buildError produces the canonical shape with optional fields', () => {
  const e = buildError({
    code: ErrorCodes.INVALID_ARGUMENT,
    message: 'bad arg',
    command: 'rns',
    suggestions: ['encode'],
    hint: 'try again',
    details: { got: 'x' },
  });
  assert.equal(e.schema_version, ERROR_SCHEMA);
  assert.equal(e.ok, false);
  assert.equal(e.error.code, 'invalid_argument');
  assert.equal(e.error.message, 'bad arg');
  assert.equal(e.error.command, 'rns');
  assert.deepEqual(e.error.suggestions, ['encode']);
  assert.equal(e.error.hint, 'try again');
  assert.deepEqual(e.error.details, { got: 'x' });
});

test('buildError omits empty optionals and defaults the code', () => {
  const e = buildError({ message: 'boom' });
  assert.equal(e.error.code, 'internal_error');
  assert.equal('command' in e.error, false);
  assert.equal('suggestions' in e.error, false);
  assert.equal('details' in e.error, false);
});

test('every error code has an exit mapping', () => {
  for (const code of Object.values(ErrorCodes)) {
    assert.equal(typeof EXIT_FOR_CODE[code], 'number', `no exit code for ${code}`);
  }
});

test('wantsJson detects the --json convention', () => {
  assert.equal(wantsJson(['x', '--json']), true);
  assert.equal(wantsJson(['x']), false);
  assert.equal(wantsJson(null), false);
});

test('errorContract is embedded in the tools manifest', () => {
  const m = buildToolsManifest();
  assert.ok(m.error_schema, 'manifest must advertise error_schema');
  assert.equal(m.error_schema.schema_version, ERROR_SCHEMA);
  assert.ok(m.error_schema.codes.includes('unknown_command'));
  assert.deepEqual(m.error_schema.codes, errorContract().codes);
});

test('unknown command emits a structured error under --json', () => {
  // 'likoqs' is a near-miss of 'liboqs' -> hits the typo guard.
  const r = spawnSync(process.execPath, [SCBE_BIN, 'likoqs', '--json'], { encoding: 'utf8' });
  assert.notEqual(r.status, 0);
  const obj = JSON.parse(r.stdout);
  assert.equal(obj.ok, false);
  assert.equal(obj.error.code, 'unknown_command');
  assert.equal(obj.error.command, 'likoqs');
  assert.ok(obj.error.suggestions.includes('liboqs'));
});

test('global backstop turns an uncaught throw into a structured error', () => {
  const code = `const { installGlobalErrorHandlers } = require(${JSON.stringify(ERR_MOD)});
    installGlobalErrorHandlers(['boom', '--json']);
    setImmediate(() => { throw new Error('kaboom-test'); });`;
  const r = spawnSync(process.execPath, ['-e', code], { encoding: 'utf8' });
  assert.equal(r.status, 1);
  const obj = JSON.parse(r.stdout);
  assert.equal(obj.ok, false);
  assert.equal(obj.error.code, 'internal_error');
  assert.ok(obj.error.message.includes('kaboom-test'));
  assert.equal(obj.error.command, 'boom');
});
