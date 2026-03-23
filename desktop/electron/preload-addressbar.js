/**
 * @file preload-addressbar.js
 * @module desktop/electron/preload-addressbar
 *
 * Preload for the address bar renderer.
 * Exposes navigation IPC channels to the address-bar.js renderer script.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('addressBarBridge', {
  navigate(url) {
    ipcRenderer.send('navigate', url);
  },
  goBack() {
    ipcRenderer.send('go-back');
  },
  goForward() {
    ipcRenderer.send('go-forward');
  },
  reload() {
    ipcRenderer.send('reload');
  },
  onNavigationUpdate(callback) {
    ipcRenderer.on('navigation-update', (_event, data) => callback(data));
  },
  onFocusAddressBar(callback) {
    ipcRenderer.on('focus-address-bar', () => callback());
  },
});
