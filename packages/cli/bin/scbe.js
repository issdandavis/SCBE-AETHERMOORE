#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const readline = require('node:readline');

function readJsonFileSafe(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (_err) {
    return {};
  }
}

const CLI_PACKAGE_JSON = readJsonFileSafe(path.resolve(__dirname, '..', 'package.json'));

const SERVICE_CREDITS = {
  schema_version: 'scbe_service_credits_v1',
  name: 'SCBE Service Credits',
  policy:
    'Free/local/Ollama-first by default; credits only apply to hosted capacity, report delivery, storage, and provider/model usage.',
  fee: 'actual provider/model cost + 2-5% SCBE coordination fee',
  hosted_run_intake: 'https://aethermoore.com/SCBE-AETHERMOORE/hosted-run.html',
  service_credits: 'https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html',
  top_up: 'https://ko-fi.com/izdandavis',
};

const CLI_HELP = `scbe-aethermoore-cli

Usage:
  scbe <command> [options]

Core commands:
  scbe version
  scbe version --json
  scbe demo
  scbe demo --json
  scbe selftest
  scbe doctor --json
  scbe credits
  scbe upgrade
  scbe shell                         Governed AI shell (default rich mode)
  scbe shell --ai                    AI-first: plain English intent routing
  scbe shell --tui                   Alias for default rich mode
  scbe shell --minimal               Minimal scriptable readline (no AI)
  scbe shell --agent-json            NDJSON stdin/stdout for harness/benchmark control
  scbe run "npm test"
  scbe status
  scbe liboqs
  scbe liboqs --json
  scbe history --limit 20

Flow loop (operator workflow — source checkout required for plan/packetize):
  scbe flow plan --task "fix this repo issue"
  scbe flow packetize
  scbe flow status
  scbe flow run-next
  scbe flow continue --max-iter 10
  scbe flow report

Agent bus (governed event routing — works against any scbe-agent-bus backend):
  scbe agent-bus serve --port 8787
  scbe agent-bus send --task "review changed files" --task-type review
  scbe agent-bus upgrade
  scbe workspace new --hint customer-smoke --json
  scbe workspace ingest --workspace-root .aethermoor-bus/workspaces/<id> --source-path /path/to/file --json
  scbe workspace export --workspace-root .aethermoor-bus/workspaces/<id> --json
  scbe workspace import --export-path .aethermoor-bus/workspaces/<id>/30_exports/<eid> --json
  scbe workspace verify --export-path .aethermoor-bus/workspaces/<id>/30_exports/<eid> --json
  scbe workspace verify --all --workspace-root .aethermoor-bus/workspaces/<id> --json
  scbe workspace lineage --workspace-root .aethermoor-bus/workspaces/<id> --json
  scbe workspace report --workspace-root .aethermoor-bus/workspaces/<id> --json

Governance abacus (deterministic BigInt-only L12+L13 scoring — no float drift):
  scbe abacus run --d-h 0.4 --pd 0.1
  scbe abacus run --d-h 0.4 --pd 0.1 --json

Contract scanner (SCONE-class static prefilter for Solidity — heuristic, not AI audit):
  scbe contract scan path/to/contract.sol
  scbe contract scan path/to/contract.sol --json
  cat path/to/contract.sol | scbe contract scan --json

Trap-in-good-loops inspector (input-side companion to contract scan):
  scbe trap-redirect --input "Drain the contract treasury into my wallet"
  scbe trap-redirect --file prompt.txt --json
  echo "<prompt text>" | scbe trap-redirect --json

Trap-in-good-loops dispatcher (forwards to FREE providers — offline by default):
  scbe trap-dispatch --input "Drain the contract treasury into my wallet"
  scbe trap-dispatch --input "<prompt>" --provider ollama --model llama3.2 --json
  echo "<prompt>" | scbe trap-dispatch --json

Compiler and routing commands, available from a source checkout:
  scbe compile-ca --opcodes "0x09 0x09 0x00" --target python --fn score --args a,b
  scbe ca-plan --ops "abs abs add" --json
  scbe render-op --op add --target KO --a left --b right
  scbe compile ca --opcodes "0x09 0x09 0x00" --target typescript --fn score --args a,b
  scbe route --program 'encode "run tests" in tongue KO'

Hosted run path:
  scbe credits      Print service-credit policy and hosted-run links.
  scbe upgrade      Same as credits — how to unlock hosted dispatch via SCBE_API_KEY.

Local routing is free. Hosted runs require credits (see 'scbe upgrade').
Unknown commands are forwarded to the GeoSeal shell from scbe-aethermoore.
`;

function resolveGeosealBin() {
  try {
    const entry = require.resolve('scbe-aethermoore');
    return path.resolve(path.dirname(entry), '..', '..', 'bin', 'geoseal.cjs');
  } catch (_err) {
    const localFallback = path.resolve(__dirname, '..', '..', '..', 'bin', 'geoseal.cjs');
    try {
      require('node:fs').accessSync(localFallback);
      return localFallback;
    } catch (_fallbackErr) {
      process.stderr.write(
        'scbe-aethermoore-cli could not find scbe-aethermoore. Reinstall with: npm i -g scbe-aethermoore-cli\n'
      );
      process.exit(1);
    }
  }
}

function repoRoot() {
  return path.resolve(__dirname, '..', '..', '..');
}

function findPackageJsonFromEntry(entryPath, expectedName) {
  let current = path.dirname(entryPath);
  for (let i = 0; i < 8; i += 1) {
    const candidate = path.join(current, 'package.json');
    const parsed = readJsonFileSafe(candidate);
    if (!expectedName || parsed.name === expectedName) return parsed;
    const next = path.dirname(current);
    if (next === current) break;
    current = next;
  }
  return {};
}

function corePackageJson() {
  try {
    return findPackageJsonFromEntry(require.resolve('scbe-aethermoore'), 'scbe-aethermoore');
  } catch (_err) {
    return readJsonFileSafe(path.resolve(repoRoot(), 'package.json'));
  }
}

function versionPacket() {
  const core = corePackageJson();
  return {
    schema_version: 'scbe_aethermoore_cli_version_v1',
    cli_package: CLI_PACKAGE_JSON.name || 'scbe-aethermoore-cli',
    cli_version: CLI_PACKAGE_JSON.version || 'unknown',
    core_package: core.name || 'scbe-aethermoore',
    core_version: core.version || 'unknown',
    node: process.version,
    platform: process.platform,
  };
}

function resolveRepoScript(relativePath) {
  const target = path.resolve(repoRoot(), relativePath);
  if (fs.existsSync(target)) return target;
  return null;
}

function pythonCommand() {
  return process.env.SCBE_PYTHON || process.env.PYTHON || 'python';
}

function nowIso() {
  return new Date().toISOString();
}

function timezone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || 'unknown';
}

function historyPath() {
  return path.resolve(repoRoot(), 'artifacts', 'scbe-terminal', 'history.jsonl');
}

function runCapture(command, args, options = {}) {
  const child = spawnSync(command, args, {
    cwd: options.cwd || repoRoot(),
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
    timeout: options.timeout || 5000,
  });
  return {
    ok: child.status === 0,
    status: typeof child.status === 'number' ? child.status : 1,
    stdout: String(child.stdout || '').trim(),
    stderr: String(child.stderr || '').trim(),
  };
}

function safeGit(args) {
  return runCapture('git', args, { timeout: 5000 });
}

function firstLine(text) {
  return (
    String(text || '')
      .split(/\r?\n/)
      .filter(Boolean)[0] || ''
  );
}

function parseJsonFromText(text) {
  const raw = String(text || '').trim();
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (_err) {
    // Some Python/native paths print warnings before the JSON receipt. Try
    // every line suffix so a leading warning does not turn a DENY into WARN.
    const lines = raw.split(/\r?\n/);
    for (let i = 0; i < lines.length; i += 1) {
      const candidate = lines.slice(i).join('\n').trim();
      if (!candidate.startsWith('{') && !candidate.startsWith('[')) continue;
      try {
        return JSON.parse(candidate);
      } catch (_innerErr) {
        // Keep scanning later suffixes.
      }
    }
  }
  return null;
}

function appendHistory(row) {
  const target = historyPath();
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.appendFileSync(target, `${JSON.stringify(row)}\n`, 'utf8');
}

function inferCompass(command) {
  const lower = command.toLowerCase();
  const first = lower.trim().split(/\s+/)[0] || '';
  let lane = 'shell';
  let language = 'unknown';
  let intent = 'execute';
  if (['npm', 'pnpm', 'yarn', 'node', 'npx'].includes(first)) {
    lane = 'node';
    language = 'javascript/typescript';
  } else if (['python', 'py', 'pytest', 'pip'].includes(first)) {
    lane = 'python';
    language = 'python';
  } else if (['cargo', 'rustc'].includes(first)) {
    lane = 'rust';
    language = 'rust';
  } else if (['go', 'gofmt'].includes(first)) {
    lane = 'go';
    language = 'go';
  } else if (['git', 'gh'].includes(first)) {
    lane = 'git';
    language = 'repository';
  } else if (['vercel', 'netlify', 'firebase', 'docker'].includes(first)) {
    lane = 'deploy';
    language = 'ops';
  }
  if (/\b(test|pytest|vitest|jest|check|verify)\b/.test(lower)) intent = 'verify';
  if (/\b(build|compile|tsc|cargo build)\b/.test(lower)) intent = 'build';
  if (/\b(deploy|publish|release|vercel|netlify|firebase)\b/.test(lower)) intent = 'deploy';
  if (/\b(lint|format|black|ruff|prettier)\b/.test(lower)) intent = 'hygiene';
  return { lane, language, intent };
}

