/**
 * AetherBrowse — Preload Script
 * Exposes safe IPC bridge to renderer
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('aetherbrowse', {
  // Navigation
  navigateTo: (url) => ipcRenderer.send('navigate-to', url),
  goBack: () => ipcRenderer.send('go-back'),
  goForward: () => ipcRenderer.send('go-forward'),

  // Agent commands
  sendCommand: (text) => ipcRenderer.send('agent-command', text),

  // Event listeners
  onNavigation: (callback) => ipcRenderer.on('navigation', (_, data) => callback(data)),
  onPageTitle: (callback) => ipcRenderer.on('page-title', (_, data) => callback(data)),
  onAgentMessage: (callback) => ipcRenderer.on('agent-message', (_, data) => callback(data)),
  onRuntimeStatus: (callback) => ipcRenderer.on('runtime-status', (_, data) => callback(data)),
});
