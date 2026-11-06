'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { scbeHome } = require('./provider-registry');

const SCHEMA = 'geoseal.cli_tools.v1';
const CONFIG_LIMIT = 65536;

function fail(code, message) {
  throw Object.assign(new Error(message), { code });
}

function nativeFile(file, platform = process.platform) {
  try {
    if (!path.isAbsolute(file) || !fs.statSync(file).isFile()) return false;
    if (platform === 'win32') return path.extname(file).toLowerCase() === '.exe';
    fs.accessSync(file, fs.constants.X_OK);
    return true;
  } catch (_) {
    return false;
  }
}

// Resolve once at startup. Never execute a shell's alias, function, batch shim,
// or a relative PATH entry that could change meaning after session cd.
function resolveNative(name, env = process.env, platform = process.platform) {
  if (path.isAbsolute(name)) return nativeFile(name, platform) ? fs.realpathSync(name) : null;
  if (!/^[\w-]+$/.test(name)) return null;
  for (const directory of (env.PATH || env.Path || '').split(path.delimiter)) {
    if (!path.isAbsolute(directory)) continue;
    const file = path.join(directory, name + (platform === 'win32' ? '.exe' : ''));
    if (nativeFile(file, platform)) return fs.realpathSync(file);
  }
  return null;
}

function defaults() {
  const cli = path.resolve(__dirname, '..', 'bin', 'scbe.js');
  return [
    { name: 'node', executable: process.execPath, args: [], description: 'Local Node.js runtime.' },
    {
      name: 'scbe',
      executable: process.execPath,
      args: [cli],
      description: 'SCBE tools and compiler commands.',
    },
    {
      name: 'agent-bus',
      executable: process.execPath,
      args: [cli, 'agent-bus'],
      description: 'SCBE agent bus CLI.',
    },
    ...['git', 'gh', 'python', 'hermes', 'blender'].map((name) => ({
      name,
      executable: resolveNative(name),
      args: [],
      description: `Local ${name} CLI, when installed.`,
    })),
  ];
}

function validateEntry(entry) {
  if (
    !entry ||
    typeof entry !== 'object' ||
    Array.isArray(entry) ||
    Object.keys(entry).some(
      (key) => !['name', 'executable', 'args', 'description'].includes(key)
    ) ||
    typeof entry.name !== 'string' ||
    !/^[a-z][a-z0-9-]{0,63}$/.test(entry.name) ||
    typeof entry.executable !== 'string' ||
    !path.isAbsolute(entry.executable) ||
    entry.executable.includes('\0') ||
    typeof entry.description !== 'string' ||
    entry.description.length > 512 ||
    !Array.isArray(entry.args) ||
    entry.args.length > 64 ||
    entry.args.some((arg) => typeof arg !== 'string' || arg.includes('\0')) ||
    entry.args.reduce((n, arg) => n + arg.length, 0) > 16384
  )
    fail(
      'invalid_tool_config',
      'Each tool needs a name, absolute executable path, literal args array and description.'
    );
  if (process.platform === 'win32' && path.extname(entry.executable).toLowerCase() !== '.exe')
    fail(
      'invalid_tool_config',
      'Windows tools require a native .exe; register Node/Python with a script argument for script CLIs.'
    );
  return { ...entry, args: [...entry.args] };
}

function readConfig(file) {
  if (!fs.existsSync(file)) return [];
  if (fs.statSync(file).size > CONFIG_LIMIT)
    fail('invalid_tool_config', 'CLI tool config exceeds 64 KiB.');
  let config;
  try {
    config = JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
  } catch (_) {
    fail('invalid_tool_config', 'CLI tool config is not valid JSON.');
  }
  if (
    !config ||
    config.schema_version !== SCHEMA ||
    !Array.isArray(config.tools) ||
    config.tools.length > 32 ||
    Object.keys(config).some((key) => !['schema_version', 'tools'].includes(key))
  )
    fail('invalid_tool_config', `Expected ${SCHEMA} and at most 32 tools.`);
  const entries = config.tools.map(validateEntry);
  if (new Set(entries.map((entry) => entry.name)).size !== entries.length)
    fail('invalid_tool_config', 'Duplicate CLI tool names.');
  return entries;
}

function createCliHost(options = {}) {
  const catalog = new Map(defaults().map((entry) => [entry.name, entry]));
  const entries =
    options.entries === undefined
      ? readConfig(options.configPath || path.join(scbeHome(), 'geoseal-tools.json'))
      : options.entries.map(validateEntry);
  for (const entry of entries) catalog.set(entry.name, entry);
  const overridden = new Set(entries.map((entry) => entry.name));
  return {
    diagnose(context = {}) {
      const { probe } = require('./process-diagnostics');
      return [...catalog.values()].map((entry) => {
        const base = { name: entry.name, executable: entry.executable || null, authentication: 'not_checked' };
        if (!entry.executable || !nativeFile(entry.executable))
          return { ...base, status: 'missing_executable' };
        if (process.platform === 'win32' && fs.statSync(entry.executable).size === 0)
          return { ...base, status: 'not_probed', reason: 'Zero-byte app execution alias; configure the native executable to avoid a Store launch.' };
        // Never run an arbitrary extension, wrapper, model or credential check
        // merely because it is registered. Only these default runtimes have
        // an explicitly bounded version-only probe.
        if (overridden.has(entry.name) || entry.args.length || !['node', 'git', 'gh', 'python'].includes(entry.name))
          return { ...base, status: 'not_probed', reason: 'No approved automatic version probe for this registration.' };
        return { ...base, ...probe(entry.executable, ['--version'], { cwd: context.cwd }) };
      });
    },
    list() {
      return {
        schema_version: SCHEMA,
        tools: [...catalog.values()].map((entry) => ({
          name: entry.name,
          description: entry.description,
          available: Boolean(entry.executable && nativeFile(entry.executable)),
        })),
        execution:
          'Native argv after the host gate; inherits host account permissions and environment. Not an OS sandbox.',
      };
    },
    async execute(name, args, context) {
      const entry = catalog.get(name);
      if (!entry)
        fail('unknown_tool', `No registered CLI named ${name}. Use tools to discover names.`);
      if (!entry.executable || !nativeFile(entry.executable))
        fail('tool_unavailable', `The registered ${name} executable is unavailable.`);
      if (typeof options.execute !== 'function')
        fail('executor_unavailable', 'No governed executor is connected.');
      const invocation = { name, executable: entry.executable, args: [...entry.args, ...args] };
      // This representation is inspected/logged, never parsed as shell code.
      const command = [invocation.executable, ...invocation.args]
        .map((arg) => JSON.stringify(arg))
        .join(' ');
      return options.execute(command, { ...context, invocation });
    },
  };
}

function spawnHostedProcess(invocation, options) {
  return spawnSync(invocation.executable, invocation.args, {
    cwd: options.cwd,
    timeout: options.timeoutMs,
    maxBuffer: 1048576,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: false,
    windowsHide: true,
  });
}

module.exports = { createCliHost, resolveNative, spawnHostedProcess };
