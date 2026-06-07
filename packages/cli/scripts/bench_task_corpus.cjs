#!/usr/bin/env node
/**
 * bench_task_corpus.cjs — Real-model task corpus benchmark
 *
 * Unlike shell_benchmark.cjs (protocol mock tests), this runs REAL tasks
 * against a live LLM via `scbe shell --agent-json` and measures:
 *   - completion_rate  (verifier passed before max_turns)
 *   - turns_to_complete (first turn where verifier passed)
 *   - false_done_count (model claimed done before verifier agreed)
 *   - ko_ban_count (ko-ban blocks triggered)
 *   - duration_ms (wall time per task)
 *
 * Exit 0 always in calibration phase — first N runs establish baselines.
 *
 * Usage:
 *   node scripts/bench_task_corpus.cjs
 *   node scripts/bench_task_corpus.cjs --task run-freshness-tests
 *   node scripts/bench_task_corpus.cjs --list
 *   SCBE_MODEL=groq/llama-3.3-70b-versatile node scripts/bench_task_corpus.cjs
 *   node scripts/bench_task_corpus.cjs --no-artifact    # skip artifact write
 *
 * Env vars (same routing as scbe shell):
 *   SCBE_PROVIDER  SCBE_MODEL  SCBE_API_KEY  SCBE_BASE_URL
 *
 * Cost ceiling: --max-corpus-turns=N (default 80 across all tasks combined).
 * Each task also has a per-task wall-time cap (task.timeout_ms, default 120s).
 *
 * VERIFIER CONTRACT (v2): every task injects {WORKDIR} — a per-run tmpdir
 * unique to that invocation. The model writes its answer to {WORKDIR}/answer.txt.
 * done_if checks that file. This means a verifier can only pass if the model
 * actually ran and wrote something — no more static-state false positives.
 */

'use strict';

const { spawnSync, spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');
const ARTIFACT_DIR = path.join(REPO_ROOT, 'artifacts', 'benchmarks', 'scbe-task-corpus');

// ── Shell detection (identical to scbe_workflow.cjs) ─────────────────────────

function commandExists(name) {
  const r = spawnSync(process.platform === 'win32' ? 'where.exe' : 'command', [name], {
    encoding: 'utf8',
    shell: process.platform !== 'win32',
  });
  return r.status === 0;
}

function detectShell() {
  if (process.platform !== 'win32') return { kind: 'bash', exe: '/bin/bash', args: ['-c'] };
  const where = spawnSync('where.exe', ['bash.exe'], { encoding: 'utf8' });
  const gitBash = (where.stdout || '')
    .split(/\r?\n/)
    .map((l) => l.trim())
    .find(
      (l) =>
        l && !/\\windows\\system32\\bash\.exe$/i.test(l) && !/\\WindowsApps\\bash\.exe$/i.test(l)
    );
  if (gitBash) return { kind: 'bash', exe: gitBash, args: ['-c'] };
  if (commandExists('pwsh.exe'))
    return {
      kind: 'powershell',
      exe: 'pwsh.exe',
      args: ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command'],
    };
  return {
    kind: 'powershell',
    exe: 'powershell.exe',
    args: ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command'],
  };
}

const SHELL = detectShell();

function runShell(cmd, timeoutMs = 30000) {
  const r = spawnSync(SHELL.exe, [...SHELL.args, cmd], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    timeout: timeoutMs,
  });
  return {
    stdout: (r.stdout || '').trim(),
    stderr: (r.stderr || '').trim(),
    status: r.status ?? 1,
  };
}

function sendLine(proc, obj) {
  proc.stdin.write(JSON.stringify(obj) + '\n');
}

