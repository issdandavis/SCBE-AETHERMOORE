#!/usr/bin/env node
/**
 * AetherDesk Browser Agent
 *
 * A stable, real-Chrome control lane for AI browser work.
 *
 * This does NOT bypass Google/service login. It creates a persistent Chrome
 * profile that the user signs into once, then the AI attaches through CDP and
 * keeps using that same signed-in browser. That is the reliable boundary:
 * persistent session reuse, not credential scraping or login-page evasion.
 */

import { spawn, spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { homedir, platform } from 'node:os';
import { fileURLToPath } from 'node:url';
import net from 'node:net';

const require = createRequire(import.meta.url);
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const DEFAULT_PORT = 9333;
const DEFAULT_PROFILE = join(homedir(), '.aetherdesk', 'browser-profile');
const ARTIFACT_DIR = join(ROOT, 'artifacts', 'aetherdesk_browser');
const VOICEOVER_ARTIFACT_DIR = join(ROOT, 'artifacts', 'aetherbrowser_voiceover');
const VOICE_CODE_ARTIFACT_DIR = join(ROOT, 'artifacts', 'aetherbrowser_voice_code');
const COLAB_ARTIFACT_DIR = join(ROOT, 'artifacts', 'colab');
const COLAB_RUNNER = join(ROOT, 'scripts', 'colab', 'colab-playwright-runner.js');
const VOICEOVER_RUNNER = join(ROOT, 'scripts', 'system', 'aetherbrowser_voiceover.py');
const VOICE_CODE_RUNNER = join(ROOT, 'scripts', 'system', 'aetherbrowser_voice_code.py');

const TARGETS = {
  colab: 'https://colab.research.google.com/',
  colab_training:
    'https://colab.research.google.com/gist/issdandavis/c2f22a0b274793d5db9805d216696ad4/train_qlora.ipynb',
  huggingface: 'https://huggingface.co/',
  kaggle: 'https://www.kaggle.com/',
  github: 'https://github.com/issdandavis/SCBE-AETHERMOORE',
  drive: 'https://drive.google.com/',
  aetherdesk: 'http://127.0.0.1:5717/'
};

function usage() {
  return [
    'AetherDesk Browser Agent',
    '',
    'Commands:',
    '  doctor',
    '  start [--port 9333] [--profile dir] [--url URL | --target NAME]',
    '  status [--port 9333] [--json]',
    '  open --url URL | --target NAME [--port 9333]',
    '  screen [--match text] [--out-dir dir] [--port 9333]',
    '  open-app --app NAME [--match text] [--port 9333]',
    '  click --x N --y N [--match text] [--port 9333]',
    '  click-text --text TEXT [--match text] [--port 9333]',
    '  type --text TEXT [--match text] [--port 9333]',
    '  key --key Enter|Escape|Control+Enter|... [--match text] [--port 9333]',
    '  inspect [--match text] [--out-dir dir] [--port 9333]',
    '  monitor --match text --watch-for text [--timeout-ms n] [--port 9333]',
    '  dedupe --match text [--keep newest|oldest] [--port 9333]',
    '  voiceover --text TEXT [--voice NAME] [--rate -10..10] [--engine sapi] [--speak-now] [--out-dir dir]',
    '  voice-code --action inventory|holophonor|guitar|proof|expressive [--song NOTES] [--notes NOTES] [--dialect NAME] [--speak] [--out-dir dir]',
    '  colab-run --url URL --code-file file.py --watch-for text [--timeout-ms n]',
    '  targets',
    '',
    'Default persistent profile:',
    `  ${DEFAULT_PROFILE}`,
    '',
    'Important:',
    '  Sign into Google/Hugging Face/Kaggle inside this Chrome profile once.',
    '  After that, the AI controls the same profile through CDP.',
    '  This avoids duplicate tabs and avoids insecure embedded login flows.'
  ].join('\n');
}

function parseArgs(argv) {
  const args = {
    command: argv[0] || 'help',
    port: DEFAULT_PORT,
    profile: DEFAULT_PROFILE,
    timeoutMs: 20 * 60 * 1000,
    waitRuntimeMs: 10 * 60 * 1000,
    keep: 'oldest',
    outDir: ARTIFACT_DIR
  };
  for (let i = 1; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--json') args.json = true;
    else if (arg === '--headless') args.headless = true;
    else if (arg === '--port') args.port = Number(argv[++i]);
    else if (arg === '--profile') args.profile = resolve(argv[++i]);
    else if (arg === '--url') args.url = argv[++i];
    else if (arg === '--target') args.target = argv[++i];
    else if (arg === '--match') args.match = argv[++i];
    else if (arg === '--watch-for') args.watchFor = argv[++i];
    else if (arg === '--timeout-ms') args.timeoutMs = Number(argv[++i]);
    else if (arg === '--wait-runtime-ms') args.waitRuntimeMs = Number(argv[++i]);
    else if (arg === '--out-dir') args.outDir = resolve(argv[++i]);
    else if (arg === '--code-file') args.codeFile = resolve(argv[++i]);
    else if (arg === '--receipt') args.receipt = resolve(argv[++i]);
    else if (arg === '--screenshot') args.screenshot = resolve(argv[++i]);
    else if (arg === '--keep') args.keep = argv[++i];
    else if (arg === '--x') args.x = Number(argv[++i]);
    else if (arg === '--y') args.y = Number(argv[++i]);
    else if (arg === '--text') args.text = argv[++i];
    else if (arg === '--app') args.app = argv[++i];
    else if (arg === '--key') args.key = argv[++i];
    else if (arg === '--voice') args.voice = argv[++i];
    else if (arg === '--rate') args.rate = Number(argv[++i]);
    else if (arg === '--engine') args.engine = argv[++i];
    else if (arg === '--speak-now') args.speakNow = true;
    else if (arg === '--action') args.action = argv[++i];
    else if (arg === '--song') args.song = argv[++i];
    else if (arg === '--notes') args.notes = argv[++i];
    else if (arg === '--mode') args.mode = argv[++i];
    else if (arg === '--dialect') args.dialect = argv[++i];
    else if (arg === '--args') args.args = argv[++i];
    else if (arg === '--proof') args.proof = argv[++i];
    else if (arg === '--speak') args.speak = true;
    else if (arg === '--basename') args.basename = argv[++i];
    else throw new Error(`unknown argument: ${arg}`);
  }
  return args;
}

function loadPlaywright() {
  try {
    return require('@playwright/test');
  } catch {
    return require('playwright');
  }
}

function ensureDir(dir) {
  mkdirSync(dir, { recursive: true });
}

function timestamp() {
  return new Date().toISOString().replace(/[:.]/g, '-');
}

function targetUrl(args) {
  if (args.url) return args.url;
  if (args.target) {
    if (!TARGETS[args.target]) {
      throw new Error(`unknown target '${args.target}'. Run: node scripts/system/aether_browser_agent.mjs targets`);
    }
    return TARGETS[args.target];
  }
  return 'about:blank';
}

function detectChromePath() {
  const candidates = [];
  if (platform() === 'win32') {
    candidates.push(
      'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
      join(homedir(), 'AppData', 'Local', 'Google', 'Chrome', 'Application', 'chrome.exe')
    );
  } else if (platform() === 'darwin') {
    candidates.push('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome');
  } else {
    candidates.push('/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser');
  }
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }
  const lookup = platform() === 'win32'
    ? spawnSync('where.exe', ['chrome'], { encoding: 'utf8' })
    : spawnSync('sh', ['-lc', 'command -v google-chrome || command -v chromium || command -v chromium-browser'], { encoding: 'utf8' });
  const first = (lookup.stdout || '').trim().split(/\r?\n/).find(Boolean);
  return first || null;
}

