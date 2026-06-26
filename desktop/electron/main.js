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
  dialog,
} = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const vault = require('./vault');
const bookmarks = require('./bookmarks');

// Use software rendering -- avoids GPU/driver crashes that leave the window invisible on launch
// (very common on laptops with integrated graphics). Slightly slower, but it always opens.
app.disableHardwareAcceleration();

// Automation surface (Playwright / AI control), OFF by default for safety.
// Only when AETHER_AUTOMATION=1 is set do we open the Chrome DevTools Protocol port,
// which lets Playwright `chromium.connectOverCDP('http://127.0.0.1:9222')` drive the
// browser pane (navigate / click / type / screenshot). Bound to localhost only.
const AUTOMATION_PORT = String(process.env.AETHER_AUTOMATION_PORT || '9222');
if (process.env.AETHER_AUTOMATION === '1') {
  app.commandLine.appendSwitch('remote-debugging-port', AUTOMATION_PORT);
  app.commandLine.appendSwitch('remote-debugging-address', '127.0.0.1');
}

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
// Tab manager — each tab owns its own WebContentsView (real multi-tab).
// `browserView` always points at the ACTIVE tab's view, so the rest of the app
// keeps operating on "the current page" without having to know about tabs.
// ---------------------------------------------------------------------------
const DEFAULT_URL = 'https://www.google.com';
const tabs = [];          // [{ id, view, url, title }]
let activeTabId = null;
let viewMode = 'single';  // 'single' = active tab fills the pane; 'grid' = tile all tabs (agent view)
let nextTabId = 1;

function activeTab() {
  return tabs.find((t) => t.id === activeTabId) || tabs[0] || null;
}
function activeView() {
  const t = activeTab();
  return t ? t.view : null;
}

function wireTabView(tab) {
  const wc = tab.view.webContents;
  const update = () => {
    tab.url = wc.getURL();
    tab.title = wc.getTitle();
    notifyTabStrip();
    if (tab.id === activeTabId) notifyAddressBar();
  };
  wc.on('did-navigate', update);
  wc.on('did-navigate-in-page', update);
  wc.on('page-title-updated', update);
  wc.on('render-process-gone', () => { try { wc.reload(); } catch { /* best effort */ } });
  // Open new windows / target=_blank as new tabs instead of separate popups.
  wc.setWindowOpenHandler(({ url }) => {
    if (/^https?:/i.test(url)) newTab(url);
    return { action: 'deny' };
  });
}