function recvLine(proc, timeoutMs = 60000) {
  return new Promise((resolve, reject) => {
    let buf = '';
    const timer = setTimeout(() => {
      proc.stdout.off('data', onData);
      reject(new Error(`recv timeout after ${timeoutMs}ms`));
    }, timeoutMs);
    const onData = (chunk) => {
      buf += chunk;
      const nl = buf.indexOf('\n');
      if (nl !== -1) {
        clearTimeout(timer);
        proc.stdout.off('data', onData);
        const line = buf.slice(0, nl).trim();
        try {
          resolve(JSON.parse(line));
        } catch (e) {
          reject(new Error(`bad JSON from agent: ${line.slice(0, 200)}`));
        }
      }
    };
    proc.stdout.on('data', onData);
  });
}

// ── Task Corpus ───────────────────────────────────────────────────────────────
//
// {WORKDIR} is substituted at runtime with a per-task tmpdir (forward-slash
// safe on Windows). The model must write its answer to {WORKDIR}/answer.txt.
// done_if verifiers read that file — they pass only if the model acted.
//
// Verifier strength:
//   strong  — checks exact content (known ground truth)
//   medium  — checks presence/shape (model must produce meaningful output)
//   weak    — checks file non-empty only (smoke-level)

const TASKS = [
  // ── Execute ────────────────────────────────────────────────────────────────
  {
    id: 'run-freshness-tests',
    category: 'execute',
    verifier: 'strong',
    difficulty: 'easy',
    instruction:
      "Run the benchmark artifact freshness test suite at packages/cli/tests/bench_artifact_freshness.test.cjs using Node's built-in test runner (`node --test packages/cli/tests/bench_artifact_freshness.test.cjs`). Count the passing tests from the output. Write the count as a plain integer (e.g. `17`) to `{WORKDIR}/answer.txt`.",
    done_if:
      `node -e "` +
      `const t=require('fs').readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `const n=parseInt(t);` +
      `if(isNaN(n)||n<15){process.stderr.write('need>=15 got:'+t+'\\n');process.exit(1)}` +
      `"`,
    max_turns: 5,
    timeout_ms: 90000,
  },
  {
    id: 'verify-pack-includes-workflow',
    category: 'execute',
    verifier: 'strong',
    difficulty: 'easy',
    instruction:
      'Run a dry-run npm pack from the packages/cli directory: `npm pack --dry-run --json`. Parse the JSON output and check whether `scripts/scbe_workflow.cjs` appears in the file list. Write exactly `yes` to `{WORKDIR}/answer.txt` if it is present, `no` if absent.',
    done_if:
      `node -e "` +
      `const t=require('fs').readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `if(t!=='yes'){process.stderr.write('expected yes got:'+t+'\\n');process.exit(1)}` +
      `"`,
    max_turns: 5,
    timeout_ms: 60000,
  },

  // ── Search + Count ─────────────────────────────────────────────────────────
  {
    id: 'count-bench-cases',
    category: 'search+count',
    verifier: 'strong',
    difficulty: 'medium',
    instruction:
      'Count how many test cases are registered in packages/cli/scripts/shell_benchmark.cjs. Cases are added using the pattern `cases.push(`. Write the exact count as a plain integer (e.g. `26`) to `{WORKDIR}/answer.txt`.',
    done_if:
      `node -e "` +
      `const t=require('fs').readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `const n=parseInt(t);` +
      `const actual=(require('fs').readFileSync('packages/cli/scripts/shell_benchmark.cjs','utf8').match(/cases\\.push/g)||[]).length;` +
      `if(isNaN(n)||n!==actual){process.stderr.write('expected '+actual+' got '+t+'\\n');process.exit(1)}` +
      `"`,
    max_turns: 5,
    timeout_ms: 60000,
  },
  {
    id: 'count-harmonic-ts-files',
    category: 'search+count',
    verifier: 'strong',
    difficulty: 'easy',
    instruction:
      'Count how many .ts files exist directly in src/harmonic/ (not in subdirectories — only the top level of that directory). Write the count as a plain integer to `{WORKDIR}/answer.txt`.',
    done_if:
      `node -e "` +
      `const t=require('fs').readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `const n=parseInt(t);` +
      `const actual=require('fs').readdirSync('src/harmonic').filter(f=>f.endsWith('.ts')).length;` +
      `if(isNaN(n)||n!==actual){process.stderr.write('expected '+actual+' got '+t+'\\n');process.exit(1)}` +
      `"`,
    max_turns: 5,
    timeout_ms: 60000,
  },
  {
    id: 'list-agent-bus-tools',
    category: 'search+count',
    verifier: 'strong',
    difficulty: 'easy',
    instruction:
      'Count how many tool entries are defined in packages/agent-bus/tools.json. Write the count as a plain integer to `{WORKDIR}/answer.txt`.',
    done_if:
      `node -e "` +
      `const tools=JSON.parse(require('fs').readFileSync('packages/agent-bus/tools.json','utf8'));` +
      `const expected=tools.length;` +
      `const t=require('fs').readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `const n=parseInt(t);` +
      `if(isNaN(n)||n!==expected){process.stderr.write('expected '+expected+' got '+t+'\\n');process.exit(1)}` +
      `"`,
    max_turns: 4,
    timeout_ms: 60000,
  },

  // ── Search + Comprehend ────────────────────────────────────────────────────
  {
    id: 'find-extractsummary-signature',
    category: 'search+comprehend',
    verifier: 'medium',
    difficulty: 'medium',
    instruction:
      'Find the function named `extractSummary` in packages/cli/scripts/scbe_workflow.cjs. Write the exact text inside its parentheses (the parameter list, without the parens) to `{WORKDIR}/answer.txt`.',
    done_if:
      `node -e "` +
      `const t=require('fs').readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `if(t.length<3||!/[a-zA-Z]/.test(t)){process.stderr.write('empty or non-alpha: '+t+'\\n');process.exit(1)}` +
      `"`,
    max_turns: 4,
    timeout_ms: 60000,
  },
  {
    id: 'identify-scbe-env-vars',
    category: 'search+enumerate',
    verifier: 'strong',
    difficulty: 'medium',
    instruction:
      'List all environment variable names starting with `SCBE_` that are read in packages/cli/bin/scbe.js. There are at least four. Write each variable name on its own line to `{WORKDIR}/answer.txt`.',
    done_if:
      `node -e "` +
      `const t=require('fs').readFileSync('{WORKDIR}/answer.txt','utf8');` +
      `const required=['SCBE_MODEL','SCBE_BASE_URL','SCBE_API_KEY','SCBE_PROVIDER'];` +
      `const missing=required.filter(v=>!t.includes(v));` +
      `if(missing.length){process.stderr.write('missing: '+missing.join(',')+'\\n');process.exit(1)}` +
      `"`,
    max_turns: 5,
    timeout_ms: 60000,
  },
  {
    id: 'trace-ko-ban-logic',
    category: 'search+comprehend',
    verifier: 'medium',
    difficulty: 'hard',
    instruction:
      'In packages/cli/bin/scbe.js, find where the ko-ban mechanism is implemented. A ko-ban blocks a command that was already tried with the same result. Write to `{WORKDIR}/answer.txt`: (1) the variable name where past attempts are stored, and (2) one sentence describing the condition that triggers a block.',
    done_if:
      `node -e "` +
      `const t=require('fs').readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `if(t.length<20||!t.toLowerCase().includes('ko')){process.stderr.write('too short or missing ko: '+t.slice(0,80)+'\\n');process.exit(1)}` +
      `"`,
    max_turns: 6,
    timeout_ms: 90000,
  },
  {
    id: 'find-reset-context-handler',
    category: 'search+comprehend',
    verifier: 'medium',
    difficulty: 'hard',
    instruction:
      'In packages/cli/bin/scbe.js, find where `reset_context` is handled. Write to `{WORKDIR}/answer.txt`: (1) what state is cleared when reset_context is true, and (2) whether a step_context summary is injected into conversation history.',
    done_if:
      `node -e "` +
      `const t=require('fs').readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `if(t.length<20||!t.toLowerCase().includes('reset')){process.stderr.write('too short or missing reset: '+t.slice(0,80)+'\\n');process.exit(1)}` +
      `"`,
    max_turns: 6,
    timeout_ms: 90000,
  },

  // ── Governance discriminators ──────────────────────────────────────────────
  {
    id: 'governance-deny-blocks-destructive',
    category: 'governance',
    verifier: 'strong',
    difficulty: 'medium',
    instruction:
      "Run the SCBE governance check on a destructive command: `node packages/cli/bin/scbe.js run 'rm -rf C:/' --json`. The output is a JSON object. Read the `governance.tier` field and write its value to `{WORKDIR}/answer.txt`.",
    done_if:
      `node -e "` +
      `const t=require('fs').readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `if(t!=='DENY'){process.stderr.write('expected DENY got:'+t+'\\n');process.exit(1)}` +
      `"`,
    max_turns: 4,
    timeout_ms: 60000,
  },

  // ── Agent bus / research discriminators ───────────────────────────────────
  {
    id: 'research-bus-arxiv',
    category: 'agent-bus',
    verifier: 'medium',
    difficulty: 'medium',
    instruction:
      "Search arXiv using the research API bus: `python scripts/research_api_bus.py --api arxiv --query 'hyperbolic geometry machine learning' --limit 3`. The command prints JSON to stdout. Write the `title` field of the first result to `{WORKDIR}/answer.txt`. If the API call fails (ok=false), write the error string instead.",
    done_if:
      `node -e "` +
      `const t=require('fs').readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `if(t.length<5){process.stderr.write('answer too short: '+t+'\\n');process.exit(1)}` +
      `"`,
    max_turns: 4,
    timeout_ms: 60000,
  },
  {
    id: 'research-bus-hf-models',
    category: 'agent-bus',
    verifier: 'medium',
    difficulty: 'medium',
    instruction:
      "Search HuggingFace for text-generation models using the research API bus: `python scripts/research_api_bus.py --api hf_models --query 'llama text generation' --limit 3`. The command prints JSON to stdout. Write the `model_id` of the first result to `{WORKDIR}/answer.txt`. If the API call fails, write the error string instead.",
    done_if:
      `node -e "` +
      `const t=require('fs').readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `if(t.length<3){process.stderr.write('answer too short: '+t+'\\n');process.exit(1)}` +
      `"`,
    max_turns: 4,
    timeout_ms: 60000,
  },
];

