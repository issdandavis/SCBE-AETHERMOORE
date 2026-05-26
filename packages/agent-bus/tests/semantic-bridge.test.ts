import { describe, it, expect } from 'vitest';
import { scanAtoms, detectTaskType, buildAtomLedger } from '../src/semantic-bridge.js';

describe('scanAtoms', () => {
  it('returns empty array for unrecognized input', () => {
    expect(scanAtoms('hello world foobar')).toEqual([]);
  });

  it('detects BLOCK from "error"', () => {
    const hits = scanAtoms('the build had an error');
    expect(hits.some((h) => h.semanticId === 'BLOCK')).toBe(true);
  });

  it('detects TRANSFORM from "compile"', () => {
    const hits = scanAtoms('compile the typescript files');
    expect(hits.some((h) => h.semanticId === 'TRANSFORM')).toBe(true);
  });

  it('detects FLOW from "pipeline"', () => {
    const hits = scanAtoms('run the data pipeline');
    expect(hits.some((h) => h.semanticId === 'FLOW')).toBe(true);
  });

  it('returns dominant atom first (by count)', () => {
    const hits = scanAtoms('error error compile pipeline');
    expect(hits[0].semanticId).toBe('BLOCK');
    expect(hits[0].count).toBe(2);
  });

  it('does not double-count overlapping matches', () => {
    const hits = scanAtoms('blocked block');
    const blockHit = hits.find((h) => h.semanticId === 'BLOCK');
    expect(blockHit?.count).toBe(2);
  });
});

describe('detectTaskType', () => {
  it('leaves non-general taskType unchanged', () => {
    expect(detectTaskType('compile everything', 'review')).toBe('review');
    expect(detectTaskType('error in pipeline', 'coding')).toBe('coding');
  });

  it('upgrades "general" to "coding" on TRANSFORM dominance', () => {
    expect(detectTaskType('compile the typescript files', 'general')).toBe('coding');
  });

  it('upgrades "general" to "governance" on BLOCK dominance', () => {
    expect(detectTaskType('deny this request, error detected', 'general')).toBe('governance');
  });

  it('upgrades "general" to "research" on FLOW dominance', () => {
    expect(detectTaskType('analyze the data pipeline stream', 'general')).toBe('research');
  });

  it('returns "general" when no atoms match', () => {
    expect(detectTaskType('hello world', 'general')).toBe('general');
  });
});

describe('buildAtomLedger', () => {
  it('returns zero tokenCount for unrecognized input', () => {
    const ledger = buildAtomLedger('hello world foobar');
    expect(ledger.tokenCount).toBe(0);
    expect(ledger.atoms).toEqual([]);
    expect(ledger.schemaVersion).toBe('scbe-atom-ledger-v1');
  });

  it('returns correct tokenCount for matched atoms', () => {
    const ledger = buildAtomLedger('compile error compile');
    expect(ledger.tokenCount).toBeGreaterThan(0);
    expect(ledger.atoms.length).toBeGreaterThan(0);
  });

  it('produces a 16-char hex inputHash', () => {
    const ledger = buildAtomLedger('test task');
    expect(ledger.inputHash).toMatch(/^[0-9a-f]{16}$/);
  });

  it('is deterministic for the same input', () => {
    const a = buildAtomLedger('transform the data pipeline');
    const b = buildAtomLedger('transform the data pipeline');
    expect(a.inputHash).toBe(b.inputHash);
    expect(a.tokenCount).toBe(b.tokenCount);
  });
});
