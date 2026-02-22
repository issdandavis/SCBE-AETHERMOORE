import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { decode, detectTongue, encode, TONGUE_CODES } from '../../dist/src/tokenizer/ss1.js';
import { BRAIN_DIMENSIONS, applyGoldenWeighting, safePoincareEmbed, vectorNorm } from '../../dist/src/ai_brain/index.js';
import { promises as fs } from 'fs';
import { createHash } from 'crypto';
import path from 'path';
import { fileURLToPath } from 'url';
import { execFile } from 'child_process';
import { promisify } from 'util';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const MAP_ROOM_DIR = path.join(REPO_ROOT, 'docs', 'map-room');
const MAP_ROOM_LATEST = path.join(MAP_ROOM_DIR, 'session_handoff_latest.md');
const TRUST_STATES = ['T0', 'T1', 'T2', 'T3', 'T4'];
const SAFE_OPS = new Set(['config.read', 'audit.export', 'diagnostics.run']);
const PHASE_STEP = Math.PI / 3;
const TONGUE_WEIGHTS = {
  KO: 1.0,
  AV: 1.618,
  RU: 2.618,
  CA: 4.236,
  UM: 6.854,
  DR: 11.09,
};
const RING_ORDER = { core: 0, inner: 1, middle: 2, outer: 3, edge: 4 };
const execFileAsync = promisify(execFile);

const server = new Server(
  {
    name: 'scbe-mcp-server',
    version: '0.1.0',
  },
  {
    capabilities: {
      tools: {},
    },
  },
);

function normalizeTongue(value) {
  if (typeof value !== 'string') return null;
  const v = value.toUpperCase();
  return TONGUE_CODES.includes(v) ? v : null;
}

function asText(value) {
  if (value === undefined || value === null) return '';
  return String(value);
}