// ── Task runner ───────────────────────────────────────────────────────────────

/**
 * @typedef {{
 *   turn: number,
 *   cmd: string|null,
 *   observation: string,
 *   rationale: string,
 *   done: boolean,
 *   blocked: boolean,
 *   verified: boolean,
 *   duration_ms: number
 * }} TurnRecord
 *
 * @typedef {{
 *   id: string,
 *   category: string,
 *   difficulty: string,
 *   verifier: string,
 *   completed: boolean,
 *   turns: number,
 *   turns_to_complete: number|null,
 *   false_done_count: number,
 *   ko_ban_count: number,
 *   valid_cmd_turns: number,
 *   duration_ms: number,
 *   turns_log: TurnRecord[],
 *   error: string|null
 * }} TaskResult
 */

async function runTask(task, opts = {}) {
  const maxTurns = task.max_turns || 6;
  const timeoutMs = task.timeout_ms || 120000;
  const costCeiling = opts.remainingBudget ?? Infinity;
  const effectiveMax = Math.min(maxTurns, costCeiling);

  /** @type {TaskResult} */
  const result = {
    id: task.id,
    category: task.category,
    difficulty: task.difficulty,
    verifier: task.verifier,
    completed: false,
    turns: 0,
    turns_to_complete: null,
    false_done_count: 0,
    ko_ban_count: 0,
    valid_cmd_turns: 0,
    duration_ms: 0,
    turns_log: [],
    error: null,
  };

  if (effectiveMax <= 0) {
    result.error = 'skipped: corpus turn budget exhausted';
    return result;
  }

  // Per-task tmpdir — substituted for {WORKDIR} in instruction + done_if.
  // Forward-slash conversion makes it safe in shell inline-node snippets on Windows.
  const workdir = fs.mkdtempSync(path.join(os.tmpdir(), `scbe-bench-${task.id}-`));
  const safeWorkdir = workdir.split(path.sep).join('/');

  const instruction = task.instruction.replace(/\{WORKDIR\}/g, safeWorkdir);
  const done_if = task.done_if ? task.done_if.replace(/\{WORKDIR\}/g, safeWorkdir) : null;

  const started = Date.now();
  let proc;

  try {
    proc = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
      stdio: ['pipe', 'pipe', 'inherit'],
      cwd: REPO_ROOT,
      env: { ...process.env, NO_COLOR: '1' },
    });

    // Wait for ready signal
    const ready = await Promise.race([
      recvLine(proc, 15000),
      new Promise((_, reject) => setTimeout(() => reject(new Error('agent ready timeout')), 15000)),
    ]);
    if (!ready.ready) throw new Error(`Expected ready, got: ${JSON.stringify(ready)}`);

    // Send first instruction
    sendLine(proc, {
      instruction,
      terminal_state: '$ ',
      done_if: done_if || null,
      max_turns: effectiveMax,
    });

    let terminalState = '$ ';
    let prevKoBans = 0;

    for (let turn = 1; turn <= effectiveMax; turn++) {
      const turnStart = Date.now();
      let resp;

      try {
        resp = await recvLine(proc, timeoutMs);
      } catch (e) {
        result.error = `turn ${turn}: ${e.message}`;
        break;
      }

      if (resp.max_turns_reached) break;
      if (resp.error) {
        result.error = `agent error: ${resp.error}`;
        break;
      }

      result.turns = turn;

      const cmd = resp.commands && resp.commands[0] ? resp.commands[0].keystrokes : null;
      const blocked = !!(resp.blocked || resp.governance_blocked);
      const boardKoBans =
        resp.board && Array.isArray(resp.board.ko_bans)
          ? resp.board.ko_bans.length
          : resp.board && typeof resp.board.ko_bans === 'number'
            ? resp.board.ko_bans
            : prevKoBans;
      const newKoBans = Math.max(0, boardKoBans - prevKoBans);
      prevKoBans = boardKoBans;
      result.ko_ban_count += newKoBans;

      if (cmd) result.valid_cmd_turns++;

      // Execute command and update terminal state
      let observation = '';
      if (cmd && !blocked) {
        const remainingMs = timeoutMs - (Date.now() - started);
        const execTimeoutMs = Math.max(1000, Math.min(30000, remainingMs));
        const exec = runShell(cmd, execTimeoutMs);
        observation = [exec.stdout, exec.stderr].filter(Boolean).join('\n').slice(0, 2000);
        terminalState = `$ ${cmd}\n${observation}`;
      } else if (blocked) {
        observation = `[BLOCKED: ${(resp.rationale || 'ko-ban/governance').slice(0, 100)}]`;
        terminalState = `$ ${cmd || '(no cmd)'}\n${observation}`;
      }

      // Check verifier after executing the command
      let verified = false;
      if (done_if) {
        const vr = runShell(done_if, 15000);
        verified = vr.status === 0;
      }

      // Track false_done: model said done but verifier disagrees
      if (resp.done && !verified) result.false_done_count++;

      /** @type {TurnRecord} */
      const record = {
        turn,
        cmd: cmd ? cmd.slice(0, 200) : null,
        observation: observation.slice(0, 500),
        rationale: (resp.rationale || '').slice(0, 200),
        done: !!resp.done,
        blocked,
        verified,
        duration_ms: Date.now() - turnStart,
      };
      result.turns_log.push(record);

      if (verified) {
        result.completed = true;
        result.turns_to_complete = turn;
        break;
      }

      if (turn >= effectiveMax) break;

      // Send next turn
      sendLine(proc, { terminal_state: terminalState });
    }
  } catch (e) {
    result.error = e.message;
  } finally {
    if (proc) {
      try {
        proc.stdin.end();
      } catch (_) {}
      try {
        proc.kill();
      } catch (_) {}
    }
    result.duration_ms = Date.now() - started;
    // Clean up per-task workdir
    try {
      fs.rmSync(workdir, { recursive: true, force: true });
    } catch (_) {}
  }

  return result;
}

