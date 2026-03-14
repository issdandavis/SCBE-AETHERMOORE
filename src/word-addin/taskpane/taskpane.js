/* global Office, Word */

let ws = null;
let term = null;
let fitAddon = null;
let inputBuffer = "";
let isStreaming = false;
const DOC_CONTEXT_LIMIT = 8000;
const SESSION_KEY = "scbe-word-taskpane-session-id";
const PAD_SURFACE = "word-taskpane";
const PAD_MODE = "COMMS";
let sessionId = localStorage.getItem(SESSION_KEY) || "";
let currentZone = "HOT";

// ── Terminal Setup ──────────────────────────────────────────

function initTerminal() {
  term = new Terminal({
    theme: {
      background: "#1a1a2e",
      foreground: "#e0e0e0",
      cursor: "#e94560",
      cursorAccent: "#1a1a2e",
      selectionBackground: "#0f346080",
      black: "#1a1a2e",
      red: "#e94560",
      green: "#4ecca3",
      yellow: "#f5c542",
      blue: "#0f3460",
      magenta: "#c77dff",
      cyan: "#53d8fb",
      white: "#e0e0e0",
    },
    fontFamily: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
    fontSize: 13,
    lineHeight: 1.3,
    cursorBlink: true,
    cursorStyle: "bar",
    scrollback: 5000,
  });

  fitAddon = new FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  term.open(document.getElementById("terminal-container"));
  fitAddon.fit();

  // Handle resize
  new ResizeObserver(() => fitAddon && fitAddon.fit()).observe(
    document.getElementById("terminal-container")
  );

  // Welcome message
  term.writeln("\x1b[1;31m  SCBE Writer\x1b[0m — AI Terminal for Word");
  term.writeln("\x1b[90m  Highlight text in Word and ask for a rewrite to edit the live document.\x1b[0m");
  term.writeln("\x1b[90m  Use 'sync' to pull broader document context when you need whole-book help.\x1b[0m");
  term.writeln("");
  prompt();

  // Handle keyboard input
  term.onData((data) => {
    if (isStreaming) return;

    const code = data.charCodeAt(0);

    if (code === 13) {
      // Enter
      term.writeln("");
      if (inputBuffer.trim()) {
        sendMessage(inputBuffer.trim());
      } else {
        prompt();
      }
      inputBuffer = "";
    } else if (code === 127 || code === 8) {
      // Backspace
      if (inputBuffer.length > 0) {
        inputBuffer = inputBuffer.slice(0, -1);
        term.write("\b \b");
      }
    } else if (code === 3) {
      // Ctrl+C
      if (isStreaming) {
        isStreaming = false;
        term.writeln("\n\x1b[90m(interrupted)\x1b[0m");
        prompt();
      } else {
        inputBuffer = "";
        term.writeln("^C");
        prompt();
      }
    } else if (code >= 32) {
      // Printable
      inputBuffer += data;
      term.write(data);
    }
  });
}

function prompt() {
  term.write("\x1b[1;31m>\x1b[0m ");
}

// ── WebSocket ───────────────────────────────────────────────

function connectWS() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const url = new URL(`${proto}//${location.host}`);
  if (sessionId) {
    url.searchParams.set("session", sessionId);
  }
  url.searchParams.set("surface", PAD_SURFACE);
  url.searchParams.set("mode", PAD_MODE);
  ws = new WebSocket(url);

  ws.onopen = () => {
    setStatus("connected", "connected");
    ws.send(JSON.stringify({
      type: "hello",
      surface: PAD_SURFACE,
      mode: PAD_MODE,
    }));
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);

    if (msg.type === "session") {
      if (msg.session_id) {
        sessionId = msg.session_id;
        localStorage.setItem(SESSION_KEY, sessionId);
      }
      currentZone = msg.zone || currentZone;
      setStatus(`connected · ${currentZone.toLowerCase()}`, "connected");
      if (msg.resumed) {
        term.writeln(`\x1b[90m(resumed session ${sessionId})\x1b[0m`);
      }
    } else if (msg.type === "stream") {
      if (!isStreaming) {
        isStreaming = true;
      }
      term.write(msg.text);
    } else if (msg.type === "stream_end") {
      isStreaming = false;
      term.writeln("");
      term.writeln("");
      prompt();
    } else if (msg.type === "word_commands") {
      executeWordCommands(msg.commands);
    } else if (msg.type === "synced") {
      currentZone = msg.zone || currentZone;
      setStatus(`connected · ${currentZone.toLowerCase()}`, "connected");
    } else if (msg.type === "error") {
      term.writeln(`\n\x1b[31mError: ${msg.message}\x1b[0m`);
      isStreaming = false;
      prompt();
    } else if (msg.type === "cleared") {
      term.writeln("\x1b[90m(conversation cleared)\x1b[0m");
      prompt();
    } else if (msg.type === "zone_update") {
      currentZone = msg.zone || currentZone;
      setStatus(`connected · ${currentZone.toLowerCase()}`, "connected");
      term.writeln(`\x1b[90m(zone ${currentZone.toLowerCase()})\x1b[0m`);
    }
  };

  ws.onclose = () => {
    setStatus("disconnected", "");
    setTimeout(connectWS, 3000);
  };

  ws.onerror = () => {
    setStatus("bridge not running", "error");
  };
}