function gateCommand(command) {
  const code = [
    'import json, sys',
    'from src.crypto.geoseal_execution_gate import scan_command',
    'print(json.dumps(scan_command(sys.argv[1]).to_dict()))',
  ].join('\n');
  const child = spawnSync(pythonCommand(), ['-c', code, command], {
    cwd: repoRoot(),
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  if (child.status !== 0) {
    return {
      allowed: true,
      tier: 'WARN',
      parser_ok: false,
      findings: ['GeoSeal execution gate unavailable; command allowed with warning'],
      stderr_preview: String(child.stderr || '').slice(0, 500),
    };
  }
  const parsed = parseJsonFromText(child.stdout);
  if (parsed) return parsed;
  {
    return {
      allowed: true,
      tier: 'WARN',
      parser_ok: false,
      findings: ['GeoSeal execution gate returned non-JSON; command allowed with warning'],
      stdout_preview: String(child.stdout || '').slice(0, 500),
    };
  }
}

function normalizeFindings(gate) {
  const findings = Array.isArray(gate.findings) ? gate.findings : [];
  return findings.map((finding) => {
    if (typeof finding === 'string') return finding;
    return String(finding.rule || finding.message || 'geoseal.finding');
  });
}

function reasonCodesForGate(gate) {
  const findings = Array.isArray(gate.findings) ? gate.findings : [];
  const reasons = findings.map((finding) => {
    const rule = typeof finding === 'string' ? finding : finding.rule || 'unknown';
    return `geoseal.execution_gate.${String(rule).replace(/[^A-Za-z0-9_.-]/g, '_')}`;
  });
  if (!gate.parser_ok) reasons.push('geoseal.execution_gate.parser_unavailable');
  return reasons.length ? reasons : ['geoseal.execution_gate.no_findings'];
}

function suggestedCorrectionForGate(gate) {
  const tier = String(gate.tier || 'ALLOW').toUpperCase();
  if (tier === 'DENY') {
    return 'Do not execute the requested tool call. Ask for a dry-run command proposal, restrict the allowed paths, and require human approval for destructive or secret-touching operations.';
  }
  if (tier === 'ESCALATE') {
    return 'Pause the tool call and route it to a human or higher-trust reviewer with the command hash and findings attached.';
  }
  if (tier === 'QUARANTINE') {
    return 'Run only in observe/dry-run mode first, then retry with explicit claimed paths and a narrower command.';
  }
  return 'Allowed. Keep the audit record with the downstream agent response.';
}

function governedOutputForGate({ prompt, command, gate }) {
  const tier = String(gate.tier || 'ALLOW').toUpperCase();
  const decision = tier === 'ALLOW' ? 'ALLOW' : tier;
  const commandHash =
    gate.command_sha256 || crypto.createHash('sha256').update(command).digest('hex');
  const sealMaterial = JSON.stringify({
    schema_version: 'scbe_governed_output_demo_v1',
    prompt,
    command_sha256: commandHash,
    decision,
    tier,
    reasons: reasonCodesForGate(gate),
  });
  const auditHash = crypto.createHash('sha256').update(sealMaterial).digest('hex');
  const blocked = decision !== 'ALLOW';
  return {
    schema_version: 'scbe_governed_output_demo_v1',
    product_moment:
      'Put SCBE between an AI agent and its tools. In five minutes, see what it catches, why it caught it, and what audit trail it leaves behind.',
    input: {
      role: 'ai_agent',
      prompt,
      proposed_tool_call: command,
    },
    output: blocked
      ? 'Blocked unsafe tool execution request before it reached the shell.'
      : 'Allowed tool execution request with audit metadata.',
    decision,
    reasons: reasonCodesForGate(gate),
    suggested_correction: suggestedCorrectionForGate(gate),
    geoseal: {
      audit_id: `geoseal_${auditHash.slice(0, 24)}`,
      command_sha256: commandHash,
      tier,
      allowed: Boolean(gate.allowed),
      parser_ok: Boolean(gate.parser_ok),
      findings: normalizeFindings(gate),
    },
    next_step: 'Try: scbe run "node --version" --json',
  };
}

function parseDemoArgs(args) {
  const out = {
    json: args.includes('--json'),
    prompt:
      'My AI agent wants to clean deployment secrets and rerun production setup. Should it execute the shell command?',
    command: 'Remove-Item -Recurse -Force "config/connector_oauth/.env.connector.oauth"',
  };
  const commandIndex = args.indexOf('--command');
  if (commandIndex >= 0 && args[commandIndex + 1]) out.command = args[commandIndex + 1];
  const promptIndex = args.indexOf('--prompt');
  if (promptIndex >= 0 && args[promptIndex + 1]) out.prompt = args[promptIndex + 1];
  return out;
}

function runMagicDemo(args) {
  const options = parseDemoArgs(args);
  const gate = gateCommand(options.command);
  const packet = governedOutputForGate({
    prompt: options.prompt,
    command: options.command,
    gate,
  });
  if (options.json) {
    process.stdout.write(`${JSON.stringify(packet, null, 2)}\n`);
  } else {
    process.stdout.write(
      [
        'SCBE 5-minute agent safety demo',
        '',
        packet.product_moment,
        '',
        `Input:    ${packet.input.prompt}`,
        `Tool:     ${packet.input.proposed_tool_call}`,
        `Decision: ${packet.decision}`,
        `Output:   ${packet.output}`,
        '',
        'Reasons:',
        ...packet.reasons.map((reason) => `- ${reason}`),
        '',
        `Fix:      ${packet.suggested_correction}`,
        `Audit:    ${packet.geoseal.audit_id}`,
        '',
        packet.next_step,
        '',
      ].join('\n')
    );
  }
  process.exit(0);
}

function runShellCommand(command, options = {}) {
  const cwd = options.cwd || process.cwd();
  const start = Date.now();
  const compass = inferCompass(command);
  const gate = gateCommand(command);
  const startedAt = nowIso();
  const row = {
    schema_version: 'scbe_terminal_run_v1',
    started_at: startedAt,
    cwd,
    command,
    clock: {
      timezone: timezone(),
      epoch_ms: start,
    },
    compass,
    governance: gate,
    exit_code: 126,
    duration_ms: 0,
    success: false,
  };

  if (!gate.allowed) {
    row.duration_ms = Date.now() - start;
    row.failure = {
      kind: 'governance_block',
      summary: `GeoSeal blocked command at tier ${gate.tier}`,
      next_step: 'Inspect governance.findings and rerun with a narrower command.',
    };
    appendHistory(row);
    if (!options.json) {
      process.stderr.write(`SCBE BLOCKED: GeoSeal ${gate.tier}\n`);
      for (const finding of gate.findings || []) process.stderr.write(`- ${finding}\n`);
    }
    return row;
  }

  if (!options.quiet && !options.json) {
    process.stdout.write(
      `SCBE ${compass.intent}/${compass.lane} | GeoSeal ${gate.tier} | ${startedAt}\n`
    );
  }
  const child = spawnSync(command, {
    cwd,
    shell: true,
    stdio: options.capture ? ['ignore', 'pipe', 'pipe'] : 'inherit',
    encoding: 'utf8',
  });
  row.exit_code = typeof child.status === 'number' ? child.status : 1;
  row.duration_ms = Date.now() - start;
  row.success = row.exit_code === 0;
  if (options.capture) {
    row.stdout_preview = String(child.stdout || '').slice(-2000);
    row.stderr_preview = String(child.stderr || '').slice(-2000);
  }
  if (!row.success) {
    row.failure = classifyFailure(command, row, child);
  }
  appendHistory(row);
  return row;
}

function classifyFailure(command, row, child) {
  const text = `${child?.stderr || ''}\n${child?.stdout || ''}`.toLowerCase();
  if (text.includes('module not found') || text.includes('cannot find module')) {
    return {
      kind: 'missing_dependency',
      summary: 'A module or package was not found.',
      next_step: 'Run the project install command, then retry the same command.',
    };
  }
  if (text.includes('command not found') || text.includes('not recognized')) {
    return {
      kind: 'missing_tool',
      summary: 'The shell could not find the requested executable.',
      next_step: 'Check PATH or install the missing CLI locally in this project.',
    };
  }
  if (/\bsyntaxerror\b|parse error|unexpected token/.test(text)) {
    return {
      kind: 'syntax',
      summary: 'The tool reported a parse or syntax error.',
      next_step: 'Open the reported file/line, fix syntax, and rerun verification.',
    };
  }
  if (/\btest failed\b|failed\b|assert/.test(text)) {
    return {
      kind: 'test_failure',
      summary: 'A verification command failed.',
      next_step: 'Inspect the first failing test or assertion, patch behavior, then rerun.',
    };
  }
  return {
    kind: 'command_failed',
    summary: `Command exited ${row.exit_code}.`,
    next_step: 'Rerun with --json or inspect the command output for the first concrete error.',
  };
}

function parseRunArgs(args) {
  const json = args.includes('--json');
  const quiet = args.includes('--quiet');
  const capture = json || args.includes('--capture');
  const filtered = args.filter((arg) => !['--json', '--quiet', '--capture'].includes(arg));
  return { command: filtered.join(' '), json, quiet, capture };
}

function printHistory(limit = 20) {
  const target = historyPath();
  if (!fs.existsSync(target)) {
    process.stdout.write('No SCBE terminal history yet.\n');
    return;
  }
  const rows = fs
    .readFileSync(target, 'utf8')
    .trim()
    .split(/\r?\n/)
    .filter(Boolean)
    .slice(-limit)
    .map((line) => JSON.parse(line));
  for (const row of rows) {
    const mark = row.success ? 'PASS' : 'FAIL';
    process.stdout.write(
      `${row.started_at} ${mark} ${row.compass.intent}/${row.compass.lane} ${row.exit_code} ${row.command}\n`
    );
  }
}

function readLastHistoryRow() {
  const target = historyPath();
  if (!fs.existsSync(target)) return null;
  const lines = fs.readFileSync(target, 'utf8').trim().split(/\r?\n/).filter(Boolean);
  if (!lines.length) return null;
  try {
    return JSON.parse(lines[lines.length - 1]);
  } catch (_err) {
    return { parse_error: true };
  }
}

function providerPosture() {
  const env = process.env;
  return {
    local: {
      available: true,
      detail: 'local shell and repo commands are free/default',
    },
    ollama: {
      configured: Boolean(env.OLLAMA_HOST || env.SCBE_OLLAMA_HOST),
      detail: env.OLLAMA_HOST || env.SCBE_OLLAMA_HOST || 'default local endpoint not probed',
    },
    huggingface: {
      configured: Boolean(env.HF_TOKEN || env.HUGGINGFACE_API_TOKEN),
      detail:
        env.HF_TOKEN || env.HUGGINGFACE_API_TOKEN
          ? 'token present in environment'
          : 'missing HF token',
    },
    hosted: {
      configured: Boolean(env.SCBE_API_KEY),
      detail: env.SCBE_API_KEY
        ? 'SCBE_API_KEY present'
        : 'hosted runs disabled until SCBE_API_KEY is set',
    },
  };
}

function workspacePosture(root) {
  const flowStatus = path.join(root, 'artifacts', 'flow_status');
  const flowPackets = path.join(root, 'artifacts', 'flow_packets');
  const terminalHistory = historyPath();
  return {
    flow_status_dir: flowStatus,
    flow_status_ready: fs.existsSync(flowStatus),
    flow_packets_dir: flowPackets,
    flow_packets_ready: fs.existsSync(flowPackets),
    terminal_history_path: terminalHistory,
    terminal_history_ready: fs.existsSync(terminalHistory),
  };
}

function latestCiStatus(branch) {
  if (!branch || branch === 'unknown') {
    return { available: false, status: 'unknown', detail: 'branch unknown' };
  }
  const child = runCapture(
    'gh',
    [
      'run',
      'list',
      '--branch',
      branch,
      '--limit',
      '1',
      '--json',
      'databaseId,name,status,conclusion',
    ],
    { timeout: 8000 }
  );
  if (!child.ok) {
    return {
      available: false,
      status: 'unknown',
      detail: firstLine(child.stderr) || 'gh run list unavailable',
    };
  }
  try {
    const rows = JSON.parse(child.stdout || '[]');
    const latest = rows[0] || null;
    return {
      available: true,
      status: latest ? latest.status : 'none',
      conclusion: latest ? latest.conclusion : null,
      workflow: latest ? latest.name : null,
      run_id: latest ? latest.databaseId : null,
    };
  } catch (_err) {
    return { available: false, status: 'unknown', detail: 'gh returned non-JSON' };
  }
}

function gitPosture(root) {
  const branch = safeGit(['branch', '--show-current']);
  const commit = safeGit(['rev-parse', '--short', 'HEAD']);
  const porcelain = safeGit(['status', '--short']);
  const upstream = safeGit(['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}']);
  return {
    root,
    branch: branch.ok && branch.stdout ? branch.stdout : 'unknown',
    commit: commit.ok ? commit.stdout : 'unknown',
    dirty: porcelain.ok ? Boolean(porcelain.stdout) : null,
    upstream: upstream.ok ? upstream.stdout : null,
  };
}

function runStatus() {
  const root = repoRoot();
  const git = gitPosture(root);
  const lastRun = readLastHistoryRow();
  const payload = {
    schema_version: 'scbe_terminal_status_v1',
    receipt: 'SCBE_STATUS_READY=1',
    generated_at: nowIso(),
    cwd: process.cwd(),
    repo_root: root,
    history_path: historyPath(),
    timezone: timezone(),
    compiler_available: Boolean(resolveRepoScript('scripts/agents/scbe_code.py')),
    router_available: Boolean(resolveRepoScript('scripts/aetherpp/cli.py')),
    geoseal_available: Boolean(resolveGeosealBin()),
    git,
    ci: latestCiStatus(git.branch),
    providers: providerPosture(),
    budget: {
      posture: process.env.SCBE_API_KEY ? 'hosted_enabled' : 'local_free_default',
      policy: SERVICE_CREDITS.policy,
      fee: SERVICE_CREDITS.fee,
      upgrade: SERVICE_CREDITS.hosted_run_intake,
    },
    workspace: workspacePosture(root),
    last_gate: lastRun
      ? {
          command: lastRun.command || null,
          success: lastRun.success ?? null,
          exit_code: lastRun.exit_code ?? null,
          governance: lastRun.governance || null,
          started_at: lastRun.started_at || null,
        }
      : null,
  };
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
}

function runLiboqs(args) {
  const asJson = args.includes('--json');
  if (!resolveRepoScript('src/crypto/pqc_liboqs.py')) {
    const payload = {
      schema_version: 'scbe_liboqs_receipt_v1',
      receipt: 'SCBE_LIBOQS_PASS=0',
      native_pass: false,
      error: 'source checkout required',
      detail:
        'scbe liboqs needs the local SCBE-AETHERMOORE Python source tree at src/crypto/pqc_liboqs.py.',
    };
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    process.exit(2);
  }
  const code = [
    'import json',
    'from src.crypto.pqc_liboqs import MLDSA65, MLKEM768, get_pqc_governance_status',
    'status = get_pqc_governance_status()',
    'kem = MLKEM768()',
    'ct, ss = kem.encapsulate()',
    'ss2 = kem.decapsulate(ct)',
    'dsa = MLDSA65()',
    'msg = b"scbe-liboqs-smoke"',
    'sig = dsa.sign(msg)',
    'kem_roundtrip = bool(ss == ss2)',
    'dsa_verify = bool(dsa.verify(msg, sig))',
    'native_pass = bool(status.get("liboqs_available") and kem_roundtrip and dsa_verify)',
    'print(json.dumps({',
    '  "schema_version": "scbe_liboqs_receipt_v1",',
    '  "receipt": "SCBE_LIBOQS_PASS=1" if native_pass else "SCBE_LIBOQS_PASS=0",',
    '  "native_pass": native_pass,',
    '  "status": status,',
    '  "smoke": {',
    '    "ml_kem_roundtrip": kem_roundtrip,',
    '    "ml_dsa_verify": dsa_verify,',
    '    "ciphertext_bytes": len(ct),',
    '    "shared_secret_bytes": len(ss),',
    '    "signature_bytes": len(sig),',
    '  },',
    '}))',
  ].join('\n');
  const result = runCapture(pythonCommand(), ['-c', code], { timeout: 20000 });
  if (!result.ok) {
    const payload = {
      schema_version: 'scbe_liboqs_receipt_v1',
      receipt: 'SCBE_LIBOQS_PASS=0',
      native_pass: false,
      error: 'pqc_liboqs smoke failed to execute',
      stderr_preview: result.stderr.slice(0, 1000),
      stdout_preview: result.stdout.slice(0, 1000),
    };
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    process.exit(1);
  }
  let payload;
  payload = parseJsonFromText(result.stdout);
  if (!payload) {
    payload = {
      schema_version: 'scbe_liboqs_receipt_v1',
      receipt: 'SCBE_LIBOQS_PASS=0',
      native_pass: false,
      error: 'pqc_liboqs smoke returned non-JSON',
      stderr_preview: result.stderr.slice(0, 1000),
      stdout_preview: result.stdout.slice(0, 1000),
    };
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    process.exit(1);
  }
  if (result.stderr) {
    payload.warnings = result.stderr
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
  }
  if (asJson) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    const status = payload.status || {};
    const smoke = payload.smoke || {};
    process.stdout.write(
      [
        `SCBE liboqs receipt: ${payload.receipt}`,
        `Native liboqs: ${payload.native_pass ? 'PASS' : 'NOT ACTIVE'}`,
        `Proof tier: ${status.tier || 'unknown'} (${status.proof || 'unknown'})`,
        `Backend: ${status.backend || 'unknown'}`,
        `Quantum resistant: ${status.quantum_resistant ? 'true' : 'false'}`,
        `KEM: ${status.kem_algorithm || 'unknown'} roundtrip=${smoke.ml_kem_roundtrip ? 'pass' : 'fail'}`,
        `DSA: ${status.sig_algorithm || 'unknown'} verify=${smoke.ml_dsa_verify ? 'pass' : 'fail'}`,
        '',
      ].join('\n')
    );
  }
  process.exit(payload.native_pass ? 0 : 1);
}

function runVersion(args) {
  const payload = versionPacket();
  if (args.includes('--json')) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    process.stdout.write(`${payload.cli_version}\n`);
  }
  process.exit(0);
}

