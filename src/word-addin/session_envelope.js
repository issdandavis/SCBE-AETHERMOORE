/**
 * @file session_envelope.js
 * @module word-addin/session-envelope
 * @layer Layer 13
 * @component Polly Pad Session Envelope
 *
 * Governance logic lives here. Word is only a thin client.
 * The envelope persists conversation, document context, governance state,
 * and audit events inside the standard Polly Pad root:
 *
 *   .scbe/polly-pads/<agent-id>/
 *     manifest.json
 *     sessions/session-<id>.json
 *     sessions/session-<id>.events.jsonl
 */

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { execFileSync } = require("child_process");

const DEFAULT_AGENT_ID = "agent.word-addin";
const DEFAULT_SURFACE = "word-taskpane";
const DEFAULT_MODE = "COMMS";
const DOC_CONTEXT_LIMIT = 8000;
const MAX_EDIT_LOG = 500;
const MAX_MESSAGE_SUMMARY = 500;
const SCHEMA_VERSION = "polly-pad-session.v2";
const PAD_ROOT = path.resolve(
  process.env.SCBE_PAD_ROOT || path.join(__dirname, "..", "..", ".scbe", "polly-pads"),
);
const SUPPORTED_MODES = new Set(["ENGINEERING", "NAVIGATION", "SYSTEMS", "SCIENCE", "COMMS", "MISSION"]);

