#!/usr/bin/env node
"use strict";

const { spawnSync } = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const readline = require("node:readline");

const SERVICE_CREDITS = {
  schema_version: "scbe_service_credits_v1",
  name: "SCBE Service Credits",
  policy:
    "Free/local/Ollama-first by default; credits only apply to hosted capacity, report delivery, storage, and provider/model usage.",
  fee: "actual provider/model cost + 2-5% SCBE coordination fee",
  hosted_run_intake: "https://aethermoore.com/SCBE-AETHERMOORE/hosted-run.html",
  service_credits: "https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html",
  top_up: "https://ko-fi.com/izdandavis",
};

const CLI_HELP = `scbe-aethermoore-cli

Usage:
  scbe <command> [options]

Core commands:
  scbe version
  scbe demo
  scbe demo --json
  scbe selftest
  scbe doctor --json
  scbe credits
  scbe upgrade
  scbe shell
  scbe run "npm test"
  scbe status
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

Governance abacus (deterministic BigInt-only L12+L13 scoring — no float drift):
  scbe abacus run --d-h 0.4 --pd 0.1
  scbe abacus run --d-h 0.4 --pd 0.1 --json

Compiler and routing commands, available from a source checkout:
  scbe compile-ca --opcodes "0x09 0x09 0x00" --target python
  scbe ca-plan --ops "abs abs add" --json
  scbe render-op --op add --target KO --a left --b right
  scbe compile ca --opcodes "0x09 0x09 0x00" --target typescript
  scbe route --program 'encode "run tests" in tongue KO'

Hosted run path:
  scbe credits      Print service-credit policy and hosted-run links.
  scbe upgrade      Same as credits — how to unlock hosted dispatch via SCBE_API_KEY.

Local routing is free. Hosted runs require credits (see 'scbe upgrade').
Unknown commands are forwarded to the GeoSeal shell from scbe-aethermoore.
`;

function resolveGeosealBin() {
  try {
    const entry = require.resolve("scbe-aethermoore");
    return path.resolve(path.dirname(entry), "..", "..", "bin", "geoseal.cjs");
  } catch (_err) {
    const localFallback = path.resolve(__dirname, "..", "..", "..", "bin", "geoseal.cjs");
    try {
      require("node:fs").accessSync(localFallback);
      return localFallback;
    } catch (_fallbackErr) {
      process.stderr.write(
        "scbe-aethermoore-cli could not find scbe-aethermoore. Reinstall with: npm i -g scbe-aethermoore-cli\n",
      );
      process.exit(1);
    }
  }
}

function repoRoot() {
  return path.resolve(__dirname, "..", "..", "..");
}

function resolveRepoScript(relativePath) {
  const target = path.resolve(repoRoot(), relativePath);
  if (fs.existsSync(target)) return target;
  return null;
}

function pythonCommand() {
  return process.env.SCBE_PYTHON || process.env.PYTHON || "python";
}

function nowIso() {
  return new Date().toISOString();
}

function timezone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "unknown";
}

function historyPath() {
  return path.resolve(repoRoot(), "artifacts", "scbe-terminal", "history.jsonl");
}

function appendHistory(row) {
  const target = historyPath();
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.appendFileSync(target, `${JSON.stringify(row)}\n`, "utf8");
}

function inferCompass(command) {
  const lower = command.toLowerCase();
  const first = lower.trim().split(/\s+/)[0] || "";
  let lane = "shell";
  let language = "unknown";
  let intent = "execute";
  if (["npm", "pnpm", "yarn", "node", "npx"].includes(first)) {
    lane = "node";
    language = "javascript/typescript";
  } else if (["python", "py", "pytest", "pip"].includes(first)) {
    lane = "python";
    language = "python";
  } else if (["cargo", "rustc"].includes(first)) {
    lane = "rust";
    language = "rust";
  } else if (["go", "gofmt"].includes(first)) {
    lane = "go";
    language = "go";
  } else if (["git", "gh"].includes(first)) {
    lane = "git";
    language = "repository";
  } else if (["vercel", "netlify", "firebase", "docker"].includes(first)) {
    lane = "deploy";
    language = "ops";
  }
  if (/\b(test|pytest|vitest|jest|check|verify)\b/.test(lower)) intent = "verify";
  if (/\b(build|compile|tsc|cargo build)\b/.test(lower)) intent = "build";
  if (/\b(deploy|publish|release|vercel|netlify|firebase)\b/.test(lower)) intent = "deploy";
  if (/\b(lint|format|black|ruff|prettier)\b/.test(lower)) intent = "hygiene";
  return { lane, language, intent };
}

