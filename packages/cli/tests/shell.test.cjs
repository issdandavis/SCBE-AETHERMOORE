const assert = require('node:assert/strict');
const { spawn, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');

function runCli(args, options = {}) {
  const home = options.home || fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-shell-'));
  const env = {
    ...process.env,
    ...(options.env || {}),
    HOME: home,
    USERPROFILE: home,
    NO_COLOR: '1',
  };
  return spawnSync(process.execPath, [CLI, ...args], {
    input: options.input || '',
    encoding: 'utf8',
    timeout: options.timeout || 15_000,
    env,
  });
}

function decodeNodeEvalPayload(command) {
  const match = String(command || '').match(/Buffer\.from\('([^']+)','base64'\)/);
  if (!match) return String(command || '');
  try {
    return Buffer.from(match[1], 'base64').toString('utf8');
  } catch {
    return String(command || '');
  }
}

test('alias command saves shortcuts and executes them through receipts', () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-alias-'));

  const saved = runCli(['alias', '--json', 'g', 'node', '--version'], { home });
  assert.equal(saved.status, 0, saved.stderr);
  const savedPayload = JSON.parse(saved.stdout);
  assert.equal(savedPayload.ok, true);
  assert.equal(savedPayload.name, 'g');
  assert.equal(savedPayload.command, 'node --version');

  const listed = runCli(['alias', 'list', '--json'], { home });
  assert.equal(listed.status, 0, listed.stderr);
  const listedPayload = JSON.parse(listed.stdout);
  assert.equal(listedPayload.aliases.g, 'node --version');

  const terminal = runCli(['terminal', '--json'], { home });
  assert.equal(terminal.status, 0, terminal.stderr);
  const terminalPayload = JSON.parse(terminal.stdout);
  assert.deepEqual(terminalPayload.aliases, [{ name: 'g', command: 'node --version' }]);

  const ran = runCli(['g', '--json'], { home });
  assert.equal(ran.status, 0, ran.stderr);
  const ranPayload = JSON.parse(ran.stdout);
  assert.equal(ranPayload.schema_version, 'scbe_terminal_run_v1');
  assert.equal(ranPayload.alias, 'g');
  assert.equal(ranPayload.command, 'node --version');
  assert.equal(ranPayload.success, true);

  const removed = runCli(['alias', 'rm', 'g', '--json'], { home });
  assert.equal(removed.status, 0, removed.stderr);
  assert.equal(JSON.parse(removed.stdout).removed, 'g');
});

function recvJsonLine(proc, timeoutMs = 30_000) {
  return new Promise((resolve, reject) => {
    let buf = '';
    const timer = setTimeout(() => {
      proc.stdout.off('data', onData);
      reject(new Error(`timeout waiting for agent-json line after ${timeoutMs}ms`));
    }, timeoutMs);
    function onData(chunk) {
      buf += chunk;
      const newline = buf.indexOf('\n');
      if (newline === -1) return;
      clearTimeout(timer);
      proc.stdout.off('data', onData);
      const line = buf.slice(0, newline).trim();
      try {
        resolve(JSON.parse(line));
      } catch (err) {
        reject(new Error(`bad JSON line: ${line.slice(0, 300)} (${err.message})`));
      }
    }
    proc.stdout.on('data', onData);
  });
}

function sendJsonLine(proc, payload) {
  proc.stdin.write(JSON.stringify(payload) + '\n');
}

function waitForText(proc, pattern, timeoutMs = 30_000) {
  return new Promise((resolve, reject) => {
    let buf = '';
    const timer = setTimeout(() => {
      proc.stdout.off('data', onData);
      reject(new Error(`timeout waiting for output matching ${pattern}`));
    }, timeoutMs);
    function onData(chunk) {
      buf += chunk.toString('utf8');
      if (pattern.test(buf)) {
        clearTimeout(timer);
        proc.stdout.off('data', onData);
        resolve(buf);
      }
    }
    proc.stdout.on('data', onData);
  });
}