function isPortListening(port) {
  return new Promise((resolvePort) => {
    const socket = net.createConnection({ host: '127.0.0.1', port });
    socket.once('connect', () => {
      socket.destroy();
      resolvePort(true);
    });
    socket.once('error', () => resolvePort(false));
    socket.setTimeout(750, () => {
      socket.destroy();
      resolvePort(false);
    });
  });
}

async function fetchJson(url) {
  const response = await fetch(url, { signal: AbortSignal.timeout(5000) });
  if (!response.ok) throw new Error(`${url} returned HTTP ${response.status}`);
  return response.json();
}

async function waitForCdp(port, retries = 80) {
  for (let i = 0; i < retries; i += 1) {
    try {
      await fetchJson(`http://127.0.0.1:${port}/json/version`);
      return true;
    } catch {
      await new Promise((resolveWait) => setTimeout(resolveWait, 500));
    }
  }
  throw new Error(`Chrome CDP did not become ready on port ${port}`);
}

async function startBrowser(args) {
  ensureDir(args.profile);
  ensureDir(ARTIFACT_DIR);

  if (await isPortListening(args.port)) {
    await waitForCdp(args.port, 4);
    return {
      ok: true,
      reused: true,
      port: args.port,
      cdpUrl: `http://127.0.0.1:${args.port}`,
      profile: args.profile
    };
  }

  const chromePath = detectChromePath();
  if (!chromePath) throw new Error('Chrome not found. Install Chrome or add it to PATH.');
  const url = targetUrl(args);
  const chromeArgs = [
    `--remote-debugging-port=${args.port}`,
    `--user-data-dir=${args.profile}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--new-window',
    url
  ];
  if (args.headless) chromeArgs.unshift('--headless=new');

  const child = spawn(chromePath, chromeArgs, {
    detached: true,
    stdio: 'ignore'
  });
  child.unref();
  await waitForCdp(args.port);

  const receipt = {
    ok: true,
    reused: false,
    pid: child.pid,
    chromePath,
    port: args.port,
    cdpUrl: `http://127.0.0.1:${args.port}`,
    profile: args.profile,
    url,
    startedAt: new Date().toISOString()
  };
  writeFileSync(join(ARTIFACT_DIR, 'last_start.json'), JSON.stringify(receipt, null, 2), 'utf8');
  return receipt;
}