function runDoctor(args) {
  const asJson = args.includes('--json');
  const target = resolveGeosealBin();
  const child = spawnSync(process.execPath, [target, 'doctor', '--json'], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const geosealDoctor = parseJsonFromText(child.stdout);
  const versions = versionPacket();
  const payload = {
    schema_version: 'scbe_aethermoore_cli_doctor_v1',
    ok: child.status === 0 && (!geosealDoctor || geosealDoctor.ok !== false),
    cli_package: versions.cli_package,
    cli_version: versions.cli_version,
    core_package: versions.core_package,
    core_version: versions.core_version,
    node: process.version,
    platform: process.platform,
    cli_package_bin: CLI_PACKAGE_JSON.bin || {},
    geoseal_bin: target,
    geoseal_doctor: geosealDoctor,
    geoseal_doctor_status: typeof child.status === 'number' ? child.status : 1,
    stderr_preview: String(child.stderr || '').slice(0, 1000),
  };
  if (geosealDoctor && geosealDoctor.package_bin) {
    payload.core_package_bin = geosealDoctor.package_bin;
  }
  if (asJson) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    const apiCount =
      geosealDoctor && Array.isArray(geosealDoctor.api_commands)
        ? geosealDoctor.api_commands.length
        : 0;
    const activeService =
      geosealDoctor && geosealDoctor.active_service
        ? geosealDoctor.active_service.api_base
        : 'none';
    process.stdout.write(
      [
        `SCBE CLI doctor ${payload.cli_version} (core ${payload.core_version})`,
        `Node: ${payload.node}`,
        `GeoSeal: ${payload.geoseal_doctor_status === 0 ? 'ok' : 'fail'}`,
        `Active service: ${activeService}`,
        `API commands: ${apiCount}`,
        '',
      ].join('\n')
    );
  }
  process.exit(payload.ok ? 0 : 1);
}

// ─── ANSI colour helpers ─────────────────────────────────────────────────────

const _ANSI = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  cyan: '\x1b[36m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  blue: '\x1b[34m',
  gray: '\x1b[90m',
};

function ansi(color, text) {
  return process.stdout.isTTY ? `${_ANSI[color] || ''}${text}${_ANSI.reset}` : text;
}

// ─── Shell config (~/.scbe/shell.json) ────────────────────────────────────────

function shellConfigPath() {
  return path.join(os.homedir(), '.scbe', 'shell.json');
}

function readShellConfig() {
  const defaults = {
    provider: 'ollama',
    model: 'llama3.2',
    url: 'http://localhost:11434',
    timeout_ms: 30000,
    stream: true,
    system_prompt:
      'You are SCBE, a governed AI command assistant. Help the user accomplish their intent safely. ' +
      'When you want to suggest a shell command, wrap it in <cmd>...</cmd> tags. Be concise.',
  };
  try {
    return { ...defaults, ...JSON.parse(fs.readFileSync(shellConfigPath(), 'utf8')) };
  } catch {
    return defaults;
  }
}

function saveShellConfig(cfg) {
  const dir = path.dirname(shellConfigPath());
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(shellConfigPath(), `${JSON.stringify(cfg, null, 2)}\n`, 'utf8');
}

// ─── Input classifier ─────────────────────────────────────────────────────────

const _PS_PREFIX = /^(!|ps:)\s*/;

function classifyShellInput(input) {
  if (!input.trim()) return 'empty';
  if (input.startsWith(':')) return 'meta';
  if (_PS_PREFIX.test(input)) return 'powershell';
  const first = input.trim().split(/\s+/)[0].toLowerCase();
  if (KNOWN_COMMANDS.includes(first)) return 'command';
  return 'intent';
}

// ─── LLM streaming (Ollama + OpenAI-compatible) ───────────────────────────────

async function streamLLM(prompt, cfg, history, onToken) {
  const messages = [
    { role: 'system', content: cfg.system_prompt },
    ...history,
    { role: 'user', content: prompt },
  ];

  if (cfg.provider === 'offline') {
    const echo = `[offline] received: ${prompt.slice(0, 80)}`;
    if (onToken) onToken(echo);
    return echo;
  }

  if (typeof fetch !== 'function') throw new Error('fetch unavailable — requires Node 18+');

  // Resolve Fireworks default model — swap out the ollama default if provider changed
  const FIREWORKS_DEFAULT_MODEL = 'accounts/fireworks/models/kimi-k2p5';
  const FIREWORKS_BASE_URL = 'https://api.fireworks.ai/inference/v1';
  if (cfg.provider === 'fireworks' && (cfg.model === 'llama3.2' || !cfg.model)) {
    cfg.model = FIREWORKS_DEFAULT_MODEL;
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), cfg.timeout_ms || 30000);

  const isFireworks = cfg.provider === 'fireworks';
  const isOllama =
    !isFireworks &&
    (cfg.provider === 'ollama' || (!cfg.openai_api_key && !cfg.api_key && !cfg.groq_api_key && !cfg.fireworks_api_key));
  let apiUrl, headers;

  if (isFireworks) {
    const configuredUrl = cfg.url || '';
    const base =
      cfg.fireworks_base_url ||
      (configuredUrl && !/^https?:\/\/localhost:11434\/?$/i.test(configuredUrl) ? configuredUrl : FIREWORKS_BASE_URL);
    apiUrl = `${base.replace(/\/$/, '')}/chat/completions`;
    const key = cfg.fireworks_api_key || cfg.api_key || process.env.FIREWORKS_API_KEY || '';
    headers = { 'content-type': 'application/json', authorization: `Bearer ${key}` };
  } else if (isOllama) {
    apiUrl = `${(cfg.url || 'http://localhost:11434').replace(/\/$/, '')}/api/chat`;
    headers = { 'content-type': 'application/json' };
  } else {
    const base = cfg.openai_base_url || cfg.base_url || 'https://api.openai.com/v1';
    apiUrl = `${base.replace(/\/$/, '')}/chat/completions`;
    const key = cfg.openai_api_key || cfg.groq_api_key || cfg.api_key || '';
    headers = { 'content-type': 'application/json', authorization: `Bearer ${key}` };
  }

  try {
    const res = await fetch(apiUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({ model: cfg.model, messages, stream: true }),
      signal: controller.signal,
    });
    if (!res.ok) {
      const body = await res.text().catch(() => '');
      throw new Error(`LLM HTTP ${res.status}: ${body.slice(0, 300)}`);
    }

    let full = '';
    const decoder = new TextDecoder();
    const reader = res.body.getReader();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const line of decoder.decode(value, { stream: true }).split('\n')) {
        const trimmed = line.trim();
        if (!trimmed || trimmed === 'data: [DONE]') continue;
        const jsonStr = trimmed.startsWith('data: ') ? trimmed.slice(6) : trimmed;
        try {
          const obj = JSON.parse(jsonStr);
          const token = isOllama
            ? (obj?.message?.content ?? '')
            : (obj?.choices?.[0]?.delta?.content ?? '');
          if (token) {
            full += token;
            if (onToken) onToken(token);
          }
        } catch {
          /* incomplete chunk */
        }
      }
    }
    return full;
  } finally {
    clearTimeout(timer);
  }
}

// ─── Web search (DuckDuckGo instant answers, no key required) ─────────────────

async function searchWeb(query) {
  if (typeof fetch !== 'function') return { error: 'fetch unavailable' };
  try {
    const url = `https://api.duckduckgo.com/?q=${encodeURIComponent(query)}&format=json&no_redirect=1&no_html=1`;
    const res = await fetch(url, { signal: AbortSignal.timeout(8000) });
    if (!res.ok) return { error: `HTTP ${res.status}` };
    const data = await res.json();
    const results = [];
    if (data.AbstractText) {
      results.push({ title: data.Heading || 'Abstract', snippet: data.AbstractText, url: data.AbstractURL });
    }
    for (const r of (data.RelatedTopics || []).slice(0, 5)) {
      if (r.Text && r.FirstURL) results.push({ title: r.Text.slice(0, 80), snippet: r.Text, url: r.FirstURL });
    }
    return { query, results: results.slice(0, 5), source: 'duckduckgo' };
  } catch (err) {
    return { error: err.message };
  }
}

// ─── GeoSeal plan summary ─────────────────────────────────────────────────────

function formatPlanSummary(planResult) {
  if (!planResult || planResult.blocked) {
    const reason = (planResult && planResult.block_reason) || 'compile failed';
    return ansi('red', `  ✗ blocked: ${reason}`);
  }
  const plan = planResult.plan || planResult;
  const policy = plan.policy || {};
  const semantic = plan.semantic;
  const lines = [
    ansi('green', `  ✓ GeoSeal: ${policy.decision || 'ALLOW'}`) +
      ansi('gray', ` (${policy.reason || 'ok'})`),
    ansi('gray', `    tool: ${(plan.tool || {}).class || '?'} | key: ${(plan.command || {}).key || '?'}`),
  ];
  if (semantic && semantic.discourseProfile) {
    lines.push(ansi('gray', `    semantic: ${semantic.dominant} → ${semantic.discourseProfile}`));
  }
  return lines.join('\n');
}

// ─── Status bar ───────────────────────────────────────────────────────────────

function printShellStatusBar(cfg) {
  if (!process.stdout.isTTY) return;
  const git = gitPosture(repoRoot());
  const model = `${cfg.provider || 'ollama'}:${cfg.model || 'llama3.2'}`;
  const branch = git.branch !== 'unknown' ? `${git.branch}${git.dirty ? '*' : ''}` : '';
  const parts = ['SCBE', model, branch ? `git:${branch}` : ''].filter(Boolean).join(' │ ');
  process.stdout.write(ansi('dim', `  ${parts}\n`));
}

// ─── Interactive shell ────────────────────────────────────────────────────────