function gateCommand(command) {
  const code = [
    "import json, sys",
    "from src.crypto.geoseal_execution_gate import scan_command",
    "print(json.dumps(scan_command(sys.argv[1]).to_dict()))",
  ].join("; ");
  const child = spawnSync(pythonCommand(), ["-c", code, command], {
    cwd: repoRoot(),
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  if (child.status !== 0) {
    return {
      allowed: true,
      tier: "WARN",
      parser_ok: false,
      findings: ["GeoSeal execution gate unavailable; command allowed with warning"],
      stderr_preview: String(child.stderr || "").slice(0, 500),
    };
  }
  try {
    return JSON.parse(String(child.stdout || "{}"));
  } catch (_err) {
    return {
      allowed: true,
      tier: "WARN",
      parser_ok: false,
      findings: ["GeoSeal execution gate returned non-JSON; command allowed with warning"],
      stdout_preview: String(child.stdout || "").slice(0, 500),
    };
  }
}

function normalizeFindings(gate) {
  const findings = Array.isArray(gate.findings) ? gate.findings : [];
  return findings.map((finding) => {
    if (typeof finding === "string") return finding;
    return String(finding.rule || finding.message || "geoseal.finding");
  });
}

function reasonCodesForGate(gate) {
  const findings = Array.isArray(gate.findings) ? gate.findings : [];
  const reasons = findings.map((finding) => {
    const rule = typeof finding === "string" ? finding : finding.rule || "unknown";
    return `geoseal.execution_gate.${String(rule).replace(/[^A-Za-z0-9_.-]/g, "_")}`;
  });
  if (!gate.parser_ok) reasons.push("geoseal.execution_gate.parser_unavailable");
  return reasons.length ? reasons : ["geoseal.execution_gate.no_findings"];
}

function suggestedCorrectionForGate(gate) {
  const tier = String(gate.tier || "ALLOW").toUpperCase();
  if (tier === "DENY") {
    return "Do not execute the requested tool call. Ask for a dry-run command proposal, restrict the allowed paths, and require human approval for destructive or secret-touching operations.";
  }
  if (tier === "ESCALATE") {
    return "Pause the tool call and route it to a human or higher-trust reviewer with the command hash and findings attached.";
  }
  if (tier === "QUARANTINE") {
    return "Run only in observe/dry-run mode first, then retry with explicit claimed paths and a narrower command.";
  }
  return "Allowed. Keep the audit record with the downstream agent response.";
}

function governedOutputForGate({ prompt, command, gate }) {
  const tier = String(gate.tier || "ALLOW").toUpperCase();
  const decision = tier === "ALLOW" ? "ALLOW" : tier;
  const commandHash = gate.command_sha256 || crypto.createHash("sha256").update(command).digest("hex");
  const sealMaterial = JSON.stringify({
    schema_version: "scbe_governed_output_demo_v1",
    prompt,
    command_sha256: commandHash,
    decision,
    tier,
    reasons: reasonCodesForGate(gate),
  });
  const auditHash = crypto.createHash("sha256").update(sealMaterial).digest("hex");
  const blocked = decision !== "ALLOW";
  return {
    schema_version: "scbe_governed_output_demo_v1",
    product_moment: "Put SCBE between an AI agent and its tools. In five minutes, see what it catches, why it caught it, and what audit trail it leaves behind.",
    input: {
      role: "ai_agent",
      prompt,
      proposed_tool_call: command,
    },
    output: blocked
      ? "Blocked unsafe tool execution request before it reached the shell."
      : "Allowed tool execution request with audit metadata.",
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
    next_step: "Try: scbe run \"node --version\" --json",
  };
}

function parseDemoArgs(args) {
  const out = {
    json: args.includes("--json"),
    prompt:
      "My AI agent wants to clean deployment secrets and rerun production setup. Should it execute the shell command?",
    command: 'Remove-Item -Recurse -Force "config/connector_oauth/.env.connector.oauth"',
  };
  const commandIndex = args.indexOf("--command");
  if (commandIndex >= 0 && args[commandIndex + 1]) out.command = args[commandIndex + 1];
  const promptIndex = args.indexOf("--prompt");
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
        "SCBE 5-minute agent safety demo",
        "",
        packet.product_moment,
        "",
        `Input:    ${packet.input.prompt}`,
        `Tool:     ${packet.input.proposed_tool_call}`,
        `Decision: ${packet.decision}`,
        `Output:   ${packet.output}`,
        "",
        "Reasons:",
        ...packet.reasons.map((reason) => `- ${reason}`),
        "",
        `Fix:      ${packet.suggested_correction}`,
        `Audit:    ${packet.geoseal.audit_id}`,
        "",
        packet.next_step,
        "",
      ].join("\n"),
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
    schema_version: "scbe_terminal_run_v1",
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
      kind: "governance_block",
      summary: `GeoSeal blocked command at tier ${gate.tier}`,
      next_step: "Inspect governance.findings and rerun with a narrower command.",
    };
    appendHistory(row);
    if (!options.json) {
      process.stderr.write(`SCBE BLOCKED: GeoSeal ${gate.tier}\n`);
      for (const finding of gate.findings || []) process.stderr.write(`- ${finding}\n`);
    }
    return row;
  }

  if (!options.quiet && !options.json) {
    process.stdout.write(`SCBE ${compass.intent}/${compass.lane} | GeoSeal ${gate.tier} | ${startedAt}\n`);
  }
  const child = spawnSync(command, {
    cwd,
    shell: true,
    stdio: options.capture ? ["ignore", "pipe", "pipe"] : "inherit",
    encoding: "utf8",
  });
  row.exit_code = typeof child.status === "number" ? child.status : 1;
  row.duration_ms = Date.now() - start;
  row.success = row.exit_code === 0;
  if (options.capture) {
    row.stdout_preview = String(child.stdout || "").slice(-2000);
    row.stderr_preview = String(child.stderr || "").slice(-2000);
  }
  if (!row.success) {
    row.failure = classifyFailure(command, row, child);
  }
  appendHistory(row);
  return row;
}

