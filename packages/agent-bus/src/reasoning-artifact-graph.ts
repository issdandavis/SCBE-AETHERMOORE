/**
 * Verifiable public reasoning artifacts for parallel agent work.
 *
 * This ledger records summaries, state transitions, syntax surfaces, provenance,
 * and measurements. It deliberately has no field for private model chain-of-thought.
 * Sacred Tongue codecs are injected so this package stays independent of any one
 * tokenizer profile while still enforcing byte-exact round trips.
 */

import crypto from 'node:crypto';

export const REASONING_TONGUES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;
export type ReasoningTongue = (typeof REASONING_TONGUES)[number];
export type ArtifactPolicy = 'allow' | 'deny' | 'quarantine' | 'adversarial';
export type ReasoningEventKind = 'append' | 'fork' | 'merge' | 'backtrack';

export interface BijectiveViewCodec {
  encode(tongue: ReasoningTongue, canonical: Uint8Array): readonly string[];
  decode(tongue: ReasoningTongue, tokens: readonly string[]): Uint8Array;
}

export interface SyntaxDelta {
  parent_id: string | null;
  previous_sha256: string | null;
  current_sha256: string;
  common_prefix_tokens: number;
  common_suffix_tokens: number;
  removed_tokens: string[];
  added_tokens: string[];
  delta_sha256: string;
}

export interface TypedEquivalenceReceipt {
  schema_version: 'scbe.reasoning_typed_equivalence.v1';
  verifier_id: string;
  verifier_sha256: string;
  parent_canonical_sha256: string[];
  output_canonical_sha256: string;
  evidence_sha256: string;
  passed: true;
}

export type EquivalenceVerifier = (
  receipt: TypedEquivalenceReceipt,
  parents: readonly ReasoningArtifactNode[],
  outputCanonicalSha256: string
) => boolean;

export type MergeAuthority =
  | { kind: 'exact-canonical' }
  | {
      kind: 'typed-equivalence';
      receipt: TypedEquivalenceReceipt;
      receipt_sha256: string;
    };

export interface ReasoningArtifactNode {
  schema_version: 'scbe.reasoning_artifact.v1';
  id: string;
  parent_ids: string[];
  tongue: ReasoningTongue;
  public_summary: string;
  state_transition: string;
  canonical_bytes_sha256: string;
  view_tokens: string[];
  view_sha256: string;
  syntax_tokens: string[];
  syntax_deltas: SyntaxDelta[];
  feature_values: number[];
  policy: ArtifactPolicy;
  evidence_hashes: string[];
  provenance_hashes: string[];
  lineage_root_sha256: string;
  merge_authority: MergeAuthority | null;
  created_sequence: number;
  node_sha256: string;
}

export interface ReasoningGraphEvent {
  schema_version: 'scbe.reasoning_graph_event.v1';
  sequence: number;
  kind: ReasoningEventKind;
  node_id: string | null;
  parent_ids: string[];
  target_node_id: string | null;
  reason_sha256: string | null;
  head_ids: string[];
  previous_event_sha256: string | null;
  event_sha256: string;
}

export interface ReasoningArtifactGraph {
  schema_version: 'scbe.reasoning_artifact_graph.v1';
  graph_id: string;
  feature_names: string[];
  nodes: Record<string, ReasoningArtifactNode>;
  events: ReasoningGraphEvent[];
  head_ids: string[];
}

export interface ReasoningArtifactInput {
  id: string;
  parent_ids?: readonly string[];
  tongue: ReasoningTongue;
  canonical_bytes: Uint8Array;
  public_summary: string;
  state_transition: string;
  syntax_tokens: readonly string[];
  feature_values: readonly number[];
  policy: ArtifactPolicy;
  evidence_hashes: readonly string[];
  provenance_hashes: readonly string[];
}

export interface ForkArtifactInput extends Omit<ReasoningArtifactInput, 'parent_ids'> {
  parent_id: string;
}

export interface MergeArtifactInput extends ReasoningArtifactInput {
  parent_ids: readonly string[];
}

export interface MergeOptions {
  equivalence_receipt?: TypedEquivalenceReceipt;
  verify_equivalence?: EquivalenceVerifier;
}

export interface GraphVerificationOptions {
  codec?: BijectiveViewCodec;
  verify_equivalence?: EquivalenceVerifier;
  require_equivalence_reverification?: boolean;
}

export interface GraphVerificationResult {
  ok: boolean;
  errors: string[];
  graph_sha256: string;
}

export interface TubalPairwiseDistance {
  left_head_id: string;
  right_head_id: string;
  distance: number;
}

export interface TubalBranchTelemetry {
  schema_version: 'scbe.reasoning_tubal_telemetry.v1';
  graph_sha256: string;
  head_ids: string[];
  tensor_shape: [branches: number, features: number, timeSteps: number];
  feature_names: string[];
  branch_depths: Record<string, number>;
  pairwise_head_distances: TubalPairwiseDistance[];
  mean_head_separation: number;
  centroid_residual: number;
  convergence_degree: number;
  spectral_mode_energy: number[];
  non_dc_energy: number;
  high_frequency_fraction: number;
  phase_coherence: number;
  head_policy_counts: Record<ArtifactPolicy, number>;
  unresolved_head_ids: string[];
  backtrack_count: number;
  authority: 'telemetry-only-not-merge-authority';
}

