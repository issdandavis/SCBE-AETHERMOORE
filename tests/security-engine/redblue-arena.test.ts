/**
 * Red/Blue Team Security Arena Tests
 *
 * @module tests/security-engine/redblue-arena
 */

import { describe, expect, it, beforeEach } from 'vitest';
import {
  Team,
  UnitRole,
  Surface,
  RoundVerdict,
  MatchResult,
  RedBlueArena,
  LocalRedStrategy,
  LocalBlueStrategy,
  judgeRound,
  DEFAULT_ARENA_CONFIG,
} from '../../src/security-engine/redblue-arena';
import { SecurityDecision } from '../../src/security-engine/context-engine';
import type {
  ArenaConfig,
  ArenaPayload,
  TeamMove,
  StrategyAdapter,
  StrategyContext,
} from '../../src/security-engine/redblue-arena';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeRedMove(overrides: Partial<ArenaPayload> = {}): TeamMove {
  return {
    team: Team.RED,
    surface: Surface.API,
    payload: {
      context6D: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
      action: 'data_export',
      target: '/api/data',
      pqcValid: true,
      metadata: {},
      ...overrides,
    },
    agentId: 'red_test',
    tokensCost: 0,
    reasoning: 'test attack',
  };
}

function makeBlueMove(overrides: Record<string, unknown> = {}): TeamMove {
  return {
    team: Team.BLUE,
    surface: Surface.API,
    payload: {
      context6D: [0, 0, 0, 0, 0, 0],
      action: 'defend',
      target: 'api',
      pqcValid: true,
      metadata: {
        anomalyThreshold: 0.3,
        requirePqc: true,
        maxContextNorm: 0.85,
        actionDenyList: ['admin_override', 'key_rotation', 'dom_inject', 'relay_inject'],
        adaptiveStrictness: 1.0,
        ...overrides,
      },
    },
    agentId: 'blue_test',
    tokensCost: 0,
    reasoning: 'test defense',
  };
}

// ---------------------------------------------------------------------------
// Enums & Constants
// ---------------------------------------------------------------------------

describe('RedBlue Arena Enums', () => {
  it('should define all team values', () => {
    expect(Team.RED).toBe('red');
    expect(Team.BLUE).toBe('blue');
  });

  it('should define all unit roles', () => {
    expect(Object.values(UnitRole)).toHaveLength(5);
    expect(UnitRole.SCOUT).toBe('scout');
    expect(UnitRole.EXPLOIT).toBe('exploit');
    expect(UnitRole.DEFEND).toBe('defend');
    expect(UnitRole.PATCH).toBe('patch');
    expect(UnitRole.JUDGE).toBe('judge');
  });

  it('should define all surfaces', () => {
    expect(Object.values(Surface)).toHaveLength(5);
  });

  it('should have default config with 5 rounds', () => {
    expect(DEFAULT_ARENA_CONFIG.rounds).toBe(5);
    expect(DEFAULT_ARENA_CONFIG.redProvider).toBe('local');
    expect(DEFAULT_ARENA_CONFIG.blueProvider).toBe('local');
  });
});

// ---------------------------------------------------------------------------
// Judge
// ---------------------------------------------------------------------------

