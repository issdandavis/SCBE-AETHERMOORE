import { execFile } from 'node:child_process';
import { mkdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

export const PLUGIN_ID = 'scbe-system-tools';
export const DEFAULT_REPO_ROOT = 'C:/Users/issda/SCBE-AETHERMOORE';
export const DEFAULT_TIMEOUT_MS = 120_000;
export const DEFAULT_LOCAL_BASE_URL = 'http://localhost:1234/v1';

type Provider = 'auto' | 'local' | 'hf';
type WorkflowTemplate = 'architecture-enhancement' | 'implementation-loop' | 'training-center-loop';
type FlowFormation =
  | 'adaptive-scatter'
  | 'concentric'
  | 'hexagonal'
  | 'hexagonal-ring'
  | 'ring'
  | 'scatter'
  | 'tetrahedral';
type DispatchLane =
  | 'none'
  | 'octoarmor-triage'
  | 'hydra-swarm'
  | 'browse-evidence'
  | 'colab-bridge-status'
  | 'colab-bridge-probe';
type HygieneAction = 'status' | 'apply' | 'clear';
type ColabBridgeAction = 'status' | 'env' | 'probe';

type PluginConfig = {
  repoRoot?: string;
  pythonBin?: string;
  timeoutMs?: number;
  defaultProvider?: Provider;
  defaultLocalBaseUrl?: string;
};

type CommandSpec = {
  command: string;
  args: string[];
  cwd: string;
  artifactPath?: string;
};

export function resolvePluginConfig(input: PluginConfig | undefined): Required<PluginConfig> {
  return {
    repoRoot: input?.repoRoot?.trim() || DEFAULT_REPO_ROOT,
    pythonBin: input?.pythonBin?.trim() || 'python',
    timeoutMs:
      typeof input?.timeoutMs === 'number' && Number.isFinite(input.timeoutMs)
        ? Math.min(Math.max(Math.trunc(input.timeoutMs), 1000), 600000)
        : DEFAULT_TIMEOUT_MS,
    defaultProvider: input?.defaultProvider || 'auto',
    defaultLocalBaseUrl: input?.defaultLocalBaseUrl?.trim() || DEFAULT_LOCAL_BASE_URL,
  };
}

export function slugify(text: string): string {
  const cleaned = text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return cleaned || 'task';
}

export function makeRunStamp(now: Date = new Date()): string {
  const iso = now.toISOString();
  return iso.replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
}

function toRepoRelative(repoRoot: string, targetPath: string): string {
  return path.relative(repoRoot, targetPath).split(path.sep).join('/');
}

async function ensureArtifactDir(artifactPath: string): Promise<void> {
  await mkdir(path.dirname(artifactPath), { recursive: true });
}

function extractLastJson(stdout: string): unknown {
  const lines = stdout
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  for (let index = lines.length - 1; index >= 0; index -= 1) {
    try {
      return JSON.parse(lines[index]);
    } catch {
      // Walk backward until a JSON line is found.
    }
  }
  return null;
}

async function runCommand(spec: CommandSpec, cfg: Required<PluginConfig>): Promise<string> {
  try {
    const result = await execFileAsync(spec.command, spec.args, {
      cwd: spec.cwd,
      timeout: cfg.timeoutMs,
      windowsHide: true,
      maxBuffer: 4 * 1024 * 1024,
    });

    if (spec.artifactPath) {
      const artifact = await readFile(spec.artifactPath, 'utf-8');
      return artifact;
    }

    const parsed = extractLastJson(result.stdout);
    if (parsed !== null) {
      return JSON.stringify(parsed, null, 2);
    }

    const combined = [result.stdout.trim(), result.stderr.trim()].filter(Boolean).join('\n');
    return combined || 'Command completed with no output.';
  } catch (error) {
    const err = error as NodeJS.ErrnoException & {
      stdout?: string;
      stderr?: string;
      code?: string | number;
    };
    const parts = [
      `Command failed: ${spec.command} ${spec.args.join(' ')}`,
      err.message,
      err.stdout?.trim(),
      err.stderr?.trim(),
    ].filter(Boolean);
    throw new Error(parts.join('\n\n'));
  }
}

export function buildFlowPlanCommand(
  cfg: Required<PluginConfig>,
  params: {
    task: string;
    formation?: FlowFormation;
    workflowTemplate?: WorkflowTemplate;
    emitActionMap?: boolean;
  },
  stamp: string = makeRunStamp(),
): CommandSpec {
  const slug = slugify(params.task);
  const artifactPath = path.join(cfg.repoRoot, 'artifacts', 'openclaw-plugin', `${stamp}-${slug}-flow-plan.json`);
  const actionRoot = path.join(cfg.repoRoot, 'artifacts', 'openclaw-plugin', `${stamp}-${slug}-action-map`);
  return {
    command: cfg.pythonBin,
    cwd: cfg.repoRoot,
    artifactPath,
    args: [
      'scripts/scbe-system-cli.py',
      'flow',
      'plan',
      '--task',
      params.task,
      '--formation',
      params.formation || 'hexagonal-ring',
      '--workflow-template',
      params.workflowTemplate || 'implementation-loop',
      '--output',
      toRepoRelative(cfg.repoRoot, artifactPath),
      ...(params.emitActionMap === false
        ? ['--no-action-map']
        : ['--action-root', toRepoRelative(cfg.repoRoot, actionRoot)]),
    ],
  };
}

export function buildOctoarmsDispatchCommand(
  cfg: Required<PluginConfig>,
  params: {
    task: string;
    lane?: DispatchLane;
    formation?: FlowFormation;
    workflowTemplate?: WorkflowTemplate;
    provider?: Provider;
    model?: string;
    backend?: 'playwright' | 'selenium' | 'cdp';
    baseUrl?: string;
    bridgeName?: string;
    url?: string;
    dryRun?: boolean;
    emitActionMap?: boolean;
  },
): CommandSpec {
  const args = [
    'scripts/system/octoarms_dispatch.py',
    '--repo-root',
    cfg.repoRoot,
    '--task',
    params.task,
    '--formation',
    params.formation || 'hexagonal-ring',
    '--workflow-template',
    params.workflowTemplate || 'implementation-loop',
    '--provider',
    params.provider || cfg.defaultProvider,
    '--backend',
    params.backend || 'playwright',
    '--base-url',
    params.baseUrl || cfg.defaultLocalBaseUrl,
    '--lane',
    params.lane || 'octoarmor-triage',
    '--bridge-name',
    params.bridgeName || 'pivot',
    '--json',
  ];
  if (params.model) {
    args.push('--model', params.model);
  }
  if (params.url) {
    args.push('--url', params.url);
  }
  if (params.dryRun !== false) {
    args.push('--dry-run');
  }
  if (params.emitActionMap === false) {
    args.push('--no-action-map');
  }
  return {
    command: cfg.pythonBin,
    cwd: cfg.repoRoot,
    args,
  };
}

export function buildLocalGitHygieneCommand(
  cfg: Required<PluginConfig>,
  params: {
    action?: HygieneAction;
    tracked?: string[];
    exclude?: string[];
    json?: boolean;
  },
): CommandSpec {
  const args = ['scripts/system/local_git_hygiene.py', params.action || 'status'];
  for (const tracked of params.tracked || []) {
    args.push('--tracked', tracked);
  }
  for (const exclude of params.exclude || []) {
    args.push('--exclude', exclude);
  }
  if (params.json !== false) {
    args.push('--json');
  }
  return {
    command: cfg.pythonBin,
    cwd: cfg.repoRoot,
    args,
  };
}

export function buildAetherauthCommand(
  cfg: Required<PluginConfig>,
  params: {
    action?: string;
    contextJson?: string;
    contextVector?: string;
    referenceVector?: string;
    secret?: string;
    signature?: string;
  },
  stamp: string = makeRunStamp(),
): CommandSpec {
  const slug = slugify(params.action || 'read');
  const artifactPath = path.join(cfg.repoRoot, 'artifacts', 'openclaw-plugin', `${stamp}-${slug}-aetherauth.json`);
  const summaryPath = path.join(cfg.repoRoot, 'artifacts', 'openclaw-plugin', `${stamp}-${slug}-aetherauth.md`);
  const args = [
    'scripts/scbe-system-cli.py',
    'aetherauth',
    '--action',
    params.action || 'read',
    '--output',
    toRepoRelative(cfg.repoRoot, artifactPath),
    '--summary',
    toRepoRelative(cfg.repoRoot, summaryPath),
    '--json',
  ];
  if (params.contextJson) {
    args.push('--context-json', params.contextJson);
  }
  if (params.contextVector) {
    args.push('--context-vector', params.contextVector);
  }
  if (params.referenceVector) {
    args.push('--reference-vector', params.referenceVector);
  }
  if (params.secret) {
    args.push('--secret', params.secret);
  }
  if (params.signature) {
    args.push('--signature', params.signature);
  }
  return {
    command: cfg.pythonBin,
    cwd: cfg.repoRoot,
    artifactPath,
    args,
  };
}

export function buildAgentCallCommand(
  cfg: Required<PluginConfig>,
  params: {
    agentId?: string;
    all?: boolean;
    prompt?: string;
    promptFile?: string;
    outputDir?: string;
    maxTokens?: number;
    showOutput?: boolean;
  },
): CommandSpec {
  const args = ['scripts/scbe-system-cli.py', 'agent', 'call', '--json'];
  if (params.all) {
    args.push('--all');
  } else if (params.agentId) {
    args.push('--agent-id', params.agentId);
  }
  if (params.prompt) {
    args.push('--prompt', params.prompt);
  }
  if (params.promptFile) {
    args.push('--prompt-file', params.promptFile);
  }
  args.push('--output-dir', params.outputDir || 'artifacts/agent_calls');
  args.push('--max-tokens', String(params.maxTokens || 420));
  if (params.showOutput !== false) {
    args.push('--show-output');
  }
  return {
    command: cfg.pythonBin,
    cwd: cfg.repoRoot,
    args,
  };
}

export function buildColabBridgeCommand(
  cfg: Required<PluginConfig>,
  params: {
    action?: ColabBridgeAction;
    name?: string;
  },
): CommandSpec {
  const actionMap: Record<ColabBridgeAction, string> = {
    status: 'bridge-status',
    env: 'bridge-env',
    probe: 'bridge-probe',
  };
  return {
    command: cfg.pythonBin,
    cwd: cfg.repoRoot,
    args: [
      'scripts/scbe-system-cli.py',
      'colab',
      actionMap[params.action || 'status'],
      '--name',
      params.name || 'pivot',
      '--json',
    ],
  };
}

export function buildModelPlanCommand(
  cfg: Required<PluginConfig>,
  params: {
    profile?: string;
    profilePath?: string;
    profileDir?: string;
  },
): CommandSpec {
  const args = ['scripts/scbe-system-cli.py', 'model', 'plan', '--json'];
  if (params.profile) {
    args.push('--profile', params.profile);
  }
  if (params.profilePath) {
    args.push('--profile-path', params.profilePath);
  }
  if (params.profileDir) {
    args.push('--profile-dir', params.profileDir);
  }
  return {
    command: cfg.pythonBin,
    cwd: cfg.repoRoot,
    args,
  };
}

function createTextResponse(text: string) {
  return { content: [{ type: 'text' as const, text }] };
}

const plugin = {
  id: PLUGIN_ID,
  name: 'SCBE System Tools',
  description: 'Expose bounded SCBE/HYDRA planning, dispatch, and local hygiene lanes to OpenClaw.',
  register(api: any) {
    const cfg = resolvePluginConfig(api.pluginConfig as PluginConfig | undefined);

    api.registerTool({
      name: 'scbe_flow_plan',
      label: 'SCBE Flow Plan',
      description: 'Build a governed SCBE flow plan packet for a task and persist it under artifacts/openclaw-plugin.',
      parameters: {
        type: 'object',
        additionalProperties: false,
        properties: {
          task: { type: 'string', description: 'Mission or objective to packetize.' },
          formation: {
            type: 'string',
            enum: ['adaptive-scatter', 'concentric', 'hexagonal', 'hexagonal-ring', 'ring', 'scatter', 'tetrahedral'],
          },
          workflowTemplate: {
            type: 'string',
            enum: ['architecture-enhancement', 'implementation-loop', 'training-center-loop'],
          },
          emitActionMap: { type: 'boolean', description: 'Emit action-map telemetry alongside the flow packet.' },
        },
        required: ['task'],
      },
      async execute(_toolCallId: string, params: any) {
        const spec = buildFlowPlanCommand(cfg, params);
        if (spec.artifactPath) {
          await ensureArtifactDir(spec.artifactPath);
        }
        const output = await runCommand(spec, cfg);
        return createTextResponse(output);
      },
    } as any);

    api.registerTool({
      name: 'scbe_octoarms_dispatch',
      label: 'SCBE OctoArms Dispatch',
      description: 'Run the repo-owned OctoArms/HYDRA dispatcher. Defaults to dry-run so swarm execution stays bounded unless explicitly enabled.',
      parameters: {
        type: 'object',
        additionalProperties: false,
        properties: {
          task: { type: 'string', description: 'Mission or objective to route through OctoArms.' },
          lane: {
            type: 'string',
            enum: ['none', 'octoarmor-triage', 'hydra-swarm', 'browse-evidence', 'colab-bridge-status', 'colab-bridge-probe'],
          },
          formation: {
            type: 'string',
            enum: ['adaptive-scatter', 'concentric', 'hexagonal', 'hexagonal-ring', 'ring', 'scatter', 'tetrahedral'],
          },
          workflowTemplate: {
            type: 'string',
            enum: ['architecture-enhancement', 'implementation-loop', 'training-center-loop'],
          },
          provider: { type: 'string', enum: ['auto', 'local', 'hf'] },
          model: { type: 'string', description: 'Optional explicit model id, including Hugging Face models.' },
          backend: { type: 'string', enum: ['playwright', 'selenium', 'cdp'] },
          baseUrl: { type: 'string', description: 'Base URL for local model backends.' },
          bridgeName: { type: 'string', description: 'Colab bridge profile name.' },
          url: { type: 'string', description: 'Target URL for browse-evidence lane.' },
          dryRun: { type: 'boolean', description: 'Defaults to true. Set false only when you want live execution.' },
          emitActionMap: { type: 'boolean', description: 'Emit action-map telemetry during packetization.' },
        },
        required: ['task'],
      },
      async execute(_toolCallId: string, params: any) {
        const output = await runCommand(buildOctoarmsDispatchCommand(cfg, params), cfg);
        return createTextResponse(output);
      },
    } as any);

    api.registerTool({
      name: 'scbe_aetherauth_check',
      label: 'SCBE AetherAuth Check',
      description: 'Run the repo-owned context-bound AetherAuth gate and persist the decision packet under artifacts/openclaw-plugin.',
      parameters: {
        type: 'object',
        additionalProperties: false,
        properties: {
          action: { type: 'string', description: 'Requested action for the gate.' },
          contextJson: { type: 'string', description: 'Context JSON payload for the decision boundary.' },
          contextVector: { type: 'string', description: 'Optional CSV 6D context vector.' },
          referenceVector: { type: 'string', description: 'Optional CSV 6D reference vector.' },
          secret: { type: 'string', description: 'Optional shared secret for signature validation.' },
          signature: { type: 'string', description: 'Optional precomputed request signature.' },
        },
      },
      async execute(_toolCallId: string, params: any) {
        const spec = buildAetherauthCommand(cfg, params || {});
        if (spec.artifactPath) {
          await ensureArtifactDir(spec.artifactPath);
        }
        const output = await runCommand(spec, cfg);
        return createTextResponse(output);
      },
    } as any);

    api.registerTool({
      name: 'scbe_agent_call',
      label: 'SCBE Agent Call',
      description: 'Call one registered Squad AI agent, or all enabled agents, through the repo-owned system CLI.',
      parameters: {
        type: 'object',
        additionalProperties: false,
        properties: {
          agentId: { type: 'string', description: 'Registered agent id. Omit when using all=true.' },
          all: { type: 'boolean', description: 'Call every enabled agent.' },
          prompt: { type: 'string', description: 'Prompt text to send to the agent lane.' },
          promptFile: { type: 'string', description: 'Optional prompt file path.' },
          outputDir: { type: 'string', description: 'Artifact directory for agent call JSON.' },
          maxTokens: { type: 'number', description: 'Max token budget for the call.' },
          showOutput: { type: 'boolean', description: 'Print successful model output in the CLI result.' },
        },
      },
      async execute(_toolCallId: string, params: any) {
        const output = await runCommand(buildAgentCallCommand(cfg, params || {}), cfg);
        return createTextResponse(output);
      },
    } as any);

    api.registerTool({
      name: 'scbe_colab_bridge',
      label: 'SCBE Colab Bridge',
      description: 'Inspect or probe the saved SCBE Colab bridge profile without leaving OpenClaw.',
      parameters: {
        type: 'object',
        additionalProperties: false,
        properties: {
          action: { type: 'string', enum: ['status', 'env', 'probe'] },
          name: { type: 'string', description: 'Bridge profile name.' },
        },
      },
      async execute(_toolCallId: string, params: any) {
        const output = await runCommand(buildColabBridgeCommand(cfg, params || {}), cfg);
        return createTextResponse(output);
      },
    } as any);

    api.registerTool({
      name: 'scbe_model_plan',
      label: 'SCBE Model Plan',
      description: 'Inspect the repo-owned model training profile and derived dataset plan for local or Hugging Face agent lanes.',
      parameters: {
        type: 'object',
        additionalProperties: false,
        properties: {
          profile: { type: 'string', description: 'Model profile id from the CLI context or profile set.' },
          profilePath: { type: 'string', description: 'Explicit model profile JSON path.' },
          profileDir: { type: 'string', description: 'Directory containing model profile JSON files.' },
        },
      },
      async execute(_toolCallId: string, params: any) {
        const output = await runCommand(buildModelPlanCommand(cfg, params || {}), cfg);
        return createTextResponse(output);
      },
    } as any);

    api.registerTool({
      name: 'scbe_local_git_hygiene',
      label: 'SCBE Local Git Hygiene',
      description: 'Inspect or apply the repo-local git hygiene lane so intentional docs/data churn stays out of daily status noise.',
      parameters: {
        type: 'object',
        additionalProperties: false,
        properties: {
          action: { type: 'string', enum: ['status', 'apply', 'clear'] },
          tracked: {
            type: 'array',
            items: { type: 'string' },
            description: 'Extra tracked paths to quiet locally.',
          },
          exclude: {
            type: 'array',
            items: { type: 'string' },
            description: 'Extra untracked patterns for .git/info/exclude.',
          },
          json: { type: 'boolean', description: 'Emit JSON instead of the text summary.' },
        },
      },
      async execute(_toolCallId: string, params: any) {
        const output = await runCommand(buildLocalGitHygieneCommand(cfg, params || {}), cfg);
        return createTextResponse(output);
      },
    } as any);
  },
};

export default plugin;
