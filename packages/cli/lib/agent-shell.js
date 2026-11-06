'use strict';

const readline = require('node:readline');
const { AgentRuntime, PERMISSION_MODES } = require('./agent-runtime');
const { listProviders } = require('./provider-registry');
const { formatPrimitives, formatWafer } = require('./mechanical-primitives');
const { ROUTE_PRESETS } = require('./guided-evidence');
const {
  commandDirectories,
  deleteCommand,
  expandCommand,
  getCommand,
  listCommands,
  saveCommand,
} = require('./custom-commands');

const SLASH_HELP = Object.freeze([
  ['/help', 'Show this command list'],
  ['/model [provider/model]', 'Show or change the active model'],
  ['/tools [all]', 'List the curated model-visible tools'],
  ['/permissions [ask|auto-edit|plan]', 'Show or change tool permissions'],
  ['/status', 'Show session, model, workspace, and tool state'],
  ['/resume [latest|session-id]', 'List or resume saved workspace sessions'],
  ['/clear', 'Start a fresh conversation'],
  ['/compact', 'Summarize history and release context space'],
  ['/ride [route] <objective>', 'Run one guided evidence route with compact citations'],
  ['/evidence <keywords>', 'Search prior compact evidence packets'],
  ['/verify-evidence <packet-id>', 'Verify a packet and its retained artifacts'],
  ['/receipts', 'Verify this workspace tool-receipt chain'],
  ['/commands', 'List user and project prompt commands'],
  ['/command new|edit|list|delete|run', 'Create and manage prompt commands'],
  ['/primitives', 'Show the DATA/BIND/BRANCH/LOOP mechanical core'],
  ['/wafer', 'Show the j-space opcode wafer and geometry views'],
  ['/exit', 'Leave SCBE'],
]);

function sanitizeTerminalText(value) {
  let text = String(value ?? '');

  // Strip OSC hyperlinks/window-title commands and the other ANSI string
  // controls before removing their individual control bytes.
  text = text
    .replace(/(?:\x1B\]|\x9D)[\s\S]*?(?:\x07|\x1B\\|\x9C)/g, '')
    .replace(/(?:\x1B[P_X^]|\x90|\x98|\x9E|\x9F)[\s\S]*?(?:\x1B\\|\x9C)/g, '')
    .replace(/(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~]/g, '')
    .replace(/\x1B[@-_]/g, '')
    .replace(/(?:\x1B\]|\x9D)[\s\S]*$/g, '')
    .replace(/(?:\x1B[P_X^]|\x90|\x98|\x9E|\x9F)[\s\S]*$/g, '');

  // Preserve useful line breaks and tabs, but prevent carriage-return,
  // backspace, C0/C1, and bidi controls from rewriting terminal output.
  return text
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '')
    .replace(/[\x00-\x08\x0B-\x1F\x7F-\x9F]/g, '')
    .replace(/[\u202A-\u202E\u2066-\u2069]/g, '');
}

function colors(enabled) {
  const wrap = (code) => (value) => (enabled ? `\x1b[${code}m${value}\x1b[0m` : String(value));
  return {
    bold: wrap('1'),
    dim: wrap('2'),
    cyan: wrap('36'),
    green: wrap('32'),
    yellow: wrap('33'),
    red: wrap('31'),
    violet: wrap('35'),
  };
}

function formatHelp() {
  const width = Math.max(...SLASH_HELP.map(([command]) => command.length));
  return ['SCBE conversation commands', ...SLASH_HELP.map(([command, help]) => `  ${command.padEnd(width)}  ${help}`)].join('\n');
}

function formatStatus(runtime) {
  const status = runtime.status();
  return [
    `session      ${status.session_id}`,
    `model        ${status.provider}/${status.model}`,
    `permissions  ${status.permission_mode}`,
    `workspace    ${status.workspace}`,
    `messages     ${status.messages}`,
    `tool calls   ${status.tool_calls}`,
    `tools        ${status.tools.length} curated`,
  ].join('\n');
}

