/**
 * drive.js — control a running AetherBrowser with Playwright.
 *
 * AetherBrowser is Electron (Chromium), so Playwright can drive it over the
 * Chrome DevTools Protocol — exactly the way it drives normal Chrome.
 *
 * PREREQUISITE: start AetherBrowser with automation enabled, e.g.
 *     set AETHER_AUTOMATION=1
 *     AetherBrowser.exe
 * (or double-click "Start AetherBrowser (Automation).cmd").
 *
 * USAGE:
 *     node automation/drive.js                       # just connect + report the current page
 *     node automation/drive.js https://example.com   # navigate the browser pane there
 *     node automation/drive.js https://example.com shot.png   # ...and save a screenshot
 *
 * This is the same surface an AI agent uses to operate the browser for you.
 */
'use strict';

const { chromium } = require('playwright-core');

const ENDPOINT = process.env.AETHER_CDP || 'http://127.0.0.1:9222';
const targetUrl = process.argv[2] || null;
const shotPath = process.argv[3] || null;

// AetherBrowser has three web surfaces: the address bar and AI sidepanel (file://),
// and the actual website (http/https). We want the website pane.
function pickWebPage(pages) {
  return pages.find((p) => /^https?:/i.test(p.url())) || null;
}

async function waitForWebPage(context, timeoutMs = 8000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const page = pickWebPage(context.pages());
    if (page) return page;
    await new Promise((r) => setTimeout(r, 250));
  }
  return null;
}

(async () => {
  let browser;
  try {
    browser = await chromium.connectOverCDP(ENDPOINT);
  } catch (err) {
    console.error(JSON.stringify({
      connected: false,
      error: `Could not connect to AetherBrowser at ${ENDPOINT}.`,
      hint: 'Start it with AETHER_AUTOMATION=1 (use the "Start AetherBrowser (Automation).cmd" launcher).',
      detail: String(err.message || err),
    }, null, 2));
    process.exit(1);
  }

  const context = browser.contexts()[0];
  const page = await waitForWebPage(context);

  if (!page) {
    console.log(JSON.stringify({
      connected: true,
      note: 'Connected, but no website pane found yet.',
      targets: context.pages().map((p) => p.url()),
    }, null, 2));
    await browser.close().catch(() => {});
    return;
  }

  if (targetUrl) {
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 20000 }).catch(() => {});
  }

  const result = {
    connected: true,
    drove: Boolean(targetUrl),
    pageUrl: page.url(),
    title: await page.title().catch(() => ''),
    firstHeading: await page.evaluate(() => document.querySelector('h1,h2')?.innerText || '').catch(() => ''),
  };

  if (shotPath) {
    try {
      await page.screenshot({ path: shotPath, fullPage: false });
      result.screenshot = shotPath;
    } catch (e) {
      result.screenshotError = String(e.message || e);
    }
  }

  console.log(JSON.stringify(result, null, 2));

  // Detach without closing AetherBrowser (we only attached to it).
  await browser.close().catch(() => {});
})();
