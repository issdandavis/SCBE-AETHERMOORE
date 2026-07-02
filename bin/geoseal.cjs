#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { spawn, spawnSync } = require("child_process");

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
       python -m src.geoseal_cli
     Use SCBE_GEOSEAL_PYTHON to pin the Python executable.

Hosted run path:
  Local/npm/Ollama-first use stays free under the open-source license.
  For AetherMoore-hosted routing, governed reports, benchmarks, storage,
  delivery, or provider/model-backed work:
    https://aethermoore.com/SCBE-AETHERMOORE/hosted-run.html
    https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html
  Service credits pass through provider/model cost with a 2-5% SCBE fee.

Useful commands:
  geoseal doctor --json
  geoseal providers --json
  geoseal lanes --json
  geoseal rooms
  geoseal rooms --room frontend --json
  geoseal stage "route task through atomize verify export"
  geoseal stage --room frontend --mode learn --diagram flow --content "component -> style -> test"
  geoseal stage --room frontend --example slideshow
  geoseal stage-frame --room github --example pr-flow
  geoseal command-check "Remove-Item -Recurse C:\\Users\\issda"
  geoseal powershell profiles --json
  geoseal powershell check --command "Get-Location" --json
  geoseal powershell run --command "Write-Output GEOSEAL_OK" --json
  geoseal powershell run --profile pwd --json
  geoseal powershell run --profile pwd --write-receipt --json
  geoseal powershell receipts --json
  geoseal code-cube "build a todo app with auth and tests" --json
  geoseal code-cube --twist tests.backend --language rust "todo api" --json
  geoseal code-cube --target manifold --dimensions 6 --twist security.deploy "station safe-mode controller" --json
  geoseal code-cube --target manifold --pitch 15 --yaw -20 --roll 5 --speed 0.7 "safe-mode controller" --json
  geoseal ask "explain this repo"
  geoseal do "add tests for the tokenizer"
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
  geoseal tokenizer-code-lanes --command shl --tongues all --output artifacts/tokenizer_code_lanes/shl_lanes.json
  geoseal verify-code-lanes "$(cat artifacts/tokenizer_code_lanes/shl_lanes.json)" --json
  geoseal decode-code-lanes "$(cat artifacts/tokenizer_code_lanes/shl_lanes.json)" --output-dir artifacts/tokenizer_code_lanes/decoded --from-binary --write-binary --json
  geoseal bits "hello"
  geoseal hex "hello"
  geoseal trits "hello"
  geoseal systems --json
  geoseal system-map --json
  geoseal system-map --check
  geoseal system-map watch --interval 30
  geoseal aethermon-adapter build --json
  geoseal aethermon-adapter preflight --json
  geoseal aethermon-adapter eval --mode oracle --json
  geoseal aethermon-adapter oracle --json
  geoseal aethermon-adapter abstain --json
  geoseal inc 1111
  geoseal map "release payload after compare" --json
  geoseal spine encode "hello" --json
  geoseal spine map "release payload after compare" --json
  geoseal spine decode --from hex 68656c6c6f --json
  geoseal spine templates --json
  geoseal ai2ai-bridge --content "def add(a, b): return a + b" --language python --json
  geoseal code-packet --content "def add(a, b): return a + b" --language python
  geoseal tongue-compile --content "ko:set r0, 2" --json
  geoseal tongue-run --content "ko:set r0, 2\nko:print r0\nko:halt" --json
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
  "code-packet": { method: "POST", path: "/v1/geoseal/code-packet", auth: false },
  "explain-route": { method: "POST", path: "/v1/geoseal/explain-route", auth: false },
  "backend-registry": { method: "POST", path: "/v1/geoseal/backend-registry", auth: false },
  "agent-harness": { method: "POST", path: "/v1/geoseal/agent-harness", auth: false },
  history: { method: "POST", path: "/v1/geoseal/history", auth: false },
  replay: { method: "POST", path: "/v1/geoseal/replay", auth: false },
  "testing-cli": { method: "POST", path: "/v1/geoseal/testing-cli", auth: false },
  "project-scaffold": { method: "POST", path: "/v1/geoseal/project-scaffold", auth: false },
  "code-roundtrip": { method: "POST", path: "/v1/geoseal/code-roundtrip", auth: false },
};

