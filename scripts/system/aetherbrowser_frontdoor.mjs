#!/usr/bin/env node
/**
 * AetherBrowser front door.
 *
 * One bounded command for humans and agents to check the governed browser lane,
 * optionally start the persistent Chrome profile, optionally open a destination,
 * and always write a compact receipt.
 */

import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { REPO_ROOT, TARGETS, runAgent } from './aetherbrowser_mcp_server.mjs';

export const SCHEMA_VERSION = 'aetherbrowser-frontdoor-v1';
export const DEFAULT_PORT = 9333;
export const DEFAULT_TARGET = 'github';
export const DEFAULT_RECEIPT_DIR = join(REPO_ROOT, 'artifacts', 'aetherbrowser_frontdoor');

function timestamp() {
  return new Date().toISOString().replace(/[:.]/g, '-');
}

function usage() {
  return [
    'AetherBrowser front door',
    '',
    'Usage:',
    '  npm run aetherbrowser:frontdoor',
    '  npm run aetherbrowser:frontdoor -- --start --target github',
    '  npm run aetherbrowser:frontdoor -- --open --url https://example.com',
    '  npm run aetherbrowser:frontdoor -- --require-ready --json',
    '',
    'Options:',
    '  --json                 Print the full receipt as JSON.',
    '  --start                Start/reuse persistent Chrome if CDP is not already ready.',
    '  --open                 Open the target or URL after ensuring Chrome is ready.',
    '  --require-ready        Exit non-zero when Chrome/CDP is not ready.',
    '  --target NAME          Named target. Default: github.',
    '  --url URL              Explicit URL. Mutually exclusive with --target.',
    '  --port N               Chrome CDP port. Default: 9333.',
    '  --profile-name NAME    Safe profile name under ~/.aetherdesk/browser-profiles/.',
    '  --receipt-dir DIR      Receipt output directory.',
    '  --no-receipt           Do not write a receipt file.',
    '  --help                 Show this help.',
  ].join('\n');
}

export function parseFrontdoorArgs(argv = []) {
  const args = {
    json: false,
    start: false,
    open: false,
    requireReady: false,
    target: DEFAULT_TARGET,
    url: null,
    port: DEFAULT_PORT,
    profileName: null,
    receiptDir: DEFAULT_RECEIPT_DIR,
    writeReceipt: true,
    help: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--json') args.json = true;
    else if (arg === '--start') args.start = true;
    else if (arg === '--open') args.open = true;
    else if (arg === '--require-ready') args.requireReady = true;
    else if (arg === '--target') args.target = argv[++i];
    else if (arg === '--url') args.url = argv[++i];
    else if (arg === '--port') args.port = Number(argv[++i]);
    else if (arg === '--profile-name') args.profileName = argv[++i];
    else if (arg === '--receipt-dir') args.receiptDir = resolve(argv[++i]);
    else if (arg === '--no-receipt') args.writeReceipt = false;
    else if (arg === '--help' || arg === '-h') args.help = true;
    else throw new Error(`unknown argument: ${arg}`);
  }

  if (!Number.isInteger(args.port) || args.port < 1 || args.port > 65535) {
    throw new Error(`invalid port: ${args.port}`);
  }
  if (args.url && argv.includes('--target')) {
    throw new Error('Provide either --url or --target, not both.');
  }
  if (args.url && !/^(https?:\/\/|file:\/\/|about:|chrome:\/\/)/i.test(args.url)) {
    throw new Error('URL must start with http://, https://, file://, about:, or chrome://');
  }
  if (!args.url && !TARGETS[args.target]) {
    throw new Error(`unknown target '${args.target}'. Known targets: ${Object.keys(TARGETS).join(', ')}`);
  }
  if (args.profileName && !/^[A-Za-z0-9_.-]{1,80}$/.test(args.profileName)) {
    throw new Error('--profile-name may contain only letters, numbers, underscore, dot, and dash.');
  }

  return args;
}

function agentInput(args) {
  const input = { port: args.port };
  if (args.profileName) input.profile_name = args.profileName;
  if (args.url) input.url = args.url;
  else input.target = args.target;
  return input;
}

function callAgent(command, input, options) {
  return options.runAgentImpl(command, input);
}

function shortAgentResult(result) {
  return {
    ok: Boolean(result?.ok),
    command: result?.command || null,
    exit_code: result?.exit_code ?? null,
    stdout: result?.stdout ?? null,
    stderr: result?.stderr || null,
    error: result?.error || null,
  };
}

function receiptPath(receiptDir) {
  return join(receiptDir, `frontdoor_${timestamp()}.json`);
}

function writeReceiptFile(receipt, options) {
  if (!receipt.write_receipt) return null;
  options.mkdirImpl(receipt.receipt_dir, { recursive: true });
  const path = receiptPath(receipt.receipt_dir);
  const payload = { ...receipt, receipt_path: path };
  options.writeFileImpl(path, JSON.stringify(payload, null, 2), 'utf8');
  return path;
}

function statusReady(statusResult) {
  return Boolean(statusResult?.ok && statusResult?.stdout?.ok);
}

