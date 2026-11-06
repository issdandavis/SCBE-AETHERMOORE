'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { Readable, Writable } = require('node:stream');
const test = require('node:test');

const { AgentRuntime, permissionDecision } = require('../lib/agent-runtime');
const { executeSlash, runAgentShell, SLASH_HELP } = require('../lib/agent-shell');
const { startAgentWebServer } = require('../lib/agent-web-server');
const { commandDirectories } = require('../lib/custom-commands');
const {
  resolveAgentConfig,
  saveAgentConfig,
  shellConfigPath,
} = require('../lib/provider-registry');
const { DEFAULT_TOOL_NAMES } = require('../lib/tool-registry');

function makeTemp(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function removeTemp(target) {
  const resolved = path.resolve(target);
  const tempRoot = `${path.resolve(os.tmpdir())}${path.sep}`;
  assert.ok(resolved.startsWith(tempRoot), `refusing to remove non-temp path: ${resolved}`);
  fs.rmSync(resolved, { recursive: true, force: true });
}

function offlineConfig(permissionMode = 'ask') {
  return {
    provider: 'offline',
    providerLabel: 'Offline',
    kind: 'offline',
    model: 'offline',
    baseUrl: '',
    apiKey: '',
    apiKeyEnv: null,
    configured: true,
    timeoutMs: 5_000,
    maxToolRounds: 4,
    permissionMode,
    temperature: 0,
  };
}

test('provider override cannot reuse a stale endpoint or key setting from another provider', (t) => {
  const home = makeTemp('scbe-agent-provider-home-');
  t.after(() => removeTemp(home));
  saveAgentConfig(
    {
      provider: 'custom',
      model: 'local-model',
      url: 'http://stale-custom.invalid/v1',
      api_key_env: 'STALE_CUSTOM_KEY',
    },
    { home, env: {} }
  );

  const config = resolveAgentConfig({
    home,
    env: {
      SCBE_PROVIDER: 'openai',
      OPENAI_API_KEY: 'openai-secret',
      OPENAI_MODEL: 'gpt-provider-test',
    },
  });

  assert.equal(config.provider, 'openai');
  assert.equal(config.model, 'gpt-provider-test');
  assert.equal(config.baseUrl, 'https://api.openai.com/v1');
  assert.equal(config.apiKey, 'openai-secret');
  assert.equal(config.apiKeyEnv, 'OPENAI_API_KEY');
});

test('model switching honors injected env and preserves provider-scoped custom settings', (t) => {
  const workspaceRoot = makeTemp('scbe-agent-provider-work-');
  const home = makeTemp('scbe-agent-provider-switch-home-');
  t.after(() => {
    removeTemp(workspaceRoot);
    removeTemp(home);
  });
  const env = {
    OPENAI_API_KEY: 'injected-openai-key',
    OPENAI_BASE_URL: 'https://injected-openai.example/v1/',
    CUSTOM_RUNTIME_KEY: 'custom-secret',
  };
  saveAgentConfig(
    {
      provider: 'offline',
      model: 'offline',
      providers: {
        custom: {
          model: 'saved-custom-model',
          base_url: 'http://127.0.0.1:9123/v1/',
          api_key_env: 'CUSTOM_RUNTIME_KEY',
        },
      },
    },
    { home, env }
  );
  const configPath = shellConfigPath({ home, env });
  const staleConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  staleConfig.api_key = 'stale-top-level-key';
  staleConfig.apiKey = 'stale-top-level-camel-key';
  staleConfig.providers.custom.api_key = 'stale-nested-key';
  staleConfig.providers.custom.apiKey = 'stale-nested-camel-key';
  fs.writeFileSync(configPath, `${JSON.stringify(staleConfig, null, 2)}\n`, 'utf8');
  const runtime = new AgentRuntime({
    workspaceRoot,
    home,
    env,
    config: offlineConfig(),
  });

  const custom = runtime.setModel('custom/next-custom-model');
  assert.equal(custom.provider, 'custom');
  assert.equal(custom.model, 'next-custom-model');
  assert.equal(custom.baseUrl, 'http://127.0.0.1:9123/v1');
  assert.equal(custom.apiKey, 'custom-secret');
  assert.equal(custom.apiKeyEnv, 'CUSTOM_RUNTIME_KEY');

  const openai = runtime.setModel('openai/gpt-switch-test');
  assert.equal(openai.provider, 'openai');
  assert.equal(openai.model, 'gpt-switch-test');
  assert.equal(openai.baseUrl, 'https://injected-openai.example/v1');
  assert.equal(openai.apiKey, 'injected-openai-key');
  assert.equal(openai.apiKeyEnv, 'OPENAI_API_KEY');

  const saved = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  assert.equal(saved.providers.custom.base_url, 'http://127.0.0.1:9123/v1');
  assert.equal(saved.providers.openai.base_url, 'https://injected-openai.example/v1');
  assert.equal(saved.api_key, undefined);
  assert.equal(saved.apiKey, undefined);
  assert.equal(saved.providers.custom.api_key, undefined);
  assert.equal(saved.providers.custom.apiKey, undefined);
  assert.equal(saved.providers.openai.api_key, undefined);
  assert.equal(saved.providers.openai.apiKey, undefined);
});

function jsonRequest(url, body, headers = {}) {
  return fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...headers },
    body: JSON.stringify(body),
  });
}

