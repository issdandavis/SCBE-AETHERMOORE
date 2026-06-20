#!/usr/bin/env node
/**
 * Smoke: governanceAbacus (BigInt mechanical) vs canonical harmonicScale (float).
 *
 * Verifies the abacus matches the canonical L12 formula to within the
 * abacus scale (1e-6 by default), across a range of representative inputs.
 */

const { runGovernanceAbacus } = require("../../dist/src/harmonic/governanceAbacus.js");
const { harmonicScale } = require("../../dist/src/harmonic/harmonicScaling.js");

const SAMPLES = [
  { d_h: 0.0, phase_dev: 0.0 },
  { d_h: 0.1, phase_dev: 0.0 },
  { d_h: 0.4, phase_dev: 0.1 },
  { d_h: 0.6, phase_dev: 0.0 },
  { d_h: 1.0, phase_dev: 0.0 },
  { d_h: 2.0, phase_dev: 0.5 },
  { d_h: 5.0, phase_dev: 1.0 },
];

const TOLERANCE = 1e-6;

function tierFromFloat(h) {
  if (h >= 0.65) return "ALLOW";
  if (h >= 0.45) return "QUARANTINE";
  if (h >= 0.25) return "ESCALATE";
  return "DENY";
}

let failed = 0;
for (const sample of SAMPLES) {
  const run = runGovernanceAbacus(sample);
  const floatScore = harmonicScale(sample.d_h, sample.phase_dev);
  const abacusScore = Number(run.score_decimal);
  const delta = Math.abs(floatScore - abacusScore);
  const floatTier = tierFromFloat(floatScore);
  const ok = delta <= TOLERANCE && floatTier === run.tier;
  if (!ok) failed += 1;
  console.log(
    `${ok ? "PASS" : "FAIL"}  d_h=${sample.d_h.toFixed(4)} pd=${sample.phase_dev.toFixed(4)}  ` +
      `float=${floatScore.toFixed(8)}  abacus=${run.score_decimal}  delta=${delta.toExponential(2)}  ` +
      `tier(float=${floatTier} abacus=${run.tier})  trit=${run.trit}`
  );
}

if (failed === 0) {
  console.log(`\nAll ${SAMPLES.length} samples within tolerance ${TOLERANCE}.`);
  process.exit(0);
}
console.log(`\n${failed}/${SAMPLES.length} samples FAILED.`);
process.exit(1);
