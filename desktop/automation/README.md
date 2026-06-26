# Driving AetherBrowser with Playwright (or an AI agent)

AetherBrowser is built on Electron, which is Chromium underneath — the same engine
Playwright was made to control. So Playwright can drive AetherBrowser exactly the way
it drives Chrome: navigate, click, type, screenshot, read the page.

## 1. Start AetherBrowser in automation mode

Double-click **`Start AetherBrowser (Automation).cmd`**.

(That just sets `AETHER_AUTOMATION=1` before launching, which opens the DevTools
control port on `127.0.0.1:9222` — this PC only. Without that variable the port stays
closed, so normal everyday use is never exposed.)

## 2. Drive it

```
node automation/drive.js                       # connect + report the current page
node automation/drive.js https://example.com   # navigate the browser pane there
node automation/drive.js https://example.com shot.png   # ...and save a screenshot
```

## 3. Or write your own

```js
const { chromium } = require('playwright-core');
const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
const page = browser.contexts()[0].pages().find(p => /^https?:/.test(p.url()));
await page.goto('https://news.ycombinator.com');
console.log(await page.title());
await page.click('a.storylink');     // anything Playwright can do, it can do here
```

The page you get back is AetherBrowser's actual browser pane — so an AI agent operating
this connection is operating the real browser the user sees.

## Notes
- The port is localhost-only and off by default (opt-in via the launcher).
- `playwright-core` is the lean driver — it controls AetherBrowser's existing Chromium,
  so there is no separate browser download.
