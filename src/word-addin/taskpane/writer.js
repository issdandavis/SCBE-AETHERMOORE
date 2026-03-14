const editor = document.getElementById("editor");
const draftTitle = document.getElementById("draft-title");
const bookSubtitle = document.getElementById("book-subtitle");
const bookAuthor = document.getElementById("book-author");
const bookTagline = document.getElementById("book-tagline");
const coverVisual = document.getElementById("cover-visual");
const coverTitleDisplay = document.getElementById("cover-title-display");
const coverSubtitleDisplay = document.getElementById("cover-subtitle-display");
const runningHeadLeft = document.getElementById("running-head-left");
const runningHeadRight = document.getElementById("running-head-right");
const draftStats = document.getElementById("draft-stats");
const saveState = document.getElementById("save-state");
const connectionState = document.getElementById("connection-state");
const selectionState = document.getElementById("selection-state");
const chatLog = document.getElementById("chat-log");
const promptInput = document.getElementById("prompt-input");
const fileInput = document.getElementById("file-input");
const imageInput = document.getElementById("image-input");
const bodyFontSelect = document.getElementById("body-font");
const headingFontSelect = document.getElementById("heading-font");
const themeSelect = document.getElementById("theme-select");
const pageWidthSelect = document.getElementById("page-width");
const bodySizeInput = document.getElementById("body-size");
const bodySizeValue = document.getElementById("body-size-value");
const lineHeightInput = document.getElementById("line-height");
const lineHeightValue = document.getElementById("line-height-value");
const dropcapToggle = document.getElementById("dropcap-toggle");

const AUTOSAVE_KEY = "scbe-book-studio-v2";
const CONTEXT_LIMIT = 16000;
const SESSION_KEY = "scbe-word-writer-session-id";
const PAD_SURFACE = "word-writer";
const PAD_MODE = "COMMS";

let ws = null;
let autosaveTimer = null;
let savedRange = null;
let pendingAssistantBubble = null;
let currentStream = "";
let pendingUploadMode = null;
let sessionId = localStorage.getItem(SESSION_KEY) || "";
let currentZone = "HOT";
let layoutState = {
  coverImage: "",
};

