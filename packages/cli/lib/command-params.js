/**
 * @file command-params.js
 * @module cli/lib/command-params
 *
 * Typed param contracts for scbe commands, keyed by command name. Each entry was
 * extracted from that command's REAL handler (bin/scbe.js, or the delegated
 * Python/cjs script for passthrough commands) — every flag and positional was
 * verified to appear in the actual source, not invented.
 *
 * tools-manifest.js merges these into COMMAND_SPECS at load time for any command
 * that does not already declare `params` inline. Param shape:
 *   { name, type: 'string'|'number'|'integer'|'boolean',
 *     flag: '--x' | position: N (exactly one), required: bool,
 *     repeated?: bool, enum?: [...], description }
 *
 * Multi-subcommand commands (bench, flow, geoseal, workspace, agent-bus, bundle,
 * react, do, work, land) model the subcommand enum + common flags; per-subcommand
 * flags that diverge are reached via the raw `args` escape hatch on every tool.
 */

'use strict';

module.exports = {
  "demo": [
    {
      "name": "prompt",
      "type": "string",
      "flag": "--prompt",
      "required": false,
      "description": "Scenario prompt for the governed demo; defaults to a built-in secrets-cleanup scenario."
    },
    {
      "name": "command",
      "type": "string",
      "flag": "--command",
      "required": false,
      "description": "Proposed shell command to gate; defaults to a built-in Remove-Item example."
    }
  ],
  "history": [
    {
      "name": "limit",
      "type": "integer",
      "flag": "--limit",
      "required": false,
      "description": "Number of most-recent history rows to print (default 20)."
    }
  ],
  "alias": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": false,
      "enum": [
        "list",
        "ls",
        "get",
        "rm",
        "remove",
        "delete",
        "set",
        "help"
      ],
      "description": "Alias operation. Defaults to 'list'. NOTE: a non-keyword first token is treated as an alias NAME for the implicit-set form (scbe alias <name> <command...>)."
    },
    {
      "name": "name",
      "type": "string",
      "position": 1,
      "required": false,
      "description": "Alias name. For get/rm it is the alias to look up/remove; for 'set' it is the name to define."
    },
    {
      "name": "command_parts",
      "type": "string",
      "position": 2,
      "required": false,
      "repeated": true,
      "description": "Command tokens joined with spaces to define the alias (used by 'set' and the implicit <name> <command...> form)."
    }
  ],
  "utterances": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": false,
      "enum": [
        "path",
        "stats",
        "export",
        "help"
      ],
      "description": "Utterance-log operation. Defaults to 'help'."
    },
    {
      "name": "min",
      "type": "number",
      "flag": "--min",
      "required": false,
      "description": "Minimum route score filter for the 'export' corpus (passed through Number())."
    },
    {
      "name": "confirmed",
      "type": "boolean",
      "flag": "--confirmed",
      "required": false,
      "description": "On 'export', include only user-confirmed/approved routes."
    },
    {
      "name": "out",
      "type": "string",
      "flag": "--out",
      "required": false,
      "description": "On 'export', write the corpus to this file path instead of stdout."
    }
  ],
  "shell": [
    {
      "name": "minimal",
      "type": "boolean",
      "flag": "--minimal",
      "required": false,
      "description": "Launch the minimal interactive shell."
    },
    {
      "name": "ai",
      "type": "boolean",
      "flag": "--ai",
      "required": false,
      "description": "Enable the conversational AI router in the shell."
    },
    {
      "name": "tui",
      "type": "boolean",
      "flag": "--tui",
      "required": false,
      "description": "Launch the full TUI shell."
    },
    {
      "name": "agent_json",
      "type": "boolean",
      "flag": "--agent-json",
      "required": false,
      "description": "Emit agent-facing JSON shell surface."
    },
    {
      "name": "scaffold",
      "type": "boolean",
      "flag": "--scaffold",
      "required": false,
      "description": "Agent JSON choice-script scaffold mode (alias --choice-script)."
    },
    {
      "name": "squad",
      "type": "boolean",
      "flag": "--squad",
      "required": false,
      "description": "Enable squad/multi-unit routing in the shell."
    }
  ],
  "advisor": [
    {
      "name": "request",
      "type": "string",
      "position": 0,
      "repeated": true,
      "required": true,
      "description": "Free-form advisor request; all non-flag tokens are joined with spaces. Exits 2 if empty."
    },
    {
      "name": "provider",
      "type": "string",
      "flag": "--provider",
      "required": false,
      "description": "LLM provider name (e.g. ollama, offline). Defaults from shell config."
    },
    {
      "name": "model",
      "type": "string",
      "flag": "--model",
      "required": false,
      "description": "Model name override. Defaults from shell config."
    },
    {
      "name": "url",
      "type": "string",
      "flag": "--url",
      "required": false,
      "description": "Provider/base URL override (alias --ollama-url)."
    },
    {
      "name": "timeout_ms",
      "type": "number",
      "flag": "--timeout-ms",
      "required": false,
      "description": "Request timeout in milliseconds; passed to Number()."
    }
  ],
  "terminal": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": false,
      "enum": [
        "bench",
        "benchmark",
        "tui",
        "help"
      ],
      "description": "Optional subcommand: bench/benchmark runs the terminal benchmark, tui launches the TUI shell, help prints usage. Default (none) prints the terminal frontend panel."
    },
    {
      "name": "tui",
      "type": "boolean",
      "flag": "--tui",
      "required": false,
      "description": "Launch the interactive TUI shell instead of the static panel."
    },
    {
      "name": "detail",
      "type": "boolean",
      "flag": "--detail",
      "required": false,
      "description": "Show the detailed panel (alias -d)."
    },
    {
      "name": "no_color",
      "type": "boolean",
      "flag": "--no-color",
      "required": false,
      "description": "Disable ANSI color in the panel."
    }
  ],
  "actions": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": false,
      "enum": [
        "list",
        "ls",
        "run",
        "help"
      ],
      "description": "Subcommand: list/ls (default) lists action bundles, run executes one, help prints usage. Any other first token is treated as an action id to run directly."
    },
    {
      "name": "action_id",
      "type": "string",
      "position": 1,
      "required": false,
      "description": "Action bundle id; required when subcommand is run. If the first token is not a known subcommand it is itself treated as the id."
    },
    {
      "name": "dry_run",
      "type": "boolean",
      "flag": "--dry-run",
      "required": false,
      "description": "Print the exact command that would run without executing it."
    }
  ],
  "action": [
    {
      "name": "action_id",
      "type": "string",
      "position": 0,
      "required": true,
      "description": "Action bundle id to execute. Exits 2 if unknown/missing."
    },
    {
      "name": "dry_run",
      "type": "boolean",
      "flag": "--dry-run",
      "required": false,
      "description": "Print the exact command that would run without executing it."
    }
  ],
  "desktop": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": false,
      "enum": [
        "status",
        "open",
        "dev",
        "browse",
        "browser",
        "capture",
        "screenshot",
        "bridge",
        "bridge-smoke",
        "smoke",
        "test",
        "app-bench",
        "apps",
        "capabilities",
        "build",
        "pack",
        "bundle",
        "help"
      ],
      "description": "Desktop subcommand. Default (none/first arg is a flag) is status."
    },
    {
      "name": "url",
      "type": "string",
      "position": 1,
      "required": false,
      "description": "Target URL positional for browse/capture (first non-flag arg after the subcommand; also settable via --url)."
    },
    {
      "name": "port",
      "type": "number",
      "flag": "--port",
      "required": false,
      "description": "Preferred local dev/bridge port (default 3000 for open, 3678 for bridge/smoke); parsed with parseInt."
    },
    {
      "name": "bridge_port",
      "type": "number",
      "flag": "--bridge-port",
      "required": false,
      "description": "Preferred action bridge port (default 3678) for open; parseInt."
    },
    {
      "name": "out",
      "type": "string",
      "flag": "--out",
      "required": false,
      "description": "Output path for capture/browse screenshot or pack zip destination."
    },
    {
      "name": "url_flag",
      "type": "string",
      "flag": "--url",
      "required": false,
      "description": "Target URL for browse/capture/bridge-smoke (alternative to the positional)."
    },
    {
      "name": "command",
      "type": "string",
      "flag": "--command",
      "required": false,
      "description": "PowerShell command for bridge-smoke terminal probe (default Write-Output \"SCBE_BRIDGE_SMOKE_OK\")."
    },
    {
      "name": "no_open",
      "type": "boolean",
      "flag": "--no-open",
      "required": false,
      "description": "For open: start the dev server without launching a browser."
    },
    {
      "name": "dry_run",
      "type": "boolean",
      "flag": "--dry-run",
      "required": false,
      "description": "For open/pack: show what would happen without executing."
    },
    {
      "name": "no_build",
      "type": "boolean",
      "flag": "--no-build",
      "required": false,
      "description": "For pack: skip the desktop build step before packing."
    }
  ],
  "run": [
    {
      "name": "command",
      "type": "string",
      "position": 0,
      "repeated": true,
      "required": true,
      "description": "Free-form shell command to run through the SCBE gate, e.g. \"npm test\". All non-flag args are joined with spaces; empty command exits 2 with a Usage error."
    },
    {
      "name": "quiet",
      "type": "boolean",
      "flag": "--quiet",
      "required": false,
      "description": "Suppress streamed command output."
    },
    {
      "name": "capture",
      "type": "boolean",
      "flag": "--capture",
      "required": false,
      "description": "Capture stdout/stderr into the receipt (implied when --json is set)."
    }
  ],
  "exec": [
    {
      "name": "command",
      "type": "string",
      "position": 0,
      "repeated": true,
      "required": true,
      "description": "Free-form argv to execute, e.g. git status --short. Tokens after a literal -- are taken verbatim; otherwise all non-flag tokens are used. Each token is shell-quoted and joined. Empty command exits 2 with a Usage error."
    },
    {
      "name": "quiet",
      "type": "boolean",
      "flag": "--quiet",
      "required": false,
      "description": "Suppress streamed command output (only honored before the -- delimiter)."
    },
    {
      "name": "capture",
      "type": "boolean",
      "flag": "--capture",
      "required": false,
      "description": "Capture stdout/stderr into the receipt (implied when --json is set; only honored before the -- delimiter)."
    }
  ],
  "format": [
    {
      "name": "dry_run",
      "type": "boolean",
      "flag": "--dry-run",
      "required": false,
      "description": "Plan the steps without executing them (status 'planned')."
    },
    {
      "name": "no_write",
      "type": "boolean",
      "flag": "--no-write",
      "required": false,
      "description": "Do not write the action receipt JSON to disk."
    }
  ],
  "test": [
    {
      "name": "dry_run",
      "type": "boolean",
      "flag": "--dry-run",
      "required": false,
      "description": "Plan the steps without executing them (status 'planned')."
    },
    {
      "name": "no_write",
      "type": "boolean",
      "flag": "--no-write",
      "required": false,
      "description": "Do not write the action receipt JSON to disk."
    }
  ],
  "fix": [
    {
      "name": "dry_run",
      "type": "boolean",
      "flag": "--dry-run",
      "required": false,
      "description": "Plan the steps without executing them (status 'planned')."
    },
    {
      "name": "no_write",
      "type": "boolean",
      "flag": "--no-write",
      "required": false,
      "description": "Do not write the action receipt JSON to disk."
    }
  ],
  "prepush": [
    {
      "name": "dry_run",
      "type": "boolean",
      "flag": "--dry-run",
      "required": false,
      "description": "Plan the steps without executing them (status 'planned')."
    },
    {
      "name": "no_write",
      "type": "boolean",
      "flag": "--no-write",
      "required": false,
      "description": "Do not write the action receipt JSON to disk."
    }
  ],
  "commit": [
    {
      "name": "message",
      "type": "string",
      "flag": "--message",
      "required": true,
      "description": "Commit message. Accepts --message <msg>, -m <msg>, or --message=<msg>; falls back to remaining positional words joined. Required: buildPlan throws if empty."
    },
    {
      "name": "dry_run",
      "type": "boolean",
      "flag": "--dry-run",
      "required": false,
      "description": "Plan the steps without executing them (status 'planned')."
    },
    {
      "name": "no_write",
      "type": "boolean",
      "flag": "--no-write",
      "required": false,
      "description": "Do not write the action receipt JSON to disk."
    }
  ],
  "push": [
    {
      "name": "branch",
      "type": "string",
      "position": 0,
      "required": false,
      "description": "Branch to push to origin. Taken from --branch <name>, else the first non-flag positional, else the current git branch (git branch --show-current)."
    },
    {
      "name": "dry_run",
      "type": "boolean",
      "flag": "--dry-run",
      "required": false,
      "description": "Plan the steps without executing them (status 'planned')."
    },
    {
      "name": "no_write",
      "type": "boolean",
      "flag": "--no-write",
      "required": false,
      "description": "Do not write the action receipt JSON to disk."
    }
  ],
  "bench": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": false,
      "enum": [
        "help",
        "list",
        "status",
        "latest",
        "dashboard",
        "prove",
        "index",
        "code-ranker",
        "codegen-ranker",
        "ranker",
        "math-reasoning",
        "math",
        "mathbench",
        "tb-smoke",
        "terminal-smoke",
        "terminal-bench-smoke",
        "providers",
        "router",
        "provider-health",
        "hard-agentic",
        "research",
        "rubix-browser",
        "arc-agi2",
        "arc-style-grid",
        "swe-local",
        "cli-competitive",
        "kaggle-api",
        "compound-decompose",
        "hydra-jobsite",
        "longform"
      ],
      "description": "Bench subcommand: meta-ops (list/status/latest/dashboard/prove/index/help) or a benchmark lane id. Lane ids run scripts/benchmark/*.py. Defaults to 'help' when omitted."
    },
    {
      "name": "lane",
      "type": "string",
      "position": 1,
      "required": false,
      "description": "Optional lane id positional for the 'latest' and 'prove' subcommands (first non --flag arg). Restricts output to one lane; omit for all lanes. Must be a BENCH_TARGETS lane id."
    },
    {
      "name": "write",
      "type": "string",
      "flag": "--write",
      "required": false,
      "description": "Output path for 'index', 'dashboard', and 'prove' subcommands (read via args.indexOf('--write') + 1). Writes JSON (or HTML for dashboard without --json) to the path."
    }
  ],
  "trap-dispatch": [
    {
      "name": "input",
      "type": "string",
      "flag": "--input",
      "required": false,
      "description": "Prompt text to run through the governance preflight and dispatch. If omitted, falls back to --file then stdin."
    },
    {
      "name": "file",
      "type": "string",
      "flag": "--file",
      "required": false,
      "description": "Path to a file whose contents are the prompt (used when --input is not given)."
    },
    {
      "name": "provider",
      "type": "string",
      "flag": "--provider",
      "required": false,
      "enum": [
        "offline",
        "ollama"
      ],
      "description": "Free local provider. 'offline' (default) is a deterministic echo; 'ollama' uses a local Ollama daemon. Any other value exits 2."
    },
    {
      "name": "model",
      "type": "string",
      "flag": "--model",
      "required": false,
      "description": "Model name. Defaults to 'llama3.2' for ollama, 'offline-echo' for offline."
    },
    {
      "name": "ollama_url",
      "type": "string",
      "flag": "--ollama-url",
      "required": false,
      "description": "Ollama daemon base URL. Defaults to $OLLAMA_BASE_URL or http://127.0.0.1:11434."
    },
    {
      "name": "timeout_ms",
      "type": "integer",
      "flag": "--timeout-ms",
      "required": false,
      "description": "Provider request timeout in milliseconds (parseInt; must be a finite positive int, else default 30000)."
    },
    {
      "name": "workspace_root",
      "type": "string",
      "flag": "--workspace-root",
      "required": false,
      "description": "If set, persists the dispatch envelope as a workspace receipt under <root>/20_receipts/."
    },
    {
      "name": "batch",
      "type": "string",
      "flag": "--batch",
      "required": false,
      "description": "Path to a .jsonl file (one prompt per line, raw text or {\"input\":...,\"tag\":...}); routes to batch mode and emits an aggregate summary."
    }
  ],
  "calc": [
    {
      "name": "expression",
      "type": "string",
      "position": 0,
      "repeated": true,
      "required": true,
      "description": "Free-form math expression or spoken-math task (e.g. 'square root of 89 times inverse ratio', 'factorial(5)', 'gcd(48,18)'). Joined from all non-flag args; the handler prints usage and exits if empty. Routed to a spoken-math worksheet, a Python tier-2 evaluator (factorial/gcd/lucas_lehmer/mersenne/euclid_perfect/control-flow), or the JS expression evaluator."
    }
  ],
  "chem": [
    {
      "name": "formula",
      "type": "string",
      "position": 0,
      "repeated": true,
      "required": true,
      "description": "Chemical formula / SMILES blob, e.g. 'H2O2', 'C9H8O4', 'C6H12O6'. All args after the verb are joined and passed verbatim to scripts/scbe_calc.py 'chem'. Handler prints usage and exits if empty."
    }
  ],
  "prime": [
    {
      "name": "number",
      "type": "string",
      "position": 0,
      "repeated": true,
      "required": true,
      "description": "The integer to factor/test, e.g. '7', '19', '127'. All args after the verb are joined and passed verbatim to scripts/scbe_calc.py 'prime'. Handler prints usage and exits if empty. Typed string at the JS layer (no Number() call) — the Python script interprets it."
    }
  ],
  "emit": [
    {
      "name": "tongue",
      "type": "string",
      "position": 0,
      "required": true,
      "enum": [
        "KO",
        "AV",
        "RU",
        "CA",
        "UM",
        "DR"
      ],
      "description": "Sacred Tongue to emit in. Taken as words[0]; required (usage printed + exit if missing). Enum from the usage line 'tongues: KO AV RU CA UM DR'."
    },
    {
      "name": "expression",
      "type": "string",
      "position": 1,
      "repeated": true,
      "required": true,
      "description": "Expression to emit, e.g. 'factorial(5)', 'gcd(48,18)'. Taken as words.slice(1); required (usage printed + exit if missing). Re-split on whitespace and passed as separate args to scripts/scbe_calc.py 'emit'."
    }
  ],
  "infer": [
    {
      "name": "text",
      "type": "string",
      "position": 0,
      "repeated": true,
      "required": true,
      "description": "Free-form sentence or task to derive a mechanical worksheet from, e.g. a spoken-math/mechanical-intent description. Joined from all non-flag args; handler prints usage and exits if empty, and errors (exit 1) if no mechanical worksheet matches."
    }
  ],
  "geoseal": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": true,
      "enum": [
        "status",
        "chat",
        "portal-box",
        "stream-wheel",
        "inspect",
        "system-cards",
        "play-card",
        "run-route",
        "project-run",
        "run-history",
        "nexus-status",
        "nexus-connect",
        "nexus-dispatch",
        "cursor-status",
        "cursor-overlord",
        "fleet-distributions",
        "orchestrator-init",
        "orchestrator-dispatch",
        "orchestrator-status",
        "orchestrator-promote",
        "code-packet",
        "explain-route",
        "backend-registry",
        "agent-harness",
        "history",
        "replay",
        "testing-cli",
        "project-scaffold",
        "code-roundtrip",
        "doctor",
        "permissions",
        "custom-commands",
        "run-command",
        "tokenizer-code-lanes",
        "verify-code-lanes",
        "decode-code-lanes",
        "ai2ai-bridge",
        "tongue-compile",
        "tongue-run",
        "service",
        "service-status",
        "service-stop",
        "version",
        "help"
      ],
      "description": "GeoSeal subcommand. The first positional token. API commands route to a service (need --api-base or a live service); doctor/permissions/custom-commands/run-command/tokenizer-code-lanes/verify-code-lanes/decode-code-lanes are handled locally; any other token falls through to the python -m geoseal_cli passthrough (e.g. tongue-compile, tongue-run, ai2ai-bridge)."
    },
    {
      "name": "content",
      "type": "string",
      "flag": "--content",
      "required": false,
      "description": "Source code / command text for code-oriented subcommands (code-packet, explain-route, testing-cli, project-scaffold, code-roundtrip, portal-box, stream-wheel, inspect, run-route, tongue-compile/run). Required for some subcommands at the handler's ensureBody() stage, not at parse time."
    },
    {
      "name": "language",
      "type": "string",
      "flag": "--language",
      "required": false,
      "description": "Source language (e.g. python, rust). Most API subcommands raise '--language is required' in ensureBody() when omitted."
    },
    {
      "name": "api_base",
      "type": "string",
      "flag": "--api-base",
      "required": false,
      "description": "GeoSeal API base URL (e.g. http://127.0.0.1:8002). Falls back to SCBE_API_BASE. Without it, API subcommands need a live autodetected service or they error."
    },
    {
      "name": "api_key",
      "type": "string",
      "flag": "--api-key",
      "required": false,
      "description": "API key for authenticated /runtime/* routes. Falls back to SCBE_API_KEY."
    },
    {
      "name": "output_dir",
      "type": "string",
      "flag": "--output-dir",
      "required": false,
      "description": "Output directory; required by project-scaffold / orchestrator-init and several orchestrator/nexus subcommands at ensureBody() time."
    },
    {
      "name": "runtime",
      "type": "boolean",
      "flag": "--runtime",
      "required": false,
      "description": "Force the authenticated runtime path for portal-box/stream-wheel."
    },
    {
      "name": "source_file",
      "type": "string",
      "flag": "--source-file",
      "required": false,
      "description": "Path to a source file; an alternative to --content for code-packet/explain-route/testing-cli."
    }
  ],
  "stasm": [
    {
      "name": "input",
      "type": "string",
      "position": 0,
      "required": true,
      "description": "Path to the Sacred Tongue assembly source file (.sts). Required positional argument."
    },
    {
      "name": "output",
      "type": "string",
      "flag": "--output",
      "required": false,
      "description": "Output bytecode (.stv) path. Defaults to 'out.stv'. Short alias -o."
    },
    {
      "name": "listing",
      "type": "boolean",
      "flag": "--listing",
      "required": false,
      "description": "Print the assembly listing to stdout after assembling."
    }
  ],
  "mason": [
    {
      "name": "cmd",
      "type": "string",
      "position": 0,
      "required": true,
      "enum": [
        "build",
        "schematics"
      ],
      "description": "Mason subcommand. 'build' assembles a schematic by setting verified stones; 'schematics' lists available schematics. Required (subparsers required=True)."
    },
    {
      "name": "schematic",
      "type": "string",
      "position": 1,
      "required": false,
      "enum": [
        "pacman_core"
      ],
      "description": "Name of the schematic to build (only for the 'build' subcommand). Choices come from the dynamic REGISTRY: always includes 'pacman_core' plus any stone-pack schematics discovered under scripts/tools/mason_stones/. Required when cmd=build."
    },
    {
      "name": "inject_stub",
      "type": "string",
      "flag": "--inject-stub",
      "required": false,
      "description": "For 'build': swap the named slot's stone for an empty/stub sphere to demonstrate capture + escalation. Default None."
    }
  ],
  "do": [
    {
      "name": "objective",
      "type": "string",
      "position": 0,
      "required": true,
      "repeated": true,
      "description": "The objective to accomplish (free-form text blob; positional, required)."
    },
    {
      "name": "loops",
      "type": "integer",
      "flag": "--loops",
      "required": false,
      "description": "Max stage iterations (default 6)."
    },
    {
      "name": "land",
      "type": "string",
      "flag": "--land",
      "required": false,
      "description": "Compatibility alias; use 'every-stage' to land every stage."
    },
    {
      "name": "land_every_stage",
      "type": "boolean",
      "flag": "--land-every-stage",
      "required": false,
      "description": "Create a landing after each stage."
    },
    {
      "name": "squad",
      "type": "boolean",
      "flag": "--squad",
      "required": false,
      "description": "Route each stage to the multi-agent squad."
    },
    {
      "name": "dispatch_provider",
      "type": "string",
      "flag": "--dispatch-provider",
      "required": false,
      "description": "Agent-bus dispatch provider for --squad (default offline)."
    },
    {
      "name": "dispatch_timeout",
      "type": "integer",
      "flag": "--dispatch-timeout",
      "required": false,
      "description": "Seconds before a squad dispatch stage times out (default 120)."
    },
    {
      "name": "resume_policy",
      "type": "string",
      "flag": "--resume-policy",
      "required": false,
      "enum": [
        "latest-safe",
        "explicit-hash"
      ],
      "description": "Resume policy (default latest-safe)."
    },
    {
      "name": "backend",
      "type": "string",
      "flag": "--backend",
      "required": false,
      "enum": [
        "local",
        "local-jsonl",
        "temporal"
      ],
      "description": "Execution backend (default local)."
    },
    {
      "name": "workspace",
      "type": "string",
      "flag": "--workspace",
      "required": false,
      "description": "Workspace directory (default cwd); -w alias."
    }
  ],
  "work": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": false,
      "enum": [
        "init",
        "status",
        "resume"
      ],
      "description": "Workspace subcommand. Defaults to status when omitted in the JS shim, but Python argparse makes it optional (no work_cmd -> help/no-op)."
    },
    {
      "name": "mission",
      "type": "string",
      "flag": "--mission",
      "required": false,
      "description": "init: Mission statement (-m alias)."
    },
    {
      "name": "objective",
      "type": "string",
      "flag": "--objective",
      "required": false,
      "description": "init: Compatibility alias for --mission."
    },
    {
      "name": "workflow",
      "type": "string",
      "flag": "--workflow",
      "required": false,
      "description": "Compatibility workflow label; ignored by single-workspace ledger (init/status/resume)."
    },
    {
      "name": "invariant",
      "type": "string",
      "flag": "--invariant",
      "required": false,
      "repeated": true,
      "description": "init: Add an invariant (repeatable, -i alias)."
    },
    {
      "name": "claim",
      "type": "string",
      "flag": "--claim",
      "required": false,
      "repeated": true,
      "description": "init: Add a claim boundary (repeatable, -c alias)."
    },
    {
      "name": "hash",
      "type": "string",
      "flag": "--hash",
      "required": false,
      "description": "resume: Landing hash prefix (default latest)."
    },
    {
      "name": "workspace",
      "type": "string",
      "flag": "--workspace",
      "required": false,
      "description": "Workspace directory (default cwd); -w alias."
    }
  ],
  "land": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": false,
      "enum": [
        "create",
        "list",
        "verify",
        "show"
      ],
      "description": "Landing subcommand (land_cmd subparser)."
    },
    {
      "name": "hash",
      "type": "string",
      "position": 1,
      "required": false,
      "description": "verify/show: Landing hash prefix (positional, required for verify and show)."
    },
    {
      "name": "workflow",
      "type": "string",
      "flag": "--workflow",
      "required": false,
      "description": "create: Compatibility workflow label; ignored by single-workspace ledger."
    },
    {
      "name": "summary",
      "type": "string",
      "flag": "--summary",
      "required": false,
      "description": "create: Compatibility summary; landing content captured from ledger."
    },
    {
      "name": "stage",
      "type": "string",
      "flag": "--stage",
      "required": false,
      "description": "create: Compatibility stage label."
    },
    {
      "name": "workspace",
      "type": "string",
      "flag": "--workspace",
      "required": false,
      "description": "Workspace directory (default cwd); -w alias."
    }
  ],
  "agent": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": true,
      "enum": [
        "spawn",
        "list",
        "status"
      ],
      "description": "Agent subcommand. scbe.js only dispatches when argv[1] is in {spawn,list,status} (scbe.js:11029); Python supports spawn/list."
    },
    {
      "name": "role",
      "type": "string",
      "position": 1,
      "required": false,
      "description": "spawn: Agent role (architect/tester/prover/etc.); optional positional, or use --role alias."
    },
    {
      "name": "mandate",
      "type": "string",
      "flag": "--mandate",
      "required": true,
      "description": "spawn: Agent mandate/objective (required by argparse for spawn)."
    },
    {
      "name": "role_flag",
      "type": "string",
      "flag": "--role",
      "required": false,
      "description": "spawn: Compatibility alias for the positional role."
    },
    {
      "name": "tools",
      "type": "string",
      "flag": "--tools",
      "required": false,
      "description": "spawn: Comma-separated allowed tools."
    },
    {
      "name": "allowed_tools",
      "type": "string",
      "flag": "--allowed-tools",
      "required": false,
      "description": "spawn: Compatibility alias for --tools."
    },
    {
      "name": "budget",
      "type": "integer",
      "flag": "--budget",
      "required": false,
      "description": "spawn: Max invocations before escalation (default 20)."
    },
    {
      "name": "workflow",
      "type": "string",
      "flag": "--workflow",
      "required": false,
      "description": "Compatibility workflow label; ignored by single-workspace ledger."
    },
    {
      "name": "workspace",
      "type": "string",
      "flag": "--workspace",
      "required": false,
      "description": "Workspace directory (default cwd); -w alias."
    }
  ],
  "flow": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": true,
      "enum": [
        "plan",
        "packetize",
        "status",
        "run-next",
        "continue",
        "report"
      ],
      "description": "Flow subcommand (flow_cmd subparser, required=True)."
    },
    {
      "name": "task",
      "type": "string",
      "flag": "--task",
      "required": false,
      "description": "plan: Mission/objective to route through the swarm (required for plan)."
    },
    {
      "name": "plan",
      "type": "string",
      "flag": "--plan",
      "required": false,
      "description": "packetize: Path to an SCBE flow plan JSON (required for packetize)."
    },
    {
      "name": "packets",
      "type": "string",
      "flag": "--packets",
      "required": false,
      "description": "status/run-next/continue: Path to an SCBE work packet bundle JSON (required for those)."
    },
    {
      "name": "status_path",
      "type": "string",
      "flag": "--status",
      "required": false,
      "description": "report: Path to a flow status board JSON (required for report)."
    },
    {
      "name": "output",
      "type": "string",
      "flag": "--output",
      "required": false,
      "description": "Output JSON path (common to plan/packetize/status/run-next/continue)."
    }
  ],
  "workspace": [
    {
      "name": "action",
      "type": "string",
      "position": 0,
      "required": false,
      "enum": [
        "new",
        "verify",
        "import",
        "report",
        "cleanup-tmp",
        "ingest",
        "lineage",
        "export"
      ],
      "description": "Workspace action (defaults to 'help' if omitted). Read as the 2nd positional after 'workspace'."
    },
    {
      "name": "workspace_root",
      "type": "string",
      "flag": "--workspace-root",
      "required": false,
      "description": "Path to the bus workspace root (verify --all/ingest/lineage/report/cleanup-tmp/export)."
    },
    {
      "name": "export_path",
      "type": "string",
      "flag": "--export-path",
      "required": false,
      "description": "import/verify: Path to an export bundle."
    },
    {
      "name": "source_path",
      "type": "string",
      "flag": "--source-path",
      "required": false,
      "description": "ingest: Path to a source file to ingest."
    },
    {
      "name": "root",
      "type": "string",
      "flag": "--root",
      "required": false,
      "description": "new: Override workspace root directory."
    },
    {
      "name": "hint",
      "type": "string",
      "flag": "--hint",
      "required": false,
      "description": "new: Human label hint for the workspace receipt."
    },
    {
      "name": "all",
      "type": "boolean",
      "flag": "--all",
      "required": false,
      "description": "verify: Verify all workspaces under --workspace-root."
    },
    {
      "name": "dry_run",
      "type": "boolean",
      "flag": "--dry-run",
      "required": false,
      "description": "cleanup-tmp: Show what would be removed without deleting."
    }
  ],
  "agent-bus": [
    {
      "name": "command",
      "type": "string",
      "position": 0,
      "required": false,
      "enum": [
        "serve",
        "ui",
        "send",
        "health",
        "queue",
        "plugins",
        "tools",
        "compass",
        "hermes",
        "rubix-browser",
        "pipeline",
        "workspace",
        "upgrade",
        "help"
      ],
      "description": "Top-level agent-bus command (positionals[0], defaults to 'help')."
    },
    {
      "name": "action",
      "type": "string",
      "position": 1,
      "required": false,
      "description": "Sub-action for commands that take one (queue/plugins/tools/compass/hermes/rubix-browser/pipeline/workspace): e.g. send/queue status, compass plan, pipeline run."
    },
    {
      "name": "task",
      "type": "string",
      "flag": "--task",
      "required": false,
      "description": "send/compass/hermes/rubix-browser: the task text (required by 'send')."
    },
    {
      "name": "intent",
      "type": "string",
      "flag": "--intent",
      "required": false,
      "description": "pipeline run/compile: natural-language intent."
    },
    {
      "name": "base_url",
      "type": "string",
      "flag": "--base-url",
      "required": false,
      "description": "Backend base URL (default http://127.0.0.1:8787)."
    },
    {
      "name": "json",
      "type": "boolean",
      "flag": "--json",
      "required": false,
      "description": "Emit JSON output (this bin's own --json, parsed by the external CLI, not the scbe --json shim)."
    }
  ],
  "compile-ca": [
    {
      "name": "opcodes",
      "type": "string",
      "flag": "--opcodes",
      "required": true,
      "description": "Comma/space-separated CA opcode bytes (hex 0x.. or decimal), e.g. \"0x09 0x09 0x00\"."
    },
    {
      "name": "target",
      "type": "string",
      "flag": "--target",
      "required": false,
      "enum": [
        "python",
        "typescript",
        "go"
      ],
      "description": "Output language. Default python."
    },
    {
      "name": "fn",
      "type": "string",
      "flag": "--fn",
      "required": false,
      "description": "Generated function name. Default tongue_fn."
    },
    {
      "name": "args",
      "type": "string",
      "flag": "--args",
      "required": false,
      "description": "Comma-separated argument names for the generated function."
    }
  ],
  "ca-plan": [
    {
      "name": "ops",
      "type": "string",
      "flag": "--ops",
      "required": false,
      "description": "Comma/space-separated CA op names, e.g. \"abs,abs,add\". Provide --ops OR --expr."
    },
    {
      "name": "expr",
      "type": "string",
      "flag": "--expr",
      "required": false,
      "description": "Known expression alias, e.g. \"abs(a)+abs(b)\" or \"abs_add\". Provide --ops OR --expr."
    }
  ],
  "render-op": [
    {
      "name": "op",
      "type": "string",
      "flag": "--op",
      "required": true,
      "description": "Op name (e.g. add) or id (5 / 0x05) to render from the lexicon."
    },
    {
      "name": "target",
      "type": "string",
      "flag": "--target",
      "required": false,
      "description": "Tongue/target code key: KO|AV|RU|CA|UM|DR|GO|ZI (case-insensitive). Default KO."
    },
    {
      "name": "a",
      "type": "string",
      "flag": "--a",
      "required": false,
      "description": "Substituted for {a} in the template. Default 'a'."
    },
    {
      "name": "b",
      "type": "string",
      "flag": "--b",
      "required": false,
      "description": "Substituted for {b} in the template. Default '_' when omitted."
    }
  ],
  "compile": [
    {
      "name": "mode",
      "type": "string",
      "position": 0,
      "required": true,
      "enum": [
        "ca",
        "compile-ca",
        "plan",
        "ca-plan",
        "op",
        "render-op",
        "manifest",
        "generate",
        "apply"
      ],
      "description": "Compiler mode. ca/compile-ca=bytes->source, plan/ca-plan=names->bytes, op/render-op=lexicon render, manifest/generate/apply=stage6/LLM/diff."
    },
    {
      "name": "opcodes",
      "type": "string",
      "flag": "--opcodes",
      "required": false,
      "description": "(ca mode) CA opcode bytes, e.g. \"0x09 0x09 0x00\"."
    },
    {
      "name": "target",
      "type": "string",
      "flag": "--target",
      "required": false,
      "description": "(ca/op modes) ca: python|typescript|go; op: tongue code key KO|AV|...|ZI."
    },
    {
      "name": "ops",
      "type": "string",
      "flag": "--ops",
      "required": false,
      "description": "(plan mode) comma/space-separated CA op names."
    },
    {
      "name": "op",
      "type": "string",
      "flag": "--op",
      "required": false,
      "description": "(op mode) op name or id to render."
    }
  ],
  "route": [
    {
      "name": "program",
      "type": "string",
      "flag": "--program",
      "required": false,
      "description": "Inline Aether++ source text. Provide --program OR --file (exactly one)."
    },
    {
      "name": "file",
      "type": "string",
      "flag": "--file",
      "required": false,
      "description": "Path to a .aether file. Provide --program OR --file (exactly one)."
    },
    {
      "name": "source_name",
      "type": "string",
      "flag": "--source-name",
      "required": false,
      "description": "Logical source name for inline programs. Default inline.aether."
    },
    {
      "name": "out_dir",
      "type": "string",
      "flag": "--out-dir",
      "required": false,
      "description": "Output directory for the route packet/AST JSON. Default artifacts/aetherpp."
    },
    {
      "name": "check",
      "type": "boolean",
      "flag": "--check",
      "required": false,
      "description": "Parse/lower and print a compact result only (no files written)."
    }
  ],
  "squad": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": false,
      "enum": [
        "status",
        "route"
      ],
      "description": "status (default) shows squad units/routing; route routes a task to a unit."
    },
    {
      "name": "task",
      "type": "string",
      "flag": "--task",
      "required": false,
      "description": "(route) task description to route. If omitted, non-flag args after the subcommand are joined as the task."
    }
  ],
  "xval": [
    {
      "name": "task",
      "type": "string",
      "flag": "--task",
      "required": true,
      "description": "Question or task to cross-validate across providers. Can also be passed as bare positional text."
    },
    {
      "name": "providers",
      "type": "string",
      "flag": "--providers",
      "required": false,
      "description": "Comma-separated provider list, e.g. cerebras,groq,ollama. Defaults to reachable units."
    }
  ],
  "bundle": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": false,
      "enum": [
        "create",
        "new",
        "add",
        "verify",
        "translate",
        "project",
        "reconstruct",
        "receive"
      ],
      "description": "Bundle op. Defaults to 'create' (also runs create if the first token is a file/text rather than a known subcommand). create/new = build, add = add an entry, verify = check hashes, translate/project = project to a target rep, reconstruct/receive = emit a receiver packet."
    },
    {
      "name": "bundle",
      "type": "string",
      "flag": "--bundle",
      "required": false,
      "description": "Path to an existing bundle JSON. Required by add/verify/translate/reconstruct (verify/translate/reconstruct also accept it as the first positional)."
    },
    {
      "name": "file",
      "type": "string",
      "flag": "--file",
      "required": false,
      "description": "Source file to ingest (create --input/--file, add --file/--input, else first positional). Required by add."
    },
    {
      "name": "intent",
      "type": "string",
      "flag": "--intent",
      "required": false,
      "description": "Intent/idea text for create (alias --text); otherwise the trailing positional text is treated as intent when no real file is given."
    },
    {
      "name": "out",
      "type": "string",
      "flag": "--out",
      "required": false,
      "description": "Output path to write the bundle JSON (alias --output). create/add only."
    },
    {
      "name": "role",
      "type": "string",
      "flag": "--role",
      "required": false,
      "enum": [
        "KO",
        "AV",
        "RU",
        "CA",
        "UM",
        "DR"
      ],
      "description": "Sacred Tongue role for the entry (create/add); defaults derived from kind."
    },
    {
      "name": "kind",
      "type": "string",
      "flag": "--kind",
      "required": false,
      "description": "Force entry kind (create/add) instead of auto-detect (code/chem/image/json/binary/text)."
    },
    {
      "name": "to",
      "type": "string",
      "flag": "--to",
      "required": false,
      "enum": [
        "binary-hex"
      ],
      "description": "translate target representation; defaults to 'binary-hex'."
    },
    {
      "name": "receiver",
      "type": "string",
      "flag": "--receiver",
      "required": false,
      "description": "reconstruct receiver id; defaults to 'generic-agent'."
    }
  ],
  "react": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": true,
      "enum": [
        "audit",
        "compare",
        "code",
        "balance",
        "geometry",
        "screen",
        "checkpoint",
        "ask",
        "audio"
      ],
      "description": "Reaction-CLI op. The JS handler passes all args straight to scripts/reaction_cli.py whose argparse requires one of these subcommands."
    },
    {
      "name": "packet",
      "type": "string",
      "flag": "--packet",
      "required": false,
      "description": "audit: reaction packet JSON file (required for 'audit')."
    },
    {
      "name": "left",
      "type": "string",
      "flag": "--left",
      "required": false,
      "description": "compare: left packet file (required for 'compare')."
    },
    {
      "name": "right",
      "type": "string",
      "flag": "--right",
      "required": false,
      "description": "compare: right packet file (required for 'compare')."
    },
    {
      "name": "source",
      "type": "string",
      "flag": "--source",
      "required": false,
      "description": "code: source file (required for 'code')."
    },
    {
      "name": "target",
      "type": "string",
      "flag": "--target",
      "required": false,
      "description": "code: target file (required for 'code')."
    },
    {
      "name": "reactants",
      "type": "string",
      "flag": "--reactants",
      "required": false,
      "description": "balance: comma-separated reactant formulas, e.g. C3H8,O2 (required for 'balance')."
    },
    {
      "name": "products",
      "type": "string",
      "flag": "--products",
      "required": false,
      "description": "balance: comma-separated product formulas, e.g. CO2,H2O (required for 'balance')."
    },
    {
      "name": "smiles",
      "type": "string",
      "flag": "--smiles",
      "required": false,
      "description": "geometry: SMILES string, e.g. CCO (required for 'geometry')."
    },
    {
      "name": "frequency",
      "type": "number",
      "flag": "--frequency",
      "required": false,
      "description": "audio: drive frequency in Hz (argparse type=float, default 440.0)."
    }
  ],
  "youtube": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": true,
      "enum": [
        "review"
      ],
      "description": "Only 'review' is accepted (any other subcommand errors with exit 2). Local YouTube package readiness gate; does not upload."
    },
    {
      "name": "package",
      "type": "string",
      "position": 1,
      "required": true,
      "description": "Path to the video package JSON (first non---flag arg after 'review'). Must be a JSON object with title/description/tags/privacy/script fields."
    }
  ],
  "foundry": [
    {
      "name": "subcommand",
      "type": "string",
      "position": 0,
      "required": false,
      "enum": [
        "package",
        "verify",
        "plan-coupon",
        "workflow"
      ],
      "description": "Foundry workflow op. JS passes all args to scripts/system/foundry_workflow.py. package = deterministic OpenSCAD+receipt; verify = check receipt vs local SCAD; plan-coupon = null-gated measurement plan; workflow = package->verify->coupon-plan. Subcommand is not argparse-required (dest='command' has no required=True), but a subcommand is needed to do anything."
    },
    {
      "name": "receipt",
      "type": "string",
      "position": 1,
      "required": false,
      "description": "verify: path to braidledger_receipt.json (positional, required when subcommand=verify)."
    },
    {
      "name": "part",
      "type": "string",
      "flag": "--part",
      "required": false,
      "description": "Part name (package/plan-coupon/workflow); default 'Dual-Nodal Dynamo Core'. package also accepts alias --part-name."
    },
    {
      "name": "out",
      "type": "string",
      "flag": "--out",
      "required": false,
      "description": "Output directory/path (package/plan-coupon/workflow); package also accepts alias --output-dir."
    },
    {
      "name": "master_seed",
      "type": "string",
      "flag": "--master-seed",
      "required": false,
      "description": "UTF-8 master seed (package/workflow); aliases --seed, and --master-seed-hex for a hex seed that overrides it."
    },
    {
      "name": "measurement",
      "type": "string",
      "flag": "--measurement",
      "required": false,
      "enum": [
        "vibration",
        "dimensional",
        "thermal",
        "rf",
        "impedance"
      ],
      "description": "Measurement type (plan-coupon/workflow); default 'vibration'."
    },
    {
      "name": "seeds",
      "type": "integer",
      "flag": "--seeds",
      "required": false,
      "description": "Number of seeds (plan-coupon/workflow; argparse type=int, default 5)."
    },
    {
      "name": "copies",
      "type": "integer",
      "flag": "--copies",
      "required": false,
      "description": "Copies per seed (plan-coupon/workflow; argparse type=int, default 3)."
    }
  ]
};
