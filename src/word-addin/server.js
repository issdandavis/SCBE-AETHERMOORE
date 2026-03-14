/**
 * SCBE Word Add-in Bridge Server
 * Serves the taskpane over HTTPS and bridges WebSocket to Claude API.
 */

const https = require("https");
const http = require("http");
const fs = require("fs");
const path = require("path");
const express = require("express");
const { spawn } = require("child_process");
const { WebSocketServer } = require("ws");
const Anthropic = require("@anthropic-ai/sdk").default;
const { loadOrCreateSession, generateSessionId } = require("./session_envelope");

const PORT = 3000;
const app = express();
const repoRoot = path.resolve(__dirname, "..", "..");
const readerEditionPath = path.join(repoRoot, "content", "book", "reader-edition", "the-six-tongues-protocol-full.md");
const buildKdpPath = path.join(repoRoot, "content", "book", "build_kdp.py");
const kdpOutputPath = path.join(repoRoot, "content", "book", "the-six-tongues-protocol-kdp.docx");
const libreOfficePath = path.join("C:", "Program Files", "LibreOffice", "program", "swriter.exe");

app.use(express.json());

// Serve manifest.xml at root for catalog discovery
app.get("/manifest.xml", (_req, res) => {
  res.type("application/xml").sendFile(path.join(__dirname, "manifest.xml"));
});

// Serve static taskpane files
app.use("/taskpane", express.static(path.join(__dirname, "taskpane")));

app.get("/", (_req, res) => {
  res.redirect("/taskpane/writer.html");
});

// Health check
app.get("/health", (_req, res) => res.json({ status: "ok", service: "scbe-word-addin" }));

app.get("/api/manuscript/reader-edition", (_req, res) => {
  try {
    const content = fs.readFileSync(readerEditionPath, "utf8");
    res.json({
      title: "The Six Tongues Protocol",
      author: "Issac Davis",
      sourcePath: readerEditionPath,
      content,
    });
  } catch (err) {
    res.status(500).json({
      error: "reader_edition_load_failed",
      message: err.message,
    });
  }
});

function runProcess(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      windowsHide: true,
      ...options,
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    child.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolve({ stdout, stderr, code });
        return;
      }

      reject(new Error(`Process failed (${command}) with exit code ${code}\n${stderr || stdout}`));
    });
  });
}

app.post("/api/book/build-kdp-open", async (_req, res) => {
  try {
    const buildResult = await runProcess("python", [buildKdpPath], {
      cwd: path.dirname(buildKdpPath),
    });

    if (!fs.existsSync(kdpOutputPath)) {
      throw new Error(`KDP output missing after build: ${kdpOutputPath}`);
    }

    let libreOfficeOpened = false;
    if (fs.existsSync(libreOfficePath)) {
      const libreProcess = spawn(libreOfficePath, [kdpOutputPath], {
        detached: true,
        stdio: "ignore",
        windowsHide: true,
      });
      libreProcess.unref();
      libreOfficeOpened = true;
    }

    res.json({
      status: "ok",
      outputPath: kdpOutputPath,
      libreOfficeOpened,
      buildStdout: buildResult.stdout,
      buildStderr: buildResult.stderr,
    });
  } catch (err) {
    res.status(500).json({
      status: "error",
      message: err.message,
    });
  }
});

// Load dev certs
function loadCerts() {
  const certDir = path.join(require("os").homedir(), ".office-addin-dev-certs");
  const keyPath = path.join(certDir, "localhost.key");
  const certPath = path.join(certDir, "localhost.crt");
  const caPath = path.join(certDir, "ca.crt");

  if (!fs.existsSync(keyPath)) {
    console.error("No dev certs found. Run: npm run certs");
    process.exit(1);
  }

  const opts = {
    key: fs.readFileSync(keyPath),
    cert: fs.readFileSync(certPath),
  };
  if (fs.existsSync(caPath)) opts.ca = fs.readFileSync(caPath);
  return opts;
}