const LOCAL_PASSTHROUGH_COMMANDS = new Set(["portal-box", "stream-wheel", "shell"]);
const SCBE_SPINE_COMMANDS = new Set([
  "spine",
  "bits",
  "hex",
  "trits",
  "inc",
  "templates",
  "map",
  "substrate",
  "systems",
  "code-systems",
]);
const CUSTOM_COMMANDS_DIR = path.join(ROOT, ".geoseal", "commands");
const AETHERMON_ADAPTER_PROFILE = "config/model_training/aethermon-agent-adapter-v0-local.json";
const GEOSEAL_POWERSHELL_RECEIPTS_DIR = path.join(ROOT, "artifacts", "geoseal_powershell_receipts");
const MAX_POWERSHELL_COMMAND_CHARS = 900;
const POWERSHELL_TIMEOUT_MS = 45000;
const POWERSHELL_ALLOWED_COMMANDS = new Set([
  "convertto-json",
  "get-childitem",
  "get-command",
  "get-content",
  "get-date",
  "get-host",
  "get-item",
  "get-location",
  "get-process",
  "get-service",
  "measure-object",
  "resolve-path",
  "select-object",
  "select-string",
  "sort-object",
  "test-path",
  "write-output",
]);
const POWERSHELL_BLOCKED_PATTERNS = Object.freeze([
  /\bRemove-Item\b/i,
  /\bSet-Item\b/i,
  /\bSet-Content\b/i,
  /\bAdd-Content\b/i,
  /\bOut-File\b/i,
  /\bNew-Item\b/i,
  /\bMove-Item\b/i,
  /\bCopy-Item\b/i,
  /\bRename-Item\b/i,
  /\bInvoke-Expression\b/i,
  /\biex\b/i,
  /\bInvoke-WebRequest\b/i,
  /\bInvoke-RestMethod\b/i,
  /\bStart-Process\b/i,
  /\bStop-Process\b/i,
  /\bSet-ExecutionPolicy\b/i,
  /\bRemove-Module\b/i,
  /\bImport-Module\b/i,
  /\bFormat-Volume\b/i,
  /\bdiskpart\b/i,
  /\bshutdown\b/i,
  /\brestart-computer\b/i,
  /\bstop-computer\b/i,
  /\bgit\s+(reset|clean|push|pull|merge|rebase)\b/i,
  /\b(?:rm|del|erase|rmdir|curl|wget|iwr|irm|ssh|scp)\b/i,
  />/,
  /</,
  /;/,
  /&&/,
  /\|\|/,
  /`/,
  /\$\(/,
  /@\(/,
  /\r|\n/,
]);
const POWERSHELL_PROFILES = Object.freeze({
  pwd: {
    label: "Working Directory",
    risk_tier: "bounded-host-read",
    description: "Print GeoSeal's repo working directory.",
    command: "Get-Location | Select-Object -ExpandProperty Path",
  },
  version: {
    label: "PowerShell Version",
    risk_tier: "bounded-host-read",
    description: "Print the local PowerShell version through Get-Host.",
    command: "Get-Host | Select-Object -ExpandProperty Version",
  },
  repo_files: {
    label: "Repo Files",
    risk_tier: "bounded-host-read",
    description: "List top-level repo entries without recursion.",
    command: "Get-ChildItem -Name",
  },
});

const STAGE_ROOMS = {
  frontend: {
    title: "Frontend Room",
    purpose: "Build UI, components, layouts, route pages, forms, slideshows, and media embeds.",
    examples: [
      "component -> state -> style -> responsive check",
      "landing page -> payment CTA -> proof section -> deploy route",
      "slideshow -> images -> captions -> keyboard controls",
    ],
    safeCommands: ["read_file", "write_file", "append_file", "make_dir", "copy"],
  },
  backend: {
    title: "Backend Room",
    purpose: "Build APIs, validation, storage, auth checks, receipts, and integration routes.",
    examples: [
      "request -> validate -> process -> receipt",
      "webhook -> verify signature -> store event -> report",
      "input schema -> handler -> tests -> deployment check",
    ],
    safeCommands: ["read_file", "write_file", "append_file", "run_shell"],
  },
  payments: {
    title: "Payments Room",
    purpose: "Add checkout links, pricing tables, webhooks, receipt pages, and delivery flows.",
    examples: [
      "offer -> checkout -> webhook -> delivery receipt",
      "pricing table -> payment link -> success page",
      "invoice request -> customer details -> manual follow-up",
    ],
    safeCommands: ["read_file", "write_file", "network_send"],
  },
  media: {
    title: "Media Room",
    purpose: "Add videos, image galleries, old-school projector slides, demos, and embeds.",
    examples: [
      "video embed -> transcript -> CTA",
      "slides -> scene notes -> export",
      "image set -> captions -> carousel controls",
    ],
    safeCommands: ["read_file", "write_file", "copy"],
  },
  cube: {
    title: "Cube Room",
    purpose: "Parse code in, hold binary/trit center, emit language faces, and show safety blocks.",
    examples: [
      "source -> parse cube -> bit spine -> emit rust",
      "workflow -> blocks -> safety verdict -> receipt",
      "opcode program -> language faces -> run output compare",
    ],
    safeCommands: ["read_file", "run_shell", "write_file"],
  },
  termux: {
    title: "Termux Room",
    purpose: "Build phone-friendly CLI flows, mobile scripts, local services, and sync handoffs.",
    examples: [
      "pkg check -> repo clone -> npm smoke -> stage output",
      "phone note -> command-check -> local script -> receipt",
      "termux api -> file output -> sync back to github",
    ],
    safeCommands: ["read_file", "run_shell", "write_file", "network_send"],
  },
  github: {
    title: "GitHub Room",
    purpose: "Plan branches, PRs, reviews, CI checks, release notes, and deploy handoffs.",
    examples: [
      "branch -> commit -> push -> pull request",
      "ci failure -> log read -> patch -> rerun",
      "product page -> preview deploy -> merge",
    ],
    safeCommands: ["read_file", "run_shell", "network_send"],
  },
};

const STAGE_EXAMPLES = {
  frontend: {
    slideshow: {
      mode: "build",
      diagram: "flow",
      content: "slides data -> image panel -> captions -> keyboard controls -> publish",
      frames: [
        "Create a slides data structure with title, image, caption, and CTA.",
        "Render one slide at a time inside a fixed stage box.",
        "Add previous, next, and keyboard controls.",
        "Run command-check before writing files or deploying.",
      ],
    },
    payment: {
      mode: "build",
      diagram: "flow",
      content: "offer -> checkout link -> success page -> delivery receipt",
      frames: [
        "Define the product offer and price.",
        "Add a visible checkout link or payment button.",
        "Create a success/delivery page.",
        "Record the receipt path for support.",
      ],
    },
  },
  media: {
    video: {
      mode: "demo",
      diagram: "projector",
      content: "video embed -> transcript -> captions -> call to action",
      frames: [
        "Place the video embed in a stable aspect-ratio frame.",
        "Add transcript and captions for users and search.",
        "Add one CTA below the video.",
      ],
    },
  },
  github: {
    "pr-flow": {
      mode: "ship",
      diagram: "flow",
      content: "branch -> commit -> push -> pull request -> checks -> merge",
      frames: [
        "Check status and isolate only the intended files.",
        "Commit one coherent change.",
        "Push the branch and open a PR with validation notes.",
        "Wait for checks before merge/deploy.",
      ],
    },
  },
  termux: {
    "mobile-smoke": {
      mode: "mobile",
      diagram: "flow",
      content: "pkg update -> clone repo -> install deps -> run smoke -> sync receipt",
      frames: [
        "Use Termux for lightweight smoke checks and command review.",
        "Run read-only checks before any write operation.",
        "Save receipts that can sync back to the repo.",
      ],
    },
  },
  cube: {
    polyglot: {
      mode: "build",
      diagram: "flow",
      content: "source -> parse cube -> bit spine -> language faces -> safety verdict",
      frames: [
        "Parse source into the cube input face.",
        "Hold the invariant in the bit/trit spine.",
        "Emit target language faces.",
        "Run blocks safety before any file mutation.",
      ],
    },
  },
};

function stageExample(roomId, exampleId) {
  const roomExamples = STAGE_EXAMPLES[roomId] || {};
  const selectedId = exampleId ? String(exampleId).toLowerCase() : "";
  if (!selectedId) return { id: "", example: null };
  return { id: selectedId, example: roomExamples[selectedId] || null };
}

function availableStageExamples(roomId) {
  return Object.keys(STAGE_EXAMPLES[roomId] || {});
}

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

function terminalWidth(flags) {
  const raw = Number(flags.width || process.env.COLUMNS || process.stdout.columns || 88);
  return Math.max(48, Math.min(140, Number.isFinite(raw) ? raw : 88));
}

function stripAnsi(text) {
  return String(text).replace(/\x1b\[[0-9;]*m/g, "");
}

function visibleLength(text) {
  return stripAnsi(text).length;
}

function truncateVisible(text, width) {
  const clean = stripAnsi(text);
  if (clean.length <= width) return text;
  if (width <= 1) return "…";
  return `${clean.slice(0, width - 1)}…`;
}

function wrapText(text, width) {
  const words = String(text || "").replace(/\s+/g, " ").trim().split(" ").filter(Boolean);
  if (!words.length) return [""];
  const lines = [];
  let line = "";
  for (const word of words) {
    if (!line) {
      line = word;
      continue;
    }
    if (visibleLength(`${line} ${word}`) <= width) {
      line = `${line} ${word}`;
    } else {
      lines.push(line);
      line = word;
    }
  }
  if (line) lines.push(line);
  return lines.flatMap((item) => {
    const clean = stripAnsi(item);
    if (clean.length <= width) return [item];
    const chunks = [];
    for (let i = 0; i < clean.length; i += width) chunks.push(clean.slice(i, i + width));
    return chunks;
  });
}

function boxLine(left, fill, right, width) {
  return `${left}${fill.repeat(Math.max(0, width - 2))}${right}`;
}

function boxed(title, lines, width) {
  const inner = width - 4;
  const safeTitle = title ? ` ${truncateVisible(title, Math.max(0, inner - 2))} ` : "";
  const topFill = Math.max(0, width - 2 - visibleLength(safeTitle));
  const top = `┌${safeTitle}${"─".repeat(topFill)}┐`;
  const body = lines.flatMap((line) => wrapText(line, inner)).map((line) => {
    const clipped = truncateVisible(line, inner);
    return `│ ${clipped}${" ".repeat(Math.max(0, inner - visibleLength(clipped)))} │`;
  });
  return [top, ...body, boxLine("└", "─", "┘", width)];
}

function stageDiagram(kind, content, innerWidth) {
  const clean = String(content || "").trim();
  if (kind === "projector") {
    const beam = Math.max(8, Math.floor(innerWidth / 3));
    return [
      "   _______",
      "  / _____ \\",
      " | |     | |" + " ".repeat(Math.max(1, beam - 10)) + "╲",
      " | |_____| |" + " ".repeat(Math.max(1, beam - 12)) + " ╲  " + truncateVisible(clean || "projected state", Math.max(12, innerWidth - beam - 8)),
      "  \\_______/" + " ".repeat(Math.max(1, beam - 10)) + "╱",
    ];
  }
  if (kind === "flow" || clean.includes("->")) {
    const parts = clean
      .split(/->|=>|→/)
      .map((part) => part.trim())
      .filter(Boolean)
      .slice(0, 6);
    if (parts.length >= 2) {
      const nodeWidth = Math.max(8, Math.min(18, Math.floor((innerWidth - (parts.length - 1) * 4) / parts.length)));
      const nodes = parts.map((part) => `[${truncateVisible(part, nodeWidth - 2).padEnd(nodeWidth - 2, " ")}]`);
      return [nodes.join(" -> ")];
    }
  }
  return wrapText(clean || "No stage content supplied.", innerWidth);
}

function runStage(positionals, flags) {
  const roomId = String(flags.room || "stage").toLowerCase();
  const { id: exampleId, example } = stageExample(roomId, flags.example);
  const jsonCarriedContent = typeof flags.json === "string" ? flags.json : "";
  const content = String(flags.content || flags.message || jsonCarriedContent || positionals.slice(1).join(" ") || (example ? example.content : "")).trim();
  const room = STAGE_ROOMS[roomId];
  const mode = String(flags.mode || (example ? example.mode : "") || "conversation").toLowerCase();
  const title = String(flags.title || (room ? room.title : "GeoSeal Terminal Stage"));
  const diagram = String(flags.diagram || (example ? example.diagram : "") || (content.includes("->") ? "flow" : "projector"));
  const width = terminalWidth(flags);
  const innerWidth = width - 4;
  const hasRouteSeparators = /->|=>|→/.test(content);
  const routeTokens = content
    ? content
        .toLowerCase()
        .split(hasRouteSeparators ? /->|=>|→/ : /\s+/)
        .map((part) => part.trim())
        .filter(Boolean)
        .slice(0, 5)
    : [];
  const route = routeTokens.length ? routeTokens.join(" → ") : "input → route → receipt";
  const payload = {
    schema_version: "geoseal_terminal_stage_v1",
    ok: true,
    title,
    room: roomId,
    example: exampleId || null,
    mode,
    diagram,
    width,
    content,
    route_hint: route,
    panels: ["signal", "stage", "receipt"],
    room_context: room || null,
    available_examples: availableStageExamples(roomId),
    frames: example ? example.frames : [],
  };
  const lines = [
    ...boxed(title, [
      `mode: ${mode}`,
      room ? room.purpose : "AI terminal projector: signal, stage, receipt.",
    ], width),
    "",
    ...boxed("signal", [content || "Pass text with: geoseal stage \"input -> route -> receipt\""], width),
    "",
    ...boxed("stage", stageDiagram(diagram, content || "input -> route -> receipt", innerWidth), width),
    "",
    ...boxed("receipt", [
      `route: ${route}`,
      example ? `example: ${exampleId} (${example.frames.length} frames)` : `examples: ${availableStageExamples(roomId).join(", ") || "none"}`,
      room ? `room examples: ${room.examples.slice(0, 2).join(" | ")}` : "next: use --json for machine output or --diagram flow/projector",
      `safety: run geoseal command-check before shell execution`,
    ], width),
  ];
  writeJsonOrText(flags, payload, lines.join("\n"));
}

function runStageFrame(positionals, flags) {
  const roomId = String(flags.room || "frontend").toLowerCase();
  const room = STAGE_ROOMS[roomId];
  const { id: exampleId, example } = stageExample(roomId, flags.example);
  const jsonCarriedContent = typeof flags.json === "string" ? flags.json : "";
  const customContent = String(flags.content || flags.message || jsonCarriedContent || positionals.slice(1).join(" ")).trim();
  const content = customContent || (example ? example.content : "");
  const frames = example
    ? example.frames
    : wrapText(content || "Start with a goal, produce one visible step, run command-check, then record a receipt.", 62);
  const width = terminalWidth(flags);
  const hasRouteSeparators = /->|=>/.test(content);
  const routeTokens = content
    ? content
        .toLowerCase()
        .split(hasRouteSeparators ? /->|=>/ : /\s+/)
        .map((part) => part.trim())
        .filter(Boolean)
        .slice(0, 6)
    : [];
  const route = routeTokens.length ? routeTokens.join(" -> ") : "frame 1 -> command-check -> receipt";
  const payload = {
    schema_version: "geoseal_stage_frame_v1",
    ok: Boolean(room && (!exampleId || example)),
    room: roomId,
    room_context: room || null,
    example: exampleId || null,
    available_examples: availableStageExamples(roomId),
    content,
    route_hint: route,
    frames: frames.map((text, index) => ({
      index: index + 1,
      title: `frame ${String(index + 1).padStart(2, "0")}`,
      text,
    })),
    safety: {
      preflight: "Run geoseal command-check before shell execution.",
      destructive_scope: "home, drive root, system, and cloud-sync destructive commands are refused.",
    },
  };
  if (!room) {
    payload.error = "unknown_room";
    payload.available = Object.keys(STAGE_ROOMS);
  } else if (exampleId && !example) {
    payload.error = "unknown_example";
  }
  const frameLines = [
    ...boxed(room ? `${room.title} Stage Frames` : "Unknown Stage Room", [
      room ? room.purpose : `available rooms: ${Object.keys(STAGE_ROOMS).join(", ")}`,
      example ? `example: ${exampleId}` : `available examples: ${availableStageExamples(roomId).join(", ") || "none"}`,
      `route: ${route}`,
    ], width),
    "",
    ...frames.flatMap((frame, index) => boxed(`frame ${String(index + 1).padStart(2, "0")}`, [
      frame,
      index === frames.length - 1 ? "receipt: save output, tests, and next command-check." : "next: continue inside this room.",
    ], width).concat("")),
    ...boxed("safety", [
      "Preflight shell commands with: geoseal command-check \"...\"",
      "Blocked: destructive commands against home, root, system, or cloud-sync scopes.",
    ], width),
  ];
  writeJsonOrText(flags, payload, frameLines.join("\n"));
  if (!payload.ok) process.exitCode = 2;
}

function runRooms(flags) {
  const roomId = flags.room ? String(flags.room).toLowerCase() : "";
  const rooms = Object.entries(STAGE_ROOMS).map(([id, room]) => ({ id, ...room }));
  const selected = roomId ? rooms.find((room) => room.id === roomId) : null;
  const payload = {
    schema_version: "geoseal_stage_rooms_v1",
    ok: Boolean(!roomId || selected),
    selected: selected || null,
    rooms,
  };
  if (roomId && !selected) {
    payload.error = "unknown_room";
    payload.available = rooms.map((room) => room.id);
  }
  const lines = selected
    ? boxed(selected.title, [
        selected.purpose,
        `examples: ${selected.examples.join(" | ")}`,
        `safe blocks: ${selected.safeCommands.join(", ")}`,
      ], terminalWidth(flags))
    : rooms.flatMap((room) => boxed(`${room.id}: ${room.title}`, [room.purpose, `try: geoseal stage --room ${room.id} --mode learn "..."`], terminalWidth(flags)).concat(""));
  writeJsonOrText(flags, payload, lines.join("\n"));
  if (roomId && !selected) process.exitCode = 2;
}

function commandRisk(commandText) {
  const text = String(commandText || "").trim();
  const lower = text.toLowerCase();
  const reasons = [];
  let decision = "allow";
  let safety = "safe";

  const hostControlPatterns = [
    /\bwsl(?:\.exe)?\b.*(?:\s|^)--shutdown\b/i,
    /\b(?:shutdown|restart-computer|stop-computer|poweroff|reboot)\b/i,
    /\bpowercfg\b.*\b(?:hibernate|standby|sleep|h(?:ibernate)?\s+(?:on|off)|-h\s+(?:on|off))\b/i,
    /\b(?:bcdedit|diskpart|format|manage-bde|reagentc)\b/i,
    /\b(?:disable-netadapter|restart-netadapter|enable-netadapter|netsh)\b/i,
    /\bdocker\b\s+system\s+prune\b.*(?:\s-a\b|\s--all\b)/i,
    /\btaskkill\b.*(?:\s\/f\b|\s\/t\b).*(?:\s\/im\s+\*|\s\/pid\s+0\b|python\.exe|node\.exe|code\.exe)/i,
    /\bstop-process\b.*(?:-force|\s-id\s+0\b|-name\s+\*|python|node|code)/i,
    /\b(?:stress|stress-ng|sysbench)\b|\bwhile\s+(?:true\b|\(\s*\$true\s*\))/i,
  ];
  const destructivePatterns = [
    /\brm\s+(-[a-z]*r[a-z]*f|-rf|-fr)\b/i,
    /\bremove-item\b.*(?:\s|^)-recurse\b/i,
    /\bdel(?:ete)?\b.*\b\/s\b/i,
    /\bformat\b/i,
    /\bdrop\s+table\b/i,
    /\bwipe\b/i,
    /\btruncate\b/i,
    /\bgit\s+reset\s+--hard\b/i,
    /\bgit\s+clean\b.*\b-[a-z]*f/i,
  ];
  const protectedScopes = [
    /(^|\s|["'])\/($|\s|["'])/,
    /c:\\($|\s|["'])/i,
    /c:\\windows/i,
    /c:\\users\\issda($|\\|\s|["'])/i,
    /system32/i,
    /program files/i,
    /\bonedrive\b/i,
  ];
  const networkPatterns = [/\bcurl\b/i, /\binvoke-webrequest\b/i, /\bwget\b/i, /\bssh\b/i, /\bscp\b/i, /\bgh\s+pr\s+merge\b/i, /\bgh\s+release\b/i];
  const writePatterns = [/\bset-content\b/i, /\badd-content\b/i, />\s*[^&]/, /\bmove-item\b/i, /\bcopy-item\b/i, /\bgit\s+push\b/i, /\bnpm\s+publish\b/i];

  if (!text) {
    return { decision: "block", safety: "missing", reasons: ["No command supplied."] };
  }
  if (hostControlPatterns.some((pattern) => pattern.test(text))) {
    decision = "block";
    safety = "refused";
    reasons.push("Command controls host power, boot, disk, network, VM, process, or stress state.");
  }
  if (destructivePatterns.some((pattern) => pattern.test(text))) {
    if (decision !== "block") {
      decision = "confirm";
      safety = "destructive";
    }
    reasons.push("Command matches a destructive operation pattern.");
  }
  if (protectedScopes.some((pattern) => pattern.test(text))) {
    decision = "block";
    safety = "refused";
    reasons.push("Command targets a protected drive, home, cloud-sync, or system scope.");
  }
  if (decision === "allow" && networkPatterns.some((pattern) => pattern.test(text))) {
    decision = "confirm";
    safety = "network";
    reasons.push("Command can transmit data or change remote state.");
  }
  if (decision === "allow" && writePatterns.some((pattern) => pattern.test(text))) {
    decision = "confirm";
    safety = "write";
    reasons.push("Command writes, moves, publishes, or mutates files/state.");
  }
  if (!reasons.length) reasons.push("No destructive, protected-scope, write, or network pattern detected.");
  return { decision, safety, reasons };
}

function runCommandCheck(positionals, flags) {
  const jsonCarriedCommand = typeof flags.json === "string" ? flags.json : "";
  const commandText = String(flags.command || flags.content || jsonCarriedCommand || positionals.slice(1).join(" ")).trim();
  const risk = commandRisk(commandText);
  const payload = {
    schema_version: "geoseal_command_preflight_v1",
    ok: risk.decision === "allow",
    command: commandText,
    ...risk,
    guidance:
      risk.decision === "allow"
        ? "Allowed for low-risk execution."
        : risk.decision === "confirm"
          ? "Require explicit human confirmation and a reason before execution."
          : "Refuse execution. Change the target or use a non-destructive plan.",
  };
  const icon = risk.decision === "allow" ? "ALLOW" : risk.decision === "confirm" ? "CONFIRM" : "BLOCK";
  const lines = boxed("command preflight", [
    `${icon}: ${risk.safety}`,
    `command: ${commandText || "<none>"}`,
    ...risk.reasons.map((reason) => `reason: ${reason}`),
    payload.guidance,
  ], terminalWidth(flags));
  writeJsonOrText(flags, payload, lines.join("\n"));
  if (risk.decision === "block") process.exitCode = 2;
  if (risk.decision === "confirm") process.exitCode = 3;
}

function powershellExecutables() {
  const executables = [];
  if (process.env.SCBE_GEOSEAL_POWERSHELL) executables.push(process.env.SCBE_GEOSEAL_POWERSHELL);
  if (process.platform === "win32") executables.push("powershell.exe", "powershell");
  executables.push("pwsh", "powershell");
  return [...new Set(executables.filter(Boolean))];
}

function redactedPowerShellProfiles() {
  return Object.entries(POWERSHELL_PROFILES).map(([id, profile]) => ({
    id,
    label: profile.label,
    risk_tier: profile.risk_tier,
    description: profile.description,
  }));
}

function validatePowerShellCommand(command) {
  const text = String(command || "").trim();
  if (!text) return { ok: false, decision: "block", safety: "missing", reasons: ["No PowerShell command supplied."] };
  if (text.length > MAX_POWERSHELL_COMMAND_CHARS) {
    return {
      ok: false,
      decision: "block",
      safety: "too_long",
      reasons: [`PowerShell command too long (${text.length} chars).`],
    };
  }
  for (const pattern of POWERSHELL_BLOCKED_PATTERNS) {
    if (pattern.test(text)) {
      return {
        ok: false,
        decision: "block",
        safety: "blocked_pattern",
        reasons: [`PowerShell command blocked by safety pattern: ${pattern}`],
      };
    }
  }

  const segments = text.split("|").map((segment) => segment.trim()).filter(Boolean);
  if (!segments.length) {
    return { ok: false, decision: "block", safety: "missing", reasons: ["No executable PowerShell segment supplied."] };
  }
  const commands = [];
  for (const segment of segments) {
    const match = segment.match(/^([A-Za-z][A-Za-z0-9-]*)\b/);
    const cmdlet = match ? match[1].toLowerCase() : "";
    if (!cmdlet || !POWERSHELL_ALLOWED_COMMANDS.has(cmdlet)) {
      return {
        ok: false,
        decision: "block",
        safety: "not_allowlisted",
        reasons: [`PowerShell segment is not allowlisted: ${segment}`],
      };
    }
    commands.push(cmdlet);
  }
  const genericRisk = commandRisk(text);
  if (genericRisk.decision === "block") {
    return { ok: false, ...genericRisk };
  }
  return {
    ok: true,
    command: text,
    decision: "allow",
    safety: "bounded-host-read",
    reasons: ["All pipeline segments use allowlisted read-only PowerShell commands."],
    commands,
  };
}

function tailText(value, limit = 8192) {
  const text = String(value || "");
  return text.length > limit ? text.slice(text.length - limit) : text;
}

function relRepoPath(absPath) {
  try {
    return path.relative(ROOT, absPath).replace(/\\/g, "/");
  } catch (_err) {
    return String(absPath);
  }
}

function resolvePowerShellReceiptDir(flags) {
  const raw = flags["receipt-dir"] || process.env.SCBE_GEOSEAL_POWERSHELL_RECEIPTS_DIR;
  const resolved = raw ? path.resolve(ROOT, String(raw)) : GEOSEAL_POWERSHELL_RECEIPTS_DIR;
  const rootResolved = ROOT;
  if (resolved !== rootResolved && !resolved.startsWith(`${rootResolved}${path.sep}`)) {
    throw new Error(`PowerShell receipt dir must stay inside repo root: ${resolved}`);
  }
  return resolved;
}

function shouldWritePowerShellReceipt(flags) {
  return Boolean(flags["write-receipt"] || flags.receipt || flags["receipt-dir"]);
}

function writePowerShellReceipt(payload, flags) {
  if (!shouldWritePowerShellReceipt(flags)) return payload;
  const receiptDir = resolvePowerShellReceiptDir(flags);
  fs.mkdirSync(receiptDir, { recursive: true });
  const timestamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\..*/, "Z");
  const digest = String(payload.command_digest || crypto.createHash("sha256").update(JSON.stringify(payload)).digest("hex")).slice(0, 12);
  const receiptPath = path.join(receiptDir, `${timestamp}_${digest}.json`);
  const withPath = {
    ...payload,
    receipt_path: relRepoPath(receiptPath),
  };
  fs.writeFileSync(receiptPath, `${JSON.stringify(withPath, null, 2)}\n`, "utf8");
  return withPath;
}

function runPowerShellReceipts(flags) {
  const receiptDir = resolvePowerShellReceiptDir(flags);
  const limit = Math.max(1, Math.min(200, Number(flags.limit || 25) || 25));
  const files = fs.existsSync(receiptDir)
    ? fs
        .readdirSync(receiptDir)
        .filter((name) => name.endsWith(".json"))
        .map((name) => {
          const receiptPath = path.join(receiptDir, name);
          const stat = fs.statSync(receiptPath);
          return {
            file: relRepoPath(receiptPath),
            bytes: stat.size,
            modified_at: stat.mtime.toISOString(),
          };
        })
        .sort((a, b) => String(b.modified_at).localeCompare(String(a.modified_at)))
        .slice(0, limit)
    : [];
  const payload = {
    schema_version: "geoseal_powershell_receipts_v1",
    ok: true,
    receipt_dir: relRepoPath(receiptDir),
    count: files.length,
    receipts: files,
  };
  const text = files.length ? files.map((item) => `${item.modified_at} ${item.file}`).join("\n") : "No PowerShell receipts found.";
  writeJsonOrText(flags, payload, text);
}

function runPowerShellProfiles(flags) {
  const payload = {
    schema_version: "geoseal_powershell_profiles_v1",
    ok: true,
    default_profile: "pwd",
    ad_hoc_profile: {
      id: "read-only-command",
      risk_tier: "bounded-host-read",
      allowed_commands: [...POWERSHELL_ALLOWED_COMMANDS].sort(),
      max_chars: MAX_POWERSHELL_COMMAND_CHARS,
    },
    profiles: redactedPowerShellProfiles(),
  };
  const text = payload.profiles.map((profile) => `${profile.id}: ${profile.description}`).join("\n");
  writeJsonOrText(flags, payload, text);
}

function runPowerShellCheck(commandText, flags) {
  const validation = validatePowerShellCommand(commandText);
  const payload = {
    schema_version: "geoseal_powershell_check_v1",
    ok: validation.ok,
    command: String(commandText || "").trim(),
    ...validation,
  };
  writeJsonOrText(flags, payload, validation.ok ? "PowerShell command allowed." : validation.reasons.join("\n"));
  if (!validation.ok) process.exitCode = 2;
}

function runPowerShellExecution(commandText, flags, source) {
  const validation = validatePowerShellCommand(commandText);
  const startedAt = new Date().toISOString();
  const baseReceipt = {
    schema_version: "geoseal_powershell_run_v1",
    command_id: "powershell:bounded-read",
    source,
    profile: source.profile || null,
    command: String(commandText || "").trim(),
    command_digest: crypto.createHash("sha256").update(String(commandText || ""), "utf8").digest("hex"),
    cwd: ROOT,
    risk_tier: validation.ok ? "bounded-host-read" : "blocked",
    started_at: startedAt,
  };
  if (!validation.ok) {
    const payload = writePowerShellReceipt({
      ok: false,
      ...baseReceipt,
      ...validation,
      exit_code: 126,
      finished_at: new Date().toISOString(),
      stdout_tail: "",
      stderr_tail: validation.reasons.join("\n"),
    }, flags);
    writeJsonOrText(flags, payload, payload.stderr_tail);
    process.exitCode = 2;
    return;
  }

  const timeoutMs = Math.max(1000, Math.min(300000, Number(flags.timeout || POWERSHELL_TIMEOUT_MS) || POWERSHELL_TIMEOUT_MS));
  for (const executable of powershellExecutables()) {
    const result = spawnSync(
      executable,
      ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", validation.command],
      {
        cwd: ROOT,
        env: process.env,
        encoding: "utf8",
        shell: false,
        timeout: timeoutMs,
      }
    );
    if (result.error && result.error.code === "ENOENT") continue;
    const exitCode = result.error ? 1 : result.status === null ? 1 : result.status;
    const payload = writePowerShellReceipt({
      ok: exitCode === 0,
      ...baseReceipt,
      executable,
      decision: validation.decision,
      safety: validation.safety,
      reasons: validation.reasons,
      allowed_commands: validation.commands,
      exit_code: exitCode,
      signal: result.signal || null,
      error: result.error ? String(result.error.message || result.error) : null,
      finished_at: new Date().toISOString(),
      stdout_tail: tailText(result.stdout),
      stderr_tail: tailText(result.stderr),
    }, flags);
    writeJsonOrText(flags, payload, payload.stdout_tail || payload.stderr_tail || `PowerShell exit ${exitCode}`);
    if (exitCode !== 0) process.exitCode = exitCode;
    return;
  }

  const payload = writePowerShellReceipt({
    ok: false,
    ...baseReceipt,
    executable: null,
    exit_code: 127,
    finished_at: new Date().toISOString(),
    stdout_tail: "",
    stderr_tail: "No PowerShell executable found. Set SCBE_GEOSEAL_POWERSHELL if needed.",
  }, flags);
  writeJsonOrText(flags, payload, payload.stderr_tail);
  process.exitCode = 127;
}

function runPowerShell(positionals, flags) {
  const action = String(positionals[1] || "profiles").toLowerCase();
  if (action === "profiles" || action === "list") {
    runPowerShellProfiles(flags);
    return;
  }
  if (action === "receipts" || action === "history") {
    runPowerShellReceipts(flags);
    return;
  }

  const profileId = String(flags.profile || "").trim();
  const profile = profileId ? POWERSHELL_PROFILES[profileId] : null;
  if (profileId && !profile) {
    writeJsonOrText(
      flags,
      {
        schema_version: "geoseal_powershell_error_v1",
        ok: false,
        error: "unknown_powershell_profile",
        profile: profileId,
        profiles: redactedPowerShellProfiles(),
      },
      `Unknown PowerShell profile: ${profileId}`
    );
    process.exitCode = 2;
    return;
  }

  const positionalCommand = positionals.slice(2).join(" ").trim();
  const commandText = String(flags.command || flags.content || (profile ? profile.command : positionalCommand)).trim();
  if (action === "check") {
    runPowerShellCheck(commandText, flags);
    return;
  }
  if (action === "run" || action === "exec") {
    runPowerShellExecution(commandText, flags, {
      kind: profile ? "profile" : "ad_hoc",
      profile: profileId || null,
    });
    return;
  }

  writeJsonOrText(
    flags,
    {
      schema_version: "geoseal_powershell_error_v1",
      ok: false,
      error: "unknown_powershell_action",
      action,
      actions: ["profiles", "check", "run", "receipts"],
    },
    `Unknown PowerShell action: ${action}`
  );
  process.exitCode = 2;
}

const CODE_CUBE_FACES = {
  frontend: {
    color: "blue",
    role: "user interface",
    outputs: ["routes", "components", "state", "responsive checks"],
  },
  backend: {
    color: "green",
    role: "api and domain logic",
    outputs: ["handlers", "validation", "service functions", "receipts"],
  },
  data: {
    color: "violet",
    role: "schema and persistence",
    outputs: ["entities", "relations", "indexes", "seed records"],
  },
  tests: {
    color: "yellow",
    role: "verification",
    outputs: ["unit tests", "route tests", "safety tests", "smoke tests"],
  },
  security: {
    color: "red",
    role: "permission and command gates",
    outputs: ["risk flags", "preflight checks", "secret boundaries", "deny rules"],
  },
  deploy: {
    color: "orange",
    role: "ship path",
    outputs: ["env vars", "build command", "healthcheck", "rollback note"],
  },
};

const CODE_CUBE_LANGUAGE_FACE = {
  python: { tongue: "KO", stack: "FastAPI or CLI", extension: "py" },
  javascript: { tongue: "AV", stack: "Node/Express or browser JS", extension: "js" },
  typescript: { tongue: "AV", stack: "Next.js/Node typed app", extension: "ts" },
  rust: { tongue: "RU", stack: "Axum/service binary", extension: "rs" },
  go: { tongue: "RU", stack: "net/http service", extension: "go" },
  sql: { tongue: "DR", stack: "schema and migrations", extension: "sql" },
  markdown: { tongue: "DR", stack: "docs and build worksheet", extension: "md" },
};

const MANIFOLD_TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"];
const MANIFOLD_FACE_MAP = {
  frontend: "AV",
  backend: "KO",
  data: "RU",
  tests: "CA",
  security: "UM",
  deploy: "DR",
};
const MANIFOLD_PRESSURE_TIERS = {
  read_only: { tier: 0, max_pressure_kpa: 25, interlock: "allow-read" },
  repo_write: { tier: 1, max_pressure_kpa: 60, interlock: "confirm-write" },
  network: { tier: 2, max_pressure_kpa: 90, interlock: "confirm-network" },
  destructive: { tier: 3, max_pressure_kpa: 0, interlock: "fail-closed-vent" },
};

function wordsFromIntent(intent) {
  return String(intent || "")
    .toLowerCase()
    .replace(/[^a-z0-9_\s-]+/g, " ")
    .split(/\s+/)
    .filter(Boolean);
}

function classifyIntent(intent) {
  const words = new Set(wordsFromIntent(intent));
  const domain = [];
  if (["todo", "task", "tasks", "kanban"].some((w) => words.has(w))) domain.push("task_management");
  if (["payment", "checkout", "stripe", "invoice"].some((w) => words.has(w))) domain.push("payments");
  if (["repo", "code", "github", "pull", "pr"].some((w) => words.has(w))) domain.push("repo_tooling");
  if (["chemistry", "materials", "waves", "fiber"].some((w) => words.has(w))) domain.push("science_workbench");
  if (!domain.length) domain.push("general_app");
  return domain;
}

function buildCodeCubeCenter(intent, flags) {
  const words = wordsFromIntent(intent);
  const domains = classifyIntent(intent);
  const wantsAuth = words.some((w) => ["auth", "login", "user", "users", "account"].includes(w));
  const wantsPayments = words.some((w) => ["payment", "checkout", "stripe", "invoice"].includes(w));
  const wantsTests = words.some((w) => ["test", "tests", "verify", "safe"].includes(w)) || true;
  const entities = [];
  if (domains.includes("task_management")) entities.push("User", "Task");
  else if (domains.includes("payments")) entities.push("Customer", "Offer", "Order", "Receipt");
  else if (domains.includes("repo_tooling")) entities.push("Repository", "Change", "Check", "Receipt");
  else if (domains.includes("science_workbench")) entities.push("Scenario", "Calculation", "Assumption", "Receipt");
  else entities.push("User", "Project", "Item", "Receipt");
  const actions = ["create", "list", "update", "export_receipt"];
  if (wantsAuth) actions.unshift("authenticate");
  if (wantsPayments) actions.push("checkout", "deliver_purchase");
  if (wantsTests) actions.push("run_tests");
  return {
    id: `codecube_${sha256Hex(`${intent}:${JSON.stringify(flags)}`).slice(0, 12)}`,
    intent,
    domains,
    canonical_ir: {
      kind: "app_blueprint",
      entities: Array.from(new Set(entities)),
      actions: Array.from(new Set(actions)),
      constraints: [
        wantsAuth ? "auth_required_for_mutation" : "public_read_private_write",
        "all_mutations_emit_receipts",
        "destructive_commands_require_preflight",
      ],
      invariants: [
        "center_ir_is_source_of_truth",
        "faces_are_projections_not_separate_apps",
        "twists_mutate_center_then_regenerate_faces",
      ],
    },
  };
}

function buildCodeCubeFaces(center, language) {
  const faceEntries = Object.entries(CODE_CUBE_FACES).map(([id, spec]) => ({
    id,
    color: spec.color,
    role: spec.role,
    outputs: spec.outputs,
    projection: {
      reads: id === "frontend" ? ["entities", "actions"] : ["canonical_ir"],
      emits: spec.outputs,
    },
  }));
  const lang = String(language || "typescript").toLowerCase();
  const languageSpec = CODE_CUBE_LANGUAGE_FACE[lang] || CODE_CUBE_LANGUAGE_FACE.typescript;
  return {
    structural_faces: faceEntries,
    language_face: {
      language: CODE_CUBE_LANGUAGE_FACE[lang] ? lang : "typescript",
      ...languageSpec,
      promise: "emit target code from the center IR; do not hand-edit a face as the source of truth",
    },
    center_preview: center.canonical_ir,
  };
}

function buildTwists(center, flags) {
  const requested = String(flags.twist || "backend.tests").toLowerCase();
  const base = [
    {
      id: "frontend.backend",
      operation: "bind UI actions to API routes",
      mutates: ["actions", "routes"],
      emits: ["route contract", "component API map"],
    },
    {
      id: "backend.data",
      operation: "bind handlers to schema",
      mutates: ["entities", "relations"],
      emits: ["schema contract", "validation rules"],
    },
    {
      id: "tests.backend",
      operation: "generate tests from backend actions",
      mutates: ["verification_plan"],
      emits: ["unit tests", "route smoke tests"],
    },
    {
      id: "security.deploy",
      operation: "run command preflight and deploy gate",
      mutates: ["ship_plan"],
      emits: ["command-check packet", "deploy receipt"],
    },
    {
      id: "language.rotate",
      operation: "emit the selected language face from the center IR",
      mutates: [],
      emits: ["target source files", "language caveats"],
    },
  ];
  return base.map((twist) => ({
    ...twist,
    selected: twist.id === requested || requested.split(",").includes(twist.id),
  }));
}

function parseIntegerList(value, fallback) {
  const raw = String(value || "").trim();
  if (!raw) return fallback;
  const parsed = raw
    .split(/[,:\s]+/)
    .map((item) => Number.parseInt(item, 10))
    .filter((item) => Number.isFinite(item) && item > 1);
  return parsed.length ? parsed : fallback;
}

function gcd(a, b) {
  let x = Math.abs(a);
  let y = Math.abs(b);
  while (y) {
    const t = y;
    y = x % y;
    x = t;
  }
  return x;
}

function pairwiseCoprime(values) {
  for (let i = 0; i < values.length; i += 1) {
    for (let j = i + 1; j < values.length; j += 1) {
      if (gcd(values[i], values[j]) !== 1) return false;
    }
  }
  return true;
}

function tritFor(seed, index) {
  const byte = crypto.createHash("sha256").update(`${seed}:${index}`).digest()[0];
  return (byte % 3) - 1;
}

function planeForTwist(twistId, dimensions) {
  const names = Object.keys(CODE_CUBE_FACES);
  const parts = String(twistId || "").split(".");
  const leftIndex = Math.max(0, names.indexOf(parts[0]));
  const rightIndex = Math.max(0, names.indexOf(parts[1]));
  const i = leftIndex % dimensions;
  const j = rightIndex % dimensions;
  return i === j ? [i, (j + 1) % dimensions] : [i, j];
}

function degreesToRadians(value) {
  return (value * Math.PI) / 180;
}

function clampNumber(value, fallback, min, max) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(min, Math.min(max, parsed));
}

function buildCenterAttitude(flags, dimensions) {
  const pitchDeg = clampNumber(flags.pitch, 0, -180, 180);
  const yawDeg = clampNumber(flags.yaw, 0, -180, 180);
  const rollDeg = clampNumber(flags.roll, 0, -180, 180);
  const speed = clampNumber(flags.speed || flags.throttle, 0.5, 0, 1);
  const pitch = degreesToRadians(pitchDeg);
  const yaw = degreesToRadians(yawDeg);
  const roll = degreesToRadians(rollDeg);

  // Start with a simple forward vector, then let attitude controls distribute
  // it across additional axes. This is a navigation packet, not flight dynamics.
  const vector = Array.from({ length: dimensions }, () => 0);
  vector[0] = Math.cos(yaw) * Math.cos(pitch) * speed;
  if (dimensions > 1) vector[1] = Math.sin(yaw) * Math.cos(pitch) * speed;
  if (dimensions > 2) vector[2] = Math.sin(pitch) * speed;
  if (dimensions > 3) vector[3] = Math.sin(roll) * speed;
  for (let i = 4; i < dimensions; i += 1) {
    vector[i] = Math.sin((pitch + yaw + roll) / (i + 1)) * speed;
  }
  const norm = Math.sqrt(vector.reduce((acc, item) => acc + item * item, 0));
  return {
    schema_version: "geoseal_center_attitude_v1",
    model: "center_jet_attitude_control",
    purpose: "turn a simple forward instruction into multi-axis face traversal",
    controls: {
      pitch_deg: pitchDeg,
      yaw_deg: yawDeg,
      roll_deg: rollDeg,
      speed,
    },
    axes: {
      forward: 0,
      yaw_lateral: dimensions > 1 ? 1 : null,
      pitch_vertical: dimensions > 2 ? 2 : null,
      roll_spin: dimensions > 3 ? 3 : null,
      higher_order_faces: dimensions > 4 ? Array.from({ length: dimensions - 4 }, (_, i) => i + 4) : [],
    },
    vector: vector.map((item) => Number(item.toPrecision(6))),
    norm: Number(norm.toPrecision(6)),
    interpretation: "pitch/yaw/roll/speed bias which face-pair rotations fire first; center remains the source of truth",
  };
}

function buildManifoldTarget(center, faces, twists, flags) {
  const dimensions = Math.max(3, Math.min(18, Number.parseInt(flags.dimensions || flags.dimension || "6", 10) || 6));
  const moduli = parseIntegerList(flags.moduli || flags["crt-moduli"], [7, 11, 13]);
  const tierName = String(flags.tier || flags["pressure-tier"] || "repo_write").toLowerCase();
  const tier = MANIFOLD_PRESSURE_TIERS[tierName] || MANIFOLD_PRESSURE_TIERS.repo_write;
  const selectedTwists = twists.filter((twist) => twist.selected);
  const activeTwists = selectedTwists.length ? selectedTwists : twists.filter((twist) => ["frontend.backend", "tests.backend", "security.deploy"].includes(twist.id));
  const attitude = buildCenterAttitude(flags, dimensions);
  const faceStates = faces.structural_faces.map((face, index) => {
    const tongue = MANIFOLD_FACE_MAP[face.id] || MANIFOLD_TONGUES[index % MANIFOLD_TONGUES.length];
    const trit = tritFor(`${center.id}:${face.id}`, index);
    return {
      face: face.id,
      tongue,
      color: face.color,
      trit,
      shuttle_state: trit < 0 ? "left" : trit > 0 ? "right" : "center",
      valve_class: tongue === "UM" ? "fail_closed_pressure_interlock" : tongue === "CA" ? "bistable_nor_logic" : tongue === "RU" ? "coprime_address_bank" : tongue === "DR" ? "purge_transform_router" : tongue === "AV" ? "gtm_coil_io_bridge" : "clock_sequencer_bistable",
    };
  });
  const addressSpace = moduli.reduce((acc, item) => acc * item, 1);
  const residueBanks = faceStates.map((face, index) => {
    const hash = crypto.createHash("sha256").update(`${center.id}:${face.face}:${face.trit}`).digest();
    const address = hash.readUInt32BE(0) % addressSpace;
    return {
      face: face.face,
      tongue: face.tongue,
      address,
      residues: moduli.map((modulus) => address % modulus),
    };
  });
  // Tongue weights price the hyperbolic boost: base rapidity = ln(w_a) + ln(w_b),
  // additive under composition (a real boost-composition property). Tier/attitude still
  // modulate it. See research/aether-manifold/rotations.md.
  const TONGUE_WEIGHT = { frontend: 1.62, backend: 4.24, data: 2.62, tests: 1.0, security: 6.85, deploy: 11.09 };
  const rotations = activeTwists.map((twist, index) => {
    const planeFaces = String(twist.id).split(".");
    const [i, j] = planeForTwist(twist.id, dimensions);
    const attitudeBias = Math.abs(attitude.vector[i] || 0) + Math.abs(attitude.vector[j] || 0);
    const quarterTurns = (index % 3) + 1;
    const angle = Number((((Math.PI / 2) * quarterTurns) + attitudeBias * 0.1).toPrecision(8));
    const baseRapidity = Math.log(TONGUE_WEIGHT[planeFaces[0]] || 1) + Math.log(TONGUE_WEIGHT[planeFaces[1]] || 1);
    const rapidity = Number((baseRapidity * Math.max(1, tier.tier) * (1 + attitude.controls.speed)).toPrecision(6));
    return {
      step: index + 1,
      twist: twist.id,
      generator: `R_${i}_${j}`,
      manifold: `SO(${dimensions}) plane rotation`,
      plane: [i, j],
      angle_rad: angle,
      attitude_bias: Number(attitudeBias.toPrecision(6)),
      hyperbolic_gate: {
        generator: `B_${i}_${j}`,
        group_note: `SO(${Math.max(1, dimensions - 1)},1) boost-like pressure/privilege gate`,
        rapidity,
        preserved_quantity: "signed pressure/state norm in the manifold packet, not a measured hardware claim",
      },
      operation: twist.operation,
      valve_action: twist.id === "security.deploy" ? "route through UM pressure interlock before deploy" : twist.id === "tests.backend" ? "feed CA verification pulses into backend lane" : twist.id === "frontend.backend" ? "bind AV interface lane to KO sequencer" : "rotate projection face over center IR",
    };
  });
  return {
    schema_version: "geoseal_code_cube_manifold_target_v1",
    target: "manifold",
    status: "software_schedule_only",
    dimensions,
    cube_order_note: `${dimensions}D state; physical tile count is not asserted. n-cube has 2^n vertices, while this packet uses ${faceStates.length} named working faces.`,
    rotation_basis: {
      euclidean: "plane/Givens rotations mutate pairs of center-state axes",
      hyperbolic: "boost-like rapidity gates model pressure/privilege transitions",
      rubix: "named twist generators form a discrete Cayley-walk over allowed face operations",
    },
    center_attitude: attitude,
    trit_states: faceStates,
    coprime_residue_routing: {
      moduli,
      pairwise_coprime: pairwiseCoprime(moduli),
      address_space: addressSpace,
      banks: residueBanks,
      fault_tolerance_note: "add one redundant coprime modulus for RRNS lane-loss recovery before any hardware claim",
    },
    geoseal_pressure_tier: {
      name: MANIFOLD_PRESSURE_TIERS[tierName] ? tierName : "repo_write",
      ...tier,
    },
    twist_schedule: rotations,
    hardware_boundary: "B2Gate/GTM/fluidic schedule only; no fabrication dimensions or measured performance are claimed",
  };
}

function buildCodeCubeFiles(center, language) {
  const lang = String(language || "typescript").toLowerCase();
  const entities = center.canonical_ir.entities;
  const actions = center.canonical_ir.actions;
  const name = center.id.replace(/^codecube_/, "app_");
  if (lang === "python") {
    return [
      { path: "app/main.py", purpose: "FastAPI-style handler skeleton", language: "python" },
      { path: "tests/test_app.py", purpose: "route and invariant tests", language: "python" },
      { path: "README.md", purpose: "receipt and run notes", language: "markdown" },
    ];
  }
  if (lang === "rust") {
    return [
      { path: "src/main.rs", purpose: "Axum/service skeleton", language: "rust" },
      { path: "tests/receipt.rs", purpose: "receipt invariant tests", language: "rust" },
      { path: "README.md", purpose: "receipt and run notes", language: "markdown" },
    ];
  }
  if (lang === "go") {
    return [
      { path: "cmd/server/main.go", purpose: "net/http service skeleton", language: "go" },
      { path: "internal/app/receipt.go", purpose: "receipt model", language: "go" },
      { path: "README.md", purpose: "receipt and run notes", language: "markdown" },
    ];
  }
  return [
    { path: "src/app.js", purpose: `${name} app shell for ${entities.join(", ")}`, language: "javascript" },
    { path: "src/routes.js", purpose: `routes for ${actions.join(", ")}`, language: "javascript" },
    { path: "tests/app.test.js", purpose: "route and command-preflight tests", language: "javascript" },
    { path: "README.md", purpose: "receipt and run notes", language: "markdown" },
  ];
}

function runCodeCube(positionals, flags) {
  const carried = typeof flags.json === "string" ? flags.json : "";
  const intent = String(flags.content || flags.intent || carried || positionals.slice(1).join(" ") || "build a small app with tests and receipts").trim();
  const language = String(flags.language || flags.lang || "typescript").toLowerCase();
  const center = buildCodeCubeCenter(intent, flags);
  const faces = buildCodeCubeFaces(center, language);
  const twists = buildTwists(center, flags);
  const files = buildCodeCubeFiles(center, faces.language_face.language);
  const suggestedCommands = [
    "npm test",
    "python -m pytest tests/api/test_ai_waves_lab.py -q",
    "git status --short",
  ];
  const preflight = suggestedCommands.map((commandText) => ({
    command: commandText,
    ...commandRisk(commandText),
  }));
  const packetCore = { center, faces, twists, files, preflight };
  const targets = String(flags.target || "software")
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
  const includeManifold = targets.includes("manifold") || targets.includes("physical") || targets.includes("all");
  const manifold = includeManifold ? buildManifoldTarget(center, faces, twists, flags) : null;
  const payload = {
    schema_version: "geoseal_code_cube_v1",
    ok: true,
    product_component: "CodeCube for GeoSeal CLI",
    mode: "software_semantics_first_physical_cube_later",
    receipt_id: `codecube_${sha256Hex(JSON.stringify(packetCore)).slice(0, 16)}`,
    center,
    faces,
    twists,
    output_packet: {
      files,
      language: faces.language_face,
      next_safe_commands: preflight,
      export_contract: "center IR -> face projections -> twist receipts -> generated project packet",
    },
    targets: {
      software: true,
      manifold: Boolean(manifold),
      manifold_schedule: manifold,
    },
    safety: {
      executes_shell: false,
      destructive_gate: "commands are described and preflighted; this component does not execute them",
      physical_hardware_claim: "not included; this is the functional software cube core",
    },
  };
  const text = [
    `CodeCube: ${center.id}`,
    `Intent: ${intent}`,
    `Center: ${center.canonical_ir.entities.join(", ")} / ${center.canonical_ir.actions.join(", ")}`,
    `Faces: ${Object.keys(CODE_CUBE_FACES).join(", ")} + ${faces.language_face.language}`,
    `Selected twists: ${twists.filter((t) => t.selected).map((t) => t.id).join(", ") || "none"}`,
    `Output files: ${files.map((file) => file.path).join(", ")}`,
    manifold ? `Manifold: ${manifold.dimensions}D, moduli ${manifold.coprime_residue_routing.moduli.join(",")}, pressure ${manifold.geoseal_pressure_tier.name}` : "Manifold: not requested",
    `Receipt: ${payload.receipt_id}`,
  ].join("\n");
  writeJsonOrText(flags, payload, text);
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

const DEFAULT_SERVICE_DIR = path.join(ROOT, "artifacts", "geoseal_service");
const DEFAULT_SERVICE_HOST = "127.0.0.1";
const DEFAULT_SERVICE_PORT = 8002;
const GEOSEAL_SERVICE_MODULE = "src.api.geoseal_service:app";
const GEOSEAL_DEMO_API_KEY = "demo_key_12345";

function pythonExecutables() {
  const executables = [];
  if (process.env.SCBE_GEOSEAL_PYTHON) executables.push(process.env.SCBE_GEOSEAL_PYTHON);
  if (process.platform === "win32") executables.push("py");
  executables.push("python", "python3");
  return [...new Set(executables.filter(Boolean))];
}

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
  for (const executable of pythonExecutables()) {
    const script = [
      "import importlib.util, json",
      `name=${JSON.stringify(moduleName)}`,
      "spec=importlib.util.find_spec(name)",
      "print(json.dumps({'module': name, 'found': spec is not None, 'origin': getattr(spec, 'origin', None)}))",
    ].join("; ");
    const result = spawnSync(executable, ["-c", script], {
      encoding: "utf8",
      shell: false,
      cwd: ROOT,
      timeout: 8000,
    });
    if (!result.error) {
      let detail = {};
      try {
        detail = JSON.parse(String(result.stdout || "{}"));
      } catch (_err) {
        detail = {};
      }
      return {
        executable,
        module: moduleName,
        ok: result.status === 0 && detail.found === true,
        status: result.status,
        origin: detail.origin || null,
        stdout_preview: String(result.stdout || "").slice(0, 600),
        stderr_preview: String(result.stderr || "").slice(0, 600),
      };
    }
  }
  return { module: moduleName, ok: false, error: "no usable Python executable found" };
}

async function probeServiceHealth(apiBase, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${apiBase.replace(/\/+$/, "")}/v1/spaceport/status`, {
      method: "GET",
      signal: controller.signal,
    });
    const text = await response.text();
    let body = null;
    try {
      body = JSON.parse(text);
    } catch (_err) {
      body = text.slice(0, 1000);
    }
    return { ok: response.ok, status: response.status, body };
  } catch (err) {
    return {
      ok: false,
      error: err && err.name === "AbortError" ? "health_probe_timeout" : "health_probe_failed",
      message: err && err.message ? err.message : String(err),
    };
  } finally {
    clearTimeout(timer);
  }
}

