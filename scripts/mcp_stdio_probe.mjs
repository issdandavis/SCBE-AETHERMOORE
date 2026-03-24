#!/usr/bin/env node

import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

function printUsage() {
  console.log(`Usage:
  node scripts/mcp_stdio_probe.mjs --command <cmd> [--arg <value> ...] [options]
  node scripts/mcp_stdio_probe.mjs --server <name> [--config <path>] [options]

Options:
  --name <label>          Friendly server label in output
  --command <cmd>         Explicit stdio server command
  --arg <value>           Repeatable command argument
  --server <name>         Server name inside an MCP config file
  --config <path>         MCP config path (default: .mcp.json when --server is used)
  --cwd <path>            Working directory for the server process
  --env KEY=VALUE         Repeatable env override
  --timeout-ms <ms>       Probe timeout in milliseconds (default: 15000)
  --tool <name>           Optional tool to call after tools/list
  --tool-args <json>      JSON object for the optional tool call
  --help                  Show this help

Examples:
  node scripts/mcp_stdio_probe.mjs --name scbe --command node --arg mcp/scbe-server/server.mjs
  node scripts/mcp_stdio_probe.mjs --server fs --config .mcp.json
`);
}

function parseArgs(argv) {
  const options = {
    name: '',
    command: '',
    args: [],
    config: '',
    server: '',
    cwd: process.cwd(),
    envOverrides: {},
    timeoutMs: 15000,
    tool: '',
    toolArgs: '{}',
  };

  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    switch (token) {
      case '--help':
        options.help = true;
        break;
      case '--name':
        options.name = argv[++i] ?? '';
        break;
      case '--command':
        options.command = argv[++i] ?? '';
        break;
      case '--arg':
        options.args.push(argv[++i] ?? '');
        break;
      case '--config':
        options.config = argv[++i] ?? '';
        break;
      case '--server':
        options.server = argv[++i] ?? '';
        break;
      case '--cwd':
        options.cwd = argv[++i] ? path.resolve(argv[i]) : process.cwd();
        break;
      case '--env': {
        const assignment = argv[++i] ?? '';
        const index = assignment.indexOf('=');
        if (index <= 0) {
          throw new Error(`Invalid --env value '${assignment}'. Expected KEY=VALUE.`);
        }
        const key = assignment.slice(0, index);
        const value = assignment.slice(index + 1);
        options.envOverrides[key] = value;
        break;
      }
      case '--timeout-ms':
        options.timeoutMs = Number(argv[++i] ?? 15000);
        break;
      case '--tool':
        options.tool = argv[++i] ?? '';
        break;
      case '--tool-args':
        options.toolArgs = argv[++i] ?? '{}';
        break;
      default:
        throw new Error(`Unknown argument: ${token}`);
    }
  }

  if (!options.command && options.server) {
    options.config = options.config || '.mcp.json';
  }

  return options;
}

function interpolateEnv(value) {
  return String(value).replace(/\$\{([A-Z0-9_]+)\}/gi, (_, key) => process.env[key] ?? '');
}

async function resolveFromConfig(configPath, serverName) {
  const resolvedConfigPath = path.resolve(configPath);
  const configDir = path.dirname(resolvedConfigPath);
  const raw = JSON.parse(await readFile(resolvedConfigPath, 'utf8'));
  const configRoot = raw?.mcpServers ?? {};
  const serverConfig = configRoot?.[serverName];
  if (!serverConfig) {
    throw new Error(`Server '${serverName}' not found in ${resolvedConfigPath}`);
  }

  const transport = serverConfig.transport?.type ? serverConfig.transport : serverConfig;
  if (transport.type !== 'stdio') {
    throw new Error(`Server '${serverName}' is not a stdio transport`);
  }

  const args = Array.isArray(transport.args) ? transport.args.map(interpolateEnv) : [];
  const env = Object.fromEntries(
    Object.entries(transport.env ?? {}).map(([key, value]) => [key, interpolateEnv(value)]),
  );

  return {
    name: serverConfig.name || serverName,
    command: transport.command,
    args,
    env,
    cwd: configDir,
    configPath: resolvedConfigPath,
    configServer: serverName,
  };
}

