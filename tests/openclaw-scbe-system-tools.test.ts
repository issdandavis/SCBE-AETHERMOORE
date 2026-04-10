import { describe, expect, it } from 'vitest';

import plugin, {
  PLUGIN_ID,
  buildAetherauthCommand,
  buildAgentCallCommand,
  buildColabBridgeCommand,
  buildFlowPlanCommand,
  buildLocalGitHygieneCommand,
  buildModelPlanCommand,
  buildOctoarmsDispatchCommand,
  resolvePluginConfig,
} from '../extensions/openclaw-scbe-system-tools/index.ts';

describe('openclaw scbe system tools plugin', () => {
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
    ]);
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
      '20260410T050000Z',
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
    const cfg = resolvePluginConfig({ repoRoot: 'C:/repo', pythonBin: 'python', defaultProvider: 'hf' });
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

  it('builds aetherauth commands with repo-owned decision artifacts', () => {
    const cfg = resolvePluginConfig({ repoRoot: 'C:/repo', pythonBin: 'py' });
    const command = buildAetherauthCommand(
      cfg,
      {
        action: 'execute',
        contextJson: '{"task":"test"}',
        contextVector: '1,0,0,0,0,0',
      },
      '20260410T050100Z',
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
});