test('help documents personal shell modes', () => {
  const result = runCli(['--help']);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /scbe shell\s+Personal command shell/);
  assert.match(result.stdout, /scbe shell --ai/);
  assert.match(result.stdout, /scbe shell --tui/);
  assert.match(result.stdout, /scbe shell --minimal/);
  assert.match(result.stdout, /platform \[--json\]/);
});

test('platform command emits cross-platform readiness JSON', () => {
  const result = runCli(['platform', '--json']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_platform_readiness_v1');
  assert.equal(payload.host.platform, process.platform);
  assert.ok(Array.isArray(payload.readiness));
  assert.ok(payload.readiness.some((row) => row.id === 'node_runtime'));
  assert.ok(payload.readiness.some((row) => row.id === 'agent_bus'));
  assert.ok(payload.modes.some((mode) => mode.command === 'scbe shell --agent-json'));
  assert.ok(payload.install_hints.scbe.includes('npm i -g'));
});

test('platform command plain output gives best modes and install hints', () => {
  const result = runCli(['platform']);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /SCBE platform readiness/);
  assert.match(result.stdout, /Best modes:/);
  assert.match(result.stdout, /Automation:\s+scbe shell --agent-json/);
  assert.match(result.stdout, /Cross-platform install hints:/);
});

test('agent-json reroutes repeated observation command into verifier artifact write', async () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-agent-json-'));
  const workdir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-agent-route-'));
  const answerFile = path.join(workdir, 'answer.txt').replace(/\\/g, '/');
  const mockResponse =
    '<cmd>node --test packages/cli/tests/bench_artifact_freshness.test.cjs</cmd>';
  const proc = spawn(process.execPath, [CLI, 'shell', '--agent-json'], {
    cwd: path.resolve(__dirname, '..', '..', '..'),
    env: {
      ...process.env,
      HOME: home,
      USERPROFILE: home,
      NO_COLOR: '1',
      SCBE_MOCK_RESPONSE: mockResponse,
      SCBE_AGENT_JSON_SKIP_GOVERNANCE: '1',
    },
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  try {
    const ready = await recvJsonLine(proc);
    assert.equal(ready.ready, true);

    const done_if = `node -e "const t=require('fs').readFileSync('${answerFile}','utf8').trim();if(parseInt(t)<15)process.exit(1)"`;
    sendJsonLine(proc, {
      instruction:
        "Run the benchmark artifact freshness test suite at packages/cli/tests/bench_artifact_freshness.test.cjs using Node's built-in test runner (`node --test packages/cli/tests/bench_artifact_freshness.test.cjs`). Count the passing tests from the output. Write the count as a plain integer to `" +
        answerFile +
        '`.',
      terminal_state: '$ ',
      done_if,
      max_turns: 4,
    });
    const first = await recvJsonLine(proc);
    assert.match(first.commands[0].keystrokes, /bench_artifact_freshness\.test\.cjs/);

    const observedPasses = Array.from({ length: 16 }, (_, i) => `✔ synthetic pass ${i + 1}`).join(
      '\n'
    );
    sendJsonLine(proc, {
      terminal_state:
        `$ ${first.commands[0].keystrokes}\n` +
        observedPasses +
        '\n# verifier still needs answer.txt',
    });
    const second = await recvJsonLine(proc);

    const decodedCommand = decodeNodeEvalPayload(second.commands[0].keystrokes);
    assert.match(decodedCommand, /writeFileSync/);
    assert.match(decodedCommand, /answer\.txt/);
    assert.match(decodedCommand, /SCBE_ROUTE_WRITE/);
    assert.equal(second.board.last_route_hint.reason, 'repeated-command-phase-shift');
  } finally {
    proc.kill();
    fs.rmSync(home, { recursive: true, force: true });
    fs.rmSync(workdir, { recursive: true, force: true });
  }
});

test('minimal shell preserves scriptable exit behavior', () => {
  const result = runCli(['shell', '--minimal'], { input: ':exit\n' });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /SCBE Terminal/);
  assert.doesNotMatch(result.stdout, /SCBE governed shell/);
});

