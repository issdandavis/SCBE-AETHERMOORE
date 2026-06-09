'use strict';

const assert = require('node:assert/strict');
const { spawn, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const net = require('node:net');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const CLI = path.resolve(__dirname, '..', 'bin', 'scbe.js');
const DESKTOP_SCRIPT = path.resolve(__dirname, '..', 'scripts', 'desktop_subsystem.cjs');

function runCli(args, options = {}) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-cli-actions-'));
  const env = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
    NO_COLOR: '1',
    ...(options.env || {}),
  };
  const result = spawnSync(process.execPath, [CLI, ...args], {
    input: options.input || '',
    encoding: 'utf8',
    timeout: options.timeout || 30_000,
    env,
  });
  fs.rmSync(home, { recursive: true, force: true });
  return result;
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
}

function getJson(url) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, (res) => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => {
        body += chunk;
      });
      res.on('end', () => {
        try {
          resolve(JSON.parse(body));
        } catch (err) {
          reject(err);
        }
      });
    });
    req.on('error', reject);
    req.setTimeout(5000, () => req.destroy(new Error('request timed out')));
  });
}

function getBuffer(url) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, (res) => {
      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => {
        resolve({
          statusCode: res.statusCode,
          headers: res.headers,
          body: Buffer.concat(chunks),
        });
      });
    });
    req.on('error', reject);
    req.setTimeout(5000, () => req.destroy(new Error('request timed out')));
  });
}

function postJson(url, payload) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(payload);
    const req = http.request(
      url,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(body),
        },
      },
      (res) => {
        let text = '';
        res.setEncoding('utf8');
        res.on('data', (chunk) => {
          text += chunk;
        });
        res.on('end', () => {
          try {
            resolve(JSON.parse(text));
          } catch (err) {
            reject(err);
          }
        });
      }
    );
    req.on('error', reject);
    req.setTimeout(30000, () => req.destroy(new Error('request timed out')));
    req.write(body);
    req.end();
  });
}

async function waitForJson(url) {
  for (let i = 0; i < 30; i += 1) {
    try {
      return await getJson(url);
    } catch (_err) {
      await new Promise((resolve) => setTimeout(resolve, 200));
    }
  }
  throw new Error(`Timed out waiting for ${url}`);
}

test('actions --json lists true runnable bundles', () => {
  const result = runCli(['actions', '--json']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_action_catalog_v1');
  assert.ok(payload.count >= 10);
  assert.ok(payload.actions.some((entry) => entry.id === 'terminal.panel'));
  assert.ok(payload.actions.some((entry) => entry.id === 'desktop.open'));
  assert.ok(payload.actions.every((entry) => entry.command));
});

test('action dry-run emits exact command without executing it', () => {
  const result = runCli(['action', 'desktop.open', '--dry-run', '--json']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_action_result_v1');
  assert.equal(payload.action_id, 'desktop.open');
  assert.equal(payload.dry_run, true);
  assert.equal(payload.success, true);
  assert.equal(payload.command, 'scbe desktop open');
});

test('action alias resolves to the same bundle', () => {
  const result = runCli(['action', 'polly-status', '--dry-run', '--json']);

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.action_id, 'desktop.status');
  assert.equal(payload.command, 'scbe desktop --json');
});

test('action can run a governed receipt smoke', () => {
  const result = runCli(['action', 'receipt.node-version', '--json'], { timeout: 45_000 });

  assert.equal(result.status, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_action_result_v1');
  assert.equal(payload.action_id, 'receipt.node-version');
  assert.equal(payload.success, true);
  assert.equal(payload.stdout_json.schema_version, 'scbe_terminal_run_v1');
  assert.match(payload.stdout_preview, /scbe_terminal_run_v1/);
  assert.match(payload.stdout_preview, /node --version/);
});

test('desktop action bridge exposes actions and runs one action over HTTP', async () => {
  const port = await freePort();
  const child = spawn(process.execPath, [DESKTOP_SCRIPT, 'bridge', '--port', String(port)], {
    cwd: path.resolve(__dirname, '..', '..', '..'),
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  try {
    const health = await waitForJson(`http://127.0.0.1:${port}/health`);
    assert.equal(health.schema_version, 'scbe_action_bridge_health_v1');
    assert.equal(health.ok, true);
    assert.equal(health.terminal.endpoint, '/terminal/run');
    assert.equal(health.internet.endpoint, '/internet/open');
    assert.equal(health.screen.endpoint, '/screen/capture');
    assert.equal(health.browser.endpoint, '/browser/open');
    assert.equal(health.browser.artifact_endpoint, '/artifact');

    const catalog = await getJson(`http://127.0.0.1:${port}/actions`);
    assert.equal(catalog.schema_version, 'scbe_action_catalog_v1');
    assert.ok(catalog.actions.some((entry) => entry.id === 'receipt.node-version'));

    const result = await postJson(`http://127.0.0.1:${port}/actions/run`, {
      id: 'receipt.node-version',
    });
    assert.equal(result.schema_version, 'scbe_action_result_v1');
    assert.equal(result.success, true);
    assert.equal(result.stdout_json.schema_version, 'scbe_terminal_run_v1');

    const session = await getJson(`http://127.0.0.1:${port}/terminal/session`);
    assert.equal(session.schema_version, 'scbe_terminal_session_v1');
    assert.match(session.shell, /powershell|pwsh/i);
    assert.match(session.cwd, /SCBE-AETHERMOORE/);
    assert.equal(session.endpoints.capture, '/screen/capture');
    assert.equal(session.endpoints.browser, '/browser/open');
    assert.equal(session.endpoints.artifact, '/artifact');

    const terminalRun = await postJson(`http://127.0.0.1:${port}/terminal/run`, {
      command: 'Write-Output "SCBE_TERMINAL_TEST"',
    });
    assert.equal(terminalRun.schema_version, 'scbe_terminal_command_result_v1');
    assert.equal(terminalRun.success, true);
    assert.match(terminalRun.stdout, /SCBE_TERMINAL_TEST/);
    assert.match(terminalRun.next_cwd, /SCBE-AETHERMOORE/);

    const browserRun = await postJson(`http://127.0.0.1:${port}/browser/open`, {
      url: 'https://example.com',
    });
    assert.equal(browserRun.schema_version, 'scbe_browser_page_v1');
    assert.equal(browserRun.success, true);
    assert.match(browserRun.title, /Example Domain/i);
    assert.match(browserRun.screenshot_url, /^\/artifact\?path=/);
    assert.ok(browserRun.bytes > 0);

    const screenshot = await getBuffer(`http://127.0.0.1:${port}${browserRun.screenshot_url}`);
    assert.equal(screenshot.statusCode, 200);
    assert.match(screenshot.headers['content-type'], /image\/png/);
    assert.ok(screenshot.body.length >= browserRun.bytes);
  } finally {
    child.kill('SIGTERM');
  }
});

test('unknown action returns a structured failure', () => {
  const result = runCli(['action', 'not.real', '--json']);

  assert.equal(result.status, 2);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.schema_version, 'scbe_action_result_v1');
  assert.equal(payload.success, false);
  assert.equal(payload.error, 'unknown action bundle');
  assert.ok(payload.known_actions.includes('desktop.open'));
});