export async function runFrontdoor(argv = [], options = {}) {
  const args = parseFrontdoorArgs(argv);
  const opts = {
    runAgentImpl: options.runAgentImpl || runAgent,
    mkdirImpl: options.mkdirImpl || mkdirSync,
    writeFileImpl: options.writeFileImpl || writeFileSync,
  };

  if (args.help) {
    return {
      ok: true,
      help: usage(),
      exitCode: 0,
      printMode: 'help',
    };
  }

  const startedAt = new Date().toISOString();
  const receipt = {
    ok: true,
    ready: false,
    schema_version: SCHEMA_VERSION,
    repo_root: REPO_ROOT,
    started_at: startedAt,
    finished_at: null,
    mode: args.open ? 'open' : args.start ? 'start' : 'status',
    target: args.url ? null : args.target,
    url: args.url,
    port: args.port,
    profile_name: args.profileName,
    receipt_dir: args.receiptDir,
    receipt_path: null,
    write_receipt: args.writeReceipt,
    commands: {
      doctor: 'npm run aetherbrowser:mcp:probe',
      status: 'npm run aetherbrowser:status -- --json',
      frontdoor_status: 'npm run aetherbrowser:frontdoor',
      frontdoor_start: `npm run aetherbrowser:frontdoor -- --start --target ${args.target || DEFAULT_TARGET}`,
      frontdoor_open: args.url
        ? `npm run aetherbrowser:frontdoor -- --open --url ${args.url}`
        : `npm run aetherbrowser:frontdoor -- --open --target ${args.target || DEFAULT_TARGET}`,
    },
    doctor: null,
    status_before: null,
    start_result: null,
    open_result: null,
    status_after: null,
    next_action: null,
  };

  const doctor = callAgent('doctor', {}, opts);
  receipt.doctor = shortAgentResult(doctor);

  const statusBefore = callAgent('status', { port: args.port, profile_name: args.profileName || undefined }, opts);
  receipt.status_before = shortAgentResult(statusBefore);

  const wasRunning = statusReady(statusBefore);
  let running = wasRunning;

  if ((args.start || args.open) && !running) {
    const startResult = callAgent('start', agentInput(args), opts);
    receipt.start_result = shortAgentResult(startResult);
    running = Boolean(startResult?.ok);
  } else if (args.start && running) {
    receipt.start_result = {
      ok: true,
      command: 'start',
      exit_code: 0,
      stdout: { ok: true, reused: true, reason: 'already-running' },
      stderr: null,
      error: null,
    };
  }

  if (args.open && running) {
    const openResult = callAgent('open', agentInput(args), opts);
    receipt.open_result = shortAgentResult(openResult);
  }

  const shouldRefreshStatus = args.start || args.open || running;
  const statusAfter = shouldRefreshStatus
    ? callAgent('status', { port: args.port, profile_name: args.profileName || undefined }, opts)
    : statusBefore;
  receipt.status_after = shortAgentResult(statusAfter);
  receipt.ready = statusReady(statusAfter);

  const doctorOk = Boolean(doctor?.ok && doctor?.stdout?.ok);
  const startNeeded = (args.start || args.open) && !wasRunning;
  const startOk = (!args.start && !startNeeded) || Boolean(receipt.start_result?.ok);
  const openOk = !args.open || Boolean(receipt.open_result?.ok);
  receipt.ok = doctorOk && startOk && openOk && (!args.requireReady || receipt.ready);
  if (!doctorOk) {
    receipt.next_action = 'Run npm run aetherbrowser:mcp:probe and inspect the doctor failure.';
  } else if (!startOk) {
    receipt.next_action = 'AetherBrowser start failed; inspect start_result.stderr and rerun the front door.';
  } else if (!openOk) {
    receipt.next_action = 'AetherBrowser open failed; inspect open_result.stderr and retry with a named target or explicit URL.';
  } else if (!receipt.ready) {
    receipt.next_action = `Run npm run aetherbrowser:frontdoor -- --start --target ${args.target || DEFAULT_TARGET}`;
  } else if (!args.open) {
    receipt.next_action = args.url
      ? `Run npm run aetherbrowser:frontdoor -- --open --url ${args.url}`
      : `Run npm run aetherbrowser:frontdoor -- --open --target ${args.target || DEFAULT_TARGET}`;
  } else {
    receipt.next_action = 'Ready. Use MCP tools or npm run aetherbrowser:status -- --json for current tabs.';
  }

  receipt.finished_at = new Date().toISOString();
  const path = writeReceiptFile(receipt, opts);
  if (path) receipt.receipt_path = path;

  return {
    ...receipt,
    exitCode: receipt.ok ? 0 : 1,
    printMode: args.json ? 'json' : 'human',
  };
}

export function formatHumanSummary(receipt) {
  if (receipt.help) return receipt.help;
  const doctorStatus = receipt.doctor?.ok && receipt.doctor?.stdout?.ok ? 'ok' : 'failed';
  const cdpStatus = receipt.ready ? 'ready' : 'not running';
  const tabs = receipt.status_after?.stdout?.tabs;
  const tabCount = Array.isArray(tabs) ? tabs.length : 0;
  const lines = [
    'AetherBrowser front door',
    `doctor: ${doctorStatus}`,
    `cdp: ${cdpStatus} on port ${receipt.port}`,
    `tabs: ${tabCount}`,
  ];
  if (receipt.start_result) {
    lines.push(`start: ${receipt.start_result.ok ? 'ok' : 'failed'}`);
  }
  if (receipt.open_result) {
    lines.push(`open: ${receipt.open_result.ok ? 'ok' : 'failed'}`);
  }
  if (receipt.receipt_path) {
    lines.push(`receipt: ${receipt.receipt_path}`);
  }
  if (receipt.next_action) {
    lines.push(`next: ${receipt.next_action}`);
  }
  return lines.join('\n');
}

async function main(argv = process.argv.slice(2)) {
  const result = await runFrontdoor(argv);
  if (result.printMode === 'json') {
    console.log(JSON.stringify(result, null, 2));
  } else {
    console.log(formatHumanSummary(result));
  }
  return result.exitCode;
}

if (fileURLToPath(import.meta.url) === resolve(process.argv[1] || '')) {
  main().then((code) => {
    process.exitCode = code;
  }).catch((error) => {
    console.error(error instanceof Error ? error.stack : String(error));
    process.exitCode = 1;
  });
}
