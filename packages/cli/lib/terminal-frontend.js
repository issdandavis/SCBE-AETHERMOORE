'use strict';

const path = require('node:path');

const { actionCard, listActionBundles, REPO_ROOT } = require('./action-bundles');
const { ui } = require('./ui');

const MODE_CARDS = [
  {
    id: 'dashboard',
    label: 'terminal panel',
    command: 'scbe terminal',
    role: 'scan state, last receipt, and launch modes',
    mode: 'human',
  },
  {
    id: 'tui',
    label: 'headed shell',
    command: 'scbe terminal tui',
    role: 'full-screen Ink terminal for manual operator work',
    mode: 'human',
  },
  {
    id: 'ai_shell',
    label: 'ai shell',
    command: 'scbe shell --ai',
    role: 'plain-English routing through local/provider models',
    mode: 'copilot',
  },
  {
    id: 'agent_json',
    label: 'headless bus',
    command: 'scbe shell --agent-json',
    role: 'NDJSON protocol for tiny agents and benchmark harnesses',
    mode: 'machine',
  },
  {
    id: 'governed_run',
    label: 'receipt run',
    command: 'scbe run "npm test" --json',
    role: 'execute one command with GeoSeal gate and terminal receipt',
    mode: 'machine',
  },
  {
    id: 'token_exec',
    label: 'token exec',
    command: 'scbe exec npm test',
    role: 'execute command tokens through the same receipt path',
    mode: 'machine',
  },
];

const HOTKEYS = [
  [':help', 'shell help'],
  [':status', 'JSON status receipt'],
  [':models', 'local model list'],
  ['! <cmd>', 'raw shell command in TUI'],
  ['tab:new:name', 'create agent room'],
  ['tab:2:run:<cmd>', 'address a room'],
];

const QUICK_COMMANDS = [
  ['scbe term', 'open this panel'],
  ['scbe actions', 'show true action bundles'],
  ['scbe term tui', 'headed terminal'],
  ['scbe x <cmd>', 'run command tokens'],
  ['scbe alias g <cmd>', 'save a shortcut'],
  ['scbe run "<cmd>" --json', 'run with receipt'],
  ['scbe shell --agent-json', 'agent protocol'],
];

const COMMAND_GRAMMAR = [
  ['/term', 'open dashboard'],
  ['/tui', 'headed terminal'],
  ['/run <cmd>', 'governed command receipt'],
  ['[verify] <cmd>', 'attach an instruction tag'],
  ['[format] <file>', 'request scoped formatting'],
  ['tab:2:run:<cmd>', 'send work to a room'],
];

const NL_EXAMPLES = [
  ['fix the repo', 'routes through the natural-language resolver'],
  ['show status', 'maps to status'],
  ['run the tests', 'maps to a governed run or shell route'],
];

function truncateMiddle(value, max = 96) {
  const text = String(value || '');
  if (text.length <= max) return text;
  const head = Math.max(8, Math.floor((max - 3) * 0.58));
  const tail = Math.max(8, max - 3 - head);
  return `${text.slice(0, head)}...${text.slice(-tail)}`;
}

function tailText(value, max = 420) {
  const text = String(value || '').trim();
  if (!text) return '';
  return text.length > max ? text.slice(-max) : text;
}

function normalizeReceipt(row) {
  if (!row) {
    return {
      available: false,
      summary: 'no terminal receipt yet',
      next_step: 'Run: scbe run "node --version" --json',
    };
  }
  if (row.parse_error) {
    return {
      available: false,
      parse_error: true,
      summary: 'latest terminal receipt could not be parsed',
      next_step: 'Inspect artifacts/scbe-terminal/history.jsonl',
    };
  }
  const success = row.success === true;
  const stdout = tailText(row.stdout_preview);
  const stderr = tailText(row.stderr_preview);
  return {
    available: true,
    started_at: row.started_at || null,
    command: row.command || '',
    cwd: row.cwd || '',
    success,
    exit_code: row.exit_code ?? null,
    duration_ms: row.duration_ms ?? null,
    compass: row.compass || null,
    governance: row.governance || null,
    stdout_tail: stdout,
    stderr_tail: stderr,
    failure: row.failure || null,
    summary: success
      ? `last run passed in ${row.duration_ms ?? '?'}ms`
      : row.failure?.summary || `last run exited ${row.exit_code ?? '?'}`,
    next_step:
      row.failure?.next_step ||
      (success
        ? 'Use scbe terminal tui for interactive follow-up.'
        : 'Rerun with --json and inspect the first concrete error.'),
  };
}

