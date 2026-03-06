/**
 * @file scbeGate.ts
 * @module conference/governance
 * @layer Layer 1-14
 *
 * SCBE Governance Gate for the Vibe Coder Conference App.
 *
 * Runs a simplified version of the 14-layer pipeline against project
 * capsule data to produce ALLOW/QUARANTINE/ESCALATE/DENY decisions.
 * This is the "guardian angel" that scores every project before it can
 * appear on the main stage.
 *
 * Integration points:
 * - L1-L5: Embed context, compute hyperbolic distance and basic risk/novelty scores
 * - L6-L13: Breathing, realms, coherence, harmonic scaling, final decision
 * - L14: Emit governance telemetry as badges and risk ribbons
 */

import type {
  ProjectCapsule,
  GovernanceResult,
  GovernanceDecision,
  LayerScore,
  HydraAuditResult,
  HydraAgentReport,
} from '../types/index.js';

// ═══════════════════════════════════════════════════════════════
// L5: Hyperbolic Distance (Poincaré ball model)
// ═══════════════════════════════════════════════════════════════

/**
 * Compute the hyperbolic distance in the Poincaré ball model.
 * dH = arcosh(1 + 2‖u-v‖² / ((1-‖u‖²)(1-‖v‖²)))
 *
 * @param u - Point in the Poincaré ball
 * @param v - Point in the Poincaré ball
 */
export function hyperbolicDistance(u: number[], v: number[]): number {
  const diffNormSq = u.reduce((s, ui, i) => s + (ui - v[i]) ** 2, 0);
  const uNormSq = u.reduce((s, ui) => s + ui * ui, 0);
  const vNormSq = v.reduce((s, vi) => s + vi * vi, 0);

  const denom = (1 - uNormSq) * (1 - vNormSq);
  if (denom <= 0) return Infinity;

  const arg = 1 + (2 * diffNormSq) / denom;
  return Math.acosh(Math.max(1, arg));
}

// ═══════════════════════════════════════════════════════════════
// L12: Harmonic Scaling (bounded safety score)
// ═══════════════════════════════════════════════════════════════

/**
 * Harmonic wall: H(d, pd) = 1 / (1 + d_H + 2*pd)
 * Returns a score in (0, 1] — higher is safer.
 */
export function harmonicScore(dH: number, phaseDivergence: number): number {
  return 1 / (1 + dH + 2 * phaseDivergence);
}

// ═══════════════════════════════════════════════════════════════
// L6: Breathing Factor
// ═══════════════════════════════════════════════════════════════

/**
 * L6-style breathing factor: b(t) = 1 + A·sin(ωt), clamped.
 * Used for time-dependent policy modulation.
 */
export function breathingFactor(
  tSec: number,
  amplitude: number = 0.25,
  omega: number = (2 * Math.PI) / 60
): number {
  const b = 1 + amplitude * Math.sin(omega * tSec);
  return Math.max(0.25, Math.min(2.5, b));
}

// ═══════════════════════════════════════════════════════════════
// Context Embedding (L1-L4)
// ═══════════════════════════════════════════════════════════════

/** Safe center in 6D Poincaré ball (origin) */
const SAFE_CENTER = [0, 0, 0, 0, 0, 0];

/**
 * Embed project capsule data into a 6D context vector.
 * Each dimension maps to a Sacred Tongue:
 *   KO (control), AV (I/O), RU (policy), CA (math), UM (security), DR (truth)
 *
 * Scores are derived from capsule metadata heuristics.
 */
function embedProjectContext(capsule: ProjectCapsule): number[] {
  // KO: Has repo + demo (completeness)
  const ko = (capsule.repoUrl ? 0.1 : 0) + (capsule.demoUrl ? 0.1 : 0) + (capsule.videoUrl ? 0.05 : 0);

  // AV: Description richness
  const descLen = capsule.description.length;
  const av = Math.min(0.2, descLen / 5000);

  // RU: Tech stack diversity
  const ru = Math.min(0.2, capsule.techStack.length * 0.03);

  // CA: Funding ask reasonableness (penalize extremes)
  const askAmount = capsule.fundingAsk.amount;
  const ca = askAmount > 0 && askAmount < 10_000_000 ? 0.1 : 0.18;

  // UM: Has pitch deck (security/trust signal)
  const um = capsule.pitchDeckUrl ? 0.05 : 0.12;

  // DR: Tagline quality (non-empty, reasonable length)
  const dr = capsule.tagline.length > 5 && capsule.tagline.length < 200 ? 0.05 : 0.15;

  return [ko, av, ru, ca, um, dr];
}

