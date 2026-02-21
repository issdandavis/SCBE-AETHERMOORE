import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { decode, detectTongue, encode, TONGUE_CODES } from '../../dist/src/tokenizer/ss1.js';
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
              tools_added: ['scbe_fetch_url', 'scbe_decide_offline'],
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

      default:
        return errText(`Unknown tool: ${name}`);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return errText(`scbe-mcp-server error: ${message}`);
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