async function status(args) {
  const version = await fetchJson(`http://127.0.0.1:${args.port}/json/version`);
  const tabs = await fetchJson(`http://127.0.0.1:${args.port}/json/list`);
  return {
    ok: true,
    port: args.port,
    cdpUrl: `http://127.0.0.1:${args.port}`,
    browser: version.Browser,
    webSocketDebuggerUrl: version.webSocketDebuggerUrl,
    tabs: tabs.map((tab) => ({ id: tab.id, type: tab.type, title: tab.title, url: tab.url }))
  };
}

async function connect(args) {
  const { chromium } = loadPlaywright();
  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${args.port}`);
  const context = browser.contexts()[0] || await browser.newContext();
  return { browser, context };
}

async function openTarget(args) {
  await startBrowser(args);
  const url = targetUrl(args);
  const { browser, context } = await connect(args);
  const page = await context.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
  const result = { ok: true, url: page.url(), title: await page.title(), port: args.port };
  await browser.close();
  return result;
}

async function pageByMatch(context, match) {
  const pages = context.pages();
  if (!match) return pages[pages.length - 1] || await context.newPage();
  return pages.find((page) => page.url().includes(match) || page.url().toLowerCase().includes(match.toLowerCase()))
    || pages.find((page) => page.url().includes(match))
    || pages[pages.length - 1]
    || await context.newPage();
}

async function inspect(args) {
  ensureDir(args.outDir);
  const { browser, context } = await connect(args);
  const page = await pageByMatch(context, args.match);
  await page.waitForTimeout(500);
  const shot = join(args.outDir, `inspect_${timestamp()}.png`);
  const textPath = join(args.outDir, `inspect_${timestamp()}.txt`);
  const jsonPath = join(args.outDir, 'last_inspect.json');
  const text = await page.locator('body').innerText({ timeout: 10000 }).catch(() => '');
  await page.screenshot({ path: shot, fullPage: false }).catch(() => {});
  const payload = {
    ok: true,
    url: page.url(),
    title: await page.title(),
    match: args.match || null,
    screenshot: shot,
    textPath,
    textTail: text.slice(-6000),
    inspectedAt: new Date().toISOString()
  };
  writeFileSync(textPath, text, 'utf8');
  writeFileSync(jsonPath, JSON.stringify(payload, null, 2), 'utf8');
  await browser.close();
  return payload;
}

async function screen(args) {
  ensureDir(args.outDir);
  const { browser, context } = await connect(args);
  const page = await pageByMatch(context, args.match);
  await page.waitForTimeout(250);
  const shot = join(args.outDir, `screen_${timestamp()}.png`);
  await page.screenshot({ path: shot, fullPage: false });
  const payload = {
    ok: true,
    url: page.url(),
    title: await page.title(),
    match: args.match || null,
    screenshot: shot,
    capturedAt: new Date().toISOString()
  };
  writeFileSync(join(args.outDir, 'last_screen.json'), JSON.stringify(payload, null, 2), 'utf8');
  await browser.close();
  return payload;
}

async function clickPage(args) {
  if (!Number.isFinite(args.x) || !Number.isFinite(args.y)) throw new Error('click requires --x N --y N');
  const { browser, context } = await connect(args);
  const page = await pageByMatch(context, args.match);
  await page.mouse.click(args.x, args.y);
  const payload = {
    ok: true,
    action: 'click',
    x: args.x,
    y: args.y,
    url: page.url(),
    title: await page.title(),
    at: new Date().toISOString()
  };
  ensureDir(args.outDir);
  writeFileSync(join(args.outDir, 'last_action.json'), JSON.stringify(payload, null, 2), 'utf8');
  await browser.close();
  return payload;
}

async function clickTextPage(args) {
  if (typeof args.text !== 'string' || !args.text.trim()) throw new Error('click-text requires --text TEXT');
  const { browser, context } = await connect(args);
  const page = await pageByMatch(context, args.match);
  const result = await page.evaluate((needle) => {
    const wanted = String(needle || '').trim().toLowerCase();
    const nodes = Array.from(document.querySelectorAll('button,a,[role="button"],[data-open],.desktop-icon,.nav-button'));
    function visible(el) {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
    }
    const hit = nodes.find((el) => visible(el) && (el.innerText || el.textContent || '').trim().toLowerCase().includes(wanted));
    if (!hit) return { clicked: false, error: 'visible text not found' };
    hit.click();
    const rect = hit.getBoundingClientRect();
    return {
      clicked: true,
      label: (hit.innerText || hit.textContent || '').trim(),
      rect: { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) }
    };
  }, args.text);
  const payload = {
    ok: Boolean(result.clicked),
    action: 'click-text',
    text: args.text,
    url: page.url(),
    title: await page.title(),
    hit: result,
    error: result.clicked ? null : result.error || 'text not found',
    at: new Date().toISOString()
  };
  ensureDir(args.outDir);
  writeFileSync(join(args.outDir, 'last_action.json'), JSON.stringify(payload, null, 2), 'utf8');
  await browser.close();
  return payload;
}

async function openAppPage(args) {
  if (typeof args.app !== 'string' || !args.app.trim()) throw new Error('open-app requires --app NAME');
  if (!/^[a-z0-9_-]+$/i.test(args.app)) throw new Error(`invalid app name: ${args.app}`);
  const { browser, context } = await connect(args);
  const page = await pageByMatch(context, args.match);
  const result = await page.evaluate((appName) => {
    const forceFront = () => {
      const target = document.querySelector(`#window-${appName}, .window[data-app="${appName}"]`);
      if (!target) return false;
      for (const win of document.querySelectorAll('.window')) {
        win.style.zIndex = win === target ? '2147483000' : '10';
      }
      target.classList.remove('hidden');
      target.removeAttribute('aria-hidden');
      if (target.parentElement) target.parentElement.appendChild(target);
      return true;
    };
    const byDataOpen = [...document.querySelectorAll('[data-open]')]
      .find((el) => el.dataset && el.dataset.open === appName);
    if (byDataOpen) {
      byDataOpen.click();
      forceFront();
      return { ok: true, app: appName, method: 'data-open' };
    }
    if (typeof window.openApp === 'function') {
      window.openApp(appName);
      forceFront();
      return { ok: true, app: appName, method: 'window.openApp' };
    }
    if (forceFront()) {
      return { ok: true, app: appName, method: 'window-direct' };
    }
    return { ok: false, app: appName, error: `app not found: ${appName}` };
  }, args.app.trim());
  await page.waitForTimeout(500);
  await browser.close();
  return result;
}

