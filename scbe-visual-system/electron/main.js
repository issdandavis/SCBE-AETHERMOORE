/**
 * SCBE Visual System - Electron Main Process
 *
 * Enables deployment to tablets, phones, and desktop computers.
 * USPTO Patent #63/961,403 (Provisional)
 *
 * @license Apache-2.0
 */

const { app, BrowserWindow, ipcMain, Menu, shell } = require('electron');
const path = require('path');
const isDev = process.env.NODE_ENV === 'development';

let mainWindow;

function createWindow() {
  // Create the browser window with tablet-optimized settings
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 768,
    minHeight: 480,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    // Tablet-friendly settings
    frame: true,
    resizable: true,
    fullscreenable: true,
    // Security
    autoHideMenuBar: false,
    icon: path.join(__dirname, '../assets/icon.png'),
  });

  // Load the app
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  // Handle external links
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Create application menu
function createMenu() {
  const template = [
    {
      label: 'SCBE',
      submenu: [
        {
          label: 'About SCBE Visual System',
          click: () => {
            const { dialog } = require('electron');
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'About SCBE Visual System',
              message: 'SCBE Visual System',
              detail: 'Quantum-Safe Fleet Tablet OS\nUSPTO Patent #63/961,403 (Provisional)\n\nVersion 3.0.0\n\n14-Layer Security Framework\nPost-Quantum Cryptography\nMulti-Agent Orchestration',
            });
          },
        },
        { type: 'separator' },
        {
          label: 'Security Dashboard',
          accelerator: 'CmdOrCtrl+Shift+S',
          click: () => {
            mainWindow.webContents.send('open-app', 'security');
          },
        },
        {
          label: 'Entropic Defense',
          accelerator: 'CmdOrCtrl+Shift+D',
          click: () => {
            mainWindow.webContents.send('open-app', 'defense');
          },
        },
        { type: 'separator' },
        { role: 'quit' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Security',
      submenu: [
        {
          label: 'Run System Scan',
          accelerator: 'CmdOrCtrl+Shift+X',
          click: () => {
            mainWindow.webContents.send('run-security-scan');
          },
        },
        {
          label: 'Check PQC Status',
          click: () => {
            mainWindow.webContents.send('check-pqc-status');
          },
        },
        { type: 'separator' },
        {
          label: 'View Audit Logs',
          click: () => {
            mainWindow.webContents.send('view-audit-logs');
          },
        },
      ],
    },
    {
      label: 'Fleet',
      submenu: [
        {
          label: 'Fleet Dashboard',
          click: () => {
            mainWindow.webContents.send('open-app', 'fleet');
          },
        },
        {
          label: 'Agent Orchestrator',
          click: () => {
            mainWindow.webContents.send('open-app', 'agents');
          },
        },
        { type: 'separator' },
        {
          label: 'Sync All Agents',
          click: () => {
            mainWindow.webContents.send('sync-fleet');
          },
        },
      ],
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'Knowledge Base',
          click: () => {
            mainWindow.webContents.send('open-app', 'knowledge');
          },
        },
        {
          label: 'Documentation',
          click: () => {
            shell.openExternal('https://github.com/ISDanDavis2/SCBE_Production_Pack');
          },
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// App ready
app.whenReady().then(() => {
  createWindow();
  createMenu();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed (except on macOS)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// IPC Handlers
ipcMain.handle('get-system-info', () => {
  return {
    platform: process.platform,
    arch: process.arch,
    version: app.getVersion(),
    electronVersion: process.versions.electron,
    nodeVersion: process.versions.node,
    chromeVersion: process.versions.chrome,
  };
});

ipcMain.handle('get-security-status', () => {
  return {
    pqc: {
      kyber768: 'active',
      dilithium3: 'active',
      sha3_256: 'active',
    },
    layers: {
      total: 14,
      active: 14,
      status: 'operational',
    },
    lastScan: new Date().toISOString(),
  };
});