// ── Corpus runner ─────────────────────────────────────────────────────────────

async function runCorpus(tasks, opts = {}) {
  const maxCorpusTurns = opts.maxCorpusTurns || 80;
  let remainingBudget = maxCorpusTurns;
  const results = [];

  for (const task of tasks) {
    console.log(`\n${'─'.repeat(60)}`);
    console.log(
      `Task: ${task.id}  [${task.category} / ${task.difficulty} / verifier:${task.verifier}]`
    );
    console.log(`Instruction: ${task.instruction.slice(0, 100)}…`);
    console.log(
      `Max turns: ${Math.min(task.max_turns, remainingBudget)}  Budget remaining: ${remainingBudget}`
    );

    const result = await runTask(task, { remainingBudget });
    results.push(result);

    remainingBudget -= result.turns;

    const status = result.completed
      ? `[PASS] in ${result.turns_to_complete} turns`
      : result.error
        ? `[ERR]  ${result.error.slice(0, 60)}`
        : `[FAIL] ${result.turns} turns, no verify`;
    console.log(
      `  → ${status}  false_done=${result.false_done_count}  ko_bans=${result.ko_ban_count}  ${result.duration_ms}ms`
    );

    if (remainingBudget <= 0) {
      console.log('\n[BUDGET EXHAUSTED] Stopping corpus early.');
      break;
    }
  }

  return results;
}

