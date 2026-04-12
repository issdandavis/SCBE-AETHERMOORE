import { readFileSync } from 'node:fs';
import path from 'node:path';

import { describe, expect, it } from 'vitest';

import plugin, {
  PLUGIN_ID,
  buildAetherauthCommand,
  buildAgentCallCommand,
  buildColabBridgeCommand,
  buildFlowPlanCommand,
  buildLocalGitHygieneCommand,
  buildModelPlanCommand,
  buildOpenClawBrowserBridgeCommand,
  buildOpenClawHfHandlerBootstrapCommand,
  buildOctoarmsDispatchCommand,
  resolvePluginConfig,
  extractJsonOutput,
} from '../extensions/openclaw-scbe-system-tools/index.ts';

describe('openclaw scbe system tools plugin', () => {
  it('parses full multi-line JSON tool output before falling back to line fragments', () => {
    const stdout = `{
  "profile_id": "hf-agentic-handler",
  "base_model": "HuggingFaceTB/SmolLM2-1.7B-Instruct",
  "target_modules": [
    "q_proj",
    "down_proj"
  ],
  "total_train_rows": 122579
}`;

    expect(extractJsonOutput(stdout)).toEqual({
      profile_id: 'hf-agentic-handler',
      base_model: 'HuggingFaceTB/SmolLM2-1.7B-Instruct',
      target_modules: ['q_proj', 'down_proj'],
      total_train_rows: 122579,
    });
  });
  it('registers the expected bounded tool surface', () => {
    const tools: string[] = [];
    plugin.register({
      pluginConfig: {},
      registerTool(tool: { name: string }) {
        tools.push(tool.name);
      },
    });
    expect(plugin.id).toBe(PLUGIN_ID);
    expect(tools).toEqual([
      'scbe_flow_plan',
      'scbe_octoarms_dispatch',
      'scbe_aetherauth_check',
      'scbe_agent_call',
      'scbe_colab_bridge',
      'scbe_model_plan',
      'scbe_local_git_hygiene',
      'scbe_openclaw_browser',
      'scbe_openclaw_hf_handler_bootstrap',
    ]);
  });

  it('ships OpenClaw package metadata that points at the plugin entry', () => {
    const packagePath = path.resolve('extensions/openclaw-scbe-system-tools/package.json');
    const pkg = JSON.parse(readFileSync(packagePath, 'utf-8')) as {
      type?: string;
      main?: string;
      openclaw?: { extensions?: string[] };
    };

    expect(pkg.type).toBe('module');
    expect(pkg.main).toBe('index.ts');
    expect(pkg.openclaw?.extensions).toEqual(['./index.ts']);
  });

  it('builds flow plan commands with repo-owned artifact paths', () => {
    const cfg = resolvePluginConfig({ repoRoot: 'C:/repo', pythonBin: 'py' });
    const command = buildFlowPlanCommand(
      cfg,
      {
        task: 'Route governed browser swarm',
        formation: 'ring',
        workflowTemplate: 'training-center-loop',
        emitActionMap: false,
      },
      '20260410T050000Z'
    );

    expect(command.command).toBe('py');
    expect(command.cwd).toBe('C:/repo');
    expect(command.args).toContain('scripts/scbe-system-cli.py');
    expect(command.args).toContain('ring');
    expect(command.args).toContain('training-center-loop');
    expect(command.args).toContain('--no-action-map');
    expect(command.artifactPath).toContain('artifacts');
    expect(command.artifactPath).toContain('openclaw-plugin');
  });

  it('defaults octoarms dispatch to dry-run and supports hf provider selection', () => {
    const cfg = resolvePluginConfig({
      repoRoot: 'C:/repo',
      pythonBin: 'python',
      defaultProvider: 'hf',
    });
    const command = buildOctoarmsDispatchCommand(cfg, {
      task: 'Test Hugging Face agent handler',
      lane: 'hydra-swarm',
      model: 'HuggingFaceTB/SmolLM2-1.7B-Instruct',
    });

    expect(command.args).toContain('--dry-run');
    expect(command.args).toContain('--provider');
    expect(command.args).toContain('hf');
    expect(command.args).toContain('HuggingFaceTB/SmolLM2-1.7B-Instruct');
    expect(command.args).toContain('--json');
  });

  it('uses the Ollama base URL when provider=ollama and no explicit baseUrl is supplied', () => {
    const cfg = resolvePluginConfig({
      repoRoot: 'C:/repo',
      pythonBin: 'python',
      defaultProvider: 'ollama',
      defaultOllamaBaseUrl: 'http://localhost:11434/v1',
    });
    const command = buildOctoarmsDispatchCommand(cfg, {
      task: 'Test local Ollama handler',
      lane: 'hydra-swarm',
      provider: 'ollama',
      model: 'qwen2.5-coder:7b',
    });

    const baseUrlIndex = command.args.indexOf('--base-url');
    expect(baseUrlIndex).toBeGreaterThan(-1);
    expect(command.args[baseUrlIndex + 1]).toBe('http://localhost:11434/v1');
  });

  it('builds aetherauth commands with repo-owned decision artifacts', () => {
    const cfg = resolvePluginConfig({ repoRoot: 'C:/repo', pythonBin: 'py' });
    const command = buildAetherauthCommand(
      cfg,
      {
        action: 'execute',
        contextJson: '{"task":"test"}',
        contextVector: '1,0,0,0,0,0',
      },
      '20260410T050100Z'
    );

    expect(command.command).toBe('py');
    expect(command.args).toContain('aetherauth');
    expect(command.args).toContain('--context-json');
    expect(command.args).toContain('{"task":"test"}');
    expect(command.args).toContain('--json');
    expect(command.artifactPath).toContain('openclaw-plugin');
    expect(command.artifactPath).toContain('aetherauth');
  });

  it('builds direct agent and bridge/model inspection commands', () => {
    const cfg = resolvePluginConfig({ repoRoot: 'C:/repo', pythonBin: 'python' });

    const agentCommand = buildAgentCallCommand(cfg, {
      agentId: 'hf-handler',
      prompt: 'run the handler loop',
      maxTokens: 512,
    });
    expect(agentCommand.args).toEqual([
      'scripts/scbe-system-cli.py',
      'agent',
      'call',
      '--json',
      '--agent-id',
      'hf-handler',
      '--prompt',
      'run the handler loop',
      '--output-dir',
      'artifacts/agent_calls',
      '--max-tokens',
      '512',
      '--show-output',
    ]);

    const colabCommand = buildColabBridgeCommand(cfg, { action: 'probe', name: 'pivot' });
    expect(colabCommand.args).toEqual([
      'scripts/scbe-system-cli.py',
      'colab',
      'bridge-probe',
      '--name',
      'pivot',
      '--json',
    ]);

    const modelCommand = buildModelPlanCommand(cfg, { profile: 'hf-agentic-handler' });
    expect(modelCommand.args).toEqual([
      'scripts/scbe-system-cli.py',
      'model',
      'plan',
      '--json',
      '--profile',
      'hf-agentic-handler',
    ]);
  });

  it('builds hygiene status commands with json output by default', () => {
    const cfg = resolvePluginConfig({ repoRoot: 'C:/repo', pythonBin: 'python' });
    const command = buildLocalGitHygieneCommand(cfg, {
      action: 'status',
      tracked: ['docs/operations'],
      exclude: ['notes/Note drops/'],
    });
    expect(command.args).toEqual([
      'scripts/system/local_git_hygiene.py',
      'status',
      '--tracked',
      'docs/operations',
      '--exclude',
      'notes/Note drops/',
      '--json',
    ]);
  });

  it('builds the OpenClaw HF handler bootstrap command with repo-owned artifact output', () => {
    const cfg = resolvePluginConfig({
      repoRoot: 'C:/repo',
      pythonBin: 'python',
      defaultProvider: 'hf',
    });
    const command = buildOpenClawHfHandlerBootstrapCommand(
      cfg,
      {
        profile: 'hf-agentic-handler',
        lane: 'hydra-swarm',
        task: 'Verify the HF lane',
        executeDispatch: true,
      },
      '20260410T060000Z'
    );

    expect(command.command).toBe('python');
    expect(command.artifactPath).toContain('openclaw-plugin');
    expect(command.args).toEqual([
      'scripts/system/openclaw_hf_handler_bootstrap.py',
      '--json',
      '--output-path',
      'artifacts/openclaw-plugin/20260410T060000Z-hf-agentic-handler-bootstrap.json',
      '--profile',
      'hf-agentic-handler',
      '--provider',
      'hf',
      '--lane',
      'hydra-swarm',
      '--formation',
      'hexagonal-ring',
      '--workflow-template',
      'training-center-loop',
      '--task',
      'Verify the HF lane',
      '--execute-dispatch',
    ]);
  });

  it('builds the OpenClaw browser bridge command against the repo-owned direct bridge', () => {
    const cfg = resolvePluginConfig({ repoRoot: 'C:/repo', pythonBin: 'python' });
    const command = buildOpenClawBrowserBridgeCommand(cfg, {
      action: 'snapshot',
      profile: 'openclaw',
      format: 'ai',
      limit: 200,
      mode: 'efficient',
      timeout: 12,
    });

    expect(command.command).toBe('python');
    expect(command.cwd).toBe('C:/repo');
    expect(command.args).toEqual([
      'scripts/system/openclaw_browser_bridge.py',
      'snapshot',
      '--profile',
      'openclaw',
      '--timeout',
      '12',
      '--format',
      'ai',
      '--limit',
      '200',
      '--mode',
      'efficient',
    ]);
  });

  it('builds a browser bridge start command for direct runtime recovery', () => {
    const cfg = resolvePluginConfig({ repoRoot: 'C:/repo', pythonBin: 'python' });
    const command = buildOpenClawBrowserBridgeCommand(cfg, {
      action: 'start',
      profile: 'openclaw',
      timeout: 9,
    });

    expect(command.args).toEqual([
      'scripts/system/openclaw_browser_bridge.py',
      'start',
      '--profile',
      'openclaw',
      '--timeout',
      '9',
    ]);
  });
});