function summarizeReadiness(platformPacket) {
  const rows = Array.isArray(platformPacket?.readiness) ? platformPacket.readiness : [];
  const fail = rows.filter((row) => row.level === 'fail');
  const warn = rows.filter((row) => row.level === 'warn');
  return {
    decision:
      fail.length > 0 ? 'REPAIR_REQUIRED' : warn.length > 0 ? 'READY_WITH_WARNINGS' : 'READY',
    fail_count: fail.length,
    warn_count: warn.length,
    attention: [...fail, ...warn].slice(0, 4).map((row) => ({
      id: row.id,
      label: row.label,
      level: row.level,
      detail: row.detail,
      next_step: row.next_step,
    })),
  };
}

function buildTerminalFrontendPayload(context = {}) {
  const platform = context.platform || {};
  const git = context.git || {};
  const version = context.version || {};
  const readiness = summarizeReadiness(platform);
  const receipt = normalizeReceipt(context.lastReceipt);
  const shellConfig = context.shellConfig || {};
  const aliases =
    shellConfig.aliases &&
    typeof shellConfig.aliases === 'object' &&
    !Array.isArray(shellConfig.aliases)
      ? Object.entries(shellConfig.aliases)
          .filter(([, command]) => typeof command === 'string' && command.trim())
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([name, command]) => ({ name, command }))
      : [];
  return {
    schema_version: 'scbe_terminal_frontend_v1',
    generated_at: context.generatedAt || new Date().toISOString(),
    title: 'SCBE Terminal Frontend',
    cwd: context.cwd || process.cwd(),
    repo_root: context.repoRoot || platform.host?.repo_root || '',
    history_path: context.historyPath || platform.host?.history_path || '',
    runtime: {
      cli_package: version.cli_package || 'scbe-aethermoore-cli',
      cli_version: version.cli_version || 'unknown',
      core_package: version.core_package || 'scbe-aethermoore',
      core_version: version.core_version || 'unknown',
      node: version.node || process.version,
      platform: version.platform || process.platform,
    },
    git: {
      branch: git.branch || 'unknown',
      commit: git.commit || 'unknown',
      dirty: git.dirty ?? null,
      upstream: git.upstream || null,
    },
    shell: {
      provider: shellConfig.provider || 'ollama',
      model: shellConfig.model || 'llama3.2',
      url: shellConfig.url || shellConfig.base_url || null,
    },
    aliases,
    natural_language: context.naturalLanguage || {
      autocorrect: true,
      word_count: null,
      learned_tools: null,
      examples: NL_EXAMPLES.map(([phrase, use]) => ({ phrase, use })),
      sources: ['static command vocabulary', 'local confirmed utterance log'],
    },
    readiness,
    modes: MODE_CARDS,
    actions: listActionBundles().map(actionCard),
    action_history_path:
      context.actionHistoryPath ||
      path.join(REPO_ROOT, 'artifacts', 'scbe-actions', 'history.jsonl'),
    quick_commands: QUICK_COMMANDS.map(([command, use]) => ({ command, use })),
    command_grammar: COMMAND_GRAMMAR.map(([syntax, use]) => ({ syntax, use })),
    hotkeys: HOTKEYS.map(([keys, use]) => ({ keys, use })),
    last_receipt: receipt,
    launch: {
      dashboard: 'scbe terminal',
      headed: 'scbe terminal tui',
      ai: 'scbe shell --ai',
      headless: 'scbe shell --agent-json',
      governed_run: 'scbe run "<command>" --json',
      token_exec: 'scbe x <program> [args...]',
    },
  };
}

function decisionTone(decision) {
  const d = String(decision || '').toLowerCase();
  if (d.includes('repair') || d.includes('fail')) return 'deny';
  if (d.includes('warn')) return 'warn';
  return 'allow';
}

function receiptTone(receipt) {
  if (!receipt.available) return 'warn';
  return receipt.success ? 'allow' : 'deny';
}

