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

const SCORE_AXES = [
  'ease_of_use',
  'utility',
  'tooling',
  'ai_support',
  'governance',
  'harness_reliability',
];

function scoreAxis(name) {
  if (
    /help|minimal|config|bare_sentence|spoken_math|worksheet|typo|terminal_panel|short/i.test(name)
  ) {
    return 'ease_of_use';
  }
  if (/powershell|math|verifier|workflow|status|freshness|scaffold/i.test(name)) {
    return 'utility';
  }
  if (/tui|package|files_tool|read_tool|test_tool|patch_tool|translation|tooling/i.test(name)) {
    return 'tooling';
  }
  if (/governance|destructive|ko_ban|move_packet|fleet/i.test(name)) {
    return 'governance';
  }
  if (/agent_json|async|model|rationale|board|context|done_signal/i.test(name)) {
    return 'ai_support';
  }
  return 'harness_reliability';
}

function scoreByAxis(cases) {
  const axes = Object.fromEntries(
    SCORE_AXES.map((axis) => [
      axis,
      {
        earned: 0,
        total: 0,
        percent: 0,
        cases: [],
      },
    ])
  );
  for (const row of cases) {
    const axis = scoreAxis(row.name);
    axes[axis].earned += row.earned;
    axes[axis].total += row.points;
    axes[axis].cases.push(row.name);
  }
  for (const axis of SCORE_AXES) {
    const bucket = axes[axis];
    bucket.percent = bucket.total ? Math.round((bucket.earned / bucket.total) * 10_000) / 100 : 0;
  }
  return axes;
}

