/**
 * @file storage.js
 * @module extension/lib/storage
 *
 * Wrapper around chrome.storage.local for settings persistence.
 */

const DEFAULTS = {
  port: 8002,
  preferences: {
    KO: 'opus',
    AV: 'flash',
    RU: 'local',
    CA: 'sonnet',
    UM: 'grok',
    DR: 'haiku',
  },
  apiKeys: {},
  autoCascade: true,
};

export async function loadSettings() {
  return new Promise((resolve) => {
    chrome.storage.local.get('aetherbrowser_settings', (result) => {
      resolve({ ...DEFAULTS, ...(result.aetherbrowser_settings || {}) });
    });
  });
}

export async function saveSettings(settings) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ aetherbrowser_settings: settings }, resolve);
  });
}

export async function getSetting(key) {
  const settings = await loadSettings();
  return settings[key];
}

export async function setSetting(key, value) {
  const settings = await loadSettings();
  settings[key] = value;
  await saveSettings(settings);
}
