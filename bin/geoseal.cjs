#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { spawnSync } = require("child_process");

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
  geoseal toolbox --json

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

function parseTongues(flags) {
  const raw = String(flags.tongues || flags.tongue || "KO");
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
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

function runToolbox(flags) {
  const payload = {
    schema_version: "geoseal_toolbox_v1",
    ok: true,
    purpose: "Small-agent mechanical tool surface for local verification, web lookup, code transport, and API routing.",
    local_tools: [
      { command: "calc", purpose: "Safe arithmetic with constants and math functions.", example: 'geoseal calc --expr "sqrt(2)^2 + phi" --json' },
      { command: "dimensions", purpose: "Dimensional analysis over SI base and common derived units.", example: 'geoseal dimensions --unit "kg*m/s^2" --json' },
      { command: "tokenizer-code-lanes", purpose: "Encode code commands into tongue-scoped binary/hex lanes.", example: "geoseal tokenizer-code-lanes --command shl --tongues KO,AV --json" },
      { command: "verify-code-lanes", purpose: "Verify tokenizer lane packets.", example: "geoseal verify-code-lanes --input-file lanes.json --json" },
      { command: "decode-code-lanes", purpose: "Decode tokenizer lane packets to text/binary artifacts.", example: "geoseal decode-code-lanes --input-file lanes.json --write-binary --json" },
    ],
    network_tools: [
      { command: "web-search", purpose: "Public no-key web search via DuckDuckGo Instant Answer.", example: 'geoseal web-search --query "site:docs.python.org pathlib" --json' },
      { command: "url-fetch", purpose: "Fetch and hash public HTTP/HTTPS content previews.", example: "geoseal url-fetch --url https://example.com --json" },
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
    "ai2ai-bridge",
    "calc",
    "dimensions",
    "web-search",
    "url-fetch",
    "toolbox",
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
  const command = positionals[0];

  if (!command || command === "help" || flags.help) {
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
  if (command === "toolbox") {
    runToolbox(flags);
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