const ANTHROPIC_MODEL = process.env.SCBE_WRITER_ANTHROPIC_MODEL || "claude-sonnet-4-20250514";
const OPENAI_MODEL = process.env.SCBE_WRITER_OPENAI_MODEL || "gpt-4o-mini";
const XAI_MODEL = process.env.SCBE_WRITER_XAI_MODEL || "grok-3-mini";
const GROQ_MODEL = process.env.SCBE_WRITER_GROQ_MODEL || "llama-3.3-70b-versatile";
const claude = process.env.ANTHROPIC_API_KEY
  ? new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
  : null;

const SYSTEM_PROMPT = `You are an AI writing assistant embedded either in Microsoft Word as a sidebar terminal or in a standalone local writing studio.
You help the author edit their manuscript directly.

When the user shares document content, you can see it and make edits.

To edit a Word document, prefer selection-based commands whenever the user highlighted text in Word. Selection commands work at the live cursor/selection and support formatting when you use HTML:
@@WORD_CMD@@{"action":"replace_selection_text","text":"replacement text"}@@END@@
@@WORD_CMD@@{"action":"replace_selection_html","html":"<p>Replacement with <em>formatting</em>.</p>"}@@END@@
@@WORD_CMD@@{"action":"insert_after_selection_html","html":"<p>New paragraph after the current selection.</p>"}@@END@@
@@WORD_CMD@@{"action":"insert_before_selection_html","html":"<h1>Chapter Title</h1><p>Chapter opener text.</p>"}@@END@@
@@WORD_CMD@@{"action":"append_document_html","html":"<p>Appendix text at the end of the document.</p>"}@@END@@
@@WORD_CMD@@{"action":"replace_document_html","html":"<h1>New Draft</h1><p>Full replacement content.</p>"}@@END@@

Fallback search-based Word commands are still allowed when there is no active selection:
@@WORD_CMD@@{"action":"replace","search":"old text to find","text":"replacement text"}@@END@@
@@WORD_CMD@@{"action":"insert_after","search":"text to find","text":"new paragraph to add after"}@@END@@
@@WORD_CMD@@{"action":"insert_before","search":"text to find","text":"new paragraph before"}@@END@@
@@WORD_CMD@@{"action":"delete","search":"text to delete"}@@END@@

When you use HTML in Word commands, keep it simple and structural: <p>, <h1>, <h2>, <strong>, <em>, <blockquote>, <ul>, <ol>, <li>, and <hr>.
If selected text is provided in context, prefer selection commands over search commands.

To edit the standalone writing studio, output a JSON block like this on its own line:
@@EDITOR_CMD@@{"action":"replace_selection","text":"replacement text"}@@END@@
@@EDITOR_CMD@@{"action":"insert_after_selection","text":"new text to insert after the selection"}@@END@@
@@EDITOR_CMD@@{"action":"replace_document","text":"full replacement document"}@@END@@
@@EDITOR_CMD@@{"action":"append_document","text":"text to append at document end"}@@END@@

You can issue multiple commands. Each must be on its own line between its marker pair.

When NOT editing, just respond conversationally. You are a skilled fiction editor with a sharp eye for prose, pacing, and voice. You write well. Keep Marcus's sardonic tone, the three-layer rule (human > magical > systems), and never flatten the world into computer metaphors.

The manuscript is "The Six Tongues Protocol" by Issac Davis — a 123K word isekai novel where magic IS protocol architecture.`;

function extractCommands(fullResponse, marker) {
  const regex = new RegExp(`${marker}([\\s\\S]+?)@@END@@`, "g");
  const commands = [];
  let match;

  while ((match = regex.exec(fullResponse)) !== null) {
    try {
      commands.push(JSON.parse(match[1]));
    } catch {}
  }

  return commands;
}

