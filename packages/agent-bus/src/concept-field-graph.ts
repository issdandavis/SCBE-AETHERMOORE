/**
 * Nested, overlapping concept fields over the public reasoning-artifact DAG.
 *
 * This module stores source-backed public reasoning records. It does not claim
 * to expose a model's private chain of thought. Concept membership, relation
 * authority, and evidence status remain explicit so a reproducible heuristic
 * cannot silently become an independently verified fact.
 */

import {
  hashReasoningValue,
  verifyReasoningArtifactGraph,
  type ArtifactPolicy,
  type ReasoningArtifactGraph,
} from './reasoning-artifact-graph.js';

export const CONCEPT_RELATIONS = [
  'supports',
  'contradicts',
  'requires',
  'explains',
  'enables',
  'returns_to',
  'elaborates',
  'transitions',
  'same_source',
] as const;

export type ConceptRelation = (typeof CONCEPT_RELATIONS)[number];
export type ConceptAuthority =
  | 'source-annotation'
  | 'deterministic-rule'
  | 'external-verifier'
  | 'model-proposal';
export type ConceptEvidenceStatus = 'source' | 'verified' | 'hypothesis' | 'rejected';
export type ConceptRouteHopKind = 'typed-edge' | 'concept-bubble';

export interface ConceptMembership {
  artifact_id: string;
  weight: number;
  authority: ConceptAuthority;
  status: ConceptEvidenceStatus;
  evidence_hashes: string[];
}

export interface ConceptBubble {
  schema_version: 'scbe.concept_bubble.v1';
  id: string;
  label: string;
  parent_bubble_ids: string[];
  memberships: ConceptMembership[];
  provenance_hashes: string[];
}

export interface TopicField {
  schema_version: 'scbe.topic_field.v1';
  id: string;
  label: string;
  parent_field_id: string | null;
  bubble_ids: string[];
  provenance_hashes: string[];
}

export interface TypedConceptEdge {
  schema_version: 'scbe.typed_concept_edge.v1';
  id: string;
  from_artifact_id: string;
  to_artifact_id: string;
  relation: ConceptRelation;
  cost: number;
  authority: ConceptAuthority;
  status: ConceptEvidenceStatus;
  evidence_hashes: string[];
}

export interface ConceptFieldGraph {
  schema_version: 'scbe.concept_field_graph.v1';
  graph_id: string;
  reasoning_graph_id: string;
  reasoning_graph_sha256: string;
  bubbles: ConceptBubble[];
  fields: TopicField[];
  edges: TypedConceptEdge[];
  graph_sha256: string;
}

export interface ConceptFieldGraphInput {
  bubbles: readonly ConceptBubble[];
  fields: readonly TopicField[];
  edges: readonly TypedConceptEdge[];
}

export interface ConceptFieldVerification {
  ok: boolean;
  errors: string[];
  graph_sha256: string;
}

export interface ConceptRouteGoal {
  id: string;
  public_goal: string;
  start_artifact_ids: string[];
  target_artifact_ids?: string[];
  target_bubble_ids?: string[];
  target_field_ids?: string[];
  relation_multipliers?: Partial<Record<ConceptRelation, number>>;
  allow_bubble_hops?: boolean;
  bubble_hop_cost?: number;
  verified_only?: boolean;
  allowed_policies?: ArtifactPolicy[];
  max_hops?: number;
  max_expansions?: number;
}

export interface NormalizedConceptRouteGoal {
  id: string;
  public_goal: string;
  start_artifact_ids: string[];
  target_artifact_ids: string[];
  target_bubble_ids: string[];
  target_field_ids: string[];
  relation_multipliers: Partial<Record<ConceptRelation, number>>;
  allow_bubble_hops: boolean;
  bubble_hop_cost: number;
  verified_only: boolean;
  allowed_policies: ArtifactPolicy[];
  max_hops: number;
  max_expansions: number;
}

export interface ConceptRouteHop {
  index: number;
  kind: ConceptRouteHopKind;
  from_artifact_id: string;
  to_artifact_id: string;
  relation: ConceptRelation | 'co_member';
  edge_id: string | null;
  bubble_id: string | null;
  authority: ConceptAuthority;
  status: ConceptEvidenceStatus;
  evidence_hashes: string[];
  step_cost: number;
  cumulative_cost: number;
  previous_receipt_sha256: string;
  receipt_sha256: string;
}

export interface PublicReasoningStep {
  id: string;
  parent_step_id: string | null;
  depth: number;
  kind: 'anchor' | 'follow-relation' | 'cross-bubble';
  artifact_id: string;
  public_summary: string;
  state_transition: string;
  bubble_ids: string[];
  field_ids: string[];
  evidence_hashes: string[];
}

