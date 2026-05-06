#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { spawnSync } = require("child_process");
const readline = require("readline");

const ROOT = path.resolve(__dirname, "..");
const PACKAGE_JSON_PATH = path.join(ROOT, "package.json");
const PACKAGE_JSON = JSON.parse(fs.readFileSync(PACKAGE_JSON_PATH, "utf8"));

const COMMAND_HELP = `GeoSeal Shell

Usage:
  geoseal <command> [options]

Modes:
  1. API shell
     Set --api-base or SCBE_API_BASE to route commands to a running GeoSeal API.

  2. Python passthrough
     Without --api-base, geoseal falls through to:
       python -m geoseal_cli
     Use SCBE_GEOSEAL_PYTHON to pin the Python executable.

Useful commands:
  geoseal tools --json
  geoseal math "sqrt(2)^2 + phi" --json
  geoseal units "kg*m/s^2" --json
  geoseal search "site:docs.python.org pathlib" --json
  geoseal fetch https://example.com --json
  geoseal materials --element W --limit 5 --json
  geoseal nomad --formula TiNi --limit 5 --json
  geoseal code-languages --json
  geoseal code-ir --source-file src/index.ts --language typescript --json
  geoseal injection-plan --source-file src/index.ts --interval lines:40 --tongues KO,AV --json
  geoseal code-verify --source-file src/index.ts --probe --json
  geoseal code-translate --source-file src/index.ts --target-language python --json
  geoseal ui

Advanced / full-surface commands:
  geoseal doctor --json
  geoseal permissions --json
  geoseal custom-commands --json
  geoseal run-command harness-benchmark --json
  geoseal status --api-base http://127.0.0.1:8002
  geoseal shell --command "portal-box --content \"def add(a, b): return a + b\" --language python --source-name sample.python --json"
  geoseal portal-box --api-base http://127.0.0.1:8002 --language python --content "def add(a, b): return a + b"
  geoseal stream-wheel --api-base http://127.0.0.1:8002 --language python --content "def add(a, b): return a + b"
  geoseal inspect --api-base http://127.0.0.1:8002 --api-key <key> --language python --content "def add(a, b): return a + b"
  geoseal run-route --api-base http://127.0.0.1:8002 --api-key <key> --language python --content "def add(a, b): return a + b"
  geoseal service --detach --allow-demo-keys --probe-health --json
  geoseal service-status --probe-health --allow-demo-keys --json
  geoseal service-stop --json
  geoseal nexus-status --api-base http://127.0.0.1:8002 --api-key <key> --hub-url https://hub.hoagsinc.com
  geoseal nexus-connect --api-base http://127.0.0.1:8002 --api-key <key> --hub-url https://hub.hoagsinc.com --token <token>
  geoseal nexus-dispatch --api-base http://127.0.0.1:8002 --api-key <key> --hub-url https://hub.hoagsinc.com --language python --content "def add(a, b): return a + b"
  geoseal cursor-status --json
  geoseal cursor-overlord --json
  geoseal fleet-distributions --json
  geoseal agent-io-contract --output-dir artifacts/agent_io_contract --json
  geoseal harness-terminal --no-health
  geoseal harness-research --json
  geoseal research-terminal
  geoseal research-sources --query arxiv --json
  geoseal polymarket --mode search --query ai --json
  geoseal github --mode status --json
  geoseal handoff-seal --sender codex --recipient claude --intent "review changed files" --secret-env SCBE_HANDOFF_SECRET --json
  geoseal handoff-open --sealed-file artifacts/agent_comm/handoff.json --secret-env SCBE_HANDOFF_SECRET --json
  geoseal tokenizer-code-lanes --command shl --tongues all --output artifacts/tokenizer_code_lanes/shl_lanes.json
  geoseal verify-code-lanes "$(cat artifacts/tokenizer_code_lanes/shl_lanes.json)" --json
  geoseal decode-code-lanes "$(cat artifacts/tokenizer_code_lanes/shl_lanes.json)" --output-dir artifacts/tokenizer_code_lanes/decoded --from-binary --write-binary --json
  geoseal code-languages --json
  geoseal code-ir --source-file scripts/example.py --language python --json
  geoseal injection-plan --source-file scripts/example.py --interval lines:25 --tongues KO,AV,RU --json
  geoseal code-verify --source-file scripts/example.py --expected-source-sha <sha256> --probe --json
  geoseal code-translate --source-file scripts/example.py --target-language typescript --json
  geoseal ai2ai-bridge --content "def add(a, b): return a + b" --language python --json
  geoseal code-packet --content "def add(a, b): return a + b" --language python
  geoseal explain-route --content "def add(a, b): return a + b" --language python --json
  geoseal backend-registry --json
  geoseal history --limit 20 --json
  geoseal replay --json
  geoseal testing-cli --source-file sample.py --language python --execute --json
  geoseal project-scaffold --content "build a pacman style web game" --language python --output-dir artifacts/pacman --json
  geoseal code-roundtrip --source hello.rs --lang rust --tongue RU --execute --json
  geoseal binary-to-tmatrix --json "01101000 01101001"
  geoseal calc --expr "sqrt(2)^2 + phi" --json
  geoseal dimensions --unit "kg*m/s^2" --json
  geoseal web-search --query "site:docs.python.org pathlib" --json
  geoseal url-fetch --url https://example.com --json
  geoseal materials --element W --limit 5 --json
  geoseal toolbox --json
  geoseal terminal-ui
  geoseal agent-bus-ui
  geoseal agent-bus-server --port 8787
  geoseal agent-bus-send --task "review changed files" --json

Flags:
  --api-base <url>       GeoSeal API base URL
  --api-key <key>        API key for authenticated /runtime/* routes
  --runtime              Force authenticated runtime path for portal-box/stream-wheel
  --json                 Print JSON when the command supports it
  --help                 Show this help
  version                Print package version
`;

const COMMAND_MAP = {
  status: { method: "GET", path: "/v1/spaceport/status", auth: false },
  chat: { method: "POST", path: "/v1/chat", auth: false },
  "portal-box": { method: "POST", path: "/v1/polly/portal-box", runtimePath: "/runtime/portal-box", auth: false, runtimeAuth: true },
  "stream-wheel": { method: "POST", path: "/v1/polly/stream-wheel", runtimePath: "/runtime/stream-wheel", auth: false, runtimeAuth: true },
  inspect: { method: "POST", path: "/runtime/inspect", auth: true },
  "system-cards": { method: "POST", path: "/runtime/system-cards", auth: true },
  "play-card": { method: "POST", path: "/runtime/play-card", auth: true },
  "run-route": { method: "POST", path: "/runtime/run-route", auth: true },
  "project-run": { method: "POST", path: "/runtime/project-run", auth: true },
  "run-history": { method: "POST", path: "/runtime/run-history", auth: true },
  "nexus-status": { method: "POST", path: "/runtime/nexus/status", auth: true },
  "nexus-connect": { method: "POST", path: "/runtime/nexus/connect", auth: true },
  "nexus-dispatch": { method: "POST", path: "/runtime/nexus/dispatch", auth: true },
  "cursor-status": { method: "POST", path: "/runtime/cursor/status", auth: true },
  "cursor-overlord": { method: "POST", path: "/runtime/cursor/overlord", auth: true },
  "fleet-distributions": { method: "POST", path: "/runtime/fleet/distributions", auth: true },
  "orchestrator-init": { method: "POST", path: "/runtime/orchestrator/init", auth: true },
  "orchestrator-dispatch": { method: "POST", path: "/runtime/orchestrator/dispatch", auth: true },
  "orchestrator-status": { method: "POST", path: "/runtime/orchestrator/status", auth: true },
  "orchestrator-promote": { method: "POST", path: "/runtime/orchestrator/promote", auth: true },
  "code-packet": { method: "POST", path: "/v1/geoseal/code-packet", auth: false },
  "explain-route": { method: "POST", path: "/v1/geoseal/explain-route", auth: false },
  "backend-registry": { method: "POST", path: "/v1/geoseal/backend-registry", auth: false },
  "agent-harness": { method: "POST", path: "/v1/geoseal/agent-harness", auth: false },
  history: { method: "POST", path: "/v1/geoseal/history", auth: false },
  replay: { method: "POST", path: "/v1/geoseal/replay", auth: false },
  "testing-cli": { method: "POST", path: "/v1/geoseal/testing-cli", auth: false },
  "project-scaffold": { method: "POST", path: "/v1/geoseal/project-scaffold", auth: false },
  "code-roundtrip": { method: "POST", path: "/v1/geoseal/code-roundtrip", auth: false },
  "binary-to-tmatrix": { method: "POST", path: "/v1/geoseal/binary-to-tmatrix", auth: false },
};

const LOCAL_PASSTHROUGH_COMMANDS = new Set(["portal-box", "stream-wheel", "shell", "binary-to-tmatrix"]);
const CUSTOM_COMMANDS_DIR = path.join(ROOT, ".geoseal", "commands");

function parseArgs(argv) {
  const positionals = [];
  const flags = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) {
      positionals.push(token);
      continue;
    }
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      flags[key] = true;
      continue;
    }
    flags[key] = next;
    i += 1;
  }
  return { positionals, flags };
}

function apiBase(flags) {
  return String(flags["api-base"] || process.env.SCBE_API_BASE || "").replace(/\/+$/, "");
}

function apiKey(flags) {
  return String(flags["api-key"] || process.env.SCBE_API_KEY || "");
}

function writeJsonOrText(flags, payload, text) {
  if (flags.json) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    process.stdout.write(text.endsWith("\n") ? text : `${text}\n`);
  }
}

function numericFlag(flags, name, fallback) {
  const raw = flags[name];
  if (raw === undefined || raw === true || raw === "") return fallback;
  const value = Number(raw);
  return Number.isFinite(value) ? value : fallback;
}

