'use strict';
/**
 * governance-gate.cjs
 *
 * Bus plugin that gates events through GeoSeal's legitimacy-trial before execution.
 *
 * Load via: SCBE_BUS_PLUGINS=./plugins/governance-gate.cjs
 *
 * Behaviour:
 *   - Low-risk local_only/general events pass without invoking the Python tool
 *     (avoids ~300ms penalty on routine dispatch).
 *   - All other events call `geoseal legitimacy-trial --json` and block on DENY.
 *   - If legitimacy-trial is unavailable (non-zero exit, missing Python), the gate
 *     FAILS OPEN so local dev is not blocked by a misconfigured env.
 *   - afterRun logs a one-liner audit trail to stderr.
 */

const { spawnSync } = require('node:child_process');
const path = require('node:path');

/** @type {import('../dist/index.js').BusPlugin} */
const plugin = {
  name: 'scbe-governance-gate',

  async beforeRun(ctx) {
    const { event } = ctx;

    // Fast-path: low-risk local events skip the full legitimacy trial
    const isLowRisk =
      (event.privacy === 'local_only' || !event.privacy) &&
      (event.taskType === 'general' || !event.taskType);

    if (isLowRisk) {
      return event;
    }

    const repoRoot = path.resolve(process.env.SCBE_REPO_ROOT || process.cwd());
    const python = process.env.PYTHON || 'python';

    const r = spawnSync(
      python,
      [
        path.join(repoRoot, 'src', 'geoseal_cli.py'),
        'legitimacy-trial',
        '--goal',
        event.task,
        '--tool',
        `agentbus.${event.tool || 'default'}`,
        '--origin',
        'agent',
        '--privacy',
        event.privacy === 'local_only' ? 'local_only' : 'hosted',
        '--json',
      ],
      { encoding: 'utf-8', cwd: repoRoot, timeout: 8000 }
    );

    // Fail open — legitimacy tool may not be configured in all envs
    if (r.status !== 0 || !r.stdout) {
      return event;
    }

    let judgment;
    try {
      judgment = JSON.parse(r.stdout);
    } catch {
      return event; // unparseable → fail open
    }

    if (judgment && judgment.decision === 'DENY') {
      process.stderr.write(
        `[governance-gate] DENY run=${ctx.runId.slice(0, 8)} reason="${judgment.reason || 'legitimacy-trial blocked'}"\n`
      );
      return null; // block the event
    }

    return event;
  },

  async afterRun(ctx) {
    const { runId, event, result } = ctx;
    const ok = result ? (result.ok ? 'OK' : 'FAIL') : '??';
    const task = event.task.slice(0, 48).replace(/\s+/g, ' ');
    process.stderr.write(
      `[governance-gate] ${ok} run=${runId.slice(0, 8)} tool=${event.tool || 'default'} task="${task}"\n`
    );
  },
};

module.exports = { plugin, default: plugin };
