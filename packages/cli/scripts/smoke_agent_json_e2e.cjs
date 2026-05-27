/**
 * End-to-end smoke for scbe shell --agent-json.
 *
 * Drives the NDJSON loop locally: executes each returned command in a real
 * shell, feeds the output back as terminal_state, and validates that done=true
 * is only accepted after the objective verifier passes.
 *
 * Usage:
 *   node scripts/smoke_agent_json_e2e.cjs            # mock turns, Git Bash execution
 *   SCBE_LIVE=1 node scripts/smoke_agent_json_e2e.cjs # real LLM (needs shell.json config)
 */

'use strict';

const { spawnSync, spawn } = require('node:child_process');
const path = require('node:path');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');

const REPO_ROOT = path.resolve(__dirname, '../../..');
const CLI = path.resolve(__dirname, '../bin/scbe.js');

// Bash binary for executing commands
const BASH =
  process.platform === 'win32'
    ? (spawnSync('where', ['bash'], { encoding: 'utf8' }).stdout.split('\n').find((l) => l.trim()) || 'bash').trim()
    : '/bin/bash';

// Use /tmp — Git Bash maps this to a writable temp dir on Windows
const SMOKE_FILE = '/tmp/scbe_smoke_e2e.txt';
const SMOKE_CONTENT = 'hello_scbe';
const INSTRUCTION = `Create the file ${SMOKE_FILE} containing exactly the text: ${SMOKE_CONTENT}`;
const DONE_IF = `test -f '${SMOKE_FILE}' && grep -qF '${SMOKE_CONTENT}' '${SMOKE_FILE}'`;

// Multi-turn mock responses. Turn 0 uses the regex-stress response (model emits <cmd> instead of </cmd>).
// Turn 1 creates the file. Turn 2 verifies and signals done.
const MOCK_TURNS = [
  // Turn 0: malformed closing tag (the exact failure seen in the live Groq smoke)
  `I'll create the file now.\n<cmd>echo "${SMOKE_CONTENT}" > ${SMOKE_FILE}<cmd>\n\nLet me verify that worked.`,
  // Turn 1: verifies the file and signals done
  `The file exists and has the right content. <cmd>cat ${SMOKE_FILE}</cmd>\n<done>`,
];

function runBash(cmd) {
  const r = spawnSync(BASH, ['-c', cmd], { encoding: 'utf8', timeout: 15000 });
  return { stdout: (r.stdout || '').trim(), stderr: (r.stderr || '').trim(), status: r.status };
}

function cleanUp() {
  runBash(`rm -f '${SMOKE_FILE}'`);
}

function startAgent(mockTurns) {
  const env = { ...process.env, NO_COLOR: '1' };
  if (mockTurns) env.SCBE_MOCK_TURNS = JSON.stringify(mockTurns);

  const proc = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env,
    cwd: REPO_ROOT,
  });
  return proc;
}

function send(proc, msg) {
  proc.stdin.write(JSON.stringify(msg) + '\n');
}

function recv(proc) {
  return new Promise((resolve, reject) => {
    let buf = '';
    const onData = (chunk) => {
      buf += chunk;
      const nl = buf.indexOf('\n');
      if (nl !== -1) {
        proc.stdout.off('data', onData);
        const line = buf.slice(0, nl).trim();
        try { resolve(JSON.parse(line)); }
        catch (e) { reject(new Error(`bad JSON: ${line.slice(0, 200)}`)); }
      }
    };
    proc.stdout.on('data', onData);
    setTimeout(() => { proc.stdout.off('data', onData); reject(new Error('recv timeout')); }, 15000);
  });
}

// ── Mock-mode multi-turn test ──────────────────────────────────────────────