const THREAT_PATTERNS = [
  /ignore\s+(all\s+)?previous\s+instructions/i,
  /reveal\s+(your\s+)?system\s+prompt/i,
  /you\s+are\s+now\s+in\s+developer\s+mode/i,
  /pretend\s+you\s+have\s+no\s+restrictions/i,
  /act\s+as\s+if\s+you\s+have\s+no\s+guardrails/i,
  /powershell\s+-enc/i,
  /rm\s+-rf\s+\//,
  /curl\s+.*\|\s*sh/i,
  /wget\s+.*\|\s*bash/i,
  /eval\s*\(\s*atob/i,
];

function nowIso() {
  return new Date().toISOString();
}

function sanitizeToken(value, fallback) {
  const safe = `${value || ""}`
    .trim()
    .replace(/[^A-Za-z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return safe || fallback;
}

function sanitizeTitle(value) {
  return `${value || ""}`.trim().slice(0, 240);
}

function normalizeMode(value) {
  const normalized = `${value || DEFAULT_MODE}`.trim().toUpperCase();
  return SUPPORTED_MODES.has(normalized) ? normalized : DEFAULT_MODE;
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

function writeJson(filePath, payload) {
  ensureDir(path.dirname(filePath));
  const tmpPath = `${filePath}.tmp`;
  fs.writeFileSync(tmpPath, `${JSON.stringify(payload, null, 2)}\n`, "utf-8");
  fs.renameSync(tmpPath, filePath);
}

function appendJsonl(filePath, payload) {
  ensureDir(path.dirname(filePath));
  fs.appendFileSync(filePath, `${JSON.stringify(payload)}\n`, "utf-8");
}

function hashText(text) {
  return crypto.createHash("sha256").update(`${text || ""}`, "utf8").digest("hex");
}

function legacySessionPath(padDir, sessionId) {
  return path.join(padDir, `session-${sessionId}.json`);
}

class SessionEnvelope {
  constructor(padId, sessionId, options = {}) {
    this.schemaVersion = SCHEMA_VERSION;
    this.padId = padId;
    this.agentId = sanitizeToken(options.agentId, DEFAULT_AGENT_ID);
    this.surface = sanitizeToken(options.surface, DEFAULT_SURFACE);
    this.mode = normalizeMode(options.mode);
    this.sessionId = sanitizeToken(sessionId, generateSessionId());
    this.createdAt = nowIso();
    this.updatedAt = this.createdAt;
    this.documentTitle = sanitizeTitle(options.documentTitle);
    this.documentContext = "";
    this.documentHash = "";
    this.selectionHash = "";
    this.conversationHistory = [];
    this.edits = [];
    this.currentZone = "HOT";
    this.coherence = 1.0;
    this.dStar = 0.0;
    this.hEff = 1.0;
    this.syncCount = 0;
    this.userMessageCount = 0;
    this.assistantMessageCount = 0;
    this.clearCount = 0;
    this.wordCommandCount = 0;
    this.editorCommandCount = 0;
    this.fallbackCount = 0;
    this.lastProvider = null;
    this.lastModel = null;
    this.lastCrosstalkPacketId = null;
    this.lastUserMessage = "";
    this.lastAssistantMessage = "";
    this.repoName = options.repoName || "SCBE-AETHERMOORE";
    this.branchName = options.branchName || "";
  }

  get padDir() {
    return path.join(PAD_ROOT, this.agentId);
  }

  get manifestPath() {
    return path.join(this.padDir, "manifest.json");
  }

  get sessionsDir() {
    return path.join(this.padDir, "sessions");
  }

  get sessionPath() {
    return path.join(this.sessionsDir, `session-${this.sessionId}.json`);
  }

  get eventPath() {
    return path.join(this.sessionsDir, `session-${this.sessionId}.events.jsonl`);
  }

  getClientSummary() {
    return {
      session_id: this.sessionId,
      pad_id: this.padId,
      agent_id: this.agentId,
      surface: this.surface,
      mode: this.mode,
      zone: this.currentZone,
      document_title: this.documentTitle,
      updated_at: this.updatedAt,
      governance: {
        coherence: this.coherence,
        d_star: this.dStar,
        h_eff: this.hEff,
      },
      metrics: {
        sync_count: this.syncCount,
        user_messages: this.userMessageCount,
        assistant_messages: this.assistantMessageCount,
        clear_count: this.clearCount,
        word_command_count: this.wordCommandCount,
        editor_command_count: this.editorCommandCount,
        fallback_count: this.fallbackCount,
      },
    };
  }

  toJSON() {
    return {
      schema_version: this.schemaVersion,
      pad_id: this.padId,
      agent_id: this.agentId,
      surface: this.surface,
      mode: this.mode,
      session_id: this.sessionId,
      created_at: this.createdAt,
      updated_at: this.updatedAt,
      document_title: this.documentTitle,
      document_context: this.documentContext.slice(0, DOC_CONTEXT_LIMIT),
      document_hash: this.documentHash,
      selection_hash: this.selectionHash,
      conversation_history: this.conversationHistory,
      edits: this.edits,
      current_zone: this.currentZone,
      governance: {
        coherence: this.coherence,
        d_star: this.dStar,
        h_eff: this.hEff,
      },
      metrics: {
        sync_count: this.syncCount,
        user_messages: this.userMessageCount,
        assistant_messages: this.assistantMessageCount,
        clear_count: this.clearCount,
        word_command_count: this.wordCommandCount,
        editor_command_count: this.editorCommandCount,
        fallback_count: this.fallbackCount,
      },
      runtime: {
        last_provider: this.lastProvider,
        last_model: this.lastModel,
      },
      summary: {
        last_user_message: this.lastUserMessage,
        last_assistant_message: this.lastAssistantMessage,
      },
      last_crosstalk_packet_id: this.lastCrosstalkPacketId,
    };
  }

  ensureManifest() {
    ensureDir(this.padDir);
    ensureDir(this.sessionsDir);

    if (!fs.existsSync(this.manifestPath)) {
      writeJson(this.manifestPath, {
        agent_id: this.agentId,
        name: `Polly Pad (${this.surface})`,
        role: "pad-surface",
        owner: process.env.USERNAME || "local-owner",
        created_at: nowIso(),
        updated_at: nowIso(),
        storage: {
          max_bytes: 256 * 1024 * 1024,
          notes_count: 0,
          books_count: 0,
          apps_count: 0,
          sessions_count: 0,
          notes: [],
          books: [],
          apps: [],
          sessions: [],
        },
        utilities: [],
        flux_state_hint: "polly",
      });
    }
  }

  syncManifest() {
    this.ensureManifest();
    const manifest = readJson(this.manifestPath);
    manifest.storage = manifest.storage || {};
    manifest.storage.sessions = Array.isArray(manifest.storage.sessions) ? manifest.storage.sessions : [];

    const summary = {
      session_id: this.sessionId,
      surface: this.surface,
      mode: this.mode,
      zone: this.currentZone,
      created_at: this.createdAt,
      updated_at: this.updatedAt,
      title: this.documentTitle,
      path: path.relative(this.padDir, this.sessionPath).replace(/\\/g, "/"),
    };

    const existingIndex = manifest.storage.sessions.findIndex((entry) => entry.session_id === this.sessionId);
    if (existingIndex >= 0) {
      manifest.storage.sessions[existingIndex] = { ...manifest.storage.sessions[existingIndex], ...summary };
    } else {
      manifest.storage.sessions.push(summary);
    }

    manifest.storage.sessions_count = manifest.storage.sessions.length;
    manifest.updated_at = nowIso();
    writeJson(this.manifestPath, manifest);
  }

  recordEvent(type, payload = {}) {
    appendJsonl(this.eventPath, {
      event_id: `${this.sessionId}-${Date.now().toString(36)}-${crypto.randomBytes(4).toString("hex")}`,
      session_id: this.sessionId,
      agent_id: this.agentId,
      surface: this.surface,
      event_type: type,
      created_at: nowIso(),
      payload,
    });
  }

  save() {
    this.updatedAt = nowIso();
    if (this.edits.length > MAX_EDIT_LOG) {
      this.edits = this.edits.slice(-MAX_EDIT_LOG);
    }

    this.ensureManifest();
    writeJson(this.sessionPath, this.toJSON());
    writeJson(legacySessionPath(this.padDir, this.sessionId), this.toJSON());
    this.syncManifest();
  }

  updateMetadata(metadata = {}) {
    if (metadata.agentId) {
      this.agentId = sanitizeToken(metadata.agentId, this.agentId);
    }
    if (metadata.surface) {
      this.surface = sanitizeToken(metadata.surface, this.surface);
    }
    if (metadata.mode) {
      this.mode = normalizeMode(metadata.mode);
    }
    if (metadata.documentTitle) {
      this.documentTitle = sanitizeTitle(metadata.documentTitle);
    }
    if (metadata.branchName !== undefined) {
      this.branchName = `${metadata.branchName || ""}`;
    }
    if (metadata.repoName) {
      this.repoName = metadata.repoName;
    }
  }

  setDocumentContext(documentContext, metadata = {}) {
    this.updateMetadata(metadata);
    this.documentContext = `${documentContext || ""}`.slice(0, DOC_CONTEXT_LIMIT);
    this.documentHash = this.documentContext ? hashText(this.documentContext) : "";
    this.syncCount += 1;
    this.save();
    this.recordEvent("sync_context", {
      document_title: this.documentTitle,
      chars: this.documentContext.length,
      sha256: this.documentHash,
    });
  }

  recordUserMessage(content, selectionContext = "", metadata = {}) {
    this.updateMetadata(metadata);
    this.lastUserMessage = `${content || ""}`.slice(0, MAX_MESSAGE_SUMMARY);
    this.selectionHash = selectionContext ? hashText(selectionContext) : "";
    this.userMessageCount += 1;
    this.recordEvent("chat_user", {
      content: `${content || ""}`.slice(0, DOC_CONTEXT_LIMIT),
      selection_sha256: this.selectionHash,
    });
  }

  recordAssistantMessage(content, details = {}) {
    this.lastAssistantMessage = `${content || ""}`.slice(0, MAX_MESSAGE_SUMMARY);
    this.assistantMessageCount += 1;
    this.wordCommandCount += Array.isArray(details.wordCommands) ? details.wordCommands.length : 0;
    this.editorCommandCount += Array.isArray(details.editorCommands) ? details.editorCommands.length : 0;
    if (details.fallback) {
      this.fallbackCount += 1;
    }
    this.lastProvider = details.provider || null;
    this.lastModel = details.model || null;
    this.recordEvent("chat_assistant", {
      provider: details.provider || "",
      model: details.model || "",
      fallback: Boolean(details.fallback),
      word_command_count: Array.isArray(details.wordCommands) ? details.wordCommands.length : 0,
      editor_command_count: Array.isArray(details.editorCommands) ? details.editorCommands.length : 0,
    });
  }

  clearConversation() {
    this.conversationHistory = [];
    this.documentContext = "";
    this.documentHash = "";
    this.selectionHash = "";
    this.clearCount += 1;
    this.save();
    this.recordEvent("clear", {});
  }

  static fromData(data, options = {}) {
    const env = new SessionEnvelope(
      data.pad_id || `pad-${crypto.randomBytes(6).toString("hex")}`,
      data.session_id,
      {
        agentId: data.agent_id || options.agentId || DEFAULT_AGENT_ID,
        surface: data.surface || options.surface || DEFAULT_SURFACE,
        mode: data.mode || options.mode || DEFAULT_MODE,
        documentTitle: data.document_title || "",
      },
    );
    env.schemaVersion = data.schema_version || SCHEMA_VERSION;
    env.createdAt = data.created_at || env.createdAt;
    env.updatedAt = data.updated_at || env.updatedAt;
    env.documentContext = data.document_context || "";
    env.documentHash = data.document_hash || (env.documentContext ? hashText(env.documentContext) : "");
    env.selectionHash = data.selection_hash || "";
    env.conversationHistory = Array.isArray(data.conversation_history) ? data.conversation_history : [];
    env.edits = Array.isArray(data.edits) ? data.edits : [];
    env.currentZone = data.current_zone || "HOT";
    env.coherence = data.governance?.coherence ?? 1.0;
    env.dStar = data.governance?.d_star ?? 0.0;
    env.hEff = data.governance?.h_eff ?? 1.0;
    env.syncCount = data.metrics?.sync_count ?? 0;
    env.userMessageCount = data.metrics?.user_messages ?? 0;
    env.assistantMessageCount = data.metrics?.assistant_messages ?? 0;
    env.clearCount = data.metrics?.clear_count ?? 0;
    env.wordCommandCount = data.metrics?.word_command_count ?? 0;
    env.editorCommandCount = data.metrics?.editor_command_count ?? 0;
    env.fallbackCount = data.metrics?.fallback_count ?? 0;
    env.lastProvider = data.runtime?.last_provider ?? null;
    env.lastModel = data.runtime?.last_model ?? null;
    env.lastCrosstalkPacketId = data.last_crosstalk_packet_id || null;
    env.lastUserMessage = data.summary?.last_user_message || "";
    env.lastAssistantMessage = data.summary?.last_assistant_message || "";
    env.updateMetadata(options);
    return env;
  }

  static load(agentId, sessionId, options = {}) {
    const safeAgentId = sanitizeToken(agentId || options.agentId, DEFAULT_AGENT_ID);
    const safeSessionId = sanitizeToken(sessionId, generateSessionId());
    const padDir = path.join(PAD_ROOT, safeAgentId);
    const newPath = path.join(padDir, "sessions", `session-${safeSessionId}.json`);
    const oldPath = legacySessionPath(padDir, safeSessionId);
    const targetPath = fs.existsSync(newPath) ? newPath : oldPath;

    if (!fs.existsSync(targetPath)) {
      return null;
    }

    try {
      return SessionEnvelope.fromData(readJson(targetPath), { ...options, agentId: safeAgentId });
    } catch {
      return null;
    }
  }

  scoreInput(text) {
    try {
      const scbePath = path.resolve(__dirname, "..", "..", "scbe.py");
      const result = execFileSync("python", [scbePath, "pipeline", "run", "--json", "--text", text], {
        timeout: 5000,
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
      });
      const score = JSON.parse(result);
      this.dStar = score.d_star;
      this.hEff = score.H_eff;
      return score;
    } catch {
      this.dStar = 1.0;
      this.hEff = 0.5;
      return { decision: "QUARANTINE", d_star: 1.0, H_eff: 0.5 };
    }
  }

  scanThreats(text) {
    const hits = [];
    for (const pattern of THREAT_PATTERNS) {
      if (pattern.test(text)) {
        hits.push(pattern.source);
      }
    }
    return { clean: hits.length === 0, hits };
  }

  governanceCheck(text) {
    const threats = this.scanThreats(text);
    const score = this.scoreInput(text);
    let decision = score.decision;
    if (!threats.clean) {
      decision = threats.hits.length >= 2 ? "DENY" : "ESCALATE";
    }
    const allowed = decision === "ALLOW" || decision === "QUARANTINE";
    return { allowed, decision, threats, score };
  }

  logEdit(action, payload, decision) {
    this.edits.push({
      timestamp: nowIso(),
      action,
      payload_summary: typeof payload === "string" ? payload.slice(0, 200) : JSON.stringify(payload).slice(0, 200),
      zone: this.currentZone,
      decision,
    });
    this.recordEvent("edit", {
      action,
      decision,
      zone: this.currentZone,
    });
  }

  promote() {
    if (this.currentZone === "SAFE") {
      return true;
    }
    if (this.hEff >= 0.6 && this.dStar < 1.5) {
      this.currentZone = "SAFE";
      this.logEdit("zone_promotion", { from: "HOT", to: "SAFE" }, "ALLOW");
      return true;
    }
    return false;
  }

  demote() {
    if (this.currentZone === "HOT") {
      return;
    }
    this.currentZone = "HOT";
    this.logEdit("zone_demotion", { from: "SAFE", to: "HOT" }, "QUARANTINE");
  }

  emitCrosstalk(recipient, intent, summary, proof = []) {
    try {
      const result = execFileSync(
        "python",
        [
          "-c",
          `
import sys, json
sys.path.insert(0, ${JSON.stringify(path.resolve(__dirname, "..", ".."))})
from scripts.system.crosstalk_relay import emit_packet
packet = {
  "sender": ${JSON.stringify(this.agentId)},
  "recipient": ${JSON.stringify(recipient)},
  "intent": ${JSON.stringify(intent)},
  "status": "in_progress",
  "repo": ${JSON.stringify(this.repoName)},
  "branch": ${JSON.stringify(this.branchName)},
  "task_id": ${JSON.stringify(this.sessionId)},
  "summary": ${JSON.stringify(summary)},
  "proof": json.loads(${JSON.stringify(JSON.stringify(proof))}),
  "risk": ${JSON.stringify(this.hEff >= 0.6 ? "low" : this.hEff >= 0.3 ? "medium" : "high")},
}
result = emit_packet(**packet)
print(json.dumps({"packet_id": result.get("packet_id", "unknown")}))
`,
        ],
        { timeout: 10000, encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"] },
      );

      const parsed = JSON.parse(result);
      this.lastCrosstalkPacketId = parsed.packet_id;
      this.recordEvent("crosstalk_emit", {
        recipient,
        intent,
        packet_id: parsed.packet_id,
      });
      return parsed.packet_id;
    } catch {
      return null;
    }
  }
}

function loadOrCreateSession(sessionId, options = {}) {
  const safeSessionId = sanitizeToken(sessionId, generateSessionId());
  const agentId = sanitizeToken(options.agentId, DEFAULT_AGENT_ID);
  const existing = SessionEnvelope.load(agentId, safeSessionId, options);
  if (existing) {
    existing.updateMetadata(options);
    return existing;
  }

  const envelope = new SessionEnvelope(`pad-${crypto.randomBytes(6).toString("hex")}`, safeSessionId, {
    ...options,
    agentId,
  });
  envelope.save();
  envelope.recordEvent("session_started", {
    surface: envelope.surface,
    mode: envelope.mode,
    document_title: envelope.documentTitle,
  });
  return envelope;
}

function generateSessionId() {
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const suffix = crypto.randomBytes(4).toString("hex");
  return `sess-${date}-${suffix}`;
}

module.exports = {
  SessionEnvelope,
  loadOrCreateSession,
  generateSessionId,
  PAD_ROOT,
  AGENT_ID: DEFAULT_AGENT_ID,
};
