/**
 * SCBE Compass command-line front door for the Agent Bus.
 *
 * This layer does not execute provider calls by itself. It produces a governed
 * route plan that the CLI, bus tools, or external operators can execute through
 * the existing dispatch surfaces.
 */

export type HermesTaskMode = 'compiler' | 'writing' | 'youtube' | 'model' | 'general';
export type ScbeCompassMode = HermesTaskMode;
export type ScbeFormation = 'forge' | 'scribe' | 'broadcast' | 'council' | 'scout' | 'field';
export type ScbeTongueDomain = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
export type ScbeBoardMechanic =
  | 'pazaak-hand'
  | 'go-board-territory'
  | 'octree-sector'
  | 'chessboard-stack';
export type ScbeRollKind =
  | 'human-input'
  | 'model-call'
  | 'api-call'
  | 'automation'
  | 'verification'
  | 'human-approval';

export interface HermesModelLane {
  id: string;
  label: string;
  costTier: 'offline' | 'local-free-after-install' | 'remote-free-tier-limited' | 'paid-remote';
  privacy: 'local_only' | 'remote_ok' | 'hosted_only';
  requires: string[];
  commandExample: string;
  notes: string;
}

export interface HermesRoutePlan {
  schema_version: 'scbe.agent_bus.hermes_route_plan.v1';
  generated_at: string;
  task: string;
  mode: HermesTaskMode;
  objective: string;
  primary_tools: string[];
  helper_actions: string[];
  model_lanes: HermesModelLane[];
  governance: {
    privacy: 'local_only';
    budget_cents: 0;
    first_gate: string;
    blocked_actions: string[];
  };
  cli_examples: string[];
}

export interface ScbeFormationStep {
  stage: string;
  action: string;
  tool?: string;
}

export interface ScbeCommandNode {
  path: string;
  domain: ScbeTongueDomain;
  tier: number;
  formation: ScbeFormation;
  label: string;
  tool?: string;
  children?: ScbeCommandNode[];
}

export interface ScbeOctreeContextPack {
  schema_version: 'scbe.agent_bus.octree_context_pack.v1';
  dense_local: string[];
  compressed_sparse: string[];
  heavily_compressed_anchor: string[];
  octree_retrieval: {
    surfaces: string[];
    source_notes: string[];
  };
}

export interface ScbeCliParityTarget {
  name: string;
  parity: string[];
  compass_plus: string[];
}

export interface ScbeBoardRule {
  mechanic: ScbeBoardMechanic;
  purpose: string;
  command_effect: string;
  source_paths: string[];
  schemas: string[];
  command_examples: string[];
}

export interface ScbeRollCard {
  id: string;
  kind: ScbeRollKind;
  title: string;
  instruction: string;
  inputs: string[];
  next_steps: string[];
  examples: string[];
  expected_output: {
    format: 'json' | 'markdown' | 'file' | 'terminal';
    required_fields: string[];
    acceptance: string[];
  };
  tools: string[];
  model_policy: {
    minimum_capability: 'offline-template' | 'small-local-llm' | 'remote-free-tier' | 'paid-remote';
    free_first: boolean;
    allowed_lanes: string[];
  };
  human_gate?: string;
}

export interface ScbeRollStackStep {
  index: number;
  roll_id: string;
  kind: ScbeRollKind;
  title: string;
  instruction: string;
  inputs: string[];
  expected_output: ScbeRollCard['expected_output'];
  tools: string[];
  human_gate?: string;
  next_roll: string | null;
}

export interface ScbeRollStackPlan {
  schema_version: 'scbe.agent_bus.roll_stack_plan.v1';
  generated_at: string;
  task: string;
  mode: ScbeCompassMode;
  command_path: string;
  formation: ScbeFormation;
  steps: ScbeRollStackStep[];
  acceptance: {
    requires_execution_receipt: boolean;
    no_remote_private_without_approval: boolean;
    no_public_publish_without_approval: boolean;
    output_contracts: string[];
  };
}

export interface ScbeCompassRoutePlan {
  schema_version: 'scbe.agent_bus.compass_route_plan.v1';
  command_surface: 'scbe-compass';
  generated_at: string;
  task: string;
  mode: ScbeCompassMode;
  formation: ScbeFormation;
  command_path: string;
  domain: ScbeTongueDomain;
  tier: number;
  objective: string;
  primary_tools: string[];
  formation_steps: ScbeFormationStep[];
  octree_context: ScbeOctreeContextPack;
  adapter_slots: string[];
  parity_targets: ScbeCliParityTarget[];
  board_rules: ScbeBoardRule[];
  roll_cards: ScbeRollCard[];
  helper_actions: string[];
  model_lanes: HermesModelLane[];
  governance: {
    privacy: 'local_only';
    budget_cents: 0;
    first_gate: string;
    blocked_actions: string[];
  };
  cli_examples: string[];
}

