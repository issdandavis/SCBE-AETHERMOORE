import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { promises as fs } from 'fs';
import { createHash } from 'crypto';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { execFile } from 'child_process';
import { promisify } from 'util';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const MAP_ROOM_DIR = path.join(REPO_ROOT, 'docs', 'map-room');
const MAP_ROOM_LATEST = path.join(MAP_ROOM_DIR, 'session_handoff_latest.md');
const PACKAGE_JSON_PATH = path.join(REPO_ROOT, 'package.json');
const SCBE_SOURCE_ROOTS_PATH = path.join(REPO_ROOT, 'docs', 'map-room', 'scbe_source_roots.md');
const BINARY_FIRST_STACK_PATH = path.join(REPO_ROOT, 'docs', 'specs', 'BINARY_FIRST_TRAINING_STACK.md');
const TRIADIC_REGISTRY_PATH = path.join(REPO_ROOT, 'docs', 'research', 'CANONICAL_TRIADIC_HARMONIC_SYMBOL_REGISTRY.md');
const SACRED_EGGS_MODEL_PATH = path.join(REPO_ROOT, 'docs', '01-architecture', 'sacred-eggs-systems-model.md');
const DIST_TOKENIZER_PATH = path.join(REPO_ROOT, 'dist', 'src', 'tokenizer', 'ss1.js');
const DIST_BRAIN_PATH = path.join(REPO_ROOT, 'dist', 'src', 'ai_brain', 'index.js');
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
const REFERENCE_DOCS = [
  {
    key: 'source-roots',
    title: 'SCBE Source Roots',
    path: SCBE_SOURCE_ROOTS_PATH,
    description: 'First re-anchor map for canon, tokenizer, geometry, embeddings, and implementation roots.',
  },
  {
    key: 'binary-first-training-stack',
    title: 'Binary-First Training Stack',
    path: BINARY_FIRST_STACK_PATH,
    description: 'Minimal binary-first training scaffold built around SS1 byte bijection and explicit orientation packets.',
  },
  {
    key: 'triadic-harmonic-symbol-registry',
    title: 'Canonical Triadic and Harmonic Symbol Registry',
    path: TRIADIC_REGISTRY_PATH,
    description: 'Canonical separation of triadic, harmonic, kernel, and 21D runtime state symbols.',
  },
  {
    key: 'sacred-eggs-systems-model',
    title: 'Sacred Eggs Systems Model',
    path: SACRED_EGGS_MODEL_PATH,
    description: 'Seed and identity model root for Sacred Eggs and related governance envelopes.',
  },
];
const COMMAND_AREAS = {
  build: {
    description: 'Compile and type-check the SCBE TypeScript runtime.',
    scripts: ['clean', 'build', 'typecheck'],
  },
  test: {
    description: 'Run TypeScript and Python validation suites.',
    scripts: ['test', 'test:python', 'test:all'],
  },
  mcp: {
    description: 'Inspect and operate the repo MCP terminal helpers.',
    scripts: ['mcp:doctor', 'mcp:servers', 'mcp:tools', 'mcp:gateway'],
  },
  docker: {
    description: 'Run local Docker health and stack workflows.',
    scripts: ['docker:doctor:api', 'docker:doctor:unified', 'docker:up:api', 'docker:up:unified', 'docker:down:api', 'docker:down:unified', 'docker:status:all'],
  },
  browser: {
    description: 'Operate local AetherBrowser service lanes.',
    scripts: ['aetherbrowser:model:cli', 'aetherbrowser:service:start', 'aetherbrowser:service:verify', 'aetherbrowser:service:stop'],
  },
  system: {
    description: 'Bootstrap and inspect the broader SCBE system surface.',
    scripts: ['connector:health', 'scbe:bootstrap', 'system:cli'],
  },
  skills: {
    description: 'Inspect repo-local SCBE skill bridge output.',
    scripts: ['skills:bridge', 'skills:bridge:full'],
  },
  publish: {
    description: 'Prepare and validate npm package publishing flows.',
    scripts: ['publish:prepare', 'publish:check:strict', 'publish:dryrun', 'package'],
  },
};
const SCBE_MCP_TOOL_NAMES = [
  'scbe_tokenize',
  'scbe_detokenize',
  'scbe_detect_tongue',
  'scbe_map_room_read_latest',
  'scbe_map_room_write_latest',
  'scbe_system_manifest',
  'scbe_command_catalog',
  'scbe_reference_lookup',
  'scbe_tokenizer_health',
  'scbe_fetch_url',
  'scbe_decide_offline',
  'scbe_state_emit_21d',
  'scbe_sacred_egg_create',
  'cymatic-voxel-layout',
  'scbe_sacred_egg_hatch',
];
let packageJsonPromise;
const referenceDocCache = new Map();