async function typePage(args) {
  if (typeof args.text !== 'string') throw new Error('type requires --text TEXT');
  const { browser, context } = await connect(args);
  const page = await pageByMatch(context, args.match);
  await page.keyboard.insertText(args.text);
  const payload = {
    ok: true,
    action: 'type',
    length: args.text.length,
    url: page.url(),
    title: await page.title(),
    at: new Date().toISOString()
  };
  ensureDir(args.outDir);
  writeFileSync(join(args.outDir, 'last_action.json'), JSON.stringify(payload, null, 2), 'utf8');
  await browser.close();
  return payload;
}

async function keyPage(args) {
  if (!args.key) throw new Error('key requires --key KEY');
  const { browser, context } = await connect(args);
  const page = await pageByMatch(context, args.match);
  await page.keyboard.press(args.key);
  const payload = {
    ok: true,
    action: 'key',
    key: args.key,
    url: page.url(),
    title: await page.title(),
    at: new Date().toISOString()
  };
  ensureDir(args.outDir);
  writeFileSync(join(args.outDir, 'last_action.json'), JSON.stringify(payload, null, 2), 'utf8');
  await browser.close();
  return payload;
}

async function monitor(args) {
  if (!args.watchFor) throw new Error('monitor requires --watch-for');
  const deadline = Date.now() + args.timeoutMs;
  const { browser, context } = await connect(args);
  const page = await pageByMatch(context, args.match);
  let text = '';
  let matched = false;
  while (Date.now() < deadline) {
    text = await collectVisibleText(page);
    if (text.includes(args.watchFor)) {
      matched = true;
      break;
    }
    await page.waitForTimeout(2500);
  }
  const notebookState = classifyNotebookText(text);
  const result = {
    ok: matched,
    status: matched ? 'WATCH_MATCH' : notebookState.status,
    watchFor: args.watchFor,
    match: args.match || null,
    url: page.url(),
    title: await page.title(),
    notebookState,
    progress: notebookState.progress || null,
    tail: text.slice(-10000),
    elapsedMs: args.timeoutMs - Math.max(0, deadline - Date.now())
  };
  ensureDir(args.outDir);
  writeFileSync(join(args.outDir, 'last_monitor.json'), JSON.stringify(result, null, 2), 'utf8');
  if (page.url().includes('colab.research.google.com')) {
    ensureDir(COLAB_ARTIFACT_DIR);
    writeFileSync(join(COLAB_ARTIFACT_DIR, `monitor_${timestamp()}.json`), JSON.stringify({
      ...result,
      command: 'monitor',
      source: 'aether_browser_agent'
    }, null, 2), 'utf8');
  }
  await browser.close();
  return result;
}

