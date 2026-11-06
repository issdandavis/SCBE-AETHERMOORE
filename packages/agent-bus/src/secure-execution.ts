/**
 * Authenticated, replay-resistant execution boundary for Agent Bus.
 *
 * A model may propose a GeoSeal plan. Only trusted host code holding the
 * authority key can issue a one-use capability. Execution is delegated to an
 * isolation provider; this module deliberately has no host-process fallback.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from './process-runner.js';
import type { GeoSealPlan } from './pipeline.js';

export const CAPABILITY_SCHEMA = 'scbe.agent_bus.capability.v1' as const;
export const RECEIPT_SCHEMA = 'scbe.agent_bus.execution_receipt.v1' as const;
export const TOPOLOGY_EVIDENCE_SCHEMA = 'scbe.topological_authorization_evidence.v1' as const;

export const TOPOLOGY_RUNTIME_PROFILES = [
  'TS_PIPELINE14',
  'PY_REFERENCE14',
  'PY_FULL14',
  'PUBLIC_SCAN',
] as const;

/** Trusted deployment identity; request payloads cannot select the evaluator. */
export interface TopologyTrustPolicy {
  profile: (typeof TOPOLOGY_RUNTIME_PROFILES)[number];
  evaluatorSha256: string;
  representationsProfile: string;
}

export type WorkspaceAccess = 'none' | 'read' | 'write';
export type IsolationKind = 'docker' | 'remote-sandbox';

export interface CapabilityLimits {
  timeout_ms: number;
  max_output_bytes: number;
  memory_mb: number;
  cpus: number;
  pids: number;
}

export interface TopologicalAuthorizationEvidence {
  schema_version: typeof TOPOLOGY_EVIDENCE_SCHEMA;
  profile: string;
  decision: 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY' | 'REVIEW' | 'SNAP';
  evaluated_at: string;
  expires_at: string;
  plan_sha256: string;
  evaluator_sha256: string;
  risk_receipt_sha256: string;
  representations: {
    profile: string;
    bit_spine_sha256: string;
    trit_array_sha256: string;
    stista_sha256: string;
    multisign_sha256: string;
  };
}
export interface CapabilityClaims {
  schema_version: typeof CAPABILITY_SCHEMA;
  capability_id: string;
  issuer: string;
  subject: string;
  audience: string;
  key_id: string;
  issued_at: string;
  not_before: string;
  expires_at: string;
  nonce: string;
  max_uses: 1;
  plan_sha256: string;
  command_sha256: string;
  argv_sha256: string;
  workspace: string;
  workspace_sha256: string;
  workspace_access: WorkspaceAccess;
  network: 'none';
  isolation: IsolationKind;
  tool_class: string;
  permission_mode: string;
  limits: CapabilityLimits;
  topological_authorization: TopologicalAuthorizationEvidence;
}

export interface SignedCapability {
  claims: CapabilityClaims;
  signature: {
    algorithm: 'HMAC-SHA256';
    key_id: string;
    value: string;
  };
}

export interface CapabilityGrant {
  subject: string;
  audience: string;
  workspace: string;
  workspaceAccess?: WorkspaceAccess;
  isolation?: IsolationKind;
  ttlMs?: number;
  nowMs?: number;
  limits?: Partial<CapabilityLimits>;
  topology: TopologicalAuthorizationEvidence;
}

export interface CapabilityExpectation {
  subject: string;
  audience: string;
  workspace: string;
  isolation: IsolationKind;
  nowMs?: number;
}

export interface ExecutorRequest {
  argv: string[];
  workspace: string;
  workspaceAccess: WorkspaceAccess;
  network: 'none';
  limits: CapabilityLimits;
  capabilityId: string;
}

export interface ExecutorResult {
  isolation: IsolationKind;
  ok: boolean;
  exitCode: number | null;
  stdout: string;
  stderr: string;
  error?: string;
}

export interface IsolatedExecutor {
  readonly kind: IsolationKind;
  execute(request: ExecutorRequest): Promise<ExecutorResult>;
}