// ── Reporting ─────────────────────────────────────────────────────────────────

function printSummaryTable(results) {
  const w = { id: 34, cat: 16, result: 22, turns: 8, fd: 6, kb: 6, ms: 8 };
  const hr = '─'.repeat(Object.values(w).reduce((a, b) => a + b + 3, 0));
  const header =
    pad('Task', w.id) +
    ' │ ' +
    pad('Category', w.cat) +
    ' │ ' +
    pad('Result', w.result) +
    ' │ ' +
    pad('Turns', w.turns) +
    ' │ ' +
    pad('FalseDone', w.fd) +
    ' │ ' +
    pad('KoBans', w.kb) +
    ' │ ' +
    pad('ms', w.ms);

  console.log('\n' + '═'.repeat(hr.length));
  console.log('TASK CORPUS RESULTS');
  console.log('═'.repeat(hr.length));
  console.log(header);
  console.log(hr);

  for (const r of results) {
    const resultStr = r.completed
      ? `PASS (turn ${r.turns_to_complete})`
      : r.error
        ? 'ERR: ' + r.error.slice(0, 14)
        : 'FAIL';
    const row =
      pad(r.id, w.id) +
      ' │ ' +
      pad(r.category, w.cat) +
      ' │ ' +
      pad(resultStr, w.result) +
      ' │ ' +
      pad(String(r.turns), w.turns) +
      ' │ ' +
      pad(String(r.false_done_count), w.fd) +
      ' │ ' +
      pad(String(r.ko_ban_count), w.kb) +
      ' │ ' +
      pad(String(r.duration_ms), w.ms);
    console.log(row);
  }

  console.log(hr);

  const completed = results.filter((r) => r.completed).length;
  const total = results.length;
  const totalTurns = results.reduce((a, r) => a + r.turns, 0);
  const totalMs = results.reduce((a, r) => a + r.duration_ms, 0);
  const totalFD = results.reduce((a, r) => a + r.false_done_count, 0);
  const totalKB = results.reduce((a, r) => a + r.ko_ban_count, 0);

  console.log(
    `\nSummary: ${completed}/${total} tasks completed` +
      `  turns=${totalTurns}  false_done=${totalFD}  ko_bans=${totalKB}  total=${totalMs}ms`
  );
  console.log('═'.repeat(hr.length));
}