const HASH_RE = /^[a-f0-9]{64}$/;
const ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const POLICIES: ArtifactPolicy[] = ['allow', 'deny', 'quarantine', 'adversarial'];
const MAX_CANONICAL_BYTES = 64 * 1024;
const MAX_VIEW_TOKENS = 256 * 1024;
const MAX_VIEW_CHARACTERS = 1024 * 1024;
const MAX_SYNTAX_TOKENS = 4096;
const MAX_FEATURES = 256;
const MAX_GRAPH_NODES = 4096;
const MAX_GRAPH_EVENTS = 8192;
const MAX_GRAPH_HEADS = 256;
const MAX_GRAPH_VIEW_CHARACTERS = 64 * 1024 * 1024;
const MAX_TUBAL_DFT_OPERATIONS = 20_000_000;

function canonicalJson(value: unknown): string {
  if (value === null) return 'null';
  if (typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error('non-finite number cannot be hashed');
    return Object.is(value, -0) ? '0' : JSON.stringify(value);
  }
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
      .filter(([, item]) => item !== undefined)
      .sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0));
    return `{${entries
      .map(([key, item]) => `${JSON.stringify(key)}:${canonicalJson(item)}`)
      .join(',')}}`;
  }
  throw new Error(`unsupported hash value: ${typeof value}`);
}

export function hashReasoningValue(value: unknown): string {
  return crypto.createHash('sha256').update(canonicalJson(value), 'utf8').digest('hex');
}

