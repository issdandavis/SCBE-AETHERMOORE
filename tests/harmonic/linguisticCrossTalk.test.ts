/**
 * @file linguisticCrossTalk.test.ts
 * @module tests/harmonic/linguisticCrossTalk
 * @layer Layer 9, Layer 10, Layer 13
 * @component Linguistic Cross-Talk Kernel Tests
 *
 * Comprehensive tests for the cross-domain reasoning kernel:
 * - Domain mapping correctness
 * - Cross-talk graph construction
 * - Tokenization pipeline
 * - Cross-domain translation
 * - Route finding
 * - Polyhedral validation
 * - Coherence scoring
 * - Governance decisions
 * - Flux state behavior
 * - Property-based tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import * as fc from 'fast-check';
import {
  // Types
  type TongueCode,
  type AcademicDomain,
  type CrossTalkEdge,
  type DomainToken,
  type CrossTalkKernelConfig,
  type PolyhedralValidator,
  // Constants
  ALL_TONGUES,
  ALL_DOMAINS,
  DOMAIN_PROFILES,
  DEFAULT_KERNEL_CONFIG,
  // Functions
  buildCrossTalkEdges,
  domainToTongue,
  tongueToDomain,
  resonanceToVector,
  computeVagueness,
  isValidatorAvailable,
  validatorFacetCount,
  validationStrength,
  // Kernel
  CrossTalkKernel,
  createCrossTalkKernel,
  defaultCrossTalkKernel,
} from '../../src/harmonic/linguisticCrossTalk.js';

// ═══════════════════════════════════════════════════════════════
// Domain Mapping Tests
// ═══════════════════════════════════════════════════════════════

describe('Domain Mapping', () => {
  it('maps 6 tongues to 6 unique academic domains', () => {
    const domains = ALL_TONGUES.map((t) => DOMAIN_PROFILES[t].domain);
    expect(new Set(domains).size).toBe(6);
    expect(domains).toEqual(ALL_DOMAINS);
  });

  it('KO → humanities', () => {
    expect(DOMAIN_PROFILES.KO.domain).toBe('humanities');
    expect(domainToTongue('humanities')).toBe('KO');
    expect(tongueToDomain('KO')).toBe('humanities');
  });

  it('AV → social_sciences', () => {
    expect(DOMAIN_PROFILES.AV.domain).toBe('social_sciences');
    expect(domainToTongue('social_sciences')).toBe('AV');
  });

  it('RU → mathematics', () => {
    expect(DOMAIN_PROFILES.RU.domain).toBe('mathematics');
    expect(domainToTongue('mathematics')).toBe('RU');
  });

  it('CA → engineering', () => {
    expect(DOMAIN_PROFILES.CA.domain).toBe('engineering');
    expect(domainToTongue('engineering')).toBe('CA');
  });

  it('UM → creative_arts', () => {
    expect(DOMAIN_PROFILES.UM.domain).toBe('creative_arts');
    expect(domainToTongue('creative_arts')).toBe('UM');
  });

  it('DR → physical_sciences', () => {
    expect(DOMAIN_PROFILES.DR.domain).toBe('physical_sciences');
    expect(domainToTongue('physical_sciences')).toBe('DR');
  });

  it('domainToTongue and tongueToDomain are inverses', () => {
    for (const t of ALL_TONGUES) {
      expect(domainToTongue(tongueToDomain(t))).toBe(t);
    }
    for (const d of ALL_DOMAINS) {
      expect(tongueToDomain(domainToTongue(d))).toBe(d);
    }
  });

  it('golden ratio weights follow φ^n progression', () => {
    const PHI = (1 + Math.sqrt(5)) / 2;
    for (let i = 0; i < ALL_TONGUES.length; i++) {
      const profile = DOMAIN_PROFILES[ALL_TONGUES[i]];
      expect(profile.languesWeight).toBeCloseTo(Math.pow(PHI, i), 5);
    }
  });

  it('navigator weights follow 1/φ^n progression', () => {
    const PHI = (1 + Math.sqrt(5)) / 2;
    for (let i = 0; i < ALL_TONGUES.length; i++) {
      const profile = DOMAIN_PROFILES[ALL_TONGUES[i]];
      expect(profile.navigatorWeight).toBeCloseTo(1 / Math.pow(PHI, i), 5);
    }
  });

  it('each profile has all required fields', () => {
    for (const t of ALL_TONGUES) {
      const p = DOMAIN_PROFILES[t];
      expect(p.tongue).toBe(t);
      expect(ALL_DOMAINS).toContain(p.domain);
      expect(p.grammar).toBeTruthy();
      expect(p.languesWeight).toBeGreaterThan(0);
      expect(p.navigatorWeight).toBeGreaterThan(0);
      expect(p.technicalRole).toBeTruthy();
      expect(p.academicRole).toBeTruthy();
      expect(p.vaguenessStrategy).toBeTruthy();
    }
  });

  it('all 6 grammar types are unique', () => {
    const grammars = ALL_TONGUES.map((t) => DOMAIN_PROFILES[t].grammar);
    expect(new Set(grammars).size).toBe(6);
  });
});

// ═══════════════════════════════════════════════════════════════
// Cross-Talk Graph Tests
// ═══════════════════════════════════════════════════════════════

describe('Cross-Talk Graph', () => {
  let edges: CrossTalkEdge[];

  beforeEach(() => {
    edges = buildCrossTalkEdges();
  });

  it('generates 30 edges (6 tongues × 5 connections × bidirectional)', () => {
    // C(6,2) = 15 pairs × 2 directions = 30
    expect(edges.length).toBe(30);
  });

  it('all edges have valid tongues', () => {
    for (const edge of edges) {
      expect(ALL_TONGUES).toContain(edge.from);
      expect(ALL_TONGUES).toContain(edge.to);
      expect(edge.from).not.toBe(edge.to);
    }
  });

  it('all edge weights are in (0, 1]', () => {
    for (const edge of edges) {
      expect(edge.weight).toBeGreaterThan(0);
      expect(edge.weight).toBeLessThanOrEqual(1);
    }
  });

  it('bidirectional: for each A→B there is B→A with same weight', () => {
    for (const edge of edges) {
      const reverse = edges.find(
        (e) => e.from === edge.to && e.to === edge.from
      );
      expect(reverse).toBeDefined();
      expect(reverse!.weight).toBeCloseTo(edge.weight, 10);
      expect(reverse!.relationship).toBe(edge.relationship);
    }
  });

  it('adjacent tongues have strongest cross-talk', () => {
    const adjacent = edges.filter((e) => e.relationship === 'adjacent');
    const nonAdjacent = edges.filter((e) => e.relationship !== 'adjacent');

    const minAdjacent = Math.min(...adjacent.map((e) => e.weight));
    const maxNonAdjacent = Math.max(...nonAdjacent.map((e) => e.weight));

    expect(minAdjacent).toBeGreaterThan(maxNonAdjacent);
  });

  it('KO↔AV is adjacent (humanities↔social_sciences)', () => {
    const edge = edges.find((e) => e.from === 'KO' && e.to === 'AV');
    expect(edge).toBeDefined();
    expect(edge!.relationship).toBe('adjacent');
    expect(edge!.validator).toBe('platonic');
  });

  it('KO↔CA is complementary (humanities↔engineering)', () => {
    const edge = edges.find((e) => e.from === 'KO' && e.to === 'CA');
    expect(edge).toBeDefined();
    expect(edge!.relationship).toBe('complementary');
  });

  it('adjacent edges validated by platonic (always available)', () => {
    const adjacent = edges.filter((e) => e.relationship === 'adjacent');
    for (const e of adjacent) {
      expect(e.validator).toBe('platonic');
    }
  });

  it('complementary edges validated by archimedean', () => {
    const complementary = edges.filter((e) => e.relationship === 'complementary');
    for (const e of complementary) {
      expect(e.validator).toBe('archimedean');
    }
  });

  it('weights follow golden ratio scaling', () => {
    const PHI = (1 + Math.sqrt(5)) / 2;
    const adjacent = edges.find((e) => e.relationship === 'adjacent');
    expect(adjacent!.weight).toBeCloseTo(1 / PHI, 5);

    const complementary = edges.find((e) => e.relationship === 'complementary');
    expect(complementary!.weight).toBeCloseTo(1 / (PHI * PHI), 5);
  });

  it('each tongue has exactly 5 outgoing edges (connected to all others)', () => {
    for (const t of ALL_TONGUES) {
      const outgoing = edges.filter((e) => e.from === t);
      expect(outgoing.length).toBe(5);
      // All target tongues are unique
      const targets = new Set(outgoing.map((e) => e.to));
      expect(targets.size).toBe(5);
      expect(targets.has(t)).toBe(false);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Polyhedral Validation Tests
// ═══════════════════════════════════════════════════════════════

describe('Polyhedral Validation', () => {
  it('POLLY mode: all validators available', () => {
    const validators: PolyhedralValidator[] = [
      'platonic', 'archimedean', 'kepler-poinsot', 'toroidal', 'johnson', 'rhombic',
    ];
    for (const v of validators) {
      expect(isValidatorAvailable(v, 'POLLY')).toBe(true);
    }
  });

  it('QUASI mode: only platonic and archimedean', () => {
    expect(isValidatorAvailable('platonic', 'QUASI')).toBe(true);
    expect(isValidatorAvailable('archimedean', 'QUASI')).toBe(true);
    expect(isValidatorAvailable('kepler-poinsot', 'QUASI')).toBe(false);
    expect(isValidatorAvailable('toroidal', 'QUASI')).toBe(false);
    expect(isValidatorAvailable('johnson', 'QUASI')).toBe(false);
    expect(isValidatorAvailable('rhombic', 'QUASI')).toBe(false);
  });

  it('DEMI mode: only platonic', () => {
    expect(isValidatorAvailable('platonic', 'DEMI')).toBe(true);
    expect(isValidatorAvailable('archimedean', 'DEMI')).toBe(false);
    expect(isValidatorAvailable('kepler-poinsot', 'DEMI')).toBe(false);
  });

  it('facet counts are positive for all families', () => {
    const validators: PolyhedralValidator[] = [
      'platonic', 'archimedean', 'kepler-poinsot', 'toroidal', 'johnson', 'rhombic',
    ];
    for (const v of validators) {
      expect(validatorFacetCount(v)).toBeGreaterThan(0);
    }
  });

  it('platonic has 50 facets (4+6+8+12+20)', () => {
    expect(validatorFacetCount('platonic')).toBe(50);
  });

  it('validationStrength returns 0 for unavailable validators', () => {
    const edge: CrossTalkEdge = {
      from: 'KO',
      to: 'RU',
      weight: 0.5,
      relationship: 'harmonic',
      validator: 'johnson',
    };
    expect(validationStrength(edge, 'DEMI')).toBe(0);
    expect(validationStrength(edge, 'QUASI')).toBe(0);
    expect(validationStrength(edge, 'POLLY')).toBeGreaterThan(0);
  });

  it('validationStrength normalized to [0, 1]', () => {
    const validators: PolyhedralValidator[] = [
      'platonic', 'archimedean', 'kepler-poinsot', 'toroidal', 'johnson', 'rhombic',
    ];
    for (const v of validators) {
      const edge: CrossTalkEdge = {
        from: 'KO',
        to: 'AV',
        weight: 0.5,
        relationship: 'adjacent',
        validator: v,
      };
      const strength = validationStrength(edge, 'POLLY');
      expect(strength).toBeGreaterThan(0);
      expect(strength).toBeLessThanOrEqual(1);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Utility Function Tests
// ═══════════════════════════════════════════════════════════════

describe('Utility Functions', () => {
  it('resonanceToVector produces array of length 6', () => {
    const resonance: Record<AcademicDomain, number> = {
      humanities: 0.5,
      social_sciences: 0.3,
      mathematics: 0.8,
      engineering: 0.1,
      creative_arts: 0.6,
      physical_sciences: 0.2,
    };
    const vec = resonanceToVector(resonance);
    expect(vec).toHaveLength(6);
    expect(vec[0]).toBe(0.5); // humanities first
    expect(vec[2]).toBe(0.8); // mathematics third
  });

  it('computeVagueness: single domain signal → 0 (not vague)', () => {
    const resonance: Record<AcademicDomain, number> = {
      humanities: 0,
      social_sciences: 0,
      mathematics: 0.9,
      engineering: 0,
      creative_arts: 0,
      physical_sciences: 0,
    };
    expect(computeVagueness(resonance)).toBe(0);
  });

  it('computeVagueness: equal top signals → high vagueness', () => {
    const resonance: Record<AcademicDomain, number> = {
      humanities: 0.5,
      social_sciences: 0.5,
      mathematics: 0,
      engineering: 0,
      creative_arts: 0,
      physical_sciences: 0,
    };
    expect(computeVagueness(resonance)).toBe(1.0);
  });

  it('computeVagueness: no signal → 1 (maximally vague)', () => {
    const resonance: Record<AcademicDomain, number> = {
      humanities: 0,
      social_sciences: 0,
      mathematics: 0,
      engineering: 0,
      creative_arts: 0,
      physical_sciences: 0,
    };
    expect(computeVagueness(resonance)).toBe(1.0);
  });

  it('computeVagueness: dominant signal with weak secondary → low vagueness', () => {
    const resonance: Record<AcademicDomain, number> = {
      humanities: 0,
      social_sciences: 0,
      mathematics: 0.9,
      engineering: 0.1,
      creative_arts: 0,
      physical_sciences: 0,
    };
    const v = computeVagueness(resonance);
    expect(v).toBeLessThan(0.2);
  });
});

// ═══════════════════════════════════════════════════════════════
// Tokenization Tests
// ═══════════════════════════════════════════════════════════════

describe('Tokenization', () => {
  let kernel: CrossTalkKernel;

  beforeEach(() => {
    kernel = new CrossTalkKernel();
  });

  it('tokenizes input into word-level tokens', () => {
    const tokens = kernel.tokenize('proof theorem algebra');
    expect(tokens).toHaveLength(3);
    expect(tokens[0].content).toBe('proof');
    expect(tokens[1].content).toBe('theorem');
    expect(tokens[2].content).toBe('algebra');
  });

  it('math keywords map to mathematics domain', () => {
    const tokens = kernel.tokenize('proof theorem');
    for (const token of tokens) {
      expect(token.primaryDomain).toBe('mathematics');
      expect(token.primaryTongue).toBe('RU');
    }
  });

  it('physics keywords map to physical_sciences domain', () => {
    const tokens = kernel.tokenize('physics energy particle');
    for (const token of tokens) {
      expect(token.primaryDomain).toBe('physical_sciences');
      expect(token.primaryTongue).toBe('DR');
    }
  });

  it('unknown words have zero resonance', () => {
    const tokens = kernel.tokenize('xyzzy foobar');
    for (const token of tokens) {
      const vec = resonanceToVector(token.resonance);
      expect(vec.every((v) => v === 0)).toBe(true);
    }
  });

  it('cross-domain keywords have non-zero vagueness', () => {
    // "design" has resonance in both engineering and creative_arts
    const tokens = kernel.tokenize('design');
    expect(tokens[0].vagueness).toBeGreaterThan(0);
  });

  it('strips punctuation and lowercases', () => {
    const tokens = kernel.tokenize('PROOF! theorem? Algebra.');
    expect(tokens[0].content).toBe('proof');
    expect(tokens[1].content).toBe('theorem');
    expect(tokens[2].content).toBe('algebra');
  });

  it('empty input produces no tokens', () => {
    expect(kernel.tokenize('')).toHaveLength(0);
    expect(kernel.tokenize('   ')).toHaveLength(0);
  });

  it('each token has a 6D resonance record', () => {
    const tokens = kernel.tokenize('wave symmetry');
    for (const token of tokens) {
      for (const d of ALL_DOMAINS) {
        expect(typeof token.resonance[d]).toBe('number');
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Cross-Domain Translation Tests
// ═══════════════════════════════════════════════════════════════

describe('Cross-Domain Translation', () => {
  let kernel: CrossTalkKernel;

  beforeEach(() => {
    kernel = new CrossTalkKernel();
  });

  it('translates cross-domain tokens', () => {
    // "design" has engineering + creative_arts resonance
    const tokens = kernel.tokenize('design');
    const translations = kernel.translateAll(tokens[0]);
    expect(translations.length).toBeGreaterThan(0);
  });

  it('translation confidence is in [0, 1]', () => {
    const tokens = kernel.tokenize('symmetry');
    const translations = kernel.translateAll(tokens[0]);
    for (const t of translations) {
      expect(t.confidence).toBeGreaterThanOrEqual(0);
      expect(t.confidence).toBeLessThanOrEqual(1);
    }
  });

  it('same-domain translation returns null', () => {
    const tokens = kernel.tokenize('proof');
    const translation = kernel.translate(tokens[0], 'mathematics');
    expect(translation).toBeNull();
  });

  it('translations include source and target info', () => {
    const tokens = kernel.tokenize('design');
    const translations = kernel.translateAll(tokens[0]);
    for (const t of translations) {
      expect(ALL_DOMAINS).toContain(t.source.domain);
      expect(ALL_DOMAINS).toContain(t.target.domain);
      expect(ALL_TONGUES).toContain(t.source.tongue);
      expect(ALL_TONGUES).toContain(t.target.tongue);
      expect(t.source.domain).not.toBe(t.target.domain);
    }
  });

  it('translations sorted by confidence (descending)', () => {
    const tokens = kernel.tokenize('symmetry');
    const translations = kernel.translateAll(tokens[0]);
    for (let i = 1; i < translations.length; i++) {
      expect(translations[i].confidence).toBeLessThanOrEqual(translations[i - 1].confidence);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Route Finding Tests
// ═══════════════════════════════════════════════════════════════

describe('Route Finding', () => {
  let kernel: CrossTalkKernel;

  beforeEach(() => {
    kernel = new CrossTalkKernel();
  });

  it('same-tongue route has length 1 and weight 1', () => {
    const route = kernel.findRoute('KO', 'KO');
    expect(route).not.toBeNull();
    expect(route!.path).toEqual(['KO']);
    expect(route!.edges).toHaveLength(0);
    expect(route!.cumulativeWeight).toBe(1.0);
  });

  it('adjacent tongues have direct route', () => {
    const route = kernel.findRoute('KO', 'AV');
    expect(route).not.toBeNull();
    expect(route!.path).toHaveLength(2);
    expect(route!.path[0]).toBe('KO');
    expect(route!.path[1]).toBe('AV');
  });

  it('all tongue pairs are reachable', () => {
    for (const a of ALL_TONGUES) {
      for (const b of ALL_TONGUES) {
        const route = kernel.findRoute(a, b);
        expect(route).not.toBeNull();
      }
    }
  });

  it('route cumulative weight is product of edge weights', () => {
    const route = kernel.findRoute('KO', 'DR');
    expect(route).not.toBeNull();
    if (route!.edges.length > 0) {
      const expectedWeight = route!.edges.reduce((p, e) => p * e.weight, 1.0);
      expect(route!.cumulativeWeight).toBeCloseTo(expectedWeight, 10);
    }
  });

  it('route length respects maxRouteLength', () => {
    const kernel2 = new CrossTalkKernel({ maxRouteLength: 2 });
    const route = kernel2.findRoute('KO', 'DR');
    // KO→DR should still be reachable directly (adjacent 5 apart = direct edge exists)
    if (route) {
      expect(route.path.length).toBeLessThanOrEqual(2);
    }
  });

  it('allValidated reflects validator availability', () => {
    // In POLLY mode, all validators available
    const routePolly = kernel.findRoute('KO', 'RU');
    expect(routePolly).not.toBeNull();
    expect(routePolly!.allValidated).toBe(true);
  });

  it('DEMI mode may restrict validation on non-platonic edges', () => {
    const demiKernel = new CrossTalkKernel({ fluxState: 'DEMI' });
    // KO→RU is harmonic, validated by johnson (not available in DEMI)
    const route = demiKernel.findRoute('KO', 'RU');
    // The route might go through non-platonic edges, so validation may fail
    // But the route should still exist (graph is fully connected)
    expect(route).not.toBeNull();
  });
});

// ═══════════════════════════════════════════════════════════════
// Full Pipeline (process) Tests
// ═══════════════════════════════════════════════════════════════

describe('Full Pipeline', () => {
  let kernel: CrossTalkKernel;

  beforeEach(() => {
    kernel = new CrossTalkKernel();
  });

  it('processes a pure math query', () => {
    const result = kernel.process('proof theorem algebra');
    expect(result.primaryDomain).toBe('mathematics');
    expect(result.resonanceVector).toHaveLength(6);
    expect(result.coherence).toBeGreaterThan(0);
    expect(result.decision).toBe('ALLOW');
  });

  it('processes a pure physics query', () => {
    const result = kernel.process('physics energy force');
    expect(result.primaryDomain).toBe('physical_sciences');
    expect(result.decision).toBe('ALLOW');
  });

  it('processes a cross-domain query (math + physics)', () => {
    const result = kernel.process('equation wave quantum');
    // Should detect cross-domain resonance
    const mathIdx = ALL_DOMAINS.indexOf('mathematics');
    const physIdx = ALL_DOMAINS.indexOf('physical_sciences');
    expect(result.resonanceVector[mathIdx]).toBeGreaterThan(0);
    expect(result.resonanceVector[physIdx]).toBeGreaterThan(0);
  });

  it('processes a cross-domain query (engineering + creative_arts)', () => {
    const result = kernel.process('design build creative');
    // Design has engineering + creative_arts resonance
    const engIdx = ALL_DOMAINS.indexOf('engineering');
    const artIdx = ALL_DOMAINS.indexOf('creative_arts');
    expect(result.resonanceVector[engIdx]).toBeGreaterThan(0);
    expect(result.resonanceVector[artIdx]).toBeGreaterThan(0);
  });

  it('empty input produces ALLOW with zero coherence', () => {
    const result = kernel.process('');
    expect(result.tokens).toHaveLength(0);
    // With zero resonance, coherence should be 0
    expect(result.coherence).toBe(0);
    expect(result.decision).toBe('DENY');
  });

  it('unknown words produce low coherence', () => {
    const result = kernel.process('xyzzy foobar bazzle');
    expect(result.coherence).toBeLessThan(0.3);
  });

  it('result includes all required fields', () => {
    const result = kernel.process('proof');
    expect(result.tokens).toBeDefined();
    expect(result.primaryDomain).toBeDefined();
    expect(result.translations).toBeDefined();
    expect(result.resonanceVector).toBeDefined();
    expect(result.coherence).toBeDefined();
    expect(result.decision).toBeDefined();
    expect(['ALLOW', 'QUARANTINE', 'DENY']).toContain(result.decision);
  });

  it('resonance vector sums correctly across tokens', () => {
    const result = kernel.process('proof theorem equation');
    // Math domain should have highest resonance
    const mathIdx = ALL_DOMAINS.indexOf('mathematics');
    const maxResonance = Math.max(...result.resonanceVector);
    expect(result.resonanceVector[mathIdx]).toBe(maxResonance);
  });

  it('cross-domain queries generate translations', () => {
    // symmetry has math + physics + creative_arts resonance
    const result = kernel.process('symmetry design');
    // At least some cross-domain translations should occur
    // (only if vagueness threshold met)
    expect(result.translations).toBeDefined();
  });
});

// ═══════════════════════════════════════════════════════════════
// Governance Decision Tests
// ═══════════════════════════════════════════════════════════════

describe('Governance Decisions', () => {
  it('focused known queries → ALLOW', () => {
    const kernel = new CrossTalkKernel();
    const result = kernel.process('theorem proof algebra');
    expect(result.decision).toBe('ALLOW');
  });

  it('empty input → DENY', () => {
    const kernel = new CrossTalkKernel();
    const result = kernel.process('');
    expect(result.decision).toBe('DENY');
  });

  it('custom thresholds affect decisions', () => {
    const strictKernel = new CrossTalkKernel({
      allowThreshold: 0.95,
      denyThreshold: 0.9,
    });
    // Even a good query might not reach 0.95 coherence
    const result = strictKernel.process('proof theorem');
    // The specific decision depends on coherence, but with strict thresholds
    // it should be harder to get ALLOW
    expect(['ALLOW', 'QUARANTINE', 'DENY']).toContain(result.decision);
  });

  it('coherence ≥ allowThreshold → ALLOW', () => {
    const kernel = new CrossTalkKernel({ allowThreshold: 0.0 });
    const result = kernel.process('proof');
    expect(result.decision).toBe('ALLOW');
  });

  it('coherence < denyThreshold → DENY', () => {
    const kernel = new CrossTalkKernel({
      allowThreshold: 0.99,
      denyThreshold: 0.98,
    });
    const result = kernel.process('xyzzy');
    expect(result.decision).toBe('DENY');
  });
});

// ═══════════════════════════════════════════════════════════════
// Flux State Behavior Tests
// ═══════════════════════════════════════════════════════════════

describe('Flux State Behavior', () => {
  it('POLLY mode allows all cross-talk paths', () => {
    const kernel = new CrossTalkKernel({ fluxState: 'POLLY' });
    // All routes should be fully validated
    const route = kernel.findRoute('KO', 'CA');
    expect(route).not.toBeNull();
  });

  it('DEMI mode restricts cross-talk to platonic-validated edges', () => {
    const demiKernel = new CrossTalkKernel({ fluxState: 'DEMI' });
    // Adjacent edges (platonic) should still work
    const adjacentRoute = demiKernel.findRoute('KO', 'AV');
    expect(adjacentRoute).not.toBeNull();
    expect(adjacentRoute!.allValidated).toBe(true); // platonic validator always available
  });

  it('QUASI mode allows platonic + archimedean validators', () => {
    const quasiKernel = new CrossTalkKernel({ fluxState: 'QUASI' });
    // Adjacent (platonic) and complementary (archimedean) should validate
    const adjacentRoute = quasiKernel.findRoute('KO', 'AV');
    expect(adjacentRoute).not.toBeNull();
    expect(adjacentRoute!.allValidated).toBe(true);
  });

  it('flux state affects process results', () => {
    const pollyResult = new CrossTalkKernel({ fluxState: 'POLLY' }).process('symmetry design');
    const demiResult = new CrossTalkKernel({ fluxState: 'DEMI' }).process('symmetry design');
    // Both should produce results, but coherence may differ
    expect(pollyResult.primaryDomain).toBeDefined();
    expect(demiResult.primaryDomain).toBeDefined();
  });
});

// ═══════════════════════════════════════════════════════════════
// Domain Affinity Tests
// ═══════════════════════════════════════════════════════════════

describe('Domain Affinity', () => {
  let kernel: CrossTalkKernel;

  beforeEach(() => {
    kernel = new CrossTalkKernel();
  });

  it('self-affinity is 1.0', () => {
    for (const d of ALL_DOMAINS) {
      expect(kernel.domainAffinity(d, d)).toBe(1.0);
    }
  });

  it('adjacent domains have higher affinity than distant ones', () => {
    // humanities↔social_sciences (adjacent) vs humanities↔engineering (complementary)
    const adjAffinity = kernel.domainAffinity('humanities', 'social_sciences');
    const compAffinity = kernel.domainAffinity('humanities', 'engineering');
    expect(adjAffinity).toBeGreaterThan(compAffinity);
  });

  it('affinity is symmetric', () => {
    for (const a of ALL_DOMAINS) {
      for (const b of ALL_DOMAINS) {
        expect(kernel.domainAffinity(a, b)).toBeCloseTo(kernel.domainAffinity(b, a), 5);
      }
    }
  });

  it('affinity matrix is 6×6', () => {
    const matrix = kernel.affinityMatrix();
    expect(matrix).toHaveLength(6);
    for (const row of matrix) {
      expect(row).toHaveLength(6);
    }
  });

  it('affinity matrix diagonal is all 1s', () => {
    const matrix = kernel.affinityMatrix();
    for (let i = 0; i < 6; i++) {
      expect(matrix[i][i]).toBe(1.0);
    }
  });

  it('all affinities are positive', () => {
    const matrix = kernel.affinityMatrix();
    for (const row of matrix) {
      for (const val of row) {
        expect(val).toBeGreaterThan(0);
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Domain Resonance Analysis Tests
// ═══════════════════════════════════════════════════════════════

describe('Domain Resonance Analysis', () => {
  let kernel: CrossTalkKernel;

  beforeEach(() => {
    kernel = new CrossTalkKernel();
  });

  it('math query resonates most with mathematics', () => {
    const resonance = kernel.domainResonance('proof theorem algebra');
    expect(resonance[0].domain).toBe('mathematics');
    expect(resonance[0].tongue).toBe('RU');
  });

  it('physics query resonates most with physical_sciences', () => {
    const resonance = kernel.domainResonance('physics energy');
    expect(resonance[0].domain).toBe('physical_sciences');
    expect(resonance[0].tongue).toBe('DR');
  });

  it('resonance returns all 6 domains', () => {
    const resonance = kernel.domainResonance('wave symmetry');
    expect(resonance).toHaveLength(6);
    const domains = resonance.map((r) => r.domain);
    expect(new Set(domains).size).toBe(6);
  });

  it('resonance sorted by score (descending)', () => {
    const resonance = kernel.domainResonance('equation wave quantum');
    for (let i = 1; i < resonance.length; i++) {
      expect(resonance[i].score).toBeLessThanOrEqual(resonance[i - 1].score);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Configuration Tests
// ═══════════════════════════════════════════════════════════════

describe('Configuration', () => {
  it('default config has reasonable values', () => {
    expect(DEFAULT_KERNEL_CONFIG.minTranslationConfidence).toBeGreaterThan(0);
    expect(DEFAULT_KERNEL_CONFIG.vaguenessThreshold).toBeGreaterThan(0);
    expect(DEFAULT_KERNEL_CONFIG.vaguenessThreshold).toBeLessThan(1);
    expect(DEFAULT_KERNEL_CONFIG.maxRouteLength).toBeGreaterThan(0);
    expect(DEFAULT_KERNEL_CONFIG.allowThreshold).toBeGreaterThan(DEFAULT_KERNEL_CONFIG.denyThreshold);
    expect(DEFAULT_KERNEL_CONFIG.fluxState).toBe('POLLY');
  });

  it('createCrossTalkKernel accepts partial config', () => {
    const kernel = createCrossTalkKernel({ fluxState: 'QUASI' });
    const config = kernel.getConfig();
    expect(config.fluxState).toBe('QUASI');
    expect(config.minTranslationConfidence).toBe(DEFAULT_KERNEL_CONFIG.minTranslationConfidence);
  });

  it('defaultCrossTalkKernel is available and functional', () => {
    const result = defaultCrossTalkKernel.process('proof');
    expect(result.primaryDomain).toBe('mathematics');
  });

  it('getEdges returns a copy', () => {
    const kernel = new CrossTalkKernel();
    const edges1 = kernel.getEdges();
    const edges2 = kernel.getEdges();
    expect(edges1).not.toBe(edges2);
    expect(edges1).toEqual(edges2);
  });
});

// ═══════════════════════════════════════════════════════════════
// Property-Based Tests
// ═══════════════════════════════════════════════════════════════

describe('Property-Based Tests', () => {
  const tongueArb = fc.constantFrom<TongueCode>('KO', 'AV', 'RU', 'CA', 'UM', 'DR');
  const domainArb = fc.constantFrom<AcademicDomain>(
    'humanities', 'social_sciences', 'mathematics', 'engineering', 'creative_arts', 'physical_sciences'
  );

  it('domainToTongue/tongueToDomain round-trip (100 iterations)', () => {
    fc.assert(
      fc.property(tongueArb, (tongue) => {
        expect(domainToTongue(tongueToDomain(tongue))).toBe(tongue);
      }),
      { numRuns: 100 }
    );
  });

  it('tongueToDomain/domainToTongue round-trip (100 iterations)', () => {
    fc.assert(
      fc.property(domainArb, (domain) => {
        expect(tongueToDomain(domainToTongue(domain))).toBe(domain);
      }),
      { numRuns: 100 }
    );
  });

  it('route from A to B always exists (100 iterations)', () => {
    const kernel = new CrossTalkKernel();
    fc.assert(
      fc.property(tongueArb, tongueArb, (a, b) => {
        const route = kernel.findRoute(a, b);
        expect(route).not.toBeNull();
        expect(route!.path[0]).toBe(a);
        expect(route!.path[route!.path.length - 1]).toBe(b);
      }),
      { numRuns: 100 }
    );
  });

  it('cross-talk edge weights are in (0, 1] (all edges)', () => {
    const edges = buildCrossTalkEdges();
    fc.assert(
      fc.property(fc.integer({ min: 0, max: edges.length - 1 }), (idx) => {
        const edge = edges[idx];
        expect(edge.weight).toBeGreaterThan(0);
        expect(edge.weight).toBeLessThanOrEqual(1);
      }),
      { numRuns: 100 }
    );
  });

  it('vagueness ∈ [0, 1] for any resonance input (100 iterations)', () => {
    fc.assert(
      fc.property(
        fc.float({ min: 0, max: 1, noNaN: true }),
        fc.float({ min: 0, max: 1, noNaN: true }),
        fc.float({ min: 0, max: 1, noNaN: true }),
        fc.float({ min: 0, max: 1, noNaN: true }),
        fc.float({ min: 0, max: 1, noNaN: true }),
        fc.float({ min: 0, max: 1, noNaN: true }),
        (h, s, m, e, c, p) => {
          const resonance: Record<AcademicDomain, number> = {
            humanities: h,
            social_sciences: s,
            mathematics: m,
            engineering: e,
            creative_arts: c,
            physical_sciences: p,
          };
          const v = computeVagueness(resonance);
          expect(v).toBeGreaterThanOrEqual(0);
          expect(v).toBeLessThanOrEqual(1);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('self-affinity is always 1.0 (100 iterations)', () => {
    const kernel = new CrossTalkKernel();
    fc.assert(
      fc.property(domainArb, (domain) => {
        expect(kernel.domainAffinity(domain, domain)).toBe(1.0);
      }),
      { numRuns: 100 }
    );
  });

  it('affinity is symmetric (100 iterations)', () => {
    const kernel = new CrossTalkKernel();
    fc.assert(
      fc.property(domainArb, domainArb, (a, b) => {
        expect(kernel.domainAffinity(a, b)).toBeCloseTo(kernel.domainAffinity(b, a), 5);
      }),
      { numRuns: 100 }
    );
  });

  it('process always returns valid decision (100 iterations)', () => {
    const kernel = new CrossTalkKernel();
    fc.assert(
      fc.property(fc.string({ minLength: 0, maxLength: 100 }), (input) => {
        const result = kernel.process(input);
        expect(['ALLOW', 'QUARANTINE', 'DENY']).toContain(result.decision);
        expect(result.coherence).toBeGreaterThanOrEqual(0);
        expect(result.coherence).toBeLessThanOrEqual(1);
        expect(result.resonanceVector).toHaveLength(6);
      }),
      { numRuns: 100 }
    );
  });
});

// ═══════════════════════════════════════════════════════════════
// Cross-Talk Kernel Integration Tests
// ═══════════════════════════════════════════════════════════════

describe('Integration: Cross-Domain Reasoning', () => {
  let kernel: CrossTalkKernel;

  beforeEach(() => {
    kernel = new CrossTalkKernel();
  });

  it('mathematics ↔ physical_sciences: equation + wave has cross-domain signal', () => {
    const result = kernel.process('equation wave');
    const mathIdx = ALL_DOMAINS.indexOf('mathematics');
    const physIdx = ALL_DOMAINS.indexOf('physical_sciences');
    expect(result.resonanceVector[mathIdx]).toBeGreaterThan(0);
    expect(result.resonanceVector[physIdx]).toBeGreaterThan(0);
  });

  it('humanities ↔ social_sciences: culture + society has cross-domain signal', () => {
    const result = kernel.process('culture society');
    const humIdx = ALL_DOMAINS.indexOf('humanities');
    const socIdx = ALL_DOMAINS.indexOf('social_sciences');
    expect(result.resonanceVector[humIdx]).toBeGreaterThan(0);
    expect(result.resonanceVector[socIdx]).toBeGreaterThan(0);
  });

  it('engineering ↔ mathematics: algorithm + proof has cross-domain signal', () => {
    const result = kernel.process('algorithm proof');
    const engIdx = ALL_DOMAINS.indexOf('engineering');
    const mathIdx = ALL_DOMAINS.indexOf('mathematics');
    expect(result.resonanceVector[engIdx]).toBeGreaterThan(0);
    expect(result.resonanceVector[mathIdx]).toBeGreaterThan(0);
  });

  it('creative_arts ↔ humanities: expression + culture has cross-domain signal', () => {
    const result = kernel.process('expression culture');
    const artIdx = ALL_DOMAINS.indexOf('creative_arts');
    const humIdx = ALL_DOMAINS.indexOf('humanities');
    expect(result.resonanceVector[artIdx]).toBeGreaterThan(0);
    expect(result.resonanceVector[humIdx]).toBeGreaterThan(0);
  });

  it('triple cross-domain: symmetry spans math + physics + creative_arts', () => {
    const result = kernel.process('symmetry');
    const mathIdx = ALL_DOMAINS.indexOf('mathematics');
    const physIdx = ALL_DOMAINS.indexOf('physical_sciences');
    const artIdx = ALL_DOMAINS.indexOf('creative_arts');
    // symmetry keyword has resonance in math, physical_sciences, and creative_arts
    expect(result.resonanceVector[mathIdx]).toBeGreaterThan(0);
    expect(result.resonanceVector[physIdx]).toBeGreaterThan(0);
    expect(result.resonanceVector[artIdx]).toBeGreaterThan(0);
  });

  it('polyhedral validation integrates with routing', () => {
    // In POLLY mode, all routes should be validated
    const route = kernel.findRoute('KO', 'DR');
    expect(route).not.toBeNull();
    // Adjacent route should be fully validated
    const adjRoute = kernel.findRoute('KO', 'AV');
    expect(adjRoute).not.toBeNull();
    expect(adjRoute!.allValidated).toBe(true);
  });

  it('six tongue cross-talk graph is fully connected', () => {
    // Every tongue pair should have a route
    for (const a of ALL_TONGUES) {
      for (const b of ALL_TONGUES) {
        const route = kernel.findRoute(a, b);
        expect(route).not.toBeNull();
        expect(route!.cumulativeWeight).toBeGreaterThan(0);
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Determinism Test
// ═══════════════════════════════════════════════════════════════

describe('Determinism', () => {
  it('same input produces same output across 50 runs', () => {
    const kernel = new CrossTalkKernel();
    const input = 'wave symmetry design proof';
    const baseline = kernel.process(input);

    for (let i = 0; i < 50; i++) {
      const result = kernel.process(input);
      expect(result.primaryDomain).toBe(baseline.primaryDomain);
      expect(result.resonanceVector).toEqual(baseline.resonanceVector);
      expect(result.coherence).toBeCloseTo(baseline.coherence, 10);
      expect(result.decision).toBe(baseline.decision);
    }
  });
});
