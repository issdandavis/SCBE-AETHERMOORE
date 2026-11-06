'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { scbeHome } = require('./provider-registry');
const { workspaceKey } = require('./session-store');
const {
  HASH_SUITE,
  appendChainedReceipt,
  canonicalJson,
  multiHashJson,
  multiHashRoot,
  sameHashes,
  verifyChainedReceipt,
  verifyReceiptFile,
} = require('./multi-hash-receipt');

const PACKET_SCHEMA = 'scbe_guided_evidence_packet_v1';
const ARTIFACT_SCHEMA = 'scbe_guided_evidence_artifact_v1';
const PACKET_RECEIPT_SCHEMA = 'scbe_guided_evidence_packet_receipt_v1';
const MAX_OBJECTIVE_CHARS = 2_000;
const MAX_PACKET_SCAN = 250;
const WORKSPACE_SEARCH_MS = 2_000;
const WORKSPACE_SEARCH_FILES = 1_500;
const WORKSPACE_FILE_BYTES = 1024 * 1024;
const MAX_PACKET_BYTES = 2 * 1024 * 1024;
const MAX_ARTIFACT_BYTES = 4 * 1024 * 1024;
const SKIP_DIRECTORIES = new Set([
  '.git',
  '.scbe',
  'node_modules',
  '.next',
  '.cache',
  'dist',
  'artifacts',
]);

const ROUTE_PRESETS = Object.freeze({
  code: Object.freeze(['workspace']),
  scholarly: Object.freeze(['arxiv', 'semantic_scholar', 'openalex', 'crossref']),
  software: Object.freeze(['workspace', 'github_repos', 'hf_models']),
  biomedical: Object.freeze(['pubmed', 'semantic_scholar', 'crossref']),
  patent: Object.freeze(['workspace', 'crossref', 'uspto']),
  'cross-check': Object.freeze(['workspace', 'semantic_scholar', 'crossref', 'github_repos']),
  full: Object.freeze([
    'workspace',
    'arxiv',
    'semantic_scholar',
    'openalex',
    'crossref',
    'github_repos',
  ]),
});

const STOP_WORDS = new Set([
  'about',
  'after',
  'again',
  'against',
  'also',
  'and',
  'are',
  'been',
  'before',
  'being',
  'between',
  'can',
  'could',
  'does',
  'from',
  'have',
  'into',
  'more',
  'most',
  'other',
  'should',
  'that',
  'their',
  'then',
  'there',
  'these',
  'they',
  'this',
  'those',
  'through',
  'using',
  'what',
  'when',
  'where',
  'which',
  'while',
  'with',
  'would',
  'your',
  'for',
  'the',
  'how',
  'why',
  'who',
  'its',
  'not',
  'use',
]);

function clampInteger(value, minimum, maximum, fallback) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(maximum, Math.max(minimum, Math.trunc(parsed)));
}

function safeText(value, limit = 500) {
  return String(value || '')
    .replace(/[\x00-\x08\x0B-\x1F\x7F-\x9F\u202A-\u202E\u2066-\u2069]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, limit);
}

