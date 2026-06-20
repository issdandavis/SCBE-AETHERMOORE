#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const ARTIFACT_DIR = path.join(REPO_ROOT, 'artifacts', 'benchmarks', 'direct-codegen');

const TASKS = {
  'codegen-hard-python-agent-worksheet': {
    language: 'python',
    files: ['agent_worksheet.py', 'test_agent_worksheet.py'],
    instruction:
      'Generate agent_worksheet.py with build_worksheet(sentence). It should return a dict with objective, chunks, and steps. Split the sentence into chunks of at most 5 words, infer steps for words like read, edit, test, commit, push, and preserve the original sentence as objective. Also generate test_agent_worksheet.py.',
    verify(dir) {
      const testPath = path.join(dir, 'test_agent_worksheet.py');
      if (!fs.existsSync(path.join(dir, 'agent_worksheet.py')))
        return fail('missing agent_worksheet.py');
      if (!fs.existsSync(testPath)) return fail('missing test_agent_worksheet.py');
      const probe = [
        'from agent_worksheet import build_worksheet',
        'w=build_worksheet("read the file edit the bug test it commit and push")',
        'assert isinstance(w, dict)',
        'assert w["objective"].startswith("read the file")',
        'assert len(w["chunks"]) >= 2',
        'assert any("test" in str(s).lower() for s in w["steps"])',
        'assert any("commit" in str(s).lower() for s in w["steps"])',
        'print("worksheet-probe-pass")',
      ].join('\n');
      const probePath = path.join(dir, '_probe_agent_worksheet.py');
      fs.writeFileSync(probePath, probe, 'utf8');
      return run(process.env.PYTHON || 'python', [probePath], dir, 30_000);
    },
  },
  'codegen-hard-python-prime-window': {
    language: 'python',
    files: ['prime_window.py', 'test_prime_window.py'],
    instruction:
      'Generate prime_window.py with nearest_primes(n, count=3) returning a sorted list of the nearest count primes to integer n, preferring lower primes first on equal distance. Also generate test_prime_window.py.',
    verify(dir) {
      if (!fs.existsSync(path.join(dir, 'prime_window.py'))) return fail('missing prime_window.py');
      const probe = [
        'from prime_window import nearest_primes',
        'assert nearest_primes(20, 3) == [17, 19, 23]',
        'assert nearest_primes(29, 3) == [23, 29, 31]',
        'assert nearest_primes(1, 3) == [2, 3, 5]',
        'print("prime-window-probe-pass")',
      ].join('\n');
      const probePath = path.join(dir, '_probe_prime_window.py');
      fs.writeFileSync(probePath, probe, 'utf8');
      return run(process.env.PYTHON || 'python', [probePath], dir, 30_000);
    },
  },
  'codegen-hard-js-jsonl-redactor': {
    language: 'javascript',
    files: ['jsonl_redactor.js', 'test-jsonl-redactor.js'],
    instruction:
      'Generate jsonl_redactor.js exporting redactJsonl(text). It should parse newline-delimited JSON, redact values for keys token, password, secret, api_key, and authorization, preserve other fields, skip blank lines, and throw on invalid JSON. Also generate test-jsonl-redactor.js.',
    verify(dir) {
      if (!fs.existsSync(path.join(dir, 'jsonl_redactor.js')))
        return fail('missing jsonl_redactor.js');
      const probe = [
        "const { redactJsonl } = require('./jsonl_redactor.js');",
        'const out = redactJsonl(\'{"user":"a","token":"abc"}\\n{"ok":true,"password":"pw"}\\n\');',
        'const rows = out.trim().split(/\\n/).map(JSON.parse);',
        "if (rows[0].token !== '[REDACTED]') throw new Error('token not redacted');",
        "if (rows[1].password !== '[REDACTED]') throw new Error('password not redacted');",
        "if (rows[0].user !== 'a' || rows[1].ok !== true) throw new Error('fields not preserved');",
        "let threw=false; try { redactJsonl('{bad'); } catch (_) { threw=true; }",
        "if (!threw) throw new Error('invalid JSON must throw');",
        "console.log('jsonl-redactor-probe-pass');",
      ].join('\n');
      const probePath = path.join(dir, '_probe_jsonl_redactor.js');
      fs.writeFileSync(probePath, probe, 'utf8');
      return run(process.execPath, [probePath], dir, 30_000);
    },
  },
};