const MODEL_LANES: HermesModelLane[] = [
  {
    id: 'offline',
    label: 'Deterministic/offline harness',
    costTier: 'offline',
    privacy: 'local_only',
    requires: [],
    commandExample: 'scbe-agent-bus compass plan --task "..." --json',
    notes: 'No model call. Produces route plans, governance metadata, and benchmarkable packets.',
  },
  {
    id: 'ollama',
    label: 'Ollama local models',
    costTier: 'local-free-after-install',
    privacy: 'local_only',
    requires: ['ollama service', 'local model'],
    commandExample:
      'python scripts/system/terminal_ai_router.py call --prompt "..." --providers ollama',
    notes:
      'No provider bill after local install, but it still uses local hardware, electricity, time, and installed model capacity.',
  },
  {
    id: 'huggingface',
    label: 'Hugging Face router/models',
    costTier: 'remote-free-tier-limited',
    privacy: 'remote_ok',
    requires: ['HF_TOKEN for authenticated quota'],
    commandExample:
      'python scripts/system/terminal_ai_router.py call --prompt "..." --providers huggingface',
    notes:
      'Remote free-tier/low-cost lane with quotas and provider limits. Do not send secrets or private manuscript text without approval.',
  },
  {
    id: 'hosted',
    label: 'Hosted paid providers',
    costTier: 'paid-remote',
    privacy: 'hosted_only',
    requires: ['provider API key', 'budget approval'],
    commandExample:
      'python scripts/system/terminal_ai_router.py call --prompt "..." --providers openai,anthropic,xai',
    notes: 'Use only after budget and privacy gates are explicit.',
  },
];

const COMMAND_TREE: ScbeCommandNode[] = [
  {
    path: 'KO.command',
    domain: 'KO',
    tier: 1,
    formation: 'field',
    label: 'Task dispatch and governed execution',
    tool: 'geoseal-compile',
  },
  {
    path: 'AV.broadcast.youtube',
    domain: 'AV',
    tier: 2,
    formation: 'broadcast',
    label: 'Video, upload, transcript, and publishing transport',
    tool: 'youtube-video-review',
  },
  {
    path: 'RU.scout.research',
    domain: 'RU',
    tier: 2,
    formation: 'scout',
    label: 'Research, evidence gathering, and entropy exploration',
    tool: 'research-arxiv',
  },
  {
    path: 'CA.forge.compiler',
    domain: 'CA',
    tier: 1,
    formation: 'forge',
    label: 'Cross-language compilation and code generation',
    tool: 'geoseal-cross-build',
  },
  {
    path: 'UM.guardian.governance',
    domain: 'UM',
    tier: 1,
    formation: 'field',
    label: 'Governance scan, audit trail, and invariant checks',
    tool: 'geoseal-verify',
  },
  {
    path: 'DR.scribe.structure',
    domain: 'DR',
    tier: 1,
    formation: 'scribe',
    label: 'Documentation, writing, manuscript, and narrative structure',
    tool: 'writing-roundtable-review',
  },
  {
    path: 'KO+DR.architectural-command',
    domain: 'KO',
    tier: 4,
    formation: 'field',
    label: 'Hodge combo for architecture plus command routing',
    tool: 'scbe-agentbus',
  },
  {
    path: 'CA+UM.secure-computation',
    domain: 'CA',
    tier: 4,
    formation: 'forge',
    label: 'Hodge combo for compiler output under security invariants',
    tool: 'tokenizer-atomic-selfcheck',
  },
  {
    path: 'RU+AV.chaotic-research',
    domain: 'RU',
    tier: 4,
    formation: 'scout',
    label: 'Hodge combo for research discovery and transport',
    tool: 'research-hf-models',
  },
];

const PARITY_TARGETS: ScbeCliParityTarget[] = [
  {
    name: 'Claude Code',
    parity: ['multi-file repo edits', 'MCP/tool integration', 'long-running coding loop'],
    compass_plus: ['SCBE formations', 'tool receipts', 'octree context packs'],
  },
  {
    name: 'OpenAI Codex CLI',
    parity: ['local terminal operation', 'sandbox/permission profiles', 'repo-aware execution'],
    compass_plus: [
      'GeoSeal governance gate',
      'durable trajectory state',
      'patent-surface tool audit',
    ],
  },
  {
    name: 'Gemini CLI',
    parity: ['open CLI distribution', 'low-friction model access', 'ecosystem adapters'],
    compass_plus: [
      'local/free-tier/paid cost boundaries',
      'adapter benchmark gate',
      'sphere-grid hierarchy',
    ],
  },
];

