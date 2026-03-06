// src/extension/background.js
chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ tabId: tab.id });
});

chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })
  .catch((e) => console.error('sidePanel.setPanelBehavior error:', e));