function formatProviders(runtime, options = {}) {
  const providers = listProviders(options);
  return [
    `Active model: ${runtime.config.provider}/${runtime.config.model}`,
    '',
    ...providers.map((provider) => {
      const active = provider.id === runtime.config.provider ? '*' : ' ';
      const ready = provider.configured ? 'ready' : provider.keyEnv.length ? provider.keyEnv.join('|') : 'available';
      return `${active} ${provider.id.padEnd(11)} ${provider.defaultModel.padEnd(36)} ${ready}`;
    }),
    '',
    'Change with: /model kimi/kimi-k2.5  or  /model ollama/qwen2.5-coder:1.5b',
  ].join('\n');
}

function formatTools(runtime, detailed = false) {
  const tools = runtime.registry.list();
  if (!detailed) {
    return [
      `Curated tools (${tools.length})`,
      tools.map((tool) => tool.name).join('  '),
      '',
      'Use /tools all for descriptions. The broader SCBE command suite stays outside the default model registry.',
    ].join('\n');
  }
  const width = Math.max(...tools.map((tool) => tool.name.length));
  return [
    `Curated tools (${tools.length})`,
    ...tools.map((tool) => `  ${tool.name.padEnd(width)}  [${tool.kind}] ${tool.description}`),
  ].join('\n');
}

function formatCommands(workspaceRoot, options = {}) {
  const commands = listCommands(workspaceRoot, options);
  const dirs = commandDirectories(workspaceRoot, options);
  if (!commands.length) {
    return [
      'No custom commands yet.',
      'Create one: /command new review Review $ARGUMENTS and return prioritized findings.',
      `User:    ${dirs.user}`,
      `Project: ${dirs.project}`,
    ].join('\n');
  }
  const width = Math.max(...commands.map((command) => command.name.length));
  return [
    `Custom commands (${commands.length})`,
    ...commands.map(
      (command) =>
        `  /${command.name.padEnd(width)}  [${command.scope}] ${command.description || 'custom prompt'}`
    ),
  ].join('\n');
}

