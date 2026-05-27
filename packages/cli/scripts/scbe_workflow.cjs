#!/usr/bin/env node
/**
 * SCBE workflow driver.
 *
 * Drives `scbe shell --agent-json` through a multi-step workflow.
 * The harness owns step transitions — the model only sees the current step.
 * Each step gets a clean context; only a one-line summary from the previous
 * step is passed forward. No context clutter across steps.
 *
 * Workflow file format (JSON):
 * {
 *   "name": "fix failing tests",
 *   "steps": [
 *     {
 *       "id": "read_errors",
 *       "instruction": "Identify which tests are failing and why",
 *       "done_if": "test -f /tmp/scbe_errors.txt",
 *       "loop": false,
 *       "max_turns": 5
 *     },
 *     {
 *       "id": "fix_code",
 *       "instruction": "Fix the errors identified in the previous step",
 *       "done_if": "npm test && echo SCBE_PASS",
 *       "loop": true,
 *       "max_turns": 20
 *     }
 *   ]
 * }
 *
 * loop: false — advance after first model response only if done_if passes
 * loop: true  — retry until done_if passes or max_turns hit
 * allow_unverified: true — explicit escape hatch for observation-only steps
 *
 * Usage:
 *   node scripts/scbe_workflow.cjs path/to/workflow.json
 *   SCBE_MODEL=groq/llama-3.3-70b-versatile node scripts/scbe_workflow.cjs workflow.json
 *   node scripts/scbe_workflow.cjs --example     # print example workflow and exit
 */

'use strict';

const { spawnSync, spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');
const OUT_DIR = path.join(REPO_ROOT, 'artifacts', 'workflow');

function commandExists(name) {
  const r = spawnSync(process.platform === 'win32' ? 'where.exe' : 'command', [name], {
    encoding: 'utf8',
    shell: process.platform !== 'win32',
  });
  return r.status === 0;
}

function detectShell() {
  if (process.platform !== 'win32') return { kind: 'bash', exe: '/bin/bash', args: ['-c'] };

  const where = spawnSync('where.exe', ['bash.exe'], { encoding: 'utf8' });
  const gitBash = (where.stdout || '')
    .split(/\r?\n/)
    .map((l) => l.trim())
    .find(
      (l) =>
        l && !/\\windows\\system32\\bash\.exe$/i.test(l) && !/\\WindowsApps\\bash\.exe$/i.test(l)
    );
  if (gitBash) return { kind: 'bash', exe: gitBash, args: ['-c'] };

  if (commandExists('pwsh.exe')) {
    return {
      kind: 'powershell',
      exe: 'pwsh.exe',
      args: ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command'],
    };
  }
  return {
    kind: 'powershell',
    exe: 'powershell.exe',
    args: ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command'],
  };
}

const SHELL = detectShell();

function normalizeVerifierCommand(cmd) {
  const value = String(cmd || '').trim();
  if (value.startsWith(':test ')) return value.slice(':test '.length).trim();
  if (value.startsWith(':cmd ')) return value.slice(':cmd '.length).trim();
  return value;
}

function runShell(cmd) {
  const verifier = normalizeVerifierCommand(cmd);
  const r = spawnSync(SHELL.exe, [...SHELL.args, verifier], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    timeout: 30000,
  });
  return {
    stdout: (r.stdout || '').trim(),
    stderr: (r.stderr || '').trim(),
    status: r.status ?? 1,
  };
}

function verifyStep(step) {
  if (!step.done_if) {
    return {
      ok: !!step.allow_unverified,
      stdout: '',
      stderr: '',
      status: step.allow_unverified ? 0 : 1,
    };
  }
  return runShell(step.done_if);
}

function extractSummary(step, terminalState, lastRationale, completed) {
  const status = completed ? 'DONE' : 'INCOMPLETE';
  const goalSnippet = (step.instruction || '').slice(0, 80).replace(/\n/g, ' ');
  // Find output lines after the last shell prompt in terminal state
  const stateLines = (terminalState || '').split('\n');
  const lastPromptIdx = stateLines.reduce((acc, l, i) => (l.startsWith('$ ') ? i : acc), -1);
  const outputLines = (lastPromptIdx >= 0 ? stateLines.slice(lastPromptIdx + 1) : stateLines).filter(Boolean);
  const keyOutput = outputLines.slice(0, 4).join(' ').replace(/\s+/g, ' ').slice(0, 150);
  const contentPart = keyOutput || (lastRationale || '').slice(0, 100).replace(/\n/g, ' ') || '(no output)';
  return `[${status}] ${step.id}: ${goalSnippet}. Output: ${contentPart}`.slice(0, 300);
}

