import { describe, expect, it } from 'vitest';
import {
  appendReasoningArtifact,
  createConceptFieldGraph,
  createReasoningArtifactGraph,
  hashReasoningValue,
  planConceptRoute,
  verifyConceptFieldGraph,
  verifyConceptRoute,
  type BijectiveViewCodec,
  type ConceptBubble,
  type ConceptFieldGraph,
  type ReasoningArtifactGraph,
  type TopicField,
  type TypedConceptEdge,
} from '../src/index.js';

const encoder = new TextEncoder();

const exactFixtureCodec: BijectiveViewCodec = {
  encode(tongue, canonical) {
    return Array.from(canonical, (value) => `${tongue}:${value.toString(16).padStart(2, '0')}`);
  },
  decode(tongue, tokens) {
    return Uint8Array.from(
      tokens.map((token) => {
        const prefix = `${tongue}:`;
        if (!token.startsWith(prefix)) throw new Error('wrong fixture tongue');
        return Number.parseInt(token.slice(prefix.length), 16);
      })
    );
  },
};

function receipt(label: string): string {
  return hashReasoningValue({ fixture: label });
}

function reasoningFixture(): ReasoningArtifactGraph {
  const rows = [
    ['root', 'Frame the public goal.'],
    ['claim', 'State the identity claim.'],
    ['example', 'Show the welcomed guest example.'],
    ['explanation', 'Explain why clutter becomes comfort.'],
    ['counterpoint', 'Inspect the outsider judgment.'],
    ['conclusion', 'Return the evidence to the identity claim.'],
    ['isolated', 'Keep one valid but unlinked source record.'],
  ] as const;
  let graph = createReasoningArtifactGraph('concept-route-fixture', ['confidence', 'cost']);
  for (const [index, [id, summary]] of rows.entries()) {
    graph = appendReasoningArtifact(
      graph,
      {
        id,
        parent_ids: index === 0 ? [] : [rows[index - 1]![0]],
        tongue: 'KO',
        canonical_bytes: encoder.encode(`source:${id}`),
        public_summary: summary,
        state_transition: `public state now includes ${id}`,
        syntax_tokens: ['source', id],
        feature_values: [1 - index / 10, index + 1],
        policy: 'allow',
        evidence_hashes: [receipt(`evidence:${id}`)],
        provenance_hashes: [receipt(`provenance:${id}`)],
      },
      exactFixtureCodec
    );
  }
  return graph;
}

function member(artifact_id: string) {
  return {
    artifact_id,
    weight: 1,
    authority: 'source-annotation' as const,
    status: 'source' as const,
    evidence_hashes: [receipt(`membership:${artifact_id}`)],
  };
}

function bubble(id: string, label: string, artifacts: string[]): ConceptBubble {
  return {
    schema_version: 'scbe.concept_bubble.v1',
    id,
    label,
    parent_bubble_ids: [],
    memberships: artifacts.map(member),
    provenance_hashes: [receipt(`bubble:${id}`)],
  };
}

function field(
  id: string,
  label: string,
  bubble_ids: string[],
  parent_field_id: string | null = null
): TopicField {
  return {
    schema_version: 'scbe.topic_field.v1',
    id,
    label,
    parent_field_id,
    bubble_ids,
    provenance_hashes: [receipt(`field:${id}`)],
  };
}

function edge(
  id: string,
  from_artifact_id: string,
  to_artifact_id: string,
  relation: TypedConceptEdge['relation'],
  options: Partial<Pick<TypedConceptEdge, 'cost' | 'authority' | 'status'>> = {}
): TypedConceptEdge {
  return {
    schema_version: 'scbe.typed_concept_edge.v1',
    id,
    from_artifact_id,
    to_artifact_id,
    relation,
    cost: options.cost ?? 1,
    authority: options.authority ?? 'source-annotation',
    status: options.status ?? 'source',
    evidence_hashes: [receipt(`edge:${id}`)],
  };
}