export function classifyHermesTask(task: string): HermesTaskMode {
  return classifyScbeCompassTask(task);
}

export function classifyScbeCompassTask(task: string): ScbeCompassMode {
  const t = task.toLowerCase();
  if (/\b(youtube|upload|thumbnail|transcript|video|shorts?)\b/.test(t)) return 'youtube';
  if (/\b(write|writing|article|blog|manuscript|chapter|script|newsletter|book)\b/.test(t)) {
    return 'writing';
  }
  if (
    /\b(cross[- ]?language|compiler|compile|binary|hex|hexa|tokenizer|interpolation|ir)\b/.test(t)
  ) {
    return 'compiler';
  }
  if (/\b(model|ollama|huggingface|openai|anthropic|gemini|router|api call)\b/.test(t)) {
    return 'model';
  }
  return 'general';
}

export function hermesModelLanes(): readonly HermesModelLane[] {
  return scbeCompassModelLanes();
}

export function scbeCompassModelLanes(): readonly HermesModelLane[] {
  return MODEL_LANES;
}

export function planHermesRoute(task: string): HermesRoutePlan {
  const compass = planScbeCompassRoute(task);
  return {
    schema_version: 'scbe.agent_bus.hermes_route_plan.v1',
    generated_at: compass.generated_at,
    task: compass.task,
    mode: compass.mode,
    objective: compass.objective,
    primary_tools: compass.primary_tools,
    helper_actions: compass.helper_actions,
    model_lanes: compass.model_lanes,
    governance: compass.governance,
    cli_examples: compass.cli_examples.map((example) =>
      example.replace('scbe-agent-bus compass', 'scbe-agent-bus hermes')
    ),
  };
}

export function planScbeCompassRoute(task: string): ScbeCompassRoutePlan {
  const trimmed = task.trim();
  const mode = classifyScbeCompassTask(trimmed);
  const primaryTools = primaryToolsForMode(mode);
  const helperActions = helperActionsForMode(mode);
  const formation = formationForMode(mode);
  const commandNode = commandNodeForMode(mode);

  return {
    schema_version: 'scbe.agent_bus.compass_route_plan.v1',
    command_surface: 'scbe-compass',
    generated_at: new Date().toISOString(),
    task: trimmed,
    mode,
    formation,
    command_path: commandNode.path,
    domain: commandNode.domain,
    tier: commandNode.tier,
    objective: objectiveForMode(mode),
    primary_tools: primaryTools,
    formation_steps: formationStepsForMode(mode),
    octree_context: buildOctreeContextPack(mode, trimmed),
    adapter_slots: adapterSlotsForMode(mode),
    parity_targets: PARITY_TARGETS,
    board_rules: boardRulesForMode(mode),
    roll_cards: rollCardsForMode(mode),
    helper_actions: helperActions,
    model_lanes: MODEL_LANES,
    governance: {
      privacy: 'local_only',
      budget_cents: 0,
      first_gate: 'geoseal compile + tool registry audit before provider/model dispatch',
      blocked_actions: [
        'public YouTube publish without explicit approval',
        'remote provider call containing secrets or private manuscript text without approval',
        'arbitrary cross-language code translation outside Tier 1 LatticeOp coverage',
      ],
    },
    cli_examples: cliExamplesForMode(mode, trimmed),
  };
}

export function scbeCompassCommandTree(): readonly ScbeCommandNode[] {
  return COMMAND_TREE;
}

export function scbeCompassParityTargets(): readonly ScbeCliParityTarget[] {
  return PARITY_TARGETS;
}

export function scbeCompassBoardRules(mode: HermesTaskMode = 'general'): readonly ScbeBoardRule[] {
  return boardRulesForMode(mode);
}

export function scbeCompassRollCards(mode: HermesTaskMode = 'general'): readonly ScbeRollCard[] {
  return rollCardsForMode(mode);
}

