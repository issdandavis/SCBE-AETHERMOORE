#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const pkgRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(pkgRoot, '..', '..');
const {
  validateToolSpec,
  registerToolSpecInFile,
  listToolSpecsFromFile,
  unregisterToolSpecInFile,
  decompose,
  recompose,
} = require(path.join(pkgRoot, 'dist', 'index.js'));

function parseArgs(argv) {
  const flags = {};
  const positionals = [];
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) {
      positionals.push(token);
      continue;
    }
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith('--')) {
      flags[key] = true;
    } else {
      flags[key] = next;
      i += 1;
    }
  }
  return { command: positionals[0] || 'help', positionals: positionals.slice(1), flags };
}

function toolsJsonPath(flags) {
  return path.resolve(String(flags['tools-json'] || path.join(pkgRoot, 'tools.json')));
}

function readInput(flags, rest) {
  if (flags.file) return fs.readFileSync(path.resolve(String(flags.file)), 'utf8');
  if (flags.text) return String(flags.text);
  return rest.join(' ').trim();
}

function parseSpec(flags, rest) {
  if (flags['spec-file']) {
    return JSON.parse(fs.readFileSync(path.resolve(String(flags['spec-file'])), 'utf8'));
  }
  if (flags.spec) {
    return JSON.parse(String(flags.spec));
  }
  const raw = rest.join(' ').trim();
  if (!raw) throw new Error('missing --spec, --spec-file, or inline JSON spec');
  return JSON.parse(raw);
}

function byteRows(text) {
  const bytes = Buffer.from(text, 'utf8');
  return Array.from(bytes).map((value, index) => ({
    index,
    byte: value,
    hex: value.toString(16).padStart(2, '0'),
    binary: value.toString(2).padStart(8, '0'),
  }));
}

function binaryHexCompile(text) {
  const decomp = decompose(text);
  const recomposed = recompose(decomp.combinedHex);
  const rows = byteRows(text);
  return {
    schema_version: 'scbe.agent_bus.binary_hex_compiler.v1',
    ok: true,
    input_sha256: crypto.createHash('sha256').update(text).digest('hex'),
    input_chars: text.length,
    utf8_bytes: rows.length,
    byte_hex: rows.map((row) => row.hex).join(''),
    byte_binary: rows.map((row) => row.binary).join(' '),
    semantic_hex: decomp.combinedHex,
    semantic_binary: decomp.combinedBinary,
    dominant: decomp.dominant,
    recomposed_closest: recomposed.closest,
    rows,
    note: 'byte_hex is lossless UTF-8 transport; semantic_hex is nearest-atom routing evidence.',
  };
}