function pad(s, n) {
  if (s.length >= n) return s.slice(0, n);
  return s + ' '.repeat(n - s.length);
}

function getHeadCommit() {
  return spawnSync('git', ['rev-parse', '--short', 'HEAD'], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
  }).stdout.trim();
}

function writeArtifact(results, model, provider) {
  if (!fs.existsSync(ARTIFACT_DIR)) fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const artifact = {
    schema: 'task-corpus/v2',
    generated_at: new Date().toISOString(),
    commit: getHeadCommit(),
    provider: provider || process.env.SCBE_PROVIDER || 'unknown',
    model: model || process.env.SCBE_MODEL || 'unknown',
    score: {
      completed: results.filter((r) => r.completed).length,
      total: results.length,
      completion_rate: results.length
        ? results.filter((r) => r.completed).length / results.length
        : 0,
    },
    totals: {
      turns: results.reduce((a, r) => a + r.turns, 0),
      false_done: results.reduce((a, r) => a + r.false_done_count, 0),
      ko_bans: results.reduce((a, r) => a + r.ko_ban_count, 0),
      duration_ms: results.reduce((a, r) => a + r.duration_ms, 0),
    },
    tasks: results,
  };
  const p = path.join(ARTIFACT_DIR, `${stamp}.json`);
  fs.writeFileSync(p, JSON.stringify(artifact, null, 2));
  return p;
}

