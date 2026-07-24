#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');

function loadTaskApi() {
  let packageError;
  try {
    const installed = require('scbe-agent-bus');
    if (installed.TaskApiClient && installed.parseTaskApiRun) return installed;
    packageError = new Error('installed scbe-agent-bus does not export the Task API client');
  } catch (error) {
    packageError = error;
  }
  const monorepoBuild = path.resolve(__dirname, '..', '..', 'agent-bus', 'dist', 'index.js');
  try {
    const local = require(monorepoBuild);
    if (local.TaskApiClient && local.parseTaskApiRun) return local;
  } catch {
    // The final error names the package requirement without leaking paths.
  }
  throw new Error(`scbe-agent-bus with the Task API client is required (${packageError.message})`);
}

function parseArgs(argv) {
  const positional = [];
  const flags = {};
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (!arg.startsWith('--')) {
      positional.push(arg);
      continue;
    }
    const equals = arg.indexOf('=');
    if (equals >= 0) {
      flags[arg.slice(2, equals)] = arg.slice(equals + 1);
      continue;
    }
    const name = arg.slice(2);
    if (index + 1 < argv.length && !argv[index + 1].startsWith('-')) {
      flags[name] = argv[index + 1];
      index += 1;
    } else {
      flags[name] = true;
    }
  }
  return { positional, flags };
}

function readJson(filePath, label) {
  if (!filePath) return undefined;
  const resolved = path.resolve(String(filePath));
  try {
    return JSON.parse(fs.readFileSync(resolved, 'utf8'));
  } catch (error) {
    throw new Error(`${label || 'JSON file'} ${resolved}: ${error.message}`);
  }
}

function csv(value) {
  return String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function integerFlag(value, fallback) {
  if (value === undefined) return fallback;
  const parsed = Number.parseInt(String(value), 10);
  if (!Number.isFinite(parsed) || parsed < 0) throw new Error(`invalid integer: ${value}`);
  return parsed;
}

function output(value, json) {
  if (json) {
    process.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
    return;
  }
  if (value && typeof value === 'object' && value.run_id) {
    process.stdout.write(
      [
        `run_id:      ${value.run_id}`,
        `status:      ${value.status}`,
        `interaction: ${value.interaction_id}`,
        `disposition: ${value.disposition?.status || 'pending'}`,
        `promotable:  ${value.disposition?.do_not_promote_to_fact === true ? 'no' : 'invalid'}`,
      ].join('\n') + '\n'
    );
    return;
  }
  process.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
}

function buildRequest(positional, flags) {
  const requestFile = readJson(flags['request-file'], 'request file');
  if (requestFile !== undefined) {
    if (!requestFile || typeof requestFile !== 'object' || Array.isArray(requestFile)) {
      throw new Error('request file must contain a JSON object');
    }
    return requestFile;
  }
  const objective = String(flags.objective || positional.join(' ')).trim();
  if (!objective) throw new Error('submit requires --objective or positional objective text');
  const evidence = readJson(flags['evidence-file'], 'evidence file');
  if (evidence !== undefined && !Array.isArray(evidence)) {
    throw new Error('evidence file must contain a JSON array');
  }
  const input = readJson(flags['input-file'], 'input file') || {};
  const outputSchema = readJson(flags['schema-file'], 'schema file');
  const includeDomains = csv(flags.include);
  const excludeDomains = csv(flags.exclude);
  return {
    objective,
    processor: String(flags.processor || 'core'),
    input,
    ...(outputSchema ? { output_schema: outputSchema } : {}),
    ...(evidence ? { evidence } : {}),
    source_policy: {
      include_domains: includeDomains,
      exclude_domains: excludeDomains,
      ...(flags.freshness !== undefined ? { freshness_days: integerFlag(flags.freshness, 0) } : {}),
    },
    tools: csv(flags.tools),
    budget: {
      max_seconds: integerFlag(flags['max-seconds'], 60),
      max_sources: integerFlag(flags['max-sources'], 20),
      max_output_chars: integerFlag(flags['max-output-chars'], 20_000),
    },
  };
}

const HELP = `scbe-task - governed async task client

Usage:
  scbe-task health|capabilities [--url http://127.0.0.1:8766]
  scbe-task submit --objective "..." [--processor core] [--wait] [--json]
  scbe-task submit --request-file task.json [--wait] [--json]
  scbe-task status|wait|basis|cancel <run-id> [--json]
  scbe-task list [--limit 100] [--json]
  scbe-task validate <run.json> [--json]

Submit inputs:
  --evidence-file <json>   Array of bounded evidence records
  --input-file <json>      Structured task input
  --schema-file <json>     Strict output JSON schema
  --include <domains>      Comma-separated domain allowlist
  --exclude <domains>      Comma-separated domain denylist
  --tools <names>          Comma-separated tool allowlist

Public hosts are denied unless --allow-public-network is paired with HTTPS.
Completed output always remains do_not_promote_to_fact until an external review.
`;

async function main() {
  const { positional, flags } = parseArgs(process.argv.slice(2));
  const [command, ...rest] = positional;
  if (!command || command === 'help' || flags.help) {
    process.stdout.write(HELP);
    return;
  }
  const taskApi = loadTaskApi();
  if (command === 'validate') {
    const raw = readJson(rest[0], 'run file');
    const parsed = taskApi.parseTaskApiRun(raw);
    output(parsed, flags.json === true);
    if (!parsed.ok) process.exitCode = 2;
    return;
  }

  const client = new taskApi.TaskApiClient({
    baseUrl: flags.url,
    timeoutMs: integerFlag(flags['timeout-ms'], 15_000),
    allowPublicNetwork: flags['allow-public-network'] === true,
  });
  let result;
  if (command === 'health') result = await client.health();
  else if (command === 'capabilities') result = await client.capabilities();
  else if (command === 'submit') {
    result = await client.createRun(buildRequest(rest, flags));
    if (flags.wait === true) {
      result = await client.waitForRun(result.run_id, {
        timeoutMs: integerFlag(flags['wait-timeout-ms'], 60_000),
        pollIntervalMs: integerFlag(flags['poll-ms'], 100),
      });
    }
  } else if (command === 'status') result = await client.getRun(rest[0] || '');
  else if (command === 'wait') {
    result = await client.waitForRun(rest[0] || '', {
      timeoutMs: integerFlag(flags['wait-timeout-ms'], 60_000),
      pollIntervalMs: integerFlag(flags['poll-ms'], 100),
    });
  } else if (command === 'basis') result = await client.getBasis(rest[0] || '');
  else if (command === 'cancel') result = await client.cancelRun(rest[0] || '');
  else if (command === 'list') result = await client.listRuns(integerFlag(flags.limit, 100));
  else throw new Error(`unknown command: ${command}`);
  output(result, flags.json === true);
}

main().catch((error) => {
  process.stderr.write(`scbe-task: ${error.message}\n`);
  process.exitCode = 1;
});
