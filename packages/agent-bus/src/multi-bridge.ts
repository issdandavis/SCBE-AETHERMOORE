import crypto from 'node:crypto';

export type BridgeKind = 'mail' | 'ai_agent' | 'human' | 'webhook' | 'file';
export type BridgeProvider =
  | 'proton'
  | 'gmail'
  | 'apollo'
  | 'codex'
  | 'claude'
  | 'gemini'
  | 'ollama'
  | 'openai'
  | 'anthropic'
  | 'huggingface'
  | 'manual'
  | 'webhook'
  | 'filesystem';
export type BridgeDirection = 'inbound' | 'outbound' | 'bidirectional';
export type BridgeTrust = 'local_private' | 'user_private' | 'team_private' | 'external';
export type BridgeDecision = 'ALLOW' | 'REVIEW' | 'QUARANTINE' | 'DENY';

export interface BridgeEndpoint {
  id: string;
  kind: BridgeKind;
  provider: BridgeProvider;
  label: string;
  trust: BridgeTrust;
  direction: BridgeDirection;
  address?: string;
  agent_id?: string;
  scopes: string[];
  metadata: Record<string, string>;
}

export interface BridgeAttachment {
  name: string;
  bytes: number;
  sha256?: string;
  content_type?: string;
}

export interface BridgeMessage {
  message_id: string;
  created_at: string;
  from: string;
  to: string[];
  subject: string;
  body: string;
  summary: string;
  tags: string[];
  attachments: BridgeAttachment[];
  metadata: Record<string, string>;
}

export interface BridgeRouteHop {
  index: number;
  from: string;
  to: string;
  provider: BridgeProvider;
  action: 'ingest' | 'normalize' | 'route' | 'review' | 'deliver' | 'hold';
}

export interface BridgeGovernanceFinding {
  code: string;
  severity: 'info' | 'warn' | 'block';
  detail: string;
}

export interface BridgeRoutePlan {
  schema_version: 'scbe.agent_bus.multi_bridge_plan.v1';
  generated_at: string;
  intent: string;
  message: BridgeMessage;
  endpoints: BridgeEndpoint[];
  route: {
    decision: BridgeDecision;
    hops: BridgeRouteHop[];
    required_human_gate: boolean;
    next_action: string;
  };
  governance: {
    privacy: 'local_only' | 'remote_allowed';
    findings: BridgeGovernanceFinding[];
    blocked_actions: string[];
  };
  audit: {
    message_sha256: string;
    endpoint_count: number;
    external_targets: string[];
  };
}

export interface AiCommPacket {
  packet_id: string;
  created_at: string;
  sender: string;
  recipient: string;
  intent: string;
  status: 'in_progress' | 'blocked' | 'done';
  repo: string;
  branch: string;
  task_id: string;
  summary: string;
  proof: string[];
  next_action: string;
  risk: 'low' | 'medium' | 'high';
  gates: {
    governance_packet: boolean;
    tests_requested: string[];
  };
}

export interface BridgeEndpointInput {
  id?: string;
  kind: BridgeKind;
  provider: BridgeProvider;
  label?: string;
  trust?: BridgeTrust;
  direction?: BridgeDirection;
  address?: string;
  agent_id?: string;
  scopes?: string[];
  metadata?: Record<string, string>;
}

export interface BridgeMessageInput {
  message_id?: string;
  created_at?: string;
  from: string;
  to: string[];
  subject?: string;
  body: string;
  summary?: string;
  tags?: string[];
  attachments?: BridgeAttachment[];
  metadata?: Record<string, string>;
}

export interface BridgeRouteOptions {
  generated_at?: string;
  allowExternalDelivery?: boolean;
  requireHumanReviewForMail?: boolean;
}

export interface AiCommPacketInput {
  packet_id?: string;
  created_at?: string;
  sender: string;
  recipient: string;
  intent: string;
  status?: AiCommPacket['status'];
  repo?: string;
  branch?: string;
  task_id?: string;
  summary: string;
  proof?: string[];
  next_action: string;
  risk?: AiCommPacket['risk'];
  tests_requested?: string[];
}