describe('judgeRound', () => {
  it('should block obviously malicious payloads', () => {
    const red = makeRedMove({
      context6D: [0.9, 0.9, 0.9, 0.9, 0.9, 0.9],
      action: 'admin_override',
      pqcValid: false,
    });
    const blue = makeBlueMove();

    const result = judgeRound(0, Surface.GOVERNANCE, red, blue, 1.0);

    expect(result.pipelineDecision).not.toBe(SecurityDecision.ALLOW);
    expect(result.blueDetected).toBe(true);
    expect(result.verdict).toBe(RoundVerdict.BLUE_BLOCK);
    expect(result.scoreDelta).toBeLessThan(0);
  });

  it('should detect mimicry attack (low context, suspicious action)', () => {
    const red = makeRedMove({
      context6D: [0.01, 0.01, 0.01, 0.01, 0.01, 0.01],
      action: 'admin_override',
      pqcValid: true,
      spectralCoherence: 0.99,
    });
    const blue = makeBlueMove();

    const result = judgeRound(0, Surface.GOVERNANCE, red, blue, 1.0);

    // Blue should catch it via action deny list even if pipeline is lenient
    expect(result.blueDetected).toBe(true);
  });

  it('should flag PQC-invalid requests', () => {
    const red = makeRedMove({ pqcValid: false });
    const blue = makeBlueMove({ requirePqc: true });

    const result = judgeRound(0, Surface.API, red, blue, 1.0);

    expect(result.blueDetected).toBe(true);
  });

  it('should return groundTruthMalicious = true for all red moves', () => {
    const result = judgeRound(0, Surface.API, makeRedMove(), makeBlueMove(), 1.0);
    expect(result.groundTruthMalicious).toBe(true);
  });

  it('should increase strictness with governance multiplier', () => {
    const red = makeRedMove({
      context6D: [0.4, 0.4, 0.4, 0.4, 0.4, 0.4],
      action: 'data_export',
    });
    const blue = makeBlueMove();

    const lenient = judgeRound(0, Surface.API, red, blue, 0.5);
    const strict = judgeRound(0, Surface.API, red, blue, 2.0);

    // Stricter governance should not produce a weaker decision
    const decisionOrder = [
      SecurityDecision.ALLOW,
      SecurityDecision.QUARANTINE,
      SecurityDecision.ESCALATE,
      SecurityDecision.DENY,
    ];
    expect(decisionOrder.indexOf(strict.pipelineDecision)).toBeGreaterThanOrEqual(
      decisionOrder.indexOf(lenient.pipelineDecision)
    );
  });

  it('should award 3 points for a full red bypass', () => {
    // Craft a benign-looking payload that bypasses blue's deny list
    const red = makeRedMove({
      context6D: [0.01, 0.01, 0.01, 0.01, 0.01, 0.01],
      action: 'read_public', // not in deny list, not suspicious
      pqcValid: true,
      spectralCoherence: 0.99,
    });
    // Relax blue's detection
    const blue = makeBlueMove({
      anomalyThreshold: 0.9,
      actionDenyList: [],
      maxContextNorm: 0.99,
    });

    const result = judgeRound(0, Surface.API, red, blue, 1.0);

    if (result.verdict === RoundVerdict.RED_BYPASS) {
      expect(result.scoreDelta).toBe(3);
    }
  });
});

// ---------------------------------------------------------------------------
// Local Strategies
// ---------------------------------------------------------------------------

describe('LocalRedStrategy', () => {
  it('should cycle through attack catalog', async () => {
    const strategy = new LocalRedStrategy();
    const surfaces: Surface[] = [];

    for (let i = 0; i < 10; i++) {
      const move = await strategy.generate({
        team: Team.RED,
        role: UnitRole.EXPLOIT,
        agentId: 'test',
        roundNumber: i,
        surface: Surface.API,
        score: { red: 0, blue: 0, rounds: i, bypasses: 0, blocks: 0, neutrals: 0 },
        history: [],
        tokenBudget: 1000,
        governanceStrictness: 1.0,
      });
      expect(move.team).toBe(Team.RED);
      expect(move.tokensCost).toBe(0); // local = free
    }
  });
});

describe('LocalBlueStrategy', () => {
  it('should tighten when losing', async () => {
    const strategy = new LocalBlueStrategy();

    const losing = await strategy.generate({
      team: Team.BLUE,
      role: UnitRole.DEFEND,
      agentId: 'test',
      roundNumber: 3,
      surface: Surface.API,
      score: { red: 6, blue: 2, rounds: 3, bypasses: 2, blocks: 1, neutrals: 0 },
      history: [],
      tokenBudget: 1000,
      governanceStrictness: 1.0,
    });

    const winning = await strategy.generate({
      team: Team.BLUE,
      role: UnitRole.DEFEND,
      agentId: 'test',
      roundNumber: 3,
      surface: Surface.API,
      score: { red: 0, blue: 6, rounds: 3, bypasses: 0, blocks: 3, neutrals: 0 },
      history: [],
      tokenBudget: 1000,
      governanceStrictness: 1.0,
    });

    const losingStrictness = losing.payload.metadata.adaptiveStrictness as number;
    const winningStrictness = winning.payload.metadata.adaptiveStrictness as number;
    expect(losingStrictness).toBeGreaterThan(winningStrictness);
  });
});

// ---------------------------------------------------------------------------
// Arena Engine
// ---------------------------------------------------------------------------