export function buildScbeRollStack(task: string): ScbeRollStackPlan {
  const route = planScbeCompassRoute(task);
  const steps = route.roll_cards.map((card, index, cards): ScbeRollStackStep => {
    const nextCard = cards[index + 1];
    return {
      index,
      roll_id: card.id,
      kind: card.kind,
      title: card.title,
      instruction: card.instruction,
      inputs: [...card.inputs],
      expected_output: {
        format: card.expected_output.format,
        required_fields: [...card.expected_output.required_fields],
        acceptance: [...card.expected_output.acceptance],
      },
      tools: [...card.tools],
      ...(card.human_gate ? { human_gate: card.human_gate } : {}),
      next_roll: nextCard ? nextCard.id : null,
    };
  });

  return {
    schema_version: 'scbe.agent_bus.roll_stack_plan.v1',
    generated_at: new Date().toISOString(),
    task: route.task,
    mode: route.mode,
    command_path: route.command_path,
    formation: route.formation,
    steps,
    acceptance: {
      requires_execution_receipt: true,
      no_remote_private_without_approval: true,
      no_public_publish_without_approval: true,
      output_contracts: route.roll_cards.map(
        (card) => `${card.id}:${card.expected_output.required_fields.join(',')}`
      ),
    },
  };
}

function commandNodeForMode(mode: HermesTaskMode): ScbeCommandNode {
  if (mode === 'compiler') return COMMAND_TREE.find((n) => n.path === 'CA.forge.compiler')!;
  if (mode === 'writing') return COMMAND_TREE.find((n) => n.path === 'DR.scribe.structure')!;
  if (mode === 'youtube') return COMMAND_TREE.find((n) => n.path === 'AV.broadcast.youtube')!;
  if (mode === 'model') return COMMAND_TREE.find((n) => n.path === 'KO+DR.architectural-command')!;
  return COMMAND_TREE.find((n) => n.path === 'KO.command')!;
}

function buildOctreeContextPack(mode: HermesTaskMode, task: string): ScbeOctreeContextPack {
  return {
    schema_version: 'scbe.agent_bus.octree_context_pack.v1',
    dense_local: [
      'current user task',
      'active CLI flags',
      'latest tool output',
      `mode:${mode}`,
      `task_chars:${task.length}`,
    ],
    compressed_sparse: [
      'relevant tool registry entries',
      'README command docs',
      'focused tests and benchmark cases',
    ],
    heavily_compressed_anchor: [
      'local_only by default',
      'budget_cents=0 by default',
      'public publish and paid providers require explicit approval',
      'cross-domain translation must pass the governed compiler surface',
    ],
    octree_retrieval: {
      surfaces: [
        'dense local view',
        'compressed sparse view',
        'heavily compressed anchor view',
        'octree spatial / structural retrieval',
      ],
      source_notes: [
        'notes/round-table/2026-05-01-night-agentic-public-ai-and-runtime-routing.md',
        'notes/sphere-grid/Agentic Sphere Grid.md',
        'notes/theory/ai-mind-map.md',
      ],
    },
  };
}