function ensureEditorBody() {
  if (!editor.innerHTML.trim()) {
    editor.innerHTML = "<p></p>";
  }
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function markdownInlineToHtml(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

function buildChapterBlockFromHeading(text) {
  const colonIndex = text.indexOf(":");
  const eyebrow = colonIndex >= 0 ? text.slice(0, colonIndex).trim() : "Section";
  const title = colonIndex >= 0 ? text.slice(colonIndex + 1).trim() : text.trim();

  return [
    '<section class="chapter-block">',
    `<p class="chapter-eyebrow">${markdownInlineToHtml(eyebrow)}</p>`,
    `<h1>${markdownInlineToHtml(title || eyebrow)}</h1>`,
    "</section>",
  ].join("");
}

function markdownToHtml(markdown) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let paragraph = [];
  let listItems = [];
  let listType = null;

  function flushParagraph() {
    if (paragraph.length === 0) {
      return;
    }

    html.push(`<p>${markdownInlineToHtml(paragraph.join(" "))}</p>`);
    paragraph = [];
  }

  function flushList() {
    if (listItems.length === 0 || !listType) {
      return;
    }

    html.push(`<${listType}>${listItems.join("")}</${listType}>`);
    listItems = [];
    listType = null;
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }

    if (/^#\s+/.test(line)) {
      flushParagraph();
      flushList();
      const heading = line.replace(/^#\s+/, "");
      if (/^(chapter|interlude|epilogue)\b/i.test(heading)) {
        html.push(buildChapterBlockFromHeading(heading));
      } else {
        html.push(`<h1>${markdownInlineToHtml(heading)}</h1>`);
      }
      continue;
    }

    if (/^##\s+/.test(line)) {
      flushParagraph();
      flushList();
      html.push(`<h2>${markdownInlineToHtml(line.replace(/^##\s+/, ""))}</h2>`);
      continue;
    }

    if (/^>\s+/.test(line)) {
      flushParagraph();
      flushList();
      html.push(`<blockquote>${markdownInlineToHtml(line.replace(/^>\s+/, ""))}</blockquote>`);
      continue;
    }

    if (/^(\*\s*\*\s*\*|---)$/.test(line)) {
      flushParagraph();
      flushList();
      html.push('<div class="ornament-break">* * *</div>');
      continue;
    }

    if (/^- /.test(line)) {
      flushParagraph();
      if (listType && listType !== "ul") {
        flushList();
      }
      listType = "ul";
      listItems.push(`<li>${markdownInlineToHtml(line.slice(2).trim())}</li>`);
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      flushParagraph();
      if (listType && listType !== "ol") {
        flushList();
      }
      listType = "ol";
      listItems.push(`<li>${markdownInlineToHtml(line.replace(/^\d+\.\s+/, ""))}</li>`);
      continue;
    }

    flushList();
    paragraph.push(line);
  }

  flushParagraph();
  flushList();

  return html.join("");
}

function paragraphsToHtml(text) {
  const trimmed = `${text || ""}`.trim();
  if (!trimmed) {
    return "<p></p>";
  }

  return trimmed
    .split(/\n{2,}/)
    .map((part) => `<p>${escapeHtml(part).replace(/\n/g, "<br>")}</p>`)
    .join("");
}

function htmlToPlainText(html) {
  const scratch = document.createElement("div");
  scratch.innerHTML = html;
  return scratch.innerText.replace(/\n{3,}/g, "\n\n").trim();
}

function getProjectState() {
  return {
    title: draftTitle.value || "Untitled Book",
    subtitle: bookSubtitle.value || "",
    author: bookAuthor.value || "",
    tagline: bookTagline.value || "",
    html: editor.innerHTML,
    coverImage: layoutState.coverImage || "",
    bodyFont: bodyFontSelect.value,
    headingFont: headingFontSelect.value,
    theme: themeSelect.value,
    pageWidth: pageWidthSelect.value,
    bodySize: bodySizeInput.value,
    lineHeight: lineHeightInput.value,
    dropcap: dropcapToggle.checked,
    savedAt: new Date().toISOString(),
  };
}

function applyProjectState(state) {
  draftTitle.value = state.title || "Untitled Book";
  bookSubtitle.value = state.subtitle || "";
  bookAuthor.value = state.author || "Issac Davis";
  bookTagline.value = state.tagline || "";
  editor.innerHTML = state.html || "<p></p>";
  layoutState.coverImage = state.coverImage || "";
  bodyFontSelect.value = state.bodyFont || bodyFontSelect.value;
  headingFontSelect.value = state.headingFont || headingFontSelect.value;
  themeSelect.value = state.theme || themeSelect.value;
  pageWidthSelect.value = state.pageWidth || pageWidthSelect.value;
  bodySizeInput.value = state.bodySize || bodySizeInput.value;
  lineHeightInput.value = state.lineHeight || lineHeightInput.value;
  dropcapToggle.checked = Boolean(state.dropcap);
  applyLayoutControls();
}

function setSaveState(text) {
  saveState.textContent = text;
}

function saveLocalProject() {
  try {
    localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(getProjectState()));
    setSaveState(`autosaved ${new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`);
  } catch {
    setSaveState("autosave failed");
  }
}

function scheduleAutosave() {
  setSaveState("pending");

  if (autosaveTimer) {
    clearTimeout(autosaveTimer);
  }

  autosaveTimer = setTimeout(saveLocalProject, 500);
}

function restoreLocalProject() {
  const raw = localStorage.getItem(AUTOSAVE_KEY);
  if (!raw) {
    applyLayoutControls();
    ensureEditorBody();
    updateStats();
    return;
  }

  try {
    const state = JSON.parse(raw);
    applyProjectState(state);
    setSaveState(state.savedAt ? `restored ${new Date(state.savedAt).toLocaleString()}` : "restored");
  } catch {
    applyLayoutControls();
    ensureEditorBody();
  }

  updateStats();
}

function updateStats() {
  const text = htmlToPlainText(editor.innerHTML);
  const words = text ? text.split(/\s+/).filter(Boolean).length : 0;
  draftStats.textContent = `${words.toLocaleString()} words`;
}

function applyLayoutControls() {
  document.documentElement.style.setProperty("--book-body-font", bodyFontSelect.value);
  document.documentElement.style.setProperty("--book-heading-font", headingFontSelect.value);
  document.documentElement.style.setProperty("--book-body-size", `${bodySizeInput.value}px`);
  document.documentElement.style.setProperty("--book-line-height", lineHeightInput.value);
  document.documentElement.style.setProperty("--book-page-width", `${pageWidthSelect.value}px`);
  bodySizeValue.textContent = `${bodySizeInput.value}px`;
  lineHeightValue.textContent = Number(lineHeightInput.value).toFixed(2);
  document.body.dataset.theme = themeSelect.value;
  document.body.classList.toggle("dropcap-enabled", dropcapToggle.checked);
  refreshFrontMatter();
}

