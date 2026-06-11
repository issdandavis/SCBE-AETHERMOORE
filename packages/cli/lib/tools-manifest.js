/**
 * @file tools-manifest.js
 * @module cli/lib/tools-manifest
 *
 * Canonical, machine-readable manifest of every top-level `scbe` command.
 *
 * WHY THIS EXISTS
 * ---------------
 * An AI agent that wants to use `scbe` as a tool surface ("an API full of
 * tools") needs to *discover* what commands exist, how to call them, and which
 * ones actually do real work. The human `--help` text can't be parsed reliably,
 * and the repo already had THREE lists that disagreed (KNOWN_COMMANDS=57,
 * agent-bus tools.json=58, ~90 real verbs).
 *
 * This module is the single source of truth for the command surface:
 *   - `scbe tools --json` emits a manifest built from COMMAND_SPECS.
 *   - bin/scbe.js derives KNOWN_COMMANDS from COMMAND_SPECS (one list, not two).
 *   - tests/tools-manifest.test.cjs scans the dispatch chain in bin/scbe.js and
 *     asserts every dispatched verb appears here — so the spec cannot silently
 *     drift behind the actual code.
 *
 * `stability` is honest, sourced from the command audit:
 *   real    — handler executes genuine logic (or delegates to a real script)
 *   partial — works but has a known limitation / source-checkout requirement
 *   stub    — placeholder; does not yet do real work
 */

'use strict';

const path = require('path');
const { errorContract } = require('./errors');

function readCliVersion() {
  try {
    // eslint-disable-next-line global-require
    const pkg = require(path.join(__dirname, '..', 'package.json'));
    return typeof pkg.version === 'string' ? pkg.version : null;
  } catch (_err) {
    return null;
  }
}

/**
 * COMMAND_SPECS — one entry per top-level scbe verb.
 * Fields: name, aliases[], category, summary, json(bool), usage, stability,
 *         subcommands[{name,summary}]?, examples[]?
 */
