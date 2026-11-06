'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { Worker } = require('node:worker_threads');
const {
  ROUTE_PRESETS,
  runGuidedEvidenceRoute,
  searchEvidencePackets,
  searchWorkspaceEvidence,
  verifyEvidencePacket,
} = require('./guided-evidence');
const { verifyReceiptLedger } = require('./session-store');

const DEFAULT_TOOL_NAMES = Object.freeze([
  'read_file',
  'list_files',
  'search_text',
  'guided_evidence',
  'search_evidence',
  'verify_evidence',
  'verify_receipts',
  'write_file',
  'edit_file',
  'create_directory',
  'run_command',
  'git_status',
  'git_diff',
  'workspace_info',
]);

const SKIP_DIRECTORIES = new Set(['.git', 'node_modules', '.next', '.cache']);
const MAX_FILE_BYTES = 1024 * 1024;
const MAX_OUTPUT_CHARS = 40_000;
const MAX_SEARCH_REGEX_CHARS = 256;
const MAX_REGEX_LINE_CHARS = 20_000;
const SEARCH_TIME_BUDGET_MS = 2_000;

function isInside(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function nearestExistingParent(target) {
  let current = target;
  while (!fs.existsSync(current)) {
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return current;
}

function resolveWorkspacePath(workspaceRoot, inputPath = '.', options = {}) {
  const root = fs.realpathSync(path.resolve(workspaceRoot));
  const requested = path.resolve(root, String(inputPath || '.'));
  if (!isInside(root, requested)) {
    throw new Error(`path is outside the workspace: ${inputPath}`);
  }
  const existingParent = nearestExistingParent(requested);
  const realParent = fs.realpathSync(existingParent);
  if (!isInside(root, realParent)) {
    throw new Error(`path resolves outside the workspace through a link: ${inputPath}`);
  }
  if (fs.existsSync(requested)) {
    const realTarget = fs.realpathSync(requested);
    if (!isInside(root, realTarget)) {
      throw new Error(`path resolves outside the workspace through a link: ${inputPath}`);
    }
  } else if (options.mustExist) {
    throw new Error(`path does not exist: ${inputPath}`);
  }
  return requested;
}

function relativePath(root, target) {
  const value = path.relative(root, target);
  return value || '.';
}

function boundedText(value, limit = MAX_OUTPUT_CHARS) {
  const text = String(value || '');
  if (text.length <= limit) return { text, truncated: false };
  return { text: `${text.slice(0, limit)}\n...[truncated]`, truncated: true };
}

function signalProcessGroup(child, signal) {
  if (!child || !Number.isSafeInteger(child.pid) || child.pid <= 0) return false;
  try {
    process.kill(-child.pid, signal);
    return true;
  } catch (_groupError) {
    try {
      child.kill(signal);
      return true;
    } catch (_childError) {
      return false;
    }
  }
}

function terminateProcessTree(child, options = {}) {
  if (!child || !Number.isSafeInteger(child.pid) || child.pid <= 0) return Promise.resolve();

  if (process.platform === 'win32') {
    return new Promise((resolve) => {
      const systemRoot = process.env.SystemRoot || 'C:\\Windows';
      const taskkill = path.join(systemRoot, 'System32', 'taskkill.exe');
      let done = false;
      let watchdog = null;
      const finish = () => {
        if (done) return;
        done = true;
        if (watchdog) clearTimeout(watchdog);
        resolve();
      };
      const fallback = () => {
        try {
          child.kill('SIGKILL');
        } catch (_error) {
          // The process may already have exited.
        }
      };
      let killer;
      try {
        // PID is passed to a fixed executable as data. Never interpolate it
        // into a shell command: timeout cleanup must not be an injection surface.
        killer = spawn(taskkill, ['/PID', String(child.pid), '/T', '/F'], {
          shell: false,
          windowsHide: true,
          stdio: 'ignore',
        });
      } catch (_error) {
        fallback();
        finish();
        return;
      }
      killer.once('error', () => {
        fallback();
        finish();
      });
      killer.once('close', (code) => {
        if (code !== 0) fallback();
        finish();
      });
      watchdog = setTimeout(() => {
        try {
          killer.kill('SIGKILL');
        } catch (_error) {
          // Ignore a cleanup race with taskkill exiting.
        }
        fallback();
        finish();
      }, 3_000);
      watchdog.unref?.();
    });
  }

  signalProcessGroup(child, 'SIGTERM');
  return new Promise((resolve) => {
    const graceMs = Math.min(5_000, Math.max(0, Number(options.graceMs ?? 750)));
    const forceTimer = setTimeout(() => {
      signalProcessGroup(child, 'SIGKILL');
      resolve();
    }, graceMs);
    forceTimer.unref?.();
  });
}

function runProcess(command, args, options = {}) {
  return new Promise((resolve) => {
    const started = Date.now();
    let stdout = '';
    let stderr = '';
    let settled = false;
    let timeoutTriggered = false;
    let timer = null;
    let child;
    try {
      child = spawn(command, args, {
        cwd: options.cwd,
        shell: options.shell === true,
        detached: process.platform !== 'win32',
        windowsHide: true,
        env: options.env || process.env,
        stdio: ['ignore', 'pipe', 'pipe'],
      });
    } catch (error) {
      resolve({
        ok: false,
        exitCode: null,
        stdout: '',
        stderr: error.message,
        durationMs: Date.now() - started,
      });
      return;
    }

    const finish = (payload) => {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
      const out = boundedText(stdout);
      const err = boundedText(stderr);
      resolve({
        ...payload,
        stdout: out.text,
        stderr: err.text,
        truncated: out.truncated || err.truncated,
        durationMs: Date.now() - started,
      });
    };

    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', (chunk) => {
      if (stdout.length < MAX_OUTPUT_CHARS * 2) stdout += chunk;
    });
    child.stderr.on('data', (chunk) => {
      if (stderr.length < MAX_OUTPUT_CHARS * 2) stderr += chunk;
    });
    child.on('error', (error) => {
      stderr += error.message;
      if (timeoutTriggered) return;
      finish({ ok: false, exitCode: null });
    });
    child.on('close', (code, signal) => {
      if (timeoutTriggered) return;
      finish({ ok: code === 0, exitCode: code, signal: signal || null });
    });

    const timeoutMs = Number(options.timeoutMs || 120_000);
    timer = setTimeout(async () => {
      timeoutTriggered = true;
      stderr += `\ncommand timed out after ${timeoutMs}ms`;
      await terminateProcessTree(child);
      finish({ ok: false, exitCode: null, timedOut: true });
    }, timeoutMs);
    timer.unref?.();
  });
}

