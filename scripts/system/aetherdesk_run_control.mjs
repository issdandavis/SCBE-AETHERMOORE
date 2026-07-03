#!/usr/bin/env node
/**
 * AetherDesk Run Control
 *
 * One control surface for the pieces that kept drifting apart:
 * browser state, Colab receipts, queued compute jobs, and done/pending verdicts.
 *
 * This does not own account secrets. It uses the persistent browser profile and
 * local artifact receipts as the source of truth.
 */

import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync, appendFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const RUN_DIR = join(ROOT, 'artifacts', 'aetherdesk_runs');
const COLAB_DIR = join(ROOT, 'artifacts', 'colab');
const BROWSER_DIR = join(ROOT, 'artifacts', 'aetherdesk_browser');
const QUEUE_FILE = join(RUN_DIR, 'queue.jsonl');
const RUN_LOG = join(RUN_DIR, 'run_log.jsonl');
const LAST_STATUS = join(RUN_DIR, 'last_status.json');
const BROWSER_AGENT = join(ROOT, 'scripts', 'system', 'aether_browser_agent.mjs');
const FAST_CELL = join(ROOT, 'artifacts', 'colab', 'scbe_fast_full_cell_one_line.py');
const RESCUE_CELL = join(ROOT, 'artifacts', 'colab', 'scbe_colab_rescue_probe.py');
const TRAIN_NOTEBOOK_URL = 'https://colab.research.google.com/gist/issdandavis/c2f22a0b274793d5db9805d216696ad4/train_qlora.ipynb';

function usage() {
  return [
    'AetherDesk Run Control',
    '',
    'Commands:',
    '  doctor',
    '  status [--json]',
    '  inventory [--json]',
    '  queue-list [--json]',
    '  queue-add-colab-rescue [--timeout-ms N]',
    '  queue-add-colab-fast [--watch-for TEXT] [--timeout-ms N]',
    '  queue-add-monitor --watch-for TEXT [--match TEXT] [--timeout-ms N]',
    '  run-next',
    '  monitor-colab --watch-for TEXT [--timeout-ms N]',
    '',
    'Default fast training marker:',
    '  SCBE_FAST_FULL_DONE'
  ].join('\n');
}

function parseArgs(argv) {
  const args = {
    command: argv[0] || 'help',
    watchFor: 'SCBE_FAST_FULL_DONE',
    match: 'train_qlora',
    timeoutMs: 30 * 60 * 1000
  };
  for (let i = 1; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--json') args.json = true;
    else if (arg === '--watch-for') args.watchFor = argv[++i];
    else if (arg === '--match') args.match = argv[++i];
    else if (arg === '--timeout-ms') args.timeoutMs = Number(argv[++i]);
    else throw new Error(`unknown argument: ${arg}`);
  }
  return args;
}

function ensureRunDir() {
  mkdirSync(RUN_DIR, { recursive: true });
}

function now() {
  return new Date().toISOString();
}

function safeJson(file) {
  try {
    return JSON.parse(readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
  } catch {
    return null;
  }
}

function listFiles(dir, predicate = () => true) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .map((name) => join(dir, name))
    .filter((file) => {
      try {
        return statSync(file).isFile() && predicate(file);
      } catch {
        return false;
      }
    })
    .sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs);
}

function listFilesRecursive(dir, predicate = () => true, limit = 5000) {
  const out = [];
  const stack = [dir];
  while (stack.length && out.length < limit) {
    const current = stack.pop();
    if (!current || !existsSync(current)) continue;
    for (const name of readdirSync(current)) {
      const file = join(current, name);
      let stat;
      try {
        stat = statSync(file);
      } catch {
        continue;
      }
      if (stat.isDirectory()) {
        if (name === 'node_modules' || name === '.git' || name === '__pycache__') continue;
        stack.push(file);
      } else if (stat.isFile() && predicate(file)) {
        out.push(file);
      }
    }
  }
  return out.sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs);
}

function runNode(args, options = {}) {
  return spawnSync(process.execPath, args, {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: options.stdio || 'pipe',
    timeout: options.timeoutMs || undefined
  });
}

function browserStatus() {
  const child = runNode([BROWSER_AGENT, 'status', '--json'], { timeoutMs: 15000 });
  const stdout = child.stdout || '';
  const parsed = safeParseFirstJson(stdout);
  if (child.status === 0 && parsed) {
    const pageTabs = (parsed.tabs || []).filter((tab) => tab.type === 'page');
    return {
      ok: true,
      port: parsed.port,
      browser: parsed.browser,
      pageTabs,
      colabTabs: pageTabs.filter((tab) => tab.url.includes('colab.research.google.com')),
      raw: parsed
    };
  }
  return {
    ok: false,
    exitCode: child.status,
    stderr: (child.stderr || '').slice(-4000),
    stdout: stdout.slice(-4000)
  };
}

