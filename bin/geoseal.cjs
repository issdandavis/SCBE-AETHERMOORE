#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
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
};

const LOCAL_PASSTHROUGH_COMMANDS = new Set(["portal-box", "stream-wheel", "shell"]);

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
    "status",
    "chat",
    ...Object.keys(COMMAND_MAP).filter((name) => name !== "status" && name !== "chat"),
    "service",
    "service-status",
    "service-stop",
    "agent-io-contract",
    "tokenizer-code-lanes",
    "verify-code-lanes",
    "decode-code-lanes",
    "ai2ai-bridge",
    "code-packet",
    "explain-route",
    "backend-registry",
    "history",
    "replay",
    "testing-cli",
    "project-scaffold",
    "code-roundtrip",
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