test('rich shell supports config inspection without touching real home config', () => {
  const result = runCli(['shell'], { input: ':config\n:exit\n' });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /SCBE\s+local/);
  assert.match(result.stdout, /"provider": "ollama"/);
  assert.match(result.stdout, /"model": "[^"]+"/);
});

test('rich shell lists local models without leaving the shell', () => {
  const result = runCli(['shell'], { input: ':models\n:exit\n' });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /SCBE\s+local/);
  assert.match(result.stdout, /local Ollama models|no local Ollama models found/);
});

test('rich shell help is shell-specific and does not dump full CLI manual', () => {
  const result = runCli(['shell'], { input: 'help\n:exit\n' });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /SCBE shell commands/);
  assert.match(result.stdout, /Time\/date:/);
  assert.match(result.stdout, /Math:/);
  assert.match(result.stdout, /Files:/);
  assert.match(result.stdout, /Build:/);
  assert.match(result.stdout, /room builder/);
  assert.match(result.stdout, /Raw tab grammar/);
  assert.doesNotMatch(result.stdout, /scbe-aethermoore-cli/);
  assert.doesNotMatch(result.stdout, /BENCH — executable evidence lanes/);
});

test('rich shell tools question is answered locally', () => {
  const result = runCli(['shell'], {
    input: 'what tools do you have\n:exit\n',
    env: { SCBE_MOCK_RESPONSE: 'should-not-call-model' },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Tools available in this shell/);
  assert.match(result.stdout, /time\/date\s+Print local time and date/);
  assert.match(result.stdout, /math\/calc\s+Calculate an expression/);
  assert.match(result.stdout, /read\s+Read a text file/);
  assert.match(result.stdout, /run\s+Run a system command directly/);
  assert.match(result.stdout, /room\s+Create\/switch agent rooms/);
  assert.match(result.stdout, /ask\/call/);
  assert.doesNotMatch(result.stdout, /should-not-call-model/);
});

test('rich shell handles everyday clock and math builtins without model', () => {
  const result = runCli(['shell'], {
    input: 'now\nmath 2 + 2 * sqrt(9)\n:exit\n',
    env: { SCBE_MOCK_RESPONSE: 'should-not-call-model' },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /now:/);
  assert.match(result.stdout, /timezone:/);
  assert.match(result.stdout, /= 8/);
  assert.doesNotMatch(result.stdout, /should-not-call-model/);
});

test('rich shell solves spoken factorial derivative dual math locally', () => {
  const result = runCli(['shell'], {
    input:
      'square root of 89 times the inverse ratio of the factoral derivate of 89 before and after the inverse ratio as a dual oeprtiuon\n:exit\n',
    env: { SCBE_MOCK_RESPONSE: 'should-not-call-model' },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /worksheet: compute\.spoken_math/);
  assert.match(result.stdout, /skills: math-worksheet/);
  assert.match(result.stdout, /primary:/);
  assert.match(result.stdout, /0\.104808/);
  assert.match(result.stdout, /dual:/);
  assert.match(result.stdout, /849\.165/);
  assert.doesNotMatch(result.stdout, /should-not-call-model/);
});

test('math command solves spoken factorial derivative dual phrase as a worksheet', () => {
  const result = runCli([
    'math',
    'square',
    'root',
    'of',
    '89',
    'times',
    'inverse',
    'ratio',
    'of',
    'factorial',
    'derivative',
    'of',
    '89',
    'before',
    'and',
    'after',
    'as',
    'dual',
  ]);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /worksheet: compute\.spoken_math/);
  assert.match(result.stdout, /primary:/);
  assert.match(result.stdout, /dual:/);
});

test('infer command fills a mechanical worksheet with hidden skill cards', () => {
  const result = runCli([
    'infer',
    'pull',
    'latest',
    'changes',
    'then',
    'fetch',
    'docs',
    'with',
    'parallel',
    'thinking',
  ]);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /worksheet: worksheet\.generic/);
  assert.match(result.stdout, /skills: pull, fetch, parallel-thinking/);
  assert.match(result.stdout, /execute: no/);
});

test('infer command routes geoseal and termux worksheets with typo tolerance', () => {
  const result = runCli([
    'infer',
    'geoseal',
    'compile',
    'intent',
    'summarize',
    'README',
    'with',
    'termunx',
    'fallback',
  ]);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /worksheet: worksheet\.generic/);
  assert.match(result.stdout, /skills: geoseal, termux/);
  assert.match(result.stdout, /execute: no/);
});

