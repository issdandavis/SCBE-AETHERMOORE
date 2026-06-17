#!/usr/bin/env node
'use strict';

/**
 * @file scbe-mcp-server.cjs
 * @module cli/mcp/scbe-mcp-server
 *
 * Model Context Protocol server that exposes the `scbe` CLI as a set of tools
 * other AI clients can call (Claude Desktop, Claude Code, any MCP client).
 *
 * SINGLE SOURCE OF TRUTH
 * ----------------------
 * The tool list is generated directly from lib/tools-manifest.js — the SAME
 * manifest that backs `scbe tools --json`. There is no second hand-maintained
 * tool list to drift: add a command to COMMAND_SPECS and it appears here too.
 *
 * Each manifest command becomes an MCP tool `scbe_<name>` (dashes -> underscores).
 * Calling it runs `node bin/scbe.js <name> [...args] [--json]` and returns the
 * command's stdout (stderr + non-zero exit are surfaced as an error result).
 *
 * Run:  node packages/cli/mcp/scbe-mcp-server.cjs
 * Wire into an MCP client (.mcp.json):
 *   { "mcpServers": { "scbe": { "command": "node",
 *       "args": ["packages/cli/mcp/scbe-mcp-server.cjs"] } } }
 */

const path = require('node:path');
const { execFile } = require('node:child_process');

const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} = require('@modelcontextprotocol/sdk/types.js');

const { buildToolsManifest, serializeParams, paramToJsonSchema } = require('../lib/tools-manifest');

const SCBE_BIN = path.join(__dirname, '..', 'bin', 'scbe.js');
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');

// Presentation-only hint (does NOT gate the tool list): commands that open an
// interactive loop will time out unless driven non-interactively.
const INTERACTIVE = new Set(['shell', 'terminal', 'advisor']);

// AI clients should not receive arbitrary shell, git-write, or remote-write
// tools by default. Those commands remain available in the human CLI; the MCP
// bridge exposes the safe/read/compute surface.
const MCP_DENIED_COMMANDS = new Set([
  'commit',
  'exec',
  'prepush',
  'push',
  'run',
  'shell',
  'store',
  'terminal',
]);

function toolName(commandName) {
  return `scbe_${commandName.replace(/-/g, '_')}`;
}

/**
 * Build the MCP tool definitions + a toolName->command map, straight from the
 * manifest. Pure (no side effects) so it can be unit-tested without a server.
 */
function buildToolDefinitions() {
  const manifest = buildToolsManifest();
  const tools = [];
  const commandFor = new Map();
  const specByTool = new Map();

  for (const c of manifest.commands) {
    if (MCP_DENIED_COMMANDS.has(c.name)) continue;
    const name = toolName(c.name);
    commandFor.set(name, c.name);
    specByTool.set(name, c);

    const hasParams = Array.isArray(c.params) && c.params.length > 0;

    const descLines = [`[${c.stability}] ${c.summary}`, `Usage: ${c.usage}`];
    if (c.subcommands && c.subcommands.length) {
      descLines.push(`Subcommands: ${c.subcommands.map((s) => s.name).join(', ')}`);
    }
    if (c.examples && c.examples.length) {
      descLines.push(`Examples: ${c.examples.join(' | ')}`);
    }
    if (hasParams) {
      descLines.push('Pass the typed params below; "args" is a raw escape hatch.');
    }
    if (INTERACTIVE.has(c.name)) {
      descLines.push(
        'Note: interactive — pass non-interactive flags (e.g. --json/--minimal) or it may time out.'
      );
    }

    // Typed params (when declared) come first; args + json are always present so
    // the raw escape hatch and the --json toggle work for every command.
    const properties = {};
    const required = [];
    if (hasParams) {
      for (const p of c.params) {
        properties[p.name] = paramToJsonSchema(p);
        if (p.required) required.push(p.name);
      }
    }
    properties.args = {
      type: 'array',
      items: { type: 'string' },
      description: hasParams
        ? `Raw positional args/flags for "scbe ${c.name}" — overrides the typed params above when set.`
        : `Positional args and flags passed to "scbe ${c.name}", e.g. ${JSON.stringify(
            (c.usage.match(/<[^>]+>|\b(run-next|add|encode|scan|list)\b/) || ['...']).slice(0, 1)
          )}.`,
    };
    properties.json = {
      type: 'boolean',
      description: c.json
        ? 'Append --json for machine-readable output (recommended).'
        : 'This command does not support --json; leave false.',
    };

    tools.push({
      name,
      description: descLines.join('\n'),
      inputSchema: {
        type: 'object',
        properties,
        // Required typed params are only enforced when the caller is NOT using
        // the raw `args` escape hatch; the server resolves that at call time, so
        // we keep the schema-level required list empty to avoid blocking args[].
        required: [],
        additionalProperties: false,
      },
    });
  }

  return { manifest, tools, commandFor, specByTool };
}