function refreshFrontMatter() {
  const title = draftTitle.value || "Untitled Book";
  const subtitle = bookSubtitle.value || "Subtitle or edition line";
  const author = bookAuthor.value || "Author";

  coverTitleDisplay.textContent = title;
  coverSubtitleDisplay.textContent = subtitle;
  runningHeadLeft.textContent = title;
  runningHeadRight.textContent = author;

  if (layoutState.coverImage) {
    coverVisual.style.backgroundImage = `linear-gradient(160deg, rgba(32, 48, 66, 0.24), rgba(108, 56, 39, 0.16)), url("${layoutState.coverImage}")`;
    const placeholder = coverVisual.querySelector(".cover-placeholder");
    if (placeholder) {
      placeholder.remove();
    }
    return;
  }

  coverVisual.style.backgroundImage = "";
  if (!coverVisual.querySelector(".cover-placeholder")) {
    const placeholder = document.createElement("div");
    placeholder.className = "cover-placeholder";
    placeholder.textContent = "Add a cover image";
    coverVisual.appendChild(placeholder);
  }
}

function clipContext(text) {
  if (text.length <= CONTEXT_LIMIT) {
    return text;
  }

  const edge = Math.floor(CONTEXT_LIMIT / 2);
  return `${text.slice(0, edge)}\n\n[...truncated...]\n\n${text.slice(-edge)}`;
}

function getFullContext() {
  return [
    `TITLE: ${draftTitle.value || "Untitled Book"}`,
    `SUBTITLE: ${bookSubtitle.value || ""}`,
    `AUTHOR: ${bookAuthor.value || ""}`,
    `TAGLINE: ${bookTagline.value || ""}`,
    `LAYOUT: body font ${bodyFontSelect.selectedOptions[0].text}, heading font ${headingFontSelect.selectedOptions[0].text}, page width ${pageWidthSelect.value}px, body size ${bodySizeInput.value}px, line height ${lineHeightInput.value}, theme ${themeSelect.value}, dropcap ${dropcapToggle.checked}`,
    "",
    clipContext(htmlToPlainText(editor.innerHTML)),
  ].join("\n");
}

function addMessage(kind, text) {
  const el = document.createElement("div");
  el.className = `message ${kind}`;
  el.textContent = text;
  chatLog.appendChild(el);
  chatLog.scrollTop = chatLog.scrollHeight;
  return el;
}

function cleanAssistantText(text) {
  return text
    .replace(/@@WORD_CMD@@[\s\S]+?@@END@@/g, "")
    .replace(/@@EDITOR_CMD@@[\s\S]+?@@END@@/g, "")
    .trim();
}

function connectWs() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const url = new URL(`${proto}//${location.host}`);
  if (sessionId) {
    url.searchParams.set("session", sessionId);
  }
  url.searchParams.set("surface", PAD_SURFACE);
  url.searchParams.set("mode", PAD_MODE);
  ws = new WebSocket(url);

  ws.onopen = () => {
    connectionState.textContent = "connected";
    addMessage("system", "Bridge connected. This lane edits the designed book page directly.");
    ws.send(JSON.stringify({
      type: "hello",
      surface: PAD_SURFACE,
      mode: PAD_MODE,
      documentTitle: draftTitle.value || "Untitled Book",
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
      connectionState.textContent = `connected · ${currentZone.toLowerCase()}`;
      if (msg.resumed) {
        addMessage("system", `Resumed session ${sessionId}.`);
      }
      return;
    }

    if (msg.type === "stream") {
      currentStream += msg.text;
      if (!pendingAssistantBubble) {
        pendingAssistantBubble = addMessage("assistant", "writing...");
      } else {
        pendingAssistantBubble.textContent = "writing...";
      }
      return;
    }

    if (msg.type === "stream_end") {
      const text = cleanAssistantText(currentStream) || "Applied editor command.";
      if (pendingAssistantBubble) {
        pendingAssistantBubble.textContent = text;
      } else {
        addMessage("assistant", text);
      }
      pendingAssistantBubble = null;
      currentStream = "";
      return;
    }

    if (msg.type === "editor_commands") {
      applyEditorCommands(msg.commands);
      return;
    }

    if (msg.type === "provider") {
      connectionState.textContent = `connected · ${msg.label} · ${currentZone.toLowerCase()}`;
      addMessage(
        "system",
        msg.fallback
          ? `AI provider fallback: ${msg.label} (${msg.model})`
          : `AI provider: ${msg.label} (${msg.model})`,
      );
      return;
    }

    if (msg.type === "synced") {
      currentZone = msg.zone || currentZone;
      connectionState.textContent = `connected · ${currentZone.toLowerCase()}`;
      addMessage("system", `Context synced: ${msg.chars.toLocaleString()} chars`);
      return;
    }

    if (msg.type === "zone_update") {
      currentZone = msg.zone || currentZone;
      connectionState.textContent = `connected · ${currentZone.toLowerCase()}`;
      addMessage("system", `Pad zone: ${currentZone}`);
      return;
    }

    if (msg.type === "cleared") {
      chatLog.innerHTML = "";
      addMessage("system", "Conversation cleared.");
      return;
    }

    if (msg.type === "error") {
      addMessage("error", msg.message);
      pendingAssistantBubble = null;
      currentStream = "";
    }
  };

  ws.onclose = () => {
    connectionState.textContent = "reconnecting...";
    setTimeout(connectWs, 3000);
  };

  ws.onerror = () => {
    connectionState.textContent = "bridge error";
  };
}

function cacheSelection() {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) {
    return;
  }

  const range = selection.getRangeAt(0);
  if (!editor.contains(range.commonAncestorContainer)) {
    return;
  }

  savedRange = range.cloneRange();
  const selected = selection.toString().trim();
  selectionState.textContent = selected
    ? `Selection cached: ${selected.split(/\s+/).filter(Boolean).length} words`
    : "Cursor cached";
}

