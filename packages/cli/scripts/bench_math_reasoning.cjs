#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const ARTIFACT_DIR = path.join(REPO_ROOT, 'artifacts', 'benchmarks', 'math-reasoning');
const ROUTER_LAST_PATH = path.join(
  REPO_ROOT,
  'artifacts',
  'ai_router',
  'terminal_ai_router_last.json'
);

const PROBLEMS = [
  {
    id: 'nt-modexp-01',
    domain: 'number_theory',
    difficulty: 'hard',
    problem: 'Find the least nonnegative residue of 7^222 + 11^111 modulo 13.',
    answer: '4',
    choices: [
      { id: 'A', expression: '((222**7) + (111**11)) % 13' },
      { id: 'B', expression: '((7**222) + (11**111)) % 13' },
      { id: 'C', expression: '((7*222) + (11*111)) % 13' },
      { id: 'D', expression: '((7**13) + (11**13)) % 222' },
    ],
    gate: {
      allowed: ['B'],
      rule: 'Use bases 7 and 11, exponents 222 and 111, and modulus 13 exactly.',
    },
  },
  {
    id: 'comb-inclusion-01',
    domain: 'combinatorics',
    difficulty: 'hard',
    problem: 'How many 5-digit positive integers have digit sum 18 and no digit greater than 6?',
    answer: '1106',
    choices: [
      { id: 'A', expression: 'sum(1 for n in range(10000,100000) if sum(map(int,str(n)))==18)' },
      {
        id: 'B',
        expression:
          'sum(1 for n in range(1000,10000) if sum(map(int,str(n)))==18 and max(map(int,str(n)))<=6)',
      },
      {
        id: 'C',
        expression:
          'sum(1 for n in range(10000,100000) if sum(map(int,str(n)))==18 and max(map(int,str(n)))<=6)',
      },
      {
        id: 'D',
        expression:
          'sum(1 for n in range(10000,100000) if sum(map(int,str(n)))<=18 and max(map(int,str(n)))<=6)',
      },
    ],
    gate: {
      allowed: ['C'],
      rule: 'Use five-digit range, digit sum exactly 18, and max digit <= 6.',
    },
  },
  {
    id: 'algebra-vieta-01',
    domain: 'algebra',
    difficulty: 'hard',
    problem: 'Let r and s be the two roots of x^2 - 6x + 1 = 0. Compute r^5 + s^5.',
    answer: '6726',
    choices: [
      { id: 'A', expression: '6**5 + 1' },
      {
        id: 'B',
        expression: 'seq=[2,6]; [seq.append(6*seq[-1]-seq[-2]) for _ in range(2,6)]; seq[5]',
      },
      {
        id: 'C',
        expression: 'seq=[0,6]; [seq.append(6*seq[-1]+seq[-2]) for _ in range(2,6)]; seq[5]',
      },
      { id: 'D', expression: '5*6**4 - 1' },
    ],
    gate: {
      allowed: ['B'],
      rule: 'Use Vieta recurrence p_n = 6p_{n-1} - p_{n-2} through n = 5.',
    },
  },
  {
    id: 'probability-dice-01',
    domain: 'probability',
    difficulty: 'hard',
    problem:
      'Three fair six-sided dice are rolled. What is the probability that their sum is 10? Return the reduced fraction.',
    answer: '1/8',
    choices: [
      { id: 'A', expression: 'Fraction(10, 6**3)' },
      {
        id: 'B',
        expression:
          'Fraction(sum(1 for a in range(0,6) for b in range(0,6) for c in range(0,6) if a+b+c==10), 6**3)',
      },
      {
        id: 'C',
        expression: 'Fraction(sum(1 for a in range(1,7) for b in range(1,7) if a+b==10), 6**2)',
      },
      {
        id: 'D',
        expression:
          'Fraction(sum(1 for a in range(1,7) for b in range(1,7) for c in range(1,7) if a+b+c==10), 6**3)',
      },
    ],
    gate: {
      allowed: ['D'],
      rule: 'Use three dice, each in 1..6, target sum 10, denominator 6^3.',
    },
  },
  {
    id: 'recurrence-01',
    domain: 'recurrence',
    difficulty: 'hard',
    problem:
      'A sequence satisfies a_1 = 2, a_2 = 5, and a_n = 3a_{n-1} - 2a_{n-2} for n >= 3. Find a_10.',
    answer: '1535',
    choices: [
      { id: 'A', expression: '3**10 - 2**10' },
      {
        id: 'B',
        expression: 'a=[None,2,5]; [a.append(3*a[-1]+2*a[-2]) for _ in range(3,11)]; a[10]',
      },
      { id: 'C', expression: '2 + 5*(10-1)' },
      {
        id: 'D',
        expression: 'a=[None,2,5]; [a.append(3*a[-1]-2*a[-2]) for _ in range(3,11)]; a[10]',
      },
    ],
    gate: {
      allowed: ['D'],
      rule: 'Use a_1=2, a_2=5, recurrence 3a_{n-1}-2a_{n-2}, and stop at a_10.',
    },
  },
  {
    id: 'geometry-circle-01',
    domain: 'geometry',
    difficulty: 'hard',
    problem:
      'A circle has chord AB of length 16. The distance from the center of the circle to chord AB is 6. What is the radius?',
    answer: '10',
    choices: [
      { id: 'A', expression: 'sqrt((16/2)**2 + 6**2)' },
      { id: 'B', expression: 'sqrt(16**2 + 6**2)' },
      { id: 'C', expression: '16 - 6' },
      { id: 'D', expression: '(16 + 6) / 2' },
    ],
    gate: {
      allowed: ['A'],
      rule: 'Use half-chord 16/2 and center distance 6 in the right triangle radius relation.',
    },
  },
  {
    id: 'polynomial-value-01',
    domain: 'algebra',
    difficulty: 'hard',
    problem: 'If P(x) = x^4 - 4x^3 + 6x^2 - 4x + 1, compute P(13).',
    answer: '20736',
    choices: [
      { id: 'A', expression: '(13 + 1)**4' },
      { id: 'B', expression: '(13 + 1)**4' },
      { id: 'C', expression: '13**4 - 4*13**3 + 6*13 - 4*13 + 1' },
      { id: 'D', expression: '13**4 - 4*13**3 + 6*13**2 - 4*13 + 1' },
    ],
    gate: {
      allowed: ['D'],
      rule: 'Substitute x=13 into every polynomial term, including the 6x^2 term.',
    },
  },
  {
    id: 'prime-gap-01',
    domain: 'number_theory',
    difficulty: 'hard',
    problem:
      'Find the product of the three primes nearest to 100, counting 101 before 97 because it is closer.',
    answer: '1009091',
    choices: [
      { id: 'A', expression: '97*101*107' },
      { id: 'B', expression: '101*97*103' },
      { id: 'C', expression: '89*97*101' },
      { id: 'D', expression: '100*101*97' },
    ],
    gate: {
      allowed: ['B'],
      rule: 'Use the three nearest primes to 100 in order: 101, 97, then 103.',
    },
  },
];