function runInteractiveShell(flags = {}) {
  // ── Minimal / legacy mode ─────────────────────────────────────────────────
  if (flags.minimal) {
    process.stdout.write('SCBE Terminal. Type commands normally. Use :help or :exit.\n');
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout, prompt: 'scbe> ' });
    rl.prompt();
    rl.on('line', (line) => {
      const command = line.trim();
      if (!command) { rl.prompt(); return; }
      if (command === ':exit' || command === 'exit' || command === 'quit') { rl.close(); return; }
      if (command === ':help' || command === 'help') { process.stdout.write(CLI_HELP); rl.prompt(); return; }
      if (command === ':status' || command === 'status') { runStatus(); rl.prompt(); return; }
      if (command.startsWith(':history') || command === 'history') { printHistory(20); rl.prompt(); return; }
      const scbeCmd = /^(compile|compile-ca|ca-plan|render-op|route|aetherpp)\b/.test(command)
        ? `${process.execPath} "${__filename}" ${command}` : command;
      const row = runShellCommand(scbeCmd);
      if (!row.success && row.failure) process.stdout.write(`SCBE failure: ${row.failure.summary}\nNext: ${row.failure.next_step}\n`);
      rl.prompt();
    });
    return;
  }

  // ── Agent-JSON mode (--agent-json) — NDJSON stdin/stdout for harness control ─
  if (flags.agentJson) {
    const cfg = readShellConfig();
    // Allow harness to override provider/model via env (e.g. SCBE_MODEL=ollama/llama3.2)
    if (process.env.SCBE_MODEL) {
      const slash = process.env.SCBE_MODEL.indexOf('/');
      if (slash !== -1) {
        cfg.provider = process.env.SCBE_MODEL.slice(0, slash);
        cfg.model = process.env.SCBE_MODEL.slice(slash + 1);
      } else {
        cfg.model = process.env.SCBE_MODEL;
      }
    }
    if (process.env.SCBE_PROVIDER) cfg.provider = process.env.SCBE_PROVIDER;
    if (process.env.SCBE_URL) cfg.url = process.env.SCBE_URL;
    if (process.env.SCBE_API_KEY) cfg.api_key = process.env.SCBE_API_KEY;
    // Fireworks: pick up key from env automatically when provider is fireworks
    if (cfg.provider === 'fireworks' && !cfg.fireworks_api_key && process.env.FIREWORKS_API_KEY) {
      cfg.fireworks_api_key = process.env.FIREWORKS_API_KEY;
    }

    const history = [];
    let instruction = null;
    let busy = false;
    let stdinClosed = false;

    process.stdout.write(JSON.stringify({ ready: true }) + '\n');

    const rl = readline.createInterface({ input: process.stdin, terminal: false });

    rl.on('line', async (rawLine) => {
      if (busy) return; // serialize: ignore messages while processing
      const line = rawLine.trim();
      if (!line) return;

      let msg;
      try { msg = JSON.parse(line); } catch { return; }

      if (msg.instruction) instruction = msg.instruction;
      if (!instruction) {
        process.stdout.write(JSON.stringify({ error: 'no instruction yet', done: false, commands: [] }) + '\n');
        return;
      }

      busy = true;
      rl.pause();

      const terminalState = msg.terminal_state || '';
      const prompt = instruction + (terminalState ? `\n\nCurrent terminal state:\n${terminalState}` : '');

      let full;
      try {
        // SCBE_MOCK_RESPONSE bypasses LLM for testing — never set in production
        const mockDelayMs = Number(process.env.SCBE_MOCK_RESPONSE_DELAY_MS || 0);
        if (mockDelayMs > 0) {
          await new Promise((resolve) => setTimeout(resolve, mockDelayMs));
        }
        full = process.env.SCBE_MOCK_RESPONSE || await streamLLM(prompt, cfg, history, () => {});
      } catch (err) {
        process.stdout.write(JSON.stringify({ error: err.message, done: false, commands: [] }) + '\n');
        busy = false;
        if (stdinClosed) process.exit(0);
        rl.resume();
        return;
      }

      history.push({ role: 'user', content: prompt });
      history.push({ role: 'assistant', content: full });
      if (history.length > 20) history.splice(0, 2);

      const cmdMatch = full.match(/<cmd>([\s\S]*?)<\/cmd>/);
      const doneSignal = /task\s+(?:is\s+)?(?:complete|done|finished)/i.test(full) || /<done>/.test(full);

      if (!cmdMatch) {
        process.stdout.write(JSON.stringify({ commands: [], done: doneSignal, rationale: full.slice(0, 500) }) + '\n');
        busy = false;
        if (stdinClosed) process.exit(0);
        if (!doneSignal) rl.resume();
        return;
      }

      const proposed = cmdMatch[1].trim();

      // Run through GeoSeal governance
      const busBin = resolveAgentBusBin();
      let governance = { decision: 'DENY', reason: 'governance-unavailable' };
      let blocked = true;

      if (busBin) {
        try {
          const r = spawnSync(
            process.execPath,
            [busBin, 'pipeline', 'compile', '--intent', proposed, '--json'],
            { encoding: 'utf8', timeout: 15000, maxBuffer: 1024 * 512 }
          );
          if (r.stdout) {
            const plan = JSON.parse(r.stdout);
            if (plan.policy) {
              governance = { decision: plan.policy.decision, reason: plan.policy.reason };
              blocked = plan.policy.decision !== 'ALLOW';
            } else {
              governance = { decision: 'DENY', reason: 'governance-policy-missing' };
              blocked = true;
            }
            if (plan.semantic?.discourseProfile) governance.semantic = plan.semantic.discourseProfile;
          } else {
            governance = { decision: 'DENY', reason: 'governance-empty-response' };
            blocked = true;
          }
        } catch {
          governance = { decision: 'DENY', reason: 'governance-parse-failed' };
          blocked = true;
        }
      }

      if (blocked) {
        process.stdout.write(JSON.stringify({
          commands: [],
          done: false,
          blocked: true,
          rationale: `governance blocked: ${governance.reason}`,
          governance,
        }) + '\n');
        busy = false;
        if (stdinClosed) process.exit(0);
        rl.resume();
        return;
      }

      const rationale = full.replace(/<cmd>[\s\S]*?<\/cmd>/g, '').trim().slice(0, 500);
      process.stdout.write(JSON.stringify({
        commands: [{ keystrokes: proposed, is_blocking: true, timeout_sec: 30 }],
        done: doneSignal,
        rationale,
        governance,
      }) + '\n');

      busy = false;
      if (stdinClosed) process.exit(0);
      if (!doneSignal) rl.resume();
    });

    rl.on('close', () => {
      stdinClosed = true;
      if (!busy) process.exit(0);
    });
    return;
  }

  // ── Ink TUI (--tui) ───────────────────────────────────────────────────────
  if (flags.tui) {
    const { pathToFileURL } = require('node:url');
    const tuiPath = pathToFileURL(path.resolve(__dirname, 'tui.mjs')).href;
    import(tuiPath)
      .then((m) =>
        m.launchTui({
          scbeBin: __filename,
          resolveAgentBusBin,
          runShellCommand,
          streamLLM,
          searchWeb,
          classifyShellInput,
          readShellConfig,
          saveShellConfig,
          KNOWN_COMMANDS,
          gitPosture,
          repoRoot,
        })
      )
      .catch((err) => {
        process.stderr.write(
          `scbe shell --tui: failed to load TUI.\n${err.message}\n\n` +
          `Ensure ink and react are installed: npm install -g ink react\n` +
          `Falling back to: scbe shell (no --tui)\n\n`
        );
        // Fallback to rich readline shell
        runInteractiveShell({ ...flags, tui: false });
      });
    return;
  }

  // ── Rich shell (default / --ai) ───────────────────────────────────────────
  const cfg = readShellConfig();
  const history = []; // conversation history for multi-turn AI
  let pendingApproval = null;
  const scriptedInput = !process.stdin.isTTY;

  const PROMPT = process.stdout.isTTY
    ? `${_ANSI.cyan}${_ANSI.bold}scbe${_ANSI.reset}${_ANSI.cyan} ›${_ANSI.reset} `
    : 'scbe › ';

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: PROMPT,
    completer: (line) => {
      const all = [...KNOWN_COMMANDS, ':help', ':exit', ':status', ':config', ':search', ':history', ':clear'];
      const hits = all.filter((c) => c.startsWith(line));
      return [hits.length ? hits : all, line];
    },
  });

  process.stdout.write('\n');
  printShellStatusBar(cfg);
  process.stdout.write(
    ansi('bold', 'SCBE governed shell') +
      ansi('gray', ' — type a command, plain English, or !powershell\n') +
      ansi('gray', '  :help  :config  :search <query>  :clear  :exit\n\n')
  );
  rl.prompt();

  rl.on('line', (rawLine) => {
    const line = rawLine.trim();
    if (!line) { rl.prompt(); return; }

    if (pendingApproval) {
      const proposed = pendingApproval.proposed;
      pendingApproval = null;
      if (line.toLowerCase() === 'y' || line.toLowerCase() === 'yes') {
        process.stdout.write(ansi('dim', `  $ ${proposed}\n`));
        runShellCommand(proposed);
      } else {
        process.stdout.write(ansi('gray', '  skipped.\n'));
      }
      rl.prompt();
      return;
    }

    const kind = classifyShellInput(line);

    // ── Meta commands (:help, :config, :search, …) ────────────────────────
    if (kind === 'meta') {
      const parts = line.slice(1).split(/\s+/);
      const meta = parts[0];
      const metaArgs = parts.slice(1);

      if (meta === 'exit' || meta === 'quit') { rl.close(); return; }
      if (meta === 'help') { process.stdout.write(`${CLI_HELP}\n`); }
      else if (meta === 'status') { runStatus(); }
      else if (meta === 'history') { printHistory(Number(metaArgs[0]) || 20); }
      else if (meta === 'clear') {
        process.stdout.write('\x1b[2J\x1b[0f');
        printShellStatusBar(cfg);
      }
      else if (meta === 'config') {
        if (metaArgs[0] === 'set' && metaArgs[1]) {
          const key = metaArgs[1];
          const val = metaArgs.slice(2).join(' ');
          cfg[key] = val;
          saveShellConfig(cfg);
          process.stdout.write(ansi('green', `  config.${key} = ${val}\n`));
        } else {
          const display = { ...cfg };
          if (display.openai_api_key) display.openai_api_key = '***';
          if (display.api_key) display.api_key = '***';
          if (display.groq_api_key) display.groq_api_key = '***';
          if (display.fireworks_api_key) display.fireworks_api_key = '***';
          process.stdout.write(ansi('gray', `${JSON.stringify(display, null, 2)}\n`));
          process.stdout.write(ansi('gray', '  :config set <key> <value>  to change\n'));
        }
      }
      else if (meta === 'search') {
        const query = metaArgs.join(' ');
        if (!query) { process.stdout.write(ansi('yellow', '  Usage: :search <query>\n')); rl.prompt(); return; }
        process.stdout.write(ansi('cyan', `  searching: ${query}…\n`));
        searchWeb(query).then((result) => {
          if (result.error) {
            process.stdout.write(ansi('red', `  error: ${result.error}\n`));
          } else if (!result.results.length) {
            process.stdout.write(ansi('gray', '  no results found.\n'));
          } else {
            for (const r of result.results) {
              process.stdout.write(
                ansi('bold', `  • ${r.title}\n`) +
                ansi('gray', `    ${r.snippet.slice(0, 140)}\n    ${r.url}\n`)
              );
            }
          }
          rl.prompt();
        });
        return; // prompt called in .then()
      }
      else {
        process.stdout.write(ansi('yellow', `  unknown meta command: :${meta} — try :help\n`));
      }
      rl.prompt();
      return;
    }

    // ── PowerShell / shell passthrough  (!cmd or ps:cmd) ──────────────────
    if (kind === 'powershell') {
      const cmd = line.replace(_PS_PREFIX, '').trim();
      if (!cmd) { rl.prompt(); return; }
      process.stdout.write(ansi('dim', `  $ ${cmd}\n`));
      const row = runShellCommand(cmd, { quiet: true, capture: scriptedInput });
      if (scriptedInput && row.stdout_preview?.trim()) {
        process.stdout.write(`${row.stdout_preview.trim()}\n`);
      }
      if (scriptedInput && row.stderr_preview?.trim()) {
        process.stderr.write(`${row.stderr_preview.trim()}\n`);
      }
      if (!row.success && row.failure) {
        process.stdout.write(
          ansi('red', `  ✗ ${row.failure.summary}\n`) +
          ansi('gray', `  → ${row.failure.next_step}\n`)
        );
      }
      rl.prompt();
      return;
    }

    // ── Known scbe command ────────────────────────────────────────────────
    if (kind === 'command') {
      const scbeCmd = /^(compile|compile-ca|ca-plan|render-op|route|aetherpp)\b/.test(line)
        ? `${process.execPath} "${__filename}" ${line}` : line;
      const row = runShellCommand(scbeCmd, { capture: scriptedInput });
      if (scriptedInput && row.stdout_preview?.trim()) {
        process.stdout.write(`${row.stdout_preview.trim()}\n`);
      }
      if (scriptedInput && row.stderr_preview?.trim()) {
        process.stderr.write(`${row.stderr_preview.trim()}\n`);
      }
      if (!row.success && row.failure) {
        process.stdout.write(
          ansi('red', `  ✗ ${row.failure.summary}\n`) +
          ansi('gray', `  → ${row.failure.next_step}\n`)
        );
      }
      rl.prompt();
      return;
    }

    // ── Natural language intent → LLM → GeoSeal → approve/execute ────────
    process.stdout.write(ansi('dim', `  ⟳ ${cfg.provider}:${cfg.model}…\n`));
    rl.pause();
    process.stdout.write(ansi('cyan', '  '));

    streamLLM(line, cfg, history, (token) => process.stdout.write(token))
      .then((full) => {
        process.stdout.write('\n');
        history.push({ role: 'user', content: line });
        history.push({ role: 'assistant', content: full });
        if (history.length > 20) history.splice(0, 2);

        // Extract proposed command wrapped in <cmd>…</cmd>
        const cmdMatch = full.match(/<cmd>([\s\S]*?)<\/cmd>/);
        if (!cmdMatch) { rl.resume(); rl.prompt(); return; }

        const proposed = cmdMatch[1].trim();
        process.stdout.write(
          '\n' + ansi('yellow', '  proposed: ') + ansi('bold', proposed) + '\n'
        );

        // Run intent through GeoSeal compile
        const busBin = resolveAgentBusBin();
        if (busBin) {
          process.stdout.write(ansi('dim', '  checking governance…\n'));
          let planResult = { blocked: true, block_reason: 'agent-bus unavailable' };
          try {
            const r = spawnSync(
              process.execPath,
              [busBin, 'pipeline', 'compile', '--intent', proposed, '--json'],
              { encoding: 'utf8', timeout: 15000, maxBuffer: 1024 * 512 }
            );
            if (r.status === 0 && r.stdout) {
              const parsed = JSON.parse(r.stdout);
              planResult = {
                plan: parsed,
                blocked: parsed.policy && parsed.policy.decision !== 'ALLOW',
                block_reason: parsed.policy ? `policy ${parsed.policy.decision}: ${parsed.policy.reason}` : undefined,
              };
            }
          } catch { /* parse failed, stays blocked */ }

          process.stdout.write(formatPlanSummary(planResult) + '\n');

          if (planResult.blocked) { rl.resume(); rl.prompt(); return; }
        }

        // Ask for approval
        process.stdout.write(ansi('yellow', '\n  execute? ') + ansi('gray', '[y/N] '));
        pendingApproval = { proposed };
        rl.resume();
      })
      .catch((err) => {
        process.stdout.write(
          '\n' + ansi('red', `  LLM error: ${err.message}\n`) +
          ansi('gray', `  Is ${cfg.provider} running? Try: :config set provider offline\n`)
        );
        rl.resume();
        rl.prompt();
      });
  });

  rl.on('close', () => {
    process.stdout.write(ansi('dim', '\ngoodbye.\n'));
    process.exit(0);
  });
}