function assertSafeSearchRegex(value) {
  const source = String(value);
  if (source.length > MAX_SEARCH_REGEX_CHARS) {
    throw new Error(`unsafe regex: patterns are limited to ${MAX_SEARCH_REGEX_CHARS} characters`);
  }
  if (/\\(?:[1-9]|k<)/.test(source)) {
    throw new Error('unsafe regex: backreferences are not supported');
  }
  if (/\(\?(?!:)/.test(source)) {
    throw new Error('unsafe regex: lookarounds, named groups, and inline modifiers are not supported');
  }

  const groups = [];
  let inClass = false;
  let escaped = false;
  let lastAtom = null;
  let unboundedQuantifiers = 0;
  let quantifiedAtoms = 0;
  let quantifiedWildcards = 0;

  const markQuantifier = (unbounded) => {
    quantifiedAtoms += 1;
    if (unbounded) unboundedQuantifiers += 1;
    if (lastAtom?.kind === 'group' && (lastAtom.hasQuantifier || lastAtom.hasAlternation)) {
      throw new Error('unsafe regex: quantified groups cannot contain alternation or another quantifier');
    }
    if (lastAtom?.wildcard) quantifiedWildcards += 1;
    if (groups.length) groups[groups.length - 1].hasQuantifier = true;
    lastAtom = { kind: 'quantified', wildcard: lastAtom?.wildcard === true };
  };

  for (let index = 0; index < source.length; index += 1) {
    const character = source[index];
    if (escaped) {
      escaped = false;
      lastAtom = { kind: 'atom', wildcard: false };
      continue;
    }
    if (character === '\\') {
      escaped = true;
      continue;
    }
    if (inClass) {
      if (character === ']') {
        inClass = false;
        lastAtom = { kind: 'atom', wildcard: false };
      }
      continue;
    }
    if (character === '[') {
      inClass = true;
      continue;
    }
    if (character === '(') {
      groups.push({ hasAlternation: false, hasQuantifier: false });
      lastAtom = null;
      continue;
    }
    if (character === ')') {
      const group = groups.pop();
      if (group) {
        if (groups.length) {
          groups[groups.length - 1].hasAlternation ||= group.hasAlternation;
          groups[groups.length - 1].hasQuantifier ||= group.hasQuantifier;
        }
        lastAtom = { kind: 'group', ...group, wildcard: false };
      }
      continue;
    }
    if (character === '|') {
      if (groups.length) groups[groups.length - 1].hasAlternation = true;
      lastAtom = null;
      continue;
    }
    if (character === '*' || character === '+') {
      markQuantifier(true);
      continue;
    }
    if (character === '?') {
      if (source[index - 1] === '(' && source[index + 1] === ':') continue;
      markQuantifier(false);
      continue;
    }
    if (character === '{') {
      const quantifier = source.slice(index).match(/^\{(\d+)(,(\d*)?)?\}/);
      if (quantifier) {
        const minimum = Number(quantifier[1]);
        const maximum = quantifier[2] ? (quantifier[3] === '' ? Infinity : Number(quantifier[3])) : minimum;
        if (minimum > 1_000 || maximum > 1_000) {
          throw new Error('unsafe regex: repetition bounds cannot exceed 1000');
        }
        markQuantifier(maximum === Infinity);
        index += quantifier[0].length - 1;
        continue;
      }
    }
    if (character === '^' || character === '$') {
      lastAtom = null;
      continue;
    }
    lastAtom = { kind: 'atom', wildcard: character === '.' };
  }

  if (unboundedQuantifiers > 3 || quantifiedAtoms > 16 || quantifiedWildcards > 1) {
    throw new Error('unsafe regex: pattern contains too many potentially ambiguous quantifiers');
  }
  return source;
}

const REGEX_SEARCH_WORKER_SOURCE = String.raw`
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { parentPort, workerData } = require('node:worker_threads');

const expression = new RegExp(workerData.query, workerData.caseSensitive ? '' : 'i');
const matches = [];
let scanned = 0;
let skippedLongLines = 0;

for (const absolute of workerData.files) {
  if (matches.length >= workerData.limit) break;
  let stat;
  try {
    stat = fs.statSync(absolute);
  } catch (_error) {
    continue;
  }
  if (!stat.isFile() || stat.size > workerData.maxFileBytes) continue;
  let text;
  try {
    text = fs.readFileSync(absolute, 'utf8');
  } catch (_error) {
    continue;
  }
  if (text.includes('\0')) continue;
  scanned += 1;
  const lines = text.split(/\r?\n/);
  for (let index = 0; index < lines.length && matches.length < workerData.limit; index += 1) {
    const line = lines[index];
    if (line.length > workerData.maxLineChars) {
      skippedLongLines += 1;
      continue;
    }
    if (expression.test(line)) {
      matches.push({
        path: path.relative(workerData.root, absolute) || '.',
        line: index + 1,
        text: line.slice(0, 500),
      });
    }
  }
}

parentPort.postMessage({ scanned, skippedLongLines, matches });
`;

function searchRegexInWorker(options) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const worker = new Worker(REGEX_SEARCH_WORKER_SOURCE, {
      eval: true,
      workerData: {
        files: options.files,
        root: options.root,
        query: options.query,
        caseSensitive: options.caseSensitive,
        limit: options.limit,
        maxFileBytes: MAX_FILE_BYTES,
        maxLineChars: MAX_REGEX_LINE_CHARS,
      },
    });
    const finish = (callback) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      callback();
    };
    worker.once('message', (result) => finish(() => resolve({ ...result, timeLimited: false })));
    worker.once('error', (error) => finish(() => reject(error)));
    worker.once('exit', (code) => {
      if (code !== 0) finish(() => reject(new Error(`regex search worker exited with code ${code}`)));
    });
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      worker.terminate().finally(() => {
        resolve({ scanned: 0, skippedLongLines: 0, matches: [], timeLimited: true });
      });
    }, SEARCH_TIME_BUDGET_MS);
  });
}