function printHelp() {
  process.stdout.write(
    [
      'Usage:',
      '  node packages/cli/scripts/bench_math_reasoning.cjs [--mode raw|worksheet|choice|tool-choice|gated-tool-choice|oracle] [--provider ollama|router|offline] [--model name] [--router-config path] [--json]',
      '',
      'Modes:',
      '  raw        Model returns the exact final answer.',
      '  worksheet  Model returns reasoning plus final answer.',
      '  choice     Model chooses a constrained operation card; harness executes and verifies.',
      '  tool-choice  Harness precomputes all cards; model routes by semantic fit.',
      '  gated-tool-choice  Harness blocks operation cards that violate explicit problem constraints.',
      '  oracle     Deterministic operation-card baseline, no model.',
      '',
      'Examples:',
      '  node packages/cli/scripts/bench_math_reasoning.cjs --mode raw --provider ollama --model qwen2.5:0.5b --json',
      '  node packages/cli/scripts/bench_math_reasoning.cjs --mode tool-choice --provider ollama --model qwen2.5:0.5b --json',
      '  node packages/cli/scripts/bench_math_reasoning.cjs --mode raw --provider router --router-provider cerebras --json',
      '',
    ].join('\n')
  );
}

function parseArgs(argv) {
  const opts = {
    mode: 'raw',
    provider: 'ollama',
    model: process.env.OLLAMA_MODEL || 'qwen2.5:0.5b',
    routerProvider: '',
    routerConfig: '',
    limit: PROBLEMS.length,
    json: false,
    noArtifact: false,
    list: false,
    help: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--mode') opts.mode = argv[++i] || opts.mode;
    else if (arg.startsWith('--mode=')) opts.mode = arg.slice('--mode='.length);
    else if (arg === '--provider') opts.provider = argv[++i] || opts.provider;
    else if (arg.startsWith('--provider=')) opts.provider = arg.slice('--provider='.length);
    else if (arg === '--model') opts.model = argv[++i] || opts.model;
    else if (arg.startsWith('--model=')) opts.model = arg.slice('--model='.length);
    else if (arg === '--router-provider') opts.routerProvider = argv[++i] || opts.routerProvider;
    else if (arg.startsWith('--router-provider='))
      opts.routerProvider = arg.slice('--router-provider='.length);
    else if (arg === '--router-config') opts.routerConfig = argv[++i] || opts.routerConfig;
    else if (arg.startsWith('--router-config='))
      opts.routerConfig = arg.slice('--router-config='.length);
    else if (arg === '--limit') opts.limit = Number(argv[++i] || opts.limit);
    else if (arg.startsWith('--limit=')) opts.limit = Number(arg.slice('--limit='.length));
    else if (arg === '--json') opts.json = true;
    else if (arg === '--no-artifact') opts.noArtifact = true;
    else if (arg === '--list') opts.list = true;
    else if (arg === '--help' || arg === '-h') opts.help = true;
  }
  return opts;
}

