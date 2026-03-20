/**
 * SCBE AI Bridge — Background Service Worker
 *
 * Listens for messages from content scripts and from external connections
 * (Playwright / Claude Code). Routes commands to the right bridge.
 */

// WebSocket server for Claude Code to connect to
let ws = null;
const WS_PORT = 9333;

// Store for responses from content scripts
const pendingResponses = new Map();
let messageId = 0;

// Handle messages from content scripts
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'bridge-ready') {
    console.log(`[SCBE Bridge] ${msg.bridge} bridge ready on tab ${sender.tab?.id}`);
    sendResponse({ ok: true });
    return;
  }

  if (msg.type === 'bridge-response') {
    const pending = pendingResponses.get(msg.id);
    if (pending) {
      pending.resolve(msg.result);
      pendingResponses.delete(msg.id);
    }
    return;
  }
});

// Handle messages from Playwright/external pages via window.postMessage
chrome.runtime.onMessageExternal.addListener((msg, sender, sendResponse) => {
  handleCommand(msg, sendResponse);
  return true; // async response
});

// Also expose via content script messaging for Playwright
chrome.runtime.onConnect.addListener((port) => {
  console.log('[SCBE Bridge] Port connected:', port.name);
  port.onMessage.addListener((msg) => {
    handleCommand(msg, (response) => port.postMessage(response));
  });
});

async function handleCommand(msg, sendResponse) {
  const { action, target, params } = msg;

  // Get the active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) {
    sendResponse({ ok: false, error: 'No active tab' });
    return;
  }

  const id = ++messageId;

  // Send command to the content script bridge
  try {
    const response = await chrome.tabs.sendMessage(tab.id, {
      type: 'bridge-command',
      id,
      action,
      target,
      params,
    });
    sendResponse({ ok: true, result: response });
  } catch (e) {
    sendResponse({ ok: false, error: e.message });
  }
}

console.log('[SCBE AI Bridge] Background service worker loaded');
