import { describe, expect, it } from 'vitest';
import { scbeSacredEggCreate, scbeSacredEggHatch, scbeStateEmit21D } from '../../mcp/scbe-server/server.mjs';

describe('SCBE MCP Server Phase 1 Tools', () => {
  it('emits canonical 21D state telemetry', () => {
    const vector = Array.from({ length: 21 }, (_, i) => (i + 1) / 100);
    const result = scbeStateEmit21D({
      vector,
      apply_golden_weighting: true,
      decision: 'ALLOW',
      confidence: 0.92,
      metadata: { source: 'unit-test' },
    });

    expect(result.schema_version).toBe('scbe-21d-v1');
    expect(result.vector_21d).toHaveLength(21);
    expect(result.blocks.tongue_position).toHaveLength(6);
    expect(result.blocks.phase).toHaveLength(6);
    expect(result.blocks.telemetry).toHaveLength(9);
    expect(result.projections.poincare_norm).toBeLessThan(1);
    expect(result.state_id).toHaveLength(16);
    expect(result.hashes.state_sha256).toHaveLength(64);
    expect(result.hashes.state_sha512).toHaveLength(128);
  });

  it('rejects non-21D vectors', () => {
    expect(() => scbeStateEmit21D({ vector: [1, 2, 3] })).toThrow(/exactly 21/i);
  });

  it('creates and hatches a sacred egg in solitary mode', () => {
    const payloadB64 = Buffer.from('phase1-egg-payload', 'utf8').toString('base64');
    const context = [0.1, -0.2, 0.3, 0.5, -0.1, 0.0];
    const egg = scbeSacredEggCreate({
      payload_b64: payloadB64,
      primary_tongue: 'KO',
      glyph: '◇',
      hatch_condition: { path: 'interior' },
      context,
    });

    const hatch = scbeSacredEggHatch({
      egg_json: egg,
      context,
      agent_tongue: 'KO',
      ritual_mode: 'solitary',
    });

    expect(egg.egg_id).toHaveLength(16);
    expect(egg.primary_tongue).toBe('KO');
    expect(hatch.success).toBe(true);
    expect(hatch.reason).toBe('hatched');
    expect(hatch.payload_b64).toBe(payloadB64);
    expect(Array.isArray(hatch.tokens)).toBe(true);
    expect(hatch.tokens.length).toBeGreaterThan(0);
  });

  it('returns fail-to-noise when solitary tongue does not match', () => {
    const payloadB64 = Buffer.from('sealed-message', 'utf8').toString('base64');
    const context = [0.2, 0.1, -0.3, 0.0, 0.5, -0.2];
    const egg = scbeSacredEggCreate({
      payload_b64: payloadB64,
      primary_tongue: 'KO',
      hatch_condition: { path: 'interior' },
      context,
    });

    const hatch = scbeSacredEggHatch({
      egg_json: egg,
      context,
      agent_tongue: 'AV',
      ritual_mode: 'solitary',
    });

    expect(hatch.success).toBe(false);
    expect(hatch.reason).toBe('sealed');
    expect(hatch.reason_code).toBe('TONGUE_MISMATCH');
    expect(Array.isArray(hatch.tokens)).toBe(true);
    expect(hatch.tokens.length).toBeGreaterThan(0);
  });

  it('enforces triadic minimum tongues and minimum weight', () => {
    const payloadB64 = Buffer.from('triadic-gate', 'utf8').toString('base64');
    const context = [0.12, 0.22, 0.18, 0.06, -0.1, 0.03];
    const egg = scbeSacredEggCreate({
      payload_b64: payloadB64,
      primary_tongue: 'KO',
      hatch_condition: { path: 'interior', min_tongues: 3, min_weight: 10.0 },
      context,
    });

    const fail = scbeSacredEggHatch({
      egg_json: egg,
      context,
      agent_tongue: 'KO',
      ritual_mode: 'triadic',
      additional_tongues: ['AV'],
    });
    expect(fail.success).toBe(false);
    expect(fail.reason).toBe('sealed');

    const pass = scbeSacredEggHatch({
      egg_json: egg,
      context,
      agent_tongue: 'KO',
      ritual_mode: 'triadic',
      additional_tongues: ['RU', 'UM'],
    });
    expect(pass.success).toBe(true);
    expect(pass.reason).toBe('hatched');
    expect(pass.payload_b64).toBe(payloadB64);
  });
});