function serviceApiBase(flags) {
  const host = String(flags.host || DEFAULT_SERVICE_HOST);
  const port = Number(flags.port || DEFAULT_SERVICE_PORT);
  return `http://${host}:${port}`;
}

function serviceRuntimeHeaders(flags) {
  if (flags["allow-demo-keys"]) return { "x-api-key": GEOSEAL_DEMO_API_KEY };
  if (apiKey(flags)) return { "x-api-key": apiKey(flags) };
  return {};
}

async function waitForService(apiBase, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastProbe = null;
  while (Date.now() < deadline) {
    lastProbe = await probeServiceHealth(apiBase, Math.min(1500, Math.max(500, timeoutMs)));
    if (lastProbe.ok) return lastProbe;
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  return lastProbe || { ok: false, error: "health_probe_timeout" };
}

async function runService(flags) {
  const stateDir = serviceOutputDir(flags);
  fs.mkdirSync(stateDir, { recursive: true });
  const statePath = path.join(stateDir, "service.json");
  const apiBaseUrl = serviceApiBase(flags);
  const existing = resolveActiveServiceBase(flags);
  if (existing) {
    const probe = flags["probe-health"] ? await probeServiceHealth(existing.apiBase, Number(flags["probe-timeout"] || 3000)) : null;
    const payload = {
      schema_version: "geoseal_service_v1",
      ok: true,
      status: "already_running",
      api_base: existing.apiBase,
      pid: existing.pid,
      state_path: existing.statePath,
      health: probe,
    };
    writeJsonOrText(flags, payload, `GeoSeal service already running at ${existing.apiBase} (pid ${existing.pid})`);
    return;
  }

  const env = { ...process.env };
  if (flags["allow-demo-keys"]) env.SCBE_ALLOW_DEMO_KEYS = "1";
  if (apiKey(flags)) env.SCBE_API_KEY = apiKey(flags);

  const args = ["-m", "uvicorn", GEOSEAL_SERVICE_MODULE, "--host", String(flags.host || DEFAULT_SERVICE_HOST), "--port", String(flags.port || DEFAULT_SERVICE_PORT)];
  const executable = pythonExecutables()[0];
  const child = spawn(executable, args, {
    cwd: ROOT,
    env,
    detached: Boolean(flags.detach),
    stdio: flags.detach ? "ignore" : "inherit",
    shell: false,
    windowsHide: true,
  });

  if (flags.detach) child.unref();

  const state = {
    schema_version: "geoseal_service_state_v1",
    api_base: apiBaseUrl,
    pid: child.pid,
    started_at: new Date().toISOString(),
    command: [executable, ...args],
    runtime_headers: serviceRuntimeHeaders(flags),
  };
  fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`, "utf8");

  if (!flags.detach) return;

  const health = flags["probe-health"] ? await waitForService(apiBaseUrl, Number(flags["probe-timeout"] || 10000)) : null;
  const ok = !health || health.ok;
  const payload = {
    schema_version: "geoseal_service_v1",
    ok,
    status: ok ? "started" : "started_health_unconfirmed",
    api_base: apiBaseUrl,
    pid: child.pid,
    state_path: statePath,
    health,
  };
  writeJsonOrText(flags, payload, `GeoSeal service ${payload.status} at ${apiBaseUrl} (pid ${child.pid})`);
  if (!ok) process.exitCode = 1;
}

async function runServiceStatus(flags) {
  const stateDir = serviceOutputDir(flags);
  const statePath = path.join(stateDir, "service.json");
  let state = null;
  try {
    state = JSON.parse(fs.readFileSync(statePath, "utf8"));
  } catch (_err) {
    const payload = {
      schema_version: "geoseal_service_status_v1",
      ok: false,
      status: "not_started",
      state_path: statePath,
      fixes: ["geoseal service --detach --allow-demo-keys --probe-health --json"],
    };
    writeJsonOrText(flags, payload, "GeoSeal service is not started.");
    process.exitCode = 2;
    return;
  }

  const pid = Number(state.pid);
  const alive = isPidAlive(pid);
  const probe = flags["probe-health"] && state.api_base ? await probeServiceHealth(String(state.api_base), Number(flags["probe-timeout"] || 3000)) : null;
  const ok = alive && (!probe || probe.ok);
  const payload = {
    schema_version: "geoseal_service_status_v1",
    ok,
    status: ok ? "running" : alive ? "running_health_failed" : "stale",
    api_base: state.api_base || null,
    pid: Number.isFinite(pid) ? pid : null,
    state_path: statePath,
    health: probe,
  };
  writeJsonOrText(flags, payload, ok ? `GeoSeal service running at ${state.api_base}` : `GeoSeal service state is ${payload.status}.`);
  if (!ok) process.exitCode = alive ? 1 : 2;
}

function runServiceStop(flags) {
  const stateDir = serviceOutputDir(flags);
  const statePath = path.join(stateDir, "service.json");
  let state = null;
  try {
    state = JSON.parse(fs.readFileSync(statePath, "utf8"));
  } catch (_err) {
    const payload = {
      schema_version: "geoseal_service_stop_v1",
      ok: true,
      status: "not_started",
      state_path: statePath,
    };
    writeJsonOrText(flags, payload, "GeoSeal service is not started.");
    return;
  }

  const pid = Number(state.pid);
  let stopped = false;
  if (Number.isFinite(pid) && pid > 0 && isPidAlive(pid)) {
    try {
      process.kill(pid);
      stopped = true;
    } catch (_err) {
      stopped = false;
    }
  }
  try {
    fs.rmSync(statePath, { force: true });
  } catch (_err) {
    // Best-effort cleanup only.
  }
  const payload = {
    schema_version: "geoseal_service_stop_v1",
    ok: stopped || !isPidAlive(pid),
    status: stopped ? "stopped" : "state_cleared",
    pid: Number.isFinite(pid) ? pid : null,
    state_path: statePath,
  };
  writeJsonOrText(flags, payload, `GeoSeal service ${payload.status}.`);
  if (!payload.ok) process.exitCode = 1;
}

function runDoctor(flags) {
  const active = resolveActiveServiceBase(flags);
  const advertisedCommands = [
    "doctor",
    "permissions",
    "custom-commands",
    "run-command",
    "providers",
    "provider-registry",
    "lanes",
    "product-lanes",
    "system-map",
    "aethermon-adapter",
    "powershell",
    "ps",
    "ask",
    "do",
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

function commandExists(command, args = ["--version"]) {
  const result = spawnSync(command, args, {
    encoding: "utf8",
    shell: false,
    timeout: 3000,
  });
  return !result.error && result.status === 0;
}

function runProviderRegistry(flags) {
  const payload = {
    schema_version: "geoseal_provider_registry_v1",
    ok: true,
    policy: {
      default_route: "free_local_first",
      remote_requires_configuration: true,
      paid_providers_are_optional: true,
      secrets_to_remote_models: "forbid_without_explicit_provider_config",
    },
    providers: [
      {
        id: "local-service",
        tier: "free",
        kind: "geoseal",
        installed: true,
        command: "geoseal service --detach --allow-demo-keys --probe-health --json",
        role: "Local GeoSeal API bridge, route inspection, agent harness, code packets.",
      },
      {
        id: "ollama",
        tier: "free",
        kind: "local_llm",
        installed: commandExists("ollama", ["--version"]),
        command: "ollama serve",
        role: "Local/offline coding and reasoning model host.",
      },
      {
        id: "llama.cpp",
        tier: "free",
        kind: "local_llm",
        installed: commandExists("llama-cli", ["--help"]) || commandExists("llama-server", ["--help"]),
        command: "llama-server",
        role: "Local GGUF model runner.",
      },
      {
        id: "lmstudio",
        tier: "free",
        kind: "local_llm",
        installed: commandExists("lms", ["--version"]),
        command: "lms server start",
        role: "Local OpenAI-compatible model server.",
      },
      {
        id: "huggingface",
        tier: "free_or_paid",
        kind: "remote_provider",
        configured: Boolean(process.env.HF_TOKEN || process.env.HUGGINGFACE_API_TOKEN),
        env: ["HF_TOKEN", "HUGGINGFACE_API_TOKEN"],
        role: "Hosted inference, datasets, model jobs.",
      },
      {
        id: "openai",
        tier: "paid",
        kind: "remote_provider",
        configured: Boolean(process.env.OPENAI_API_KEY),
        env: ["OPENAI_API_KEY"],
        role: "Paid model fallback for coding and analysis.",
      },
      {
        id: "anthropic",
        tier: "paid",
        kind: "remote_provider",
        configured: Boolean(process.env.ANTHROPIC_API_KEY),
        env: ["ANTHROPIC_API_KEY"],
        role: "Paid Claude fallback when explicitly configured.",
      },
      {
        id: "openrouter",
        tier: "paid",
        kind: "remote_provider",
        configured: Boolean(process.env.OPENROUTER_API_KEY),
        env: ["OPENROUTER_API_KEY"],
        role: "Paid multi-model router fallback.",
      },
    ],
  };
  const text = payload.providers
    .map((provider) => `${provider.id} [${provider.tier}] ${provider.installed || provider.configured ? "ready" : "not configured"}`)
    .join("\n");
  writeJsonOrText(flags, payload, text);
}

function runProductLanes(flags) {
  const payload = {
    schema_version: "geoseal_product_lanes_v1",
    ok: true,
    product: "multi-agent free/local-first coding shell with optional paid AI",
    lanes: [
      {
        id: "agents",
        commands: ["geoseal ask", "geoseal do", "geoseal agent-harness", "geoseal compile", "geoseal orchestrator-dispatch"],
        purpose: "Claude Code / Clawbot-style task routing, plans, manifests, and execution receipts.",
      },
      {
        id: "providers",
        commands: ["geoseal providers", "geoseal backend-registry", "geoseal explain-route"],
        purpose: "Free/local-first provider chain with paid AI as explicit fallback.",
      },
      {
        id: "chemistry",
        commands: ["scbe chem atomize", "scbe chem bonds", "scbe chem convert", "scbe chem orbitals", "scbe chem benchmark"],
        purpose: "Chemistry adapter, molecular conversion, orbital semantics, and industry benchmarks.",
      },
      {
        id: "tokenizer",
        commands: ["geoseal tokenizer-code-lanes", "geoseal verify-code-lanes", "geoseal decode-code-lanes", "geoseal tongue-compile", "geoseal tongue-run"],
        purpose: "Bijective command tokenization, binary/hex lanes, six-tongue code families, and VM execution.",
      },
      {
        id: "map-and-training",
        commands: ["geoseal system-map --check", "geoseal aethermon-adapter build", "geoseal aethermon-adapter preflight", "geoseal aethermon-adapter eval"],
        purpose: "Procedural repo map, AETHERMON local adapter target, and executable promotion gates.",
      },
      {
        id: "host-powershell",
        commands: [
          "geoseal powershell profiles",
          "geoseal powershell check --command \"Get-Location\"",
          "geoseal powershell run --profile pwd --write-receipt",
          "geoseal powershell receipts",
        ],
        purpose: "Bounded Windows PowerShell checks and read-only command receipts for local automation.",
      },
      {
        id: "arrays-spreadsheets",
        commands: ["scbe describe --json", "scbe chem benchmark --json", "geoseal code-packet --json"],
        purpose: "Machine-readable arrays and spreadsheet-ready evidence packets.",
      },
      {
        id: "receipts",
        commands: ["geoseal history", "geoseal replay", "geoseal testing-cli", "geoseal permissions"],
        purpose: "Audit trail, replayable runs, test playback, and permission model.",
      },
    ],
  };
  const text = payload.lanes.map((lane) => `${lane.id}: ${lane.purpose}`).join("\n");
  writeJsonOrText(flags, payload, text);
}

async function runAliasApi(alias, apiCommand, positionals, flags) {
  const prompt = String(flags.message || flags.goal || flags.content || positionals.slice(1).join(" ")).trim();
  if (!prompt) {
    const payload = {
      schema_version: "geoseal_alias_v1",
      ok: false,
      error: "missing_prompt",
      message: `Pass text, for example: geoseal ${alias} "add tests for tokenizer lanes"`,
    };
    writeJsonOrText(flags, payload, payload.message);
    process.exitCode = 2;
    return;
  }
  const routedFlags = { ...flags };
  if (apiCommand === "chat") {
    routedFlags.message = prompt;
    routedFlags.content = prompt;
  } else {
    routedFlags.goal = prompt;
    routedFlags.language = routedFlags.language || "python";
    routedFlags["permission-mode"] = routedFlags["permission-mode"] || "observe";
  }
  const explicitBase = apiBase(routedFlags);
  if (explicitBase) {
    await runApi(apiCommand, routedFlags, { resolvedBase: explicitBase, autoContext: null });
    return;
  }
  const active = resolveActiveServiceBase(routedFlags);
  if (active) {
    process.stderr.write(
      `[geoseal] using detected service at ${active.apiBase} (pid ${active.pid}) - set SCBE_GEOSEAL_AUTODETECT=0 to disable\n`
    );
    await runApi(apiCommand, routedFlags, { resolvedBase: active.apiBase, autoContext: active });
    return;
  }
  const payload = {
    schema_version: "geoseal_alias_v1",
    ok: false,
    error: "local_service_required",
    alias,
    routes_to: apiCommand,
    prompt,
    fixes: [
      "geoseal service --detach --allow-demo-keys --probe-health --json",
      `geoseal ${alias} "${prompt.replace(/"/g, '\\"')}" --json`,
      "geoseal providers --json",
    ],
  };
  writeJsonOrText(routedFlags, payload, `${alias} needs a local GeoSeal service. Try: ${payload.fixes[0]}`);
  process.exitCode = 2;
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
  if (command === "orchestrator-dispatch" || command === "orchestrator-status" || command === "orchestrator-promote") {
    if (!body.output_dir && !body.run_contract_file) {
      throw new Error("--output-dir or --run-contract-file is required");
    }
    return;
  }
  if (command === "chat") {
    if (!body.message) throw new Error("--message or --content is required");
    return;
  }
  if (!body.language) throw new Error("--language is required");
  if (!body.content && command !== "chat") throw new Error("--content is required");
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
  const moduleCandidates = ["src.geoseal_cli", "geoseal_cli"];

  for (const executable of pythonExecutables()) {
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

  process.stderr.write(
    "GeoSeal npm shell could not find a usable Python runtime. Install the PyPI package and set SCBE_GEOSEAL_PYTHON if needed.\n"
  );
  process.exit(1);
}

