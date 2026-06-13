'use strict';

/**
 * End-to-end test for the scbe MCP bridge.
 *
 * Spawns mcp/scbe-mcp-server.cjs over real stdio via the MCP client SDK, then:
 *   - lists tools (asserting the list is generated from the manifest, incl. the
 *     new `scbe_rns`), and
 *   - actually CALLS two tools through the protocol (scbe_version, scbe_rns) and
 *     checks the real output — proving the bridge runs commands, not just boots.
 *
 * Run: node --test packages/cli/tests/mcp-server.test.cjs
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');

const { buildToolDefinitions, toolName, resolveArgs } = require('../mcp/scbe-mcp-server.cjs');
const { buildToolsManifest } = require('../lib/tools-manifest');

const SERVER = path.join(__dirname, '..', 'mcp', 'scbe-mcp-server.cjs');

test('tool definitions are generated 1:1 from the manifest', () => {
  const { tools, commandFor } = buildToolDefinitions();
  const manifest = buildToolsManifest();
  assert.equal(tools.length, manifest.command_count);
  // dash -> underscore mapping round-trips
  assert.equal(toolName('agent-bus'), 'scbe_agent_bus');
  assert.equal(commandFor.get('scbe_agent_bus'), 'agent-bus');
  assert.equal(commandFor.get('scbe_rns'), 'rns');
  assert.equal(commandFor.get('scbe_version'), 'version');
  // every tool has a schema with args + json
  for (const t of tools) {
    assert.ok(t.name.startsWith('scbe_'));
    assert.ok(t.description.length > 0);
    assert.ok(t.inputSchema.properties.args);
    assert.ok(t.inputSchema.properties.json);
  }
});

test('commands with params expose a TYPED input schema (alongside args/json)', () => {
  const { tools } = buildToolDefinitions();
  const abacus = tools.find((t) => t.name === 'scbe_abacus');
  const props = abacus.inputSchema.properties;
  // typed params present with correct JSON types + enum
  assert.equal(props.subcommand.type, 'string');
  assert.deepEqual(props.subcommand.enum, ['run']);
  assert.equal(props.d_h.type, 'number');
  assert.equal(props.pd.type, 'number');
  // escape hatch + json still present (back-compat the bridge relies on)
  assert.ok(props.args);
  assert.ok(props.json);
  // repeated integer param renders as an array of integers
  const rns = tools.find((t) => t.name === 'scbe_rns');
  assert.equal(rns.inputSchema.properties.operands.type, 'array');
  assert.equal(rns.inputSchema.properties.operands.items.type, 'integer');
});

test('resolveArgs serializes typed params and honors the raw-args escape hatch', () => {
  const { specByTool } = buildToolDefinitions();
  const abacusSpec = specByTool.get('scbe_abacus');
  // structured params -> argv
  assert.deepEqual(resolveArgs(abacusSpec, { subcommand: 'run', d_h: 0.4, pd: 0.1 }), [
    'run',
    '--d-h',
    '0.4',
    '--pd',
    '0.1',
  ]);
  // raw args win when provided (explicit escape hatch)
  assert.deepEqual(resolveArgs(abacusSpec, { args: ['run', '--d-h', '0.9', '--pd', '0.0'] }), [
    'run',
    '--d-h',
    '0.9',
    '--pd',
    '0.0',
  ]);
  // bad structured call surfaces a clear error (not a malformed command)
  assert.throws(() => resolveArgs(abacusSpec, { subcommand: 'run', d_h: 0.4 }), /missing required param "pd"/);
});

test('server lists and runs tools over real MCP stdio', { timeout: 60000 }, async () => {
  const transport = new StdioClientTransport({ command: process.execPath, args: [SERVER] });
  const client = new Client({ name: 'scbe-mcp-test', version: '1.0.0' }, { capabilities: {} });
  await client.connect(transport);
  try {
    const listed = await client.listTools();
    const names = new Set(listed.tools.map((t) => t.name));
    assert.ok(names.has('scbe_version'), 'scbe_version tool should be listed');
    assert.ok(names.has('scbe_rns'), 'scbe_rns tool should be listed');
    assert.ok(names.has('scbe_flow'), 'scbe_flow tool should be listed');

    // Call scbe_version --json and confirm real JSON came back through the protocol.
    const ver = await client.callTool({ name: 'scbe_version', arguments: { json: true } });
    assert.equal(ver.isError || false, false);
    const verText = ver.content.map((c) => c.text).join('');
    const verObj = JSON.parse(verText);
    assert.ok(verObj && typeof verObj === 'object');

    // Call scbe_rns add 30000 30000 --json — exercises arg passing + the new command.
    const rns = await client.callTool({
      name: 'scbe_rns',
      arguments: { args: ['add', '30000', '30000'], json: true },
    });
    assert.equal(rns.isError || false, false);
    const rnsObj = JSON.parse(rns.content.map((c) => c.text).join(''));
    assert.equal(rnsObj.decoded, 60000);
    assert.equal(rnsObj.overflow, true);
    assert.equal(rnsObj.exact, true);

    // Call scbe_rns with STRUCTURED params (no raw args) — proves the bridge
    // serializes the typed param contract into a real, runnable invocation.
    const rnsTyped = await client.callTool({
      name: 'scbe_rns',
      arguments: { subcommand: 'add', operands: [30000, 30000], json: true },
    });
    assert.equal(rnsTyped.isError || false, false);
    const rnsTypedObj = JSON.parse(rnsTyped.content.map((c) => c.text).join(''));
    assert.equal(rnsTypedObj.decoded, 60000);
    assert.equal(rnsTypedObj.exact, true);

    // A bad structured call is rejected cleanly (clear error, no malformed run).
    const bad = await client.callTool({
      name: 'scbe_rns',
      arguments: { subcommand: 'divide', operands: [1, 2] },
    });
    assert.equal(bad.isError, true);
    assert.match(bad.content.map((c) => c.text).join(''), /must be one of/);
  } finally {
    await client.close();
  }
});