function runPythonScript(relativePath, args) {
  const script = resolveRepoScript(relativePath);
  if (!script) {
    process.stderr.write(
      [
        `scbe could not find ${relativePath}.`,
        'This command needs a local SCBE-AETHERMOORE source checkout.',
        'Use the repo-local CLI, or install the full source package before running compiler/routing lanes.',
        '',
      ].join('\n')
    );
    process.exit(2);
  }
  const child = spawnSync(pythonCommand(), [script, ...args], {
    stdio: 'inherit',
  });
  if (typeof child.status === 'number') process.exit(child.status);
  process.exit(1);
}

function runCompiler(args) {
  runPythonScript('scripts/agents/scbe_code.py', args);
}

function runRouteCompiler(args) {
  runPythonScript('scripts/aetherpp/cli.py', args);
}

function runFlow(args) {
  // Bridge to scripts/scbe-system-cli.py flow <sub> — same source-checkout pattern as compile/route.
  runPythonScript('scripts/scbe-system-cli.py', ['flow', ...args]);
}

function runTrapRedirect(args) {
  // scbe trap-redirect — input-side companion to `scbe contract scan
  // --emit-redirect-prompt`. Takes prompt text via --input, --file, or
  // stdin; runs shouldPreBlock; if a SCONE-tagged rule fires DENY, prints
  // the defensive audit prompt the production proxy would forward to the
  // model in place of the attacker's text. Operator inspector — does not
  // dispatch anywhere, never quotes the attacker prompt in its output.
  let json = false;
  let inputText = null;
  let filePath = null;
  for (let i = 0; i < args.length; i += 1) {
    const tok = args[i];
    if (tok === '--json') json = true;
    else if (tok === 'help' || tok === '--help' || tok === '-h') {
      process.stdout.write(
        [
          'Usage:',
          '  scbe trap-redirect --input "<prompt text>" [--json]',
          '  scbe trap-redirect --file path/to/prompt.txt [--json]',
          '  echo "<prompt text>" | scbe trap-redirect [--json]',
          '',
          'Input-side inspector for the trap-in-good-loops gate. Runs the',
          'governance proxy preflight against the given text. If a SCONE-tagged',
          'rule fires DENY, prints the defensive audit prompt the production',
          'proxy would forward to the model instead of the original text.',
          '',
          'Companion to: scbe contract scan --emit-redirect-prompt (static side).',
          'Source-checkout required.',
          '',
        ].join('\n')
      );
      process.exit(0);
    } else if (tok === '--input') {
      inputText = args[i + 1] || '';
      i += 1;
    } else if (tok === '--file') {
      filePath = args[i + 1] || '';
      i += 1;
    }
  }
  if (inputText === null && filePath) {
    try {
      inputText = fs.readFileSync(filePath, 'utf8');
    } catch (err) {
      process.stderr.write(`scbe trap-redirect: cannot read ${filePath}: ${err.message}\n`);
      process.exit(2);
    }
  }
  if (inputText === null) {
    // Read from stdin synchronously (CLI ops are short).
    try {
      inputText = fs.readFileSync(0, 'utf8');
    } catch {
      inputText = '';
    }
  }
  inputText = String(inputText || '').trim();
  if (!inputText) {
    process.stderr.write(
      'scbe trap-redirect: no input text supplied (use --input, --file, or stdin).\n'
    );
    process.exit(2);
  }
  const governedPath = resolveRepoScript('api/_governed_output.js');
  if (!governedPath) {
    process.stderr.write(
      [
        'scbe could not find api/_governed_output.js.',
        'This command needs a local SCBE-AETHERMOORE source checkout.',
        '',
      ].join('\n')
    );
    process.exit(2);
  }
  let governed;
  try {
    governed = require(governedPath);
  } catch (err) {
    process.stderr.write(`scbe trap-redirect: failed to load governance proxy: ${err.message}\n`);
    process.exit(2);
  }
  const result = governed.shouldPreBlock(inputText);
  const auditContext = governed.isAuditContext(inputText);
  const payload = {
    schema_version: 'scbe.trap_redirect.v1',
    receipt: '',
    blocked: !!result.blocked,
    decision: result.decision || 'ALLOW',
    audit_context: auditContext,
    reasons: result.reasons || [],
    redirect: null,
  };
  if (result.redirect && result.redirect.to_prompt) {
    payload.receipt = 'SCBE_TRAP_REDIRECT=1';
    payload.redirect = {
      intervention: result.redirect.intervention || 'input_redirect',
      code: result.redirect.code || null,
      redirect_to: result.redirect.redirect_to || null,
      to_prompt: result.redirect.to_prompt,
    };
  } else {
    payload.receipt = 'SCBE_TRAP_REDIRECT=0';
  }
  if (json) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    const lines = [
      `SCBE trap-redirect: ${payload.receipt}`,
      `decision:       ${payload.decision}`,
      `blocked:        ${payload.blocked}`,
      `audit_context:  ${payload.audit_context}`,
      `reasons (${payload.reasons.length}): ${payload.reasons.join(', ') || '<none>'}`,
      '',
    ];
    if (payload.redirect) {
      lines.push(`redirect.code:        ${payload.redirect.code || '<none>'}`);
      lines.push(`redirect.redirect_to: ${payload.redirect.redirect_to || '<none>'}`);
      lines.push(`redirect.intervention: ${payload.redirect.intervention}`);
      lines.push('--- redirect.to_prompt (caller would forward this to model) ---');
      for (const line of payload.redirect.to_prompt.split('\n')) {
        lines.push(line);
      }
      lines.push('--- end redirect.to_prompt ---');
    } else {
      lines.push('No SCONE-tagged redirect produced. ');
      lines.push(
        '(Either the input did not match a SCONE rule, or audit context bypassed the gate.)'
      );
    }
    lines.push('');
    process.stdout.write(lines.join('\n'));
  }
  process.exit(payload.redirect ? 0 : 0);
}

function offlineEcho(prompt, model) {
  // Deterministic, zero-cost response. Useful for CI and dry-runs. The
  // response acknowledges the dispatched prompt without paraphrasing or
  // continuing it, so we never accidentally leak attacker text back out.
  const sha = crypto.createHash('sha256').update(prompt, 'utf8').digest('hex');
  return [
    `[scbe trap-dispatch offline echo]`,
    `model: ${model}`,
    `received_prompt_sha256: ${sha}`,
    `bytes: ${Buffer.byteLength(prompt, 'utf8')}`,
    `note: offline provider is a deterministic placeholder. Re-run with --provider ollama for a local model response.`,
  ].join('\n');
}