function safeParseFirstJson(text) {
  const start = text.indexOf('{');
  const end = text.lastIndexOf('}');
  if (start < 0 || end < start) return null;
  try {
    return JSON.parse(text.slice(start, end + 1));
  } catch {
    return null;
  }
}

function latestColabReceipt() {
  const files = listFiles(COLAB_DIR, (file) => file.toLowerCase().endsWith('.json'));
  const receipts = [];
  for (const file of files) {
    const json = safeJson(file);
    if (!json) continue;
    if (json.command === 'run-cell' || json.status || json.result) {
      receipts.push(classifyReceipt(file, json));
    }
  }
  receipts.sort((a, b) => {
    if (b.priority !== a.priority) return b.priority - a.priority;
    return new Date(b.mtime).getTime() - new Date(a.mtime).getTime();
  });
  if (receipts.length) return receipts[0];
  return { ok: false, status: 'NO_RECEIPT', file: null };
}

function classifyReceipt(file, json) {
  const text = JSON.stringify(json);
  const notebookStatus = json.notebookState && json.notebookState.status;
  const progress = json.progress || (json.notebookState && json.notebookState.progress) || null;
  const receiptStatus = json.status || (json.result && json.result.status) || null;
  const matchedReceipt = receiptStatus === 'WATCH_MATCH' || json.ok === true;
  const done = text.includes('SCBE_FAST_FULL_DONE');
  const rescue = text.includes('SCBE_COLAB_RESCUE_DONE');
  const pushed = text.includes('SCBE_FAST_FULL_PUSHED') || text.includes('pushed adapter');
  const speed = text.includes('SCBE_FAST_FULL_SPEED');
  const oom = /CUDA out of memory|OutOfMemoryError/i.test(text);
  const interrupted = /KeyboardInterrupt|interrupted by user/i.test(text) || notebookStatus === 'INTERRUPTED';
  const progressSeen = notebookStatus === 'TRAINING_PROGRESS_SEEN' || Boolean(progress) || speed;
  const timeout = json.status === 'TIMEOUT' || (json.result && json.result.status === 'TIMEOUT');
  let verdict = 'UNKNOWN';
  if (matchedReceipt && done && pushed) verdict = 'DONE_AND_PUSHED';
  else if (matchedReceipt && done) verdict = 'DONE_LOCAL';
  else if (notebookStatus === 'TRAINING_PUSHED') verdict = 'DONE_AND_PUSHED';
  else if (notebookStatus === 'TRAINING_DONE') verdict = 'DONE_LOCAL';
  else if (matchedReceipt && rescue) verdict = 'COLAB_RESCUE_READY';
  else if (progressSeen) verdict = 'RUNNING_OR_PROGRESS_SEEN';
  else if (oom) verdict = 'OOM_FAILED';
  else if (interrupted) verdict = 'INTERRUPTED';
  else if (notebookStatus === 'RUNTIME_CONNECTING') verdict = 'RUNTIME_CONNECTING';
  else if (timeout) verdict = 'TIMEOUT_NO_DONE_MARKER';
  else if (json.ok) verdict = 'OK_NON_TRAINING_MARKER';
  else verdict = json.status || 'FAILED_OR_INCOMPLETE';
  const priority = {
    DONE_AND_PUSHED: 100,
    DONE_LOCAL: 95,
    RUNNING_OR_PROGRESS_SEEN: 80,
    COLAB_RESCUE_READY: 60,
    RUNTIME_CONNECTING: 45,
    OK_NON_TRAINING_MARKER: 40,
    TIMEOUT_NO_DONE_MARKER: 20,
    INTERRUPTED: 15,
    OOM_FAILED: 10,
    FAILED_OR_INCOMPLETE: 5,
    UNKNOWN: 0
  }[verdict] ?? 0;
  return {
    ok: verdict === 'DONE_AND_PUSHED' || verdict === 'DONE_LOCAL' || verdict === 'RUNNING_OR_PROGRESS_SEEN' || verdict === 'COLAB_RESCUE_READY',
    verdict,
    priority,
    file,
    mtime: statSync(file).mtime.toISOString(),
    receiptOk: Boolean(json.ok),
    status: receiptStatus,
    notebookStatus: notebookStatus || null,
    progress,
    codeFile: json.codeFile || null,
    screenshot: json.screenshot || null,
    markers: { done, rescue, pushed, speed, oom, interrupted, progressSeen, timeout }
  };
}

