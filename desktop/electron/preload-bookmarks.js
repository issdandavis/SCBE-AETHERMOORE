/**
 * @file preload-bookmarks.js
 * Bridge for the Bookmark Board window.
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('bookmarksUI', {
  list: () => ipcRenderer.invoke('bookmarks:list'),
  remove: (id) => ipcRenderer.invoke('bookmark:remove', id),
  open: (url) => ipcRenderer.send('bookmark:open', url),
});