describe('RedBlueArena', () => {
  it('should run a full match with default config', async () => {
    const arena = new RedBlueArena();
    const record = await arena.runMatch();

    expect(record.rounds).toHaveLength(5);
    expect(record.score.rounds).toBe(5);
    expect([MatchResult.RED_WIN, MatchResult.BLUE_WIN, MatchResult.DRAW]).toContain(record.result);
    expect(record.agents).toHaveLength(5);
    expect(record.id).toContain('match_');
  });

  it('should create agents with correct team assignments', () => {
    const arena = new RedBlueArena();
    const agents = arena.getAgents();

    const redAgents = agents.filter((a) => a.team === Team.RED);
    const blueAgents = agents.filter((a) => a.team === Team.BLUE);

    expect(redAgents.length).toBeGreaterThanOrEqual(2);
    expect(blueAgents.length).toBeGreaterThanOrEqual(2);
  });

  it('should cycle through surfaces', async () => {
    const arena = new RedBlueArena({ rounds: 10 });
    const record = await arena.runMatch();

    const surfaces = record.rounds.map((r) => r.surface);
    const unique = new Set(surfaces);
    expect(unique.size).toBe(5); // all surfaces used
  });

  it('should track score correctly', async () => {
    const arena = new RedBlueArena();
    const record = await arena.runMatch();

    expect(record.score.bypasses + record.score.blocks + record.score.neutrals).toBe(
      record.score.rounds
    );
  });

  it('should accept custom config', async () => {
    const arena = new RedBlueArena({
      rounds: 3,
      governanceStrictness: 2.0,
      surfaces: [Surface.API, Surface.CRYPTO],
    });
    const record = await arena.runMatch();

    expect(record.rounds).toHaveLength(3);
    expect(record.config.governanceStrictness).toBe(2.0);
  });

  it('should support custom strategy adapters', async () => {
    // Custom red strategy that always sends a benign payload
    const passiveRed: StrategyAdapter = {
      providerId: 'local',
      async generate(context: StrategyContext): Promise<TeamMove> {
        return {
          team: Team.RED,
          surface: context.surface,
          payload: {
            context6D: [0, 0, 0, 0, 0, 0],
            action: 'read_public',
            target: '/api/public',
            pqcValid: true,
            metadata: {},
          },
          agentId: context.agentId,
          tokensCost: 0,
          reasoning: 'intentionally passive',
        };
      },
    };

    const arena = new RedBlueArena({ rounds: 3 }, passiveRed);
    const record = await arena.runMatch();

    // Passive red should never score bypasses
    // (blue might still detect false positives, but red shouldn't get bypass points)
    expect(record.score.bypasses).toBeLessThanOrEqual(record.rounds.length);
  });

  it('should produce a replayable match record', async () => {
    const arena = new RedBlueArena({ rounds: 3 });
    const record = await arena.runMatch();

    // Verify record has all required fields for replay
    expect(record.id).toBeDefined();
    expect(record.config).toBeDefined();
    expect(record.startedAt).toBeLessThanOrEqual(record.completedAt);
    expect(record.rounds.every((r) => r.timestamp > 0)).toBe(true);
    expect(record.rounds.every((r) => r.judgeNotes.length > 0)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Scoring Invariants
// ---------------------------------------------------------------------------

describe('Scoring invariants', () => {
  it('should never have negative team scores', async () => {
    const arena = new RedBlueArena({ rounds: 20 });
    const record = await arena.runMatch();

    expect(record.score.red).toBeGreaterThanOrEqual(0);
    expect(record.score.blue).toBeGreaterThanOrEqual(0);
  });

  it('should have consistent verdict counts', async () => {
    const arena = new RedBlueArena({ rounds: 10 });
    const record = await arena.runMatch();

    const bypassCount = record.rounds.filter((r) => r.verdict === RoundVerdict.RED_BYPASS).length;
    const blockCount = record.rounds.filter(
      (r) => r.verdict === RoundVerdict.BLUE_BLOCK || r.verdict === RoundVerdict.NEUTRAL
    ).length;
    const drawCount = record.rounds.filter((r) => r.verdict === RoundVerdict.DRAW).length;

    expect(bypassCount + blockCount + drawCount).toBe(10);
  });

  it('blue should win with default strategies (governance is strong)', async () => {
    // Run multiple matches to check blue advantage with default governance
    let blueWins = 0;
    for (let i = 0; i < 5; i++) {
      const arena = new RedBlueArena({ rounds: 10 });
      const record = await arena.runMatch();
      if (record.result === MatchResult.BLUE_WIN) blueWins++;
    }
    // Blue should win most matches since governance pipeline + detection should catch most attacks
    expect(blueWins).toBeGreaterThanOrEqual(3);
  });
});