function fail(error) {
  return { ok: false, status: 1, stdout: '', stderr: error };
}

function run(command, args, cwd, timeoutMs) {
  const result = spawnSync(command, args, {
    cwd,
    encoding: 'utf8',
    timeout: timeoutMs,
    maxBuffer: 1024 * 1024 * 4,
  });
  return {
    ok: result.status === 0,
    status: typeof result.status === 'number' ? result.status : null,
    stdout: (result.stdout || '').trim(),
    stderr: (result.stderr || result.error?.message || '').trim(),
  };
}

function parseArgs(argv) {
  const opts = {
    provider: 'ollama',
    model: process.env.OLLAMA_MODEL || 'qwen2.5-coder:1.5b',
    task: 'codegen-hard-python-agent-worksheet',
    routerProvider: '',
    output: '',
    json: false,
    noArtifact: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--provider') opts.provider = argv[++i] || opts.provider;
    else if (arg.startsWith('--provider=')) opts.provider = arg.slice('--provider='.length);
    else if (arg === '--model') opts.model = argv[++i] || opts.model;
    else if (arg.startsWith('--model=')) opts.model = arg.slice('--model='.length);
    else if (arg === '--task') opts.task = argv[++i] || opts.task;
    else if (arg.startsWith('--task=')) opts.task = arg.slice('--task='.length);
    else if (arg === '--router-provider') opts.routerProvider = argv[++i] || opts.routerProvider;
    else if (arg.startsWith('--router-provider=')) {
      opts.routerProvider = arg.slice('--router-provider='.length);
    } else if (arg === '--output') opts.output = argv[++i] || '';
    else if (arg.startsWith('--output=')) opts.output = arg.slice('--output='.length);
    else if (arg === '--json') opts.json = true;
    else if (arg === '--no-artifact') opts.noArtifact = true;
    else if (arg === '--list') opts.list = true;
    else if (arg === '--help' || arg === '-h') opts.help = true;
  }
  return opts;
}

function buildPrompt(taskId, task) {
  return [
    'You are being graded by a direct code-generation benchmark.',
    'No terminal tools are available. Return only JSON, no markdown.',
    'Schema: {"files":{"filename.ext":"full file content"}}',
    'Do not include explanations. Do not include code fences.',
    '',
    `Task id: ${taskId}`,
    `Language: ${task.language}`,
    `Required files: ${task.files.join(', ')}`,
    task.instruction,
  ].join('\n');
}

function extractJsonObject(text) {
  const raw = String(text || '').trim();
  try {
    return JSON.parse(raw);
  } catch (_) {}
  const start = raw.indexOf('{');
  const end = raw.lastIndexOf('}');
  if (start === -1 || end === -1 || end <= start) {
    throw new Error('model output did not contain a JSON object');
  }
  return JSON.parse(raw.slice(start, end + 1));
}