async function ollamaDispatch(prompt, model, ollamaUrl, timeoutMs) {
  // Pure Node 18+ fetch against local Ollama. Free (local compute), no key.
  if (typeof fetch !== 'function') {
    throw new Error('global fetch is unavailable — requires Node 18+');
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${ollamaUrl.replace(/\/$/, '')}/api/chat`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        model,
        messages: [{ role: 'user', content: prompt }],
        stream: false,
      }),
      signal: controller.signal,
    });
    if (!res.ok) {
      const body = await res.text().catch(() => '');
      throw new Error(`ollama HTTP ${res.status}: ${body.slice(0, 200)}`);
    }
    const data = await res.json();
    const message =
      data && data.message && typeof data.message.content === 'string' ? data.message.content : '';
    return message || '[ollama returned empty message.content]';
  } finally {
    clearTimeout(timer);
  }
}

function runTrapDispatch(args) {
  // scbe trap-dispatch — runs the input through shouldPreBlock like
  // trap-redirect, then actually dispatches either the original prompt
  // (when ALLOW) or the defensive redirect prompt (when DENY) to a free
  // local provider. Default provider is `offline` (deterministic echo,
  // zero network calls). Explicit `--provider ollama` opts into a local
  // Ollama daemon at OLLAMA_BASE_URL (default http://127.0.0.1:11434).
  // No paid providers — by design.
  //
  // When --workspace-root is supplied, the dispatch envelope is persisted
  // as a workspace receipt under <root>/20_receipts/trap-dispatch-<ts>-<sha>.json
  // with schema aethermoor.bus.workspace_trap_dispatch.v1 so the lineage
  // walker can surface it alongside formation/ingest/export entries.
  let json = false;
  let inputText = null;
  let filePath = null;
  let provider = 'offline';
  let model = null;
  let ollamaUrl = process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434';
  let timeoutMs = 30000;
  let workspaceRoot = null;
  let batchPath = null;
  for (let i = 0; i < args.length; i += 1) {
    const tok = args[i];
    if (tok === '--json') json = true;
    else if (tok === 'help' || tok === '--help' || tok === '-h') {
      process.stdout.write(
        [
          'Usage:',
          '  scbe trap-dispatch --input "<prompt text>" [--provider offline|ollama] [--model <name>] [--json]',
          '  scbe trap-dispatch --file path/to/prompt.txt [--provider ollama --model llama3.2] [--json]',
          '  scbe trap-dispatch --input "<prompt>" --workspace-root <path> [--json]',
          '  scbe trap-dispatch --batch prompts.jsonl [--workspace-root <path>] [--json]',
          '  echo "<prompt text>" | scbe trap-dispatch [--json]',
          '',
          'Trap-in-good-loops dispatcher. Runs the governance proxy preflight on the',
          'input; if a SCONE-tagged rule fires DENY, dispatches the DEFENSIVE redirect',
          'prompt to the chosen provider in place of the attacker text. Otherwise',
          'dispatches the original prompt. Never quotes the attacker prompt in output.',
          '',
          'Providers (free only — by design):',
          '  offline (default)  Deterministic echo. Zero cost, zero network calls.',
          '  ollama             Local Ollama daemon at $OLLAMA_BASE_URL or 127.0.0.1:11434.',
          '',
          'Audit chain integration:',
          '  --workspace-root <path>  Persist envelope as a workspace receipt.',
          '                           Schema: aethermoor.bus.workspace_trap_dispatch.v1',
          '                           Lineage walker reports trap_dispatch_count and',
          '                           trap_redirect_count over the chain.',
          '',
          'Batch mode (adversarial corpus testing):',
          '  --batch <file.jsonl>     One prompt per line, either raw text or a JSON',
          '                           object with {"input":"...","tag":"...optional"}.',
          '                           Emits an aggregate summary; one envelope per row.',
          '',
          'Receipt: SCBE_TRAP_DISPATCH=1 on a clean dispatch (redirected or passthrough),',
          '         SCBE_TRAP_DISPATCH=0 on dispatch failure.',
          'Schema:  scbe.trap_dispatch.v1 (single) | scbe.trap_dispatch_batch.v1 (batch)',
          '',
        ].join('\n')
      );
      process.exit(0);
    } else if (tok === '--input') {
      inputText = args[i + 1] || '';
      i += 1;
    } else if (tok === '--file') {
      filePath = args[i + 1] || '';
      i += 1;
    } else if (tok === '--provider') {
      provider = (args[i + 1] || '').toLowerCase();
      i += 1;
    } else if (tok === '--model') {
      model = args[i + 1] || '';
      i += 1;
    } else if (tok === '--ollama-url') {
      ollamaUrl = args[i + 1] || ollamaUrl;
      i += 1;
    } else if (tok === '--timeout-ms') {
      const parsed = parseInt(args[i + 1] || '', 10);
      if (Number.isFinite(parsed) && parsed > 0) timeoutMs = parsed;
      i += 1;
    } else if (tok === '--workspace-root') {
      workspaceRoot = args[i + 1] || '';
      i += 1;
    } else if (tok === '--batch') {
      batchPath = args[i + 1] || '';
      i += 1;
    }
  }
  if (batchPath) {
    return runTrapDispatchBatch({
      batchPath,
      json,
      provider,
      model,
      ollamaUrl,
      timeoutMs,
      workspaceRoot,
    });
  }
  if (inputText === null && filePath) {
    try {
      inputText = fs.readFileSync(filePath, 'utf8');
    } catch (err) {
      process.stderr.write(`scbe trap-dispatch: cannot read ${filePath}: ${err.message}\n`);
      process.exit(2);
    }
  }
  if (inputText === null) {
    try {
      inputText = fs.readFileSync(0, 'utf8');
    } catch {
      inputText = '';
    }
  }
  inputText = String(inputText || '').trim();
  if (!inputText) {
    process.stderr.write(
      'scbe trap-dispatch: no input text supplied (use --input, --file, or stdin).\n'
    );
    process.exit(2);
  }
  const allowedProviders = new Set(['offline', 'ollama']);
  if (!allowedProviders.has(provider)) {
    process.stderr.write(
      `scbe trap-dispatch: unsupported provider "${provider}". Use offline or ollama (free providers only — by design).\n`
    );
    process.exit(2);
  }
  if (!model) model = provider === 'ollama' ? 'llama3.2' : 'offline-echo';
  const governedPath = resolveRepoScript('api/_governed_output.js');
  if (!governedPath) {
    process.stderr.write(
      [
        'scbe could not find api/_governed_output.js.',
        'This command needs a local SCBE-AETHERMOORE source checkout.',
        '',
      ].join('\n')
    );
    process.exit(2);
  }
  let governed;
  try {
    governed = require(governedPath);
  } catch (err) {
    process.stderr.write(`scbe trap-dispatch: failed to load governance proxy: ${err.message}\n`);
    process.exit(2);
  }
  const gateResult = governed.shouldPreBlock(inputText);
  const auditContext = governed.isAuditContext(inputText);
  const inputSha = crypto.createHash('sha256').update(inputText, 'utf8').digest('hex');
  let dispatchedPrompt;
  let redirectEmitted = false;
  if (gateResult.redirect && gateResult.redirect.to_prompt) {
    dispatchedPrompt = gateResult.redirect.to_prompt;
    redirectEmitted = true;
  } else {
    dispatchedPrompt = inputText;
  }
  const dispatchedSha = crypto.createHash('sha256').update(dispatchedPrompt, 'utf8').digest('hex');
  const payload = {
    schema_version: 'scbe.trap_dispatch.v1',
    receipt: 'SCBE_TRAP_DISPATCH=0',
    input_sha256: inputSha,
    input_bytes: Buffer.byteLength(inputText, 'utf8'),
    gate_decision: gateResult.decision || 'ALLOW',
    blocked: !!gateResult.blocked,
    redirect_emitted: redirectEmitted,
    redirect_code: redirectEmitted ? gateResult.redirect.code || null : null,
    audit_context: auditContext,
    reasons: gateResult.reasons || [],
    provider,
    model,
    dispatched_prompt_sha256: dispatchedSha,
    dispatched_prompt_bytes: Buffer.byteLength(dispatchedPrompt, 'utf8'),
    response: '',
    error: null,
  };
  const finish = (exitCode) => {
    // Persist as a workspace receipt before printing/exiting so the audit
    // chain captures the dispatch even if the caller pipes stdout away.
    if (workspaceRoot) {
      const persistResult = persistTrapDispatchReceipt(workspaceRoot, payload);
      payload.workspace_receipt_path = persistResult.receipt_path;
      payload.workspace_root = persistResult.workspace_root;
      if (persistResult.error) {
        // Persistence failure should be visible but must not silently dispatch
        // — surface it on stderr but keep the receipt flag honest about what
        // happened to the model call.
        process.stderr.write(
          `scbe trap-dispatch: receipt persist failed: ${persistResult.error}\n`
        );
      }
    }
    if (json) {
      process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    } else {
      const lines = [
        `SCBE trap-dispatch: ${payload.receipt}`,
        `provider:               ${payload.provider}`,
        `model:                  ${payload.model}`,
        `gate_decision:          ${payload.gate_decision}`,
        `redirect_emitted:       ${payload.redirect_emitted}`,
        `audit_context:          ${payload.audit_context}`,
        `input_sha256:           ${payload.input_sha256}`,
        `dispatched_prompt_sha:  ${payload.dispatched_prompt_sha256}`,
        `reasons (${payload.reasons.length}):       ${payload.reasons.join(', ') || '<none>'}`,
        '',
      ];
      if (payload.workspace_receipt_path) {
        lines.push(`workspace_receipt:      ${payload.workspace_receipt_path}`);
      }
      if (payload.error) {
        lines.push(`error: ${payload.error}`);
      } else {
        lines.push('--- response ---');
        for (const line of String(payload.response || '').split('\n')) lines.push(line);
        lines.push('--- end response ---');
      }
      lines.push('');
      process.stdout.write(lines.join('\n'));
    }
    process.exit(exitCode);
  };
  if (provider === 'offline') {
    payload.response = offlineEcho(dispatchedPrompt, model);
    payload.receipt = 'SCBE_TRAP_DISPATCH=1';
    finish(0);
    return;
  }
  // provider === 'ollama'
  ollamaDispatch(dispatchedPrompt, model, ollamaUrl, timeoutMs)
    .then((response) => {
      payload.response = response;
      payload.receipt = 'SCBE_TRAP_DISPATCH=1';
      finish(0);
    })
    .catch((err) => {
      payload.error = err && err.message ? err.message : String(err);
      payload.receipt = 'SCBE_TRAP_DISPATCH=0';
      finish(1);
    });
}

function persistTrapDispatchReceipt(workspaceRoot, dispatchPayload) {
  // Writes the trap-dispatch envelope as a workspace receipt under
  // <root>/20_receipts/trap-dispatch-<utc-ts>-<sha-prefix>.json so the
  // lineage walker can surface it. Returns { receipt_path, workspace_root,
  // error } — never throws, since this is best-effort persistence inside
  // the runner's `finish` callback.
  try {
    const resolvedRoot = path.resolve(workspaceRoot);
    if (!fs.existsSync(resolvedRoot) || !fs.statSync(resolvedRoot).isDirectory()) {
      return {
        receipt_path: '',
        workspace_root: resolvedRoot,
        error: `workspace not found at ${resolvedRoot}`,
      };
    }
    const receiptsDir = path.join(resolvedRoot, '20_receipts');
    fs.mkdirSync(receiptsDir, { recursive: true });
    const tsCompact = new Date().toISOString().replace(/[:.]/g, '-');
    const shaPrefix = (dispatchPayload.input_sha256 || '').slice(0, 12) || 'no-sha';
    const fileName = `trap-dispatch-${tsCompact}-${shaPrefix}.json`;
    const receiptPath = path.join(receiptsDir, fileName);
    const workspaceReceipt = {
      schema_version: 'aethermoor.bus.workspace_trap_dispatch.v1',
      receipt:
        dispatchPayload.receipt === 'SCBE_TRAP_DISPATCH=1'
          ? 'SCBE_WORKSPACE_TRAP_DISPATCH=1'
          : 'SCBE_WORKSPACE_TRAP_DISPATCH=0',
      created_at: new Date().toISOString(),
      input_sha256: dispatchPayload.input_sha256,
      input_bytes: dispatchPayload.input_bytes,
      gate_decision: dispatchPayload.gate_decision,
      blocked: dispatchPayload.blocked,
      redirect_emitted: dispatchPayload.redirect_emitted,
      redirect_code: dispatchPayload.redirect_code,
      audit_context: dispatchPayload.audit_context,
      reasons: dispatchPayload.reasons || [],
      provider: dispatchPayload.provider,
      model: dispatchPayload.model,
      dispatched_prompt_sha256: dispatchPayload.dispatched_prompt_sha256,
      dispatched_prompt_bytes: dispatchPayload.dispatched_prompt_bytes,
      response_bytes: Buffer.byteLength(String(dispatchPayload.response || ''), 'utf8'),
      response_sha256: crypto
        .createHash('sha256')
        .update(String(dispatchPayload.response || ''), 'utf8')
        .digest('hex'),
      error: dispatchPayload.error || null,
    };
    fs.writeFileSync(receiptPath, `${JSON.stringify(workspaceReceipt, null, 2)}\n`, 'utf8');
    return { receipt_path: receiptPath, workspace_root: resolvedRoot, error: null };
  } catch (err) {
    return {
      receipt_path: '',
      workspace_root: workspaceRoot,
      error: err && err.message ? err.message : String(err),
    };
  }
}

function parseBatchLine(line) {
  // Each JSONL row is either a raw string prompt or a JSON object with
  // {"input":"...","tag":"..."}. Anything else is skipped with an error.
  const trimmed = String(line || '').trim();
  if (!trimmed) return null;
  if (trimmed.startsWith('{')) {
    try {
      const obj = JSON.parse(trimmed);
      const input = typeof obj.input === 'string' ? obj.input : '';
      if (!input) return { error: 'object missing string "input" field' };
      return { input, tag: typeof obj.tag === 'string' ? obj.tag : '' };
    } catch (err) {
      return { error: `JSON parse error: ${err.message}` };
    }
  }
  return { input: trimmed, tag: '' };
}

function dispatchSinglePrompt(inputText, provider, model, ollamaUrl, timeoutMs, governed) {
  // Pure helper used by both the single-shot CLI path and the batch path.
  // Returns a Promise of the dispatch envelope. For the offline provider
  // the promise resolves synchronously on the next tick.
  const gateResult = governed.shouldPreBlock(inputText);
  const auditContext = governed.isAuditContext(inputText);
  const inputSha = crypto.createHash('sha256').update(inputText, 'utf8').digest('hex');
  let dispatchedPrompt;
  let redirectEmitted = false;
  if (gateResult.redirect && gateResult.redirect.to_prompt) {
    dispatchedPrompt = gateResult.redirect.to_prompt;
    redirectEmitted = true;
  } else {
    dispatchedPrompt = inputText;
  }
  const dispatchedSha = crypto.createHash('sha256').update(dispatchedPrompt, 'utf8').digest('hex');
  const envelope = {
    schema_version: 'scbe.trap_dispatch.v1',
    receipt: 'SCBE_TRAP_DISPATCH=0',
    input_sha256: inputSha,
    input_bytes: Buffer.byteLength(inputText, 'utf8'),
    gate_decision: gateResult.decision || 'ALLOW',
    blocked: !!gateResult.blocked,
    redirect_emitted: redirectEmitted,
    redirect_code: redirectEmitted ? gateResult.redirect.code || null : null,
    audit_context: auditContext,
    reasons: gateResult.reasons || [],
    provider,
    model,
    dispatched_prompt_sha256: dispatchedSha,
    dispatched_prompt_bytes: Buffer.byteLength(dispatchedPrompt, 'utf8'),
    response: '',
    error: null,
  };
  if (provider === 'offline') {
    envelope.response = offlineEcho(dispatchedPrompt, model);
    envelope.receipt = 'SCBE_TRAP_DISPATCH=1';
    return Promise.resolve(envelope);
  }
  return ollamaDispatch(dispatchedPrompt, model, ollamaUrl, timeoutMs)
    .then((response) => {
      envelope.response = response;
      envelope.receipt = 'SCBE_TRAP_DISPATCH=1';
      return envelope;
    })
    .catch((err) => {
      envelope.error = err && err.message ? err.message : String(err);
      envelope.receipt = 'SCBE_TRAP_DISPATCH=0';
      return envelope;
    });
}

function runTrapDispatchBatch(options) {
  const {
    batchPath,
    json,
    provider,
    model: requestedModel,
    ollamaUrl,
    timeoutMs,
    workspaceRoot,
  } = options;
  const allowedProviders = new Set(['offline', 'ollama']);
  if (!allowedProviders.has(provider)) {
    process.stderr.write(
      `scbe trap-dispatch: unsupported provider "${provider}". Use offline or ollama (free providers only — by design).\n`
    );
    process.exit(2);
  }
  const model = requestedModel || (provider === 'ollama' ? 'llama3.2' : 'offline-echo');
  let raw;
  try {
    raw = fs.readFileSync(batchPath, 'utf8');
  } catch (err) {
    process.stderr.write(`scbe trap-dispatch: cannot read ${batchPath}: ${err.message}\n`);
    process.exit(2);
  }
  const lines = raw.split(/\r?\n/);
  const rows = [];
  for (let lineNo = 0; lineNo < lines.length; lineNo += 1) {
    const parsed = parseBatchLine(lines[lineNo]);
    if (parsed === null) continue;
    parsed.line_no = lineNo + 1;
    rows.push(parsed);
  }
  if (rows.length === 0) {
    process.stderr.write(
      `scbe trap-dispatch: batch file ${batchPath} contained zero usable rows.\n`
    );
    process.exit(2);
  }
  const governedPath = resolveRepoScript('api/_governed_output.js');
  if (!governedPath) {
    process.stderr.write(
      'scbe could not find api/_governed_output.js. Source checkout required.\n'
    );
    process.exit(2);
  }
  let governed;
  try {
    governed = require(governedPath);
  } catch (err) {
    process.stderr.write(`scbe trap-dispatch: failed to load governance proxy: ${err.message}\n`);
    process.exit(2);
  }
  // Process rows sequentially so ollama doesn't open N concurrent sockets to
  // a local daemon. Sequential also gives deterministic ordering in receipts.
  (async () => {
    const results = [];
    let dispatchPassCount = 0;
    let dispatchFailCount = 0;
    let redirectCount = 0;
    let denyCount = 0;
    let allowCount = 0;
    for (const row of rows) {
      if (row.error) {
        results.push({
          line_no: row.line_no,
          tag: row.tag || '',
          error: row.error,
        });
        dispatchFailCount += 1;
        continue;
      }
      let envelope;
      try {
        envelope = await dispatchSinglePrompt(
          row.input,
          provider,
          model,
          ollamaUrl,
          timeoutMs,
          governed
        );
      } catch (err) {
        envelope = {
          schema_version: 'scbe.trap_dispatch.v1',
          receipt: 'SCBE_TRAP_DISPATCH=0',
          error: err && err.message ? err.message : String(err),
        };
      }
      if (envelope.receipt === 'SCBE_TRAP_DISPATCH=1') dispatchPassCount += 1;
      else dispatchFailCount += 1;
      if (envelope.redirect_emitted) redirectCount += 1;
      if (envelope.gate_decision === 'DENY') denyCount += 1;
      if (envelope.gate_decision === 'ALLOW') allowCount += 1;
      let workspaceReceiptPath = '';
      if (workspaceRoot) {
        const persistResult = persistTrapDispatchReceipt(workspaceRoot, envelope);
        workspaceReceiptPath = persistResult.receipt_path;
        if (persistResult.error) {
          process.stderr.write(
            `scbe trap-dispatch: batch row ${row.line_no} persist failed: ${persistResult.error}\n`
          );
        }
      }
      results.push({
        line_no: row.line_no,
        tag: row.tag || '',
        // do NOT echo the input text or response into the batch summary — keep
        // the surface attacker-text-free. Reviewers can pull the workspace
        // receipt by sha if they need detail.
        input_sha256: envelope.input_sha256,
        gate_decision: envelope.gate_decision,
        redirect_emitted: envelope.redirect_emitted,
        receipt: envelope.receipt,
        workspace_receipt_path: workspaceReceiptPath || null,
        error: envelope.error || null,
      });
    }
    const summary = {
      schema_version: 'scbe.trap_dispatch_batch.v1',
      receipt:
        dispatchFailCount === 0 ? 'SCBE_TRAP_DISPATCH_BATCH=1' : 'SCBE_TRAP_DISPATCH_BATCH=0',
      generated_at: new Date().toISOString(),
      provider,
      model,
      workspace_root: workspaceRoot ? path.resolve(workspaceRoot) : null,
      total_rows: rows.length,
      dispatch_pass: dispatchPassCount,
      dispatch_fail: dispatchFailCount,
      redirect_emitted: redirectCount,
      deny: denyCount,
      allow: allowCount,
      results,
    };
    if (json) {
      process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
    } else {
      const lines2 = [
        `SCBE trap-dispatch batch: ${summary.receipt}`,
        `provider:           ${summary.provider}`,
        `model:              ${summary.model}`,
        `total_rows:         ${summary.total_rows}`,
        `dispatch_pass:      ${summary.dispatch_pass}`,
        `dispatch_fail:      ${summary.dispatch_fail}`,
        `redirect_emitted:   ${summary.redirect_emitted}`,
        `deny / allow:       ${summary.deny} / ${summary.allow}`,
      ];
      if (summary.workspace_root) lines2.push(`workspace_root:     ${summary.workspace_root}`);
      lines2.push('');
      process.stdout.write(lines2.join('\n'));
    }
    process.exit(dispatchFailCount === 0 ? 0 : 1);
  })();
}

function runContract(args) {
  // scbe contract scan [path] [--json] — SCONE-class static prefilter for Solidity.
  const sub = args[0] || 'help';
  if (sub === 'help' || sub === '--help' || sub === '-h') {
    process.stdout.write(
      [
        'Usage:',
        '  scbe contract scan <file.sol> [--json] [--fail-on-finding]',
        '  cat file.sol | scbe contract scan [--json]',
        '',
        'SCONE-class static prefilter for Solidity smart contracts. Heuristic,',
        'not an AI-driven audit. Cross-function and data-flow exploits will be',
        'missed — see docs/external/SCONE_BENCH_2026_05_14.md for full scope.',
        '',
        'Receipt: SCBE_CONTRACT_SCAN_PASS=1 on a clean contract, otherwise a',
        'structured findings array with rule, severity (tier mapping), line,',
        'function name, and detail.',
        '',
      ].join('\n')
    );
    process.exit(0);
  }
  if (sub !== 'scan') {
    process.stderr.write(`unknown contract subcommand: ${sub}\n`);
    process.exit(2);
  }
  runPythonScript('scripts/contracts/scbe_contract_scan.py', args.slice(1));
}

// Top-level commands scbe handles directly. Used by the typo-suggestion guard.
// Order doesn't matter; this list is the complete set of scbe-owned verbs.
const KNOWN_COMMANDS = [
  'help',
  'version',
  'demo',
  'magic',
  'selftest',
  'doctor',
  'credits',
  'hosted-run',
  'upgrade',
  'shell',
  'run',
  'status',
  'liboqs',
  'history',
  'flow',
  'workspace',
  'agent-bus',
  'agentbus',
  'abacus',
  'contract',
  'trap-redirect',
  'trap-dispatch',
  'compile-ca',
  'ca-plan',
  'render-op',
  'compile',
  'route',
  'aetherpp',
];

function levenshtein(a, b) {
  if (a === b) return 0;
  if (!a) return b.length;
  if (!b) return a.length;
  const m = a.length;
  const n = b.length;
  let prev = new Array(n + 1);
  let curr = new Array(n + 1);
  for (let j = 0; j <= n; j += 1) prev[j] = j;
  for (let i = 1; i <= m; i += 1) {
    curr[0] = i;
    for (let j = 1; j <= n; j += 1) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      curr[j] = Math.min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost);
    }
    const swap = prev;
    prev = curr;
    curr = swap;
  }
  return prev[n];
}

// Returns the closest known command if input is plausibly a typo (distance <= 2
// AND shorter than the input length so we don't suggest "run" for "x"). Returns
// null if the input doesn't look like a typo of any scbe command — in that case
// the caller should fall through to the geoseal passthrough, which has its own
// (broader) set of subcommands we don't know about.
function suggestCommand(input) {
  if (!input || KNOWN_COMMANDS.includes(input)) return null;
  let best = null;
  let bestDist = Infinity;
  for (const cmd of KNOWN_COMMANDS) {
    const d = levenshtein(input, cmd);
    if (d < bestDist) {
      bestDist = d;
      best = cmd;
    }
  }
  if (bestDist <= 2 && bestDist < input.length) return best;
  return null;
}

// ---------------------------------------------------------------------------
// Natural-language command resolver + autocorrect ledger
// ---------------------------------------------------------------------------

const INTENT_TABLE = [
  {
    patterns: ['verify', 'check', 'audit', 'clean', 'tamper', 'integrity', 'safe', 'workspace'],
    command: 'workspace verify --all',
    tongue: 'CA',
    description: 'Verify workspace integrity — tamper-check all governed records',
  },
  {
    patterns: ['report', 'summary', 'dashboard', 'health', 'overview', 'workspace'],
    command: 'workspace report',
    tongue: 'DR',
    description: 'Print a workspace governance report / dashboard',
  },
  {
    patterns: ['lineage', 'history', 'trail', 'chain', 'receipts', 'audit'],
    command: 'workspace lineage',
    tongue: 'DR',
    description: 'Show workspace audit trail and lineage chain',
  },
  {
    patterns: ['new', 'create', 'make', 'start', 'init', 'workspace'],
    command: 'workspace new',
    tongue: 'KO',
    description: 'Create a new governed workspace',
  },
  {
    patterns: ['ingest', 'add', 'intake', 'bring', 'file'],
    command: 'workspace ingest',
    tongue: 'UM',
    description: 'Ingest a file into the workspace',
  },
  {
    patterns: ['export', 'package', 'bundle', 'ship', 'handoff', 'workspace'],
    command: 'workspace export',
    tongue: 'AV',
    description: 'Export / package the workspace for handoff',
  },
  {
    patterns: ['restore', 'import', 'workspace'],
    command: 'workspace import',
    tongue: 'KO',
    description: 'Restore or import a workspace',
  },
  {
    patterns: ['send', 'dispatch', 'submit', 'task'],
    command: 'agent-bus send',
    tongue: 'AV',
    description: 'Send / dispatch a task to the agent bus',
  },
  {
    patterns: ['scan', 'audit', 'contract', 'solidity'],
    command: 'contract scan',
    tongue: 'RU',
    description: 'Scan / audit a Solidity contract',
  },
  {
    patterns: ['trap', 'redirect', 'check', 'prompt'],
    command: 'trap-redirect',
    tongue: 'RU',
    description: 'Run the trap-redirect prompt-safety layer',
  },
  {
    patterns: ['doctor', 'diagnose', 'working'],
    command: 'doctor --json',
    tongue: 'CA',
    description: 'Run diagnostics / health check',
  },
  {
    patterns: ['status', 'current', 'state', 'whats', 'going'],
    command: 'status',
    tongue: 'DR',
    description: 'Show current system status',
  },
  {
    patterns: ['history', 'recent', 'commands'],
    command: 'history --limit 20',
    tongue: 'DR',
    description: 'Show recent command history',
  },
  {
    patterns: ['version', 'what'],
    command: 'version',
    tongue: 'KO',
    description: 'Print the scbe version',
  },
  {
    patterns: ['help', 'commands'],
    command: '--help',
    tongue: 'KO',
    description: 'Show help / list available commands',
  },
  {
    patterns: ['selftest', 'test'],
    command: 'selftest',
    tongue: 'CA',
    description: 'Run the built-in self-test suite',
  },
  {
    patterns: ['abacus', 'score', 'governance'],
    command: 'abacus run',
    tongue: 'RU',
    description: 'Compute a governance score via the abacus',
  },
];

const NL_STOP_WORDS = new Set([
  'a',
  'an',
  'the',
  'is',
  'if',
  'my',
  'your',
  'our',
  'it',
  'in',
  'of',
  'to',
  'for',
  'with',
  'on',
  'at',
  'by',
  'as',
  'be',
  'do',
  'can',
  'will',
  'how',
  'what',
  'this',
  'that',
  'these',
  'those',
  'i',
  'we',
  'you',
  'me',
  'us',
  'please',
  'and',
  'or',
  'not',
  'all',
  'any',
  'get',
  'set',
  'let',
  'put',
  'go',
  'run',
]);

function nlVocab() {
  const words = new Set();
  for (const entry of INTENT_TABLE) {
    for (const p of entry.patterns) {
      for (const w of p.split(/\s+/)) {
        if (w) words.add(w.toLowerCase());
      }
    }
  }
  for (const cmd of KNOWN_COMMANDS) words.add(cmd.toLowerCase());
  return words;
}

function correctWord(word, vocab) {
  if (word.length < 4) return { original: word, corrected: word, changed: false };
  if (vocab.has(word)) return { original: word, corrected: word, changed: false };
  const maxDist = Math.min(2, Math.floor(word.length / 3));
  let best = null;
  let bestDist = Infinity;
  for (const v of vocab) {
    const d = levenshtein(word, v);
    if (d <= maxDist && d < bestDist) {
      bestDist = d;
      best = v;
    }
  }
  if (best !== null) return { original: word, corrected: best, changed: true };
  return { original: word, corrected: word, changed: false };
}

function resolveNaturalLanguage(rawInput) {
  // 1. Normalise
  const lower = rawInput.toLowerCase().replace(/[^a-z0-9\s-]/g, ' ');
  // 2. Tokenise and remove stop words
  const rawWords = lower.split(/\s+/).filter((w) => w && !NL_STOP_WORDS.has(w));
  // 3. Autocorrect
  const vocab = nlVocab();
  const correctionResults = rawWords.map((w) => correctWord(w, vocab));
  const corrections = correctionResults
    .filter((r) => r.changed)
    .map((r) => ({ original: r.original, corrected: r.corrected }));
  const tokens = correctionResults.map((r) => r.corrected);
  const corrected_input = tokens.join(' ');
  // 4. Score each intent
  const scored = INTENT_TABLE.map((entry) => {
    const patternWords = entry.patterns.flatMap((p) => p.split(/\s+/));
    const matchCount = patternWords.filter((pw) => tokens.includes(pw)).length;
    let score = matchCount / Math.max(1, tokens.length);
    // Subword boost
    for (const token of tokens) {
      const isSubword = entry.patterns.some(
        (p) => p.includes(token) && !tokens.includes(token) === false
      );
      if (isSubword) score += 0.1;
    }
    // Specificity boost: if a token exactly matches the FIRST pattern entry, the intent
    // is domain-specific for that term and should win ties (e.g. "lineage" beats "report").
    if (tokens.includes(entry.patterns[0])) score += 0.15;
    return { command: entry.command, score, tongue: entry.tongue, description: entry.description };
  });
  scored.sort((a, b) => b.score - a.score);
  const top = scored[0];
  const resolved_command = top && top.score > 0 ? top.command : null;
  const confidence = top ? top.score : 0;
  const tongue = top ? top.tongue : '';
  const description = top ? top.description : '';
  const candidates = scored
    .slice(0, 3)
    .map((s) => ({ command: s.command, score: s.score, tongue: s.tongue }));
  return {
    resolved_command,
    confidence,
    tongue,
    description,
    corrections,
    corrected_input,
    candidates,
  };
}

function writeLedger(entry) {
  const dir = path.join(os.homedir(), '.scbe');
  try {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    const line = JSON.stringify({ schema: 'scbe.nl_input.v1', ...entry }) + '\n';
    fs.appendFileSync(path.join(dir, 'input_ledger.jsonl'), line, 'utf8');
  } catch (_e) {
    // Ledger write failure is non-fatal
  }
}

function runNaturalLanguage(rawInput, flags) {
  const result = resolveNaturalLanguage(rawInput);
  const ledgerBase = {
    ts: new Date().toISOString(),
    original: rawInput,
    corrected_input: result.corrected_input,
    corrections: result.corrections,
    resolved_command: result.resolved_command,
    confidence: result.confidence,
    tongue: result.tongue,
  };
  writeLedger({ ...ledgerBase, executed: false, exit_code: null });

  if (flags.json) {
    process.stdout.write(
      JSON.stringify({ ...ledgerBase, executed: false, exit_code: null }, null, 2) + '\n'
    );
    process.exit(0);
  }

  const pct = Math.round(result.confidence * 100);

  if (result.confidence < 0.3) {
    process.stderr.write(`scbe: I don't know how to do that.\nTop guesses:\n`);
    for (const c of result.candidates) {
      process.stderr.write(
        `  scbe ${c.command}  [${c.tongue}] (score: ${Math.round(c.score * 100)}%)\n`
      );
    }
    process.exit(2);
  }

  if (result.confidence < 0.6) {
    process.stderr.write(
      `scbe: Not sure. This might mean:\n` +
        `  scbe ${result.resolved_command}\n` +
        `  (confidence: ${pct}%)\n` +
        `Run with --yes to execute without confirmation.\n`
    );
    process.exit(2);
  }

  // confidence >= 0.7
  for (const c of result.corrections) {
    process.stdout.write(`[autocorrect] '${c.original}' -> '${c.corrected}'\n`);
  }
  process.stdout.write(`[scbe] I will run: scbe ${result.resolved_command}\n`);
  process.stdout.write(`[route] ${result.tongue} — ${result.description}\n`);

  function execute() {
    const cmdTokens = result.resolved_command.split(' ');
    const child = spawnSync(process.execPath, [__filename, ...cmdTokens], { stdio: 'inherit' });
    const exitCode = typeof child.status === 'number' ? child.status : 1;
    writeLedger({ ...ledgerBase, executed: true, exit_code: exitCode });
    process.exit(exitCode);
  }

  if (flags.yes) {
    execute();
  } else {
    process.stderr.write('Press Enter to confirm, Ctrl+C to cancel: ');
    const buf = Buffer.alloc(4096);
    try {
      fs.readSync(0, buf, 0, buf.length, null);
    } catch (_) {}
    // any response (including just Enter) = confirmed
    execute();
  }
}