function inventory() {
  const scripts = listFilesRecursive(join(ROOT, 'scripts'), (file) => /\.(py|ps1|js|mjs|ipynb)$/i.test(file));
  const selected = scripts.filter((file) => /hf|hugging|kaggle|colab|training|model/i.test(file));
  const packageJson = safeJson(join(ROOT, 'package.json')) || {};
  let packageScripts = packageJson.scripts || {};
  if (!Object.keys(packageScripts).length) {
    const pkg = spawnSync('npm', ['pkg', 'get', 'scripts', '--json'], {
      cwd: ROOT,
      encoding: 'utf8',
      stdio: 'pipe'
    });
    const parsed = safeParseFirstJson(pkg.stdout || '');
    packageScripts = parsed || {};
  }
  const trainingScripts = Object.keys(packageScripts).filter((name) => /training|hf|kaggle|colab|model/i.test(name));
  return {
    ok: true,
    repo: ROOT,
    counts: {
      matchedLocalScripts: selected.length,
      packageTrainingScripts: trainingScripts.length,
      colabArtifacts: listFiles(COLAB_DIR).length,
      browserArtifacts: listFiles(BROWSER_DIR).length
    },
    packageTrainingScripts: trainingScripts,
    topLocalScripts: selected.slice(0, 80).map((file) => file.replace(`${ROOT}\\`, ''))
  };
}

function readQueue() {
  if (!existsSync(QUEUE_FILE)) return [];
  return readFileSync(QUEUE_FILE, 'utf8')
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return { id: 'BROKEN', kind: 'broken-line', raw: line };
      }
    });
}

function writeQueue(items) {
  ensureRunDir();
  writeFileSync(QUEUE_FILE, items.map((item) => JSON.stringify(item)).join('\n') + (items.length ? '\n' : ''), 'utf8');
}

function addQueue(item) {
  const items = readQueue();
  items.push(item);
  writeQueue(items);
  return item;
}