async function callOllama(prompt, model) {
  const base = (process.env.OLLAMA_BASE_URL || process.env.OLLAMA_URL || 'http://127.0.0.1:11434')
    .replace(/\/+$/g, '')
    .replace(/\/api$/i, '');
  const response = await fetch(`${base}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(process.env.OLLAMA_API_KEY
        ? { Authorization: `Bearer ${process.env.OLLAMA_API_KEY}` }
        : {}),
    },
    body: JSON.stringify({
      model,
      stream: false,
      options: { temperature: 0 },
      messages: [{ role: 'user', content: prompt }],
    }),
    signal: AbortSignal.timeout(120_000),
  });
  const body = await response.text();
  if (!response.ok) throw new Error(`ollama HTTP ${response.status}: ${body.slice(0, 240)}`);
  const parsed = JSON.parse(body);
  return String(parsed.message?.content || parsed.response || '').trim();
}

function callRouter(prompt, opts) {
  const promptFile = path.join(os.tmpdir(), `scbe-direct-codegen-${Date.now()}-${process.pid}.txt`);
  fs.writeFileSync(promptFile, prompt, 'utf8');
  const providers = opts.routerProvider || opts.provider;
  const args = [
    'scripts/system/terminal_ai_router.py',
    'call',
    '--prompt-file',
    promptFile,
    '--providers',
    providers,
    '--complexity',
    'hard',
    '--temperature',
    '0',
    '--max-output-tokens',
    '4096',
    '--response-only',
  ];
  const result = spawnSync(process.env.PYTHON || 'python', args, {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    timeout: 180_000,
    maxBuffer: 1024 * 1024 * 6,
  });
  try {
    fs.rmSync(promptFile, { force: true });
  } catch (_) {}
  if (result.status !== 0) {
    throw new Error(
      (result.stderr || result.stdout || result.error?.message || 'router failed').trim()
    );
  }
  return (result.stdout || '').trim();
}

function writeFiles(workdir, files) {
  if (!files || typeof files !== 'object' || Array.isArray(files)) {
    throw new Error('JSON missing object field "files"');
  }
  const written = [];
  for (const [name, content] of Object.entries(files)) {
    const clean = path.basename(String(name));
    if (!clean || clean === '.' || clean === '..') continue;
    const filePath = path.join(workdir, clean);
    fs.writeFileSync(filePath, String(content), 'utf8');
    written.push(clean);
  }
  return written.sort();
}

function writeArtifact(payload, output) {
  const out =
    output ||
    path.join(
      ARTIFACT_DIR,
      `${new Date().toISOString().replace(/[:.]/g, '-')}-${payload.provider}-${payload.model.replace(/[^a-z0-9_.:-]+/gi, '_')}.json`
    );
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify(payload, null, 2));
  return out;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    console.log(
      [
        'Usage: node packages/cli/scripts/bench_direct_codegen.cjs [options]',
        '',
        'Options:',
        '  --task <id>                 Task id; use --list for options',
        '  --provider ollama|router    Direct Ollama or terminal_ai_router',
        '  --model <ollama-model>      Ollama model',
        '  --router-provider <name>    cerebras|anthropic|huggingface|...',
        '  --json                      Print JSON payload',
        '  --no-artifact               Do not write artifact',
        '  --output <path>             Artifact output path',
      ].join('\n')
    );
    return;
  }
  if (opts.list) {
    for (const [id, task] of Object.entries(TASKS)) {
      console.log(`${id} [${task.language}] files=${task.files.join(',')}`);
    }
    return;
  }
  const task = TASKS[opts.task];
  if (!task) throw new Error(`unknown task: ${opts.task}`);
  const modelLabel =
    opts.provider === 'router'
      ? `terminal_ai_router:${opts.routerProvider || opts.provider}`
      : opts.model;

  const workdir = fs.mkdtempSync(path.join(os.tmpdir(), `scbe-direct-${opts.task}-`));
  const started = Date.now();
  const prompt = buildPrompt(opts.task, task);
  let payload;
  try {
    const text =
      opts.provider === 'router' ? callRouter(prompt, opts) : await callOllama(prompt, opts.model);
    const parsed = extractJsonObject(text);
    const written = writeFiles(workdir, parsed.files);
    const verify = task.verify(workdir);
    payload = {
      schema: 'scbe.direct_codegen_bench.v1',
      generated_at: new Date().toISOString(),
      provider: opts.provider,
      router_provider: opts.routerProvider || null,
      model: modelLabel,
      task: opts.task,
      mode: 'direct-no-terminal-harness',
      completed: verify.ok,
      duration_ms: Date.now() - started,
      workdir,
      written_files: written,
      verifier: {
        status: verify.status,
        stdout: verify.stdout.slice(0, 1000),
        stderr: verify.stderr.slice(0, 1000),
      },
      output_preview: text.slice(0, 800),
    };
  } catch (error) {
    payload = {
      schema: 'scbe.direct_codegen_bench.v1',
      generated_at: new Date().toISOString(),
      provider: opts.provider,
      router_provider: opts.routerProvider || null,
      model: modelLabel,
      task: opts.task,
      mode: 'direct-no-terminal-harness',
      completed: false,
      duration_ms: Date.now() - started,
      workdir,
      error: error.message,
    };
  }
  if (!opts.noArtifact) payload.artifact = writeArtifact(payload, opts.output);
  if (opts.json) {
    console.log(JSON.stringify(payload, null, 2));
  } else {
    console.log(
      `${payload.completed ? 'PASS' : 'FAIL'} direct ${payload.provider}:${payload.router_provider || payload.model} ${payload.task} ${payload.duration_ms}ms`
    );
    if (payload.artifact) console.log(`Artifact: ${payload.artifact}`);
    if (payload.error) console.log(`Error: ${payload.error}`);
    if (payload.verifier?.stderr) console.log(`Verifier stderr: ${payload.verifier.stderr}`);
  }
  process.exit(payload.completed ? 0 : 1);
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
