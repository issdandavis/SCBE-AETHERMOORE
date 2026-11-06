'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { Readable, Writable } = require('node:stream');
const test = require('node:test');

const {
  MAX_MESSAGES,
  createSession,
  loadSession,
  normalizeMessages,
  saveSession,
  workspaceKey,
} = require('../lib/session-store');
const { runAgentShell, sanitizeTerminalText } = require('../lib/agent-shell');

function makeTemp(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function removeTemp(target) {
  const resolved = path.resolve(target);
  const tempRoot = `${path.resolve(os.tmpdir())}${path.sep}`;
  assert.ok(resolved.startsWith(tempRoot), `refusing to remove non-temp path: ${resolved}`);
  fs.rmSync(resolved, { recursive: true, force: true });
}

function transcriptSink() {
  let transcript = '';
  return {
    output: new Writable({
      write(chunk, _encoding, callback) {
        transcript += chunk.toString('utf8');
        callback();
      },
    }),
    read: () => transcript,
  };
}

test('workspace identity folds case on Windows but preserves it on POSIX', () => {
  const upper = path.resolve('SCBE-Workspace-Case-Probe').toUpperCase();
  const lower = upper.toLowerCase();

  assert.equal(workspaceKey(upper, { platform: 'win32' }), workspaceKey(lower, { platform: 'win32' }));
  assert.notEqual(workspaceKey(upper, { platform: 'linux' }), workspaceKey(lower, { platform: 'linux' }));
  assert.equal(
    workspaceKey(upper),
    workspaceKey(process.platform === 'win32' ? lower : upper)
  );
});

test('message trimming retains whole tool turns and summarizes dropped history', (t) => {
  const workspaceRoot = makeTemp('scbe-session-hardening-work-');
  const home = makeTemp('scbe-session-hardening-home-');
  t.after(() => {
    removeTemp(workspaceRoot);
    removeTemp(home);
  });

  const messages = [];
  for (let index = 0; index < 70; index += 1) {
    const callId = `call-${index}`;
    messages.push(
      { role: 'user', content: `turn-${index}` },
      {
        role: 'assistant',
        content: '',
        tool_calls: [
          {
            id: callId,
            type: 'function',
            function: { name: 'read_file', arguments: '{"path":"note.txt"}' },
          },
        ],
      },
      { role: 'tool', tool_call_id: callId, name: 'read_file', content: '{"ok":true}' },
      { role: 'assistant', content: `done-${index}` }
    );
  }

  const normalized = normalizeMessages(messages);
  assert.equal(normalized.length, MAX_MESSAGES);
  assert.equal(normalized[0].role, 'user');
  assert.equal(normalized[0].content, 'turn-10');

  let pending = new Set();
  for (const message of normalized) {
    if (message.role === 'user') {
      assert.equal(pending.size, 0, 'a retained user turn must not split pending tool calls');
    } else if (message.role === 'assistant' && Array.isArray(message.tool_calls)) {
      assert.equal(pending.size, 0);
      pending = new Set(message.tool_calls.map((call) => call.id));
    } else if (message.role === 'tool') {
      assert.equal(pending.delete(message.tool_call_id), true, 'tool result must retain its assistant call');
    }
  }
  assert.equal(pending.size, 0);

  const session = createSession({ workspaceRoot, id: 'trimmed-session' });
  session.messages = messages;
  saveSession(session, { home });
  const loaded = loadSession(workspaceRoot, session.id, { home });
  assert.equal(loaded.messages.length, MAX_MESSAGES);
  assert.match(loaded.summary, /Automatically compacted history:/);
  assert.match(loaded.summary, /turn-9/);

  const oversized = [{ role: 'user', content: 'oversized complete turn' }];
  for (let index = 0; index < 120; index += 1) {
    const callId = `oversized-${index}`;
    oversized.push(
      {
        role: 'assistant',
        content: '',
        tool_calls: [
          {
            id: callId,
            type: 'function',
            function: { name: 'read_file', arguments: '{}' },
          },
        ],
      },
      { role: 'tool', tool_call_id: callId, name: 'read_file', content: '{"ok":true}' }
    );
  }
  oversized.push({ role: 'assistant', content: 'oversized turn complete' });
  const oversizedSession = createSession({ workspaceRoot, id: 'oversized-session' });
  oversizedSession.messages = oversized;
  saveSession(oversizedSession, { home });
  assert.deepEqual(oversizedSession.messages, []);
  assert.match(oversizedSession.summary, /oversized complete turn/);
  assert.match(oversizedSession.summary, /oversized turn complete/);
});

test('terminal sanitizer removes ANSI, OSC, rewrite, and bidi controls', () => {
  const unsafe =
    'safe\x1b[31m red\x1b[0m\x1b]8;;https://evil.example\x07link\x1b]8;;\x07' +
    '\x1b]2;forged title\x07\rREWRITE\b!\u202Ehidden';
  const safe = sanitizeTerminalText(unsafe);

  assert.equal(safe, 'safe redlinkREWRITE!hidden');
  assert.doesNotMatch(safe, /[\x00-\x08\x0B-\x1F\x7F-\x9F\u202A-\u202E\u2066-\u2069]/);
});

test('noninteractive one-shot model failure renders safely and sets a failing exit status', async (t) => {
  const priorExitCode = process.exitCode;
  process.exitCode = undefined;
  t.after(() => {
    process.exitCode = priorExitCode;
  });
  const sink = transcriptSink();
  const runtime = {
    config: { provider: 'test', model: 'failure', permissionMode: 'ask' },
    async runTurn() {
      throw new Error('provider failed\x1b]2;forged\x07\x1b[31m badly\x1b[0m');
    },
  };

  await runAgentShell({
    input: Readable.from([]),
    output: sink.output,
    terminal: false,
    initialPrompt: 'one shot\x1b]2;prompt title\x07',
    runtime,
  });

  assert.equal(process.exitCode, 1);
  assert.match(sink.read(), /you › one shot/);
  assert.match(sink.read(), /model error provider failed badly/);
  assert.doesNotMatch(sink.read(), /\x1b|forged|prompt title/);
});

test('assistant responses are sanitized before noninteractive terminal rendering', async () => {
  const sink = transcriptSink();
  const runtime = {
    config: { provider: 'test', model: 'safe-output', permissionMode: 'plan' },
    async runTurn() {
      return { content: 'answer\x1b[2J\x1b]2;owned\x07 remains' };
    },
  };

  await runAgentShell({
    input: Readable.from([]),
    output: sink.output,
    terminal: false,
    initialPrompt: 'render it',
    runtime,
  });

  assert.match(sink.read(), /scbe › answer remains/);
  assert.doesNotMatch(sink.read(), /\x1b|owned/);
});