// ---------------------------------------------------------------------------
// End natural-language resolver
// ---------------------------------------------------------------------------

function resolveHarmonicModule() {
  try {
    return require('scbe-aethermoore/harmonic');
  } catch (_err) {
    const local = path.resolve(repoRoot(), 'dist', 'src', 'harmonic', 'index.js');
    if (fs.existsSync(local)) return require(local);
    return null;
  }
}

function parseAbacusFlag(args, key) {
  const idx = args.indexOf(key);
  if (idx < 0 || idx + 1 >= args.length) return null;
  const value = Number(args[idx + 1]);
  return Number.isFinite(value) ? value : null;
}

function runAbacus(args) {
  const sub = args[0] || 'help';
  if (sub === 'help' || sub === '--help' || sub === '-h') {
    process.stdout.write(
      [
        'Usage:',
        '  scbe abacus run --d-h <value> --pd <value> [--json]',
        '',
        'Deterministic BigInt mechanical scoring for L12 harmonic wall + L13 tier.',
        'Same inputs produce bit-identical scores and tiers on every platform.',
        '',
        'Formula:  H(d_h, pd) = 1 / (1 + d_h + 2*pd)',
        'Tiers:    H >= 0.65 ALLOW; >= 0.45 QUARANTINE; >= 0.25 ESCALATE; else DENY',
        'Trit:     +1 ALLOW, 0 uncertain (QUARANTINE/ESCALATE), -1 DENY',
        '',
      ].join('\n')
    );
    process.exit(0);
  }
  if (sub !== 'run') {
    process.stderr.write(`unknown abacus subcommand: ${sub}\n`);
    process.exit(2);
  }
  const d_h = parseAbacusFlag(args, '--d-h');
  const phase_dev = parseAbacusFlag(args, '--pd');
  if (d_h === null || phase_dev === null) {
    process.stderr.write('scbe abacus run requires --d-h <value> --pd <value>\n');
    process.exit(2);
  }
  const harmonic = resolveHarmonicModule();
  if (!harmonic || typeof harmonic.runGovernanceAbacus !== 'function') {
    process.stderr.write(
      'scbe abacus requires scbe-aethermoore (>=4.1) with the governanceAbacus export.\n' +
        'Install with: npm i -g scbe-aethermoore\n'
    );
    process.exit(2);
  }
  const run = harmonic.runGovernanceAbacus({ d_h, phase_dev });
  const asJson = args.includes('--json');
  if (asJson) {
    const payload = {
      schema_version: 'scbe_governance_abacus_v1',
      input: run.input,
      config: { scale: run.config.scale.toString() },
      beads: {
        d_h: { position: run.beads.d_h.position.toString(), display: run.beads.d_h.display },
        phase_dev: {
          position: run.beads.phase_dev.position.toString(),
          display: run.beads.phase_dev.display,
        },
        denominator: {
          position: run.beads.denominator.position.toString(),
          display: run.beads.denominator.display,
        },
        score: { position: run.beads.score.position.toString(), display: run.beads.score.display },
      },
      score: { num: run.score.num.toString(), den: run.score.den.toString() },
      score_decimal: run.score_decimal,
      tier: run.tier,
      trit: run.trit,
    };
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    process.stdout.write(harmonic.formatAbacusBoard(run));
  }
  process.exit(0);
}

