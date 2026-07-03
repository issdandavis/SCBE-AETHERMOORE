#!/usr/bin/env node
/**
 * Aetherbrowser MCP bridge.
 *
 * This exposes the existing persistent-Chrome Aetherbrowser agent as typed MCP
 * tools. The bridge intentionally shells only to the repo-owned
 * aether_browser_agent.mjs entrypoint with an allowlisted command set.
 */

import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

export const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
export const AGENT_PATH = join(REPO_ROOT, 'scripts', 'system', 'aether_browser_agent.mjs');
export const DEFAULT_TIMEOUT_MS = 30_000;
export const LONG_TIMEOUT_MS = 20 * 60 * 1000;
export const VOICEOVER_TIMEOUT_MS = 120_000;
export const VOICE_CODE_TIMEOUT_MS = 120_000;
export const DEFAULT_ARTIFACT_ROOT = join(REPO_ROOT, 'artifacts', 'aetherbrowser_mcp');
export const DEFAULT_VOICEOVER_ARTIFACT_ROOT = join(REPO_ROOT, 'artifacts', 'aetherbrowser_voiceover');
export const DEFAULT_VOICE_CODE_ARTIFACT_ROOT = join(REPO_ROOT, 'artifacts', 'aetherbrowser_voice_code');

export const TARGETS = {
  colab: 'https://colab.research.google.com/',
  colab_training:
    'https://colab.research.google.com/gist/issdandavis/c2f22a0b274793d5db9805d216696ad4/train_qlora.ipynb',
  huggingface: 'https://huggingface.co/',
  kaggle: 'https://www.kaggle.com/',
  github: 'https://github.com/issdandavis/SCBE-AETHERMOORE',
  drive: 'https://drive.google.com/',
  aetherdesk: 'http://127.0.0.1:5717/',
};

export const TOOL_NAMES = [
  'aetherbrowser_doctor',
  'aetherbrowser_targets',
  'aetherbrowser_start',
  'aetherbrowser_status',
  'aetherbrowser_open',
  'aetherbrowser_inspect',
  'aetherbrowser_screen',
  'aetherbrowser_click_text',
  'aetherbrowser_type_text',
  'aetherbrowser_press_key',
  'aetherbrowser_monitor',
  'aetherbrowser_voiceover',
  'aetherbrowser_voice_code',
];

const targetEnum = z.enum(Object.keys(TARGETS));
const portSchema = z.number().int().min(1).max(65535).default(9333);
const matchSchema = z.string().trim().min(1).max(500).optional();
const profileNameSchema = z
  .string()
  .trim()
  .regex(/^[A-Za-z0-9_.-]{1,80}$/)
  .optional()
  .describe('Optional persistent profile name under ~/.aetherdesk/browser-profiles/.');
const artifactSubdirSchema = z
  .string()
  .trim()
  .regex(/^[A-Za-z0-9_.-]{1,80}$/)
  .optional()
  .describe('Optional artifact subdirectory under artifacts/aetherbrowser_mcp/.');
const urlSchema = z
  .string()
  .trim()
  .min(1)
  .max(2048)
  .refine(isAllowedUrl, 'URL must start with http://, https://, file://, about:, or chrome://')
  .optional();

const browserTargetSchema = {
  port: portSchema.optional(),
  profile_name: profileNameSchema,
};

const startOpenSchema = {
  ...browserTargetSchema,
  url: urlSchema,
  target: targetEnum.optional(),
  headless: z.boolean().optional(),
};

const pageSchema = {
  port: portSchema.optional(),
  match: matchSchema,
};

const artifactPageSchema = {
  ...pageSchema,
  artifact_subdir: artifactSubdirSchema,
};

function isAllowedUrl(value) {
  return /^(https?:\/\/|file:\/\/|about:|chrome:\/\/)/i.test(String(value || ''));
}

function assertSingleDestination(input) {
  if (input?.url && input?.target) {
    throw new Error('Provide either url or target, not both.');
  }
}

function appendCommonArgs(args, input = {}) {
  if (input.port !== undefined) args.push('--port', String(input.port));
  if (input.profile_name) {
    args.push('--profile', join(homedir(), '.aetherdesk', 'browser-profiles', input.profile_name));
  }
  if (input.match) args.push('--match', input.match);
  return args;
}

export function resolveArtifactDir(artifactSubdir) {
  if (!artifactSubdir) return DEFAULT_ARTIFACT_ROOT;
  if (!/^[A-Za-z0-9_.-]{1,80}$/.test(artifactSubdir)) {
    throw new Error('artifact_subdir may contain only letters, numbers, underscore, dot, and dash.');
  }
  return join(DEFAULT_ARTIFACT_ROOT, artifactSubdir);
}