async function pathExists(targetPath) {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function ensureCompiledRuntimeArtifacts() {
  const requiredArtifacts = [DIST_TOKENIZER_PATH, DIST_BRAIN_PATH];
  const missingBeforeBuild = [];
  for (const target of requiredArtifacts) {
    if (!(await pathExists(target))) missingBeforeBuild.push(target);
  }
  if (missingBeforeBuild.length === 0) return;

  const tscEntrypoint = path.join(REPO_ROOT, 'node_modules', 'typescript', 'bin', 'tsc');
  if (!(await pathExists(tscEntrypoint))) {
    throw new Error(
      `Missing TypeScript compiler at ${tscEntrypoint}. Run npm install in ${REPO_ROOT} before starting scbe-mcp-server.`,
    );
  }

  try {
    await execFileAsync(process.execPath, [tscEntrypoint, '-p', path.join(REPO_ROOT, 'tsconfig.json')], {
      cwd: REPO_ROOT,
      windowsHide: true,
      timeout: 120000,
      maxBuffer: 16 * 1024 * 1024,
    });
  } catch (error) {
    const stderr = asText(error?.stderr || '').trim();
    const stdout = asText(error?.stdout || '').trim();
    const detail = stderr || stdout || asText(error?.message || error);
    throw new Error(`Unable to compile SCBE runtime artifacts automatically: ${detail}`);
  }

  const missingAfterBuild = [];
  for (const target of requiredArtifacts) {
    if (!(await pathExists(target))) missingAfterBuild.push(target);
  }
  if (missingAfterBuild.length > 0) {
    throw new Error(`Automatic build completed without required artifacts: ${missingAfterBuild.join(', ')}`);
  }
}

await ensureCompiledRuntimeArtifacts();

const tokenizerMod = await import(pathToFileURL(DIST_TOKENIZER_PATH).href);
const brainMod = await import(pathToFileURL(DIST_BRAIN_PATH).href);

const { decode, detectTongue, encode, TONGUE_CODES } = tokenizerMod;
const { BRAIN_DIMENSIONS, applyGoldenWeighting, safePoincareEmbed, vectorNorm } = brainMod;

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

function asInteger(value, fallback, min, max) {
  const parsed = Math.floor(asNumber(value, fallback));
  return Math.max(min, Math.min(max, parsed));
}

function toRepoRelative(targetPath) {
  return path.relative(REPO_ROOT, targetPath).replace(/\\/g, '/');
}

function uniqueStrings(values) {
  return [...new Set(values.filter(Boolean))];
}

function compactWhitespace(value) {
  return asText(value).replace(/\s+/g, ' ').trim();
}

function compactSnippet(value, maxChars = 240) {
  const compact = compactWhitespace(value);
  if (compact.length <= maxChars) return compact;
  return `${compact.slice(0, Math.max(0, maxChars - 1)).trimEnd()}…`;
}

function splitMarkdownSections(markdown) {
  const source = asText(markdown);
  const sectionPattern = /^##\s+(.+)$/gm;
  const sections = [];
  let previousTitle = 'Overview';
  let previousIndex = 0;
  let match;

  while ((match = sectionPattern.exec(source)) !== null) {
    const body = source.slice(previousIndex, match.index).trim();
    if (body) sections.push({ title: previousTitle, body });
    previousTitle = match[1].trim();
    previousIndex = sectionPattern.lastIndex;
  }

  const tail = source.slice(previousIndex).trim();
  if (tail) sections.push({ title: previousTitle, body: tail });
  return sections;
}

function extractBulletLines(markdown) {
  return asText(markdown)
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.startsWith('- '))
    .map((line) => line.slice(2).trim());
}