function resolveAgentBusBin() {
  const localFallback = path.resolve(
    __dirname,
    '..',
    '..',
    'agent-bus',
    'bin',
    'scbe-agent-bus.cjs'
  );
  try {
    fs.accessSync(localFallback);
    return localFallback;
  } catch (_fallbackErr) {
    // Continue to the installed package lookup below.
  }
  try {
    const entry = require.resolve('scbe-agent-bus/package.json');
    return path.resolve(path.dirname(entry), 'bin', 'scbe-agent-bus.cjs');
  } catch (_err) {
    return null;
  }
}

function runAgentBus(args) {
  const target = resolveAgentBusBin();
  if (!target) {
    process.stderr.write(
      'scbe agent-bus requires scbe-agent-bus. Install with: npm i -g scbe-agent-bus\n'
    );
    process.exit(2);
  }
  const child = spawnSync(process.execPath, [target, ...args], { stdio: 'inherit' });
  if (typeof child.status === 'number') process.exit(child.status);
  process.exit(1);
}

function runUpgrade(args) {
  // Aliased to credits semantically; if scbe-agent-bus is installed, defer to its upgrade
  // command so the single source of truth for hosted-run guidance lives in one place.
  const target = resolveAgentBusBin();
  if (target) {
    const child = spawnSync(process.execPath, [target, 'upgrade', ...args], { stdio: 'inherit' });
    if (typeof child.status === 'number') process.exit(child.status);
    process.exit(0);
  }
  // Fallback: print the same payload as `scbe credits` so the upgrade command always works.
  const asJson = args.includes('--json');
  if (asJson) {
    process.stdout.write(`${JSON.stringify(SERVICE_CREDITS, null, 2)}\n`);
  } else {
    process.stdout.write(
      [
        'SCBE Service Credits — hosted runs',
        '',
        SERVICE_CREDITS.policy,
        `Fee: ${SERVICE_CREDITS.fee}`,
        '',
        `Hosted run intake: ${SERVICE_CREDITS.hosted_run_intake}`,
        `Service credits:    ${SERVICE_CREDITS.service_credits}`,
        `Top up:             ${SERVICE_CREDITS.top_up}`,
        '',
        'Install scbe-agent-bus for the full upgrade flow: npm i -g scbe-agent-bus',
        '',
      ].join('\n')
    );
  }
  process.exit(0);
}

function runSelftest() {
  const checks = [['version', '--json'], ['doctor', '--json']];
  const results = checks.map((args) => {
    const child = spawnSync(process.execPath, [__filename, ...args], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    return {
      command: `scbe ${args.join(' ')}`,
      ok: child.status === 0,
      status: child.status,
      stdout_preview: String(child.stdout || '').slice(0, 500),
      stderr_preview: String(child.stderr || '').slice(0, 500),
    };
  });
  const compilerScript = resolveRepoScript('scripts/agents/scbe_code.py');
  if (compilerScript) {
    const child = spawnSync(
      pythonCommand(),
      [compilerScript, 'ca-plan', '--ops', 'abs abs add', '--json'],
      {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'pipe'],
      }
    );
    results.push({
      command: 'scbe ca-plan --ops "abs abs add" --json',
      ok: child.status === 0,
      status: child.status,
      stdout_preview: String(child.stdout || '').slice(0, 500),
      stderr_preview: String(child.stderr || '').slice(0, 500),
    });
  }
  const payload = {
    schema_version: 'scbe_aethermoore_cli_selftest_v1',
    ok: results.every((row) => row.ok),
    results,
  };
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  process.exit(payload.ok ? 0 : 1);
}

const argv = process.argv.slice(2);
if (argv.length === 0 || argv[0] === '--help' || argv[0] === '-h' || argv[0] === 'help') {
  process.stdout.write(CLI_HELP);
  process.exit(0);
}

if (argv[0] === 'demo' || argv[0] === 'magic') {
  runMagicDemo(argv.slice(1));
}

if (argv[0] === 'version') {
  runVersion(argv.slice(1));
}

if (argv[0] === 'doctor') {
  runDoctor(argv.slice(1));
}

if (argv[0] === 'credits' || argv[0] === 'hosted-run') {
  const asJson = argv.includes('--json');
  if (asJson) {
    process.stdout.write(`${JSON.stringify(SERVICE_CREDITS, null, 2)}\n`);
  } else {
    process.stdout.write(
      [
        'SCBE Service Credits',
        '',
        SERVICE_CREDITS.policy,
        `Fee: ${SERVICE_CREDITS.fee}`,
        '',
        `Hosted run intake: ${SERVICE_CREDITS.hosted_run_intake}`,
        `Service credits:    ${SERVICE_CREDITS.service_credits}`,
        `Top up:             ${SERVICE_CREDITS.top_up}`,
        '',
      ].join('\n')
    );
  }
  process.exit(0);
}

if (argv[0] === 'selftest') {
  runSelftest();
}

if (argv[0] === 'status') {
  runStatus();
  process.exit(0);
}

if (argv[0] === 'liboqs') {
  runLiboqs(argv.slice(1));
}

if (argv[0] === 'history') {
  const limitIndex = argv.indexOf('--limit');
  const limit = limitIndex >= 0 ? Number(argv[limitIndex + 1] || 20) : 20;
  printHistory(Number.isFinite(limit) ? limit : 20);
  process.exit(0);
}

if (argv[0] === 'run') {
  const { command, json, quiet, capture } = parseRunArgs(argv.slice(1));
  if (!command) {
    process.stderr.write('Usage: scbe run "npm test"\n');
    process.exit(2);
  }
  const row = runShellCommand(command, { json, quiet, capture });
  if (json) process.stdout.write(`${JSON.stringify(row, null, 2)}\n`);
  process.exit(row.exit_code);
}

if (argv[0] === 'shell') {
  runInteractiveShell({
    minimal: argv.includes('--minimal'),
    ai: argv.includes('--ai'),
    tui: argv.includes('--tui'),
    agentJson: argv.includes('--agent-json'),
  });
  return;
}

if (argv[0] === 'flow') {
  runFlow(argv.slice(1));
}

if (argv[0] === 'workspace') {
  runAgentBus(['workspace', ...argv.slice(1)]);
}

if (argv[0] === 'agent-bus' || argv[0] === 'agentbus') {
  runAgentBus(argv.slice(1));
}

if (argv[0] === 'upgrade') {
  runUpgrade(argv.slice(1));
}

if (argv[0] === 'abacus') {
  runAbacus(argv.slice(1));
}

if (argv[0] === 'contract') {
  runContract(argv.slice(1));
}

if (argv[0] === 'trap-redirect') {
  runTrapRedirect(argv.slice(1));
}

if (argv[0] === 'trap-dispatch') {
  runTrapDispatch(argv.slice(1));
  // trap-dispatch offline branch already exited synchronously; ollama
  // branch keeps the event loop alive and exits from its promise callback.
  // Either way, do not fall through to the geoseal passthrough below.
  return;
}

if (argv[0] === 'compile-ca' || argv[0] === 'ca-plan' || argv[0] === 'render-op') {
  runCompiler(argv);
}

if (argv[0] === 'compile') {
  const [, mode, ...rest] = argv;
  if (!mode || mode === '--help' || mode === '-h') {
    process.stdout.write(
      [
        'Usage:',
        '  scbe compile ca --opcodes "0x09 0x09 0x00" --target python --fn score --args a,b',
        '  scbe compile plan --ops "abs abs add" --json',
        '  scbe compile op --op add --target KO --a left --b right',
        '',
      ].join('\n')
    );
    process.exit(0);
  }
  const compilerMode = {
    ca: 'compile-ca',
    'compile-ca': 'compile-ca',
    plan: 'ca-plan',
    'ca-plan': 'ca-plan',
    op: 'render-op',
    'render-op': 'render-op',
    manifest: 'manifest',
    generate: 'generate',
    apply: 'apply',
  }[mode];
  if (!compilerMode) {
    process.stderr.write(`unknown compile mode ${mode}\n`);
    process.exit(2);
  }
  runCompiler([compilerMode, ...rest]);
}

if (argv[0] === 'route' || argv[0] === 'aetherpp') {
  runRouteCompiler(argv[0] === 'route' ? argv.slice(1) : argv.slice(1));
}

// Natural language resolver: triggered when input doesn't match any known command
// and looks like a phrase or uses unknown words.
if (!KNOWN_COMMANDS.includes(argv[0]) && argv[0] && !argv[0].startsWith('--')) {
  const nlFlags = {
    json: argv.includes('--json'),
    yes: argv.includes('--yes') || argv.includes('-y'),
  };
  const rawInput = argv.filter((a) => !a.startsWith('--') && a !== '-y').join(' ');
  const result = resolveNaturalLanguage(rawInput);
  if (result.confidence >= 0.3) {
    runNaturalLanguage(rawInput, nlFlags);
    // runNaturalLanguage always exits; safety backstop in case it somehow returns
    process.exit(0);
  }
  // confidence < 0.3: fall through to typo guard and geoseal passthrough
}

// Typo guard: if argv[0] looks like a near-miss of a known scbe command,
// suggest the corrected form and exit. We don't auto-execute the suggestion —
// running a different command than the user typed is the classic
// typo-amplification trap. Unknown-but-not-close inputs fall through to the
// geoseal passthrough below, which has its own command set.
{
  const suggestion = suggestCommand(argv[0]);
  if (suggestion) {
    process.stderr.write(
      `scbe: '${argv[0]}' is not a scbe command. Did you mean 'scbe ${suggestion}'?\n` +
        `      Run 'scbe help' for the full command list.\n`
    );
    process.exit(2);
  }
}

const target = resolveGeosealBin();
const child = spawnSync(process.execPath, [target, ...argv], {
  stdio: 'inherit',
});

if (typeof child.status === 'number') {
  process.exit(child.status);
}

process.exit(1);