function runScbePassthrough(args) {
  const script = path.join(ROOT, "scbe.py");
  for (const executable of pythonExecutables()) {
    const result = spawnSync(executable, [script, ...args], {
      stdio: "inherit",
      shell: false,
      cwd: ROOT,
    });
    if (result.error) continue;
    process.exit(result.status === null ? 1 : result.status);
  }

  process.stderr.write(
    "GeoSeal npm shell could not find a usable Python runtime for scbe.py. Set SCBE_GEOSEAL_PYTHON if needed.\n"
  );
  process.exit(1);
}

function runPythonScript(scriptRel, args, failureMessage) {
  const script = path.join(ROOT, scriptRel);
  if (!fs.existsSync(script)) {
    process.stderr.write(`GeoSeal local script not found: ${scriptRel}\n`);
    process.exit(2);
  }
  for (const executable of pythonExecutables()) {
    const result = spawnSync(executable, [script, ...args], {
      stdio: "inherit",
      shell: false,
      cwd: ROOT,
    });
    if (result.error) continue;
    process.exit(result.status === null ? 1 : result.status);
  }

  process.stderr.write(`${failureMessage}\n`);
  process.exit(1);
}

function runSystemMap(positionals, argv) {
  const action = String(positionals[1] || "").toLowerCase();
  let args = argv.slice(1);
  if (action === "check") {
    args = ["--check", ...args.slice(1)];
  } else if (action === "watch") {
    args = ["--watch", ...args.slice(1)];
  } else if (action === "build" || action === "write" || action === "once") {
    args = args.slice(1);
  } else if (action && !action.startsWith("--")) {
    writeJsonOrText(
      { json: argv.includes("--json") },
      {
        ok: false,
        error: "unknown_system_map_action",
        action,
        actions: ["build", "check", "watch"],
      },
      `Unknown system-map action: ${action}`
    );
    process.exit(2);
  }

  runPythonScript(
    "scripts/system/procedural_system_map.py",
    args,
    "GeoSeal could not find a usable Python runtime for procedural_system_map.py. Set SCBE_GEOSEAL_PYTHON if needed."
  );
}