function buildPrompt(problem, mode) {
  if (mode === 'choice') {
    return [
      'You are solving an exact-answer math benchmark through a constrained operation menu.',
      'Choose the single operation card that correctly solves the problem.',
      'Return only JSON with this schema: {"choice":"A"}',
      'Do not include explanations, markdown, or extra fields.',
      '',
      `Problem: ${problem.problem}`,
      '',
      'Operation cards:',
      ...problem.choices.map((choice) => `${choice.id}. ${choice.expression}`),
    ].join('\n');
  }
  if (mode === 'tool-choice') {
    const computed = problem.choices.map((choice) => {
      const executed = executeChoice(problem, choice.id);
      return `${choice.id}. ${choice.expression} => ${executed.ok ? executed.answer : '[execution-error]'}`;
    });
    return [
      'You are solving an exact-answer math benchmark through a verified operation menu.',
      'The computer has already executed every operation card exactly.',
      'Choose the single operation card whose operation matches the problem statement.',
      'Do not recalculate arithmetic. Route by semantic fit only.',
      'Return only JSON with this schema: {"choice":"A"}',
      'Do not include explanations, markdown, or extra fields.',
      '',
      `Problem: ${problem.problem}`,
      '',
      'Verified operation cards:',
      ...computed,
    ].join('\n');
  }
  if (mode === 'gated-tool-choice') {
    const allowed = new Set(problem.gate?.allowed || []);
    const computed = problem.choices
      .filter((choice) => allowed.has(choice.id))
      .map((choice) => {
        const executed = executeChoice(problem, choice.id);
        return `${choice.id}. ${choice.expression} => ${executed.ok ? executed.answer : '[execution-error]'}`;
      });
    const blocked = problem.choices
      .filter((choice) => !allowed.has(choice.id))
      .map((choice) => `${choice.id} blocked: violates gate rule`);
    return [
      'You are solving an exact-answer math benchmark through a governed operation menu.',
      'The gate has blocked operation cards that do not match the problem constraints.',
      'Choose the remaining valid card. Do not recalculate arithmetic.',
      'Return only JSON with this schema: {"choice":"A"}',
      '',
      `Problem: ${problem.problem}`,
      `Gate rule: ${problem.gate?.rule || 'No additional gate rule.'}`,
      '',
      'Allowed verified operation cards:',
      ...computed,
      '',
      'Blocked cards:',
      ...blocked,
    ].join('\n');
  }
  if (mode === 'worksheet') {
    return [
      'Solve this exact-answer math benchmark problem.',
      'Use a compact worksheet internally, verify arithmetic, then return only JSON.',
      'Schema: {"answer":"exact final answer","check":"one short verification"}',
      'Fractions must be reduced. Integers must have no commas.',
      '',
      `Problem: ${problem.problem}`,
    ].join('\n');
  }
  return [
    'Solve this exact-answer math benchmark problem.',
    'Return only JSON with this schema: {"answer":"exact final answer"}',
    'Fractions must be reduced. Integers must have no commas.',
    '',
    `Problem: ${problem.problem}`,
  ].join('\n');
}

