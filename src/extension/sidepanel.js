/**
 * @file sidepanel.js
 * @module extension/sidepanel
 *
 * Main entry point for the AetherBrowser sidebar.
 * Wires WebSocket, components, and user interactions together.
 */

import { WsClient } from './lib/ws-client.js';
import { loadSettings } from './lib/storage.js';
import { readActivePage } from './lib/dom-reader.js';
import { renderAgentGrid, updateAgentBadge, resetAllBadges } from './components/AgentGrid.js';
import { initConversationFeed, appendMessage, appendUserMessage } from './components/ConversationFeed.js';
import { renderZoneApproval } from './components/ZoneApproval.js';
import { renderProgress } from './components/ProgressCard.js';
import { renderDisconnectedBanner } from './components/DisconnectedBanner.js';
import { renderSettingsPanel } from './components/SettingsPanel.js';

// DOM refs
const agentGridEl = document.getElementById('agent-grid');
const feedEl = document.getElementById('conversation-feed');
const disconnectedEl = document.getElementById('disconnected-banner');
const settingsEl = document.getElementById('settings-panel');
const inputEl = document.getElementById('input-text');
const sendBtn = document.getElementById('btn-send');
const thisPageBtn = document.getElementById('btn-this-page');
const researchBtn = document.getElementById('btn-research');
const commandBar = document.getElementById('command-bar');

let ws = null;

async function init() {
  const settings = await loadSettings();

  renderAgentGrid(agentGridEl);
  initConversationFeed(feedEl);

  // Add settings gear to agent grid
  const gearBtn = document.createElement('button');
  gearBtn.className = 'ab-btn ab-btn--secondary';
  gearBtn.textContent = '\u2699';
  gearBtn.title = 'Settings';
  gearBtn.style.cssText = 'margin-left:auto;font-size:16px;padding:2px 6px';
  gearBtn.addEventListener('click', () => {
    renderSettingsPanel(settingsEl, async () => {
      const newSettings = await loadSettings();
      if (ws) {
        ws.disconnect();
        ws.url = `ws://127.0.0.1:${newSettings.port}/ws`;
        ws.connect();
      }
    });
  });
  agentGridEl.appendChild(gearBtn);

  // Connect WebSocket
  ws = new WsClient({
    url: `ws://127.0.0.1:${settings.port}/ws`,
    onMessage: handleWsMessage,
    onConnectionChange: handleConnectionChange,
  });
  ws.connect();

  // Bind events
  sendBtn.addEventListener('click', handleSend);
  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });
  thisPageBtn.addEventListener('click', handleThisPage);
  researchBtn.addEventListener('click', handleResearch);
}

function handleWsMessage(msg) {
  switch (msg.type) {
    case 'chat':
      appendMessage(feedEl, msg);
      break;
    case 'agent_status':
      updateAgentBadge(msg.agent, msg.payload?.state || 'idle', msg.model);
      break;
    case 'progress':
      renderProgress(feedEl, msg);
      break;
    case 'zone_request':
      renderZoneApproval(feedEl, msg, (seq, decision) => {
        ws.sendZoneResponse(seq, decision);
      });
      break;
    case 'error':
      appendMessage(feedEl, {
        agent: 'system',
        payload: { text: `Error: ${msg.payload?.reason || 'unknown'}` },
      });
      break;
  }
}

function handleConnectionChange(connected) {
  if (connected) {
    disconnectedEl.classList.add('hidden');
    feedEl.classList.remove('hidden');
    commandBar.classList.remove('hidden');
    resetAllBadges();
  } else {
    feedEl.classList.add('hidden');
    commandBar.classList.add('hidden');
    disconnectedEl.classList.remove('hidden');
    renderDisconnectedBanner(disconnectedEl, {
      port: ws?.url ? parseInt(new URL(ws.url).port, 10) : 8002,
      onServerStarted: () => ws.connect(),
    });
  }
}

function handleSend() {
  const text = inputEl.value.trim();
  if (!text) return;
  appendUserMessage(feedEl, text);
  ws.sendCommand(text);
  inputEl.value = '';
  inputEl.focus();
}

async function handleThisPage() {
  try {
    appendUserMessage(feedEl, '[Analyzing current page...]');
    const page = await readActivePage();
    ws.sendPageContext(page.url, page.title, page.text);
  } catch (err) {
    appendMessage(feedEl, {
      agent: 'system',
      payload: { text: `Could not read page: ${err.message}` },
    });
  }
}

function handleResearch() {
  const text = inputEl.value.trim();
  if (!text) {
    inputEl.placeholder = 'Type a research topic first...';
    inputEl.focus();
    return;
  }
  appendUserMessage(feedEl, `[Research] ${text}`);
  ws.sendCommand(text);
  inputEl.value = '';
}

init().catch(console.error);