function getConfiguredProviders() {
  const providers = [];

  if (claude) {
    providers.push({
      id: "anthropic",
      label: "Claude",
      model: ANTHROPIC_MODEL,
    });
  }

  if (process.env.OPENAI_API_KEY) {
    providers.push({
      id: "openai",
      label: "OpenAI",
      model: OPENAI_MODEL,
      baseUrl: "https://api.openai.com/v1",
      apiKey: process.env.OPENAI_API_KEY,
    });
  }

  const xaiKey = process.env.XAI_API_KEY || process.env.GROK_API_KEY;
  if (xaiKey) {
    providers.push({
      id: "xai",
      label: "xAI",
      model: XAI_MODEL,
      baseUrl: "https://api.x.ai/v1",
      apiKey: xaiKey,
    });
  }

  if (process.env.GROQ_API_KEY) {
    providers.push({
      id: "groq",
      label: "Groq",
      model: GROQ_MODEL,
      baseUrl: "https://api.groq.com/openai/v1",
      apiKey: process.env.GROQ_API_KEY,
    });
  }

  return providers;
}

function normalizeAssistantContent(content) {
  if (typeof content === "string") {
    return content;
  }

  if (Array.isArray(content)) {
    return content
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (item && typeof item.text === "string") {
          return item.text;
        }
        if (item?.type === "text" && typeof item?.text === "string") {
          return item.text;
        }
        return "";
      })
      .join("");
  }

  return "";
}

function extractProviderError(payload, fallbackMessage) {
  if (!payload || typeof payload !== "object") {
    return fallbackMessage;
  }

  if (typeof payload.error === "string") {
    return payload.error;
  }

  if (payload.error && typeof payload.error.message === "string") {
    return payload.error.message;
  }

  if (typeof payload.message === "string") {
    return payload.message;
  }

  return fallbackMessage;
}

async function runAnthropicConversation(messages, onText) {
  if (!claude) {
    throw new Error("Anthropic is not configured.");
  }

  return new Promise((resolve, reject) => {
    const stream = claude.messages.stream({
      model: ANTHROPIC_MODEL,
      max_tokens: 8192,
      system: SYSTEM_PROMPT,
      messages,
    });

    let fullResponse = "";

    stream.on("text", (text) => {
      fullResponse += text;
      onText(text);
    });

    stream.on("end", () => {
      resolve({
        provider: "anthropic",
        label: "Claude",
        model: ANTHROPIC_MODEL,
        text: fullResponse,
      });
    });

    stream.on("error", (err) => {
      err.partialResponse = fullResponse;
      err.hasPartialResponse = fullResponse.length > 0;
      reject(err);
    });
  });
}