function walk(root, options = {}) {
  const limit = Math.min(2000, Math.max(1, Number(options.limit || 200)));
  const maxDepth = Math.min(12, Math.max(0, Number(options.depth ?? 4)));
  const includeHidden = options.includeHidden === true;
  const out = [];
  const queue = [{ dir: root, depth: 0 }];
  while (queue.length && out.length < limit) {
    const current = queue.shift();
    let entries;
    try {
      entries = fs.readdirSync(current.dir, { withFileTypes: true });
    } catch (_error) {
      continue;
    }
    entries.sort((a, b) => a.name.localeCompare(b.name));
    for (const entry of entries) {
      if (out.length >= limit) break;
      if (!includeHidden && entry.name.startsWith('.')) continue;
      const absolute = path.join(current.dir, entry.name);
      out.push({ absolute, entry, depth: current.depth });
      if (
        entry.isDirectory() &&
        !entry.isSymbolicLink() &&
        current.depth < maxDepth &&
        !SKIP_DIRECTORIES.has(entry.name)
      ) {
        queue.push({ dir: absolute, depth: current.depth + 1 });
      }
    }
  }
  return { entries: out, truncated: queue.length > 0 || out.length >= limit };
}

function definition(name, description, kind, inputSchema, execute) {
  return { name, description, kind, inputSchema, execute };
}