function setStatus(text, cls) {
  const el = document.getElementById("status-text");
  el.textContent = text;
  el.className = cls || "";
}

// ── Document Interaction ────────────────────────────────────

async function getDocumentText() {
  try {
    const result = await Word.run(async (context) => {
      const body = context.document.body;
      body.load("text");
      await context.sync();
      return body.text;
    });
    return result;
  } catch (err) {
    return `[Could not read document: ${err.message}]`;
  }
}

async function getSelectedText() {
  try {
    const result = await Word.run(async (context) => {
      const sel = context.document.getSelection();
      sel.load("text");
      await context.sync();
      return sel.text;
    });
    return result;
  } catch {
    return "";
  }
}

function setWordCount(docText) {
  const wordCount = docText.split(/\s+/).filter(Boolean).length;
  document.getElementById("word-count").textContent = `${wordCount.toLocaleString()} words`;
  return wordCount;
}

function truncateDocumentContext(docText) {
  if (docText.length <= DOC_CONTEXT_LIMIT) {
    return docText;
  }

  const edgeSize = Math.floor(DOC_CONTEXT_LIMIT / 2);
  return docText.slice(0, edgeSize) + "\n\n[...truncated...]\n\n" + docText.slice(-edgeSize);
}

function summarizeWordTarget(text) {
  return `${text || ""}`.replace(/\s+/g, " ").trim().slice(0, 40);
}

function logWordResult(kind, detail, color = "32") {
  term.writeln(`\x1b[${color}m  [${kind}: ${detail}]\x1b[0m`);
}

function hasTextPayload(cmd) {
  return typeof cmd?.text === "string";
}

function hasHtmlPayload(cmd) {
  return typeof cmd?.html === "string";
}

async function syncDocumentContext() {
  const docText = await getDocumentText();
  const wordCount = setWordCount(docText);

  if (!ws || ws.readyState !== WebSocket.OPEN) {
    term.writeln("\x1b[31mNot connected to bridge. Start the server.\x1b[0m");
    return false;
  }

  ws.send(JSON.stringify({
    type: "sync_context",
    documentContext: truncateDocumentContext(docText),
    surface: PAD_SURFACE,
    mode: PAD_MODE,
  }));

  term.writeln(`\x1b[90m  (synced ${wordCount.toLocaleString()} words from document)\x1b[0m`);
  return true;
}

