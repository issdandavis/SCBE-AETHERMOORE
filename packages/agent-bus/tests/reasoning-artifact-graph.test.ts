import { describe, expect, it } from 'vitest';
import { decode, encode, TONGUE_CODES } from '../../../src/tokenizer/ss1.js';
import {
  appendReasoningArtifact,
  backtrackReasoningGraph,
  computeTubalBranchTelemetry,
  createReasoningArtifactGraph,
  forkReasoningArtifact,
  hashReasoningBytes,
  hashReasoningValue,
  mergeReasoningArtifacts,
  verifyReasoningArtifactGraph,
  type ArtifactPolicy,
  type BijectiveViewCodec,
  type ReasoningArtifactGraph,
  type ReasoningArtifactInput,
  type ReasoningTongue,
  type TypedEquivalenceReceipt,
} from '../src/index.js';

const textEncoder = new TextEncoder();

const sacredTongueCodec: BijectiveViewCodec = {
  encode(tongue, canonical) {
    const spell = encode(canonical, tongue, false);
    return spell.length ? spell.split(/\s+/) : [];
  },
  decode(tongue, tokens) {
    return decode(tokens.join(' '), tongue);
  },
};

function bytes(value: string): Uint8Array {
  return textEncoder.encode(value);
}

function receiptHash(label: string): string {
  return hashReasoningValue({ fixture: label });
}

function artifact(
  id: string,
  parentIds: readonly string[] = [],
  overrides: Partial<ReasoningArtifactInput> = {}
): ReasoningArtifactInput {
  return {
    id,
    parent_ids: parentIds,
    tongue: 'KO',
    canonical_bytes: bytes(`canonical:${id}`),
    public_summary: `public summary for ${id}`,
    state_transition: `state moved to ${id}`,
    syntax_tokens: ['state', id],
    feature_values: [0.25, 0.5, 0.75],
    policy: 'allow',
    evidence_hashes: [receiptHash(`evidence:${id}`)],
    provenance_hashes: [receiptHash(`provenance:${id}`)],
    ...overrides,
  };
}

function rootGraph(): ReasoningArtifactGraph {
  return appendReasoningArtifact(
    createReasoningArtifactGraph('fixture-graph', ['risk', 'confidence', 'cost']),
    artifact('root'),
    sacredTongueCodec
  );
}

function exactBranches(
  policies: [ArtifactPolicy, ArtifactPolicy] = ['allow', 'allow']
): ReasoningArtifactGraph {
  const canonical = bytes('shared canonical result');
  let graph = rootGraph();
  graph = forkReasoningArtifact(
    graph,
    {
      ...artifact('left', [], {
        tongue: 'AV',
        canonical_bytes: canonical,
        syntax_tokens: ['load', 'left', 'verify'],
        policy: policies[0],
      }),
      parent_id: 'root',
    },
    sacredTongueCodec
  );
  graph = forkReasoningArtifact(
    graph,
    {
      ...artifact('right', [], {
        tongue: 'RU',
        canonical_bytes: canonical,
        syntax_tokens: ['load', 'right', 'verify'],
        policy: policies[1],
      }),
      parent_id: 'root',
    },
    sacredTongueCodec
  );
  return graph;
}

function divergentBranches(): ReasoningArtifactGraph {
  let graph = rootGraph();
  graph = forkReasoningArtifact(
    graph,
    {
      ...artifact('left', [], {
        tongue: 'CA',
        canonical_bytes: bytes('left program output'),
        feature_values: [0.5, 0.8, 0.2],
      }),
      parent_id: 'root',
    },
    sacredTongueCodec
  );
  graph = forkReasoningArtifact(
    graph,
    {
      ...artifact('right', [], {
        tongue: 'UM',
        canonical_bytes: bytes('right program output'),
        feature_values: [0.5, 0.8, 0.2],
      }),
      parent_id: 'root',
    },
    sacredTongueCodec
  );
  return graph;
}

