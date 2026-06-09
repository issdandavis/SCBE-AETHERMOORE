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
 *   node scripts/bench_task_corpus.cjs --category codegen
 *   node scripts/bench_task_corpus.cjs --provider offline --fail-on-incomplete
 *   node scripts/bench_task_corpus.cjs --provider ollama --model qwen2.5-coder:1.5b
 *   node scripts/bench_task_corpus.cjs --category codegen-hard --advisor-model qwen2.5-coder:1.5b
 *   node scripts/bench_task_corpus.cjs --category codegen-hard --chart
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

function nodeEval(script) {
  const encoded = Buffer.from(
    String(script).replace(/\{WORKDIR\}/g, '__WORKDIR__'),
    'utf8'
  ).toString('base64');
  return `node -e "const __s=Buffer.from('${encoded}','base64').toString().replace(/__WORKDIR__/g,'{WORKDIR}');eval(__s)"`;
}

function advisorConfig(opts = {}) {
  const model = opts.advisorModel || process.env.SCBE_ADVISOR_MODEL || '';
  const provider =
    opts.advisorProvider || process.env.SCBE_ADVISOR_PROVIDER || (model ? 'ollama' : '');
  if (!model && !provider) return null;
  return {
    provider: provider || 'ollama',
    model: model || (provider === 'offline' ? 'offline-echo' : ''),
    maxChars: Number(opts.advisorMaxChars || process.env.SCBE_ADVISOR_MAX_CHARS || 1400),
    mode: opts.advisorMode || process.env.SCBE_ADVISOR_MODE || 'retry',
  };
}

function taskStrategy(task) {
  if (task.category === 'codegen-hard') return 'repair/generate files; verifier runs code';
  if (task.category === 'codegen') return 'generate runnable artifact; verifier imports it';
  if (task.category === 'execute') return 'run command and extract result';
  if (task.category.startsWith('search')) return 'search repo, compute exact answer';
  if (task.category === 'governance') return 'inspect policy/gate result';
  if (task.category === 'agent-bus') return 'call bus/research tool and parse output';
  return 'primary agent acts; verifier decides';
}

function printAssignmentChart(tasks, opts = {}) {
  const advisor = advisorConfig(opts);
  const primary = `${process.env.SCBE_PROVIDER || opts.provider || 'ollama'}:${process.env.SCBE_MODEL || opts.model || '(default)'}`;
  const advisorLabel = advisor
    ? `${advisor.provider}:${advisor.model || '(default)'}/${advisor.mode}`
    : 'none';
  const rows = tasks.map((task) => ({
    task: task.id,
    difficulty: task.difficulty,
    category: task.category,
    primary,
    advisor: advisorLabel,
    verifier: task.verifier,
    strategy: taskStrategy(task),
  }));

  const widths = {
    task: Math.max(4, ...rows.map((r) => r.task.length)),
    difficulty: Math.max(10, ...rows.map((r) => r.difficulty.length)),
    category: Math.max(8, ...rows.map((r) => r.category.length)),
    primary: Math.max(7, ...rows.map((r) => r.primary.length)),
    advisor: Math.max(7, ...rows.map((r) => r.advisor.length)),
    verifier: Math.max(8, ...rows.map((r) => r.verifier.length)),
    strategy: Math.max(8, ...rows.map((r) => r.strategy.length)),
  };
  const header =
    pad('Task', widths.task) +
    ' │ ' +
    pad('Difficulty', widths.difficulty) +
    ' │ ' +
    pad('Category', widths.category) +
    ' │ ' +
    pad('Primary', widths.primary) +
    ' │ ' +
    pad('Advisor', widths.advisor) +
    ' │ ' +
    pad('Verifier', widths.verifier) +
    ' │ ' +
    pad('Assignment', widths.strategy);
  const hr = '─'.repeat(header.length);
  console.log('\nTASK DIFFICULTY + ASSIGNMENT CHART');
  console.log(hr);
  console.log(header);
  console.log(hr);
  for (const row of rows) {
    console.log(
      pad(row.task, widths.task) +
        ' │ ' +
        pad(row.difficulty, widths.difficulty) +
        ' │ ' +
        pad(row.category, widths.category) +
        ' │ ' +
        pad(row.primary, widths.primary) +
        ' │ ' +
        pad(row.advisor, widths.advisor) +
        ' │ ' +
        pad(row.verifier, widths.verifier) +
        ' │ ' +
        pad(row.strategy, widths.strategy)
    );
  }
  console.log(hr);
}

function buildAdvisorPrompt(task) {
  const research = task.researchBrief
    ? ['', 'CONTROLLED WEB RESEARCH BRIEF (allowlisted snippets only):', task.researchBrief].join(
        '\n'
      )
    : '';
  return [
    'You are an advisor for a coding benchmark harness.',
    'Do not claim completion. Do not ask follow-up questions. Do not run commands.',
    'Return a compact worksheet for the primary coding agent:',
    '1. files to create or edit',
    '2. core algorithm or fix',
    '3. edge cases the verifier is likely to test',
    '4. one shortest safe command shape, if useful',
    '',
    `Task id: ${task.id}`,
    `Category: ${task.category}`,
    `Difficulty: ${task.difficulty}`,
    `Verifier: ${task.verifier}`,
    '',
    'Instruction:',
    task.instruction,
    research,
  ].join('\n');
}

function parseCsv(value) {
  return String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function hostnameOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./i, '').toLowerCase();
  } catch (_) {
    return '';
  }
}

function allowedByDomain(url, domains) {
  if (!domains.length) return false;
  const host = hostnameOf(url);
  return domains.some((domain) => {
    const clean = String(domain || '')
      .replace(/^www\./i, '')
      .toLowerCase();
    return host === clean || host.endsWith(`.${clean}`);
  });
}

