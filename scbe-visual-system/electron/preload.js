/**
 * SCBE Visual System - Electron Preload Script
 *
 * Secure bridge between renderer and main process.
 * Implements context isolation for security.
 *
 * @license Apache-2.0
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods for the renderer to use
contextBridge.exposeInMainWorld('scbeElectron', {
  // System Information
  getSystemInfo: () => ipcRenderer.invoke('get-system-info'),
  getSecurityStatus: () => ipcRenderer.invoke('get-security-status'),

  // Event listeners
  onOpenApp: (callback) => {
    ipcRenderer.on('open-app', (_, appId) => callback(appId));
  },
  onSecurityScan: (callback) => {
    ipcRenderer.on('run-security-scan', () => callback());
  },
  onPQCStatus: (callback) => {
    ipcRenderer.on('check-pqc-status', () => callback());
  },
  onAuditLogs: (callback) => {
    ipcRenderer.on('view-audit-logs', () => callback());
  },
  onFleetSync: (callback) => {
    ipcRenderer.on('sync-fleet', () => callback());
  },

  // Platform detection
  platform: process.platform,
  isElectron: true,
});

// Also expose AI Studio compatibility
contextBridge.exposeInMainWorld('aistudio', {
  hasSelectedApiKey: async () => {
    // Check if API key is configured
    return process.env.GEMINI_API_KEY ? true : false;
  },
  openSelectKey: async () => {
    // Open key configuration dialog
    ipcRenderer.send('open-api-key-config');
  },
});