function restoreSelection() {
  if (!savedRange) {
    return null;
  }

  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(savedRange);
  return savedRange;
}

function moveCaretAfter(node) {
  const range = document.createRange();
  range.setStartAfter(node);
  range.collapse(true);
  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
  savedRange = range.cloneRange();
}

function replaceRangeWithHtml(range, html, collapseAfter) {
  const container = document.createElement("div");
  container.innerHTML = html;
  const fragment = document.createDocumentFragment();
  let lastNode = null;

  while (container.firstChild) {
    lastNode = fragment.appendChild(container.firstChild);
  }

  range.deleteContents();
  range.insertNode(fragment);

  if (lastNode && collapseAfter) {
    moveCaretAfter(lastNode);
  }
}

function insertHtmlAtSelection(html) {
  editor.focus();
  const range = restoreSelection() || (() => {
    const endRange = document.createRange();
    endRange.selectNodeContents(editor);
    endRange.collapse(false);
    return endRange;
  })();

  range.collapse(false);
  replaceRangeWithHtml(range, html, true);
  ensureEditorBody();
  scheduleAutosave();
  updateStats();
}

function buildChapterBlockHtml() {
  return [
    '<section class="chapter-block">',
    '<p class="chapter-eyebrow">Chapter</p>',
    "<h1>Chapter Title</h1>",
    '<p class="chapter-subtitle">Optional subtitle or location line</p>',
    "</section>",
    "<p></p>",
  ].join("");
}

function buildOrnamentBreakHtml() {
  return '<div class="ornament-break">* * *</div><p></p>';
}

function buildArtHtml(src, kind) {
  return [
    `<figure class="art art-${kind}">`,
    `<img src="${src}" alt="Book art"/>`,
    "<figcaption>Art caption</figcaption>",
    "</figure>",
    "<p></p>",
  ].join("");
}

function applyEditorCommands(commands) {
  editor.focus();

  commands.forEach((command) => {
    if (command.action === "replace_document" && command.text) {
      editor.innerHTML = paragraphsToHtml(command.text);
      return;
    }

    if (command.action === "append_document" && command.text) {
      insertHtmlAtSelection(paragraphsToHtml(command.text));
      return;
    }

    if (command.action === "replace_selection" && command.text) {
      const range = restoreSelection();
      if (!range) {
        addMessage("error", "No selection was cached for the editor command.");
        return;
      }

      replaceRangeWithHtml(range, paragraphsToHtml(command.text), true);
      return;
    }

    if (command.action === "insert_after_selection" && command.text) {
      const range = restoreSelection();
      if (!range) {
        addMessage("error", "No selection was cached for the editor command.");
        return;
      }

      range.collapse(false);
      replaceRangeWithHtml(range, paragraphsToHtml(command.text), true);
    }
  });

  ensureEditorBody();
  scheduleAutosave();
  updateStats();
  addMessage("system", "Editor command applied.");
}

