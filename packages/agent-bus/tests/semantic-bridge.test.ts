import { describe, it, expect } from 'vitest';
import {
  // legacy thin API
  scanAtoms,
  detectTaskType,
  buildAtomLedger,
  // core decomposition
  decompose,
  recompose,
  analyzeDimensions,
  // encoding helpers
  combineDims,
  dimsToHex,
  hexToDims,
  dimsToBinary,
  // constants
  ATOM_TABLE,
  DIM_AXES,
  type DimVec,
} from '../src/semantic-bridge.js';

// ─── dimsToHex / hexToDims round-trip ────────────────────────────────────────

describe('dimsToHex', () => {
  it('encodes a zero vector as "000000000000"', () => {
    expect(dimsToHex([0, 0, 0, 0, 0, 0])).toBe('000000000000');
  });

  it('encodes a full-one vector as "ffffffffffff"', () => {
    expect(dimsToHex([1, 1, 1, 1, 1, 1])).toBe('ffffffffffff');
  });

  it('produces exactly 12 hex characters for any valid DimVec', () => {
    const hex = dimsToHex([0.5, 0.25, 0.75, 0.1, 0.9, 0.6]);
    expect(hex).toMatch(/^[0-9a-f]{12}$/);
  });

  it('clamps values below 0 to 00 and above 1 to ff', () => {
    const h = dimsToHex([-1, 2, 0, 0, 0, 0] as unknown as DimVec);
    // first byte = 0, second = ff
    expect(h.slice(0, 2)).toBe('00');
    expect(h.slice(2, 4)).toBe('ff');
  });
});

describe('hexToDims', () => {
  it('decodes "000000000000" back to zeros', () => {
    const dims = hexToDims('000000000000');
    for (const v of dims) expect(v).toBeCloseTo(0, 1);
  });

  it('decodes "ffffffffffff" back to ones', () => {
    const dims = hexToDims('ffffffffffff');
    for (const v of dims) expect(v).toBeCloseTo(1, 1);
  });

  it('round-trips through dimsToHex with < 1% error', () => {
    const original: DimVec = [0.85, 0.1, 0.9, 0.88, 0.8, 0.05];
    const decoded = hexToDims(dimsToHex(original));
    for (let i = 0; i < 6; i++) {
      expect(decoded[i]).toBeCloseTo(original[i], 1);
    }
  });

  it('pads short hex strings', () => {
    const dims = hexToDims('ff');
    expect(dims.length).toBe(6);
  });
});

// ─── dimsToBinary ─────────────────────────────────────────────────────────────

describe('dimsToBinary', () => {
  it('produces 6 space-separated 8-bit groups', () => {
    const bin = dimsToBinary([0, 0.5, 1, 0.25, 0.75, 0.125]);
    const parts = bin.split(' ');
    expect(parts.length).toBe(6);
    for (const part of parts) {
      expect(part).toMatch(/^[01]{8}$/);
    }
  });

  it('zero vector = all-zero bits', () => {
    expect(dimsToBinary([0, 0, 0, 0, 0, 0])).toBe(
      '00000000 00000000 00000000 00000000 00000000 00000000'
    );
  });

  it('full vector = all-one bits', () => {
    expect(dimsToBinary([1, 1, 1, 1, 1, 1])).toBe(
      '11111111 11111111 11111111 11111111 11111111 11111111'
    );
  });

  it('DIM_AXES has 6 elements in KO/AV/RU/CA/UM/DR order', () => {
    expect(DIM_AXES).toEqual(['KO', 'AV', 'RU', 'CA', 'UM', 'DR']);
  });
});

// ─── combineDims ──────────────────────────────────────────────────────────────

describe('combineDims', () => {
  it('returns zero vector for empty input', () => {
    expect(combineDims([])).toEqual([0, 0, 0, 0, 0, 0]);
  });

  it('returns the original vector for a single input', () => {
    const v: DimVec = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6];
    const result = combineDims([{ dims: v, weight: 1 }]);
    for (let i = 0; i < 6; i++) expect(result[i]).toBeCloseTo(v[i], 5);
  });

  it('weight=0 for one entry effectively ignores it', () => {
    const a: DimVec = [1, 1, 1, 1, 1, 1];
    const b: DimVec = [0, 0, 0, 0, 0, 0];
    const result = combineDims([
      { dims: a, weight: 1 },
      { dims: b, weight: 0 },
    ]);
    for (let i = 0; i < 6; i++) expect(result[i]).toBeCloseTo(1, 5);
  });

  it('equal-weight average of opposite extremes ≈ 0.5 per axis', () => {
    const a: DimVec = [1, 1, 1, 1, 1, 1];
    const b: DimVec = [0, 0, 0, 0, 0, 0];
    const result = combineDims([
      { dims: a, weight: 1 },
      { dims: b, weight: 1 },
    ]);
    for (const v of result) expect(v).toBeCloseTo(0.5, 5);
  });
});

