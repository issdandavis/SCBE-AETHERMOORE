/**
 * @file session_envelope.js
 * @module word-addin/session-envelope
 * @layer Layer 13
 * @component Polly Pad Session Envelope
 *
 * Every edit, prompt, and command flows through this envelope.
 * The envelope binds the Word add-in to a Polly Pad session so that:
 *   - All conversation state persists across reconnects
 *   - Every edit is logged with governance decision and zone
 *   - Inter-agent communication goes through crosstalk packets
 *   - Antivirus scanning gates command execution
 *
 * This is the "one narrow governed lane" — nothing bypasses it.
 */

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { execFileSync } = require("child_process");

// ─── Constants ───

const PAD_ROOT = path.join(
  process.env.SCBE_PAD_ROOT ||
    path.resolve(__dirname, "..", "..", ".scbe", "polly-pads")
);

const AGENT_ID = "agent.word-addin";
const DOC_CONTEXT_LIMIT = 8000; // chars
const MAX_EDIT_LOG = 500; // keep last N edits per session

// Threat patterns (subset of agents/antivirus_membrane.py)
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

// ─── Session Envelope ───

class SessionEnvelope {
  constructor(padId, sessionId) {
    this.padId = padId;
    this.agentId = AGENT_ID;
    this.sessionId = sessionId;
    this.createdAt = new Date().toISOString();
    this.updatedAt = this.createdAt;
    this.documentTitle = "";
    this.documentContext = "";
    this.conversationHistory = [];
    this.edits = [];
    this.currentZone = "HOT"; // HOT = draft, SAFE = execution
    this.coherence = 1.0;
    this.dStar = 0.0;
    this.hEff = 1.0;
    this.lastCrosstalkPacketId = null;
  }

  // ─── Persistence ───

  /** Directory for this agent's pad storage. */
  get padDir() {
    return path.join(PAD_ROOT, this.agentId);
  }

  /** Path to the session file. */
  get sessionPath() {
    return path.join(this.padDir, `session-${this.sessionId}.json`);
  }

  /** Save envelope to disk. */
  save() {
    fs.mkdirSync(this.padDir, { recursive: true });
    this.updatedAt = new Date().toISOString();

    // Trim edit log to prevent unbounded growth
    if (this.edits.length > MAX_EDIT_LOG) {
      this.edits = this.edits.slice(-MAX_EDIT_LOG);
    }

    const payload = {
      pad_id: this.padId,
      agent_id: this.agentId,
      session_id: this.sessionId,
      created_at: this.createdAt,
      updated_at: this.updatedAt,
      document_title: this.documentTitle,
      document_context: this.documentContext.slice(0, DOC_CONTEXT_LIMIT),
      conversation_history: this.conversationHistory,
      edits: this.edits,
      current_zone: this.currentZone,
      governance: {
        coherence: this.coherence,
        d_star: this.dStar,
        h_eff: this.hEff,
      },
      last_crosstalk_packet_id: this.lastCrosstalkPacketId,
    };

    const json = JSON.stringify(payload, null, 2);
    const tmp = this.sessionPath + ".tmp";
    fs.writeFileSync(tmp, json, "utf-8");
    fs.renameSync(tmp, this.sessionPath); // atomic on same filesystem
  }

  /** Load envelope from disk. Returns null if not found. */
  static load(agentId, sessionId) {
    const sessionPath = path.join(
      PAD_ROOT,
      agentId,
      `session-${sessionId}.json`
    );
    if (!fs.existsSync(sessionPath)) return null;

    try {
      const data = JSON.parse(fs.readFileSync(sessionPath, "utf-8"));
      const env = new SessionEnvelope(data.pad_id, data.session_id);
      env.agentId = data.agent_id || AGENT_ID;
      env.createdAt = data.created_at;
      env.updatedAt = data.updated_at;
      env.documentTitle = data.document_title || "";
      env.documentContext = data.document_context || "";
      env.conversationHistory = data.conversation_history || [];
      env.edits = data.edits || [];
      env.currentZone = data.current_zone || "HOT";
      env.coherence = data.governance?.coherence ?? 1.0;
      env.dStar = data.governance?.d_star ?? 0.0;
      env.hEff = data.governance?.h_eff ?? 1.0;
      env.lastCrosstalkPacketId = data.last_crosstalk_packet_id || null;
      return env;
    } catch {
      return null;
    }
  }

  // ─── Governance Gate ───