export interface ExecutionReceiptRecord {
  schema_version: typeof RECEIPT_SCHEMA;
  receipt_id: string;
  sequence: number;
  event: 'AUTHORIZED' | 'RESERVED' | 'RESULT';
  recorded_at: string;
  capability_id: string;
  issuer: string;
  subject: string;
  audience: string;
  plan_sha256: string;
  command_sha256: string;
  nonce_sha256: string;
  isolation: IsolationKind;
  previous_receipt_sha256: string | null;
  details: Record<string, unknown>;
}

export interface SignedExecutionReceipt {
  record: ExecutionReceiptRecord;
  signature: {
    algorithm: 'HMAC-SHA256';
    key_id: string;
    value: string;
  };
}

export interface ReceiptTransaction {
  directory: string;
  authorization: SignedExecutionReceipt;
  reservation: SignedExecutionReceipt;
  previousSha256: string;
}

export interface SecureExecutionContext {
  authority: CapabilityAuthority;
  replayStore: FileReplayStore;
  receiptJournal: FileReceiptJournal;
  executor: IsolatedExecutor;
  expectation: Omit<CapabilityExpectation, 'isolation'>;
}

export interface SecureExecutionResult {
  capability: SignedCapability;
  executor: ExecutorResult;
  authorization_receipt: string;
  reservation_receipt: string;
  result_receipt: string;
}

/** Trusted host configuration for the secure branch of runPipeline. */
export interface SecurePipelineOptions {
  context: SecureExecutionContext;
  grant: {
    /** Precomputed evidence for an already compiled plan, or a trusted evaluator. */
    topology:
      | TopologicalAuthorizationEvidence
      | ((
          plan: GeoSealPlan
        ) => TopologicalAuthorizationEvidence | Promise<TopologicalAuthorizationEvidence>);
    workspaceAccess?: WorkspaceAccess;
    ttlMs?: number;
    nowMs?: number;
    limits?: Partial<CapabilityLimits>;
  };
}

const DEFAULT_LIMITS: CapabilityLimits = {
  timeout_ms: 30_000,
  max_output_bytes: 8 * 1024 * 1024,
  memory_mb: 512,
  cpus: 1,
  pids: 128,
};

function requirePlainObject(value: object): Record<string, unknown> {
  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null) {
    throw new TypeError('canonical JSON accepts only plain objects');
  }
  return value as Record<string, unknown>;
}

