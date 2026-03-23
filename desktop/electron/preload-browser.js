/**
 * @file preload-browser.js
 * @module desktop/electron/preload-browser
 *
 * DOM bridge for the browser pane.
 * Exposes window.aetherBridge with page reading utilities
 * that the main process can also invoke via IPC.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('aetherBridge', {
  /**
   * Read the current page's visible text, headings, links, etc.
   * Delegates to the main process which runs executeJavaScript
   * on the browser pane's webContents.
   */
  async readPage() {
    return ipcRenderer.invoke('read-page');
  },

  /**
   * Get lightweight page metadata: url, title, favicon.
   */
  async getPageMeta() {
    return ipcRenderer.invoke('get-page-meta');
  },
});
