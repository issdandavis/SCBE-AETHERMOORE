#!/usr/bin/env node
/*
Fresh-install smoke for the public npm surfaces.

This packs the root `scbe-aethermoore` package and the `packages/agent-bus`
package, installs both tarballs into a new temp project, and verifies the API
and CLI entrypoints a downloader expects to use.
*/

import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import os from 'node:os';
import path from 'node:path';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const node = process.execPath;
const npmCli =
  process.env.npm_execpath ||
  path.join(path.dirname(node), 'node_modules', 'npm', 'bin', 'npm-cli.js');
const npxCli = path.join(path.dirname(npmCli), 'npx-cli.js');

function run(cmd, args, options = {}) {
  return execFileSync(cmd, args, {
    cwd: options.cwd || repoRoot,
    encoding: 'utf-8',
    stdio: options.stdio || ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, ...(options.env || {}) },
  });
}

function pack(cwd) {
  const stdout = run(
    node,
    [npmCli, 'pack', '--json', '--cache', path.join(repoRoot, '.npm-cache')],
    { cwd }
  );
  const lines = stdout.split(/\r?\n/);
  const jsonStart = lines.findIndex((line) => line.trim() === '[');
  if (jsonStart < 0) {
    throw new Error(`npm pack did not emit JSON: ${stdout.slice(0, 1000)}`);
  }
  const payload = JSON.parse(lines.slice(jsonStart).join('\n'));
  return path.join(cwd, payload[0].filename);
}

function assertIncludes(text, expected, label) {
  if (!text.includes(expected)) {
    throw new Error(`${label} did not include ${JSON.stringify(expected)}: ${text.slice(0, 500)}`);
  }
}

const rootTarball = pack(repoRoot);
const busTarball = pack(path.join(repoRoot, 'packages', 'agent-bus'));
const consumerDir = mkdtempSync(path.join(os.tmpdir(), 'scbe-npm-consumer-'));
const rootPackage = JSON.parse(readFileSync(path.join(repoRoot, 'package.json'), 'utf-8'));

run(node, [npmCli, 'init', '-y'], { cwd: consumerDir });
run(
  node,
  [npmCli, 'install', rootTarball, busTarball, '--cache', path.join(consumerDir, '.npm-cache')],
  {
    cwd: consumerDir,
  }
);

assertIncludes(
  run(
    node,
    [
      '-e',
      "const scbe=require('scbe-aethermoore'); const r=scbe.scan('hello world'); if(r.decision!=='ALLOW') throw new Error('scan failed'); console.log('root-api', r.decision, typeof scbe.scanBatch, typeof scbe.isSafe, typeof scbe.harmonicWall);",
    ],
    { cwd: consumerDir }
  ),
  'root-api ALLOW function function function',
  'root CommonJS API'
);

assertIncludes(
  run(
    node,
    [
      '--input-type=module',
      '-e',
      "import scbe, { scan } from 'scbe-aethermoore'; const r=scan('hello from esm'); if(!r || r.decision!=='ALLOW') throw new Error('esm scan failed'); console.log('root-esm', r.decision, typeof scbe.scanBatch);",
    ],
    { cwd: consumerDir }
  ),
  'root-esm ALLOW function',
  'root ESM API'
);

const scanRecord = JSON.parse(
  run(node, [npxCli, 'scbe-scan', '--json', 'hello world'], { cwd: consumerDir })
);
if (scanRecord.decision !== 'ALLOW') {
  throw new Error(`scbe-scan returned ${scanRecord.decision}`);
}

assertIncludes(
  run(node, [npxCli, 'geoseal', 'version'], { cwd: consumerDir }),
  rootPackage.version,
  'geoseal version'
);
assertIncludes(
  run(
    node,
    [
      '-e',
      "const bus=require('scbe-agent-bus'); const keys=['runEvent','runBatch','startAgentBusServer','postAgentBusEvent','runAgentBusTerminalUi']; for (const k of keys) if(typeof bus[k]!=='function') throw new Error('missing '+k); console.log('bus-api', keys.join(','));",
    ],
    { cwd: consumerDir }
  ),
  'bus-api runEvent,runBatch,startAgentBusServer,postAgentBusEvent,runAgentBusTerminalUi',
  'agent-bus API'
);

assertIncludes(
  run(node, [npxCli, 'scbe-agent-bus', '--help'], { cwd: consumerDir }),
  'SCBE Agent Bus',
  'agent-bus help'
);
assertIncludes(
  run(
    node,
    [
      '-e',
      "const bus=require('scbe-agent-bus'); (async()=>{const h=await bus.startAgentBusServer({port:8791}); const res=await fetch(h.url+'/health').then(r=>r.json()); await h.close(); if(!res.ok) throw new Error('health failed'); console.log('bus-health', res.ok, h.url);})().catch(e=>{console.error(e); process.exit(1);});",
    ],
    { cwd: consumerDir }
  ),
  'bus-health true http://127.0.0.1:8791',
  'agent-bus local health'
);

assertIncludes(
  run(
    node,
    [
      '-e',
      "const bus=require('scbe-agent-bus'); (async()=>{const r=await bus.runEvent({task:'npm harness smoke from installed package', taskType:'smoke', privacy:'remote_allowed', dispatch:false},{repoRoot:process.env.SCBE_REPO_ROOT}); console.log('bus-run', r.ok, r.exit_code, r.event.task_chars); if(!r.ok) { console.error(r.stderr_tail); process.exit(1); }})().catch(e=>{console.error(e); process.exit(1);});",
    ],
    { cwd: consumerDir, env: { ...process.env, SCBE_REPO_ROOT: repoRoot } }
  ),
  'bus-run true 0 40',
  'agent-bus repo-backed run'
);

console.log(
  JSON.stringify(
    {
      ok: true,
      consumer_dir: consumerDir,
      root_tarball: rootTarball,
      agent_bus_tarball: busTarball,
    },
    null,
    2
  )
);