function safeUrl(value) {
  const url = safeText(value, 2_000);
  if (/^https?:\/\//i.test(url) || /^workspace:\/\//i.test(url)) return url;
  return '';
}

function tokenize(value) {
  return (
    safeText(value, 20_000)
      .toLowerCase()
      .match(/[a-z0-9][a-z0-9._+-]{2,}/g) || []
  );
}

function normalizeTitle(value) {
  return tokenize(value)
    .filter((token) => !STOP_WORDS.has(token))
    .join(' ');
}

function extractKeywords(values, limit = 16) {
  const counts = new Map();
  for (const value of values) {
    for (const token of tokenize(value)) {
      if (STOP_WORDS.has(token) || token.length < 3 || token.length > 48) continue;
      counts.set(token, (counts.get(token) || 0) + 1);
    }
  }
  return Array.from(counts.entries())
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .slice(0, limit)
    .map(([keyword]) => keyword);
}

function evidenceDirectory(workspaceRoot, options = {}) {
  return path.join(
    scbeHome(options.env, options.home),
    'evidence',
    workspaceKey(workspaceRoot, options)
  );
}

function packetDirectory(workspaceRoot, options = {}) {
  return path.join(evidenceDirectory(workspaceRoot, options), 'packets');
}

function evidenceLedgerPath(workspaceRoot, options = {}) {
  return path.join(evidenceDirectory(workspaceRoot, options), 'receipts.jsonl');
}

function safePacketId(value) {
  const id = String(value || '').trim();
  if (!/^[a-zA-Z0-9._-]{1,120}$/.test(id)) throw new Error('invalid evidence packet id');
  return id;
}

function makePacketId(now = new Date(), randomBytes = crypto.randomBytes) {
  const stamp = now
    .toISOString()
    .replace(/[-:]/g, '')
    .replace(/\.\d{3}Z$/, 'Z');
  return stamp + '-' + randomBytes(4).toString('hex');
}

function packetPath(workspaceRoot, packetId, options = {}) {
  return path.join(packetDirectory(workspaceRoot, options), safePacketId(packetId) + '.json');
}

function writeJsonAtomic(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const temporary =
    filePath + '.' + process.pid + '.' + crypto.randomBytes(3).toString('hex') + '.tmp';
  fs.writeFileSync(temporary, JSON.stringify(value, null, 2) + '\n', 'utf8');
  fs.renameSync(temporary, filePath);
}

function isInside(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function readJsonWithin(root, filePath, maximumBytes, label) {
  const realRoot = fs.realpathSync(root);
  const realFile = fs.realpathSync(filePath);
  if (!isInside(realRoot, realFile)) throw new Error(label + ' resolves outside evidence storage');
  const stat = fs.statSync(realFile);
  if (!stat.isFile()) throw new Error(label + ' is not a regular file');
  if (stat.size > maximumBytes) throw new Error(label + ' exceeds the verification limit');
  return JSON.parse(fs.readFileSync(realFile, 'utf8'));
}

function itemTitle(item, source, index) {
  return safeText(
    item?.title ||
      item?.name ||
      item?.model_id ||
      item?.application_number ||
      source + ' result ' + (index + 1),
    240
  );
}

function itemSummary(item) {
  const words = safeText(
    item?.summary || item?.abstract || item?.description || item?.publisher || item?.journal || '',
    5_000
  )
    .split(/\s+/)
    .filter(Boolean);
  const compact = [];
  for (let index = 0; index < words.length && compact.join(' ').length < 220;) {
    let repeated = false;
    const maximumBlock = Math.min(8, compact.length, words.length - index);
    for (let block = maximumBlock; block >= 1; block -= 1) {
      const previous = compact.slice(-block).join('\0').toLowerCase();
      const upcoming = words
        .slice(index, index + block)
        .join('\0')
        .toLowerCase();
      if (previous === upcoming) {
        index += block;
        repeated = true;
        break;
      }
    }
    if (!repeated) compact.push(words[index++]);
  }
  return safeText(compact.join(' '), 220);
}

function itemUrl(item) {
  const direct = safeUrl(item?.url);
  if (direct) return direct;
  const doi = safeText(item?.doi, 300).replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, '');
  return doi ? 'https://doi.org/' + encodeURI(doi) : '';
}

function itemIdentifier(item, title, url) {
  const raw =
    item?.doi ||
    item?.pmid ||
    item?.application_number ||
    item?.notice_id ||
    item?.model_id ||
    item?.name ||
    url;
  const identifier = safeText(raw, 500).toLowerCase();
  return identifier || normalizeTitle(title);
}

function normalizeEvidenceItem(source, item, index, artifactPath) {
  const title = itemTitle(item, source, index);
  const summary = itemSummary(item);
  const url = itemUrl(item);
  const identifier = itemIdentifier(item, title, url);
  const itemHashes = multiHashJson(item && typeof item === 'object' ? item : { value: item });
  return {
    source,
    title,
    summary,
    url,
    identifier,
    title_key: normalizeTitle(title),
    artifact_pointer: artifactPath + '#/response/results/' + index,
    proof_root: multiHashRoot(itemHashes, 'SCBE-EVIDENCE-ITEM-v1'),
  };
}

function assignEvidenceIds(evidence) {
  return evidence.map((item, index) => ({ id: 'E' + (index + 1), ...item }));
}

function buildCrossChecks(evidence) {
  const groups = new Map();
  for (const item of evidence) {
    const key = item.identifier || item.title_key;
    if (!key) continue;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  }
  const checks = [];
  for (const rows of groups.values()) {
    const sources = Array.from(new Set(rows.map((row) => row.source)));
    if (sources.length < 2) continue;
    checks.push({
      title: rows[0].title,
      evidence_ids: rows.map((row) => row.id),
      sources,
      basis: 'matching normalized identifier or title',
      interpretation: 'cross-source agreement; not independent proof of truth',
    });
  }
  return checks.slice(0, 12);
}

function roundRobinEvidence(evidence, limit = 30) {
  const bySource = new Map();
  for (const row of evidence) {
    if (!bySource.has(row.source)) bySource.set(row.source, []);
    bySource.get(row.source).push(row);
  }
  const ordered = [];
  while (ordered.length < limit) {
    let moved = false;
    for (const rows of bySource.values()) {
      if (!rows.length) continue;
      ordered.push(rows.shift());
      moved = true;
      if (ordered.length >= limit) break;
    }
    if (!moved) break;
  }
  return ordered;
}

function compactPacketView(packet, tokenBudget) {
  const maximumCharacters = clampInteger(tokenBudget, 256, 4_000, 1_200) * 4;
  const view = {
    ok: packet.successful_stops > 0,
    schema_version: 'scbe_guided_context_packet_v1',
    packet_id: packet.packet_id,
    route: packet.route,
    objective: packet.objective,
    keywords: packet.keywords,
    source_status: packet.source_status,
    cross_checks: packet.cross_checks,
    evidence: [],
    retrieval: {
      packet_id: packet.packet_id,
      search_tool: 'search_evidence',
      verify_tool: 'verify_evidence',
      raw_results_in_prompt: false,
    },
    receipt: {
      hash_suite: packet.receipt.hash_suite,
      receipt_root: packet.receipt.receipt_root,
      packet_hashes: packet.receipt.payload.packet_hashes,
    },
    context_metrics: {
      raw_characters: packet.context_metrics.raw_characters,
      returned_characters: 0,
      estimated_raw_tokens: Math.ceil(packet.context_metrics.raw_characters / 4),
      estimated_returned_tokens: 0,
      reduction_ratio: 1,
      full_results_retained: true,
      budget_characters: maximumCharacters,
      budget_exceeded_by_required_metadata: false,
    },
  };

  for (const item of roundRobinEvidence(packet.evidence)) {
    const compact = {
      id: item.id,
      source: item.source,
      title: item.title,
      url: item.url,
      summary: item.summary,
      proof_root: item.proof_root,
    };
    const candidate = { ...view, evidence: [...view.evidence, compact] };
    if (view.evidence.length > 0 && JSON.stringify(candidate).length > maximumCharacters) break;
    view.evidence.push(compact);
  }

  const measure = () => {
    let returnedCharacters = JSON.stringify(view).length;
    view.context_metrics.returned_characters = returnedCharacters;
    view.context_metrics.estimated_returned_tokens = Math.ceil(returnedCharacters / 4);
    view.context_metrics.reduction_ratio =
      packet.context_metrics.raw_characters > 0
        ? Number((returnedCharacters / packet.context_metrics.raw_characters).toFixed(4))
        : 1;
    returnedCharacters = JSON.stringify(view).length;
    view.context_metrics.returned_characters = returnedCharacters;
    view.context_metrics.estimated_returned_tokens = Math.ceil(returnedCharacters / 4);
    return returnedCharacters;
  };
  let returnedCharacters = measure();
  while (view.evidence.length > 1 && returnedCharacters > maximumCharacters) {
    view.evidence.pop();
    returnedCharacters = measure();
  }
  view.context_metrics.budget_exceeded_by_required_metadata =
    returnedCharacters > maximumCharacters;
  measure();
  return view;
}

async function runGuidedEvidenceRoute(options = {}) {
  const workspaceRoot = path.resolve(options.workspaceRoot || process.cwd());
  const objective = safeText(options.objective, MAX_OBJECTIVE_CHARS);
  if (objective.length < 3) throw new Error('objective must contain at least 3 characters');
  const route = String(options.route || 'cross-check').toLowerCase();
  const preset = ROUTE_PRESETS[route];
  if (!preset) throw new Error('unknown evidence route: ' + route);
  if (typeof options.sourceRunner !== 'function')
    throw new Error('guided evidence source runner is unavailable');
  const resultLimit = clampInteger(options.limit, 1, 5, 3);
  const tokenBudget = clampInteger(options.tokenBudget, 256, 4_000, 1_200);
  const maxStops = clampInteger(options.maxStops, 1, 6, preset.length);
  const now = options.now || new Date();
  const packetId = options.packetId || makePacketId(now, options.randomBytes || crypto.randomBytes);
  const root = evidenceDirectory(workspaceRoot, options);
  const routeDir = path.join(root, 'artifacts', safePacketId(packetId));
  const sources = preset.slice(0, maxStops);

  const sourceRows = await Promise.all(
    sources.map(async (source) => {
      try {
        const response = await options.sourceRunner({
          source,
          query: objective,
          limit: resultLimit,
        });
        return {
          source,
          ok: response?.ok === true,
          response:
            response && typeof response === 'object'
              ? response
              : { ok: false, error: 'invalid response' },
          error:
            response?.ok === true ? null : safeText(response?.error || 'source query failed', 300),
        };
      } catch (error) {
        return {
          source,
          ok: false,
          response: {
            ok: false,
            source,
            count: 0,
            results: [],
            error: safeText(error.message || error, 300),
          },
          error: safeText(error.message || error, 300),
        };
      }
    })
  );

  const artifacts = [];
  const evidence = [];
  let rawCharacters = 0;
  for (const row of sourceRows) {
    const artifactBody = {
      schema_version: ARTIFACT_SCHEMA,
      packet_id: packetId,
      source: row.source,
      query: objective,
      captured_at: now.toISOString(),
      response: row.response,
    };
    rawCharacters += canonicalJson(row.response).length;
    const hashes = multiHashJson(artifactBody);
    const integrity = {
      hash_suite: HASH_SUITE,
      hashes,
      root: multiHashRoot(hashes, 'SCBE-EVIDENCE-ARTIFACT-v1'),
    };
    const artifactFile = path.join(routeDir, row.source + '.json');
    writeJsonAtomic(artifactFile, { ...artifactBody, integrity });
    const relativeArtifact = path.relative(root, artifactFile).replace(/\\/g, '/');
    artifacts.push({
      source: row.source,
      path: relativeArtifact,
      ok: row.ok,
      count: Array.isArray(row.response.results) ? row.response.results.length : 0,
      integrity,
      error: row.error,
    });
    const results = Array.isArray(row.response.results)
      ? row.response.results.slice(0, resultLimit)
      : [];
    for (let index = 0; index < results.length; index += 1) {
      evidence.push(normalizeEvidenceItem(row.source, results[index], index, relativeArtifact));
    }
  }

  const numberedEvidence = assignEvidenceIds(evidence);
  const sourceStatus = sourceRows.map((row) => ({
    source: row.source,
    ok: row.ok,
    count: Array.isArray(row.response.results) ? row.response.results.length : 0,
    error: row.error,
  }));
  const successfulStops = sourceRows.filter((row) => row.ok).length;
  const packetBody = {
    schema_version: PACKET_SCHEMA,
    packet_id: packetId,
    created_at: now.toISOString(),
    workspace_key: workspaceKey(workspaceRoot, options),
    route,
    objective,
    stops: sources,
    successful_stops: successfulStops,
    failed_stops: sourceRows.length - successfulStops,
    source_status: sourceStatus,
    keywords: extractKeywords([
      objective,
      ...numberedEvidence.map((row) => row.title),
      ...numberedEvidence.map((row) => row.summary),
    ]),
    evidence: numberedEvidence,
    cross_checks: buildCrossChecks(numberedEvidence),
    artifacts,
    context_metrics: {
      raw_characters: rawCharacters,
      normalized_reference_characters: JSON.stringify(numberedEvidence).length,
      raw_results_stored_outside_context: true,
    },
  };
  const packetHashes = multiHashJson(packetBody);
  const receipt = appendChainedReceipt(
    evidenceLedgerPath(workspaceRoot, options),
    {
      schema_version: PACKET_RECEIPT_SCHEMA,
      packet_id: packetId,
      route,
      objective_sha256: crypto.createHash('sha256').update(objective, 'utf8').digest('hex'),
      packet_hashes: packetHashes,
      packet_root: multiHashRoot(packetHashes, 'SCBE-EVIDENCE-PACKET-v1'),
      artifact_roots: artifacts.map((artifact) => ({
        source: artifact.source,
        root: artifact.integrity.root,
      })),
    },
    { receiptType: 'guided_evidence_packet', now }
  );
  const packet = { ...packetBody, receipt };
  writeJsonAtomic(packetPath(workspaceRoot, packetId, options), packet);
  return compactPacketView(packet, tokenBudget);
}

function scorePacket(packet, terms) {
  const objective = tokenize(packet.objective).join(' ');
  const keywords = Array.isArray(packet.keywords) ? packet.keywords.join(' ').toLowerCase() : '';
  const evidence = Array.isArray(packet.evidence) ? packet.evidence : [];
  let score = 0;
  for (const term of terms) {
    if (objective.includes(term)) score += 4;
    if (keywords.includes(term)) score += 3;
    for (const row of evidence) {
      if (
        String(row.title || '')
          .toLowerCase()
          .includes(term)
      )
        score += 2;
      if (
        String(row.summary || '')
          .toLowerCase()
          .includes(term)
      )
        score += 1;
    }
  }
  return score;
}

function searchEvidencePackets(workspaceRoot, query, options = {}) {
  const terms = extractKeywords([query], 12);
  if (!terms.length) throw new Error('evidence search requires a keyword');
  const limit = clampInteger(options.limit, 1, 50, 10);
  const dir = packetDirectory(workspaceRoot, options);
  if (!fs.existsSync(dir))
    return { ok: true, query: safeText(query, 500), matches: [], scanned: 0 };
  const root = evidenceDirectory(workspaceRoot, options);
  const files = fs
    .readdirSync(dir)
    .filter((name) => name.endsWith('.json'))
    .sort()
    .reverse()
    .slice(0, MAX_PACKET_SCAN);
  const matches = [];
  for (const file of files) {
    try {
      const packet = readJsonWithin(
        root,
        path.join(dir, file),
        MAX_PACKET_BYTES,
        'evidence packet'
      );
      const score = scorePacket(packet, terms);
      if (score <= 0) continue;
      const evidence = (Array.isArray(packet.evidence) ? packet.evidence : [])
        .filter((row) =>
          terms.some((term) => (row.title + ' ' + row.summary).toLowerCase().includes(term))
        )
        .slice(0, 5)
        .map((row) => ({
          id: row.id,
          source: row.source,
          title: row.title,
          url: row.url,
          proof_root: row.proof_root,
        }));
      matches.push({
        packet_id: packet.packet_id,
        route: packet.route,
        objective: packet.objective,
        created_at: packet.created_at,
        keywords: packet.keywords,
        score,
        evidence,
        receipt_root: packet.receipt?.receipt_root || null,
      });
    } catch (_error) {
      // Corrupt packets are surfaced by verify_evidence rather than injected into search context.
    }
  }
  matches.sort(
    (left, right) =>
      right.score - left.score || String(right.created_at).localeCompare(left.created_at)
  );
  return {
    ok: true,
    query: safeText(query, 500),
    terms,
    matches: matches.slice(0, limit),
    scanned: files.length,
  };
}

function verifyArtifact(root, manifest, packetId) {
  const candidate = path.resolve(root, String(manifest.path || ''));
  const relative = path.relative(root, candidate);
  if (relative.startsWith('..') || path.isAbsolute(relative))
    return { ok: false, error: 'artifact path escaped root' };
  if (!fs.existsSync(candidate))
    return { ok: false, error: 'artifact missing', path: manifest.path };
  try {
    const stored = readJsonWithin(root, candidate, MAX_ARTIFACT_BYTES, 'evidence artifact');
    const integrity = stored.integrity;
    const body = { ...stored };
    delete body.integrity;
    const hashes = multiHashJson(body);
    const rootHash = multiHashRoot(hashes, 'SCBE-EVIDENCE-ARTIFACT-v1');
    const metadataBound =
      stored.schema_version === ARTIFACT_SCHEMA &&
      stored.packet_id === packetId &&
      stored.source === manifest.source;
    return {
      ok:
        metadataBound &&
        sameHashes(hashes, integrity?.hashes) &&
        sameHashes(hashes, manifest.integrity?.hashes) &&
        rootHash === integrity?.root &&
        rootHash === manifest.integrity?.root,
      path: manifest.path,
      root: rootHash,
      error: metadataBound ? undefined : 'artifact metadata binding mismatch',
    };
  } catch (error) {
    return { ok: false, path: manifest.path, error: safeText(error.message || error, 300) };
  }
}

function verifyEvidencePacket(workspaceRoot, packetId, options = {}) {
  const root = evidenceDirectory(workspaceRoot, options);
  const filePath = packetPath(workspaceRoot, packetId, options);
  if (!fs.existsSync(filePath)) throw new Error('evidence packet not found: ' + packetId);
  const packet = readJsonWithin(root, filePath, MAX_PACKET_BYTES, 'evidence packet');
  const receipt = packet.receipt;
  const body = { ...packet };
  delete body.receipt;
  const packetHashes = multiHashJson(body);
  const receiptCheck = verifyChainedReceipt(receipt);
  const packetHashOk = sameHashes(packetHashes, receipt?.payload?.packet_hashes);
  const packetRoot = multiHashRoot(packetHashes, 'SCBE-EVIDENCE-PACKET-v1');
  const artifacts = (Array.isArray(packet.artifacts) ? packet.artifacts : []).map((manifest) =>
    verifyArtifact(root, manifest, packet.packet_id)
  );
  const expectedArtifactRoots = (Array.isArray(packet.artifacts) ? packet.artifacts : []).map(
    (artifact) => ({
      source: artifact.source,
      root: artifact.integrity?.root,
    })
  );
  const artifactRootsBound =
    canonicalJson(expectedArtifactRoots) === canonicalJson(receipt?.payload?.artifact_roots || []);
  const ledger = verifyReceiptFile(evidenceLedgerPath(workspaceRoot, options));
  const receiptInLedger = ledger.receipts.some((row) => row.receipt_root === receipt?.receipt_root);
  const errors = [];
  if (packet.schema_version !== PACKET_SCHEMA) errors.push('unsupported packet schema');
  if (packet.packet_id !== safePacketId(packetId)) errors.push('packet filename binding mismatch');
  if (packet.workspace_key !== workspaceKey(workspaceRoot, options))
    errors.push('packet workspace binding mismatch');
  if (receipt?.receipt_type !== 'guided_evidence_packet')
    errors.push('unexpected packet receipt type');
  if (receipt?.payload?.schema_version !== PACKET_RECEIPT_SCHEMA)
    errors.push('unsupported packet receipt schema');
  if (receipt?.payload?.packet_id !== packet.packet_id) errors.push('packet id binding mismatch');
  if (receipt?.payload?.route !== packet.route) errors.push('packet route binding mismatch');
  const objectiveSha256 = crypto
    .createHash('sha256')
    .update(String(packet.objective || ''), 'utf8')
    .digest('hex');
  if (receipt?.payload?.objective_sha256 !== objectiveSha256)
    errors.push('packet objective binding mismatch');
  if (!receiptCheck.ok) errors.push(...receiptCheck.errors);
  if (!packetHashOk) errors.push('packet hash mismatch');
  if (receipt?.payload?.packet_root !== packetRoot) errors.push('packet root mismatch');
  if (!artifactRootsBound) errors.push('artifact root binding mismatch');
  if (!ledger.ok) errors.push(...ledger.errors);
  if (!receiptInLedger) errors.push('packet receipt is absent from ledger');
  if (artifacts.some((artifact) => !artifact.ok))
    errors.push('one or more artifacts failed verification');
  return {
    ok: errors.length === 0,
    packet_id: packet.packet_id,
    route: packet.route,
    receipt_root: receipt?.receipt_root || null,
    packet_hashes: packetHashes,
    artifacts,
    ledger: {
      ok: ledger.ok,
      legacy_receipts: ledger.legacy_receipts,
      chained_receipts: ledger.chained_receipts,
      root: ledger.root,
    },
    errors,
  };
}

function searchWorkspaceEvidence(workspaceRoot, query, limit = 3) {
  const root = fs.realpathSync(path.resolve(workspaceRoot));
  const terms = extractKeywords([query], 8);
  const maximum = clampInteger(limit, 1, 20, 3);
  const deadline = Date.now() + WORKSPACE_SEARCH_MS;
  const queue = [{ dir: root, depth: 0 }];
  const results = [];
  let scanned = 0;
  while (
    queue.length &&
    scanned < WORKSPACE_SEARCH_FILES &&
    results.length < maximum &&
    Date.now() <= deadline
  ) {
    const current = queue.shift();
    let entries;
    try {
      entries = fs.readdirSync(current.dir, { withFileTypes: true });
    } catch (_error) {
      continue;
    }
    for (const entry of entries) {
      if (Date.now() > deadline || scanned >= WORKSPACE_SEARCH_FILES || results.length >= maximum)
        break;
      if (entry.name.startsWith('.') && entry.name !== '.github') continue;
      const absolute = path.join(current.dir, entry.name);
      if (
        entry.isDirectory() &&
        !entry.isSymbolicLink() &&
        current.depth < 10 &&
        !SKIP_DIRECTORIES.has(entry.name)
      ) {
        queue.push({ dir: absolute, depth: current.depth + 1 });
        continue;
      }
      if (!entry.isFile()) continue;
      scanned += 1;
      let stat;
      try {
        stat = fs.statSync(absolute);
      } catch (_error) {
        continue;
      }
      if (stat.size > WORKSPACE_FILE_BYTES) continue;
      let content;
      try {
        content = fs.readFileSync(absolute, 'utf8');
      } catch (_error) {
        continue;
      }
      if (content.includes('\0')) continue;
      const lines = content.split(/\r?\n/);
      for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
        const line = lines[lineIndex];
        const lower = line.toLowerCase();
        if (!terms.some((term) => lower.includes(term))) continue;
        const relative = path.relative(root, absolute).replace(/\\/g, '/');
        results.push({
          title: relative + ':' + (lineIndex + 1),
          summary: safeText(line, 400),
          url: 'workspace://' + encodeURI(relative) + '#L' + (lineIndex + 1),
          path: relative,
          line: lineIndex + 1,
        });
        break;
      }
    }
  }
  return {
    ok: true,
    api: 'workspace',
    count: results.length,
    results,
    scanned_files: scanned,
    time_limited: Date.now() > deadline,
  };
}

module.exports = {
  PACKET_SCHEMA,
  ARTIFACT_SCHEMA,
  PACKET_RECEIPT_SCHEMA,
  ROUTE_PRESETS,
  evidenceDirectory,
  evidenceLedgerPath,
  packetDirectory,
  packetPath,
  makePacketId,
  extractKeywords,
  runGuidedEvidenceRoute,
  searchEvidencePackets,
  verifyEvidencePacket,
  searchWorkspaceEvidence,
};
