'use strict';

const path = require('node:path');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');

const ACTION_BUNDLES = [
  {
    id: 'terminal.panel',
    aliases: ['term', 'panel', 'dashboard'],
    label: 'terminal panel',
    surface: 'terminal',
    intent: 'Show the compact SCBE command panel and next actions.',
    command: { runner: 'scbe', argv: ['terminal', '--detail'] },
    risk: 'low',
    feedback: 'renders route cards, readiness, grammar, and last receipt',
    agent_use: 'Use first when an agent needs orientation before choosing a command.',
  },
  {
    id: 'terminal.state-json',
    aliases: ['state', 'json', 'terminal-json'],
    label: 'terminal state json',
    surface: 'terminal',
    intent: 'Emit the terminal front-end state as machine-readable JSON.',
    command: { runner: 'scbe', argv: ['terminal', '--json'] },
    risk: 'low',
    feedback: 'returns schema_version=scbe_terminal_frontend_v1',
    agent_use: 'Use when a small model needs structured routing context.',
  },
  {
    id: 'desktop.status',
    aliases: ['desk-status', 'polly-status'],
    label: 'portable desktop status',
    surface: 'portable desktop',
    intent: 'Inspect the Polly Pad OS desktop package without launching it.',
    command: { runner: 'scbe', argv: ['desktop', '--json'] },
    risk: 'low',
    feedback: 'reports app count, dependency state, build state, and launcher commands',
    agent_use: 'Use before launching or packing the portable desktop.',
  },
  {
    id: 'desktop.open',
    aliases: ['desktop', 'desk', 'polly', 'open-desktop'],
    label: 'open portable desktop',
    surface: 'portable desktop',
    intent: 'Start the Polly Pad OS desktop locally.',
    command: { runner: 'scbe', argv: ['desktop', 'open'] },
    risk: 'medium',
    feedback: 'opens a local browser URL and keeps the Vite server alive',
    agent_use: 'Use when the operator wants the visual desktop surface.',
  },
  {
    id: 'desktop.browser-open',
    aliases: ['browser-open', 'browse', 'open-page'],
    label: 'browser open',
    surface: 'portable desktop',
    intent: 'Open a real web page headlessly and capture a screenshot artifact.',
    command: {
      runner: 'scbe',
      argv: ['desktop', 'browse', 'https://example.com', '--json'],
      timeout_ms: 90000,
    },
    risk: 'medium',
    feedback: 'returns schema_version=scbe_browser_page_v1 with title, final_url, and screenshot artifact',
    agent_use: 'Use when the operator needs real browser evidence instead of a stub.',
  },
  {
    id: 'desktop.capture',
    aliases: ['capture', 'screenshot', 'screen-capture'],
    label: 'screen capture',
    surface: 'portable desktop',
    intent: 'Capture the desktop or page surface to a screenshot artifact.',
    command: {
      runner: 'scbe',
      argv: ['desktop', 'capture', '--json'],
      timeout_ms: 90000,
    },
    risk: 'medium',
    feedback: 'returns schema_version=scbe_screen_capture_v1 with artifact path and byte count',
    agent_use: 'Use when the operator needs a screenshot receipt from the desktop/browser surface.',
  },
  {
    id: 'desktop.bridge-smoke',
    aliases: ['bridge-smoke', 'desktop-smoke', 'browser-smoke'],
    label: 'desktop bridge smoke',
    surface: 'portable desktop',
    intent: 'Prove the bridge health endpoint, PowerShell terminal lane, and browser capture lane in one run.',
    command: {
      runner: 'scbe',
      argv: ['desktop', 'bridge-smoke', '--json'],
      timeout_ms: 90000,
    },
    risk: 'medium',
    feedback: 'returns schema_version=scbe_action_bridge_smoke_v1 with health, terminal, and browser results',
    agent_use: 'Use before claiming the operator bridge is fully live.',
  },
  {
    id: 'desktop.test',
    aliases: ['desk-test', 'polly-test'],
    label: 'test portable desktop',
    surface: 'portable desktop',
    intent: 'Run the desktop runtime tests.',
    command: { runner: 'scbe', argv: ['desktop', 'test'] },
    risk: 'low',
    feedback: 'passes or fails the desktop test suite with stdout/stderr',
    agent_use: 'Use before claiming desktop changes work.',
  },
  {
    id: 'desktop.build',
    aliases: ['desk-build', 'polly-build'],
    label: 'build portable desktop',
    surface: 'portable desktop',
    intent: 'Build the portable desktop static bundle.',
    command: { runner: 'scbe', argv: ['desktop', 'build'] },
    risk: 'low',
    feedback: 'creates or refreshes packages/polly-pad-os/dist',
    agent_use: 'Use before packing or publishing the desktop.',
  },
  {
    id: 'desktop.pack',
    aliases: ['desk-pack', 'polly-pack'],
    label: 'pack portable desktop',
    surface: 'portable desktop',
    intent: 'Build a portable static desktop zip.',
    command: { runner: 'scbe', argv: ['desktop', 'pack'] },
    risk: 'low',
    feedback: 'writes artifacts/portable-desktop/scbe-portable-desktop.zip',
    agent_use: 'Use when the operator wants a movable desktop artifact.',
  },
  {
    id: 'repo.status',
    aliases: ['git-status', 'status'],
    label: 'repo status',
    surface: 'repo',
    intent: 'Show branch and dirty-tree state.',
    command: { runner: 'bin', bin: 'git', argv: ['status', '--short', '--branch'] },
    risk: 'low',
    feedback: 'prints current branch and changed paths',
    agent_use: 'Use before staging or committing.',
  },
  {
    id: 'cli.test',
    aliases: ['cli-tests', 'test-cli'],
    label: 'test CLI package',
    surface: 'cli',
    intent: 'Run the SCBE CLI node:test suite.',
    command: {
      runner: 'bin',
      bin: 'npm',
      argv: ['--prefix', 'packages/cli', 'test'],
      timeout_ms: 120000,
    },
    risk: 'medium',
    feedback: 'passes or fails every packages/cli test file',
    agent_use: 'Use before shipping CLI behavior changes.',
  },
  {
    id: 'cli.pack-dry',
    aliases: ['pack-dry', 'npm-pack'],
    label: 'dry-run CLI package',
    surface: 'cli',
    intent: 'Verify the npm package file list without publishing.',
    command: {
      runner: 'bin',
      bin: 'npm',
      argv: ['--prefix', 'packages/cli', 'run', 'pack:dry'],
      timeout_ms: 60000,
    },
    risk: 'low',
    feedback: 'emits npm pack --dry-run JSON',
    agent_use: 'Use before npm publish or release work.',
  },
  {
    id: 'receipt.node-version',
    aliases: ['node-receipt', 'receipt-smoke'],
    label: 'receipt smoke',
    surface: 'governed receipt',
    intent: 'Run a tiny command through the governed receipt path.',
    command: { runner: 'scbe', argv: ['x', '--json', 'node', '--version'] },
    risk: 'low',
    feedback: 'returns schema_version=scbe_terminal_run_v1 with command receipt',
    agent_use: 'Use to verify the command receipt lane is alive.',
  },
];

