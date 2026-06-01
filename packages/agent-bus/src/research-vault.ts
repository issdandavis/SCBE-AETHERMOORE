import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { type BridgeRoutePlan, planBridgeRoute } from './multi-bridge.js';

export type ResearchSourceType =
  | 'book'
  | 'paper'
  | 'video'
  | 'interview'
  | 'note'
  | 'web'
  | 'primary_doc';
export type ResearchRightsStatus =
  | 'owned'
  | 'public_domain'
  | 'licensed'
  | 'citation_only'
  | 'unknown';
export type ResearchQuality = 'raw' | 'reviewed' | 'trusted';
export type ResearchStyleScope = 'author' | 'project' | 'chapter' | 'scene' | 'proposal';
export type ResearchMechanicsVisibility = 'hidden' | 'light' | 'explicit';
export type ResearchReviewDecision = 'approve' | 'revise' | 'reject';
export type ResearchVaultDecision = 'ALLOW' | 'REVIEW' | 'QUARANTINE' | 'DENY';
export type ResearchVaultLabel =
  | 'author_voice_guides_framed_phrases'
  | 'author_quotes'
  | 'quotes_from_sources'
  | 'extrapolation'
  | 'history'
  | 'sources'
  | 'ai_prose'
  | 'author_prose'
  | 'author_quotes_with_extensions'
  | 'lore_sources'
  | 'citation_needed'
  | 'human_review_required';

export interface ResearchSourceCard {
  schema_version: 'source_card_v1';
  source_id: string;
  title: string;
  author: string;
  source_type: ResearchSourceType;
  locator: string;
  rights_status: ResearchRightsStatus;
  claims: string[];
  quotes: string[];
  verified_notes: string[];
  quality: ResearchQuality;
  created_at: string;
  namespace: string;
}

export interface ResearchStyleCard {
  schema_version: 'style_card_v1';
  style_id: string;
  scope: ResearchStyleScope;
  allowed_moves: string[];
  banned_moves: string[];
  cadence_notes: string[];
  quote_rules: string[];
  mechanics_visibility: ResearchMechanicsVisibility;
  created_at: string;
  namespace: string;
}

export interface ResearchSelectedNote {
  source_id: string;
  note: string;
  labels: ResearchVaultLabel[];
}

export interface ResearchRetrievalPacket {
  schema_version: 'retrieval_packet_v1';
  packet_id: string;
  task_id: string;
  query: string;
  source_cards: ResearchSourceCard[];
  style_cards: ResearchStyleCard[];
  selected_notes: ResearchSelectedNote[];
  blocked_sources: Array<{ source_id: string; reason: string }>;
  citation_requirements: string[];
  review_required: boolean;
  namespace: string;
  created_at: string;
}

export interface ResearchReviewRecord {
  schema_version: 'review_decision_v1';
  packet_id: string;
  reviewer: 'human' | 'agent';
  decision: ResearchReviewDecision;
  reasons: string[];
  approved_output_path: string;
  audit_hash: string;
}

export interface ResearchVaultFinding {
  code: string;
  severity: 'info' | 'warn' | 'block';
  detail: string;
}

export interface ResearchVaultPlan {
  schema_version: 'scbe.agent_bus.research_vault_plan.v1';
  generated_at: string;
  packet: ResearchRetrievalPacket;
  bridge_plan: BridgeRoutePlan;
  governance: {
    decision: ResearchVaultDecision;
    findings: ResearchVaultFinding[];
    blocked_actions: string[];
  };
  audit: {
    packet_sha256: string;
    source_count: number;
    style_count: number;
    selected_note_count: number;
    namespace: string;
  };
}

export interface ResearchSourceCardInput {
  source_id?: string;
  title: string;
  author?: string;
  source_type: ResearchSourceType;
  locator: string;
  rights_status?: ResearchRightsStatus;
  claims?: string[];
  quotes?: string[];
  verified_notes?: string[];
  quality?: ResearchQuality;
  created_at?: string;
  namespace?: string;
}

export interface ResearchStyleCardInput {
  style_id?: string;
  scope: ResearchStyleScope;
  allowed_moves?: string[];
  banned_moves?: string[];
  cadence_notes?: string[];
  quote_rules?: string[];
  mechanics_visibility?: ResearchMechanicsVisibility;
  created_at?: string;
  namespace?: string;
}

