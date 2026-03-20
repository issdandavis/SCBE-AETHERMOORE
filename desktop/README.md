# AetherBrowser Desktop

Electron-based standalone browser with an AI-governed multi-agent sidepanel.
This is the "Perplexity-killer" standalone app that wraps the existing
`src/extension/` sidepanel UI into a full desktop browser experience.

## Architecture

```
+------------------------------------------------------------+
|  Address Bar (url input, back/forward/reload)              |
+------------------------------------------+-----------------+
|                                          |                 |
|  Browser Pane (75%)                      | Sidepanel (25%) |
|  Standard Chromium webview               | Reuses          |
|  with DOM extraction bridge              | src/extension/  |
|                                          | sidepanel.html  |
|                                          |                 |
+------------------------------------------+-----------------+
```

The main process also spawns the Python backend
(`python -m uvicorn src.aetherbrowser.serve:app --port 8002`)
so the sidepanel WebSocket connection works out of the box.

## Prerequisites

- Node.js >= 18
- Python >= 3.11 (with `uvicorn` and project deps installed)
- The parent SCBE-AETHERMOORE repo (this app lives in its `desktop/` subdirectory)

## Quick Start

```bash
cd desktop
npm install
npm run dev
```

This runs `vite build --watch` for any renderer bundling and launches Electron.

If you only want to launch Electron (no Vite watcher):

```bash
npm run dev:electron
```

## Building the Installer

```bash
npm run package
```

Produces a Windows NSIS installer in `dist-electron/`.

## Key Files

| File | Purpose |
|------|---------|
| `electron/main.js` | Main process: window, views, IPC, backend spawner |
| `electron/preload-sidepanel.js` | Chrome API shim so extension sidepanel works in Electron |
| `electron/preload-browser.js` | DOM bridge for reading pages from the browser pane |
| `electron/preload-addressbar.js` | IPC bridge for the address bar renderer |
| `renderer/address-bar.html` | URL/search bar with navigation buttons |
| `renderer/address-bar.js` | URL detection, search dispatch, navigation state |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+T | New tab |
| Ctrl+W | Close tab |
| Ctrl+L | Focus address bar |
| Ctrl+R | Reload page |
| Alt+Left | Back |
| Alt+Right | Forward |
| F12 | Browser pane DevTools |
| Ctrl+Shift+I | Sidepanel DevTools |

## How the Chrome Shim Works

The sidepanel code (`src/extension/sidepanel.js`) calls Chrome Extension APIs like
`chrome.tabs.query()`, `chrome.tabs.sendMessage()`, `chrome.storage.local`, etc.

In Electron, `preload-sidepanel.js` exposes a `window.chrome` object that routes
these calls through Electron IPC to the main process, which then interacts with
the browser pane's `webContents` directly. The sidepanel code runs unmodified.