async function collectVisibleText(page) {
  const chunks = [];
  const body = await page.locator('.output_text, .output pre, pre, body').allInnerTexts()
    .then((items) => items.join('\n'))
    .catch(() => '');
  if (body) chunks.push(body);
  for (const frame of page.frames()) {
    if (frame === page.mainFrame()) continue;
    const frameText = await frame.locator('body').innerText({ timeout: 1500 }).catch(() => '');
    if (frameText) chunks.push(frameText);
  }
  return chunks.join('\n');
}

function classifyNotebookText(text) {
  const body = String(text || '');
  const progress = parseTrainerProgress(body);
  if (/SCBE_FAST_FULL_DONE/i.test(body)) {
    return { status: 'TRAINING_DONE', progress };
  }
  if (/SCBE_FAST_FULL_PUSHED|pushed adapter/i.test(body)) {
    return { status: 'TRAINING_PUSHED', progress };
  }
  if (/CUDA out of memory|OutOfMemoryError/i.test(body)) {
    return { status: 'OOM_FAILED', progress };
  }
  if (/KeyboardInterrupt|interrupted by user/i.test(body)) {
    return { status: 'INTERRUPTED', progress };
  }
  if (/Connecting|Resuming execution|Allocating|Initializing runtime|Reconnect/i.test(body)) {
    return { status: 'RUNTIME_CONNECTING', progress };
  }
  if (progress) {
    return { status: 'TRAINING_PROGRESS_SEEN', progress };
  }
  return { status: 'NO_PROGRESS_VISIBLE', progress: null };
}