// ═══════════════════════════════════════════════════════════════
// L13: Decision Function
// ═══════════════════════════════════════════════════════════════

function makeDecision(hScore: number, coherence: number): GovernanceDecision {
  if (hScore >= 0.6 && coherence >= 0.7) return 'ALLOW';
  if (hScore >= 0.4 && coherence >= 0.4) return 'QUARANTINE';
  if (hScore >= 0.2 || coherence >= 0.2) return 'ESCALATE';
  return 'DENY';
}

function riskLabel(decision: GovernanceDecision): 'low' | 'medium' | 'high' | 'critical' {
  switch (decision) {
    case 'ALLOW': return 'low';
    case 'QUARANTINE': return 'medium';
    case 'ESCALATE': return 'high';
    case 'DENY': return 'critical';
  }
}

// ═══════════════════════════════════════════════════════════════
// Main Pipeline
// ═══════════════════════════════════════════════════════════════

/**
 * Run the SCBE governance pipeline against a project capsule.
 *
 * This is a simplified in-process version; in production, this
 * would call the full 14-layer pipeline service.
 */
export function scoreProject(capsule: ProjectCapsule): GovernanceResult {
  const layers: LayerScore[] = [];

  // L1-L2: Complex context → realification
  const contextVec = embedProjectContext(capsule);
  layers.push({ layer: 1, name: 'Complex Context', score: 1.0, passed: true });
  layers.push({ layer: 2, name: 'Realify', score: 1.0, passed: true });

  // L3-L4: Weighted metric → Poincaré embedding
  const vecNorm = Math.sqrt(contextVec.reduce((s, x) => s + x * x, 0));
  const clampedNorm = Math.min(vecNorm, 0.95);
  layers.push({ layer: 3, name: 'Langues Metric', score: clampedNorm, passed: true });
  layers.push({ layer: 4, name: 'Poincaré Embed', score: clampedNorm < 0.95 ? 1.0 : 0.8, passed: true });

  // L5: Hyperbolic distance from safe center
  const dH = hyperbolicDistance(contextVec, SAFE_CENTER);
  const l5Pass = dH < 3.0;
  layers.push({ layer: 5, name: 'Hyperbolic Distance', score: dH, passed: l5Pass, note: `dH=${dH.toFixed(4)}` });

  // L6: Breathing transform (time-dependent modulation)
  const bFactor = breathingFactor(Date.now() / 1000);
  const breathAdjustedDH = dH * bFactor;
  layers.push({ layer: 6, name: 'Breathing Transform', score: bFactor, passed: true, note: `b(t)=${bFactor.toFixed(4)}` });

  // L7: Phase (Möbius rotation) — simplified phase divergence
  const phaseDivergence = Math.abs(Math.sin(vecNorm * Math.PI));
  layers.push({ layer: 7, name: 'Möbius Phase', score: 1 - phaseDivergence, passed: phaseDivergence < 0.8 });

  // L8: Multi-well realms
  layers.push({ layer: 8, name: 'Realms', score: 1.0, passed: true });

  // L9-L10: Spectral + spin coherence
  const coherence = Math.max(0, 1 - breathAdjustedDH / 5);
  layers.push({ layer: 9, name: 'Spectral Coherence', score: coherence, passed: coherence > 0.3 });
  layers.push({ layer: 10, name: 'Spin Coherence', score: coherence, passed: coherence > 0.3 });

  // L11: Triadic distance
  layers.push({ layer: 11, name: 'Triadic Distance', score: 1.0, passed: true });

  // L12: Harmonic scaling
  const hScore = harmonicScore(breathAdjustedDH, phaseDivergence);
  layers.push({ layer: 12, name: 'Harmonic Scaling', score: hScore, passed: hScore > 0.3, note: `H=${hScore.toFixed(4)}` });

  // L13: Decision
  const decision = makeDecision(hScore, coherence);
  layers.push({ layer: 13, name: 'Decision Gate', score: decision === 'ALLOW' ? 1 : decision === 'QUARANTINE' ? 0.5 : 0, passed: decision !== 'DENY' });

  // L14: Telemetry axis
  layers.push({ layer: 14, name: 'Audio Axis', score: 1.0, passed: true });

  return {
    decision,
    coherence,
    hyperbolicDistance: dH,
    harmonicScore: hScore,
    noveltyScore: Math.min(1, dH / 3),
    riskLabel: riskLabel(decision),
    layerSummary: layers,
    scoredAt: new Date().toISOString(),
  };
}

