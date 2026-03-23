/**
 * @file hyperbolicTrustBrowser.ts
 * @module browser/hyperbolicTrustBrowser
 * @layer Layer 1-14 (full pipeline integration)
 * @component Framework 1: Hyperbolic Trust Browser (HTB)
 *
 * Every navigation decision flows through the 14-layer hyperbolic geometry
 * pipeline. Domain trust is scored in Poincaré ball space where adversarial
 * drift costs exponentially more via d_H = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²))).
 *
 * Sacred Tongue governance gates:
 *   KO (Control)  — is this a controlled navigation?
 *   AV (I/O)      — is the target domain safe for interaction?
 *   RU (Policy)    — does this violate browsing policy?
 *   CA (Logic)     — is the navigation logically sound?
 *   UM (Security)  — cryptographic safety of connection
 *   DR (Types)     — data type safety for expected content
 *
 * A4: Symmetry — same risk → same treatment regardless of actor
 * A3: Causality — temporal ordering enforced via breathing phase
 */

import { createHash, randomBytes } from 'crypto';
import {
  BrowserAction,
  BrowserDecision,
  GovernanceResult,
  ACTION_SENSITIVITY,
  BrowserActionType,
} from './types.js';

// ============================================================================
// Types
// ============================================================================

/** Navigation intent submitted to the trust pipeline */
export interface NavigationIntent {
  /** Target URL */
  url: string;
  /** Action type */
  action: BrowserActionType;
  /** Agent ID performing the action */
  agentId: string;
  /** Actor type */
  actorType: 'human' | 'ai' | 'system';
  /** Trust score of the actor [0,1] */
  trustScore: number;
  /** Optional context for HMAC binding */
  context?: Record<string, unknown>;
}

/** Trust score result from the hyperbolic pipeline */
export interface HyperbolicTrustScore {
  /** Hyperbolic distance from safe origin */
  hyperbolicDistance: number;
  /** Per-layer contribution scores (L1-L14) */
  layerScores: number[];
  /** Sacred Tongue resonance status (KO, AV, RU, CA, UM, DR) */
  tongueResonance: boolean[];
  /** Final authorization decision */
  decision: BrowserDecision;
  /** Breathing phase at time of evaluation (temporal oscillation) */
  breathingPhase: number;
  /** Harmonic wall cost */
  harmonicCost: number;
  /** Combined risk score [0,1] */
  riskScore: number;
  /** Explanation */
  explanation: string;
}

/** Domain trust record for history tracking */
export interface DomainTrustRecord {
  domain: string;
  visits: number;
  avgHyperbolicDistance: number;
  lastVisitedAt: number;
  decisions: Record<BrowserDecision, number>;
  trustDecay: number;
}

/** HTB configuration */
export interface HTBConfig {
  /** ALLOW threshold (default: 0.3) */
  allowThreshold: number;
  /** QUARANTINE threshold (default: 0.6) */
  quarantineThreshold: number;
  /** DENY threshold (default: 0.85) */
  denyThreshold: number;
  /** Breathing frequency (default: 0.1 Hz) */
  breathingFreqHz: number;
  /** Golden ratio for tongue weighting */
  phi: number;
  /** Poincaré ball radius bound */
  ballRadiusBound: number;
}

// ============================================================================
// Constants
// ============================================================================

const PHI = 1.618033988749895;

const DEFAULT_CONFIG: HTBConfig = {
  allowThreshold: 0.3,
  quarantineThreshold: 0.6,
  denyThreshold: 0.85,
  breathingFreqHz: 0.1,
  phi: PHI,
  ballRadiusBound: 0.999,
};

/** Domain risk patterns */
const DOMAIN_RISK_PATTERNS: Array<[RegExp, number]> = [
  [/bank|chase|wellsfargo|citi/i, 0.9],
  [/paypal|stripe|venmo|finance/i, 0.85],
  [/health|medical|hospital/i, 0.8],
  [/\.gov$/i, 0.8],
  [/amazon|ebay|shop|store/i, 0.6],
  [/facebook|twitter|instagram/i, 0.5],
  [/news|cnn|bbc|reuters/i, 0.2],
  [/google|bing|search/i, 0.1],
];

