import type { EnforcementContext, EnforcementRequest } from './offline_mode.js';

export interface MMXScalars {
  mm_coherence: number;
  mm_conflict: number;
  mm_drift: number;
  wall_cost: number;
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  if (value <= 0) return 0;
  if (value >= 1) return 1;
  return value;
}

function meanAbs(values: Float64Array): number {
  if (values.length === 0) return 0;
  let sum = 0;
  for (const v of values) sum += Math.abs(v);
  return sum / values.length;
}

function variance(values: Float64Array): number {
  if (values.length === 0) return 0;
  let mean = 0;
  for (const v of values) mean += v;
  mean /= values.length;
  let acc = 0;
  for (const v of values) {
    const d = v - mean;
    acc += d * d;
  }
  return acc / values.length;
}

export function mmx(
  request: EnforcementRequest,
  context: EnforcementContext,
): MMXScalars {
  const actionEntropy = (request.action.length + request.subject.length + request.object.length) % 101;
  const actionSignal = actionEntropy / 100;

  if (!context.modality_embeddings || context.modality_embeddings.length === 0) {
    const coherence = clamp01(0.55 + actionSignal * 0.35);
    const conflict = clamp01(1 - coherence);
    const drift = clamp01(0.35 + (1 - coherence) * 0.5);
    const wall = clamp01((conflict + drift) / 2);
    return {
      mm_coherence: coherence,
      mm_conflict: conflict,
      mm_drift: drift,
      wall_cost: wall,
    };
  }

  const embeds = context.modality_embeddings;
  const mag = clamp01(meanAbs(embeds));
  const spread = clamp01(variance(embeds));
  const coherence = clamp01(1 - spread * 0.8 + (1 - mag) * 0.1);
  const conflict = clamp01(spread * 0.9 + actionSignal * 0.1);
  const drift = clamp01((1 - coherence) * 0.7 + mag * 0.2 + actionSignal * 0.1);
  const wall = clamp01((conflict * 0.55 + drift * 0.45) * 1.1);

  return {
    mm_coherence: coherence,
    mm_conflict: conflict,
    mm_drift: drift,
    wall_cost: wall,
  };
}