function syncContext() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    addMessage("error", "Bridge is not connected.");
    return;
  }

  ws.send(JSON.stringify({
    type: "sync_context",
    documentContext: getFullContext(),
    documentTitle: draftTitle.value || "Untitled Book",
    surface: PAD_SURFACE,
    mode: PAD_MODE,
  }));
}

function sendPrompt(text, extraContext = "") {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    addMessage("error", "Bridge is not connected.");
    return;
  }

  addMessage("user", text);
  currentStream = "";
  pendingAssistantBubble = null;

  ws.send(JSON.stringify({
    type: "chat",
    content: text,
    documentContext: extraContext,
    documentTitle: draftTitle.value || "Untitled Book",
    surface: PAD_SURFACE,
    mode: PAD_MODE,
  }));
}

function getSelectionText() {
  const selection = window.getSelection();
  return selection ? selection.toString().trim() : "";
}

function runSelectionAction(kind) {
  const selected = getSelectionText();
  if (!selected) {
    addMessage("error", "Select text first.");
    return;
  }

  cacheSelection();

  const prompts = {
    rewrite: "Rewrite the selected passage for stronger voice, clarity, and rhythm. Return exactly one @@EDITOR_CMD@@ replace_selection block, then a short rationale.",
    expand: "Expand the selected passage with 2 to 4 sentences of concrete scene depth. Return exactly one @@EDITOR_CMD@@ replace_selection block, then a short rationale.",
    continue: "Continue directly after the selected passage. Return exactly one @@EDITOR_CMD@@ insert_after_selection block, then a short rationale.",
    summarize: "Summarize the selected passage and explain what it is doing emotionally and structurally. Do not emit edit commands.",
  };

  sendPrompt(prompts[kind], `[SELECTION]\n${selected}\n\n[BOOK CONTEXT]\n${getFullContext()}`);
}

function downloadFile(name, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

function openDraftFromFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    const content = reader.result;

    if (/\.html?$/i.test(file.name)) {
      const doc = new DOMParser().parseFromString(content, "text/html");
      const embeddedState = doc.querySelector("#scbe-book-state");
      if (embeddedState) {
        try {
          applyProjectState(JSON.parse(embeddedState.textContent));
          ensureEditorBody();
          updateStats();
          scheduleAutosave();
          return;
        } catch {}
      }

      const exportEditor = doc.querySelector(".export-editor") || doc.querySelector("#editor") || doc.body;
      editor.innerHTML = exportEditor ? exportEditor.innerHTML : content;
      draftTitle.value = file.name.replace(/\.[^.]+$/, "");
      ensureEditorBody();
      updateStats();
      scheduleAutosave();
      return;
    }

    draftTitle.value = file.name.replace(/\.[^.]+$/, "");
    editor.innerHTML = /\.md$/i.test(file.name) ? markdownToHtml(content) : paragraphsToHtml(content);
    ensureEditorBody();
    updateStats();
    scheduleAutosave();
  };
  reader.readAsText(file);
}

async function loadReaderEditionFromRepo() {
  try {
    const response = await fetch("/api/manuscript/reader-edition");
    if (!response.ok) {
      throw new Error(`Load failed with status ${response.status}`);
    }

    const payload = await response.json();
    draftTitle.value = payload.title || "Untitled Book";
    bookAuthor.value = payload.author || bookAuthor.value;
    editor.innerHTML = markdownToHtml(payload.content || "");
    ensureEditorBody();
    applyLayoutControls();
    updateStats();
    scheduleAutosave();
    addMessage("system", `Loaded reader edition from ${payload.sourcePath}`);
  } catch (err) {
    addMessage("error", `Reader edition load failed: ${err.message}`);
  }
}

async function buildKdpAndOpenLibreOffice() {
  setSaveState("building kdp...");
  addMessage("system", "Building KDP manuscript and opening LibreOffice...");

  try {
    const response = await fetch("/api/book/build-kdp-open", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
    });

    let payload = null;
    try {
      payload = await response.json();
    } catch {
      throw new Error(`Build request failed with status ${response.status}`);
    }

    if (!response.ok || payload.status !== "ok") {
      throw new Error(payload.message || `Build request failed with status ${response.status}`);
    }

    setSaveState("kdp built");
    const officeStatus = payload.libreOfficeOpened ? "LibreOffice opened." : "LibreOffice was not found.";
    addMessage("system", `KDP build finished. ${officeStatus} Output: ${payload.outputPath}`);
  } catch (err) {
    setSaveState("build failed");
    addMessage("error", `KDP build failed: ${err.message}`);
  }
}