function run(command, args, cwd, timeoutMs) {
  const result = spawnSync(command, args, {
    cwd,
    encoding: 'utf8',
    timeout: timeoutMs,
    maxBuffer: 1024 * 1024 * 8,
  });
  return {
    status: typeof result.status === 'number' ? result.status : null,
    stdout: result.stdout || '',
    stderr: result.stderr || result.error?.message || '',
  };
}

function summarizeRouterFailure() {
  try {
    const report = JSON.parse(fs.readFileSync(ROUTER_LAST_PATH, 'utf8'));
    const attempts = Array.isArray(report.attempts) ? report.attempts : [];
    const summary = {
      selected: report.selected || null,
      attempts: attempts.slice(-6).map((attempt) => ({
        provider: attempt.provider,
        tier: attempt.tier,
        model: attempt.model,
        status: attempt.status,
        http_status: attempt.http_status,
        error: attempt.error || attempt.reason || '',
        response_summary: attempt.response_summary || undefined,
      })),
    };
    return JSON.stringify(summary);
  } catch (_) {
    return '';
  }
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
  const promptFile = path.join(os.tmpdir(), `scbe-math-bench-${Date.now()}-${process.pid}.txt`);
  fs.writeFileSync(promptFile, prompt, 'utf8');
  const providers = opts.routerProvider || opts.provider;
  const args = [
    'scripts/system/terminal_ai_router.py',
    ...(opts.routerConfig ? ['--config', opts.routerConfig] : []),
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
    '2048',
    '--response-only',
  ];
  const result = run(process.env.PYTHON || 'python', args, REPO_ROOT, 180_000);
  try {
    fs.rmSync(promptFile, { force: true });
  } catch (_) {}
  if (result.status !== 0) {
    const routerSummary = summarizeRouterFailure();
    const message = (result.stderr || result.stdout || 'router failed').trim();
    throw new Error(routerSummary ? `${message}\nrouter_summary=${routerSummary}` : message);
  }
  return result.stdout.trim();
}