function sendLine(proc, obj) {
  proc.stdin.write(JSON.stringify(obj) + '\n');
}

function recvLine(proc, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    let buf = '';
    const timer = setTimeout(() => {
      proc.stdout.off('data', onData);
      reject(new Error(`recv timeout after ${timeoutMs}ms`));
    }, timeoutMs);
    const onData = (chunk) => {
      buf += chunk;
      const nl = buf.indexOf('\n');
      if (nl !== -1) {
        clearTimeout(timer);
        proc.stdout.off('data', onData);
        const line = buf.slice(0, nl).trim();
        try {
          resolve(JSON.parse(line));
        } catch (e) {
          reject(new Error(`bad JSON from agent: ${line.slice(0, 200)}`));
        }
      }
    };
    proc.stdout.on('data', onData);
  });
}

async function runStep(proc, step, stepIndex, totalSteps, prevSummary, initialTerminalState) {
  const stepNum = stepIndex + 1;
  const isFirst = stepIndex === 0;
  const maxTurns = step.max_turns ?? (step.loop ? 20 : 5);

  console.log(`\n${'─'.repeat(60)}`);
  console.log(`Step ${stepNum}/${totalSteps}: ${step.id}`);
  console.log(`Instruction: ${step.instruction.slice(0, 120)}`);
  console.log(`Loop: ${step.loop ? 'yes' : 'no'}  Max turns: ${maxTurns}`);
  if (prevSummary) console.log(`Context from prev: ${prevSummary.slice(0, 100)}`);

  // Send step init message (reset_context for all steps after the first)
  sendLine(proc, {
    instruction: step.instruction,
    terminal_state: initialTerminalState || '$ ',
    done_if: step.done_if || null,
    reset_context: !isFirst,
    step_context: isFirst ? null : prevSummary,
    step_index: stepNum,
    step_total: totalSteps,
    max_turns: maxTurns,
  });

  let terminalState = initialTerminalState || '$ ';
  let lastRationale = '';
  let stepComplete = false;
  let turns = 0;

  while (turns < maxTurns) {
    let resp;
    try {
      resp = await recvLine(proc, 60000);
    } catch (e) {
      console.error(`  [TIMEOUT] ${e.message}`);
      break;
    }

    turns++;

    if (resp.error) {
      console.error(`  [ERROR] ${resp.error}`);
      break;
    }
    if (resp.max_turns_reached) {
      console.log(`  [MAX_TURNS] Step hit turn limit (${maxTurns})`);
      break;
    }

    const cmd = resp.commands && resp.commands[0] ? resp.commands[0].keystrokes : null;
    lastRationale = resp.rationale || '';

    console.log(
      `  Turn ${turns}: ${cmd ? `cmd=${cmd.slice(0, 70)}` : '(no cmd)'} | done=${resp.done}`
    );

    const verifier = verifyStep(step);

    if (resp.step_complete || resp.done || verifier.ok || verifier.status === 0) {
      stepComplete = true;
      console.log(`  [COMPLETE] Step ${stepNum} verified complete`);
      break;
    }

    if (!step.loop) {
      // Non-loop: capture output and advance immediately
      if (cmd) {
        const exec = runShell(cmd);
        terminalState = `$ ${cmd}\n${exec.stdout}${exec.stderr ? '\n' + exec.stderr : ''}`;
        console.log(`  Exec: ${exec.stdout.slice(0, 80) || '(empty)'}`);
      }
      const postExecVerifier = verifyStep(step);
      if (postExecVerifier.status === 0) {
        stepComplete = true;
        console.log(`  [COMPLETE] Step ${stepNum} verified complete`);
      } else if (step.allow_unverified) {
        console.log(`  [UNVERIFIED] Step ${stepNum} allowed to advance by allow_unverified=true`);
      } else {
        console.log(
          `  [VERIFY_FAILED] ${step.done_if ? step.done_if.slice(0, 100) : 'missing done_if'}`
        );
      }
      break;
    }

    // Loop step: execute command and send next turn
    if (cmd) {
      const exec = runShell(cmd);
      terminalState = `$ ${cmd}\n${exec.stdout}${exec.stderr ? '\n' + exec.stderr : ''}`;
      console.log(`  Exec: ${exec.stdout.slice(0, 80) || '(empty)'}`);
      const postExecVerifier = verifyStep(step);
      if (postExecVerifier.status === 0) {
        stepComplete = true;
        console.log(`  [COMPLETE] Step ${stepNum} verified complete`);
        break;
      }
    }

    if (resp.blocked) {
      console.log(
        `  [BLOCKED] ${resp.rationale ? resp.rationale.slice(0, 80) : 'governance/ko-ban'}`
      );
    }

    sendLine(proc, { terminal_state: terminalState });
  }

  const summary = extractSummary(step, terminalState, lastRationale, stepComplete);
  return { step_id: step.id, completed: stepComplete, turns, summary };
}

