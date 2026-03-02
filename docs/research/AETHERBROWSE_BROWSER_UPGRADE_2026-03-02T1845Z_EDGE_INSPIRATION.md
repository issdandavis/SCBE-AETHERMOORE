# AetherBrowse Browser Upgrade Notes — Edge-Inspired Usability Pass

Date: 2026-03-02
Owner: SCBE-AETHERMOORE
Scope: Desktop shell + agent runtime UX hooks

## What changed

### Electron shell
- Added a tab model in `aetherbrowse/electron/main.js`:
  - Multiple `BrowserView` instances per tab.
  - Tab state tracking: `tabs`, `activeTabId`, per-tab title/url/loading.
  - IPC handlers for:
    - `new-tab`, `close-tab`, `switch-tab`
    - `reload-tab`, `stop-tab`, `go-home`
    - enhanced `navigate-to` payload support (url + `tabId` + `newTab`).
  - Resizable layout keeps:
    - left sidebar width fixed,
    - top controls/tabs fixed,
    - bottom governance panel fixed.

### Renderer UI (`aetherbrowse/renderer/index.html`)
- Added top strip with:
  - navigation controls (`Back`, `Forward`, `Reload`, `Stop`, `Home`)
  - full-width URL/search bar.
  - runtime status dot.
- Added tab strip:
  - per-tab chip with title + short URL,
  - active tab highlighting,
  - close button.
- Added quick action buttons:
  - `Reader` -> sends `extract article`
  - `Video` -> sends `extract video`
- Added richer event wiring:
  - `onTabsUpdated` and `onActiveTabChanged` listeners
  - tab-aware URL updates and title updates.
- Keyboard shortcuts:
  - `Ctrl/Cmd+T` new tab
  - `Ctrl/Cmd+L` focus URL bar
  - `Enter` navigate, `Ctrl/Cmd/Shift+Enter` open in new tab.

### Runtime bridge (`aetherbrowse/runtime/server.py`)
- Added direct command handling for deterministic actions:
  - `extract article` -> `browser-command extract_article`
  - `extract video` -> `browser-command extract_video`
  - `reload` / `refresh` -> `browser-command reload`
- Keeps existing plan fallback for broader commands.

### IPC preload (`aetherbrowse/electron/preload.js`)
- Exposed new window-shell APIs:
  - tab lifecycle/navigation helpers.
  - browser-command passthrough.
  - new tab state event subscriptions.

## Why this matters

This pass moves AetherBrowse from a “single-pane webview plus sidebar” into a practical browser-like shell:
- users can keep multiple workflows live in separate tabs,
- maintain focus on governance/log panel while browsing,
- trigger article/video extraction directly from UX controls,
- and operate with familiar browser navigation behaviors.

## Next steps

1. Persist tab/session context across restarts.
2. Add in-place reader/video result panel view instead of log-only output.
3. Add Edge-like favorites/quick-launch and settings panel.
4. Wire command bar intents to structured workflow cards in the bottom panel.