function parseProcessJson(stdout) {
  const text = String(stdout || '').trim();
  if (!text) return null;
  const lines = text.split(/\r?\n/).reverse();
  for (const line of lines) {
    try {
      const parsed = JSON.parse(line);
      if (parsed && typeof parsed === 'object') return parsed;
    } catch (_error) {
      // Some Python startup diagnostics may precede the final JSON object.
    }
  }
  try {
    const parsed = JSON.parse(text);
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch (_error) {
    return null;
  }
}

function researchBusScript() {
  const monorepoRoot = path.resolve(__dirname, '..', '..', '..');
  const expectedLib = path.join(monorepoRoot, 'packages', 'cli', 'lib');
  if (path.resolve(expectedLib) !== path.resolve(__dirname)) return null;
  const candidate = path.join(monorepoRoot, 'scripts', 'research_api_bus.py');
  return fs.existsSync(candidate) ? candidate : null;
}

async function runEvidenceSource(workspaceRoot, request, options = {}) {
  if (request.source === 'workspace') {
    return searchWorkspaceEvidence(workspaceRoot, request.query, request.limit);
  }
  const script = researchBusScript();
  if (!script) {
    return {
      ok: false,
      api: request.source,
      count: 0,
      results: [],
      error: 'research_api_bus.py is unavailable; use the code route or run inside the SCBE repository',
    };
  }
  const env = options.env || process.env;
  const python = String(env.SCBE_PYTHON || env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3'));
  const executed = await runProcess(
    python,
    [script, '--api', request.source, '--query', request.query, '--limit', String(request.limit)],
    {
      cwd: workspaceRoot,
      shell: false,
      timeoutMs: 40_000,
      env,
    }
  );
  const parsed = parseProcessJson(executed.stdout);
  if (parsed) return parsed;
  return {
    ok: false,
    api: request.source,
    count: 0,
    results: [],
    error: executed.timedOut
      ? 'research source timed out'
      : 'research source returned no valid JSON' + (executed.stderr ? ': ' + String(executed.stderr).slice(0, 200) : ''),
  };
}

function buildTools(workspaceRoot, options = {}) {
  const root = fs.realpathSync(path.resolve(workspaceRoot));
  const evidenceSourceRunner =
    options.evidenceSourceRunner || ((request) => runEvidenceSource(root, request, options));
  return [
    definition(
      'read_file',
      'Read a UTF-8 text file in the current workspace, optionally by line range.',
      'read',
      {
        type: 'object',
        properties: {
          path: { type: 'string', description: 'Workspace-relative file path.' },
          start_line: { type: 'integer', minimum: 1 },
          end_line: { type: 'integer', minimum: 1 },
        },
        required: ['path'],
        additionalProperties: false,
      },
      async (args) => {
        const target = resolveWorkspacePath(root, args.path, { mustExist: true });
        const stat = fs.statSync(target);
        if (!stat.isFile()) throw new Error(`not a file: ${args.path}`);
        if (stat.size > MAX_FILE_BYTES) {
          throw new Error(`file is larger than ${MAX_FILE_BYTES} bytes: ${args.path}`);
        }
        const lines = fs.readFileSync(target, 'utf8').split(/\r?\n/);
        const start = Math.max(1, Number(args.start_line || 1));
        const end = Math.min(lines.length, Number(args.end_line || lines.length));
        return {
          ok: true,
          path: relativePath(root, target),
          start_line: start,
          end_line: end,
          total_lines: lines.length,
          content: lines.slice(start - 1, Math.max(start - 1, end)).join('\n'),
        };
      }
    ),
    definition(
      'list_files',
      'List files and directories inside the current workspace. Use depth to bound recursion.',
      'read',
      {
        type: 'object',
        properties: {
          path: { type: 'string', default: '.' },
          depth: { type: 'integer', minimum: 0, maximum: 12, default: 2 },
          limit: { type: 'integer', minimum: 1, maximum: 2000, default: 200 },
          include_hidden: { type: 'boolean', default: false },
        },
        additionalProperties: false,
      },
      async (args) => {
        const target = resolveWorkspacePath(root, args.path || '.', { mustExist: true });
        if (!fs.statSync(target).isDirectory()) throw new Error(`not a directory: ${args.path}`);
        const walked = walk(target, {
          depth: args.depth ?? 2,
          limit: args.limit ?? 200,
          includeHidden: args.include_hidden === true,
        });
        return {
          ok: true,
          root: relativePath(root, target),
          entries: walked.entries.map(({ absolute, entry }) => ({
            path: relativePath(root, absolute),
            type: entry.isDirectory() ? 'directory' : entry.isFile() ? 'file' : 'other',
          })),
          truncated: walked.truncated,
        };
      }
    ),
    definition(
      'search_text',
      'Search UTF-8 workspace files. Matching is literal by default; regex=true enables a bounded safe subset.',
      'read',
      {
        type: 'object',
        properties: {
          query: { type: 'string' },
          path: { type: 'string', default: '.' },
          regex: { type: 'boolean', default: false },
          case_sensitive: { type: 'boolean', default: false },
          limit: { type: 'integer', minimum: 1, maximum: 500, default: 100 },
        },
        required: ['query'],
        additionalProperties: false,
      },
      async (args) => {
        const target = resolveWorkspacePath(root, args.path || '.', { mustExist: true });
        const limit = Math.min(500, Math.max(1, Number(args.limit || 100)));
        const query = String(args.query);
        const regexMode = args.regex === true;
        const regexSource = regexMode ? assertSafeSearchRegex(query) : null;
        if (regexMode) new RegExp(regexSource, args.case_sensitive ? '' : 'i');
        const literalNeedle = args.case_sensitive ? query : query.toLowerCase();
        const files = fs.statSync(target).isFile()
          ? [{ absolute: target, entry: { isFile: () => true } }]
          : walk(target, { depth: 12, limit: 1500, includeHidden: false }).entries;
        if (regexMode) {
          const result = await searchRegexInWorker({
            files: files.filter((item) => item.entry.isFile()).map((item) => item.absolute),
            root,
            query: regexSource,
            caseSensitive: args.case_sensitive === true,
            limit,
          });
          return {
            ok: true,
            query: args.query,
            mode: 'regex',
            scanned_files: result.scanned,
            matches: result.matches,
            skipped_long_lines: result.skippedLongLines,
            time_limited: result.timeLimited,
            truncated:
              result.matches.length >= limit || result.skippedLongLines > 0 || result.timeLimited,
          };
        }
        const matches = [];
        let scanned = 0;
        let timeLimited = false;
        const deadline = Date.now() + SEARCH_TIME_BUDGET_MS;
        searchFiles:
        for (const item of files) {
          if (Date.now() > deadline) {
            timeLimited = true;
            break;
          }
          if (matches.length >= limit || !item.entry.isFile()) continue;
          let stat;
          try {
            stat = fs.statSync(item.absolute);
          } catch (_error) {
            continue;
          }
          if (stat.size > MAX_FILE_BYTES) continue;
          let text;
          try {
            text = fs.readFileSync(item.absolute, 'utf8');
          } catch (_error) {
            continue;
          }
          if (text.includes('\0')) continue;
          scanned += 1;
          const lines = text.split(/\r?\n/);
          for (let index = 0; index < lines.length && matches.length < limit; index += 1) {
            if (Date.now() > deadline) {
              timeLimited = true;
              break searchFiles;
            }
            const line = lines[index];
            const matched = (args.case_sensitive ? line : line.toLowerCase()).includes(literalNeedle);
            if (matched) {
              matches.push({
                path: relativePath(root, item.absolute),
                line: index + 1,
                text: line.slice(0, 500),
              });
            }
          }
        }
        return {
          ok: true,
          query: args.query,
          mode: regexMode ? 'regex' : 'literal',
          scanned_files: scanned,
          matches,
          skipped_long_lines: 0,
          time_limited: timeLimited,
          truncated: matches.length >= limit || timeLimited,
        };
      }
    ),
    definition(
      'guided_evidence',
      'Ride a bounded preset research route. Full source results stay outside model context; the tool returns compact citation handles, cross-source matches, retrieval keywords, and a chained multi-hash receipt.',
      'execute',
      {
        type: 'object',
        properties: {
          objective: { type: 'string', minLength: 3, maxLength: 2000 },
          route: { type: 'string', enum: Object.keys(ROUTE_PRESETS), default: 'cross-check' },
          limit: { type: 'integer', minimum: 1, maximum: 5, default: 3 },
          token_budget: { type: 'integer', minimum: 256, maximum: 4000, default: 1200 },
          max_stops: { type: 'integer', minimum: 1, maximum: 6 },
        },
        required: ['objective'],
        additionalProperties: false,
      },
      async (args) =>
        runGuidedEvidenceRoute({
          workspaceRoot: root,
          objective: args.objective,
          route: args.route || 'cross-check',
          limit: args.limit,
          tokenBudget: args.token_budget,
          maxStops: args.max_stops,
          env: options.env,
          home: options.home,
          sourceRunner: evidenceSourceRunner,
        })
    ),
    definition(
      'search_evidence',
      'Keyword-search compact guided-evidence packets without loading retained raw search results into context.',
      'read',
      {
        type: 'object',
        properties: {
          query: { type: 'string', minLength: 2, maxLength: 500 },
          limit: { type: 'integer', minimum: 1, maximum: 50, default: 10 },
        },
        required: ['query'],
        additionalProperties: false,
      },
      async (args) =>
        searchEvidencePackets(root, args.query, {
          limit: args.limit,
          env: options.env,
          home: options.home,
        })
    ),
    definition(
      'verify_evidence',
      'Recompute every packet and artifact digest and verify the packet receipt against its append-only chain.',
      'read',
      {
        type: 'object',
        properties: { packet_id: { type: 'string', minLength: 1, maxLength: 120 } },
        required: ['packet_id'],
        additionalProperties: false,
      },
      async (args) =>
        verifyEvidencePacket(root, args.packet_id, {
          env: options.env,
          home: options.home,
        })
    ),
    definition(
      'verify_receipts',
      'Verify the current workspace agent-tool receipt chain and report legacy and multi-hash receipt counts.',
      'read',
      { type: 'object', properties: {}, additionalProperties: false },
      async () => verifyReceiptLedger(root, { env: options.env, home: options.home })
    ),
    definition(
      'write_file',
      'Create a UTF-8 file in the workspace. Existing files require overwrite=true.',
      'write',
      {
        type: 'object',
        properties: {
          path: { type: 'string' },
          content: { type: 'string' },
          overwrite: { type: 'boolean', default: false },
        },
        required: ['path', 'content'],
        additionalProperties: false,
      },
      async (args) => {
        const target = resolveWorkspacePath(root, args.path);
        if (fs.existsSync(target) && args.overwrite !== true) {
          throw new Error(`file already exists; set overwrite=true to replace it: ${args.path}`);
        }
        fs.mkdirSync(path.dirname(target), { recursive: true });
        fs.writeFileSync(target, String(args.content), 'utf8');
        return { ok: true, path: relativePath(root, target), bytes: Buffer.byteLength(String(args.content)) };
      }
    ),
    definition(
      'edit_file',
      'Replace exact text in one UTF-8 workspace file. By default the old text must occur exactly once.',
      'write',
      {
        type: 'object',
        properties: {
          path: { type: 'string' },
          old_text: { type: 'string' },
          new_text: { type: 'string' },
          replace_all: { type: 'boolean', default: false },
        },
        required: ['path', 'old_text', 'new_text'],
        additionalProperties: false,
      },
      async (args) => {
        const target = resolveWorkspacePath(root, args.path, { mustExist: true });
        const before = fs.readFileSync(target, 'utf8');
        const oldText = String(args.old_text);
        if (!oldText) throw new Error('old_text cannot be empty');
        const count = before.split(oldText).length - 1;
        if (count === 0) throw new Error('old_text was not found');
        if (count > 1 && args.replace_all !== true) {
          throw new Error(`old_text occurs ${count} times; provide more context or set replace_all=true`);
        }
        const after = args.replace_all === true
          ? before.split(oldText).join(String(args.new_text))
          : before.replace(oldText, String(args.new_text));
        fs.writeFileSync(target, after, 'utf8');
        return { ok: true, path: relativePath(root, target), replacements: args.replace_all === true ? count : 1 };
      }
    ),
    definition(
      'create_directory',
      'Create a directory inside the current workspace.',
      'write',
      {
        type: 'object',
        properties: { path: { type: 'string' } },
        required: ['path'],
        additionalProperties: false,
      },
      async (args) => {
        const target = resolveWorkspacePath(root, args.path);
        fs.mkdirSync(target, { recursive: true });
        return { ok: true, path: relativePath(root, target) };
      }
    ),
    definition(
      'run_command',
      'Run one shell command in the current workspace and return bounded stdout, stderr, and exit status.',
      'execute',
      {
        type: 'object',
        properties: {
          command: { type: 'string' },
          timeout_ms: { type: 'integer', minimum: 100, maximum: 600000, default: 120000 },
        },
        required: ['command'],
        additionalProperties: false,
      },
      async (args) => {
        const command = String(args.command || '').trim();
        if (!command) throw new Error('command cannot be empty');
        return runProcess(command, [], {
          cwd: root,
          shell: true,
          timeoutMs: Math.min(600_000, Math.max(100, Number(args.timeout_ms || 120_000))),
        });
      }
    ),
    definition(
      'git_status',
      'Read the concise Git status for the current workspace.',
      'read',
      { type: 'object', properties: {}, additionalProperties: false },
      async () => runProcess('git', ['status', '--short', '--branch'], { cwd: root, timeoutMs: 15_000 })
    ),
    definition(
      'git_diff',
      'Read the current Git diff, optionally staged and optionally limited to one workspace path.',
      'read',
      {
        type: 'object',
        properties: {
          staged: { type: 'boolean', default: false },
          path: { type: 'string' },
        },
        additionalProperties: false,
      },
      async (args) => {
        const argv = ['diff'];
        if (args.staged === true) argv.push('--cached');
        if (args.path) {
          const target = resolveWorkspacePath(root, args.path);
          argv.push('--', relativePath(root, target));
        }
        return runProcess('git', argv, { cwd: root, timeoutMs: 30_000 });
      }
    ),
    definition(
      'workspace_info',
      'Inspect the current workspace root, platform, Node version, Git presence, and top-level entries.',
      'read',
      { type: 'object', properties: {}, additionalProperties: false },
      async () => {
        const entries = fs.readdirSync(root, { withFileTypes: true }).slice(0, 100);
        return {
          ok: true,
          root,
          platform: process.platform,
          node: process.version,
          git: fs.existsSync(path.join(root, '.git')),
          entries: entries.map((entry) => ({
            name: entry.name,
            type: entry.isDirectory() ? 'directory' : entry.isFile() ? 'file' : 'other',
          })),
        };
      }
    ),
  ];
}

function createToolRegistry(options = {}) {
  const workspaceRoot = path.resolve(options.workspaceRoot || process.cwd());
  const tools = buildTools(workspaceRoot, options);
  const byName = new Map(tools.map((tool) => [tool.name, tool]));
  return {
    workspaceRoot,
    names: () => tools.map((tool) => tool.name),
    list: () => tools.map(({ execute: _execute, ...tool }) => ({ ...tool })),
    definitions: () =>
      tools.map((tool) => ({
        name: tool.name,
        description: tool.description,
        inputSchema: tool.inputSchema,
      })),
    get: (name) => byName.get(String(name || '')) || null,
    async execute(name, args = {}) {
      const tool = byName.get(String(name || ''));
      if (!tool) throw new Error(`unknown tool: ${name}`);
      return tool.execute(args && typeof args === 'object' ? args : {});
    },
  };
}

module.exports = {
  DEFAULT_TOOL_NAMES,
  createToolRegistry,
  resolveWorkspacePath,
  runProcess,
  terminateProcessTree,
};