function boardRulesForMode(mode: HermesTaskMode): ScbeBoardRule[] {
  const rules: ScbeBoardRule[] = [
    {
      mechanic: 'octree-sector',
      purpose: 'Place the task into a sparse spatial context sector before execution.',
      command_effect: 'Compass route includes dense/sparse/anchor/octree context surfaces.',
      source_paths: [
        'notes/sphere-grid/Agentic Sphere Grid.md',
        'notes/round-table/2026-05-01-night-agentic-public-ai-and-runtime-routing.md',
        'src/crypto/octree.py',
        'src/ai_brain/quasi-space.ts',
        'hydra/octree_sphere_grid.py',
        'src/kernel/context_grid.py',
      ],
      schemas: ['scbe.agent_bus.octree_context_pack.v1'],
      command_examples: ['scbe-agent-bus compass tree --json'],
    },
    {
      mechanic: 'go-board-territory',
      purpose:
        'Treat tools, files, tests, and receipts as occupied territory on a legal-move board.',
      command_effect:
        'A command is legal only when prerequisites and adjacent verification stones exist.',
      source_paths: [
        'src/coding_board/pipeline.py',
        'src/coding_board/probe.py',
        'src/coding_board/__init__.py',
        'tests/coding_board/test_coding_board.py',
      ],
      schemas: ['scbe-coding-trial-v1'],
      command_examples: [
        'python -m src.geoseal_cli coding-trial --goal "compile candidate" --tool git.status --json -- python -m py_compile src/coding_board/__init__.py',
      ],
    },
    {
      mechanic: 'pazaak-hand',
      purpose:
        'Hold optional modifier cards that can nudge a route without changing the base formation.',
      command_effect:
        'Future flags can apply budget, privacy, model, verifier, or target-language modifiers.',
      source_paths: [
        'scripts/system/agentic_pazaak_board.py',
        'config/eval/agentic_pazaak_cards.v1.json',
        'tests/system/test_agentic_pazaak_board.py',
      ],
      schemas: ['scbe_agentic_pazaak_board_report_v1', 'scbe_agentic_pazaak_cards_v1'],
      command_examples: ['python scripts/system/agentic_pazaak_board.py --limit 5'],
    },
    {
      mechanic: 'chessboard-stack',
      purpose:
        'Generate role packets for Spec Kit, BMAD, GSD, Superpowers, and task-promotion lanes.',
      command_effect:
        'A command can be decomposed into named chessboard packets before model dispatch.',
      source_paths: [
        'scripts/system/chessboard_dev_stack.py',
        'workflows/momentum/chessboard_dev_stack_train.json',
        'docs/specs/AGENTIC_DEV_CHESSBOARD_STACK.md',
      ],
      schemas: ['scbe_chessboard_packets_v1'],
      command_examples: [
        'python scripts/system/chessboard_dev_stack.py --goal "improve agentic CLI"',
      ],
    },
  ];
  if (mode === 'compiler') {
    return [
      ...rules,
      {
        mechanic: 'go-board-territory',
        purpose:
          'Prevent arbitrary target-language emission from jumping over the IR intersection point.',
        command_effect:
          'Tier 1 compiles through LatticeOp; Tier 2 must prove parser-backed lift first.',
        source_paths: [
          'src/coding_board/pipeline.py',
          'src/coding_board/probe.py',
          'tests/coding_board/test_coding_board.py',
          'src/geoseal_cli.py',
        ],
        schemas: ['scbe-coding-trial-v1', 'scbe_command_plan_v1'],
        command_examples: [
          'python src/geoseal_cli.py cross-build --src-code "(x + y)" --src-tongue KO --dst-tongue RU',
          'python -m src.geoseal_cli coding-trial --goal "compiler lift" --tool geoseal-cross-build --json -- python -m py_compile src/coding_board/pipeline.py',
        ],
      },
    ];
  }
  return rules;
}

function baseRollCards(): ScbeRollCard[] {
  return [
    {
      id: 'roll.collect-human-input',
      kind: 'human-input',
      title: 'Collect missing operator facts',
      instruction:
        'Ask only for facts required by the next step. Do not invent credentials, file paths, publication settings, prices, titles, or approvals.',
      inputs: ['task', 'known_context', 'missing_fields'],
      next_steps: [
        'List the missing fields as short questions.',
        'Accept partial answers and keep unknown fields marked unknown.',
        'Return a structured input packet for the next roll.',
      ],
      examples: [
        'Ask for target URL before website audit.',
        'Ask for video title and source file before YouTube upload prep.',
      ],
      expected_output: {
        format: 'json',
        required_fields: ['questions', 'known_context', 'unknown_fields', 'next_roll'],
        acceptance: [
          'No fabricated values',
          'At most five questions',
          'Every unknown remains explicitly marked',
        ],
      },
      tools: [],
      model_policy: {
        minimum_capability: 'offline-template',
        free_first: true,
        allowed_lanes: ['offline', 'ollama', 'huggingface'],
      },
    },
    {
      id: 'roll.execute-bounded-local-tool',
      kind: 'automation',
      title: 'Execute bounded local tool and capture receipt',
      instruction:
        'Run the selected local/offline tool with bounded inputs. Capture stdout, stderr tail, exit code, runtime, and a receipt hash. Do not mutate files, publish, spend money, or call remote providers unless the prior roll granted that gate.',
      inputs: ['validated_input_packet', 'tool_name', 'expected_output', 'governance'],
      next_steps: [
        'Resolve the local tool from the registry.',
        'Run it with bounded arguments and a timeout.',
        'Capture execution evidence, including exit_code, duration_ms, and receipt_hash.',
        'Send the execution packet to the verifier roll.',
      ],
      examples: [
        'Run roll-stack-maze-benchmark locally and capture the JSON report.',
        'Run geoseal-cross-build-broadcast after the input contract passes.',
      ],
      expected_output: {
        format: 'json',
        required_fields: [
          'tool',
          'exit_code',
          'duration_ms',
          'stdout',
          'stderr_tail',
          'receipt_hash',
        ],
        acceptance: [
          'exit_code is numeric',
          'receipt_hash is derived from executed input and output',
          'No blocked action occurred without a human gate',
        ],
      },
      tools: ['scbe-agentbus'],
      model_policy: {
        minimum_capability: 'offline-template',
        free_first: true,
        allowed_lanes: ['offline'],
      },
    },
    {
      id: 'roll.verify-output-contract',
      kind: 'verification',
      title: 'Verify output shape before execution',
      instruction:
        'Check the previous roll result against required fields, blocked actions, and human gates before any tool/API execution.',
      inputs: ['roll_result', 'expected_output', 'governance'],
      next_steps: [
        'Validate required fields.',
        'Reject public publish, paid API, or secret-bearing remote calls without explicit approval.',
        'Emit pass/fail with exact missing fields and next repair roll.',
      ],
      examples: [
        'Fail if YouTube publish visibility is public.',
        'Fail if a remote model call includes private manuscript text without approval.',
      ],
      expected_output: {
        format: 'json',
        required_fields: ['ok', 'missing_fields', 'blocked_actions', 'next_roll'],
        acceptance: [
          'PASS only when all required fields exist',
          'Blocked actions are explicit',
          'Repair path is named when failing',
        ],
      },
      tools: ['geoseal-compile', 'geoseal-verify'],
      model_policy: {
        minimum_capability: 'offline-template',
        free_first: true,
        allowed_lanes: ['offline'],
      },
    },
  ];
}

