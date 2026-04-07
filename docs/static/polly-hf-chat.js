(() => {
  const DEFAULTS = {
    title: "Polly",
    subtitle: "A quiet operating surface for SCBE chat.",
    assistantName: "Polly",
    endpoint: "https://router.huggingface.co/v1/chat/completions",
    model: "issdandavis/scbe-pivot-qwen-0.5b",
    compareModels: [],
    proxyEndpoint: "",
    apiKey: "",
    storagePrefix: "scbe_hf_chat",
    exportSource: "polly_hf_chat",
    compact: false,
    maxTokens: 480,
    temperature: 0.45,
    systemPrompt:
      "You are Polly, Fifth Circle Archive Keeper of Aethermoor. Sarcastic raven archivist. Know the Six Sacred Tongues: KO=Kor'aelin/Korvath (Intent), AV=Avali/Avhari (Wisdom/Routing), RU=Runethic/Runeveil (Governance), CA=Cassisivadan/Caelith (Compute), UM=Umbroth/Umbraex (Security), DR=Draumric/Draethis (Structure). Phi-weighted: 1.000, 1.618, 2.618, 4.236, 6.854, 11.090. Harmonic Wall: H(d*,R)=R^((phi*d*)^2). 14-layer pipeline. NEVER guess tongue meanings. Be direct, sardonic, accurate.",
    suggestions: [],
    initialAssistantText: "Add a token or proxy and start talking."
  };

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function normalizeContent(content) {
    if (typeof content === "string") return content.trim();
    if (Array.isArray(content)) {
      return content
        .map((part) => {
          if (!part) return "";
          if (typeof part === "string") return part;
          if (part.type === "text") return part.text || "";
          if (part.type === "output_text") return part.text || "";
          if (part.type === "input_text") return part.text || "";
          return "";
        })
        .join("\n")
        .trim();
    }
    if (content && typeof content === "object" && typeof content.text === "string") {
      return content.text.trim();
    }
    return "";
  }

  function storageKey(prefix, suffix) {
    return `${prefix}:${suffix}`;
  }

  function readStored(prefix, suffix, fallback = "") {
    try {
      return window.localStorage.getItem(storageKey(prefix, suffix)) || fallback;
    } catch {
      return fallback;
    }
  }

  function writeStored(prefix, suffix, value) {
    try {
      window.localStorage.setItem(storageKey(prefix, suffix), value);
    } catch {
      return;
    }
  }

  function readFeedback(prefix) {
    const raw = readStored(prefix, "feedback", "[]");
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  function writeFeedback(prefix, records) {
    writeStored(prefix, "feedback", JSON.stringify(records));
  }

  function normalizeModelList(value) {
    const rawItems = Array.isArray(value)
      ? value
      : typeof value === "string"
        ? value.split(/[\n,]/)
        : [];
    return [...new Set(rawItems.map((item) => String(item || "").trim()).filter(Boolean))];
  }

  function shortModelName(modelId) {
    const value = String(modelId || "").trim();
    if (!value) return "assistant";
    const parts = value.split("/");
    return parts[parts.length - 1] || value;
  }

  function nextSessionId() {
    return `scbe-chat-${new Date().toISOString().replace(/[:.]/g, "-")}-${Math.random().toString(16).slice(2, 8)}`;
  }

  function createMessage(role, content, extra = {}) {
    return {
      role,
      content: String(content || "").trim(),
      createdAt: new Date().toISOString(),
      ...extra
    };
  }

  function readThread(prefix) {
    const raw = readStored(prefix, "thread", "");
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      const messages = Array.isArray(parsed?.messages)
        ? parsed.messages
            .filter((message) => message && (message.role === "assistant" || message.role === "user"))
            .map((message) => ({
              role: message.role,
              content: String(message.content || "").trim(),
              createdAt: String(message.createdAt || new Date().toISOString()),
              initial: Boolean(message.initial),
              model: String(message.model || ""),
              lane: String(message.lane || ""),
              label: String(message.label || "")
            }))
            .filter((message) => message.content)
        : [];
      if (!messages.length) return null;
      return {
        session: {
          id: String(parsed?.session?.id || nextSessionId()),
          startedAt: String(parsed?.session?.startedAt || new Date().toISOString())
        },
        messages
      };
    } catch {
      return null;
    }
  }

  function writeThread(prefix, payload) {
    writeStored(prefix, "thread", JSON.stringify(payload));
  }

  function downloadFile(filename, text, mimeType) {
    const blob = new Blob([text], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 500);
  }

  async function requestCompletion(config, messages) {
    const headers = {
      "Content-Type": "application/json"
    };

    const target = (config.proxyEndpoint || "").trim() || config.endpoint;
    const usingProxy = Boolean((config.proxyEndpoint || "").trim());

    if (!usingProxy) {
      if (!config.token.trim()) {
        throw new Error("Add a Hugging Face token or configure a proxy endpoint.");
      }
      headers.Authorization = `Bearer ${config.token.trim()}`;
    } else if (config.apiKey && config.apiKey.trim()) {
      headers.SCBE_api_key = config.apiKey.trim();
    }

    const response = await fetch(target, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model: config.model.trim(),
        messages,
        max_tokens: config.maxTokens,
        temperature: config.temperature,
        stream: false
      })
    });

    const rawText = await response.text();
    let data = {};

    try {
      data = rawText ? JSON.parse(rawText) : {};
    } catch {
      data = { rawText };
    }

    if (!response.ok) {
      const message =
        data.error ||
        data.message ||
        data.rawText ||
        `HF request failed (${response.status})`;
      throw new Error(String(message).slice(0, 400));
    }

    const text =
      normalizeContent(data?.choices?.[0]?.message?.content) ||
      normalizeContent(data?.message?.content) ||
      normalizeContent(data?.content) ||
      normalizeContent(data?.generated_text) ||
      normalizeContent(data?.text) ||
      normalizeContent(Array.isArray(data) ? data[0]?.generated_text : "");

    if (!text) {
      throw new Error("HF returned no assistant text.");
    }

    return text;
  }

  function buildStyles(compact) {
    return `
      :host, .polly-chat-root {
        display: block;
        height: 100%;
        color: #eef5ff;
        --polly-line: rgba(183, 218, 255, 0.14);
        --polly-soft: rgba(255,255,255,0.05);
        --polly-soft-strong: rgba(255,255,255,0.08);
        --polly-muted: #a9bdd4;
        --polly-accent: #73d2ff;
        --polly-gold: #d4b676;
        font-family: "Aptos", "Segoe UI Variable Text", "Trebuchet MS", sans-serif;
      }
      .polly-shell {
        display: grid;
        grid-template-columns: ${compact ? "1fr" : "minmax(280px, 340px) 1fr"};
        height: 100%;
        min-height: ${compact ? "540px" : "680px"};
      }
      .polly-context {
        padding: 22px;
        border-right: ${compact ? "0" : "1px solid var(--polly-line)"};
        border-bottom: ${compact ? "1px solid var(--polly-line)" : "0"};
        background: linear-gradient(180deg, rgba(5,12,20,0.35), rgba(5,12,20,0.08));
      }
      .polly-kicker {
        margin: 0 0 12px;
        color: var(--polly-accent);
        letter-spacing: 0.16em;
        text-transform: uppercase;
        font-size: 0.74rem;
      }
      .polly-title {
        margin: 0;
        font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
        font-size: ${compact ? "1.75rem" : "2.35rem"};
        line-height: 0.96;
      }
      .polly-subtitle {
        margin: 12px 0 0;
        color: var(--polly-muted);
        line-height: 1.6;
      }
      .polly-meta,
      .polly-tips {
        margin-top: 20px;
        padding-top: 18px;
        border-top: 1px solid var(--polly-line);
      }
      .polly-meta h3,
      .polly-tips h3 {
        margin: 0 0 10px;
        font-size: 0.95rem;
      }
      .polly-meta p,
      .polly-tips li {
        color: var(--polly-muted);
        line-height: 1.55;
      }
      .polly-tips ul {
        margin: 0;
        padding-left: 18px;
      }
      .polly-main {
        display: grid;
        grid-template-rows: auto 1fr auto;
        min-height: 0;
      }
      .polly-bar {
        padding: 18px 20px 14px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        border-bottom: 1px solid var(--polly-line);
      }
      .polly-bar-title {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .polly-bar-title strong {
        font-size: 1rem;
      }
      .polly-bar-title span {
        color: var(--polly-muted);
        font-size: 0.88rem;
      }
      .polly-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }
      .polly-button,
      .polly-chip {
        border: 1px solid var(--polly-line);
        background: var(--polly-soft);
        color: #eef5ff;
        border-radius: 999px;
        padding: 10px 14px;
        font: inherit;
        cursor: pointer;
        transition: transform 150ms ease, background 150ms ease, border-color 150ms ease;
      }
      .polly-button:hover,
      .polly-chip:hover {
        transform: translateY(-1px);
        background: var(--polly-soft-strong);
        border-color: rgba(115, 210, 255, 0.3);
      }
      .polly-button.primary {
        background: linear-gradient(135deg, rgba(115, 210, 255, 0.24), rgba(115, 210, 255, 0.08));
        border-color: rgba(115, 210, 255, 0.34);
      }
      .polly-thread {
        overflow: auto;
        padding: 20px;
        display: flex;
        flex-direction: column;
        gap: 14px;
        background:
          radial-gradient(circle at top right, rgba(115, 210, 255, 0.08), transparent 26%),
          linear-gradient(180deg, rgba(8, 16, 27, 0.24), rgba(8, 16, 27, 0.08));
      }
      .polly-message {
        max-width: min(100%, 760px);
        padding: 14px 16px;
        border-radius: 18px;
        border: 1px solid var(--polly-line);
        line-height: 1.6;
        white-space: pre-wrap;
        opacity: 0;
        transform: translateY(8px);
        animation: polly-rise 220ms ease forwards;
      }
      .polly-message.user {
        align-self: flex-end;
        background: rgba(115, 210, 255, 0.12);
        border-color: rgba(115, 210, 255, 0.24);
      }
      .polly-message.assistant {
        align-self: flex-start;
        background: rgba(255, 255, 255, 0.04);
      }
      .polly-message-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 8px;
        font-size: 0.8rem;
        color: var(--polly-muted);
        text-transform: uppercase;
        letter-spacing: 0.12em;
      }
      .polly-feedback {
        margin-top: 10px;
        display: flex;
        gap: 8px;
      }
      .polly-feedback button {
        border: 0;
        background: transparent;
        color: var(--polly-muted);
        font: inherit;
        cursor: pointer;
        padding: 0;
      }
      .polly-suggestions {
        padding: 0 20px 14px;
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        border-top: 1px solid transparent;
      }
      .polly-compose {
        border-top: 1px solid var(--polly-line);
        padding: 18px 20px 20px;
        display: grid;
        gap: 12px;
      }
      .polly-textarea {
        width: 100%;
        min-height: ${compact ? "88px" : "118px"};
        resize: vertical;
        border-radius: 18px;
        border: 1px solid var(--polly-line);
        background: rgba(0, 0, 0, 0.16);
        color: #eef5ff;
        padding: 14px 16px;
        font: inherit;
      }
      .polly-compose-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        flex-wrap: wrap;
      }
      .polly-status {
        color: var(--polly-muted);
        font-size: 0.9rem;
      }
      .polly-settings {
        display: none;
        gap: 12px;
        margin-top: 8px;
        padding-top: 14px;
        border-top: 1px solid var(--polly-line);
      }
      .polly-settings.open {
        display: grid;
      }
      .polly-field {
        display: grid;
        gap: 6px;
      }
      .polly-field label {
        color: var(--polly-muted);
        font-size: 0.84rem;
      }
      .polly-field input,
      .polly-field textarea {
        width: 100%;
        border-radius: 14px;
        border: 1px solid var(--polly-line);
        background: rgba(0, 0, 0, 0.18);
        color: #eef5ff;
        padding: 11px 13px;
        font: inherit;
      }
      .polly-footer-note {
        color: var(--polly-muted);
        font-size: 0.84rem;
        line-height: 1.5;
      }
      @keyframes polly-rise {
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }
      @media (max-width: 860px) {
        .polly-shell {
          grid-template-columns: 1fr;
        }
        .polly-context {
          border-right: 0;
          border-bottom: 1px solid var(--polly-line);
        }
      }
    `;
  }

  function mount(root, options = {}) {
    if (!root) return;

    const config = {
      ...DEFAULTS,
      ...options,
      compareModels: normalizeModelList(options.compareModels || DEFAULTS.compareModels)
    };
    const initialAssistantText = options.initialAssistantText || config.initialAssistantText;
    const storedThread = readThread(config.storagePrefix);
    const state = {
      settings: {
        token: options.token || readStored(config.storagePrefix, "token", ""),
        model: options.model || readStored(config.storagePrefix, "model", config.model),
        compareModelsText:
          (Array.isArray(options.compareModels)
            ? options.compareModels.join(", ")
            : options.compareModels) || readStored(config.storagePrefix, "compareModels", config.compareModels.join(", ")),
        proxyEndpoint: options.proxyEndpoint || readStored(config.storagePrefix, "proxy", config.proxyEndpoint),
        apiKey: options.apiKey || readStored(config.storagePrefix, "apiKey", config.apiKey),
        systemPrompt:
          options.systemPrompt || readStored(config.storagePrefix, "systemPrompt", config.systemPrompt)
      },
      session: storedThread?.session || {
        id: nextSessionId(),
        startedAt: new Date().toISOString()
      },
      messages:
        storedThread?.messages || [
          createMessage("assistant", initialAssistantText, {
            initial: true,
            label: config.assistantName
          })
        ],
      busy: false,
      settingsOpen: false,
      status: ""
    };

    function persistThread() {
      writeThread(config.storagePrefix, {
        session: state.session,
        messages: state.messages.map((message) => ({
          role: message.role,
          content: message.content,
          createdAt: message.createdAt,
          initial: Boolean(message.initial),
          model: message.model || "",
          lane: message.lane || "",
          label: message.label || ""
        }))
      });
    }

    function getCompareModels() {
      return normalizeModelList(state.settings.compareModelsText).filter(
        (modelId) => modelId !== state.settings.model.trim()
      );
    }

    function getUserMessageBefore(index) {
      for (let i = index - 1; i >= 0; i -= 1) {
        if (state.messages[i] && state.messages[i].role === "user") {
          return state.messages[i].content;
        }
      }
      return "";
    }

    function saveSettings() {
      writeStored(config.storagePrefix, "token", state.settings.token);
      writeStored(config.storagePrefix, "model", state.settings.model);
      writeStored(config.storagePrefix, "compareModels", state.settings.compareModelsText);
      writeStored(config.storagePrefix, "proxy", state.settings.proxyEndpoint);
      writeStored(config.storagePrefix, "apiKey", state.settings.apiKey);
      writeStored(config.storagePrefix, "systemPrompt", state.settings.systemPrompt);
    }

    function buildThreadBundle() {
      return {
        session: state.session,
        exportedAt: new Date().toISOString(),
        title: config.title,
        subtitle: config.subtitle,
        assistantName: config.assistantName,
        primaryModel: state.settings.model,
        compareModels: getCompareModels(),
        proxyEndpoint: state.settings.proxyEndpoint,
        systemPrompt: state.settings.systemPrompt,
        source: config.exportSource,
        messages: state.messages
      };
    }

    function buildSftRows() {
      const compareModels = getCompareModels();
      return state.messages.flatMap((message, index) => {
        if (message.role !== "assistant" || message.initial || message.lane === "error") return [];
        const prompt = getUserMessageBefore(index);
        if (!prompt) return [];
        return [
          {
            instruction: "",
            input: prompt,
            output: message.content,
            source: config.exportSource,
            model: message.model || state.settings.model,
            lane: message.lane || "primary",
            timestamp: message.createdAt,
            session_id: state.session.id,
            title: config.title,
            metadata: JSON.stringify({
              assistant_name: config.assistantName,
              compare_models: compareModels,
              proxy_backed: Boolean(state.settings.proxyEndpoint.trim()),
              system_prompt: state.settings.systemPrompt
            })
          }
        ];
      });
    }

    function exportThreadBundle() {
      const bundle = buildThreadBundle();
      downloadFile(
        `scbe-hf-thread-${state.session.id}.json`,
        JSON.stringify(bundle, null, 2),
        "application/json"
      );
      state.status = `Exported thread bundle for ${state.session.id}.`;
      render();
    }

    function exportSftRows() {
      const rows = buildSftRows();
      downloadFile(
        `scbe-hf-sft-${state.session.id}.jsonl`,
        rows.map((row) => JSON.stringify(row)).join("\n"),
        "application/jsonl"
      );
      state.status = rows.length ? `Exported ${rows.length} SFT rows.` : "No assistant replies yet.";
      render();
    }

    function exportFeedback() {
      const records = readFeedback(config.storagePrefix);
      const lines = records.map((record) => JSON.stringify(record)).join("\n");
      downloadFile(
        `scbe-hf-feedback-${new Date().toISOString().replace(/[:.]/g, "-")}.jsonl`,
        lines || "",
        "application/jsonl"
      );
      state.status = records.length ? `Exported ${records.length} feedback records.` : "No feedback records yet.";
      render();
    }

    function pushFeedback(index, rating) {
      const message = state.messages[index];
      if (!message || message.role !== "assistant") return;
      const records = readFeedback(config.storagePrefix);
      records.push({
        timestamp: new Date().toISOString(),
        model: message.model || state.settings.model,
        lane: message.lane || "primary",
        rating,
        prompt: getUserMessageBefore(index),
        response: message.content
      });
      writeFeedback(config.storagePrefix, records);
      state.status = `Saved feedback: ${rating}.`;
      render();
    }

    async function sendPrompt(text) {
      const prompt = text.trim();
      if (!prompt || state.busy) return;

      state.messages.push(createMessage("user", prompt));
      state.busy = true;
      persistThread();
      const compareModels = getCompareModels();
      const targetModels = [state.settings.model.trim(), ...compareModels].filter(Boolean);
      state.status = `Waiting for ${targetModels.length} model${targetModels.length === 1 ? "" : "s"}...`;
      render();

      try {
        saveSettings();
        const requestMessages = [
          { role: "system", content: state.settings.systemPrompt.trim() },
          ...state.messages
            .filter((entry) => !entry.initial)
            .map((entry) => ({ role: entry.role, content: entry.content }))
        ];

        const replies = await Promise.all(
          targetModels.map(async (modelId, index) => {
            try {
              const reply = await requestCompletion(
                {
                  token: state.settings.token,
                  model: modelId,
                  endpoint: config.endpoint,
                  proxyEndpoint: state.settings.proxyEndpoint,
                  apiKey: state.settings.apiKey,
                  maxTokens: config.maxTokens,
                  temperature: config.temperature
                },
                requestMessages
              );
              return createMessage("assistant", reply, {
                model: modelId,
                lane: index === 0 ? "primary" : "compare",
                label: index === 0 ? config.assistantName : shortModelName(modelId)
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : "Unknown HF error.";
              return createMessage(
                "assistant",
                `Request failed.\n\n${message}\n\nIf this is a public page, use a proxy endpoint instead of a raw token.`,
                {
                  model: modelId,
                  lane: "error",
                  label: shortModelName(modelId)
                }
              );
            }
          })
        );

        state.messages.push(...replies);
        persistThread();
        state.status = `Collected ${replies.length} ${replies.length === 1 ? "reply" : "replies"}.`;
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown HF error.";
        state.messages.push(
          createMessage(
            "assistant",
            `Request failed.\n\n${message}\n\nIf this is a public page, use a proxy endpoint instead of a raw token.`,
            {
              model: state.settings.model.trim(),
              lane: "error",
              label: config.assistantName
            }
          )
        );
        persistThread();
        state.status = "HF request failed.";
      } finally {
        state.busy = false;
        render();
        const thread = root.querySelector(".polly-thread");
        if (thread) {
          thread.scrollTop = thread.scrollHeight;
        }
      }
    }

    persistThread();

    function render() {
      root.innerHTML = `
        <div class="polly-chat-root">
          <style>${buildStyles(config.compact)}</style>
          <div class="polly-shell">
            <section class="polly-context">
              <p class="polly-kicker">HF assistant</p>
              <h2 class="polly-title">${escapeHtml(config.title)}</h2>
              <p class="polly-subtitle">${escapeHtml(config.subtitle)}</p>

              <div class="polly-meta">
                <h3>Current route</h3>
                <p>${state.settings.proxyEndpoint.trim()
                  ? "Proxy endpoint active. Safe for public surfaces if the proxy keeps the token server-side."
                  : "Direct Hugging Face route active. Good for private device use. Do not expose the token on public pages."}</p>
              </div>

              <div class="polly-tips">
                <h3>Model facts</h3>
                <ul>
                  <li><code>scbe-pivot-qwen-0.5b</code> is the chat-capable default.</li>
                  <li><code>phdm-21d-embedding</code> stays embeddings-only.</li>
                  <li><code>spiralverse-ai-federated-v1</code> stays federated-learning oriented.</li>
                </ul>
              </div>
            </section>

            <section class="polly-main">
              <div class="polly-bar">
                <div class="polly-bar-title">
                  <strong>${escapeHtml(state.settings.model || config.model)}</strong>
                  <span>${state.settings.proxyEndpoint.trim() ? "Proxy-backed" : "Direct HF chat route"} • ${getCompareModels().length ? `${getCompareModels().length} compare lane(s)` : "Single-model lane"}</span>
                </div>
                <div class="polly-actions">
                  <button class="polly-button" type="button" data-action="toggle-settings">Settings</button>
                  <button class="polly-button" type="button" data-action="export-thread">Export thread</button>
                  <button class="polly-button" type="button" data-action="export-sft">Export SFT</button>
                  <button class="polly-button" type="button" data-action="export-feedback">Export feedback</button>
                </div>
              </div>

              <div class="polly-thread" id="pollyThread">
                ${state.messages
                  .map((message, index) => `
                    <article class="polly-message ${message.role}">
                      <div class="polly-message-header">
                        <span>${message.role === "assistant" ? escapeHtml(message.label || config.assistantName) : "You"}</span>
                        ${message.role === "assistant" && message.model ? `<span>${escapeHtml((message.lane || "primary").toUpperCase())} • ${escapeHtml(shortModelName(message.model))}</span>` : `<span>${message.createdAt ? escapeHtml(new Date(message.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })) : ""}</span>`}
                      </div>
                      <div>${escapeHtml(message.content)}</div>
                      ${message.role === "assistant" && !message.initial ? `
                        <div class="polly-feedback">
                          <button type="button" data-action="feedback-up" data-index="${index}">Useful</button>
                          <button type="button" data-action="feedback-down" data-index="${index}">Needs work</button>
                        </div>
                      ` : ""}
                    </article>
                  `)
                  .join("")}
              </div>

              ${config.suggestions.length ? `
                <div class="polly-suggestions">
                  ${config.suggestions
                    .map((suggestion) => `<button class="polly-chip" type="button" data-action="suggestion">${escapeHtml(suggestion)}</button>`)
                    .join("")}
                </div>
              ` : ""}

              <div class="polly-compose">
                <div class="polly-settings ${state.settingsOpen ? "open" : ""}">
                  <div class="polly-field">
                    <label for="pollyToken">HF token</label>
                    <input id="pollyToken" type="password" value="${escapeHtml(state.settings.token)}" placeholder="hf_xxx for private device use">
                  </div>
                  <div class="polly-field">
                    <label for="pollyProxy">Proxy endpoint</label>
                    <input id="pollyProxy" type="text" value="${escapeHtml(state.settings.proxyEndpoint)}" placeholder="https://your-domain/api/hf-chat">
                  </div>
                  <div class="polly-field">
                    <label for="pollyApiKey">Proxy API key</label>
                    <input id="pollyApiKey" type="password" value="${escapeHtml(state.settings.apiKey)}" placeholder="SCBE_api_key for private/operator use">
                  </div>
                  <div class="polly-field">
                    <label for="pollyModel">Model</label>
                    <input id="pollyModel" type="text" value="${escapeHtml(state.settings.model)}" placeholder="issdandavis/scbe-pivot-qwen-0.5b">
                  </div>
                  <div class="polly-field">
                    <label for="pollyCompareModels">Compare models</label>
                    <input id="pollyCompareModels" type="text" value="${escapeHtml(state.settings.compareModelsText)}" placeholder="meta-llama/Llama-3.3-70B-Instruct, Qwen/QwQ-32B">
                  </div>
                  <div class="polly-field">
                    <label for="pollySystemPrompt">System prompt</label>
                    <textarea id="pollySystemPrompt" rows="4" placeholder="Assistant behavior">${escapeHtml(state.settings.systemPrompt)}</textarea>
                  </div>
                  <div class="polly-footer-note">
                    For public pages, prefer a proxy endpoint and leave the raw HF token out of the browser. If the proxy is protected, add an SCBE API key here for operator or other-AI access. Thread export saves the raw conversation bundle; SFT export turns assistant replies into training rows.
                  </div>
                </div>

                <textarea class="polly-textarea" id="pollyComposer" placeholder="Ask Polly something concrete.">${state.busy ? "" : ""}</textarea>

                <div class="polly-compose-row">
                  <div class="polly-status">${escapeHtml(state.status)}</div>
                  <div class="polly-actions">
                    <button class="polly-button" type="button" data-action="clear-thread">Clear</button>
                    <button class="polly-button primary" type="button" data-action="send"${state.busy ? " disabled" : ""}>${state.busy ? "Thinking..." : "Send"}</button>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      `;

      const composer = root.querySelector("#pollyComposer");
      if (composer instanceof HTMLTextAreaElement) {
        composer.addEventListener("keydown", (event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendPrompt(composer.value);
            composer.value = "";
          }
        });
      }

      root.querySelectorAll("[data-action='suggestion']").forEach((button) => {
        button.addEventListener("click", () => {
          if (composer instanceof HTMLTextAreaElement) {
            composer.value = button.textContent || "";
            composer.focus();
          }
        });
      });

      root.querySelectorAll("[data-action='feedback-up']").forEach((button) => {
        button.addEventListener("click", () => {
          pushFeedback(Number(button.getAttribute("data-index")), "up");
        });
      });

      root.querySelectorAll("[data-action='feedback-down']").forEach((button) => {
        button.addEventListener("click", () => {
          pushFeedback(Number(button.getAttribute("data-index")), "down");
        });
      });

      const toggle = root.querySelector("[data-action='toggle-settings']");
      if (toggle) {
        toggle.addEventListener("click", () => {
          state.settingsOpen = !state.settingsOpen;
          render();
        });
      }

      const exporter = root.querySelector("[data-action='export-feedback']");
      if (exporter) {
        exporter.addEventListener("click", exportFeedback);
      }

      const threadExporter = root.querySelector("[data-action='export-thread']");
      if (threadExporter) {
        threadExporter.addEventListener("click", exportThreadBundle);
      }

      const sftExporter = root.querySelector("[data-action='export-sft']");
      if (sftExporter) {
        sftExporter.addEventListener("click", exportSftRows);
      }

      const sendButton = root.querySelector("[data-action='send']");
      if (sendButton) {
        sendButton.addEventListener("click", () => {
          if (!(composer instanceof HTMLTextAreaElement)) return;
          sendPrompt(composer.value);
          composer.value = "";
        });
      }

      const clearButton = root.querySelector("[data-action='clear-thread']");
      if (clearButton) {
        clearButton.addEventListener("click", () => {
          state.session = {
            id: nextSessionId(),
            startedAt: new Date().toISOString()
          };
          state.messages = [
            createMessage("assistant", initialAssistantText, {
              initial: true,
              label: config.assistantName
            })
          ];
          persistThread();
          state.status = "Thread cleared.";
          render();
        });
      }

      const tokenField = root.querySelector("#pollyToken");
      if (tokenField instanceof HTMLInputElement) {
        tokenField.addEventListener("change", () => {
          state.settings.token = tokenField.value;
          saveSettings();
        });
      }

      const proxyField = root.querySelector("#pollyProxy");
      if (proxyField instanceof HTMLInputElement) {
        proxyField.addEventListener("change", () => {
          state.settings.proxyEndpoint = proxyField.value;
          saveSettings();
        });
      }

      const apiKeyField = root.querySelector("#pollyApiKey");
      if (apiKeyField instanceof HTMLInputElement) {
        apiKeyField.addEventListener("change", () => {
          state.settings.apiKey = apiKeyField.value;
          saveSettings();
        });
      }

      const modelField = root.querySelector("#pollyModel");
      if (modelField instanceof HTMLInputElement) {
        modelField.addEventListener("change", () => {
          state.settings.model = modelField.value;
          saveSettings();
        });
      }

      const compareModelsField = root.querySelector("#pollyCompareModels");
      if (compareModelsField instanceof HTMLInputElement) {
        compareModelsField.addEventListener("change", () => {
          state.settings.compareModelsText = compareModelsField.value;
          saveSettings();
        });
      }

      const systemPromptField = root.querySelector("#pollySystemPrompt");
      if (systemPromptField instanceof HTMLTextAreaElement) {
        systemPromptField.addEventListener("change", () => {
          state.settings.systemPrompt = systemPromptField.value;
          saveSettings();
        });
      }
    }

    render();
  }

  window.PollyHFChat = {
    mount,
    requestCompletion
  };
})();