function sentenceSplit(text) {
  return text
    .replace(/\s+/g, ' ')
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function abridge(text, maxChars) {
  const clean = text.replace(/\s+/g, ' ').trim();
  if (clean.length <= maxChars) {
    return {
      abridged: clean,
      strategy: 'identity',
      omitted_chars: 0,
    };
  }
  const sentences = sentenceSplit(clean);
  const selected = [];
  for (const sentence of sentences) {
    const candidate = [...selected, sentence].join(' ');
    if (candidate.length > maxChars) break;
    selected.push(sentence);
  }
  if (selected.length > 0) {
    const abridged = selected.join(' ');
    return {
      abridged,
      strategy: 'leading-sentences',
      omitted_chars: clean.length - abridged.length,
    };
  }
  const head = clean.slice(0, Math.max(0, maxChars - 16)).trimEnd();
  return {
    abridged: `${head} [abridged]`,
    strategy: 'hard-truncate',
    omitted_chars: clean.length - head.length,
  };
}

function clockPayload(flags, rest) {
  const now = new Date();
  const tasks = String(flags.tasks || rest.join(' ') || '')
    .split(/[,\n]/)
    .map((task) => task.trim())
    .filter(Boolean);
  const taskLimit = Math.max(1, Number(flags.limit || 5));
  const shownTasks = tasks.slice(0, taskLimit);
  return {
    schema_version: 'scbe.agent_bus.clock_ticker.v1',
    generated_at: now.toISOString(),
    iss_time: {
      label: 'ISS mission clock uses UTC/GMT for normal operations',
      utc: now.toISOString(),
    },
    local_time: {
      value: now.toLocaleString(),
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'local',
      offset_minutes: -now.getTimezoneOffset(),
    },
    system_time: {
      epoch_ms: now.getTime(),
      node_uptime_seconds: Number(process.uptime().toFixed(3)),
      platform: process.platform,
    },
    ticker: {
      count: tasks.length,
      shown: shownTasks,
      compact: shownTasks.map((task, index) => `${index + 1}. ${task}`).join(' | '),
    },
  };
}

function printJson(payload) {
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
}

function printHelp() {
  process.stdout.write(`SCBE Toolsmith

Usage:
  node packages/agent-bus/scripts/toolsmith.cjs list [--filter <substring>] [--tools-json <path>]
  node packages/agent-bus/scripts/toolsmith.cjs validate --spec '{"name":"x","description":"...","command":"node","args":["script.cjs","{task}"]}'
  node packages/agent-bus/scripts/toolsmith.cjs register --spec '{"name":"x","description":"...","command":"node","args":["script.cjs","{task}"]}'
  node packages/agent-bus/scripts/toolsmith.cjs unregister --name <tool-name>
  node packages/agent-bus/scripts/toolsmith.cjs binary-hex "text to compile"
  node packages/agent-bus/scripts/toolsmith.cjs abridge --max-chars 480 "long text"
  node packages/agent-bus/scripts/toolsmith.cjs clock --tasks "one,two,three"

Notes:
  Tool registration is validation-first and writes tools.json atomically.
  binary-hex emits both lossless UTF-8 bytes and SCBE semantic hex routing evidence.
  ISS time is reported as UTC/GMT, which is the normal ISS operating time base.
`);
}

function main() {
  const { command, positionals, flags } = parseArgs(process.argv);
  if (command === 'help' || flags.help) {
    printHelp();
    return;
  }
  if (command === 'list') {
    const filter = String(flags.filter || positionals[0] || '');
    const result = listToolSpecsFromFile(toolsJsonPath(flags));
    const filtered = filter
      ? { ...result, tools: result.tools.filter((t) => t.name.includes(filter)) }
      : result;
    printJson(filtered);
    return;
  }
  if (command === 'validate') {
    const raw = parseSpec(flags, positionals);
    const result = validateToolSpec(raw);
    printJson({
      schema_version: 'scbe.agent_bus.tool_factory.validate.v1',
      ok: result.ok,
      errors: result.errors,
      ...(result.spec && { spec: result.spec }),
    });
    process.exitCode = result.ok ? 0 : 1;
    return;
  }
  if (command === 'register') {
    const raw = parseSpec(flags, positionals);
    const validated = validateToolSpec(raw);
    if (!validated.ok) {
      printJson({
        schema_version: 'scbe.agent_bus.tool_factory.v1',
        ok: false,
        action: 'rejected',
        errors: validated.errors,
      });
      process.exitCode = 1;
      return;
    }
    const result = registerToolSpecInFile(
      validated.spec,
      toolsJsonPath(flags),
      path.resolve(String(flags['repo-root'] || repoRoot)),
      flags['skip-verify'] === true
    );
    printJson(result);
    process.exitCode = result.ok ? 0 : 1;
    return;
  }
  if (command === 'unregister') {
    const name = String(flags.name || positionals[0] || '').trim();
    if (!name) throw new Error('unregister requires --name <tool-name>');
    const result = unregisterToolSpecInFile(name, toolsJsonPath(flags));
    printJson({
      schema_version: 'scbe.agent_bus.tool_factory.unregister.v1',
      name,
      ...result,
    });
    process.exitCode = result.ok ? 0 : 1;
    return;
  }
  if (command === 'binary-hex') {
    const text = readInput(flags, positionals);
    if (!text) throw new Error('binary-hex requires text or --file');
    printJson(binaryHexCompile(text));
    return;
  }
  if (command === 'abridge') {
    const text = readInput(flags, positionals);
    if (!text) throw new Error('abridge requires text or --file');
    const maxChars = Math.max(80, Number(flags['max-chars'] || 480));
    const result = abridge(text, maxChars);
    printJson({
      schema_version: 'scbe.agent_bus.auto_abridgement.v1',
      ok: true,
      input_chars: text.length,
      max_chars: maxChars,
      output_chars: result.abridged.length,
      ...result,
    });
    return;
  }
  if (command === 'clock') {
    printJson(clockPayload(flags, positionals));
    return;
  }
  throw new Error(`unknown toolsmith command: ${command}`);
}

try {
  main();
} catch (err) {
  process.stderr.write(`${err instanceof Error ? err.message : String(err)}\n`);
  process.exitCode = 1;
}