function asNumber(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function asBoolean(value, fallback) {
  if (typeof value === 'boolean') return value;
  if (value === undefined || value === null) return fallback;
  const s = String(value).toLowerCase().trim();
  if (s === 'true') return true;
  if (s === 'false') return false;
  return fallback;
}

function canonicalStringify(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map((v) => canonicalStringify(v)).join(',')}]`;
  const record = value;
  const keys = Object.keys(record).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${canonicalStringify(record[k])}`).join(',')}}`;
}

function sha512Hex(value) {
  return createHash('sha512').update(canonicalStringify(value)).digest('hex');
}

function sha256Hex(value) {
  return createHash('sha256').update(canonicalStringify(value)).digest('hex');
}

function stripHtml(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function isTlsIssuerCertError(error) {
  const code = error?.cause?.code || error?.code || '';
  const message = String(error?.cause?.message || error?.message || '').toLowerCase();
  return code === 'UNABLE_TO_GET_ISSUER_CERT_LOCALLY' || message.includes('unable to get local issuer certificate');
}

async function fetchViaCurl(url, method, headers, body, timeoutMs) {
  const marker = '__SCBE_CURL_META_9f4cf4__';
  const args = [
    '--silent',
    '--show-error',
    '--location',
    '--max-time',
    String(Math.max(1, Math.ceil(timeoutMs / 1000))),
    '--request',
    method,
  ];

  for (const [key, value] of Object.entries(headers)) {
    if (value === undefined || value === null) continue;
    args.push('--header', `${key}: ${String(value)}`);
  }

  if (body !== undefined && method !== 'GET' && method !== 'HEAD') {
    args.push('--data-binary', body);
  }

  args.push('--write-out', `${marker}%{http_code}|%{content_type}`);
  args.push(url);

  const { stdout } = await execFileAsync('curl', args, {
    encoding: 'utf8',
    windowsHide: true,
    maxBuffer: 16 * 1024 * 1024,
  });

  const markerIndex = stdout.lastIndexOf(marker);
  if (markerIndex < 0) {
    throw new Error('curl fallback response missing metadata marker');
  }

  const responseText = stdout.slice(0, markerIndex);
  const meta = stdout.slice(markerIndex + marker.length).trim();
  const [statusRaw, contentTypeRaw = ''] = meta.split('|');
  const status = Number(statusRaw);

  if (!Number.isFinite(status)) {
    throw new Error(`curl fallback invalid status code: ${statusRaw}`);
  }

  return {
    status,
    statusText: '',
    ok: status >= 200 && status <= 299,
    contentType: contentTypeRaw.trim(),
    responseText,
  };
}

function normalizeContext6(value) {
  const raw = Array.isArray(value) ? value : [];
  const out = [];
  for (let i = 0; i < 6; i++) out.push(asNumber(raw[i], 0));
  return out;
}

function classifyRing(context6) {
  const bounded = context6.map((x) => (Math.tanh(x / 5) + 1) / 2);
  const radius = bounded.reduce((acc, x) => acc + x, 0) / Math.max(1, bounded.length);
  if (radius < 0.3) return 'core';
  if (radius < 0.5) return 'inner';
  if (radius < 0.7) return 'middle';
  if (radius < 0.9) return 'outer';
  return 'edge';
}

function classifyPath(context6) {
  const triadNorm = Math.sqrt(context6[0] ** 2 + context6[1] ** 2 + context6[2] ** 2);
  return triadNorm < 0.95 ? 'interior' : 'exterior';
}

function normalizeVector21(value) {
  if (!Array.isArray(value)) throw new Error('vector must be an array');
  if (value.length !== BRAIN_DIMENSIONS) throw new Error(`vector must contain exactly ${BRAIN_DIMENSIONS} numeric entries`);
  const out = value.map((v) => asNumber(v, Number.NaN));
  if (out.some((v) => !Number.isFinite(v))) throw new Error('vector must contain finite numeric entries');
  return out;
}

function xorWithSeed(buf, seed) {
  const src = Buffer.from(buf);
  if (src.length === 0) return src;
  const out = Buffer.alloc(src.length);
  let counter = 0;
  let offset = 0;
  while (offset < src.length) {
    const block = createHash('sha256')
      .update(seed)
      .update(String(counter))
      .digest();
    const n = Math.min(block.length, src.length - offset);
    for (let i = 0; i < n; i++) out[offset + i] = src[offset + i] ^ block[i];
    offset += n;
    counter += 1;
  }
  return out;
}

function splitSpellTokens(spellText) {
  return asText(spellText)
    .trim()
    .split(/\s+/)
    .filter((x) => x.length > 0);
}

function deriveEggSeed(primaryTongue, hatchCondition, context6) {
  return createHash('sha256')
    .update('SCBE_SACRED_EGG_V1')
    .update(primaryTongue)
    .update(canonicalStringify(hatchCondition))
    .update(canonicalStringify(context6))
    .digest();
}

function normalizeTongueList(value) {
  const list = Array.isArray(value) ? value : [];
  const unique = new Set();
  for (const item of list) {
    const tg = normalizeTongue(item);
    if (tg) unique.add(tg);
  }
  return [...unique];
}

function ritualWeight(tongue) {
  return TONGUE_WEIGHTS[tongue] ?? 0;
}

function deterministicNoiseBytes(length, seedText) {
  const out = Buffer.alloc(Math.max(1, length));
  let offset = 0;
  let counter = 0;
  while (offset < out.length) {
    const block = createHash('sha256')
      .update(seedText)
      .update(String(counter))
      .digest();
    const n = Math.min(block.length, out.length - offset);
    block.copy(out, offset, 0, n);
    offset += n;
    counter += 1;
  }
  return out;
}

function parseEggInput(value) {
  if (typeof value === 'string') return JSON.parse(value);
  if (value && typeof value === 'object') return value;
  throw new Error('egg_json must be an object or JSON string');
}

function normalizePathHistory(value) {
  const list = Array.isArray(value) ? value : [];
  return list
    .map((step) => asText(step?.ring).toLowerCase())
    .filter((ring) => Object.prototype.hasOwnProperty.call(RING_ORDER, ring));
}

function isStrictlyInward(pathHistory) {
  if (pathHistory.length < 1) return false;
  for (let i = 0; i < pathHistory.length - 1; i++) {
    if (RING_ORDER[pathHistory[i]] <= RING_ORDER[pathHistory[i + 1]]) return false;
  }
  return true;
}

export function scbeStateEmit21D(args = {}) {
  const vector21d = normalizeVector21(args.vector ?? args.state_vector);
  const weighted = asBoolean(args.apply_golden_weighting, false) ? applyGoldenWeighting(vector21d) : null;
  const poincare21d = safePoincareEmbed(vector21d);
  const payload = {
    schema_version: 'scbe-21d-v1',
    emitted_at: new Date().toISOString(),
    decision: asText(args.decision || ''),
    confidence: asNumber(args.confidence, 0),
    vector_21d: vector21d,
    blocks: {
      tongue_position: vector21d.slice(0, 6),
      phase: vector21d.slice(6, 12),
      telemetry: vector21d.slice(12, BRAIN_DIMENSIONS),
    },
    projections: {
      poincare_21d: poincare21d,
      poincare_norm: vectorNorm(poincare21d),
      radial_norm_6d: vectorNorm(poincare21d.slice(0, 6)),
      inside_poincare_ball: vectorNorm(poincare21d) < 1,
    },
    weighted_21d: weighted,
    metadata: typeof args.metadata === 'object' && args.metadata !== null ? args.metadata : {},
  };
  payload.hashes = {
    state_sha256: sha256Hex(payload.vector_21d),
    state_sha512: sha512Hex({ vector_21d: payload.vector_21d, decision: payload.decision }),
  };
  payload.state_id = payload.hashes.state_sha256.slice(0, 16);
  return payload;
}

export function scbeSacredEggCreate(args = {}) {
  const payloadB64 = asText(args.payload_b64).trim();
  if (!payloadB64) throw new Error('Missing required field: payload_b64');
  const payload = Buffer.from(payloadB64, 'base64');
  const primaryTongue = normalizeTongue(args.primary_tongue) ?? 'KO';
  const glyph = asText(args.glyph || '◇');
  const hatchCondition = typeof args.hatch_condition === 'object' && args.hatch_condition !== null ? args.hatch_condition : {};
  const context6 = normalizeContext6(args.context);
  const seed = deriveEggSeed(primaryTongue, hatchCondition, context6);
  const ciphertext = xorWithSeed(payload, seed);
  const pathClass = classifyPath(context6);
  const ring = classifyRing(context6);
  const attest = {
    ritual_version: 'sacred-eggs-v1',
    ring,
    path: pathClass,
    context_sha256: sha256Hex(context6),
    payload_sha256: createHash('sha256').update(payload).digest('hex'),
    created_at_unix: Math.floor(Date.now() / 1000),
  };
  const yolkBase = {
    ct_k: createHash('sha256').update(seed).update('ct_k').digest('base64'),
    ct_spec: ciphertext.toString('base64'),
    attest,
  };
  const yolk_ct = {
    ...yolkBase,
    sig: createHash('sha256').update(canonicalStringify(yolkBase)).digest('base64'),
  };
  const eggCore = {
    primary_tongue: primaryTongue,
    glyph,
    hatch_condition: hatchCondition,
    yolk_ct,
  };
  return {
    egg_id: createHash('sha256').update(canonicalStringify(eggCore)).digest('hex').slice(0, 16),
    ...eggCore,
  };
}

export function scbeSacredEggHatch(args = {}) {
  const egg = parseEggInput(args.egg_json ?? args.egg);
  const primaryTongue = normalizeTongue(egg.primary_tongue);
  if (!primaryTongue) throw new Error('egg_json.primary_tongue is invalid');
  const agentTongue = normalizeTongue(args.agent_tongue);
  if (!agentTongue) throw new Error('Invalid or missing agent_tongue. Expected one of KO/AV/RU/CA/UM/DR');
  const hatchCondition = typeof egg.hatch_condition === 'object' && egg.hatch_condition !== null ? egg.hatch_condition : {};
  const yolk = egg.yolk_ct ?? {};
  const ctSpec = Buffer.from(asText(yolk.ct_spec || ''), 'base64');
  if (!ctSpec.length) throw new Error('egg_json.yolk_ct.ct_spec is required');
  const context6 = normalizeContext6(args.context ?? args.current_context);
  const currentRing = classifyRing(context6);
  const currentPath = classifyPath(context6);
  const ritualMode = asText(args.ritual_mode || 'solitary').trim().toLowerCase();
  const additionalTongues = normalizeTongueList(args.additional_tongues);
  const pathHistory = normalizePathHistory(args.path_history);

  let sealedReason = null;
  const requiredPath = asText(hatchCondition.path || '').toLowerCase();
  const requiredRing = asText(hatchCondition.ring || '').toLowerCase();
  if (requiredPath && requiredPath !== currentPath) {
    sealedReason = 'PATH_MISMATCH';
  } else if (requiredRing && requiredRing !== currentRing) {
    sealedReason = 'RING_MISMATCH';
  } else if (ritualMode === 'solitary') {
    if (agentTongue !== primaryTongue) sealedReason = 'TONGUE_MISMATCH';
  } else if (ritualMode === 'triadic') {
    const active = new Set([primaryTongue, agentTongue, ...additionalTongues]);
    const minTongues = Math.max(1, Math.floor(asNumber(hatchCondition.min_tongues, 3)));
    const minWeight = asNumber(hatchCondition.min_weight, 10.0);
    const totalWeight = [...active].reduce((acc, tongue) => acc + ritualWeight(tongue), 0);
    if (active.size < minTongues) sealedReason = 'INSUFFICIENT_TONGUES';
    else if (totalWeight < minWeight) sealedReason = 'INSUFFICIENT_WEIGHT';
  } else if (ritualMode === 'ring_descent') {
    if (!isStrictlyInward(pathHistory)) sealedReason = 'INVALID_RING_PATH';
    else if (currentRing !== 'core') sealedReason = 'CORE_REQUIRED';
  } else {
    sealedReason = 'UNKNOWN_RITUAL_MODE';
  }

  const fail = (reasonCode) => {
    const seedText = canonicalStringify({ egg_id: egg.egg_id || '', reasonCode, context6, agentTongue });
    const noiseBytes = deterministicNoiseBytes(ctSpec.length, seedText);
    return {
      success: false,
      reason: 'sealed',
      reason_code: reasonCode,
      tokens: splitSpellTokens(encode(noiseBytes, agentTongue, true)),
      attestation: null,
    };
  };

  if (sealedReason) return fail(sealedReason);

  const seed = deriveEggSeed(primaryTongue, hatchCondition, context6);
  const payload = xorWithSeed(ctSpec, seed);
  const payloadSha = createHash('sha256').update(payload).digest('hex');
  const attest = yolk.attest ?? {};
  if (asText(attest.context_sha256) && asText(attest.context_sha256) !== sha256Hex(context6)) {
    return fail('CONTEXT_BINDING_FAILED');
  }
  if (asText(attest.payload_sha256) && asText(attest.payload_sha256) !== payloadSha) {
    return fail('PAYLOAD_INTEGRITY_FAILED');
  }

  const primaryTokens = splitSpellTokens(encode(payload, primaryTongue, true));
  if (agentTongue === primaryTongue) {
    return {
      success: true,
      reason: 'hatched',
      tokens: primaryTokens,
      payload_b64: payload.toString('base64'),
      attestation: { ...attest, xlate: null },
    };
  }

  const translatedTokens = splitSpellTokens(encode(payload, agentTongue, true));
  const srcIndex = Math.max(0, TONGUE_CODES.indexOf(primaryTongue));
  const dstIndex = Math.max(0, TONGUE_CODES.indexOf(agentTongue));
  const phaseDelta = ((dstIndex - srcIndex + 6) % 6) * PHASE_STEP;

  return {
    success: true,
    reason: 'hatched',
    tokens: translatedTokens,
    payload_b64: payload.toString('base64'),
    attestation: {
      ...attest,
      xlate: {
        src: primaryTongue,
        dst: agentTongue,
        phase_delta: phaseDelta,
        weight_ratio: ritualWeight(agentTongue) / Math.max(ritualWeight(primaryTongue), 1e-12),
        payload_sha256: payloadSha,
      },
    },
  };
}

function evaluateTrustState(ctx) {
  if (!ctx.integrity_ok) return 'T4';
  if (ctx.key_rotation_needed) return 'T3';
  if (!ctx.manifest_current) return 'T2';
  if (!ctx.time_trusted) return 'T1';
  return 'T0';
}

function getThresholdsForState(trust, thresholdInput = {}) {
  const base = {
    coherence_min: asNumber(thresholdInput.coherence_min, 0.6),
    conflict_max: asNumber(thresholdInput.conflict_max, 0.3),
    drift_max: asNumber(thresholdInput.drift_max, 0.2),
    wall_cost_max: asNumber(thresholdInput.wall_cost_max, 0.8),
  };

  const staleFactor = 1.5;
  const strictFactor = 1.25;

  if (trust === 'T1') {
    return {
      coherence_min: Math.min(base.coherence_min * strictFactor, 1.0),
      conflict_max: base.conflict_max / strictFactor,
      drift_max: base.drift_max / strictFactor,
      wall_cost_max: base.wall_cost_max / strictFactor,
    };
  }

  if (trust === 'T2') {
    return {
      coherence_min: Math.min(base.coherence_min * staleFactor, 1.0),
      conflict_max: base.conflict_max / staleFactor,
      drift_max: base.drift_max / staleFactor,
      wall_cost_max: base.wall_cost_max / staleFactor,
    };
  }

  if (trust === 'T3') {
    return {
      coherence_min: 0.99,
      conflict_max: 0.01,
      drift_max: 0.01,
      wall_cost_max: 0.05,
    };
  }

  if (trust === 'T4') {
    return {
      coherence_min: Number.POSITIVE_INFINITY,
      conflict_max: 0,
      drift_max: 0,
      wall_cost_max: 0,
    };
  }

  return base;
}

function evaluateFailClosed(failClosedCheck, action) {
  if (!failClosedCheck.laws_present || !failClosedCheck.laws_hash_valid) {
    return { pass: SAFE_OPS.has(action), reason: 'LAWS_MISSING_OR_CORRUPT' };
  }
  if (!failClosedCheck.manifest_present || !failClosedCheck.manifest_sig_ok) {
    return { pass: SAFE_OPS.has(action), reason: 'MANIFEST_INVALID' };
  }
  if (!failClosedCheck.keys_present) {
    return { pass: SAFE_OPS.has(action), reason: 'KEYS_MISSING' };
  }
  if (!failClosedCheck.audit_intact) {
    return { pass: SAFE_OPS.has(action), reason: 'AUDIT_CORRUPTED' };
  }
  if (!failClosedCheck.voxel_root_ok) {
    return { pass: SAFE_OPS.has(action), reason: 'VOXEL_ROOT_MISMATCH' };
  }
  return { pass: true };
}

function decideOffline(args) {
  const action = asText(args.action);
  const trustContextInput = args.trust_context ?? {};
  const failClosedInput = args.fail_closed_check ?? {};
  const scalarsInput = args.scalars ?? {};

  const failClosedCheck = {
    laws_present: asBoolean(failClosedInput.laws_present, true),
    laws_hash_valid: asBoolean(failClosedInput.laws_hash_valid, true),
    manifest_present: asBoolean(failClosedInput.manifest_present, true),
    manifest_sig_ok: asBoolean(failClosedInput.manifest_sig_ok, true),
    keys_present: asBoolean(failClosedInput.keys_present, true),
    audit_intact: asBoolean(failClosedInput.audit_intact, true),
    voxel_root_ok: asBoolean(failClosedInput.voxel_root_ok, true),
  };

  const trustContext = {
    keys_valid: asBoolean(trustContextInput.keys_valid, true),
    time_trusted: asBoolean(trustContextInput.time_trusted, true),
    manifest_current: asBoolean(trustContextInput.manifest_current, true),
    key_rotation_needed: asBoolean(trustContextInput.key_rotation_needed, false),
    integrity_ok: asBoolean(trustContextInput.integrity_ok, true),
  };

  const trustStateInput = asText(args.trust_state).toUpperCase();
  const trust = TRUST_STATES.includes(trustStateInput) ? trustStateInput : evaluateTrustState(trustContext);

  const failGate = evaluateFailClosed(failClosedCheck, action);
  if (!failGate.pass) {
    const proof = {
      inputs_hash: sha512Hex({ action, failClosedCheck }),
      laws_hash: asText(args.laws_hash || ''),
      manifest_hash: asText(args.manifest_hash || ''),
      state_root: asText(args.state_root || ''),
      timestamp_monotonic: asText(args.timestamp_monotonic || '0'),
      signature: null,
      signature_note: 'unsigned-local-eval',
    };
    return {
      decision: 'DENY',
      reason_codes: [failGate.reason ?? 'FAIL_CLOSED'],
      governance_scalars: {
        mm_coherence: 0,
        mm_conflict: 1,
        mm_drift: 1,
        wall_cost: 1,
        trust_level: 'T4',
      },
      thresholds_used: getThresholdsForState('T4', args.thresholds ?? {}),
      proof,
      mode: 'offline-fail-closed',
    };
  }

  const scalars = {
    mm_coherence: asNumber(scalarsInput.mm_coherence, 0),
    mm_conflict: asNumber(scalarsInput.mm_conflict, 1),
    mm_drift: asNumber(scalarsInput.mm_drift, 1),
    wall_cost: asNumber(scalarsInput.wall_cost, 1),
  };

  const thresholds = getThresholdsForState(trust, args.thresholds ?? {});
  const reasons = [];

  if (scalars.mm_coherence < thresholds.coherence_min) reasons.push('LOW_COHERENCE');
  if (scalars.mm_conflict > thresholds.conflict_max) reasons.push('HIGH_CONFLICT');
  if (scalars.mm_drift > thresholds.drift_max) reasons.push('EXCESSIVE_DRIFT');
  if (scalars.wall_cost > thresholds.wall_cost_max) reasons.push('WALL_COST_EXCEEDED');

  let decision;
  if (trust === 'T4') {
    decision = 'QUARANTINE';
    reasons.push('INTEGRITY_DEGRADED');
  } else if (trust === 'T3' && reasons.length > 0) {
    decision = 'DENY';
    reasons.push('KEY_ROLLOVER_REQUIRED');
  } else if (reasons.length >= 2) {
    decision = 'DENY';
  } else if (reasons.length === 1) {
    decision = 'QUARANTINE';
  } else if (trust === 'T2') {
    decision = 'DEFER';
    reasons.push('MANIFEST_STALE');
  } else {
    decision = 'ALLOW';
  }

  const proofPayload = {
    action,
    trust,
    scalars,
    thresholds,
    reasons,
    timestamp_monotonic: asText(args.timestamp_monotonic || '0'),
    laws_hash: asText(args.laws_hash || ''),
    manifest_hash: asText(args.manifest_hash || ''),
    state_root: asText(args.state_root || ''),
  };

  return {
    decision,
    reason_codes: reasons,
    governance_scalars: {
      ...scalars,
      trust_level: trust,
    },
    thresholds_used: thresholds,
    proof: {
      inputs_hash: sha512Hex({ action, trust, scalars }),
      laws_hash: proofPayload.laws_hash,
      manifest_hash: proofPayload.manifest_hash,
      state_root: proofPayload.state_root,
      timestamp_monotonic: proofPayload.timestamp_monotonic,
      signature: null,
      signature_note: 'unsigned-local-eval',
      capsule_hash: sha512Hex(proofPayload),
    },
    mode: 'offline-deterministic',
  };
}

function okText(text) {
  return {
    content: [{ type: 'text', text }],
  };
}

function errText(text) {
  return {
    content: [{ type: 'text', text }],
    isError: true,
  };
}

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'scbe_tokenize',
      description: 'Encode plain text into SCBE Sacred Tongue spell-text tokens.',
      inputSchema: {
        type: 'object',
        properties: {
          text: { type: 'string', description: 'UTF-8 source text to encode' },
          tongue: { type: 'string', enum: TONGUE_CODES, description: 'Tongue code (KO/AV/RU/CA/UM/DR)' },
          include_prefix: { type: 'boolean', description: 'Include tongue prefix on each token' },
        },
        required: ['text', 'tongue'],
      },
    },
    {
      name: 'scbe_detokenize',
      description: 'Decode SCBE spell-text tokens back into plain text.',
      inputSchema: {
        type: 'object',
        properties: {
          spell_text: { type: 'string', description: 'Tokenized spell-text input' },
          tongue: { type: 'string', enum: TONGUE_CODES, description: 'Optional if prefixes are included in spell_text' },
        },
        required: ['spell_text'],
      },
    },
    {
      name: 'scbe_detect_tongue',
      description: 'Detect likely Sacred Tongue for a token.',
      inputSchema: {
        type: 'object',
        properties: {
          token: { type: 'string' },
        },
        required: ['token'],
      },
    },
    {
      name: 'scbe_map_room_read_latest',
      description: 'Read docs/map-room/session_handoff_latest.md from this SCBE repo.',
      inputSchema: {
        type: 'object',
        properties: {},
      },
    },
    {
      name: 'scbe_map_room_write_latest',
      description: 'Write or append markdown to docs/map-room/session_handoff_latest.md.',
      inputSchema: {
        type: 'object',
        properties: {
          markdown: { type: 'string' },
          append: { type: 'boolean' },
        },
        required: ['markdown'],
      },
    },
    {
      name: 'scbe_tokenizer_health',
      description: 'Return tokenizer tool health and supported tongues.',
      inputSchema: {
        type: 'object',
        properties: {},
      },
    },
    {
      name: 'scbe_fetch_url',
      description: 'Fetch URL content without external fetch MCP dependency.',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string', description: 'http(s) URL to fetch' },
          method: { type: 'string', description: 'HTTP method (default GET)' },
          headers: { type: 'object', description: 'Request headers object' },
          body: { type: 'string', description: 'Optional request body' },
          timeout_ms: { type: 'number', description: 'Timeout in milliseconds (default 10000)' },
          max_chars: { type: 'number', description: 'Max response chars returned (default 12000)' },
          strip_html: { type: 'boolean', description: 'Strip HTML tags for text output (default true)' },
        },
        required: ['url'],
      },
    },
    {
      name: 'scbe_decide_offline',
      description: 'Run deterministic OFS-style offline governance decision evaluation.',
      inputSchema: {
        type: 'object',
        properties: {
          action: { type: 'string', description: 'Requested action identifier' },
          trust_state: { type: 'string', enum: TRUST_STATES, description: 'Optional override for trust state' },
          trust_context: {
            type: 'object',
            description: 'Optional trust context booleans',
            properties: {
              keys_valid: { type: 'boolean' },
              time_trusted: { type: 'boolean' },
              manifest_current: { type: 'boolean' },
              key_rotation_needed: { type: 'boolean' },
              integrity_ok: { type: 'boolean' },
            },
          },
          fail_closed_check: {
            type: 'object',
            description: 'Optional fail-closed gate booleans',
            properties: {
              laws_present: { type: 'boolean' },
              laws_hash_valid: { type: 'boolean' },
              manifest_present: { type: 'boolean' },
              manifest_sig_ok: { type: 'boolean' },
              keys_present: { type: 'boolean' },
              audit_intact: { type: 'boolean' },
              voxel_root_ok: { type: 'boolean' },
            },
          },
          scalars: {
            type: 'object',
            description: 'Governance scalars',
            properties: {
              mm_coherence: { type: 'number' },
              mm_conflict: { type: 'number' },
              mm_drift: { type: 'number' },
              wall_cost: { type: 'number' },
            },
          },
          thresholds: {
            type: 'object',
            description: 'Base threshold overrides',
            properties: {
              coherence_min: { type: 'number' },
              conflict_max: { type: 'number' },
              drift_max: { type: 'number' },
              wall_cost_max: { type: 'number' },
            },
          },
          laws_hash: { type: 'string' },
          manifest_hash: { type: 'string' },
          state_root: { type: 'string' },
          timestamp_monotonic: { type: 'string' },
        },
        required: ['action', 'scalars'],
      },
    },
    {
      name: 'scbe_state_emit_21d',
      description: 'Emit canonical 21D state telemetry with projections and stable state hashes.',
      inputSchema: {
        type: 'object',
        properties: {
          vector: {
            type: 'array',
            description: 'Canonical 21D vector (length = 21).',
            items: { type: 'number' },
          },
          apply_golden_weighting: { type: 'boolean', description: 'Include phi-weighted 21D vector in output.' },
          decision: { type: 'string', description: 'Optional decision label (ALLOW/QUARANTINE/DENY).' },
          confidence: { type: 'number', description: 'Optional confidence score [0,1].' },
          metadata: { type: 'object', description: 'Optional metadata object to attach to state record.' },
        },
        required: ['vector'],
      },
    },
    {
      name: 'scbe_sacred_egg_create',
      description: 'Create a Sacred Egg envelope from payload + ritual conditions.',
      inputSchema: {
        type: 'object',
        properties: {
          payload_b64: { type: 'string', description: 'Payload bytes encoded as base64.' },
          primary_tongue: { type: 'string', enum: TONGUE_CODES, description: 'Primary hatch tongue.' },
          glyph: { type: 'string', description: 'Display glyph for the egg.' },
          hatch_condition: { type: 'object', description: 'Ritual constraints (path/ring/min_tongues/min_weight).' },
          context: { type: 'array', description: 'Context vector used for context binding.', items: { type: 'number' } },
        },
        required: ['payload_b64'],
      },
    },
    {
      name: 'scbe_sacred_egg_hatch',
      description: 'Attempt to hatch a Sacred Egg. Failures return fail-to-noise tokens.',
      inputSchema: {
        type: 'object',
        properties: {
          egg_json: { description: 'Sacred Egg object or JSON string.' },
          context: { type: 'array', description: 'Current context vector for hatch evaluation.', items: { type: 'number' } },
          agent_tongue: { type: 'string', enum: TONGUE_CODES, description: 'Active tongue attempting hatch.' },
          ritual_mode: { type: 'string', description: 'solitary | triadic | ring_descent' },
          additional_tongues: { type: 'array', items: { type: 'string', enum: TONGUE_CODES } },
          path_history: { type: 'array', description: 'Ring traversal history for ring_descent mode.' },
        },
        required: ['egg_json', 'context', 'agent_tongue'],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const name = request.params?.name;
  const args = request.params?.arguments ?? {};

  try {
    switch (name) {
      case 'scbe_tokenize': {
        const text = asText(args.text);
        const tongue = normalizeTongue(args.tongue);
        const includePrefix = args.include_prefix === undefined ? true : Boolean(args.include_prefix);
        if (!tongue) return errText('Invalid or missing tongue. Expected one of KO/AV/RU/CA/UM/DR.');

        const spellText = encode(Buffer.from(text, 'utf8'), tongue, includePrefix);
        return okText(
          JSON.stringify(
            {
              tongue,
              include_prefix: includePrefix,
              input_bytes: Buffer.byteLength(text, 'utf8'),
              spell_text: spellText,
            },
            null,
            2,
          ),
        );
      }

      case 'scbe_detokenize': {
        const spellText = asText(args.spell_text).trim();
        const tongue = args.tongue ? normalizeTongue(args.tongue) : undefined;
        const bytes = decode(spellText, tongue);
        return okText(
          JSON.stringify(
            {
              tongue: tongue ?? null,
              text_utf8: bytes.toString('utf8'),
              bytes_base64: bytes.toString('base64'),
              byte_length: bytes.length,
            },
            null,
            2,
          ),
        );
      }

      case 'scbe_detect_tongue': {
        const token = asText(args.token);
        const detected = detectTongue(token);
        return okText(JSON.stringify({ token, detected_tongue: detected }, null, 2));
      }

      case 'scbe_map_room_read_latest': {
        const content = await fs.readFile(MAP_ROOM_LATEST, 'utf8');
        return okText(content);
      }

      case 'scbe_map_room_write_latest': {
        const markdown = asText(args.markdown);
        const append = Boolean(args.append);
        await fs.mkdir(MAP_ROOM_DIR, { recursive: true });
        if (append) {
          await fs.appendFile(MAP_ROOM_LATEST, markdown, 'utf8');
        } else {
          await fs.writeFile(MAP_ROOM_LATEST, markdown, 'utf8');
        }
        return okText(
          JSON.stringify(
            {
              path: MAP_ROOM_LATEST,
              bytes_written: Buffer.byteLength(markdown, 'utf8'),
              mode: append ? 'append' : 'overwrite',
            },
            null,
            2,
          ),
        );
      }

      case 'scbe_tokenizer_health': {
        return okText(
          JSON.stringify(
            {
              status: 'ok',
              repo_root: REPO_ROOT,
              map_room_latest: MAP_ROOM_LATEST,
              tongues: TONGUE_CODES,
              server: 'scbe-mcp-server',
              tools_added: [
                'scbe_fetch_url',
                'scbe_decide_offline',
                'scbe_state_emit_21d',
                'scbe_sacred_egg_create',
                'scbe_sacred_egg_hatch',
              ],
            },
            null,
            2,
          ),
        );
      }

      case 'scbe_fetch_url': {
        const urlRaw = asText(args.url).trim();
        if (!urlRaw) return errText('Missing required field: url');

        let urlObj;
        try {
          urlObj = new URL(urlRaw);
        } catch {
          return errText(`Invalid URL: ${urlRaw}`);
        }
        if (!['http:', 'https:'].includes(urlObj.protocol)) {
          return errText(`Unsupported protocol: ${urlObj.protocol}`);
        }

        const method = asText(args.method || 'GET').toUpperCase();
        const timeoutMs = Math.max(500, Math.min(120000, asNumber(args.timeout_ms, 10000)));
        const maxChars = Math.max(256, Math.min(500000, asNumber(args.max_chars, 12000)));
        const stripHtmlFlag = asBoolean(args.strip_html, true);
        const headers = typeof args.headers === 'object' && args.headers !== null ? args.headers : {};
        const body = args.body === undefined || args.body === null ? undefined : asText(args.body);

        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort('timeout'), timeoutMs);

        try {
          let response;
          let fetchBackend = 'node-fetch';
          try {
            const requestInit = {
              method,
              headers,
              signal: controller.signal,
            };
            if (body !== undefined && method !== 'GET' && method !== 'HEAD') {
              requestInit.body = body;
            }

            const res = await fetch(urlObj.toString(), requestInit);
            response = {
              status: res.status,
              statusText: res.statusText,
              ok: res.ok,
              contentType: res.headers.get('content-type') || '',
              responseText: await res.text(),
            };
          } catch (error) {
            if (urlObj.protocol !== 'https:' || !isTlsIssuerCertError(error)) {
              throw error;
            }
            response = await fetchViaCurl(urlObj.toString(), method, headers, body, timeoutMs);
            fetchBackend = 'curl-fallback';
          }

          const isHtml = response.contentType.toLowerCase().includes('text/html');
          let outputText = stripHtmlFlag && isHtml ? stripHtml(response.responseText) : response.responseText;
          if (outputText.length > maxChars) outputText = outputText.slice(0, maxChars);

          return okText(
            JSON.stringify(
              {
                url: urlObj.toString(),
                status: response.status,
                status_text: response.statusText,
                ok: response.ok,
                content_type: response.contentType,
                body_chars: outputText.length,
                body: outputText,
                fetch_backend: fetchBackend,
              },
              null,
              2,
            ),
          );
        } finally {
          clearTimeout(timer);
        }
      }

      case 'scbe_decide_offline': {
        const result = decideOffline(args);
        return okText(JSON.stringify(result, null, 2));
      }

      case 'scbe_state_emit_21d': {
        const result = scbeStateEmit21D(args);
        return okText(JSON.stringify(result, null, 2));
      }

      case 'scbe_sacred_egg_create': {
        const result = scbeSacredEggCreate(args);
        return okText(JSON.stringify(result, null, 2));
      }

      case 'scbe_sacred_egg_hatch': {
        const result = scbeSacredEggHatch(args);
        return okText(JSON.stringify(result, null, 2));
      }

      default:
        return errText(`Unknown tool: ${name}`);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return errText(`scbe-mcp-server error: ${message}`);
  }
});

export async function startServer() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

if (process.argv[1] && path.resolve(process.argv[1]) === __filename) {
  await startServer();
}