test('bare sentence routes to worksheet before weak natural-language guess', () => {
  const result = runCli([
    'geoseal',
    'compile',
    'intent',
    'summarize',
    'README',
    'with',
    'termunx',
    'fallback',
  ]);

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /worksheet: worksheet\.generic/);
  assert.match(result.stdout, /skills: geoseal, termux/);
  assert.doesNotMatch(result.stderr, /workspace ingest/);
});

test('rich shell treats run plus prose as an assistant request, not executable a.exe', () => {
  const result = runCli(['shell'], {
    input: 'run a polynomial search function through negative inner counter space\n:exit\n',
    env: { SCBE_MOCK_RESPONSE: 'prose-route-ok' },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /prose-route-ok/);
  assert.doesNotMatch(result.stdout + result.stderr, /'a' is not recognized/);
});

test('rich shell handles file write read and count builtins', () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-core-home-'));
  const workdir = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-core-work-'));
  const env = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
    NO_COLOR: '1',
    SCBE_MOCK_RESPONSE: 'should-not-call-model',
  };
  const result = spawnSync(process.execPath, [CLI, 'shell'], {
    cwd: workdir,
    input: 'write note.txt hello world\nread note.txt\ncount note.txt\n:exit\n',
    encoding: 'utf8',
    timeout: 15_000,
    env,
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /wrote 11 bytes/);
  assert.match(result.stdout, /hello world/);
  assert.match(result.stdout, /words: 2/);
  assert.doesNotMatch(result.stdout, /should-not-call-model/);

  fs.rmSync(home, { recursive: true, force: true });
  fs.rmSync(workdir, { recursive: true, force: true });
});

test('rich shell run builtin executes a normal system command directly', () => {
  const result = runCli(['shell'], {
    input: 'run node -e "console.log(12345)"\n:exit\n',
    env: { SCBE_MOCK_RESPONSE: 'should-not-call-model' },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /12345/);
  assert.doesNotMatch(result.stdout, /SCBE .*GeoSeal/);
  assert.doesNotMatch(result.stdout, /should-not-call-model/);
});

test(
  'rich shell run builtin uses PowerShell semantics on Windows',
  { skip: process.platform !== 'win32' },
  () => {
    const binDir = path.resolve(__dirname, '..', 'bin');
    const result = runCli(['shell'], {
      input: `run Get-ChildItem -Name ${binDir}\n:exit\n`,
      env: { SCBE_MOCK_RESPONSE: 'should-not-call-model' },
    });

    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /scbe\.js/);
    assert.doesNotMatch(result.stdout + result.stderr, /not recognized/);
    assert.doesNotMatch(result.stdout, /should-not-call-model/);
  }
);

