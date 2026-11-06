'use strict';

const fs = require('node:fs');
const path = require('node:path');
const readline = require('node:readline');
const { once } = require('node:events');
const { sanitizeTerminalText } = require('./agent-shell');
const { createCliHost } = require('./cli-host');

const MAX_REQUEST_BYTES = 131072;
const HELP = `GeoSeal command shell
  <command>           Execute native shell syntax (PowerShell on Windows)
  cd <literal path>   Change the session directory; quotes are supported
  pwd / status        Inspect the session
  geo <task>          Set geometric routing context using the agent bus
  geo / geo clear     Inspect / clear routing context
  bus [task]          Record local bus intake; defaults to the geo task
  tools               List the host's named CLI tools
  diagnose            Check local runtimes and shell startup (no sign-in)
  tool <name> [JSON]   Run literal arguments, e.g. tool git ["status","--short"]
  ask <question>      Request AI advice through the configured provider
  help / exit         Show commands / close the shell

Agents: geoseal shell --agent-json (NDJSON); geoseal shell --describe
Directory and geo context persist. Native variables/functions do not.
Geo routing is context; every native command still passes the existing gate.`;

function loadCommandBus() {
  const local = path.resolve(__dirname, '..', '..', 'agent-bus', 'dist', 'index.js');
  const bus = fs.existsSync(local) ? require(local) : require('scbe-agent-bus');
  if (typeof bus.CommandSession !== 'function' || !bus.COMMAND_SESSION_OPERATIONS?.tool || !bus.COMMAND_SESSION_OPERATIONS?.diagnose) {
    throw new Error(
      'The connected agent bus lacks CLI-host diagnostics. Build/update scbe-agent-bus with tool/tools/diagnose support.'
    );
  }
  return bus;
}

/** Bounded framing: discard an oversized line through its newline, then resume. */
async function* boundedLines(input, maxBytes = MAX_REQUEST_BYTES) {
  let parts = [];
  let bytes = 0;
  let oversized = false;
  for await (const chunk of input) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    let offset = 0;
    while (offset < buffer.length) {
      const newline = buffer.indexOf(10, offset);
      const end = newline < 0 ? buffer.length : newline;
      const part = buffer.subarray(offset, end);
      bytes += part.length;
      if (bytes > maxBytes) {
        oversized = true;
        parts = [];
      } else if (!oversized) parts.push(Buffer.from(part));
      if (newline < 0) break;
      yield oversized
        ? { error: 'request_too_large' }
        : { line: Buffer.concat(parts).toString('utf8').replace(/\r$/, '') };
      parts = [];
      bytes = 0;
      oversized = false;
      offset = newline + 1;
    }
  }
  if (bytes)
    yield oversized
      ? { error: 'request_too_large' }
      : { line: Buffer.concat(parts).toString('utf8').replace(/\r$/, '') };
}

async function write(output, value) {
  if (!output.write(value)) await once(output, 'drain');
}

function literalPath(value) {
  const text = value.trim().replace(/^-LiteralPath\s+/i, '');
  if (
    (text.startsWith('"') && text.endsWith('"')) ||
    (text.startsWith("'") && text.endsWith("'"))
  ) {
    const quote = text[0];
    return text.slice(1, -1).replaceAll(quote + quote, quote);
  }
  return text;
}

function humanRequest(line, id) {
  const match = line.trim().match(/^(:?[\w-]+)(?:\s+([\s\S]*))?$/);
  const verb = (match?.[1] || '').replace(/^:/, '').toLowerCase();
  const rest = match?.[2] || '';
  if (['help', 'exit', 'quit', 'ask'].includes(verb)) return { control: verb, text: rest };
  if (verb === 'pwd' || verb === 'status') return { id, op: 'status' };
  if (verb === 'cd' || verb === 'set-location')
    return { id, op: 'cd', path: literalPath(rest || '.') };
  if (verb === 'geo')
    return { id, op: 'geo', ...(rest ? { task: rest === 'clear' ? null : rest } : {}) };
  if (verb === 'bus') return { id, op: 'bus', ...(rest ? { task: rest } : {}) };
  if (verb === 'tools' || verb === 'diagnose') return { id, op: verb };
  if (verb === 'tool') {
    const parts = rest.match(/^(\S+)(?:\s+([\s\S]*))?$/);
    let args;
    try {
      args = JSON.parse(parts?.[2] || '[]');
    } catch (_) {
      args = null;
    }
    return { id, op: 'tool', name: parts?.[1] || '', args };
  }
  return { id, op: 'run', command: verb === 'run' ? rest : line };
}