function conceptFixture(reasoning: ReasoningArtifactGraph): ConceptFieldGraph {
  return createConceptFieldGraph('nested-concepts', reasoning, {
    bubbles: [
      bubble('identity', 'Identity', ['claim', 'conclusion']),
      bubble('hospitality', 'Hospitality', ['example', 'explanation']),
      bubble('judgment', 'Outsider judgment', ['claim', 'counterpoint']),
      bubble('resolution', 'Resolution', ['conclusion']),
    ],
    fields: [
      field('essay', 'Whole essay', []),
      field('argument', 'Identity and judgment', ['identity', 'judgment'], 'essay'),
      field('home', 'Home and hospitality', ['hospitality', 'identity'], 'essay'),
      field('ending', 'Return and resolution', ['resolution'], 'essay'),
    ],
    edges: [
      edge('e-root-claim', 'root', 'claim', 'enables'),
      edge('e-claim-example', 'claim', 'example', 'requires'),
      edge('e-example-explanation', 'example', 'explanation', 'supports'),
      edge('e-explanation-conclusion', 'explanation', 'conclusion', 'returns_to'),
      edge('e-claim-counterpoint', 'claim', 'counterpoint', 'contradicts'),
      edge('e-counterpoint-conclusion', 'counterpoint', 'conclusion', 'explains'),
      edge('e-hypothesis-shortcut', 'root', 'conclusion', 'same_source', {
        cost: 0.1,
        authority: 'model-proposal',
        status: 'hypothesis',
      }),
    ],
  });
}