export function resolveVoiceoverDir(artifactSubdir) {
  if (!artifactSubdir) return DEFAULT_VOICEOVER_ARTIFACT_ROOT;
  if (!/^[A-Za-z0-9_.-]{1,80}$/.test(artifactSubdir)) {
    throw new Error('artifact_subdir may contain only letters, numbers, underscore, dot, and dash.');
  }
  return join(DEFAULT_VOICEOVER_ARTIFACT_ROOT, artifactSubdir);
}

export function resolveVoiceCodeDir(artifactSubdir) {
  if (!artifactSubdir) return DEFAULT_VOICE_CODE_ARTIFACT_ROOT;
  if (!/^[A-Za-z0-9_.-]{1,80}$/.test(artifactSubdir)) {
    throw new Error('artifact_subdir may contain only letters, numbers, underscore, dot, and dash.');
  }
  return join(DEFAULT_VOICE_CODE_ARTIFACT_ROOT, artifactSubdir);
}

export function buildAgentArgs(command, input = {}) {
  const args = [command];
  switch (command) {
    case 'doctor':
    case 'targets':
      return args;

    case 'start':
      assertSingleDestination(input);
      appendCommonArgs(args, input);
      if (input.url) args.push('--url', input.url);
      if (input.target) args.push('--target', input.target);
      if (input.headless) args.push('--headless');
      return args;

    case 'status':
      appendCommonArgs(args, input);
      args.push('--json');
      return args;

    case 'open':
      assertSingleDestination(input);
      appendCommonArgs(args, input);
      if (input.url) args.push('--url', input.url);
      if (input.target) args.push('--target', input.target);
      return args;

    case 'inspect':
    case 'screen':
      appendCommonArgs(args, input);
      args.push('--out-dir', resolveArtifactDir(input.artifact_subdir));
      return args;

    case 'click-text':
      appendCommonArgs(args, input);
      args.push('--text', input.text);
      return args;

    case 'type':
      appendCommonArgs(args, input);
      args.push('--text', input.text);
      return args;

    case 'key':
      appendCommonArgs(args, input);
      args.push('--key', input.key);
      return args;

    case 'monitor':
      appendCommonArgs(args, input);
      args.push('--watch-for', input.watch_for);
      if (input.timeout_ms !== undefined) args.push('--timeout-ms', String(input.timeout_ms));
      return args;

    case 'voiceover':
      args.push('--text', input.text);
      if (input.artifact_subdir) args.push('--out-dir', resolveVoiceoverDir(input.artifact_subdir));
      if (input.voice) args.push('--voice', input.voice);
      if (input.rate !== undefined) args.push('--rate', String(input.rate));
      if (input.engine) args.push('--engine', input.engine);
      if (input.basename) args.push('--basename', input.basename);
      if (input.speak_now) args.push('--speak-now');
      return args;

    case 'voice-code':
      args.push('--action', input.action || 'inventory');
      if (input.artifact_subdir) args.push('--out-dir', resolveVoiceCodeDir(input.artifact_subdir));
      if (input.basename) args.push('--basename', input.basename);
      if (input.song) args.push('--song', input.song);
      if (input.notes) args.push('--notes', input.notes);
      if (input.instrument_mode) args.push('--mode', input.instrument_mode);
      if (input.dialect) args.push('--dialect', input.dialect);
      if (input.holophonor_args) args.push('--args', input.holophonor_args);
      if (input.proof) args.push('--proof', input.proof);
      if (input.text) args.push('--text', input.text);
      if (input.voice) args.push('--voice', input.voice);
      if (input.rate !== undefined) args.push('--rate', String(input.rate));
      if (input.speak) args.push('--speak');
      if (input.speak_now) args.push('--speak-now');
      return args;

    default:
      throw new Error(`Unsupported Aetherbrowser command: ${command}`);
  }
}

export function parseAgentStdout(stdout) {
  const text = String(stdout || '').trim();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    for (let i = text.length - 1; i >= 0; i -= 1) {
      const char = text[i];
      if (char !== '{' && char !== '[') continue;
      try {
        return JSON.parse(text.slice(i));
      } catch {
        // Keep scanning for the start of the last JSON payload.
      }
    }
  }
  return { raw_stdout: text };
}