describe('canonical Sacred Tongue adapter', () => {
  it('round-trips all 256 byte values in all six canonical TypeScript tongues', () => {
    const canonical = Uint8Array.from({ length: 256 }, (_, index) => index);
    for (const tongue of TONGUE_CODES) {
      const tokens = sacredTongueCodec.encode(tongue, canonical);
      const decoded = sacredTongueCodec.decode(tongue, tokens);
      expect(Buffer.from(decoded).equals(Buffer.from(canonical))).toBe(true);
      expect(tokens).toHaveLength(256);
    }
  });

  it('refuses a codec that changes even one canonical byte', () => {
    const broken: BijectiveViewCodec = {
      encode: sacredTongueCodec.encode,
      decode(tongue, tokens) {
        const decoded = sacredTongueCodec.decode(tongue, tokens);
        decoded[0] = decoded[0]! ^ 1;
        return decoded;
      },
    };
    expect(() =>
      appendReasoningArtifact(
        createReasoningArtifactGraph('broken-codec', ['risk']),
        artifact('root', [], { feature_values: [0.1] }),
        broken
      )
    ).toThrow(/round trip changed canonical bytes/);
  });

  it('bounds canonical artifacts and expanded codec views', () => {
    expect(() =>
      appendReasoningArtifact(
        createReasoningArtifactGraph('oversized-canonical', ['risk']),
        artifact('root', [], {
          canonical_bytes: new Uint8Array(64 * 1024 + 1),
          feature_values: [0.1],
        }),
        sacredTongueCodec
      )
    ).toThrow(/canonical_bytes must contain/);

    const inflated: BijectiveViewCodec = {
      encode: () => Array.from({ length: 3000 }, () => 'x'.repeat(512)),
      decode: (_tongue, _tokens) => bytes('canonical:root'),
    };
    expect(() =>
      appendReasoningArtifact(
        createReasoningArtifactGraph('inflated-view', ['risk', 'confidence', 'cost']),
        artifact('root'),
        inflated
      )
    ).toThrow(/storage budget/);
  });
});