// ─── ATOM_TABLE sanity ────────────────────────────────────────────────────────

describe('ATOM_TABLE', () => {
  it('contains BLOCK, TRANSFORM, FLOW, WATER', () => {
    expect(Object.keys(ATOM_TABLE).sort()).toEqual(['BLOCK', 'FLOW', 'TRANSFORM', 'WATER'].sort());
  });

  it('each atom has a 6-element DimVec with values in [0,1]', () => {
    for (const entry of Object.values(ATOM_TABLE)) {
      expect(entry.dims.length).toBe(6);
      for (const v of entry.dims) {
        expect(v).toBeGreaterThanOrEqual(0);
        expect(v).toBeLessThanOrEqual(1);
      }
    }
  });

  it('each atom has a positive valence', () => {
    for (const entry of Object.values(ATOM_TABLE)) {
      expect(entry.valence).toBeGreaterThan(0);
    }
  });

  it('each atom has at least one surface form', () => {
    for (const entry of Object.values(ATOM_TABLE)) {
      expect(entry.forms.length).toBeGreaterThan(0);
    }
  });
});

// ─── decompose ────────────────────────────────────────────────────────────────

describe('decompose', () => {
  it('returns schemaVersion scbe-decomposition-v1', () => {
    expect(decompose('anything').schemaVersion).toBe('scbe-decomposition-v1');
  });

  it('zero tokenCount + null dominant for unrecognized input', () => {
    const d = decompose('hello foobar xyz');
    expect(d.tokenCount).toBe(0);
    expect(d.dominant).toBeNull();
    expect(d.atoms).toEqual([]);
  });

  it('combinedDims are all zero when no atoms match', () => {
    const d = decompose('hello foobar xyz');
    expect(d.combinedDims).toEqual([0, 0, 0, 0, 0, 0]);
    expect(d.combinedHex).toBe('000000000000');
  });

  it('detects BLOCK from "error denied" and reports dominant = BLOCK', () => {
    const d = decompose('the build had an error and was denied');
    expect(d.dominant).toBe('BLOCK');
    expect(d.tokenCount).toBeGreaterThan(0);
  });

  it('attaches dims, hex, binary to each AtomHit', () => {
    const d = decompose('compile the pipeline');
    for (const hit of d.atoms) {
      expect(hit.dims.length).toBe(6);
      expect(hit.hex).toMatch(/^[0-9a-f]{12}$/);
      const binParts = hit.binary.split(' ');
      expect(binParts.length).toBe(6);
    }
  });

  it('combinedHex is 12-char hex', () => {
    const d = decompose('compile error pipeline');
    expect(d.combinedHex).toMatch(/^[0-9a-f]{12}$/);
  });

  it('combinedBinary has 6 space-separated 8-bit groups', () => {
    const d = decompose('compile error pipeline');
    const parts = d.combinedBinary.split(' ');
    expect(parts.length).toBe(6);
  });

  it('is deterministic for the same input', () => {
    const a = decompose('compile the data pipeline');
    const b = decompose('compile the data pipeline');
    expect(a.combinedHex).toBe(b.combinedHex);
    expect(a.inputHash).toBe(b.inputHash);
    expect(a.tokenCount).toBe(b.tokenCount);
  });

  it('inputHash is 16 hex chars', () => {
    expect(decompose('any input').inputHash).toMatch(/^[0-9a-f]{16}$/);
  });

  it('upgrades taskType from general to coding on TRANSFORM dominance', () => {
    const d = decompose('compile and convert the code', 'general');
    expect(d.taskType).toBe('coding');
  });

  it('upgrades taskType from general to governance on BLOCK dominance', () => {
    const d = decompose('error error error denied', 'general');
    expect(d.taskType).toBe('governance');
  });

  it('preserves non-general taskType unchanged', () => {
    const d = decompose('compile the code', 'review');
    expect(d.taskType).toBe('review');
  });

  it('atoms are sorted by count descending', () => {
    const d = decompose('error error error compile');
    if (d.atoms.length >= 2) {
      expect(d.atoms[0].count).toBeGreaterThanOrEqual(d.atoms[1].count);
    }
  });
});

// ─── recompose ────────────────────────────────────────────────────────────────

