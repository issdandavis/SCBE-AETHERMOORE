/**
 * @file preload-passwords.js
 * Bridge for the Saved-Passwords management window.
 * Exposes only listing/remove/import -- never raw password reads.
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('vaultUI', {
  list: () => ipcRenderer.invoke('vault:list'),
  remove: (id) => ipcRenderer.invoke('vault:remove', id),
  importFile: () => ipcRenderer.invoke('vault:importDialog'),
});