describe('reasoning artifact graph', () => {
  it('records parallel forks and an exact canonical merge as a verified DAG', () => {
    const branches = exactBranches();
    const canonical = bytes('shared canonical result');
    const merged = mergeReasoningArtifacts(
      branches,
      artifact('joined', ['left', 'right'], {
        tongue: 'DR',
        canonical_bytes: canonical,
        syntax_tokens: ['load', 'shared', 'verify'],
      }),
      sacredTongueCodec
    );

    expect(branches.head_ids).toEqual(['left', 'right']);
    expect(merged.head_ids).toEqual(['joined']);
    expect(merged.nodes.joined!.merge_authority).toEqual({ kind: 'exact-canonical' });
    expect(merged.nodes.joined!.parent_ids).toEqual(['left', 'right']);
    expect(verifyReasoningArtifactGraph(merged, { codec: sacredTongueCodec })).toMatchObject({
      ok: true,
      errors: [],
    });
  });

  it('records deterministic syntax changes against each parent', () => {
    let graph = appendReasoningArtifact(
      createReasoningArtifactGraph('syntax-diff', ['risk']),
      artifact('root', [], { syntax_tokens: ['load', 'x'], feature_values: [0] }),
      sacredTongueCodec
    );
    graph = appendReasoningArtifact(
      graph,
      artifact('next', ['root'], {
        syntax_tokens: ['load', 'y', 'verify'],
        feature_values: [0.1],
      }),
      sacredTongueCodec
    );

    expect(graph.nodes.next!.syntax_deltas[0]).toMatchObject({
      parent_id: 'root',
      common_prefix_tokens: 1,
      common_suffix_tokens: 0,
      removed_tokens: ['x'],
      added_tokens: ['y', 'verify'],
    });
  });

  it('requires an explicit fork when branching from a historical checkpoint', () => {
    let graph = rootGraph();
    graph = appendReasoningArtifact(graph, artifact('next', ['root']), sacredTongueCodec);
    expect(() =>
      appendReasoningArtifact(graph, artifact('implicit-branch', ['root']), sacredTongueCodec)
    ).toThrow(/explicit fork/);
    expect(() =>
      forkReasoningArtifact(
        graph,
        { ...artifact('explicit-branch'), parent_id: 'root' },
        sacredTongueCodec
      )
    ).not.toThrow();
  });

  it.each<ArtifactPolicy>(['deny', 'quarantine', 'adversarial'])(
    'blocks a merge when a branch policy is %s',
    (policy) => {
      const graph = exactBranches(['allow', policy]);
      expect(() =>
        mergeReasoningArtifacts(
          graph,
          artifact('joined', ['left', 'right'], {
            canonical_bytes: bytes('shared canonical result'),
          }),
          sacredTongueCodec
        )
      ).toThrow(/policy blocks merge/);
    }
  );

  it('does not treat identical geometry as semantic merge authority', () => {
    const graph = divergentBranches();
    const telemetry = computeTubalBranchTelemetry(graph);
    expect(telemetry.mean_head_separation).toBe(0);
    expect(telemetry.convergence_degree).toBe(1);
    expect(() =>
      mergeReasoningArtifacts(
        graph,
        artifact('joined', ['left', 'right'], {
          canonical_bytes: bytes('left program output'),
          feature_values: [0.5, 0.8, 0.2],
        }),
        sacredTongueCodec
      )
    ).toThrow(/geometry or similarity cannot authorize/);
  });

  it('accepts a non-exact merge only through a bound external equivalence receipt', () => {
    const graph = divergentBranches();
    const output = bytes('verified common behavior');
    const evidence = receiptHash('executed typed equivalence');
    const receipt: TypedEquivalenceReceipt = {
      schema_version: 'scbe.reasoning_typed_equivalence.v1',
      verifier_id: 'fixture-executable-equivalence',
      verifier_sha256: receiptHash('verifier source'),
      parent_canonical_sha256: [
        graph.nodes.left!.canonical_bytes_sha256,
        graph.nodes.right!.canonical_bytes_sha256,
      ].sort(),
      output_canonical_sha256: hashReasoningBytes(output),
      evidence_sha256: evidence,
      passed: true,
    };
    const verify = (candidate: TypedEquivalenceReceipt) =>
      candidate.verifier_id === 'fixture-executable-equivalence';
    const merged = mergeReasoningArtifacts(
      graph,
      artifact('joined', ['left', 'right'], {
        canonical_bytes: output,
        evidence_hashes: [evidence],
      }),
      sacredTongueCodec,
      { equivalence_receipt: receipt, verify_equivalence: verify }
    );

    expect(merged.nodes.joined!.merge_authority?.kind).toBe('typed-equivalence');
    expect(
      verifyReasoningArtifactGraph(merged, {
        codec: sacredTongueCodec,
        verify_equivalence: verify,
        require_equivalence_reverification: true,
      }).ok
    ).toBe(true);
    expect(
      verifyReasoningArtifactGraph(merged, { require_equivalence_reverification: true }).errors
    ).toContain('typed equivalence verifier unavailable: joined');
  });

  it('rejects a claimed equivalence when the external verifier refuses it', () => {
    const graph = divergentBranches();
    const output = bytes('unverified common behavior');
    const evidence = receiptHash('untrusted equivalence');
    const receipt: TypedEquivalenceReceipt = {
      schema_version: 'scbe.reasoning_typed_equivalence.v1',
      verifier_id: 'refused-verifier',
      verifier_sha256: receiptHash('refused verifier source'),
      parent_canonical_sha256: [
        graph.nodes.left!.canonical_bytes_sha256,
        graph.nodes.right!.canonical_bytes_sha256,
      ].sort(),
      output_canonical_sha256: hashReasoningBytes(output),
      evidence_sha256: evidence,
      passed: true,
    };
    expect(() =>
      mergeReasoningArtifacts(
        graph,
        artifact('joined', ['left', 'right'], {
          canonical_bytes: output,
          evidence_hashes: [evidence],
        }),
        sacredTongueCodec,
        { equivalence_receipt: receipt, verify_equivalence: () => false }
      )
    ).toThrow(/not accepted by an external verifier/);
  });

  it('backtracks by moving the head while retaining immutable later nodes', () => {
    let graph = rootGraph();
    graph = appendReasoningArtifact(graph, artifact('a', ['root']), sacredTongueCodec);
    graph = appendReasoningArtifact(graph, artifact('b', ['a']), sacredTongueCodec);
    const beforeNodeHashes = Object.fromEntries(
      Object.entries(graph.nodes).map(([id, node]) => [id, node.node_sha256])
    );
    graph = backtrackReasoningGraph(graph, 'root', 'public fixture rollback');

    expect(graph.head_ids).toEqual(['root']);
    expect(Object.keys(graph.nodes).sort()).toEqual(['a', 'b', 'root']);
    expect(
      Object.fromEntries(Object.entries(graph.nodes).map(([id, node]) => [id, node.node_sha256]))
    ).toEqual(beforeNodeHashes);
    expect(computeTubalBranchTelemetry(graph).backtrack_count).toBe(1);
    expect(verifyReasoningArtifactGraph(graph).ok).toBe(true);
  });

  it('detects node and event tampering after JSON serialization', () => {
    const graph = exactBranches();
    const nodeTamper = JSON.parse(JSON.stringify(graph)) as ReasoningArtifactGraph;
    nodeTamper.nodes.left!.public_summary = 'silently replaced';
    expect(verifyReasoningArtifactGraph(nodeTamper).errors).toContain('node hash mismatch: left');

    const eventTamper = JSON.parse(JSON.stringify(graph)) as ReasoningArtifactGraph;
    eventTamper.events[1]!.head_ids = ['invented'];
    const errors = verifyReasoningArtifactGraph(eventTamper).errors;
    expect(errors).toContain('event hash mismatch: 1');
    expect(errors).toContain('event head mismatch: 1');
  });

  it('rejects hash-consistent but malformed public artifacts', () => {
    const graph = exactBranches();
    const malformed = JSON.parse(JSON.stringify(graph)) as ReasoningArtifactGraph;
    const node = malformed.nodes.left!;
    node.public_summary = '   ';
    const { node_sha256: _oldHash, ...body } = node;
    node.node_sha256 = hashReasoningValue(body);

    expect(verifyReasoningArtifactGraph(malformed).errors).toContain(
      'invalid public artifact text: left'
    );
  });
});