/** Tongue-to-weight mapping using golden ratio progression */
const TONGUE_WEIGHTS: Record<string, number> = {
  KO: 1.0,
  AV: PHI,
  RU: PHI * PHI,
  CA: PHI * PHI * PHI,
  UM: Math.pow(PHI, 4),
  DR: Math.pow(PHI, 5),
};

// ============================================================================
// Hyperbolic Trust Browser
// ============================================================================

/**
 * Hyperbolic Trust Browser (HTB).
 *
 * Evaluates every browser action through hyperbolic geometry:
 * 1. Encode intent as a vector in Poincaré ball space
 * 2. Compute d_H from safe origin (Layer 5)
 * 3. Apply harmonic wall scaling H(d,pd) = 1/(1+d+2*pd) (Layer 12)
 * 4. Evaluate Sacred Tongue gates (Layer 13)
 * 5. Final decision: ALLOW / QUARANTINE / ESCALATE / DENY
 */
export class HyperbolicTrustBrowser {
  private readonly config: HTBConfig;
  private readonly domainHistory: Map<string, DomainTrustRecord> = new Map();

  constructor(config?: Partial<HTBConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Evaluate a navigation intent through the full 14-layer pipeline.
   */
  evaluate(intent: NavigationIntent): HyperbolicTrustScore {
    // L1-L2: Encode intent as embedding vector
    const embedding = this.encodeIntent(intent);

    // L3: Weighted transform with golden ratio
    const weighted = this.weightedTransform(embedding);

    // L4: Project to Poincaré ball
    const poincarePoint = this.projectToBall(weighted);

    // L5: Hyperbolic distance from safe origin
    const origin = new Array(poincarePoint.length).fill(0);
    const hyperbolicDistance = this.hyperbolicDistance(poincarePoint, origin);

    // L6: Breathing phase (temporal oscillation)
    const breathingPhase = this.breathingTransform(Date.now());

    // L7-L10: Phase modulation + spectral coherence (simplified)
    const layerScores = this.computeLayerScores(intent, hyperbolicDistance, breathingPhase);

    // L12: Harmonic wall cost
    const phaseDeviation = Math.abs(breathingPhase);
    const harmonicCost = this.harmonicScale(hyperbolicDistance, phaseDeviation);

    // L13: Sacred Tongue evaluation
    const tongueResonance = this.evaluateTongues(intent, hyperbolicDistance, harmonicCost);

    // Composite risk
    const riskScore = this.computeRisk(hyperbolicDistance, harmonicCost, tongueResonance, intent);

    // Decision
    const decision = this.decide(riskScore, tongueResonance);

    // Update domain history
    this.updateDomainHistory(intent.url, hyperbolicDistance, decision);

    return {
      hyperbolicDistance,
      layerScores,
      tongueResonance,
      decision,
      breathingPhase,
      harmonicCost,
      riskScore,
      explanation: this.explain(decision, riskScore, tongueResonance),
    };
  }

  /**
   * Get domain trust history.
   */
  getDomainHistory(domain?: string): DomainTrustRecord[] {
    if (domain) {
      const record = this.domainHistory.get(this.extractDomain(domain));
      return record ? [record] : [];
    }
    return Array.from(this.domainHistory.values());
  }

  // --------------------------------------------------------------------------
  // Pipeline Stages
  // --------------------------------------------------------------------------

  /** L1-L2: Encode navigation intent as numeric embedding */
  private encodeIntent(intent: NavigationIntent): number[] {
    const urlHash = createHash('sha256').update(intent.url).digest();
    const actionSensitivity = ACTION_SENSITIVITY[intent.action] ?? 0.5;
    const domainRisk = this.domainRiskScore(intent.url);

    // 6D embedding: [urlFeature, actionRisk, domainRisk, trustInverse, actorBias, temporalWeight]
    return [
      (urlHash[0]! / 255) * 0.9, // URL feature normalized
      actionSensitivity,
      domainRisk,
      1.0 - intent.trustScore, // Higher value = less trusted
      intent.actorType === 'ai' ? 0.7 : intent.actorType === 'system' ? 0.3 : 0.1,
      (Date.now() % 86400000) / 86400000, // Time-of-day feature
    ];
  }

  /** L3: Golden-ratio weighted transform */
  private weightedTransform(embedding: number[]): number[] {
    const tongueKeys = Object.keys(TONGUE_WEIGHTS);
    return embedding.map((v, i) => {
      const weight = TONGUE_WEIGHTS[tongueKeys[i % tongueKeys.length]!]!;
      return v * Math.sqrt(weight);
    });
  }

  /** L4: Project to Poincaré ball (clamp norm < 1) */
  private projectToBall(vector: number[]): number[] {
    const norm = Math.sqrt(vector.reduce((sum, v) => sum + v * v, 0));
    if (norm === 0) return vector;
    const maxNorm = this.config.ballRadiusBound;
    if (norm >= maxNorm) {
      const scale = maxNorm / norm;
      return vector.map((v) => v * scale);
    }
    return vector;
  }

  /**
   * L5: Poincaré ball distance.
   * d_H(u,v) = arcosh(1 + 2‖u-v‖² / ((1-‖u‖²)(1-‖v‖²)))
   */
  private hyperbolicDistance(u: number[], v: number[]): number {
    const diffSqNorm = u.reduce((sum, ui, i) => sum + (ui - (v[i] ?? 0)) ** 2, 0);
    const uSqNorm = u.reduce((sum, ui) => sum + ui * ui, 0);
    const vSqNorm = v.reduce((sum, vi) => sum + vi * vi, 0);

    const denom = (1 - uSqNorm) * (1 - vSqNorm);
    if (denom <= 0) return Infinity;

    const arg = 1 + (2 * diffSqNorm) / denom;
    return Math.acosh(Math.max(1, arg));
  }

  /** L6: Breathing transform — temporal oscillation */
  private breathingTransform(timestamp: number): number {
    const t = timestamp / 1000;
    const f = this.config.breathingFreqHz;
    return Math.sin(2 * Math.PI * f * t) * Math.cos(2 * Math.PI * f * 0.7 * t);
  }

  /** L7-L10: Compute per-layer contribution scores */
  private computeLayerScores(
    intent: NavigationIntent,
    distance: number,
    breathingPhase: number
  ): number[] {
    const actionRisk = ACTION_SENSITIVITY[intent.action] ?? 0.5;
    const domainRisk = this.domainRiskScore(intent.url);
    const trustGap = 1.0 - intent.trustScore;

    return [
      actionRisk, // L1: action embedding
      domainRisk, // L2: domain embedding
      actionRisk * domainRisk, // L3: weighted product
      Math.min(1, distance / 5), // L4: Poincaré embedding normalized
      Math.min(1, distance / 10), // L5: hyperbolic distance normalized
      Math.abs(breathingPhase), // L6: breathing amplitude
      Math.abs(Math.sin(distance)), // L7: phase modulation
      Math.min(1, distance * actionRisk), // L8: multi-well potential
      1.0 / (1 + Math.exp(-distance + 3)), // L9: spectral coherence (sigmoid)
      trustGap, // L10: spin coherence / trust gap
      Math.min(1, trustGap * (1 + Math.abs(breathingPhase))), // L11: temporal
      this.harmonicScale(distance, Math.abs(breathingPhase)), // L12: harmonic wall
      this.computeRisk(
        distance,
        this.harmonicScale(distance, 0),
        [true, true, true, true, true, true],
        intent
      ), // L13: risk
      Math.abs(breathingPhase) * actionRisk, // L14: audio axis
    ];
  }

  /**
   * L12: Harmonic scaling — bounded safety score in (0, 1].
   * H(d, pd) = 1 / (1 + d + 2 * pd)
   */
  private harmonicScale(distance: number, phaseDeviation: number): number {
    return 1.0 / (1 + distance + 2 * phaseDeviation);
  }

  /** L13: Evaluate Sacred Tongue gates */
  private evaluateTongues(
    intent: NavigationIntent,
    distance: number,
    harmonicCost: number
  ): boolean[] {
    // KO (Control): Is this a controlled navigation?
    const ko = intent.trustScore > 0.2;

    // AV (I/O): Is the target domain safe for interaction?
    const domainRisk = this.domainRiskScore(intent.url);
    const av = domainRisk < 0.85 || intent.trustScore > 0.8;

    // RU (Policy): Does this violate browsing policy?
    const destructive = ['execute_script', 'upload', 'download'].includes(intent.action);
    const ru = !(destructive && intent.actorType === 'ai' && intent.trustScore < 0.7);

    // CA (Logic): Is the navigation logically sound?
    const ca = distance < 8.0 && harmonicCost > 0.05;

    // UM (Security): Cryptographic safety of connection
    const um = intent.url.startsWith('https://') || intent.url.startsWith('about:');

    // DR (Types): Data type safety for expected content
    const dr = !intent.url.match(/\.(exe|dll|sh|bat|cmd|ps1)(\?|$)/i);

    return [ko, av, ru, ca, um, dr];
  }

  /** Compute composite risk score */
  private computeRisk(
    distance: number,
    harmonicCost: number,
    tongues: boolean[],
    intent: NavigationIntent
  ): number {
    const actionRisk = ACTION_SENSITIVITY[intent.action] ?? 0.5;
    const domainRisk = this.domainRiskScore(intent.url);
    const trustPenalty = 1.0 - intent.trustScore;

    // Tongue penalty: each failing tongue adds weighted risk
    const tongueNames = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
    let tonguePenalty = 0;
    for (let i = 0; i < tongues.length; i++) {
      if (!tongues[i]) {
        tonguePenalty += (TONGUE_WEIGHTS[tongueNames[i]!]! / Math.pow(PHI, 5)) * 0.15;
      }
    }

    const raw =
      0.25 * actionRisk +
      0.2 * domainRisk +
      0.2 * Math.min(1, distance / 5) +
      0.15 * trustPenalty +
      0.1 * (1 - harmonicCost) +
      0.1 * tonguePenalty;

    return Math.max(0, Math.min(1, raw));
  }

  /** Make governance decision from risk score and tongue status */
  private decide(riskScore: number, tongues: boolean[]): BrowserDecision {
    // Critical tongue failures (RU + UM) → immediate DENY
    if (!tongues[2] && !tongues[4]) return 'DENY';

    // Security tongue failure alone → ESCALATE
    if (!tongues[4]) return 'ESCALATE';

    if (riskScore >= this.config.denyThreshold) return 'DENY';
    if (riskScore >= this.config.quarantineThreshold) return 'ESCALATE';
    if (riskScore >= this.config.allowThreshold) return 'QUARANTINE';
    return 'ALLOW';
  }

  // --------------------------------------------------------------------------
  // Utilities
  // --------------------------------------------------------------------------

  private domainRiskScore(url: string): number {
    const domain = this.extractDomain(url);
    for (const [pattern, risk] of DOMAIN_RISK_PATTERNS) {
      if (pattern.test(domain)) return risk;
    }
    // Check history
    const record = this.domainHistory.get(domain);
    if (record && record.visits > 5) {
      return Math.min(0.8, record.avgHyperbolicDistance / 10);
    }
    return 0.4; // Unknown domain
  }

  private extractDomain(url: string): string {
    try {
      return new URL(url).hostname;
    } catch {
      return url;
    }
  }

  private updateDomainHistory(url: string, distance: number, decision: BrowserDecision): void {
    const domain = this.extractDomain(url);
    const existing = this.domainHistory.get(domain);

    if (existing) {
      existing.visits++;
      existing.avgHyperbolicDistance =
        (existing.avgHyperbolicDistance * (existing.visits - 1) + distance) / existing.visits;
      existing.lastVisitedAt = Date.now();
      existing.decisions[decision] = (existing.decisions[decision] || 0) + 1;
    } else {
      this.domainHistory.set(domain, {
        domain,
        visits: 1,
        avgHyperbolicDistance: distance,
        lastVisitedAt: Date.now(),
        decisions: { ALLOW: 0, QUARANTINE: 0, ESCALATE: 0, DENY: 0, [decision]: 1 },
        trustDecay: 1.0,
      });
    }
  }

  private explain(decision: BrowserDecision, risk: number, tongues: boolean[]): string {
    const tongueNames = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
    const failedTongues = tongueNames.filter((_, i) => !tongues[i]);
    const parts = [`Decision: ${decision} (risk=${risk.toFixed(3)})`];
    if (failedTongues.length > 0) {
      parts.push(`Failed tongues: ${failedTongues.join(', ')}`);
    }
    return parts.join('. ');
  }
}