test('agent runtime exposes fourteen curated tools and completes an iterative read-tool turn', async (t) => {
  const workspaceRoot = makeTemp('scbe-agent-runtime-work-');
  const home = makeTemp('scbe-agent-runtime-home-');
  t.after(() => {
    removeTemp(workspaceRoot);
    removeTemp(home);
  });
  fs.writeFileSync(path.join(workspaceRoot, 'note.txt'), 'verified from the tool\n', 'utf8');

  const requests = [];
  const runtime = new AgentRuntime({
    workspaceRoot,
    home,
    config: offlineConfig('plan'),
    transport: async ({ messages, tools }) => {
      requests.push({ messages, tools });
      if (requests.length === 1) {
        return {
          content: 'I will inspect the file.',
          toolCalls: [
            {
              id: 'read-note',
              name: 'read_file',
              arguments: JSON.stringify({ path: 'note.txt' }),
            },
          ],
          usage: null,
        };
      }
      const toolMessage = messages.find(
        (message) => message.role === 'tool' && message.tool_call_id === 'read-note'
      );
      assert.ok(toolMessage, 'the second model call must contain the tool result');
      assert.match(toolMessage.content, /verified from the tool/);
      return { content: 'The file is verified.', toolCalls: [], usage: null };
    },
  });

  const result = await runtime.runTurn('Read note.txt and report what it says.');

  assert.equal(DEFAULT_TOOL_NAMES.length, 14);
  assert.deepEqual(runtime.registry.names(), [...DEFAULT_TOOL_NAMES]);
  assert.equal(requests.length, 2);
  assert.equal(requests[0].tools.length, 14);
  assert.equal(result.content, 'The file is verified.');
  assert.equal(result.toolRounds, 1);
  assert.deepEqual(
    runtime.session.messages.map((message) => message.role),
    ['user', 'assistant', 'tool', 'assistant']
  );

  const receiptDir = path.join(home, '.scbe', 'receipts');
  const receiptFiles = fs.readdirSync(receiptDir);
  assert.equal(receiptFiles.length, 1);
  assert.match(fs.readFileSync(path.join(receiptDir, receiptFiles[0]), 'utf8'), /"tool":"read_file"/);
});

test('plan mode reads but blocks writes without touching the workspace', async (t) => {
  const workspaceRoot = makeTemp('scbe-agent-plan-work-');
  const home = makeTemp('scbe-agent-plan-home-');
  t.after(() => {
    removeTemp(workspaceRoot);
    removeTemp(home);
  });

  let modelCalls = 0;
  const runtime = new AgentRuntime({
    workspaceRoot,
    home,
    config: offlineConfig('plan'),
    transport: async ({ messages }) => {
      modelCalls += 1;
      if (modelCalls === 1) {
        return {
          content: '',
          toolCalls: [
            {
              id: 'write-blocked',
              name: 'write_file',
              arguments: JSON.stringify({ path: 'blocked.txt', content: 'must not exist' }),
            },
          ],
        };
      }
      const toolMessage = messages.find((message) => message.role === 'tool');
      assert.ok(toolMessage);
      assert.deepEqual(JSON.parse(toolMessage.content), {
        ok: false,
        denied: true,
        reason: 'plan mode blocks edits and commands',
      });
      return { content: 'The write was blocked by plan mode.', toolCalls: [] };
    },
  });

  const result = await runtime.runTurn('Write blocked.txt.');

  assert.equal(result.content, 'The write was blocked by plan mode.');
  assert.equal(fs.existsSync(path.join(workspaceRoot, 'blocked.txt')), false);
  assert.deepEqual(permissionDecision('plan', 'read'), {
    allowed: true,
    ask: false,
    reason: 'read tools are allowed',
  });
  assert.equal(permissionDecision('plan', 'write').allowed, false);
});