test('rich shell supports short room chat aliases', () => {
  const result = runCli(['shell'], {
    input: 'room builder\nask builder hello from room\nrooms\n:exit\n',
    env: { SCBE_MOCK_RESPONSE: 'builder-chat-ok' },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /active tab 2: builder/);
  assert.match(result.stdout, /\[tab:2 builder\]/);
  assert.match(result.stdout, /builder-chat-ok/);
  assert.match(result.stdout, /shell tabs/);
  assert.match(result.stdout, /2 builder/);
});

test('rich shell supports short room command aliases', () => {
  const result = runCli(['shell'], {
    input: 'room worker\ncmd worker echo easy-room-ok\nrooms\n:exit\n',
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /active tab 2: worker/);
  assert.match(result.stdout, /easy-room-ok/);
  assert.match(result.stdout, /last=run:ok/);
});

test('rich shell supports agent-addressable tab run commands', () => {
  const result = runCli(['shell'], {
    input: 'tab:new:worker\ntab:2:run:echo agent-room-ok\ntab:list\n:exit\n',
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /active tab 2: worker/);
  assert.match(result.stdout, /agent-room-ok/);
  assert.match(result.stdout, /shell tabs/);
  assert.match(result.stdout, /2 worker/);
  assert.match(result.stdout, /last=run:ok/);
});

test('rich shell supports mocked agent-addressable tab chat commands', () => {
  const result = runCli(['shell'], {
    input: 'tab:1:chat:hello from an agent\n:exit\n',
    env: { SCBE_MOCK_RESPONSE: 'tab-agent-ok' },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /\[tab:1 main\]/);
  assert.match(result.stdout, /tab-agent-ok/);
});

test('rich shell natural-language chat uses active tab history', () => {
  const result = runCli(['shell'], {
    input: 'hey\n:exit\n',
    env: { SCBE_MOCK_RESPONSE: 'normal-chat-ok' },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /ollama:[^\s]+/);
  assert.match(result.stdout, /normal-chat-ok/);
  assert.doesNotMatch(result.stderr + result.stdout, /ReferenceError: history is not defined/);
});

test('rich shell logs AI-routed utterances to isolated local log', async () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-utt-home-'));
  const logPath = path.join(home, 'utterance-log.jsonl');
  const proc = spawn(process.execPath, [CLI, 'shell'], {
    cwd: path.resolve(__dirname, '..', '..', '..'),
    env: {
      ...process.env,
      HOME: home,
      USERPROFILE: home,
      NO_COLOR: '1',
      SCBE_NO_UTTERANCE_LOG: '',
      SCBE_UTTERANCE_LOG: logPath,
      SCBE_UTTERANCE_LOG_SCRIPTED: '1',
      SCBE_MOCK_RESPONSE: '<cmd>node -e "console.log(1)"</cmd>',
    },
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  try {
    proc.stdin.write('hey\n');
    const firstRoute = await waitForText(proc, /execute\? \[y\/N\]|blocked:/);
    const allowed = /execute\? \[y\/N\]/.test(firstRoute);
    if (allowed) {
      proc.stdin.write('y\n');
      await waitForText(proc, /\$ node -e "console\.log\(1\)"/);
    }
    proc.stdin.write(':exit\n');
    await new Promise((resolve) => proc.once('close', resolve));

    const records = fs
      .readFileSync(logPath, 'utf8')
      .trim()
      .split(/\r?\n/)
      .map((line) => JSON.parse(line));
    assert.equal(records.length, 1);
    assert.equal(records[0].utterance, 'hey');
    assert.ok(records[0].tool);
    assert.match(records[0].decision, allowed ? /^(ALLOW|ROUTE)$/ : /^(BLOCKED|DENY|QUARANTINE)$/);
    assert.equal(records[0].mode, 'ai');
    assert.equal(records[0].confirmed, allowed);
  } finally {
    proc.kill();
    fs.rmSync(home, { recursive: true, force: true });
  }
});

test('rich shell rejects nonsense model-proposed commands before approval', () => {
  const result = runCli(['shell'], {
    input: 'lol\n:exit\n',
    env: { SCBE_MOCK_RESPONSE: '<cmd>a</cmd>; lol' },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /ignored proposed command/);
  assert.match(result.stdout, /one-letter command/);
  assert.doesNotMatch(result.stdout, /execute\? \[y\/N\]/);
});

test('tui.mjs exists and exports launchTui', async () => {
  const { pathToFileURL } = require('node:url');
  const tuiPath = path.resolve(__dirname, '..', 'bin', 'tui.mjs');
  assert.ok(fs.existsSync(tuiPath), 'bin/tui.mjs must exist');
  const m = await import(pathToFileURL(tuiPath).href);
  assert.equal(typeof m.launchTui, 'function', 'tui.mjs must export launchTui');
});