describe('branch x feature x time telemetry', () => {
  function telemetryGraph(rightFeatures: readonly number[]): ReasoningArtifactGraph {
    let graph = appendReasoningArtifact(
      createReasoningArtifactGraph('telemetry', ['risk', 'confidence']),
      artifact('root', [], {
        canonical_bytes: bytes('shared root'),
        feature_values: [0, 0],
      }),
      sacredTongueCodec
    );
    graph = forkReasoningArtifact(
      graph,
      {
        ...artifact('left', [], {
          canonical_bytes: bytes('left'),
          feature_values: [1, 1],
        }),
        parent_id: 'root',
      },
      sacredTongueCodec
    );
    return forkReasoningArtifact(
      graph,
      {
        ...artifact('right', [], {
          canonical_bytes: bytes('right'),
          feature_values: rightFeatures,
        }),
        parent_id: 'root',
      },
      sacredTongueCodec
    );
  }

  it('reports perfect geometric convergence for identical public feature tubes', () => {
    const telemetry = computeTubalBranchTelemetry(telemetryGraph([1, 1]));
    expect(telemetry.tensor_shape).toEqual([2, 2, 2]);
    expect(telemetry.mean_head_separation).toBe(0);
    expect(telemetry.centroid_residual).toBe(0);
    expect(telemetry.convergence_degree).toBe(1);
    expect(telemetry.phase_coherence).toBeCloseTo(1, 12);
    expect(telemetry.spectral_mode_energy).toHaveLength(2);
    expect(telemetry.authority).toBe('telemetry-only-not-merge-authority');
  });

  it('shows greater separation and lower convergence for divergent branch heads', () => {
    const same = computeTubalBranchTelemetry(telemetryGraph([1, 1]));
    const different = computeTubalBranchTelemetry(telemetryGraph([4, -2]));
    expect(different.mean_head_separation).toBeGreaterThan(same.mean_head_separation);
    expect(different.centroid_residual).toBeGreaterThan(same.centroid_residual);
    expect(different.convergence_degree).toBeLessThan(same.convergence_degree);
    expect(different.non_dc_energy).toBeGreaterThan(0);
  });

  it('counts held policy states in global telemetry', () => {
    let graph = telemetryGraph([1, 1]);
    graph = {
      ...graph,
      nodes: {
        ...graph.nodes,
        right: { ...graph.nodes.right!, policy: 'quarantine' },
      },
    };
    // The direct mutation invalidates the node hash, so the telemetry refuses it.
    expect(() => computeTubalBranchTelemetry(graph)).toThrow(/invalid graph/);

    const governed = exactBranches(['allow', 'quarantine']);
    const telemetry = computeTubalBranchTelemetry(governed);
    expect(telemetry.head_policy_counts.quarantine).toBe(1);
    expect(telemetry.unresolved_head_ids).toEqual(['right']);
  });
});
