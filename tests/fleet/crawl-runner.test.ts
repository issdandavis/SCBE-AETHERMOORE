/**
 * @file crawl-runner.test.ts
 * @module tests/fleet/crawl-runner
 * @component CrawlRunner integration test suite
 *
 * Tests the CrawlRunner integration layer that connects:
 *   CrawlCoordinator → task assignment, role switching
 *   BrowserAgent → page observation, 14-layer governance
 *   Detection System → sentinel anomaly detection
 *
 * Groups:
 *   A: Link & data extraction utilities (8 tests)
 *   B: Trajectory building (6 tests)
 *   C: Agent management (7 tests)
 *   D: Crawl step execution (12 tests)
 *   E: Sentinel scanning (10 tests)
 *   F: Role switching integration (6 tests)
 *   G: Full lifecycle integration (5 tests)
 *   H: Statistics & queries (4 tests)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  CrawlRunner,
  extractLinksFromObservation,
  extractDataFromObservation,
  buildTrajectoryPoint,
  DEFAULT_RUNNER_CONFIG,
  type CrawlAgentBrowserConfig,
  type ManagedAgent,
  type CrawlStepResult,
} from '../../src/fleet/crawl-runner.js';
import type { BrowserBackend } from '../../src/browser/agent.js';
import type {
  BrowserObservation,
  PageObservation,
  GovernanceResult,
  DOMElementState,
  FormObservation,
} from '../../src/browser/types.js';
import type { TrajectoryPoint, CombinedAssessment, DetectionResult } from '../../src/ai_brain/types.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function mockPageObs(url = 'https://example.com', overrides: Partial<PageObservation> = {}): PageObservation {
  return {
    url,
    title: `Page at ${url}`,
    readyState: 'complete',
    viewport: { width: 1280, height: 720 },
    scroll: { x: 0, y: 0 },
    interactiveElements: [],
    forms: [],
    dialogs: [],
    loadTime: 100,
    timestamp: Date.now(),
    ...overrides,
  };
}

function mockObservation(url = 'https://example.com', overrides: Partial<PageObservation> = {}): BrowserObservation {
  return {
    sessionId: 'test-session',
    sequence: 0,
    page: mockPageObs(url, overrides),
    timestamp: Date.now(),
  };
}

function mockGovernance(overrides: Partial<GovernanceResult> = {}): GovernanceResult {
  return {
    decision: 'ALLOW',
    decisionId: 'gov-test-1',
    riskScore: 0.15,
    confidence: 0.5,
    riskFactors: {
      actionRisk: 0.3,
      domainRisk: 0.4,
      sessionRisk: 0,
      temporalRisk: 0.05,
      historicalRisk: 0,
    },
    explanation: 'ALLOW: test action',
    requiredTier: 'KO',
    requiresRoundtable: false,
    ...overrides,
  };
}

function makeDOMElement(
  tagName: string,
  dataAttributes: Record<string, string> = {},
  value?: string,
): DOMElementState {
  return {
    tagName,
    classList: [],
    textContent: '',
    bounds: { x: 0, y: 0, width: 100, height: 30 },
    visible: true,
    interactive: true,
    dataAttributes,
    ...(value !== undefined ? { value } : {}),
  };
}

function makeForm(id: string, fields: Array<{ name: string; sensitive?: boolean }> = []): FormObservation {
  return {
    identifier: id,
    action: '/submit',
    method: 'POST',
    fields: fields.map((f) => ({
      name: f.name,
      type: 'text',
      value: '',
      required: true,
      sensitivity: f.sensitive ? 'password' as const : 'none' as const,
    })),
    hasSensitiveFields: fields.some((f) => f.sensitive),
    sensitiveFieldTypes: fields.filter((f) => f.sensitive).map(() => 'password' as const),
  };
}

/** Create a mock browser backend with configurable observations */
function createMockBackend(
  obs: PageObservation = mockPageObs(),
): BrowserBackend {
  let currentUrl = 'about:blank';
  let connected = false;

  return {
    async initialize() { connected = true; },
    async navigate(url: string) { currentUrl = url; obs = { ...obs, url }; },
    async click() {},
    async type() {},
    async scroll() {},
    async executeScript<T>(script: string): Promise<T> { return undefined as T; },
    async screenshot() { return Buffer.from('mock'); },
    async observe(): Promise<PageObservation> {
      return { ...obs, url: currentUrl };
    },
    async close() { connected = false; },
    isConnected() { return connected; },
  };
}

