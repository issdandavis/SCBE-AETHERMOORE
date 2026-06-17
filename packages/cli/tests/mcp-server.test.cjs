'use strict';

/**
 * End-to-end test for the scbe MCP bridge.
 *
 * Spawns mcp/scbe-mcp-server.cjs over real stdio via the MCP client SDK, then:
 *   - lists tools generated from the manifest,
 *   - proves high-risk shell/git tools are not exposed to AI clients, and
 *   - actually calls safe tools through the protocol.
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

test('tool definitions are generated from the manifest with high-risk tools withheld', () => {
  const { tools, commandFor } = buildToolDefinitions();
  const manifest = buildToolsManifest();
  assert.ok(tools.length < manifest.command_count);

  assert.equal(toolName('agent-bus'), 'scbe_agent_bus');
  assert.equal(commandFor.get('scbe_agent_bus'), 'agent-bus');
  assert.equal(commandFor.get('scbe_rns'), 'rns');
  assert.equal(commandFor.get('scbe_version'), 'version');
  assert.equal(commandFor.get('scbe_push'), undefined);
  assert.equal(commandFor.get('scbe_exec'), undefined);
  assert.equal(commandFor.get('scbe_run'), undefined);

  for (const t of tools) {
    assert.ok(t.name.startsWith('scbe_'));
    assert.ok(t.description.length > 0);
    assert.ok(t.inputSchema.properties.args);
    assert.ok(t.inputSchema.properties.json);
  }
});

test('commands with params expose a typed input schema alongside args/json', () => {
  const { tools } = buildToolDefinitions();
  const abacus = tools.find((t) => t.name === 'scbe_abacus');
  const props = abacus.inputSchema.properties;
  assert.equal(props.subcommand.type, 'string');
  assert.deepEqual(props.subcommand.enum, ['run']);
  assert.equal(props.d_h.type, 'number');
  assert.equal(props.pd.type, 'number');
  assert.ok(props.args);
  assert.ok(props.json);

  const rns = tools.find((t) => t.name === 'scbe_rns');
  assert.equal(rns.inputSchema.properties.operands.type, 'array');
  assert.equal(rns.inputSchema.properties.operands.items.type, 'integer');
});

test('resolveArgs serializes typed params and rejects malformed raw args', () => {
  const { specByTool } = buildToolDefinitions();
  const abacusSpec = specByTool.get('scbe_abacus');

  assert.deepEqual(resolveArgs(abacusSpec, { subcommand: 'run', d_h: 0.4, pd: 0.1 }), [
    'run',
    '--d-h',
    '0.4',
    '--pd',
    '0.1',
  ]);
  assert.deepEqual(resolveArgs(abacusSpec, { args: ['run', '--d-h', '0.9', '--pd', '0.0'] }), [
    'run',
    '--d-h',
    '0.9',
    '--pd',
    '0.0',
  ]);
  assert.throws(() => resolveArgs(abacusSpec, { args: [{ bad: true }] }), /items must be/);
  assert.throws(() => resolveArgs(abacusSpec, ['run']), /arguments must be an object/);
  assert.throws(() => resolveArgs(abacusSpec, { subcommand: 'run', d_h: 0.4 }), /missing required param "pd"/);
});

test('server lists safe tools, runs them, and refuses withheld tools over stdio', { timeout: 60000 }, async () => {
  const transport = new StdioClientTransport({ command: process.execPath, args: [SERVER] });
  const client = new Client({ name: 'scbe-mcp-test', version: '1.0.0' }, { capabilities: {} });
  await client.connect(transport);
  try {
    const listed = await client.listTools();
    const names = new Set(listed.tools.map((t) => t.name));
    assert.ok(names.has('scbe_version'), 'scbe_version tool should be listed');
    assert.ok(names.has('scbe_rns'), 'scbe_rns tool should be listed');
    assert.ok(names.has('scbe_flow'), 'scbe_flow tool should be listed');
    assert.equal(names.has('scbe_push'), false, 'scbe_push must not be AI-callable over MCP');
    assert.equal(names.has('scbe_exec'), false, 'scbe_exec must not be AI-callable over MCP');
    assert.equal(names.has('scbe_run'), false, 'scbe_run must not be AI-callable over MCP');

    const ver = await client.callTool({ name: 'scbe_version', arguments: { json: true } });
    assert.equal(ver.isError || false, false);
    const verObj = JSON.parse(ver.content.map((c) => c.text).join(''));
    assert.ok(verObj && typeof verObj === 'object');

    const demo = await client.callTool({ name: 'scbe_demo', arguments: { json: true } });
    assert.equal(demo.isError || false, false);
    const demoObj = JSON.parse(demo.content.map((c) => c.text).join(''));
    assert.equal(demoObj.decision, 'DENY');

    const bad = await client.callTool({
      name: 'scbe_abacus',
      arguments: { subcommand: 'walk', d_h: 0.4, pd: 0.1 },
    });
    assert.equal(bad.isError, true);
    assert.match(bad.content.map((c) => c.text).join(''), /must be one of/);

    const denied = await client.callTool({ name: 'scbe_push', arguments: { args: ['main'] } });
    assert.equal(denied.isError, true);
    assert.match(denied.content.map((c) => c.text).join(''), /Unknown tool/);
  } finally {
    await client.close();
  }
});
