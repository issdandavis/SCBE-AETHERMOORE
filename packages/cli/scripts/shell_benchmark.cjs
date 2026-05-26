#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');
const OUT_DIR = path.join(REPO_ROOT, 'artifacts', 'benchmarks', 'scbe-shell');

function stamp() {
  return new Date().toISOString().replace(/[:.]/g, '-');
}

function makeHome() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-shell-bench-'));
}

function runNodeCli(args, options = {}) {
  const home = options.home || (options.isolateHome === false ? null : makeHome());
  const env = {
    ...process.env,
    NO_COLOR: '1',
  };
  if (home) {
    env.HOME = home;
    env.USERPROFILE = home;
  }
  const started = Date.now();
  const proc = spawnSync(process.execPath, [CLI, ...args], {
    cwd: REPO_ROOT,
    input: options.input || '',
    encoding: 'utf8',
    timeout: options.timeout || 20_000,
    env,
  });
  return {
    status: proc.status,
    signal: proc.signal,
    duration_ms: Date.now() - started,
    stdout: String(proc.stdout || ''),
    stderr: String(proc.stderr || ''),
    home,
  };
}

function caseResult(name, fn, points = 1) {
  const started = Date.now();
  try {
    const evidence = fn();
    return {
      name,
      passed: true,
      points,
      earned: points,
      duration_ms: Date.now() - started,
      evidence,
    };
  } catch (err) {
    return {
      name,
      passed: false,
      points,
      earned: 0,
      duration_ms: Date.now() - started,
      error: err && err.stack ? String(err.stack) : String(err),
    };
  }
}

function main() {
  const cases = [];

  cases.push(caseResult('help_lists_all_shell_modes', () => {
    const r = runNodeCli(['--help']);
    assert.equal(r.status, 0);
    for (const needle of ['scbe shell', 'scbe shell --ai', 'scbe shell --tui', 'scbe shell --minimal']) {
      assert.match(r.stdout, new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    }
    return { stdout_preview: r.stdout.slice(0, 240), duration_ms: r.duration_ms };
  }));

  cases.push(caseResult('minimal_shell_scriptable_exit', () => {
    const r = runNodeCli(['shell', '--minimal'], { input: ':exit\n' });
    assert.equal(r.status, 0);
    assert.match(r.stdout, /SCBE Terminal/);
    assert.doesNotMatch(r.stdout, /SCBE governed shell/);
    return { stdout_preview: r.stdout.slice(0, 240), duration_ms: r.duration_ms };
  }));

  cases.push(caseResult('rich_shell_config_is_local_free_by_default', () => {
    const r = runNodeCli(['shell'], { input: ':config\n:exit\n' });
    assert.equal(r.status, 0);
    assert.match(r.stdout, /SCBE governed shell/);
    assert.match(r.stdout, /"provider": "ollama"/);
    assert.match(r.stdout, /"model": "llama3\.2"/);
    return { stdout_preview: r.stdout.slice(0, 360), duration_ms: r.duration_ms };
  }));

  cases.push(caseResult('rich_shell_config_set_persists_to_isolated_home', () => {
    const home = makeHome();
    const r = runNodeCli(['shell'], {
      home,
      input: ':config set provider offline\n:config\n:exit\n',
    });
    assert.equal(r.status, 0);
    const cfgPath = path.join(home, '.scbe', 'shell.json');
    const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
    assert.equal(cfg.provider, 'offline');
    assert.match(r.stdout, /config\.provider = offline/);
    return { config_path_exists: fs.existsSync(cfgPath), duration_ms: r.duration_ms };
  }));

  cases.push(caseResult('powershell_passthrough_executes_without_ai_layer', () => {
    const r = runNodeCli(['shell'], {
      input: '!echo SCBE_BENCH_OK\n:exit\n',
      isolateHome: false,
    });
    assert.equal(r.status, 0);
    assert.match(r.stdout, /SCBE_BENCH_OK/);
    assert.doesNotMatch(r.stdout, /thinking/);
    return { stdout_preview: r.stdout.slice(0, 420), duration_ms: r.duration_ms };
  }));

  cases.push(caseResult('governance_blocks_destructive_command', () => {
    const r = runNodeCli(['run', 'rm -rf C:/', '--json'], { isolateHome: false });
    assert.notEqual(r.status, 0);
    const payload = JSON.parse(r.stdout);
    assert.equal(payload.governance.allowed, false);
    assert.equal(payload.governance.tier, 'DENY');
    assert.equal(payload.exit_code, 126);
    return {
      tier: payload.governance.tier,
      finding: payload.governance.findings[0],
      duration_ms: r.duration_ms,
    };
  }, 2));

  cases.push(caseResult('tui_module_imports_and_exports_launcher', () => {
    const code = "import('./packages/cli/bin/tui.mjs').then(m=>{if(typeof m.launchTui!=='function')process.exit(2); console.log('ok')})";
    const r = spawnSync(process.execPath, ['--input-type=module', '-e', code], {
      cwd: REPO_ROOT,
      encoding: 'utf8',
      timeout: 20_000,
    });
    assert.equal(r.status, 0, r.stderr || r.stdout);
    assert.match(r.stdout, /ok/);
    return { stdout_preview: r.stdout.trim(), duration_ms: r.duration_ms };
  }));

  cases.push(caseResult('npm_package_includes_tui_runtime_files', () => {
    const r = spawnSync('npm', ['pack', '--dry-run', '--json'], {
      cwd: path.resolve(__dirname, '..'),
      encoding: 'utf8',
      timeout: 30_000,
      shell: process.platform === 'win32',
    });
    assert.equal(r.status, 0, r.stderr || r.stdout);
    const payload = JSON.parse(r.stdout);
    const files = new Set((payload[0] && payload[0].files || []).map((row) => row.path));
    assert.ok(files.has('bin/scbe.js'));
    assert.ok(files.has('bin/tui.mjs'));
    return { entry_count: payload[0].entryCount, files: Array.from(files).sort() };
  }));

  const total = cases.reduce((sum, row) => sum + row.points, 0);
  const earned = cases.reduce((sum, row) => sum + row.earned, 0);
  const report = {
    schema: 'scbe_shell_agentic_benchmark_v1',
    generated_at: new Date().toISOString(),
    cli: CLI,
    branch: spawnSync('git', ['branch', '--show-current'], { cwd: REPO_ROOT, encoding: 'utf8' }).stdout.trim(),
    commit: spawnSync('git', ['rev-parse', '--short', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).stdout.trim(),
    score: {
      earned,
      total,
      percent: total ? Math.round((earned / total) * 10_000) / 100 : 0,
    },
    cases,
    ready: earned === total,
  };

  fs.mkdirSync(OUT_DIR, { recursive: true });
  const outPath = path.join(OUT_DIR, `${stamp()}-shell-agentic-benchmark.json`);
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  process.stdout.write(`${JSON.stringify({ ...report, artifact: outPath }, null, 2)}\n`);
  process.exit(report.ready ? 0 : 1);
}

main();