async function runMockSmoke() {
  console.log('\n═══ MOCK E2E SMOKE ═══');
  console.log(`Instruction : ${INSTRUCTION}`);
  console.log(`Verifier    : ${DONE_IF}`);
  console.log(`Bash        : ${BASH}`);
  cleanUp();

  // We'll drive the loop manually using SCBE_MOCK_RESPONSE changing per turn.
  // Since the harness only supports a single SCBE_MOCK_RESPONSE, we drive each
  // turn as a separate one-shot process invocation (same protocol, fresh state).
  // This tests: regex parse → command extraction → bash execution → verifier gate.

  let terminalState = '$ ';
  let turnsPassed = [];

  for (let turn = 0; turn < MOCK_TURNS.length; turn++) {
    const mockResp = MOCK_TURNS[turn];
    console.log(`\n── Turn ${turn} ──`);
    console.log('Mock response:', mockResp.replace(/\n/g, '\\n').slice(0, 100));

    const r = spawnSync(process.execPath, [CLI, 'shell', '--agent-json'], {
      cwd: REPO_ROOT,
      input: JSON.stringify({ instruction: INSTRUCTION, terminal_state: terminalState, done_if: DONE_IF }) + '\n\n',
      encoding: 'utf8',
      timeout: 20000,
      env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mockResp },
    });

    const lines = (r.stdout || '').split('\n').map((l) => l.trim()).filter(Boolean);
    assert.ok(lines.length >= 2, `expected ready + response, got stdout: ${r.stdout}`);

    const ready = JSON.parse(lines[0]);
    assert.ok(ready.ready, 'first line must be {ready:true}');

    const resp = JSON.parse(lines[1]);
    console.log('Response    :', JSON.stringify(resp).slice(0, 200));

    if (resp.commands && resp.commands.length > 0) {
      const ks = resp.commands[0].keystrokes;
      console.log('Command     :', ks);
      assert.ok(!ks.startsWith(':'), 'translated command must not start with :');

      const exec = runBash(ks);
      console.log('Exec stdout :', exec.stdout || '(empty)');
      console.log('Exec status :', exec.status);
      terminalState = `$ ${ks}\n${exec.stdout}${exec.stderr ? '\n' + exec.stderr : ''}`;
    }

    // Check if verify_failed was correctly triggered on turn 0 (file not yet created)
    if (turn === 0) {
      const fileExists = runBash(`test -f '${SMOKE_FILE}'`).status === 0;
      if (!fileExists) {
        console.log('PASS: file absent after turn 0 — verifier correctly prevented early done');
        assert.ok(!resp.done, `turn 0 done should be false (file does not exist), got: ${resp.done}`);
        assert.ok(resp.verify_failed, `turn 0 must have verify_failed=true because file absent`);
      } else {
        console.log('NOTE: file created on turn 0 (regex fix extracted valid command)');
      }
    }

    turnsPassed.push(turn);
  }

  // Final state: verify file exists and has correct content
  const finalCheck = runBash(`cat '${SMOKE_FILE}'`);
  console.log('\n── Final verification ──');
  console.log('File content:', JSON.stringify(finalCheck.stdout));
  console.log('Expected    :', JSON.stringify(SMOKE_CONTENT));

  if (finalCheck.stdout.trim() === SMOKE_CONTENT) {
    console.log('\n✓ SMOKE PASSED: file created with correct content');
  } else if (finalCheck.status !== 0) {
    console.log('\n✗ SMOKE FAILED: file not created');
    console.log('This means the regex fix did not extract a valid executable command.');
    process.exitCode = 1;
  } else {
    console.log('\n✗ SMOKE FAILED: file exists but content wrong');
    process.exitCode = 1;
  }

  cleanUp();
}

// ── Regex-stress unit test ─────────────────────────────────────────────────
// Directly verify that the regex fix extracts the right command from the
// known-bad Groq response format (uses <cmd> as closing tag).

