#!/usr/bin/env node
/**
 * @file ui-preview.js
 * @description Renders the REAL scbe command surfaces through lib/ui.js so the
 *   styling can be seen on live data without editing scbe.js (which is mid-edit).
 *
 *   It shells the existing `--json` variants of version / doctor / platform / demo
 *   and re-renders that real output the way a modern published CLI would
 *   (color, status symbols, aligned summaries, governance badges).
 *
 *   Run:  node packages/cli/bin/ui-preview.js
 *         node packages/cli/bin/ui-preview.js --no-color   # NO_COLOR demo
 *         node packages/cli/bin/ui-preview.js --json        # proves styling is inert
 */

'use strict';

const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { ui } = require('../lib/ui');

const SCBE = path.resolve(__dirname, 'scbe.js');
const jsonMode = process.argv.includes('--json');
const forceNoColor = process.argv.includes('--no-color');

const u = ui({ json: jsonMode, color: forceNoColor ? false : undefined });

/** Shell `scbe <args> --json`; return parsed object or a fallback sample. */
function fetchJson(args, fallback) {
  try {
    const r = spawnSync(process.execPath, [SCBE, ...args, '--json'], {
      encoding: 'utf8',
      timeout: 90000,
      maxBuffer: 8 * 1024 * 1024,
    });
    if (r.status === 0 || r.stdout) {
      const text = r.stdout.trim();
      const start = text.indexOf('{');
      if (start >= 0) return { data: JSON.parse(text.slice(start)), live: true };
    }
  } catch (_e) {
    /* fall through to sample */
  }
  return { data: fallback, live: false };
}

/** Plain (un-styled) capture of a command, for the before/after panel. */
function fetchPlain(args) {
  try {
    const r = spawnSync(process.execPath, [SCBE, ...args], {
      encoding: 'utf8',
      timeout: 90000,
      maxBuffer: 8 * 1024 * 1024,
    });
    return (r.stdout || '').replace(/\s+$/, '');
  } catch (_e) {
    return '(unavailable)';
  }
}

function levelTone(level) {
  const l = String(level || '').toLowerCase();
  if (/(ready|ok|pass|green|available|present|installed)/.test(l)) return 'allow';
  if (/(partial|warn|degraded|optional|yellow|limited)/.test(l)) return 'warn';
  if (/(missing|fail|red|blocked|absent|error)/.test(l)) return 'deny';
  return 'neutral';
}

function liveTag(live) {
  return live ? u.dim('(live)') : u.dim('(sample — scbe --json unavailable)');
}

// ── JSON mode: styling must be fully inert. Emit a single machine object. ────
if (jsonMode) {
  const payload = {
    schema_version: 'scbe_ui_preview_v1',
    note: 'ui-preview in --json mode emits no ANSI; styling is inert by contract',
    color_enabled: u.enabled,
    unicode: u.unicode,
  };
  process.stdout.write(JSON.stringify(payload) + '\n');
  process.exit(0);
}

// ── Header ──────────────────────────────────────────────────────────────────
console.log('');
console.log(
  u.box(
    [
      `${u.bold('scbe')} ${u.dim('· UI kit preview')}`,
      u.dim('real command output, rendered like a modern npm/pypi CLI'),
      u.dim(`color=${u.enabled}  unicode=${u.unicode}`),
    ],
    { title: 'scbe-aethermoore-cli', color: u.cyan }
  )
);

// ── version → kv summary ─────────────────────────────────────────────────────
{
  const { data, live } = fetchJson(['version'], {
    cli_version: '4.5.0',
    core_version: '4.3.0',
    node: process.version,
    platform: process.platform,
  });
  console.log('\n' + u.heading('version'));
  console.log(
    u.kv(
      [
        ['cli', `${u.bold(data.cli_version || '?')} ${liveTag(live)}`],
        ['core', data.core_version || '?'],
        ['node', data.node || process.version],
        ['platform', data.platform || process.platform],
      ],
      {}
    )
  );
}