describe('nested concept fields', () => {
  it('keeps overlapping concept memberships and nested fields explicit', () => {
    const reasoning = reasoningFixture();
    const graph = conceptFixture(reasoning);
    const claimBubbles = graph.bubbles
      .filter((candidate) => candidate.memberships.some((row) => row.artifact_id === 'claim'))
      .map((candidate) => candidate.id)
      .sort();

    expect(claimBubbles).toEqual(['identity', 'judgment']);
    expect(graph.fields.find((candidate) => candidate.id === 'home')?.bubble_ids).toContain(
      'identity'
    );
    expect(verifyConceptFieldGraph(graph, reasoning)).toMatchObject({ ok: true, errors: [] });
  });

  it('changes a route when the public goal changes relation costs', () => {
    const reasoning = reasoningFixture();
    const graph = conceptFixture(reasoning);
    const common = {
      start_artifact_ids: ['root'],
      target_artifact_ids: ['conclusion'],
      allow_bubble_hops: false,
      verified_only: true,
    };
    const explanatory = planConceptRoute(graph, reasoning, {
      ...common,
      id: 'explain-route',
      public_goal: 'Build the example and explanation before returning to the claim.',
      relation_multipliers: { contradicts: 10 },
    });
    const challenging = planConceptRoute(graph, reasoning, {
      ...common,
      id: 'challenge-route',
      public_goal: 'Inspect the counterpoint before returning to the claim.',
      relation_multipliers: { requires: 10, supports: 10, returns_to: 10, contradicts: 0.5 },
    });

    expect(explanatory.artifact_path).toEqual([
      'root',
      'claim',
      'example',
      'explanation',
      'conclusion',
    ]);
    expect(challenging.artifact_path).toEqual(['root', 'claim', 'counterpoint', 'conclusion']);
    expect(explanatory.public_steps.map((step) => step.depth)).toEqual([0, 1, 2, 3, 4]);
    expect(explanatory.public_steps[2]?.bubble_ids).toContain('hospitality');
  });

  it('uses a bubble as an overlapping hyperedge when the goal permits it', () => {
    const reasoning = reasoningFixture();
    const graph = conceptFixture(reasoning);
    const route = planConceptRoute(graph, reasoning, {
      id: 'bubble-crossing',
      public_goal: 'Move from the identity claim to its matching conclusion.',
      start_artifact_ids: ['claim'],
      target_artifact_ids: ['conclusion'],
      allow_bubble_hops: true,
      bubble_hop_cost: 0.25,
      verified_only: true,
    });

    expect(route.artifact_path).toEqual(['claim', 'conclusion']);
    expect(route.hops[0]).toMatchObject({
      kind: 'concept-bubble',
      bubble_id: 'identity',
      relation: 'co_member',
      status: 'source',
    });
  });

  it('does not let a cheap model hypothesis enter a source-only route', () => {
    const reasoning = reasoningFixture();
    const graph = conceptFixture(reasoning);
    const strict = planConceptRoute(graph, reasoning, {
      id: 'strict',
      public_goal: 'Reach the conclusion using source-backed relations.',
      start_artifact_ids: ['root'],
      target_artifact_ids: ['conclusion'],
      allow_bubble_hops: false,
      verified_only: true,
    });
    const exploratory = planConceptRoute(graph, reasoning, {
      id: 'explore',
      public_goal: 'Include model-proposed relations while exploring.',
      start_artifact_ids: ['root'],
      target_artifact_ids: ['conclusion'],
      allow_bubble_hops: false,
      verified_only: false,
    });

    expect(strict.artifact_path).toEqual(['root', 'claim', 'counterpoint', 'conclusion']);
    expect(exploratory.artifact_path).toEqual(['root', 'conclusion']);
    expect(exploratory.hops[0]?.status).toBe('hypothesis');
  });

  it('returns a stable refusal instead of inventing a bridge', () => {
    const reasoning = reasoningFixture();
    const graph = conceptFixture(reasoning);
    const first = planConceptRoute(graph, reasoning, {
      id: 'unreachable',
      public_goal: 'Reach the isolated source record.',
      start_artifact_ids: ['root'],
      target_artifact_ids: ['isolated'],
      allow_bubble_hops: false,
      verified_only: true,
    });
    const second = planConceptRoute(graph, reasoning, first.goal);

    expect(first).toMatchObject({
      status: 'no-route',
      rejection_code: 'E_NO_ROUTE',
      artifact_path: [],
    });
    expect(second.route_sha256).toBe(first.route_sha256);
    expect(verifyConceptRoute(first, graph, reasoning)).toEqual({ ok: true, errors: [] });
  });

  it('replays receipts exactly and detects route or graph tampering', () => {
    const reasoning = reasoningFixture();
    const graph = conceptFixture(reasoning);
    const route = planConceptRoute(graph, reasoning, {
      id: 'replay',
      public_goal: 'Reach hospitality evidence.',
      start_artifact_ids: ['root'],
      target_bubble_ids: ['hospitality'],
      allow_bubble_hops: false,
      verified_only: true,
    });
    const replay = planConceptRoute(graph, reasoning, route.goal);
    expect(replay.route_sha256).toBe(route.route_sha256);
    expect(verifyConceptRoute(route, graph, reasoning)).toEqual({ ok: true, errors: [] });

    const routeTamper = structuredClone(route);
    routeTamper.hops[0]!.to_artifact_id = 'counterpoint';
    expect(verifyConceptRoute(routeTamper, graph, reasoning).errors).toContain(
      'route hash mismatch'
    );

    const graphTamper = structuredClone(graph);
    graphTamper.edges[0]!.cost = 99;
    expect(verifyConceptFieldGraph(graphTamper, reasoning).errors).toContain(
      'concept field graph hash mismatch'
    );
  });

  it('rejects malformed values even when an attacker recomputes the graph hash', () => {
    const reasoning = reasoningFixture();
    const graph = conceptFixture(reasoning);
    const malformed = structuredClone(graph);
    malformed.bubbles[0]!.memberships[0]!.weight = 2;
    const { graph_sha256: _oldHash, ...body } = malformed;
    malformed.graph_sha256 = hashReasoningValue(body);

    const verification = verifyConceptFieldGraph(malformed, reasoning);
    expect(verification.ok).toBe(false);
    expect(verification.errors).toContain(
      'invalid concept bubble: membership weight must be in (0, 1]'
    );
    expect(verification.errors).not.toContain('concept field graph hash mismatch');
  });

  it('returns an error instead of throwing on a malformed runtime object', () => {
    const reasoning = reasoningFixture();
    const malformed = structuredClone(conceptFixture(reasoning)) as unknown as {
      bubbles: Array<ConceptBubble | null>;
    };
    malformed.bubbles[0] = null;

    let verification: ReturnType<typeof verifyConceptFieldGraph> | undefined;
    expect(() => {
      verification = verifyConceptFieldGraph(malformed as unknown as ConceptFieldGraph, reasoning);
    }).not.toThrow();
    expect(verification?.errors.some((error) => error.startsWith('invalid concept bubble:'))).toBe(
      true
    );
  });

  it('refuses cyclic topic hierarchies', () => {
    const reasoning = reasoningFixture();
    expect(() =>
      createConceptFieldGraph('cycle', reasoning, {
        bubbles: [bubble('identity', 'Identity', ['claim'])],
        fields: [field('one', 'One', ['identity'], 'two'), field('two', 'Two', [], 'one')],
        edges: [],
      })
    ).toThrow(/field parent cycle/);
  });
});
