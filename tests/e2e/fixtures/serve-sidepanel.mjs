/**
 * Tiny static file server + mock WebSocket backend for e2e sidepanel tests.
 *
 * Serves the extension files from src/extension/ on HTTP port 9222.
 * Injects the chrome-shim.js before sidepanel.js loads.
 * Runs a WebSocket server on /ws that speaks the WsFeed protocol.
 */

import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { join, extname } from 'node:path';
import { WebSocketServer } from 'ws';

const PORT = 9222;
const EXT_DIR = join(process.cwd(), 'src', 'extension');
const FIXTURES_DIR = join(process.cwd(), 'tests', 'e2e', 'fixtures');

const MIME = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
};

// --------------------------------------------------------------------------
// HTTP server — serves extension files + injects chrome shim into the HTML
// --------------------------------------------------------------------------

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);

  // Health endpoint — mirrors the real backend shape so health polling works
  if (url.pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'ok',
      version: '0.1.0-test',
      agents: {},
      providers: {
        local: { available: true, family: 'local', reason: 'local_runtime', tier: 0 },
        haiku: { available: false, family: 'anthropic', reason: 'missing_env:ANTHROPIC_API_KEY', tier: 1 },
        sonnet: { available: false, family: 'anthropic', reason: 'missing_env:ANTHROPIC_API_KEY', tier: 3 },
        opus: { available: false, family: 'anthropic', reason: 'missing_env:ANTHROPIC_API_KEY', tier: 4 },
        flash: { available: false, family: 'openai', reason: 'missing_env:OPENAI_API_KEY', tier: 2 },
        grok: { available: false, family: 'xai', reason: 'missing_env:XAI_API_KEY', tier: 2 },
      },
      executor: {
        local: { available: true, family: 'local', model_id: 'local-control', reason: 'local_runtime', env_vars: [], packages: [] },
        haiku: { available: false, family: 'anthropic', model_id: 'claude-3-5-haiku-20241022', reason: 'missing_env:ANTHROPIC_API_KEY', env_vars: ['ANTHROPIC_API_KEY'], packages: ['anthropic'] },
        sonnet: { available: false, family: 'anthropic', model_id: 'claude-sonnet-4-20250514', reason: 'missing_env:ANTHROPIC_API_KEY', env_vars: ['ANTHROPIC_API_KEY'], packages: ['anthropic'] },
        opus: { available: false, family: 'anthropic', model_id: 'claude-opus-4-1-20250805', reason: 'missing_env:ANTHROPIC_API_KEY', env_vars: ['ANTHROPIC_API_KEY'], packages: ['anthropic'] },
        flash: { available: false, family: 'openai', model_id: 'gpt-4o-mini', reason: 'missing_env:OPENAI_API_KEY', env_vars: ['OPENAI_API_KEY'], packages: ['openai'] },
        grok: { available: false, family: 'xai', model_id: 'grok-3-mini', reason: 'missing_env:XAI_API_KEY', env_vars: ['XAI_API_KEY'], packages: ['openai'] },
      },
    }));
    return;
  }

  let filePath = url.pathname === '/' ? '/sidepanel.html' : url.pathname;

  // Serve chrome-shim from fixtures
  if (filePath === '/chrome-shim.js') {
    try {
      const content = await readFile(join(FIXTURES_DIR, 'chrome-shim.js'), 'utf-8');
      res.writeHead(200, { 'Content-Type': 'application/javascript' });
      res.end(content);
    } catch {
      res.writeHead(404);
      res.end('Not found');
    }
    return;
  }

  const absPath = join(EXT_DIR, filePath);

  try {
    let content = await readFile(absPath, extname(absPath) === '.png' ? undefined : 'utf-8');

    // Inject chrome shim before sidepanel.js loads
    if (filePath === '/sidepanel.html') {
      content = content.replace(
        '<script type="module" src="sidepanel.js"></script>',
        '<script src="/chrome-shim.js"></script>\n  <script type="module" src="sidepanel.js"></script>',
      );
    }

    const mime = MIME[extname(absPath)] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': mime });
    res.end(content);
  } catch {
    res.writeHead(404);
    res.end('Not found');
  }
});