function createTab(url) {
  const view = new WebContentsView({
    webPreferences: {
      preload: PRELOAD_BROWSER,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  const tab = { id: nextTabId++, view, url: url || DEFAULT_URL, title: 'New Tab' };
  tabs.push(tab);
  if (mainWindow) mainWindow.contentView.addChildView(view);
  wireTabView(tab);
  view.webContents.loadURL(url || DEFAULT_URL);
  return tab;
}

function newTab(url) {
  const tab = createTab(url || DEFAULT_URL);
  switchTab(tab.id);
  return tab;
}

function switchTab(id) {
  if (!tabs.some((t) => t.id === id)) return;
  activeTabId = id;
  browserView = activeView();
  layoutViews();
  notifyAddressBar();
  notifyTabStrip();
}

function closeTab(id) {
  const idx = tabs.findIndex((t) => t.id === id);
  if (idx === -1) return;
  const [tab] = tabs.splice(idx, 1);
  try { mainWindow.contentView.removeChildView(tab.view); } catch { /* ignore */ }
  try { tab.view.webContents.close(); } catch { /* ignore */ }
  if (activeTabId === id) {
    const next = tabs[idx] || tabs[idx - 1] || null;
    if (next) switchTab(next.id);
    else { activeTabId = null; browserView = null; newTab(DEFAULT_URL); }
  } else {
    layoutViews();
    notifyTabStrip();
  }
}

// ---------------------------------------------------------------------------
// Window creation
// ---------------------------------------------------------------------------
let mainWindow = null;
let addressBarView = null;
let tabStripView = null;
let browserView = null;       // pointer to the ACTIVE tab's view
let sidepanelView = null;

const SIDEPANEL_RATIO = 0.25;
const ADDRESS_BAR_HEIGHT = 52;
const TAB_STRIP_HEIGHT = 38;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    title: 'AetherBrowser',
    backgroundColor: '#0d1117',
    show: true,        // show immediately -- never leave the user with no window if a pane is slow
    center: true,
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

  // --- Tab strip (between the address bar and the page) ---
  tabStripView = new WebContentsView({
    webPreferences: {
      preload: path.join(__dirname, 'preload-tabstrip.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.contentView.addChildView(tabStripView);
  tabStripView.webContents.loadFile(path.join(RENDERER_DIR, 'tab-strip.html'));

  // --- First tab (the browser pane) ---
  const first = createTab(DEFAULT_URL);
  activeTabId = first.id;
  browserView = first.view;

  // --- Sidepanel (reuses extension UI) ---
  sidepanelView = new WebContentsView({
    webPreferences: {
      preload: PRELOAD_SIDEPANEL,
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.contentView.addChildView(sidepanelView);
  // Packaged download -> bundled self-contained panel (always present). Dev -> the full
  // extension UI if it exists locally. This keeps a downloaded app from showing a blank panel.
  const externalPanel = path.join(EXTENSION_DIR, 'sidepanel.html');
  const sidepanelHtml = (!app.isPackaged && fs.existsSync(externalPanel))
    ? externalPanel
    : path.join(RENDERER_DIR, 'sidepanel.html');
  sidepanelView.webContents.loadFile(sidepanelHtml);

  // --- Layout ---
  layoutViews();
  mainWindow.on('resize', layoutViews);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Fallback: always show the window within 2.5s even if a child view is slow to become ready,
  // so a hiccup in one pane can never leave the user staring at nothing.
  setTimeout(() => {
    if (mainWindow && !mainWindow.isVisible()) mainWindow.show();
  }, 2500);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function layoutViews() {
  if (!mainWindow) return;
  const [width, height] = mainWindow.getContentSize();
  const topH = TAB_STRIP_HEIGHT + ADDRESS_BAR_HEIGHT;
  const spWidth = Math.round(width * SIDEPANEL_RATIO);
  const bpWidth = width - spWidth;
  const bodyHeight = Math.max(0, height - topH);
  const bpX = 0;
  const bpY = topH;

  if (tabStripView) tabStripView.setBounds({ x: 0, y: 0, width, height: TAB_STRIP_HEIGHT });
  if (addressBarView) addressBarView.setBounds({ x: 0, y: TAB_STRIP_HEIGHT, width, height: ADDRESS_BAR_HEIGHT });
  if (sidepanelView) sidepanelView.setBounds({ x: bpWidth, y: bpY, width: spWidth, height: bodyHeight });

  const HIDDEN = { x: 0, y: 0, width: 0, height: 0 };
  if (viewMode === 'grid' && tabs.length > 1) {
    // Agent view: tile every open tab so several pages are visible at once.
    const cols = Math.ceil(Math.sqrt(tabs.length));
    const rows = Math.ceil(tabs.length / cols);
    const cw = Math.floor(bpWidth / cols);
    const ch = Math.floor(bodyHeight / rows);
    tabs.forEach((t, i) => {
      const r = Math.floor(i / cols);
      const c = i % cols;
      t.view.setBounds({ x: bpX + c * cw, y: bpY + r * ch, width: cw, height: ch });
    });
  } else {
    // Single view: the active tab fills the pane, the rest are parked at zero size.
    tabs.forEach((t) => {
      t.view.setBounds(t.id === activeTabId ? { x: bpX, y: bpY, width: bpWidth, height: bodyHeight } : HIDDEN);
    });
  }
}

function notifyAddressBar() {
  if (!addressBarView || !browserView) return;
  const wc = browserView.webContents;
  addressBarView.webContents.send('navigation-update', {
    url: wc.getURL(),
    title: wc.getTitle(),
    canGoBack: wc.canGoBack(),
    canGoForward: wc.canGoForward(),
  });
}

function notifyTabStrip() {
  if (!tabStripView) return;
  tabStripView.webContents.send('tabs:update', {
    tabs: tabs.map((t) => ({ id: t.id, title: t.title || 'New Tab', active: t.id === activeTabId })),
    mode: viewMode,
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

// --- Tab strip / multi-tab / agent grid view ---
ipcMain.on('tabstrip:ready', () => notifyTabStrip());
ipcMain.on('tab:new', () => newTab(DEFAULT_URL));
ipcMain.on('tab:close', (_event, id) => closeTab(id));
ipcMain.on('tab:select', (_event, id) => switchTab(id));
ipcMain.on('view:setMode', (_event, mode) => {
  viewMode = mode === 'grid' ? 'grid' : 'single';
  layoutViews();
  notifyTabStrip();
});

// --- Bookmarks ---
ipcMain.handle('bookmarks:list', () => bookmarks.list());
ipcMain.handle('bookmark:remove', (_event, id) => { bookmarks.remove(id); refreshBookmarksWindow(); return bookmarks.list(); });
ipcMain.on('bookmark:addCurrent', () => {
  const t = activeTab();
  if (t) { bookmarks.add(t.url, t.title); refreshBookmarksWindow(); }
});
ipcMain.on('bookmark:open', (_event, url) => { if (url) newTab(url); });
ipcMain.on('bookmarks:openWindow', () => openBookmarksWindow());

// Sidepanel chrome API shims
ipcMain.handle('chrome-tabs-query', async () => {
  return tabs.map((tab) => ({
    id: tab.id,
    title: tab.title || '',
    url: tab.url || '',
    active: tab.id === activeTabId,
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
// Secure password vault (autofill + save). Encryption is OS-level (safeStorage).
// ---------------------------------------------------------------------------

// The real origin of the frame that sent an IPC message. Used so a web page can
// only ever read/fill ITS OWN saved password -- never another site's.
function senderOrigin(event) {
  try {
    return new URL(event.senderFrame.url).origin;
  } catch {
    return null;
  }
}

// Autofill: the browser pane asks for credentials for the page it is actually on.
ipcMain.handle('vault:get', (event) => {
  const origin = senderOrigin(event);
  if (!origin || origin === 'null') return [];
  return vault.getForOrigin(origin);
});

// Save prompt: triggered when a login form is submitted in the browser pane.
// We confirm with a native Windows dialog (CSP-proof, clearly trustworthy).
ipcMain.on('vault:capture', async (event, payload) => {
  try {
    let origin = String((payload && payload.origin) || '');
    if (!/^https?:\/\//i.test(origin)) return;
    origin = new URL(origin).origin;
    const username = String((payload && payload.username) || '').slice(0, 512);
    const password = String((payload && payload.password) || '');
    if (!password) return;
    if (vault.isNever(origin)) return;
    const existing = vault.getForOrigin(origin).find((e) => e.username === username);
    if (existing && existing.password === password) return; // already saved, unchanged

    const host = new URL(origin).host;
    const { response } = await dialog.showMessageBox(mainWindow, {
      type: 'question',
      buttons: ['Save', 'Never for this site', 'Not now'],
      defaultId: 0,
      cancelId: 2,
      noLink: true,
      title: 'AetherBrowser',
      message: existing ? `Update saved password for ${host}?` : `Save password for ${host}?`,
      detail:
        (username ? `Username: ${username}\n\n` : '') +
        'AetherBrowser will fill this in for you next time. It is encrypted with Windows security and never leaves this computer.',
    });
    if (response === 0) vault.upsert({ origin, username, password });
    else if (response === 1) vault.addNever(origin);
  } catch {
    /* never let a save prompt break browsing */
  }
});

// Management-window IPC (no passwords are sent to the list view).
ipcMain.handle('vault:list', () => vault.list());
ipcMain.handle('vault:remove', (_event, id) => vault.remove(id));
ipcMain.handle('vault:importDialog', async (event) => {
  const win = BrowserWindow.fromWebContents(event.sender) || mainWindow;
  return importPasswordsDialog(win);
});

// --- Import from a Google or Proton Pass export file (CSV or JSON) ---------

function parseCSV(text) {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += c;
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ',') {
      row.push(field); field = '';
    } else if (c === '\n') {
      row.push(field); rows.push(row); row = []; field = '';
    } else if (c !== '\r') {
      field += c;
    }
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows;
}

function parsePasswordExport(raw, filePath) {
  const isJson = /\.json$/i.test(filePath) || /^\s*[[{]/.test(raw);
  if (isJson) {
    const records = [];
    let data;
    try { data = JSON.parse(raw); } catch { return records; }
    // Best-effort walk: collect any object that carries a password-like field.
    const visit = (node) => {
      if (!node || typeof node !== 'object') return;
      if (Array.isArray(node)) { node.forEach(visit); return; }
      const pw = node.password || node.pass;
      if (pw) {
        const url = node.url || node.uri || (Array.isArray(node.urls) && node.urls[0]) || node.website || '';
        records.push({ url, username: node.username || node.email || node.login || node.user || '', password: pw });
      }
      Object.values(node).forEach(visit);
    };
    visit(data);
    return records;
  }
  // CSV (Google: name,url,username,password,note  /  Proton Pass: name,url,username,password,note,totp,...)
  const rows = parseCSV(raw).filter((r) => r.length && r.some((c) => c.trim() !== ''));
  if (rows.length < 2) return [];
  const header = rows[0].map((h) => h.trim().toLowerCase());
  const findCol = (...names) => {
    for (const n of names) {
      const idx = header.indexOf(n);
      if (idx !== -1) return idx;
    }
    return -1;
  };
  const urlCol = findCol('url', 'website', 'uri', 'login_uri');
  const userCol = findCol('username', 'login', 'user');
  const emailCol = findCol('email', 'e-mail');
  const passCol = findCol('password', 'pass', 'login_password');
  if (passCol === -1) return [];
  const records = [];
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i];
    records.push({
      url: urlCol !== -1 ? r[urlCol] : '',
      username: (userCol !== -1 && r[userCol]) ? r[userCol] : (emailCol !== -1 ? r[emailCol] : ''),
      password: r[passCol] || '',
    });
  }
  return records;
}

async function importPasswordsDialog(parent) {
  const res = await dialog.showOpenDialog(parent, {
    title: 'Import passwords (Google or Proton Pass export)',
    filters: [{ name: 'Password export', extensions: ['csv', 'json'] }, { name: 'All files', extensions: ['*'] }],
    properties: ['openFile'],
  });
  if (res.canceled || !res.filePaths[0]) return { imported: 0, canceled: true };
  try {
    const file = res.filePaths[0];
    const raw = fs.readFileSync(file, 'utf8');
    const records = parsePasswordExport(raw, file);
    const imported = vault.importMany(records);
    await dialog.showMessageBox(parent, {
      type: imported > 0 ? 'info' : 'warning',
      title: 'AetherBrowser',
      message: `Imported ${imported} password${imported === 1 ? '' : 's'}.`,
      detail:
        imported > 0
          ? 'They are encrypted in your vault and will auto-fill the next time you visit those sites.'
          : 'No usable rows were found. Make sure this is a Google or Proton Pass CSV/JSON export (it needs a password column).',
    });
    return { imported };
  } catch (err) {
    await dialog.showMessageBox(parent, { type: 'error', title: 'AetherBrowser', message: 'Could not read that file.', detail: String(err.message || err) });
    return { imported: 0, error: true };
  }
}

// --- Saved-passwords management window -------------------------------------
let passwordsWindow = null;
function openPasswordsWindow() {
  if (passwordsWindow && !passwordsWindow.isDestroyed()) {
    passwordsWindow.focus();
    return;
  }
  passwordsWindow = new BrowserWindow({
    width: 760,
    height: 620,
    title: 'AetherBrowser — Saved Passwords',
    backgroundColor: '#0d1117',
    parent: mainWindow,
    show: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload-passwords.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  passwordsWindow.setMenuBarVisibility(false);
  passwordsWindow.loadFile(path.join(RENDERER_DIR, 'passwords.html'));
  passwordsWindow.on('closed', () => { passwordsWindow = null; });
}

// --- Bookmark board window -------------------------------------------------
let bookmarksWindow = null;
function openBookmarksWindow() {
  if (bookmarksWindow && !bookmarksWindow.isDestroyed()) {
    bookmarksWindow.focus();
    return;
  }
  bookmarksWindow = new BrowserWindow({
    width: 820,
    height: 640,
    title: 'AetherBrowser — Bookmark Board',
    backgroundColor: '#0d1117',
    parent: mainWindow,
    show: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload-bookmarks.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  bookmarksWindow.setMenuBarVisibility(false);
  bookmarksWindow.loadFile(path.join(RENDERER_DIR, 'bookmarks.html'));
  bookmarksWindow.on('closed', () => { bookmarksWindow = null; });
}
function refreshBookmarksWindow() {
  if (bookmarksWindow && !bookmarksWindow.isDestroyed()) {
    bookmarksWindow.webContents.reload();
  }
}

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
          click: () => newTab(DEFAULT_URL),
        },
        {
          label: 'Close Tab',
          accelerator: 'CmdOrCtrl+W',
          click: () => {
            const t = activeTab();
            if (tabs.length > 1 && t) closeTab(t.id);
            else if (mainWindow) mainWindow.close();
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
      label: 'Passwords',
      submenu: [
        {
          label: 'Saved Passwords…',
          accelerator: 'CmdOrCtrl+Shift+P',
          click: () => openPasswordsWindow(),
        },
        {
          label: 'Import from File (Google / Proton)…',
          click: () => importPasswordsDialog(mainWindow),
        },
      ],
    },
    {
      label: 'Bookmarks',
      submenu: [
        {
          label: 'Bookmark This Page',
          accelerator: 'CmdOrCtrl+D',
          click: () => {
            const t = activeTab();
            if (t) { bookmarks.add(t.url, t.title); refreshBookmarksWindow(); }
          },
        },
        {
          label: 'Open Bookmark Board…',
          accelerator: 'CmdOrCtrl+Shift+B',
          click: () => openBookmarksWindow(),
        },
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
          label: 'Toggle Agent Grid View',
          accelerator: 'CmdOrCtrl+G',
          click: () => {
            viewMode = viewMode === 'grid' ? 'single' : 'grid';
            layoutViews();
            notifyTabStrip();
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
  // Only try to launch the Python AI backend in development. A packaged download has no
  // Python; the browser + sidepanel work standalone, and the panel shows "AI offline" gracefully.
  if (!app.isPackaged) spawnBackend();
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