export interface ConceptRouteResult {
  schema_version: 'scbe.concept_route.v1';
  route_id: string;
  status: 'reached' | 'no-route';
  rejection_code: null | 'E_NO_ROUTE';
  goal: NormalizedConceptRouteGoal;
  goal_sha256: string;
  reasoning_graph_sha256: string;
  concept_graph_sha256: string;
  selected_start_artifact_id: string | null;
  target_artifact_id: string | null;
  artifact_path: string[];
  hops: ConceptRouteHop[];
  public_steps: PublicReasoningStep[];
  total_cost: number | null;
  expanded_states: number;
  route_sha256: string;
}

const ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const HASH_RE = /^[a-f0-9]{64}$/;
const AUTHORITIES: ConceptAuthority[] = [
  'source-annotation',
  'deterministic-rule',
  'external-verifier',
  'model-proposal',
];
const STATUSES: ConceptEvidenceStatus[] = ['source', 'verified', 'hypothesis', 'rejected'];
const POLICIES: ArtifactPolicy[] = ['allow', 'deny', 'quarantine', 'adversarial'];
const MAX_BUBBLES = 4096;
const MAX_FIELDS = 2048;
const MAX_EDGES = 32768;
const MAX_MEMBERS_PER_BUBBLE = 2048;
const MAX_ROUTE_HOPS = 256;
const MAX_ROUTE_EXPANSIONS = 100_000;

interface CandidateHop {
  kind: ConceptRouteHopKind;
  from_artifact_id: string;
  to_artifact_id: string;
  relation: ConceptRelation | 'co_member';
  edge_id: string | null;
  bubble_id: string | null;
  authority: ConceptAuthority;
  status: ConceptEvidenceStatus;
  evidence_hashes: string[];
  step_cost: number;
}

interface SearchState {
  artifact_id: string;
  start_artifact_id: string;
  cost: number;
  hops: CandidateHop[];
  path: string[];
  signature: string;
}

function requireId(name: string, value: unknown): asserts value is string {
  if (typeof value !== 'string' || !ID_RE.test(value)) {
    throw new Error(`${name} is not a valid stable identifier`);
  }
}

function requireText(name: string, value: unknown, maximum = 8192): asserts value is string {
  if (typeof value !== 'string' || value.trim().length === 0 || value.length > maximum) {
    throw new Error(`${name} must be non-empty and at most ${maximum} characters`);
  }
}

function normalizeHashes(name: string, values: readonly string[]): string[] {
  if (!Array.isArray(values) || values.length === 0) {
    throw new Error(`${name} must contain at least one receipt hash`);
  }
  for (const value of values) {
    if (typeof value !== 'string' || !HASH_RE.test(value)) {
      throw new Error(`${name} must contain lowercase SHA-256 digests`);
    }
  }
  return [...new Set(values)].sort();
}

function uniqueSortedIds(name: string, values: readonly string[], allowEmpty = true): string[] {
  if (!Array.isArray(values) || (!allowEmpty && values.length === 0)) {
    throw new Error(`${name} must be ${allowEmpty ? 'an array' : 'a non-empty array'}`);
  }
  for (const value of values) requireId(name, value);
  if (new Set(values).size !== values.length) throw new Error(`${name} contains duplicates`);
  return [...values].sort();
}

function graphBody(graph: ConceptFieldGraph): Omit<ConceptFieldGraph, 'graph_sha256'> {
  const { graph_sha256: _ignored, ...body } = graph;
  return body;
}

function routeBody(route: ConceptRouteResult): Omit<ConceptRouteResult, 'route_sha256'> {
  const { route_sha256: _ignored, ...body } = route;
  return body;
}

function validateAcyclicParents(
  label: string,
  ids: readonly string[],
  parentsFor: (id: string) => readonly string[]
): string[] {
  const errors: string[] = [];
  const state = new Map<string, 0 | 1 | 2>();
  const visit = (id: string, stack: string[]): void => {
    const current = state.get(id) ?? 0;
    if (current === 2) return;
    if (current === 1) {
      errors.push(`${label} parent cycle: ${[...stack, id].join(' -> ')}`);
      return;
    }
    state.set(id, 1);
    for (const parent of parentsFor(id)) visit(parent, [...stack, id]);
    state.set(id, 2);
  };
  for (const id of ids) visit(id, []);
  return errors;
}

function normalizedMembership(value: ConceptMembership): ConceptMembership {
  requireId('membership artifact_id', value.artifact_id);
  if (!Number.isFinite(value.weight) || value.weight <= 0 || value.weight > 1) {
    throw new Error('membership weight must be in (0, 1]');
  }
  if (!AUTHORITIES.includes(value.authority)) throw new Error('unknown membership authority');
  if (!STATUSES.includes(value.status)) throw new Error('unknown membership status');
  return {
    artifact_id: value.artifact_id,
    weight: value.weight,
    authority: value.authority,
    status: value.status,
    evidence_hashes: normalizeHashes('membership evidence_hashes', value.evidence_hashes),
  };
}

