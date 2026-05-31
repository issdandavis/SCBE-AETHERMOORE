#!/usr/bin/env node
'use strict';
/**
 * Tool Factory CLI — register, validate, and list bus tools.
 *
 * Usage:
 *   node tool_factory.cjs register '<json_spec>'
 *   node tool_factory.cjs validate '<json_spec>'
 *   node tool_factory.cjs list [--filter <substring>]
 *   node tool_factory.cjs unregister <tool-name>
 *
 * All writes go through an atomic temp-file→rename and pre-registration
 * file/module verification. No writes happen for validate-only calls.
 *
 * Exit codes: 0 = ok, 1 = error, 2 = bad input
 */

const path = require('node:path');
const fs = require('node:fs');

const pkgRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(pkgRoot, '..', '..');
const toolsJsonPath = path.join(pkgRoot, 'tools.json');

let factory;
try {
  factory = require(path.join(pkgRoot, 'dist', 'index.js'));
} catch (err) {
  process.stderr.write(
    JSON.stringify(
      {
        schema_version: 'scbe.agent_bus.tool_factory_error.v1',
        error: `Failed to load dist/index.js: ${err instanceof Error ? err.message : String(err)}`,
        hint: 'Run: npm run build inside packages/agent-bus',
      },
      null,
      2
    ) + '\n'
  );
  process.exit(1);
}

const { validateToolSpec, registerToolSpecInFile, unregisterToolSpecInFile, listToolSpecsFromFile } =
  factory;

const argv = process.argv.slice(2);

if (argv.length === 0) {
  process.stderr.write(
    [
      'Usage:',
      '  node tool_factory.cjs register \'<json_spec>\'',
      '  node tool_factory.cjs validate \'<json_spec>\'',
      '  node tool_factory.cjs list [--filter <substring>]',
      '  node tool_factory.cjs unregister <tool-name>',
      '',
    ].join('\n')
  );
  process.exit(2);
}

const command = argv[0];

// ─── register ────────────────────────────────────────────────────────────────
if (command === 'register') {
  const rawSpec = argv.slice(1).join(' ').trim();
  if (!rawSpec) {
    process.stderr.write('Error: register requires a JSON spec argument\n');
    process.exit(2);
  }

  let parsed;
  try {
    parsed = JSON.parse(rawSpec);
  } catch (e) {
    const out = {
      schema_version: 'scbe.agent_bus.tool_factory.v1',
      ok: false,
      action: 'rejected',
      errors: [`invalid JSON: ${e instanceof Error ? e.message : String(e)}`],
    };
    process.stdout.write(JSON.stringify(out, null, 2) + '\n');
    process.exit(1);
  }

  const validation = validateToolSpec(parsed);
  if (!validation.ok) {
    const out = {
      schema_version: 'scbe.agent_bus.tool_factory.v1',
      ok: false,
      action: 'rejected',
      errors: validation.errors,
    };
    process.stdout.write(JSON.stringify(out, null, 2) + '\n');
    process.exit(1);
  }

  const result = registerToolSpecInFile(validation.spec, toolsJsonPath, repoRoot);
  process.stdout.write(JSON.stringify(result, null, 2) + '\n');
  process.exit(result.ok ? 0 : 1);
}

// ─── validate ────────────────────────────────────────────────────────────────
if (command === 'validate') {
  const rawSpec = argv.slice(1).join(' ').trim();
  if (!rawSpec) {
    process.stderr.write('Error: validate requires a JSON spec argument\n');
    process.exit(2);
  }

  let parsed;
  try {
    parsed = JSON.parse(rawSpec);
  } catch (e) {
    const out = {
      schema_version: 'scbe.agent_bus.tool_factory.validate.v1',
      ok: false,
      errors: [`invalid JSON: ${e instanceof Error ? e.message : String(e)}`],
    };
    process.stdout.write(JSON.stringify(out, null, 2) + '\n');
    process.exit(1);
  }

  const result = validateToolSpec(parsed);
  const out = {
    schema_version: 'scbe.agent_bus.tool_factory.validate.v1',
    ok: result.ok,
    errors: result.errors,
    ...(result.spec && { spec: result.spec }),
  };
  process.stdout.write(JSON.stringify(out, null, 2) + '\n');
  process.exit(result.ok ? 0 : 1);
}

// ─── list ─────────────────────────────────────────────────────────────────────
if (command === 'list') {
  const filterIdx = argv.indexOf('--filter');
  const filter = filterIdx !== -1 ? argv[filterIdx + 1] ?? '' : argv[1] ?? '';

  const result = listToolSpecsFromFile(toolsJsonPath);

  const filtered =
    filter
      ? { ...result, tools: result.tools.filter((t) => t.name.includes(filter)) }
      : result;

  process.stdout.write(JSON.stringify(filtered, null, 2) + '\n');
  process.exit(0);
}

// ─── unregister ───────────────────────────────────────────────────────────────
if (command === 'unregister') {
  const name = argv[1];
  if (!name) {
    process.stderr.write('Error: unregister requires a tool name argument\n');
    process.exit(2);
  }

  const result = unregisterToolSpecInFile(name, toolsJsonPath);
  process.stdout.write(JSON.stringify({
    schema_version: 'scbe.agent_bus.tool_factory.unregister.v1',
    ...result,
    name,
  }, null, 2) + '\n');
  process.exit(result.ok ? 0 : 1);
}

// ─── unknown command ──────────────────────────────────────────────────────────
process.stderr.write(
  JSON.stringify(
    {
      schema_version: 'scbe.agent_bus.tool_factory_error.v1',
      error: `unknown command: ${JSON.stringify(command)}`,
      valid_commands: ['register', 'validate', 'list', 'unregister'],
    },
    null,
    2
  ) + '\n'
);
process.exit(2);