function classifyFailure(command, row, child) {
  const text = `${child?.stderr || ""}\n${child?.stdout || ""}`.toLowerCase();
  if (text.includes("module not found") || text.includes("cannot find module")) {
    return {
      kind: "missing_dependency",
      summary: "A module or package was not found.",
      next_step: "Run the project install command, then retry the same command.",
    };
  }
  if (text.includes("command not found") || text.includes("not recognized")) {
    return {
      kind: "missing_tool",
      summary: "The shell could not find the requested executable.",
      next_step: "Check PATH or install the missing CLI locally in this project.",
    };
  }
  if (/\bsyntaxerror\b|parse error|unexpected token/.test(text)) {
    return {
      kind: "syntax",
      summary: "The tool reported a parse or syntax error.",
      next_step: "Open the reported file/line, fix syntax, and rerun verification.",
    };
  }
  if (/\btest failed\b|failed\b|assert/.test(text)) {
    return {
      kind: "test_failure",
      summary: "A verification command failed.",
      next_step: "Inspect the first failing test or assertion, patch behavior, then rerun.",
    };
  }
  return {
    kind: "command_failed",
    summary: `Command exited ${row.exit_code}.`,
    next_step: "Rerun with --json or inspect the command output for the first concrete error.",
  };
}

function parseRunArgs(args) {
  const json = args.includes("--json");
  const quiet = args.includes("--quiet");
  const capture = json || args.includes("--capture");
  const filtered = args.filter((arg) => !["--json", "--quiet", "--capture"].includes(arg));
  return { command: filtered.join(" "), json, quiet, capture };
}

function printHistory(limit = 20) {
  const target = historyPath();
  if (!fs.existsSync(target)) {
    process.stdout.write("No SCBE terminal history yet.\n");
    return;
  }
  const rows = fs
    .readFileSync(target, "utf8")
    .trim()
    .split(/\r?\n/)
    .filter(Boolean)
    .slice(-limit)
    .map((line) => JSON.parse(line));
  for (const row of rows) {
    const mark = row.success ? "PASS" : "FAIL";
    process.stdout.write(
      `${row.started_at} ${mark} ${row.compass.intent}/${row.compass.lane} ${row.exit_code} ${row.command}\n`,
    );
  }
}

