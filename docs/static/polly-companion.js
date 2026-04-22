(function () {
  const DEFAULT_API_BASE = window.POLLY_API_BASE || localStorage.getItem("pollyApiBase") || "";
  const CORPUS_URL = (window.POLLY_CORPUS_URL || "chatbot-corpus.json");
  const STARTERS = [
    "What does SCBE actually improve in model training?",
    "Explain the hyperbolic cost wall in plain English.",
    "What shipped in April 2026?",
    "/nav milestones",
    "/search hyperbolic geometry AI safety",
    "/help",
  ];

  let CORPUS_CACHE = null;
  let CORPUS_FETCH_ATTEMPTED = false;

  const STOPWORDS = new Set([
    "a","an","and","are","as","at","be","but","by","for","from","how","i",
    "if","in","is","it","its","of","on","or","that","the","their","there",
    "these","this","to","was","were","what","when","where","which","who",
    "why","will","with","you","your","about","do","does","can","could",
    "should","would","me","my","we","our","us",
  ]);

  function tokenize(text) {
    return String(text || "")
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, " ")
      .split(/\s+/)
      .filter((t) => t && t.length > 1 && !STOPWORDS.has(t));
  }

  async function loadCorpus() {
    if (CORPUS_CACHE) return CORPUS_CACHE;
    if (CORPUS_FETCH_ATTEMPTED) return null;
    CORPUS_FETCH_ATTEMPTED = true;
    try {
      const res = await fetch(CORPUS_URL, { cache: "force-cache" });
      if (!res.ok) return null;
      const data = await res.json();
      if (!data || !Array.isArray(data.passages)) return null;
      CORPUS_CACHE = data.passages.map((p) => ({
        ...p,
        _tokens: new Set(tokenize(`${p.title || ""} ${(p.tags || []).join(" ")} ${p.excerpt || ""}`)),
      }));
      return CORPUS_CACHE;
    } catch (_err) {
      return null;
    }
  }

  function scoreCorpus(query, passages) {
    const qTokens = tokenize(query);
    if (!qTokens.length) return [];
    return passages
      .map((p) => {
        let hits = 0;
        for (const t of qTokens) if (p._tokens.has(t)) hits += 1;
        const titleBonus = qTokens.some((t) => (p.title || "").toLowerCase().includes(t)) ? 1 : 0;
        const tagBonus = qTokens.some((t) =>
          (p.tags || []).some((tag) => tag.toLowerCase().includes(t))
        )
          ? 1
          : 0;
        return { passage: p, score: hits + titleBonus + tagBonus };
      })
      .filter((s) => s.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 3);
  }

  async function offlineAnswer(query) {
    const passages = await loadCorpus();
    if (!passages || !passages.length) return null;
    const top = scoreCorpus(query, passages);
    if (!top.length) return null;
    const sources = top.map(({ passage }) => ({
      title: passage.title,
      path: passage.path,
      excerpt: passage.excerpt,
    }));
    const body =
      "I am running in offline mode (no backend reachable), so here are the closest passages from the curated docs corpus:\n\n" +
      top
        .map(({ passage }, i) => `**${i + 1}. ${passage.title}**\n${passage.excerpt}`)
        .join("\n\n");
    return { body, sources, matchCount: top.length };
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;");
  }

  function markdownToHtml(text) {
    const safe = escapeHtml(text);
    return safe
      .split(/\n{2,}/)
      .map((block) => `<p>${block.replace(/\n/g, "<br>")}</p>`)
      .join("");
  }

  function apiBase() {
    const raw = window.POLLY_API_BASE || localStorage.getItem("pollyApiBase") || DEFAULT_API_BASE || "";
    return raw.replace(/\/+$/, "");
  }

  function apiUrl(path) {
    const base = apiBase();
    return base ? `${base}${path}` : path;
  }

  function chip(label, state) {
    return `<span class="polly-chip" data-state="${escapeHtml(state)}">${escapeHtml(label)}</span>`;
  }

  function profileState(name) {
    if (name === "coding") return "science";
    if (name === "tokenizer") return "science";
    if (name === "geoseal") return "trusted";
    if (name === "memory") return "provisional";
    if (name === "arc_solver") return "science";
    return "science";
  }

  function createShell(mode) {
    const shell = document.createElement("section");
    shell.className = mode === "page" ? "polly-shell polly-page" : "polly-shell";
    shell.dataset.open = mode === "page" ? "true" : "false";
    shell.dataset.settings = "false";

    if (mode === "page") {
      shell.innerHTML = `
        <div class="polly-page-shell">
          <div class="polly-page-grid">
            <aside class="polly-page-card">
              <div class="polly-title">Polly Chat</div>
              <p class="polly-subtitle">
                Polly routes questions between <strong>lore canon</strong>, <strong>SCBE science</strong>, and the
                <strong>SCBE coding spine</strong>.
                Ask about AetherMoore story world, or ask about the governed AI stack, hyperbolic math,
                demos, models, GitHub-backed proof, or coding through Sacred Tongues and shared IR.
              </p>
              <div class="polly-statusbar" data-role="statusbar"></div>
              <div class="polly-starters" data-role="starters"></div>
              <label class="polly-subtitle" style="display:block;margin-top:18px;">Backend URL</label>
              <input class="polly-config" data-role="config" placeholder="https://your-backend.example.com">
              <p class="polly-subtitle" style="margin-top:10px;">
                Leave blank to use the current host. For GitHub Pages, point this at the running AetherBrowser API.
              </p>
              <p class="polly-subtitle" style="margin-top:18px;">
                <a class="polly-link" href="index.html">Back to homepage</a>
              </p>
            </aside>
            <div class="polly-page-chat">
              ${panelMarkup(true)}
            </div>
          </div>
        </div>
      `;
      return shell;
    }

    shell.innerHTML = `
      <button class="polly-launcher" type="button" aria-label="Open Polly chat (Ctrl+/)" aria-expanded="false" title="Open Polly (Ctrl+/)">Polly</button>
      ${panelMarkup(false)}
    `;
    return shell;
  }

  function panelMarkup(isPage) {
    return `
      <div class="polly-panel" aria-live="polite">
        <div class="polly-header">
          <div class="polly-title-row">
            <div class="polly-title">Polly</div>
            ${
              isPage
                ? '<button class="polly-close" type="button" data-role="toggle-settings" aria-label="Toggle settings">&#9881;</button>'
                : '<div style="display:flex;gap:8px;align-items:center;"><button class="polly-close" type="button" data-role="toggle-settings" aria-label="Toggle settings">&#9881;</button><button class="polly-close" type="button" data-role="close" aria-label="Close Polly">&times;</button></div>'
            }
          </div>
          <div class="polly-subtitle">One assistant, three lanes: lore, science, and SCBE coding.</div>
        </div>
        <div class="polly-statusbar" data-role="statusbar"></div>
        <div class="polly-settings" data-role="settings">
          <label class="polly-subtitle" style="display:block;">Backend URL</label>
          <input class="polly-config" data-role="config" placeholder="https://your-backend.example.com">
        </div>
        <div class="polly-thread" data-role="thread"></div>
        <div class="polly-starters" data-role="starters"></div>
        <div class="polly-composer">
          <textarea class="polly-input" data-role="input" aria-label="Message Polly. Use /help for commands. Enter to send, Shift+Enter for newline." placeholder="Ask lore, SCBE science, coding, or /help for commands."></textarea>
          <div class="polly-actions">
            <div class="polly-hint">Shift+Enter for a new line.</div>
            <button class="polly-send" data-role="send" type="button" aria-label="Send message">Send</button>
          </div>
        </div>
      </div>
    `;
  }

  function addMessage(thread, role, html, metaHtml) {
    const item = document.createElement("article");
    item.className = `polly-msg ${role}`;
    item.innerHTML = `${metaHtml ? `<div class="polly-msg-meta">${metaHtml}</div>` : ""}${html}`;
    thread.appendChild(item);
    thread.scrollTop = thread.scrollHeight;
  }

  function renderSources(sources) {
    if (!Array.isArray(sources) || !sources.length) {
      return "";
    }
    const items = sources.slice(0, 3).map((source, index) => {
      const href = source.public_url || "";
      const title = source.title || `Source ${index + 1}`;
      const path = source.path || "";
      const excerpt = source.excerpt || "";
      const titleHtml = href
        ? `<a href="${escapeHtml(href)}">${escapeHtml(title)}</a>`
        : `<strong>${escapeHtml(title)}</strong>`;
      return `
        <div class="polly-source">
          ${titleHtml}
          <small>${escapeHtml(path)}</small>
          <small>${escapeHtml(excerpt)}</small>
        </div>
      `;
    });
    return `<div class="polly-sources">${items.join("")}</div>`;
  }

  async function loadStatus(shell) {
    const bar = shell.querySelectorAll('[data-role="statusbar"]');
    const configInputs = shell.querySelectorAll('[data-role="config"]');
    configInputs.forEach((input) => {
      input.value = apiBase();
      input.addEventListener("change", () => {
        const next = input.value.trim();
        if (next) {
          localStorage.setItem("pollyApiBase", next);
        } else {
          localStorage.removeItem("pollyApiBase");
        }
        loadStatus(shell);
      });
    });

    if (!apiBase()) {
      const passages = await loadCorpus();
      const count = passages ? passages.length : 0;
      bar.forEach((node) => {
        node.innerHTML = `${chip("Offline mode", "offline")}${chip(`Corpus ${count} passages`, "science")}`;
      });
      return;
    }

    try {
      const response = await fetch(apiUrl("/v1/spaceport/status"));
      if (!response.ok) throw new Error(`status ${response.status}`);
      const data = await response.json();
      const repoLabel = data?.repo?.connected ? `GitHub linked` : "GitHub offline";
      const repoState = data?.repo?.connected ? "online" : "offline";
      const ollamaState = data?.backends?.ollama?.connected ? "online" : "offline";
      const hfState = data?.backends?.huggingface?.connected ? "online" : "offline";
      const ragState = data?.backends?.rag?.enabled ? "online" : "offline";
      const html = [
        chip(repoLabel, repoState),
        chip(`Ollama ${data?.backends?.ollama?.model || "offline"}`, ollamaState),
        chip(`HF ${data?.backends?.huggingface?.model || "offline"}`, hfState),
        chip(`RAG ${data?.backends?.rag?.chunk_count || 0} chunks`, ragState),
        ...(Array.isArray(data?.backends?.rag?.topics)
          ? data.backends.rag.topics.slice(0, 2).map((topic) => chip(topic.name, profileState(topic.name)))
          : []),
      ].join("");
      bar.forEach((node) => {
        node.innerHTML = html;
      });
    } catch (_err) {
      const passages = await loadCorpus();
      const count = passages ? passages.length : 0;
      bar.forEach((node) => {
        node.innerHTML = `${chip("Backend unreachable", "offline")}${chip(`Offline corpus ${count}`, "science")}`;
      });
    }
  }

  function mountStarters(shell, thread, input, send) {
    shell.querySelectorAll('[data-role="starters"]').forEach((container) => {
      container.innerHTML = STARTERS.map((text) => `<button class="polly-starter" type="button">${escapeHtml(text)}</button>`).join("");
      container.querySelectorAll(".polly-starter").forEach((button) => {
        button.addEventListener("click", () => {
          input.value = button.textContent || "";
          send();
        });
      });
    });

    addMessage(
      thread,
      "system",
      "<p>Ask about the AetherMoore story world, technical questions about SCBE training and governance, or ask Polly to teach coding through Sacred Tongues, language routing, and shared IR.</p>",
      `${chip("Lore", "lore")}${chip("Science", "science")}${chip("Coding", "science")}`
    );
  }

  const NAV_MAP = {
    top: "offer",
    home: "offer",
    offer: "offer",
    hero: "offer",
    "governance demo": "governance-demo",
    demo: "governance-demo",
    demos: "governance-demo",
    integrations: "integration-stack",
    "integration stack": "integration-stack",
    milestones: "recent-milestones",
    "recent milestones": "recent-milestones",
    recent: "recent-milestones",
    updates: "recent-milestones",
    "news": "recent-milestones",
    paths: "choose-path",
    "choose path": "choose-path",
    "choose your path": "choose-path",
    training: "dual-layer-training",
    "dual layer": "dual-layer-training",
    "dual-layer training": "dual-layer-training",
    audience: "who-this-is-for",
    "who is this for": "who-this-is-for",
    "who this is for": "who-this-is-for",
    expectations: "buyer-expectations",
    "buyer expectations": "buyer-expectations",
    includes: "includes",
    "what's included": "includes",
    "whats included": "includes",
    story: "story",
    lore: "story",
    vault: "training-vault",
    "training vault": "training-vault",
    watch: "watch",
    videos: "watch",
    "field notes": "field-notes",
    notes: "field-notes",
    formula: "formula-evolution",
    formulas: "formula-evolution",
    math: "formula-evolution",
    "formula evolution": "formula-evolution",
    fit: "fit",
    proof: "proof",
    delivery: "delivery",
    faq: "faq",
    questions: "faq",
    "open source": "open-source-tools",
    "open-source tools": "open-source-tools",
    tools: "open-source-tools",
    benchmark: "benchmark",
    benchmarks: "benchmark",
  };

  function resolveNavTarget(raw) {
    const key = String(raw || "").toLowerCase().trim();
    if (!key) return null;
    if (NAV_MAP[key]) return NAV_MAP[key];
    if (document.getElementById(key)) return key;
    for (const alias of Object.keys(NAV_MAP)) {
      if (key.includes(alias)) return NAV_MAP[alias];
    }
    return null;
  }

  function parseCommand(message) {
    const trimmed = String(message || "").trim();
    if (!trimmed) return null;
    if (trimmed.startsWith("/")) {
      const match = trimmed.match(/^\/(\w+)(?:\s+(.+))?$/);
      if (!match) return null;
      const verb = match[1].toLowerCase();
      const rest = (match[2] || "").trim();
      if (verb === "help" || verb === "h") return { type: "help" };
      if (verb === "nav" || verb === "go" || verb === "goto") return { type: "nav", query: rest };
      if (verb === "search" || verb === "web" || verb === "lookup") return { type: "search", query: rest };
      if (verb === "sections" || verb === "list") return { type: "sections" };
      return null;
    }
    const lower = trimmed.toLowerCase();
    const navIntent = lower.match(/^(?:take me to|go to|jump to|scroll to|show me|open)\s+(?:the\s+)?(.+?)\s*(?:section|part|page)?\s*[?!.]*$/);
    if (navIntent) return { type: "nav", query: navIntent[1] };
    const searchIntent = lower.match(/^(?:search(?:\s+(?:for|the\s+web\s+for))?|look\s+up|web\s+search(?:\s+for)?|find\s+(?:me\s+)?(?:info\s+on\s+)?)\s+(.+?)\s*[?!.]*$/);
    if (searchIntent) return { type: "search", query: searchIntent[1] };
    return null;
  }

  function listSectionsHtml() {
    const seen = new Set();
    const rows = [];
    for (const [alias, id] of Object.entries(NAV_MAP)) {
      if (seen.has(id)) continue;
      seen.add(id);
      rows.push(`<li><code>/nav ${escapeHtml(alias)}</code> &rarr; <code>#${escapeHtml(id)}</code></li>`);
    }
    return `<p>Jumpable sections:</p><ul class="polly-list">${rows.join("")}</ul>`;
  }

  function helpHtml() {
    return (
      "<p><strong>Polly commands:</strong></p>" +
      "<ul class=\"polly-list\">" +
      "<li><code>/nav &lt;section&gt;</code> &mdash; jump to a page section (e.g. <code>/nav milestones</code>)</li>" +
      "<li><code>/search &lt;query&gt;</code> &mdash; DuckDuckGo instant answer (free, no key)</li>" +
      "<li><code>/sections</code> &mdash; list all jumpable sections</li>" +
      "<li><code>/help</code> &mdash; this help</li>" +
      "</ul>" +
      "<p>Freeform also works: <em>take me to demos</em>, <em>search for hyperbolic geometry</em>.</p>"
    );
  }

  async function ddgSearch(query) {
    const url = `https://api.duckduckgo.com/?q=${encodeURIComponent(query)}&format=json&no_html=1&skip_disambig=1&t=aethermoore-polly`;
    try {
      const res = await fetch(url, { headers: { Accept: "application/json" } });
      if (!res.ok) return { ok: false, error: `DDG status ${res.status}` };
      const data = await res.json();
      return { ok: true, data };
    } catch (err) {
      return { ok: false, error: (err && err.message) || "network error" };
    }
  }

  function renderDdgResult(query, data) {
    const bits = [];
    if (data.AbstractText) {
      bits.push(`<p><strong>${escapeHtml(data.Heading || query)}</strong></p>`);
      bits.push(`<p>${escapeHtml(data.AbstractText)}</p>`);
      if (data.AbstractURL) {
        bits.push(
          `<p><a class="polly-link" href="${escapeHtml(data.AbstractURL)}" target="_blank" rel="noopener">` +
            `${escapeHtml(data.AbstractSource || "Source")}</a></p>`
        );
      }
    } else if (data.Answer) {
      bits.push(`<p><strong>${escapeHtml(data.Heading || query)}</strong></p>`);
      bits.push(`<p>${escapeHtml(data.Answer)}</p>`);
    } else if (data.Definition) {
      bits.push(`<p><strong>${escapeHtml(data.Heading || query)}</strong></p>`);
      bits.push(`<p>${escapeHtml(data.Definition)}</p>`);
      if (data.DefinitionURL) {
        bits.push(
          `<p><a class="polly-link" href="${escapeHtml(data.DefinitionURL)}" target="_blank" rel="noopener">` +
            `${escapeHtml(data.DefinitionSource || "Source")}</a></p>`
        );
      }
    }
    const related = Array.isArray(data.RelatedTopics) ? data.RelatedTopics.slice(0, 5) : [];
    if (related.length) {
      const items = related
        .map((t) => {
          if (!t) return "";
          if (t.Text && t.FirstURL) {
            return `<li><a class="polly-link" href="${escapeHtml(t.FirstURL)}" target="_blank" rel="noopener">${escapeHtml(t.Text)}</a></li>`;
          }
          if (t.Name && Array.isArray(t.Topics)) {
            return `<li><em>${escapeHtml(t.Name)}</em></li>`;
          }
          return "";
        })
        .filter(Boolean)
        .join("");
      if (items) bits.push(`<p><strong>Related:</strong></p><ul class="polly-list">${items}</ul>`);
    }
    if (!bits.length) {
      bits.push(
        `<p>DuckDuckGo had no instant answer for <em>${escapeHtml(query)}</em>. ` +
          `<a class="polly-link" href="https://duckduckgo.com/?q=${encodeURIComponent(query)}" target="_blank" rel="noopener">Open full results</a>.</p>`
      );
    }
    return bits.join("");
  }

  function attach(shell) {
    const thread = shell.querySelector('[data-role="thread"]');
    const input = shell.querySelector('[data-role="input"]');
    const sendBtn = shell.querySelector('[data-role="send"]');
    const launcher = shell.querySelector(".polly-launcher");
    const closeBtn = shell.querySelector('[data-role="close"]');
    const settingsBtn = shell.querySelector('[data-role="toggle-settings"]');

    const renderOffline = async (message) => {
      const offline = await offlineAnswer(message);
      if (!offline) {
        addMessage(
          thread,
          "assistant",
          `<p>Backend is unreachable and no offline corpus entries matched your question.</p><p>Try a topic like <em>harmonic wall</em>, <em>Sacred Tongues</em>, <em>MATHBAC</em>, or <em>SAM.gov</em>, or set the backend URL in settings.</p>`,
          chip("Offline", "offline")
        );
        return;
      }
      addMessage(
        thread,
        "assistant",
        `${markdownToHtml(offline.body)}${renderSources(offline.sources)}`,
        `${chip("Offline corpus", "offline")}${chip(`${offline.matchCount} passages`, "science")}`
      );
    };

    const runNav = (rawQuery) => {
      const target = resolveNavTarget(rawQuery);
      if (!target) {
        addMessage(
          thread,
          "assistant",
          `<p>I could not resolve <em>${escapeHtml(rawQuery)}</em> to a section. Try <code>/sections</code> to see what is jumpable.</p>`,
          chip("Nav", "offline")
        );
        return;
      }
      const el = document.getElementById(target);
      if (!el) {
        addMessage(
          thread,
          "assistant",
          `<p>Section <code>#${escapeHtml(target)}</code> is not on this page. Try from the homepage.</p>`,
          chip("Nav", "offline")
        );
        return;
      }
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      try {
        history.replaceState(null, "", `#${target}`);
      } catch (_) {
        window.location.hash = `#${target}`;
      }
      addMessage(
        thread,
        "assistant",
        `<p>Jumped to <code>#${escapeHtml(target)}</code>.</p>`,
        `${chip("Nav", "trusted")}${chip(target, "science")}`
      );
    };

    const runSearch = async (query) => {
      if (!query) {
        addMessage(thread, "assistant", "<p>Usage: <code>/search &lt;query&gt;</code></p>", chip("Search", "offline"));
        return;
      }
      addMessage(thread, "system", `<p>Searching DuckDuckGo for <em>${escapeHtml(query)}</em>...</p>`, chip("Web", "science"));
      const pending = thread.lastElementChild;
      const result = await ddgSearch(query);
      if (pending) pending.remove();
      if (!result.ok) {
        addMessage(
          thread,
          "assistant",
          `<p>DuckDuckGo request failed (${escapeHtml(result.error)}). ` +
            `<a class="polly-link" href="https://duckduckgo.com/?q=${encodeURIComponent(query)}" target="_blank" rel="noopener">Open full results</a>.</p>`,
          chip("Search", "offline")
        );
        return;
      }
      addMessage(thread, "assistant", renderDdgResult(query, result.data), `${chip("DuckDuckGo", "trusted")}${chip("instant", "science")}`);
    };

    const handleCommand = async (cmd) => {
      if (cmd.type === "help") {
        addMessage(thread, "assistant", helpHtml(), chip("Help", "science"));
        return true;
      }
      if (cmd.type === "sections") {
        addMessage(thread, "assistant", listSectionsHtml(), chip("Sections", "science"));
        return true;
      }
      if (cmd.type === "nav") {
        runNav(cmd.query);
        return true;
      }
      if (cmd.type === "search") {
        await runSearch(cmd.query);
        return true;
      }
      return false;
    };

    const submit = async () => {
      const message = input.value.trim();
      if (!message) return;
      input.value = "";
      sendBtn.disabled = true;
      addMessage(thread, "user", markdownToHtml(message));

      const cmd = parseCommand(message);
      if (cmd) {
        try {
          await handleCommand(cmd);
        } finally {
          sendBtn.disabled = false;
        }
        return;
      }

      addMessage(thread, "system", "<p>Routing question...</p>", chip("Thinking", "science"));
      const thinkingNode = thread.lastElementChild;

      const base = apiBase();
      if (!base) {
        if (thinkingNode) thinkingNode.remove();
        await renderOffline(message);
        sendBtn.disabled = false;
        return;
      }

      try {
        const response = await fetch(apiUrl("/v1/chat"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message,
            tentacle: "ollama",
            mode: "public-site",
            context: [
              { role: "system", content: `Page context: ${document.title}` },
              { role: "system", content: `Page URL: ${window.location.pathname}` },
            ],
          }),
        });
        if (!response.ok) throw new Error(`backend status ${response.status}`);
        const data = await response.json();
        if (thinkingNode) thinkingNode.remove();

        const domain = data.domain || "science";
        const domainLabel = domain === "hybrid" ? "Lore + Science" : domain === "lore" ? "Lore" : "Science";
        const codingMeta = [];
        if (data.coding_spine) {
          if (data.coding_spine.tongue) codingMeta.push(chip(data.coding_spine.tongue, "science"));
          if (data.coding_spine.language) codingMeta.push(chip(data.coding_spine.language, "science"));
        }
        const meta = [
          chip(domainLabel, domain),
          chip(data.model || data.tentacle || "assistant", data.response ? "online" : "offline"),
          ...(Array.isArray(data.active_profiles)
            ? data.active_profiles.slice(0, 3).map((profile) => chip(profile, profileState(profile)))
            : []),
          ...codingMeta,
        ].join("");
        const body = markdownToHtml(data.response || data.detail || "No response received.");
        addMessage(thread, "assistant", `${body}${renderSources(data.sources)}`, meta);
      } catch (_error) {
        if (thinkingNode) thinkingNode.remove();
        await renderOffline(message);
      } finally {
        sendBtn.disabled = false;
      }
    };

    mountStarters(shell, thread, input, submit);
    loadStatus(shell);
    setInterval(() => loadStatus(shell), 20000);

    sendBtn.addEventListener("click", submit);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        submit();
      }
    });

    const setOpen = (open) => {
      shell.dataset.open = open ? "true" : "false";
      if (launcher) launcher.setAttribute("aria-expanded", open ? "true" : "false");
      if (open) {
        setTimeout(() => {
          try { input.focus(); } catch (_) { /* noop */ }
        }, 50);
      }
    };

    if (launcher) {
      launcher.addEventListener("click", () => {
        setOpen(shell.dataset.open !== "true");
      });
    }
    if (closeBtn) {
      closeBtn.addEventListener("click", () => setOpen(false));
    }
    if (settingsBtn) {
      settingsBtn.addEventListener("click", () => {
        shell.dataset.settings = shell.dataset.settings === "true" ? "false" : "true";
      });
    }

    document.addEventListener("keydown", (event) => {
      const isSlashToggle = (event.ctrlKey || event.metaKey) && event.key === "/";
      if (isSlashToggle) {
        event.preventDefault();
        setOpen(shell.dataset.open !== "true");
        return;
      }
      if (event.key === "Escape" && shell.dataset.open === "true") {
        const tag = (document.activeElement && document.activeElement.tagName) || "";
        if (tag === "TEXTAREA" || tag === "INPUT") {
          if (document.activeElement && document.activeElement.value) return;
        }
        setOpen(false);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    const mode = document.body.classList.contains("polly-chat-page") ? "page" : "widget";
    const shell = createShell(mode);
    if (mode === "page") {
      document.body.appendChild(shell);
    } else {
      document.body.appendChild(shell);
    }
    attach(shell);
  });
})();