function rollCardsForMode(mode: HermesTaskMode): ScbeRollCard[] {
  const shared = baseRollCards();
  if (mode === 'youtube') {
    return [
      ...shared,
      {
        id: 'roll.youtube-upload-prep',
        kind: 'automation',
        title: 'Prepare YouTube upload packet',
        instruction:
          'Build an upload-prep packet from source title, description, transcript/article, tags, and visibility. Never publish publicly; use unlisted-first only.',
        inputs: ['source_file_or_article', 'title', 'description', 'tags', 'visibility'],
        next_steps: [
          'Inspect or summarize the source content.',
          'Draft title, description, tags, and pinned-comment candidates.',
          'Run metadata review.',
          'Prepare unlisted upload command only after human approval.',
        ],
        examples: [
          'python scripts/apollo/video_review.py review-all',
          'python scripts/publish/youtube_video_tool.py build --source content/articles/example.md',
        ],
        expected_output: {
          format: 'json',
          required_fields: ['title', 'description', 'tags', 'visibility', 'review_command'],
          acceptance: [
            'visibility is unlisted or draft',
            'title and description are non-empty',
            'human approval is required before upload',
          ],
        },
        tools: ['youtube-video-review', 'youtube-article-dry-run', 'youtube-upload-unlisted'],
        model_policy: {
          minimum_capability: 'small-local-llm',
          free_first: true,
          allowed_lanes: ['offline', 'ollama', 'huggingface'],
        },
        human_gate: 'Approve title, description, tags, source file, and unlisted visibility.',
      },
    ];
  }
  if (mode === 'writing') {
    return [
      ...shared,
      {
        id: 'roll.writing-draft-review',
        kind: 'model-call',
        title: 'Draft and review a writing packet',
        instruction:
          'Turn source notes into a structured draft packet, then review for claims, tone, missing evidence, and next edits.',
        inputs: ['source_notes', 'audience', 'format', 'target_length'],
        next_steps: [
          'Create outline.',
          'Draft the smallest useful section.',
          'List unsupported claims.',
          'Return revision tasks instead of publishing.',
        ],
        examples: [
          'scbe-agent-bus send --tool writing-roundtable-review --task "content/articles/example.md" --json',
        ],
        expected_output: {
          format: 'markdown',
          required_fields: ['outline', 'draft', 'unsupported_claims', 'next_edits'],
          acceptance: [
            'Keeps source wording where requested',
            'Flags unsupported claims',
            'Does not publish or send externally',
          ],
        },
        tools: ['writing-roundtable-review'],
        model_policy: {
          minimum_capability: 'small-local-llm',
          free_first: true,
          allowed_lanes: ['offline', 'ollama', 'huggingface'],
        },
      },
    ];
  }
  if (mode === 'compiler') {
    return [
      ...shared,
      {
        id: 'roll.cross-language-compile',
        kind: 'automation',
        title: 'Compile through governed lattice IR',
        instruction:
          'Use only supported Tier 1 expressions unless a parser-backed lift is present. Quarantine arbitrary source code.',
        inputs: ['src_code', 'src_tongue', 'dst_tongue'],
        next_steps: [
          'Check the source expression against Tier 1 LatticeOp coverage.',
          'Run cross-build.',
          'Emit destination code plus IR provenance.',
          'Quarantine unsupported code with the reason.',
        ],
        examples: [
          'python src/geoseal_cli.py cross-build --src-code "(x + y)" --src-tongue KO --dst-tongue RU',
        ],
        expected_output: {
          format: 'json',
          required_fields: ['src_tongue', 'dst_tongue', 'ir', 'dst_code', 'verdict'],
          acceptance: [
            'Supported operation has IR provenance',
            'Unsupported source returns QUARANTINE',
            'No arbitrary AST translation claim',
          ],
        },
        tools: ['geoseal-cross-build', 'semantic-hex-bridge', 'tokenizer-atomic-selfcheck'],
        model_policy: {
          minimum_capability: 'offline-template',
          free_first: true,
          allowed_lanes: ['offline'],
        },
      },
    ];
  }
  if (mode === 'model') {
    return [
      ...shared,
      {
        id: 'roll.free-model-dispatch',
        kind: 'api-call',
        title: 'Dispatch to cheapest allowed model lane',
        instruction:
          'Try offline/local first, then remote free-tier only when the input is safe to send. Paid providers require explicit budget approval.',
        inputs: ['prompt', 'privacy_level', 'budget_cents', 'allowed_providers'],
        next_steps: [
          'Check privacy and budget.',
          'Run provider health check.',
          'Select offline, Ollama, or Hugging Face before paid lanes.',
          'Record provider, model, quota note, and output contract.',
        ],
        examples: [
          'scbe-agent-bus send --tool ai-router-health --task "provider check" --json',
          'python scripts/system/terminal_ai_router.py call --prompt "..." --providers ollama,huggingface',
        ],
        expected_output: {
          format: 'json',
          required_fields: ['selected_lane', 'provider', 'model', 'cost_tier', 'quota_note'],
          acceptance: [
            'No paid provider when budget_cents is 0',
            'No secrets sent to remote free-tier',
            'Provider metadata is recorded',
          ],
        },
        tools: ['ai-router-health', 'ai-router-call'],
        model_policy: {
          minimum_capability: 'remote-free-tier',
          free_first: true,
          allowed_lanes: ['offline', 'ollama', 'huggingface'],
        },
        human_gate: 'Approve any paid or remote-private model call.',
      },
    ];
  }
  return shared;
}

