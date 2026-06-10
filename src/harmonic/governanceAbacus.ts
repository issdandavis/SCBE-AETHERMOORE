/**
 * @file governanceAbacus.ts
 * @module harmonic/governanceAbacus
 * @layer Layer 12, Layer 13
 * @component Governance Abacus (deterministic mechanical scoring)
 * @version 1.0.0
 *
 * Exact-arithmetic mechanical implementation of the L12 harmonic wall scoring +
 * L13 tier assignment. All computation runs in BigInt with a fixed scale; no
 * floating-point arithmetic, no platform-dependent drift.
 *
 * "Like an abacus": each input is quantized to a discrete bead position on a
 * rod (an integer). The harmonic-wall computation is a sequence of integer
 * additions and one integer division. The tier is read from the score rod by
 * comparing against fixed integer thresholds. Same inputs → same beads → same
 * tier on every platform, forever.
 *
 * Canonical formula (matches `harmonicScale` in harmonicScaling.ts exactly):
 *   H(d_h, pd) = 1 / (1 + d_h + 2*pd)  ∈ (0, 1]
 *
 * The L13 tier mapping is:
 *   H >= 0.65 → ALLOW
 *   H >= 0.45 → QUARANTINE
 *   H >= 0.25 → ESCALATE
 *   H <  0.25 → DENY
 *
 * Output is BOTH the four-tier governance decision and a balanced-ternary
 * collapse for tri-state surfaces:
 *   +1 = ALLOW         (safe)
 *    0 = QUARANTINE or ESCALATE  (uncertain)
 *   -1 = DENY          (unsafe)
 *
 * Phi does NOT enter this formula. Phi-weighted tongue scoring is a separate
 * abacus (per-tongue, future extension). See docs/ABACUS_ARCHITECTURE.md for
 * the multi-abacus roadmap.
 *
 * Public API:
 *   - runGovernanceAbacus({ d_h, phase_dev }) → AbacusRun
 *   - formatAbacusBoard(run) → string (human-readable bead display)
 *
 * @see src/harmonic/balancedTernary.ts — the tri-state primitive
 * @see src/harmonic/harmonicScaling.ts — the canonical float version of H_score
 */

import type { Trit } from './balancedTernary.js';

export type GovernanceTier = 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';

export interface AbacusConfig {
  /** Bead-grid resolution. Default 1_000_000 (6 decimal places of input precision). */
  scale?: bigint;
}

export interface AbacusInput {
  /** Hyperbolic distance from the safe center, d_h ≥ 0. */
  d_h: number;
  /** Phase deviation from expected coherence, pd ≥ 0. */
  phase_dev: number;
}

/**
 * Tier thresholds, expressed as score lower bounds. A score >= 0.65 is ALLOW,
 * >= 0.45 is QUARANTINE, >= 0.25 is ESCALATE, otherwise DENY. Stored as
 * rationals so the comparison is exact.
 */
export const TIER_THRESHOLDS: ReadonlyArray<{
  tier: GovernanceTier;
  minScoreNum: bigint;
  minScoreDen: bigint;
}> = [
  { tier: 'ALLOW', minScoreNum: 65n, minScoreDen: 100n },
  { tier: 'QUARANTINE', minScoreNum: 45n, minScoreDen: 100n },
  { tier: 'ESCALATE', minScoreNum: 25n, minScoreDen: 100n },
  { tier: 'DENY', minScoreNum: 0n, minScoreDen: 1n },
];

export interface AbacusBead {
  /** Rod label (human-readable). */
  rod: string;
  /** Integer bead position on the rod. */
  position: bigint;
  /** Scale (denominator) for converting position to a real number. */
  scale: bigint;
  /** Decoded human-readable value. */
  display: string;
}

export interface AbacusRun {
  /** Original input values (echo for trace). */
  input: AbacusInput;
  /** Configuration in effect (with defaults filled in). */
  config: Required<AbacusConfig>;
  /** Bead positions on each rod after the run. */
  beads: {
    d_h: AbacusBead;
    phase_dev: AbacusBead;
    /** Denominator rod: 1 + d_h + 2*pd (scaled). */
    denominator: AbacusBead;
    /** Final score rod: scale^2 / denominator. */
    score: AbacusBead;
  };
  /** Exact score as a rational number. */
  score: { num: bigint; den: bigint };
  /** Score as a decimal string with explicit precision (no float). */
  score_decimal: string;
  /** Four-tier governance decision. */
  tier: GovernanceTier;
  /** Balanced-ternary collapse: +1 ALLOW, 0 uncertain, -1 DENY. */
  trit: Trit;
}

function quantize(value: number, scale: bigint): bigint {
  if (!Number.isFinite(value)) {
    throw new RangeError(`abacus input must be finite, got ${value}`);
  }
  if (value < 0) {
    throw new RangeError(`abacus input must be >= 0, got ${value}`);
  }
  // Round half-away-from-zero (since value >= 0, this is just round half up).
  const scaled = Math.round(value * Number(scale));
  return BigInt(scaled);
}