const SECRET_PATTERNS: Array<{ code: string; pattern: RegExp; detail: string }> = [
  {
    code: 'private_key_material',
    pattern: /-----BEGIN [A-Z ]*PRIVATE KEY-----/i,
    detail: 'message contains private key material',
  },
  {
    code: 'api_token_literal',
    pattern: /\b(api[_-]?key|token|secret|password)\s*[:=]\s*['"]?[A-Za-z0-9_\-.]{12,}/i,
    detail: 'message appears to contain a literal credential',
  },
  {
    code: 'bearer_token',
    pattern: /\bBearer\s+[A-Za-z0-9_\-.]{12,}/i,
    detail: 'message appears to contain a bearer token',
  },
];

function stableId(prefix: string, value: string): string {
  return `${prefix}-${crypto.createHash('sha256').update(value).digest('hex').slice(0, 16)}`;
}

function normalizeText(value: string | undefined, fallback = ''): string {
  return String(value ?? fallback).trim();
}

function messageHash(message: BridgeMessage): string {
  return crypto
    .createHash('sha256')
    .update(
      JSON.stringify({
        from: message.from,
        to: message.to,
        subject: message.subject,
        body: message.body,
        attachments: message.attachments.map((attachment) => ({
          name: attachment.name,
          bytes: attachment.bytes,
          sha256: attachment.sha256,
        })),
      })
    )
    .digest('hex');
}

function endpointDefaultTrust(kind: BridgeKind): BridgeTrust {
  if (kind === 'ai_agent' || kind === 'file') return 'local_private';
  if (kind === 'mail' || kind === 'human') return 'user_private';
  return 'external';
}

function hasExternalTarget(endpoints: BridgeEndpoint[]): boolean {
  return endpoints.some((endpoint) => endpoint.trust === 'external');
}

function collectFindings(
  message: BridgeMessage,
  endpoints: BridgeEndpoint[]
): BridgeGovernanceFinding[] {
  const text = `${message.subject}\n${message.body}`;
  const findings: BridgeGovernanceFinding[] = [];
  for (const secret of SECRET_PATTERNS) {
    if (secret.pattern.test(text)) {
      findings.push({ code: secret.code, severity: 'block', detail: secret.detail });
    }
  }
  if (message.attachments.length > 0) {
    findings.push({
      code: 'attachments_present',
      severity: 'warn',
      detail: 'attachments require review before bridge delivery',
    });
  }
  if (hasExternalTarget(endpoints)) {
    findings.push({
      code: 'external_target',
      severity: 'warn',
      detail: 'route includes at least one external endpoint',
    });
  }
  if (endpoints.length === 0) {
    findings.push({
      code: 'no_endpoints',
      severity: 'block',
      detail: 'route has no endpoint to deliver to',
    });
  }
  return findings;
}

function decideBridgeRoute(
  message: BridgeMessage,
  endpoints: BridgeEndpoint[],
  options: BridgeRouteOptions
): BridgeDecision {
  const findings = collectFindings(message, endpoints);
  if (findings.some((finding) => finding.severity === 'block')) return 'DENY';
  const hasMailOrHuman = endpoints.some(
    (endpoint) => endpoint.kind === 'mail' || endpoint.kind === 'human'
  );
  if (message.attachments.length > 0 || hasExternalTarget(endpoints)) return 'QUARANTINE';
  if (hasMailOrHuman && options.requireHumanReviewForMail !== false) return 'REVIEW';
  return 'ALLOW';
}

function routeAction(decision: BridgeDecision, index: number): BridgeRouteHop['action'] {
  if (decision === 'DENY') return 'hold';
  if (decision === 'QUARANTINE') return index === 0 ? 'normalize' : 'review';
  if (decision === 'REVIEW') return index === 0 ? 'normalize' : 'review';
  if (index === 0) return 'normalize';
  return 'deliver';
}

export function createBridgeEndpoint(input: BridgeEndpointInput): BridgeEndpoint {
  const label = normalizeText(input.label, `${input.provider}:${input.kind}`);
  const address = normalizeText(input.address);
  const agentId = normalizeText(input.agent_id);
  const id =
    normalizeText(input.id) ||
    stableId('bridge-endpoint', `${input.kind}:${input.provider}:${label}:${address}:${agentId}`);
  return {
    id,
    kind: input.kind,
    provider: input.provider,
    label,
    trust: input.trust || endpointDefaultTrust(input.kind),
    direction: input.direction || 'bidirectional',
    ...(address ? { address } : {}),
    ...(agentId ? { agent_id: agentId } : {}),
    scopes: [...(input.scopes || [])].sort(),
    metadata: { ...(input.metadata || {}) },
  };
}

export function createBridgeMessage(input: BridgeMessageInput): BridgeMessage {
  const createdAt = input.created_at || new Date().toISOString();
  const subject = normalizeText(input.subject);
  const body = String(input.body || '');
  const summary = normalizeText(input.summary, body.slice(0, 240));
  const draft: BridgeMessage = {
    message_id:
      normalizeText(input.message_id) ||
      stableId(
        'bridge-message',
        `${createdAt}:${input.from}:${input.to.join(',')}:${subject}:${body}`
      ),
    created_at: createdAt,
    from: normalizeText(input.from),
    to: input.to.map((target) => normalizeText(target)).filter(Boolean),
    subject,
    body,
    summary,
    tags: [...(input.tags || [])]
      .map((tag) => normalizeText(tag))
      .filter(Boolean)
      .sort(),
    attachments: [...(input.attachments || [])],
    metadata: { ...(input.metadata || {}) },
  };
  if (!draft.from) throw new Error('bridge message missing sender');
  if (draft.to.length === 0) throw new Error('bridge message missing recipient');
  return draft;
}

export function planBridgeRoute(
  intent: string,
  messageInput: BridgeMessageInput | BridgeMessage,
  endpointInputs: Array<BridgeEndpointInput | BridgeEndpoint>,
  options: BridgeRouteOptions = {}
): BridgeRoutePlan {
  const message =
    'message_id' in messageInput && 'created_at' in messageInput
      ? (messageInput as BridgeMessage)
      : createBridgeMessage(messageInput as BridgeMessageInput);
  const endpoints = endpointInputs.map((endpoint) =>
    'id' in endpoint && 'label' in endpoint
      ? (endpoint as BridgeEndpoint)
      : createBridgeEndpoint(endpoint as BridgeEndpointInput)
  );
  const decision = decideBridgeRoute(message, endpoints, options);
  const findings = collectFindings(message, endpoints);
  const externalTargets = endpoints
    .filter((endpoint) => endpoint.trust === 'external')
    .map((endpoint) => endpoint.id);
  const hops: BridgeRouteHop[] = endpoints.map((endpoint, index) => ({
    index,
    from: index === 0 ? message.from : endpoints[index - 1].id,
    to: endpoint.id,
    provider: endpoint.provider,
    action: routeAction(decision, index),
  }));
  const blockedActions =
    decision === 'DENY'
      ? ['deliver', 'remote_forward']
      : decision === 'QUARANTINE'
        ? ['auto_deliver_external']
        : [];
  return {
    schema_version: 'scbe.agent_bus.multi_bridge_plan.v1',
    generated_at: options.generated_at || new Date().toISOString(),
    intent: normalizeText(intent, 'bridge message'),
    message,
    endpoints,
    route: {
      decision,
      hops,
      required_human_gate: decision === 'REVIEW' || decision === 'QUARANTINE',
      next_action:
        decision === 'ALLOW'
          ? 'deliver through approved local bridge'
          : decision === 'REVIEW'
            ? 'route to user review before delivery'
            : decision === 'QUARANTINE'
              ? 'hold in review queue and strip or approve risky fields'
              : 'block delivery and remove restricted material',
    },
    governance: {
      privacy: externalTargets.length > 0 ? 'remote_allowed' : 'local_only',
      findings,
      blocked_actions: blockedActions,
    },
    audit: {
      message_sha256: messageHash(message),
      endpoint_count: endpoints.length,
      external_targets: externalTargets,
    },
  };
}

export function summarizeBridgePlan(plan: BridgeRoutePlan): string {
  const targets = plan.endpoints.map((endpoint) => endpoint.label).join(', ');
  return `${plan.route.decision}: ${plan.message.from} -> ${targets}; next=${plan.route.next_action}`;
}

export function createAiCommPacket(input: AiCommPacketInput): AiCommPacket {
  const createdAt = input.created_at || new Date().toISOString();
  const packetId =
    normalizeText(input.packet_id) ||
    stableId(
      'aid',
      `${createdAt}:${input.sender}:${input.recipient}:${input.intent}:${input.summary}`
    );
  return {
    packet_id: packetId,
    created_at: createdAt,
    sender: normalizeText(input.sender),
    recipient: normalizeText(input.recipient),
    intent: normalizeText(input.intent),
    status: input.status || 'in_progress',
    repo: normalizeText(input.repo, 'SCBE-AETHERMOORE'),
    branch: normalizeText(input.branch, 'unknown'),
    task_id: normalizeText(input.task_id, packetId),
    summary: normalizeText(input.summary),
    proof: [...(input.proof || [])],
    next_action: normalizeText(input.next_action),
    risk: input.risk || 'low',
    gates: {
      governance_packet: true,
      tests_requested: [...(input.tests_requested || [])],
    },
  };
}
