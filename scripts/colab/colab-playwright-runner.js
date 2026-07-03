#!/usr/bin/env node
/* eslint-disable no-console */
const fs = require('fs');
const os = require('os');
const path = require('path');

const DEFAULT_PROFILE = path.join(os.tmpdir(), 'scbe-colab-playwright-profile');
const DEFAULT_RECEIPT = path.join('artifacts', 'colab', 'playwright-run-receipt.json');
const DEFAULT_SCREENSHOT = path.join('artifacts', 'colab', 'playwright-run.png');

const OOM_PATTERNS = [
  /CUDA out of memory/i,
  /OutOfMemoryError/i,
  /Tried to allocate .* GiB/i
];

function usage() {
  return [
    'SCBE Colab Playwright Runner',
    '',
    'Commands:',
    '  doctor [--json]',
    '  ace-step-snippet [--out file]',
    '  ace-step-guard --url COLAB_URL --cdp-url http://127.0.0.1:9222',
    '  open --url COLAB_URL [--profile dir] [--cdp-url http://127.0.0.1:9222] [--headless]',
    '  run-cell --url COLAB_URL --code-file file.py [--watch-for text] [--timeout-ms n]',
    '           [--wait-login-ms n]',
    '           [--profile dir] [--cdp-url http://127.0.0.1:9222] [--receipt file]',
    '           [--screenshot file] [--headless]',
    '',
    'Real Chrome mode:',
    '  Start Chrome yourself with --remote-debugging-port=9222, then pass --cdp-url http://127.0.0.1:9222',
    '',
    'Examples:',
    '  node scripts/colab/colab-playwright-runner.js doctor',
    '  node scripts/colab/colab-playwright-runner.js ace-step-snippet --out artifacts/colab/ace_step_t4_guard_cell.py',
    '  node scripts/colab/colab-playwright-runner.js open --url https://colab.research.google.com/drive/...',
    '  node scripts/colab/colab-playwright-runner.js run-cell --url https://colab.research.google.com/drive/... --code-file scripts/colab/ace_step_t4_guard.py --watch-for SCBE_ACE_T4_GUARD'
  ].join('\n');
}

function parseArgs(argv) {
  const args = {
    command: argv[0] || 'help',
    headless: false,
    profile: DEFAULT_PROFILE,
    timeoutMs: 20 * 60 * 1000,
    waitRuntimeMs: 10 * 60 * 1000,
    receipt: DEFAULT_RECEIPT,
    screenshot: DEFAULT_SCREENSHOT
  };
  for (let i = 1; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--json') args.json = true;
    else if (arg === '--headless') args.headless = true;
    else if (arg === '--headed') args.headless = false;
    else if (arg === '--url') args.url = argv[++i];
    else if (arg === '--profile') args.profile = path.resolve(argv[++i]);
    else if (arg === '--cdp-url') args.cdpUrl = argv[++i];
    else if (arg === '--code-file') args.codeFile = path.resolve(argv[++i]);
    else if (arg === '--watch-for') args.watchFor = argv[++i];
    else if (arg === '--timeout-ms') args.timeoutMs = Number(argv[++i]);
    else if (arg === '--wait-runtime-ms') args.waitRuntimeMs = Number(argv[++i]);
    else if (arg === '--wait-login-ms') args.waitLoginMs = Number(argv[++i]);
    else if (arg === '--receipt') args.receipt = path.resolve(argv[++i]);
    else if (arg === '--screenshot') args.screenshot = path.resolve(argv[++i]);
    else if (arg === '--out') args.out = path.resolve(argv[++i]);
    else throw new Error(`unknown argument: ${arg}`);
  }
  return args;
}

function requirePlaywright() {
  try {
    return require('@playwright/test');
  } catch {
    return require('playwright');
  }
}

function mkdirFor(file) {
  fs.mkdirSync(path.dirname(path.resolve(file)), { recursive: true });
}

function aceStepSnippet() {
  const guardPath = 'scripts/colab/ace_step_t4_guard.py';
  return [
    'import os, gc, torch',
    'os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"',
    'gc.collect()',
    'if torch.cuda.is_available():',
    '    torch.cuda.empty_cache()',
    '    free, total = torch.cuda.mem_get_info()',
    '    print("SCBE_ACE_T4_GUARD", {"device": torch.cuda.get_device_name(0), "free_gb": round(free/1024**3, 2), "total_gb": round(total/1024**3, 2)})',
    'else:',
    '    print("SCBE_ACE_T4_GUARD", {"cuda": False})',
    '',
    '# Use these when constructing ACEStepPipeline on Colab T4:',
    '# cpu_offload=True, torch_compile=False, overlapped_decode=False',
    '# Local helper with same defaults lives at: ' + guardPath
  ].join('\n');
}

