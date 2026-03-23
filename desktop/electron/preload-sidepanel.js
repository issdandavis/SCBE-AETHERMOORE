/**
 * @file preload-sidepanel.js
 * @module desktop/electron/preload-sidepanel
 *
 * Chrome API shim so the existing src/extension/sidepanel.js works
 * inside Electron without modification.
 *
 * Bridges:
 *   chrome.tabs.query         -> IPC chrome-tabs-query
 *   chrome.tabs.sendMessage   -> IPC chrome-tabs-sendMessage
 *   chrome.tabs.captureVisibleTab -> IPC chrome-tabs-captureVisibleTab
 *   chrome.tabs.update        -> IPC navigate (for topology node clicks)
 *   chrome.storage.local      -> localStorage wrapper
 *   chrome.runtime.sendMessage -> routes to appropriate IPC handler
 *   chrome.runtime.lastError  -> always null (errors thrown instead)
 */

const { contextBridge, ipcRenderer } = require('electron');

// ---------------------------------------------------------------------------
// chrome.storage.local — backed by localStorage
// ---------------------------------------------------------------------------
const storageLocal = {
  get(keys, callback) {
    try {
      const keyList = typeof keys === 'string' ? [keys] : Array.isArray(keys) ? keys : Object.keys(keys);
      const result = {};
      for (const key of keyList) {
        const raw = localStorage.getItem(`aether_${key}`);
        if (raw !== null) {
          try {
            result[key] = JSON.parse(raw);
          } catch {
            result[key] = raw;
          }
        }
      }
      if (callback) callback(result);
    } catch (err) {
      console.error('[preload-sidepanel] storage.get error:', err);
      if (callback) callback({});
    }
  },

  set(items, callback) {
    try {
      for (const [key, value] of Object.entries(items)) {
        localStorage.setItem(`aether_${key}`, JSON.stringify(value));
      }
      if (callback) callback();
    } catch (err) {
      console.error('[preload-sidepanel] storage.set error:', err);
      if (callback) callback();
    }
  },

  remove(keys, callback) {
    const keyList = typeof keys === 'string' ? [keys] : keys;
    for (const key of keyList) {
      localStorage.removeItem(`aether_${key}`);
    }
    if (callback) callback();
  },
};

// ---------------------------------------------------------------------------
// chrome.tabs shim
// ---------------------------------------------------------------------------
const tabsShim = {
  async query(queryInfo, callback) {
    try {
      const tabs = await ipcRenderer.invoke('chrome-tabs-query');
      if (callback) callback(tabs);
      return tabs;
    } catch (err) {
      console.error('[preload-sidepanel] tabs.query error:', err);
      if (callback) callback([]);
      return [];
    }
  },

  async sendMessage(tabId, message, callback) {
    try {
      const response = await ipcRenderer.invoke('chrome-tabs-sendMessage', tabId, message);
      if (callback) callback(response);
      return response;
    } catch (err) {
      console.error('[preload-sidepanel] tabs.sendMessage error:', err);
      if (callback) callback(null);
      return null;
    }
  },

  async captureVisibleTab(windowId, options, callback) {
    // Handle overloaded signatures: (callback), (options, callback), (windowId, options, callback)
    if (typeof windowId === 'function') {
      callback = windowId;
    } else if (typeof options === 'function') {
      callback = options;
    }
    try {
      const result = await ipcRenderer.invoke('chrome-tabs-captureVisibleTab');
      if (result?.ok) {
        if (callback) callback(result.dataUrl);
        return result.dataUrl;
      }
      if (callback) callback('');
      return '';
    } catch (err) {
      console.error('[preload-sidepanel] captureVisibleTab error:', err);
      if (callback) callback('');
      return '';
    }
  },

  update(tabIdOrProps, propsOrCallback, maybeCallback) {
    // chrome.tabs.update({ url }) or chrome.tabs.update(tabId, { url })
    let props;
    if (typeof tabIdOrProps === 'object') {
      props = tabIdOrProps;
    } else {
      props = propsOrCallback;
    }
    if (props?.url) {
      ipcRenderer.send('navigate', props.url);
    }
  },
};

// ---------------------------------------------------------------------------
// chrome.runtime shim
// ---------------------------------------------------------------------------
const runtimeShim = {
  lastError: null,

  sendMessage(message, callback) {
    // Route extension background.js messages to the appropriate IPC handler
    if (message?.action === 'captureVisibleTab') {
      ipcRenderer.invoke('chrome-tabs-captureVisibleTab').then((result) => {
        if (callback) callback(result);
      });
      return true;
    }
    if (message?.action === 'getOpenTabs') {
      ipcRenderer.invoke('chrome-tabs-query').then((tabs) => {
        if (callback) callback({ ok: true, tabs });
      });
      return true;
    }
    if (callback) callback(null);
    return false;
  },

  onMessage: {
    addListener() { /* no-op in Electron */ },
    removeListener() { /* no-op */ },
  },
};

// ---------------------------------------------------------------------------
// chrome.sidePanel shim (no-op — we are the sidepanel)
// ---------------------------------------------------------------------------
const sidePanelShim = {
  open() {},
  setPanelBehavior() { return Promise.resolve(); },
};

// ---------------------------------------------------------------------------
// Expose as window.chrome
// ---------------------------------------------------------------------------
contextBridge.exposeInMainWorld('chrome', {
  tabs: tabsShim,
  storage: { local: storageLocal },
  runtime: runtimeShim,
  sidePanel: sidePanelShim,
  action: { onClicked: { addListener() {} } },
});