function tokenizeQueryTerms(value) {
  return uniqueStrings(
    compactWhitespace(value.toLowerCase())
      .split(/[^a-z0-9]+/)
      .filter((token) => token.length >= 2),
  );
}

function scoreReferenceMatch(queryTerms, doc, section) {
  if (queryTerms.length === 0) return 0;
  const titleText = `${doc.key} ${doc.title} ${section.title}`.toLowerCase();
  const bodyText = section.body.toLowerCase();
  const descriptionText = doc.description.toLowerCase();
  let score = 0;

  for (const term of queryTerms) {
    if (titleText.includes(term)) score += 6;
    if (descriptionText.includes(term)) score += 3;
    if (bodyText.includes(term)) score += 2;
  }

  return score;
}

async function loadPackageJson() {
  if (!packageJsonPromise) {
    packageJsonPromise = fs.readFile(PACKAGE_JSON_PATH, 'utf8').then((content) => JSON.parse(content));
  }
  return packageJsonPromise;
}

async function loadReferenceDoc(doc) {
  if (!referenceDocCache.has(doc.path)) {
    referenceDocCache.set(doc.path, fs.readFile(doc.path, 'utf8'));
  }
  return referenceDocCache.get(doc.path);
}

async function buildScbeSystemManifest() {
  const pkg = await loadPackageJson();
  const sourceRoots = await loadReferenceDoc(REFERENCE_DOCS[0]);
  const sections = splitMarkdownSections(sourceRoots).filter(({ title }) => title !== 'Overview');

  return {
    repo: {
      name: pkg.name,
      version: pkg.version,
      description: pkg.description,
      repo_root: REPO_ROOT,
    },
    mcp: {
      server: 'scbe-mcp-server',
      entrypoint: toRepoRelative(path.join(__dirname, 'server.mjs')),
      tool_count: SCBE_MCP_TOOL_NAMES.length,
      tools: SCBE_MCP_TOOL_NAMES,
    },
    package_bins: pkg.bin || {},
    primary_source_dirs: ['src/', 'tests/', 'docs/', 'scripts/', 'mcp/scbe-server/'],
    command_areas: Object.fromEntries(
      Object.entries(COMMAND_AREAS).map(([area, config]) => [
        area,
        {
          description: config.description,
          commands: config.scripts.filter((name) => pkg.scripts?.[name]).map((name) => `npm run ${name}`),
        },
      ]),
    ),
    reference_docs: REFERENCE_DOCS.map((doc) => ({
      key: doc.key,
      title: doc.title,
      path: toRepoRelative(doc.path),
      description: doc.description,
    })),
    source_root_sections: sections.map((section) => ({
      title: section.title,
      bullet_count: extractBulletLines(section.body).length,
    })),
    recommended_first_steps: [
      'Use scbe_system_manifest to orient to the repo, tool surface, and command areas.',
      'Use scbe_command_catalog for the exact npm lanes before falling back to shell exploration.',
      'Use scbe_reference_lookup with topics like tokenizer, sacred eggs, triadic, geometry, or training to find canonical docs.',
    ],
  };
}

