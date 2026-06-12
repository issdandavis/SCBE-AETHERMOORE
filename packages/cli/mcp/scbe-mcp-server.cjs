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

const { buildToolsManifest } = require('../lib/tools-manifest');

const SCBE_BIN = path.join(__dirname, '..', 'bin', 'scbe.js');
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');

// Presentation-only hint (does NOT gate the tool list): commands that open an
// interactive loop will time out unless driven non-interactively.
const INTERACTIVE = new Set(['shell', 'terminal', 'advisor']);

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

  for (const c of manifest.commands) {
    const name = toolName(c.name);
    commandFor.set(name, c.name);

    const descLines = [`[${c.stability}] ${c.summary}`, `Usage: ${c.usage}`];
    if (c.subcommands && c.subcommands.length) {
      descLines.push(`Subcommands: ${c.subcommands.map((s) => s.name).join(', ')}`);
    }
    if (c.examples && c.examples.length) {
      descLines.push(`Examples: ${c.examples.join(' | ')}`);
    }
    if (INTERACTIVE.has(c.name)) {
      descLines.push(
        'Note: interactive — pass non-interactive flags (e.g. --json/--minimal) or it may time out.'
      );
    }

    tools.push({
      name,
      description: descLines.join('\n'),
      inputSchema: {
        type: 'object',
        properties: {
          args: {
            type: 'array',
            items: { type: 'string' },
            description: `Positional args and flags passed to "scbe ${c.name}", e.g. ${JSON.stringify(
              (c.usage.match(/<[^>]+>|\b(run-next|add|encode|scan|list)\b/) || ['...']).slice(0, 1)
            )}.`,
          },
          json: {
            type: 'boolean',
            description: c.json
              ? 'Append --json for machine-readable output (recommended).'
              : 'This command does not support --json; leave false.',
          },
        },
        required: [],
        additionalProperties: false,
      },
    });
  }

  return { manifest, tools, commandFor };
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
  const { tools, commandFor } = buildToolDefinitions();

  const server = new Server({ name: 'scbe', version: '1.0.0' }, { capabilities: { tools: {} } });

  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools }));

  server.setRequestHandler(CallToolRequestSchema, async (req) => {
    const { name, arguments: callArgs } = req.params;
    const commandName = commandFor.get(name);
    if (!commandName) {
      return {
        isError: true,
        content: [{ type: 'text', text: `Unknown tool: ${name}` }],
      };
    }
    const args = Array.isArray(callArgs && callArgs.args) ? callArgs.args.map(String) : [];
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

module.exports = { buildToolDefinitions, toolName, runScbe };

if (require.main === module) {
  main().catch((err) => {
    process.stderr.write(`scbe-mcp-server fatal: ${err && err.stack ? err.stack : err}\n`);
    process.exit(1);
  });
}