/**
 * Resolve a tool call's structured arguments into the argv array for `scbe`.
 * Raw `args` (when non-empty) wins as an explicit escape hatch; otherwise the
 * declared params are serialized. Throws on missing-required / bad-enum so the
 * caller gets a clear error instead of a malformed command.
 */
function resolveArgs(spec, callArgs) {
  if (callArgs && (typeof callArgs !== 'object' || Array.isArray(callArgs))) {
    throw new Error('arguments must be an object');
  }
  const raw = callArgs && callArgs.args;
  if (raw !== undefined && !Array.isArray(raw)) {
    throw new Error('"args" must be an array of strings');
  }
  if (Array.isArray(raw) && raw.length > 0) {
    for (const item of raw) {
      const t = typeof item;
      if (item === null || (t !== 'string' && t !== 'number' && t !== 'boolean')) {
        throw new Error('"args" items must be strings, numbers, or booleans');
      }
    }
    return raw.map(String);
  }
  if (spec && Array.isArray(spec.params) && spec.params.length) {
    return serializeParams(spec, callArgs || {});
  }
  return [];
}

// Async on purpose: spawnSync blocked the server's event loop, so concurrent
// tool calls from agent fleets serialized (N x slowest-call tail latency, the
// "~36s/call" seen under 10-agent load). execFile keeps the loop free, so
// concurrent calls run concurrently. Resolves with a spawnSync-shaped result.
function runScbe(commandName, args, wantJson, timeoutMs) {
  const finalArgs = [SCBE_BIN, commandName, ...args];
  if (wantJson) finalArgs.push('--json');
  return new Promise((resolve) => {
    execFile(
      process.execPath,
      finalArgs,
      {
        cwd: REPO_ROOT,
        encoding: 'utf8',
        timeout: timeoutMs || 120000,
        maxBuffer: 16 * 1024 * 1024,
      },
      (error, stdout, stderr) => {
        if (!error) {
          resolve({ error: null, status: 0, stdout, stderr });
        } else if (error.killed && error.signal) {
          resolve({ error: { code: 'ETIMEDOUT', message: error.message }, status: null, stdout, stderr });
        } else if (typeof error.code === 'number') {
          // Normal nonzero exit: not a spawn failure.
          resolve({ error: null, status: error.code, stdout, stderr });
        } else {
          resolve({ error, status: null, stdout, stderr });
        }
      }
    );
  });
}

async function main() {
  const { tools, commandFor, specByTool } = buildToolDefinitions();

  const server = new Server({ name: 'scbe', version: '1.0.0' }, { capabilities: { tools: {} } });

  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools }));

  server.setRequestHandler(CallToolRequestSchema, async (req) => {
    const params = req && req.params && typeof req.params === 'object' ? req.params : {};
    const { name, arguments: callArgs } = params;
    if (typeof name !== 'string') {
      return {
        isError: true,
        content: [{ type: 'text', text: 'Tool name must be a string' }],
      };
    }
    const commandName = commandFor.get(name);
    if (!commandName) {
      return {
        isError: true,
        content: [{ type: 'text', text: `Unknown tool: ${name}` }],
      };
    }
    let args;
    try {
      args = resolveArgs(specByTool.get(name), callArgs);
    } catch (err) {
      return {
        isError: true,
        content: [{ type: 'text', text: `scbe ${commandName}: ${err.message}` }],
      };
    }
    const wantJson = Boolean(callArgs && callArgs.json);

    const res = await runScbe(commandName, args, wantJson);
    if (res.error) {
      const reason =
        res.error.code === 'ETIMEDOUT'
          ? 'timed out (interactive or long-running?)'
          : res.error.message;
      return {
        isError: true,
        content: [{ type: 'text', text: `scbe ${commandName} failed to run: ${reason}` }],
      };
    }
    const stdout = (res.stdout || '').trim();
    const stderr = (res.stderr || '').trim();
    const ok = res.status === 0;
    const body = ok
      ? stdout || '(no output)'
      : [stdout, stderr].filter(Boolean).join('\n') || `exit ${res.status}`;
    return {
      isError: !ok,
      content: [{ type: 'text', text: body }],
    };
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
  // Stay alive on stdio; the transport handles the lifecycle.
}

module.exports = { buildToolDefinitions, toolName, runScbe, resolveArgs };

if (require.main === module) {
  main().catch((err) => {
    process.stderr.write(`scbe-mcp-server fatal: ${err && err.stack ? err.stack : err}\n`);
    process.exit(1);
  });
}
