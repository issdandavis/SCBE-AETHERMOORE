#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { getAppCapability, summarizeCapabilities } from '../src/os/appCapabilities.ts';
import { createPollyPadRuntime } from '../src/os/runtime.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const DEFAULT_OUT_DIR = path.join(REPO_ROOT, 'artifacts', 'benchmarks', 'polly-pad-os');
const APP_LOADER = path.join(REPO_ROOT, 'packages', 'polly-pad-os', 'src', 'os', 'AppLoader.tsx');

function hasFlag(args: string[], name: string) {
  return args.includes(name);
}

function flagValue(args: string[], name: string, fallback = '') {
  const index = args.indexOf(name);
  if (index < 0) return fallback;
  const value = args[index + 1];
  if (!value || value.startsWith('--')) return fallback;
  return value;
}

function stamp() {
  return new Date().toISOString().replace(/[:.]/g, '-');
}

function mkdirp(dir: string) {
  fs.mkdirSync(dir, { recursive: true });
}

function readComponentIds() {
  const source = fs.readFileSync(APP_LOADER, 'utf8');
  const ids = new Set<string>();
  for (const match of source.matchAll(/^\s*([a-z0-9]+):\s*\(\)\s*=>\s*import\(/gim)) {
    ids.add(match[1]);
  }
  return ids;
}

function buildBenchmark() {
  const runtime = createPollyPadRuntime({
    now: () => 1_700_000_000_000,
    random: () => 0.123456,
    viewport: { width: 1440, height: 960 },
  });
  const initial = runtime.snapshot();
  const appIds = initial.apps.map((app) => app.id).sort();
  const componentIds = readComponentIds();
  const defaultVisible = new Set(initial.desktopIcons.map((icon) => icon.appId));
  const tasks = appIds.map((appId) => {
    const capability = getAppCapability(appId);
    const open = runtime.invoke(appId, 'open');
    const close = open.windowId
      ? runtime.invoke(appId, 'close', { windowId: open.windowId })
      : null;
    return {
      app_id: appId,
      capability_status: capability.status,
      component_mapped: componentIds.has(appId),
      default_visible: defaultVisible.has(appId),
      goal: capability.goal,
      memory_profile: capability.memoryProfile,
      open_ok: open.ok,
      close_ok: close ? close.ok : false,
      proof: capability.proof,
      task:
        capability.status === 'download-ready'
          ? `Install or wire backend for ${appId}, then promote to real/local with a regression test.`
          : `Keep ${appId} covered by runtime smoke and source-level regression tests.`,
    };
  });
  const capabilityCounts = summarizeCapabilities(appIds);
  const passed = tasks.filter((task) => task.open_ok && task.close_ok).length;
  const mapped = tasks.filter((task) => task.component_mapped).length;
  const failed = tasks.filter((task) => !task.open_ok || !task.close_ok || !task.component_mapped);

  return {
    schema_version: 'scbe_polly_app_capability_benchmark_v1',
    generated_at: new Date().toISOString(),
    repo_root: REPO_ROOT,
    summary: {
      ...capabilityCounts,
      runtime_open_passed: passed,
      runtime_open_total: tasks.length,
      runtime_open_rate: tasks.length ? passed / tasks.length : 0,
      component_mapped_passed: mapped,
      component_mapped_total: tasks.length,
      component_mapped_rate: tasks.length ? mapped / tasks.length : 0,
      hidden_by_default: capabilityCounts.local + capabilityCounts.download_ready,
    },
    goals: [
      {
        id: 'g1-real-surfaces',
        target: 'The default desktop contains only bridge-backed or test-proven real surfaces.',
        status: capabilityCounts.real === 4 ? 'pass' : 'review',
      },
      {
        id: 'g2-lazy-local-apps',
        target:
          'Light local apps may remain lazy-loaded if they open/close and have a mapped component.',
        status: failed.length === 0 ? 'pass' : 'review',
      },
      {
        id: 'g3-download-ready-backlog',
        target:
          'Heavy or connector-dependent apps stay hidden until their backend is installed and tested.',
        status: capabilityCounts.download_ready > 0 ? 'active' : 'pass',
      },
      {
        id: 'g4-promote-by-proof',
        target:
          'No app moves to the default desktop without a named endpoint, receipt path, or deterministic test.',
        status: 'active',
      },
    ],
    tasks,
    failures: failed,
  };
}

function printText(payload: ReturnType<typeof buildBenchmark>) {
  console.log('SCBE Polly Pad OS capability benchmark');
  console.log(`apps: ${payload.summary.total}`);
  console.log(`real: ${payload.summary.real}`);
  console.log(`local lazy: ${payload.summary.local}`);
  console.log(`download-ready: ${payload.summary.download_ready}`);
  console.log(
    `runtime open: ${payload.summary.runtime_open_passed}/${payload.summary.runtime_open_total}`
  );
  console.log('');
  for (const goal of payload.goals) {
    console.log(`${goal.status.toUpperCase()} ${goal.id}: ${goal.target}`);
  }
}

function main() {
  const args = process.argv.slice(2);
  const asJson = hasFlag(args, '--json');
  const out = flagValue(args, '--out');
  const payload = buildBenchmark();

  if (out) {
    const outPath = path.resolve(REPO_ROOT, out);
    mkdirp(path.dirname(outPath));
    fs.writeFileSync(outPath, `${JSON.stringify(payload, null, 2)}\n`);
  } else if (hasFlag(args, '--write')) {
    mkdirp(DEFAULT_OUT_DIR);
    const outPath = path.join(DEFAULT_OUT_DIR, `${stamp()}-polly-app-capabilities.json`);
    fs.writeFileSync(outPath, `${JSON.stringify(payload, null, 2)}\n`);
    (payload.summary as Record<string, unknown>).artifact_path = outPath;
  }

  if (asJson) {
    console.log(JSON.stringify(payload, null, 2));
  } else {
    printText(payload);
  }

  process.exit(payload.failures.length ? 1 : 0);
}

main();
