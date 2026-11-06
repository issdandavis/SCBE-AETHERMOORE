'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { scbeHome } = require('./provider-registry');
const {
  appendChainedReceipt,
  multiHashJson,
  verifyReceiptFile,
} = require('./multi-hash-receipt');

const SESSION_SCHEMA = 'scbe_agent_session_v1';
const MAX_MESSAGES = 240;
const MAX_MESSAGE_CHARS = 80_000;
const MAX_SUMMARY_CHARS = 20_000;

function canonicalWorkspacePath(workspaceRoot, options = {}) {
  const platform = options.platform || process.platform;
  const resolved = path.resolve(workspaceRoot);
  return platform === 'win32' ? resolved.toLowerCase() : resolved;
}

function workspaceKey(workspaceRoot, options = {}) {
  return crypto
    .createHash('sha256')
    .update(canonicalWorkspacePath(workspaceRoot, options), 'utf8')
    .digest('hex')
    .slice(0, 16);
}

function sessionDirectory(workspaceRoot, options = {}) {
  return path.join(scbeHome(options.env, options.home), 'sessions', workspaceKey(workspaceRoot, options));
}

function receiptPath(workspaceRoot, options = {}) {
  return path.join(scbeHome(options.env, options.home), 'receipts', `${workspaceKey(workspaceRoot, options)}.jsonl`);
}

function safeSessionId(value) {
  const id = String(value || '').trim();
  if (!/^[a-zA-Z0-9._-]{1,96}$/.test(id)) throw new Error('invalid session id');
  return id;
}

function makeSessionId(now = new Date()) {
  const stamp = now.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
  return `${stamp}-${crypto.randomBytes(3).toString('hex')}`;
}

function prepareMessages(messages) {
  return (Array.isArray(messages) ? messages : [])
    .filter((message) => message && typeof message === 'object' && message.role)
    .map((message) => {
      const next = { ...message, role: String(message.role) };
      if (typeof next.content === 'string' && next.content.length > MAX_MESSAGE_CHARS) {
        next.content = `${next.content.slice(0, MAX_MESSAGE_CHARS)}\n...[truncated while saving]`;
      }
      return next;
    });
}

function toolCallIds(message) {
  if (!Array.isArray(message.tool_calls) || !message.tool_calls.length) return [];
  return message.tool_calls.map((call) => String(call?.id || '')).filter(Boolean);
}

function analyzeTurn(messages) {
  if (!messages.length || messages[0].role !== 'user') return { valid: false, complete: false };
  let pending = null;
  let sawAssistant = false;
  for (let index = 1; index < messages.length; index += 1) {
    const message = messages[index];
    if (message.role === 'assistant') {
      if (pending?.size) return { valid: false, complete: false };
      const ids = toolCallIds(message);
      if (ids.length) {
        if (new Set(ids).size !== ids.length) return { valid: false, complete: false };
        pending = new Set(ids);
      } else {
        pending = null;
      }
      sawAssistant = true;
      continue;
    }
    if (message.role === 'tool') {
      const callId = String(message.tool_call_id || '');
      if (!pending?.has(callId)) return { valid: false, complete: false };
      pending.delete(callId);
      continue;
    }
    return { valid: false, complete: false };
  }
  const finalMessage = messages[messages.length - 1];
  return {
    valid: true,
    complete: sawAssistant && !pending?.size && finalMessage.role === 'assistant' && !toolCallIds(finalMessage).length,
  };
}

function splitTurns(messages) {
  const turns = [];
  const preamble = [];
  let current = null;
  for (const message of messages) {
    if (message.role === 'user') {
      if (current) turns.push(current);
      current = [message];
    } else if (current) {
      current.push(message);
    } else {
      preamble.push(message);
    }
  }
  if (current) turns.push(current);
  return { turns, preamble };
}

function normalizeMessageHistory(messages) {
  const prepared = prepareMessages(messages);
  if (prepared.length <= MAX_MESSAGES) return { messages: prepared, dropped: [] };

  const { turns, preamble } = splitTurns(prepared);
  const retained = [];
  let retainedCount = 0;
  let firstRetainedIndex = turns.length;

  for (let index = turns.length - 1; index >= 0; index -= 1) {
    const turn = turns[index];
    const analysis = analyzeTurn(turn);
    const isNewest = index === turns.length - 1;
    if (!analysis.valid || (!analysis.complete && !isNewest)) break;
    if (analysis.complete && retainedCount === 0 && turn.length > MAX_MESSAGES) break;
    if (retainedCount > 0 && retainedCount + turn.length > MAX_MESSAGES) break;

    // An in-flight newest turn may temporarily exceed the soft limit. A
    // completed oversized turn is compacted instead of splitting its protocol.
    retained.unshift(...turn);
    retainedCount += turn.length;
    firstRetainedIndex = index;
    if (retainedCount >= MAX_MESSAGES) break;
  }

  const droppedTurns = turns.slice(0, firstRetainedIndex).flat();
  return { messages: retained, dropped: [...preamble, ...droppedTurns] };
}

function normalizeMessages(messages) {
  return normalizeMessageHistory(messages).messages;
}

function mergeAutomaticSummary(existing, messages) {
  if (!messages.length) return String(existing || '');
  const compacted = deterministicSummary(messages);
  const merged = [String(existing || '').trim(), `Automatically compacted history:\n${compacted}`]
    .filter(Boolean)
    .join('\n\n');
  if (merged.length <= MAX_SUMMARY_CHARS) return merged;
  return `...[older summary omitted]\n${merged.slice(-(MAX_SUMMARY_CHARS - 29))}`;
}

