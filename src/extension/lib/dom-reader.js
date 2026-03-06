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