async function openBrowser(args) {
  const { chromium } = requirePlaywright();
  if (args.cdpUrl) {
    const browser = await chromium.connectOverCDP(args.cdpUrl);
    const context = browser.contexts()[0] || (await browser.newContext());
    return { browser, context, close: () => browser.close() };
  }
  const context = await chromium.launchPersistentContext(path.resolve(args.profile), {
    headless: Boolean(args.headless),
    channel: 'chromium',
    viewport: { width: 1440, height: 1000 },
    acceptDownloads: true
  });
  return { browser: null, context, close: () => context.close() };
}

async function pageForUrl(context, url) {
  const pages = context.pages();
  const existing = pages.find((page) => page.url().startsWith(url));
  const page = existing || pages[0] || (await context.newPage());
  if (!page.url().startsWith(url)) await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
  return page;
}

async function clickFirst(page, candidates, timeout = 5000) {
  for (const candidate of candidates) {
    const locator = candidate(page);
    try {
      if ((await locator.count()) > 0) {
        await locator.first().click({ timeout });
        return true;
      }
    } catch {
      // try next candidate
    }
  }
  return false;
}

async function pasteCodeCell(page, code) {
  await page.waitForLoadState('domcontentloaded', { timeout: 120000 });

  const added = await clickFirst(page, [
    (p) => p.getByText('+ Code', { exact: true }),
    (p) => p.getByText('Code', { exact: true }),
    (p) => p.locator('[aria-label*="Code"]').filter({ hasText: /Code/i })
  ]);
  if (!added) {
    throw new Error('could not find Colab + Code button; make sure the notebook is open and editable');
  }

  await page.waitForTimeout(1200);
  const editorSelector = [
    '.monaco-editor textarea:visible',
    '.cm-content[contenteditable="true"]:visible',
    '.cm-line:visible',
    '[role="textbox"][contenteditable="true"]:visible',
    '[role="textbox"]:visible',
    'textarea:visible'
  ].join(', ');
  let editors = page.locator(editorSelector);
  if ((await editors.count()) === 0) {
    await page.keyboard.press(process.platform === 'darwin' ? 'Meta+M' : 'Control+M').catch(() => {});
    await page.keyboard.press('B').catch(() => {});
    await page.waitForTimeout(1200);
    editors = page.locator(editorSelector);
  }
  if ((await editors.count()) === 0) {
    const textboxInfo = await page.evaluate(() => [...document.querySelectorAll('textarea,[contenteditable="true"],[role="textbox"],.cm-content,.monaco-editor')]
      .slice(-20)
      .map((el) => ({
        tag: el.tagName,
        role: el.getAttribute('role'),
        cls: el.className && String(el.className).slice(0, 120),
        editable: el.getAttribute('contenteditable'),
        text: (el.innerText || el.value || '').slice(0, 120)
      })));
    throw new Error(`could not find a Colab code editor after adding a cell; candidates=${JSON.stringify(textboxInfo)}`);
  }
  await editors.last().scrollIntoViewIfNeeded().catch(() => {});
  await editors.last().click({ timeout: 10000, force: true });
  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A');
  await page.keyboard.press('Backspace');
  await page.keyboard.insertText(code);
  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+Enter' : 'Control+Enter');
  await page.waitForTimeout(1000);
  await clickFirst(page, [
    (p) => p.getByText('Run anyway', { exact: true }),
    (p) => p.getByRole('button', { name: /Run anyway/i })
  ], 5000);
}

async function pageText(page) {
  return page.locator('body').innerText({ timeout: 10000 }).catch(() => '');
}

function classifyPageText(text) {
  if (/This browser or app may not be secure/i.test(text)) return 'INSECURE_BROWSER_BLOCK';
  if (/Sign in\\s+with your Google Account|Email or phone|Couldn.t sign you in/i.test(text)) return 'LOGIN_REQUIRED';
  if (/\\bConnecting\\b|Resuming execution|Allocating|Initializing runtime|Reconnect/i.test(text)) return 'RUNTIME_CONNECTING';
  return 'UNKNOWN';
}