// ── Main ──────────────────────────────────────────────────────────────────────

(async () => {
  const args = process.argv.slice(2);

  if (args.includes('--list')) {
    console.log('Task corpus:');
    for (const t of TASKS) {
      console.log(
        `  ${t.id.padEnd(36)} [${t.category}] difficulty=${t.difficulty} verifier=${t.verifier}`
      );
    }
    process.exit(0);
  }

  if (args.includes('--help') || args.includes('-h')) {
    console.log(
      [
        'Usage: node scripts/bench_task_corpus.cjs [options]',
        '',
        'Options:',
        '  --task <id>              Run only a single task by id',
        '  --list                   Print task corpus and exit',
        '  --no-artifact            Skip writing the JSON artifact',
        '  --max-corpus-turns=N     Total turn budget across corpus (default: 80)',
        '  --help                   This message',
        '',
        'Env vars (same as scbe shell):',
        '  SCBE_PROVIDER  SCBE_MODEL  SCBE_API_KEY  SCBE_BASE_URL',
        '',
        'Tip: smoke-test verifiers without a model:',
        '  SCBE_PROVIDER=offline node scripts/bench_task_corpus.cjs --task list-agent-bus-tools',
      ].join('\n')
    );
    process.exit(0);
  }

  const taskArg = args.find((a) => a.startsWith('--task'));
  const taskFilter = taskArg
    ? taskArg.includes('=')
      ? taskArg.split('=')[1]
      : args[args.indexOf(taskArg) + 1]
    : null;
  const noArtifact = args.includes('--no-artifact');
  const maxTurnsArg = args.find((a) => a.startsWith('--max-corpus-turns='));
  const maxCorpusTurns = maxTurnsArg ? parseInt(maxTurnsArg.split('=')[1], 10) : 80;

  const tasksToRun = taskFilter ? TASKS.filter((t) => t.id === taskFilter) : TASKS;
  if (!tasksToRun.length) {
    console.error(`No task found matching: ${taskFilter}`);
    process.exit(1);
  }

  const model = process.env.SCBE_MODEL || '(default)';
  const provider = process.env.SCBE_PROVIDER || 'ollama';
  console.log(`\nTask Corpus Bench v2 — provider=${provider} model=${model}`);
  console.log(`Tasks: ${tasksToRun.length}  Corpus turn budget: ${maxCorpusTurns}`);
  console.log(
    'Verifier contract v2: {WORKDIR}/answer.txt per task — no static-state false positives\n'
  );

  const results = await runCorpus(tasksToRun, { maxCorpusTurns });

  printSummaryTable(results);

  if (!noArtifact) {
    const artifactPath = writeArtifact(results, model, provider);
    console.log(`\nArtifact: ${artifactPath}`);
  }

  // Exit 0 always — calibration phase, no baseline gate
  process.exit(0);
})();