function makeId(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

function queueAddColabFast(args) {
  if (!existsSync(FAST_CELL)) {
    throw new Error(`fast Colab cell not found: ${FAST_CELL}`);
  }
  return addQueue({
    id: makeId('colab-fast'),
    kind: 'colab-run',
    createdAt: now(),
    url: TRAIN_NOTEBOOK_URL,
    codeFile: FAST_CELL,
    watchFor: args.watchFor || 'SCBE_FAST_FULL_DONE',
    timeoutMs: args.timeoutMs,
    waitRuntimeMs: 10 * 60 * 1000
  });
}

function queueAddColabRescue(args) {
  if (!existsSync(RESCUE_CELL)) {
    throw new Error(`Colab rescue cell not found: ${RESCUE_CELL}`);
  }
  return addQueue({
    id: makeId('colab-rescue'),
    kind: 'colab-run',
    createdAt: now(),
    url: TRAIN_NOTEBOOK_URL,
    codeFile: RESCUE_CELL,
    watchFor: 'SCBE_COLAB_RESCUE_DONE',
    timeoutMs: Math.min(args.timeoutMs || 600000, 30 * 60 * 1000),
    waitRuntimeMs: 2 * 60 * 1000
  });
}

function queueAddMonitor(args) {
  if (!args.watchFor) throw new Error('queue-add-monitor requires --watch-for');
  return addQueue({
    id: makeId('monitor'),
    kind: 'monitor',
    createdAt: now(),
    match: args.match || 'train_qlora',
    watchFor: args.watchFor,
    timeoutMs: args.timeoutMs
  });
}

function appendRunLog(entry) {
  ensureRunDir();
  appendFileSync(RUN_LOG, JSON.stringify(entry) + '\n', 'utf8');
}

function runItem(item) {
  const startedAt = now();
  let child;
  if (item.kind === 'colab-run') {
    child = runNode([
      BROWSER_AGENT,
      'colab-run',
      '--url',
      item.url,
      '--code-file',
      item.codeFile,
      '--watch-for',
      item.watchFor,
      '--timeout-ms',
      String(item.timeoutMs),
      '--wait-runtime-ms',
      String(item.waitRuntimeMs || 10 * 60 * 1000)
    ], { timeoutMs: item.timeoutMs + (item.waitRuntimeMs || 0) + 120000 });
  } else if (item.kind === 'monitor') {
    child = runNode([
      BROWSER_AGENT,
      'monitor',
      '--match',
      item.match,
      '--watch-for',
      item.watchFor,
      '--timeout-ms',
      String(item.timeoutMs)
    ], { timeoutMs: item.timeoutMs + 120000 });
  } else {
    throw new Error(`unknown queue item kind: ${item.kind}`);
  }
  const entry = {
    id: item.id,
    kind: item.kind,
    startedAt,
    finishedAt: now(),
    exitCode: child.status,
    ok: child.status === 0,
    stdoutTail: (child.stdout || '').slice(-12000),
    stderrTail: (child.stderr || '').slice(-8000)
  };
  appendRunLog(entry);
  return entry;
}

function runNext() {
  const items = readQueue();
  if (!items.length) return { ok: false, status: 'QUEUE_EMPTY' };
  const [item, ...rest] = items;
  writeQueue(rest);
  const result = runItem(item);
  return { ok: result.ok, item, result, remaining: rest.length };
}

function status() {
  const browser = browserStatus();
  const colab = latestColabReceipt();
  const queue = readQueue();
  const inv = inventory();
  const payload = {
    ok: true,
    checkedAt: now(),
    productVerdict: {
      browserControl: browser.ok ? 'WORKING' : 'BROKEN',
      colabVisibility: browser.ok && browser.colabTabs && browser.colabTabs.length ? 'WORKING' : 'NOT_VISIBLE',
      trainingCompletion: colab.verdict || 'UNKNOWN',
      trainingProgress: colab.progress || null,
      unifiedQueue: 'WORKING'
    },
    browser,
    colab,
    queue: {
      length: queue.length,
      next: queue[0] || null
    },
    inventory: {
      matchedLocalScripts: inv.counts.matchedLocalScripts,
      packageTrainingScripts: inv.counts.packageTrainingScripts,
      colabArtifacts: inv.counts.colabArtifacts,
      browserArtifacts: inv.counts.browserArtifacts
    }
  };
  ensureRunDir();
  writeFileSync(LAST_STATUS, JSON.stringify(payload, null, 2), 'utf8');
  return payload;
}

function monitorColab(args) {
  const child = runNode([
    BROWSER_AGENT,
    'monitor',
    '--match',
    args.match || 'train_qlora',
    '--watch-for',
    args.watchFor,
    '--timeout-ms',
    String(args.timeoutMs)
  ], { timeoutMs: args.timeoutMs + 120000 });
  const entry = {
    kind: 'monitor-colab',
    startedAt: now(),
    exitCode: child.status,
    ok: child.status === 0,
    stdoutTail: (child.stdout || '').slice(-12000),
    stderrTail: (child.stderr || '').slice(-8000)
  };
  appendRunLog(entry);
  return entry;
}

async function main(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  if (args.command === 'help' || args.command === '-h' || args.command === '--help') {
    console.log(usage());
    return 0;
  }
  if (args.command === 'doctor') {
    const payload = {
      ok: true,
      repo: ROOT,
      runDir: RUN_DIR,
      queueFile: QUEUE_FILE,
      browserAgent: existsSync(BROWSER_AGENT),
      fastCell: existsSync(FAST_CELL),
      rescueCell: existsSync(RESCUE_CELL),
      colabDir: existsSync(COLAB_DIR),
      browserDir: existsSync(BROWSER_DIR)
    };
    ensureRunDir();
    console.log(JSON.stringify(payload, null, 2));
    return payload.ok ? 0 : 1;
  }
  if (args.command === 'status') {
    const payload = status();
    console.log(JSON.stringify(payload, null, 2));
    return payload.ok ? 0 : 1;
  }
  if (args.command === 'inventory') {
    const payload = inventory();
    console.log(JSON.stringify(payload, null, 2));
    return 0;
  }
  if (args.command === 'queue-list') {
    const payload = { ok: true, queue: readQueue() };
    console.log(JSON.stringify(payload, null, 2));
    return 0;
  }
  if (args.command === 'queue-add-colab-fast') {
    const item = queueAddColabFast(args);
    console.log(JSON.stringify({ ok: true, item }, null, 2));
    return 0;
  }
  if (args.command === 'queue-add-colab-rescue') {
    const item = queueAddColabRescue(args);
    console.log(JSON.stringify({ ok: true, item }, null, 2));
    return 0;
  }
  if (args.command === 'queue-add-monitor') {
    const item = queueAddMonitor(args);
    console.log(JSON.stringify({ ok: true, item }, null, 2));
    return 0;
  }
  if (args.command === 'run-next') {
    const payload = runNext();
    console.log(JSON.stringify(payload, null, 2));
    return payload.ok ? 0 : 1;
  }
  if (args.command === 'monitor-colab') {
    const payload = monitorColab(args);
    console.log(JSON.stringify(payload, null, 2));
    return payload.ok ? 0 : 3;
  }
  throw new Error(`unknown command: ${args.command}`);
}

main().then((code) => {
  process.exitCode = code;
}).catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exitCode = 1;
});