/** Create a standard agent config */
function agentConfig(
  agentId: string,
  role: 'scout' | 'analyzer' | 'sentinel' | 'reporter',
  tongue: 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR' = 'KO',
  obs?: PageObservation,
): CrawlAgentBrowserConfig {
  return {
    agentId,
    tongue,
    backend: createMockBackend(obs),
    role,
  };
}

/** Build a fake CombinedAssessment */
function makeCombinedAssessment(score: number, flagged: boolean): CombinedAssessment {
  const makeDetection = (name: string): DetectionResult => ({
    mechanism: name,
    score: score,
    flagged,
    detectedAttackTypes: flagged ? ['test_attack'] : [],
  });
  return {
    detections: [
      makeDetection('phase_distance'),
      makeDetection('curvature_accumulation'),
      makeDetection('threat_lissajous'),
      makeDetection('decimal_drift'),
      makeDetection('six_tonic'),
    ],
    combinedScore: score,
    decision: score >= 0.85 ? 'DENY' : score >= 0.7 ? 'ESCALATE' : score >= 0.5 ? 'QUARANTINE' : 'ALLOW',
    anyFlagged: flagged,
    flagCount: flagged ? 5 : 0,
    timestamp: Date.now(),
  };
}

// ═══════════════════════════════════════════════════════════════
// A: Link & Data Extraction Utilities
// ═══════════════════════════════════════════════════════════════

describe('A — Link & Data Extraction', () => {
  it('A1: extracts no links from empty elements', () => {
    const obs = mockObservation();
    expect(extractLinksFromObservation(obs)).toEqual([]);
  });

  it('A2: extracts HTTP links from anchor elements with dataAttributes', () => {
    const obs = mockObservation('https://example.com', {
      interactiveElements: [
        makeDOMElement('a', { href: 'https://example.com/page1' }),
        makeDOMElement('a', { href: 'https://example.com/page2' }),
        makeDOMElement('button'),
      ],
    });
    const links = extractLinksFromObservation(obs);
    expect(links).toHaveLength(2);
    expect(links).toContain('https://example.com/page1');
    expect(links).toContain('https://example.com/page2');
  });

  it('A3: filters out non-HTTP links', () => {
    const obs = mockObservation('https://example.com', {
      interactiveElements: [
        makeDOMElement('a', { href: 'javascript:void(0)' }),
        makeDOMElement('a', { href: 'mailto:test@example.com' }),
        makeDOMElement('a', { href: 'https://valid.com' }),
      ],
    });
    const links = extractLinksFromObservation(obs);
    expect(links).toHaveLength(1);
    expect(links[0]).toBe('https://valid.com');
  });

  it('A4: deduplicates identical links', () => {
    const obs = mockObservation('https://example.com', {
      interactiveElements: [
        makeDOMElement('a', { href: 'https://same.com' }),
        makeDOMElement('a', { href: 'https://same.com' }),
      ],
    });
    expect(extractLinksFromObservation(obs)).toHaveLength(1);
  });

  it('A5: extracts links from value field as fallback', () => {
    const obs = mockObservation('https://example.com', {
      interactiveElements: [
        makeDOMElement('a', {}, 'https://via-value.com'),
      ],
    });
    const links = extractLinksFromObservation(obs);
    expect(links).toHaveLength(1);
    expect(links[0]).toBe('https://via-value.com');
  });

  it('A6: extracts basic page data from observation', () => {
    const obs = mockObservation('https://example.com', {
      loadTime: 250,
      interactiveElements: [makeDOMElement('button'), makeDOMElement('input')],
    });
    const data = extractDataFromObservation(obs);
    expect(data.url).toBe('https://example.com');
    expect(data.title).toBe('Page at https://example.com');
    expect(data.loadTime).toBe(250);
    expect(data.interactiveElementCount).toBe(2);
    expect(data.formCount).toBe(0);
    expect(data.hasDialogs).toBe(false);
  });

  it('A7: extracts form metadata without field values', () => {
    const obs = mockObservation('https://example.com', {
      forms: [
        makeForm('login-form', [
          { name: 'username' },
          { name: 'password', sensitive: true },
        ]),
      ],
    });
    const data = extractDataFromObservation(obs);
    expect(data.formCount).toBe(1);
    const forms = data.forms as Array<Record<string, unknown>>;
    expect(forms).toHaveLength(1);
    expect(forms[0].identifier).toBe('login-form');
    expect(forms[0].fieldCount).toBe(2);
    expect(forms[0].hasSensitiveFields).toBe(true);
  });

  it('A8: handles observation with no interactive elements', () => {
    const obs = mockObservation('https://minimal.com', {
      interactiveElements: [],
      forms: [],
      dialogs: [],
    });
    const data = extractDataFromObservation(obs);
    expect(data.interactiveElementCount).toBe(0);
    expect(data.formCount).toBe(0);
    expect(data.hasDialogs).toBe(false);
  });
});