  /**
   * Score text through the lightweight pipeline (calls scbe.py).
   * Updates this envelope's governance fields.
   */
  scoreInput(text) {
    try {
      const scbePath = path.resolve(__dirname, "..", "..", "scbe.py");
      const result = execFileSync(
        "python",
        [scbePath, "pipeline", "run", "--json", "--text", text],
        { timeout: 5000, encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"] }
      );
      const score = JSON.parse(result);
      this.dStar = score.d_star;
      this.hEff = score.H_eff;
      return score;
    } catch {
      // If scoring fails, don't block — degrade to QUARANTINE-level defaults
      this.dStar = 1.0;
      this.hEff = 0.5;
      return { decision: "QUARANTINE", d_star: 1.0, H_eff: 0.5 };
    }
  }

  /**
   * Scan text for threats (inline JS port of antivirus_membrane patterns).
   * Returns { clean: bool, hits: string[] }
   */
  scanThreats(text) {
    const hits = [];
    for (const pattern of THREAT_PATTERNS) {
      if (pattern.test(text)) {
        hits.push(pattern.source);
      }
    }
    return { clean: hits.length === 0, hits };
  }

  /**
   * Full governance check: scan + score + decide.
   * Returns { allowed: bool, decision: string, threats: object, score: object }
   */
  governanceCheck(text) {
    const threats = this.scanThreats(text);
    const score = this.scoreInput(text);

    // Threat hits override score decision
    let decision = score.decision;
    if (!threats.clean) {
      decision = threats.hits.length >= 2 ? "DENY" : "ESCALATE";
    }

    const allowed = decision === "ALLOW" || decision === "QUARANTINE";
    return { allowed, decision, threats, score };
  }

  // ─── Edit Logging ───

  /**
   * Log an edit action to the envelope's audit trail.
   */
  logEdit(action, payload, decision) {
    this.edits.push({
      timestamp: new Date().toISOString(),
      action,
      payload_summary:
        typeof payload === "string"
          ? payload.slice(0, 200)
          : JSON.stringify(payload).slice(0, 200),
      zone: this.currentZone,
      decision,
    });
  }

  // ─── Zone Management ───

  /** Promote from HOT to SAFE (requires clean governance check). */
  promote() {
    if (this.currentZone === "SAFE") return true;
    if (this.hEff >= 0.6 && this.dStar < 1.5) {
      this.currentZone = "SAFE";
      this.logEdit("zone_promotion", { from: "HOT", to: "SAFE" }, "ALLOW");
      return true;
    }
    return false;
  }

  /** Demote from SAFE to HOT. */
  demote() {
    if (this.currentZone === "HOT") return;
    this.currentZone = "HOT";
    this.logEdit("zone_demotion", { from: "SAFE", to: "HOT" }, "QUARANTINE");
  }

  // ─── Crosstalk ───

  /**
   * Emit a crosstalk packet via the relay (calls Python).
   * Returns packet_id or null on failure.
   */
  emitCrosstalk(recipient, intent, summary, proof = []) {
    try {
      const relayPath = path.resolve(
        __dirname,
        "..",
        "..",
        "scripts",
        "system",
        "crosstalk_relay.py"
      );
      const packet = {
        sender: this.agentId,
        recipient,
        intent,
        status: "in_progress",
        repo: "SCBE-AETHERMOORE",
        branch: "book/six-tongues-protocol-v1",
        task_id: this.sessionId,
        summary,
        proof,
        risk: this.hEff >= 0.6 ? "low" : this.hEff >= 0.3 ? "medium" : "high",
      };

      const result = execFileSync(
        "python",
        [
          "-c",
          `
import sys, json
sys.path.insert(0, ${JSON.stringify(path.resolve(__dirname, "..", ".."))})
from scripts.system.crosstalk_relay import emit_packet
packet = json.loads(${JSON.stringify(JSON.stringify(packet))})
result = emit_packet(**packet)
print(json.dumps({"packet_id": result.get("packet_id", "unknown")}))
`,
        ],
        { timeout: 10000, encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"] }
      );

      const parsed = JSON.parse(result);
      this.lastCrosstalkPacketId = parsed.packet_id;
      return parsed.packet_id;
    } catch {
      return null;
    }
  }
}

// ─── Factory ───

/**
 * Load an existing session or create a new one.
 */
function loadOrCreateSession(sessionId) {
  const existing = SessionEnvelope.load(AGENT_ID, sessionId);
  if (existing) return existing;

  const padId = `pad-${crypto.randomBytes(6).toString("hex")}`;
  const envelope = new SessionEnvelope(padId, sessionId);
  envelope.save();
  return envelope;
}

/**
 * Generate a session ID from the current date + random suffix.
 */
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
  AGENT_ID,
};