async function executeWordCommands(commands) {
  for (const cmd of commands) {
    try {
      await Word.run(async (context) => {
        const body = context.document.body;
        const selection = context.document.getSelection();
        selection.load("text");
        await context.sync();

        if ((cmd.action === "replace_selection" || cmd.action === "replace_selection_text") && hasTextPayload(cmd)) {
          selection.insertText(cmd.text, Word.InsertLocation.replace);
          logWordResult("selection replaced", summarizeWordTarget(selection.text || cmd.text));
        } else if (cmd.action === "replace_selection_html" && hasHtmlPayload(cmd)) {
          selection.insertHtml(cmd.html, Word.InsertLocation.replace);
          logWordResult("selection formatted", "html");
        } else if ((cmd.action === "insert_after_selection" || cmd.action === "insert_after_selection_text") && hasTextPayload(cmd)) {
          selection.insertText(`\n${cmd.text}`, Word.InsertLocation.after);
          logWordResult("inserted after selection", summarizeWordTarget(cmd.text));
        } else if ((cmd.action === "insert_before_selection" || cmd.action === "insert_before_selection_text") && hasTextPayload(cmd)) {
          selection.insertText(`${cmd.text}\n`, Word.InsertLocation.before);
          logWordResult("inserted before selection", summarizeWordTarget(cmd.text));
        } else if (cmd.action === "insert_after_selection_html" && hasHtmlPayload(cmd)) {
          selection.insertHtml(cmd.html, Word.InsertLocation.after);
          logWordResult("inserted after selection", "html");
        } else if (cmd.action === "insert_before_selection_html" && hasHtmlPayload(cmd)) {
          selection.insertHtml(cmd.html, Word.InsertLocation.before);
          logWordResult("inserted before selection", "html");
        } else if (cmd.action === "append_document_text" && hasTextPayload(cmd)) {
          body.insertText(`\n${cmd.text}`, Word.InsertLocation.end);
          logWordResult("appended document", summarizeWordTarget(cmd.text));
        } else if (cmd.action === "append_document_html" && hasHtmlPayload(cmd)) {
          body.insertHtml(cmd.html, Word.InsertLocation.end);
          logWordResult("appended document", "html");
        } else if (cmd.action === "replace_document_text" && hasTextPayload(cmd)) {
          body.insertText(cmd.text, Word.InsertLocation.replace);
          logWordResult("document replaced", summarizeWordTarget(cmd.text));
        } else if (cmd.action === "replace_document_html" && hasHtmlPayload(cmd)) {
          body.insertHtml(cmd.html, Word.InsertLocation.replace);
          logWordResult("document replaced", "html");
        } else if (cmd.action === "replace" && cmd.search && hasTextPayload(cmd)) {
          const results = body.search(cmd.search, { matchCase: true, matchWholeWord: false });
          results.load("items");
          await context.sync();
          if (results.items.length > 0) {
            results.items[0].insertText(cmd.text, Word.InsertLocation.replace);
            logWordResult("replaced", `"${summarizeWordTarget(cmd.search)}..."`);
          } else {
            logWordResult("not found", `"${summarizeWordTarget(cmd.search)}..."`, "33");
          }
        } else if (cmd.action === "insert_after" && cmd.search && hasTextPayload(cmd)) {
          const results = body.search(cmd.search, { matchCase: true });
          results.load("items");
          await context.sync();
          if (results.items.length > 0) {
            results.items[0].insertText("\n" + cmd.text, Word.InsertLocation.after);
            logWordResult("inserted after", `"${summarizeWordTarget(cmd.search)}..."`);
          } else {
            logWordResult("not found", `"${summarizeWordTarget(cmd.search)}..."`, "33");
          }
        } else if (cmd.action === "insert_before" && cmd.search && hasTextPayload(cmd)) {
          const results = body.search(cmd.search, { matchCase: true });
          results.load("items");
          await context.sync();
          if (results.items.length > 0) {
            results.items[0].insertText(cmd.text + "\n", Word.InsertLocation.before);
            logWordResult("inserted before", `"${summarizeWordTarget(cmd.search)}..."`);
          } else {
            logWordResult("not found", `"${summarizeWordTarget(cmd.search)}..."`, "33");
          }
        } else if (cmd.action === "delete" && cmd.search) {
          const results = body.search(cmd.search, { matchCase: true });
          results.load("items");
          await context.sync();
          if (results.items.length > 0) {
            results.items[0].delete();
            logWordResult("deleted", `"${summarizeWordTarget(cmd.search)}..."`);
          } else {
            logWordResult("not found", `"${summarizeWordTarget(cmd.search)}..."`, "33");
          }
        } else {
          logWordResult("ignored command", cmd.action || "unknown", "33");
        }

        await context.sync();
      });
    } catch (err) {
      term.writeln(`\x1b[31m  [edit failed: ${err.message}]\x1b[0m`);
    }
  }
}

// ── Send Message ────────────────────────────────────────────

async function sendMessage(text) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    term.writeln("\x1b[31mNot connected to bridge. Start the server.\x1b[0m");
    prompt();
    return;
  }

  // Auto-sync on first message or if user says "sync"
  let docContext = null;
  const lower = text.toLowerCase();

  if (lower === "sync" || lower === "/sync") {
    await syncDocumentContext();
    prompt();
    return;
  }

  // Check for selection
  const selected = await getSelectedText();
  if (selected && selected.length > 10) {
    docContext = `[SELECTED TEXT]\n${selected}\n\n[EDIT MODE]\nUse selection-based Word commands for this request.`;
  }

  ws.send(JSON.stringify({
    type: "chat",
    content: text,
    documentContext: docContext,
    surface: PAD_SURFACE,
    mode: PAD_MODE,
  }));
}

// ── Sync Button ─────────────────────────────────────────────

async function syncDocument() {
  await syncDocumentContext();
}

// ── Init ────────────────────────────────────────────────────

Office.onReady((info) => {
  if (info.host === Office.HostType.Word) {
    initTerminal();
    connectWS();

    document.getElementById("btn-sync").addEventListener("click", syncDocument);
    document.getElementById("btn-clear").addEventListener("click", () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "clear" }));
      }
    });
  }
});
