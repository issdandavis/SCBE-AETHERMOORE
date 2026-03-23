# AetherBrowser Extension Ownership Stack

Date: 2026-03-17

## Goal

Make the browser more "ours" by moving more sensing and acting into browser-native surfaces instead of spending model tokens and remote compute on work the browser can do deterministically.

The right split is:

- browser handles page access, DOM reads, screenshots, tab state, keyboard/mouse actions, cookies, and local lightweight processing
- local runtime handles routing, governance, memory, and long-horizon planning
- models handle ambiguity, synthesis, and multi-step reasoning

That gives the agent better eyes and hands without wasting model compute on tasks the browser can already do.

## What Already Exists In This Repo

### 1. MV3 extension shell

- `src/extension/manifest.json`
  - Current permissions: `activeTab`, `sidePanel`, `storage`, `nativeMessaging`
  - Current model: sidepanel + service worker + content script
- `src/extension/background.js`
  - Opens the side panel from the browser action
- `src/extension/content.js`
  - Already extracts visible text from the current page
- `src/extension/sidepanel.js`
  - Already connects the side panel to the local WebSocket backend and sends page context

### 2. Local backend for the extension

- `src/aetherbrowser/serve.py`
  - FastAPI + WebSocket backend for the extension
- `src/browser/evaluator.ts`
  - Sidepanel brief / recommendation logic already exists in the TS browser lane
- `src/browser/types.ts`
  - Sidepanel payload types already exist

### 3. Browser automation lanes

- `agents/aetherbrowse_cli.py`
  - Main CLI entry for governed browser actions
- `agents/browser/session_manager.py`
  - Session wrapper that routes into browser backends
- `agents/browsers/playwright_backend.py`
  - Main isolated automation backend
- `src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent/headless_driver.py`
  - Hidden but important: this already has storage-state cookie persistence logic
- `scripts/playwright_both_side.py`
  - Persistent Playwright profile pattern already exists
- `scripts/shopify_both_side_test.py`
  - Another good example of a persistent profile lane

### 4. Human-visible browser/device shell

- `kindle-app/www/browse.html`
  - Local browser shell with tabs, quick links, recent items, and URL state
- `kindle-app/www/device-shell.html`
  - Main panel + assistant panel shell
- `kindle-app/www/static/polly-pad-mobile.json`
  - Already describes persistent tab / URL state in the mobile lane

## Current Gap

Right now the browser is split into three partial systems:

- extension sidepanel for page context
- Playwright/CDP for automation
- Kindle/browser shell for owned UI

The missing piece is a shared browser-native capability layer:

- page map
- screenshot / visual capture
- action primitives
- cookie / session reuse
- browser-local compute
- local runtime bridge

That is the layer that makes the browser feel like a real owned instrument instead of "Chrome plus a helper."

## The Browser APIs That Matter

These are the practical APIs for "eyes and hands."

### 1. `sidePanel`

Use this for the always-visible agent surface.

Why it matters:

- keeps the assistant anchored to the current tab
- avoids a popup-only workflow
- gives a persistent operator surface

This repo already uses it in `src/extension/manifest.json` and `src/extension/background.js`.

### 2. Content scripts + `scripting`

Use this for deterministic, low-cost page reads and page actions.

What it gives:

- visible text extraction
- element maps
- button / form / link inventories
- page-local action helpers
- injected instrumentation without remote browser control

This is the cheapest form of "sight." The model should not be parsing raw HTML if a content script can emit a structured page brief first.

### 3. `tabs.captureVisibleTab`

Use this for screenshot-based fallback vision.

Best use:

- pages where the DOM is incomplete
- canvas-heavy surfaces
- PDFs / rendered documents
- sanity checks before risky actions

Important constraint:

- Chrome documents that `captureVisibleTab` is expensive and rate-limited
- use it as fallback or checkpoint capture, not your default loop

### 4. `debugger`

This is the strongest "deep eyes and deep hands" API.

What it gives through CDP domains:

- DOM / DOMSnapshot
- Accessibility tree
- Network events
- Input dispatch
- Runtime evaluation
- Page metadata
- Performance / tracing

This is how you stop guessing. Instead of asking the model to infer page structure from text alone, the extension can query the page through DevTools protocol domains and hand the runtime a richer state packet.

Tradeoff:

- strong permission warning
- should be behind a governed escalation path

### 5. `storage` + `cookies`

Use this for browser-owned state, not ad hoc local files only.

What belongs here:

- extension preferences
- last active tasks
- page summaries
- tab manifests
- lightweight session metadata

Cookies are specifically useful for:

- tracking signed-in state by platform
- routing the runtime toward a logged-in lane instead of cold-starting a session

Raw session secrets should still be handled carefully, but the browser should know whether a platform lane is warm or cold.

### 6. `commands` + `contextMenus`

Use these for operator-grade hands.

Examples:

- `Ctrl+Shift+Y` = summarize current page
- `Ctrl+Shift+O` = build page map
- right-click selected text = send to research lane
- right-click image = capture into evidence packet

