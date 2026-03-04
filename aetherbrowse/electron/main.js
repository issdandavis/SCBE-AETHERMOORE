/**
 * AetherBrowse — Electron Main Process
 *
 * Creates the governed browser window with:
 * - Main browser pane (BrowserView)
 * - Agent sidebar
 * - Governance log panel
 * - WebSocket bridge to Python agent runtime
 */

const { app, BrowserWindow, BrowserView, ipcMain } = require('electron');
const WebSocket = require('ws');
const path = require('path');

let runtimeWs = null;
let mainWindow = null;
const runtimeHost =
  process.env.AETHERBROWSE_RUNTIME_HOST ||
  process.env.AETHERSCREEN_RUNTIME_HOST ||
  process.env.AETHERSCREEN_HOST ||
  '127.0.0.1';
const runtimePort = process.env.AETHERBROWSE_RUNTIME_PORT || process.env.AETHERSCREEN_RUNTIME_PORT || process.env.AETHERSCREEN_PORT || '8400';
const runtimeUrl = `ws://${runtimeHost}:${runtimePort}/ws`;
const homeUrl =
  process.env.AETHERBROWSE_HOME_URL ||
  process.env.AETHERSCREEN_HOME_URL ||
  'http://127.0.0.1:8500/home';
const sideBarWidth = 280;
const topBarHeight = 84;
const bottomPanelHeight = 210;

const tabs = new Map(); // tabId -> { id, view, url, title, loading }
let activeTabId = null;
let nextTabId = 1;

function formatTabState() {
  return Array.from(tabs.values()).map((tab) => ({
    id: tab.id,
    url: tab.url,
    title: tab.title,
    loading: tab.loading,
  }));
}

function getActiveTab() {
  return activeTabId ? tabs.get(activeTabId) : null;
}

function normalizeUrl(raw) {
  if (!raw) {
    return homeUrl;
  }
  const value = String(raw).trim();
  if (!value) {
    return homeUrl;
  }
  if (/^[a-zA-Z][a-zA-Z\d+\-.]*:/.test(value)) {
    return value;
  }
  if (value.includes('.') && !/\s/.test(value)) {
    return `https://${value}`;
  }
  return `https://duckduckgo.com/?q=${encodeURIComponent(value)}`;
}

function sendToRenderer(channel, payload) {
  if (!mainWindow) {
    return;
  }
  mainWindow.webContents.send(channel, payload);
}

function emitTabState() {
  sendToRenderer('tabs-updated', {
    tabs: formatTabState(),
    activeTabId,
  });
}

function emitActiveTab() {
  sendToRenderer('active-tab-changed', { activeTabId });
}

function applyLayout() {
  if (!mainWindow) {
    return;
  }
  const [width, height] = mainWindow.getContentSize();
  const active = getActiveTab();
  if (!active) {
    return;
  }
  active.view.setBounds({
    x: sideBarWidth,
    y: topBarHeight,
    width: width - sideBarWidth,
    height: height - topBarHeight - bottomPanelHeight,
  });
  active.view.setAutoResize({ width: true, height: true });
  mainWindow.setBrowserView(active.view);
}

function hideAllViews() {
  if (!mainWindow) {
    return;
  }
  tabs.forEach((tab) => {
    if (mainWindow.getBrowserView() === tab.view) {
      mainWindow.setBrowserView(null);
    }
  });
}

function getOrCreateActiveTabId() {
  if (activeTabId && tabs.has(activeTabId)) {
    return activeTabId;
  }
  const fallback = Array.from(tabs.keys())[0] || null;
  if (fallback) {
    activeTabId = fallback;
    return activeTabId;
  }
  const created = createTab(homeUrl);
  activeTabId = created;
  return created;
}