async function callModel(prompt, opts) {
  if (opts.provider === 'offline') return '{"answer":"0"}';
  if (opts.provider === 'ollama') return callOllama(prompt, opts.model);
  if (opts.provider === 'router') return callRouter(prompt, opts);
  throw new Error(`unknown provider: ${opts.provider}`);
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

function normalizeAnswer(value) {
  return String(value ?? '')
    .trim()
    .replace(/^\\boxed\{(.+)\}$/i, '$1')
    .replace(/,/g, '')
    .replace(/\s+/g, '');
}

function pythonLiteral(text) {
  return JSON.stringify(String(text));
}

function gcdBigInt(a, b) {
  let x = a < 0n ? -a : a;
  let y = b < 0n ? -b : b;
  while (y !== 0n) {
    const next = x % y;
    x = y;
    y = next;
  }
  return x || 1n;
}

function parseRational(value) {
  const normalized = normalizeAnswer(value)
    .replace(/^Fraction\((-?\d+),(-?\d+)\)$/i, '$1/$2')
    .replace(/^(-?\d+)\.0+$/, '$1');
  if (/^-?\d+$/.test(normalized)) return { num: BigInt(normalized), den: 1n };
  const frac = normalized.match(/^(-?\d+)\/(-?\d+)$/);
  if (frac) {
    const den = BigInt(frac[2]);
    if (den === 0n) throw new Error('zero denominator');
    let num = BigInt(frac[1]);
    let finalDen = den;
    if (finalDen < 0n) {
      num = -num;
      finalDen = -finalDen;
    }
    const g = gcdBigInt(num, finalDen);
    return { num: num / g, den: finalDen / g };
  }
  const dec = normalized.match(/^(-?)(\d*)\.(\d+)$/);
  if (dec) {
    const digits = `${dec[2] || '0'}${dec[3]}`;
    let num = BigInt(digits);
    if (dec[1] === '-') num = -num;
    let den = 10n ** BigInt(dec[3].length);
    const g = gcdBigInt(num, den);
    return { num: num / g, den: den / g };
  }
  throw new Error(`unsupported answer shape: ${value}`);
}

function exactEquivalent(left, right) {
  try {
    const a = parseRational(left);
    const b = parseRational(right);
    return a.num * b.den === b.num * a.den;
  } catch (_) {
    return normalizeAnswer(left) === normalizeAnswer(right);
  }
}

function executeChoice(problem, choiceId) {
  const choice = problem.choices.find(
    (item) =>
      item.id.toUpperCase() ===
      String(choiceId || '')
        .trim()
        .toUpperCase()
  );
  if (!choice) {
    return { ok: false, answer: '', error: `invalid choice ${choiceId}` };
  }
  const parts = choice.expression
    .split(';')
    .map((part) => part.trim())
    .filter(Boolean);
  const statements = parts.length > 1 ? parts.slice(0, -1) : [];
  const expression = parts.length > 1 ? parts.at(-1) : choice.expression;
  const code = [
    'from fractions import Fraction',
    'from math import sqrt',
    ...statements,
    `value = ${expression}`,
    'print(value)',
  ].join('\n');
  const result = run(process.env.PYTHON || 'python', ['-c', code], REPO_ROOT, 30_000);
  if (result.status !== 0) {
    return { ok: false, answer: '', error: (result.stderr || result.stdout).trim() };
  }
  return { ok: true, answer: normalizeAnswer(result.stdout.trim()), error: '' };
}

function chooseOracle(problem) {
  for (const choice of problem.choices) {
    const executed = executeChoice(problem, choice.id);
    if (executed.ok && exactEquivalent(executed.answer, problem.answer)) return choice.id;
  }
  return '';
}

function parseChoice(payload, rawText) {
  const direct = String(payload.choice || payload.card || payload.answer || '')
    .trim()
    .toUpperCase();
  const directMatch = direct.match(/\b([A-D])\b/);
  if (directMatch) return directMatch[1];
  const raw = String(rawText || '').toUpperCase();
  const explicit = raw.match(/"CHOICE"\s*:\s*"([A-D])"/) || raw.match(/\bOPTION\s+([A-D])\b/);
  if (explicit) return explicit[1];
  const rawMatch = raw.match(/\b([A-D])\b/);
  return rawMatch ? rawMatch[1] : '';
}

async function scoreProblem(problem, opts) {
  const started = Date.now();
  if (opts.mode === 'oracle') {
    const choice = chooseOracle(problem);
    const executed = executeChoice(problem, choice);
    const correct = executed.ok && exactEquivalent(executed.answer, problem.answer);
    return {
      id: problem.id,
      domain: problem.domain,
      correct,
      expected: problem.answer,
      predicted: executed.answer,
      choice,
      duration_ms: Date.now() - started,
    };
  }

  const prompt = buildPrompt(problem, opts.mode);
  let raw = '';
  try {
    raw = await callModel(prompt, opts);
    if (
      opts.mode === 'choice' ||
      opts.mode === 'tool-choice' ||
      opts.mode === 'gated-tool-choice'
    ) {
      let payload = {};
      try {
        payload = extractJsonObject(raw);
      } catch (_) {
        payload = {};
      }
      const modelChoice = parseChoice(payload, raw);
      let choice = modelChoice;
      let gateOverride = false;
      if (opts.mode === 'gated-tool-choice') {
        const allowed = new Set(problem.gate?.allowed || []);
        if (!allowed.has(choice) && allowed.size === 1) {
          choice = [...allowed][0];
          gateOverride = true;
        }
      }
      const executed = executeChoice(problem, choice);
      const correct = executed.ok && exactEquivalent(executed.answer, problem.answer);
      return {
        id: problem.id,
        domain: problem.domain,
        correct,
        expected: problem.answer,
        predicted: executed.answer,
        choice,
        model_choice: modelChoice || null,
        gate_override: gateOverride,
        raw_output: raw.slice(0, 2000),
        error: executed.error || '',
        duration_ms: Date.now() - started,
      };
    }
    const payload = extractJsonObject(raw);
    const predicted = normalizeAnswer(payload.answer);
    return {
      id: problem.id,
      domain: problem.domain,
      correct: exactEquivalent(predicted, problem.answer),
      expected: problem.answer,
      predicted,
      raw_output: raw.slice(0, 2000),
      duration_ms: Date.now() - started,
    };
  } catch (error) {
    return {
      id: problem.id,
      domain: problem.domain,
      correct: false,
      expected: problem.answer,
      predicted: '',
      raw_output: raw.slice(0, 2000),
      error: error?.message || String(error),
      duration_ms: Date.now() - started,
    };
  }
}

function writeArtifact(report) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const safeModel = String(report.model || 'model').replace(/[^a-zA-Z0-9_.-]+/g, '_');
  const outPath = path.join(
    ARTIFACT_DIR,
    `${stamp}-${report.mode}-${report.provider}-${safeModel}.json`
  );
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2), 'utf8');
  return outPath;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    printHelp();
    return;
  }
  if (opts.list) {
    process.stdout.write(
      JSON.stringify(
        { schema_version: 'scbe_math_reasoning_problem_list_v1', problems: PROBLEMS },
        null,
        2
      ) + '\n'
    );
    return;
  }
  if (
    !['raw', 'worksheet', 'choice', 'tool-choice', 'gated-tool-choice', 'oracle'].includes(
      opts.mode
    )
  ) {
    throw new Error(`unknown mode: ${opts.mode}`);
  }

  const selected = PROBLEMS.slice(
    0,
    Math.max(1, Math.min(PROBLEMS.length, opts.limit || PROBLEMS.length))
  );
  const started = Date.now();
  const results = [];
  for (const problem of selected) {
    // Sequential by design: avoids hiding provider timeouts behind parallelism.
    results.push(await scoreProblem(problem, opts));
  }
  const correct = results.filter((row) => row.correct).length;
  const report = {
    schema_version: 'scbe_math_reasoning_benchmark_v1',
    generated_at: new Date().toISOString(),
    benchmark: 'SCBE exact-answer hard math microbench',
    claim_boundary:
      'Local exact-answer microbench. Official GPT-4 comparison requires the same command against an OpenAI model or a cited public benchmark target.',
    mode: opts.mode,
    provider: opts.provider,
    router_provider: opts.routerProvider || null,
    model:
      opts.provider === 'router'
        ? `terminal_ai_router:${opts.routerProvider || opts.provider}`
        : opts.model,
    score: {
      correct,
      total: selected.length,
      accuracy: selected.length ? correct / selected.length : 0,
    },
    duration_ms: Date.now() - started,
    results,
  };
  if (!opts.noArtifact) report.artifact = writeArtifact(report);
  if (opts.json) {
    process.stdout.write(JSON.stringify(report, null, 2) + '\n');
  } else {
    process.stdout.write(
      `SCBE math reasoning: ${report.model} ${opts.mode} ${correct}/${selected.length}\n`
    );
    for (const row of results) {
      process.stdout.write(
        `${row.correct ? 'PASS' : 'FAIL'} ${row.id} expected=${row.expected} predicted=${row.predicted || '(none)'}${row.choice ? ` choice=${row.choice}` : ''}\n`
      );
    }
    if (report.artifact) process.stdout.write(`artifact: ${report.artifact}\n`);
  }
}

main().catch((error) => {
  process.stderr.write(`bench_math_reasoning: ${error?.message || String(error)}\n`);
  process.exit(1);
});