function runAethermonAdapter(positionals, flags, argv) {
  const knownActions = new Set(["build", "preflight", "eval", "oracle", "abstain"]);
  const rawAction = String(positionals[1] || "build").toLowerCase();
  if (!knownActions.has(rawAction)) {
    writeJsonOrText(
      flags,
      {
        ok: false,
        error: "unknown_aethermon_adapter_action",
        action: rawAction,
        actions: [...knownActions],
      },
      `Unknown aethermon-adapter action: ${rawAction}`
    );
    process.exit(2);
  }

  const args = positionals[1] ? argv.slice(2) : argv.slice(1);
  if (rawAction === "build") {
    runPythonScript(
      "scripts/system/build_aethermon_agent_adapter_v0.py",
      args,
      "GeoSeal could not find a usable Python runtime for build_aethermon_agent_adapter_v0.py. Set SCBE_GEOSEAL_PYTHON if needed."
    );
  }
  if (rawAction === "preflight") {
    runPythonScript(
      "scripts/system/preflight_zero_cost_training.py",
      ["--profile", AETHERMON_ADAPTER_PROFILE, ...args],
      "GeoSeal could not find a usable Python runtime for preflight_zero_cost_training.py. Set SCBE_GEOSEAL_PYTHON if needed."
    );
  }
  if (rawAction === "eval") {
    runPythonScript(
      "scripts/system/eval_aethermon_agent_adapter_v0.py",
      args,
      "GeoSeal could not find a usable Python runtime for eval_aethermon_agent_adapter_v0.py. Set SCBE_GEOSEAL_PYTHON if needed."
    );
  }

  const outPath = `artifacts/aethermon_agent_adapter_v0/eval_${rawAction}.json`;
  runPythonScript(
    "scripts/system/eval_aethermon_agent_adapter_v0.py",
    ["--mode", rawAction, "--out", outPath, ...args],
    "GeoSeal could not find a usable Python runtime for eval_aethermon_agent_adapter_v0.py. Set SCBE_GEOSEAL_PYTHON if needed."
  );
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
  if (SCBE_SPINE_COMMANDS.has(command)) {
    runScbePassthrough(argv);
    return;
  }
  if (command === "system-map" || command === "map-system") {
    runSystemMap(positionals, argv);
    return;
  }
  if (command === "aethermon-adapter" || command === "aethermon") {
    runAethermonAdapter(positionals, flags, argv);
    return;
  }
  if (command === "powershell" || command === "ps") {
    runPowerShell(positionals, flags);
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
  if (command === "providers" || command === "provider-registry") {
    runProviderRegistry(flags);
    return;
  }
  if (command === "lanes" || command === "product-lanes") {
    runProductLanes(flags);
    return;
  }
  if (command === "rooms") {
    runRooms(flags);
    return;
  }
  if (command === "stage") {
    runStage(positionals, flags);
    return;
  }
  if (command === "stage-frame" || command === "frames") {
    runStageFrame(positionals, flags);
    return;
  }
  if (command === "command-check" || command === "preflight") {
    runCommandCheck(positionals, flags);
    return;
  }
  if (command === "code-cube" || command === "codecube") {
    runCodeCube(positionals, flags);
    return;
  }
  if (command === "ask") {
    await runAliasApi("ask", "chat", positionals, flags);
    return;
  }
  if (command === "do") {
    await runAliasApi("do", "agent-harness", positionals, flags);
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
  if (command === "service") {
    await runService(flags);
    return;
  }
  if (command === "service-status") {
    await runServiceStatus(flags);
    return;
  }
  if (command === "service-stop") {
    runServiceStop(flags);
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