export interface ResearchRetrievalPacketInput {
  packet_id?: string;
  task_id?: string;
  query: string;
  source_cards: Array<ResearchSourceCardInput | ResearchSourceCard>;
  style_cards?: Array<ResearchStyleCardInput | ResearchStyleCard>;
  namespace?: string;
  created_at?: string;
  max_notes?: number;
  allow_unknown_rights?: boolean;
  allow_cross_namespace?: boolean;
  require_review?: boolean;
}

export interface ResearchVaultPlanInput extends ResearchRetrievalPacketInput {
  reviewer_agent?: string;
  generated_at?: string;
}

const SECRET_PATTERNS: RegExp[] = [
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/i,
  /\b(api[_-]?key|token|secret|password)\s*[:=]\s*['"]?[A-Za-z0-9_\-.]{12,}/i,
  /\bBearer\s+[A-Za-z0-9_\-.]{12,}/i,
];

function stableId(prefix: string, value: string): string {
  return `${prefix}-${crypto.createHash('sha256').update(value).digest('hex').slice(0, 16)}`;
}

function normalizeText(value: string | undefined, fallback = ''): string {
  return String(value ?? fallback).trim();
}

function cleanList(values: string[] | undefined): string[] {
  return [...(values || [])].map((value) => normalizeText(value)).filter(Boolean);
}

function hasSecretMaterial(values: string[]): boolean {
  const text = values.join('\n');
  return SECRET_PATTERNS.some((pattern) => pattern.test(text));
}

function hashPacket(packet: ResearchRetrievalPacket): string {
  return crypto.createHash('sha256').update(JSON.stringify(packet)).digest('hex');
}

function isSourceCard(
  value: ResearchSourceCardInput | ResearchSourceCard
): value is ResearchSourceCard {
  return 'schema_version' in value && value.schema_version === 'source_card_v1';
}

function isStyleCard(
  value: ResearchStyleCardInput | ResearchStyleCard
): value is ResearchStyleCard {
  return 'schema_version' in value && value.schema_version === 'style_card_v1';
}

export function createResearchSourceCard(input: ResearchSourceCardInput): ResearchSourceCard {
  const title = normalizeText(input.title);
  const locator = normalizeText(input.locator);
  if (!title) throw new Error('source card missing title');
  if (!locator) throw new Error('source card missing locator');
  const createdAt = input.created_at || new Date().toISOString();
  const claims = cleanList(input.claims);
  const quotes = cleanList(input.quotes);
  const verifiedNotes = cleanList(input.verified_notes);
  const sourceId =
    normalizeText(input.source_id) ||
    stableId('source', `${title}:${input.author || ''}:${input.source_type}:${locator}`);
  return {
    schema_version: 'source_card_v1',
    source_id: sourceId,
    title,
    author: normalizeText(input.author, 'unknown'),
    source_type: input.source_type,
    locator,
    rights_status: input.rights_status || 'unknown',
    claims,
    quotes,
    verified_notes: verifiedNotes,
    quality: input.quality || 'raw',
    created_at: createdAt,
    namespace: normalizeText(input.namespace, 'internal'),
  };
}

export function createResearchStyleCard(input: ResearchStyleCardInput): ResearchStyleCard {
  const createdAt = input.created_at || new Date().toISOString();
  const basis = [
    input.scope,
    ...(input.allowed_moves || []),
    ...(input.banned_moves || []),
    ...(input.cadence_notes || []),
  ].join(':');
  return {
    schema_version: 'style_card_v1',
    style_id: normalizeText(input.style_id) || stableId('style', basis),
    scope: input.scope,
    allowed_moves: cleanList(input.allowed_moves),
    banned_moves: cleanList(input.banned_moves),
    cadence_notes: cleanList(input.cadence_notes),
    quote_rules: cleanList(input.quote_rules),
    mechanics_visibility: input.mechanics_visibility || 'hidden',
    created_at: createdAt,
    namespace: normalizeText(input.namespace, 'internal'),
  };
}

function selectedLabels(source: ResearchSourceCard): ResearchVaultLabel[] {
  const labels: ResearchVaultLabel[] = ['sources'];
  if (source.quotes.length > 0) labels.push('quotes_from_sources');
  if (source.quality === 'raw' || source.rights_status === 'unknown')
    labels.push('citation_needed');
  return labels;
}

function collectFindings(packet: ResearchRetrievalPacket): ResearchVaultFinding[] {
  const findings: ResearchVaultFinding[] = [];
  const namespaces = new Set([
    ...packet.source_cards.map((source) => source.namespace),
    ...packet.style_cards.map((style) => style.namespace),
  ]);
  if (packet.blocked_sources.length > 0) {
    findings.push({
      code: 'blocked_sources_present',
      severity: 'warn',
      detail: `${packet.blocked_sources.length} source(s) blocked from packet`,
    });
  }
  if (
    namespaces.size > 1 ||
    packet.blocked_sources.some((blocked) => blocked.reason.includes('namespace'))
  ) {
    findings.push({
      code: 'mixed_namespaces',
      severity: 'block',
      detail: 'source/style cards span more than one namespace',
    });
  }
  if (packet.selected_notes.length === 0) {
    findings.push({
      code: 'empty_selected_notes',
      severity: 'block',
      detail: 'retrieval packet has no selected notes',
    });
  }
  const packetText = [
    packet.query,
    ...packet.selected_notes.map((note) => note.note),
    ...packet.source_cards.flatMap((source) => [...source.claims, ...source.quotes]),
  ];
  if (hasSecretMaterial(packetText)) {
    findings.push({
      code: 'secret_material_detected',
      severity: 'block',
      detail: 'packet text appears to contain credential or private-key material',
    });
  }
  if (packet.review_required) {
    findings.push({
      code: 'human_review_required',
      severity: 'info',
      detail: 'packet must be reviewed before client-facing output',
    });
  }
  return findings;
}

function decideResearchVaultPlan(findings: ResearchVaultFinding[]): ResearchVaultDecision {
  if (findings.some((finding) => finding.severity === 'block')) return 'DENY';
  if (findings.some((finding) => finding.code === 'blocked_sources_present')) return 'QUARANTINE';
  if (findings.some((finding) => finding.code === 'human_review_required')) return 'REVIEW';
  return 'ALLOW';
}

export function buildResearchRetrievalPacket(
  input: ResearchRetrievalPacketInput
): ResearchRetrievalPacket {
  const namespace = normalizeText(input.namespace, 'internal');
  const createdAt = input.created_at || new Date().toISOString();
  const sourceCards = input.source_cards.map((source) =>
    isSourceCard(source)
      ? source
      : createResearchSourceCard({ ...source, namespace: source.namespace || namespace })
  );
  const styleCards = (input.style_cards || []).map((style) =>
    isStyleCard(style)
      ? style
      : createResearchStyleCard({ ...style, namespace: style.namespace || namespace })
  );
  const blockedSources: ResearchRetrievalPacket['blocked_sources'] = [];
  const allowedSources = sourceCards.filter((source) => {
    if (!input.allow_cross_namespace && source.namespace !== namespace) {
      blockedSources.push({ source_id: source.source_id, reason: 'namespace_mismatch' });
      return false;
    }
    if (!input.allow_unknown_rights && source.rights_status === 'unknown') {
      blockedSources.push({ source_id: source.source_id, reason: 'unknown_rights' });
      return false;
    }
    return true;
  });
  for (const style of styleCards) {
    if (!input.allow_cross_namespace && style.namespace !== namespace) {
      blockedSources.push({ source_id: style.style_id, reason: 'style_namespace_mismatch' });
    }
  }
  const maxNotes = Math.max(1, input.max_notes || 12);
  const selectedNotes: ResearchSelectedNote[] = [];
  for (const source of allowedSources) {
    const notes = source.verified_notes.length > 0 ? source.verified_notes : source.claims;
    for (const note of notes) {
      if (selectedNotes.length >= maxNotes) break;
      selectedNotes.push({ source_id: source.source_id, note, labels: selectedLabels(source) });
    }
    if (selectedNotes.length >= maxNotes) break;
  }
  const citationRequirements = allowedSources.map(
    (source) => `${source.source_id}: cite ${source.locator}`
  );
  const packetDraft = {
    schema_version: 'retrieval_packet_v1' as const,
    packet_id: '',
    task_id: normalizeText(input.task_id) || stableId('task', `${namespace}:${input.query}`),
    query: normalizeText(input.query),
    source_cards: allowedSources,
    style_cards: styleCards,
    selected_notes: selectedNotes,
    blocked_sources: blockedSources,
    citation_requirements: citationRequirements,
    review_required: input.require_review !== false,
    namespace,
    created_at: createdAt,
  };
  return {
    ...packetDraft,
    packet_id:
      normalizeText(input.packet_id) ||
      stableId('retrieval', `${packetDraft.task_id}:${packetDraft.query}:${createdAt}`),
  };
}

export function planResearchVaultPacket(input: ResearchVaultPlanInput): ResearchVaultPlan {
  const generatedAt = input.generated_at || new Date().toISOString();
  const packet = buildResearchRetrievalPacket(input);
  const findings = collectFindings(packet);
  const decision = decideResearchVaultPlan(findings);
  const blockedActions =
    decision === 'DENY'
      ? ['draft_delivery', 'client_export']
      : decision === 'QUARANTINE'
        ? ['auto_client_export']
        : [];
  const bridgePlan = planBridgeRoute(
    'research vault retrieval packet',
    {
      created_at: generatedAt,
      from: 'research-vault',
      to: [input.reviewer_agent || 'human-review'],
      subject: `Research Vault packet ${packet.packet_id}`,
      body: JSON.stringify({
        packet_id: packet.packet_id,
        query: packet.query,
        namespace: packet.namespace,
        selected_notes: packet.selected_notes.length,
        decision,
      }),
      tags: ['research-vault', 'retrieval-packet', decision.toLowerCase()],
    },
    [
      {
        kind: decision === 'ALLOW' ? 'file' : 'human',
        provider: decision === 'ALLOW' ? 'filesystem' : 'manual',
        label: decision === 'ALLOW' ? 'local research vault packet' : 'human review queue',
        trust: 'local_private',
      },
    ],
    { generated_at: generatedAt }
  );
  return {
    schema_version: 'scbe.agent_bus.research_vault_plan.v1',
    generated_at: generatedAt,
    packet,
    bridge_plan: bridgePlan,
    governance: {
      decision,
      findings,
      blocked_actions: blockedActions,
    },
    audit: {
      packet_sha256: hashPacket(packet),
      source_count: packet.source_cards.length,
      style_count: packet.style_cards.length,
      selected_note_count: packet.selected_notes.length,
      namespace: packet.namespace,
    },
  };
}

export interface ResearchVaultPersistReceipt {
  schema_version: 'scbe.agent_bus.research_vault_persist.v1';
  persisted_at: string;
  workspace_root: string;
  packet_id: string;
  governance_decision: ResearchVaultDecision;
  /**
   * Path to packet JSON written to 10_work/.
   * Null when governance DENY or QUARANTINE blocks the write.
   */
  packet_path: string | null;
  receipt_path: string;
  packet_sha256: string;
}

/**
 * Persist a governed research vault plan to a workspace.
 *
 * ALLOW / REVIEW  → writes packet JSON to 10_work/vault-<packet_id>.json
 *                   + governance receipt to 20_receipts/vault-plan-<packet_id>.json
 * DENY / QUARANTINE → writes only the governance receipt; no packet payload escapes.
 *
 * Throws when workspaceRoot does not exist.
 */
export function persistResearchVaultPlan(
  plan: ResearchVaultPlan,
  workspaceRoot: string
): ResearchVaultPersistReceipt {
  const resolvedRoot = path.resolve(workspaceRoot);
  if (!fs.existsSync(resolvedRoot) || !fs.statSync(resolvedRoot).isDirectory()) {
    throw new Error(`workspace not found at ${resolvedRoot}`);
  }

  const decision = plan.governance.decision;
  const packetId = plan.packet.packet_id;
  const persistedAt = new Date().toISOString();
  const packetJson = `${JSON.stringify(plan.packet, null, 2)}\n`;
  const packetSha256 = crypto.createHash('sha256').update(packetJson).digest('hex');

  let packetPath: string | null = null;
  if (decision === 'ALLOW' || decision === 'REVIEW') {
    const workDir = path.join(resolvedRoot, '10_work');
    fs.mkdirSync(workDir, { recursive: true });
    packetPath = path.join(workDir, `vault-${packetId}.json`);
    fs.writeFileSync(packetPath, packetJson, 'utf8');
  }

  const receiptsDir = path.join(resolvedRoot, '20_receipts');
  fs.mkdirSync(receiptsDir, { recursive: true });
  const receiptPath = path.join(receiptsDir, `vault-plan-${packetId}.json`);

  const receipt: ResearchVaultPersistReceipt = {
    schema_version: 'scbe.agent_bus.research_vault_persist.v1',
    persisted_at: persistedAt,
    workspace_root: resolvedRoot,
    packet_id: packetId,
    governance_decision: decision,
    packet_path: packetPath,
    receipt_path: receiptPath,
    packet_sha256: packetSha256,
  };
  fs.writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
  return receipt;
}
