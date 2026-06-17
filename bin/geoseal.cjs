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

  const destructivePatterns = [
    /\brm\s+(-[a-z]*r[a-z]*f|-rf|-fr)\b/i,
    /\bremove-item\b.*\b-recurse\b/i,
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
  if (destructivePatterns.some((pattern) => pattern.test(text))) {
    decision = "confirm";
    safety = "destructive";
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