function loadConnectorEnvValue(name) {
  if (process.env[name]) return process.env[name];
  const candidates = [
    path.join(process.cwd(), "config", "connector_oauth", ".env.connector.oauth"),
    path.join(ROOT, "config", "connector_oauth", ".env.connector.oauth"),
  ];
  for (const envPath of candidates) {
    if (!fs.existsSync(envPath)) continue;
    const lines = fs.readFileSync(envPath, "utf8").split(/\r?\n/);
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
      const index = trimmed.indexOf("=");
      const key = trimmed.slice(0, index).trim();
      if (key !== name) continue;
      return trimmed.slice(index + 1).trim().replace(/^["']|["']$/g, "");
    }
  }
  return "";
}

function normalizeCommand(command) {
  const aliases = {
    tools: "toolbox",
    tool: "toolbox",
    math: "calc",
    calculate: "calc",
    unit: "dimensions",
    units: "dimensions",
    dimensional: "dimensions",
    search: "web-search",
    lookup: "web-search",
    fetch: "url-fetch",
    get: "url-fetch",
    material: "materials",
    "material-search": "materials",
    nomad: "materials",
    bus: "agent-bus-ui",
    "bus-ui": "agent-bus-ui",
    "bus-server": "agent-bus-server",
    "bus-send": "agent-bus-send",
    languages: "code-languages",
    "code-langs": "code-languages",
    "code-sync": "injection-plan",
    "sync-plan": "injection-plan",
  };
  return aliases[command] || command;
}

const LANGUAGE_REGISTRY = [
  {
    language: "python",
    extensions: [".py"],
    tongue: "KO",
    support_level: "ir_summary_and_runtime_probe",
    runner: "python",
    compile_check: "python -m py_compile <file>",
  },
  {
    language: "typescript",
    extensions: [".ts", ".tsx"],
    tongue: "AV",
    support_level: "ir_summary_and_typecheck_probe",
    runner: "node/vitest after transpile",
    compile_check: "npm run typecheck",
  },
  {
    language: "javascript",
    extensions: [".js", ".mjs", ".cjs"],
    tongue: "AV",
    support_level: "ir_summary_and_runtime_probe",
    runner: "node",
    compile_check: "node --check <file>",
  },
  {
    language: "rust",
    extensions: [".rs"],
    tongue: "RU",
    support_level: "ir_summary_only_until_cargo_probe",
    runner: "cargo",
    compile_check: "cargo check",
  },
  {
    language: "c",
    extensions: [".c", ".h"],
    tongue: "CA",
    support_level: "ir_summary_only_until_compiler_probe",
    runner: "cc",
    compile_check: "cc -fsyntax-only <file>",
  },
  {
    language: "julia",
    extensions: [".jl"],
    tongue: "UM",
    support_level: "declared_tongue_lane_ir_summary_later",
    runner: "julia",
    compile_check: "julia --compile=min <file>",
  },
  {
    language: "haskell",
    extensions: [".hs"],
    tongue: "DR",
    support_level: "declared_tongue_lane_ir_summary_later",
    runner: "ghc",
    compile_check: "ghc -fno-code <file>",
  },
];

function makeScanner(input) {
  return {
    text: String(input || ""),
    index: 0,
    peek() {
      return this.text[this.index] || "";
    },
    skipWs() {
      while (/\s/.test(this.peek())) this.index += 1;
    },
    match(value) {
      this.skipWs();
      if (this.text.slice(this.index, this.index + value.length) === value) {
        this.index += value.length;
        return true;
      }
      return false;
    },
    number() {
      this.skipWs();
      const match = /^(\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?/i.exec(this.text.slice(this.index));
      if (!match) return null;
      this.index += match[0].length;
      return Number(match[0]);
    },
    identifier() {
      this.skipWs();
      const match = /^[A-Za-z_][A-Za-z0-9_]*/.exec(this.text.slice(this.index));
      if (!match) return null;
      this.index += match[0].length;
      return match[0];
    },
  };
}

function evaluateExpression(expression) {
  const scanner = makeScanner(expression);
  const constants = {
    pi: Math.PI,
    e: Math.E,
    phi: (1 + Math.sqrt(5)) / 2,
    tau: Math.PI * 2,
  };
  const functions = {
    abs: Math.abs,
    acos: Math.acos,
    asin: Math.asin,
    atan: Math.atan,
    ceil: Math.ceil,
    cos: Math.cos,
    exp: Math.exp,
    floor: Math.floor,
    ln: Math.log,
    log: Math.log10,
    max: Math.max,
    min: Math.min,
    pow: Math.pow,
    round: Math.round,
    sin: Math.sin,
    sqrt: Math.sqrt,
    tan: Math.tan,
  };

  function parseExpression() {
    let value = parseTerm();
    while (true) {
      if (scanner.match("+")) value += parseTerm();
      else if (scanner.match("-")) value -= parseTerm();
      else return value;
    }
  }

  function parseTerm() {
    let value = parsePower();
    while (true) {
      if (scanner.match("*")) value *= parsePower();
      else if (scanner.match("/")) value /= parsePower();
      else return value;
    }
  }

  function parsePower() {
    let value = parseUnary();
    if (scanner.match("^")) {
      value = Math.pow(value, parsePower());
    }
    return value;
  }

  function parseUnary() {
    if (scanner.match("+")) return parseUnary();
    if (scanner.match("-")) return -parseUnary();
    return parsePrimary();
  }

  function parseArgs() {
    const args = [];
    if (scanner.match(")")) return args;
    while (true) {
      args.push(parseExpression());
      if (scanner.match(")")) return args;
      if (!scanner.match(",")) throw new Error("Expected ',' or ')' in function call");
    }
  }

  function parsePrimary() {
    const number = scanner.number();
    if (number !== null) return number;
    if (scanner.match("(")) {
      const value = parseExpression();
      if (!scanner.match(")")) throw new Error("Expected ')'");
      return value;
    }
    const name = scanner.identifier();
    if (name) {
      const key = name.toLowerCase();
      if (scanner.match("(")) {
        const fn = functions[key];
        if (!fn) throw new Error(`Unknown function: ${name}`);
        const args = parseArgs();
        return fn(...args);
      }
      if (Object.prototype.hasOwnProperty.call(constants, key)) return constants[key];
      throw new Error(`Unknown constant: ${name}`);
    }
    throw new Error(`Unexpected token near '${scanner.text.slice(scanner.index, scanner.index + 16)}'`);
  }

  const result = parseExpression();
  scanner.skipWs();
  if (scanner.index !== scanner.text.length) {
    throw new Error(`Unexpected trailing input near '${scanner.text.slice(scanner.index, scanner.index + 16)}'`);
  }
  if (!Number.isFinite(result)) throw new Error("Expression did not produce a finite number");
  return result;
}

const DIMENSION_LABELS = ["M", "L", "T", "I", "Theta", "N", "J"];
const UNIT_DIMENSIONS = {
  kg: [1, 0, 0, 0, 0, 0, 0],
  g: [1, 0, 0, 0, 0, 0, 0],
  m: [0, 1, 0, 0, 0, 0, 0],
  meter: [0, 1, 0, 0, 0, 0, 0],
  metre: [0, 1, 0, 0, 0, 0, 0],
  s: [0, 0, 1, 0, 0, 0, 0],
  sec: [0, 0, 1, 0, 0, 0, 0],
  A: [0, 0, 0, 1, 0, 0, 0],
  amp: [0, 0, 0, 1, 0, 0, 0],
  K: [0, 0, 0, 0, 1, 0, 0],
  mol: [0, 0, 0, 0, 0, 1, 0],
  cd: [0, 0, 0, 0, 0, 0, 1],
  N: [1, 1, -2, 0, 0, 0, 0],
  newton: [1, 1, -2, 0, 0, 0, 0],
  J: [1, 2, -2, 0, 0, 0, 0],
  joule: [1, 2, -2, 0, 0, 0, 0],
  W: [1, 2, -3, 0, 0, 0, 0],
  watt: [1, 2, -3, 0, 0, 0, 0],
  Pa: [1, -1, -2, 0, 0, 0, 0],
  pascal: [1, -1, -2, 0, 0, 0, 0],
  C: [0, 0, 1, 1, 0, 0, 0],
  V: [1, 2, -3, -1, 0, 0, 0],
  ohm: [1, 2, -3, -2, 0, 0, 0],
  Hz: [0, 0, -1, 0, 0, 0, 0],
  rad: [0, 0, 0, 0, 0, 0, 0],
  one: [0, 0, 0, 0, 0, 0, 0],
};

const QUANTITY_DIMENSIONS = {
  force: [1, 1, -2, 0, 0, 0, 0],
  energy: [1, 2, -2, 0, 0, 0, 0],
  power: [1, 2, -3, 0, 0, 0, 0],
  pressure: [1, -1, -2, 0, 0, 0, 0],
  velocity: [0, 1, -1, 0, 0, 0, 0],
  acceleration: [0, 1, -2, 0, 0, 0, 0],
  charge: [0, 0, 1, 1, 0, 0, 0],
  voltage: [1, 2, -3, -1, 0, 0, 0],
};

function addDims(left, right, scale = 1) {
  return left.map((value, index) => value + scale * right[index]);
}

function scaleDims(vector, scale) {
  return vector.map((value) => value * scale);
}

function formatDimensions(vector) {
  const parts = vector
    .map((value, index) => [DIMENSION_LABELS[index], value])
    .filter((row) => row[1] !== 0)
    .map(([label, value]) => `${label}${value === 1 ? "" : `^${value}`}`);
  return parts.length ? parts.join(" ") : "dimensionless";
}

function analyzeDimensions(unitExpression) {
  const scanner = makeScanner(unitExpression || "one");

  function parseExpression() {
    let value = parseFactor();
    while (true) {
      if (scanner.match("*")) value = addDims(value, parseFactor());
      else if (scanner.match("/")) value = addDims(value, parseFactor(), -1);
      else return value;
    }
  }

  function parseFactor() {
    let value = parsePrimary();
    if (scanner.match("^")) {
      const exponent = scanner.number();
      if (!Number.isFinite(exponent)) throw new Error("Expected numeric exponent after '^'");
      value = scaleDims(value, exponent);
    }
    return value;
  }

  function parsePrimary() {
    if (scanner.match("(")) {
      const value = parseExpression();
      if (!scanner.match(")")) throw new Error("Expected ')' in unit expression");
      return value;
    }
    const name = scanner.identifier();
    if (!name) throw new Error(`Expected unit near '${scanner.text.slice(scanner.index, scanner.index + 16)}'`);
    const vector = UNIT_DIMENSIONS[name] || UNIT_DIMENSIONS[name.toLowerCase()] || QUANTITY_DIMENSIONS[name.toLowerCase()];
    if (!vector) throw new Error(`Unknown unit or quantity: ${name}`);
    return vector;
  }

  const vector = parseExpression();
  scanner.skipWs();
  if (scanner.index !== scanner.text.length) {
    throw new Error(`Unexpected trailing unit input near '${scanner.text.slice(scanner.index, scanner.index + 16)}'`);
  }
  return vector;
}

function parseFrontmatter(text) {
  if (!text.startsWith("---\n") && !text.startsWith("---\r\n")) {
    return { metadata: {}, body: text };
  }
  const normalized = text.replace(/\r\n/g, "\n");
  const end = normalized.indexOf("\n---\n", 4);
  if (end === -1) {
    return { metadata: {}, body: text };
  }
  const metadata = {};
  const header = normalized.slice(4, end).trim();
  for (const line of header.split("\n")) {
    const match = /^([A-Za-z0-9_-]+):\s*(.*)$/.exec(line.trim());
    if (match) {
      metadata[match[1]] = match[2].replace(/^["']|["']$/g, "");
    }
  }
  return { metadata, body: normalized.slice(end + 5).trim() };
}

function loadCustomCommand(filePath) {
  const raw = fs.readFileSync(filePath, "utf8");
  const parsed = parseFrontmatter(raw);
  const fallbackName = path.basename(filePath, path.extname(filePath));
  const relativePath = path.relative(ROOT, filePath).replace(/\\/g, "/");
  const body = parsed.body.trim();
  return {
    name: String(parsed.metadata.name || fallbackName),
    description: String(parsed.metadata.description || ""),
    path: relativePath,
    execution_mode: "template_only",
    body,
    body_preview: body.slice(0, 600),
  };
}

function listCustomCommands() {
  if (!fs.existsSync(CUSTOM_COMMANDS_DIR)) return [];
  return fs
    .readdirSync(CUSTOM_COMMANDS_DIR)
    .filter((name) => name.endsWith(".md"))
    .map((name) => loadCustomCommand(path.join(CUSTOM_COMMANDS_DIR, name)))
    .sort((left, right) => left.name.localeCompare(right.name));
}

function runCustomCommands(flags) {
  const commands = listCustomCommands().map((command) => ({
    name: command.name,
    description: command.description,
    path: command.path,
    execution_mode: command.execution_mode,
  }));
  const payload = {
    schema_version: "geoseal_custom_commands_v1",
    ok: true,
    command_dir: path.relative(ROOT, CUSTOM_COMMANDS_DIR).replace(/\\/g, "/"),
    count: commands.length,
    commands,
  };
  const text = commands.length
    ? commands.map((command) => `${command.name}: ${command.description}`).join("\n")
    : "No custom commands found.";
  writeJsonOrText(flags, payload, text);
}

function runPermissions(flags) {
  const payload = {
    schema_version: "geoseal_permissions_v1",
    ok: true,
    default_profile: "local-first",
    max_tier: "repo_write",
    modes: [
      {
        name: "local_secret_review",
        provider_policy: "local_only",
        allowed_providers: ["ollama", "llamacpp", "lmstudio", "vllm"],
        requires_signal: false,
      },
      {
        name: "training_eval",
        provider_policy: "remote_allowed_with_signal",
        allowed_providers: ["nvidia", "huggingface", "deepseek", "openrouter", "openai"],
        requires_signal: true,
      },
      {
        name: "release_gate",
        provider_policy: "evidence_required",
        allowed_actions: ["test", "benchmark", "readiness", "package"],
        requires_clean_harness: true,
      },
    ],
    gates: {
      destructive_filesystem: "forbid_without_explicit_user_request",
      secrets_to_remote_models: "forbid",
      repo_write: "allow_with_tests",
      package_publish: "require_release_gate",
    },
  };
  const text = [
    `GeoSeal permissions ${payload.schema_version}`,
    `Default profile: ${payload.default_profile}`,
    `Max tier: ${payload.max_tier}`,
    `Secrets to remote models: ${payload.gates.secrets_to_remote_models}`,
  ].join("\n");
  writeJsonOrText(flags, payload, text);
}

function runCustomCommand(name, flags) {
  if (!name) {
    const payload = {
      schema_version: "geoseal_custom_command_v1",
      ok: false,
      error: "missing_custom_command",
      message: "Pass a custom command name, for example: geoseal run-command harness-benchmark --json",
    };
    writeJsonOrText(flags, payload, payload.message);
    process.exitCode = 2;
    return;
  }
  const command = listCustomCommands().find((item) => item.name === name);
  if (!command) {
    const payload = {
      schema_version: "geoseal_custom_command_v1",
      ok: false,
      error: "custom_command_not_found",
      name,
      available: listCustomCommands().map((item) => item.name),
    };
    writeJsonOrText(flags, payload, `Custom command not found: ${name}`);
    process.exitCode = 2;
    return;
  }
  const payload = {
    schema_version: "geoseal_custom_command_v1",
    ok: true,
    command,
    safety: {
      executes_shell: false,
      note: "This command surface returns a governed template packet; it does not execute shell commands.",
    },
  };
  writeJsonOrText(flags, payload, command.body);
}

function sha256Hex(text) {
  return crypto.createHash("sha256").update(String(text), "utf8").digest("hex");
}

function sha256Data(data) {
  return crypto.createHash("sha256").update(data).digest("hex");
}

function bytesToHex(text) {
  return Buffer.from(String(text), "utf8").toString("hex");
}

function parseTongues(flags) {
  const raw = String(flags.tongues || flags.tongue || "KO");
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function readSourceFromFlags(flags, positionals) {
  if (flags["source-file"]) {
    const sourcePath = path.resolve(process.cwd(), String(flags["source-file"]));
    return {
      source: fs.readFileSync(sourcePath, "utf8"),
      source_file: path.relative(ROOT, sourcePath).replace(/\\/g, "/"),
      source_path: sourcePath,
    };
  }
  const inline = flags.content || flags.command || positionals.slice(1).join(" ");
  if (inline) {
    return {
      source: String(inline),
      source_file: null,
      source_path: null,
    };
  }
  throw new Error("--source-file or --content is required");
}

function inferLanguage(flags, sourceFile) {
  if (flags.language || flags.lang) return String(flags.language || flags.lang).toLowerCase();
  const ext = sourceFile ? path.extname(sourceFile).toLowerCase() : "";
  const match = LANGUAGE_REGISTRY.find((item) => item.extensions.includes(ext));
  return match ? match.language : "text";
}

function uniqueMatches(source, regex, group = 1) {
  const values = [];
  for (const match of source.matchAll(regex)) {
    const value = String(match[group] || "").trim();
    if (value && !values.includes(value)) values.push(value);
  }
  return values;
}

function extractPythonImports(source) {
  // Per-line scan so we never bleed across newlines (the previous regex used
  // [A-Za-z0-9_.,\s]+ which captures across line breaks). Handles:
  //   from pkg.mod import a, b as c
  //   import os
  //   import json, math, sys
  //   import numpy as np
  const imports = [];
  const seen = new Set();
  const lines = String(source || "").split(/\r?\n/);
  for (const rawLine of lines) {
    const line = rawLine.replace(/#.*$/, "").trimEnd();
    const fromMatch = line.match(/^\s*from\s+([A-Za-z0-9_.]+)\s+import\b/);
    if (fromMatch) {
      const mod = fromMatch[1];
      if (!seen.has(mod)) {
        seen.add(mod);
        imports.push(mod);
      }
      continue;
    }
    const importMatch = line.match(/^\s*import\s+(.+?)\s*$/);
    if (importMatch) {
      for (const part of importMatch[1].split(",")) {
        const aliased = part.trim();
        if (!aliased) continue;
        const mod = aliased.split(/\s+as\s+/)[0].trim();
        if (mod && !seen.has(mod)) {
          seen.add(mod);
          imports.push(mod);
        }
      }
    }
  }
  return imports;
}

function summarizeCodeIr(source, language) {
  const common = {
    imports: [],
    functions: [],
    classes: [],
    types: [],
    exports: [],
  };
  if (language === "python") {
    common.imports = extractPythonImports(source);
    common.functions = uniqueMatches(source, /^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(/gm);
    common.classes = uniqueMatches(source, /^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)/gm);
    return common;
  }
  if (language === "typescript" || language === "javascript") {
    common.imports = uniqueMatches(source, /^\s*import\s+.*?\s+from\s+["']([^"']+)["']/gm)
      .concat(uniqueMatches(source, /^\s*const\s+.*?=\s*require\(["']([^"']+)["']\)/gm))
      .filter((value, index, array) => array.indexOf(value) === index);
    common.functions = uniqueMatches(source, /^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(/gm)
      .concat(uniqueMatches(source, /^\s*(?:export\s+)?const\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s*)?\(/gm))
      .filter((value, index, array) => array.indexOf(value) === index);
    common.classes = uniqueMatches(source, /^\s*(?:export\s+)?class\s+([A-Za-z_$][A-Za-z0-9_$]*)/gm);
    common.types = uniqueMatches(source, /^\s*(?:export\s+)?(?:type|interface)\s+([A-Za-z_$][A-Za-z0-9_$]*)/gm);
    common.exports = uniqueMatches(source, /^\s*export\s+(?:default\s+)?(?:class|function|const|type|interface)\s+([A-Za-z_$][A-Za-z0-9_$]*)/gm);
    return common;
  }
  if (language === "rust") {
    common.imports = uniqueMatches(source, /^\s*use\s+([^;]+);/gm);
    common.functions = uniqueMatches(source, /^\s*(?:pub\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(/gm);
    common.classes = uniqueMatches(source, /^\s*(?:pub\s+)?(?:struct|enum|trait)\s+([A-Za-z_][A-Za-z0-9_]*)/gm);
    common.types = uniqueMatches(source, /^\s*(?:pub\s+)?(?:struct|enum|trait|type)\s+([A-Za-z_][A-Za-z0-9_]*)/gm);
    return common;
  }
  if (language === "c") {
    common.imports = uniqueMatches(source, /^\s*#include\s+[<"]([^>"]+)[>"]/gm);
    common.functions = uniqueMatches(source, /^\s*[A-Za-z_][A-Za-z0-9_\s*]*\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\s*\{/gm);
    common.types = uniqueMatches(source, /^\s*typedef\s+.*?\s+([A-Za-z_][A-Za-z0-9_]*)\s*;/gm);
    return common;
  }
  return common;
}

function runCodeLanguages(flags) {
  const payload = {
    schema_version: "geoseal_code_languages_v1",
    ok: true,
    bijection_scope: {
      transport: "byte_hex_binary_tongue_lanes_are_exact_when_hashes_round_trip",
      semantics: "cross_language_generation_requires_ir_and_compile_or_behavior_verification",
    },
    languages: LANGUAGE_REGISTRY,
  };
  writeJsonOrText(flags, payload, LANGUAGE_REGISTRY.map((item) => `${item.language}: ${item.support_level}`).join("\n"));
}

function runCodeIr(flags, positionals) {
  const sourceInfo = readSourceFromFlags(flags, positionals);
  const language = inferLanguage(flags, sourceInfo.source_file);
  const registry = LANGUAGE_REGISTRY.find((item) => item.language === language) || null;
  const symbols = summarizeCodeIr(sourceInfo.source, language);
  const sourceHex = bytesToHex(sourceInfo.source);
  const payload = {
    schema_version: "geoseal_code_ir_v1",
    ok: true,
    language,
    source_file: sourceInfo.source_file,
    source_sha256: sha256Hex(sourceInfo.source),
    byte_length: Buffer.byteLength(sourceInfo.source, "utf8"),
    hex_sha256: sha256Hex(sourceHex),
    transport_lanes_available: ["byte", "hex", "binary", "tongue"],
    bijection_scope: {
      exact: "source_text_to_byte_hex_binary_tongue_transport",
      not_claimed: "semantic equivalence across programming languages",
    },
    registry,
    symbols,
    metrics: {
      line_count: sourceInfo.source.split(/\r?\n/).length,
      import_count: symbols.imports.length,
      function_count: symbols.functions.length,
      class_count: symbols.classes.length,
      type_count: symbols.types.length,
    },
  };
  writeJsonOrText(flags, payload, JSON.stringify(payload, null, 2));
}

function parseInjectionInterval(raw) {
  const value = String(raw || "lines:40").trim();
  const match = value.match(/^(lines|chars|bytes):(\d+)$/);
  if (!match) {
    throw new Error("--interval must look like lines:40, chars:800, or bytes:800");
  }
  const count = Number(match[2]);
  if (!Number.isInteger(count) || count <= 0) {
    throw new Error("--interval count must be a positive integer");
  }
  return { mode: match[1], count, raw: value };
}

function buildLineChunks(source, count) {
  const lines = source.split(/\r?\n/);
  const chunks = [];
  for (let start = 0; start < lines.length; start += count) {
    const chunkLines = lines.slice(start, start + count);
    chunks.push({
      start_line: start + 1,
      end_line: start + chunkLines.length,
      text: chunkLines.join("\n"),
    });
  }
  return chunks;
}

function buildFixedWidthChunks(source, count, mode) {
  if (mode === "bytes") {
    const buffer = Buffer.from(String(source), "utf8");
    const chunks = [];
    for (let start = 0; start < buffer.length; start += count) {
      const slice = buffer.subarray(start, Math.min(start + count, buffer.length));
      chunks.push({
        byte_start: start,
        byte_end: start + slice.length,
        text: slice.toString("utf8"),
        hex: slice.toString("hex"),
        buffer: slice,
        mode,
      });
    }
    return chunks;
  }
  const text = String(source);
  const chunks = [];
  for (let start = 0; start < text.length; start += count) {
    chunks.push({
      char_start: start,
      char_end: Math.min(start + count, text.length),
      text: text.slice(start, start + count),
      mode,
    });
  }
  return chunks;
}

function runInjectionPlan(flags, positionals) {
  const sourceInfo = readSourceFromFlags(flags, positionals);
  const language = inferLanguage(flags, sourceInfo.source_file);
  const interval = parseInjectionInterval(flags.interval);
  const tongues = parseTongues(flags);
  const chunks =
    interval.mode === "lines"
      ? buildLineChunks(sourceInfo.source, interval.count)
      : buildFixedWidthChunks(sourceInfo.source, interval.count, interval.mode);
  const checkpoints = chunks.map((chunk, index) => {
    const tongue = tongues[index % tongues.length] || "KO";
    const chunkHash = chunk.buffer ? sha256Data(chunk.buffer) : sha256Hex(chunk.text);
    const chunkHex = chunk.hex || bytesToHex(chunk.text);
    return {
      index,
      tongue,
      marker: `SCBE_SYNC_${tongue}_${String(index).padStart(4, "0")}_${chunkHash.slice(0, 12)}`,
      source_sha256: sha256Hex(sourceInfo.source),
      chunk_sha256: chunkHash,
      token_sha256: sha256Hex(`${tongue}:${chunkHex}`),
      byte_length: chunk.buffer ? chunk.buffer.length : Buffer.byteLength(chunk.text, "utf8"),
      start_line: chunk.start_line || null,
      end_line: chunk.end_line || null,
      char_start: chunk.char_start ?? null,
      char_end: chunk.char_end ?? null,
      byte_start: chunk.byte_start ?? null,
      byte_end: chunk.byte_end ?? null,
    };
  });
  const payload = {
    schema_version: "geoseal_code_injection_plan_v1",
    ok: true,
    language,
    source_file: sourceInfo.source_file,
    source_sha256: sha256Hex(sourceInfo.source),
    interval,
    tongues,
    checkpoint_count: checkpoints.length,
    checkpoint_policy: "deterministic_hash_sync_markers_only_no_prompt_or_code_injection",
    bijection_scope: {
      exact: "checkpoint hashes bind byte_hex_binary_tongue transport segments",
      not_claimed: "target language semantic equivalence",
    },
    checkpoints,
  };
  writeJsonOrText(flags, payload, JSON.stringify(payload, null, 2));
}

function _normalizeIrSymbols(ir) {
  if (!ir || typeof ir !== "object") return null;
  // Accept either a full code-ir packet (top-level "symbols") or a raw symbols object.
  const symbols = ir.symbols && typeof ir.symbols === "object" ? ir.symbols : ir;
  return {
    imports: Array.isArray(symbols.imports) ? symbols.imports.slice().sort() : [],
    functions: Array.isArray(symbols.functions) ? symbols.functions.slice().sort() : [],
    classes: Array.isArray(symbols.classes) ? symbols.classes.slice().sort() : [],
    types: Array.isArray(symbols.types) ? symbols.types.slice().sort() : [],
    exports: Array.isArray(symbols.exports) ? symbols.exports.slice().sort() : [],
  };
}

function _diffSymbolLists(expected, actual) {
  const exp = new Set(expected || []);
  const act = new Set(actual || []);
  const missing = [];
  const extra = [];
  for (const item of exp) if (!act.has(item)) missing.push(item);
  for (const item of act) if (!exp.has(item)) extra.push(item);
  return { missing: missing.sort(), extra: extra.sort() };
}

function _diffIr(expected, actual) {
  const expectedNorm = _normalizeIrSymbols(expected);
  const actualNorm = _normalizeIrSymbols(actual);
  if (!expectedNorm || !actualNorm) {
    return { ok: false, error: "ir_normalize_failed" };
  }
  const fields = ["imports", "functions", "classes", "types", "exports"];
  const perField = {};
  let allOk = true;
  for (const field of fields) {
    const diff = _diffSymbolLists(expectedNorm[field], actualNorm[field]);
    perField[field] = diff;
    if (diff.missing.length > 0 || diff.extra.length > 0) allOk = false;
  }
  return { ok: allOk, fields: perField };
}

function _resolveProbeCommand(language, sourceFile) {
  const reg = LANGUAGE_REGISTRY.find((item) => item.language === language);
  if (!reg || !reg.compile_check) return null;
  const command = String(reg.compile_check);
  if (command.includes("<file>")) {
    return command.replace("<file>", JSON.stringify(sourceFile));
  }
  // For commands like "npm run typecheck" that don't take a per-file arg.
  return command;
}

function runCodeVerify(flags, positionals) {
  const sourceInfo = readSourceFromFlags(flags, positionals);
  const language = inferLanguage(flags, sourceInfo.source_file);
  const registry = LANGUAGE_REGISTRY.find((item) => item.language === language) || null;
  const sourceSha = sha256Hex(sourceInfo.source);
  const symbols = summarizeCodeIr(sourceInfo.source, language);

  const expectedSha = flags["expected-source-sha"] ? String(flags["expected-source-sha"]).trim() : null;
  const expectedIrPath = flags["expected-ir-file"] ? String(flags["expected-ir-file"]).trim() : null;

  const sha_check = expectedSha
    ? {
        provided: true,
        expected_source_sha256: expectedSha,
        actual_source_sha256: sourceSha,
        ok: expectedSha === sourceSha,
      }
    : { provided: false, actual_source_sha256: sourceSha, ok: true };

  let ir_check = { provided: false, ok: true };
  if (expectedIrPath) {
    let parsedExpected = null;
    try {
      const raw = fs.readFileSync(path.isAbsolute(expectedIrPath) ? expectedIrPath : path.join(ROOT, expectedIrPath), "utf8");
      parsedExpected = JSON.parse(raw);
    } catch (err) {
      ir_check = {
        provided: true,
        ok: false,
        error: `failed_to_load_expected_ir: ${err.message}`,
      };
    }
    if (parsedExpected) {
      const diff = _diffIr(parsedExpected, { symbols });
      ir_check = {
        provided: true,
        expected_ir_file: expectedIrPath,
        ok: diff.ok,
        fields: diff.fields,
      };
    }
  }

  const probeRequested = flags.probe === true || flags.probe === "true" || flags["compile-probe"] === true || flags["compile-probe"] === "true";
  let probe = { requested: false, ok: true };
  if (probeRequested) {
    const cmd = _resolveProbeCommand(language, sourceInfo.source_file);
    if (!cmd) {
      probe = {
        requested: true,
        ok: false,
        error: `no_compile_check_for_language: ${language}`,
      };
    } else {
      try {
        const { execSync } = require("node:child_process");
        const stdout = execSync(cmd, {
          cwd: ROOT,
          encoding: "utf8",
          stdio: ["ignore", "pipe", "pipe"],
          timeout: 30000,
        });
        probe = {
          requested: true,
          ok: true,
          command: cmd,
          stdout_preview: String(stdout || "").slice(0, 800),
        };
      } catch (err) {
        probe = {
          requested: true,
          ok: false,
          command: cmd,
          exit_code: err.status ?? null,
          stdout_preview: String(err.stdout || "").slice(0, 800),
          stderr_preview: String(err.stderr || err.message || "").slice(0, 800),
        };
      }
    }
  }

  const verdict_ok = sha_check.ok && ir_check.ok && probe.ok;
  const payload = {
    schema_version: "geoseal_code_verify_v1",
    ok: verdict_ok,
    language,
    source_file: sourceInfo.source_file,
    actual_source_sha256: sourceSha,
    byte_length: Buffer.byteLength(sourceInfo.source, "utf8"),
    bijection_scope: {
      exact: "source_sha + extracted_symbol_lists are deterministic",
      not_claimed: "compile_probe success only proves syntax/typecheck on this host",
    },
    registry,
    symbols,
    sha_check,
    ir_check,
    probe,
    verdict: {
      ok: verdict_ok,
      checks: {
        sha_check_ok: sha_check.ok,
        ir_check_ok: ir_check.ok,
        probe_ok: probe.ok,
      },
    },
  };
  writeJsonOrText(flags, payload, JSON.stringify(payload, null, 2));
}

function runCodeTranslate(flags, positionals) {
  const sourceInfo = readSourceFromFlags(flags, positionals);
  const sourceLanguage = inferLanguage(flags, sourceInfo.source_file);
  const targetRaw = String(flags["target-language"] || flags.target || "").trim().toLowerCase();
  if (!targetRaw) {
    throw new Error("--target-language is required (e.g. python, typescript, rust)");
  }
  const sourceRegistry = LANGUAGE_REGISTRY.find((item) => item.language === sourceLanguage) || null;
  const targetRegistry = LANGUAGE_REGISTRY.find((item) => item.language === targetRaw) || null;
  if (!targetRegistry) {
    throw new Error(`unknown target language: ${targetRaw}`);
  }
  if (sourceLanguage === targetRaw) {
    throw new Error("source-language and target-language must differ");
  }
  const sourceSymbols = summarizeCodeIr(sourceInfo.source, sourceLanguage);
  const sourceSha = sha256Hex(sourceInfo.source);
  // Required-preserved symbols: function and class names. Types/exports can
  // legitimately differ across languages (idiomatic naming, language-specific
  // type systems), so they are listed as "advisory_preserve" rather than
  // "must_preserve".
  const must_preserve = {
    functions: sourceSymbols.functions.slice().sort(),
    classes: sourceSymbols.classes.slice().sort(),
  };
  const advisory_preserve = {
    types: sourceSymbols.types.slice().sort(),
    imports_semantic_intent: sourceSymbols.imports.slice().sort(),
  };
  // Deterministic translation contract id binds source SHA + target language
  // so two callers with the same inputs get the same contract id.
  const contractId = sha256Hex(`translate:${sourceSha}:${targetRaw}`).slice(0, 24);
  // Forced-prefix scaffold (mirrors src/governance/coding_eval_constrained_decoding.py
  // pattern): the LLM consumer should emit code that contains every must_preserve
  // identifier verbatim. Render the prefix in the canonical form so the gate
  // and the prompt scaffold agree on what counts as preserved.
  const prefix_tokens = [...must_preserve.functions, ...must_preserve.classes];
  const forced_prefix = prefix_tokens.length
    ? `required-preserved-identifiers: ${prefix_tokens.map((t) => "`" + t + "`").join(" | ")} ::`
    : "required-preserved-identifiers: (none) ::";
  const payload = {
    schema_version: "geoseal_code_translate_contract_v1",
    ok: true,
    contract_id: contractId,
    source: {
      file: sourceInfo.source_file,
      language: sourceLanguage,
      sha256: sourceSha,
      byte_length: Buffer.byteLength(sourceInfo.source, "utf8"),
      tongue: sourceRegistry ? sourceRegistry.tongue : null,
      symbols: sourceSymbols,
    },
    target: {
      language: targetRaw,
      tongue: targetRegistry.tongue,
      registry: targetRegistry,
    },
    contract: {
      must_preserve,
      advisory_preserve,
      forced_prefix,
      verify_command: `geoseal code-verify --source-file <translated-output> --language ${targetRaw} --expected-ir-file <this-contract-as-ir-file> --probe`,
    },
    bijection_scope: {
      exact: "source_sha + must_preserve identifier set + contract_id are deterministic",
      not_claimed: "the LLM-produced translation; that requires code-verify --probe to pass on the output",
    },
    policy: "contract_only_no_llm_invocation_no_code_execution",
  };
  writeJsonOrText(flags, payload, JSON.stringify(payload, null, 2));
}

function runTokenizerCodeLanes(flags) {
  const command = String(flags.command || flags.content || "");
  if (!command) {
    throw new Error("--command is required for tokenizer-code-lanes");
  }
  const tongues = parseTongues(flags);
  const lanes = tongues.map((tongue, index) => {
    const source = `${tongue}:${command}`;
    const binary = Buffer.from(source, "utf8").toString("hex");
    return {
      index,
      tongue,
      command,
      source,
      binary,
      source_sha256: sha256Hex(source),
      token_sha256: sha256Hex(`${tongue}:${binary}`),
    };
  });
  const payload = {
    schema_version: "geoseal_tokenizer_code_lanes_v1",
    ok: true,
    command,
    tongues,
    lanes,
  };
  if (flags.output) {
    const outputPath = path.resolve(ROOT, String(flags.output));
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
    payload.output = path.relative(ROOT, outputPath).replace(/\\/g, "/");
  }
  writeJsonOrText(flags, payload, JSON.stringify(payload, null, 2));
}

function loadLanePacket(flags, positionals) {
  if (flags["input-file"]) {
    return JSON.parse(fs.readFileSync(path.resolve(ROOT, String(flags["input-file"])), "utf8"));
  }
  const raw = positionals.find((item) => item.trim().startsWith("{"));
  if (raw) return JSON.parse(raw);
  throw new Error("--input-file or a JSON packet argument is required");
}

function runVerifyCodeLanes(flags, positionals) {
  const packet = loadLanePacket(flags, positionals);
  const lanes = Array.isArray(packet.lanes) ? packet.lanes : [];
  const payload = {
    schema_version: "geoseal_verify_code_lanes_v1",
    ok: packet.schema_version === "geoseal_tokenizer_code_lanes_v1" && lanes.length > 0,
    decoded_count: lanes.length,
    lane_count: lanes.length,
  };
  writeJsonOrText(flags, payload, payload.ok ? "Code lanes verified." : "Code lanes failed verification.");
}

function runDecodeCodeLanes(flags, positionals) {
  const packet = loadLanePacket(flags, positionals);
  const lanes = Array.isArray(packet.lanes) ? packet.lanes : [];
  const outputDir = path.resolve(ROOT, String(flags["output-dir"] || "artifacts/tokenizer_code_lanes/decoded"));
  fs.mkdirSync(outputDir, { recursive: true });
  const written = [];
  for (const lane of lanes) {
    const base = `${String(lane.index).padStart(2, "0")}_${lane.tongue}_${lane.command}`;
    const safeBase = base.replace(/[^A-Za-z0-9_.-]+/g, "_");
    const textPath = path.join(outputDir, `${safeBase}.txt`);
    const binaryPath = path.join(outputDir, `${safeBase}.bin`);
    fs.writeFileSync(textPath, String(lane.source || lane.command || ""), "utf8");
    if (flags["write-binary"]) {
      fs.writeFileSync(binaryPath, String(lane.binary || ""), "utf8");
    }
    written.push({
      path: path.relative(ROOT, textPath).replace(/\\/g, "/"),
      binary_path: path.relative(ROOT, binaryPath).replace(/\\/g, "/"),
      tongue: lane.tongue,
    });
  }
  const payload = {
    schema_version: "geoseal_decode_code_lanes_v1",
    ok: true,
    decoded_count: lanes.length,
    written,
  };
  writeJsonOrText(flags, payload, `Decoded ${lanes.length} code lanes.`);
}

function runCalc(flags, positionals) {
  const expression = String(flags.expr || flags.expression || positionals.slice(1).join(" ")).trim();
  if (!expression) {
    const payload = {
      schema_version: "geoseal_calc_v1",
      ok: false,
      error: "missing_expression",
      message: "Pass --expr, for example: geoseal calc --expr \"sqrt(2)^2 + phi\" --json",
    };
    writeJsonOrText(flags, payload, payload.message);
    process.exitCode = 2;
    return;
  }
  const value = evaluateExpression(expression);
  const payload = {
    schema_version: "geoseal_calc_v1",
    ok: true,
    expression,
    value,
    rounded_12: Number(value.toFixed(12)),
    constants: {
      phi: (1 + Math.sqrt(5)) / 2,
      pi: Math.PI,
      tau: Math.PI * 2,
    },
  };
  writeJsonOrText(flags, payload, `${payload.rounded_12}`);
}

function runDimensions(flags, positionals) {
  const unit = String(flags.unit || flags.quantity || positionals.slice(1).join(" ") || "one").trim();
  const vector = analyzeDimensions(unit);
  const payload = {
    schema_version: "geoseal_dimensional_analysis_v1",
    ok: true,
    input: unit,
    labels: DIMENSION_LABELS,
    vector,
    canonical: formatDimensions(vector),
    basis: {
      M: "mass",
      L: "length",
      T: "time",
      I: "electric_current",
      Theta: "temperature",
      N: "amount_of_substance",
      J: "luminous_intensity",
    },
  };
  writeJsonOrText(flags, payload, `${unit} => ${payload.canonical}`);
}

function flattenDuckRelated(items, limit, rows = []) {
  for (const item of items || []) {
    if (rows.length >= limit) break;
    if (Array.isArray(item.Topics)) {
      flattenDuckRelated(item.Topics, limit, rows);
      continue;
    }
    if (item.Text || item.FirstURL) {
      rows.push({
        title: String(item.Text || "").split(" - ")[0].slice(0, 180),
        snippet: String(item.Text || "").slice(0, 600),
        url: String(item.FirstURL || ""),
      });
    }
  }
  return rows;
}

async function runWebSearch(flags, positionals) {
  const query = String(flags.query || flags.q || positionals.slice(1).join(" ")).trim();
  if (!query) {
    const payload = {
      schema_version: "geoseal_web_search_v1",
      ok: false,
      error: "missing_query",
      message: "Pass --query, for example: geoseal web-search --query \"site:docs.python.org pathlib\" --json",
    };
    writeJsonOrText(flags, payload, payload.message);
    process.exitCode = 2;
    return;
  }
  const limit = Math.max(1, Math.min(10, numericFlag(flags, "limit", 5)));
  const url = new URL("https://api.duckduckgo.com/");
  url.searchParams.set("q", query);
  url.searchParams.set("format", "json");
  url.searchParams.set("no_html", "1");
  url.searchParams.set("skip_disambig", "1");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), Math.max(1000, numericFlag(flags, "timeout-ms", 10000)));
  try {
    const response = await fetch(url, {
      headers: { "user-agent": "scbe-geoseal-cli/4" },
      signal: controller.signal,
    });
    const text = await response.text();
    let data = {};
    try {
      data = JSON.parse(text);
    } catch (_err) {
      data = {};
    }
    const results = [];
    if (data.AbstractText || data.AbstractURL) {
      results.push({
        title: String(data.Heading || query),
        snippet: String(data.AbstractText || "").slice(0, 1000),
        url: String(data.AbstractURL || ""),
      });
    }
    flattenDuckRelated(data.RelatedTopics, limit, results);
    const payload = {
      schema_version: "geoseal_web_search_v1",
      ok: response.ok,
      provider: "duckduckgo_instant_answer",
      query,
      status: response.status,
      result_count: Math.min(results.length, limit),
      results: results.slice(0, limit),
      note: "Public no-key search surface. Use url-fetch on a selected result for page-level inspection.",
    };
    writeJsonOrText(flags, payload, payload.results.map((row) => `${row.title}\n${row.url}`).join("\n\n") || "No instant-answer results.");
  } finally {
    clearTimeout(timeout);
  }
}

function stripHtml(text) {
  return String(text || "")
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\s+/g, " ")
    .trim();
}

async function runUrlFetch(flags, positionals) {
  const rawUrl = String(flags.url || positionals[1] || "").trim();
  if (!rawUrl) {
    const payload = {
      schema_version: "geoseal_url_fetch_v1",
      ok: false,
      error: "missing_url",
      message: "Pass --url, for example: geoseal url-fetch --url https://example.com --json",
    };
    writeJsonOrText(flags, payload, payload.message);
    process.exitCode = 2;
    return;
  }
  const url = new URL(rawUrl);
  if (!["http:", "https:"].includes(url.protocol)) {
    throw new Error("url-fetch only supports http and https URLs");
  }
  const maxChars = Math.max(200, Math.min(20000, numericFlag(flags, "max-chars", 4000)));
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), Math.max(1000, numericFlag(flags, "timeout-ms", 10000)));
  try {
    const response = await fetch(url, {
      headers: { "user-agent": "scbe-geoseal-cli/4" },
      signal: controller.signal,
    });
    const contentType = String(response.headers.get("content-type") || "");
    const raw = await response.text();
    const text = contentType.includes("html") ? stripHtml(raw) : raw.replace(/\s+/g, " ").trim();
    const payload = {
      schema_version: "geoseal_url_fetch_v1",
      ok: response.ok,
      url: url.toString(),
      status: response.status,
      content_type: contentType,
      byte_count: Buffer.byteLength(raw, "utf8"),
      text_preview: text.slice(0, maxChars),
      sha256: sha256Hex(raw),
    };
    writeJsonOrText(flags, payload, payload.text_preview);
  } finally {
    clearTimeout(timeout);
  }
}

function compactNomadEntry(entry) {
  const results = entry && typeof entry.results === "object" ? entry.results : {};
  const material = results && typeof results.material === "object" ? results.material : {};
  const method = results && typeof results.method === "object" ? results.method : {};
  const properties = results && typeof results.properties === "object" ? results.properties : {};
  const entryId = String(entry.entry_id || "");
  return {
    entry_id: entryId,
    upload_id: entry.upload_id || null,
    external_db: entry.external_db || null,
    domain: entry.domain || null,
    formula: material.chemical_formula_hill || material.chemical_formula_reduced || null,
    elements: Array.isArray(material.elements) ? material.elements : [],
    material_id: material.material_id || null,
    method_name: method.method_name || null,
    available_property_groups: Object.keys(properties).sort(),
    entry_create_time: entry.entry_create_time || null,
    nomad_gui_url: entryId ? `https://nomad-lab.eu/prod/v1/gui/search/entries/entry/id/${entryId}` : null,
  };
}

async function runMaterials(flags, positionals) {
  const element = String(flags.element || flags.elements || "").trim();
  const formula = String(flags.formula || flags.f || "").trim();
  const searchText = String(flags.query || flags.q || positionals.slice(1).join(" ")).trim();
  const inferredElement = element || (/^[A-Z][a-z]?$/.test(searchText) ? searchText : "");
  const inferredFormula = formula || (!inferredElement ? searchText : "");
  if (!inferredElement && !inferredFormula) {
    const payload = {
      schema_version: "geoseal_material_search_v1",
      ok: false,
      error: "missing_material_query",
      message: "Pass --element W or --formula TiNi, for example: geoseal materials --element W --json",
    };
    writeJsonOrText(flags, payload, payload.message);
    process.exitCode = 2;
    return;
  }
  const limit = Math.max(1, Math.min(25, numericFlag(flags, "limit", 5)));
  const url = new URL("https://nomad-lab.eu/prod/v1/api/v1/entries");
  url.searchParams.set("page_size", String(limit));
  if (inferredElement) url.searchParams.set("results.material.elements", inferredElement);
  if (inferredFormula) url.searchParams.set("results.material.chemical_formula_hill", inferredFormula);
  const headers = { accept: "application/json", "user-agent": "scbe-geoseal-cli/4" };
  const token = loadConnectorEnvValue("NOMAD_TOKEN");
  if (token) headers.authorization = `Bearer ${token}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), Math.max(1000, numericFlag(flags, "timeout-ms", 15000)));
  try {
    const response = await fetch(url, { headers, signal: controller.signal });
    const raw = await response.text();
    let data = {};
    try {
      data = JSON.parse(raw);
    } catch (_err) {
      data = {};
    }
    const entries = Array.isArray(data.data) ? data.data.map(compactNomadEntry) : [];
    const payload = {
      schema_version: "geoseal_material_search_v1",
      ok: response.ok,
      provider: "nomad_v1_entries",
      auth: token ? "bearer_token_present" : "public_no_token",
      query: {
        element: inferredElement || null,
        formula: inferredFormula || null,
        limit,
      },
      status: response.status,
      total: data.pagination && Number.isFinite(Number(data.pagination.total)) ? Number(data.pagination.total) : null,
      result_count: entries.length,
      entries,
      note: "NOMAD material metadata search. Use result entry_id/nomad_gui_url for deeper inspection; token is never printed.",
    };
    if (flags.output && payload.ok) {
      const outputPath = path.resolve(String(flags.output));
      fs.mkdirSync(path.dirname(outputPath), { recursive: true });
      fs.writeFileSync(outputPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
      payload.output = outputPath;
    }
    const text = entries
      .map((entry) => `${entry.formula || "(formula unavailable)"} ${entry.external_db || ""} ${entry.entry_id}`)
      .join("\n");
    writeJsonOrText(flags, payload, text || "No NOMAD material records returned.");
  } finally {
    clearTimeout(timeout);
  }
}

function runToolbox(flags) {
  const payload = {
    schema_version: "geoseal_toolbox_v1",
    ok: true,
    purpose: "Small-agent mechanical tool surface for local verification, web lookup, code transport, and API routing.",
    quick_start: [
      { command: "tools", alias_for: "toolbox", purpose: "Show this grouped tool list.", example: "geoseal tools --json" },
      { command: "math", alias_for: "calc", purpose: "Quick calculator alias.", example: 'geoseal math "sqrt(2)^2 + phi" --json' },
      { command: "units", alias_for: "dimensions", purpose: "Quick dimensional-analysis alias.", example: 'geoseal units "kg*m/s^2" --json' },
      { command: "search", alias_for: "web-search", purpose: "Public no-key search alias.", example: 'geoseal search "site:docs.python.org pathlib" --json' },
      { command: "fetch", alias_for: "url-fetch", purpose: "Public URL fetch alias.", example: "geoseal fetch https://example.com --json" },
      { command: "materials", alias_for: "materials", purpose: "NOMAD material metadata search.", example: "geoseal materials --element W --limit 5 --json" },
      { command: "code-languages", purpose: "List code-language lanes, tongues, and verifier probes.", example: "geoseal code-languages --json" },
      { command: "code-ir", purpose: "Summarize source into a hash-bound code IR packet.", example: "geoseal code-ir --source-file src/index.ts --language typescript --json" },
      { command: "injection-plan", purpose: "Emit deterministic checkpoint markers for code/token streams.", example: "geoseal injection-plan --source-file src/index.ts --interval lines:40 --tongues KO,AV --json" },
      { command: "code-verify", purpose: "Verify source against expected SHA, expected IR, and an optional compile probe.", example: "geoseal code-verify --source-file src/index.ts --expected-ir-file ir.json --probe --json" },
      { command: "code-translate", purpose: "Emit a deterministic translation contract (no LLM, no execution) bounding cross-language code generation.", example: "geoseal code-translate --source-file lib.py --target-language typescript --json" },
    ],
    local_tools: [
      { command: "calc", purpose: "Safe arithmetic with constants and math functions.", example: 'geoseal calc --expr "sqrt(2)^2 + phi" --json' },
      { command: "dimensions", purpose: "Dimensional analysis over SI base and common derived units.", example: 'geoseal dimensions --unit "kg*m/s^2" --json' },
      { command: "tokenizer-code-lanes", purpose: "Encode code commands into tongue-scoped binary/hex lanes.", example: "geoseal tokenizer-code-lanes --command shl --tongues KO,AV --json" },
      { command: "verify-code-lanes", purpose: "Verify tokenizer lane packets.", example: "geoseal verify-code-lanes --input-file lanes.json --json" },
      { command: "decode-code-lanes", purpose: "Decode tokenizer lane packets to text/binary artifacts.", example: "geoseal decode-code-lanes --input-file lanes.json --write-binary --json" },
      { command: "code-languages", purpose: "Advertise language adapters and proof boundaries.", example: "geoseal code-languages --json" },
      { command: "code-ir", purpose: "Extract a source summary with byte/hex/tongue transport hashes.", example: "geoseal code-ir --source-file sample.py --language python --json" },
      { command: "injection-plan", purpose: "Plan governed sync beacons at fixed line/char/byte intervals.", example: "geoseal injection-plan --source-file sample.py --interval lines:20 --tongues KO,AV --json" },
      { command: "code-verify", purpose: "Re-extract IR and run optional compile probe; verdict is hash-bound.", example: "geoseal code-verify --source-file sample.py --probe --json" },
      { command: "code-translate", purpose: "Emit a deterministic translation contract — must-preserve identifiers + forced prefix; no LLM, no execution.", example: "geoseal code-translate --source-file sample.py --target-language typescript --json" },
    ],
    network_tools: [
      { command: "web-search", purpose: "Public no-key web search via DuckDuckGo Instant Answer.", example: 'geoseal web-search --query "site:docs.python.org pathlib" --json' },
      { command: "url-fetch", purpose: "Fetch and hash public HTTP/HTTPS content previews.", example: "geoseal url-fetch --url https://example.com --json" },
      { command: "materials", purpose: "Search NOMAD material records by element/formula; uses NOMAD_TOKEN if present.", example: "geoseal materials --element W --limit 5 --json" },
      { command: "github", purpose: "Repo/issue helper routed through existing Python passthrough when installed.", example: "geoseal github --mode status --json" },
      { command: "polymarket", purpose: "Prediction-market research routed through existing Python passthrough when installed.", example: "geoseal polymarket --mode search --query ai --json" },
    ],
    api_tools: Object.keys(COMMAND_MAP).sort(),
    safety: {
      secrets_to_remote_models: "forbid",
      default_network_mode: "public_no_key",
      shell_execution: "not provided by these local tools",
    },
  };
  writeJsonOrText(flags, payload, payload.local_tools.map((tool) => `${tool.command}: ${tool.purpose}`).join("\n"));
}

function loadAgentBusModule() {
  const localDist = path.join(ROOT, "packages", "agent-bus", "dist", "index.js");
  if (fs.existsSync(localDist)) {
    return require(localDist);
  }
  try {
    return require("scbe-agent-bus");
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`scbe-agent-bus is not available. Run npm install or install scbe-aethermoore-cli. Details: ${message}`);
  }
}

function agentBusFrontendPacket() {
  return {
    schema_version: "geoseal_agent_bus_frontend_v1",
    ok: true,
    backend_default: "http://127.0.0.1:8787",
    commands: [
      { command: "agent-bus-server", purpose: "Start the local agent-bus HTTP backend.", example: "geoseal agent-bus-server --port 8787" },
      { command: "agent-bus-ui", purpose: "Open the terminal frontend for the agent bus.", example: "geoseal agent-bus-ui" },
      { command: "agent-bus-send", purpose: "Send one governed task to the backend.", example: 'geoseal agent-bus-send --task "review changed files" --json' },
    ],
    safety: {
      shell_execution: "not available",
      default_privacy: "local_only",
      remote_dispatch: "explicit flags only",
    },
  };
}

async function runAgentBusServer(flags) {
  const agentBus = loadAgentBusModule();
  const handle = await agentBus.startAgentBusServer({
    host: String(flags.host || "127.0.0.1"),
    port: Number(flags.port || 8787),
    repoRoot: flags["repo-root"] ? String(flags["repo-root"]) : ROOT,
    python: flags.python ? String(flags.python) : undefined,
    continueOnError: Boolean(flags["continue-on-error"]),
  });
  const payload = {
    schema_version: "geoseal_agent_bus_backend_start_v1",
    ok: true,
    url: handle.url,
    routes: ["/health", "/v1/events", "/v1/batch"],
  };
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
}

async function runAgentBusUi(flags) {
  if (flags.json) {
    writeJsonOrText(flags, agentBusFrontendPacket(), "agent-bus-ui");
    return;
  }
  const agentBus = loadAgentBusModule();
  await agentBus.runAgentBusTerminalUi({
    baseUrl: String(flags["base-url"] || process.env.SCBE_AGENT_BUS_URL || "http://127.0.0.1:8787"),
  });
}

async function runAgentBusSend(flags) {
  const task = String(flags.task || "").trim();
  if (!task) {
    const payload = {
      schema_version: "geoseal_agent_bus_send_v1",
      ok: false,
      error: "missing_task",
      message: 'Pass --task, for example: geoseal agent-bus-send --task "review changed files" --json',
    };
    writeJsonOrText(flags, payload, payload.message);
    return;
  }
  const agentBus = loadAgentBusModule();
  const result = await agentBus.postAgentBusEvent(
    {
      task,
      taskType: String(flags["task-type"] || "general"),
      privacy: String(flags.privacy || "local_only"),
      budgetCents: Number(flags["budget-cents"] || 0),
      dispatchProvider: String(flags["dispatch-provider"] || "offline"),
      dispatch: flags.dispatch !== "false",
    },
    { baseUrl: String(flags["base-url"] || process.env.SCBE_AGENT_BUS_URL || "http://127.0.0.1:8787") }
  );
  writeJsonOrText(flags, result, JSON.stringify(result));
}

const TERMINAL_UI_COMMANDS = [
  { command: "toolbox", label: "Toolbox overview", prompt: null },
  { command: "doctor", label: "Doctor / command inventory", prompt: null },
  { command: "calc", label: "Calculator", prompt: "Expression" },
  { command: "dimensions", label: "Dimensional analysis", prompt: "Unit expression" },
  { command: "code-languages", label: "Code language lanes", prompt: null },
  { command: "code-ir", label: "Code IR summary", prompt: "Source file" },
  { command: "injection-plan", label: "Code injection/checkpoint plan", prompt: "Source file" },
  { command: "materials", label: "NOMAD material search", prompt: "Element or formula" },
  { command: "web-search", label: "Public web search", prompt: "Search query" },
  { command: "url-fetch", label: "Fetch public URL", prompt: "URL" },
  { command: "exit", label: "Exit", prompt: null },
];

function terminalUiPacket(interactive) {
  return {
    schema_version: "geoseal_terminal_ui_v1",
    ok: true,
    interactive,
    purpose: "Optional terminal menu over GeoSeal local tools and public no-key network helpers.",
    commands: TERMINAL_UI_COMMANDS.map((item, index) => ({
      index: index + 1,
      command: item.command,
      label: item.label,
      requires_input: Boolean(item.prompt),
    })),
    safety: {
      shell_execution: "not available",
      remote_model_calls: "not available",
      network_tools: "public_no_key_only",
    },
  };
}

function askLine(rl, prompt) {
  return new Promise((resolve) => rl.question(prompt, (answer) => resolve(String(answer || "").trim())));
}

async function runTerminalUi(flags) {
  const interactive = Boolean(process.stdin.isTTY && process.stdout.isTTY && !flags.json);
  const packet = terminalUiPacket(interactive);
  if (!interactive) {
    writeJsonOrText(
      { ...flags, json: true },
      packet,
      packet.commands.map((item) => `${item.index}. ${item.label} (${item.command})`).join("\n")
    );
    return;
  }

  process.stdout.write("GeoSeal Terminal UI\n");
  process.stdout.write("Safe local tools plus public no-key lookup. No shell execution.\n\n");

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  try {
    while (true) {
      for (const item of TERMINAL_UI_COMMANDS) {
        process.stdout.write(`${item.command === "exit" ? "0" : item.index}. ${item.label}\n`);
      }
      const choice = await askLine(rl, "\nSelect tool: ");
      const selected =
        TERMINAL_UI_COMMANDS.find((item) => item.command === choice.toLowerCase()) ||
        TERMINAL_UI_COMMANDS.find((item) => String(item.index) === choice) ||
        (choice === "0" ? TERMINAL_UI_COMMANDS.find((item) => item.command === "exit") : null);

      if (!selected) {
        process.stdout.write("Unknown selection.\n\n");
        continue;
      }
      if (selected.command === "exit") {
        process.stdout.write("Bye.\n");
        return;
      }

      process.stdout.write("\n");
      if (selected.command === "toolbox") {
        runToolbox({});
      } else if (selected.command === "doctor") {
        runDoctor({});
      } else if (selected.command === "calc") {
        const expr = await askLine(rl, `${selected.prompt}: `);
        runCalc({ expr }, []);
      } else if (selected.command === "dimensions") {
        const unit = await askLine(rl, `${selected.prompt}: `);
        runDimensions({ unit }, []);
      } else if (selected.command === "code-languages") {
        runCodeLanguages({});
      } else if (selected.command === "code-ir") {
        const sourceFile = await askLine(rl, `${selected.prompt}: `);
        runCodeIr({ "source-file": sourceFile }, []);
      } else if (selected.command === "injection-plan") {
        const sourceFile = await askLine(rl, `${selected.prompt}: `);
        runInjectionPlan({ "source-file": sourceFile, interval: "lines:40" }, []);
      } else if (selected.command === "materials") {
        const query = await askLine(rl, `${selected.prompt}: `);
        await runMaterials({ query }, []);
      } else if (selected.command === "web-search") {
        const query = await askLine(rl, `${selected.prompt}: `);
        await runWebSearch({ query }, []);
      } else if (selected.command === "url-fetch") {
        const url = await askLine(rl, `${selected.prompt}: `);
        await runUrlFetch({ url }, []);
      }
      process.stdout.write("\n");
    }
  } finally {
    rl.close();
  }
}

const DEFAULT_SERVICE_DIR = path.join(ROOT, "artifacts", "geoseal_service");

function serviceOutputDir(flags) {
  const explicit = flags["service-output-dir"] || flags["state-dir"] || process.env.SCBE_GEOSEAL_SERVICE_DIR;
  if (explicit && typeof explicit === "string") {
    return path.isAbsolute(explicit) ? explicit : path.resolve(process.cwd(), explicit);
  }
  return DEFAULT_SERVICE_DIR;
}

function isPidAlive(pid) {
  const n = Number(pid);
  if (!Number.isFinite(n) || n <= 0) return false;
  try {
    process.kill(n, 0);
    return true;
  } catch (_err) {
    // Fall through to the Windows process table check below. On Windows,
    // process.kill(pid, 0) can fail for permission-bound live processes.
  }
  if (process.platform === "win32") {
    const result = spawnSync("tasklist", ["/FI", `PID eq ${n}`, "/NH"], {
      encoding: "utf8",
      shell: false,
      timeout: 2000,
    });
    if (result.error || result.status !== 0) return false;
    const stdout = String(result.stdout || "").trim();
    if (!stdout) return false;
    if (stdout.includes("No tasks are running")) return false;
    return true;
  }
  try {
    process.kill(n, 0);
    return true;
  } catch (_err) {
    return false;
  }
}

function resolveActiveServiceBase(flags) {
  if (String(process.env.SCBE_GEOSEAL_AUTODETECT || "").toLowerCase() === "0") return null;
  const statePath = path.join(serviceOutputDir(flags), "service.json");
  let raw;
  try {
    raw = fs.readFileSync(statePath, "utf8");
  } catch (_err) {
    return null;
  }
  let state;
  try {
    state = JSON.parse(raw);
  } catch (_err) {
    return null;
  }
  if (!state || typeof state !== "object") return null;
  const base = typeof state.api_base === "string" ? state.api_base.replace(/\/+$/, "") : "";
  const pid = Number(state.pid);
  if (!base || !Number.isFinite(pid) || pid <= 0) return null;
  if (!isPidAlive(pid)) return null;
  const headers = state.runtime_headers && typeof state.runtime_headers === "object" ? state.runtime_headers : {};
  return { apiBase: base, pid, authHeaders: headers, statePath };
}

function probePythonModule(moduleName) {
  const executables = [];
  if (process.env.SCBE_GEOSEAL_PYTHON) executables.push(process.env.SCBE_GEOSEAL_PYTHON);
  if (process.platform === "win32") executables.push("py");
  executables.push("python", "python3");

  for (const executable of executables) {
    const result = spawnSync(executable, ["-m", moduleName, "--help"], {
      encoding: "utf8",
      shell: false,
      cwd: ROOT,
      timeout: 8000,
    });
    if (!result.error) {
      return {
        executable,
        module: moduleName,
        ok: result.status === 0,
        status: result.status,
        stdout_preview: String(result.stdout || "").slice(0, 600),
        stderr_preview: String(result.stderr || "").slice(0, 600),
      };
    }
  }
  return { module: moduleName, ok: false, error: "no usable Python executable found" };
}

function runDoctor(flags) {
  const active = resolveActiveServiceBase(flags);
  const advertisedCommands = [
    "doctor",
    "permissions",
    "custom-commands",
    "run-command",
    "status",
    "chat",
    ...Object.keys(COMMAND_MAP).filter((name) => name !== "status" && name !== "chat"),
    "service",
    "service-status",
    "service-stop",
    "agent-io-contract",
    "harness-terminal",
    "harness-research",
    "research-terminal",
    "research-sources",
    "polymarket",
    "github",
    "gh",
    "lane-grid",
    "handoff-seal",
    "handoff-open",
    "tokenizer-code-lanes",
    "verify-code-lanes",
    "decode-code-lanes",
    "code-languages",
    "code-ir",
    "injection-plan",
    "languages",
    "code-sync",
    "ai2ai-bridge",
    "calc",
    "dimensions",
    "web-search",
    "url-fetch",
    "materials",
    "nomad",
    "tools",
    "math",
    "units",
    "search",
    "fetch",
    "toolbox",
    "terminal-ui",
    "ui",
    "agent-bus-ui",
    "agent-bus-server",
    "agent-bus-send",
  ];
  const payload = {
    ok: true,
    version: PACKAGE_JSON.version,
    node: process.version,
    platform: process.platform,
    package_bin: PACKAGE_JSON.bin || {},
    api_base_configured: Boolean(apiBase(flags)),
    service_autodetect_enabled: String(process.env.SCBE_GEOSEAL_AUTODETECT || "").toLowerCase() !== "0",
    active_service: active
      ? { api_base: active.apiBase, pid: active.pid, state_path: active.statePath }
      : null,
    api_commands: Object.keys(COMMAND_MAP).sort(),
    advertised_commands: advertisedCommands,
    custom_commands: listCustomCommands().map((command) => ({
      name: command.name,
      description: command.description,
      path: command.path,
      execution_mode: command.execution_mode,
    })),
    python_modules: [probePythonModule("src.geoseal_cli"), probePythonModule("geoseal_cli")],
    notes: [
      "API commands require --api-base/SCBE_API_BASE or a live autodetected service.",
      "Python passthrough commands are limited to the installed geoseal_cli parser.",
    ],
  };
  const text = [
    `GeoSeal doctor ${payload.version}`,
    `Node: ${payload.node}`,
    `Active service: ${payload.active_service ? payload.active_service.api_base : "none"}`,
    `API commands: ${payload.api_commands.length}`,
    `Python module src.geoseal_cli: ${payload.python_modules[0].ok ? "ok" : "fail"}`,
  ].join("\n");
  writeJsonOrText(flags, payload, text);
}

function buildBody(command, flags) {
  const body = {};
  if (flags.language) body.language = String(flags.language);
  if (flags.content) body.content = String(flags.content);
  if (flags["source-name"]) body.source_name = String(flags["source-name"]);
  if (flags["include-extended"] !== undefined) body.include_extended = flags["include-extended"] === true || String(flags["include-extended"]).toLowerCase() === "true";
  if (flags["deck-size"]) body.deck_size = Number(flags["deck-size"]);
  if (flags["branch-width"]) body.branch_width = Number(flags["branch-width"]);
  if (flags.card) body.card = String(flags.card);
  if (flags.timeout) body.timeout = Number(flags.timeout);
  if (flags.tongue) body.tongue = String(flags.tongue);
  if (flags["project-shell-file"]) body.project_shell_file = String(flags["project-shell-file"]);
  if (flags.serve !== undefined) body.serve = flags.serve === true || String(flags.serve).toLowerCase() === "true";
  if (flags.port) body.port = Number(flags.port);
  if (flags["output-dir"]) body.output_dir = String(flags["output-dir"]);
  if (flags["history-file"]) body.history_file = String(flags["history-file"]);
  if (flags.command) body.command = String(flags.command);
  if (flags["source-name"]) body.source_name = String(flags["source-name"]);
  if (flags.decision) body.decision = String(flags.decision);
  if (flags.limit) body.limit = Number(flags.limit);
  if (flags["run-contract-file"]) body.run_contract_file = String(flags["run-contract-file"]);
  if (flags["target-stage"]) body.target_stage = String(flags["target-stage"]);
  if (flags.workspace) body.workspace = String(flags.workspace);
  if (flags["manifest-file"]) body.manifest_file = String(flags["manifest-file"]);
  if (flags["hub-url"]) body.hub_url = String(flags["hub-url"]);
  if (flags["token-env-var"]) body.token_env_var = String(flags["token-env-var"]);
  if (flags.token) body.token = String(flags.token);
  if (flags["probe-timeout"]) body.probe_timeout = Number(flags["probe-timeout"]);
  if (flags["agent-dir"]) body.agent_dir = String(flags["agent-dir"]);
  if (flags.execute !== undefined) body.execute = flags.execute === true || String(flags.execute).toLowerCase() === "true";
  if (command === "chat") {
    body.message = String(flags.message || flags.content || "");
    body.tentacle = String(flags.tentacle || "local");
    body.mode = String(flags.mode || "local-polypad");
  }
  if (flags.source) body.source = String(flags.source);
  if (flags["source-file"]) body.source_file = String(flags["source-file"]);
  if (flags.ledger) body.ledger = String(flags.ledger);
  if (flags.type) body.type = String(flags.type);
  if (flags.op) body.op = String(flags.op);
  if (flags.index !== undefined && flags.index !== true && Number.isFinite(Number(flags.index))) {
    body.index = Number(flags.index);
  }
  if (flags["no-ledger"] !== undefined) {
    body.no_ledger = flags["no-ledger"] === true || String(flags["no-ledger"]).toLowerCase() === "true";
  }
  if (flags.lang) body.lang = String(flags.lang);
  if (flags.provider) body.provider = String(flags.provider);
  if (flags.bits) body.bits = String(flags.bits);
  if (flags["small-first"] !== undefined) {
    body.small_first = flags["small-first"] === true || String(flags["small-first"]).toLowerCase() === "true";
  }
  if (flags["governance-tier"]) body.governance_tier = String(flags["governance-tier"]);
  if (flags.backend) body.backend = String(flags.backend);
  if (flags.goal) body.goal = String(flags.goal);
  if (flags["permission-mode"]) body.permission_mode = String(flags["permission-mode"]);
  return body;
}

function ensureBody(command, body) {
  if (command === "status") return;
  if (command === "project-run") {
    if (!body.project_shell_file) {
      throw new Error("--project-shell-file is required for project-run");
    }
    return;
  }
  if (command === "run-history") {
    if (!body.output_dir && !body.history_file) {
      throw new Error("--output-dir or --history-file is required for run-history");
    }
    return;
  }
  if (command === "nexus-status") {
    if (!body.hub_url && !body.output_dir && !body.manifest_file) {
      throw new Error("--hub-url, --output-dir, or --manifest-file is required for nexus-status");
    }
    return;
  }
  if (command === "nexus-connect") {
    if (!body.hub_url && !body.output_dir && !body.manifest_file) {
      throw new Error("--hub-url, --output-dir, or --manifest-file is required for nexus-connect");
    }
    return;
  }
  if (command === "nexus-dispatch") {
    if (!body.hub_url && !body.output_dir && !body.manifest_file) {
      throw new Error("--hub-url, --output-dir, or --manifest-file is required for nexus-dispatch");
    }
  }
  if (command === "cursor-status" || command === "cursor-overlord" || command === "fleet-distributions") {
    return;
  }
  if (command === "backend-registry") return;
  if (command === "agent-harness") return;
  if (command === "history") return;
  if (command === "replay") return;
  if (command === "code-packet") {
    if (!body.content && !body.source_file) {
      throw new Error("--content or --source-file is required for code-packet");
    }
    return;
  }
  if (command === "explain-route") {
    if (!body.content && !body.source_file) {
      throw new Error("--content or --source-file is required for explain-route");
    }
    return;
  }
  if (command === "testing-cli") {
    if (!body.content && !body.source_file) {
      throw new Error("--content or --source-file is required for testing-cli");
    }
    return;
  }
  if (command === "project-scaffold") {
    if (!body.content) {
      throw new Error("--content is required for project-scaffold");
    }
    if (!body.output_dir) {
      throw new Error("--output-dir is required for project-scaffold");
    }
    return;
  }
  if (command === "code-roundtrip") {
    if (!body.source && !body.content) {
      throw new Error("--source or --content is required for code-roundtrip");
    }
    return;
  }
  if (command === "binary-to-tmatrix") {
    if (!body.bits) {
      throw new Error("--bits is required for binary-to-tmatrix");
    }
    return;
  }
  if (command === "orchestrator-dispatch" || command === "orchestrator-status" || command === "orchestrator-promote") {
    if (!body.output_dir && !body.run_contract_file) {
      throw new Error("--output-dir or --run-contract-file is required");
    }
    return;
  }
  if (!body.language) throw new Error("--language is required");
  if (!body.content && command !== "chat") throw new Error("--content is required");
  if (command === "chat" && !body.message) throw new Error("--message or --content is required");
  if (command === "play-card" && !body.card) throw new Error("--card is required for play-card");
  if (command === "orchestrator-init" && !body.output_dir) throw new Error("--output-dir is required for orchestrator-init");
}

async function runApi(command, flags, ctx = {}) {
  const base = (ctx.resolvedBase || apiBase(flags)).replace(/\/+$/, "");
  const entry = COMMAND_MAP[command];
  if (!entry) throw new Error(`Unknown API command: ${command}`);
  const useRuntime = Boolean(flags.runtime) && entry.runtimePath;
  const pathName = useRuntime ? entry.runtimePath : entry.path;
  const requiresAuth = useRuntime ? Boolean(entry.runtimeAuth) : Boolean(entry.auth);
  const headers = { "Content-Type": "application/json" };
  if (requiresAuth) {
    let key = apiKey(flags);
    if (!key && ctx.autoContext && ctx.autoContext.authHeaders && ctx.autoContext.authHeaders["x-api-key"]) {
      key = ctx.autoContext.authHeaders["x-api-key"];
    }
    if (!key) throw new Error(`--api-key or SCBE_API_KEY is required for ${command}`);
    headers["x-api-key"] = key;
  }
  const url = `${base}${pathName}`;
  const options = { method: entry.method, headers };
  if (entry.method !== "GET") {
    const body = buildBody(command, flags);
    ensureBody(command, body);
    options.body = JSON.stringify(body);
  }
  const response = await fetch(url, options);
  const text = await response.text();
  if (!response.ok) {
    process.stderr.write(text || `${response.status} ${response.statusText}\n`);
    process.exitCode = 1;
    return;
  }
  try {
    const data = JSON.parse(text);
    process.stdout.write(`${JSON.stringify(data, null, 2)}\n`);
  } catch (_err) {
    process.stdout.write(text.endsWith("\n") ? text : `${text}\n`);
  }
}

function runPythonPassthrough(args) {
  const executables = [];
  if (process.env.SCBE_GEOSEAL_PYTHON) executables.push(process.env.SCBE_GEOSEAL_PYTHON);
  if (process.platform === "win32") executables.push("py");
  executables.push("python", "python3");

  const moduleCandidates = ["src.geoseal_cli", "geoseal_cli"];

  for (const executable of executables) {
    for (const moduleName of moduleCandidates) {
      const result = spawnSync(executable, ["-m", moduleName, ...args], {
        stdio: "inherit",
        shell: false,
        cwd: ROOT,
      });
      if (result.error) continue;
      if (result.status === 0) {
        process.exit(0);
      }
      const stderrText = result.stderr ? String(result.stderr) : "";
      if (stderrText.includes("No module named")) continue;
      process.exit(result.status === null ? 1 : result.status);
    }
  }

  for (const executable of executables) {
    const result = spawnSync(executable, ["-m", "geoseal_cli", ...args], {
      stdio: "inherit",
      shell: false,
      cwd: ROOT,
    });
    if (result.error) continue;
    process.exit(result.status === null ? 1 : result.status);
  }

  process.stderr.write(
    "GeoSeal npm shell could not find a usable Python runtime. Install the PyPI package and set SCBE_GEOSEAL_PYTHON if needed.\n"
  );
  process.exit(1);
}

async function main() {
  const argv = process.argv.slice(2);
  const { positionals, flags } = parseArgs(argv);
  const rawCommand = positionals[0];
  const command = normalizeCommand(rawCommand);

  if (!rawCommand || rawCommand === "help" || flags.help) {
    process.stdout.write(COMMAND_HELP);
    return;
  }
  if (command === "version") {
    process.stdout.write(`${PACKAGE_JSON.version}\n`);
    return;
  }
  if (command === "doctor") {
    runDoctor(flags);
    return;
  }
  if (command === "permissions") {
    runPermissions(flags);
    return;
  }
  if (command === "custom-commands") {
    runCustomCommands(flags);
    return;
  }
  if (command === "run-command") {
    runCustomCommand(positionals[1], flags);
    return;
  }
  if (command === "tokenizer-code-lanes") {
    runTokenizerCodeLanes(flags);
    return;
  }
  if (command === "verify-code-lanes") {
    runVerifyCodeLanes(flags, positionals.slice(1));
    return;
  }
  if (command === "decode-code-lanes") {
    runDecodeCodeLanes(flags, positionals.slice(1));
    return;
  }
  if (command === "code-languages") {
    runCodeLanguages(flags);
    return;
  }
  if (command === "code-ir") {
    runCodeIr(flags, positionals);
    return;
  }
  if (command === "injection-plan") {
    runInjectionPlan(flags, positionals);
    return;
  }
  if (command === "code-verify") {
    runCodeVerify(flags, positionals);
    return;
  }
  if (command === "code-translate") {
    runCodeTranslate(flags, positionals);
    return;
  }
  if (command === "calc") {
    runCalc(flags, positionals);
    return;
  }
  if (command === "dimensions") {
    runDimensions(flags, positionals);
    return;
  }
  if (command === "web-search") {
    await runWebSearch(flags, positionals);
    return;
  }
  if (command === "url-fetch") {
    await runUrlFetch(flags, positionals);
    return;
  }
  if (command === "materials") {
    await runMaterials(flags, positionals);
    return;
  }
  if (command === "toolbox") {
    runToolbox(flags);
    return;
  }
  if (command === "terminal-ui" || command === "ui") {
    await runTerminalUi(flags);
    return;
  }
  if (command === "agent-bus-ui") {
    await runAgentBusUi(flags);
    return;
  }
  if (command === "agent-bus-server") {
    await runAgentBusServer(flags);
    return;
  }
  if (command === "agent-bus-send") {
    await runAgentBusSend(flags);
    return;
  }

  const explicitBase = apiBase(flags);
  if (explicitBase && COMMAND_MAP[command]) {
    await runApi(command, flags, { resolvedBase: explicitBase, autoContext: null });
    return;
  }

  if (!explicitBase && COMMAND_MAP[command] && !LOCAL_PASSTHROUGH_COMMANDS.has(command)) {
    const active = resolveActiveServiceBase(flags);
    if (active) {
      process.stderr.write(
        `[geoseal] using detected service at ${active.apiBase} (pid ${active.pid}) — set SCBE_GEOSEAL_AUTODETECT=0 to disable\n`
      );
      await runApi(command, flags, { resolvedBase: active.apiBase, autoContext: active });
      return;
    }
    const payload = {
      ok: false,
      error: "api_command_requires_service",
      command,
      message: `${command} is a GeoSeal API command. Start a service or pass --api-base.`,
      fixes: [
        "geoseal service --detach --allow-demo-keys --probe-health --json",
        `geoseal ${command} --api-base http://127.0.0.1:8002 --json`,
        "geoseal doctor --json",
      ],
    };
    writeJsonOrText(flags, payload, `${payload.message}\nTry: ${payload.fixes[2]}`);
    process.exitCode = 2;
    return;
  }

  runPythonPassthrough(argv);
}

main().catch((err) => {
  process.stderr.write(`${err && err.message ? err.message : String(err)}\n`);
  process.exit(1);
});