export function runAgent(command, input = {}, options = {}) {
  const spawnImpl = options.spawnSyncImpl || spawnSync;
  const args = buildAgentArgs(command, input);
  const timeout =
    options.timeoutMs ||
    (command === 'monitor'
      ? LONG_TIMEOUT_MS
      : command === 'voiceover'
        ? VOICEOVER_TIMEOUT_MS
        : command === 'voice-code'
          ? VOICE_CODE_TIMEOUT_MS
          : DEFAULT_TIMEOUT_MS);
  const startedAt = new Date().toISOString();
  const result = spawnImpl(process.execPath, [AGENT_PATH, ...args], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    timeout,
    env: {
      ...process.env,
      AETHERBROWSER_MCP_BRIDGE: '1',
    },
  });
  const finishedAt = new Date().toISOString();
  const stdoutPayload = parseAgentStdout(result.stdout);
  const ok = !result.error && result.status === 0;
  return {
    ok,
    schema_version: 'aetherbrowser-mcp-result-v1',
    bridge: 'aetherbrowser_mcp_server',
    command,
    agent_args: args,
    repo_root: REPO_ROOT,
    agent_path: AGENT_PATH,
    started_at: startedAt,
    finished_at: finishedAt,
    exit_code: result.status,
    signal: result.signal || null,
    error: result.error ? String(result.error.message || result.error) : null,
    stdout: stdoutPayload,
    stderr: result.stderr ? String(result.stderr).slice(0, 8000) : null,
  };
}

function asMcpResult(payload, isError = false) {
  return {
    isError,
    structuredContent: payload,
    content: [{ type: 'text', text: JSON.stringify(payload, null, 2) }],
  };
}

function callAgentTool(command, input, options = {}) {
  try {
    const payload = runAgent(command, input, options);
    return asMcpResult(payload, !payload.ok);
  } catch (error) {
    return asMcpResult(
      {
        ok: false,
        schema_version: 'aetherbrowser-mcp-result-v1',
        bridge: 'aetherbrowser_mcp_server',
        command,
        error: error instanceof Error ? error.message : String(error),
      },
      true
    );
  }
}