// --------------------------------------------------------------------------
// WebSocket server — mock WsFeed protocol
// --------------------------------------------------------------------------

const wss = new WebSocketServer({ server, path: '/ws' });
let seq = 0;

function makeMsg(type, agent, payload = {}, extra = {}) {
  seq++;
  return JSON.stringify({
    type,
    agent,
    payload,
    ts: new Date().toISOString(),
    seq,
    ...extra,
  });
}

wss.on('connection', (ws) => {
  ws.on('message', (raw) => {
    let msg;
    try {
      msg = JSON.parse(raw.toString());
    } catch {
      ws.send(makeMsg('error', 'system', { reason: 'Invalid JSON' }));
      return;
    }

    if (msg.type === 'command') {
      const text = msg.payload?.text || '';

      // Send KO working status
      ws.send(makeMsg('agent_status', 'KO', { state: 'working' }, { model: 'local' }));

      // If the command contains "login" or "delete", trigger a zone request
      if (/login|delete|deploy/i.test(text)) {
        seq++;
        const zoneSeq = seq;
        ws.send(JSON.stringify({
          type: 'zone_request',
          agent: 'RU',
          zone: 'RED',
          payload: {
            url: 'https://example.com/login',
            action: 'authenticate',
            description: 'Page contains authentication or credential entry',
          },
          ts: new Date().toISOString(),
          seq: zoneSeq,
        }));
        return;
      }

      // Normal response
      ws.send(makeMsg('chat', 'KO', {
        text: `Acknowledged: "${text}". Local execution lane active.`,
        plan: {
          intent: 'general_assist',
          task_type: 'general',
          complexity: 'low',
          provider: 'local',
          selection_reason: 'local_runtime',
          risk_tier: 'low',
          fallback_chain: [],
          browser_action_required: false,
          escalation_ready: false,
          preferred_engine: 'playwright',
          targets: [],
          approval_required: false,
          required_approvals: [],
          auto_cascade: true,
          next_actions: [
            { label: 'Route through the browser dispatcher', reason: 'Start from the governed lane.', risk_tier: 'low', requires_approval: false },
          ],
          assignments: [
            { role: 'KO', task: 'Orchestrate the response' },
            { role: 'DR', task: 'Structure the output' },
          ],
        },
      }, { model: 'local' }));

      ws.send(makeMsg('agent_status', 'KO', { state: 'done' }, { model: 'local' }));
    }

    if (msg.type === 'page_context') {
      ws.send(makeMsg('agent_status', 'CA', { state: 'analyzing' }));
      ws.send(makeMsg('chat', 'CA', {
        text: `Page: ${msg.payload?.title || 'Unknown'}\nWords: 42\nTopics: General`,
        page_analysis: {
          url: msg.payload?.url || '',
          title: msg.payload?.title || '',
          word_count: 42,
          summary: 'Mock page analysis for e2e test.',
          topics: ['General'],
          intent: 'inspect_page',
          risk_tier: 'low',
          page_type: 'generic',
          heading_count: 0,
          link_count: 0,
          form_count: 0,
          button_count: 0,
          tab_count: 0,
          next_actions: [{ label: 'Capture page snapshot', reason: 'Preserve evidence.', risk_tier: 'low', requires_approval: false }],
          required_approvals: [],
        },
      }, { model: 'local' }));
      ws.send(makeMsg('agent_status', 'CA', { state: 'done' }));
    }

    if (msg.type === 'zone_response') {
      const decision = msg.payload?.decision || 'deny';
      ws.send(makeMsg('chat', 'RU', {
        text: `Zone decision received: ${decision}. ${decision === 'deny' ? 'Browser plan denied.' : 'Releasing the held browser plan.'}`,
      }));
      ws.send(makeMsg('agent_status', 'KO', { state: decision === 'deny' ? 'error' : 'done' }, { model: 'local' }));
    }
  });
});

// --------------------------------------------------------------------------
// Start
// --------------------------------------------------------------------------

server.listen(PORT, '127.0.0.1', () => {
  console.log(`AetherBrowser e2e fixture server on http://127.0.0.1:${PORT}`);
});