function renderCompactTerminalFrontend(payload, u) {
  const receipt = payload.last_receipt || {};
  const receiptStatus = receipt.available
    ? receipt.success
      ? u.badge('pass', 'allow')
      : u.badge('fail', 'deny')
    : u.badge('empty', 'warn');
  const command = receipt.command ? u.truncate(receipt.command, 50) : u.dim('none yet');
  const quickRows = (payload.quick_commands || [])
    .slice(0, 4)
    .map((entry) => [u.cyan(entry.command), entry.use]);
  const actionRows = (payload.actions || [])
    .slice(0, 5)
    .map((entry) => [
      u.badge(entry.risk || 'low', entry.risk === 'medium' ? 'warn' : 'allow'),
      u.bold(entry.id),
      u.cyan(entry.command),
    ]);
  const grammarRows = [
    [u.cyan('say it'), 'natural language + autocorrect'],
    [u.cyan('/run <cmd>'), 'governed receipt'],
    [u.cyan('[verify] <cmd>'), 'extra instruction tag'],
    [u.cyan('tab:2:run:<cmd>'), 'room routing'],
  ];

  return [
    u.box(
      [
        `${u.badge(payload.readiness?.decision || 'unknown', decisionTone(payload.readiness?.decision))} ${payload.git?.branch || 'unknown'}${payload.git?.dirty ? '*' : ''} ${u.dim(`${payload.shell?.provider || 'offline'}:${payload.shell?.model || 'offline'}`)}`,
        `${u.dim('next')} ${u.cyan(payload.launch?.headed || 'scbe term tui')} ${u.dim('|')} ${u.cyan(payload.launch?.governed_run || 'scbe run "<command>" --json')}`,
      ],
      { title: 'SCBE TERMINAL', color: u.cyan }
    ),
    '',
    u.bold('Quick nav'),
    u.table(quickRows, { head: ['type', 'does'] }),
    '',
    u.bold('Action cards'),
    u.table(actionRows, { head: ['risk', 'id', 'true command'] }),
    '',
    u.bold('Last receipt'),
    u.kv([
      ['status', receiptStatus],
      ['command', command],
      ['next', receipt.next_step || 'Run a governed command to create a receipt.'],
    ]),
    '',
    u.bold('Inputs'),
    u.table(grammarRows, { head: ['form', 'meaning'] }),
    '',
    u.dim('More: scbe term --detail  |  Actions: scbe actions  |  Agents: scbe term --json'),
  ].join('\n');
}