async function runWorkflow(workflowPath) {
  const wf = JSON.parse(fs.readFileSync(workflowPath, 'utf8'));
  const steps = wf.steps || [];
  if (!steps.length) throw new Error('Workflow has no steps');

  console.log(`\nWorkflow: ${wf.name || workflowPath}`);
  console.log(`Steps: ${steps.length}`);

  const proc = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
    stdio: ['pipe', 'pipe', 'inherit'],
    cwd: REPO_ROOT,
    env: { ...process.env, NO_COLOR: '1' },
  });

  // Wait for ready signal
  const ready = await recvLine(proc, 10000);
  if (!ready.ready) throw new Error(`Expected ready signal, got: ${JSON.stringify(ready)}`);

  const results = [];
  let prevSummary = null;
  let terminalState = wf.initial_terminal_state || '$ ';

  for (let i = 0; i < steps.length; i++) {
    const result = await runStep(proc, steps[i], i, steps.length, prevSummary, terminalState);
    results.push(result);
    prevSummary = result.summary;
    // Terminal state passes forward (harness owns the environment)
  }

  proc.stdin.end();
  proc.kill();

  const completed = results.filter((r) => r.completed).length;
  console.log(`\n${'═'.repeat(60)}`);
  console.log(`Workflow complete: ${completed}/${steps.length} steps verified`);
  for (const r of results) {
    console.log(`  ${r.completed ? '[OK]' : '[--]'} ${r.step_id} (${r.turns} turns)`);
  }

  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const reportPath = path.join(
    OUT_DIR,
    `${stamp}-${(wf.name || 'workflow').replace(/\s+/g, '-')}.json`
  );
  fs.writeFileSync(
    reportPath,
    JSON.stringify(
      { workflow: wf.name, steps: results, timestamp: new Date().toISOString() },
      null,
      2
    )
  );
  console.log(`Receipt: ${reportPath}`);

  return results;
}

// ── Example workflow output ──────────────────────────────────────────────────

function printExample() {
  const example = {
    name: 'fix-failing-tests',
    steps: [
      {
        id: 'identify',
        instruction: 'Run the tests and write any failures to /tmp/scbe_errors.txt',
        done_if: 'test -f /tmp/scbe_errors.txt && test -s /tmp/scbe_errors.txt',
        loop: false,
        max_turns: 5,
      },
      {
        id: 'fix',
        instruction: 'Fix the test failures listed in /tmp/scbe_errors.txt',
        done_if: ':test npm test',
        loop: true,
        max_turns: 20,
      },
      {
        id: 'verify',
        instruction: 'Run the full test suite and confirm all tests pass',
        done_if: 'npm test',
        loop: false,
        max_turns: 3,
      },
    ],
  };
  console.log(JSON.stringify(example, null, 2));
}

// ── Main ─────────────────────────────────────────────────────────────────────

(async () => {
  const arg = process.argv[2];
  if (!arg || arg === '--help') {
    console.log('Usage: node scbe_workflow.cjs <workflow.json>');
    console.log('       node scbe_workflow.cjs --example');
    process.exit(0);
  }
  if (arg === '--example') {
    printExample();
    process.exit(0);
  }
  try {
    const results = await runWorkflow(path.resolve(arg));
    const allDone = results.every((r) => r.completed);
    process.exit(allDone ? 0 : 1);
  } catch (e) {
    console.error('Workflow error:', e.message);
    process.exit(1);
  }
})();