export function buildMcpServer(options = {}) {
  const server = new McpServer(
    {
      name: 'aetherbrowser',
      version: '0.2.0',
    },
    {
      capabilities: { tools: {}, logging: {} },
    }
  );

  server.registerTool(
    'aetherbrowser_doctor',
    {
      description:
        'Check local Aetherbrowser bridge readiness: repo path, Chrome detection, Playwright availability, and artifact paths.',
      inputSchema: {},
    },
    async () => callAgentTool('doctor', {}, options)
  );

  server.registerTool(
    'aetherbrowser_targets',
    {
      description: 'List named Aetherbrowser web targets such as github, colab, huggingface, kaggle, drive, and aetherdesk.',
      inputSchema: {},
    },
    async () => callAgentTool('targets', {}, options)
  );

  server.registerTool(
    'aetherbrowser_start',
    {
      description:
        'Start or reuse persistent Chrome with remote debugging for Aetherbrowser. Use this before open/inspect/click/type tools.',
      inputSchema: startOpenSchema,
    },
    async (input) => callAgentTool('start', input, options)
  );

  server.registerTool(
    'aetherbrowser_status',
    {
      description: 'Return the current Aetherbrowser Chrome CDP status and open tabs.',
      inputSchema: browserTargetSchema,
    },
    async (input) => callAgentTool('status', input, options)
  );

  server.registerTool(
    'aetherbrowser_open',
    {
      description: 'Open a URL or named target in the persistent Aetherbrowser Chrome profile.',
      inputSchema: startOpenSchema,
    },
    async (input) => callAgentTool('open', input, options)
  );

  server.registerTool(
    'aetherbrowser_inspect',
    {
      description:
        'Inspect the matched tab, save a screenshot/text receipt, and return title, URL, screenshot path, and visible text tail.',
      inputSchema: artifactPageSchema,
    },
    async (input) => callAgentTool('inspect', input, options)
  );

  server.registerTool(
    'aetherbrowser_screen',
    {
      description: 'Capture a screenshot receipt for the matched tab and return the artifact path.',
      inputSchema: artifactPageSchema,
    },
    async (input) => callAgentTool('screen', input, options)
  );

  server.registerTool(
    'aetherbrowser_click_text',
    {
      description: 'Click a visible link/button/control by text in the matched Aetherbrowser tab.',
      inputSchema: {
        ...pageSchema,
        text: z.string().trim().min(1).max(250),
      },
    },
    async (input) => callAgentTool('click-text', input, options)
  );

  server.registerTool(
    'aetherbrowser_type_text',
    {
      description:
        'Type text into the focused field in the matched Aetherbrowser tab. Do not use for sensitive data without explicit user approval.',
      inputSchema: {
        ...pageSchema,
        text: z.string().min(1).max(20_000),
      },
    },
    async (input) => callAgentTool('type', input, options)
  );

  server.registerTool(
    'aetherbrowser_press_key',
    {
      description: 'Press a browser key chord such as Enter, Escape, Control+Enter, or Tab in the matched tab.',
      inputSchema: {
        ...pageSchema,
        key: z.string().trim().min(1).max(80),
      },
    },
    async (input) => callAgentTool('key', input, options)
  );

  server.registerTool(
    'aetherbrowser_monitor',
    {
      description:
        'Monitor visible text in a matched tab until a phrase appears; useful for Colab/training progress receipts.',
      inputSchema: {
        ...pageSchema,
        watch_for: z.string().trim().min(1).max(500),
        timeout_ms: z.number().int().min(1000).max(LONG_TIMEOUT_MS).optional(),
      },
    },
    async (input) => callAgentTool('monitor', input, options)
  );

  server.registerTool(
    'aetherbrowser_voiceover',
    {
      description:
        'Create a local WAV voiceover from text using the SCBE TTS backend, optionally speaking it through the default audio device.',
      inputSchema: {
        text: z.string().trim().min(1).max(20_000).describe('Transcript text to synthesize.'),
        artifact_subdir: artifactSubdirSchema,
        voice: z.string().trim().min(1).max(120).optional().describe('Optional local voice name substring.'),
        rate: z.number().int().min(-10).max(10).optional().describe('Speech rate; SAPI uses roughly -10 to 10.'),
        engine: z.enum(['sapi', 'pyttsx3', 'espeak', 'say']).optional().describe('Optional local TTS engine override.'),
        basename: z
          .string()
          .trim()
          .regex(/^[A-Za-z0-9_.-]{1,80}$/)
          .optional()
          .describe('Optional safe artifact filename stem.'),
        speak_now: z.boolean().optional().describe('When true, also speak through the default audio device.'),
      },
    },
    async (input) => callAgentTool('voiceover', input, options)
  );

  server.registerTool(
    'aetherbrowser_voice_code',
    {
      description:
        'Compile voice/music coding surfaces into SCBE receipts: notes to code, guitar-mode tape programs, proofs, and expressive prosody WAVs.',
      inputSchema: {
        action: z
          .enum(['inventory', 'holophonor', 'guitar', 'proof', 'expressive'])
          .optional()
          .describe('Voice-code lane to run. inventory lists available lanes.'),
        artifact_subdir: artifactSubdirSchema,
        basename: z
          .string()
          .trim()
          .regex(/^[A-Za-z0-9_.-]{1,80}$/)
          .optional()
          .describe('Optional safe artifact filename stem.'),
        song: z.string().trim().min(1).max(1000).optional().describe('Note phrase for holophonor, e.g. C E or C,E.'),
        notes: z.string().trim().min(1).max(1000).optional().describe('Note phrase for guitar/key mode, e.g. E E G.'),
        instrument_mode: z.string().trim().min(1).max(120).optional().describe('Holophonor mode; defaults to coding.'),
        dialect: z.string().trim().min(1).max(120).optional().describe('Guitar/key dialect such as E minor or C major.'),
        holophonor_args: z
          .string()
          .trim()
          .min(1)
          .max(500)
          .optional()
          .describe('Comma or space separated numeric args for holophonor execution, e.g. 2,3,4.'),
        proof: z.enum(['key', 'instrument', 'any-instrument', 'all']).optional().describe('Proof kind for action=proof.'),
        text: z
          .string()
          .trim()
          .min(1)
          .max(20_000)
          .optional()
          .describe('Expressive text for action=expressive; supports *word*, ^word^, ~word~, +word+, =word=, |, ||.'),
        voice: z.string().trim().min(1).max(120).optional().describe('Optional local voice name substring.'),
        rate: z.number().int().min(-10).max(10).optional().describe('Speech rate; SAPI uses roughly -10 to 10.'),
        speak: z.boolean().optional().describe('When supported, write a local WAV artifact.'),
        speak_now: z.boolean().optional().describe('When true, also speak through the default audio device.'),
      },
    },
    async (input) => callAgentTool('voice-code', input, options)
  );

  return server;
}

async function main() {
  if (!existsSync(AGENT_PATH)) {
    throw new Error(`Aetherbrowser agent not found: ${AGENT_PATH}`);
  }
  const server = buildMcpServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

if (fileURLToPath(import.meta.url) === resolve(process.argv[1] || '')) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.stack : String(error));
    process.exitCode = 1;
  });
}
