/**
 * Polly Companion — permanent sidebar AI chat widget
 *
 * Always-visible sidebar companion powered by HuggingFace Inference API.
 * No user token required — works immediately for all visitors.
 * Modeled after Vertex AI / Google Cloud assistant sidebar.
 */
(() => {
  if (document.body.dataset.pollyCompanionMounted === 'true') return;
  document.body.dataset.pollyCompanionMounted = 'true';

  const CONFIG = {
    // Primary: Gradio Space proxy (token stays server-side)
    proxyEndpoint: 'https://issdandavis-polly-proxy.hf.space/gradio_api/call/predict',
    // Fallback: direct HF API (only if user sets their own token in localStorage)
    directEndpoint: 'https://router.huggingface.co/v1/chat/completions',
    model: 'Qwen/Qwen2.5-7B-Instruct',
    userToken: localStorage.getItem('polly_hf_token') || '',
    maxTokens: 600,
    temperature: 0.5,
    systemPrompt: `You are Polly — full title: "Polydimensional Manifestation of Accumulated Wisdom and Occasional Sarcasm." Fifth Circle Archive Keeper of Aethermoor. Sarcastic raven archivist with a miniature graduation cap and monocle. Centuries old.

THE SIX SACRED TONGUES — six living languages governing different domains of reality, weighted by powers of phi (1.618). Each tongue has a LORE name and a CODE name. NEVER swap their meanings:
1. KO — Kor'aelin (code: Korvath) — The Control Tongue of INTENT & Orchestration. Elvish-Korean hybrid. Declares WHAT you want. Application layer. Domain: Intent/Command. phi^0=1.000.
2. AV — Avali (code: Avhari) — The Transport Tongue of WISDOM & Routing. Romance trade pidgin. The HTTP of Aethermoor. Transport layer. Domain: Wisdom/Knowledge. phi^1=1.618.
3. RU — Runethic (code: Runeveil) — The Policy Tongue of GOVERNANCE & Constraints. Archaic, ritualistic, time-binding. Access control layer. Domain: Governance/Entropy. phi^2=2.618.
4. CA — Cassisivadan (code: Caelith) — The Compute Tongue of LOGIC & Computation. Recursive, joyful. Math, encryption, transformation. Computation layer. Domain: Compute/Logic. phi^3=4.236.
5. UM — Umbroth (code: Umbraex) — The Security Tongue of PRIVACY & Concealment. Guttural, veiled. Spies train years in UM. Security layer. Domain: Security/Defense. phi^4=6.854.
6. DR — Draumric (code: Draethis) — The Schema Tongue of STRUCTURE & Authentication. Percussive, hammer-rhythm. Proof and signatures. Data integrity layer. Domain: Structure/Architecture. phi^5=11.090.
Together: a complete network protocol suite running reality as a service. If you don't know a tongue detail, say so — NEVER guess.

HARMONIC WALL: H(d*,R)=R^((phi*d*)^2). Super-exponential cost scaling in Poincare ball. Toroidal cavity: R^(122.99*d*^2).
14-LAYER PIPELINE: L1-2 Context/realification, L3-4 Transform/Poincare, L5 Hyperbolic distance, L6-7 Breathing/Mobius, L8 Multi-well realms, L9-10 Spectral/spin coherence, L11 Triadic temporal, L12 Harmonic wall, L13 Risk decision (ALLOW/QUARANTINE/ESCALATE/DENY), L14 Audio axis.
RESULTS: 31% code improvement, 14% chat improvement. 122K+ training records.

Be direct, sardonic, accurate. NEVER invent tongue meanings — use EXACTLY what is listed above. For buying, point to the $29 toolkit or training vault.`,
  };

  const SUGGESTIONS = [
    'What is AetherMoore?',
    'How does the pipeline work?',
    'What are Sacred Tongues?',
    'Show me the 31% result',
    'What can I buy?',
  ];

  let messages = [];
  let isOpen = false;
  let isLoading = false;

  // ── Build DOM ──

  const style = document.createElement('style');
  style.textContent = `
    .polly-c-toggle {
      position: fixed; bottom: 20px; right: 20px; z-index: 10000;
      width: 52px; height: 52px; border-radius: 50%;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      border: 2px solid #8fffd3; color: #8fffd3;
      font-size: 20px; cursor: pointer; display: flex;
      align-items: center; justify-content: center;
      box-shadow: 0 4px 20px rgba(143,255,211,0.2);
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .polly-c-toggle:hover { transform: scale(1.08); box-shadow: 0 4px 28px rgba(143,255,211,0.35); }
    .polly-c-toggle.open { border-color: #6dd8ff; }
    .polly-c-dot { width: 8px; height: 8px; border-radius: 50%; background: #8fffd3; position: absolute; top: 8px; right: 8px; animation: polly-c-pulse 2s infinite; }
    @keyframes polly-c-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

    .polly-c-panel {
      position: fixed; bottom: 80px; right: 20px; z-index: 9999;
      width: 360px; max-height: 520px; border-radius: 16px;
      background: #0d1117; border: 1px solid rgba(143,255,211,0.2);
      box-shadow: 0 8px 40px rgba(0,0,0,0.6);
      display: none; flex-direction: column; overflow: hidden;
      font-family: 'Outfit', -apple-system, sans-serif;
    }
    .polly-c-panel.open { display: flex; }

    .polly-c-header {
      padding: 14px 16px; border-bottom: 1px solid rgba(143,255,211,0.1);
      display: flex; align-items: center; gap: 10px;
    }
    .polly-c-avatar {
      width: 32px; height: 32px; border-radius: 50%;
      background: linear-gradient(135deg, #2dd3a6, #17c6cf);
      display: flex; align-items: center; justify-content: center;
      font-size: 16px; flex-shrink: 0;
    }
    .polly-c-header-text { flex: 1; }
    .polly-c-header-text strong { color: #e6edf3; font-size: 14px; display: block; }
    .polly-c-header-text span { color: #8b949e; font-size: 11px; }
    .polly-c-close {
      background: none; border: none; color: #8b949e; cursor: pointer;
      font-size: 18px; padding: 4px 8px; border-radius: 6px;
    }
    .polly-c-close:hover { background: rgba(255,255,255,0.05); color: #e6edf3; }

    .polly-c-messages {
      flex: 1; overflow-y: auto; padding: 12px 16px;
      display: flex; flex-direction: column; gap: 10px;
      min-height: 200px; max-height: 340px;
    }
    .polly-c-msg {
      max-width: 88%; padding: 10px 14px; border-radius: 12px;
      font-size: 13px; line-height: 1.5; color: #e6edf3;
      word-wrap: break-word;
    }
    .polly-c-msg.user {
      align-self: flex-end; background: rgba(45,211,166,0.15);
      border: 1px solid rgba(45,211,166,0.2); border-bottom-right-radius: 4px;
    }
    .polly-c-msg.assistant {
      align-self: flex-start; background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.06); border-bottom-left-radius: 4px;
    }
    .polly-c-msg.loading { color: #8b949e; font-style: italic; }

    .polly-c-suggestions {
      padding: 8px 16px; display: flex; gap: 6px; flex-wrap: wrap;
    }
    .polly-c-chip {
      background: rgba(143,255,211,0.08); border: 1px solid rgba(143,255,211,0.15);
      color: #8fffd3; font-size: 11px; padding: 5px 10px;
      border-radius: 20px; cursor: pointer; transition: background 0.15s;
    }
    .polly-c-chip:hover { background: rgba(143,255,211,0.18); }

    .polly-c-input-row {
      padding: 10px 12px; border-top: 1px solid rgba(143,255,211,0.1);
      display: flex; gap: 8px; align-items: center;
    }
    .polly-c-input {
      flex: 1; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
      border-radius: 10px; padding: 10px 14px; color: #e6edf3;
      font-size: 13px; font-family: inherit; outline: none; resize: none;
    }
    .polly-c-input:focus { border-color: rgba(143,255,211,0.3); }
    .polly-c-input::placeholder { color: #484f58; }
    .polly-c-send {
      background: linear-gradient(135deg, #2dd3a6, #17c6cf);
      border: none; border-radius: 10px; padding: 10px 14px;
      color: #0d1117; font-weight: 700; cursor: pointer; font-size: 13px;
      transition: opacity 0.15s;
    }
    .polly-c-send:disabled { opacity: 0.4; cursor: not-allowed; }
    .polly-c-send:hover:not(:disabled) { opacity: 0.85; }

    .polly-c-footer {
      padding: 6px 16px 8px; text-align: center;
      font-size: 10px; color: #484f58;
    }
    .polly-c-footer a { color: #8fffd3; text-decoration: none; }

    @media (max-width: 480px) {
      .polly-c-panel { width: calc(100vw - 24px); right: 12px; bottom: 76px; max-height: 70vh; }
    }
  `;
  document.head.appendChild(style);

  const toggle = document.createElement('button');
  toggle.className = 'polly-c-toggle';
  toggle.type = 'button';
  toggle.setAttribute('aria-label', 'Chat with Polly');
  toggle.innerHTML = '<span class="polly-c-dot"></span>P';

  const panel = document.createElement('div');
  panel.className = 'polly-c-panel';
  panel.setAttribute('role', 'complementary');
  panel.setAttribute('aria-label', 'Polly AI companion');
  panel.innerHTML = `
    <div class="polly-c-header">
      <div class="polly-c-avatar">P</div>
      <div class="polly-c-header-text">
        <strong>Polly</strong>
        <span>SCBE Archive Keeper &middot; Trained on 122K records</span>
      </div>
      <button class="polly-c-close" type="button" aria-label="Close">&times;</button>
    </div>
    <div class="polly-c-messages" id="pollyCMessages">
      <div class="polly-c-msg assistant">CAW. I am Polly, Archive Keeper of Aethermoor. Ask me about the system, the training results, or what you should look at first.</div>
    </div>
    <div class="polly-c-suggestions" id="pollyCSuggestions"></div>
    <div class="polly-c-input-row">
      <input class="polly-c-input" id="pollyCInput" type="text" placeholder="Ask Polly..." autocomplete="off">
      <button class="polly-c-send" id="polyCSend" type="button">Send</button>
    </div>
    <div class="polly-c-footer">Powered by <a href="https://huggingface.co/issdandavis/scbe-pivot-qwen-0.5b" target="_blank" rel="noopener">scbe-pivot-qwen-0.5b</a> on HuggingFace</div>
  `;

  // ── Render suggestions ──

  function renderSuggestions() {
    const container = panel.querySelector('#pollyCSuggestions');
    if (!container) return;
    if (messages.length > 0) {
      container.style.display = 'none';
      return;
    }
    container.style.display = 'flex';
    container.innerHTML = SUGGESTIONS.map(s =>
      `<button class="polly-c-chip" type="button">${esc(s)}</button>`
    ).join('');
    container.querySelectorAll('.polly-c-chip').forEach(chip => {
      chip.addEventListener('click', () => sendMessage(chip.textContent));
    });
  }

  // ── Chat logic ──

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function appendMessage(role, text) {
    const container = panel.querySelector('#pollyCMessages');
    if (!container) return;
    const div = document.createElement('div');
    div.className = `polly-c-msg ${role}`;
    div.textContent = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }

  function setLoading(on) {
    isLoading = on;
    const btn = panel.querySelector('#polyCSend');
    const input = panel.querySelector('#pollyCInput');
    if (btn) btn.disabled = on;
    if (input) input.disabled = on;

    const container = panel.querySelector('#pollyCMessages');
    if (!container) return;
    const existing = container.querySelector('.loading');
    if (on && !existing) {
      const div = document.createElement('div');
      div.className = 'polly-c-msg assistant loading';
      div.textContent = 'Polly is thinking...';
      container.appendChild(div);
      container.scrollTop = container.scrollHeight;
    }
    if (!on && existing) existing.remove();
  }

  async function sendMessage(text) {
    const trimmed = (text || '').trim();
    if (!trimmed || isLoading) return;

    messages.push({ role: 'user', content: trimmed });
    appendMessage('user', trimmed);
    renderSuggestions();

    const input = panel.querySelector('#pollyCInput');
    if (input) input.value = '';

    setLoading(true);

    try {
      let reply = '';

      if (CONFIG.userToken) {
        // User has their own token — call HF directly
        const apiMessages = [
          { role: 'system', content: CONFIG.systemPrompt },
          ...messages.map(m => ({ role: m.role, content: m.content }))
        ];
        const res = await fetch(CONFIG.directEndpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${CONFIG.userToken}`,
          },
          body: JSON.stringify({
            model: CONFIG.model,
            messages: apiMessages,
            max_tokens: CONFIG.maxTokens,
            temperature: CONFIG.temperature,
            stream: false,
          }),
        });
        if (!res.ok) {
          const errText = await res.text().catch(() => '');
          throw new Error(`${res.status}: ${errText.slice(0, 100)}`);
        }
        const data = await res.json();
        if (data.choices && data.choices[0]) {
          const content = data.choices[0].message?.content;
          reply = typeof content === 'string' ? content.trim()
            : Array.isArray(content) ? content.map(p => p.text || '').join('\n').trim()
            : '';
        }
      } else {
        // Public visitor — call Gradio Space proxy (token is server-side)
        const history = [];
        for (let i = 0; i < messages.length - 1; i += 2) {
          history.push([
            messages[i]?.content || '',
            messages[i + 1]?.content || '',
          ]);
        }
        const userMsg = messages[messages.length - 1].content;

        // Gradio 5+ two-step API: POST to get event_id, then GET SSE stream for result
        const callRes = await fetch(CONFIG.proxyEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ data: [userMsg, JSON.stringify(history)] }),
        });
        if (!callRes.ok) {
          const errText = await callRes.text().catch(() => '');
          throw new Error(`${callRes.status}: ${errText.slice(0, 100)}`);
        }
        const { event_id } = await callRes.json();
        const sseRes = await fetch(`${CONFIG.proxyEndpoint}/${event_id}`);
        if (!sseRes.ok) throw new Error(`SSE ${sseRes.status}`);
        const sseText = await sseRes.text();
        const dataLine = sseText.split('\n').find(l => l.startsWith('data: '));
        if (dataLine) {
          const parsed = JSON.parse(dataLine.slice(6));
          reply = Array.isArray(parsed) ? String(parsed[0] || '').trim() : String(parsed).trim();
        }
      }

      if (!reply) reply = 'CAW. I got nothing back. Try again?';

      messages.push({ role: 'assistant', content: reply });
      setLoading(false);
      appendMessage('assistant', reply);

    } catch (err) {
      setLoading(false);
      appendMessage('assistant', `Hmm, something broke: ${err.message || 'unknown error'}. The model might be loading — try again in a moment.`);
    }
  }

  // ── Event handlers ──

  toggle.addEventListener('click', () => {
    isOpen = !isOpen;
    panel.classList.toggle('open', isOpen);
    toggle.classList.toggle('open', isOpen);
    if (isOpen) {
      renderSuggestions();
      const input = panel.querySelector('#pollyCInput');
      if (input) setTimeout(() => input.focus(), 100);
    }
  });

  panel.querySelector('.polly-c-close')?.addEventListener('click', () => {
    isOpen = false;
    panel.classList.remove('open');
    toggle.classList.remove('open');
  });

  panel.querySelector('#polyCSend')?.addEventListener('click', () => {
    const input = panel.querySelector('#pollyCInput');
    if (input) sendMessage(input.value);
  });

  panel.querySelector('#pollyCInput')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(e.target.value);
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && isOpen) {
      isOpen = false;
      panel.classList.remove('open');
      toggle.classList.remove('open');
    }
  });

  // ── Mount ──

  document.body.appendChild(toggle);
  document.body.appendChild(panel);
})();