function normalizedBubble(value: ConceptBubble): ConceptBubble {
  requireId('bubble id', value.id);
  requireText('bubble label', value.label, 256);
  if (!Array.isArray(value.memberships) || value.memberships.length === 0) {
    throw new Error('bubble memberships must be non-empty');
  }
  if (value.memberships.length > MAX_MEMBERS_PER_BUBBLE) {
    throw new Error(`bubble memberships exceed ${MAX_MEMBERS_PER_BUBBLE}`);
  }
  const memberships = value.memberships.map(normalizedMembership);
  if (new Set(memberships.map((item) => item.artifact_id)).size !== memberships.length) {
    throw new Error(`bubble memberships contain duplicate artifacts: ${value.id}`);
  }
  return {
    schema_version: 'scbe.concept_bubble.v1',
    id: value.id,
    label: value.label.trim(),
    parent_bubble_ids: uniqueSortedIds('parent_bubble_ids', value.parent_bubble_ids),
    memberships: memberships.sort((left, right) =>
      left.artifact_id.localeCompare(right.artifact_id)
    ),
    provenance_hashes: normalizeHashes('bubble provenance_hashes', value.provenance_hashes),
  };
}

function normalizedField(value: TopicField): TopicField {
  requireId('field id', value.id);
  requireText('field label', value.label, 256);
  if (value.parent_field_id !== null) requireId('parent_field_id', value.parent_field_id);
  return {
    schema_version: 'scbe.topic_field.v1',
    id: value.id,
    label: value.label.trim(),
    parent_field_id: value.parent_field_id,
    bubble_ids: uniqueSortedIds('field bubble_ids', value.bubble_ids),
    provenance_hashes: normalizeHashes('field provenance_hashes', value.provenance_hashes),
  };
}

function normalizedEdge(value: TypedConceptEdge): TypedConceptEdge {
  requireId('edge id', value.id);
  requireId('from_artifact_id', value.from_artifact_id);
  requireId('to_artifact_id', value.to_artifact_id);
  if (value.from_artifact_id === value.to_artifact_id) {
    throw new Error('typed concept edge cannot point to itself');
  }
  if (!CONCEPT_RELATIONS.includes(value.relation)) throw new Error('unknown concept relation');
  if (!Number.isFinite(value.cost) || value.cost <= 0) {
    throw new Error('typed concept edge cost must be positive');
  }
  if (!AUTHORITIES.includes(value.authority)) throw new Error('unknown edge authority');
  if (!STATUSES.includes(value.status)) throw new Error('unknown edge status');
  return {
    schema_version: 'scbe.typed_concept_edge.v1',
    id: value.id,
    from_artifact_id: value.from_artifact_id,
    to_artifact_id: value.to_artifact_id,
    relation: value.relation,
    cost: value.cost,
    authority: value.authority,
    status: value.status,
    evidence_hashes: normalizeHashes('edge evidence_hashes', value.evidence_hashes),
  };
}

export function createConceptFieldGraph(
  graphId: string,
  reasoningGraph: ReasoningArtifactGraph,
  input: ConceptFieldGraphInput
): ConceptFieldGraph {
  requireId('graph_id', graphId);
  const reasoningVerification = verifyReasoningArtifactGraph(reasoningGraph);
  if (!reasoningVerification.ok) {
    throw new Error(`reasoning graph is invalid: ${reasoningVerification.errors[0]}`);
  }
  if (input.bubbles.length > MAX_BUBBLES) throw new Error('too many concept bubbles');
  if (input.fields.length > MAX_FIELDS) throw new Error('too many topic fields');
  if (input.edges.length > MAX_EDGES) throw new Error('too many typed concept edges');

  const bubbles = input.bubbles.map(normalizedBubble).sort((a, b) => a.id.localeCompare(b.id));
  const fields = input.fields.map(normalizedField).sort((a, b) => a.id.localeCompare(b.id));
  const edges = input.edges.map(normalizedEdge).sort((a, b) => a.id.localeCompare(b.id));
  if (new Set(bubbles.map((item) => item.id)).size !== bubbles.length) {
    throw new Error('concept bubble ids must be unique');
  }
  if (new Set(fields.map((item) => item.id)).size !== fields.length) {
    throw new Error('topic field ids must be unique');
  }
  if (new Set(edges.map((item) => item.id)).size !== edges.length) {
    throw new Error('typed concept edge ids must be unique');
  }

  const body: Omit<ConceptFieldGraph, 'graph_sha256'> = {
    schema_version: 'scbe.concept_field_graph.v1',
    graph_id: graphId,
    reasoning_graph_id: reasoningGraph.graph_id,
    reasoning_graph_sha256: reasoningVerification.graph_sha256,
    bubbles,
    fields,
    edges,
  };
  const graph = { ...body, graph_sha256: hashReasoningValue(body) };
  const verified = verifyConceptFieldGraph(graph, reasoningGraph);
  if (!verified.ok) throw new Error(`concept field graph is invalid: ${verified.errors[0]}`);
  return graph;
}