async function waitForEditableNotebook(page, args, startedAt) {
  const waitLoginMs = Number(args.waitLoginMs || 0);
  const waitRuntimeMs = Number(args.waitRuntimeMs || 0);
  const deadline = Date.now() + waitLoginMs;
  const runtimeDeadline = Date.now() + waitRuntimeMs;
  let lastClassification = 'UNKNOWN';
  while (true) {
    const codeButtonChecks = await Promise.all([
      page.getByText('+ Code', { exact: true }).count().then((count) => count > 0),
      page.getByText('Code', { exact: true }).count().then((count) => count > 0),
      page.locator('[aria-label*="Code"]').count().then((count) => count > 0)
    ]).catch(() => false);
    const hasCodeButton = Array.isArray(codeButtonChecks) ? codeButtonChecks.some(Boolean) : Boolean(codeButtonChecks);
    const text = await pageText(page);
    lastClassification = classifyPageText(text);
    if (hasCodeButton && lastClassification !== 'RUNTIME_CONNECTING') return { ok: true };
    if (lastClassification === 'RUNTIME_CONNECTING' && Date.now() >= runtimeDeadline) {
      return {
        ok: false,
        status: 'RUNTIME_NOT_CONNECTED',
        elapsedMs: Date.now() - startedAt,
        tail: text.slice(-4000),
        advice: [
          'Colab is still Connecting/Resuming execution.',
          'Wait for the runtime to connect, then rerun the queued item.',
          'Do not paste long training cells while the runtime is not ready.'
        ]
      };
    }
    if (lastClassification === 'INSECURE_BROWSER_BLOCK') {
      return {
        ok: false,
        status: 'INSECURE_BROWSER_BLOCK',
        elapsedMs: Date.now() - startedAt,
        tail: text.slice(-4000),
        advice: [
          'Do not use Playwright Chromium for Google login.',
          'Use real Chrome with --remote-debugging-port=9222 and --cdp-url http://127.0.0.1:9222.'
        ]
      };
    }
    if (lastClassification === 'LOGIN_REQUIRED' && Date.now() >= deadline) {
      return {
        ok: false,
        status: 'LOGIN_REQUIRED',
        elapsedMs: Date.now() - startedAt,
        tail: text.slice(-4000),
        advice: [
          'Sign in in the real Chrome window that is open on Colab.',
          'Then rerun with --cdp-url http://127.0.0.1:9222, or run once with --wait-login-ms 600000 before signing in.'
        ]
      };
    }
    if (Date.now() >= deadline && waitLoginMs > 0) {
      return {
        ok: false,
        status: lastClassification === 'UNKNOWN' ? 'NOTEBOOK_NOT_EDITABLE' : lastClassification,
        elapsedMs: Date.now() - startedAt,
        tail: text.slice(-4000)
      };
    }
    if (waitLoginMs <= 0) {
      if (lastClassification === 'RUNTIME_CONNECTING') {
        await page.waitForTimeout(3000);
        continue;
      }
      return {
        ok: false,
        status: lastClassification === 'UNKNOWN' ? 'NOTEBOOK_NOT_EDITABLE' : lastClassification,
        elapsedMs: Date.now() - startedAt,
        tail: text.slice(-4000)
      };
    }
    await page.waitForTimeout(3000);
  }
}

async function monitorRun(page, args, startedAt) {
  const deadline = Date.now() + args.timeoutMs;
  let lastText = '';
  while (Date.now() < deadline) {
    await page.waitForTimeout(3000);
    const outputText = await page.locator('.output_text, .output pre, pre').allInnerTexts().then((items) => items.join('\n')).catch(() => '');
    if (args.watchFor && outputText.includes(args.watchFor)) {
      return { status: 'WATCH_MATCH', watchFor: args.watchFor, elapsedMs: Date.now() - startedAt, output: outputText.slice(-12000) };
    }
    const text = await page.locator('body').innerText({ timeout: 10000 }).catch(() => '');
    lastText = text.slice(-12000);
    if (OOM_PATTERNS.some((pattern) => pattern.test(text))) {
      return {
        status: 'OOM_DETECTED',
        elapsedMs: Date.now() - startedAt,
        advice: [
          'Restart Colab runtime after CUDA OOM.',
          'Set PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True before importing torch-heavy code.',
          'Use cpu_offload=True, torch_compile=False, overlapped_decode=False for ACEStep on T4.',
          'Run scripts/colab/ace_step_t4_guard.py or ace-step-snippet before model load.'
        ],
        tail: lastText
      };
    }
  }
  return { status: 'TIMEOUT', elapsedMs: Date.now() - startedAt, tail: lastText };
}