export function hashReasoningBytes(value: Uint8Array): string {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function requireText(name: string, value: unknown, maximum = 8192): asserts value is string {
  if (typeof value !== 'string' || value.trim().length === 0 || value.length > maximum) {
    throw new Error(`${name} must be non-empty and at most ${maximum} characters`);
  }
}

function requireId(name: string, value: string): void {
  if (!ID_RE.test(value)) throw new Error(`${name} is not a valid stable identifier`);
}

function requireHash(name: string, value: string): void {
  if (!HASH_RE.test(value)) throw new Error(`${name} must be a lowercase SHA-256 digest`);
}

function normalizeHashes(name: string, values: readonly string[]): string[] {
  if (!Array.isArray(values) || values.length === 0) {
    throw new Error(`${name} must contain at least one receipt hash`);
  }
  for (const value of values) requireHash(name, value);
  return [...new Set(values)].sort();
}

function normalizeSyntax(tokens: readonly string[]): string[] {
  if (!Array.isArray(tokens) || tokens.length > MAX_SYNTAX_TOKENS) {
    throw new Error(`syntax_tokens must contain at most ${MAX_SYNTAX_TOKENS} entries`);
  }
  return tokens.map((token) => {
    if (typeof token !== 'string' || token.length === 0 || token.length > 256) {
      throw new Error('syntax token must be a non-empty string of at most 256 characters');
    }
    return token;
  });
}

function normalizeFeatures(values: readonly number[], expected: number): number[] {
  if (!Array.isArray(values) || values.length !== expected || expected > MAX_FEATURES) {
    throw new Error(`feature_values must match the ${expected}-feature graph schema`);
  }
  if (values.some((value) => typeof value !== 'number' || !Number.isFinite(value))) {
    throw new Error('feature_values must be finite numbers');
  }
  return [...values];
}

function arraysEqual<T>(left: readonly T[], right: readonly T[]): boolean {
  return left.length === right.length && left.every((item, index) => item === right[index]);
}

function bytesEqual(left: Uint8Array, right: Uint8Array): boolean {
  return left.length === right.length && left.every((item, index) => item === right[index]);
}

function syntaxDelta(
  parentId: string | null,
  previous: readonly string[],
  current: readonly string[]
): SyntaxDelta {
  let prefix = 0;
  while (
    prefix < previous.length &&
    prefix < current.length &&
    previous[prefix] === current[prefix]
  ) {
    prefix += 1;
  }
  let suffix = 0;
  while (
    suffix < previous.length - prefix &&
    suffix < current.length - prefix &&
    previous[previous.length - 1 - suffix] === current[current.length - 1 - suffix]
  ) {
    suffix += 1;
  }
  const body = {
    parent_id: parentId,
    previous_sha256: parentId === null ? null : hashReasoningValue(previous),
    current_sha256: hashReasoningValue(current),
    common_prefix_tokens: prefix,
    common_suffix_tokens: suffix,
    removed_tokens: previous.slice(prefix, previous.length - suffix),
    added_tokens: current.slice(prefix, current.length - suffix),
  };
  return { ...body, delta_sha256: hashReasoningValue(body) };
}

function unsignedNode(node: ReasoningArtifactNode): Omit<ReasoningArtifactNode, 'node_sha256'> {
  const { node_sha256: _ignored, ...body } = node;
  return body;
}

function unsignedEvent(event: ReasoningGraphEvent): Omit<ReasoningGraphEvent, 'event_sha256'> {
  const { event_sha256: _ignored, ...body } = event;
  return body;
}

function graphDigest(graph: ReasoningArtifactGraph): string {
  return hashReasoningValue({
    schema_version: graph.schema_version,
    graph_id: graph.graph_id,
    feature_names: graph.feature_names,
    node_hashes: Object.keys(graph.nodes)
      .sort()
      .map((id) => [id, graph.nodes[id]!.node_sha256]),
    event_hashes: graph.events.map((event) => event.event_sha256),
    head_ids: graph.head_ids,
  });
}

export function createReasoningArtifactGraph(
  graphId: string,
  featureNames: readonly string[]
): ReasoningArtifactGraph {
  requireId('graph_id', graphId);
  if (
    !Array.isArray(featureNames) ||
    featureNames.length === 0 ||
    featureNames.length > MAX_FEATURES
  ) {
    throw new Error(`feature_names must contain between 1 and ${MAX_FEATURES} entries`);
  }
  const normalized = featureNames.map((name) => {
    requireText('feature name', name, 128);
    return name;
  });
  if (new Set(normalized).size !== normalized.length) {
    throw new Error('feature_names must be unique');
  }
  return {
    schema_version: 'scbe.reasoning_artifact_graph.v1',
    graph_id: graphId,
    feature_names: normalized,
    nodes: {},
    events: [],
    head_ids: [],
  };
}

function buildNode(
  graph: ReasoningArtifactGraph,
  input: ReasoningArtifactInput,
  codec: BijectiveViewCodec,
  parentIds: string[],
  mergeAuthority: MergeAuthority | null
): ReasoningArtifactNode {
  if (
    Object.keys(graph.nodes).length >= MAX_GRAPH_NODES ||
    graph.events.length >= MAX_GRAPH_EVENTS
  ) {
    throw new Error('reasoning graph capacity reached; seal this graph and start a linked segment');
  }
  requireId('artifact id', input.id);
  if (graph.nodes[input.id]) throw new Error(`artifact already exists: ${input.id}`);
  if (!REASONING_TONGUES.includes(input.tongue)) throw new Error('unknown reasoning tongue');
  if (!POLICIES.includes(input.policy)) throw new Error('unknown artifact policy');
  requireText('public_summary', input.public_summary);
  requireText('state_transition', input.state_transition);
  if (!(input.canonical_bytes instanceof Uint8Array)) {
    throw new Error('canonical_bytes must be a Uint8Array');
  }
  if (input.canonical_bytes.length === 0 || input.canonical_bytes.length > MAX_CANONICAL_BYTES) {
    throw new Error(`canonical_bytes must contain 1..${MAX_CANONICAL_BYTES} bytes`);
  }
  const features = normalizeFeatures(input.feature_values, graph.feature_names.length);
  const syntax = normalizeSyntax(input.syntax_tokens);
  const evidence = normalizeHashes('evidence_hashes', input.evidence_hashes);
  const provenance = normalizeHashes('provenance_hashes', input.provenance_hashes);
  const viewTokens = [...codec.encode(input.tongue, input.canonical_bytes)];
  if (viewTokens.length === 0 || viewTokens.length > MAX_VIEW_TOKENS) {
    throw new Error('codec returned an invalid token count');
  }
  for (const token of viewTokens) {
    if (typeof token !== 'string' || token.length === 0 || token.length > 512) {
      throw new Error('codec returned an invalid view token');
    }
  }
  const viewCharacters = viewTokens.reduce((sum, token) => sum + token.length, 0);
  const priorViewCharacters = Object.values(graph.nodes).reduce(
    (sum, node) => sum + node.view_tokens.reduce((inner, token) => inner + token.length, 0),
    0
  );
  if (
    viewCharacters > MAX_VIEW_CHARACTERS ||
    priorViewCharacters + viewCharacters > MAX_GRAPH_VIEW_CHARACTERS
  ) {
    throw new Error('encoded view exceeds the bounded artifact-graph storage budget');
  }
  const decoded = codec.decode(input.tongue, viewTokens);
  if (!(decoded instanceof Uint8Array) || !bytesEqual(input.canonical_bytes, decoded)) {
    throw new Error('bijective codec round trip changed canonical bytes');
  }

  const canonicalHash = hashReasoningBytes(input.canonical_bytes);
  const parents = parentIds.map((id) => {
    const parent = graph.nodes[id];
    if (!parent) throw new Error(`parent artifact not found: ${id}`);
    return parent;
  });
  const roots = new Set(parents.map((parent) => parent.lineage_root_sha256));
  if (roots.size > 1) throw new Error('cannot join artifacts from different lineage roots');
  const deltas = parents.length
    ? parents.map((parent) => syntaxDelta(parent.id, parent.syntax_tokens, syntax))
    : [syntaxDelta(null, [], syntax)];
  const body: Omit<ReasoningArtifactNode, 'node_sha256'> = {
    schema_version: 'scbe.reasoning_artifact.v1',
    id: input.id,
    parent_ids: parentIds,
    tongue: input.tongue,
    public_summary: input.public_summary,
    state_transition: input.state_transition,
    canonical_bytes_sha256: canonicalHash,
    view_tokens: viewTokens,
    view_sha256: hashReasoningValue({ tongue: input.tongue, tokens: viewTokens }),
    syntax_tokens: syntax,
    syntax_deltas: deltas,
    feature_values: features,
    policy: input.policy,
    evidence_hashes: evidence,
    provenance_hashes: provenance,
    lineage_root_sha256: parents[0]?.lineage_root_sha256 ?? canonicalHash,
    merge_authority: mergeAuthority,
    created_sequence: graph.events.length,
  };
  return { ...body, node_sha256: hashReasoningValue(body) };
}

function appendEvent(
  graph: ReasoningArtifactGraph,
  kind: Exclude<ReasoningEventKind, 'backtrack'>,
  node: ReasoningArtifactNode
): ReasoningArtifactGraph {
  const heads = new Set(graph.head_ids);
  for (const parentId of node.parent_ids) heads.delete(parentId);
  heads.add(node.id);
  if (heads.size > MAX_GRAPH_HEADS) {
    throw new Error('too many simultaneous branch heads; contract or seal branches first');
  }
  const headIds = [...heads].sort();
  const body: Omit<ReasoningGraphEvent, 'event_sha256'> = {
    schema_version: 'scbe.reasoning_graph_event.v1',
    sequence: graph.events.length,
    kind,
    node_id: node.id,
    parent_ids: [...node.parent_ids],
    target_node_id: null,
    reason_sha256: null,
    head_ids: headIds,
    previous_event_sha256: graph.events.at(-1)?.event_sha256 ?? null,
  };
  const event = { ...body, event_sha256: hashReasoningValue(body) };
  return {
    ...graph,
    nodes: { ...graph.nodes, [node.id]: node },
    events: [...graph.events, event],
    head_ids: headIds,
  };
}

function requireValidGraph(graph: ReasoningArtifactGraph, codec?: BijectiveViewCodec): void {
  const verified = verifyReasoningArtifactGraph(graph, { codec });
  if (!verified.ok) throw new Error(`reasoning graph is invalid: ${verified.errors[0]}`);
}

export function appendReasoningArtifact(
  graph: ReasoningArtifactGraph,
  input: ReasoningArtifactInput,
  codec: BijectiveViewCodec
): ReasoningArtifactGraph {
  requireValidGraph(graph, codec);
  const parents = [...(input.parent_ids ?? [])];
  if (graph.events.length === 0) {
    if (parents.length !== 0) throw new Error('root artifact cannot declare a parent');
  } else {
    if (parents.length !== 1) throw new Error('append requires exactly one parent');
    if (!graph.head_ids.includes(parents[0]!)) {
      throw new Error('append parent is historical; use an explicit fork or backtrack');
    }
  }
  const node = buildNode(graph, input, codec, parents, null);
  return appendEvent(graph, 'append', node);
}

export function forkReasoningArtifact(
  graph: ReasoningArtifactGraph,
  input: ForkArtifactInput,
  codec: BijectiveViewCodec
): ReasoningArtifactGraph {
  requireValidGraph(graph, codec);
  requireId('parent_id', input.parent_id);
  if (!graph.nodes[input.parent_id])
    throw new Error(`parent artifact not found: ${input.parent_id}`);
  const { parent_id: parentId, ...artifact } = input;
  const node = buildNode(graph, { ...artifact, parent_ids: [parentId] }, codec, [parentId], null);
  return appendEvent(graph, 'fork', node);
}

function validateTypedReceipt(
  receipt: TypedEquivalenceReceipt,
  parents: readonly ReasoningArtifactNode[],
  outputHash: string,
  verify: EquivalenceVerifier | undefined
): void {
  requireText('equivalence verifier_id', receipt.verifier_id, 256);
  requireHash('equivalence verifier_sha256', receipt.verifier_sha256);
  requireHash('equivalence evidence_sha256', receipt.evidence_sha256);
  requireHash('equivalence output_canonical_sha256', receipt.output_canonical_sha256);
  const expectedParents = parents.map((parent) => parent.canonical_bytes_sha256).sort();
  if (
    receipt.schema_version !== 'scbe.reasoning_typed_equivalence.v1' ||
    receipt.passed !== true ||
    !arraysEqual(receipt.parent_canonical_sha256, expectedParents) ||
    receipt.output_canonical_sha256 !== outputHash
  ) {
    throw new Error('typed equivalence receipt does not bind these artifacts and output');
  }
  if (!verify || verify(receipt, parents, outputHash) !== true) {
    throw new Error('typed equivalence was not accepted by an external verifier');
  }
}

export function mergeReasoningArtifacts(
  graph: ReasoningArtifactGraph,
  input: MergeArtifactInput,
  codec: BijectiveViewCodec,
  options: MergeOptions = {}
): ReasoningArtifactGraph {
  requireValidGraph(graph, codec);
  const parentIds = [...new Set(input.parent_ids)].sort();
  if (parentIds.length < 2 || parentIds.length !== input.parent_ids.length) {
    throw new Error('merge requires at least two distinct parents');
  }
  if (parentIds.some((id) => !graph.head_ids.includes(id))) {
    throw new Error('merge parents must all be current branch heads');
  }
  const parents = parentIds.map((id) => graph.nodes[id]!);
  if (input.policy !== 'allow' || parents.some((parent) => parent.policy !== 'allow')) {
    throw new Error('deny, quarantine, or adversarial policy blocks merge');
  }
  if (new Set(parents.map((parent) => parent.lineage_root_sha256)).size !== 1) {
    throw new Error('cannot merge different canonical lineage roots');
  }
  const outputHash = hashReasoningBytes(input.canonical_bytes);
  const parentHashes = parents.map((parent) => parent.canonical_bytes_sha256);
  let authority: MergeAuthority;
  if (new Set(parentHashes).size === 1 && parentHashes[0] === outputHash) {
    authority = { kind: 'exact-canonical' };
  } else {
    const receipt = options.equivalence_receipt;
    if (!receipt) {
      throw new Error('geometry or similarity cannot authorize a non-exact merge');
    }
    validateTypedReceipt(receipt, parents, outputHash, options.verify_equivalence);
    if (!input.evidence_hashes.includes(receipt.evidence_sha256)) {
      throw new Error('merged artifact must retain the equivalence evidence hash');
    }
    authority = {
      kind: 'typed-equivalence',
      receipt: {
        ...receipt,
        parent_canonical_sha256: [...receipt.parent_canonical_sha256],
      },
      receipt_sha256: hashReasoningValue(receipt),
    };
  }
  const node = buildNode(graph, input, codec, parentIds, authority);
  return appendEvent(graph, 'merge', node);
}

function isAncestor(
  nodes: Readonly<Record<string, ReasoningArtifactNode>>,
  ancestorId: string,
  descendantId: string
): boolean {
  const pending = [descendantId];
  const visited = new Set<string>();
  while (pending.length) {
    const current = pending.pop()!;
    if (current === ancestorId) return true;
    if (visited.has(current)) continue;
    visited.add(current);
    pending.push(...(nodes[current]?.parent_ids ?? []));
  }
  return false;
}

export function backtrackReasoningGraph(
  graph: ReasoningArtifactGraph,
  targetNodeId: string,
  publicReason: string
): ReasoningArtifactGraph {
  requireValidGraph(graph);
  if (graph.events.length >= MAX_GRAPH_EVENTS) {
    throw new Error(
      'reasoning graph event capacity reached; seal this graph and start a linked segment'
    );
  }
  requireText('public backtrack reason', publicReason, 2048);
  if (!graph.nodes[targetNodeId]) throw new Error(`backtrack target not found: ${targetNodeId}`);
  if (!graph.head_ids.some((headId) => isAncestor(graph.nodes, targetNodeId, headId))) {
    throw new Error('backtrack target is not on an active branch lineage');
  }
  const body: Omit<ReasoningGraphEvent, 'event_sha256'> = {
    schema_version: 'scbe.reasoning_graph_event.v1',
    sequence: graph.events.length,
    kind: 'backtrack',
    node_id: null,
    parent_ids: [],
    target_node_id: targetNodeId,
    reason_sha256: hashReasoningValue(publicReason),
    head_ids: [targetNodeId],
    previous_event_sha256: graph.events.at(-1)?.event_sha256 ?? null,
  };
  const event = { ...body, event_sha256: hashReasoningValue(body) };
  return { ...graph, events: [...graph.events, event], head_ids: [targetNodeId] };
}

function compareJson(left: unknown, right: unknown): boolean {
  return canonicalJson(left) === canonicalJson(right);
}

export function verifyReasoningArtifactGraph(
  graph: ReasoningArtifactGraph,
  options: GraphVerificationOptions = {}
): GraphVerificationResult {
  const errors: string[] = [];
  const add = (message: string): void => {
    if (!errors.includes(message)) errors.push(message);
  };
  try {
    if (graph.schema_version !== 'scbe.reasoning_artifact_graph.v1') add('invalid graph schema');
    try {
      requireId('graph_id', graph.graph_id);
    } catch (error) {
      add((error as Error).message);
    }
    if (
      !Array.isArray(graph.feature_names) ||
      graph.feature_names.length === 0 ||
      graph.feature_names.length > MAX_FEATURES ||
      new Set(graph.feature_names).size !== graph.feature_names.length
    ) {
      add('invalid feature schema');
    }

    const nodeIds = Object.keys(graph.nodes);
    if (
      nodeIds.length > MAX_GRAPH_NODES ||
      graph.events.length > MAX_GRAPH_EVENTS ||
      graph.head_ids.length > MAX_GRAPH_HEADS
    ) {
      add('graph exceeds bounded node, event, or head capacity');
    }
    let graphViewCharacters = 0;
    for (const [key, node] of Object.entries(graph.nodes)) {
      if (key !== node.id) add(`node key differs from id: ${key}`);
      if (node.schema_version !== 'scbe.reasoning_artifact.v1') add(`invalid node schema: ${key}`);
      if (!ID_RE.test(node.id)) add(`invalid node id: ${key}`);
      if (!REASONING_TONGUES.includes(node.tongue)) add(`invalid tongue: ${key}`);
      if (
        typeof node.public_summary !== 'string' ||
        node.public_summary.trim().length === 0 ||
        typeof node.state_transition !== 'string' ||
        node.state_transition.trim().length === 0
      ) {
        add(`invalid public artifact text: ${key}`);
      }
      if (node.node_sha256 !== hashReasoningValue(unsignedNode(node)))
        add(`node hash mismatch: ${key}`);
      if (!HASH_RE.test(node.node_sha256) || !HASH_RE.test(node.canonical_bytes_sha256)) {
        add(`invalid node digest: ${key}`);
      }
      if (
        node.created_sequence < 0 ||
        !Number.isSafeInteger(node.created_sequence) ||
        new Set(node.parent_ids).size !== node.parent_ids.length ||
        !arraysEqual(node.parent_ids, [...node.parent_ids].sort())
      ) {
        add(`non-canonical node lineage: ${key}`);
      }
      if (
        node.view_sha256 !== hashReasoningValue({ tongue: node.tongue, tokens: node.view_tokens })
      ) {
        add(`view hash mismatch: ${key}`);
      }
      if (
        !HASH_RE.test(node.view_sha256) ||
        node.view_tokens.length === 0 ||
        node.view_tokens.some(
          (token) => typeof token !== 'string' || token.length === 0 || token.length > 512
        ) ||
        node.syntax_tokens.length > MAX_SYNTAX_TOKENS ||
        node.syntax_tokens.some(
          (token) => typeof token !== 'string' || token.length === 0 || token.length > 256
        )
      ) {
        add(`invalid encoded or syntax view: ${key}`);
      }
      graphViewCharacters += node.view_tokens.reduce(
        (sum, token) => sum + (typeof token === 'string' ? token.length : 0),
        0
      );
      if (node.feature_values.length !== graph.feature_names.length)
        add(`feature width mismatch: ${key}`);
      if (node.feature_values.some((value) => !Number.isFinite(value)))
        add(`non-finite feature: ${key}`);
      if (!POLICIES.includes(node.policy)) add(`invalid policy: ${key}`);
      if (
        node.evidence_hashes.length === 0 ||
        node.provenance_hashes.length === 0 ||
        [...node.evidence_hashes, ...node.provenance_hashes].some((hash) => !HASH_RE.test(hash))
      ) {
        add(`invalid evidence/provenance hashes: ${key}`);
      }
      const parents = node.parent_ids
        .map((id) => graph.nodes[id])
        .filter(Boolean) as ReasoningArtifactNode[];
      if (parents.length !== node.parent_ids.length) add(`missing parent: ${key}`);
      if (parents.some((parent) => parent.created_sequence >= node.created_sequence)) {
        add(`parent is not earlier than child: ${key}`);
      }
      const expectedRoot = parents[0]?.lineage_root_sha256 ?? node.canonical_bytes_sha256;
      if (
        node.lineage_root_sha256 !== expectedRoot ||
        new Set(parents.map((parent) => parent.lineage_root_sha256)).size > 1
      ) {
        add(`lineage root mismatch: ${key}`);
      }
      const expectedDeltas = parents.length
        ? parents.map((parent) => syntaxDelta(parent.id, parent.syntax_tokens, node.syntax_tokens))
        : [syntaxDelta(null, [], node.syntax_tokens)];
      if (!compareJson(node.syntax_deltas, expectedDeltas)) add(`syntax delta mismatch: ${key}`);
      if (options.codec) {
        try {
          const decoded = options.codec.decode(node.tongue, node.view_tokens);
          if (hashReasoningBytes(decoded) !== node.canonical_bytes_sha256) {
            add(`codec view does not recover canonical bytes: ${key}`);
          }
        } catch {
          add(`codec rejected stored view: ${key}`);
        }
      }
      if (node.parent_ids.length < 2 && node.merge_authority !== null) {
        add(`non-merge node has merge authority: ${key}`);
      }
      if (node.parent_ids.length >= 2) {
        const authority = node.merge_authority;
        if (!authority) {
          add(`merge node lacks authority: ${key}`);
        } else if (authority.kind === 'exact-canonical') {
          const hashes = new Set(parents.map((parent) => parent.canonical_bytes_sha256));
          if (hashes.size !== 1 || !hashes.has(node.canonical_bytes_sha256)) {
            add(`exact merge is not canonical-byte exact: ${key}`);
          }
        } else {
          const receipt = authority.receipt;
          if (
            receipt.schema_version !== 'scbe.reasoning_typed_equivalence.v1' ||
            receipt.passed !== true ||
            typeof receipt.verifier_id !== 'string' ||
            receipt.verifier_id.trim().length === 0 ||
            !HASH_RE.test(receipt.verifier_sha256) ||
            !HASH_RE.test(receipt.evidence_sha256) ||
            !HASH_RE.test(receipt.output_canonical_sha256)
          ) {
            add(`invalid typed equivalence receipt: ${key}`);
          }
          if (authority.receipt_sha256 !== hashReasoningValue(receipt)) {
            add(`typed equivalence receipt hash mismatch: ${key}`);
          }
          const expected = parents.map((parent) => parent.canonical_bytes_sha256).sort();
          if (
            !arraysEqual(receipt.parent_canonical_sha256, expected) ||
            receipt.output_canonical_sha256 !== node.canonical_bytes_sha256 ||
            !node.evidence_hashes.includes(receipt.evidence_sha256)
          ) {
            add(`typed equivalence receipt binding mismatch: ${key}`);
          }
          if (options.verify_equivalence) {
            if (!options.verify_equivalence(receipt, parents, node.canonical_bytes_sha256)) {
              add(`typed equivalence re-verification failed: ${key}`);
            }
          } else if (options.require_equivalence_reverification) {
            add(`typed equivalence verifier unavailable: ${key}`);
          }
        }
      }
    }
    if (graphViewCharacters > MAX_GRAPH_VIEW_CHARACTERS) {
      add('graph exceeds bounded encoded-view storage');
    }

    const replayHeads = new Set<string>();
    const created = new Set<string>();
    let previous: string | null = null;
    for (let index = 0; index < graph.events.length; index += 1) {
      const event = graph.events[index]!;
      if (event.schema_version !== 'scbe.reasoning_graph_event.v1') {
        add(`invalid event schema: ${index}`);
      }
      if (!['append', 'fork', 'merge', 'backtrack'].includes(event.kind)) {
        add(`invalid event kind: ${index}`);
      }
      if (
        !HASH_RE.test(event.event_sha256) ||
        (event.previous_event_sha256 !== null && !HASH_RE.test(event.previous_event_sha256)) ||
        (event.reason_sha256 !== null && !HASH_RE.test(event.reason_sha256))
      ) {
        add(`invalid event digest: ${index}`);
      }
      if (event.sequence !== index) add(`event sequence mismatch: ${index}`);
      if (event.previous_event_sha256 !== previous) add(`event chain mismatch: ${index}`);
      if (event.event_sha256 !== hashReasoningValue(unsignedEvent(event))) {
        add(`event hash mismatch: ${index}`);
      }
      if (event.kind === 'backtrack') {
        if (
          event.node_id !== null ||
          event.parent_ids.length !== 0 ||
          !event.target_node_id ||
          !graph.nodes[event.target_node_id] ||
          !event.reason_sha256
        ) {
          add(`invalid backtrack event: ${index}`);
        } else {
          const active = [...replayHeads];
          if (!active.some((headId) => isAncestor(graph.nodes, event.target_node_id!, headId))) {
            add(`backtrack target was not active lineage: ${index}`);
          }
          replayHeads.clear();
          replayHeads.add(event.target_node_id);
        }
      } else {
        const node = event.node_id ? graph.nodes[event.node_id] : undefined;
        if (!node || created.has(node.id)) {
          add(`invalid or repeated event node: ${index}`);
        } else {
          if (node.created_sequence !== index) add(`node creation sequence mismatch: ${node.id}`);
          if (!arraysEqual(node.parent_ids, event.parent_ids))
            add(`event parent mismatch: ${node.id}`);
          if (node.parent_ids.some((parentId) => !created.has(parentId))) {
            add(`event references a future parent: ${node.id}`);
          }
          if (event.kind === 'append') {
            if (index === 0 ? node.parent_ids.length !== 0 : node.parent_ids.length !== 1) {
              add(`invalid append arity: ${node.id}`);
            }
            if (index > 0 && !replayHeads.has(node.parent_ids[0]!)) {
              add(`append did not use an active head: ${node.id}`);
            }
          }
          if (event.kind === 'fork' && node.parent_ids.length !== 1) {
            add(`invalid fork arity: ${node.id}`);
          }
          if (event.kind === 'merge') {
            if (node.parent_ids.length < 2 || node.parent_ids.some((id) => !replayHeads.has(id))) {
              add(`merge did not consume active heads: ${node.id}`);
            }
          }
          for (const parentId of node.parent_ids) replayHeads.delete(parentId);
          replayHeads.add(node.id);
          created.add(node.id);
        }
      }
      const expectedHeads = [...replayHeads].sort();
      if (!arraysEqual(event.head_ids, expectedHeads)) add(`event head mismatch: ${index}`);
      previous = event.event_sha256;
    }
    if (created.size !== nodeIds.length || nodeIds.some((id) => !created.has(id))) {
      add('one or more nodes have no creation event');
    }
    if (!arraysEqual(graph.head_ids, [...replayHeads].sort()))
      add('graph heads differ from replayed heads');
  } catch (error) {
    add(`verification exception: ${(error as Error).message}`);
  }
  let digest: string;
  try {
    digest = graphDigest(graph);
  } catch {
    digest = '0'.repeat(64);
  }
  return { ok: errors.length === 0, errors, graph_sha256: digest };
}

function primaryPath(graph: ReasoningArtifactGraph, headId: string): ReasoningArtifactNode[] {
  const reverse: ReasoningArtifactNode[] = [];
  const visited = new Set<string>();
  let current: ReasoningArtifactNode | undefined = graph.nodes[headId];
  if (!current) throw new Error(`telemetry head not found: ${headId}`);
  while (current) {
    if (visited.has(current.id)) throw new Error('cycle found while constructing branch tube');
    visited.add(current.id);
    reverse.push(current);
    const primaryParent: string | undefined = [...current.parent_ids].sort()[0];
    current = primaryParent ? graph.nodes[primaryParent] : undefined;
  }
  return reverse.reverse();
}

function euclidean(left: readonly number[], right: readonly number[]): number {
  return Math.sqrt(left.reduce((sum, value, index) => sum + (value - right[index]!) ** 2, 0));
}

function complexAmplitude(values: readonly number[], mode: number): [number, number] {
  const scale = 1 / Math.sqrt(values.length);
  let real = 0;
  let imaginary = 0;
  for (let time = 0; time < values.length; time += 1) {
    const angle = (-2 * Math.PI * mode * time) / values.length;
    real += values[time]! * Math.cos(angle);
    imaginary += values[time]! * Math.sin(angle);
  }
  return [real * scale, imaginary * scale];
}

export function computeTubalBranchTelemetry(
  graph: ReasoningArtifactGraph,
  requestedHeadIds: readonly string[] = graph.head_ids
): TubalBranchTelemetry {
  const verified = verifyReasoningArtifactGraph(graph);
  if (!verified.ok) throw new Error(`cannot measure invalid graph: ${verified.errors[0]}`);
  const headIds = [...new Set(requestedHeadIds)].sort();
  if (headIds.length === 0) throw new Error('at least one branch head is required');
  const paths = headIds.map((headId) => primaryPath(graph, headId));
  const timeSteps = Math.max(...paths.map((path) => path.length));
  const features = graph.feature_names.length;
  const dftOperations = headIds.length * features * timeSteps * timeSteps;
  if (dftOperations > MAX_TUBAL_DFT_OPERATIONS) {
    throw new Error(
      'requested tubal DFT exceeds the bounded telemetry budget; segment or downsample first'
    );
  }
  // Shape: branch x feature x time. Short branches hold their final public state.
  const tubes = paths.map((path) => {
    const values = path.map((node) => node.feature_values);
    while (values.length < timeSteps) values.push([...values.at(-1)!]);
    return Array.from({ length: features }, (_, feature) =>
      values.map((sample) => sample[feature]!)
    );
  });

  const finalVectors = paths.map((path) => path.at(-1)!.feature_values);
  const pairwise: TubalPairwiseDistance[] = [];
  for (let left = 0; left < headIds.length; left += 1) {
    for (let right = left + 1; right < headIds.length; right += 1) {
      pairwise.push({
        left_head_id: headIds[left]!,
        right_head_id: headIds[right]!,
        distance: euclidean(finalVectors[left]!, finalVectors[right]!),
      });
    }
  }
  const meanSeparation = pairwise.length
    ? pairwise.reduce((sum, item) => sum + item.distance, 0) / pairwise.length
    : 0;
  const centroid = Array.from(
    { length: features },
    (_, feature) =>
      finalVectors.reduce((sum, vector) => sum + vector[feature]!, 0) / finalVectors.length
  );
  const centroidResidual =
    finalVectors.reduce((sum, vector) => sum + euclidean(vector, centroid), 0) /
    finalVectors.length;

  const spectral = Array.from({ length: timeSteps }, (_, mode) => {
    let energy = 0;
    for (const branch of tubes) {
      for (const tube of branch) {
        const [real, imaginary] = complexAmplitude(tube, mode);
        energy += real ** 2 + imaginary ** 2;
      }
    }
    return energy / (headIds.length * features);
  });
  const nonDc = spectral.slice(1).reduce((sum, energy) => sum + energy, 0);
  const highCutoff = Math.max(1, Math.ceil(timeSteps / 4));
  const highEnergy = spectral.reduce((sum, energy, mode) => {
    if (mode === 0) return sum;
    const foldedMode = Math.min(mode, timeSteps - mode);
    return foldedMode >= highCutoff ? sum + energy : sum;
  }, 0);

  let coherenceWeight = 0;
  let weightedCoherence = 0;
  for (let mode = 1; mode <= Math.floor(timeSteps / 2); mode += 1) {
    for (let feature = 0; feature < features; feature += 1) {
      const amplitudes = tubes
        .map((branch) => complexAmplitude(branch[feature]!, mode))
        .map(([real, imaginary]) => ({ real, imaginary, magnitude: Math.hypot(real, imaginary) }))
        .filter((item) => item.magnitude > 1e-12);
      if (amplitudes.length === 0) continue;
      const real = amplitudes.reduce((sum, item) => sum + item.real / item.magnitude, 0);
      const imaginary = amplitudes.reduce((sum, item) => sum + item.imaginary / item.magnitude, 0);
      const coherence = Math.hypot(real, imaginary) / amplitudes.length;
      const weight = amplitudes.reduce((sum, item) => sum + item.magnitude, 0);
      weightedCoherence += coherence * weight;
      coherenceWeight += weight;
    }
  }

  const policyCounts: Record<ArtifactPolicy, number> = {
    allow: 0,
    deny: 0,
    quarantine: 0,
    adversarial: 0,
  };
  for (const headId of headIds) policyCounts[graph.nodes[headId]!.policy] += 1;
  return {
    schema_version: 'scbe.reasoning_tubal_telemetry.v1',
    graph_sha256: verified.graph_sha256,
    head_ids: headIds,
    tensor_shape: [headIds.length, features, timeSteps],
    feature_names: [...graph.feature_names],
    branch_depths: Object.fromEntries(
      headIds.map((headId, index) => [headId, paths[index]!.length - 1])
    ),
    pairwise_head_distances: pairwise,
    mean_head_separation: meanSeparation,
    centroid_residual: centroidResidual,
    convergence_degree: 1 / (1 + meanSeparation),
    spectral_mode_energy: spectral,
    non_dc_energy: nonDc,
    high_frequency_fraction: nonDc > 0 ? highEnergy / nonDc : 0,
    phase_coherence: coherenceWeight > 0 ? weightedCoherence / coherenceWeight : 1,
    head_policy_counts: policyCounts,
    unresolved_head_ids: headIds.filter((headId) => graph.nodes[headId]!.policy !== 'allow'),
    backtrack_count: graph.events.filter((event) => event.kind === 'backtrack').length,
    authority: 'telemetry-only-not-merge-authority',
  };
}