export function verifyConceptFieldGraph(
  graph: ConceptFieldGraph,
  reasoningGraph: ReasoningArtifactGraph
): ConceptFieldVerification {
  const errors: string[] = [];
  const reasoningVerification = verifyReasoningArtifactGraph(reasoningGraph);
  if (!reasoningVerification.ok) {
    errors.push(...reasoningVerification.errors.map((error) => `reasoning graph: ${error}`));
  }
  if (graph.schema_version !== 'scbe.concept_field_graph.v1') {
    errors.push('unsupported concept field graph schema');
  }
  try {
    requireId('graph_id', graph.graph_id);
    requireId('reasoning_graph_id', graph.reasoning_graph_id);
  } catch (error) {
    errors.push(error instanceof Error ? error.message : String(error));
  }
  if (graph.reasoning_graph_id !== reasoningGraph.graph_id) {
    errors.push('reasoning graph id mismatch');
  }
  if (graph.reasoning_graph_sha256 !== reasoningVerification.graph_sha256) {
    errors.push('reasoning graph hash mismatch');
  }
  let expectedHash = '';
  try {
    expectedHash = hashReasoningValue(graphBody(graph));
    if (graph.graph_sha256 !== expectedHash) errors.push('concept field graph hash mismatch');
  } catch (error) {
    errors.push(
      `concept field graph cannot be hashed: ${error instanceof Error ? error.message : String(error)}`
    );
  }

  let unsafeStructure = false;
  if (!Array.isArray(graph.bubbles)) {
    errors.push('concept bubbles must be an array');
    unsafeStructure = true;
  }
  if (!Array.isArray(graph.fields)) {
    errors.push('topic fields must be an array');
    unsafeStructure = true;
  }
  if (!Array.isArray(graph.edges)) {
    errors.push('typed concept edges must be an array');
    unsafeStructure = true;
  }
  const bubbles = Array.isArray(graph.bubbles) ? graph.bubbles : [];
  const fields = Array.isArray(graph.fields) ? graph.fields : [];
  const edges = Array.isArray(graph.edges) ? graph.edges : [];
  if (bubbles.length > MAX_BUBBLES) {
    errors.push('too many concept bubbles');
    unsafeStructure = true;
  }
  if (fields.length > MAX_FIELDS) {
    errors.push('too many topic fields');
    unsafeStructure = true;
  }
  if (edges.length > MAX_EDGES) {
    errors.push('too many typed concept edges');
    unsafeStructure = true;
  }
  if (unsafeStructure) return { ok: false, errors, graph_sha256: expectedHash };

  for (const bubble of bubbles) {
    try {
      const normalized = normalizedBubble(bubble);
      if (hashReasoningValue(normalized) !== hashReasoningValue(bubble)) {
        errors.push(`concept bubble is not canonical: ${normalized.id}`);
      }
    } catch (error) {
      unsafeStructure = true;
      errors.push(
        `invalid concept bubble: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }
  for (const field of fields) {
    try {
      const normalized = normalizedField(field);
      if (hashReasoningValue(normalized) !== hashReasoningValue(field)) {
        errors.push(`topic field is not canonical: ${normalized.id}`);
      }
    } catch (error) {
      unsafeStructure = true;
      errors.push(`invalid topic field: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  for (const edge of edges) {
    try {
      const normalized = normalizedEdge(edge);
      if (hashReasoningValue(normalized) !== hashReasoningValue(edge)) {
        errors.push(`typed concept edge is not canonical: ${normalized.id}`);
      }
    } catch (error) {
      unsafeStructure = true;
      errors.push(
        `invalid typed concept edge: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  if (unsafeStructure) return { ok: false, errors, graph_sha256: expectedHash };

  const artifactIds = new Set(Object.keys(reasoningGraph.nodes));
  const bubbleMap = new Map(bubbles.map((bubble) => [bubble.id, bubble]));
  const fieldMap = new Map(fields.map((field) => [field.id, field]));
  const edgeIds = new Set<string>();
  if (bubbleMap.size !== bubbles.length) errors.push('duplicate concept bubble id');
  if (fieldMap.size !== fields.length) errors.push('duplicate topic field id');

  for (const bubble of bubbles) {
    for (const parent of bubble.parent_bubble_ids) {
      if (!bubbleMap.has(parent)) errors.push(`unknown parent bubble: ${bubble.id} -> ${parent}`);
      if (parent === bubble.id) errors.push(`self-parent bubble: ${bubble.id}`);
    }
    const seen = new Set<string>();
    for (const membership of bubble.memberships) {
      if (!artifactIds.has(membership.artifact_id)) {
        errors.push(`unknown membership artifact: ${bubble.id} -> ${membership.artifact_id}`);
      }
      if (seen.has(membership.artifact_id)) {
        errors.push(`duplicate membership artifact: ${bubble.id} -> ${membership.artifact_id}`);
      }
      seen.add(membership.artifact_id);
    }
  }
  for (const field of fields) {
    if (field.parent_field_id !== null && !fieldMap.has(field.parent_field_id)) {
      errors.push(`unknown parent field: ${field.id} -> ${field.parent_field_id}`);
    }
    if (field.parent_field_id === field.id) errors.push(`self-parent field: ${field.id}`);
    for (const bubbleId of field.bubble_ids) {
      if (!bubbleMap.has(bubbleId)) errors.push(`unknown field bubble: ${field.id} -> ${bubbleId}`);
    }
  }
  for (const edge of edges) {
    if (edgeIds.has(edge.id)) errors.push(`duplicate typed edge id: ${edge.id}`);
    edgeIds.add(edge.id);
    if (!artifactIds.has(edge.from_artifact_id)) {
      errors.push(`unknown edge source artifact: ${edge.id}`);
    }
    if (!artifactIds.has(edge.to_artifact_id)) {
      errors.push(`unknown edge target artifact: ${edge.id}`);
    }
  }
  errors.push(
    ...validateAcyclicParents(
      'bubble',
      bubbles.map((bubble) => bubble.id),
      (id) => bubbleMap.get(id)?.parent_bubble_ids ?? []
    )
  );
  errors.push(
    ...validateAcyclicParents(
      'field',
      fields.map((field) => field.id),
      (id) => {
        const parent = fieldMap.get(id)?.parent_field_id;
        return parent ? [parent] : [];
      }
    )
  );
  return { ok: errors.length === 0, errors, graph_sha256: expectedHash };
}

function normalizeGoal(goal: ConceptRouteGoal): NormalizedConceptRouteGoal {
  requireId('goal id', goal.id);
  requireText('public_goal', goal.public_goal);
  const starts = uniqueSortedIds('start_artifact_ids', goal.start_artifact_ids, false);
  const targetArtifacts = uniqueSortedIds('target_artifact_ids', goal.target_artifact_ids ?? []);
  const targetBubbles = uniqueSortedIds('target_bubble_ids', goal.target_bubble_ids ?? []);
  const targetFields = uniqueSortedIds('target_field_ids', goal.target_field_ids ?? []);
  if (targetArtifacts.length + targetBubbles.length + targetFields.length === 0) {
    throw new Error('route goal needs at least one target artifact, bubble, or field');
  }
  const multipliers: Partial<Record<ConceptRelation, number>> = {};
  for (const [relation, multiplier] of Object.entries(goal.relation_multipliers ?? {})) {
    if (!CONCEPT_RELATIONS.includes(relation as ConceptRelation)) {
      throw new Error(`unknown goal relation multiplier: ${relation}`);
    }
    if (typeof multiplier !== 'number' || !Number.isFinite(multiplier) || multiplier <= 0) {
      throw new Error(`relation multiplier must be positive: ${relation}`);
    }
    multipliers[relation as ConceptRelation] = multiplier;
  }
  const policies = [...new Set(goal.allowed_policies ?? ['allow'])].sort() as ArtifactPolicy[];
  if (policies.length === 0 || policies.some((policy) => !POLICIES.includes(policy))) {
    throw new Error('allowed_policies contains an unknown policy');
  }
  const maxHops = goal.max_hops ?? 32;
  const maxExpansions = goal.max_expansions ?? 10_000;
  const bubbleHopCost = goal.bubble_hop_cost ?? 2;
  if (!Number.isInteger(maxHops) || maxHops < 0 || maxHops > MAX_ROUTE_HOPS) {
    throw new Error(`max_hops must be an integer in 0..${MAX_ROUTE_HOPS}`);
  }
  if (
    !Number.isInteger(maxExpansions) ||
    maxExpansions < 1 ||
    maxExpansions > MAX_ROUTE_EXPANSIONS
  ) {
    throw new Error(`max_expansions must be an integer in 1..${MAX_ROUTE_EXPANSIONS}`);
  }
  if (!Number.isFinite(bubbleHopCost) || bubbleHopCost <= 0) {
    throw new Error('bubble_hop_cost must be positive');
  }
  return {
    id: goal.id,
    public_goal: goal.public_goal.trim(),
    start_artifact_ids: starts,
    target_artifact_ids: targetArtifacts,
    target_bubble_ids: targetBubbles,
    target_field_ids: targetFields,
    relation_multipliers: multipliers,
    allow_bubble_hops: goal.allow_bubble_hops ?? true,
    bubble_hop_cost: bubbleHopCost,
    verified_only: goal.verified_only ?? true,
    allowed_policies: policies,
    max_hops: maxHops,
    max_expansions: maxExpansions,
  };
}

function evidenceAdmitted(status: ConceptEvidenceStatus, verifiedOnly: boolean): boolean {
  if (status === 'rejected') return false;
  if (verifiedOnly && status === 'hypothesis') return false;
  return true;
}

function descendantFieldIds(graph: ConceptFieldGraph, roots: readonly string[]): Set<string> {
  const selected = new Set(roots);
  let changed = true;
  while (changed) {
    changed = false;
    for (const field of graph.fields) {
      if (field.parent_field_id && selected.has(field.parent_field_id) && !selected.has(field.id)) {
        selected.add(field.id);
        changed = true;
      }
    }
  }
  return selected;
}

function targetArtifacts(graph: ConceptFieldGraph, goal: NormalizedConceptRouteGoal): Set<string> {
  const target = new Set(goal.target_artifact_ids);
  const bubbleIds = new Set(goal.target_bubble_ids);
  const fields = descendantFieldIds(graph, goal.target_field_ids);
  for (const field of graph.fields) {
    if (fields.has(field.id)) for (const bubbleId of field.bubble_ids) bubbleIds.add(bubbleId);
  }
  for (const bubble of graph.bubbles) {
    if (!bubbleIds.has(bubble.id)) continue;
    for (const membership of bubble.memberships) {
      if (evidenceAdmitted(membership.status, goal.verified_only)) {
        target.add(membership.artifact_id);
      }
    }
  }
  return target;
}

function bubbleAndFieldMaps(graph: ConceptFieldGraph): {
  bubblesForArtifact: Map<string, string[]>;
  fieldsForBubble: Map<string, string[]>;
} {
  const bubblesForArtifact = new Map<string, string[]>();
  for (const bubble of graph.bubbles) {
    for (const membership of bubble.memberships) {
      const rows = bubblesForArtifact.get(membership.artifact_id) ?? [];
      rows.push(bubble.id);
      bubblesForArtifact.set(membership.artifact_id, rows);
    }
  }
  for (const rows of bubblesForArtifact.values()) rows.sort();

  const fieldsForBubble = new Map<string, string[]>();
  const fieldMap = new Map(graph.fields.map((field) => [field.id, field]));
  for (const field of graph.fields) {
    for (const bubbleId of field.bubble_ids) {
      const rows = fieldsForBubble.get(bubbleId) ?? [];
      let current: TopicField | undefined = field;
      while (current) {
        if (!rows.includes(current.id)) rows.push(current.id);
        current = current.parent_field_id ? fieldMap.get(current.parent_field_id) : undefined;
      }
      fieldsForBubble.set(bubbleId, rows);
    }
  }
  for (const rows of fieldsForBubble.values()) rows.sort();
  return { bubblesForArtifact, fieldsForBubble };
}

function routeNeighbors(
  artifactId: string,
  graph: ConceptFieldGraph,
  goal: NormalizedConceptRouteGoal
): CandidateHop[] {
  const candidates: CandidateHop[] = [];
  for (const edge of graph.edges) {
    if (edge.from_artifact_id !== artifactId) continue;
    if (!evidenceAdmitted(edge.status, goal.verified_only)) continue;
    const multiplier = goal.relation_multipliers[edge.relation] ?? 1;
    candidates.push({
      kind: 'typed-edge',
      from_artifact_id: edge.from_artifact_id,
      to_artifact_id: edge.to_artifact_id,
      relation: edge.relation,
      edge_id: edge.id,
      bubble_id: null,
      authority: edge.authority,
      status: edge.status,
      evidence_hashes: edge.evidence_hashes,
      step_cost: edge.cost * multiplier,
    });
  }
  if (goal.allow_bubble_hops) {
    for (const bubble of graph.bubbles) {
      const source = bubble.memberships.find((member) => member.artifact_id === artifactId);
      if (!source || !evidenceAdmitted(source.status, goal.verified_only)) continue;
      for (const member of bubble.memberships) {
        if (member.artifact_id === artifactId) continue;
        if (!evidenceAdmitted(member.status, goal.verified_only)) continue;
        candidates.push({
          kind: 'concept-bubble',
          from_artifact_id: artifactId,
          to_artifact_id: member.artifact_id,
          relation: 'co_member',
          edge_id: null,
          bubble_id: bubble.id,
          authority:
            source.authority === member.authority ? source.authority : 'deterministic-rule',
          status:
            source.status === 'verified' && member.status === 'verified'
              ? 'verified'
              : source.status === 'source' && member.status === 'source'
                ? 'source'
                : 'hypothesis',
          evidence_hashes: [
            ...new Set([...source.evidence_hashes, ...member.evidence_hashes]),
          ].sort(),
          step_cost: goal.bubble_hop_cost,
        });
      }
    }
  }
  return candidates.sort((left, right) => {
    const leftKey = `${left.to_artifact_id}|${left.kind}|${left.edge_id ?? left.bubble_id}`;
    const rightKey = `${right.to_artifact_id}|${right.kind}|${right.edge_id ?? right.bubble_id}`;
    return leftKey.localeCompare(rightKey);
  });
}

function publicSteps(
  reasoningGraph: ReasoningArtifactGraph,
  conceptGraph: ConceptFieldGraph,
  startArtifactId: string,
  hops: readonly ConceptRouteHop[]
): PublicReasoningStep[] {
  const maps = bubbleAndFieldMaps(conceptGraph);
  const artifactIds = [startArtifactId, ...hops.map((hop) => hop.to_artifact_id)];
  return artifactIds.map((artifactId, index) => {
    const node = reasoningGraph.nodes[artifactId]!;
    const bubbleIds = maps.bubblesForArtifact.get(artifactId) ?? [];
    const fieldIds = [
      ...new Set(bubbleIds.flatMap((bubbleId) => maps.fieldsForBubble.get(bubbleId) ?? [])),
    ].sort();
    return {
      id: `step:${index}`,
      parent_step_id: index === 0 ? null : `step:${index - 1}`,
      depth: index,
      kind:
        index === 0
          ? 'anchor'
          : hops[index - 1]!.kind === 'typed-edge'
            ? 'follow-relation'
            : 'cross-bubble',
      artifact_id: artifactId,
      public_summary: node.public_summary,
      state_transition: node.state_transition,
      bubble_ids: bubbleIds,
      field_ids: fieldIds,
      evidence_hashes: node.evidence_hashes,
    };
  });
}

function finalizeRoute(body: Omit<ConceptRouteResult, 'route_sha256'>): ConceptRouteResult {
  return { ...body, route_sha256: hashReasoningValue(body) };
}

export function planConceptRoute(
  conceptGraph: ConceptFieldGraph,
  reasoningGraph: ReasoningArtifactGraph,
  routeGoal: ConceptRouteGoal
): ConceptRouteResult {
  const verification = verifyConceptFieldGraph(conceptGraph, reasoningGraph);
  if (!verification.ok)
    throw new Error(`concept field graph is invalid: ${verification.errors[0]}`);
  const goal = normalizeGoal(routeGoal);
  const artifacts = reasoningGraph.nodes;
  for (const start of goal.start_artifact_ids) {
    if (!artifacts[start]) throw new Error(`unknown start artifact: ${start}`);
  }
  const bubbleIds = new Set(conceptGraph.bubbles.map((bubble) => bubble.id));
  const fieldIds = new Set(conceptGraph.fields.map((field) => field.id));
  for (const id of goal.target_bubble_ids) {
    if (!bubbleIds.has(id)) throw new Error(`unknown target bubble: ${id}`);
  }
  for (const id of goal.target_field_ids) {
    if (!fieldIds.has(id)) throw new Error(`unknown target field: ${id}`);
  }
  for (const id of goal.target_artifact_ids) {
    if (!artifacts[id]) throw new Error(`unknown target artifact: ${id}`);
  }
  const targets = targetArtifacts(conceptGraph, goal);
  const goalSha = hashReasoningValue(goal);
  const initialReceipt = hashReasoningValue({
    goal_sha256: goalSha,
    reasoning_graph_sha256: conceptGraph.reasoning_graph_sha256,
    concept_graph_sha256: conceptGraph.graph_sha256,
  });

  const frontier: SearchState[] = [];
  for (const start of goal.start_artifact_ids) {
    if (!goal.allowed_policies.includes(artifacts[start]!.policy)) continue;
    frontier.push({
      artifact_id: start,
      start_artifact_id: start,
      cost: 0,
      hops: [],
      path: [start],
      signature: start,
    });
  }
  const best = new Map<string, { cost: number; signature: string }>();
  let expanded = 0;
  let reached: SearchState | null = null;

  while (frontier.length > 0 && expanded < goal.max_expansions) {
    frontier.sort(
      (left, right) => left.cost - right.cost || left.signature.localeCompare(right.signature)
    );
    const current = frontier.shift()!;
    const known = best.get(current.artifact_id);
    if (
      known &&
      (current.cost > known.cost ||
        (Math.abs(current.cost - known.cost) < 1e-12 && current.signature >= known.signature))
    ) {
      continue;
    }
    best.set(current.artifact_id, { cost: current.cost, signature: current.signature });
    expanded += 1;
    if (targets.has(current.artifact_id)) {
      reached = current;
      break;
    }
    if (current.hops.length >= goal.max_hops) continue;

    for (const candidate of routeNeighbors(current.artifact_id, conceptGraph, goal)) {
      const target = artifacts[candidate.to_artifact_id];
      if (!target || !goal.allowed_policies.includes(target.policy)) continue;
      if (current.path.includes(candidate.to_artifact_id)) continue;
      const nextCost = current.cost + candidate.step_cost;
      const signature = `${current.signature}>${candidate.to_artifact_id}:${candidate.edge_id ?? candidate.bubble_id}`;
      const prior = best.get(candidate.to_artifact_id);
      if (
        prior &&
        (nextCost > prior.cost ||
          (Math.abs(nextCost - prior.cost) < 1e-12 && signature >= prior.signature))
      ) {
        continue;
      }
      frontier.push({
        artifact_id: candidate.to_artifact_id,
        start_artifact_id: current.start_artifact_id,
        cost: nextCost,
        hops: [...current.hops, candidate],
        path: [...current.path, candidate.to_artifact_id],
        signature,
      });
    }
  }

  if (!reached) {
    return finalizeRoute({
      schema_version: 'scbe.concept_route.v1',
      route_id: goal.id,
      status: 'no-route',
      rejection_code: 'E_NO_ROUTE',
      goal,
      goal_sha256: goalSha,
      reasoning_graph_sha256: conceptGraph.reasoning_graph_sha256,
      concept_graph_sha256: conceptGraph.graph_sha256,
      selected_start_artifact_id: null,
      target_artifact_id: null,
      artifact_path: [],
      hops: [],
      public_steps: [],
      total_cost: null,
      expanded_states: expanded,
    });
  }

  let previousReceipt = initialReceipt;
  let cumulative = 0;
  const hops: ConceptRouteHop[] = reached.hops.map((candidate, index) => {
    cumulative += candidate.step_cost;
    const body = {
      index,
      kind: candidate.kind,
      from_artifact_id: candidate.from_artifact_id,
      to_artifact_id: candidate.to_artifact_id,
      relation: candidate.relation,
      edge_id: candidate.edge_id,
      bubble_id: candidate.bubble_id,
      authority: candidate.authority,
      status: candidate.status,
      evidence_hashes: candidate.evidence_hashes,
      step_cost: candidate.step_cost,
      cumulative_cost: cumulative,
      previous_receipt_sha256: previousReceipt,
    };
    const hop = { ...body, receipt_sha256: hashReasoningValue(body) };
    previousReceipt = hop.receipt_sha256;
    return hop;
  });
  const steps = publicSteps(reasoningGraph, conceptGraph, reached.start_artifact_id, hops);
  return finalizeRoute({
    schema_version: 'scbe.concept_route.v1',
    route_id: goal.id,
    status: 'reached',
    rejection_code: null,
    goal,
    goal_sha256: goalSha,
    reasoning_graph_sha256: conceptGraph.reasoning_graph_sha256,
    concept_graph_sha256: conceptGraph.graph_sha256,
    selected_start_artifact_id: reached.start_artifact_id,
    target_artifact_id: reached.artifact_id,
    artifact_path: reached.path,
    hops,
    public_steps: steps,
    total_cost: reached.cost,
    expanded_states: expanded,
  });
}

export function verifyConceptRoute(
  route: ConceptRouteResult,
  conceptGraph: ConceptFieldGraph,
  reasoningGraph: ReasoningArtifactGraph
): { ok: boolean; errors: string[] } {
  const errors: string[] = [];
  if (route.schema_version !== 'scbe.concept_route.v1') errors.push('unsupported route schema');
  if (route.reasoning_graph_sha256 !== conceptGraph.reasoning_graph_sha256) {
    errors.push('route reasoning graph hash mismatch');
  }
  if (route.concept_graph_sha256 !== conceptGraph.graph_sha256) {
    errors.push('route concept graph hash mismatch');
  }
  const expectedHash = hashReasoningValue(routeBody(route));
  if (route.route_sha256 !== expectedHash) errors.push('route hash mismatch');
  try {
    const replanned = planConceptRoute(conceptGraph, reasoningGraph, route.goal);
    if (replanned.route_sha256 !== route.route_sha256) errors.push('route replay mismatch');
  } catch (error) {
    errors.push(`route replay failed: ${error instanceof Error ? error.message : String(error)}`);
  }
  return { ok: errors.length === 0, errors };
}