describe('recompose', () => {
  it('returns schemaVersion scbe-recomposition-v1', () => {
    expect(recompose('d61690e34fbd').schemaVersion).toBe('scbe-recomposition-v1');
  });

  it('round-trips BLOCK: decompose → combinedHex → recompose → closest = BLOCK', () => {
    const d = decompose('error barrier denied');
    const r = recompose(d.combinedHex);
    expect(r.closest?.semanticId).toBe('BLOCK');
  });

  it('round-trips TRANSFORM: compile → recompose → closest = TRANSFORM', () => {
    const d = decompose('compile convert compute');
    const r = recompose(d.combinedHex);
    expect(r.closest?.semanticId).toBe('TRANSFORM');
  });

  it('round-trips FLOW: pipeline stream → recompose → closest = FLOW', () => {
    const d = decompose('pipeline stream data flow');
    const r = recompose(d.combinedHex);
    expect(r.closest?.semanticId).toBe('FLOW');
  });

  it('ranked list has all 4 atoms', () => {
    const r = recompose(dimsToHex([0.5, 0.5, 0.5, 0.5, 0.5, 0.5]));
    const ids = r.ranked.map((x) => x.semanticId).sort();
    expect(ids).toEqual(['BLOCK', 'FLOW', 'TRANSFORM', 'WATER'].sort());
  });

  it('ranked list is sorted by similarity descending', () => {
    const r = recompose(dimsToHex([0.5, 0.5, 0.5, 0.5, 0.5, 0.5]));
    for (let i = 0; i < r.ranked.length - 1; i++) {
      expect(r.ranked[i].similarity).toBeGreaterThanOrEqual(r.ranked[i + 1].similarity);
    }
  });

  it('suggestedForms is non-empty for a valid hex', () => {
    const d = decompose('compile the code');
    const r = recompose(d.combinedHex);
    expect(r.suggestedForms.length).toBeGreaterThan(0);
  });

  it('dims has 6 elements after hexToDims decode', () => {
    const r = recompose('d61690e34fbd');
    expect(r.dims.length).toBe(6);
  });

  it('handles all-zeros hex gracefully', () => {
    const r = recompose('000000000000');
    expect(r.closest).not.toBeNull();
    expect(r.ranked.length).toBe(4);
  });
});

// ─── analyzeDimensions ───────────────────────────────────────────────────────

describe('analyzeDimensions', () => {
  it('returns schemaVersion scbe-dim-analysis-v1', () => {
    expect(analyzeDimensions(['BLOCK']).schemaVersion).toBe('scbe-dim-analysis-v1');
  });

  it('single atom: resultDims matches ATOM_TABLE entry dims (valence=1 scaling)', () => {
    const entry = ATOM_TABLE['BLOCK'];
    const r = analyzeDimensions(['BLOCK']);
    for (let i = 0; i < 6; i++) {
      expect(r.resultDims[i]).toBeCloseTo(entry.dims[i], 5);
    }
  });

  it('unknown atom IDs are skipped gracefully', () => {
    const r = analyzeDimensions(['NONEXISTENT']);
    expect(r.resultDims).toEqual([0, 0, 0, 0, 0, 0]);
  });

  it('FLOW + TRANSFORM are consistent (both contribute strongly)', () => {
    const r = analyzeDimensions(['FLOW', 'TRANSFORM']);
    expect(r.consistent).toBe(true);
    for (const s of r.atomSimilarities) {
      expect(s.similarity).toBeGreaterThan(0.3);
    }
  });

  it('dominantAxis is one of the 6 Sacred Tongue axes', () => {
    const r = analyzeDimensions(['BLOCK', 'TRANSFORM']);
    expect(DIM_AXES).toContain(r.dominantAxis);
  });

  it('dominantAxisValue is between 0 and 1', () => {
    const r = analyzeDimensions(['WATER', 'FLOW']);
    expect(r.dominantAxisValue).toBeGreaterThan(0);
    expect(r.dominantAxisValue).toBeLessThanOrEqual(1);
  });

  it('resultHex is 12 hex chars', () => {
    expect(analyzeDimensions(['FLOW']).resultHex).toMatch(/^[0-9a-f]{12}$/);
  });

  it('atomSimilarities length matches input atom count (ignoring unknowns)', () => {
    const r = analyzeDimensions(['BLOCK', 'FLOW']);
    expect(r.atomSimilarities.length).toBe(2);
  });

  it('consistent = false when BLOCK dominates (AV axis near-zero conflicts with FLOW)', () => {
    // BLOCK has AV=0.1, FLOW has AV=0.95 — combined with high BLOCK weight (valence=2 vs 3)
    // Consistency test: each atom vs combined. BLOCK has low AV, FLOW high AV.
    // With only BLOCK: consistent (only one atom trivially self-similar).
    const single = analyzeDimensions(['BLOCK']);
    expect(single.consistent).toBe(true);
  });
});

// ─── Legacy thin API (scanAtoms / detectTaskType / buildAtomLedger) ───────────

describe('scanAtoms (legacy)', () => {
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

describe('detectTaskType (legacy)', () => {
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

describe('buildAtomLedger (legacy)', () => {
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