function adapterSlotsForMode(mode: HermesTaskMode): string[] {
  const shared = [
    'tool-registry adapter for any CLI with deterministic argv',
    'model-provider adapter with local/free-tier/paid cost metadata',
    'receipt adapter for replayable JSON evidence',
    'benchmark adapter for pass/fail and latency evidence',
  ];
  if (mode === 'compiler') {
    return [
      ...shared,
      'parser adapter for Tree-sitter/Babel/other AST front ends',
      'IR adapter for MLIR-style dialect lowering into LatticeOp',
      'target-language emitter adapter',
    ];
  }
  if (mode === 'youtube' || mode === 'writing') {
    return [
      ...shared,
      'content-source adapter for articles, transcripts, manuscripts, and notes',
      'media-render adapter for local renderers or external video APIs',
      'publisher adapter for unlisted-first YouTube and other channels',
    ];
  }
  if (mode === 'model') {
    return [
      ...shared,
      'OpenAI-compatible chat adapter',
      'Ollama/local HTTP adapter',
      'Hugging Face/free-tier adapter',
      'structured-output validator adapter',
    ];
  }
  return shared;
}

function primaryToolsForMode(mode: HermesTaskMode): string[] {
  if (mode === 'youtube') {
    return ['youtube-video-review', 'youtube-article-dry-run', 'youtube-upload-unlisted'];
  }
  if (mode === 'writing') {
    return ['writing-roundtable-review', 'youtube-article-dry-run', 'ai-router-call'];
  }
  if (mode === 'compiler') {
    return [
      'geoseal-cross-build',
      'geoseal-encode',
      'semantic-hex-bridge',
      'tokenizer-atomic-selfcheck',
    ];
  }
  if (mode === 'model') {
    return ['ai-router-health', 'ai-router-call', 'research-hf-models'];
  }
  return ['geoseal-compile', 'scbe-agentbus', 'ai-router-health'];
}

function helperActionsForMode(mode: HermesTaskMode): string[] {
  if (mode === 'youtube') {
    return [
      'review uploaded/video candidate metadata before generation',
      'dry-run article-to-video before rendering',
      'upload unlisted only after local artifact exists',
    ];
  }
  if (mode === 'writing') {
    return [
      'route draft through local/offline helper first',
      'run round-table review on structure and claims',
      'only escalate to remote model after privacy approval',
    ];
  }
  if (mode === 'compiler') {
    return [
      'compile to LatticeOp IR before target-language emission',
      'emit binary/hex semantic packet for audit',
      'quarantine arbitrary code until Tier 2 AST lift exists',
    ];
  }
  if (mode === 'model') {
    return [
      'health-check provider availability without exposing secrets',
      'prefer local Ollama, then free Hugging Face, then paid providers',
      'record provider/model metadata and spend estimate',
    ];
  }
  return ['compile intent', 'audit tool readiness', 'execute only after governance gate'];
}

