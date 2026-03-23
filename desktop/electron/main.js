/**
 * @file main.js
 * @module desktop/electron/main
 *
 * AetherBrowser Electron main process.
 * Creates a shell with two WebContentsView children:
 *   - Browser pane (75% width) — navigable Chromium webview
 *   - Sidepanel (25% width) — reuses src/extension/ sidepanel UI
 *
 * Spawns the Python backend (src.aetherbrowser.serve:app) on port 8002
 * and tears it down on quit.
 */

const {
  app,
  BrowserWindow,
  WebContentsView,
  ipcMain,
  Menu,
  globalShortcut,
  nativeImage,
} = require('electron');
const path = require('path');
const { spawn } = require('child_process');

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
const ROOT = path.resolve(__dirname, '..', '..');
const EXTENSION_DIR = path.join(ROOT, 'src', 'extension');
const RENDERER_DIR = path.join(__dirname, '..', 'renderer');
const PRELOAD_SIDEPANEL = path.join(__dirname, 'preload-sidepanel.js');
const PRELOAD_BROWSER = path.join(__dirname, 'preload-browser.js');

// ---------------------------------------------------------------------------
// Backend process management
// ---------------------------------------------------------------------------
let backendProcess = null;
const BACKEND_PORT = 8002;

function spawnBackend() {
  if (backendProcess) return;

  backendProcess = spawn(
    'python',
    ['-m', 'uvicorn', 'src.aetherbrowser.serve:app', '--port', String(BACKEND_PORT), '--host', '127.0.0.1'],
    {
      cwd: ROOT,
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: true,
    }
  );

  backendProcess.stdout.on('data', (data) => {
    console.log(`[backend] ${data.toString().trim()}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`[backend] ${data.toString().trim()}`);
  });

  backendProcess.on('close', (code) => {
    console.log(`[backend] exited with code ${code}`);
    backendProcess = null;
  });

  backendProcess.on('error', (err) => {
    console.error(`[backend] failed to start: ${err.message}`);
    backendProcess = null;
  });
}

function killBackend() {
  if (!backendProcess) return;
  try {
    // On Windows, spawn a taskkill to ensure the whole tree dies
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(backendProcess.pid), '/T', '/F'], { shell: true });
    } else {
      backendProcess.kill('SIGTERM');
    }
  } catch {
    // best effort
  }
  backendProcess = null;
}

// ---------------------------------------------------------------------------
// Tab state — tracks the browser pane's navigation
// ---------------------------------------------------------------------------
const tabs = [];
let activeTabIndex = 0;

function currentTab() {
  return tabs[activeTabIndex] || null;
}

function syncTabState(browserView) {
  const wc = browserView.webContents;
  const tab = currentTab();
  if (tab) {
    tab.url = wc.getURL();
    tab.title = wc.getTitle();
  }
}

// ---------------------------------------------------------------------------
// Window creation
// ---------------------------------------------------------------------------
let mainWindow = null;
let addressBarView = null;
let browserView = null;
let sidepanelView = null;

const SIDEPANEL_RATIO = 0.25;
const ADDRESS_BAR_HEIGHT = 52;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    title: 'AetherBrowser',
    backgroundColor: '#0d1117',
    show: false,
  });

  // --- Address bar (top chrome) ---
  addressBarView = new WebContentsView({
    webPreferences: {
      preload: path.join(__dirname, 'preload-addressbar.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.contentView.addChildView(addressBarView);
  addressBarView.webContents.loadFile(path.join(RENDERER_DIR, 'address-bar.html'));

  // --- Browser pane ---
  browserView = new WebContentsView({
    webPreferences: {
      preload: PRELOAD_BROWSER,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  mainWindow.contentView.addChildView(browserView);

  // Start with a welcome page or blank
  browserView.webContents.loadURL('https://www.google.com');
  tabs.push({ url: 'https://www.google.com', title: 'Google' });

  // Track navigation in the browser pane
  browserView.webContents.on('did-navigate', () => {
    syncTabState(browserView);
    notifyAddressBar();
  });
  browserView.webContents.on('did-navigate-in-page', () => {
    syncTabState(browserView);
    notifyAddressBar();
  });
  browserView.webContents.on('page-title-updated', () => {
    syncTabState(browserView);
    notifyAddressBar();
  });

  // --- Sidepanel (reuses extension UI) ---
  sidepanelView = new WebContentsView({
    webPreferences: {
      preload: PRELOAD_SIDEPANEL,
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.contentView.addChildView(sidepanelView);
  sidepanelView.webContents.loadFile(path.join(EXTENSION_DIR, 'sidepanel.html'));

  // --- Layout ---
  layoutViews();
  mainWindow.on('resize', layoutViews);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function layoutViews() {
  if (!mainWindow) return;
  const [width, height] = mainWindow.getContentSize();
  const spWidth = Math.round(width * SIDEPANEL_RATIO);
  const bpWidth = width - spWidth;
  const bodyHeight = height - ADDRESS_BAR_HEIGHT;

  addressBarView.setBounds({ x: 0, y: 0, width, height: ADDRESS_BAR_HEIGHT });
  browserView.setBounds({ x: 0, y: ADDRESS_BAR_HEIGHT, width: bpWidth, height: bodyHeight });
  sidepanelView.setBounds({ x: bpWidth, y: ADDRESS_BAR_HEIGHT, width: spWidth, height: bodyHeight });
}

function notifyAddressBar() {
  if (!addressBarView) return;
  const wc = browserView.webContents;
  addressBarView.webContents.send('navigation-update', {
    url: wc.getURL(),
    title: wc.getTitle(),
    canGoBack: wc.canGoBack(),
    canGoForward: wc.canGoForward(),
  });
}

// ---------------------------------------------------------------------------
// IPC handlers
// ---------------------------------------------------------------------------

// Navigation from address bar
ipcMain.on('navigate', (_event, url) => {
  if (browserView) {
    browserView.webContents.loadURL(url);
  }
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

ipcMain.on('reload', () => {
  if (browserView) {
    browserView.webContents.reload();
  }
});

// Sidepanel chrome API shims
ipcMain.handle('chrome-tabs-query', async () => {
  return tabs.map((tab, i) => ({
    id: i,
    title: tab.title || '',
    url: tab.url || '',
    active: i === activeTabIndex,
    pinned: false,
    audible: false,
  }));
});

ipcMain.handle('chrome-tabs-sendMessage', async (_event, tabId, message) => {
  // Forward message to the browser pane's content and get a response
  if (message.action === 'getPageContent') {
    try {
      const result = await browserView.webContents.executeJavaScript(`
        (function() {
          const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'SVG', 'IFRAME']);
          const MAX_LENGTH = 100000;
          let text = '';
          const walker = document.createTreeWalker(
            document.body || document.documentElement,
            NodeFilter.SHOW_TEXT,
            {
              acceptNode(node) {
                const parent = node.parentElement;
                if (!parent) return NodeFilter.FILTER_REJECT;
                if (SKIP_TAGS.has(parent.tagName)) return NodeFilter.FILTER_REJECT;
                if (parent.hidden || parent.getAttribute('aria-hidden') === 'true')
                  return NodeFilter.FILTER_REJECT;
                const style = getComputedStyle(parent);
                if (style.display === 'none' || style.visibility === 'hidden')
                  return NodeFilter.FILTER_REJECT;
                return NodeFilter.FILTER_ACCEPT;
              },
            }
          );
          while (walker.nextNode()) {
            const value = walker.currentNode.nodeValue.trim();
            if (value) { text += value + ' '; if (text.length > MAX_LENGTH) break; }
          }

          const headings = Array.from(document.querySelectorAll('h1, h2, h3'))
            .slice(0, 20)
            .map(el => ({ level: el.tagName, text: el.textContent?.trim() || '' }))
            .filter(r => r.text);

          const links = Array.from(document.querySelectorAll('a[href]'))
            .slice(0, 40)
            .map(el => ({ text: (el.textContent || '').trim(), href: el.href || '' }))
            .filter(r => r.href);

          const buttons = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"]'))
            .slice(0, 20)
            .map(el => ({ text: (el.textContent || el.value || '').trim(), type: el.getAttribute('type') || el.tagName.toLowerCase() }))
            .filter(r => r.text);

          const forms = Array.from(document.forms).slice(0, 10).map((form, index) => ({
            index,
            action: form.action || '',
            method: (form.method || 'get').toLowerCase(),
            fields: Array.from(form.elements).slice(0, 20).map(f => ({
              name: f.name || '',
              type: f.type || f.tagName.toLowerCase(),
            })).filter(f => f.name || f.type),
          }));

          let pageType = 'generic';
          if (document.forms.length > 0) pageType = 'form';
          else if (document.querySelector('article')) pageType = 'article';
          else if (document.querySelector('[role="main"]')) pageType = 'app';

          return {
            url: window.location.href,
            title: document.title,
            text: text.slice(0, MAX_LENGTH).trim(),
            headings,
            links,
            buttons,
            forms,
            selection: window.getSelection()?.toString().trim() || '',
            pageType,
          };
        })();
      `);
      return result;
    } catch (err) {
      return { url: '', title: '', text: '', error: err.message };
    }
  }
  return null;
});

ipcMain.handle('chrome-tabs-captureVisibleTab', async () => {
  if (!browserView) return { ok: false, error: 'No browser pane' };
  try {
    const image = await browserView.webContents.capturePage();
    const dataUrl = 'data:image/jpeg;base64,' + image.toJPEG(70).toString('base64');
    return { ok: true, dataUrl };
  } catch (err) {
    return { ok: false, error: err.message };
  }
});

// Browser pane preload APIs
ipcMain.handle('read-page', async () => {
  if (!browserView) return null;
  try {
    return await browserView.webContents.executeJavaScript(`
      ({
        url: window.location.href,
        title: document.title,
        text: document.body?.innerText?.slice(0, 100000) || '',
      })
    `);
  } catch {
    return null;
  }
});

ipcMain.handle('get-page-meta', async () => {
  if (!browserView) return null;
  try {
    return await browserView.webContents.executeJavaScript(`
      ({
        url: window.location.href,
        title: document.title,
        favicon: document.querySelector('link[rel*="icon"]')?.href || '',
      })
    `);
  } catch {
    return null;
  }
});

// ---------------------------------------------------------------------------
// Application menu with keyboard shortcuts
// ---------------------------------------------------------------------------
function buildMenu() {
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'New Tab',
          accelerator: 'CmdOrCtrl+T',
          click: () => {
            if (browserView) {
              tabs.push({ url: 'https://www.google.com', title: 'New Tab' });
              activeTabIndex = tabs.length - 1;
              browserView.webContents.loadURL('https://www.google.com');
            }
          },
        },
        {
          label: 'Close Tab',
          accelerator: 'CmdOrCtrl+W',
          click: () => {
            if (tabs.length > 1) {
              tabs.splice(activeTabIndex, 1);
              activeTabIndex = Math.min(activeTabIndex, tabs.length - 1);
              const tab = currentTab();
              if (tab && browserView) {
                browserView.webContents.loadURL(tab.url);
              }
            } else if (mainWindow) {
              mainWindow.close();
            }
          },
        },
        { type: 'separator' },
        {
          label: 'Focus Address Bar',
          accelerator: 'CmdOrCtrl+L',
          click: () => {
            if (addressBarView) {
              addressBarView.webContents.send('focus-address-bar');
            }
          },
        },
        { type: 'separator' },
        { role: 'quit' },
      ],
    },
    {
      label: 'View',
      submenu: [
        {
          label: 'Reload Page',
          accelerator: 'CmdOrCtrl+R',
          click: () => {
            if (browserView) browserView.webContents.reload();
          },
        },
        {
          label: 'Toggle Sidepanel DevTools',
          accelerator: 'CmdOrCtrl+Shift+I',
          click: () => {
            if (sidepanelView) sidepanelView.webContents.toggleDevTools();
          },
        },
        {
          label: 'Toggle Browser DevTools',
          accelerator: 'F12',
          click: () => {
            if (browserView) browserView.webContents.toggleDevTools();
          },
        },
      ],
    },
    {
      label: 'Navigate',
      submenu: [
        {
          label: 'Back',
          accelerator: 'Alt+Left',
          click: () => {
            if (browserView && browserView.webContents.canGoBack())
              browserView.webContents.goBack();
          },
        },
        {
          label: 'Forward',
          accelerator: 'Alt+Right',
          click: () => {
            if (browserView && browserView.webContents.canGoForward())
              browserView.webContents.goForward();
          },
        },
      ],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ---------------------------------------------------------------------------
// App lifecycle
// ---------------------------------------------------------------------------
app.whenReady().then(() => {
  spawnBackend();
  buildMenu();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  killBackend();
  app.quit();
});

app.on('before-quit', () => {
  killBackend();
});
