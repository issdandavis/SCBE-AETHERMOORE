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

let mainWindow = null;
let browserView = null;
let runtimeWs = null;

// WebSocket connection to Python agent runtime
function connectRuntime() {
  const ws = new WebSocket('ws://127.0.0.1:8400/ws');

  ws.on('open', () => {
    console.log('[AetherBrowse] Connected to agent runtime');
    runtimeWs = ws;
    if (mainWindow) {
      mainWindow.webContents.send('runtime-status', { connected: true });
    }
  });

  ws.on('message', (data) => {
    const msg = JSON.parse(data.toString());
    // Forward agent messages to renderer
    if (mainWindow) {
      mainWindow.webContents.send('agent-message', msg);
    }
    // Handle browser commands from agents
    if (msg.type === 'browser-command' && browserView) {
      handleBrowserCommand(msg);
    }
  });

  ws.on('close', () => {
    console.log('[AetherBrowse] Runtime disconnected, reconnecting in 3s...');
    runtimeWs = null;
    setTimeout(connectRuntime, 3000);
  });

  ws.on('error', () => {
    // Silently retry
    setTimeout(connectRuntime, 3000);
  });
}

function handleBrowserCommand(msg) {
  const wc = browserView.webContents;
  switch (msg.action) {
    case 'navigate':
      wc.loadURL(msg.url);
      break;
    case 'go-back':
      if (wc.canGoBack()) wc.goBack();
      break;
    case 'go-forward':
      if (wc.canGoForward()) wc.goForward();
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
    title: 'AetherBrowse — SCBE Governed Browser',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Load the React UI
  mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));

  // Create embedded browser view (main browsing pane)
  browserView = new BrowserView({
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.setBrowserView(browserView);

  // Position: leave space for sidebar (280px left) and bottom panel (200px)
  const [width, height] = mainWindow.getContentSize();
  browserView.setBounds({
    x: 280,
    y: 50,  // top bar
    width: width - 280,
    height: height - 250,  // bottom panel
  });
  browserView.setAutoResize({ width: true, height: true });
  browserView.webContents.loadURL('https://www.google.com');

  // Track navigation events
  browserView.webContents.on('did-navigate', (event, url) => {
    mainWindow.webContents.send('navigation', { url });
    sendToRuntime({ type: 'navigation', url });
  });

  browserView.webContents.on('page-title-updated', (event, title) => {
    mainWindow.webContents.send('page-title', { title });
  });

  // Handle window resize
  mainWindow.on('resize', () => {
    const [w, h] = mainWindow.getContentSize();
    browserView.setBounds({
      x: 280,
      y: 50,
      width: w - 280,
      height: h - 250,
    });
  });
}

// IPC handlers from renderer
ipcMain.on('navigate-to', (event, url) => {
  if (browserView) {
    // Ensure URL has protocol
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://' + url;
    }
    browserView.webContents.loadURL(url);
  }
});

ipcMain.on('agent-command', (event, command) => {
  // Forward user commands to agent runtime
  sendToRuntime({ type: 'user-command', text: command });
});

ipcMain.on('go-back', () => {
  if (browserView && browserView.webContents.canGoBack()) {
    browserView.webContents.goBack();
  }
});

ipcMain.on('go-forward', () => {
  if (browserView && browserView.webContents.canGoForward()) {
    browserView.webContents.goForward();
  }
});

app.whenReady().then(() => {
  createWindow();
  connectRuntime();
});

app.on('window-all-closed', () => {
  app.quit();
});