function runStatus() {
  const payload = {
    schema_version: "scbe_terminal_status_v1",
    cwd: process.cwd(),
    repo_root: repoRoot(),
    history_path: historyPath(),
    timezone: timezone(),
    compiler_available: Boolean(resolveRepoScript("scripts/agents/scbe_code.py")),
    router_available: Boolean(resolveRepoScript("scripts/aetherpp/cli.py")),
    geoseal_available: Boolean(resolveGeosealBin()),
  };
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
}

function runInteractiveShell() {
  process.stdout.write("SCBE Terminal. Type commands normally. Use :help or :exit.\n");
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: "scbe> ",
  });
  rl.prompt();
  rl.on("line", (line) => {
    const command = line.trim();
    if (!command) {
      rl.prompt();
      return;
    }
    if (command === ":exit" || command === "exit" || command === "quit") {
      rl.close();
      return;
    }
    if (command === ":help" || command === "help") {
      process.stdout.write(CLI_HELP);
      rl.prompt();
      return;
    }
    if (command === ":status" || command === "status") {
      runStatus();
      rl.prompt();
      return;
    }
    if (command.startsWith(":history") || command === "history") {
      printHistory(20);
      rl.prompt();
      return;
    }
    const scbeCommand = /^(compile|compile-ca|ca-plan|render-op|route|aetherpp)\b/.test(command)
      ? `${process.execPath} "${__filename}" ${command}`
      : command;
    const row = runShellCommand(scbeCommand);
    if (!row.success && row.failure) {
      process.stdout.write(`SCBE failure: ${row.failure.summary}\nNext: ${row.failure.next_step}\n`);
    }
    rl.prompt();
  });
}

function runPythonScript(relativePath, args) {
  const script = resolveRepoScript(relativePath);
  if (!script) {
    process.stderr.write(
      [
        `scbe could not find ${relativePath}.`,
        "This command needs a local SCBE-AETHERMOORE source checkout.",
        "Use the repo-local CLI, or install the full source package before running compiler/routing lanes.",
        "",
      ].join("\n"),
    );
    process.exit(2);
  }
  const child = spawnSync(pythonCommand(), [script, ...args], {
    stdio: "inherit",
  });
  if (typeof child.status === "number") process.exit(child.status);
  process.exit(1);
}

function runCompiler(args) {
  runPythonScript("scripts/agents/scbe_code.py", args);
}

function runRouteCompiler(args) {
  runPythonScript("scripts/aetherpp/cli.py", args);
}

function runFlow(args) {
  // Bridge to scripts/scbe-system-cli.py flow <sub> — same source-checkout pattern as compile/route.
  runPythonScript("scripts/scbe-system-cli.py", ["flow", ...args]);
}