test('slash command maker stores user and project commands with project precedence', async (t) => {
  const workspaceRoot = makeTemp('scbe-agent-command-work-');
  const home = makeTemp('scbe-agent-command-home-');
  t.after(() => {
    removeTemp(workspaceRoot);
    removeTemp(home);
  });
  const runtime = new AgentRuntime({ workspaceRoot, home, config: offlineConfig() });
  const options = { home };

  const userSaved = await executeSlash(
    runtime,
    '/command new review User review of $ARGUMENTS --user',
    options
  );
  const projectSaved = await executeSlash(
    runtime,
    '/command new review Project review of $ARGUMENTS --project',
    options
  );
  const directRun = await executeSlash(runtime, '/review src', options);
  const explicitRun = await executeSlash(runtime, '/command run review tests', options);

  assert.match(userSaved.output, /Saved \/review in user commands/);
  assert.match(projectSaved.output, /Saved \/review in project commands/);
  assert.equal(directRun.prompt, 'Project review of src');
  assert.equal(explicitRun.prompt, 'Project review of tests');

  const dirs = commandDirectories(workspaceRoot, { home });
  assert.equal(fs.existsSync(path.join(dirs.user, 'review.md')), true);
  assert.equal(fs.existsSync(path.join(dirs.project, 'review.md')), true);

  const removed = await executeSlash(runtime, '/command delete review --project', options);
  const fallback = await executeSlash(runtime, '/review src', options);
  assert.match(removed.output, /Deleted \/review from project commands/);
  assert.equal(fallback.prompt, 'User review of src');
});

test('guided evidence slash commands put agents on preset routes without injecting raw results', async (t) => {
  const workspaceRoot = makeTemp('scbe-agent-ride-work-');
  const home = makeTemp('scbe-agent-ride-home-');
  t.after(() => {
    removeTemp(workspaceRoot);
    removeTemp(home);
  });
  const runtime = new AgentRuntime({ workspaceRoot, home, config: offlineConfig() });

  const ride = await executeSlash(
    runtime,
    '/ride scholarly "tamper evident context packets"',
    { home }
  );
  assert.match(ride.prompt, /guided_evidence exactly once/);
  assert.match(ride.prompt, /route "scholarly"/);
  assert.match(ride.prompt, /cite its E-number hyperlinks/);

  const prior = await executeSlash(runtime, '/evidence context packets', { home });
  assert.deepEqual(JSON.parse(prior.output).matches, []);
  const receipts = await executeSlash(runtime, '/receipts', { home });
  assert.equal(JSON.parse(receipts.output).ok, true);
});

test('non-interactive shell processes multiple slash commands and an offline prompt without hanging', async (t) => {
  const workspaceRoot = makeTemp('scbe-agent-shell-work-');
  const home = makeTemp('scbe-agent-shell-home-');
  t.after(() => {
    removeTemp(workspaceRoot);
    removeTemp(home);
  });
  const input = Readable.from([
    '/help\n/status\n/tools\n/permissions plan\n' +
      '/command new brief Summarize $ARGUMENTS --project\n' +
      '/brief current changes\n/exit\n',
  ]);
  let transcript = '';
  const output = new Writable({
    write(chunk, _encoding, callback) {
      transcript += chunk.toString('utf8');
      callback();
    },
  });

  await runAgentShell({
    input,
    output,
    terminal: false,
    workspaceRoot,
    home,
    env: { ...process.env, SCBE_PROVIDER: 'offline' },
  });

  const slashCommands = new Set(SLASH_HELP.map(([command]) => command.split(' ')[0]));
  for (const required of [
    '/help',
    '/model',
    '/tools',
    '/permissions',
    '/status',
    '/resume',
    '/clear',
    '/compact',
    '/ride',
    '/evidence',
    '/verify-evidence',
    '/receipts',
    '/commands',
    '/command',
    '/exit',
  ]) {
    assert.equal(slashCommands.has(required), true, `missing required slash command: ${required}`);
  }
  assert.match(transcript, /SCBE agent · offline\/offline · ask · \/help/);
  assert.match(transcript, /SCBE conversation commands/);
  assert.match(transcript, /tools\s+14 curated/);
  assert.match(transcript, /Curated tools \(14\)/);
  assert.match(transcript, /Permissions set to plan/);
  assert.match(transcript, /Saved \/brief in project commands/);
  assert.match(transcript, /\[offline\] I saved your message: Summarize current changes/);
  assert.match(transcript, /goodbye\./);
});

