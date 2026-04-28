/**
 * Polly v2 sidebar — SCBE-AETHERMOORE
 *
 * Features:
 *  - Thinking mode toggle (uses Gemini on server when enabled)
 *  - Service status bar (/v1/polly/context)
 *  - Command auto-detection: search / email / slack / think
 *  - Local memory saved to localStorage
 *  - Training export (downloads conversation as JSONL)
 *
 * Uses CSS classes from polly-sidebar.css.
 * Mount: <script src="static/polly-sidebar.js" data-polly-api="https://api.aethermoore.com"></script>
 */
(function () {
  "use strict";

  // -------------------------------------------------------------------------
  // Config
  // -------------------------------------------------------------------------

  var scriptEl = document.currentScript;
  var DEFAULT_API = (scriptEl && scriptEl.dataset.pollyApi) ||
    window.POLLY_V2_API ||
    localStorage.getItem("pollyV2Api") ||
    "https://api.aethermoore.com";

  var MEMORY_KEY = "pollyV2Memory";
  var MAX_MEMORY = 100; // max stored turns
  var STATUS_REFRESH_MS = 30000; // 30-second service status poll interval

  // -------------------------------------------------------------------------
  // Utilities
  // -------------------------------------------------------------------------

  function esc(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function md(text) {
    var safe = esc(text);
    // bold
    safe = safe.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    // inline code
    safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
    // paragraphs
    return safe
      .split(/\n{2,}/)
      .map(function (block) { return "<p>" + block.replace(/\n/g, "<br>") + "</p>"; })
      .join("");
  }

  function apiUrl(path) {
    var base = (window.POLLY_V2_API || localStorage.getItem("pollyV2Api") || DEFAULT_API).replace(/\/+$/, "");
    return base + path;
  }

  // -------------------------------------------------------------------------
  // Memory
  // -------------------------------------------------------------------------

  function loadMemory() {
    try {
      return JSON.parse(localStorage.getItem(MEMORY_KEY) || "[]");
    } catch (_) {
      return [];
    }
  }

  function saveMemory(turns) {
    try {
      var trimmed = turns.slice(-MAX_MEMORY);
      localStorage.setItem(MEMORY_KEY, JSON.stringify(trimmed));
    } catch (_) { /* storage quota */ }
  }

  function appendMemory(role, content) {
    var turns = loadMemory();
    turns.push({ role: role, content: content, ts: Date.now() });
    saveMemory(turns);
  }

  function exportMemory() {
    var turns = loadMemory();
    if (!turns.length) { alert("No conversation memory to export."); return; }
    var lines = turns.map(function (t) { return JSON.stringify(t); }).join("\n");
    var blob = new Blob([lines], { type: "application/jsonl" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "polly-memory-" + Date.now() + ".jsonl";
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(url); a.remove(); }, 1000);
  }

  // -------------------------------------------------------------------------
  // DOM helpers
  // -------------------------------------------------------------------------

  function chip(label, state) {
    return '<span class="polly-chip" data-state="' + esc(state) + '">' + esc(label) + "</span>";
  }

  function addMsg(thread, role, html, metaHtml) {
    var el = document.createElement("article");
    el.className = "polly-msg " + role;
    el.innerHTML = (metaHtml ? '<div class="polly-msg-meta">' + metaHtml + "</div>" : "") + html;
    thread.appendChild(el);
    thread.scrollTop = thread.scrollHeight;
    return el;
  }

  // -------------------------------------------------------------------------
  // Status bar
  // -------------------------------------------------------------------------

  function refreshStatus(bar) {
    fetch(apiUrl("/v1/polly/context"), { method: "GET" })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (ctx) {
        var chips = [];
        chips.push(chip("Polly v2", "online"));
        chips.push(chip("Gemini " + (ctx.gemini ? "✓" : "—"), ctx.gemini ? "online" : "offline"));
        chips.push(chip("Tavily " + (ctx.tavily ? "✓" : "—"), ctx.tavily ? "online" : "offline"));
        chips.push(chip("Email " + (ctx.email ? "✓" : "—"), ctx.email ? "online" : "offline"));
        chips.push(chip("Slack " + (ctx.slack ? "✓" : "—"), ctx.slack ? "online" : "offline"));
        bar.innerHTML = chips.join("");
      })
      .catch(function () {
        bar.innerHTML = chip("Backend unreachable", "offline") + chip("Polly v2", "lore");
      });
  }

  // -------------------------------------------------------------------------
  // Command parsing
  // -------------------------------------------------------------------------

  /**
   * Detect structured commands.
   * Returns { type, ... } or null for freeform chat.
   */
  function parseCmd(message) {
    var t = String(message || "").trim();
    if (!t) return null;

    // slash commands
    if (t.charAt(0) === "/") {
      var m = t.match(/^\/(\w+)(?:\s+([\s\S]+))?$/);
      if (!m) return null;
      var verb = m[1].toLowerCase();
      var rest = (m[2] || "").trim();
      if (verb === "help") return { type: "help" };
      if (verb === "clear") return { type: "clear" };
      if (verb === "export") return { type: "export" };
      if (verb === "search") return { type: "search", query: rest };
      if (verb === "email") return parseEmailCmd(rest);
      if (verb === "slack") return { type: "slack", text: rest };
      if (verb === "think") return { type: "chat", message: rest, thinking: true };
      return null;
    }

    var lower = t.toLowerCase();

    // "search <query>"
    var sm = lower.match(/^(?:search(?:\s+(?:for|the\s+web\s+for))?|look\s+up|web\s+search(?:\s+for)?)\s+(.+?)\s*[?!.]*$/);
    if (sm) return { type: "search", query: sm[1] };

    // "email <to> subject: <s> body: <b>"
    var em = lower.match(/^email\s/);
    if (em) return parseEmailCmd(t.slice(6).trim());

    // "slack <message>"
    var slm = lower.match(/^slack\s+(.+)$/);
    if (slm) return { type: "slack", text: t.slice(6).trim() };

    // "think about ..." or "think: ..."
    var thm = lower.match(/^think(?:\s+about|\s*:)\s+(.+)$/);
    if (thm) return { type: "chat", message: thm[1], thinking: true };

    return null;
  }

  function parseEmailCmd(raw) {
    // Format: <to> subject: <subject> body: <body>
    var toM = raw.match(/^([^\s]+)\s+subject:\s*(.*?)\s+body:\s*([\s\S]*)$/i);
    if (toM) {
      return { type: "email", to: toM[1], subject: toM[2].trim(), body: toM[3].trim() };
    }
    // Simpler: just an address + body
    var simpleM = raw.match(/^([^\s]+)\s+([\s\S]+)$/);
    if (simpleM) {
      return { type: "email", to: simpleM[1], subject: "Message from Polly", body: simpleM[2].trim() };
    }
    return null;
  }

  // -------------------------------------------------------------------------
  // Command handlers
  // -------------------------------------------------------------------------

  function helpHtml() {
    return (
      "<p><strong>Polly v2 commands:</strong></p>" +
      '<ul class="polly-list">' +
      "<li><code>search &lt;query&gt;</code> — web search via Tavily</li>" +
      "<li><code>email &lt;to&gt; subject: &lt;s&gt; body: &lt;b&gt;</code> — send email</li>" +
      "<li><code>slack &lt;message&gt;</code> — post Slack notification</li>" +
      "<li><code>think about &lt;question&gt;</code> — deep reasoning (Gemini)</li>" +
      "<li><code>/export</code> — download conversation as JSONL</li>" +
      "<li><code>/clear</code> — clear thread and memory</li>" +
      "<li><code>/help</code> — this help</li>" +
      "</ul>" +
      "<p>Or just ask naturally — Polly routes science, lore, pricing, support, and setup questions automatically.</p>"
    );
  }

  async function handleSearch(query, thread) {
    var pending = addMsg(thread, "system", "<p>Searching for <em>" + esc(query) + "</em>…</p>", chip("DuckDuckGo", "science"));
    try {
      // Try backend first
      var data = null;
      try {
        var resp = await fetch(apiUrl("/v1/polly/search"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: query }),
          signal: AbortSignal.timeout(5000),
        });
        if (resp.ok) data = await resp.json();
      } catch (_) {}

      // Fallback: DuckDuckGo API directly from browser
      if (!data || !data.results || !data.results.length) {
        var ddgResp = await fetch(SEARCH_PROXY, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: query }),
        });
        if (ddgResp.ok) {
          data = await ddgResp.json();
        }
      }

      if (pending) pending.remove();
      if (!data.results.length) {
        addMsg(thread, "assistant", "<p>No results for <em>" + esc(query) + "</em>. Try a broader search.</p>", chip("DuckDuckGo", "offline"));
        return;
      }
      var html = data.results.map(function (r) {
        var link = r.url
          ? '<a class="polly-link" href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(r.title || r.url) + "</a>"
          : "<strong>" + esc(r.title) + "</strong>";
        return '<div class="polly-source">' + link + "<small>" + esc(r.excerpt) + "</small></div>";
      }).join("");
      addMsg(thread, "assistant", '<div class="polly-sources">' + html + "</div>", chip(data.source || "DuckDuckGo", "online"));
    } catch (err) {
      if (pending) pending.remove();
      addMsg(thread, "assistant", "<p>Search failed: " + esc(String(err)) + "</p>", chip("Error", "offline"));
    }
  }

  async function handleEmail(cmd, thread) {
    if (!cmd || !cmd.to || !cmd.body) {
      addMsg(thread, "assistant",
        "<p>Email usage: <code>email &lt;to@address.com&gt; subject: &lt;subject&gt; body: &lt;message&gt;</code></p>",
        chip("Email", "offline")
      );
      return;
    }
    var pending = addMsg(thread, "system", "<p>Sending email to <em>" + esc(cmd.to) + "</em>…</p>", chip("Email", "science"));
    try {
      var resp = await fetch(apiUrl("/v1/polly/email"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to: cmd.to, subject: cmd.subject || "Message from Polly", body: cmd.body }),
      });
      if (pending) pending.remove();
      var data = await resp.json();
      if (data.ok) {
        addMsg(thread, "assistant", "<p>Email sent to <strong>" + esc(cmd.to) + "</strong>.</p>", chip("Email", "online"));
      } else {
        addMsg(thread, "assistant", "<p>Email failed: " + esc(data.error || "unknown error") + "</p>", chip("Email", "offline"));
      }
    } catch (err) {
      if (pending) pending.remove();
      addMsg(thread, "assistant", "<p>Email error: " + esc(String(err)) + "</p>", chip("Error", "offline"));
    }
  }

  async function handleSlack(text, thread) {
    if (!text) {
      addMsg(thread, "assistant", "<p>Slack usage: <code>slack &lt;message&gt;</code></p>", chip("Slack", "offline"));
      return;
    }
    var pending = addMsg(thread, "system", "<p>Posting to Slack…</p>", chip("Slack", "science"));
    try {
      var resp = await fetch(apiUrl("/v1/polly/slack"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text }),
      });
      if (pending) pending.remove();
      var data = await resp.json();
      if (data.ok) {
        addMsg(thread, "assistant", "<p>Slack notification sent.</p>", chip("Slack", "online"));
      } else {
        addMsg(thread, "assistant", "<p>Slack failed: " + esc(data.error || "unknown error") + "</p>", chip("Slack", "offline"));
      }
    } catch (err) {
      if (pending) pending.remove();
      addMsg(thread, "assistant", "<p>Slack error: " + esc(String(err)) + "</p>", chip("Error", "offline"));
    }
  }

  var HF_MODEL = "Qwen/Qwen2.5-72B-Instruct";
  var VERCEL_BASE = window.POLLY_VERCEL_BASE || "https://scbe-aethermoore.vercel.app";
  var CHAT_PROXY = VERCEL_BASE + "/api/agent/chat";
  var SEARCH_PROXY = VERCEL_BASE + "/api/agent/search";

  async function handleChat(message, thinking, thread) {
    var thinkingMode = thinking || false;
    var metaLabel = thinkingMode ? chip("Thinking…", "science") : chip("Routing…", "science");
    var pending = addMsg(thread, "system", "<p>Working on it…</p>", metaLabel);

    var history = loadMemory().slice(-6).map(function (t) {
      return { role: t.role === "polly" ? "assistant" : t.role, content: t.content };
    });

    // Try backend first (local server or Vercel)
    var answered = false;
    try {
      var resp = await fetch(apiUrl("/v1/polly/chat"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: message,
          thinking: thinkingMode,
          history: history,
          page_context: document.title + " — " + window.location.pathname,
        }),
        signal: AbortSignal.timeout(8000),
      });
      if (resp.ok) {
        var data = await resp.json();
        if (pending) pending.remove();
        var routeMeta = [
          chip(data.route || "general", data.thinking ? "science" : "hybrid"),
          chip(data.model || "polly", data.thinking ? "online" : "lore"),
        ].join("");
        addMsg(thread, "assistant", md(data.response || "No response."), routeMeta);
        appendMemory("polly", data.response || "");
        answered = true;
      }
    } catch (_) {}

    if (answered) return;

    // Fallback: call HuggingFace directly from the browser (free, no API key needed for public models)
    try {
      if (pending) { pending.remove(); pending = null; }
      pending = addMsg(thread, "system", "<p>Calling Qwen 72B…</p>", chip("HuggingFace", "science"));

      var hfResp = await fetch(CHAT_PROXY, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message, history: history }),
      });

      if (pending) pending.remove();

      if (hfResp.ok) {
        var hfData = await hfResp.json();
        var text = hfData.text || "No response from model.";
        addMsg(thread, "assistant", md(text), chip("Qwen 72B", "online") + chip("HuggingFace", "science"));
        appendMemory("polly", text);
      } else {
        var errText = await hfResp.text();
        addMsg(thread, "assistant", "<p>AI is busy — free tier may be warming up. Try again in a moment.</p><p style='font-size:0.8rem;color:#8b949e;'>" + esc(errText.substring(0, 150)) + "</p>", chip("HuggingFace", "offline"));
      }
    } catch (err) {
      if (pending) pending.remove();
      addMsg(thread, "assistant", "<p>Could not reach AI. Check your internet connection.</p>", chip("Offline", "offline"));
    }
  }

  // -------------------------------------------------------------------------
  // Build HTML
  // -------------------------------------------------------------------------

  function buildShell() {
    var shell = document.createElement("section");
    shell.className = "polly-shell";
    shell.dataset.open = "false";
    shell.dataset.settings = "false";
    shell.innerHTML =
      '<button class="polly-launcher" type="button" aria-label="Open Polly (Ctrl+/)" aria-expanded="false">Polly</button>' +
      '<div class="polly-panel" aria-live="polite">' +
        '<div class="polly-header">' +
          '<div class="polly-title-row">' +
            '<div class="polly-title">Polly v2</div>' +
            '<div style="display:flex;gap:6px;align-items:center;">' +
              '<button class="polly-icon-btn" type="button" data-role="toggle-think" aria-label="Toggle thinking mode" title="Thinking mode (uses Gemini)">💡</button>' +
              '<button class="polly-icon-btn" type="button" data-role="toggle-settings" aria-label="Settings">&#9881;</button>' +
              '<button class="polly-close" type="button" data-role="close" aria-label="Close">&times;</button>' +
            "</div>" +
          "</div>" +
          '<div class="polly-subtitle" data-role="think-label">Chat · search · email · slack</div>' +
        "</div>" +
        '<div class="polly-statusbar" data-role="statusbar"></div>' +
        '<div class="polly-settings" data-role="settings">' +
          '<label class="polly-subtitle" style="display:block;">API Base URL</label>' +
          '<input class="polly-config" data-role="config" placeholder="https://api.aethermoore.com">' +
          '<button class="polly-starter" type="button" data-role="export-btn" style="margin-top:10px;">Export memory JSONL</button>' +
        "</div>" +
        '<div class="polly-thread" data-role="thread"></div>' +
        '<div class="polly-starters" data-role="starters"></div>' +
        '<div class="polly-composer">' +
          '<textarea class="polly-input" data-role="input" aria-label="Message Polly" placeholder="Ask anything, or: search &lt;q&gt;, email &lt;to&gt;, slack &lt;msg&gt;, think about &lt;q&gt;"></textarea>' +
          '<div class="polly-actions">' +
            '<div class="polly-hint" data-role="mode-hint">Shift+Enter for newline</div>' +
            '<button class="polly-send" data-role="send" type="button">Send</button>' +
          "</div>" +
        "</div>" +
      "</div>";
    return shell;
  }

  // -------------------------------------------------------------------------
  // Attach behaviour
  // -------------------------------------------------------------------------

  function attach(shell) {
    var panel = shell.querySelector(".polly-panel");
    var thread = shell.querySelector('[data-role="thread"]');
    var input = shell.querySelector('[data-role="input"]');
    var sendBtn = shell.querySelector('[data-role="send"]');
    var launcher = shell.querySelector(".polly-launcher");
    var closeBtn = shell.querySelector('[data-role="close"]');
    var settingsBtn = shell.querySelector('[data-role="toggle-settings"]');
    var thinkBtn = shell.querySelector('[data-role="toggle-think"]');
    var thinkLabel = shell.querySelector('[data-role="think-label"]');
    var modeHint = shell.querySelector('[data-role="mode-hint"]');
    var statusBar = shell.querySelector('[data-role="statusbar"]');
    var configInput = shell.querySelector('[data-role="config"]');
    var exportBtn = shell.querySelector('[data-role="export-btn"]');
    var startersContainer = shell.querySelector('[data-role="starters"]');

    var thinkingOn = false;

    // Starter prompts
    var STARTERS = [
      "What is the harmonic wall?",
      "search hyperbolic geometry AI safety",
      "How do I get started?",
      "think about the 14-layer pipeline",
      "/help",
    ];
    startersContainer.innerHTML = STARTERS.map(function (s) {
      return '<button class="polly-starter" type="button">' + esc(s) + "</button>";
    }).join("");
    startersContainer.querySelectorAll(".polly-starter").forEach(function (btn) {
      btn.addEventListener("click", function () {
        input.value = btn.textContent || "";
        submit();
      });
    });

    // Config input
    if (configInput) {
      configInput.value = localStorage.getItem("pollyV2Api") || DEFAULT_API;
      configInput.addEventListener("change", function () {
        var v = configInput.value.trim();
        if (v) { localStorage.setItem("pollyV2Api", v); }
        else { localStorage.removeItem("pollyV2Api"); }
        refreshStatus(statusBar);
      });
    }

    // Export button
    if (exportBtn) {
      exportBtn.addEventListener("click", exportMemory);
    }

    // Status bar
    refreshStatus(statusBar);
    var statusInterval = null;

    function startStatusPoll() {
      if (statusInterval) clearInterval(statusInterval);
      statusInterval = setInterval(function () { refreshStatus(statusBar); }, STATUS_REFRESH_MS);
    }
    startStatusPoll();

    // Welcome message
    addMsg(
      thread,
      "system",
      "<p>Polly v2 ready. Chat, search, send email, post to Slack, or enable Thinking mode for deep reasoning. Type <code>/help</code> for commands.</p>",
      chip("Polly v2", "lore")
    );

    // Thinking toggle
    if (thinkBtn) {
      thinkBtn.addEventListener("click", function () {
        thinkingOn = !thinkingOn;
        thinkBtn.style.opacity = thinkingOn ? "1" : "0.5";
        if (thinkLabel) {
          thinkLabel.textContent = thinkingOn
            ? "Thinking mode ON — step-by-step reasoning"
            : "Chat · search · email · slack";
        }
        if (modeHint) {
          modeHint.textContent = thinkingOn ? "Thinking mode active (Gemini)" : "Shift+Enter for newline";
        }
      });
      // Start dimmed
      thinkBtn.style.opacity = "0.5";
    }

    // Submit
    var submit = async function () {
      var message = input.value.trim();
      if (!message || sendBtn.disabled) return;
      input.value = "";
      sendBtn.disabled = true;

      addMsg(thread, "user", md(message));
      appendMemory("user", message);

      var cmd = parseCmd(message);
      if (cmd) {
        try {
          if (cmd.type === "help") {
            addMsg(thread, "assistant", helpHtml(), chip("Help", "science"));
          } else if (cmd.type === "clear") {
            thread.innerHTML = "";
            saveMemory([]);
            addMsg(thread, "system", "<p>Memory cleared.</p>", chip("Clear", "lore"));
          } else if (cmd.type === "export") {
            exportMemory();
          } else if (cmd.type === "search") {
            await handleSearch(cmd.query, thread);
          } else if (cmd.type === "email") {
            await handleEmail(cmd, thread);
          } else if (cmd.type === "slack") {
            await handleSlack(cmd.text, thread);
          } else if (cmd.type === "chat") {
            await handleChat(cmd.message, cmd.thinking, thread);
          } else {
            addMsg(thread, "assistant", "<p>Unknown command. Type <code>/help</code> for options.</p>", chip("Help", "offline"));
          }
        } finally {
          sendBtn.disabled = false;
        }
        return;
      }

      // Freeform → chat
      try {
        await handleChat(message, thinkingOn, thread);
      } finally {
        sendBtn.disabled = false;
      }
    };

    sendBtn.addEventListener("click", submit);
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submit();
      }
    });

    // Open/close
    var setOpen = function (open) {
      shell.dataset.open = open ? "true" : "false";
      if (launcher) launcher.setAttribute("aria-expanded", open ? "true" : "false");
      if (panel) panel.setAttribute("aria-hidden", open ? "false" : "true");
      if (open) {
        refreshStatus(statusBar);
        startStatusPoll();
        setTimeout(function () { try { input.focus(); } catch (_) {} }, 50);
      } else {
        if (statusInterval) { clearInterval(statusInterval); statusInterval = null; }
      }
    };

    if (launcher) launcher.addEventListener("click", function () { setOpen(shell.dataset.open !== "true"); });
    if (closeBtn) closeBtn.addEventListener("click", function () { setOpen(false); });

    if (settingsBtn) {
      settingsBtn.addEventListener("click", function () {
        shell.dataset.settings = shell.dataset.settings === "true" ? "false" : "true";
      });
    }

    document.addEventListener("keydown", function (e) {
      var isToggle = (e.ctrlKey || e.metaKey) && e.key === "/";
      if (isToggle) { e.preventDefault(); setOpen(shell.dataset.open !== "true"); return; }
      if (e.key === "Escape" && shell.dataset.open === "true") {
        var tag = (document.activeElement && document.activeElement.tagName) || "";
        if ((tag === "TEXTAREA" || tag === "INPUT") && document.activeElement.value) return;
        setOpen(false);
      }
    });
  }

  // -------------------------------------------------------------------------
  // Mount
  // -------------------------------------------------------------------------

  function mount() {
    if (document.body.dataset.pollyV2Mounted === "true") return;
    document.body.dataset.pollyV2Mounted = "true";
    var shell = buildShell();
    document.body.appendChild(shell);
    attach(shell);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