// Top-level commands scbe handles directly. Used by the typo-suggestion guard.
// Order doesn't matter; this list is the complete set of scbe-owned verbs.
const KNOWN_COMMANDS = [
  "help",
  "version",
  "demo",
  "magic",
  "selftest",
  "doctor",
  "credits",
  "hosted-run",
  "upgrade",
  "shell",
  "run",
  "status",
  "history",
  "flow",
  "agent-bus",
  "agentbus",
  "abacus",
  "compile-ca",
  "ca-plan",
  "render-op",
  "compile",
  "route",
  "aetherpp",
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

function resolveHarmonicModule() {
  try {
    return require("scbe-aethermoore/harmonic");
  } catch (_err) {
    const local = path.resolve(repoRoot(), "dist", "src", "harmonic", "index.js");
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
  const sub = args[0] || "help";
  if (sub === "help" || sub === "--help" || sub === "-h") {
    process.stdout.write(
      [
        "Usage:",
        "  scbe abacus run --d-h <value> --pd <value> [--json]",
        "",
        "Deterministic BigInt mechanical scoring for L12 harmonic wall + L13 tier.",
        "Same inputs produce bit-identical scores and tiers on every platform.",
        "",
        "Formula:  H(d_h, pd) = 1 / (1 + d_h + 2*pd)",
        "Tiers:    H >= 0.65 ALLOW; >= 0.45 QUARANTINE; >= 0.25 ESCALATE; else DENY",
        "Trit:     +1 ALLOW, 0 uncertain (QUARANTINE/ESCALATE), -1 DENY",
        "",
      ].join("\n"),
    );
    process.exit(0);
  }
  if (sub !== "run") {
    process.stderr.write(`unknown abacus subcommand: ${sub}\n`);
    process.exit(2);
  }
  const d_h = parseAbacusFlag(args, "--d-h");
  const phase_dev = parseAbacusFlag(args, "--pd");
  if (d_h === null || phase_dev === null) {
    process.stderr.write("scbe abacus run requires --d-h <value> --pd <value>\n");
    process.exit(2);
  }
  const harmonic = resolveHarmonicModule();
  if (!harmonic || typeof harmonic.runGovernanceAbacus !== "function") {
    process.stderr.write(
      "scbe abacus requires scbe-aethermoore (>=4.1) with the governanceAbacus export.\n" +
        "Install with: npm i -g scbe-aethermoore\n",
    );
    process.exit(2);
  }
  const run = harmonic.runGovernanceAbacus({ d_h, phase_dev });
  const asJson = args.includes("--json");
  if (asJson) {
    const payload = {
      schema_version: "scbe_governance_abacus_v1",
      input: run.input,
      config: { scale: run.config.scale.toString() },
      beads: {
        d_h: { position: run.beads.d_h.position.toString(), display: run.beads.d_h.display },
        phase_dev: { position: run.beads.phase_dev.position.toString(), display: run.beads.phase_dev.display },
        denominator: { position: run.beads.denominator.position.toString(), display: run.beads.denominator.display },
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
  try {
    const entry = require.resolve("scbe-agent-bus/package.json");
    return path.resolve(path.dirname(entry), "bin", "scbe-agent-bus.cjs");
  } catch (_err) {
    const localFallback = path.resolve(__dirname, "..", "..", "agent-bus", "bin", "scbe-agent-bus.cjs");
    try {
      fs.accessSync(localFallback);
      return localFallback;
    } catch (_fallbackErr) {
      return null;
    }
  }
}

function runAgentBus(args) {
  const target = resolveAgentBusBin();
  if (!target) {
    process.stderr.write(
      "scbe agent-bus requires scbe-agent-bus. Install with: npm i -g scbe-agent-bus\n",
    );
    process.exit(2);
  }
  const child = spawnSync(process.execPath, [target, ...args], { stdio: "inherit" });
  if (typeof child.status === "number") process.exit(child.status);
  process.exit(1);
}

function runUpgrade(args) {
  // Aliased to credits semantically; if scbe-agent-bus is installed, defer to its upgrade
  // command so the single source of truth for hosted-run guidance lives in one place.
  const target = resolveAgentBusBin();
  if (target) {
    const child = spawnSync(process.execPath, [target, "upgrade", ...args], { stdio: "inherit" });
    if (typeof child.status === "number") process.exit(child.status);
    process.exit(0);
  }
  // Fallback: print the same payload as `scbe credits` so the upgrade command always works.
  const asJson = args.includes("--json");
  if (asJson) {
    process.stdout.write(`${JSON.stringify(SERVICE_CREDITS, null, 2)}\n`);
  } else {
    process.stdout.write(
      [
        "SCBE Service Credits — hosted runs",
        "",
        SERVICE_CREDITS.policy,
        `Fee: ${SERVICE_CREDITS.fee}`,
        "",
        `Hosted run intake: ${SERVICE_CREDITS.hosted_run_intake}`,
        `Service credits:    ${SERVICE_CREDITS.service_credits}`,
        `Top up:             ${SERVICE_CREDITS.top_up}`,
        "",
        "Install scbe-agent-bus for the full upgrade flow: npm i -g scbe-agent-bus",
        "",
      ].join("\n"),
    );
  }
  process.exit(0);
}

function runSelftest() {
  const target = resolveGeosealBin();
  const checks = [
    ["version"],
    ["doctor", "--json"],
  ];
  const results = checks.map((args) => {
    const child = spawnSync(process.execPath, [target, ...args], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
    return {
      command: `scbe ${args.join(" ")}`,
      ok: child.status === 0,
      status: child.status,
      stdout_preview: String(child.stdout || "").slice(0, 500),
      stderr_preview: String(child.stderr || "").slice(0, 500),
    };
  });
  const compilerScript = resolveRepoScript("scripts/agents/scbe_code.py");
  if (compilerScript) {
    const child = spawnSync(
      pythonCommand(),
      [compilerScript, "ca-plan", "--ops", "abs abs add", "--json"],
      {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
    results.push({
      command: "scbe ca-plan --ops \"abs abs add\" --json",
      ok: child.status === 0,
      status: child.status,
      stdout_preview: String(child.stdout || "").slice(0, 500),
      stderr_preview: String(child.stderr || "").slice(0, 500),
    });
  }
  const payload = {
    schema_version: "scbe_aethermoore_cli_selftest_v1",
    ok: results.every((row) => row.ok),
    results,
  };
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  process.exit(payload.ok ? 0 : 1);
}

const argv = process.argv.slice(2);
if (argv.length === 0 || argv[0] === "--help" || argv[0] === "-h" || argv[0] === "help") {
  process.stdout.write(CLI_HELP);
  process.exit(0);
}

if (argv[0] === "demo" || argv[0] === "magic") {
  runMagicDemo(argv.slice(1));
}

if (argv[0] === "credits" || argv[0] === "hosted-run") {
  const asJson = argv.includes("--json");
  if (asJson) {
    process.stdout.write(`${JSON.stringify(SERVICE_CREDITS, null, 2)}\n`);
  } else {
    process.stdout.write(
      [
        "SCBE Service Credits",
        "",
        SERVICE_CREDITS.policy,
        `Fee: ${SERVICE_CREDITS.fee}`,
        "",
        `Hosted run intake: ${SERVICE_CREDITS.hosted_run_intake}`,
        `Service credits:    ${SERVICE_CREDITS.service_credits}`,
        `Top up:             ${SERVICE_CREDITS.top_up}`,
        "",
      ].join("\n"),
    );
  }
  process.exit(0);
}

if (argv[0] === "selftest") {
  runSelftest();
}

if (argv[0] === "status") {
  runStatus();
  process.exit(0);
}

if (argv[0] === "history") {
  const limitIndex = argv.indexOf("--limit");
  const limit = limitIndex >= 0 ? Number(argv[limitIndex + 1] || 20) : 20;
  printHistory(Number.isFinite(limit) ? limit : 20);
  process.exit(0);
}

if (argv[0] === "run") {
  const { command, json, quiet, capture } = parseRunArgs(argv.slice(1));
  if (!command) {
    process.stderr.write('Usage: scbe run "npm test"\n');
    process.exit(2);
  }
  const row = runShellCommand(command, { json, quiet, capture });
  if (json) process.stdout.write(`${JSON.stringify(row, null, 2)}\n`);
  process.exit(row.exit_code);
}

if (argv[0] === "shell") {
  runInteractiveShell();
  return;
}

if (argv[0] === "flow") {
  runFlow(argv.slice(1));
}

if (argv[0] === "agent-bus" || argv[0] === "agentbus") {
  runAgentBus(argv.slice(1));
}

if (argv[0] === "upgrade") {
  runUpgrade(argv.slice(1));
}

if (argv[0] === "abacus") {
  runAbacus(argv.slice(1));
}

if (argv[0] === "compile-ca" || argv[0] === "ca-plan" || argv[0] === "render-op") {
  runCompiler(argv);
}

if (argv[0] === "compile") {
  const [, mode, ...rest] = argv;
  if (!mode || mode === "--help" || mode === "-h") {
    process.stdout.write(
      [
        "Usage:",
        "  scbe compile ca --opcodes \"0x09 0x09 0x00\" --target python",
        "  scbe compile plan --ops \"abs abs add\" --json",
        "  scbe compile op --op add --target KO --a left --b right",
        "",
      ].join("\n"),
    );
    process.exit(0);
  }
  const compilerMode = {
    ca: "compile-ca",
    "compile-ca": "compile-ca",
    plan: "ca-plan",
    "ca-plan": "ca-plan",
    op: "render-op",
    "render-op": "render-op",
    manifest: "manifest",
    generate: "generate",
    apply: "apply",
  }[mode];
  if (!compilerMode) {
    process.stderr.write(`unknown compile mode ${mode}\n`);
    process.exit(2);
  }
  runCompiler([compilerMode, ...rest]);
}

if (argv[0] === "route" || argv[0] === "aetherpp") {
  runRouteCompiler(argv[0] === "route" ? argv.slice(1) : argv.slice(1));
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
        `      Run 'scbe help' for the full command list.\n`,
    );
    process.exit(2);
  }
}

const target = resolveGeosealBin();
const child = spawnSync(process.execPath, [target, ...argv], {
  stdio: "inherit",
});

if (typeof child.status === "number") {
  process.exit(child.status);
}

process.exit(1);