function normalizeToolCallResult(result) {
  if (!result) return null;
  return {
    isError: Boolean(result.isError),
    content: Array.isArray(result.content) ? result.content : [],
    structuredContent: result.structuredContent ?? null,
  };
}

async function run() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    printUsage();
    return 0;
  }

  let probeConfig;
  if (options.server) {
    probeConfig = await resolveFromConfig(options.config, options.server);
  } else if (options.command) {
    probeConfig = {
      name: options.name || 'stdio-probe',
      command: options.command,
      args: options.args,
      env: {},
      cwd: options.cwd,
      configPath: null,
      configServer: null,
    };
  } else {
    throw new Error('Provide either --command or --server.');
  }

  const mergedEnv = { ...process.env, ...probeConfig.env, ...options.envOverrides };
  const transport = new StdioClientTransport({
    command: probeConfig.command,
    args: probeConfig.args,
    cwd: probeConfig.cwd,
    env: mergedEnv,
  });
  const client = new Client({
    name: 'scbe-mcp-probe',
    version: '0.1.0',
  });

  const startedAt = Date.now();
  const timeoutMs = Number.isFinite(options.timeoutMs) && options.timeoutMs > 0 ? options.timeoutMs : 15000;

  try {
    await Promise.race([
      client.connect(transport),
      new Promise((_, reject) => {
        setTimeout(() => reject(new Error(`Probe timed out after ${timeoutMs}ms during connect`)), timeoutMs);
      }),
    ]);

    const toolList = await Promise.race([
      client.listTools(),
      new Promise((_, reject) => {
        setTimeout(() => reject(new Error(`Probe timed out after ${timeoutMs}ms during tools/list`)), timeoutMs);
      }),
    ]);

    const summary = {
      status: 'ok',
      server: options.name || probeConfig.name,
      transport: 'stdio',
      command: probeConfig.command,
      args: probeConfig.args,
      cwd: probeConfig.cwd,
      env_keys: Object.keys({ ...probeConfig.env, ...options.envOverrides }).sort(),
      config_path: probeConfig.configPath,
      config_server: probeConfig.configServer,
      duration_ms: Date.now() - startedAt,
      tool_count: Array.isArray(toolList.tools) ? toolList.tools.length : 0,
      tools: Array.isArray(toolList.tools)
        ? toolList.tools.map((tool) => ({
            name: tool.name,
            description: tool.description ?? '',
          }))
        : [],
    };

    if (options.tool) {
      const toolArgs = JSON.parse(options.toolArgs);
      const toolResult = await Promise.race([
        client.callTool({ name: options.tool, arguments: toolArgs }),
        new Promise((_, reject) => {
          setTimeout(() => reject(new Error(`Probe timed out after ${timeoutMs}ms during tools/call`)), timeoutMs);
        }),
      ]);
      summary.tool_call = {
        name: options.tool,
        arguments: toolArgs,
        result: normalizeToolCallResult(toolResult),
      };
    }

    console.log(JSON.stringify(summary, null, 2));
    return 0;
  } catch (error) {
    console.log(
      JSON.stringify(
        {
          status: 'error',
          server: options.name || probeConfig.name,
          transport: 'stdio',
          command: probeConfig.command,
          args: probeConfig.args,
          cwd: probeConfig.cwd,
          config_path: probeConfig.configPath,
          config_server: probeConfig.configServer,
          duration_ms: Date.now() - startedAt,
          error: error instanceof Error ? error.message : String(error),
        },
        null,
        2,
      ),
    );
    return 1;
  } finally {
    try {
      await transport.close();
    } catch {
      // Ignore transport shutdown failures during diagnostics.
    }
  }
}

const exitCode = await run();
process.exit(exitCode);