function shellQuote(value) {
  const text = String(value);
  if (/^[A-Za-z0-9_./:=@\\-]+$/.test(text)) return text;
  return JSON.stringify(text);
}

function displayCommand(bundle) {
  const command = bundle.command || {};
  if (command.runner === 'scbe') {
    return ['scbe', ...(command.argv || [])].map(shellQuote).join(' ');
  }
  if (command.runner === 'bin') {
    return [command.bin, ...(command.argv || [])].map(shellQuote).join(' ');
  }
  return String(command.display || bundle.id);
}

function normalizeAction(bundle) {
  return {
    ...bundle,
    command_text: displayCommand(bundle),
  };
}

function listActionBundles() {
  return ACTION_BUNDLES.map(normalizeAction);
}

function findActionBundle(idOrAlias) {
  const needle = String(idOrAlias || '')
    .trim()
    .toLowerCase();
  if (!needle) return null;
  const found = ACTION_BUNDLES.find((bundle) => {
    if (bundle.id.toLowerCase() === needle) return true;
    return (bundle.aliases || []).some((alias) => alias.toLowerCase() === needle);
  });
  return found ? normalizeAction(found) : null;
}

function actionCard(bundle) {
  const normalized = normalizeAction(bundle);
  return {
    id: normalized.id,
    label: normalized.label,
    surface: normalized.surface,
    intent: normalized.intent,
    command: normalized.command_text,
    risk: normalized.risk,
    feedback: normalized.feedback,
    agent_use: normalized.agent_use,
  };
}

module.exports = {
  REPO_ROOT,
  ACTION_BUNDLES,
  actionCard,
  displayCommand,
  findActionBundle,
  listActionBundles,
};