function objectiveForMode(mode: HermesTaskMode): string {
  if (mode === 'youtube') return 'governed writing-to-video and upload pipeline';
  if (mode === 'writing') return 'local-first writing helper and publication prep pipeline';
  if (mode === 'compiler') return 'cross-domain compiler with binary/hex transport evidence';
  if (mode === 'model') return 'cheap-first model routing with local/free options';
  return 'general governed agent-bus task route';
}

function formationForMode(mode: HermesTaskMode): ScbeFormation {
  if (mode === 'compiler') return 'forge';
  if (mode === 'writing') return 'scribe';
  if (mode === 'youtube') return 'broadcast';
  if (mode === 'model') return 'council';
  return 'field';
}

function formationStepsForMode(mode: HermesTaskMode): ScbeFormationStep[] {
  if (mode === 'compiler') {
    return [
      { stage: 'gate', action: 'compile intent and audit tool readiness', tool: 'geoseal-compile' },
      {
        stage: 'lift',
        action: 'lower supported expression into LatticeOp IR',
        tool: 'geoseal-cross-build',
      },
      {
        stage: 'seal',
        action: 'emit semantic binary/hex transport evidence',
        tool: 'semantic-hex-bridge',
      },
      {
        stage: 'verify',
        action: 'run atomic tokenizer transport self-check',
        tool: 'tokenizer-atomic-selfcheck',
      },
    ];
  }
  if (mode === 'writing') {
    return [
      { stage: 'gate', action: 'keep the draft local-first until privacy is explicit' },
      {
        stage: 'draft',
        action: 'route through writing review formation',
        tool: 'writing-roundtable-review',
      },
      {
        stage: 'package',
        action: 'prepare article/video dry-run when the draft is publishable',
        tool: 'youtube-article-dry-run',
      },
    ];
  }
  if (mode === 'youtube') {
    return [
      { stage: 'inspect', action: 'review channel/upload metadata', tool: 'youtube-video-review' },
      {
        stage: 'render-check',
        action: 'dry-run article-to-video before generating media',
        tool: 'youtube-article-dry-run',
      },
      {
        stage: 'release-gate',
        action: 'upload unlisted only; public publish requires human approval',
        tool: 'youtube-upload-unlisted',
      },
    ];
  }
  if (mode === 'model') {
    return [
      {
        stage: 'health',
        action: 'check provider/model availability without exposing secrets',
        tool: 'ai-router-health',
      },
      {
        stage: 'route',
        action: 'prefer offline/local, then quota-limited remote free tier, then paid provider',
        tool: 'ai-router-call',
      },
      { stage: 'audit', action: 'record provider, model, quota, and estimated spend metadata' },
    ];
  }
  return [
    { stage: 'gate', action: 'compile the intent before execution', tool: 'geoseal-compile' },
    { stage: 'route', action: 'select a bus tool or local agent route', tool: 'scbe-agentbus' },
    { stage: 'verify', action: 'keep the result tied to receipts and state' },
  ];
}

function cliExamplesForMode(mode: HermesTaskMode, task: string): string[] {
  const q = JSON.stringify(task || 'your task');
  const examples = [
    `scbe-agent-bus compass plan --task ${q} --json`,
    `scbe-agent-bus pipeline compile --intent ${q} --governed-state --json`,
  ];
  if (mode === 'youtube') {
    examples.push(
      'scbe-agent-bus send --tool youtube-video-review --task "review all uploads" --json'
    );
    examples.push(
      'scbe-agent-bus send --tool youtube-article-dry-run --task "content/articles/example.md" --json'
    );
  } else if (mode === 'writing') {
    examples.push(
      'scbe-agent-bus send --tool writing-roundtable-review --task "content/articles/example.md" --json'
    );
  } else if (mode === 'compiler') {
    examples.push(
      'python src/geoseal_cli.py cross-build --src-code "(x + y)" --src-tongue KO --dst-tongue RU'
    );
  } else if (mode === 'model') {
    examples.push('scbe-agent-bus send --tool ai-router-health --task "provider check" --json');
  }
  return examples;
}