function createTab(rawUrl, activate = true, title = 'New tab') {
  const id = String(nextTabId++);
  const view = new BrowserView({
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const tab = {
    id,
    view,
    url: normalizeUrl(rawUrl || homeUrl),
    title,
    loading: false,
  };
  tabs.set(id, tab);

  const wc = view.webContents;
  const normalized = normalizeUrl(rawUrl || homeUrl);
  wc.loadURL(normalized);

  wc.on('did-start-loading', () => {
    tab.loading = true;
    if (activeTabId === id) {
      emitTabState();
    }
  });

  wc.on('did-stop-loading', () => {
    tab.loading = false;
    emitTabState();
  });

  wc.on('did-navigate', (event, url) => {
    tab.url = url;
    if (activeTabId === id) {
      sendToRenderer('navigation', { tabId: id, url });
    }
    emitTabState();
  });

  wc.on('page-title-updated', (event, title) => {
    tab.title = title || 'New tab';
    if (activeTabId === id) {
      sendToRenderer('page-title', { tabId: id, title: tab.title });
    }
    emitTabState();
  });

  wc.on('did-fail-load', (_event, _errorCode, errorDesc) => {
    if (activeTabId === id) {
      sendToRenderer('agent-message', {
        type: 'governance-event',
        from: 'system',
        message: `Navigation failed: ${errorDesc || 'Unknown error'}`,
        governance: { decision: 'DENY', coherence: 1.0 },
      });
    }
  });

  // Open window.open() targets in a new tab.
  wc.setWindowOpenHandler(({ url }) => {
    if (url) {
      const newTabId = createTab(url, true, 'New tab');
      switchTab(newTabId);
    }
    return { action: 'deny' };
  });

  emitTabState();

  if (activate) {
    switchTab(id);
  }

  return id;
}

function switchTab(tabId) {
  if (!tabs.has(tabId)) {
    return;
  }
  activeTabId = tabId;
  applyLayout();
  emitTabState();
  emitActiveTab();

  const active = tabs.get(tabId);
  if (active) {
    sendToRenderer('navigation', { tabId, url: active.url });
    sendToRenderer('page-title', { tabId, title: active.title });
  }
}

function closeTab(tabId) {
  const tab = tabs.get(tabId);
  if (!tab) {
    return;
  }

  if (mainWindow && mainWindow.getBrowserView() === tab.view) {
    hideAllViews();
  }

  tab.view.webContents.destroy();
  tabs.delete(tabId);

  if (!tabs.size) {
    const fresh = createTab(homeUrl, true, 'New tab');
    activeTabId = fresh;
    emitTabState();
    emitActiveTab();
    return;
  }

  if (activeTabId === tabId) {
    const fallbackId = Array.from(tabs.keys())[0];
    activeTabId = fallbackId;
    applyLayout();
  }
  emitTabState();
  emitActiveTab();
}

function updateActiveTabUrl(tabId, url) {
  const tab = tabs.get(tabId);
  if (!tab) {
    return;
  }
  tab.url = url;
  if (activeTabId === tabId) {
    sendToRenderer('navigation', { tabId, url });
  }
  emitTabState();
}

function getTargetTabId(input) {
  if (!input) {
    return getOrCreateActiveTabId();
  }
  if (typeof input === 'string' || typeof input.tabId === 'undefined') {
    return getOrCreateActiveTabId();
  }
  return tabs.has(input.tabId) ? input.tabId : getOrCreateActiveTabId();
}

// WebSocket connection to Python agent runtime
function connectRuntime() {
  const ws = new WebSocket(runtimeUrl);

  ws.on('open', () => {
    console.log('[AetherBrowse] Connected to agent runtime');
    runtimeWs = ws;
    sendToRenderer('runtime-status', { connected: true });
  });

  ws.on('message', (data) => {
    const msg = JSON.parse(data.toString());
    // Forward agent messages to renderer
    sendToRenderer('agent-message', msg);
    // Handle browser commands from agents
    if (msg.type === 'browser-command') {
      handleBrowserCommand(msg);
    }
  });

  ws.on('close', () => {
    console.log('[AetherBrowse] Runtime disconnected, reconnecting in 3s...');
    runtimeWs = null;
    sendToRenderer('runtime-status', { connected: false });
    setTimeout(connectRuntime, 3000);
  });

  ws.on('error', () => {
    // Silently retry
    setTimeout(connectRuntime, 3000);
  });
}

function handleBrowserCommand(msg) {
  const target = msg.tabId ? tabs.get(msg.tabId) : getActiveTab();
  if (!target) {
    return;
  }
  const wc = target.view.webContents;
  switch (msg.action) {
    case 'navigate':
      wc.loadURL(normalizeUrl(msg.url || homeUrl));
      break;
    case 'go-back':
      if (wc.canGoBack()) wc.goBack();
      break;
    case 'go-forward':
      if (wc.canGoForward()) wc.goForward();
      break;
    case 'reload':
      wc.reload();
      break;
    case 'stop':
      wc.stop();
      break;
    case 'go-home':
      wc.loadURL(homeUrl);
      break;
    case 'evaluate':
      wc.executeJavaScript(msg.script).then(result => {
        sendToRuntime({ type: 'eval-result', requestId: msg.requestId, result });
      }).catch(err => {
        sendToRuntime({ type: 'eval-error', requestId: msg.requestId, error: err.message });
      });
      break;
    case 'snapshot':
      // Get accessibility tree via CDP
      wc.debugger.attach('1.3');
      wc.debugger.sendCommand('Accessibility.getFullAXTree').then(tree => {
        wc.debugger.detach();
        sendToRuntime({ type: 'dom-snapshot', requestId: msg.requestId, tree });
      }).catch(() => {
        wc.debugger.detach();
      });
      break;
  }
}

function sendToRuntime(msg) {
  if (runtimeWs && runtimeWs.readyState === WebSocket.OPEN) {
    runtimeWs.send(JSON.stringify(msg));
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    title: 'Kerrigan — AI Home',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Load the React UI
  mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));

  mainWindow.on('resize', applyLayout);
  createTab(homeUrl, true, 'New tab');
  emitTabState();
}

// IPC handlers from renderer
ipcMain.on('navigate-to', (event, url) => {
  const openInNewTab = typeof url === 'object' && !!url.newTab;
  if (openInNewTab) {
    const newTabId = createTab(url && (url.url || url.value || ''));
    return;
  }

  const targetTabId = getTargetTabId(url);
  const tab = tabs.get(targetTabId);
  if (!tab) {
    return;
  }
  const next = typeof url === 'string'
    ? url
    : normalizeUrl(url && (url.url || url.value || ''));
  const finalUrl = normalizeUrl(next);
  tab.view.webContents.loadURL(finalUrl);
  updateActiveTabUrl(targetTabId, finalUrl);
});

ipcMain.on('agent-command', (event, command) => {
  // Forward user commands to agent runtime
  sendToRuntime({ type: 'user-command', text: command });
});

ipcMain.on('new-tab', (_event, url) => {
  const created = createTab(typeof url === 'string' ? url : homeUrl, true, 'New tab');
  emitTabState();
  emitActiveTab();
  const target = tabs.get(created);
  if (target) {
    sendToRenderer('navigation', { tabId: created, url: target.url });
  }
});

ipcMain.on('close-tab', (_event, tabId) => {
  const normalized = typeof tabId === 'string' ? tabId : (activeTabId && String(activeTabId));
  if (normalized) {
    closeTab(normalized);
  }
});

ipcMain.on('switch-tab', (_event, tabId) => {
  if (!tabId) {
    return;
  }
  switchTab(tabId);
});

ipcMain.on('go-back', (_event, tabId) => {
  const target = getTargetTabId({ tabId });
  const tab = tabs.get(target);
  if (tab && tab.view.webContents.canGoBack()) {
    tab.view.webContents.goBack();
  }
});

ipcMain.on('go-forward', (_event, tabId) => {
  const target = getTargetTabId({ tabId });
  const tab = tabs.get(target);
  if (tab && tab.view.webContents.canGoForward()) {
    tab.view.webContents.goForward();
  }
});

ipcMain.on('reload-tab', (_event, tabId) => {
  const target = getTargetTabId({ tabId });
  const tab = tabs.get(target);
  if (tab) {
    tab.view.webContents.reload();
  }
});

ipcMain.on('stop-tab', (_event, tabId) => {
  const target = getTargetTabId({ tabId });
  const tab = tabs.get(target);
  if (tab) {
    tab.view.webContents.stop();
  }
});

ipcMain.on('go-home', (_event, tabId) => {
  const target = getTargetTabId({ tabId });
  const tab = tabs.get(target);
  if (tab) {
    tab.view.webContents.loadURL(homeUrl);
  }
});

ipcMain.on('browser-command', (_event, command) => {
  if (!command || !command.type) {
    return;
  }
  switch (command.type) {
    case 'send-user-command':
      sendToRuntime({ type: 'user-command', text: String(command.payload || '') });
      break;
    default:
      if (runtimeWs && runtimeWs.readyState === WebSocket.OPEN) {
        runtimeWs.send(JSON.stringify({ type: 'browser-command', ...command }));
      }
      break;
  }
});

app.whenReady().then(() => {
  createWindow();
  connectRuntime();
});

app.on('window-all-closed', () => {
  app.quit();
});