function splitWords(value) {
  const matches = String(value || '').match(/(?:[^\s"']+|"[^"]*"|'[^']*')+/g) || [];
  return matches.map((token) => {
    if ((token.startsWith('"') && token.endsWith('"')) || (token.startsWith("'") && token.endsWith("'"))) {
      return token.slice(1, -1);
    }
    return token;
  });
}

async function executeSlash(runtime, rawLine, options = {}) {
  const line = String(rawLine || '').trim().replace(/^:/, '/');
  if (!line.startsWith('/')) return { handled: false };
  const body = line.slice(1);
  const separator = body.search(/\s/);
  const command = (separator === -1 ? body : body.slice(0, separator)).toLowerCase();
  const rest = separator === -1 ? '' : body.slice(separator).trim();
  const storageOptions = { env: options.env, home: options.home };

  if (['exit', 'quit', 'q'].includes(command)) return { handled: true, exit: true, output: 'goodbye.' };
  if (command === 'help') return { handled: true, output: formatHelp() };
  if (command === 'status') return { handled: true, output: formatStatus(runtime) };
  if (command === 'tools') return { handled: true, output: formatTools(runtime, rest === 'all') };
  if (command === 'model') {
    if (!rest) return { handled: true, output: formatProviders(runtime, storageOptions) };
    const selected = runtime.setModel(rest);
    return {
      handled: true,
      output: `Model set to ${selected.provider}/${selected.model}${selected.configured ? '' : ' (API key not detected)'}.`,
    };
  }
  if (command === 'permissions') {
    if (!rest) {
      return {
        handled: true,
        output: [
          `Permission mode: ${runtime.config.permissionMode}`,
          ...Object.entries(PERMISSION_MODES).map(([name, description]) => `  ${name.padEnd(10)} ${description}`),
        ].join('\n'),
      };
    }
    if (!['ask', 'auto-edit', 'accept-edits', 'plan', 'read-only'].includes(rest.toLowerCase())) {
      return { handled: true, output: 'Use: /permissions ask | auto-edit | plan', error: true };
    }
    const mode = runtime.setPermissionMode(rest);
    return { handled: true, output: `Permissions set to ${mode}: ${PERMISSION_MODES[mode]}.` };
  }
  if (command === 'clear') {
    const session = runtime.newSession();
    return { handled: true, output: `Conversation cleared. New session: ${session.id}` };
  }
  if (command === 'compact') {
    const result = await runtime.compact();
    return {
      handled: true,
      output: result.removed
        ? `Compacted ${result.removed} messages into the session summary.`
        : 'Nothing to compact.',
    };
  }
  if (command === 'resume') {
    if (!rest) {
      const sessions = runtime.sessions().slice(0, 12);
      if (!sessions.length) return { handled: true, output: 'No saved sessions for this workspace.' };
      return {
        handled: true,
        output: [
          'Saved sessions',
          ...sessions.map(
            (session) =>
              `  ${session.id}  ${String(session.title).slice(0, 50)}  (${session.messages} messages)`
          ),
          '',
          'Resume with: /resume latest  or  /resume <session-id>',
        ].join('\n'),
      };
    }
    const session = runtime.resume(rest);
    return {
      handled: true,
      output: `Resumed ${session.id}: ${session.title} (${session.messages.length} messages).`,
    };
  }
  if (command === 'commands') {
    return { handled: true, output: formatCommands(runtime.workspaceRoot, storageOptions) };
  }
  if (command === 'ride') {
    const tokens = splitWords(rest);
    let route = 'cross-check';
    if (tokens[0] && Object.prototype.hasOwnProperty.call(ROUTE_PRESETS, tokens[0].toLowerCase())) {
      route = tokens.shift().toLowerCase();
    }
    const objective = tokens.join(' ').trim();
    if (!objective) {
      return {
        handled: true,
        output: 'Use: /ride [code|scholarly|software|biomedical|patent|cross-check|full] <objective>',
        error: true,
      };
    }
    return {
      handled: true,
      prompt:
        'Use guided_evidence exactly once with route "' +
        route +
        '" for this objective: ' +
        objective +
        '. Work from the compact packet, cite its E-number hyperlinks, and use search_evidence only if a stored packet needs targeted retrieval. Treat cross-source matches as corroboration, not proof of truth.',
    };
  }
  if (command === 'evidence') {
    if (!rest) return { handled: true, output: 'Use: /evidence <keywords>', error: true };
    const result = await runtime.registry.execute('search_evidence', { query: rest, limit: 10 });
    return { handled: true, output: JSON.stringify(result, null, 2) };
  }
  if (command === 'verify-evidence') {
    if (!rest) return { handled: true, output: 'Use: /verify-evidence <packet-id>', error: true };
    const result = await runtime.registry.execute('verify_evidence', { packet_id: rest });
    return { handled: true, output: JSON.stringify(result, null, 2), error: result.ok !== true };
  }
  if (command === 'receipts') {
    const result = await runtime.registry.execute('verify_receipts', {});
    return { handled: true, output: JSON.stringify(result, null, 2), error: result.ok !== true };
  }
  if (command === 'primitives') return { handled: true, output: formatPrimitives() };
  if (command === 'wafer') return { handled: true, output: formatWafer() };
  if (command === 'command') {
    const tokens = splitWords(rest);
    const action = String(tokens.shift() || 'list').toLowerCase();
    const projectFlag = tokens.includes('--project');
    const userFlag = tokens.includes('--user');
    const filtered = tokens.filter((token) => token !== '--project' && token !== '--user');
    const scope = projectFlag ? 'project' : userFlag ? 'user' : 'user';
    if (action === 'list') {
      return { handled: true, output: formatCommands(runtime.workspaceRoot, storageOptions) };
    }
    if (action === 'new' || action === 'edit') {
      const name = filtered.shift();
      if (!name) {
        return {
          handled: true,
          output: `Use: /command ${action} <name> [template] [--user|--project]`,
          error: true,
        };
      }
      const existing = getCommand(runtime.workspaceRoot, name, storageOptions);
      if (action === 'new' && existing && existing.scope === scope) {
        return { handled: true, output: `/${name} already exists in ${scope} commands.`, error: true };
      }
      let template = filtered.join(' ').trim();
      if (!template && options.ask) {
        if (action === 'edit' && existing) {
          const answer = await options.ask(
            `Current template:\n${sanitizeTerminalText(existing.template)}\n\nNew template › `
          );
          template = String(answer || '').trim();
        } else {
          const answer = await options.ask('Template (use $ARGUMENTS for invocation text) › ');
          template = String(answer || '').trim();
        }
      }
      if (!template) {
        return { handled: true, output: 'A non-empty template is required.', error: true };
      }
      const saved = saveCommand(
        runtime.workspaceRoot,
        {
          name,
          template,
          scope: action === 'edit' && existing && !projectFlag && !userFlag ? existing.scope : scope,
          createOnly: action === 'new',
        },
        storageOptions
      );
      return { handled: true, output: `Saved /${saved.name} in ${saved.scope} commands.` };
    }
    if (['delete', 'remove', 'rm'].includes(action)) {
      const name = filtered[0];
      if (!name) return { handled: true, output: 'Use: /command delete <name>', error: true };
      const removed = deleteCommand(runtime.workspaceRoot, name, {
        ...storageOptions,
        ...(projectFlag || userFlag ? { scope } : {}),
      });
      return {
        handled: true,
        output: removed ? `Deleted /${removed.name} from ${removed.scope} commands.` : `No command named /${name}.`,
        error: !removed,
      };
    }
    if (action === 'run') {
      const name = filtered.shift();
      if (!name) return { handled: true, output: 'Use: /command run <name> [args]', error: true };
      const custom = getCommand(runtime.workspaceRoot, name, storageOptions);
      if (!custom) return { handled: true, output: `No command named /${name}.`, error: true };
      return { handled: true, prompt: expandCommand(custom, filtered.join(' ')), command: custom };
    }
    return {
      handled: true,
      output: 'Use: /command new|edit|list|delete|run ...',
      error: true,
    };
  }

  const custom = getCommand(runtime.workspaceRoot, command, storageOptions);
  if (custom) return { handled: true, prompt: expandCommand(custom, rest), command: custom };
  return { handled: true, output: `Unknown command /${command}. Use /help.`, error: true };
}

function createQuestion(rl, output) {
  let closed = false;
  rl.once('close', () => {
    closed = true;
  });
  return async (prompt) => {
    if (closed) return null;
    return new Promise((resolve) => {
      let finished = false;
      const settle = (value) => {
        if (finished) return;
        finished = true;
        rl.off('close', onClose);
        resolve(value);
      };
      const onClose = () => settle(null);
      rl.once('close', onClose);
      try {
        rl.question(prompt, (answer) => settle(answer));
      } catch (_error) {
        output.write(prompt);
        settle(null);
      }
    });
  };
}

async function runAgentShell(options = {}) {
  const input = options.input || process.stdin;
  const output = options.output || process.stdout;
  const terminal = options.terminal ?? Boolean(input.isTTY && output.isTTY);
  const c = colors(terminal && !process.env.NO_COLOR);
  const rl = readline.createInterface({ input, output, terminal });
  const ask = createQuestion(rl, output);
  let permissionPromptActive = false;
  const runtime =
    options.runtime ||
    new AgentRuntime({
      workspaceRoot: options.workspaceRoot || process.cwd(),
      env: options.env,
      home: options.home,
      transport: options.transport,
      permissionResolver:
        options.permissionResolver ||
        (terminal
          ? async ({ tool, kind, args }) => {
              permissionPromptActive = true;
              const preview =
                kind === 'execute' ? args.command || safePreview(args) : args.path || safePreview(args);
              const safeTool = sanitizeTerminalText(tool);
              const safePreviewText = sanitizeTerminalText(preview).slice(0, 120);
              const answer = await ask(
                `${c.yellow('allow')} ${c.bold(safeTool)} ${c.dim(safePreviewText)}? [y/N] `
              );
              permissionPromptActive = false;
              return /^y(es)?$/i.test(String(answer || '').trim());
            }
          : async () => false),
      onEvent: async (event) => {
        if (event.type === 'tool_start') {
          const tool = sanitizeTerminalText(event.tool);
          const kind = sanitizeTerminalText(event.kind);
          output.write(
            `\n${c.violet('↳')} ${c.bold(tool)} ${c.dim(`[${kind}]`)}\n`
          );
        } else if (event.type === 'tool_result') {
          const mark = event.ok ? c.green('✓') : event.denied ? c.yellow('blocked') : c.red('failed');
          output.write(`${c.dim('  ')}${mark} ${c.dim(`${sanitizeTerminalText(event.duration_ms)}ms`)}\n`);
        } else if (event.type === 'permission' && event.decision === 'deny' && !permissionPromptActive) {
          output.write(`${c.yellow('  permission denied')} ${c.dim(sanitizeTerminalText(event.reason))}\n`);
        } else if (event.type === 'assistant_note' && event.content) {
          output.write(`\n${c.cyan('scbe')} › ${sanitizeTerminalText(event.content)}\n`);
        }
      },
    });

  const provider = sanitizeTerminalText(runtime.config.provider);
  const model = sanitizeTerminalText(runtime.config.model);
  const permissionMode = sanitizeTerminalText(runtime.config.permissionMode);
  const banner = `agent · ${provider}/${model} · ${permissionMode} · /help`;
  output.write(`${c.bold(c.cyan('SCBE'))} ${c.dim(banner)}\n`);

  const runPrompt = async (prompt) => {
    if (terminal) output.write(`${c.cyan('scbe')} › ${c.dim('working…')}\r`);
    try {
      const result = await runtime.runTurn(prompt);
      output.write(
        `${terminal ? '\x1b[2K\r' : ''}${c.cyan('scbe')} › ${sanitizeTerminalText(result.content)}\n`
      );
    } catch (error) {
      if (!terminal && (!Number.isInteger(process.exitCode) || process.exitCode === 0)) {
        process.exitCode = 1;
      }
      const message = sanitizeTerminalText(error?.message || error);
      output.write(
        `${terminal ? '\x1b[2K\r' : ''}${c.red('model error')} ${message}\n` +
          `${c.dim('Use /model to inspect or change providers.')}\n`
      );
    }
  };

  if (options.initialPrompt) {
    output.write(`${c.bold('you')} › ${sanitizeTerminalText(options.initialPrompt)}\n`);
    await runPrompt(options.initialPrompt);
    if (!terminal && options.continueAfterPrompt !== true) {
      rl.close();
      return runtime;
    }
  }

  const handleLine = async (answer) => {
    const line = String(answer).trim();
    if (!line) return false;
    const slash = await executeSlash(runtime, line, {
      ...(terminal ? { ask } : {}),
      env: options.env,
      home: options.home,
    });
    if (slash.handled) {
      if (slash.output) {
        const safeOutput = sanitizeTerminalText(slash.output);
        output.write(`${slash.error ? c.yellow(safeOutput) : safeOutput}\n`);
      }
      if (slash.exit) return true;
      if (slash.prompt) await runPrompt(slash.prompt);
      return false;
    }
    await runPrompt(line);
    return false;
  };

  if (!terminal) {
    output.write(`${c.bold('you')} › `);
    for await (const answer of rl) {
      if (await handleLine(answer)) break;
      output.write(`${c.bold('you')} › `);
    }
  } else {
    while (true) {
      const answer = await ask(`${c.bold('you')} › `);
      if (answer == null || (await handleLine(answer))) break;
    }
  }
  if (!rl.closed) rl.close();
  return runtime;
}

function safePreview(value) {
  try {
    return JSON.stringify(value);
  } catch (_error) {
    return '[arguments]';
  }
}

module.exports = {
  SLASH_HELP,
  executeSlash,
  formatHelp,
  formatStatus,
  formatProviders,
  formatTools,
  formatCommands,
  sanitizeTerminalText,
  runAgentShell,
};