This matters because it turns the browser into a tool, not just a viewport.

### 7. `nativeMessaging`

This is the clean bridge from extension to local runtime.

Use it for:

- sending structured page packets to local Python / FastAPI services
- requesting governed actions from SCBE
- receiving action plans or model output back into the browser

The repo already has `nativeMessaging` permission in `src/extension/manifest.json`, which is the correct direction.

### 8. `offscreen`

Use offscreen documents for browser-local processing that should not live in the visible sidepanel.

Good uses:

- screenshot processing
- audio handling
- OCR / preprocessing
- DOM serialization / parsing
- local background compute steps

### 9. Browser-local AI / GPU surfaces

For "without using your compute" or at least "using less model compute", the browser can do more locally than it used to.

Useful direction:

- WebGPU for client-side tensor / image work
- built-in AI APIs where available for short local text transforms
- web workers / offscreen documents for preprocessing before the runtime sees anything

This is not the place for full long-horizon reasoning. It is the place for:

- first-pass cleanup
- ranking
- filtering
- cheap labeling
- local compression of page context

## Recommended AetherBrowser Stack

### Phase 0. Session lane

First, stop browser amnesia.

- unify cookie / storage-state persistence across:
  - extension
  - Playwright backend
  - visible browser shell
- keep one session manifest per platform
- know whether GitHub / Amazon / KDP / Hugging Face / USPTO are warm or cold

This is the prerequisite for real browser work.

### Phase 1. Deterministic page map

Build a content-script page map packet with:

- URL
- title
- visible text excerpt
- headings
- forms
- buttons
- links
- interactive regions
- obvious candidate actions

This should become the default "eyes" packet before any model pass.

### Phase 2. Visual fallback

Add screenshot capture and basic visual packet generation:

- visible screenshot
- viewport metadata
- candidate element overlays
- optional DOM-to-vision crosswalk

Use it only when DOM confidence is low.

### Phase 3. Governed deep instrumentation

Add a debugger-backed lane for escalated tasks:

- DOMSnapshot
- Accessibility
- Network
- Input
- Runtime

This should be opt-in and auditable, not the default lane.

### Phase 4. Native browser action layer

Create browser-native action primitives:

- click candidate by id
- focus field
- type text
- choose dropdown option
- open sidepanel workflow
- capture selected text / link / image
- snapshot current tab

These should run in the extension first when possible, before falling back to Playwright.

### Phase 5. Browser-local preprocessing

Before invoking the model:

- collapse noisy DOM
- dedupe text
- rank visible actions
- classify page type
- compress state into a short structured packet

This is where local compute pays off.

## Concrete Extension Upgrades

If we make the extension more native, these are the first upgrades worth shipping:

1. Expand `src/extension/manifest.json` with:
- `scripting`
- `tabs`
- `cookies`
- `commands`
- `contextMenus`
- optionally `debugger`
- optionally `offscreen`

2. Replace the current single-purpose `content.js` with a richer page map emitter:
- visible text
- headings
- forms
- buttons
- links
- candidate action list
- page-type hints

3. Add screenshot capture support:
- visible-tab screenshot
- save into evidence packet
- send preview to sidepanel

4. Add command palette / keyboard shortcuts:
- summarize page
- extract forms
- mark action targets
- send selected text to research

5. Add native messaging bridge packets:
- browser -> local runtime
- local runtime -> browser action request

6. Add a warm-session manifest:
- platform
- last used
- signed-in hint
- cookie/storage-state path
- last successful tab URL

7. Add a governed debugger lane:
- disabled by default
- enabled only for specific tasks requiring deep access

## Best Product Direction

Do not try to make the browser "a big model window."

The better product is:

- extension gives eyes
- browser gives hands
- runtime gives memory and governance
- models give judgment

That split is stronger than pushing everything through Playwright or through chat.

## What To Build Next

If the goal is fastest leverage, build in this order:

1. cookie / storage-state system shared by Playwright + extension
2. page-map content script
3. screenshot fallback lane
4. native messaging packet bridge
5. debugger escalation lane

That would turn the current repo from "browser pieces" into a real owned browser stack.

## Sources

- Chrome Extensions API reference: https://developer.chrome.com/docs/extensions/reference/api
- Chrome Side Panel API: https://developer.chrome.com/docs/extensions/reference/api/sidePanel
- Chrome Content Scripts: https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts
- Chrome Scripting API: https://developer.chrome.com/docs/extensions/reference/api/scripting
- Chrome Tabs API (`captureVisibleTab`): https://developer.chrome.com/docs/extensions/reference/api/tabs
- Chrome Debugger API: https://developer.chrome.com/docs/extensions/reference/api/debugger
- Chrome Offscreen API: https://developer.chrome.com/docs/extensions/reference/api/offscreen
- Chrome Native Messaging: https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging
- Chrome built-in AI / Writing APIs: https://developer.chrome.com/docs/ai
- MDN WebExtensions API index: https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API