const COMMAND_SPECS = [
  // ── CORE ──────────────────────────────────────────────────────────────────
  {
    name: 'help',
    aliases: ['-h', '--help'],
    category: 'core',
    json: false,
    stability: 'real',
    summary: 'Show the full human help text.',
    usage: 'scbe help',
  },
  {
    name: 'tools',
    aliases: ['list-tools'],
    category: 'core',
    json: true,
    stability: 'real',
    summary: 'Emit this machine-readable manifest of every command (for AI/tool callers).',
    usage: 'scbe tools [--json]',
    examples: ['scbe tools --json'],
  },
  {
    name: 'version',
    aliases: ['-v', '--version'],
    category: 'core',
    json: true,
    stability: 'real',
    summary: 'Print version + build metadata (pkg, node, platform, liboqs, providers).',
    usage: 'scbe version [--json]',
    examples: ['scbe version --json'],
  },
  {
    name: 'demo',
    aliases: ['magic'],
    category: 'core',
    json: true,
    stability: 'real',
    summary: 'Governance safety demo: L12 harmonic wall scoring + L13 risk decision.',
    usage: 'scbe demo [--json]',
    examples: ['scbe demo --json'],
  },
  {
    name: 'selftest',
    aliases: [],
    category: 'core',
    json: false,
    stability: 'real',
    summary: 'Verify CLI wiring end-to-end; exit 0 on pass, non-zero on any broken component.',
    usage: 'scbe selftest',
  },
  {
    name: 'doctor',
    aliases: [],
    category: 'core',
    json: true,
    stability: 'real',
    summary: 'Full health check: node, liboqs PQC bindings, provider keys, agent-bus, GeoSeal.',
    usage: 'scbe doctor [--json]',
  },
  {
    name: 'platform',
    aliases: [],
    category: 'core',
    json: true,
    stability: 'real',
    summary: 'Cross-platform readiness matrix: OS, Node, Python, Git/GitHub, Ollama, agent-bus.',
    usage: 'scbe platform [--json]',
  },
  {
    name: 'tourney',
    aliases: [],
    category: 'core',
    json: true,
    stability: 'real',
    summary: 'Benchmark tournament board: local evidence lanes, public targets, next routes.',
    usage: 'scbe tourney [--json]',
  },
  {
    name: 'credits',
    aliases: ['hosted-run'],
    category: 'core',
    json: true,
    stability: 'real',
    summary: 'Print service-credit policy and hosted-run intake links.',
    usage: 'scbe credits [--json]',
  },
  {
    name: 'upgrade',
    aliases: [],
    category: 'core',
    json: false,
    stability: 'real',
    summary: 'Print upgrade instructions and SCBE_API_KEY setup.',
    usage: 'scbe upgrade',
  },
  {
    name: 'history',
    aliases: [],
    category: 'core',
    json: false,
    stability: 'real',
    summary: 'Show recent command history from the autocorrect ledger.',
    usage: 'scbe history [--limit N]',
  },
  {
    name: 'alias',
    aliases: ['aliases'],
    category: 'core',
    json: false,
    stability: 'real',
    summary: 'List or manage local command shortcuts in ~/.scbe/shell.json.',
    usage: 'scbe alias | scbe alias <name> <command> | scbe alias rm <name>',
  },
  {
    name: 'utterances',
    aliases: ['utterance-log'],
    category: 'core',
    json: false,
    stability: 'real',
    summary: 'Show the natural-language utterance log.',
    usage: 'scbe utterances',
  },

  // ── SHELL ─────────────────────────────────────────────────────────────────
  {
    name: 'shell',
    aliases: [],
    category: 'shell',
    json: true,
    stability: 'real',
    summary: 'Personal interactive shell. Flags pick the mode.',
    usage: 'scbe shell [--tui|--ai|--minimal|--agent-json|--squad]',
    examples: ['scbe shell --ai', 'scbe shell --agent-json'],
  },
  {
    name: 'advisor',
    aliases: [],
    category: 'shell',
    json: false,
    stability: 'real',
    summary: 'One-shot advisor answer using the shell/provider stack.',
    usage: 'scbe advisor "<request>"',
  },
  {
    name: 'terminal',
    aliases: ['term', 'ui'],
    category: 'shell',
    json: true,
    stability: 'real',
    summary: 'Compact control panel for the shell and command receipts.',
    usage: 'scbe terminal [tui|bench] [--detail] [--json]',
    subcommands: [
      { name: 'tui', summary: 'Open the headed Ink terminal UI.' },
      { name: 'bench', summary: 'Benchmark terminal frontend startup/render.' },
    ],
  },
  {
    name: 'desktop',
    aliases: ['desk'],
    category: 'shell',
    json: false,
    stability: 'real',
    summary: 'Portable desktop subsystem for Polly Pad OS.',
    usage: 'scbe desktop [open|pack]',
    subcommands: [
      { name: 'open', summary: 'Start the portable desktop locally.' },
      { name: 'pack', summary: 'Build a portable static desktop zip.' },
    ],
  },
  {
    name: 'actions',
    aliases: [],
    category: 'shell',
    json: false,
    stability: 'real',
    summary: 'List true action bundles (collapse common routes into one command).',
    usage: 'scbe actions',
  },
  {
    name: 'action',
    aliases: [],
    category: 'shell',
    json: false,
    stability: 'real',
    summary: 'Run one action bundle.',
    usage: 'scbe action <id>',
    examples: ['scbe action desktop.open'],
  },

  // ── RUN / STATUS ────────────────────────────────────────────────────────────
  {
    name: 'run',
    aliases: [],
    category: 'run',
    json: false,
    stability: 'real',
    summary: 'Execute a shell command inside the governed harness with a GeoSeal receipt.',
    usage: 'scbe run "<command>"',
    examples: ['scbe run "npm test"'],
  },
  {
    name: 'exec',
    aliases: ['x'],
    category: 'run',
    json: true,
    stability: 'real',
    summary: 'Execute command tokens (no quote-wrapping) through the governed receipt path.',
    usage: 'scbe exec [--json] <cmd...>',
    examples: ['scbe exec git status --short'],
  },
  {
    name: 'status',
    aliases: [],
    category: 'run',
    json: true,
    stability: 'partial',
    summary: 'Print current workspace, bus, and provider status.',
    usage: 'scbe status [--json]',
  },
  {
    name: 'liboqs',
    aliases: [],
    category: 'run',
    json: true,
    stability: 'real',
    summary:
      'Post-quantum proof receipt: ML-KEM-768 encap/decap + ML-DSA-65 sign/verify, with timing.',
    usage: 'scbe liboqs [--json]',
  },

  // ── DEV / PREPUSH ─────────────────────────────────────────────────────────
  {
    name: 'format',
    aliases: [],
    category: 'dev',
    json: false,
    stability: 'real',
    summary: 'Format coding surfaces through a GeoSeal action plan.',
    usage: 'scbe format [--dry-run]',
  },
  {
    name: 'test',
    aliases: [],
    category: 'dev',
    json: false,
    stability: 'real',
    summary: 'Run CLI + desktop verification plan through an action receipt.',
    usage: 'scbe test [--dry-run]',
  },
  {
    name: 'fix',
    aliases: [],
    category: 'dev',
    json: false,
    stability: 'real',
    summary: 'Format, then verify, through an action receipt.',
    usage: 'scbe fix [--dry-run]',
  },
  {
    name: 'prepush',
    aliases: ['ship'],
    category: 'dev',
    json: false,
    stability: 'real',
    summary: 'Run the before-push gate: diff check, app bench, tests, build.',
    usage: 'scbe prepush [--dry-run]',
  },
  {
    name: 'commit',
    aliases: [],
    category: 'dev',
    json: false,
    stability: 'real',
    summary: 'Run prepush, then commit staged changes.',
    usage: 'scbe commit -m "message"',
  },
  {
    name: 'push',
    aliases: [],
    category: 'dev',
    json: false,
    stability: 'real',
    summary: 'Run prepush, then push a branch.',
    usage: 'scbe push [branch]',
  },

  // ── BENCH ─────────────────────────────────────────────────────────────────
  {
    name: 'bench',
    aliases: ['benchmark'],
    category: 'bench',
    json: true,
    stability: 'real',
    summary: 'Executable evidence lanes: run benchmarks and emit claim-safe proof packets.',
    usage: 'scbe bench <lane> [--json] [--open-report]',
    subcommands: [
      { name: 'hard-agentic', summary: 'Hard agentic pretest matrix.' },
      { name: 'research', summary: 'BrowseComp/GAIA-style local research fixtures.' },
      { name: 'rubix-browser', summary: 'Permission-hypercube browser-control fixture.' },
      { name: 'terminal-adapter', summary: 'Terminal-Bench-style adapter contract.' },
      { name: 'tb-smoke', summary: 'One external Terminal-Bench smoke through WSL.' },
      { name: 'kaggle-api', summary: 'Live Kaggle API reachability through scbe run.' },
      { name: 'chemistry', summary: 'Chemistry/STISTA capability lane.' },
      { name: 'compound-decompose', summary: 'RDKit compound decomposition/recomposition.' },
      { name: 'hydra-jobsite', summary: 'Multi-agent project-conservation benchmark.' },
      { name: 'full', summary: 'Full-system evidence matrix.' },
      { name: 'circuit', summary: 'Ordered improve/cross-test circuit.' },
      { name: 'bfcl', summary: 'BFCL tool-call adapter: schema export + model eval.' },
      { name: 'tau-bench', summary: 'Tau-bench policy microbench.' },
      { name: 'code-ranker', summary: 'Rank codegen models against benchmarks.' },
      { name: 'math-reasoning', summary: 'Hard math microbench (raw/choice/tool-choice/gated).' },
      { name: 'list', summary: 'List registered evidence lanes.' },
      { name: 'status', summary: 'Compact readiness/status view.' },
      { name: 'latest', summary: 'Show latest artifact summary for a lane.' },
      { name: 'dashboard', summary: 'Emit operator dashboard from evidence lanes.' },
      { name: 'prove', summary: 'Emit a claim-safe proof packet.' },
    ],
    examples: ['scbe bench list', 'scbe bench full --json'],
  },

  // ── GOVERNANCE / COMPUTE ────────────────────────────────────────────────────
  {
    name: 'abacus',
    aliases: [],
    category: 'governance',
    json: true,
    stability: 'real',
    summary: 'Compute the harmonic-wall score and L13 risk tier (deterministic governance abacus).',
    usage: 'scbe abacus run --d-h <float> --pd <float> [--json]',
    examples: ['scbe abacus run --d-h 0.4 --pd 0.1 --json'],
  },
  {
    name: 'contract',
    aliases: [],
    category: 'governance',
    json: true,
    stability: 'real',
    summary: 'Scan Solidity for governance red-flags (SCONE-class static filter).',
    usage: 'scbe contract scan <file|stdin> [--json] [--fail-on-finding]',
    examples: ['cat Vault.sol | scbe contract scan --json'],
  },
  {
    name: 'trap-redirect',
    aliases: [],
    category: 'governance',
    json: true,
    stability: 'real',
    summary: 'Inspect a prompt for adversarial redirect/jailbreak; emit an audit packet.',
    usage: 'scbe trap-redirect --input "<text>" | --file <path> [--json]',
  },
  {
    name: 'trap-dispatch',
    aliases: [],
    category: 'governance',
    json: true,
    stability: 'real',
    summary: 'Forward a prompt to a FREE provider for evaluation (zero-cost lane).',
    usage: 'scbe trap-dispatch --input "<text>" [--provider ollama|cerebras|groq] [--json]',
  },

  // ── TIER-2 COMPUTE ──────────────────────────────────────────────────────────
  {
    name: 'rns',
    aliases: [],
    category: 'compute',
    json: true,
    stability: 'real',
    summary:
      'Exact carry-free Residue Number System arithmetic over Fermat primes, with overflow detection (results are exact and overflow is flagged, never silently wrong).',
    usage: 'scbe rns <report|encode|add|sub|mul> [args] [--json]',
    subcommands: [
      { name: 'report', summary: 'Run self-checks and print the capability report.' },
      { name: 'encode', summary: 'Encode an integer to RNS residues. e.g. scbe rns encode 12345' },
      { name: 'add', summary: 'Exact add of two integers. e.g. scbe rns add 30000 30000 --json' },
      { name: 'sub', summary: 'Exact subtract of two integers.' },
      { name: 'mul', summary: 'Exact multiply of two integers (overflow-detected).' },
    ],
    examples: ['scbe rns add 30000 30000 --json', 'scbe rns encode 12345 --json'],
  },
  {
    name: 'calc',
    aliases: ['math'],
    category: 'compute',
    json: false,
    stability: 'partial',
    summary: 'Evaluate a math expression or spoken math.',
    usage: 'scbe calc "<expression>"',
  },
  {
    name: 'chem',
    aliases: [],
    category: 'compute',
    json: false,
    stability: 'partial',
    summary: 'Chemical formula analysis (requires source checkout for scbe_calc.py).',
    usage: 'scbe chem <formula>',
  },
  {
    name: 'prime',
    aliases: [],
    category: 'compute',
    json: false,
    stability: 'partial',
    summary: 'Prime-number analysis (requires source checkout for scbe_calc.py).',
    usage: 'scbe prime <number>',
  },
  {
    name: 'emit',
    aliases: [],
    category: 'compute',
    json: false,
    stability: 'partial',
    summary: 'Emit an expression rendered in a Sacred Tongue.',
    usage: 'scbe emit <tongue> <expression>',
  },
  {
    name: 'infer',
    aliases: [],
    category: 'compute',
    json: true,
    stability: 'stub',
    summary: 'Mechanical worksheet inference (placeholder — limited matching).',
    usage: 'scbe infer "<sentence or task>" [--json]',
  },

  // ── CODING TOOLCHAIN (Sacred Tongue assembler + GeoSeal coding surface) ──────
  {
    name: 'geoseal',
    aliases: ['geocli'],
    category: 'coding',
    json: true,
    stability: 'real',
    summary:
      'GeoSeal coding toolchain: build weighted code packets, compile/run Sacred Tongue, round-trip source, scaffold projects, and tokenize — each step emits a replayable GeoSeal receipt.',
    usage: 'scbe geoseal <subcommand> [args]   (run "scbe geoseal --help" for the full list)',
    subcommands: [
      { name: 'code-packet', summary: 'Build an SCBE weighted code packet from a source file.' },
      { name: 'tongue-compile', summary: 'Compile a program into Sacred Tongue bytecode.' },
      { name: 'tongue-run', summary: 'Execute compiled Sacred Tongue bytecode.' },
      { name: 'code-roundtrip', summary: 'Round-trip source through the tongue IR and back.' },
      { name: 'project-scaffold', summary: 'Scaffold a governed project skeleton.' },
      { name: 'coding-trial', summary: 'Run a coding trial with execution receipts.' },
      { name: 'atomic', summary: 'Atomic tokenizer over source (ids + hex fingerprint).' },
      { name: 'verify', summary: 'Verify a sealed coding artifact.' },
    ],
    examples: [
      'scbe geoseal ops',
      'scbe geoseal code-packet --source-file foo.ts --source-name foo --language typescript',
    ],
  },
  {
    name: 'stasm',
    aliases: [],
    category: 'coding',
    json: false,
    stability: 'real',
    summary:
      'Sacred Tongue assembler (Phase-1): assemble .sts source into .stv bytecode the in-repo VM executes.',
    usage: 'scbe stasm <input.sts> [-o out.stv] [--listing]',
    examples: ['scbe stasm program.sts -o program.stv --listing'],
  },
  {
    name: 'store',
    aliases: [],
    category: 'storage',
    json: true,
    stability: 'real',
    summary:
      'Unified storage over rclone remotes (gdrive, onedrive, ...). Safe by default — list/read/pull/copy-up only, never deletes.',
    usage: 'scbe store <remotes|ls|pull|push|check> [args] [--json]',
    subcommands: [
      { name: 'remotes', summary: 'List configured rclone remotes.' },
      { name: 'ls', summary: 'List files at a remote path. e.g. scbe store ls gdrive:backups' },
      { name: 'pull', summary: 'Copy DOWN from remote to local (additive).' },
      { name: 'push', summary: 'Copy UP from local to remote (additive).' },
      { name: 'check', summary: 'Verify local vs remote match (read-only).' },
    ],
    examples: ['scbe store remotes --json', 'scbe store ls gdrive: --json'],
  },
  {
    name: 'mason',
    aliases: [],
    category: 'coding',
    json: true,
    stability: 'real',
    summary:
      'Build working code by setting pre-verified procedural "stones" into a schematic — each block verified in place by real execution; stubs are captured (never placed), big blocks/errors escalate to a bigger model.',
    usage: 'scbe mason <build|schematics> [name] [--inject-stub SLOT] [--json]',
    subcommands: [
      {
        name: 'build',
        summary:
          'Build a schematic into a verified, runnable artifact. e.g. scbe mason build pacman_core',
      },
      { name: 'schematics', summary: 'List available schematics.' },
    ],
    examples: [
      'scbe mason build pacman_core',
      'scbe mason build pacman_core --inject-stub game --json',
    ],
  },

  // ── LONGFORM / FLOW (governed long tasks with receipts) ─────────────────────
  {
    name: 'do',
    aliases: [],
    category: 'longform',
    json: true,
    stability: 'partial',
    summary: 'Durable governed agentic workflow (requires source checkout).',
    usage: 'scbe do "<objective>" [--loops N] [--land-every-stage] [--squad] [--json]',
  },
  {
    name: 'work',
    aliases: [],
    category: 'longform',
    json: true,
    stability: 'partial',
    summary: 'Longform workflow workspace (init/status/resume; requires source checkout).',
    usage: 'scbe work <init|status|resume> [--json]',
    subcommands: [
      { name: 'init', summary: 'Initialize a longform workflow workspace.' },
      { name: 'status', summary: 'Show bricks, landings, open questions.' },
      { name: 'resume', summary: 'Resume from latest (or specified) landing.' },
    ],
  },
  {
    name: 'land',
    aliases: [],
    category: 'longform',
    json: true,
    stability: 'partial',
    summary: 'Verified context landings — the resume contract (requires source checkout).',
    usage: 'scbe land <create|list|verify|show> [hash] [--json]',
    subcommands: [
      { name: 'create', summary: 'Create a verified context landing.' },
      { name: 'list', summary: 'List all landings with hash + timestamp.' },
      { name: 'verify', summary: "Verify a landing's cryptographic integrity." },
      { name: 'show', summary: 'Show full landing content.' },
    ],
  },
  {
    name: 'agent',
    aliases: [],
    category: 'longform',
    json: true,
    stability: 'partial',
    summary: 'Spawn/list governed agents in a workflow (requires source checkout).',
    usage: 'scbe agent <spawn|list> [--json]',
    subcommands: [
      { name: 'spawn', summary: 'Spawn a governed agent with a role contract.' },
      { name: 'list', summary: 'List agents in the current workflow.' },
    ],
  },
  {
    name: 'flow',
    aliases: [],
    category: 'longform',
    json: true,
    stability: 'real',
    summary:
      'Operator flow loop: decompose a task into governed packets and run them through the gate. Each packet run emits a real RuntimeGate receipt; DENY blocks with a reroute; failures carry a recovery plan.',
    usage: 'scbe flow <plan|packetize|status|run-next|continue|report> [--json]',
    subcommands: [
      { name: 'plan', summary: 'Decompose a task into a governed flow plan.' },
      { name: 'packetize', summary: 'Re-emit bounded work packets from a plan.' },
      { name: 'status', summary: 'Show pending/running/done packets.' },
      {
        name: 'run-next',
        summary: 'Run the next ready packet through the gate (--heal-retries N for self-healing).',
      },
      { name: 'continue', summary: 'Run all pending packets sequentially.' },
      { name: 'report', summary: 'Emit a governance summary.' },
    ],
    examples: ['scbe flow run-next --packets <bundle> --json'],
  },
  {
    name: 'workspace',
    aliases: [],
    category: 'longform',
    json: true,
    stability: 'real',
    summary: 'Audit-chain file bus: governed workspaces with versioned, signed snapshots.',
    usage: 'scbe workspace <new|ingest|export|import|verify|lineage|report> [--json]',
    subcommands: [
      { name: 'new', summary: 'Create a new workspace with an audit chain.' },
      { name: 'ingest', summary: 'Ingest a file into a workspace.' },
      { name: 'export', summary: 'Export workspace state as a versioned snapshot.' },
      { name: 'import', summary: 'Import a previously exported snapshot.' },
      { name: 'verify', summary: 'Verify export integrity (hash + signature).' },
      { name: 'lineage', summary: 'Print the audit lineage.' },
      { name: 'report', summary: 'Emit a governance summary.' },
    ],
  },
  {
    name: 'agent-bus',
    aliases: ['agentbus'],
    category: 'longform',
    json: true,
    stability: 'real',
    summary:
      'Governed multi-agent bus: route one task across free providers (Cerebras/Groq/Ollama/HF).',
    usage: 'scbe agent-bus <serve|send|upgrade> [--json]',
    subcommands: [
      { name: 'serve', summary: 'Start the local governed bus server.' },
      { name: 'send', summary: 'Dispatch a governed task envelope to the bus.' },
      { name: 'upgrade', summary: 'Check for bus package updates.' },
    ],
    examples: ['scbe agent-bus send --task "..." --task-type governance --json'],
  },

  // ── TONGUE / COMPILER / ROUTING ─────────────────────────────────────────────
  {
    name: 'compile-ca',
    aliases: [],
    category: 'tongue',
    json: false,
    stability: 'partial',
    summary: 'Compile Sacred Tongue opcodes into a function body (requires source checkout).',
    usage: 'scbe compile-ca --opcodes "0x09 ..." --target <lang> --fn <name> --args <a,b>',
  },
  {
    name: 'ca-plan',
    aliases: [],
    category: 'tongue',
    json: true,
    stability: 'partial',
    summary: 'Emit an opcode execution plan with mapping (requires source checkout).',
    usage: 'scbe ca-plan --ops "op op op" [--json]',
  },
  {
    name: 'render-op',
    aliases: [],
    category: 'tongue',
    json: false,
    stability: 'partial',
    summary: 'Render a single op in a Sacred Tongue surface (requires source checkout).',
    usage: 'scbe render-op --op <name> --target <tongue> --a <left> --b <right>',
  },
  {
    name: 'compile',
    aliases: [],
    category: 'tongue',
    json: false,
    stability: 'partial',
    summary: 'Compile a Sacred Tongue program (requires source checkout).',
    usage: 'scbe compile <program>',
  },
  {
    name: 'route',
    aliases: ['aetherpp'],
    category: 'tongue',
    json: false,
    stability: 'partial',
    summary:
      'Route a program to the best Sacred Tongue and emit a plan (requires source checkout).',
    usage: 'scbe route "<program>"',
  },
  {
    name: 'squad',
    aliases: [],
    category: 'tongue',
    json: true,
    stability: 'real',
    summary: 'Provider squad routing: status and task-class routing across units.',
    usage: 'scbe squad <status|route> [--json]',
    subcommands: [
      { name: 'status', summary: 'Show configured squad units, roles, reachability.' },
      { name: 'route', summary: 'Determine which unit handles a task class.' },
    ],
  },
  {
    name: 'xval',
    aliases: [],
    category: 'tongue',
    json: true,
    stability: 'real',
    summary: 'Cross-validate: fan a task out to all providers and score agreement.',
    usage: 'scbe xval --task "..." [--providers a,b,c] [--json]',
  },

  // ── BUNDLE / CONTENT ────────────────────────────────────────────────────────
  {
    name: 'bundle',
    aliases: [],
    category: 'content',
    json: true,
    stability: 'real',
    summary: 'Polyglot reaction bundles: create, hash-verify, translate, reconstruct.',
    usage: 'scbe bundle <create|add|verify|translate|reconstruct> [--json]',
    subcommands: [
      { name: 'create', summary: 'Create a bundle from a file or intent text.' },
      { name: 'add', summary: 'Add a file to a bundle (optional tongue role).' },
      { name: 'verify', summary: 'Verify bundle hashes.' },
      { name: 'translate', summary: 'Emit a receiver-ready projection.' },
      { name: 'reconstruct', summary: 'Emit reconstruction notes.' },
    ],
  },
  {
    name: 'react',
    aliases: [],
    category: 'content',
    json: true,
    stability: 'real',
    summary: 'Reaction packets: audit, compare, code-transform, audio-field observables.',
    usage: 'scbe react <audit|compare|code|audio> [--json]',
    subcommands: [
      { name: 'audit', summary: 'Audit a reaction packet or benchmark report.' },
      { name: 'compare', summary: 'Compare two reaction packet files.' },
      { name: 'code', summary: 'Emit a code/file transform reaction packet.' },
      { name: 'audio', summary: 'Audio-field observable reaction packet.' },
    ],
  },
  {
    name: 'youtube',
    aliases: [],
    category: 'content',
    json: true,
    stability: 'real',
    summary: 'Review a YouTube package JSON before upload.',
    usage: 'scbe youtube review <file> [--json]',
  },
  {
    name: 'foundry',
    aliases: [],
    category: 'content',
    json: true,
    stability: 'partial',
    summary:
      'Space-foundry research: seed → package → verify → coupon plan (requires source checkout).',
    usage: 'scbe foundry <workflow|package|verify|plan-coupon> [--json]',
    subcommands: [
      { name: 'workflow', summary: 'Run seed → package → verify → coupon-plan.' },
      { name: 'package', summary: 'Generate deterministic OpenSCAD + receipt.' },
      { name: 'verify', summary: 'Verify a receipt against the local SCAD hash.' },
      { name: 'plan-coupon', summary: 'Create a null-gated physical coupon measurement plan.' },
    ],
  },
];