// ── platform → readiness table with status badges ───────────────────────────
{
  const { data, live } = fetchJson(['platform'], {
    ok: false,
    readiness: [
      { label: 'Node', level: 'ready', detail: 'v24', next_step: '' },
      { label: 'Python', level: 'ready', detail: '3.12', next_step: '' },
      { label: 'liboqs PQC', level: 'partial', detail: 'fallback', next_step: 'install liboqs' },
      { label: 'agent-bus', level: 'missing', detail: 'no server', next_step: 'scbe bus serve' },
    ],
  });
  const rows = (data.readiness || []).map((r) => [
    u.badge(r.level || '?', levelTone(r.level)),
    u.bold(r.label || r.id || '?'),
    u.dim(u.truncate(r.detail || '', 34)),
    r.next_step ? u.cyan(`${u.sym.arrow} ${u.truncate(r.next_step, 38)}`) : '',
  ]);
  console.log('\n' + u.heading('platform readiness') + '  ' + liveTag(live));
  const overall = data.ok === true ? u.ok('all lanes ready') : u.warn('some lanes need attention');
  console.log('  ' + overall + '\n');
  console.log(u.table(rows, {}));
}

// ── demo → governance decision badge + reasons ──────────────────────────────
{
  const { data, live } = fetchJson(['demo'], {
    decision: 'DENY',
    output: 'Blocked unsafe tool execution request before it reached the shell.',
    reasons: ['geoseal.execution_gate.env-secret-path'],
    suggested_correction: 'Require a dry-run proposal and human approval for secret-touching ops.',
  });
  const tone = String(data.decision || 'neutral').toLowerCase();
  console.log('\n' + u.heading('governance demo') + '  ' + liveTag(live));
  console.log('  ' + u.badge(data.decision || '?', tone) + '  ' + (data.output || ''));
  for (const r of data.reasons || []) console.log('  ' + u.bullet(u.dim(r)));
  if (data.suggested_correction) {
    console.log('  ' + u.arrow(u.italic(data.suggested_correction)));
  }
}

// ── geoseal stamp → the signature governance receipt ────────────────────────
{
  const { data, live } = fetchJson(['demo'], {
    decision: 'DENY',
    geoseal: {
      audit_id: 'geoseal_3f2a9c4d1e7b08a5c6d2',
      command_sha256: 'a1b2c3d4e5f6',
      tier: 'DENY',
      findings: ['geoseal.execution_gate.env-secret-path'],
    },
  });
  const g = data.geoseal || {};
  console.log('\n' + u.heading('geoseal stamp') + '  ' + liveTag(live));
  console.log(
    u.seal(data.decision || 'ALLOW', {
      fields: [
        ['audit', u.dim(g.audit_id || 'geoseal_…')],
        ['sha256', u.dim(`${String(g.command_sha256 || '').slice(0, 12)}…`)],
        ['tier', g.tier || data.decision || 'ALLOW'],
        ['findings', String((g.findings || []).length)],
      ],
      stamp: '18:42:07Z',
    })
  );
  // a contrasting ALLOW seal so both tones are visible at a glance
  console.log(
    '\n' +
      u.seal('ALLOW', {
        fields: [
          ['audit', u.dim('geoseal_0a1b2c3d4e5f6a7b8c9d')],
          ['sha256', u.dim('9f8e7d6c5b4a…')],
          ['lane', 'build · code'],
        ],
        stamp: '18:42:09Z',
      })
  );
}

// ── doctor → pass/fail checks ────────────────────────────────────────────────
{
  const { data, live } = fetchJson(['doctor'], {
    ok: true,
    node: process.version,
    geoseal_doctor_status: 0,
  });
  console.log('\n' + u.heading('doctor') + '  ' + liveTag(live));
  console.log(
    u.kv([
      ['overall', data.ok === true ? u.ok('healthy') : u.err('issues found')],
      ['node', data.node || process.version],
      ['geoseal', data.geoseal_doctor_status === 0 ? u.ok('reachable') : u.warn('check needed')],
    ])
  );
}

// ── before / after, on the same real command ────────────────────────────────
console.log('\n' + u.heading('before / after — scbe version'));
console.log('  ' + u.dim('BEFORE (current plain output):'));
const before = fetchPlain(['version'])
  .split('\n')
  .map((l) => '    ' + u.gray(l))
  .join('\n');
console.log(before);
console.log('\n  ' + u.dim('AFTER (same data through lib/ui.js):'));
{
  const { data } = fetchJson(['version'], { cli_version: '4.5.0', node: process.version });
  console.log(
    u.kv(
      [
        [
          'scbe',
          `${u.bold(data.cli_version || '?')}  ${u.green(u.sym.ok)} ${u.dim('post-quantum ready')}`,
        ],
        ['node', data.node || process.version],
        ['platform', data.platform || process.platform],
      ],
      { indent: 4 }
    )
  );
}

console.log(
  '\n' + u.dim('  NO_COLOR=1 or --no-color disables styling; --json keeps output pure.\n')
);
