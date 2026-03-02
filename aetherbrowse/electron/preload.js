/**
 * AetherBrowse — Preload Script
 * Exposes safe IPC bridge to renderer
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('aetherbrowse', {
  // Navigation
  navigateTo: (payload) => ipcRenderer.send('navigate-to', payload),
  goBack: (tabId) => ipcRenderer.send('go-back', tabId),
  goForward: (tabId) => ipcRenderer.send('go-forward', tabId),
  reload: (tabId) => ipcRenderer.send('reload-tab', tabId),
  stop: (tabId) => ipcRenderer.send('stop-tab', tabId),
  goHome: (tabId) => ipcRenderer.send('go-home', tabId),
  newTab: (url = '') => ipcRenderer.send('new-tab', url),
  closeTab: (tabId) => ipcRenderer.send('close-tab', tabId),
  switchTab: (tabId) => ipcRenderer.send('switch-tab', tabId),
  browserCommand: (command) => ipcRenderer.send('browser-command', command),

  // Agent commands
  sendCommand: (text) => ipcRenderer.send('agent-command', text),

  // Event listeners
  onNavigation: (callback) => ipcRenderer.on('navigation', (_, data) => callback(data)),
  onPageTitle: (callback) => ipcRenderer.on('page-title', (_, data) => callback(data)),
  onAgentMessage: (callback) => ipcRenderer.on('agent-message', (_, data) => callback(data)),
  onRuntimeStatus: (callback) => ipcRenderer.on('runtime-status', (_, data) => callback(data)),
  onTabsUpdated: (callback) => ipcRenderer.on('tabs-updated', (_, data) => callback(data)),
  onActiveTabChanged: (callback) => ipcRenderer.on('active-tab-changed', (_, data) => callback(data)),
});
