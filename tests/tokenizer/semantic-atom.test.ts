import { describe, expect, it } from 'vitest';
import {
  buildSemanticLedgerEntry,
  buildSemanticWorkflowThread,
  embedSemanticAtom,
  getSemanticAtom,
  tokenizeSemanticAtoms,
} from '../../src/tokenizer/semantic-atom.js';

describe('semantic atom tokenizer', () => {
  it('defines flow as a stable nucleus with code and natural orbitals', () => {
    const flow = getSemanticAtom('FLOW');

    expect(flow?.nucleus.invariants).toEqual([
      'direction',
      'continuity',
      'path',
      'state_transition',
    ]);
    expect(flow?.orbitals.map((orbital) => orbital.domain)).toContain('code');
    expect(flow?.orbitals.map((orbital) => orbital.domain)).toContain('natural');
    expect(flow?.codeRelations.blockers).toContain('type error');
    expect(flow?.codeRelations.patterns).toContain('input -> function -> output');
  });

  it('keeps water and flow related without collapsing them into the same atom', () => {
    const water = getSemanticAtom('WATER');
    const flow = getSemanticAtom('FLOW');

    expect(water?.semanticId).toBe('WATER');
    expect(flow?.semanticId).toBe('FLOW');
    expect(water?.bonds).toContainEqual(
      expect.objectContaining({ kind: 'enables', target: 'FLOW', domain: 'natural' })
    );
    expect(water?.codeRelations.analogies).toContain('filter:water :: validator:input_stream');
  });

  it('tokenizes plain language into semantic atoms with relation trees and embeddings', () => {
    const tokens = tokenizeSemanticAtoms('A type error blocks data flow in the pipeline.', 'AV');

    expect(tokens.map((token) => token.semanticId)).toEqual(
      expect.arrayContaining(['BLOCK', 'FLOW'])
    );
    const block = tokens.find((token) => token.semanticId === 'BLOCK');
    const flow = tokens.find((token) => token.semanticId === 'FLOW');

    expect(block?.relationTree.near).toContain('BOUNDARY');
    expect(block?.relationTree.blockers).toContain('DISPATCH');
    expect(flow?.relationTree.blockers).toContain('BLOCK');
    expect(flow?.embedding).toHaveLength(12);
    expect(flow?.embedding[11]).toBeCloseTo(0.2, 10);
  });

  it('maps the same semantic bucket across tongues while preserving tongue-specific embedding lane', () => {
    const koFlow = tokenizeSemanticAtoms('control flow', 'KO').find(
      (token) => token.semanticId === 'FLOW'
    );
    const avFlow = tokenizeSemanticAtoms('control flow', 'AV').find(
      (token) => token.semanticId === 'FLOW'
    );

    expect(koFlow?.bucketId).toBe(avFlow?.bucketId);
    expect(koFlow?.embedding.slice(0, 11)).toEqual(avFlow?.embedding.slice(0, 11));
    expect(koFlow?.embedding[11]).not.toBe(avFlow?.embedding[11]);
  });

  it('builds a ledger entry that preserves original input and selected semantic changes', () => {
    const input = 'Water can flow, but a failed test blocks deploy.';
    const tokens = tokenizeSemanticAtoms(input, 'RU');
    const ledger = buildSemanticLedgerEntry(input, tokens);

    expect(ledger.originalInput).toBe(input);
    expect(ledger.normalizedInput).toBe('water can flow, but a failed test blocks deploy.');
    expect(ledger.tokenCount).toBeGreaterThanOrEqual(3);
    expect(ledger.tokens.map((token) => token.semanticId)).toEqual(
      expect.arrayContaining(['WATER', 'FLOW', 'BLOCK'])
    );
    expect(ledger.inputHash).toMatch(/^[a-f0-9]{64}$/);
  });

  it('uses deterministic embeddings for the same atom and tongue', () => {
    const block = getSemanticAtom('BLOCK');
    expect(block).toBeDefined();

    const first = embedSemanticAtom(block!, 'DR');
    const second = embedSemanticAtom(block!, 'DR');
    expect(first).toEqual(second);
  });

  it('builds braided workflow threads from semantic atoms and typed flow channels', () => {
    const thread = buildSemanticWorkflowThread(
      'Water enters the flow, then a block redirects the pipeline.',
      'KO'
    );

    expect(thread.schemaVersion).toBe('scbe-semantic-workflow-thread-v1');
    expect(thread.nodes.map((node) => node.semanticId)).toEqual(['WATER', 'FLOW', 'BLOCK', 'FLOW']);
    expect(thread.edges.map((edge) => edge.channel)).toEqual(['pipe', 'bifurcation', 'merge']);
    expect(thread.edges[1].stateRule).toBe(
      'split flow under a rule and ledger which lanes continue, halt, or exit'
    );
    expect(thread.edges[2].reversible).toBe(true);
    expect(thread.braidedDomains).toEqual(expect.arrayContaining(['code', 'natural', 'workflow']));
    expect(thread.receipt.edgeCount).toBe(3);
  });
});
