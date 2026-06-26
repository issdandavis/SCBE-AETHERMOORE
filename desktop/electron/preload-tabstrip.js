/**
 * @file preload-tabstrip.js
 * Bridge for the tab strip UI (open tabs, new/close/select, grid toggle, bookmarks).
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('tabStrip', {
  onUpdate(cb) {
    ipcRenderer.on('tabs:update', (_e, data) => cb(data));
    ipcRenderer.send('tabstrip:ready'); // ask main to push the current state
  },
  select: (id) => ipcRenderer.send('tab:select', id),
  close: (id) => ipcRenderer.send('tab:close', id),
  newTab: () => ipcRenderer.send('tab:new'),
  setMode: (mode) => ipcRenderer.send('view:setMode', mode),
  bookmarkCurrent: () => ipcRenderer.send('bookmark:addCurrent'),
  openBookmarks: () => ipcRenderer.send('bookmarks:openWindow'),
});