async function buildCommandCatalog(area) {
  const pkg = await loadPackageJson();
  const selectedAreas = area ? [area] : Object.keys(COMMAND_AREAS);

  return Object.fromEntries(
    selectedAreas.map((areaName) => {
      const config = COMMAND_AREAS[areaName];
      return [
        areaName,
        {
          description: config.description,
          commands: config.scripts
            .filter((scriptName) => pkg.scripts?.[scriptName])
            .map((scriptName) => ({
              name: scriptName,
              command: `npm run ${scriptName}`,
              script: pkg.scripts[scriptName],
            })),
        },
      ];
    }),
  );
}

async function lookupReferenceDocs(topic, maxMatches) {
  const query = compactWhitespace(topic);
  if (!query) {
    return {
      topic: '',
      matches: [],
      available_docs: REFERENCE_DOCS.map((doc) => ({
        key: doc.key,
        title: doc.title,
        path: toRepoRelative(doc.path),
        description: doc.description,
      })),
    };
  }

  const queryTerms = tokenizeQueryTerms(query);
  const matches = [];

  for (const doc of REFERENCE_DOCS) {
    const markdown = await loadReferenceDoc(doc);
    const sections = splitMarkdownSections(markdown).filter(({ title }) => title !== 'Overview');
    for (const section of sections) {
      const score = scoreReferenceMatch(queryTerms, doc, section);
      if (score <= 0) continue;
      matches.push({
        score,
        key: doc.key,
        title: doc.title,
        path: toRepoRelative(doc.path),
        section: section.title,
        snippet: compactSnippet(section.body, 280),
      });
    }
  }

  matches.sort((a, b) => b.score - a.score || a.title.localeCompare(b.title) || a.section.localeCompare(b.section));

  return {
    topic: query,
    matches: matches.slice(0, maxMatches),
  };
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

function startsWithInsensitive(source, index, needle) {
  return source.slice(index, index + needle.length).toLowerCase() === needle.toLowerCase();
}

function appendNormalizedText(buffer, value, state) {
  for (const ch of value) {
    if (/\s/.test(ch)) {
      if (!state.lastWasSpace && buffer.length > 0) {
        buffer.push(' ');
        state.lastWasSpace = true;
      }
      continue;
    }
    buffer.push(ch);
    state.lastWasSpace = false;
  }
}

function findTagEnd(source, startIndex) {
  let quote = null;
  for (let i = startIndex; i < source.length; i++) {
    const ch = source[i];
    if (quote) {
      if (ch === quote) quote = null;
      continue;
    }
    if (ch === '"' || ch === "'") {
      quote = ch;
      continue;
    }
    if (ch === '>') return i;
  }
  return -1;
}

function readTagName(source, startIndex) {
  let i = startIndex;
  while (i < source.length && /\s/.test(source[i])) i += 1;
  if (source[i] === '/') i += 1;
  while (i < source.length && /\s/.test(source[i])) i += 1;
  const begin = i;
  while (i < source.length && /[A-Za-z0-9:-]/.test(source[i])) i += 1;
  return source.slice(begin, i).toLowerCase();
}

export function stripHtml(html) {
  const source = String(html ?? '');
  const buffer = [];
  const state = { lastWasSpace: true };
  let mode = 'text';

  for (let i = 0; i < source.length; i += 1) {
    if (mode === 'comment') {
      if (source.startsWith('-->', i)) {
        mode = 'text';
        i += 2;
      }
      continue;
    }

    if (mode === 'script' || mode === 'style') {
      const closingTag = `</${mode}`;
      if (startsWithInsensitive(source, i, closingTag)) {
        const tagEnd = findTagEnd(source, i);
        if (tagEnd >= 0) {
          mode = 'text';
          i = tagEnd;
          appendNormalizedText(buffer, ' ', state);
          continue;
        }
      }
      continue;
    }

    const ch = source[i];
    if (ch !== '<') {
      appendNormalizedText(buffer, ch, state);
      continue;
    }

    if (source.startsWith('<!--', i)) {
      mode = 'comment';
      i += 3;
      continue;
    }

    const tagEnd = findTagEnd(source, i + 1);
    if (tagEnd < 0) {
      appendNormalizedText(buffer, source.slice(i), state);
      break;
    }

    const tagName = readTagName(source, i + 1);
    if (tagName === 'script' || tagName === 'style') {
      mode = tagName;
      i = tagEnd;
      continue;
    }

    appendNormalizedText(buffer, ' ', state);
    i = tagEnd;
  }

  return buffer.join('').trim();
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

const VOXEL_APP_NODES = [
  { id: 'ingress_a', label: 'Ingress A', x: -0.68, y: -0.24, isMerge: false },
  { id: 'ingress_b', label: 'Ingress B', x: -0.68, y: 0.24, isMerge: false },
  { id: 'router_a', label: 'Router A', x: -0.24, y: -0.26, isMerge: false },
  { id: 'router_b', label: 'Router B', x: -0.24, y: 0.26, isMerge: false },
  { id: 'merge_hub', label: 'Merge Hub', x: 0.0, y: 0.0, isMerge: true },
  { id: 'audit', label: 'Audit', x: 0.3, y: -0.18, isMerge: false },
  { id: 'archive', label: 'Archive', x: 0.62, y: 0.24, isMerge: false },
  { id: 'publish', label: 'Publish', x: 0.62, y: -0.24, isMerge: false },
  { id: 'near_merge', label: 'Near Merge Lane', x: 0.08, y: 0.08, isMerge: false },
];

const VOXEL_APP_EDGES = [
  { from: 'ingress_a', to: 'router_a' },
  { from: 'ingress_b', to: 'router_b' },
  { from: 'router_a', to: 'merge_hub' },
  { from: 'router_b', to: 'merge_hub' },
  { from: 'merge_hub', to: 'audit' },
  { from: 'merge_hub', to: 'archive' },
  { from: 'merge_hub', to: 'publish' },
  { from: 'router_a', to: 'near_merge' },
  { from: 'near_merge', to: 'publish' },
  { from: 'near_merge', to: 'archive' },
  { from: 'audit', to: 'publish' },
];

function canonicalVoxelPath(mode, index) {
  if (mode === 'dense') {
    return index % 2 === 0
      ? ['ingress_a', 'router_a', 'merge_hub', 'publish']
      : ['ingress_b', 'router_b', 'merge_hub', 'archive'];
  }
  if (mode === 'quasi') {
    if (index % 3 === 0) return ['ingress_a', 'router_a', 'near_merge', 'publish'];
    if (index % 3 === 1) return ['ingress_b', 'router_b', 'merge_hub', 'archive'];
    return ['ingress_a', 'router_a', 'merge_hub', 'audit', 'publish'];
  }
  if (index % 3 === 0) return ['ingress_a', 'router_a', 'merge_hub', 'publish'];
  if (index % 3 === 1) return ['ingress_b', 'router_b', 'merge_hub', 'archive'];
  return ['ingress_a', 'router_a', 'near_merge', 'archive'];
}

function phaseFromFlowDepth(flowId, depth) {
  const seed = `${flowId}:${depth}`;
  let total = 0;
  for (const ch of seed) total += ch.charCodeAt(0);
  return ((total % 360) / 180) * Math.PI;
}

function normalizeVector3(value) {
  const arr = Array.isArray(value) ? value : [];
  return [asNumber(arr[0], 0), asNumber(arr[1], 0), asNumber(arr[2], 0)];
}

function toUnixMs(value, fallback) {
  const n = asNumber(value, Number.NaN);
  if (!Number.isFinite(n)) return fallback;
  if (n > 0 && n < 1e11) return n * 1000;
  return n;
}

function normalizeCymaticVoxelLayout(raw, mode, atUnixMs, windowMs, flowCount) {
  const source = raw && typeof raw === 'object' ? raw : {};
  const nodeMap = Object.fromEntries(VOXEL_APP_NODES.map((n) => [n.id, n]));

  const flowsRaw = Array.isArray(source.flows) ? source.flows : [];
  const fallbackCount = Math.max(1, Math.min(32, Math.floor(flowCount)));
  const totalFlows = Math.max(fallbackCount, flowsRaw.length || 0);

  const flows = Array.from({ length: totalFlows }).map((_, idx) => {
    const src = flowsRaw[idx] && typeof flowsRaw[idx] === 'object' ? flowsRaw[idx] : {};
    const sequence = Math.max(0, Math.floor(asNumber(src.sequence, idx)));
    const id = asText(src.id || `flow_${idx + 1}`);
    const path = Array.isArray(src.path) && src.path.length > 0
      ? src.path.map((v) => asText(v))
      : canonicalVoxelPath(mode, sequence);
    return {
      id,
      sequence,
      wavelengthNm: asNumber(src.wavelengthNm, 540),
      authority: asText(src.authority || 'internal'),
      intentTag: asText(src.intentTag || 'route'),
      intentVector: normalizeVector3(src.intentVector),
      path,
    };
  });

  const flowById = Object.fromEntries(flows.map((f) => [f.id, f]));

  const voxelsRaw = Array.isArray(source.voxels) ? source.voxels : [];
  const voxels = voxelsRaw.map((value, idx) => {
    const src = value && typeof value === 'object' ? value : {};
    const rawId = asText(src.id || `voxel_${idx + 1}`);
    const inferredFlowId = rawId.match(/^(flow_\d+)/)?.[1] || flows[0]?.id || 'flow_1';
    const flowId = asText(src.flowId || inferredFlowId);
    const flow = flowById[flowId] || flows[0];
    const depth = Math.max(0, Math.floor(asNumber(src.z, 0)));
    const fallbackNodeId = flow?.path?.[Math.min(depth, Math.max(0, flow.path.length - 1))] || 'merge_hub';
    const nodeId = asText(src.nodeId || fallbackNodeId);
    const node = nodeMap[nodeId] || nodeMap.merge_hub;
    const createdAtUnixMs = toUnixMs(src.createdAtUnixMs ?? src.created_at, atUnixMs);
    const updatedAtUnixMs = toUnixMs(src.updatedAtUnixMs ?? src.updated_at, createdAtUnixMs);
    const authority = asText(src.authority || flow?.authority || 'internal');
    const intentTag = asText(src.intentTag || flow?.intentTag || 'route');
    const intentVector = normalizeVector3(src.intentVector || flow?.intentVector);

    return {
      id: rawId,
      flowId,
      nodeId,
      x: asNumber(src.x, node.x),
      y: asNumber(src.y, node.y),
      z: asNumber(src.z, depth),
      phase: asNumber(src.phase, phaseFromFlowDepth(flowId, depth)),
      intensity: asNumber(src.intensity, 0.5),
      wavelengthNm: asNumber(src.wavelengthNm, flow?.wavelengthNm || 540),
      authority,
      authoritySignature: asText(src.authoritySignature || src.authorityHash || src.authority_hash || ''),
      authorityHash: asText(src.authorityHash || src.authority_hash || src.authoritySignature || ''),
      intentTag,
      intentVector,
      modeN: asNumber(src.modeN, 3),
      modeM: asNumber(src.modeM, 2),
      chladniValue: asNumber(src.chladniValue, src.chladniAddress),
      createdAtUnixMs,
      updatedAtUnixMs,
      tIndex: Math.floor((updatedAtUnixMs - (atUnixMs - windowMs)) / Math.max(1, windowMs)),
    };
  });

  const collisionsRaw = Array.isArray(source.collisions) ? source.collisions : [];
  const collisions = collisionsRaw.map((value) => {
    const src = value && typeof value === 'object' ? value : {};
    const flowA = asText(src.flows?.[0] || src.flowA || flows[0]?.id || 'flow_1');
    const flowB = asText(src.flows?.[1] || src.flowB || flowA);
    return {
      type: asText(src.type || 'node_overlap'),
      flows: [flowA, flowB],
      detail: asText(src.detail || ''),
    };
  });

  const temporalSource = source.temporal && typeof source.temporal === 'object' ? source.temporal : {};
  const temporalAuthority = { public: 0, internal: 0, restricted: 0, sealed: 0 };
  const temporalIntent = {};
  const halfWindow = windowMs / 2;
  const activeVoxels = voxels.filter((v) =>
    Math.abs(v.updatedAtUnixMs - atUnixMs) <= halfWindow ||
    (v.createdAtUnixMs <= atUnixMs && atUnixMs <= v.updatedAtUnixMs + halfWindow));
  for (const voxel of activeVoxels) {
    if (Object.prototype.hasOwnProperty.call(temporalAuthority, voxel.authority)) {
      temporalAuthority[voxel.authority] += 1;
    }
    temporalIntent[voxel.intentTag] = (temporalIntent[voxel.intentTag] || 0) + 1;
  }
  const activeFlowIds = new Set(activeVoxels.map((v) => v.flowId));
  const activeCollisionCount = collisions.filter(
    (c) => activeFlowIds.has(c.flows[0]) && activeFlowIds.has(c.flows[1]),
  ).length;

  const collisionFlowIds = new Set(collisions.flatMap((c) => c.flows));
  const spectralIsolation = mode === 'dense' ? 0.08 : 0.1;
  const hyperbolicMinSeparation = mode === 'quasi' ? 0.25 : 0.3;

  return {
    mode,
    thresholds: {
      spectralIsolation: asNumber(source?.thresholds?.spectralIsolation, spectralIsolation),
      hyperbolicMinSeparation: asNumber(source?.thresholds?.hyperbolicMinSeparation, hyperbolicMinSeparation),
    },
    dimensions: source.dimensions || {
      explicit: ['x', 'y', 'z', 'spectral', 'authority', 'intent'],
      implied: ['timestamp'],
    },
    nodes: VOXEL_APP_NODES,
    edges: VOXEL_APP_EDGES,
    flows,
    collisions,
    voxels,
    temporal: {
      atUnixMs: asNumber(temporalSource.atUnixMs, atUnixMs),
      windowMs: asNumber(temporalSource.windowMs, windowMs),
      activeVoxelCount: asNumber(temporalSource.activeVoxelCount, activeVoxels.length),
      activeCollisionCount: asNumber(temporalSource.activeCollisionCount, activeCollisionCount),
      authorityDistribution: temporalSource.authorityDistribution || temporalAuthority,
      intentDistribution: temporalSource.intentDistribution || temporalIntent,
    },
    metrics: {
      collisionCount: collisions.length,
      safeFlowCount: Math.max(0, flows.length - collisionFlowIds.size),
      mergeNodeCount: VOXEL_APP_NODES.filter((n) => n.isMerge).length,
      sealedVoxelCount: voxels.filter((v) => v.authority === 'sealed').length,
      authorityDiversity: new Set(voxels.map((v) => v.authority)).size,
      intentDiversity: new Set(voxels.map((v) => v.intentTag)).size,
      sourceMetrics: source.metrics || {},
    },
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
      name: 'scbe_system_manifest',
      description: 'Return the SCBE repo, MCP, command-area, and canonical-doc manifest for orientation.',
      inputSchema: {
        type: 'object',
        properties: {},
      },
    },
    {
      name: 'scbe_command_catalog',
      description: 'Return grouped npm command lanes for SCBE system work.',
      inputSchema: {
        type: 'object',
        properties: {
          area: {
            type: 'string',
            enum: Object.keys(COMMAND_AREAS),
            description: 'Optional command area filter (build/test/mcp/docker/browser/system/skills/publish).',
          },
        },
      },
    },
    {
      name: 'scbe_reference_lookup',
      description: 'Search canonical SCBE docs for a topic and return the best-matching sections.',
      inputSchema: {
        type: 'object',
        properties: {
          topic: { type: 'string', description: 'Topic or keyword to locate in canonical SCBE docs.' },
          max_matches: { type: 'number', description: 'Maximum number of section matches to return (default 5).' },
        },
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
      name: 'cymatic-voxel-layout',
      description: 'Generate a 6D+t cymatic voxel layout with spectral flow isolation, authority/intent encoding, Chladni addressing, and temporal slicing.',
      inputSchema: {
        type: 'object',
        properties: {
          flowCount: { type: 'number', description: 'Number of spectral flows (1-32, default 8)' },
          mode: { type: 'string', enum: ['default', 'quasi', 'dense'], description: 'Layout mode' },
          atUnixMs: { type: 'number', description: 'Center timestamp for temporal slice (default: now)' },
          windowMs: { type: 'number', description: 'Window width in ms for temporal slice (default 60000)' },
        },
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

      case 'scbe_system_manifest': {
        const manifest = await buildScbeSystemManifest();
        return okText(JSON.stringify(manifest, null, 2));
      }

      case 'scbe_command_catalog': {
        const area = asText(args.area).trim().toLowerCase();
        if (area && !COMMAND_AREAS[area]) {
          return errText(`Unknown command area: ${area}. Expected one of ${Object.keys(COMMAND_AREAS).join(', ')}.`);
        }

        const catalog = await buildCommandCatalog(area || null);
        return okText(
          JSON.stringify(
            {
              repo_root: REPO_ROOT,
              selected_area: area || null,
              available_areas: Object.keys(COMMAND_AREAS),
              catalog,
            },
            null,
            2,
          ),
        );
      }

      case 'scbe_reference_lookup': {
        const maxMatches = asInteger(args.max_matches, 5, 1, 12);
        const payload = await lookupReferenceDocs(args.topic, maxMatches);
        payload.available_topics = uniqueStrings([
          'tokenizer',
          'sacred eggs',
          'triadic',
          'harmonic',
          '21d state',
          'geometry',
          'training',
          'source roots',
        ]);
        return okText(JSON.stringify(payload, null, 2));
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
              tool_count: SCBE_MCP_TOOL_NAMES.length,
              tools: SCBE_MCP_TOOL_NAMES,
              canonical_docs: REFERENCE_DOCS.map((doc) => ({ key: doc.key, path: toRepoRelative(doc.path) })),
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

      case 'cymatic-voxel-layout': {
        const flowCount = asNumber(args.flowCount, 8);
        const mode = ['default', 'quasi', 'dense'].includes(asText(args.mode)) ? asText(args.mode) : 'default';
        const atUnixMs = asNumber(args.atUnixMs, Date.now());
        const windowMs = asNumber(args.windowMs, 60000);
        const pyArgs = [
          '-m', 'hydra.voxel_cli', 'layout',
          '--flows', String(Math.max(1, Math.min(32, Math.floor(flowCount)))),
          '--mode', mode,
          '--at-unix-ms', String(atUnixMs),
          '--window-ms', String(windowMs),
          '--json',
        ];
        try {
          const { stdout } = await execFileAsync('python', pyArgs, {
            cwd: REPO_ROOT,
            encoding: 'utf8',
            windowsHide: true,
            timeout: 30000,
          });
          const rawText = asText(stdout).trim();
          let payload;
          try {
            const parsed = JSON.parse(rawText);
            payload = normalizeCymaticVoxelLayout(parsed, mode, atUnixMs, windowMs, flowCount);
          } catch {
            payload = normalizeCymaticVoxelLayout({}, mode, atUnixMs, windowMs, flowCount);
            payload.metrics.sourceParseError = 'python_layout_json_parse_failed';
            payload.metrics.rawTextPreview = rawText.slice(0, 1000);
          }
          return okText(JSON.stringify(payload, null, 2));
        } catch (pyErr) {
          return errText(`cymatic-voxel-layout error: ${pyErr.message || pyErr}`);
        }
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