const CATEGORY_ORDER = [
  'core',
  'shell',
  'run',
  'dev',
  'bench',
  'governance',
  'compute',
  'longform',
  'tongue',
  'content',
];

/** Flat, deduped, lowercase list of every verb + alias. Drives KNOWN_COMMANDS. */
function manifestCommandNames() {
  const names = new Set();
  for (const spec of COMMAND_SPECS) {
    names.add(spec.name.toLowerCase());
    for (const a of spec.aliases || []) {
      const key = String(a).toLowerCase();
      // Skip flag-style aliases (-h/--help/-v/--version) — they aren't verbs.
      if (!key.startsWith('-')) names.add(key);
    }
  }
  return Array.from(names);
}

/** Build the manifest object emitted by `scbe tools --json`. Deterministic. */
function buildToolsManifest() {
  const categories = Array.from(new Set(COMMAND_SPECS.map((s) => s.category)));
  categories.sort((a, b) => {
    const ia = CATEGORY_ORDER.indexOf(a);
    const ib = CATEGORY_ORDER.indexOf(b);
    return (ia < 0 ? 999 : ia) - (ib < 0 ? 999 : ib);
  });
  const commands = COMMAND_SPECS.map((s) => {
    const out = {
      name: s.name,
      aliases: (s.aliases || []).filter((a) => !String(a).startsWith('-')),
      category: s.category,
      summary: s.summary,
      json: Boolean(s.json),
      stability: s.stability,
      usage: s.usage || `scbe ${s.name}`,
    };
    if (s.subcommands && s.subcommands.length) out.subcommands = s.subcommands;
    if (s.examples && s.examples.length) out.examples = s.examples;
    return out;
  });
  const stabilityCounts = commands.reduce((acc, c) => {
    acc[c.stability] = (acc[c.stability] || 0) + 1;
    return acc;
  }, {});
  return {
    schema_version: 'scbe_tools_manifest_v1',
    tool: 'scbe',
    tool_version: readCliVersion(),
    description:
      'SCBE-AETHERMOORE governed command surface. Call any command as a tool; ' +
      'commands with "json": true accept --json for machine-readable output.',
    invocation: 'scbe <command> [subcommand] [options]',
    discovery: 'scbe tools --json',
    stability_legend: {
      real: 'handler executes genuine logic (or delegates to a present script)',
      partial: 'works but has a known limitation or requires a source checkout',
      stub: 'placeholder; does not yet do real work',
    },
    command_count: commands.length,
    stability_counts: stabilityCounts,
    error_schema: errorContract(),
    categories,
    commands,
  };
}

/** Human-readable rendering of the manifest for non-JSON `scbe tools`. */
function renderToolsHuman(manifest) {
  const lines = [];
  lines.push(
    `${manifest.tool} — ${manifest.command_count} commands${manifest.tool_version ? ` (v${manifest.tool_version})` : ''}`
  );
  lines.push(manifest.description);
  lines.push(`Discover as JSON: ${manifest.discovery}`);
  lines.push('');
  for (const cat of manifest.categories) {
    lines.push(`── ${cat.toUpperCase()} ──`);
    for (const c of manifest.commands.filter((x) => x.category === cat)) {
      const tag = c.stability === 'real' ? '' : `  [${c.stability}]`;
      const j = c.json ? ' (--json)' : '';
      lines.push(`  ${c.name}${j}${tag}`);
      lines.push(`      ${c.summary}`);
    }
    lines.push('');
  }
  return lines.join('\n').trimEnd();
}

module.exports = {
  COMMAND_SPECS,
  CATEGORY_ORDER,
  manifestCommandNames,
  buildToolsManifest,
  renderToolsHuman,
};