test('loopback web interface serves the app and shares offline runtime and command APIs', async (t) => {
  const workspaceRoot = makeTemp('scbe-agent-web-work-');
  const home = makeTemp('scbe-agent-web-home-');
  let announceConcurrentA;
  let releaseConcurrentA;
  let singleApprovedResult = null;
  let singleReplayResult = null;
  const concurrentAStarted = new Promise((resolve) => {
    announceConcurrentA = resolve;
  });
  const concurrentACanFinish = new Promise((resolve) => {
    releaseConcurrentA = resolve;
  });
  const transport = async ({ messages }) => {
    const toolMessages = messages.filter((message) => message.role === 'tool');
    const lastUser = [...messages].reverse().find((message) => message.role === 'user');
    const concurrent = /^concurrent request ([AB])$/.exec(String(lastUser?.content || ''));
    if (concurrent) {
      const lane = concurrent[1];
      const callId = `concurrent-command-${lane}`;
      const ownToolMessage = toolMessages.find((message) => message.tool_call_id === callId);
      if (!ownToolMessage) {
        if (lane === 'A') {
          announceConcurrentA();
          await concurrentACanFinish;
        }
        return {
          content: '',
          toolCalls: [
            {
              id: callId,
              name: 'run_command',
              arguments: JSON.stringify({ command: 'node --version' }),
            },
          ],
        };
      }
      const toolResult = JSON.parse(ownToolMessage.content);
      if (lane === 'A') {
        assert.equal(toolResult.ok, true);
        assert.match(toolResult.stdout, /^v\d+\./);
      } else {
        assert.deepEqual(toolResult, {
          ok: false,
          denied: true,
          reason: 'denied by user',
        });
      }
      return { content: `Concurrent request ${lane} completed.`, toolCalls: [] };
    }
    if (lastUser?.content === 'run one approved command') {
      if (!toolMessages.length) {
        return {
          content: '',
          toolCalls: [
            {
              id: 'approved-command',
              name: 'run_command',
              arguments: JSON.stringify({ command: 'node --version' }),
            },
            {
              id: 'replayed-command',
              name: 'run_command',
              arguments: JSON.stringify({ command: 'node --version' }),
            },
          ],
        };
      }
      const approved = JSON.parse(
        toolMessages.find((message) => message.tool_call_id === 'approved-command').content
      );
      const replayed = JSON.parse(
        toolMessages.find((message) => message.tool_call_id === 'replayed-command').content
      );
      singleApprovedResult = approved;
      singleReplayResult = replayed;
      return { content: 'The command approval was consumed once.', toolCalls: [] };
    }
    return {
      content: `[offline] I saved your message: ${String(lastUser?.content || '').slice(0, 120)}`,
      toolCalls: [],
    };
  };
  const handle = await startAgentWebServer({
    host: '127.0.0.1',
    port: 0,
    workspaceRoot,
    home,
    env: { ...process.env, SCBE_PROVIDER: 'offline' },
    transport,
  });
  t.after(async () => {
    await handle.close();
    removeTemp(workspaceRoot);
    removeTemp(home);
  });

  const healthResponse = await fetch(`${handle.url}/api/health`);
  const health = await healthResponse.json();
  assert.equal(healthResponse.status, 200);
  assert.deepEqual(health, { ok: true, service: 'scbe-agent-web', loopback: true });

  const pageResponse = await fetch(`${handle.url}/`);
  const page = await pageResponse.text();
  assert.equal(pageResponse.status, 200);
  assert.match(pageResponse.headers.get('content-security-policy'), /default-src 'self'/);
  assert.match(page, /SCBE/);
  assert.match(page, new RegExp(handle.apiToken));

  const missingTokenResponse = await jsonRequest(`${handle.url}/api/chat`, {
    message: 'this request has no token',
  });
  assert.equal(missingTokenResponse.status, 401);
  assert.deepEqual(await missingTokenResponse.json(), {
    ok: false,
    error: 'invalid SCBE web token',
  });

  const crossOriginResponse = await jsonRequest(
    `${handle.url}/api/chat`,
    { message: 'this request is cross-origin' },
    {
      'x-scbe-web-token': handle.apiToken,
      origin: 'https://not-the-scbe-origin.example',
    }
  );
  assert.equal(crossOriginResponse.status, 403);
  assert.deepEqual(await crossOriginResponse.json(), {
    ok: false,
    error: 'cross-origin API access is not allowed',
  });

  const authHeaders = {
    'x-scbe-web-token': handle.apiToken,
    origin: handle.url,
  };

  const statusResponse = await fetch(`${handle.url}/api/status`, { headers: authHeaders });
  const status = await statusResponse.json();
  assert.equal(status.ok, true);
  assert.equal(status.status.provider, 'offline');
  assert.equal(status.tools.length, 14);

  const chatResponse = await jsonRequest(
    `${handle.url}/api/chat`,
    { message: 'hello from web' },
    authHeaders
  );
  const chat = await chatResponse.json();
  assert.equal(chatResponse.status, 200);
  assert.equal(chat.ok, true);
  assert.match(chat.message, /^\[offline\] I saved your message: hello from web/);
  assert.equal(chat.status.tools.length, 14);

  const approvedCommandResponse = await jsonRequest(
    `${handle.url}/api/chat`,
    {
      message: 'run one approved command',
      approved_tools: ['run_command'],
    },
    authHeaders
  );
  const approvedCommand = await approvedCommandResponse.json();
  assert.equal(approvedCommandResponse.status, 200, JSON.stringify(approvedCommand));
  assert.equal(approvedCommand.message, 'The command approval was consumed once.');
  assert.equal(singleApprovedResult.ok, true, JSON.stringify(singleApprovedResult));
  assert.match(singleApprovedResult.stdout, /^v\d+\./);
  assert.deepEqual(singleReplayResult, {
    ok: false,
    denied: true,
    reason: 'denied by user',
  });
  assert.equal(
    approvedCommand.events.filter(
      (event) => event.type === 'tool_result' && event.tool === 'run_command' && event.ok
    ).length,
    1
  );
  assert.equal(
    approvedCommand.events.filter(
      (event) => event.type === 'tool_result' && event.tool === 'run_command' && event.denied
    ).length,
    1
  );

  const concurrentSessionId = status.status.session_id;
  const requestA = jsonRequest(
    `${handle.url}/api/chat`,
    {
      session_id: concurrentSessionId,
      message: 'concurrent request A',
      approved_tools: ['run_command'],
    },
    authHeaders
  );
  await concurrentAStarted;
  const requestB = jsonRequest(
    `${handle.url}/api/chat`,
    {
      session_id: concurrentSessionId,
      message: 'concurrent request B',
      approved_tools: [],
    },
    authHeaders
  );
  await new Promise((resolve) => setTimeout(resolve, 50));
  releaseConcurrentA();
  const [responseA, responseB] = await Promise.all([requestA, requestB]);
  const [concurrentA, concurrentB] = await Promise.all([responseA.json(), responseB.json()]);

  assert.equal(responseA.status, 200);
  assert.equal(responseB.status, 200);
  assert.equal(concurrentA.message, 'Concurrent request A completed.');
  assert.equal(concurrentB.message, 'Concurrent request B completed.');
  assert.deepEqual(
    concurrentA.events.filter((event) => event.type === 'turn_start').map((event) => event.prompt),
    ['concurrent request A']
  );
  assert.deepEqual(
    concurrentB.events.filter((event) => event.type === 'turn_start').map((event) => event.prompt),
    ['concurrent request B']
  );
  assert.equal(
    concurrentA.events.some(
      (event) => event.type === 'tool_result' && event.tool === 'run_command' && event.ok
    ),
    true
  );
  assert.equal(
    concurrentA.events.some((event) => event.type === 'permission' && event.decision === 'deny'),
    false
  );
  assert.equal(
    concurrentB.events.some((event) => event.type === 'tool_start' && event.tool === 'run_command'),
    false
  );
  assert.equal(
    concurrentB.events.some(
      (event) => event.type === 'tool_result' && event.tool === 'run_command' && event.denied
    ),
    true
  );

  const savedResponse = await jsonRequest(
    `${handle.url}/api/commands`,
    {
      action: 'new',
      name: 'web-review',
      scope: 'project',
      template: 'Review $ARGUMENTS in the web lane.',
    },
    authHeaders
  );
  const saved = await savedResponse.json();
  assert.equal(saved.ok, true);
  assert.ok(saved.commands.some((command) => command.name === 'web-review'));

  const runResponse = await jsonRequest(
    `${handle.url}/api/commands`,
    {
      action: 'run',
      name: 'web-review',
      args: 'the release',
    },
    authHeaders
  );
  const run = await runResponse.json();
  assert.equal(run.result.prompt, 'Review the release in the web lane.');
});
