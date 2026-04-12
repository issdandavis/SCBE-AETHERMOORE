export type HfAgentId = 'hf-coder' | 'hf-terminal';

export type HfPairAction = 'help' | 'install' | 'launch' | 'status' | 'train';

export interface HfAgentProfile {
  id: HfAgentId;
  label: string;
  modelId: string;
  roleSummary: string;
  launchSummary: string;
}

export interface ParsedHfPairCommand {
  action: HfPairAction;
  agentId: HfAgentId | null;
}

const HF_PAIR_CONTROL_ACTIONS = new Set<HfPairAction>(['help', 'install', 'launch', 'status', 'train']);

export const HF_AGENT_PAIR: Record<HfAgentId, HfAgentProfile> = {
  'hf-coder': {
    id: 'hf-coder',
    label: 'HF Coder',
    modelId: 'Qwen/Qwen2.5-Coder-7B-Instruct',
    roleSummary: 'Code generation, refactors, debugging, and file-level implementation work.',
    launchSummary: 'Routes AI panel prompts to the coding head for implementation-heavy tasks.',
  },
  'hf-terminal': {
    id: 'hf-terminal',
    label: 'HF Terminal',
    modelId: 'Qwen/Qwen2.5-7B-Instruct',
    roleSummary: 'CLI planning, shell workflows, repo ops, and terminal-first problem solving.',
    launchSummary: 'Routes AI panel prompts to the terminal head for command and workflow work.',
  },
};

export const DEFAULT_HF_AGENT_ID: HfAgentId = 'hf-coder';

export const HF_PAIR_STORAGE_KEY = 'scbe.hf-agent-pair.v1';

export const HF_PAIR_TRAINING_COMMANDS = [
  'powershell -ExecutionPolicy Bypass -File scripts/system/run_polly_npc_roundtable.ps1 -RunAudit',
  'python scripts/convert_to_sft.py --help',
  'python scripts/train_hf_longrun_placeholder.py --help',
  'powershell -ExecutionPolicy Bypass -File scripts/run_hf_training_and_monitor.ps1',
];

export const HF_AGENT_PAIR_GUIDE = `# Hugging Face Agent Pair

This pad follows the Clone Trooper / Polly Pad shape:

- hot-swappable AI heads
- one coding head
- one terminal head
- training kept separate from governance

## Installed Commands

\`\`\`
@hf-pair install
@hf-pair status
@hf-pair train
@hf-coder launch
@hf-terminal launch
\`\`\`

## Chat Routing

Inside the AI panel you can target either head directly:

\`\`\`
@hf-coder build a React component for the toolbar
@hf-terminal give me the shell steps to run the trainer
\`\`\`

If one head is launched from the terminal, the AI panel keeps using that head until you switch again.

## Default Models

- HF Coder: \`Qwen/Qwen2.5-Coder-7B-Instruct\`
- HF Terminal: \`Qwen/Qwen2.5-7B-Instruct\`

These defaults are chosen because they are practical to swap between router-backed inference and self-hosted free lanes.

## Free Lane Notes

Hugging Face hosted router credits are limited. For a sustained free fallback:

- keep \`HF_TOKEN\` set for normal router use
- point \`HF_CHAT_ROUTER_URL\` at your own OpenAI-compatible endpoint when needed
- use Colab T4 as the primary free training / fallback GPU lane

## Training Lane

Keep governance deterministic. Train only the bounded learned layer:

- NPC and agent voice/style
- preference shaping
- routing / retrieval helpers

Recommended starting commands:

\`\`\`
${HF_PAIR_TRAINING_COMMANDS.join('\n')}
\`\`\`
`;

export function getHfAgent(agentId: HfAgentId): HfAgentProfile {
  return HF_AGENT_PAIR[agentId];
}

export function parseHfPairCommand(input: string): ParsedHfPairCommand | null {
  const trimmed = input.trim();
  if (!trimmed.startsWith('@hf-')) {
    return null;
  }

  const [head = '', maybeAction = ''] = trimmed.split(/\s+/, 3);
  const normalizedHead = head.toLowerCase();

  if (normalizedHead !== '@hf-pair' && normalizedHead !== '@hf-coder' && normalizedHead !== '@hf-terminal') {
    return null;
  }

  const normalizedAction = maybeAction.toLowerCase();
  if (normalizedHead === '@hf-pair') {
    if (!normalizedAction) {
      return { action: 'status', agentId: null };
    }
    if (!HF_PAIR_CONTROL_ACTIONS.has(normalizedAction as HfPairAction)) {
      return null;
    }
    return { action: normalizedAction as HfPairAction, agentId: null };
  }

  const agentId = normalizedHead.slice(1) as HfAgentId;
  if (!normalizedAction) {
    return { action: 'launch', agentId };
  }
  if (!HF_PAIR_CONTROL_ACTIONS.has(normalizedAction as HfPairAction)) {
    return null;
  }
  return { action: normalizedAction as HfPairAction, agentId };
}

export function parseHfAgentPrompt(input: string): { agentId: HfAgentId | null; prompt: string } {
  const trimmed = input.trim();
  const match = trimmed.match(/^@(hf-coder|hf-terminal)\b/i);
  if (!match) {
    return { agentId: null, prompt: trimmed };
  }

  const agentId = match[1].toLowerCase() as HfAgentId;
  const prompt = trimmed.slice(match[0].length).trim();
  return { agentId, prompt };
}
