// src/extension/background.js
chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ tabId: tab.id });
});

chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })
  .catch((e) => console.error('sidePanel.setPanelBehavior error:', e));

chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.action === 'captureVisibleTab') {
    chrome.tabs.captureVisibleTab(undefined, { format: 'jpeg', quality: 70 }, (dataUrl) => {
      if (chrome.runtime.lastError) {
        sendResponse({ ok: false, error: chrome.runtime.lastError.message });
        return;
      }
      sendResponse({ ok: true, dataUrl });
    });
    return true;
  }

  if (request.action === 'getOpenTabs') {
    chrome.tabs.query({ currentWindow: true }, (tabs) => {
      if (chrome.runtime.lastError) {
        sendResponse({ ok: false, error: chrome.runtime.lastError.message });
        return;
      }
      const payload = (tabs || []).map((tab) => ({
        id: tab.id,
        title: tab.title || '',
        url: tab.url || '',
        active: Boolean(tab.active),
        pinned: Boolean(tab.pinned),
        audible: Boolean(tab.audible),
      }));
      sendResponse({ ok: true, tabs: payload });
    });
    return true;
  }

  return false;
});
