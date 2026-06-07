#!/usr/bin/env node
'use strict';
/**
 * SCBE Compass — governed route planner CLI wrapper.
 *
 * Usage:
 *   node packages/agent-bus/scripts/compass.cjs "cross-language compile add(x,y)"
 *   node packages/agent-bus/scripts/compass.cjs --classify "review YouTube upload"
 *
 * Flags:
 *   --classify  Only print the task mode classification (no full plan)
 *
 * Exit codes: 0 = ok, 1 = error, 2 = missing input
 */

const path = require('node:path');

const pkgRoot = path.resolve(__dirname, '..');
const { planScbeCompassRoute, classifyScbeCompassTask } = require(
  path.join(pkgRoot, 'dist', 'index.js')
);

const args = process.argv.slice(2);
if (args.length === 0) {
  process.stderr.write(
    ['Usage: node compass.cjs "<task>"', '       node compass.cjs --classify "<task>"', ''].join(
      '\n'
    )
  );
  process.exit(2);
}

const classifyMode = args[0] === '--classify';
const flagConsumed = classifyMode ? 1 : 0;
const task = args.slice(flagConsumed).join(' ').trim();

if (!task) {
  process.stderr.write('Error: task string is required\n');
  process.exit(2);
}

try {
  if (classifyMode) {
    const mode = classifyScbeCompassTask(task);
    process.stdout.write(
      JSON.stringify(
        { schema_version: 'scbe.agent_bus.compass_classify.v1', task, mode },
        null,
        2
      ) + '\n'
    );
  } else {
    const plan = planScbeCompassRoute(task);
    process.stdout.write(JSON.stringify(plan, null, 2) + '\n');
  }
} catch (err) {
  process.stderr.write(
    JSON.stringify(
      {
        schema_version: 'scbe.agent_bus.compass_error.v1',
        error: err instanceof Error ? err.message : String(err),
        task,
      },
      null,
      2
    ) + '\n'
  );
  process.exit(1);
}
