/**
 * Chrome Extension API shim for testing the sidepanel outside a real extension.
 *
 * Provides chrome.storage.local, chrome.runtime, and chrome.tabs stubs
 * so the sidepanel ES modules load and function in a normal browser page.
 */

const _store = {
  // Pre-seed settings so the sidepanel connects to the fixture server port
  aetherbrowser_settings: {
    port: 9222,
    preferences: { KO: 'opus', AV: 'flash', RU: 'local', CA: 'sonnet', UM: 'grok', DR: 'haiku' },
    apiKeys: {},
    autoCascade: true,
  },
};

window.chrome = {
  storage: {
    local: {
      get(key, cb) {
        const result = typeof key === 'string' ? { [key]: _store[key] } : {};
        setTimeout(() => cb(result), 0);
      },
      set(items, cb) {
        Object.assign(_store, items);
        if (cb) setTimeout(cb, 0);
      },
    },
  },
  runtime: {
    lastError: null,
    onMessage: {
      addListener() {},
      removeListener() {},
    },
    sendMessage(_msg, cb) {
      // Stub: captureVisibleTab and getOpenTabs fallback to error so catch() paths fire
      if (cb) {
        setTimeout(() => cb({ ok: false, error: 'shim: not in extension context' }), 0);
      }
    },
  },
  action: {
    onClicked: { addListener() {} },
  },
  sidePanel: {
    open() {},
    setPanelBehavior() { return Promise.resolve(); },
  },
  tabs: {
    query(_opts, cb) {
      setTimeout(() => cb([{ id: 1, title: 'Test Tab', url: 'about:blank', active: true }]), 0);
    },
    captureVisibleTab(_windowId, _opts, cb) {
      setTimeout(() => cb('data:image/jpeg;base64,/9j/stub'), 0);
    },
  },
};