// ═══════════════════════════════════════════════════════════════
// HYDRA Swarm Audit (Simulated)
// ═══════════════════════════════════════════════════════════════

const TONGUE_AGENTS: Array<{ tongue: HydraAgentReport['tongue']; role: string }> = [
  { tongue: 'KO', role: 'SCOUT' },
  { tongue: 'AV', role: 'VISION' },
  { tongue: 'RU', role: 'READER' },
  { tongue: 'CA', role: 'CLICKER' },
  { tongue: 'UM', role: 'TYPER' },
  { tongue: 'DR', role: 'JUDGE' },
];

/**
 * Simulate a HYDRA swarm browser audit of a project.
 * In production, this would dispatch actual browser agents.
 */
export function auditProject(capsule: ProjectCapsule): HydraAuditResult {
  const agents: HydraAgentReport[] = TONGUE_AGENTS.map(({ tongue, role }) => {
    const findings: string[] = [];
    let score = 0.8;

    switch (tongue) {
      case 'KO':
        if (capsule.repoUrl) findings.push('Repository accessible');
        else { findings.push('No repository link provided'); score -= 0.2; }
        break;
      case 'AV':
        if (capsule.demoUrl) findings.push('Demo URL responds');
        else { findings.push('No live demo available'); score -= 0.1; }
        break;
      case 'RU':
        findings.push(`Tech stack: ${capsule.techStack.join(', ')}`);
        if (capsule.description.length > 100) findings.push('Detailed description');
        break;
      case 'CA':
        findings.push(`Funding ask: $${capsule.fundingAsk.amount.toLocaleString()}`);
        break;
      case 'UM':
        if (capsule.pitchDeckUrl) findings.push('Pitch deck available');
        break;
      case 'DR':
        findings.push(score >= 0.7 ? 'Overall assessment: viable' : 'Overall assessment: needs review');
        break;
    }

    return { tongue, role, findings, score: Math.max(0, Math.min(1, score)) };
  });

  const avgScore = agents.reduce((s, a) => s + a.score, 0) / agents.length;
  const agreeCount = agents.filter(a => a.score >= 0.6).length;

  return {
    agents,
    qualityScore: avgScore,
    securityFlags: capsule.repoUrl ? [] : ['no-repo-link'],
    provenanceFlags: [],
    quorumMet: agreeCount >= 4, // 4/6 quorum threshold
    phaseLockScore: avgScore > 0.7 ? 0.9 : 0.5,
    auditedAt: new Date().toISOString(),
  };
}

// ═══════════════════════════════════════════════════════════════
// Access Level Computation
// ═══════════════════════════════════════════════════════════════

/**
 * Compute what an investor can see for a given project.
 */
export function computeAccessLevel(
  ndaSigned: boolean,
  projectDecision: GovernanceDecision
): {
  canViewPublicProfile: boolean;
  canViewFullDeck: boolean;
  canAccessDataRoom: boolean;
  canJoinLiveQA: boolean;
  canSoftCommit: boolean;
  ndaRequired: boolean;
  ndaSigned: boolean;
} {
  const isPublic = projectDecision === 'ALLOW';
  return {
    canViewPublicProfile: isPublic || projectDecision === 'QUARANTINE',
    canViewFullDeck: ndaSigned && isPublic,
    canAccessDataRoom: ndaSigned && isPublic,
    canJoinLiveQA: ndaSigned && isPublic,
    canSoftCommit: ndaSigned && isPublic,
    ndaRequired: true,
    ndaSigned,
  };
}