async function runCell(args) {
  if (!args.url) throw new Error('run-cell requires --url');
  if (!args.codeFile) throw new Error('run-cell requires --code-file');
  const code = fs.readFileSync(args.codeFile, 'utf8');
  const opened = await openBrowser(args);
  let receipt;
  const startedAt = Date.now();
  try {
    const page = await pageForUrl(opened.context, args.url);
    const editable = await waitForEditableNotebook(page, args, startedAt);
    if (!editable.ok) {
      mkdirFor(args.screenshot);
      await page.screenshot({ path: args.screenshot, fullPage: false }).catch(() => {});
      receipt = {
        ok: false,
        command: 'run-cell',
        url: page.url(),
        codeFile: args.codeFile,
        status: editable.status,
        result: editable,
        screenshot: path.resolve(args.screenshot),
        timestamp: new Date().toISOString()
      };
      mkdirFor(args.receipt);
      fs.writeFileSync(args.receipt, JSON.stringify(receipt, null, 2));
      console.log(JSON.stringify(receipt, null, 2));
      return resultExitCode(receipt.status);
    }
    await pasteCodeCell(page, code);
    const result = await monitorRun(page, args, startedAt);
    mkdirFor(args.screenshot);
    await page.screenshot({ path: args.screenshot, fullPage: false }).catch(() => {});
    receipt = {
      ok: result.status === 'WATCH_MATCH',
      command: 'run-cell',
      url: page.url(),
      codeFile: args.codeFile,
      status: result.status,
      result,
      screenshot: path.resolve(args.screenshot),
      timestamp: new Date().toISOString()
    };
  } finally {
    if (args.headless || args.cdpUrl) await opened.close().catch(() => {});
  }
  mkdirFor(args.receipt);
  fs.writeFileSync(args.receipt, JSON.stringify(receipt, null, 2));
  console.log(JSON.stringify(receipt, null, 2));
  return receipt.ok ? 0 : resultExitCode(receipt.status);
}

function resultExitCode(status) {
  if (status === 'OOM_DETECTED') return 2;
  if (status === 'TIMEOUT') return 3;
  if (status === 'LOGIN_REQUIRED' || status === 'INSECURE_BROWSER_BLOCK') return 4;
  return 1;
}

async function main(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  if (args.command === 'help' || args.command === '--help' || args.command === '-h') {
    console.log(usage());
    return 0;
  }
  if (args.command === 'doctor') {
    const payload = {
      ok: true,
      node: process.version,
      cwd: process.cwd(),
      playwright: Boolean(requirePlaywright()),
      defaultProfile: DEFAULT_PROFILE,
      note: 'Use --cdp-url for your real Chrome, or persistent Playwright Chromium profile for Colab login reuse.'
    };
    console.log(args.json ? JSON.stringify(payload, null, 2) : usage() + '\n\n' + JSON.stringify(payload, null, 2));
    return 0;
  }
  if (args.command === 'ace-step-snippet') {
    const snippet = aceStepSnippet();
    if (args.out) {
      mkdirFor(args.out);
      fs.writeFileSync(args.out, snippet);
      console.log(JSON.stringify({ ok: true, out: args.out }, null, 2));
    } else {
      console.log(snippet);
    }
    return 0;
  }
  if (args.command === 'ace-step-guard') {
    if (!args.url) throw new Error('ace-step-guard requires --url');
    const marker = `SCBE_ACE_T4_DONE_${Date.now()}`;
    const compact = [
      'import os,gc,torch',
      'os.environ["PYTORCH_CUDA_ALLOC_CONF"]="expandable_segments:True"',
      'gc.collect()',
      'torch.cuda.empty_cache() if torch.cuda.is_available() else None',
      'print("SCBE_ACE_T4_GUARD", {"cuda": torch.cuda.is_available(), "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, "mem": tuple(round(x/1024**3,2) for x in torch.cuda.mem_get_info()) if torch.cuda.is_available() else None})',
      'print("SCBE_ACE_T4_KWARGS", {"dtype":"bfloat16","torch_compile":False,"cpu_offload":True,"overlapped_decode":False})',
      `print("${marker}")`
    ].join('; ');
    const tmpFile = path.join(os.tmpdir(), `scbe-ace-step-guard-${Date.now()}.py`);
    fs.writeFileSync(tmpFile, compact);
    args.codeFile = tmpFile;
    args.watchFor = marker;
    args.receipt = args.receipt || path.join('artifacts', 'colab', 'ace-step-guard-receipt.json');
    args.screenshot = args.screenshot || path.join('artifacts', 'colab', 'ace-step-guard.png');
    return runCell(args);
  }
  if (args.command === 'open') {
    if (!args.url) throw new Error('open requires --url');
    const opened = await openBrowser(args);
    const page = await pageForUrl(opened.context, args.url);
    console.log(JSON.stringify({ ok: true, url: page.url(), headless: args.headless, profile: args.profile }, null, 2));
    if (args.headless || args.cdpUrl) await opened.close().catch(() => {});
    return 0;
  }
  if (args.command === 'run-cell') return runCell(args);
  throw new Error(`unknown command: ${args.command}`);
}

if (require.main === module) {
  main().then((code) => {
    process.exitCode = code;
  }).catch((error) => {
    console.error(error && error.stack ? error.stack : String(error));
    process.exitCode = 1;
  });
}

module.exports = {
  OOM_PATTERNS,
  aceStepSnippet,
  parseArgs,
  usage
};