function renderReply(reply) {
  if (reply.error) return `error [${reply.error.code}]: ${reply.error.message}\n`;
  const result = reply.result;
  if (result?.schema_version === 'scbe.agent_bus.compass_route_plan.v1') {
    return `Geo task: ${result.task}\nRoute: ${result.domain} / ${result.command_path}\nFormation: ${result.formation}\n`;
  }
  if (result?.receipt_id)
    return `Bus receipt: ${result.receipt_id} (${result.reason || 'local intake'})\n`;
  if (result?.cwd) {
    return `${result.cwd}\n${result.geo ? `Geo: ${result.geo.domain} / ${result.geo.formation} / ${result.geo.task}\n` : ''}`;
  }
  if (result && Object.hasOwn(result, 'success')) {
    const stdout = result.stdout ?? result.stdout_preview ?? '';
    const stderr = result.stderr ?? result.stderr_preview ?? '';
    return `${stdout}${stderr}${!reply.ok ? `\nexit ${result.exit_code}: ${result.failure?.summary || 'command failed'}\n` : ''}`;
  }
  return `${JSON.stringify(result, null, 2)}\n`;
}

async function runCommandShell(options = {}) {
  const input = options.input || process.stdin;
  const output = options.output || process.stdout;
  const bus = options.bus || loadCommandBus();
  const cliHost = options.cliHost || createCliHost({ execute: options.execute });
  const session =
    options.session ||
    new bus.CommandSession({
      cwd: options.cwd,
      execute: options.execute,
      listTools: () => cliHost.list(),
      diagnose: ({ cwd }) => {
        const shell = require('./native-shell').inspectShell(true);
        const tools = cliHost.diagnose({ cwd });
        return {
          schema_version: 'geoseal.runtime_diagnostics.v1',
          checked_at: new Date().toISOString(),
          cwd,
          shell,
          tools,
          status: shell.status === 'ready' && tools.every((tool) => ['ready', 'not_probed'].includes(tool.status)) ? 'ok' : 'degraded',
          authentication: 'not_checked; classify authentication errors only from actual tool failures',
          scope: 'Current host account and environment; repeat inside the failing worker sandbox. No permission changes.',
        };
      },
      executeTool: (name, args, context) => cliHost.execute(name, args, context),
      recordEvent: (event) => bus.runEvent(event, { repoRoot: options.cwd || process.cwd() }),
    });
  if (options.help && !options.json) {
    await write(output, `${HELP}\n`);
    return 0;
  }
  if (options.describe || options.help) {
    await write(output, `${JSON.stringify(session.describe(), null, 2)}\n`);
    return 0;
  }
  if (options.diagnose) {
    const reply = await session.dispatch({ id: 'diagnostics', op: 'diagnose' });
    await write(output, `${JSON.stringify(reply, null, 2)}\n`);
    return reply.ok ? 0 : 1;
  }
  if (options.json) {
    await write(
      output,
      `${JSON.stringify({ ready: true, schema_version: bus.COMMAND_SESSION_SCHEMA, session: session.snapshot() })}\n`
    );
    let failed = false;
    for await (const frame of boundedLines(input)) {
      if (!frame.error && !frame.line.trim()) continue;
      let reply;
      try {
        if (frame.error) throw new Error(frame.error);
        reply = await session.dispatch(JSON.parse(frame.line));
      } catch (error) {
        reply = await session.dispatch(null);
        reply.error = {
          code: frame.error || 'invalid_json',
          message: frame.error
            ? `Request exceeds ${MAX_REQUEST_BYTES} bytes.`
            : 'Expected one JSON object per line.',
        };
      }
      failed ||= !reply.ok;
      await write(output, `${JSON.stringify(reply)}\n`);
    }
    return failed ? 1 : 0;
  }

  const terminal = Boolean(input.isTTY && output.isTTY);
  const rl = readline.createInterface({ input, output, terminal });
  const prompt = () => {
    if (terminal) {
      rl.setPrompt(`geo ${sanitizeTerminalText(session.snapshot().cwd)}> `);
      rl.prompt();
    }
  };
  if (terminal) await write(output, `${HELP}\n\n`);
  prompt();
  let sequence = 0;
  let failed = false;
  try {
    for await (const line of rl) {
      if (!line.trim()) {
        prompt();
        continue;
      }
      const request = humanRequest(line, `terminal-${++sequence}`);
      if (request.control === 'exit' || request.control === 'quit') break;
      if (request.control === 'help') await write(output, `${HELP}\n`);
      else if (request.control === 'ask') {
        if (!request.text.trim() || !options.ask)
          await write(output, 'usage: ask <question> (configured AI provider required)\n');
        else {
          try {
            const answer = await options.ask(request.text);
            failed ||= answer.ok === false;
            await write(
              output,
              `${sanitizeTerminalText(answer.response || answer.error || JSON.stringify(answer))}\n`
            );
          } catch (error) {
            failed = true;
            await write(output, `AI error: ${sanitizeTerminalText(error.message)}\n`);
          }
        }
      } else {
        const reply = await session.dispatch(request);
        failed ||= !reply.ok;
        await write(output, sanitizeTerminalText(renderReply(reply)));
      }
      prompt();
    }
  } finally {
    rl.close();
  }
  return failed ? 1 : 0;
}

module.exports = { runCommandShell, boundedLines, humanRequest, loadCommandBus, MAX_REQUEST_BYTES };
