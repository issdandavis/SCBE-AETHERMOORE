/**
 * @file dom-reader.js
 * @module extension/lib/dom-reader
 *
 * Reads the active tab's DOM content via the content script.
 */

export async function readActivePage() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    throw new Error('No active tab found');
  }

  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tab.id, { action: 'getPageContent' }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      resolve(response || { url: tab.url, title: tab.title, text: '' });
    });
  });
}

export async function getOpenTabs() {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ action: 'getOpenTabs' }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      if (!response?.ok) {
        reject(new Error(response?.error || 'Could not fetch tabs'));
        return;
      }
      resolve(response.tabs || []);
    });
  });
}

export async function captureVisibleTab() {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ action: 'captureVisibleTab' }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      if (!response?.ok) {
        reject(new Error(response?.error || 'Could not capture visible tab'));
        return;
      }
      resolve(response.dataUrl || '');
    });
  });
}