async function controlledWebResearch(query, config = {}) {
  if (!query) return null;
  const allowedDomains = parseCsv(
    config.domains ||
      'swebench.com,terminalbench.lol,tbench.ai,github.com,arxiv.org,kaggle.com,chemrag.github.io,superchem.pku.edu.cn,huggingface.co'
  );
  const maxResults = Math.max(1, Math.min(5, Number(config.maxResults || 3)));
  const started = Date.now();
  const result = {
    query,
    allowed_domains: allowedDomains,
    source: 'duckduckgo_instant_answer',
    ok: false,
    duration_ms: 0,
    results: [],
    error: null,
  };
  if (typeof fetch !== 'function') {
    result.error = 'fetch unavailable';
    return result;
  }
  try {
    const url = `https://api.duckduckgo.com/?q=${encodeURIComponent(query)}&format=json&no_redirect=1&no_html=1`;
    const res = await fetch(url, { signal: AbortSignal.timeout(8000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const candidates = [];
    if (data.AbstractText && data.AbstractURL) {
      candidates.push({
        title: data.Heading || 'Abstract',
        url: data.AbstractURL,
        snippet: data.AbstractText,
      });
    }
    for (const item of data.RelatedTopics || []) {
      if (item.Text && item.FirstURL) {
        candidates.push({
          title: item.Text.slice(0, 90),
          url: item.FirstURL,
          snippet: item.Text,
        });
      }
    }
    result.results = candidates
      .filter((item) => allowedByDomain(item.url, allowedDomains))
      .slice(0, maxResults)
      .map((item) => ({
        title: item.title,
        url: item.url,
        domain: hostnameOf(item.url),
        snippet: String(item.snippet || '').slice(0, 280),
      }));
    result.ok = result.results.length > 0;
  } catch (error) {
    result.error = error.message;
  } finally {
    result.duration_ms = Date.now() - started;
  }
  return result;
}

function formatResearchBrief(research) {
  if (!research?.results?.length) return '';
  return research.results
    .map((item, index) => `${index + 1}. ${item.title}\n   ${item.url}\n   ${item.snippet}`)
    .join('\n');
}

function callAdvisor(task, workdir, config) {
  if (!config) return null;
  const started = Date.now();
  const promptPath = path.join(workdir, 'advisor_prompt.txt');
  fs.writeFileSync(promptPath, buildAdvisorPrompt(task), 'utf8');
  const args = [
    CLI,
    'trap-dispatch',
    '--file',
    promptPath,
    '--provider',
    config.provider,
    '--json',
  ];
  if (config.model) args.push('--model', config.model);
  const run = spawnSync(process.execPath, args, {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    timeout: 90000,
    env: { ...process.env, NO_COLOR: '1' },
    maxBuffer: 1024 * 1024 * 4,
  });
  const raw = (run.stdout || '').trim();
  let parsed = null;
  try {
    parsed = JSON.parse(raw);
  } catch (_) {}
  const text = String(parsed?.response || raw || run.stderr || '').trim();
  return {
    provider: config.provider,
    model: config.model || '',
    ok: run.status === 0 && (!parsed || parsed.receipt === 'SCBE_TRAP_DISPATCH=1'),
    duration_ms: Date.now() - started,
    hint: text.slice(0, Math.max(200, config.maxChars || 1400)),
    error:
      run.status === 0
        ? null
        : (run.stderr || run.error?.message || 'advisor failed').slice(0, 500),
  };
}

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

  // ── Code generation ───────────────────────────────────────────────────────
  {
    id: 'codegen-js-clamp-module',
    category: 'codegen',
    verifier: 'strong',
    difficulty: 'medium',
    instruction:
      'Generate a JavaScript module at `{WORKDIR}/clamp.js` exporting `clamp(value, min, max)`, plus a runnable test file at `{WORKDIR}/test-clamp.js`. The function must clamp high/low values, return in-range values unchanged, and throw if `min > max`. Run the test with Node. If it passes, write exactly `pass` to `{WORKDIR}/answer.txt`.',
    done_if:
      `node -e "` +
      `const fs=require('fs'),cp=require('child_process'),p=require('path');` +
      `const dir=p.dirname('{WORKDIR}/answer.txt');` +
      `const answer=fs.readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `if(answer!=='pass'){process.stderr.write('expected pass got:'+answer+'\\n');process.exit(1)}` +
      `if(!fs.existsSync(p.join(dir,'clamp.js'))||!fs.existsSync(p.join(dir,'test-clamp.js'))){process.stderr.write('missing generated files\\n');process.exit(1)}` +
      `const r=cp.spawnSync(process.execPath,[p.join(dir,'test-clamp.js')],{cwd:dir,encoding:'utf8'});` +
      `if(r.status!==0){process.stderr.write((r.stdout||'')+(r.stderr||''));process.exit(1)}` +
      `"`,
    max_turns: 4,
    timeout_ms: 60000,
  },
  {
    id: 'codegen-python-prime-coordinate',
    category: 'codegen',
    verifier: 'strong',
    difficulty: 'medium',
    instruction:
      'Generate a Python module at `{WORKDIR}/prime_coordinate.py` containing `factor_profile(n)`. It should return a dictionary with `is_prime`, `omega`, `omega_distinct`, and `residue30`. Use the prime-depth coordinate method: `omega` counts prime factors with multiplicity, `omega_distinct` counts distinct prime factors, and `residue30` is `n % 30`. Add a runnable test file at `{WORKDIR}/test_prime_coordinate.py`. If tests pass, write exactly `pass` to `{WORKDIR}/answer.txt`.',
    done_if:
      `node -e "` +
      `const fs=require('fs'),cp=require('child_process'),p=require('path');` +
      `const dir=p.dirname('{WORKDIR}/answer.txt');` +
      `const answer=fs.readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `if(answer!=='pass'){process.stderr.write('expected pass got:'+answer+'\\n');process.exit(1)}` +
      `if(!fs.existsSync(p.join(dir,'prime_coordinate.py'))||!fs.existsSync(p.join(dir,'test_prime_coordinate.py'))){process.stderr.write('missing generated files\\n');process.exit(1)}` +
      `const py=process.env.PYTHON||'python';` +
      `const r=cp.spawnSync(py,[p.join(dir,'test_prime_coordinate.py')],{cwd:dir,encoding:'utf8'});` +
      `if(r.status!==0){process.stderr.write((r.stdout||'')+(r.stderr||''));process.exit(1)}` +
      `"`,
    max_turns: 4,
    timeout_ms: 60000,
  },
  {
    id: 'codegen-js-intent-router',
    category: 'codegen',
    verifier: 'strong',
    difficulty: 'medium',
    instruction:
      'Generate a JavaScript module at `{WORKDIR}/intent_router.js` exporting `classifyInput(input)`, plus a runnable test file at `{WORKDIR}/test-intent-router.js`. The function should classify `/run dir` as `{kind:"slash", target:"run", args:"dir"}`, `[bash: git status]` as `{kind:"bracket", target:"bash", args:"git status"}`, `math 2+2` as `{kind:"math", target:"math", args:"2+2"}`, and ordinary text as `{kind:"natural", target:"chat", args:<trimmed text>}`. Run the test with Node. If it passes, write exactly `pass` to `{WORKDIR}/answer.txt`.',
    done_if:
      `node -e "` +
      `const fs=require('fs'),cp=require('child_process'),p=require('path');` +
      `const dir=p.dirname('{WORKDIR}/answer.txt');` +
      `const answer=fs.readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `if(answer!=='pass'){process.stderr.write('expected pass got:'+answer+'\\n');process.exit(1)}` +
      `if(!fs.existsSync(p.join(dir,'intent_router.js'))||!fs.existsSync(p.join(dir,'test-intent-router.js'))){process.stderr.write('missing generated files\\n');process.exit(1)}` +
      `const r=cp.spawnSync(process.execPath,[p.join(dir,'test-intent-router.js')],{cwd:dir,encoding:'utf8'});` +
      `if(r.status!==0){process.stderr.write((r.stdout||'')+(r.stderr||''));process.exit(1)}` +
      `"`,
    max_turns: 4,
    timeout_ms: 60000,
  },
  {
    id: 'codegen-python-prime-abacus',
    category: 'codegen',
    verifier: 'strong',
    difficulty: 'medium',
    instruction:
      'Generate a Python module at `{WORKDIR}/prime_abacus.py` containing `is_prime(n)`, `prime_depth(n)`, and `anchor_gap(n)`. `prime_depth(n)` should count primes <= n. `anchor_gap(n)` should return a dictionary with `anchor` equal to the greatest prime <= n, `depth` equal to `prime_depth(n)`, and `gap` equal to `n - anchor`. Add a runnable test file at `{WORKDIR}/test_prime_abacus.py`. If tests pass, write exactly `pass` to `{WORKDIR}/answer.txt`.',
    done_if:
      `node -e "` +
      `const fs=require('fs'),cp=require('child_process'),p=require('path');` +
      `const dir=p.dirname('{WORKDIR}/answer.txt');` +
      `const answer=fs.readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `if(answer!=='pass'){process.stderr.write('expected pass got:'+answer+'\\n');process.exit(1)}` +
      `if(!fs.existsSync(p.join(dir,'prime_abacus.py'))||!fs.existsSync(p.join(dir,'test_prime_abacus.py'))){process.stderr.write('missing generated files\\n');process.exit(1)}` +
      `const py=process.env.PYTHON||'python';` +
      `const r=cp.spawnSync(py,[p.join(dir,'test_prime_abacus.py')],{cwd:dir,encoding:'utf8'});` +
      `if(r.status!==0){process.stderr.write((r.stdout||'')+(r.stderr||''));process.exit(1)}` +
      `"`,
    max_turns: 4,
    timeout_ms: 60000,
  },
  {
    id: 'codegen-python-chunk-worksheet',
    category: 'codegen',
    verifier: 'strong',
    difficulty: 'medium',
    instruction:
      'Generate a Python module at `{WORKDIR}/chunk_worksheet.py` containing `chunk_text(text, size)` and `worksheet(text, size=3)`. `chunk_text` should split text into word chunks of at most `size` words. `worksheet` should return rows like `{"index": 0, "start": 0, "end": 3, "text": "..."}` so an agent can work in token-like chunks. Add a runnable test file at `{WORKDIR}/test_chunk_worksheet.py`. If tests pass, write exactly `pass` to `{WORKDIR}/answer.txt`.',
    done_if:
      `node -e "` +
      `const fs=require('fs'),cp=require('child_process'),p=require('path');` +
      `const dir=p.dirname('{WORKDIR}/answer.txt');` +
      `const answer=fs.readFileSync('{WORKDIR}/answer.txt','utf8').trim();` +
      `if(answer!=='pass'){process.stderr.write('expected pass got:'+answer+'\\n');process.exit(1)}` +
      `if(!fs.existsSync(p.join(dir,'chunk_worksheet.py'))||!fs.existsSync(p.join(dir,'test_chunk_worksheet.py'))){process.stderr.write('missing generated files\\n');process.exit(1)}` +
      `const py=process.env.PYTHON||'python';` +
      `const r=cp.spawnSync(py,[p.join(dir,'test_chunk_worksheet.py')],{cwd:dir,encoding:'utf8'});` +
      `if(r.status!==0){process.stderr.write((r.stdout||'')+(r.stderr||''));process.exit(1)}` +
      `"`,
    max_turns: 4,
    timeout_ms: 60000,
  },

  // ── Hard code generation / repair ────────────────────────────────────────
  {
    id: 'codegen-hard-js-fix-average',
    category: 'codegen-hard',
    verifier: 'strong',
    difficulty: 'hard',
    setup: nodeEval(`
      const fs = require('fs');
      const path = require('path');
      const dir = '{WORKDIR}';
      fs.writeFileSync(path.join(dir, 'stats.js'), [
        'function average(values) {',
        '  return values.reduce((a, b) => a + b, 0) / (values.length - 1);',
        '}',
        'module.exports = { average };',
        ''
      ].join('\\n'));
      fs.writeFileSync(path.join(dir, 'test-stats.js'), [
        'const assert = require("node:assert/strict");',
        'const { average } = require("./stats.js");',
        'assert.equal(average([1, 2, 3, 4]), 2.5);',
        'assert.equal(average([10]), 10);',
        'assert.equal(average([]), 0);',
        'console.log("stats-pass");',
        ''
      ].join('\\n'));
    `),
    instruction:
      'Task id: codegen-hard-js-fix-average. A failing JavaScript fixture already exists at `{WORKDIR}/stats.js` with tests at `{WORKDIR}/test-stats.js`. Edit `stats.js` so `node {WORKDIR}/test-stats.js` passes. Do not weaken the test. If it passes, write exactly `pass` to `{WORKDIR}/answer.txt`.',
    done_if: nodeEval(`
      const fs = require('fs');
      const cp = require('child_process');
      const path = require('path');
      const dir = path.dirname('{WORKDIR}/answer.txt');
      const answer = fs.readFileSync(path.join(dir, 'answer.txt'), 'utf8').trim();
      if (answer !== 'pass') throw new Error('expected pass got ' + answer);
      const mod = require(path.join(dir, 'stats.js'));
      if (mod.average([1, 2, 3, 4]) !== 2.5) throw new Error('bad average list');
      if (mod.average([10]) !== 10) throw new Error('bad singleton');
      if (mod.average([]) !== 0) throw new Error('bad empty');
      const r = cp.spawnSync(process.execPath, [path.join(dir, 'test-stats.js')], { cwd: dir, encoding: 'utf8' });
      if (r.status !== 0) throw new Error((r.stdout || '') + (r.stderr || ''));
    `),
    max_turns: 4,
    timeout_ms: 90000,
  },
  {
    id: 'codegen-hard-python-fix-normalizer',
    category: 'codegen-hard',
    verifier: 'strong',
    difficulty: 'hard',
    setup: nodeEval(`
      const fs = require('fs');
      const path = require('path');
      const dir = '{WORKDIR}';
      fs.writeFileSync(path.join(dir, 'normalizer.py'), [
        'def normalize_command(text):',
        '    return str(text)',
        ''
      ].join('\\n'));
      fs.writeFileSync(path.join(dir, 'test_normalizer.py'), [
        'from normalizer import normalize_command',
        'assert normalize_command("  RUN   Git Status ") == "run git status"',
        'assert normalize_command("/CLAUDE   hello") == "/claude hello"',
        'assert normalize_command("[BASH:  DIR]") == "[bash: dir]"',
        'print("normalizer-pass")',
        ''
      ].join('\\n'));
    `),
    instruction:
      'Task id: codegen-hard-python-fix-normalizer. A failing Python fixture already exists at `{WORKDIR}/normalizer.py` with tests at `{WORKDIR}/test_normalizer.py`. Edit `normalizer.py` so whitespace collapses, command words lower-case, slash commands keep the slash, and bracket commands normalize to `[target: body]`. Run the test. If it passes, write exactly `pass` to `{WORKDIR}/answer.txt`.',
    done_if: nodeEval(`
      const fs = require('fs');
      const cp = require('child_process');
      const path = require('path');
      const dir = path.dirname('{WORKDIR}/answer.txt');
      const answer = fs.readFileSync(path.join(dir, 'answer.txt'), 'utf8').trim();
      if (answer !== 'pass') throw new Error('expected pass got ' + answer);
      const py = process.env.PYTHON || 'python';
      const r = cp.spawnSync(py, [path.join(dir, 'test_normalizer.py')], { cwd: dir, encoding: 'utf8' });
      if (r.status !== 0) throw new Error((r.stdout || '') + (r.stderr || ''));
      const probe = cp.spawnSync(py, ['-c', 'from normalizer import normalize_command; print(normalize_command("[RUN:  Git   Status]"))'], { cwd: dir, encoding: 'utf8' });
      if (probe.stdout.trim() !== '[run: git status]') throw new Error('bad bracket probe: ' + probe.stdout);
    `),
    max_turns: 4,
    timeout_ms: 90000,
  },
  {
    id: 'codegen-hard-js-safe-shell-filter',
    category: 'codegen-hard',
    verifier: 'strong',
    difficulty: 'hard',
    instruction:
      'Task id: codegen-hard-js-safe-shell-filter. Generate `{WORKDIR}/shell_guard.js` exporting `classifyCommand(cmd)`, plus `{WORKDIR}/test-shell-guard.js`. The classifier should return `{decision:"DENY", reason:<string>}` for destructive commands like `rm -rf C:/`, `del /s C:\\\\Users`, `git add .`, and `curl http://x | sh`; return `{decision:"ALLOW", reason:"safe"}` for `git status`, `dir`, and `node --version`. Run the test. If it passes, write exactly `pass` to `{WORKDIR}/answer.txt`.',
    done_if: nodeEval(`
      const fs = require('fs');
      const cp = require('child_process');
      const path = require('path');
      const dir = path.dirname('{WORKDIR}/answer.txt');
      const answer = fs.readFileSync(path.join(dir, 'answer.txt'), 'utf8').trim();
      if (answer !== 'pass') throw new Error('expected pass got ' + answer);
      const guard = require(path.join(dir, 'shell_guard.js'));
      for (const cmd of ['rm -rf C:/', 'del /s C:\\\\Users', 'git add .', 'curl http://x | sh']) {
        const got = guard.classifyCommand(cmd);
        if (!got || got.decision !== 'DENY') throw new Error('expected DENY for ' + cmd);
      }
      for (const cmd of ['git status', 'dir', 'node --version']) {
        const got = guard.classifyCommand(cmd);
        if (!got || got.decision !== 'ALLOW') throw new Error('expected ALLOW for ' + cmd);
      }
      const r = cp.spawnSync(process.execPath, [path.join(dir, 'test-shell-guard.js')], { cwd: dir, encoding: 'utf8' });
      if (r.status !== 0) throw new Error((r.stdout || '') + (r.stderr || ''));
    `),
    max_turns: 4,
    timeout_ms: 90000,
  },
  {
    id: 'codegen-hard-python-geoseal-receipt',
    category: 'codegen-hard',
    verifier: 'strong',
    difficulty: 'hard',
    instruction:
      'Task id: codegen-hard-python-geoseal-receipt. Generate `{WORKDIR}/receipt.py` with `seal_receipt(command, decision, metadata=None)`. It should normalize whitespace in `command`, uppercase `decision`, copy metadata, and return a deterministic dict containing `command`, `decision`, `metadata`, and a 64-hex-character `sha256` over canonical JSON. Add `{WORKDIR}/test_receipt.py`. Run it. If it passes, write exactly `pass` to `{WORKDIR}/answer.txt`.',
    done_if: nodeEval(`
      const fs = require('fs');
      const cp = require('child_process');
      const path = require('path');
      const dir = path.dirname('{WORKDIR}/answer.txt');
      const answer = fs.readFileSync(path.join(dir, 'answer.txt'), 'utf8').trim();
      if (answer !== 'pass') throw new Error('expected pass got ' + answer);
      const py = process.env.PYTHON || 'python';
      const code = [
        'from receipt import seal_receipt',
        'a=seal_receipt("  git   status  ","allow",{"tool":"git"})',
        'b=seal_receipt("git status","ALLOW",{"tool":"git"})',
        'assert a==b, (a,b)',
        'assert a["command"]=="git status"',
        'assert a["decision"]=="ALLOW"',
        'assert len(a["sha256"])==64 and all(c in "0123456789abcdef" for c in a["sha256"])',
        'print("receipt-probe-pass")'
      ].join('; ');
      const probe = cp.spawnSync(py, ['-c', code], { cwd: dir, encoding: 'utf8' });
      if (probe.status !== 0) throw new Error((probe.stdout || '') + (probe.stderr || ''));
      const r = cp.spawnSync(py, [path.join(dir, 'test_receipt.py')], { cwd: dir, encoding: 'utf8' });
      if (r.status !== 0) throw new Error((r.stdout || '') + (r.stderr || ''));
    `),
    max_turns: 4,
    timeout_ms: 90000,
  },
  {
    id: 'codegen-hard-js-jsonl-redactor',
    category: 'codegen-hard',
    verifier: 'strong',
    difficulty: 'hard',
    instruction:
      'Task id: codegen-hard-js-jsonl-redactor. Generate `{WORKDIR}/jsonl_redactor.js` exporting `redactLine(line)` and `redactJsonl(text)`, plus `{WORKDIR}/test-jsonl-redactor.js`. It must parse JSONL when possible, redact emails, `sk-...` keys, `ghp_...` keys, `Bearer ...` tokens, and 12-19 digit card-like runs, then serialize JSON back to one line per record. Invalid JSON lines should be redacted as text, not dropped. Run the test. If it passes, write exactly `pass` to `{WORKDIR}/answer.txt`.',
    done_if: nodeEval(`
      const fs = require('fs');
      const cp = require('child_process');
      const path = require('path');
      const dir = path.dirname('{WORKDIR}/answer.txt');
      const answer = fs.readFileSync(path.join(dir, 'answer.txt'), 'utf8').trim();
      if (answer !== 'pass') throw new Error('expected pass got ' + answer);
      const redactor = require(path.join(dir, 'jsonl_redactor.js'));
      const input = '{"email":"me@example.com","key":"sk-abcdef1234567890","note":"Bearer abc.def.ghi"}\\nnot json ghp_abcdef1234567890 4111111111111111';
      const out = redactor.redactJsonl(input);
      for (const leak of ['me@example.com', 'sk-abcdef', 'ghp_abcdef', '4111111111111111', 'Bearer abc']) {
        if (out.includes(leak)) throw new Error('leak: ' + leak + ' in ' + out);
      }
      if (!out.includes('[secret]')) throw new Error('missing redaction marker');
      const r = cp.spawnSync(process.execPath, [path.join(dir, 'test-jsonl-redactor.js')], { cwd: dir, encoding: 'utf8' });
      if (r.status !== 0) throw new Error((r.stdout || '') + (r.stderr || ''));
    `),
    max_turns: 4,
    timeout_ms: 90000,
  },
  {
    id: 'codegen-hard-python-prime-window',
    category: 'codegen-hard',
    verifier: 'strong',
    difficulty: 'hard',
    instruction:
      'Task id: codegen-hard-python-prime-window. Generate `{WORKDIR}/prime_window.py` with `nearest_primes(n, count=3)` returning a sorted list of the nearest `count` primes to integer `n`, preferring lower primes first on equal distance. Include a runnable `{WORKDIR}/test_prime_window.py`. Run it. If it passes, write exactly `pass` to `{WORKDIR}/answer.txt`.',
    done_if: nodeEval(`
      const fs = require('fs');
      const cp = require('child_process');
      const path = require('path');
      const dir = path.dirname('{WORKDIR}/answer.txt');
      const answer = fs.readFileSync(path.join(dir, 'answer.txt'), 'utf8').trim();
      if (answer !== 'pass') throw new Error('expected pass got ' + answer);
      const py = process.env.PYTHON || 'python';
      const code = 'from prime_window import nearest_primes; assert nearest_primes(90,3)==[83,89,97]; assert nearest_primes(100,4)==[97,101,103,107]; print("prime-window-probe-pass")';
      const probe = cp.spawnSync(py, ['-c', code], { cwd: dir, encoding: 'utf8' });
      if (probe.status !== 0) throw new Error((probe.stdout || '') + (probe.stderr || ''));
      const r = cp.spawnSync(py, [path.join(dir, 'test_prime_window.py')], { cwd: dir, encoding: 'utf8' });
      if (r.status !== 0) throw new Error((r.stdout || '') + (r.stderr || ''));
    `),
    max_turns: 4,
    timeout_ms: 90000,
  },
  {
    id: 'codegen-hard-js-autocorrect-router',
    category: 'codegen-hard',
    verifier: 'strong',
    difficulty: 'hard',
    instruction:
      'Task id: codegen-hard-js-autocorrect-router. Generate `{WORKDIR}/autocorrect_router.js` exporting `routeInput(text, dictionary)`, plus a runnable test file. It should correct one-edit command typos using the dictionary keys, preserving the rest of the text: `mat 2+2` -> `{command:"math", args:"2+2"}`, `claud hello` -> `{command:"claude", args:"hello"}`, and exact `/run dir` should route to `{command:"run", args:"dir"}`. If no command matches, return `{command:"chat", args:<trimmed text>}`. If tests pass, write exactly `pass` to `{WORKDIR}/answer.txt`.',
    done_if: nodeEval(`
      const fs = require('fs');
      const cp = require('child_process');
      const path = require('path');
      const dir = path.dirname('{WORKDIR}/answer.txt');
      const answer = fs.readFileSync(path.join(dir, 'answer.txt'), 'utf8').trim();
      if (answer !== 'pass') throw new Error('expected pass got ' + answer);
      const router = require(path.join(dir, 'autocorrect_router.js'));
      const dict = { math: true, claude: true, codex: true, run: true };
      const checks = [
        ['mat 2+2', { command: 'math', args: '2+2' }],
        ['claud hello', { command: 'claude', args: 'hello' }],
        ['/run dir', { command: 'run', args: 'dir' }],
        ['ordinary words', { command: 'chat', args: 'ordinary words' }]
      ];
      for (const [input, expected] of checks) {
        const got = router.routeInput(input, dict);
        if (JSON.stringify(got) !== JSON.stringify(expected)) throw new Error(input + ' -> ' + JSON.stringify(got));
      }
      const r = cp.spawnSync(process.execPath, [path.join(dir, 'test-autocorrect-router.js')], { cwd: dir, encoding: 'utf8' });
      if (r.status !== 0) throw new Error((r.stdout || '') + (r.stderr || ''));
    `),
    max_turns: 4,
    timeout_ms: 90000,
  },
  {
    id: 'codegen-hard-python-agent-worksheet',
    category: 'codegen-hard',
    verifier: 'strong',
    difficulty: 'hard',
    instruction:
      'Task id: codegen-hard-python-agent-worksheet. Generate `{WORKDIR}/agent_worksheet.py` with `build_worksheet(sentence)`. It should return a dict with `objective`, `chunks`, and `steps`. Split the sentence into chunks of at most 5 words, infer steps for words like read, edit, test, commit, push, and preserve the original sentence as objective. Add a runnable test file. If tests pass, write exactly `pass` to `{WORKDIR}/answer.txt`.',
    done_if: nodeEval(`
      const fs = require('fs');
      const cp = require('child_process');
      const path = require('path');
      const dir = path.dirname('{WORKDIR}/answer.txt');
      const answer = fs.readFileSync(path.join(dir, 'answer.txt'), 'utf8').trim();
      if (answer !== 'pass') throw new Error('expected pass got ' + answer);
      const py = process.env.PYTHON || 'python';
      const code = [
        'from agent_worksheet import build_worksheet',
        'w=build_worksheet("read the file edit the bug test it commit and push")',
        'assert w["objective"].startswith("read the file")',
        'assert all(len(c.split())<=5 for c in w["chunks"])',
        'assert set(["read","edit","test","commit","push"]).issubset(set(w["steps"])), w',
        'print("worksheet-probe-pass")'
      ].join('; ');
      const probe = cp.spawnSync(py, ['-c', code], { cwd: dir, encoding: 'utf8' });
      if (probe.status !== 0) throw new Error((probe.stdout || '') + (probe.stderr || ''));
      const r = cp.spawnSync(py, [path.join(dir, 'test_agent_worksheet.py')], { cwd: dir, encoding: 'utf8' });
      if (r.status !== 0) throw new Error((r.stdout || '') + (r.stderr || ''));
    `),
    max_turns: 4,
    timeout_ms: 90000,
  },
  {
    id: 'codegen-hard-js-dual-file-cli',
    category: 'codegen-hard',
    verifier: 'strong',
    difficulty: 'hard',
    setup: nodeEval(`
      const fs = require('fs');
      const path = require('path');
      const dir = '{WORKDIR}';
      fs.writeFileSync(path.join(dir, 'math_ops.js'), 'module.exports = {};\\n');
      fs.writeFileSync(path.join(dir, 'cli.js'), [
        'const { sum, product } = require("./math_ops.js");',
        'const [op, ...raw] = process.argv.slice(2);',
        'const nums = raw.map(Number);',
        'if (op === "sum") console.log(sum(nums));',
        'else if (op === "product") console.log(product(nums));',
        'else { console.error("unknown op"); process.exit(2); }',
        ''
      ].join('\\n'));
    `),
    instruction:
      'Task id: codegen-hard-js-dual-file-cli. A two-file JavaScript CLI exists in `{WORKDIR}`. Edit `math_ops.js` so `node {WORKDIR}/cli.js sum 2 3 4` prints `9` and `node {WORKDIR}/cli.js product 2 3 4` prints `24`. Add a small `{WORKDIR}/test-cli.js` that checks both commands. If it passes, write exactly `pass` to `{WORKDIR}/answer.txt`.',
    done_if: nodeEval(`
      const fs = require('fs');
      const cp = require('child_process');
      const path = require('path');
      const dir = path.dirname('{WORKDIR}/answer.txt');
      const answer = fs.readFileSync(path.join(dir, 'answer.txt'), 'utf8').trim();
      if (answer !== 'pass') throw new Error('expected pass got ' + answer);
      const sum = cp.spawnSync(process.execPath, [path.join(dir, 'cli.js'), 'sum', '2', '3', '4'], { cwd: dir, encoding: 'utf8' });
      const prod = cp.spawnSync(process.execPath, [path.join(dir, 'cli.js'), 'product', '2', '3', '4'], { cwd: dir, encoding: 'utf8' });
      if (sum.stdout.trim() !== '9') throw new Error('bad sum: ' + sum.stdout + sum.stderr);
      if (prod.stdout.trim() !== '24') throw new Error('bad product: ' + prod.stdout + prod.stderr);
      const r = cp.spawnSync(process.execPath, [path.join(dir, 'test-cli.js')], { cwd: dir, encoding: 'utf8' });
      if (r.status !== 0) throw new Error((r.stdout || '') + (r.stderr || ''));
    `),
    max_turns: 4,
    timeout_ms: 90000,
  },
  {
    id: 'codegen-hard-crosslang-prime-manifest',
    category: 'codegen-hard',
    verifier: 'strong',
    difficulty: 'hard',
    instruction:
      'Task id: codegen-hard-crosslang-prime-manifest. Generate both `{WORKDIR}/prime_manifest.py` and `{WORKDIR}/prime_manifest.js`. Each must expose/print the same prime coordinate manifest for `n=90`: `{n:90, prime_depth:24, anchor:89, gap:1, omega:4, omega_distinct:3, residue30:0}`. Add tests `{WORKDIR}/test_prime_manifest.py` and `{WORKDIR}/test-prime-manifest.js`. If both tests pass and both languages agree, write exactly `pass` to `{WORKDIR}/answer.txt`.',
    done_if: nodeEval(`
      const fs = require('fs');
      const cp = require('child_process');
      const path = require('path');
      const dir = path.dirname('{WORKDIR}/answer.txt');
      const answer = fs.readFileSync(path.join(dir, 'answer.txt'), 'utf8').trim();
      if (answer !== 'pass') throw new Error('expected pass got ' + answer);
      const py = process.env.PYTHON || 'python';
      const p = cp.spawnSync(py, ['-c', 'import json, prime_manifest; print(json.dumps(prime_manifest.manifest(90), sort_keys=True))'], { cwd: dir, encoding: 'utf8' });
      const j = cp.spawnSync(process.execPath, ['-e', 'const { manifest } = require("./prime_manifest.js"); console.log(JSON.stringify(manifest(90)))'], { cwd: dir, encoding: 'utf8' });
      if (p.status !== 0 || j.status !== 0) throw new Error((p.stdout || '') + (p.stderr || '') + (j.stdout || '') + (j.stderr || ''));
      const pyObj = JSON.parse(p.stdout.trim());
      const jsObj = JSON.parse(j.stdout.trim());
      const expected = { n: 90, prime_depth: 24, anchor: 89, gap: 1, omega: 4, omega_distinct: 3, residue30: 0 };
      for (const [key, value] of Object.entries(expected)) {
        if (pyObj[key] !== value) throw new Error('bad python manifest: ' + key + '=' + pyObj[key]);
        if (jsObj[key] !== value) throw new Error('bad js manifest: ' + key + '=' + jsObj[key]);
      }
      const rt = cp.spawnSync(py, [path.join(dir, 'test_prime_manifest.py')], { cwd: dir, encoding: 'utf8' });
      const jt = cp.spawnSync(process.execPath, [path.join(dir, 'test-prime-manifest.js')], { cwd: dir, encoding: 'utf8' });
      if (rt.status !== 0 || jt.status !== 0) throw new Error((rt.stdout || '') + (rt.stderr || '') + (jt.stdout || '') + (jt.stderr || ''));
    `),
    max_turns: 4,
    timeout_ms: 90000,
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
 *   advisor: object|null,
 *   research: object|null,
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
    advisor: null,
    research: null,
    turns_log: [],
    error: null,
  };

  if (effectiveMax <= 0) {
    result.error = 'skipped: corpus turn budget exhausted';
    return result;
  }

  // Per-task tmpdir — substituted for {WORKDIR} in setup/instruction/done_if.
  // Forward-slash conversion makes it safe in shell inline-node snippets on Windows.
  const workdir = fs.mkdtempSync(path.join(os.tmpdir(), `scbe-bench-${task.id}-`));
  const safeWorkdir = workdir.split(path.sep).join('/');

  const setup = task.setup ? task.setup.replace(/\{WORKDIR\}/g, safeWorkdir) : null;
  let instruction = task.instruction.replace(/\{WORKDIR\}/g, safeWorkdir);
  const done_if = task.done_if ? task.done_if.replace(/\{WORKDIR\}/g, safeWorkdir) : null;
  const advisor = advisorConfig(opts);
  const advisorMode = advisor?.mode || 'off';
  const webQuery = opts.advisorWeb
    ? opts.advisorWebQuery || `${task.id} ${task.category} benchmark coding agent`
    : '';
  const advisorBlock = () =>
    result.advisor?.ok && result.advisor.hint
      ? '\n\nADVISOR WORKSHEET (secondary model; verifier still decides):\n' +
        result.advisor.hint.replace(/\{WORKDIR\}/g, safeWorkdir)
      : '';

  const started = Date.now();
  let proc;

  try {
    if (setup) {
      const sr = runShell(setup, 15000);
      if (sr.status !== 0) {
        result.error = `setup failed: ${[sr.stdout, sr.stderr].filter(Boolean).join('\n')}`;
        result.duration_ms = Date.now() - started;
        return result;
      }
    }

    if (advisor && opts.advisorWeb) {
      result.research = await controlledWebResearch(webQuery, {
        domains: opts.advisorWebDomains,
        maxResults: opts.advisorWebMaxResults,
      });
    }

    if (result.research?.results?.length) {
      task = { ...task, researchBrief: formatResearchBrief(result.research) };
    }

    if (advisor && advisorMode === 'preload') {
      result.advisor = callAdvisor(task, workdir, advisor);
      instruction += advisorBlock();
    }

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

      if (advisor && advisorMode !== 'preload' && !result.advisor) {
        result.advisor = callAdvisor(task, workdir, advisor);
        if (result.advisor?.ok) terminalState += advisorBlock();
      }

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
  const canRescue = Boolean(opts.rescueAdvisor && advisorConfig(opts));

  for (const task of tasks) {
    console.log(`\n${'─'.repeat(60)}`);
    console.log(
      `Task: ${task.id}  [${task.category} / ${task.difficulty} / verifier:${task.verifier}]`
    );
    console.log(`Instruction: ${task.instruction.slice(0, 100)}…`);
    console.log(
      `Max turns: ${Math.min(task.max_turns, remainingBudget)}  Budget remaining: ${remainingBudget}`
    );

    let result = await runTask(task, {
      ...opts,
      advisorProvider: opts.rescueAdvisor ? '' : opts.advisorProvider,
      advisorModel: opts.rescueAdvisor ? '' : opts.advisorModel,
      remainingBudget,
    });
    remainingBudget -= result.turns;

    if (!result.completed && canRescue && remainingBudget > 0) {
      const rescueAdvisor = advisorConfig(opts);
      console.log(
        `    rescue: verifier failed; retrying with advisor (${rescueAdvisor.provider}:${rescueAdvisor.model || '(default)'})`
      );
      const rescue = await runTask(task, {
        ...opts,
        advisorMode: opts.rescueAdvisorMode || opts.advisorMode || 'retry',
        remainingBudget,
      });
      remainingBudget -= rescue.turns;
      result = {
        ...rescue,
        turns: result.turns + rescue.turns,
        duration_ms: result.duration_ms + rescue.duration_ms,
        turns_to_complete: rescue.completed ? result.turns + rescue.turns_to_complete : null,
        rescued_by_advisor: rescue.completed,
        baseline_attempt: {
          completed: result.completed,
          turns: result.turns,
          error: result.error,
        },
        rescue_attempt: {
          completed: rescue.completed,
          turns: rescue.turns,
          error: rescue.error,
        },
      };
    }

    results.push(result);

    const status = result.completed
      ? `[PASS] in ${result.turns_to_complete} turns`
      : result.error
        ? `[ERR]  ${result.error.slice(0, 60)}`
        : `[FAIL] ${result.turns} turns, no verify`;
    console.log(
      `  → ${status}  false_done=${result.false_done_count}  ko_bans=${result.ko_ban_count}  ${result.duration_ms}ms`
    );
    if (result.advisor) {
      const advisorStatus = result.advisor.ok ? 'ok' : 'warn';
      console.log(
        `    advisor=${advisorStatus} ${result.advisor.provider}:${result.advisor.model || '(default)'} ${result.advisor.duration_ms}ms`
      );
    }
    if (result.rescued_by_advisor) console.log('    rescued_by_advisor=true');

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

function writeArtifact(results, model, provider, opts = {}) {
  if (!fs.existsSync(ARTIFACT_DIR)) fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const advisor = advisorConfig(opts);
  const artifact = {
    schema: 'task-corpus/v2',
    generated_at: new Date().toISOString(),
    commit: getHeadCommit(),
    provider: provider || process.env.SCBE_PROVIDER || 'unknown',
    model: model || process.env.SCBE_MODEL || 'unknown',
    advisor: advisor
      ? {
          provider: advisor.provider,
          model: advisor.model,
          max_chars: advisor.maxChars,
          mode: advisor.mode,
          rescue_enabled: Boolean(opts.rescueAdvisor),
          rescue_mode: opts.rescueAdvisorMode || advisor.mode || 'retry',
          web_enabled: Boolean(opts.advisorWeb),
          web_domains: opts.advisorWebDomains || null,
        }
      : null,
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

  function readOption(name) {
    const exact = args.indexOf(name);
    if (exact !== -1) return args[exact + 1] || null;
    const prefix = `${name}=`;
    const arg = args.find((a) => a.startsWith(prefix));
    return arg ? arg.slice(prefix.length) : null;
  }

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
        '  --category <name>        Run only tasks in one category',
        '  --provider <name>        Override SCBE_PROVIDER for this run',
        '  --model <name>           Override SCBE_MODEL for this run',
        '  --advisor-provider <name>  Advisor provider: offline | ollama',
        '  --advisor-model <name>   Advisor model. Defaults provider to ollama.',
        '  --advisor-max-chars=N    Max advisor worksheet chars (default: 1400)',
        '  --advisor-mode <mode>    retry (default) | preload',
        '  --advisor-web           Add controlled allowlisted web snippets to advisor prompt',
        '  --advisor-web-query <q>  Override advisor web query',
        '  --advisor-web-domain <csv>  Allowed advisor web domains',
        '  --advisor-web-max=N     Max advisor web results (1-5, default: 3)',
        '  --rescue-advisor        Run plain first; advisor retries only failed tasks',
        '  --rescue-advisor-mode <mode>  Advisor mode for rescue attempt (default: retry)',
        '  --chart                  Print difficulty/assignment chart and exit',
        '  --offline                Alias for --provider offline',
        '  --fail-on-incomplete     Exit 1 if any selected task fails verification',
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
        '  SCBE_PROVIDER=offline node scripts/bench_task_corpus.cjs --category codegen',
      ].join('\n')
    );
    process.exit(0);
  }

  const taskFilter = readOption('--task');
  const categoryFilter = readOption('--category');
  const providerOverride = args.includes('--offline') ? 'offline' : readOption('--provider');
  if (providerOverride) process.env.SCBE_PROVIDER = providerOverride;
  const modelOverride = readOption('--model');
  if (modelOverride) process.env.SCBE_MODEL = modelOverride;
  const noArtifact = args.includes('--no-artifact');
  const failOnIncomplete = args.includes('--fail-on-incomplete');
  const advisorProvider = readOption('--advisor-provider');
  const advisorModel = readOption('--advisor-model') || readOption('--advisor');
  const advisorMaxChars = readOption('--advisor-max-chars');
  const advisorMode = readOption('--advisor-mode');
  const advisorWeb = args.includes('--advisor-web') || process.env.SCBE_ADVISOR_WEB === '1';
  const advisorWebQuery = readOption('--advisor-web-query') || process.env.SCBE_ADVISOR_WEB_QUERY;
  const advisorWebDomains =
    readOption('--advisor-web-domain') ||
    readOption('--advisor-web-domains') ||
    process.env.SCBE_ADVISOR_WEB_DOMAINS;
  const advisorWebMaxResults = readOption('--advisor-web-max') || process.env.SCBE_ADVISOR_WEB_MAX;
  const rescueAdvisor = args.includes('--rescue-advisor');
  const rescueAdvisorMode = readOption('--rescue-advisor-mode');
  const maxTurnsArg = readOption('--max-corpus-turns');
  const maxCorpusTurns = maxTurnsArg ? parseInt(maxTurnsArg, 10) : 80;

  let tasksToRun = TASKS;
  if (taskFilter) tasksToRun = tasksToRun.filter((t) => t.id === taskFilter);
  if (categoryFilter) tasksToRun = tasksToRun.filter((t) => t.category === categoryFilter);
  if (!tasksToRun.length) {
    console.error(
      `No task found matching: task=${taskFilter || '*'} category=${categoryFilter || '*'}`
    );
    process.exit(1);
  }

  const model = process.env.SCBE_MODEL || '(default)';
  const provider = process.env.SCBE_PROVIDER || 'ollama';
  console.log(`\nTask Corpus Bench v2 — provider=${provider} model=${model}`);
  console.log(`Tasks: ${tasksToRun.length}  Corpus turn budget: ${maxCorpusTurns}`);
  console.log(
    'Verifier contract v2: {WORKDIR}/answer.txt per task — no static-state false positives\n'
  );

  const runOpts = {
    maxCorpusTurns,
    advisorProvider,
    advisorModel,
    advisorMaxChars,
    advisorMode,
    advisorWeb,
    advisorWebQuery,
    advisorWebDomains,
    advisorWebMaxResults,
    rescueAdvisor,
    rescueAdvisorMode,
  };

  if (args.includes('--chart')) {
    printAssignmentChart(tasksToRun, {
      provider,
      model,
      advisorProvider,
      advisorModel,
      advisorMaxChars,
      advisorMode,
    });
    process.exit(0);
  }

  const results = await runCorpus(tasksToRun, runOpts);

  printSummaryTable(results);

  if (!noArtifact) {
    const artifactPath = writeArtifact(results, model, provider, runOpts);
    console.log(`\nArtifact: ${artifactPath}`);
  }

  const hasIncomplete = results.some((r) => !r.completed);
  process.exit(failOnIncomplete && hasIncomplete ? 1 : 0);
})();