function main() {
  const cases = [];

  cases.push(
    caseResult('help_lists_all_shell_modes', () => {
      const r = runNodeCli(['--help']);
      assert.equal(r.status, 0);
      for (const needle of [
        'scbe shell',
        'scbe shell --ai',
        'scbe shell --tui',
        'scbe shell --minimal',
      ]) {
        assert.match(r.stdout, new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
      }
      return { stdout_preview: r.stdout.slice(0, 240), duration_ms: r.duration_ms };
    })
  );

  cases.push(
    caseResult('minimal_shell_scriptable_exit', () => {
      const r = runNodeCli(['shell', '--minimal'], { input: ':exit\n' });
      assert.equal(r.status, 0);
      assert.match(r.stdout, /SCBE Terminal/);
      assert.doesNotMatch(r.stdout, /SCBE governed shell/);
      return { stdout_preview: r.stdout.slice(0, 240), duration_ms: r.duration_ms };
    })
  );

  cases.push(
    caseResult('rich_shell_config_is_local_free_by_default', () => {
      const r = runNodeCli(['shell'], { input: ':config\n:exit\n' });
      assert.equal(r.status, 0);
      assert.match(r.stdout, /SCBE\s+local/);
      assert.match(r.stdout, /"provider": "ollama"/);
      assert.match(r.stdout, /"model": "[^"]+"/);
      return { stdout_preview: r.stdout.slice(0, 360), duration_ms: r.duration_ms };
    })
  );

  cases.push(
    caseResult('bare_sentence_geoseal_termux_routes_to_worksheet', () => {
      const r = runNodeCli([
        'geoseal',
        'compile',
        'intent',
        'summarize',
        'README',
        'with',
        'termunx',
        'fallback',
      ]);
      assert.equal(r.status, 0);
      assert.match(r.stdout, /worksheet: worksheet\.generic/);
      assert.match(r.stdout, /skills: geoseal, termux/);
      assert.match(r.stdout, /execute: no/);
      assert.doesNotMatch(r.stderr, /workspace ingest/);
      return { stdout_preview: r.stdout.slice(0, 360), duration_ms: r.duration_ms };
    })
  );

  cases.push(
    caseResult('spoken_math_worksheet_handles_long_plain_english', () => {
      const r = runNodeCli([
        'square',
        'root',
        'of',
        '89',
        'times',
        'the',
        'inverse',
        'ratio',
        'of',
        'the',
        'factorial',
        'derivative',
        'of',
        '89',
        'before',
        'and',
        'after',
        'as',
        'a',
        'dual',
        'operation',
      ]);
      assert.equal(r.status, 0);
      assert.match(r.stdout, /worksheet: compute\.spoken_math/);
      assert.match(r.stdout, /primary:/);
      assert.match(r.stdout, /dual:/);
      return { stdout_preview: r.stdout.slice(0, 360), duration_ms: r.duration_ms };
    })
  );

  cases.push(
    caseResult('rich_shell_config_set_persists_to_isolated_home', () => {
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
    })
  );

  cases.push(
    caseResult('powershell_passthrough_executes_without_ai_layer', () => {
      const r = runNodeCli(['shell'], {
        input: '!echo SCBE_BENCH_OK\n:exit\n',
        isolateHome: false,
      });
      assert.equal(r.status, 0);
      assert.match(r.stdout, /SCBE_BENCH_OK/);
      assert.doesNotMatch(r.stdout, /thinking/);
      return { stdout_preview: r.stdout.slice(0, 420), duration_ms: r.duration_ms };
    })
  );

  cases.push(
    caseResult(
      'governance_blocks_destructive_command',
      () => {
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
      },
      2
    )
  );

  cases.push(
    caseResult('tui_module_imports_and_exports_launcher', () => {
      const code =
        "import('./packages/cli/bin/tui.mjs').then(m=>{if(typeof m.launchTui!=='function')process.exit(2); console.log('ok')})";
      const r = spawnSync(process.execPath, ['--input-type=module', '-e', code], {
        cwd: REPO_ROOT,
        encoding: 'utf8',
        timeout: 20_000,
      });
      assert.equal(r.status, 0, r.stderr || r.stdout);
      assert.match(r.stdout, /ok/);
      return { stdout_preview: r.stdout.trim(), duration_ms: r.duration_ms };
    })
  );

  cases.push(
    caseResult('npm_package_includes_tui_runtime_files', () => {
      const r = spawnSync('npm', ['pack', '--dry-run', '--json'], {
        cwd: path.resolve(__dirname, '..'),
        encoding: 'utf8',
        timeout: 30_000,
        shell: process.platform === 'win32',
      });
      assert.equal(r.status, 0, r.stderr || r.stdout);
      const payload = JSON.parse(r.stdout);
      const files = new Set(((payload[0] && payload[0].files) || []).map((row) => row.path));
      assert.ok(files.has('bin/scbe.js'));
      assert.ok(files.has('bin/tui.mjs'));
      assert.ok(
        !Array.from(files).some((file) => file.includes('__pycache__') || file.endsWith('.pyc'))
      );
      return { entry_count: payload[0].entryCount, files: Array.from(files).sort() };
    })
  );

  cases.push(
    caseResult('agent_json_protocol_ready_signal_and_round_trip', () => {
      // Spawn --agent-json, verify ready signal, send one instruction, read response
      const { spawnSync: spawn } = require('node:child_process');
      const inputLines = [
        JSON.stringify({ instruction: 'list files in current directory', terminal_state: '$ ' }),
        '',
      ].join('\n');
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input: inputLines,
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_PROVIDER: 'offline' },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 1, `expected at least 1 output line, got: ${r.stdout}`);
      const ready = JSON.parse(lines[0]);
      assert.equal(ready.ready, true, 'first line must be {"ready":true}');
      if (lines.length >= 2) {
        const resp = JSON.parse(lines[1]);
        assert.ok(Array.isArray(resp.commands), 'response must have commands array');
        assert.ok(typeof resp.done === 'boolean', 'response must have done boolean');
      }
      return {
        ready: ready.ready,
        lines_received: lines.length,
        first_response: lines[1] ? JSON.parse(lines[1]) : null,
      };
    })
  );

  cases.push(
    caseResult('agent_json_cmd_extraction_governance_and_done_signal', () => {
      // Use SCBE_MOCK_RESPONSE to inject a known LLM reply containing <cmd> and done signal.
      // This exercises: regex extraction, governance spawn, done detection — all previously offline-only.
      const { spawnSync: spawn } = require('node:child_process');
      const mockResponse = 'I will list the files. <cmd>ls -la</cmd> task is complete';
      const inputLines = [
        JSON.stringify({ instruction: 'list files', terminal_state: '$ ' }),
        '',
      ].join('\n');
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input: inputLines,
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mockResponse },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 2, `expected ready + response lines, got: ${r.stdout}`);
      const ready = JSON.parse(lines[0]);
      assert.equal(ready.ready, true, 'first line must be {"ready":true}');
      const resp = JSON.parse(lines[1]);
      assert.ok(Array.isArray(resp.commands), 'response must have commands array');
      assert.ok(typeof resp.done === 'boolean', 'response must have done boolean');
      // If governance is available, commands should be populated; if not, may be empty due to offline governance
      // What matters: cmd extraction ran (rationale or commands present), done=true was detected
      assert.equal(resp.done, true, 'done signal must be detected from mock response');
      assert.ok(
        (resp.commands.length > 0 && resp.commands[0].keystrokes === 'ls -la') ||
          resp.blocked === true,
        `expected keystrokes='ls -la' or governance block, got: ${JSON.stringify(resp)}`
      );
      return {
        commands: resp.commands,
        done: resp.done,
        governance: resp.governance || null,
        rationale_preview: (resp.rationale || '').slice(0, 120),
      };
    })
  );

  cases.push(
    caseResult('agent_json_waits_for_async_response_after_stdin_close', () => {
      // Regression: piped harness input closes stdin immediately. The process must
      // still wait for the async model/governance turn before exiting.
      const { spawnSync: spawn } = require('node:child_process');
      const mockResponse = '<cmd>git status --short --branch</cmd> task complete';
      const inputLines = [
        JSON.stringify({ instruction: 'inspect repo state', terminal_state: '$ ' }),
        '',
      ].join('\n');
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input: inputLines,
        encoding: 'utf8',
        timeout: 20_000,
        env: {
          ...process.env,
          NO_COLOR: '1',
          SCBE_MOCK_RESPONSE: mockResponse,
          SCBE_MOCK_RESPONSE_DELAY_MS: '250',
        },
      });
      assert.equal(r.status, 0, r.stderr || r.stdout);
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 2, `expected ready + delayed response, got: ${r.stdout}`);
      const ready = JSON.parse(lines[0]);
      const resp = JSON.parse(lines[1]);
      assert.equal(ready.ready, true);
      assert.equal(resp.done, true);
      assert.equal(resp.commands[0].keystrokes, 'git status --short --branch');
      return { lines_received: lines.length, command: resp.commands[0].keystrokes };
    })
  );

  // ── Tool translation cases ────────────────────────────────────────────────

  cases.push(
    caseResult('agent_json_files_tool_translates_to_find', () => {
      const { spawnSync: spawn } = require('node:child_process');
      const mock = 'Let me search. <cmd>:files auth.py</cmd>';
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input:
          JSON.stringify({ instruction: 'find the auth module', terminal_state: '$ ' }) + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mock },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 2, `expected ready + response, got: ${r.stdout}`);
      const resp = JSON.parse(lines[1]);
      assert.ok(resp.commands.length > 0 || resp.blocked, 'expected command or governance block');
      if (resp.commands.length > 0) {
        const ks = resp.commands[0].keystrokes;
        assert.ok(
          ks.includes('find') || ks.includes('grep'),
          `expected find/grep translation, got: ${ks}`
        );
        assert.ok(!ks.startsWith(':'), 'translated command must not start with :');
      }
      return { translated: resp.commands[0]?.keystrokes || resp.rationale };
    })
  );

  cases.push(
    caseResult('agent_json_read_tool_translates_to_sed', () => {
      const { spawnSync: spawn } = require('node:child_process');
      const mock = 'Reading file. <cmd>:read src/index.ts 1:20</cmd>';
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input:
          JSON.stringify({ instruction: 'read the index file', terminal_state: '$ ' }) + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mock },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 2, `expected ready + response, got: ${r.stdout}`);
      const resp = JSON.parse(lines[1]);
      if (resp.commands.length > 0) {
        const ks = resp.commands[0].keystrokes;
        assert.ok(ks.includes('sed'), `expected sed translation, got: ${ks}`);
        assert.ok(!ks.startsWith(':'), 'translated command must not start with :');
      }
      return { translated: resp.commands[0]?.keystrokes || resp.rationale };
    })
  );

  cases.push(
    caseResult('agent_json_test_tool_wraps_with_pass_fail_echo', () => {
      const { spawnSync: spawn } = require('node:child_process');
      const mock = 'Running tests. <cmd>:test npm test</cmd>';
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input: JSON.stringify({ instruction: 'run the tests', terminal_state: '$ ' }) + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mock },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 2, `expected ready + response, got: ${r.stdout}`);
      const resp = JSON.parse(lines[1]);
      if (resp.commands.length > 0) {
        const ks = resp.commands[0].keystrokes;
        assert.ok(ks.includes('SCBE_TEST_PASS'), `expected SCBE_TEST_PASS echo, got: ${ks}`);
        assert.ok(ks.includes('npm test'), `expected npm test in command, got: ${ks}`);
      }
      return { translated: resp.commands[0]?.keystrokes || resp.rationale };
    })
  );

  cases.push(
    caseResult('agent_json_ko_ban_blocks_repeated_cmd_obs_pair', () => {
      // Send 3 turns: same command, same observation each turn.
      // On the 3rd turn the board should ko-ban the move and block it.
      const { spawnSync: spawn } = require('node:child_process');
      const mock = '<cmd>ls -la</cmd>';
      const errorState = '$ ls -la\nls: cannot access: No such file or directory';
      const inputLines = [
        JSON.stringify({ instruction: 'list files', terminal_state: '$ ' }),
        JSON.stringify({ terminal_state: errorState }),
        JSON.stringify({ terminal_state: errorState }),
        '',
      ].join('\n');
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input: inputLines,
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mock },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      const responses = lines
        .slice(1)
        .map((l) => {
          try {
            return JSON.parse(l);
          } catch {
            return null;
          }
        })
        .filter(Boolean);
      assert.ok(responses.length >= 1, `expected at least one response, got: ${r.stdout}`);
      const last = responses[responses.length - 1];
      if (responses.length >= 3) {
        assert.equal(
          last.blocked,
          true,
          `expected blocked=true on 3rd turn, got: ${JSON.stringify(last)}`
        );
        assert.equal(
          last.governance?.reason,
          'ko-ban',
          `expected governance.reason='ko-ban', got: ${last.governance?.reason}`
        );
        assert.ok(last.board, `response must include board state`);
        assert.ok(last.board.ko_bans.length > 0, `board must have at least one ko-ban entry`);
      }
      return { response_count: responses.length, last };
    })
  );

  cases.push(
    caseResult('agent_json_board_returned_every_turn', () => {
      // Every non-error response must include a board object with the expected shape.
      const { spawnSync: spawn } = require('node:child_process');
      const mock = 'Listing files now. <cmd>ls</cmd>';
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input: JSON.stringify({ instruction: 'list files', terminal_state: '$ ' }) + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mock },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 2, `expected ready + response`);
      const resp = JSON.parse(lines[1]);
      assert.ok(resp.board, `response must include board`);
      assert.ok(typeof resp.board.turn === 'number', `board.turn must be a number`);
      assert.ok(Array.isArray(resp.board.attempts), `board.attempts must be an array`);
      assert.ok(Array.isArray(resp.board.ko_bans), `board.ko_bans must be an array`);
      assert.ok(Array.isArray(resp.board.legal_moves), `board.legal_moves must be an array`);
      assert.strictEqual(resp.board.done, false, `board.done must be false initially`);
      assert.strictEqual(
        resp.board.path_policy,
        'non_optimal_correct',
        `board.path_policy must be 'non_optimal_correct'`
      );
      return { board: resp.board };
    })
  );

  cases.push(
    caseResult('agent_json_rationale_strips_cmd_content', () => {
      // Groq-format response (<cmd>...<cmd> — no </cmd>). Rationale must not include the cmd text.
      const { spawnSync: spawn } = require('node:child_process');
      const cmdText = 'echo scbe_rationale_strip_sentinel';
      const mockResponse = `I will run the command.\n<cmd>${cmdText}<cmd>\n\nLet me check the result.`;
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input: JSON.stringify({ instruction: 'run a test echo', terminal_state: '$ ' }) + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mockResponse },
      });
      assert.ok((r.stdout || '').length > 0, `no stdout from agent-json`);
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 2, `expected ready + response, got: ${r.stdout}`);
      const resp = JSON.parse(lines[1]);
      assert.ok(resp.rationale != null, `response must have rationale`);
      assert.ok(
        !resp.rationale.includes(cmdText),
        `rationale must not contain cmd text "${cmdText}", got: "${resp.rationale.slice(0, 200)}"`
      );
      return { rationale_preview: resp.rationale.slice(0, 120) };
    })
  );

  cases.push(
    caseResult('agent_json_no_cmd_response_includes_governance', () => {
      // No-cmd path (model explains without a command) must include a governance field for consistency.
      const { spawnSync: spawn } = require('node:child_process');
      const mockResponse =
        'The task requires more information before I can proceed. Please clarify.';
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input:
          JSON.stringify({ instruction: 'do something unclear', terminal_state: '$ ' }) + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mockResponse },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 2, `expected ready + response`);
      const resp = JSON.parse(lines[1]);
      assert.ok(resp.governance, `no-cmd response must include governance field`);
      assert.ok(resp.governance.decision, `governance must have decision`);
      assert.strictEqual(resp.commands.length, 0, `no-cmd response must have empty commands`);
      return { governance: resp.governance };
    })
  );

  cases.push(
    caseResult('agent_json_reset_context_clears_board', () => {
      // reset_context: true must wipe attempts, ko_bans, and turn; new instruction takes effect.
      const { spawnSync: spawn } = require('node:child_process');
      const mock = 'Working on it. <cmd>echo step</cmd>';
      const msg1 = JSON.stringify({ instruction: 'first step task', terminal_state: '$ ' });
      const msg2 = JSON.stringify({
        reset_context: true,
        instruction: 'second step task',
        terminal_state: '$ ',
        step_context: 'first step completed',
      });
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input: msg1 + '\n' + msg2 + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mock },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 3, `expected ready + 2 responses, got ${lines.length} lines`);
      const resp2 = JSON.parse(lines[2]);
      assert.ok(resp2.board, 'second response must include board');
      // Reset cleared step-1 state; turn was reset to 0 then incremented, so it must be 1 now.
      assert.strictEqual(
        resp2.board.turn,
        1,
        `reset_context must reset turn to 1, got ${resp2.board.turn}`
      );
      assert.strictEqual(resp2.board.ko_bans.length, 0, 'reset_context must clear ko_bans');
      // Any attempts present belong to the new step only (turn ≤ 1).
      const staleAttempts = (resp2.board.attempts || []).filter((a) => a.turn > 1);
      assert.strictEqual(
        staleAttempts.length,
        0,
        `stale attempts from previous step must be gone, got: ${JSON.stringify(staleAttempts)}`
      );
      assert.strictEqual(
        resp2.board.objective,
        'second step task',
        'new instruction must be board objective'
      );
      return {
        turn: resp2.board.turn,
        attempts: resp2.board.attempts.length,
        objective: resp2.board.objective,
      };
    })
  );

  cases.push(
    caseResult('agent_json_step_index_shown_in_board', () => {
      // step_index + step_total sent in message must appear in the returned board.
      const { spawnSync: spawn } = require('node:child_process');
      const mock = 'Processing. <cmd>echo progress</cmd>';
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input:
          JSON.stringify({
            instruction: 'workflow step task',
            terminal_state: '$ ',
            step_index: 2,
            step_total: 5,
          }) + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mock },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 2, `expected ready + response, got ${lines.length}`);
      const resp = JSON.parse(lines[1]);
      assert.ok(resp.board, 'response must include board');
      assert.strictEqual(
        resp.board.step_index,
        2,
        `expected step_index=2, got ${resp.board.step_index}`
      );
      assert.strictEqual(
        resp.board.step_total,
        5,
        `expected step_total=5, got ${resp.board.step_total}`
      );
      return { step_index: resp.board.step_index, step_total: resp.board.step_total };
    })
  );

  cases.push(
    caseResult('agent_json_max_turns_emits_limit_signal', () => {
      // After the turn budget is exhausted, the next response must be max_turns_reached=true.
      const { spawnSync: spawn } = require('node:child_process');
      const mock = 'Working. <cmd>echo working</cmd>';
      const msg1 = JSON.stringify({
        instruction: 'task with tight limit',
        terminal_state: '$ ',
        max_turns: 1,
      });
      const msg2 = JSON.stringify({ terminal_state: '$ echo working\nworking' });
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input: msg1 + '\n' + msg2 + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mock },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 3, `expected ready + 2 responses, got ${lines.length} lines`);
      const resp2 = JSON.parse(lines[2]);
      assert.strictEqual(
        resp2.max_turns_reached,
        true,
        `expected max_turns_reached=true, got: ${JSON.stringify(resp2).slice(0, 200)}`
      );
      assert.strictEqual(resp2.done, false, 'max_turns_reached response must have done=false');
      assert.deepStrictEqual(
        resp2.commands,
        [],
        'max_turns_reached response must have empty commands'
      );
      return {
        max_turns_reached: resp2.max_turns_reached,
        rationale: resp2.rationale?.slice(0, 60),
      };
    })
  );

  cases.push(
    caseResult('agent_json_two_step_workflow_passes_context', () => {
      // Two-step workflow: second step receives reset_context + step_context from step 1.
      // Board must reflect new objective, empty attempts, and correct step_index.
      const { spawnSync: spawn } = require('node:child_process');
      const mock = 'Understood. <cmd>echo ok</cmd>';
      const msg1 = JSON.stringify({
        instruction: 'step one: identify issues',
        terminal_state: '$ ',
        step_index: 1,
        step_total: 2,
      });
      const msg2 = JSON.stringify({
        reset_context: true,
        instruction: 'step two: fix the issues',
        terminal_state: '$ ',
        step_context: 'step one identified failing tests',
        step_index: 2,
        step_total: 2,
      });
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input: msg1 + '\n' + msg2 + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mock },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 3, `expected ready + 2 responses, got ${lines.length} lines`);
      const resp2 = JSON.parse(lines[2]);
      assert.ok(resp2.board, 'second step response must include board');
      assert.strictEqual(
        resp2.board.step_index,
        2,
        'board step_index must be 2 after context reset'
      );
      assert.strictEqual(resp2.board.step_total, 2, 'board step_total must be 2');
      assert.strictEqual(
        resp2.board.objective,
        'step two: fix the issues',
        'board objective must be updated'
      );
      // Reset cleared step-1 history; turn must be 1 (reset to 0, incremented once for this step).
      assert.strictEqual(
        resp2.board.turn,
        1,
        `turn must reset to 1 for new step, got ${resp2.board.turn}`
      );
      // No stale attempts from step 1.
      const stale = (resp2.board.attempts || []).filter((a) => a.turn > 1);
      assert.strictEqual(
        stale.length,
        0,
        `step-1 attempts must not bleed into step-2 board, got: ${JSON.stringify(stale)}`
      );
      return {
        step: `${resp2.board.step_index}/${resp2.board.step_total}`,
        turn: resp2.board.turn,
        objective: resp2.board.objective.slice(0, 40),
      };
    })
  );

  cases.push(
    caseResult('agent_json_patch_tool_translates_to_patch_command', () => {
      const { spawnSync: spawn } = require('node:child_process');
      const mock = 'Applying patch. <cmd>:patch /tmp/fix.patch</cmd>';
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input:
          JSON.stringify({ instruction: 'apply the patch file', terminal_state: '$ ' }) + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mock },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 2, `expected ready + response, got: ${r.stdout}`);
      const resp = JSON.parse(lines[1]);
      if (resp.commands.length > 0) {
        const ks = resp.commands[0].keystrokes;
        assert.ok(ks.includes('patch -p1'), `expected patch -p1 in keystrokes, got: ${ks}`);
        assert.ok(ks.includes('fix.patch'), `expected fix.patch in keystrokes, got: ${ks}`);
        assert.ok(!ks.startsWith(':'), 'translated command must not start with :');
      }
      return { translated: resp.commands[0]?.keystrokes || resp.rationale };
    })
  );

  cases.push(
    caseResult('agent_json_command_includes_bijective_move_packet', () => {
      const { spawnSync: spawn } = require('node:child_process');
      const mock = 'Check repo state. <cmd>git status --short --branch</cmd>';
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input: JSON.stringify({ instruction: 'check repo state', terminal_state: '$ ' }) + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mock },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 2, `expected ready + response, got: ${r.stdout}`);
      const resp = JSON.parse(lines[1]);
      assert.ok(resp.commands.length > 0 || resp.blocked, 'expected command or governance block');
      assert.ok(resp.move_packet, 'response must include move_packet');
      assert.equal(resp.move_packet.schema_version, 'scbe_agent_move_packet_v1');
      assert.equal(resp.move_packet.round_trip_ok, true);
      assert.equal(resp.move_packet.bijective_proof.ok, true);
      assert.ok(
        resp.move_packet.atomic_units?.[0]?.hex?.length > 0,
        'expected byte/hex atomic unit'
      );
      assert.match(resp.move_packet.boundaries.not_claimed, /not a source-to-source compiler/);
      return {
        move_id: resp.move_packet.move_id,
        tokens: resp.move_packet.tokens.slice(0, 3),
        round_trip_ok: resp.move_packet.round_trip_ok,
      };
    })
  );

  cases.push(
    caseResult('agent_json_command_includes_fleet_governance_gate', () => {
      const { spawnSync: spawn } = require('node:child_process');
      const mock = 'Push to main. <cmd>git push origin main</cmd>';
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input:
          JSON.stringify({
            instruction: 'push changes',
            terminal_state: '$ ',
            fleet_posture: {
              posture: 'production',
              fleet_size: 4,
              byzantine_faults_tolerated: 1,
            },
            fleet_authority: {
              actor_id: 'bench-agent',
              clearance: 2,
              approved_by: ['bench-agent'],
            },
          }) + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mock },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 2, `expected ready + response, got: ${r.stdout}`);
      const resp = JSON.parse(lines[1]);
      assert.ok(resp.fleet_governance, 'response must include fleet_governance');
      assert.equal(resp.fleet_governance.ok, true);
      assert.equal(resp.fleet_governance.state_vector.operation_class, 'deploy');
      assert.equal(resp.fleet_governance.decision_record.decision, 'ESCALATE');
      assert.equal(resp.fleet_governance.decision_record.reason, 'quorum_not_met');
      return {
        operation_class: resp.fleet_governance.state_vector.operation_class,
        decision: resp.fleet_governance.decision_record.decision,
        reason: resp.fleet_governance.decision_record.reason,
      };
    })
  );

  cases.push(
    caseResult('agent_json_offline_scaffold_emits_task_command', () => {
      const { spawnSync: spawn } = require('node:child_process');
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input:
          JSON.stringify({
            instruction:
              "Run the benchmark artifact freshness test suite at packages/cli/tests/bench_artifact_freshness.test.cjs using Node's built-in test runner (`node --test`). Report how many tests pass.",
            terminal_state: '$ ',
          }) + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_PROVIDER: 'offline' },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 2, `expected ready + response, got: ${r.stdout}`);
      const resp = JSON.parse(lines[1]);
      assert.ok(resp.commands.length > 0, 'expected scaffold command');
      assert.match(resp.commands[0].keystrokes, /node --test/);
      assert.match(resp.commands[0].keystrokes, /bench_artifact_freshness\.test\.cjs/);
      return { command: resp.commands[0].keystrokes };
    })
  );

  cases.push(
    caseResult('agent_json_unreachable_model_falls_back_to_scaffold', () => {
      const { spawnSync: spawn } = require('node:child_process');
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input:
          JSON.stringify({
            instruction:
              'Run a dry-run npm pack for the CLI package at packages/cli and confirm that scripts/scbe_workflow.cjs appears in the file list. Use: npm pack --dry-run --json (run from the packages/cli directory).',
            terminal_state: '$ ',
          }) + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: {
          ...process.env,
          NO_COLOR: '1',
          SCBE_PROVIDER: 'ollama',
          SCBE_URL: 'http://127.0.0.1:9',
        },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 2, `expected ready + response, got: ${r.stdout}`);
      const resp = JSON.parse(lines[1]);
      assert.ok(!resp.error, `fallback must not return hard agent error: ${JSON.stringify(resp)}`);
      assert.ok(resp.commands.length > 0, 'expected fallback command');
      assert.match(resp.commands[0].keystrokes, /npm pack --dry-run --json/);
      return { command: resp.commands[0].keystrokes };
    })
  );

  cases.push(
    caseResult('agent_json_board_includes_pazaak_action_cards', () => {
      const { spawnSync: spawn } = require('node:child_process');
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input:
          JSON.stringify({
            instruction:
              'Find the function named extractSummary in packages/cli/scripts/scbe_workflow.cjs and verify the exact signature.',
            terminal_state: '$ ',
            done_if:
              "node -e \"const fs=require('fs');const t=fs.readFileSync('packages/cli/scripts/scbe_workflow.cjs','utf8');process.exit(t.includes('function extractSummary')?0:1)\"",
          }) + '\n\n',
        encoding: 'utf8',
        timeout: 20_000,
        env: { ...process.env, NO_COLOR: '1', SCBE_PROVIDER: 'offline' },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 2, `expected ready + response, got: ${r.stdout}`);
      const resp = JSON.parse(lines[1]);
      const ids = (resp.board.pazaak_cards || []).map((card) => card.id);
      assert.ok(ids.includes('focus_plus'), `expected focus_plus, got ${ids.join(',')}`);
      assert.ok(
        ids.includes('verify_minus_risk'),
        `expected verify_minus_risk, got ${ids.join(',')}`
      );
      return { cards: ids };
    })
  );

  cases.push(
    caseResult('agent_json_verifier_accepts_done_after_prior_move', () => {
      const { spawnSync: spawn } = require('node:child_process');
      const first = {
        instruction:
          'Run a small command, then stop only after the verifier confirms the task is complete.',
        terminal_state: '$ ',
        done_if: 'node -e "process.exit(0)"',
      };
      const second = { terminal_state: '$ node -e "console.log(1)"\n1' };
      const r = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
        cwd: REPO_ROOT,
        input: `${JSON.stringify(first)}\n${JSON.stringify(second)}\n\n`,
        encoding: 'utf8',
        timeout: 20_000,
        env: {
          ...process.env,
          NO_COLOR: '1',
          SCBE_MOCK_RESPONSE: '<cmd>node -e "console.log(1)"</cmd>',
        },
      });
      const lines = (r.stdout || '')
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      assert.ok(lines.length >= 3, `expected ready + two responses, got: ${r.stdout}`);
      const firstResp = JSON.parse(lines[1]);
      const secondResp = JSON.parse(lines[2]);
      assert.ok(firstResp.commands.length > 0, 'first turn should propose a command');
      assert.equal(secondResp.done, true);
      assert.equal(secondResp.step_complete, true);
      assert.equal(secondResp.verifier_accepted, true);
      assert.deepEqual(secondResp.commands, []);
      return { rationale: secondResp.rationale };
    })
  );

  const total = cases.reduce((sum, row) => sum + row.points, 0);
  const earned = cases.reduce((sum, row) => sum + row.earned, 0);
  const axis_scores = scoreByAxis(cases);
  const report = {
    schema: 'scbe_shell_agentic_benchmark_v1',
    generated_at: new Date().toISOString(),
    cli: CLI,
    branch: spawnSync('git', ['branch', '--show-current'], {
      cwd: REPO_ROOT,
      encoding: 'utf8',
    }).stdout.trim(),
    commit: spawnSync('git', ['rev-parse', '--short', 'HEAD'], {
      cwd: REPO_ROOT,
      encoding: 'utf8',
    }).stdout.trim(),
    score: {
      earned,
      total,
      percent: total ? Math.round((earned / total) * 10_000) / 100 : 0,
    },
    axis_scores,
    cases,
    ready: earned === total,
  };

  fs.mkdirSync(OUT_DIR, { recursive: true });
  const outPath = path.join(OUT_DIR, `${stamp()}-shell-agentic-benchmark.json`);
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  process.stdout.write(`${JSON.stringify({ ...report, artifact: outPath }, null, 2)}\n`);
  process.exit(report.ready ? 0 : 1);
}