function renderTerminalFrontend(payload, options = {}) {
  const u = options.ui || ui({ json: options.json, color: options.color });
  const width = options.width || 88;
  const detail = Boolean(options.detail);
  const receipt = payload.last_receipt || {};

  if (!detail) return renderCompactTerminalFrontend(payload, u);

  const modeRows = (payload.modes || []).map((mode) => [
    u.badge(
      mode.mode,
      mode.mode === 'machine' ? 'info' : mode.mode === 'copilot' ? 'warn' : 'allow'
    ),
    u.bold(mode.label),
    mode.command,
    u.dim(u.truncate(mode.role, 42)),
  ]);
  const attentionRows =
    payload.readiness?.attention?.length > 0
      ? payload.readiness.attention.map((row) => [
          u.badge(row.level || '?', row.level === 'fail' ? 'deny' : 'warn'),
          row.label || row.id || '?',
          u.dim(u.truncate(row.detail || '', 46)),
          row.next_step ? u.cyan(u.truncate(row.next_step, 36)) : '',
        ])
      : [[u.badge('ok', 'allow'), 'runtime', u.dim('no failing readiness lanes'), '']];
  const hasAttention = Boolean(payload.readiness?.attention?.length);

  const out = [];
  out.push(
    u.box(
      [
        `${u.bold(payload.title || 'SCBE Terminal Frontend')} ${u.dim('type less, see more')}`,
        `${u.dim('next')} ${u.cyan(payload.launch?.headed || 'scbe terminal tui')} ${u.dim('|')} ${u.cyan(payload.launch?.governed_run || 'scbe run "<command>" --json')}`,
        `${u.dim('state')} ${u.badge(payload.readiness?.decision || 'unknown', decisionTone(payload.readiness?.decision))} ${payload.git?.branch || 'unknown'}${payload.git?.dirty ? '*' : ''} ${u.dim(`${payload.shell?.provider || 'offline'}:${payload.shell?.model || 'offline'}`)}`,
      ],
      { title: 'SCBE', color: u.cyan }
    )
  );
  out.push('');
  if (detail) {
    out.push(u.heading('Posture', width));
    out.push(
      u.kv([
        [
          'decision',
          u.badge(
            payload.readiness?.decision || 'unknown',
            decisionTone(payload.readiness?.decision)
          ),
        ],
        [
          'git',
          `${payload.git?.branch || 'unknown'}${payload.git?.dirty ? '*' : ''} ${u.dim(payload.git?.commit || '')}`,
        ],
        [
          'runtime',
          `${payload.runtime?.cli_package || 'scbe'} ${payload.runtime?.cli_version || '?'} ${u.dim(`node ${payload.runtime?.node || process.version}`)}`,
        ],
        ['model', `${payload.shell?.provider || 'offline'}:${payload.shell?.model || 'offline'}`],
        ['history', payload.history_path || 'artifacts/scbe-terminal/history.jsonl'],
      ])
    );
    out.push('');
  }
  out.push(u.heading('Quick Nav', width));
  out.push(
    u.table(
      (payload.quick_commands || []).map((entry) => [u.cyan(entry.command), entry.use]),
      { head: ['type', 'does'] }
    )
  );
  out.push('');
  out.push(u.heading('Action Cards', width));
  out.push(
    u.table(
      (payload.actions || []).map((entry) => [
        u.badge(entry.risk || 'low', entry.risk === 'medium' ? 'warn' : 'allow'),
        u.bold(entry.id),
        u.cyan(entry.command),
        u.dim(u.truncate(entry.feedback || entry.intent || '', 38)),
      ]),
      { head: ['risk', 'id', 'run', 'feedback'] }
    )
  );
  out.push('');
  if (detail) {
    out.push(u.heading('Launch Modes', width));
    out.push(u.table(modeRows, { head: ['mode', 'surface', 'command', 'use'] }));
    out.push('');
  }
  out.push(u.heading('Last Receipt', width));
  out.push(
    u.kv([
      [
        'status',
        u.badge(
          receipt.available ? (receipt.success ? 'pass' : 'fail') : 'empty',
          receiptTone(receipt)
        ),
      ],
      ['summary', receipt.summary || 'no terminal receipt yet'],
      ['command', receipt.command ? u.truncate(receipt.command, 78) : u.dim('none')],
      ['exit', receipt.exit_code == null ? u.dim('n/a') : String(receipt.exit_code)],
      ['next', receipt.next_step || 'Run a governed command to create a receipt.'],
    ])
  );
  if (detail && receipt.stdout_tail) {
    out.push('');
    out.push(u.dim('stdout tail:'));
    out.push(
      receipt.stdout_tail
        .split(/\r?\n/)
        .slice(-6)
        .map((line) => `  ${u.gray(u.truncate(line, 100))}`)
        .join('\n')
    );
  }
  if (detail && receipt.stderr_tail) {
    out.push('');
    out.push(u.dim('stderr tail:'));
    out.push(
      receipt.stderr_tail
        .split(/\r?\n/)
        .slice(-6)
        .map((line) => `  ${u.yellow(u.truncate(line, 100))}`)
        .join('\n')
    );
  }
  if (detail || hasAttention) {
    out.push('');
    out.push(u.heading('Readiness Attention', width));
    out.push(u.table(attentionRows, { head: ['state', 'lane', 'detail', 'next'] }));
    out.push('');
  } else {
    out.push('');
  }
  out.push(u.heading('Natural Language', width));
  out.push(
    u.kv([
      [
        'autocorrect',
        payload.natural_language?.autocorrect ? u.badge('on', 'allow') : u.badge('off', 'warn'),
      ],
      [
        'word list',
        payload.natural_language?.word_count == null
          ? u.dim('available')
          : `${payload.natural_language.word_count} words`,
      ],
      [
        'learned',
        payload.natural_language?.learned_tools == null
          ? u.dim('local corpus')
          : `${payload.natural_language.learned_tools} tool routes`,
      ],
    ])
  );
  if (detail) {
    out.push(
      u.table(
        (payload.natural_language?.examples || []).map((entry) => [
          u.cyan(entry.phrase),
          entry.use,
        ]),
        { head: ['say', 'does'] }
      )
    );
  }
  out.push('');
  out.push(u.heading('Command Grammar', width));
  out.push(
    u.table(
      (detail ? payload.command_grammar || [] : (payload.command_grammar || []).slice(0, 4)).map(
        (entry) => [u.cyan(entry.syntax), entry.use]
      ),
      { head: ['syntax', 'meaning'] }
    )
  );
  if (detail) {
    out.push('');
    out.push(u.heading('Shell Controls', width));
    out.push(
      u.table(
        (payload.hotkeys || []).map((hotkey) => [u.cyan(hotkey.keys), hotkey.use]),
        { head: ['input', 'action'] }
      )
    );
    out.push('');
  } else {
    out.push('');
  }
  out.push(
    u.dim(
      detail
        ? 'JSON for agents: scbe terminal --json'
        : 'More detail: scbe terminal --detail  |  JSON for agents: scbe terminal --json'
    )
  );
  return out.join('\n');
}

module.exports = {
  buildTerminalFrontendPayload,
  renderTerminalFrontend,
  normalizeReceipt,
};