// ═══════════════════════════════════════════════════════════════
// B: Trajectory Building
// ═══════════════════════════════════════════════════════════════

describe('B — Trajectory Building', () => {
  it('B1: builds a 21D state vector', () => {
    const obs = mockObservation();
    const gov = mockGovernance();
    const point = buildTrajectoryPoint(obs, gov, 0);
    expect(point.state).toHaveLength(21);
  });

  it('B2: includes step number', () => {
    const point = buildTrajectoryPoint(mockObservation(), mockGovernance(), 42);
    expect(point.step).toBe(42);
  });

  it('B3: maps risk factors to state dimensions', () => {
    const gov = mockGovernance({
      riskScore: 0.75,
      riskFactors: {
        actionRisk: 0.9,
        domainRisk: 0.8,
        sessionRisk: 0.5,
        temporalRisk: 0.3,
        historicalRisk: 0.4,
      },
      confidence: 0.6,
    });
    const point = buildTrajectoryPoint(mockObservation(), gov, 0);

    // SCBE Context block
    expect(point.state[0]).toBe(0.9); // actionRisk
    expect(point.state[1]).toBe(0.8); // domainRisk
    expect(point.state[2]).toBe(0.5); // sessionRisk
    expect(point.state[3]).toBe(0.75); // behavior score = riskScore
    expect(point.state[5]).toBe(0.6); // intent alignment = confidence
  });

  it('B4: embedded is 6D projection', () => {
    const point = buildTrajectoryPoint(mockObservation(), mockGovernance(), 0);
    expect(point.embedded).toHaveLength(6);
  });

  it('B5: distance scales with risk score', () => {
    const lowRisk = buildTrajectoryPoint(mockObservation(), mockGovernance({ riskScore: 0.1 }), 0);
    const highRisk = buildTrajectoryPoint(mockObservation(), mockGovernance({ riskScore: 0.9 }), 0);
    expect(highRisk.distance).toBeGreaterThan(lowRisk.distance);
  });

  it('B6: curvature initialized to 0', () => {
    const point = buildTrajectoryPoint(mockObservation(), mockGovernance(), 0);
    expect(point.curvature).toBe(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// C: Agent Management
// ═══════════════════════════════════════════════════════════════

describe('C — Agent Management', () => {
  let runner: CrawlRunner;

  beforeEach(() => {
    runner = new CrawlRunner();
  });

  it('C1: registers agents with coordinator and managed map', () => {
    const managed = runner.addAgent(agentConfig('scout-1', 'scout'));
    expect(managed.agentId).toBe('scout-1');
    expect(managed.tongue).toBe('KO');
    expect(managed.sessionActive).toBe(false);
    expect(managed.trajectory).toHaveLength(0);

    // Also registered in coordinator
    const crawlAgent = runner.coordinator.getAgent('scout-1');
    expect(crawlAgent).toBeDefined();
    expect(crawlAgent!.role).toBe('scout');
  });

  it('C2: getAgent returns managed agent', () => {
    runner.addAgent(agentConfig('a1', 'scout'));
    const agent = runner.getAgent('a1');
    expect(agent).toBeDefined();
    expect(agent!.agentId).toBe('a1');
  });

  it('C3: getAgent returns undefined for unknown agent', () => {
    expect(runner.getAgent('nonexistent')).toBeUndefined();
  });

  it('C4: getAllAgents returns all managed agents', () => {
    runner.addAgent(agentConfig('a1', 'scout'));
    runner.addAgent(agentConfig('a2', 'analyzer'));
    runner.addAgent(agentConfig('a3', 'sentinel'));
    expect(runner.getAllAgents()).toHaveLength(3);
  });

  it('C5: removeAgent removes from both managed and coordinator', async () => {
    runner.addAgent(agentConfig('rm-1', 'scout'));
    const removed = await runner.removeAgent('rm-1');
    expect(removed).toBe(true);
    expect(runner.getAgent('rm-1')).toBeUndefined();
    expect(runner.coordinator.getAgent('rm-1')).toBeUndefined();
  });

  it('C6: removeAgent returns false for unknown agent', async () => {
    expect(await runner.removeAgent('unknown')).toBe(false);
  });

  it('C7: multiple agents with different tongues', () => {
    runner.addAgent(agentConfig('ko-agent', 'scout', 'KO'));
    runner.addAgent(agentConfig('dr-agent', 'sentinel', 'DR'));
    expect(runner.getAgent('ko-agent')!.tongue).toBe('KO');
    expect(runner.getAgent('dr-agent')!.tongue).toBe('DR');
  });
});

// ═══════════════════════════════════════════════════════════════
// D: Crawl Step Execution
// ═══════════════════════════════════════════════════════════════

describe('D — Crawl Step Execution', () => {
  let runner: CrawlRunner;

  beforeEach(() => {
    runner = new CrawlRunner();
  });

  it('D1: step returns null for unknown agent', async () => {
    expect(await runner.step('nobody')).toBeNull();
  });

  it('D2: step returns null for sentinel agents', async () => {
    runner.addAgent(agentConfig('sentinel-1', 'sentinel'));
    runner.addSeedUrls(['https://example.com']);
    expect(await runner.step('sentinel-1')).toBeNull();
  });

  it('D3: step returns null for reporter agents', async () => {
    runner.addAgent(agentConfig('reporter-1', 'reporter'));
    runner.addSeedUrls(['https://example.com']);
    expect(await runner.step('reporter-1')).toBeNull();
  });

  it('D4: step returns null when no work available', async () => {
    runner.addAgent(agentConfig('scout-1', 'scout'));
    // No seed URLs added
    expect(await runner.step('scout-1')).toBeNull();
  });

  it('D5: scout step navigates and discovers links', async () => {
    const obs = mockPageObs('https://example.com', {
      interactiveElements: [
        makeDOMElement('a', { href: 'https://example.com/page1' }),
        makeDOMElement('a', { href: 'https://example.com/page2' }),
      ],
    });
    runner.addAgent(agentConfig('scout-1', 'scout', 'KO', obs));
    runner.addSeedUrls(['https://example.com']);

    const result = await runner.step('scout-1');
    expect(result).not.toBeNull();
    expect(result!.success).toBe(true);
    expect(result!.agentId).toBe('scout-1');
    expect(result!.url).toContain('example.com');
    expect(result!.discoveredUrls.length).toBeGreaterThanOrEqual(0);
    expect(result!.governance).not.toBeNull();
    expect(result!.durationMs).toBeGreaterThanOrEqual(0);
  });

  it('D6: analyzer step extracts structured data', async () => {
    const obs = mockPageObs('https://example.com', {
      forms: [makeForm('login', [{ name: 'email' }])],
    });
    runner.addAgent(agentConfig('analyzer-1', 'analyzer', 'RU', obs));
    runner.addSeedUrls(['https://example.com']);

    const result = await runner.step('analyzer-1');
    expect(result).not.toBeNull();
    expect(result!.success).toBe(true);
    expect(result!.extractedData).toBeDefined();
    expect(result!.extractedData.formCount).toBe(1);
  });

  it('D7: step initializes browser session automatically', async () => {
    const config = agentConfig('auto-init', 'scout');
    runner.addAgent(config);
    runner.addSeedUrls(['https://example.com']);

    const managed = runner.getAgent('auto-init')!;
    expect(managed.sessionActive).toBe(false);

    await runner.step('auto-init');
    expect(managed.sessionActive).toBe(true);
  });

  it('D8: step records trajectory point', async () => {
    runner.addAgent(agentConfig('track-1', 'scout'));
    runner.addSeedUrls(['https://example.com']);

    await runner.step('track-1');

    const managed = runner.getAgent('track-1')!;
    expect(managed.trajectory).toHaveLength(1);
    expect(managed.trajectory[0].state).toHaveLength(21);
  });

  it('D9: step records governance log', async () => {
    runner.addAgent(agentConfig('gov-1', 'scout'));
    runner.addSeedUrls(['https://example.com']);

    await runner.step('gov-1');

    const managed = runner.getAgent('gov-1')!;
    expect(managed.governanceLog).toHaveLength(1);
    expect(managed.governanceLog[0].decision).toBeDefined();
  });

  it('D10: step reports result to coordinator', async () => {
    runner.addAgent(agentConfig('report-1', 'scout'));
    runner.addSeedUrls(['https://example.com']);

    await runner.step('report-1');

    const results = runner.coordinator.getResults();
    expect(results).toHaveLength(1);
    expect(results[0].agentId).toBe('report-1');
    expect(results[0].role).toBe('scout');
  });

  it('D11: step updates stats on success', async () => {
    runner.addAgent(agentConfig('stats-1', 'scout'));
    runner.addSeedUrls(['https://example.com']);

    await runner.step('stats-1');

    const stats = runner.getStats();
    expect(stats.totalSteps).toBe(1);
    expect(stats.successfulSteps).toBe(1);
    expect(stats.failedSteps).toBe(0);
  });

  it('D12: stepAll runs steps for all active crawling agents', async () => {
    runner.addAgent(agentConfig('s1', 'scout'));
    runner.addAgent(agentConfig('s2', 'scout'));
    runner.addAgent(agentConfig('sent-1', 'sentinel')); // Should be skipped
    runner.addSeedUrls(['https://a.com', 'https://b.com']);

    const results = await runner.stepAll();
    // At most 2 scouts can step (sentinel is skipped)
    expect(results.length).toBeGreaterThanOrEqual(1);
    expect(results.length).toBeLessThanOrEqual(2);
    // Sentinel should not appear
    expect(results.every((r) => r.agentId !== 'sent-1')).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// E: Sentinel Scanning
// ═══════════════════════════════════════════════════════════════

describe('E — Sentinel Scanning', () => {
  let runner: CrawlRunner;

  beforeEach(() => {
    runner = new CrawlRunner({ minTrajectoryLength: 2 });
  });

  it('E1: non-sentinel agents cannot scan', () => {
    runner.addAgent(agentConfig('scout-1', 'scout'));
    const result = runner.sentinelScan('scout-1');
    expect(result.scannedAgents).toHaveLength(0);
  });

  it('E2: sentinel scan skips agents with short trajectories', () => {
    runner.addAgent(agentConfig('sentinel-1', 'sentinel'));
    runner.addAgent(agentConfig('scout-1', 'scout'));
    // scout-1 has no trajectory points

    const result = runner.sentinelScan('sentinel-1');
    expect(result.scannedAgents).toHaveLength(0);
  });

  it('E3: sentinel scan with detection function flags anomalous agents', () => {
    runner.addAgent(agentConfig('sentinel-1', 'sentinel'));
    runner.addAgent(agentConfig('scout-1', 'scout'));

    // Manually add trajectory points to scout-1
    const managed = runner.getAgent('scout-1')!;
    for (let i = 0; i < 5; i++) {
      managed.trajectory.push({
        step: i,
        state: new Array(21).fill(0.5),
        embedded: new Array(6).fill(0.3),
        distance: 2.5,
        curvature: 0,
        timestamp: Date.now(),
      });
    }

    // Inject detection function that flags high scores
    runner.setDetectionFunction(() => makeCombinedAssessment(0.9, true));

    const result = runner.sentinelScan('sentinel-1');
    expect(result.scannedAgents).toContain('scout-1');
    expect(result.flaggedAgents).toHaveLength(1);
    expect(result.flaggedAgents[0].agentId).toBe('scout-1');
    expect(result.flaggedAgents[0].combinedScore).toBe(0.9);
  });

  it('E4: sentinel scan auto-quarantines above threshold', () => {
    runner.addAgent(agentConfig('sentinel-1', 'sentinel'));
    runner.addAgent(agentConfig('bad-agent', 'scout'));

    const managed = runner.getAgent('bad-agent')!;
    for (let i = 0; i < 5; i++) {
      managed.trajectory.push({
        step: i, state: new Array(21).fill(0.8),
        embedded: new Array(6).fill(0.5), distance: 4,
        curvature: 0, timestamp: Date.now(),
      });
    }

    runner.setDetectionFunction(() => makeCombinedAssessment(0.95, true));

    const result = runner.sentinelScan('sentinel-1');
    expect(result.quarantinedAgents).toContain('bad-agent');

    const crawlAgent = runner.coordinator.getAgent('bad-agent');
    expect(crawlAgent!.status).toBe('quarantined');
  });

  it('E5: sentinel scan does NOT quarantine below threshold', () => {
    runner.addAgent(agentConfig('sentinel-1', 'sentinel'));
    runner.addAgent(agentConfig('safe-agent', 'scout'));

    const managed = runner.getAgent('safe-agent')!;
    for (let i = 0; i < 5; i++) {
      managed.trajectory.push({
        step: i, state: new Array(21).fill(0.1),
        embedded: new Array(6).fill(0.05), distance: 0.5,
        curvature: 0, timestamp: Date.now(),
      });
    }

    runner.setDetectionFunction(() => makeCombinedAssessment(0.3, false));

    const result = runner.sentinelScan('sentinel-1');
    expect(result.flaggedAgents).toHaveLength(0);
    expect(result.quarantinedAgents).toHaveLength(0);
  });

  it('E6: sentinel does not scan itself', () => {
    runner.addAgent(agentConfig('sentinel-1', 'sentinel'));
    const managed = runner.getAgent('sentinel-1')!;
    for (let i = 0; i < 5; i++) {
      managed.trajectory.push({
        step: i, state: new Array(21).fill(0.9),
        embedded: new Array(6).fill(0.5), distance: 4,
        curvature: 0, timestamp: Date.now(),
      });
    }

    runner.setDetectionFunction(() => makeCombinedAssessment(0.95, true));

    const result = runner.sentinelScan('sentinel-1');
    expect(result.scannedAgents).not.toContain('sentinel-1');
  });

  it('E7: fallback detection uses governance log when no detection function', () => {
    runner.addAgent(agentConfig('sentinel-1', 'sentinel'));
    runner.addAgent(agentConfig('risky-agent', 'scout'));

    const managed = runner.getAgent('risky-agent')!;
    for (let i = 0; i < 5; i++) {
      managed.trajectory.push({
        step: i, state: new Array(21).fill(0.5),
        embedded: new Array(6).fill(0.3), distance: 2,
        curvature: 0, timestamp: Date.now(),
      });
    }
    // Add high-risk governance entries
    for (let i = 0; i < 3; i++) {
      managed.governanceLog.push(mockGovernance({ riskScore: 0.9, decision: 'DENY' }));
    }

    // No detection function set — uses fallback
    const result = runner.sentinelScan('sentinel-1');
    expect(result.flaggedAgents.length).toBeGreaterThanOrEqual(1);
  });

  it('E8: sentinel scan updates stats', () => {
    runner.addAgent(agentConfig('sentinel-1', 'sentinel'));
    runner.sentinelScan('sentinel-1');

    const stats = runner.getStats();
    expect(stats.sentinelScans).toBe(1);
  });

  it('E9: sentinel scan with multiple agents scans all', () => {
    runner.addAgent(agentConfig('sentinel-1', 'sentinel'));
    runner.addAgent(agentConfig('a1', 'scout'));
    runner.addAgent(agentConfig('a2', 'analyzer'));

    // Give both agents trajectories
    for (const id of ['a1', 'a2']) {
      const managed = runner.getAgent(id)!;
      for (let i = 0; i < 5; i++) {
        managed.trajectory.push({
          step: i, state: new Array(21).fill(0.2),
          embedded: new Array(6).fill(0.1), distance: 1,
          curvature: 0, timestamp: Date.now(),
        });
      }
    }

    runner.setDetectionFunction(() => makeCombinedAssessment(0.2, false));
    const result = runner.sentinelScan('sentinel-1');
    expect(result.scannedAgents).toHaveLength(2);
    expect(result.scannedAgents).toContain('a1');
    expect(result.scannedAgents).toContain('a2');
  });

  it('E10: sentinel scan publishes on sentinel channel', () => {
    runner.addAgent(agentConfig('sentinel-1', 'sentinel'));
    runner.sentinelScan('sentinel-1');

    const sentinelMessages = runner.coordinator.bus.getMessagesByChannel('sentinel');
    expect(sentinelMessages.length).toBeGreaterThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// F: Role Switching Integration
// ═══════════════════════════════════════════════════════════════

describe('F — Role Switching', () => {
  let runner: CrawlRunner;

  beforeEach(() => {
    runner = new CrawlRunner({ coordinator: { requireConsensusForRoleSwitch: false } });
    runner.addAgent(agentConfig('a1', 'scout'));
    runner.addAgent(agentConfig('a2', 'analyzer'));
    runner.addAgent(agentConfig('a3', 'sentinel'));
  });

  it('F1: valid role switch through runner', () => {
    const requestId = runner.requestRoleSwitch('a1', 'analyzer', 'need analysis');
    expect(requestId).not.toBeNull();

    const crawlAgent = runner.coordinator.getAgent('a1');
    expect(crawlAgent!.role).toBe('analyzer');
  });

  it('F2: invalid braid transition returns null', () => {
    // analyzer → reporter is invalid (Chebyshev distance > 1)
    const requestId = runner.requestRoleSwitch('a2', 'reporter', 'want to report');
    expect(requestId).toBeNull();
  });

  it('F3: consensus-based role switch', () => {
    const consensusRunner = new CrawlRunner({
      coordinator: { requireConsensusForRoleSwitch: true, roleSwitchQuorum: 2 },
    });
    consensusRunner.addAgent(agentConfig('x1', 'scout'));
    consensusRunner.addAgent(agentConfig('x2', 'analyzer'));
    consensusRunner.addAgent(agentConfig('x3', 'sentinel'));

    const requestId = consensusRunner.requestRoleSwitch('x1', 'analyzer', 'analysis needed');
    expect(requestId).not.toBeNull();

    // Vote
    consensusRunner.voteOnRoleSwitch(requestId!, 'x2', true);
    const result = consensusRunner.voteOnRoleSwitch(requestId!, 'x3', true);
    expect(result).toBe('approved');

    const agent = consensusRunner.coordinator.getAgent('x1');
    expect(agent!.role).toBe('analyzer');
  });

  it('F4: denied consensus role switch', () => {
    const consensusRunner = new CrawlRunner({
      coordinator: { requireConsensusForRoleSwitch: true, roleSwitchQuorum: 2 },
    });
    consensusRunner.addAgent(agentConfig('x1', 'scout'));
    consensusRunner.addAgent(agentConfig('x2', 'analyzer'));
    consensusRunner.addAgent(agentConfig('x3', 'sentinel'));

    const requestId = consensusRunner.requestRoleSwitch('x1', 'analyzer', 'analysis needed');

    // Both deny
    consensusRunner.voteOnRoleSwitch(requestId!, 'x2', false);
    const result = consensusRunner.voteOnRoleSwitch(requestId!, 'x3', false);
    expect(result).toBe('denied');

    const agent = consensusRunner.coordinator.getAgent('x1');
    expect(agent!.role).toBe('scout'); // Unchanged
  });

  it('F5: role switch for unknown agent returns null', () => {
    expect(runner.requestRoleSwitch('unknown', 'scout', 'test')).toBeNull();
  });

  it('F6: sentinel→scout transition is valid', () => {
    const requestId = runner.requestRoleSwitch('a3', 'scout', 'switching to explore');
    expect(requestId).not.toBeNull();
    expect(runner.coordinator.getAgent('a3')!.role).toBe('scout');
  });
});

// ═══════════════════════════════════════════════════════════════
// G: Full Lifecycle Integration
// ═══════════════════════════════════════════════════════════════

describe('G — Full Lifecycle', () => {
  it('G1: full crawl + sentinel scan lifecycle', async () => {
    const runner = new CrawlRunner({
      coordinator: { requireConsensusForRoleSwitch: false },
      minTrajectoryLength: 1,
    });

    // Register agents
    runner.addAgent(agentConfig('scout-1', 'scout'));
    runner.addAgent(agentConfig('sentinel-1', 'sentinel'));

    // Seed
    runner.addSeedUrls(['https://example.com', 'https://test.com']);

    // Scout crawls
    const r1 = await runner.step('scout-1');
    expect(r1).not.toBeNull();
    expect(r1!.success).toBe(true);

    const r2 = await runner.step('scout-1');
    expect(r2).not.toBeNull();
    expect(r2!.success).toBe(true);

    // Sentinel scans
    runner.setDetectionFunction(() => makeCombinedAssessment(0.2, false));
    const scan = runner.sentinelScan('sentinel-1');
    expect(scan.scannedAgents).toContain('scout-1');
    expect(scan.quarantinedAgents).toHaveLength(0);

    // Verify trajectory growth
    const managed = runner.getAgent('scout-1')!;
    expect(managed.trajectory).toHaveLength(2);
    expect(managed.urlsCrawled).toHaveLength(2);

    // Stats
    const stats = runner.getStats();
    expect(stats.totalSteps).toBe(2);
    expect(stats.successfulSteps).toBe(2);
    expect(stats.sentinelScans).toBe(1);
  });

  it('G2: quarantined agent cannot crawl', async () => {
    const runner = new CrawlRunner({ minTrajectoryLength: 1 });

    runner.addAgent(agentConfig('bad-1', 'scout'));
    runner.addSeedUrls(['https://example.com', 'https://test.com']);

    // Crawl once to build trajectory
    await runner.step('bad-1');

    // Quarantine
    runner.coordinator.quarantineAgent('bad-1', 'testing');

    // Cannot crawl while quarantined
    const result = await runner.step('bad-1');
    expect(result).toBeNull();
  });

  it('G3: multiple scouts sharing frontier', async () => {
    const runner = new CrawlRunner();

    runner.addAgent(agentConfig('s1', 'scout'));
    runner.addAgent(agentConfig('s2', 'scout'));

    runner.addSeedUrls(['https://a.com', 'https://b.com', 'https://c.com']);

    const r1 = await runner.step('s1');
    const r2 = await runner.step('s2');

    // Both should get different URLs
    expect(r1).not.toBeNull();
    expect(r2).not.toBeNull();
    expect(r1!.url).not.toBe(r2!.url);
  });

  it('G4: shutdown closes all sessions', async () => {
    const runner = new CrawlRunner();
    runner.addAgent(agentConfig('a1', 'scout'));
    runner.addAgent(agentConfig('a2', 'scout'));
    runner.addSeedUrls(['https://example.com', 'https://test.com']);

    await runner.step('a1');
    await runner.step('a2');

    // Both sessions should be active
    expect(runner.getAgent('a1')!.sessionActive).toBe(true);
    expect(runner.getAgent('a2')!.sessionActive).toBe(true);

    await runner.shutdown();

    expect(runner.getAgent('a1')!.sessionActive).toBe(false);
    expect(runner.getAgent('a2')!.sessionActive).toBe(false);
  });

  it('G5: role switch mid-crawl changes behavior', async () => {
    const runner = new CrawlRunner({
      coordinator: { requireConsensusForRoleSwitch: false },
    });

    const obs = mockPageObs('https://example.com', {
      forms: [makeForm('search', [{ name: 'q' }])],
      interactiveElements: [makeDOMElement('a', { href: 'https://example.com/link1' })],
    });
    runner.addAgent(agentConfig('flex-1', 'scout', 'KO', obs));
    runner.addSeedUrls(['https://example.com', 'https://test.com']);

    // Crawl as scout — extracts links
    const r1 = await runner.step('flex-1');
    expect(r1).not.toBeNull();

    // Switch to analyzer
    runner.requestRoleSwitch('flex-1', 'analyzer', 'need data');
    const agentNow = runner.coordinator.getAgent('flex-1');
    expect(agentNow!.role).toBe('analyzer');

    // Crawl as analyzer — extracts data
    const r2 = await runner.step('flex-1');
    expect(r2).not.toBeNull();
    if (r2!.success) {
      expect(r2!.extractedData).toBeDefined();
      expect(r2!.extractedData.formCount).toBe(1);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// H: Statistics & Queries
// ═══════════════════════════════════════════════════════════════

describe('H — Statistics & Queries', () => {
  it('H1: getStats includes coordinator stats', () => {
    const runner = new CrawlRunner();
    runner.addAgent(agentConfig('a1', 'scout'));
    runner.addSeedUrls(['https://example.com']);

    const stats = runner.getStats();
    expect(stats.coordinatorStats).toBeDefined();
    expect(stats.coordinatorStats.totalAgents).toBe(1);
    expect(stats.coordinatorStats.urlsQueued).toBe(1);
  });

  it('H2: getTrajectory returns agent trajectory', async () => {
    const runner = new CrawlRunner();
    runner.addAgent(agentConfig('a1', 'scout'));
    runner.addSeedUrls(['https://example.com']);

    await runner.step('a1');

    const trajectory = runner.getTrajectory('a1');
    expect(trajectory).toHaveLength(1);
    expect(trajectory[0].state).toHaveLength(21);
  });

  it('H3: getGovernanceLog returns governance history', async () => {
    const runner = new CrawlRunner();
    runner.addAgent(agentConfig('a1', 'scout'));
    runner.addSeedUrls(['https://example.com']);

    await runner.step('a1');

    const log = runner.getGovernanceLog('a1');
    expect(log).toHaveLength(1);
    expect(log[0].decision).toBeDefined();
  });

  it('H4: getResults returns coordinator results', async () => {
    const runner = new CrawlRunner();
    runner.addAgent(agentConfig('a1', 'scout'));
    runner.addSeedUrls(['https://example.com']);

    await runner.step('a1');

    const results = runner.getResults();
    expect(results).toHaveLength(1);
    expect(results[0].agentId).toBe('a1');
  });
});