// --last-artifact: read the most recent bench JSON and exit 0/1.
// Fails if the artifact was produced on a different commit than HEAD (stale guard).
// Pass --allow-stale to skip the commit check (e.g. in detached-HEAD CI contexts).
// Pass --artifact-dir=<path> to override the default artifact directory (used by tests).
if (process.argv.includes('--last-artifact')) {
  const artifactDirArg = process.argv.find((a) => a.startsWith('--artifact-dir='));
  const artifactDir = artifactDirArg ? artifactDirArg.slice('--artifact-dir='.length) : OUT_DIR;

  if (!fs.existsSync(artifactDir)) {
    process.stderr.write('No bench artifacts found\n');
    process.exit(1);
  }
  const files = fs
    .readdirSync(artifactDir)
    .filter((f) => f.endsWith('.json'))
    .sort();
  if (!files.length) {
    process.stderr.write('No bench artifacts found\n');
    process.exit(1);
  }
  let last;
  try {
    last = JSON.parse(fs.readFileSync(path.join(artifactDir, files[files.length - 1]), 'utf8'));
  } catch (e) {
    process.stderr.write(`Corrupted artifact: ${e.message}\n`);
    process.exit(1);
  }

  if (!process.argv.includes('--allow-stale')) {
    const headCommit = spawnSync('git', ['rev-parse', '--short', 'HEAD'], {
      cwd: REPO_ROOT,
      encoding: 'utf8',
    }).stdout.trim();
    const artifactCommit = (last.commit || '').trim();
    if (headCommit && artifactCommit && headCommit !== artifactCommit) {
      process.stderr.write(
        `Stale artifact: bench was run on ${artifactCommit}, HEAD is ${headCommit}. Run the bench first.\n`
      );
      process.exit(1);
    }
  }

  const { earned = 0, total = 0, percent = 0 } = last.score || {};
  process.stdout.write(
    `${earned}/${total} (${percent}%) — ${last.generated_at} — commit ${last.commit || 'unknown'}\n`
  );
  process.exit(percent === 100 ? 0 : 1);
}

main();