async function runOpenAiCompatibleConversation(provider, messages, onText) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 90000);

  try {
    const response = await fetch(`${provider.baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${provider.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: provider.model,
        max_tokens: 4096,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          ...messages,
        ],
      }),
      signal: controller.signal,
    });

    let payload = null;
    try {
      payload = await response.json();
    } catch {
      throw new Error(`${provider.label} returned a non-JSON response.`);
    }

    if (!response.ok) {
      throw new Error(extractProviderError(payload, `${provider.label} request failed with status ${response.status}.`));
    }

    const text = normalizeAssistantContent(payload?.choices?.[0]?.message?.content).trim();
    if (!text) {
      throw new Error(`${provider.label} returned an empty response.`);
    }

    onText(text);
    return {
      provider: provider.id,
      label: provider.label,
      model: provider.model,
      text,
    };
  } catch (err) {
    if (err?.name === "AbortError") {
      throw new Error(`${provider.label} request timed out.`);
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

async function runConversationWithFallback(messages, onText) {
  const providers = getConfiguredProviders();
  if (providers.length === 0) {
    throw new Error("No AI provider is configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, XAI_API_KEY, GROK_API_KEY, or GROQ_API_KEY.");
  }

  const failures = [];

  for (const provider of providers) {
    try {
      const result = provider.id === "anthropic"
        ? await runAnthropicConversation(messages, onText)
        : await runOpenAiCompatibleConversation(provider, messages, onText);

      return {
        ...result,
        fallback: failures.length > 0,
      };
    } catch (err) {
      if (err?.hasPartialResponse) {
        throw err;
      }

      failures.push(`${provider.label}: ${err.message}`);
    }
  }

  throw new Error(`All AI providers failed. ${failures.join(" | ")}`);
}

function buildSessionMetadata(req, msg = {}, options = {}) {
  const url = new URL(req.url || "/", "ws://localhost");
  return {
    agentId: msg.agentId || url.searchParams.get("agent") || process.env.SCBE_WORD_ADDIN_AGENT_ID || undefined,
    surface: msg.surface || url.searchParams.get("surface") || undefined,
    mode: msg.mode || url.searchParams.get("mode") || undefined,
    documentTitle: msg.documentTitle || undefined,
    repoName: "SCBE-AETHERMOORE",
    branchName: options.branchName || process.env.SCBE_WORD_ADDIN_BRANCH || "",
  };
}

function attachWebSocketBridge(server, options = {}) {
  const wss = new WebSocketServer({ server });

  wss.on("connection", (ws, req) => {
    const url = new URL(req.url || "/", `ws://localhost`);
    const sessionId = url.searchParams.get("session") || generateSessionId();
    const envelope = loadOrCreateSession(sessionId, buildSessionMetadata(req, {}, options));
    const resumed = envelope.conversationHistory.length > 0 || envelope.syncCount > 0;

    console.log(`[bridge] Client connected — session=${sessionId} pad=${envelope.padId} zone=${envelope.currentZone}`);

    let conversationHistory = envelope.conversationHistory;
    let syncedDocumentContext = envelope.documentContext;

    ws.send(JSON.stringify({
      type: "session",
      resumed,
      ...envelope.getClientSummary(),
    }));

    ws.on("message", async (raw) => {
      let msg;
      try {
        msg = JSON.parse(raw);
      } catch {
        return;
      }

      if (msg.type === "hello") {
        envelope.updateMetadata(buildSessionMetadata(req, msg, options));
        envelope.save();
        ws.send(JSON.stringify({
          type: "session",
          resumed: true,
          ...envelope.getClientSummary(),
        }));
      } else if (msg.type === "sync_context") {
        syncedDocumentContext = typeof msg.documentContext === "string" ? msg.documentContext : "";
        envelope.setDocumentContext(syncedDocumentContext, buildSessionMetadata(req, msg, options));
        ws.send(JSON.stringify({
          type: "synced",
          chars: syncedDocumentContext.length,
          zone: envelope.currentZone,
          session_id: envelope.sessionId,
        }));
      } else if (msg.type === "chat") {
        let userContent = msg.content;
        const messageMetadata = buildSessionMetadata(req, msg, options);

        const governance = envelope.governanceCheck(userContent);
        if (!governance.threats.clean) {
          envelope.logEdit("threat_blocked", { hits: governance.threats.hits }, "DENY");
          envelope.save();
          ws.send(JSON.stringify({
            type: "error",
            message: `Input blocked by antivirus gate (${governance.threats.hits.length} pattern match${governance.threats.hits.length > 1 ? "es" : ""})`,
          }));
          return;
        }

        const contextBlocks = [];

        if (syncedDocumentContext) {
          contextBlocks.push(`[DOCUMENT SNAPSHOT — synced from Word]\n${syncedDocumentContext}`);
        }

        if (msg.documentContext) {
          contextBlocks.push(`[CURRENT SELECTION]\n${msg.documentContext}`);
        }

        if (contextBlocks.length > 0) {
          userContent = `${contextBlocks.join("\n\n")}\n\n[USER MESSAGE]\n${userContent}`;
        }

        conversationHistory.push({ role: "user", content: userContent });
        envelope.recordUserMessage(msg.content, msg.documentContext || "", messageMetadata);

        if (conversationHistory.length > 40) {
          conversationHistory = conversationHistory.slice(-30);
        }

        try {
          let fullResponse = "";
          const result = await runConversationWithFallback(conversationHistory, (text) => {
            fullResponse += text;
            ws.send(JSON.stringify({ type: "stream", text }));
          });

          ws.send(JSON.stringify({
            type: "provider",
            label: result.label,
            model: result.model,
            fallback: result.fallback,
          }));

          conversationHistory.push({ role: "assistant", content: fullResponse });

          const wordCommands = extractCommands(fullResponse, "@@WORD_CMD@@");
          const editorCommands = extractCommands(fullResponse, "@@EDITOR_CMD@@");

          const responseThreats = envelope.scanThreats(fullResponse);

          if (wordCommands.length > 0) {
            const decision = responseThreats.clean ? governance.score.decision : "ESCALATE";
            envelope.logEdit("word_commands", {
              count: wordCommands.length,
              decision,
              zone: envelope.currentZone,
            }, decision);

            if (decision === "ALLOW" || decision === "QUARANTINE") {
              ws.send(JSON.stringify({ type: "word_commands", commands: wordCommands }));
            } else {
              ws.send(JSON.stringify({
                type: "error",
                message: `Word commands held — governance decision: ${decision}`,
              }));
            }
          }

          if (editorCommands.length > 0) {
            ws.send(JSON.stringify({ type: "editor_commands", commands: editorCommands }));
          }

          envelope.conversationHistory = conversationHistory;
          envelope.recordAssistantMessage(fullResponse, {
            provider: result.label,
            model: result.model,
            fallback: result.fallback,
            wordCommands,
            editorCommands,
          });
          envelope.save();

          ws.send(JSON.stringify({ type: "stream_end" }));
        } catch (err) {
          envelope.recordEvent("error", {
            message: err.message,
          });
          ws.send(JSON.stringify({ type: "error", message: err.message }));
        }
      } else if (msg.type === "clear") {
        conversationHistory = [];
        syncedDocumentContext = "";
        envelope.clearConversation();
        ws.send(JSON.stringify({ type: "cleared" }));
      } else if (msg.type === "promote") {
        const promoted = envelope.promote();
        envelope.save();
        ws.send(JSON.stringify({
          type: "zone_update",
          zone: envelope.currentZone,
          promoted,
          session_id: envelope.sessionId,
        }));
      }
    });

    ws.on("close", () => {
      envelope.conversationHistory = conversationHistory;
      envelope.save();
      envelope.recordEvent("disconnect", {});
      console.log(`[bridge] Client disconnected — session=${sessionId}`);
    });
  });

  return wss;
}

function createBridgeServer(options = {}) {
  const useHttps = options.useHttps !== false;
  const server = useHttps
    ? https.createServer(loadCerts(), app)
    : http.createServer(app);
  const wss = attachWebSocketBridge(server, options);
  return { server, wss };
}

function startBridgeServer(options = {}) {
  const { server, wss } = createBridgeServer(options);
  const port = options.port ?? PORT;
  const protocol = options.useHttps === false ? "http" : "https";
  const wsProtocol = options.useHttps === false ? "ws" : "wss";

  return new Promise((resolve) => {
    server.listen(port, () => {
      const boundPort = server.address()?.port ?? port;
      console.log(`\n  SCBE Word Add-in Bridge`);
      console.log(`  ${protocol}://localhost:${boundPort}/taskpane/taskpane.html`);
      console.log(`  WebSocket: ${wsProtocol}://localhost:${boundPort}`);
      console.log(`  Press Ctrl+C to stop\n`);
      resolve({ server, wss, port: boundPort });
    });
  });
}

if (require.main === module) {
  startBridgeServer().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = {
  app,
  attachWebSocketBridge,
  createBridgeServer,
  extractCommands,
  getConfiguredProviders,
  loadCerts,
  startBridgeServer,
};