function parseTrainerProgress(text) {
  const body = String(text || '').replace(/\r/g, '\n');
  const patterns = [
    /\[\s*(\d+)\s*\/\s*(\d+)\s+([0-9:]+)\s*<\s*([0-9:]+)\s*,\s*([0-9.]+)\s*it\/s/i,
    /(\d+)\s*\/\s*(\d+)\s+\[?[0-9:]+\s*<\s*([0-9:]+)\s*,\s*([0-9.]+)\s*it\/s/i
  ];
  for (const pattern of patterns) {
    const matches = [...body.matchAll(new RegExp(pattern.source, `${pattern.flags}g`))];
    const match = matches[matches.length - 1];
    if (!match) continue;
    const step = Number(match[1]);
    const total = Number(match[2]);
    const elapsed = match.length === 6 ? match[3] : null;
    const eta = match.length === 6 ? match[4] : match[3];
    const itPerSec = Number(match.length === 6 ? match[5] : match[4]);
    if (!Number.isFinite(step) || !Number.isFinite(total) || total <= 0) continue;
    return {
      step,
      total,
      percent: Number(((step / total) * 100).toFixed(2)),
      elapsed,
      eta,
      itPerSec: Number.isFinite(itPerSec) ? itPerSec : null
    };
  }
  return null;
}

async function dedupe(args) {
  if (!args.match) throw new Error('dedupe requires --match');
  const { browser, context } = await connect(args);
  const pages = context.pages().filter((page) => page.url().includes(args.match) || page.url().toLowerCase().includes(args.match.toLowerCase()));
  const ordered = args.keep === 'newest' ? [...pages].reverse() : pages;
  const keep = ordered[0];
  const closed = [];
  for (const page of pages) {
    if (page === keep) continue;
    closed.push({ title: await page.title().catch(() => ''), url: page.url() });
    await page.close().catch(() => {});
  }
  const result = {
    ok: true,
    match: args.match,
    kept: keep ? { title: await keep.title().catch(() => ''), url: keep.url() } : null,
    closedCount: closed.length,
    closed
  };
  await browser.close();
  return result;
}

function colabRun(args) {
  if (!args.url) throw new Error('colab-run requires --url');
  if (!args.codeFile) throw new Error('colab-run requires --code-file');
  if (!existsSync(COLAB_RUNNER)) throw new Error(`Colab runner not found: ${COLAB_RUNNER}`);
  const receipt = args.receipt || join(ROOT, 'artifacts', 'colab', `aether_browser_colab_${timestamp()}.json`);
  const screenshot = args.screenshot || join(ROOT, 'artifacts', 'colab', `aether_browser_colab_${timestamp()}.png`);
  const runnerArgs = [
    COLAB_RUNNER,
    'run-cell',
    '--cdp-url',
    `http://127.0.0.1:${args.port}`,
    '--url',
    args.url,
    '--code-file',
    args.codeFile,
    '--receipt',
    receipt,
    '--screenshot',
    screenshot,
    '--timeout-ms',
    String(args.timeoutMs),
    '--wait-runtime-ms',
    String(args.waitRuntimeMs)
  ];
  if (args.watchFor) runnerArgs.push('--watch-for', args.watchFor);
  const child = spawnSync(process.execPath, runnerArgs, {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: 'pipe'
  });
  if (child.stdout) process.stdout.write(child.stdout);
  if (child.stderr) process.stderr.write(child.stderr);
  return child.status || 0;
}

function parseJsonOutput(text) {
  const body = String(text || '').trim();
  if (!body) return null;
  try {
    return JSON.parse(body);
  } catch {
    for (let i = body.length - 1; i >= 0; i -= 1) {
      if (body[i] !== '{' && body[i] !== '[') continue;
      try {
        return JSON.parse(body.slice(i));
      } catch {
        // Keep scanning for the last JSON payload.
      }
    }
  }
  return { raw: body };
}

function localTtsEngine() {
  const child = spawnSync(process.env.PYTHON || 'python', [
    '-c',
    'from python.scbe.tts_backend import available; print(available() or "")'
  ], {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: 'pipe'
  });
  if (child.status !== 0) return null;
  return (child.stdout || '').trim() || null;
}

function voiceover(args) {
  if (typeof args.text !== 'string' || !args.text.trim()) {
    return { ok: false, error: 'voiceover requires --text TEXT' };
  }
  if (!existsSync(VOICEOVER_RUNNER)) {
    return { ok: false, error: `Voiceover runner not found: ${VOICEOVER_RUNNER}` };
  }
  const outDir = args.outDir === ARTIFACT_DIR ? VOICEOVER_ARTIFACT_DIR : args.outDir;
  const runnerArgs = [
    VOICEOVER_RUNNER,
    '--text',
    args.text,
    '--out-dir',
    outDir
  ];
  if (args.voice) runnerArgs.push('--voice', args.voice);
  if (Number.isFinite(args.rate)) runnerArgs.push('--rate', String(args.rate));
  if (args.engine) runnerArgs.push('--engine', args.engine);
  if (args.basename) runnerArgs.push('--basename', args.basename);
  if (args.speakNow) runnerArgs.push('--speak-now');

  const child = spawnSync(process.env.PYTHON || 'python', runnerArgs, {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: 'pipe'
  });
  const payload = parseJsonOutput(child.stdout) || {
    ok: false,
    error: child.stderr || 'voiceover runner produced no JSON'
  };
  return {
    ok: child.status === 0 && Boolean(payload.ok),
    command: 'voiceover',
    runner: VOICEOVER_RUNNER,
    runnerExitCode: child.status,
    result: payload,
    stderr: child.stderr ? child.stderr.slice(0, 4000) : null
  };
}

function voiceCode(args) {
  if (!existsSync(VOICE_CODE_RUNNER)) {
    return { ok: false, error: `Voice-code runner not found: ${VOICE_CODE_RUNNER}` };
  }
  const outDir = args.outDir === ARTIFACT_DIR ? VOICE_CODE_ARTIFACT_DIR : args.outDir;
  const runnerArgs = [
    VOICE_CODE_RUNNER,
    '--action',
    args.action || 'inventory',
    '--out-dir',
    outDir
  ];
  if (args.basename) runnerArgs.push('--basename', args.basename);
  if (args.song) runnerArgs.push('--song', args.song);
  if (args.notes) runnerArgs.push('--notes', args.notes);
  if (args.mode) runnerArgs.push('--mode', args.mode);
  if (args.dialect) runnerArgs.push('--dialect', args.dialect);
  if (args.args) runnerArgs.push('--args', args.args);
  if (args.proof) runnerArgs.push('--proof', args.proof);
  if (args.text) runnerArgs.push('--text', args.text);
  if (args.voice) runnerArgs.push('--voice', args.voice);
  if (Number.isFinite(args.rate)) runnerArgs.push('--rate', String(args.rate));
  if (args.speak) runnerArgs.push('--speak');
  if (args.speakNow) runnerArgs.push('--speak-now');

  const child = spawnSync(process.env.PYTHON || 'python', runnerArgs, {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: 'pipe'
  });
  const payload = parseJsonOutput(child.stdout) || {
    ok: false,
    error: child.stderr || 'voice-code runner produced no JSON'
  };
  return {
    ok: child.status === 0 && Boolean(payload.ok),
    command: 'voice-code',
    runner: VOICE_CODE_RUNNER,
    runnerExitCode: child.status,
    result: payload,
    stderr: child.stderr ? child.stderr.slice(0, 4000) : null
  };
}

async function main(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  if (args.command === 'help' || args.command === '--help' || args.command === '-h') {
    console.log(usage());
    return 0;
  }
  if (args.command === 'targets') {
    console.log(JSON.stringify(TARGETS, null, 2));
    return 0;
  }
  if (args.command === 'doctor') {
    const payload = {
      ok: true,
      repo: ROOT,
      chromePath: detectChromePath(),
      defaultPort: DEFAULT_PORT,
      defaultProfile: DEFAULT_PROFILE,
      artifactDir: ARTIFACT_DIR,
      voiceoverRunner: existsSync(VOICEOVER_RUNNER),
      voiceoverArtifactDir: VOICEOVER_ARTIFACT_DIR,
      voiceCodeRunner: existsSync(VOICE_CODE_RUNNER),
      voiceCodeArtifactDir: VOICE_CODE_ARTIFACT_DIR,
      localTtsEngine: localTtsEngine(),
      playwright: Boolean(loadPlaywright()),
      colabRunner: existsSync(COLAB_RUNNER)
    };
    console.log(JSON.stringify(payload, null, 2));
    return payload.ok ? 0 : 1;
  }
  if (args.command === 'start') {
    console.log(JSON.stringify(await startBrowser(args), null, 2));
    return 0;
  }
  if (args.command === 'status') {
    const payload = await status(args);
    console.log(args.json ? JSON.stringify(payload, null, 2) : JSON.stringify(payload, null, 2));
    return 0;
  }
  if (args.command === 'open') {
    console.log(JSON.stringify(await openTarget(args), null, 2));
    return 0;
  }
  if (args.command === 'screen') {
    console.log(JSON.stringify(await screen(args), null, 2));
    return 0;
  }
  if (args.command === 'click') {
    console.log(JSON.stringify(await clickPage(args), null, 2));
    return 0;
  }
  if (args.command === 'click-text') {
    const result = await clickTextPage(args);
    console.log(JSON.stringify(result, null, 2));
    return result.ok ? 0 : 1;
  }
  if (args.command === 'open-app') {
    const result = await openAppPage(args);
    console.log(JSON.stringify(result, null, 2));
    return result.ok ? 0 : 1;
  }
  if (args.command === 'type') {
    console.log(JSON.stringify(await typePage(args), null, 2));
    return 0;
  }
  if (args.command === 'key') {
    console.log(JSON.stringify(await keyPage(args), null, 2));
    return 0;
  }
  if (args.command === 'inspect') {
    console.log(JSON.stringify(await inspect(args), null, 2));
    return 0;
  }
  if (args.command === 'monitor') {
    const result = await monitor(args);
    console.log(JSON.stringify(result, null, 2));
    return result.ok ? 0 : 3;
  }
  if (args.command === 'dedupe') {
    console.log(JSON.stringify(await dedupe(args), null, 2));
    return 0;
  }
  if (args.command === 'voiceover') {
    const result = voiceover(args);
    console.log(JSON.stringify(result, null, 2));
    return result.ok ? 0 : 1;
  }
  if (args.command === 'voice-code') {
    const result = voiceCode(args);
    console.log(JSON.stringify(result, null, 2));
    return result.ok ? 0 : 1;
  }
  if (args.command === 'colab-run') {
    await startBrowser(args);
    return colabRun(args);
  }
  throw new Error(`unknown command: ${args.command}`);
}

main().then((code) => {
  process.exitCode = code;
}).catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exitCode = 1;
});