function formatScaled(position: bigint, scale: bigint, decimals: number): string {
  // position / scale, rendered with `decimals` digits after the point.
  if (decimals < 0 || decimals > 18) {
    throw new RangeError('decimals must be in [0, 18]');
  }
  const sign = position < 0n ? '-' : '';
  const abs = position < 0n ? -position : position;
  const whole = abs / scale;
  const remainder = abs - whole * scale;
  if (decimals === 0) {
    return `${sign}${whole.toString()}`;
  }
  // Render fractional part by re-scaling.
  const tenPow = 10n ** BigInt(decimals);
  const fracRescaled = (remainder * tenPow) / scale;
  const fracStr = fracRescaled.toString().padStart(decimals, '0');
  return `${sign}${whole.toString()}.${fracStr}`;
}

function tierFor(scoreNum: bigint, scoreDen: bigint): GovernanceTier {
  // Compare score = scoreNum/scoreDen against each threshold minScoreNum/minScoreDen.
  // score >= threshold  ⟺  scoreNum * thresholdDen >= thresholdNum * scoreDen
  for (const t of TIER_THRESHOLDS) {
    if (scoreNum * t.minScoreDen >= t.minScoreNum * scoreDen) {
      return t.tier;
    }
  }
  return 'DENY';
}

function tritFor(tier: GovernanceTier): Trit {
  if (tier === 'ALLOW') return 1;
  if (tier === 'DENY') return -1;
  return 0;
}

/**
 * Run the governance abacus on a single input. Pure, deterministic, BigInt-only.
 *
 * Matches the canonical `harmonicScale(d_h, phase_dev)` from harmonicScaling.ts
 * to within the configured `scale` (default 1e6 = 6 decimal places). The exact
 * rational score is also returned for consumers that want zero-loss audit
 * trails.
 *
 * @example
 *   const run = runGovernanceAbacus({ d_h: 0.4, phase_dev: 0.1 });
 *   // run.tier === 'QUARANTINE'
 *   // run.trit === 0
 *   // run.score_decimal === '0.625000'
 */
export function runGovernanceAbacus(input: AbacusInput, config: AbacusConfig = {}): AbacusRun {
  const scale = config.scale ?? 1_000_000n;
  if (scale <= 0n) {
    throw new RangeError('scale must be a positive bigint');
  }

  // Quantize inputs to bead positions on their rods.
  const d_h_pos = quantize(input.d_h, scale);
  const pd_pos = quantize(input.phase_dev, scale);

  // Compute denominator = 1 + d_h + 2*pd, all in `scale` units.
  //   scaled_one        = scale
  //   scaled_d_h        = d_h_pos
  //   scaled_two_pd     = 2 * pd_pos
  const denPos = scale + d_h_pos + 2n * pd_pos;
  if (denPos <= 0n) {
    throw new RangeError(
      'abacus denominator collapsed to zero (impossible for non-negative inputs)'
    );
  }

  // score = 1 / (1 + d_h + 2*pd)
  //       = scale / denPos    (as a rational; both numerator and denominator are in `scale` units)
  // For the bead display, render score * scale rounded to integer.
  const scorePos = (scale * scale) / denPos;

  // Exact rational score.
  const scoreNum = scale; // numerator in `scale` units
  const scoreDen = denPos;

  const tier = tierFor(scoreNum, scoreDen);
  const trit = tritFor(tier);

  const scoreDecimals = 6;
  const score_decimal = formatScaled(scorePos, scale, scoreDecimals);

  return {
    input,
    config: { scale },
    beads: {
      d_h: {
        rod: 'd_h',
        position: d_h_pos,
        scale,
        display: formatScaled(d_h_pos, scale, 6),
      },
      phase_dev: {
        rod: 'phase_dev',
        position: pd_pos,
        scale,
        display: formatScaled(pd_pos, scale, 6),
      },
      denominator: {
        rod: 'denominator',
        position: denPos,
        scale,
        display: formatScaled(denPos, scale, 6),
      },
      score: {
        rod: 'score',
        position: scorePos,
        scale,
        display: score_decimal,
      },
    },
    score: { num: scoreNum, den: scoreDen },
    score_decimal,
    tier,
    trit,
  };
}

/**
 * Render an abacus run as a human-readable bead board.
 */
export function formatAbacusBoard(run: AbacusRun): string {
  const lines = [
    `SCBE Governance Abacus (deterministic, BigInt-only)`,
    ``,
    `  formula: H(d_h, pd) = 1 / (1 + d_h + 2*pd)`,
    `  config:  scale=${run.config.scale.toString()}`,
    ``,
    `  rod          | bead position                         | reads as`,
    `  -------------+---------------------------------------+----------`,
    `  d_h          | ${run.beads.d_h.position.toString().padStart(37, ' ')} | ${run.beads.d_h.display}`,
    `  phase_dev    | ${run.beads.phase_dev.position.toString().padStart(37, ' ')} | ${run.beads.phase_dev.display}`,
    `  denominator  | ${run.beads.denominator.position.toString().padStart(37, ' ')} | ${run.beads.denominator.display}`,
    `  score        | ${run.beads.score.position.toString().padStart(37, ' ')} | ${run.score_decimal}`,
    ``,
    `  exact score: ${run.score.num.toString()} / ${run.score.den.toString()}`,
    `  tier:        ${run.tier}`,
    `  trit:        ${run.trit > 0 ? '+' : ''}${run.trit}    (${run.trit === 1 ? 'ALLOW' : run.trit === -1 ? 'DENY' : 'uncertain'})`,
    ``,
  ];
  return lines.join('\n');
}