/** RFC-8785-style subset sufficient for SCBE's JSON contracts. */
export function canonicalJson(value: unknown): string {
  if (value === null) return 'null';
  if (typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new TypeError('non-finite number in signed payload');
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (typeof value === 'object') {
    const object = requirePlainObject(value);
    const entries = Object.keys(object)
      .filter((key) => object[key] !== undefined)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(object[key])}`);
    return `{${entries.join(',')}}`;
  }
  throw new TypeError(`unsupported signed payload type: ${typeof value}`);
}

export function sha256Hex(value: string | Buffer): string {
  return crypto.createHash('sha256').update(value).digest('hex');
}

export function digestJson(value: unknown): string {
  return sha256Hex(canonicalJson(value));
}

/** Parse the fixed GeoSeal command template without invoking a shell. */
export function parseCapabilityArgv(template: string): string[] {
  if (typeof template !== 'string' || /[\r\n\0]/.test(template)) {
    throw new Error('command template contains a forbidden control character');
  }
  const argv: string[] = [];
  let current = '';
  let inSingle = false;
  let inDouble = false;
  for (const character of template) {
    if (character === "'" && !inDouble) {
      inSingle = !inSingle;
      continue;
    }
    if (character === '"' && !inSingle) {
      inDouble = !inDouble;
      continue;
    }
    if (/\s/.test(character) && !inSingle && !inDouble) {
      if (current) {
        argv.push(current);
        current = '';
      }
      continue;
    }
    current += character;
  }
  if (inSingle || inDouble) throw new Error('unterminated quote in command template');
  if (current) argv.push(current);
  return argv;
}

function requireSha256(value: string, label: string): void {
  if (typeof value !== 'string' || !/^[a-f0-9]{64}$/i.test(value)) {
    throw new Error(label + ' must be a SHA-256 digest');
  }
}

function validateTopologicalEvidence(
  evidence: TopologicalAuthorizationEvidence,
  plan: GeoSealPlan,
  nowMs: number,
  maxLifetimeMs: number,
  trust: Readonly<TopologyTrustPolicy>
): void {
  if (!evidence || evidence.schema_version !== TOPOLOGY_EVIDENCE_SCHEMA) {
    throw new Error('missing or unsupported topological authorization evidence');
  }
  requireText(evidence.profile, 'topology profile');
  requireText(evidence.representations?.profile, 'representation profile');
  if (
    evidence.profile !== trust.profile ||
    evidence.evaluator_sha256 !== trust.evaluatorSha256 ||
    evidence.representations.profile !== trust.representationsProfile
  ) {
    throw new Error('topological evaluator or representation profile differs from trusted policy');
  }
  if (evidence.decision !== 'ALLOW') {
    throw new Error('topological authorization decision is ' + evidence.decision);
  }
  if (evidence.plan_sha256 !== digestJson(plan)) {
    throw new Error('topological authorization does not bind the supplied plan');
  }
  requireSha256(evidence.evaluator_sha256, 'topology evaluator');
  requireSha256(evidence.risk_receipt_sha256, 'topology risk receipt');
  for (const name of [
    'bit_spine_sha256',
    'trit_array_sha256',
    'stista_sha256',
    'multisign_sha256',
  ] as const) {
    requireSha256(evidence.representations[name], 'representation ' + name);
  }
  for (const [name, digest] of Object.entries(evidence.representations || {})) {
    if (name !== 'profile') requireSha256(String(digest), 'representation ' + name);
  }
  const evaluatedMs = Date.parse(evidence.evaluated_at);
  const expiresMs = Date.parse(evidence.expires_at);
  if (!Number.isFinite(evaluatedMs) || !Number.isFinite(expiresMs)) {
    throw new Error('invalid topological authorization time');
  }
  if (
    evaluatedMs > nowMs ||
    expiresMs <= nowMs ||
    expiresMs <= evaluatedMs ||
    expiresMs - evaluatedMs > maxLifetimeMs
  ) {
    throw new Error('topological authorization is stale or outside its lifetime policy');
  }
}
function hmacHex(key: Buffer, domain: string, value: unknown): string {
  return crypto
    .createHmac('sha256', key)
    .update(domain, 'utf8')
    .update('\0', 'utf8')
    .update(canonicalJson(value), 'utf8')
    .digest('hex');
}

function timingSafeHexEqual(left: string, right: string): boolean {
  if (!/^[a-f0-9]{64}$/i.test(left) || !/^[a-f0-9]{64}$/i.test(right)) return false;
  return crypto.timingSafeEqual(Buffer.from(left, 'hex'), Buffer.from(right, 'hex'));
}

function requireText(value: string, label: string): void {
  if (typeof value !== 'string' || value.trim().length === 0 || value.length > 512) {
    throw new Error(`${label} must be non-empty and bounded`);
  }
}

function validateLimits(limits: CapabilityLimits): void {
  const integerKeys: Array<keyof CapabilityLimits> = [
    'timeout_ms',
    'max_output_bytes',
    'memory_mb',
    'pids',
  ];
  for (const key of integerKeys) {
    if (!Number.isInteger(limits[key]) || limits[key] <= 0) {
      throw new Error(`invalid capability limit ${key}`);
    }
  }
  if (!Number.isFinite(limits.cpus) || limits.cpus <= 0 || limits.cpus > 8) {
    throw new Error('invalid capability limit cpus');
  }
  if (limits.timeout_ms > 15 * 60_000) throw new Error('capability timeout exceeds 15 minutes');
  if (limits.max_output_bytes > 64 * 1024 * 1024) throw new Error('output allowance too large');
  if (limits.memory_mb > 16 * 1024) throw new Error('memory allowance too large');
  if (limits.pids > 1024) throw new Error('pid allowance too large');
}

function commandDigest(plan: GeoSealPlan): string {
  return sha256Hex(plan.command.template || '');
}

function validatePlanForCapability(plan: GeoSealPlan, argv: string[]): void {
  if (plan.schema_version !== 'scbe_command_plan_v1') throw new Error('unsupported plan schema');
  if (
    plan.policy.decision !== 'ALLOW' ||
    plan.policy.ok !== true ||
    plan.command.runnable !== true
  ) {
    throw new Error('capabilities may only be issued for runnable ALLOW plans');
  }
  if (!Array.isArray(argv) || argv.length === 0 || argv.some((part) => typeof part !== 'string')) {
    throw new Error('capability argv must be a non-empty string array');
  }
  if (argv.some((part) => part.includes('\0'))) throw new Error('capability argv contains NUL');
  if (canonicalJson(parseCapabilityArgv(plan.command.template)) !== canonicalJson(argv)) {
    throw new Error('capability argv does not match the command template');
  }
  if (plan.hashes.intent_sha256 !== sha256Hex(plan.intent.text)) {
    throw new Error('intent hash does not match plan');
  }
  if (plan.hashes.tool_sha256 && plan.hashes.tool_sha256 !== sha256Hex(plan.tool.class)) {
    throw new Error('tool hash does not match plan');
  }
  if (!plan.hashes.command_sha256 || plan.hashes.command_sha256 !== commandDigest(plan)) {
    throw new Error('command hash does not match plan');
  }
}

export class CapabilityAuthority {
  readonly issuer: string;
  readonly keyId: string;
  readonly maxTtlMs: number;
  private readonly key: Buffer;
  private readonly topologyPolicy: Readonly<TopologyTrustPolicy>;

  constructor(options: {
    issuer: string;
    keyId: string;
    key: Buffer;
    maxTtlMs?: number;
    topologyPolicy: TopologyTrustPolicy;
  }) {
    requireText(options.issuer, 'issuer');
    requireText(options.keyId, 'key id');
    if (!Buffer.isBuffer(options.key) || options.key.length < 32) {
      throw new Error('capability authority requires an explicit key of at least 32 bytes');
    }
    if (
      !options.topologyPolicy ||
      !TOPOLOGY_RUNTIME_PROFILES.includes(options.topologyPolicy.profile)
    ) {
      throw new Error('capability authority requires an explicit supported topology policy');
    }
    requireSha256(options.topologyPolicy.evaluatorSha256, 'trusted evaluator');
    requireText(options.topologyPolicy.representationsProfile, 'trusted representation profile');
    this.topologyPolicy = Object.freeze({ ...options.topologyPolicy });
    this.issuer = options.issuer;
    this.keyId = options.keyId;
    this.key = Buffer.from(options.key);
    this.maxTtlMs = options.maxTtlMs ?? 5 * 60_000;
    if (!Number.isInteger(this.maxTtlMs) || this.maxTtlMs < 1 || this.maxTtlMs > 60 * 60_000) {
      throw new Error('invalid authority maximum TTL');
    }
  }

  issue(plan: GeoSealPlan, argv: string[], grant: CapabilityGrant): SignedCapability {
    validatePlanForCapability(plan, argv);
    requireText(grant.subject, 'subject');
    requireText(grant.audience, 'audience');
    const nowMs = grant.nowMs ?? Date.now();
    if (!Number.isInteger(nowMs)) throw new Error('invalid capability issue time');
    validateTopologicalEvidence(grant.topology, plan, nowMs, this.maxTtlMs, this.topologyPolicy);
    const topologyExpiresMs = Date.parse(grant.topology.expires_at);
    const ttlMs = grant.ttlMs ?? Math.min(60_000, this.maxTtlMs, topologyExpiresMs - nowMs);
    if (!Number.isInteger(ttlMs) || ttlMs < 1 || ttlMs > this.maxTtlMs) {
      throw new Error('invalid capability lifetime');
    }
    if (nowMs + ttlMs > topologyExpiresMs) {
      throw new Error('capability would outlive its topological authorization');
    }
    const workspace = path.resolve(grant.workspace);
    const workspaceAccess = grant.workspaceAccess ?? 'read';
    const isolation = grant.isolation ?? 'docker';
    if (!(['none', 'read', 'write'] as const).includes(workspaceAccess)) {
      throw new Error('invalid workspace access');
    }
    if (!(['docker', 'remote-sandbox'] as const).includes(isolation)) {
      throw new Error('invalid isolation provider');
    }
    const limits: CapabilityLimits = { ...DEFAULT_LIMITS, ...(grant.limits || {}) };
    validateLimits(limits);
    const nonce = crypto.randomBytes(32).toString('hex');
    const partial = {
      issuer: this.issuer,
      subject: grant.subject,
      audience: grant.audience,
      nonce,
      plan_sha256: digestJson(plan),
    };
    const capabilityId = digestJson(partial);
    const claims: CapabilityClaims = {
      schema_version: CAPABILITY_SCHEMA,
      capability_id: capabilityId,
      issuer: this.issuer,
      subject: grant.subject,
      audience: grant.audience,
      key_id: this.keyId,
      issued_at: new Date(nowMs).toISOString(),
      not_before: new Date(nowMs).toISOString(),
      expires_at: new Date(nowMs + ttlMs).toISOString(),
      nonce,
      max_uses: 1,
      plan_sha256: digestJson(plan),
      command_sha256: commandDigest(plan),
      argv_sha256: digestJson(argv),
      workspace,
      workspace_sha256: sha256Hex(workspace),
      workspace_access: workspaceAccess,
      network: 'none',
      isolation,
      tool_class: plan.tool.class,
      permission_mode: plan.intent.permission_mode,
      limits,
      topological_authorization: structuredClone(grant.topology),
    };
    return {
      claims,
      signature: {
        algorithm: 'HMAC-SHA256',
        key_id: this.keyId,
        value: hmacHex(this.key, 'scbe-capability-v1', claims),
      },
    };
  }

  verify(
    capability: SignedCapability,
    plan: GeoSealPlan,
    argv: string[],
    expected: CapabilityExpectation
  ): CapabilityClaims {
    const { claims, signature } = capability;
    if (!claims || claims.schema_version !== CAPABILITY_SCHEMA)
      throw new Error('unsupported capability');
    if (
      signature?.algorithm !== 'HMAC-SHA256' ||
      signature.key_id !== this.keyId ||
      claims.key_id !== this.keyId ||
      claims.issuer !== this.issuer
    ) {
      throw new Error('capability authority mismatch');
    }
    const expectedMac = hmacHex(this.key, 'scbe-capability-v1', claims);
    if (!timingSafeHexEqual(signature.value, expectedMac))
      throw new Error('invalid capability signature');

    validatePlanForCapability(plan, argv);
    requireText(claims.subject, 'subject');
    requireText(claims.audience, 'audience');
    if (claims.subject !== expected.subject || claims.audience !== expected.audience) {
      throw new Error('capability subject or audience mismatch');
    }
    const workspace = path.resolve(expected.workspace);
    if (claims.workspace !== workspace || claims.workspace_sha256 !== sha256Hex(workspace)) {
      throw new Error('capability workspace mismatch');
    }
    if (claims.isolation !== expected.isolation || claims.network !== 'none') {
      throw new Error('capability isolation mismatch');
    }
    if (claims.max_uses !== 1 || !/^[a-f0-9]{64}$/.test(claims.nonce)) {
      throw new Error('capability is not one-use');
    }
    validateLimits(claims.limits);
    if (
      claims.plan_sha256 !== digestJson(plan) ||
      claims.command_sha256 !== commandDigest(plan) ||
      claims.argv_sha256 !== digestJson(argv) ||
      claims.tool_class !== plan.tool.class ||
      claims.permission_mode !== plan.intent.permission_mode
    ) {
      throw new Error('capability does not bind the supplied plan');
    }
    const nowMs = expected.nowMs ?? Date.now();
    if (!Number.isInteger(nowMs)) throw new Error('invalid capability verification time');
    validateTopologicalEvidence(
      claims.topological_authorization,
      plan,
      nowMs,
      this.maxTtlMs,
      this.topologyPolicy
    );
    const issuedMs = Date.parse(claims.issued_at);
    const notBeforeMs = Date.parse(claims.not_before);
    const expiresMs = Date.parse(claims.expires_at);
    if (![issuedMs, notBeforeMs, expiresMs].every(Number.isFinite))
      throw new Error('invalid capability time');
    if (expiresMs - issuedMs > this.maxTtlMs || expiresMs <= issuedMs) {
      throw new Error('capability lifetime exceeds authority policy');
    }
    if (
      issuedMs > nowMs ||
      notBeforeMs < issuedMs ||
      notBeforeMs >= expiresMs ||
      expiresMs > Date.parse(claims.topological_authorization.expires_at) ||
      nowMs < notBeforeMs ||
      nowMs >= expiresMs
    )
      throw new Error('capability is not currently valid');
    return claims;
  }

  receiptKey(): Buffer {
    return Buffer.from(this.key);
  }
}

export class FileReplayStore {
  readonly root: string;

  constructor(root: string) {
    this.root = path.resolve(root);
  }

  consume(claims: CapabilityClaims): string {
    if (!/^[a-f0-9]{64}$/.test(claims.nonce)) throw new Error('invalid replay nonce');
    fs.mkdirSync(this.root, { recursive: true });
    const file = path.join(this.root, `${sha256Hex(claims.nonce)}.used`);
    const body = `${canonicalJson({ capability_id: claims.capability_id, consumed_at: new Date().toISOString() })}\n`;
    try {
      fs.writeFileSync(file, body, { encoding: 'utf8', flag: 'wx', mode: 0o600 });
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'EEXIST')
        throw new Error('capability replay detected');
      throw error;
    }
    return file;
  }
}

export class FileReceiptJournal {
  readonly root: string;
  readonly keyId: string;
  private readonly key: Buffer;

  constructor(options: { root: string; keyId: string; key: Buffer }) {
    requireText(options.keyId, 'receipt key id');
    if (!Buffer.isBuffer(options.key) || options.key.length < 32) {
      throw new Error('receipt journal requires an explicit key of at least 32 bytes');
    }
    this.root = path.resolve(options.root);
    this.keyId = options.keyId;
    this.key = Buffer.from(options.key);
  }

  private sign(record: ExecutionReceiptRecord): SignedExecutionReceipt {
    return {
      record,
      signature: {
        algorithm: 'HMAC-SHA256',
        key_id: this.keyId,
        value: hmacHex(this.key, 'scbe-execution-receipt-v1', record),
      },
    };
  }

  private writeExclusive(file: string, receipt: SignedExecutionReceipt): void {
    fs.writeFileSync(file, `${canonicalJson(receipt)}\n`, {
      encoding: 'utf8',
      flag: 'wx',
      mode: 0o600,
    });
  }

  begin(claims: CapabilityClaims): ReceiptTransaction {
    fs.mkdirSync(this.root, { recursive: true });
    const directory = path.join(this.root, claims.capability_id);
    fs.mkdirSync(directory);
    const common = {
      schema_version: RECEIPT_SCHEMA,
      capability_id: claims.capability_id,
      issuer: claims.issuer,
      subject: claims.subject,
      audience: claims.audience,
      plan_sha256: claims.plan_sha256,
      command_sha256: claims.command_sha256,
      nonce_sha256: sha256Hex(claims.nonce),
      isolation: claims.isolation,
    } as const;
    const authorization = this.sign({
      ...common,
      receipt_id: `${claims.capability_id}:1`,
      sequence: 1,
      event: 'AUTHORIZED',
      recorded_at: new Date().toISOString(),
      previous_receipt_sha256: null,
      details: {
        expires_at: claims.expires_at,
        workspace_sha256: claims.workspace_sha256,
        workspace_access: claims.workspace_access,
        network: claims.network,
        limits: claims.limits,
        topology_evidence_sha256: digestJson(claims.topological_authorization),
        topology_profile: claims.topological_authorization.profile,
        topology_decision: claims.topological_authorization.decision,
        representation_profile: claims.topological_authorization.representations.profile,
      },
    });
    this.writeExclusive(path.join(directory, 'authorization.json'), authorization);
    const authorizationSha = digestJson(authorization);
    const reservation = this.sign({
      ...common,
      receipt_id: `${claims.capability_id}:2`,
      sequence: 2,
      event: 'RESERVED',
      recorded_at: new Date().toISOString(),
      previous_receipt_sha256: authorizationSha,
      details: { result_path: 'result.json' },
    });
    this.writeExclusive(path.join(directory, 'reservation.json'), reservation);
    return {
      directory,
      authorization,
      reservation,
      previousSha256: digestJson(reservation),
    };
  }

  finish(
    claims: CapabilityClaims,
    transaction: ReceiptTransaction,
    result: ExecutorResult
  ): SignedExecutionReceipt {
    const receipt = this.sign({
      schema_version: RECEIPT_SCHEMA,
      receipt_id: `${claims.capability_id}:3`,
      sequence: 3,
      event: 'RESULT',
      recorded_at: new Date().toISOString(),
      capability_id: claims.capability_id,
      issuer: claims.issuer,
      subject: claims.subject,
      audience: claims.audience,
      plan_sha256: claims.plan_sha256,
      command_sha256: claims.command_sha256,
      nonce_sha256: sha256Hex(claims.nonce),
      isolation: claims.isolation,
      previous_receipt_sha256: transaction.previousSha256,
      details: {
        ok: result.ok,
        exit_code: result.exitCode,
        stdout_sha256: sha256Hex(result.stdout),
        stderr_sha256: sha256Hex(result.stderr),
        stdout_bytes: Buffer.byteLength(result.stdout),
        stderr_bytes: Buffer.byteLength(result.stderr),
        error: result.error || null,
      },
    });
    this.writeExclusive(path.join(transaction.directory, 'result.json'), receipt);
    return receipt;
  }

  verify(receipt: SignedExecutionReceipt): boolean {
    if (
      receipt?.record?.schema_version !== RECEIPT_SCHEMA ||
      receipt?.signature?.algorithm !== 'HMAC-SHA256' ||
      receipt.signature.key_id !== this.keyId
    ) {
      return false;
    }
    return timingSafeHexEqual(
      receipt.signature.value,
      hmacHex(this.key, 'scbe-execution-receipt-v1', receipt.record)
    );
  }
}

function isWithin(parent: string, candidate: string): boolean {
  const relative = path.relative(parent, candidate);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function verifyControlStateOutsideWorkspace(
  context: SecureExecutionContext,
  workspace: string
): void {
  const realWorkspace = fs.realpathSync.native(workspace);
  for (const [label, root] of [
    ['replay store', context.replayStore.root],
    ['receipt journal', context.receiptJournal.root],
  ] as const) {
    fs.mkdirSync(root, { recursive: true });
    const realRoot = fs.realpathSync.native(root);
    if (isWithin(realWorkspace, realRoot)) {
      throw new Error(`${label} must be outside the granted workspace`);
    }
  }
}

export interface DockerSandboxOptions {
  image: string;
  dockerBin?: string;
  containerWorkspace?: string;
}

export class DockerSandboxExecutor implements IsolatedExecutor {
  readonly kind = 'docker' as const;
  readonly image: string;
  readonly dockerBin: string;
  readonly containerWorkspace: string;

  constructor(options: DockerSandboxOptions) {
    if (!/@sha256:[a-f0-9]{64}$/i.test(options.image)) {
      throw new Error('Docker sandbox image must be pinned by sha256 digest');
    }
    this.image = options.image;
    this.dockerBin = options.dockerBin || 'docker';
    this.containerWorkspace = options.containerWorkspace || '/workspace';
    if (!this.containerWorkspace.startsWith('/'))
      throw new Error('container workspace must be absolute');
  }

  buildArgs(request: ExecutorRequest): string[] {
    if (request.network !== 'none') throw new Error('Docker executor supports network=none only');
    validateLimits(request.limits);
    const workspace = path.resolve(request.workspace);
    if (workspace.includes(',') || /[\r\n\0]/.test(workspace)) {
      throw new Error('workspace path cannot be represented safely as a Docker mount');
    }
    const argv = request.argv.map((value) => {
      if (value.includes('\0')) throw new Error('NUL in executor argv');
      if (!path.isAbsolute(value)) return value;
      const resolved = path.resolve(value);
      if (!isWithin(workspace, resolved))
        throw new Error('host absolute argument escapes workspace');
      if (request.workspaceAccess === 'none')
        throw new Error('host path requires workspace capability');
      const relative = path.relative(workspace, resolved).split(path.sep).join('/');
      return relative ? `${this.containerWorkspace}/${relative}` : this.containerWorkspace;
    });
    const args = [
      'run',
      '--rm',
      '--pull',
      'never',
      '--init',
      '--network',
      'none',
      '--cap-drop',
      'ALL',
      '--security-opt',
      'no-new-privileges',
      '--read-only',
      '--pids-limit',
      String(request.limits.pids),
      '--memory',
      `${request.limits.memory_mb}m`,
      '--cpus',
      String(request.limits.cpus),
      '--user',
      '65532:65532',
      '--tmpfs',
      '/tmp:rw,noexec,nosuid,size=64m',
    ];
    if (request.workspaceAccess !== 'none') {
      const readonly = request.workspaceAccess === 'read' ? ',readonly' : '';
      args.push(
        '--mount',
        `type=bind,src=${workspace},dst=${this.containerWorkspace}${readonly}`,
        '--workdir',
        this.containerWorkspace
      );
    } else {
      args.push('--workdir', '/tmp');
    }
    args.push(this.image, ...argv);
    return args;
  }

  async execute(request: ExecutorRequest): Promise<ExecutorResult> {
    const args = this.buildArgs(request);
    const run = spawnSync(this.dockerBin, args, {
      encoding: 'utf8',
      timeout: request.limits.timeout_ms,
      maxBuffer: request.limits.max_output_bytes,
      windowsHide: true,
      shell: false,
    });
    const error = run.error ? String(run.error.message || run.error) : undefined;
    return {
      isolation: this.kind,
      ok: run.status === 0 && !error,
      exitCode: run.status,
      stdout: String(run.stdout || ''),
      stderr: String(run.stderr || ''),
      ...(error ? { error } : {}),
    };
  }
}

export async function executeAuthorizedPlan(
  plan: GeoSealPlan,
  argv: string[],
  capability: SignedCapability,
  context: SecureExecutionContext
): Promise<SecureExecutionResult> {
  const claims = context.authority.verify(capability, plan, argv, {
    ...context.expectation,
    isolation: context.executor.kind,
  });
  verifyControlStateOutsideWorkspace(context, claims.workspace);
  context.replayStore.consume(claims);
  const transaction = context.receiptJournal.begin(claims);
  let result: ExecutorResult;
  try {
    result = await context.executor.execute({
      argv: [...argv],
      workspace: claims.workspace,
      workspaceAccess: claims.workspace_access,
      network: claims.network,
      limits: { ...claims.limits },
      capabilityId: claims.capability_id,
    });
  } catch (error) {
    result = {
      isolation: context.executor.kind,
      ok: false,
      exitCode: null,
      stdout: '',
      stderr: '',
      error: error instanceof Error ? error.message : String(error),
    };
  }
  if (result.isolation !== claims.isolation) {
    result = {
      isolation: claims.isolation,
      ok: false,
      exitCode: null,
      stdout: '',
      stderr: '',
      error: 'executor returned the wrong isolation identity',
    };
  }
  context.receiptJournal.finish(claims, transaction, result);
  return {
    capability,
    executor: result,
    authorization_receipt: path.join(transaction.directory, 'authorization.json'),
    reservation_receipt: path.join(transaction.directory, 'reservation.json'),
    result_receipt: path.join(transaction.directory, 'result.json'),
  };
}

export async function issueAndExecutePlan(
  plan: GeoSealPlan,
  argv: string[],
  grant: CapabilityGrant,
  context: SecureExecutionContext
): Promise<SecureExecutionResult> {
  const capability = context.authority.issue(plan, argv, {
    ...grant,
    subject: context.expectation.subject,
    audience: context.expectation.audience,
    workspace: context.expectation.workspace,
    isolation: context.executor.kind,
  });
  return executeAuthorizedPlan(plan, argv, capability, context);
}
/**
 * Parse a compiled GeoSeal command and execute it through a one-use capability.
 * Trusted subject, audience, workspace, and isolation values come only from
 * the host context and cannot be replaced by model-controlled grant data.
 */
export async function executeCompiledPlanSecure(
  plan: GeoSealPlan,
  options: SecurePipelineOptions
): Promise<SecureExecutionResult> {
  // A trusted evaluator receives a separate snapshot; neither it nor a caller
  // mutating the original object during an await can swap the executed command.
  plan = structuredClone(plan);
  const grant = { ...options.grant };
  const topology =
    typeof grant.topology === 'function'
      ? await grant.topology(structuredClone(plan))
      : structuredClone(grant.topology);
  const argv = parseCapabilityArgv(plan.command.template);
  return issueAndExecutePlan(
    plan,
    argv,
    {
      ...grant,
      topology,
      subject: options.context.expectation.subject,
      audience: options.context.expectation.audience,
      workspace: options.context.expectation.workspace,
      isolation: options.context.executor.kind,
    },
    options.context
  );
}