function createSession(options = {}) {
  const now = options.now || new Date();
  return {
    schema_version: SESSION_SCHEMA,
    id: options.id || makeSessionId(now),
    workspace_root: path.resolve(options.workspaceRoot || process.cwd()),
    title: String(options.title || 'New conversation').slice(0, 120),
    created_at: now.toISOString(),
    updated_at: now.toISOString(),
    provider: options.provider || 'ollama',
    model: options.model || '',
    permission_mode: options.permissionMode || 'ask',
    summary: '',
    messages: [],
    tool_calls: 0,
  };
}

function sessionPath(workspaceRoot, id, options = {}) {
  return path.join(sessionDirectory(workspaceRoot, options), `${safeSessionId(id)}.json`);
}

function saveSession(session, options = {}) {
  const root = path.resolve(session.workspace_root || options.workspaceRoot || process.cwd());
  const filePath = sessionPath(root, session.id, options);
  const normalized = normalizeMessageHistory(session.messages);
  const next = {
    ...session,
    schema_version: SESSION_SCHEMA,
    workspace_root: root,
    updated_at: new Date().toISOString(),
    summary: mergeAutomaticSummary(session.summary, normalized.dropped),
    messages: normalized.messages,
  };
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const temporary = `${filePath}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(next, null, 2)}\n`, 'utf8');
  fs.renameSync(temporary, filePath);
  Object.assign(session, next);
  return filePath;
}

function loadSession(workspaceRoot, id, options = {}) {
  const filePath = sessionPath(workspaceRoot, id, options);
  const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  if (parsed.schema_version !== SESSION_SCHEMA) {
    throw new Error(`unsupported session schema: ${parsed.schema_version || 'missing'}`);
  }
  if (canonicalWorkspacePath(parsed.workspace_root, options) !== canonicalWorkspacePath(workspaceRoot, options)) {
    throw new Error('session belongs to a different workspace');
  }
  const normalized = normalizeMessageHistory(parsed.messages);
  return {
    ...parsed,
    summary: mergeAutomaticSummary(parsed.summary, normalized.dropped),
    messages: normalized.messages,
  };
}

function listSessions(workspaceRoot, options = {}) {
  const dir = sessionDirectory(workspaceRoot, options);
  if (!fs.existsSync(dir)) return [];
  const rows = [];
  for (const file of fs.readdirSync(dir).filter((name) => name.endsWith('.json'))) {
    try {
      const parsed = JSON.parse(fs.readFileSync(path.join(dir, file), 'utf8'));
      if (parsed.schema_version !== SESSION_SCHEMA) continue;
      rows.push({
        id: parsed.id,
        title: parsed.title || 'Conversation',
        updated_at: parsed.updated_at,
        created_at: parsed.created_at,
        provider: parsed.provider,
        model: parsed.model,
        messages: Array.isArray(parsed.messages) ? parsed.messages.length : 0,
        tool_calls: Number(parsed.tool_calls || 0),
      });
    } catch (_error) {
      // A corrupt session is ignored here; direct /resume <id> still reports it.
    }
  }
  return rows.sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at)));
}

function loadLatestSession(workspaceRoot, options = {}) {
  const latest = listSessions(workspaceRoot, options)[0];
  return latest ? loadSession(workspaceRoot, latest.id, options) : null;
}

function titleFromPrompt(prompt) {
  const clean = String(prompt || '')
    .replace(/\s+/g, ' ')
    .trim();
  return clean ? clean.slice(0, 72) : 'New conversation';
}

function deterministicSummary(messages, limit = 6000) {
  const relevant = prepareMessages(messages)
    .filter((message) => ['user', 'assistant'].includes(message.role))
    .filter((message) => message.role === 'user' || String(message.content || '').trim())
    .slice(-24)
    .map((message) => `${message.role}: ${String(message.content || '').replace(/\s+/g, ' ').slice(0, 700)}`)
    .join('\n');
  if (!relevant) return 'No conversation content.';
  return relevant.length <= limit ? relevant : `...[earlier turns omitted]\n${relevant.slice(-limit)}`;
}

function appendReceipt(workspaceRoot, receipt, options = {}) {
  const filePath = receiptPath(workspaceRoot, options);
  const argsHashes = multiHashJson(receipt.args || {});
  const resultHashes = multiHashJson(receipt.result || {});
  return appendChainedReceipt(
    filePath,
    {
      schema_version: 'scbe_agent_tool_event_v2',
      at: (options.now || new Date()).toISOString(),
      session_id: receipt.session_id || null,
      tool: receipt.tool || null,
      kind: receipt.kind || null,
      decision: receipt.decision || null,
      ok: receipt.ok === true,
      duration_ms: Number(receipt.duration_ms || 0),
      args_sha256: argsHashes.sha256,
      result_sha256: resultHashes.sha256,
      args_hashes: argsHashes,
      result_hashes: resultHashes,
      error: receipt.error ? String(receipt.error).slice(0, 500) : null,
    },
    { receiptType: 'agent_tool', now: options.now }
  );
}

function verifyReceiptLedger(workspaceRoot, options = {}) {
  const result = verifyReceiptFile(receiptPath(workspaceRoot, options));
  return {
    ...result,
    receipts: undefined,
  };
}

module.exports = {
  SESSION_SCHEMA,
  MAX_MESSAGES,
  canonicalWorkspacePath,
  workspaceKey,
  sessionDirectory,
  receiptPath,
  makeSessionId,
  createSession,
  saveSession,
  loadSession,
  listSessions,
  loadLatestSession,
  titleFromPrompt,
  deterministicSummary,
  normalizeMessages,
  appendReceipt,
  verifyReceiptLedger,
};