function applyFormat(command) {
  editor.focus();

  const map = {
    bold: () => document.execCommand("bold"),
    italic: () => document.execCommand("italic"),
    underline: () => document.execCommand("underline"),
    h1: () => document.execCommand("formatBlock", false, "h1"),
    h2: () => document.execCommand("formatBlock", false, "h2"),
    quote: () => document.execCommand("formatBlock", false, "blockquote"),
    ul: () => document.execCommand("insertUnorderedList"),
    ol: () => document.execCommand("insertOrderedList"),
    chapter: () => insertHtmlAtSelection(buildChapterBlockHtml()),
    break: () => insertHtmlAtSelection(buildOrnamentBreakHtml()),
    clear: () => document.execCommand("removeFormat"),
  };

  if (!map[command]) {
    return;
  }

  map[command]();
  ensureEditorBody();
  scheduleAutosave();
  updateStats();
}

function buildExportHtml() {
  const title = escapeHtml(draftTitle.value || "Untitled Book");
  const subtitle = escapeHtml(bookSubtitle.value || "");
  const author = escapeHtml(bookAuthor.value || "");
  const tagline = escapeHtml(bookTagline.value || "").replace(/\n/g, "<br>");
  const coverImage = layoutState.coverImage
    ? `<div class="export-cover-visual" style="background-image: linear-gradient(160deg, rgba(32,48,66,0.22), rgba(108,56,39,0.16)), url('${layoutState.coverImage}')"></div>`
    : `<div class="export-cover-visual export-cover-placeholder">Add Cover</div>`;
  const embeddedState = JSON.stringify(getProjectState()).replace(/</g, "\\u003c");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>${title}</title>
  <style>
    :root {
      --book-body-font: ${bodyFontSelect.value};
      --book-heading-font: ${headingFontSelect.value};
      --book-body-size: ${bodySizeInput.value}px;
      --book-line-height: ${lineHeightInput.value};
      --page-width: ${pageWidthSelect.value}px;
      --ink: #261c15;
      --muted: #6e6155;
      --accent: ${getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#b55334"};
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      background: #f6f2ea;
      font-family: "Segoe UI Variable Text", "Aptos", sans-serif;
      padding: 28px;
    }
    .export-shell { display: flex; flex-direction: column; align-items: center; gap: 24px; }
    .export-cover,
    .export-page {
      width: min(100%, var(--page-width));
      background: white;
      border: 1px solid rgba(38,28,21,0.08);
      box-shadow: 0 16px 32px rgba(38,28,21,0.12);
    }
    .export-cover {
      display: grid;
      grid-template-columns: minmax(240px, 0.42fr) minmax(0, 0.58fr);
      gap: 18px;
      padding: 18px;
    }
    .export-cover-visual {
      aspect-ratio: 2 / 3;
      border-radius: 18px;
      background-size: cover;
      background-position: center;
      background-color: #203042;
    }
    .export-cover-placeholder {
      display: flex;
      align-items: center;
      justify-content: center;
      color: rgba(255,255,255,0.75);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.16em;
    }
    .export-cover-copy {
      display: flex;
      flex-direction: column;
      justify-content: center;
      gap: 12px;
    }
    .export-cover-copy h1 {
      margin: 0;
      font-family: var(--book-heading-font);
      font-size: clamp(34px, 4vw, 52px);
      line-height: 1.02;
    }
    .export-cover-copy .subtitle {
      margin: 0;
      font-family: var(--book-body-font);
      font-size: 18px;
      color: var(--muted);
    }
    .export-cover-copy .author {
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .export-cover-copy .tagline {
      margin: 0;
      font-size: 14px;
      line-height: 1.6;
      color: var(--muted);
    }
    .export-page {
      min-height: 1120px;
      padding: 26px 68px 82px;
    }
    .running-head {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding-bottom: 16px;
      margin-bottom: 22px;
      border-bottom: 1px solid rgba(38,28,21,0.08);
      color: rgba(110,97,85,0.9);
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }
    .export-editor {
      font-family: var(--book-body-font);
      font-size: var(--book-body-size);
      line-height: var(--book-line-height);
      color: var(--ink);
    }
    .export-editor p { margin: 0 0 1.05em; }
    .export-editor ul, .export-editor ol { margin: 0 0 1.2em 1.3em; padding: 0; }
    .export-editor li { margin: 0 0 0.4em; }
    .export-editor h1,
    .export-editor h2,
    .export-editor h3,
    .export-editor .chapter-block h1 {
      font-family: var(--book-heading-font);
      line-height: 1.15;
      margin: 1.2em 0 0.5em;
    }
    .export-editor .chapter-block { margin: 3.8em 0 2.6em; text-align: center; }
    .export-editor .chapter-eyebrow { margin: 0 0 0.8em; text-transform: uppercase; letter-spacing: 0.24em; font-size: 11px; color: var(--muted); }
    .export-editor .chapter-subtitle { margin: 0.3em auto 0; max-width: 26em; color: var(--muted); font-size: 0.9em; }
    .export-editor blockquote { margin: 1.4em 0; padding: 0.25em 0 0.25em 1em; border-left: 3px solid rgba(181,83,52,0.36); color: #5d4939; font-style: italic; }
    .export-editor .ornament-break { margin: 2.4em 0; text-align: center; color: rgba(110,97,85,0.92); letter-spacing: 0.5em; text-transform: uppercase; font-size: 12px; }
    .export-editor .art { margin: 1.8em 0; display: flex; flex-direction: column; gap: 10px; }
    .export-editor .art img { width: 100%; display: block; border-radius: 14px; box-shadow: 0 12px 24px rgba(38,28,21,0.12); }
    .export-editor .art figcaption { font-size: 13px; color: var(--muted); text-align: center; }
    .export-editor .art-left, .export-editor .art-right { max-width: 48%; }
    .export-editor .art-left { float: left; margin-right: 1.4em; }
    .export-editor .art-right { float: right; margin-left: 1.4em; }
    .export-editor .art-full { width: 100%; }
    body.dropcap-enabled .export-editor > p:first-of-type:first-letter {
      float: left;
      font-family: var(--book-heading-font);
      font-size: 4.4em;
      line-height: 0.82;
      padding-right: 0.12em;
      padding-top: 0.04em;
      color: var(--accent);
    }
    @media print {
      body { background: white; padding: 0; }
      .export-cover, .export-page { width: 100%; box-shadow: none; border: none; break-after: page; }
      .export-page { padding: 24mm 20mm; }
    }
    @media (max-width: 900px) {
      .export-cover { grid-template-columns: 1fr; }
      .export-page { padding: 24px 18px 42px; }
      .export-editor .art-left, .export-editor .art-right { float: none; max-width: 100%; margin-left: 0; margin-right: 0; }
    }
  </style>
</head>
<body class="${dropcapToggle.checked ? "dropcap-enabled" : ""}">
  <script id="scbe-book-state" type="application/json">${embeddedState}</script>
  <main class="export-shell">
    <section class="export-cover">
      ${coverImage}
      <div class="export-cover-copy">
        <div class="kicker">Final Form Front Matter</div>
        <h1>${title}</h1>
        <p class="subtitle">${subtitle || " "}</p>
        <div class="author">${author}</div>
        <p class="tagline">${tagline || " "}</p>
      </div>
    </section>

    <article class="export-page">
      <div class="running-head">
        <span>${title}</span>
        <span>${author}</span>
      </div>
      <div class="export-editor">${editor.innerHTML}</div>
    </article>
  </main>
</body>
</html>`;
}

function printPreview() {
  const preview = window.open("", "_blank", "noopener,noreferrer");
  if (!preview) {
    addMessage("error", "Popup blocked. Allow popups for print preview.");
    return;
  }

  preview.document.open();
  preview.document.write(buildExportHtml());
  preview.document.close();
}

function promptForImage(mode) {
  pendingUploadMode = mode;
  imageInput.click();
}

function handleImageFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    if (pendingUploadMode === "cover") {
      layoutState.coverImage = reader.result;
      applyLayoutControls();
      scheduleAutosave();
      return;
    }

    if (pendingUploadMode === "art-left") {
      insertHtmlAtSelection(buildArtHtml(reader.result, "left"));
      return;
    }

    if (pendingUploadMode === "art-right") {
      insertHtmlAtSelection(buildArtHtml(reader.result, "right"));
      return;
    }

    if (pendingUploadMode === "art-full") {
      insertHtmlAtSelection(buildArtHtml(reader.result, "full"));
    }
  };
  reader.readAsDataURL(file);
}

function wireEvents() {
  ensureEditorBody();

  [
    draftTitle,
    bookSubtitle,
    bookAuthor,
    bookTagline,
    bodyFontSelect,
    headingFontSelect,
    themeSelect,
    pageWidthSelect,
    bodySizeInput,
    lineHeightInput,
    dropcapToggle,
  ].forEach((element) => {
    element.addEventListener("input", () => {
      applyLayoutControls();
      scheduleAutosave();
    });
    element.addEventListener("change", () => {
      applyLayoutControls();
      scheduleAutosave();
    });
  });

  editor.addEventListener("input", () => {
    ensureEditorBody();
    scheduleAutosave();
    updateStats();
  });

  editor.addEventListener("mouseup", cacheSelection);
  editor.addEventListener("keyup", cacheSelection);
  document.addEventListener("selectionchange", cacheSelection);

  document.querySelectorAll("[data-command]").forEach((button) => {
    button.addEventListener("click", () => applyFormat(button.dataset.command));
  });

  document.getElementById("new-draft").addEventListener("click", () => {
    draftTitle.value = "Untitled Book";
    bookSubtitle.value = "";
    bookAuthor.value = "Issac Davis";
    bookTagline.value = "";
    editor.innerHTML = "<p></p>";
    layoutState.coverImage = "";
    savedRange = null;
    applyLayoutControls();
    scheduleAutosave();
    updateStats();
  });

  document.getElementById("load-reader-edition").addEventListener("click", loadReaderEditionFromRepo);
  document.getElementById("build-kdp-open").addEventListener("click", buildKdpAndOpenLibreOffice);

  document.getElementById("open-draft").addEventListener("click", () => {
    pendingUploadMode = "draft";
    fileInput.click();
  });

  document.getElementById("export-html").addEventListener("click", () => {
    downloadFile(`${draftTitle.value || "untitled-book"}.html`, buildExportHtml(), "text/html");
  });

  document.getElementById("export-text").addEventListener("click", () => {
    downloadFile(`${draftTitle.value || "untitled-book"}.txt`, htmlToPlainText(editor.innerHTML), "text/plain");
  });

  document.getElementById("print-preview").addEventListener("click", printPreview);
  document.getElementById("sync-context").addEventListener("click", syncContext);

  document.getElementById("upload-cover").addEventListener("click", () => promptForImage("cover"));
  document.getElementById("remove-cover").addEventListener("click", () => {
    layoutState.coverImage = "";
    applyLayoutControls();
    scheduleAutosave();
  });
  document.getElementById("insert-art-left").addEventListener("click", () => promptForImage("art-left"));
  document.getElementById("insert-art-right").addEventListener("click", () => promptForImage("art-right"));
  document.getElementById("insert-art-full").addEventListener("click", () => promptForImage("art-full"));
  document.getElementById("insert-scene-break").addEventListener("click", () => insertHtmlAtSelection(buildOrnamentBreakHtml()));
  document.getElementById("insert-chapter").addEventListener("click", () => insertHtmlAtSelection(buildChapterBlockHtml()));

  document.getElementById("clear-chat").addEventListener("click", () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "clear" }));
    }
  });

  document.getElementById("send-prompt").addEventListener("click", () => {
    const text = promptInput.value.trim();
    if (!text) {
      return;
    }

    const selection = getSelectionText();
    const context = selection
      ? `[SELECTION]\n${selection}\n\n[BOOK CONTEXT]\n${getFullContext()}`
      : `[BOOK CONTEXT]\n${getFullContext()}`;

    sendPrompt(text, context);
    promptInput.value = "";
  });

  promptInput.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      document.getElementById("send-prompt").click();
    }
  });

  document.getElementById("rewrite-selection").addEventListener("click", () => runSelectionAction("rewrite"));
  document.getElementById("expand-selection").addEventListener("click", () => runSelectionAction("expand"));
  document.getElementById("continue-selection").addEventListener("click", () => runSelectionAction("continue"));
  document.getElementById("summarize-selection").addEventListener("click", () => runSelectionAction("summarize"));

  fileInput.addEventListener("change", (event) => {
    const [file] = event.target.files || [];
    if (file && pendingUploadMode === "draft") {
      openDraftFromFile(file);
    }
    pendingUploadMode = null;
    event.target.value = "";
  });

  imageInput.addEventListener("change", (event) => {
    const [file] = event.target.files || [];
    if (file) {
      handleImageFile(file);
    }
    pendingUploadMode = null;
    event.target.value = "";
  });
}

restoreLocalProject();
wireEvents();
connectWs();
applyLayoutControls();
updateStats();