function testRegexFix() {
  console.log('\n═══ REGEX FIX UNIT TEST ═══');

  const badResponse = `I'll create the file.\n<cmd>echo "${SMOKE_CONTENT}" > ${SMOKE_FILE}<cmd>\n\nLet me verify.`;
  const goodResponse = `<cmd>echo "${SMOKE_CONTENT}" > ${SMOKE_FILE}</cmd>`;

  function extractCmd(full) {
    // Same regex as scbe.js
    const m = full.match(/<cmd>([\s\S]*?)(?:<\/cmd>|(?=\s*<cmd>))/);
    return m ? m[1].trim() : null;
  }

  const fromBad = extractCmd(badResponse);
  const fromGood = extractCmd(goodResponse);

  console.log('Bad  (Groq-style):', fromBad);
  console.log('Good (proper)    :', fromGood);

  assert.strictEqual(fromBad, `echo "${SMOKE_CONTENT}" > ${SMOKE_FILE}`, 'regex must extract cmd from <cmd>...<cmd> format');
  assert.strictEqual(fromGood, `echo "${SMOKE_CONTENT}" > ${SMOKE_FILE}`, 'regex must extract cmd from <cmd>...</cmd> format');

  // Execute bad-format extracted command, verify result, clean up
  cleanUp();
  const r1 = runBash(fromBad);
  assert.strictEqual(r1.status, 0, `bad-format cmd must execute (status 0), got stderr: ${r1.stderr}`);
  const c1 = runBash(`cat '${SMOKE_FILE}'`);
  assert.strictEqual(c1.stdout.trim(), SMOKE_CONTENT, `bad-format: file content must equal "${SMOKE_CONTENT}", got: "${c1.stdout.trim()}"`);
  cleanUp();

  // Execute good-format extracted command, verify result, clean up
  const r2 = runBash(fromGood);
  assert.strictEqual(r2.status, 0, `good-format cmd must execute (status 0), got stderr: ${r2.stderr}`);
  const c2 = runBash(`cat '${SMOKE_FILE}'`);
  assert.strictEqual(c2.stdout.trim(), SMOKE_CONTENT, `good-format: file content must equal "${SMOKE_CONTENT}", got: "${c2.stdout.trim()}"`);

  console.log('✓ Regex fix correctly extracts executable commands from both formats');
  cleanUp();
}

// ── Verifier gate unit test ────────────────────────────────────────────────
// Tests that done_if prevents early done even when the model signals completion.

async function testVerifierGate() {
  console.log('\n═══ VERIFIER GATE TEST ═══');
  cleanUp(); // ensure file does not exist

  const mockDoneEarly = `I think the task is complete. <done>`;

  const r = spawnSync(process.execPath, [CLI, 'shell', '--agent-json'], {
    cwd: REPO_ROOT,
    input: JSON.stringify({ instruction: INSTRUCTION, terminal_state: '$ ', done_if: DONE_IF }) + '\n\n',
    encoding: 'utf8',
    timeout: 20000,
    env: { ...process.env, NO_COLOR: '1', SCBE_MOCK_RESPONSE: mockDoneEarly },
  });

  const lines = (r.stdout || '').split('\n').map((l) => l.trim()).filter(Boolean);
  assert.ok(lines.length >= 2, `expected ready + response`);

  const resp = JSON.parse(lines[1]);
  console.log('Response:', JSON.stringify(resp).slice(0, 300));

  assert.ok(!resp.done, `done must be false when done_if check fails (file does not exist)`);
  assert.ok(resp.verify_failed, `verify_failed must be true`);
  assert.ok(resp.rationale.includes('verifier'), `rationale must mention verifier`);

  console.log('✓ Verifier gate correctly blocked early done signal');
  cleanUp();
}

// ── Main ──────────────────────────────────────────────────────────────────

(async () => {
  try {
    testRegexFix();
    await testVerifierGate();
    await runMockSmoke();
    console.log('\n═══ ALL E2E SMOKE TESTS PASSED ═══\n');
  } catch (e) {
    console.error('\n✗ SMOKE FAILED:', e.message);
    if (e.stack) console.error(e.stack);
    cleanUp();
    process.exit(1);
  }
})();
